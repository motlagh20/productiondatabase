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


class SettingEvent(models.Model):
    """CHAMBER-CENTRIC Setting batch header (F2). One dryer chamber unloaded → its body
    loaded onto 1..4 wagons until the chamber is empty. Mirrors staging `setting_event`."""
    setting_event_id = models.BigAutoField(primary_key=True)
    date_jalali = models.CharField(max_length=10, blank=True, default='')
    shift = models.SmallIntegerField(null=True, blank=True)
    chamber = models.ForeignKey(Chamber, on_delete=models.PROTECT, db_column='chamber_id')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, db_column='product_id',
                                null=True, blank=True)
    supervisor = models.ForeignKey(Operator, on_delete=models.PROTECT, db_column='supervisor_id',
                                   null=True, blank=True, related_name='supervised_setting_events')
    operator = models.ForeignKey(Operator, on_delete=models.PROTECT, db_column='operator_id',
                                 null=True, blank=True, related_name='setting_operator')
    personnel_count = models.IntegerField(null=True, blank=True)
    fingers_count = models.IntegerField(null=True, blank=True)
    columns_count = models.IntegerField(null=True, blank=True)
    dryer_waste = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    source_row = models.IntegerField(null=True, blank=True)
    client_token = models.UUIDField(null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('setting_event_id',)

    def __str__(self):
        return f'setting#{self.setting_event_id} (chamber {self.chamber_id}, {self.date_jalali})'


class SettingWagon(models.Model):
    """One wagon loaded within a Setting batch (F2). 1..4 per event. Assigns its own trip."""
    setting_wagon_id = models.BigAutoField(primary_key=True)
    setting_event = models.ForeignKey(SettingEvent, on_delete=models.PROTECT,
                                      db_column='setting_event_id', related_name='wagons')
    wagon = models.ForeignKey(Wagon, on_delete=models.PROTECT, db_column='wagon_id')
    glaze = models.ForeignKey(Glaze, on_delete=models.PROTECT, db_column='glaze_id',
                              null=True, blank=True)
    trip = models.ForeignKey(WagonTrip, on_delete=models.PROTECT, db_column='trip_id',
                             related_name='setting_wagons', null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    packages = models.IntegerField(null=True, blank=True)
    khesht_count = models.IntegerField(null=True, blank=True)
    position_in_event = models.SmallIntegerField(default=1)

    class Meta:
        ordering = ('setting_event', 'position_in_event')
        unique_together = (('setting_event', 'wagon', 'position_in_event'),)


class KilnPush(models.Model):
    """One kiln push = one wagon (F3). push_seq is the FIFO ordering key. push_time captured exactly."""
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


class DryerCycle(models.Model):
    """F1 (FIRST production step): one dryer chamber load/unload cycle. The dried body
    produced here is what Setting later loads onto wagons. Mirrors staging `dryer_cycle`."""
    dryer_cycle_id = models.BigAutoField(primary_key=True)
    chamber = models.ForeignKey(Chamber, on_delete=models.PROTECT, db_column='chamber_id',
                               null=True, blank=True)
    load_date = models.CharField(max_length=10, blank=True, default='')
    load_time = models.TimeField(null=True, blank=True)
    unload_date = models.CharField(max_length=10, blank=True, default='')
    unload_time = models.TimeField(null=True, blank=True)
    load_operator = models.ForeignKey(Operator, on_delete=models.PROTECT, db_column='load_operator_id',
                                     null=True, blank=True, related_name='+')
    unload_operator = models.ForeignKey(Operator, on_delete=models.PROTECT, db_column='unload_operator_id',
                                       null=True, blank=True, related_name='+')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, db_column='product_id',
                               null=True, blank=True)
    finger_count = models.IntegerField(null=True, blank=True)
    chamber_no = models.IntegerField(null=True, blank=True)  # raw reference to dryer chamber 1..40
    source_row = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('dryer_cycle_id',)


class DryerReading(models.Model):
    """Hourly humidity/temp reading for a dryer cycle (row-oriented, 22 readings per day)."""
    dryer_reading_id = models.BigAutoField(primary_key=True)
    dryer_cycle = models.ForeignKey(DryerCycle, on_delete=models.CASCADE, db_column='dryer_cycle_id',
                                   related_name='readings')
    hour_offset = models.IntegerField(null=True, blank=True)  # 0..21
    humidity_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    temperature_c = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = (('dryer_cycle', 'hour_offset'),)


class EtlReject(models.Model):
    """Quarantine for historical rows that cannot enter the clean app core (ADR-0008).

    The historical staging data contains operator typos (wagon_no > 80, NULL plates,
    out-of-range batches). Per the owner rule, these are NEVER silently corrected or
    admitted into the app — they are logged here with the reason + raw source row so a
    human can adjudicate them against the paper ledgers. The app's clean core stays
    unpolluted; this table is the *only* place dirty history lands.
    """
    MODULE_CHOICES = [
        ('setting', 'setting'),
        ('kiln', 'kiln'),
        ('packing', 'packing'),
        ('dryer', 'dryer'),
    ]
    etl_reject_id = models.BigAutoField(primary_key=True)
    module = models.CharField(max_length=20, choices=MODULE_CHOICES)
    source_row = models.IntegerField(null=True, blank=True)
    reason = models.TextField()
    raw = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('etl_reject_id',)

    def __str__(self):
        return f'reject#{self.etl_reject_id} ({self.module}): {self.reason[:60]}'
