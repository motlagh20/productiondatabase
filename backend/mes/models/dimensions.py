"""Dimension masters (clean core, ADR-0006).

These mirror the canonical staging dimensions. They are seeded once from staging
(see management/commands/seed_dimensions.py) and are otherwise read-only reference
data in the app. Wagon identity = FK here; no ">80" validator (dropdown prevents
typos at source — clean-core rule, M5_PROPOSED_SCHEMA §3).
"""
from django.db import models

# Avoid circular import: reference spine models by string label.
DRYER_CYCLE = 'mes.DryerCycle'
SETTING_EVENT = 'mes.SettingEvent'


class Operator(models.Model):
    operator_id = models.BigAutoField(primary_key=True)
    operator_code = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=100, blank=True, default='')
    role = models.CharField(max_length=50, blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('operator_id',)

    def __str__(self):
        return f'{self.operator_code} — {self.full_name}'


class Chamber(models.Model):
    chamber_id = models.BigAutoField(primary_key=True)
    chamber_code = models.CharField(max_length=20, unique=True)
    chamber_type = models.CharField(max_length=20, default='SETTING')
    description = models.CharField(max_length=100, blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('chamber_id',)

    def __str__(self):
        return self.chamber_code


class Product(models.Model):
    """Composite product (mold + glaze + attributes). Legacy codes are cross-references only."""
    product_id = models.BigAutoField(primary_key=True)
    product_code_kiln = models.CharField(max_length=20, blank=True, default='')
    product_code_packing = models.CharField(max_length=20, blank=True, default='')
    product_name_setting = models.CharField(max_length=100, blank=True, default='')
    product_group = models.CharField(max_length=50, blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('product_id',)

    def __str__(self):
        return self.product_name_setting or self.product_code_kiln or f'#{self.product_id}'


class Glaze(models.Model):
    glaze_id = models.BigAutoField(primary_key=True)
    glaze_code = models.CharField(max_length=20, unique=True)
    glaze_name = models.CharField(max_length=100)
    formula = models.TextField(blank=True, default='')
    description = models.TextField(blank=True, default='')
    is_combined = models.BooleanField(default=False)

    class Meta:
        ordering = ('glaze_id',)

    def __str__(self):
        return f'{self.glaze_code} — {self.glaze_name}'


class Wagon(models.Model):
    """Physical wagon identified by plate NAME (1..80 valid range)."""
    wagon_id = models.BigAutoField(primary_key=True)
    wagon_name = models.CharField(max_length=20, unique=True)

    class Meta:
        ordering = ('wagon_id',)

    def __str__(self):
        return self.wagon_name


class KilnSensor(models.Model):
    sensor_id = models.BigAutoField(primary_key=True)
    sensor_code = models.CharField(max_length=30, unique=True)
    sensor_name = models.CharField(max_length=50, blank=True, default='')
    position_order = models.SmallIntegerField(default=0)
    is_measured = models.BooleanField(default=True)

    class Meta:
        ordering = ('position_order', 'sensor_id')

    def __str__(self):
        return self.sensor_code


class ChamberState(models.Model):
    """Point-in-time control table: is a drying chamber currently LOADED (full)?

    A chamber goes empty -> loaded when its dryer cycle is registered, and back to
    empty when its loaded body is discharged into a Setting batch. Because a chamber
    stays loaded for 1-2+ days (drying time), the live state is NOT derivable from a
    whole-history aggregate — it tracks the LAST event per chamber. This table is the
    authoritative 'which chambers are full right now' source for the Setting form.
    """
    chamber = models.OneToOneField(Chamber, on_delete=models.PROTECT, primary_key=True,
                                   related_name='state')
    is_loaded = models.BooleanField(default=False)
    current_dryer_cycle = models.ForeignKey(DRYER_CYCLE, on_delete=models.SET_NULL,
                                            null=True, blank=True, related_name='+')
    current_setting_event = models.ForeignKey(SETTING_EVENT, on_delete=models.SET_NULL,
                                              null=True, blank=True, related_name='+')
    loaded_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('chamber',)

    def __str__(self):
        return f'{self.chamber.chamber_code}: {"LOADED" if self.is_loaded else "empty"}'
