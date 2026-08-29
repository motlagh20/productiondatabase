"""Trip spine + module fact tables (clean core).

The wagon_trip is the journey spine: trip_id is system-assigned at Setting load
START (owner rule 2026-08-29), never typed by an operator. Unlike the staging
wagon_trip CHECK (which allows only in_progress/completed/abandoned/incomplete),
the app models the FULL SRS §3.1 state machine — body_dried and waiting_hall
included — because the app owns its own schema (ADR-0008 clean core).
"""
from django.db import models

from .dimensions import Chamber, Glaze, KilnSensor, Operator, Product, Wagon


class WagonTrip(models.Model):
    STATUS_BODY_DRIED = 'body_dried'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_WAITING_HALL = 'waiting_hall'
    STATUS_IN_TUNNEL = 'in_tunnel'
    STATUS_AWAITING_DISCHARGE = 'awaiting_discharge'
    STATUS_COMPLETED = 'completed'
    STATUS_ABANDONED = 'abandoned'
    STATUS_INCOMPLETE = 'incomplete'
    STATUS_CHOICES = [
        (STATUS_BODY_DRIED, 'body_dried'),
        (STATUS_IN_PROGRESS, 'in_progress'),
        (STATUS_WAITING_HALL, 'waiting_hall'),
        (STATUS_IN_TUNNEL, 'in_tunnel'),
        (STATUS_AWAITING_DISCHARGE, 'awaiting_discharge'),
        (STATUS_COMPLETED, 'completed'),
        (STATUS_ABANDONED, 'abandoned'),
        (STATUS_INCOMPLETE, 'incomplete'),
    ]

    trip_id = models.BigAutoField(primary_key=True)
    wagon = models.ForeignKey(Wagon, on_delete=models.PROTECT, db_column='wagon_id')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_IN_PROGRESS)
    source_module = models.CharField(max_length=20, default='setting')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('trip_id',)

    def __str__(self):
        return f'trip#{self.trip_id} ({self.wagon.wagon_name}, {self.status})'


class SettingLoad(models.Model):
    """One wagon load in Setting. Assigns the trip (F2). chamber = REFERENCE to
    the source dryer chamber (1..40), not a Setting-owned chamber."""
    setting_load_id = models.BigAutoField(primary_key=True)
    trip = models.ForeignKey(WagonTrip, on_delete=models.PROTECT, db_column='trip_id',
                             related_name='setting_loads')
    wagon = models.ForeignKey(Wagon, on_delete=models.PROTECT, db_column='wagon_id')
    chamber = models.ForeignKey(Chamber, on_delete=models.PROTECT, db_column='chamber_id',
                                null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, db_column='product_id',
                                null=True, blank=True)
    glaze = models.ForeignKey(Glaze, on_delete=models.PROTECT, db_column='glaze_id',
                              null=True, blank=True)
    operator = models.ForeignKey(Operator, on_delete=models.PROTECT, db_column='operator_id',
                                 null=True, blank=True)
    shift = models.SmallIntegerField(null=True, blank=True)
    date_jalali = models.CharField(max_length=10, blank=True, default='')
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    packages = models.IntegerField(null=True, blank=True)
    khesht_count = models.IntegerField(null=True, blank=True)
    # Replay-safety: a retried POST with the same token returns the original row.
    client_token = models.UUIDField(null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('setting_load_id',)


class KilnPush(models.Model):
    """One kiln push = one wagon (F3). push_seq is the FIFO ordering key."""
    kiln_push_id = models.BigAutoField(primary_key=True)
    trip = models.ForeignKey(WagonTrip, on_delete=models.PROTECT, db_column='trip_id',
                             related_name='kiln_pushes')
    wagon = models.ForeignKey(Wagon, on_delete=models.PROTECT, db_column='wagon_id')
    push_seq = models.BigIntegerField(unique=True)
    push_date = models.CharField(max_length=10, blank=True, default='')
    push_time = models.TimeField(null=True, blank=True)
    shift = models.SmallIntegerField(null=True, blank=True)
    operator = models.ForeignKey(Operator, on_delete=models.PROTECT, db_column='operator_id',
                                 null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, db_column='product_id',
                                null=True, blank=True)
    push_duration = models.DurationField(null=True, blank=True)
    client_token = models.UUIDField(null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('push_seq',)


class KilnReading(models.Model):
    """One sensor reading per push (row-oriented, 18 sensors)."""
    kiln_reading_id = models.BigAutoField(primary_key=True)
    kiln_push = models.ForeignKey(KilnPush, on_delete=models.CASCADE, db_column='kiln_push_id',
                                  related_name='readings')
    sensor = models.ForeignKey(KilnSensor, on_delete=models.PROTECT, db_column='sensor_id')
    temperature_c = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = (('kiln_push', 'sensor'),)


class KilnExit(models.Model):
    """Awaiting-discharge list (F4). FIFO-44: exit_push_seq = entry_push_seq + 43."""
    kiln_exit_id = models.BigAutoField(primary_key=True)
    trip = models.ForeignKey(WagonTrip, on_delete=models.PROTECT, db_column='trip_id',
                             related_name='kiln_exits', null=True, blank=True)
    wagon = models.ForeignKey(Wagon, on_delete=models.PROTECT, db_column='wagon_id')
    entry_push_seq = models.IntegerField(null=True, blank=True)
    exit_push_seq = models.IntegerField(null=True, blank=True)
    exit_date = models.CharField(max_length=10, blank=True, default='')
    discharged = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('exit_push_seq',)
        unique_together = (('wagon', 'exit_push_seq'),)


class PackingHeader(models.Model):
    """One packing session (F5). Closing packing completes the trip(s)."""
    packing_header_id = models.BigAutoField(primary_key=True)
    pack_date = models.CharField(max_length=10, blank=True, default='')
    shift = models.SmallIntegerField(null=True, blank=True)
    controller = models.ForeignKey(Operator, on_delete=models.PROTECT, db_column='controller_id',
                                   null=True, blank=True)
    worker_count = models.IntegerField(null=True, blank=True)
    client_token = models.UUIDField(null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('packing_header_id',)


class PackingWagon(models.Model):
    packing_wagon_id = models.BigAutoField(primary_key=True)
    packing_header = models.ForeignKey(PackingHeader, on_delete=models.CASCADE,
                                       db_column='packing_header_id', related_name='wagons')
    trip = models.ForeignKey(WagonTrip, on_delete=models.PROTECT, db_column='trip_id',
                             related_name='packing_wagons', null=True, blank=True)
    wagon = models.ForeignKey(Wagon, on_delete=models.PROTECT, db_column='wagon_id')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, db_column='product_id',
                                null=True, blank=True)
    total_count = models.IntegerField(null=True, blank=True)
    grade1_count = models.IntegerField(null=True, blank=True)
    grade2_count = models.IntegerField(null=True, blank=True)
    waste_count = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ('packing_wagon_id',)
