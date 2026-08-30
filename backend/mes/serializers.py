"""DRF serializers for the slice endpoints.

Input serializers validate clean-core rules (wagon plate must exist in the dimension,
chamber 1..40) so typos cannot enter — the frontend uses dropdowns, and the backend
double-checks the FK exists.
"""
from rest_framework import serializers

from .models import Chamber, DryerCycle, Glaze, Operator, Product, Wagon


class ReadingIn(serializers.Serializer):
    sensor_code = serializers.CharField(max_length=30)
    temperature_c = serializers.DecimalField(max_digits=6, decimal_places=2,
                                              required=False, allow_null=True)


class SettingWagonIn(serializers.Serializer):
    wagon_id = serializers.IntegerField()
    glaze_id = serializers.IntegerField(required=False, allow_null=True)
    start_time = serializers.TimeField(required=False, allow_null=True)
    end_time = serializers.TimeField(required=False, allow_null=True)
    packages = serializers.IntegerField(required=False, allow_null=True)
    khesht_count = serializers.IntegerField(required=False, allow_null=True)

    def validate_wagon_id(self, value):
        if not Wagon.objects.filter(pk=value).exists():
            raise serializers.ValidationError(f'Unknown wagon id: {value}')
        return value


class SettingEventIn(serializers.Serializer):
    """CHAMBER-CENTRIC Setting batch: one chamber + 1..4 wagons fed from it."""
    chamber_code = serializers.CharField(max_length=20)
    date_jalali = serializers.CharField(max_length=10, required=False, allow_blank=True)
    shift = serializers.IntegerField(required=False, allow_null=True)
    product_id = serializers.IntegerField(required=False, allow_null=True)
    supervisor_id = serializers.IntegerField(required=False, allow_null=True)
    operator_id = serializers.IntegerField(required=False, allow_null=True)
    personnel_count = serializers.IntegerField(required=False, allow_null=True)
    fingers_count = serializers.IntegerField(required=False, allow_null=True)
    columns_count = serializers.IntegerField(required=False, allow_null=True)
    dryer_waste = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, allow_null=True)
    wagons = SettingWagonIn(many=True)
    client_token = serializers.UUIDField(required=False, allow_null=True)

    def validate_chamber_code(self, value):
        if not Chamber.objects.filter(chamber_code=value).exists():
            raise serializers.ValidationError(f'Unknown chamber: {value}')
        return value

    def validate_wagons(self, value):
        if not (1 <= len(value) <= 4):
            raise serializers.ValidationError('A Setting batch needs 1..4 wagons.')
        return value


class KilnPushIn(serializers.Serializer):
    trip_id = serializers.IntegerField()
    push_date = serializers.CharField(max_length=10, required=False, allow_blank=True)
    push_time = serializers.TimeField(required=False, allow_null=True)
    shift = serializers.IntegerField(required=False, allow_null=True)
    operator_id = serializers.IntegerField(required=False, allow_null=True)
    product_id = serializers.IntegerField(required=False, allow_null=True)
    readings = ReadingIn(many=True, required=False)
    client_token = serializers.UUIDField(required=False, allow_null=True)


class KilnExitIn(serializers.Serializer):
    trip_id = serializers.IntegerField()
    exit_date = serializers.CharField(max_length=10, required=False, allow_blank=True)


class PackingWagonIn(serializers.Serializer):
    trip_id = serializers.IntegerField()
    product_id = serializers.IntegerField(required=False, allow_null=True)
    total_count = serializers.IntegerField(required=True)
    grade1_count = serializers.IntegerField(required=True)
    grade2_count = serializers.IntegerField(required=True)
    waste_count = serializers.IntegerField(required=True)


class PackingHeaderIn(serializers.Serializer):
    pack_date = serializers.CharField(max_length=10, required=False, allow_blank=True)
    shift = serializers.IntegerField(required=False, allow_null=True)
    controller_id = serializers.IntegerField(required=False, allow_null=True)
    worker_count = serializers.IntegerField(required=False, allow_null=True)
    wagons = PackingWagonIn(many=True)
    client_token = serializers.UUIDField(required=False, allow_null=True)

    def validate_wagons(self, value):
        if not value:
            raise serializers.ValidationError('At least one wagon is required.')
        return value


# --- Dimension read serializers (for form dropdowns) ---
class OperatorOut(serializers.ModelSerializer):
    class Meta:
        model = Operator
        fields = ('operator_id', 'operator_code', 'full_name')


class ProductOut(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ('product_id', 'product_name_setting', 'product_code_kiln', 'product_code_packing')


class GlazeOut(serializers.ModelSerializer):
    class Meta:
        model = Glaze
        fields = ('glaze_id', 'glaze_code', 'glaze_name')


class WagonOut(serializers.ModelSerializer):
    class Meta:
        model = Wagon
        fields = ('wagon_id', 'wagon_name')


class ChamberOut(serializers.ModelSerializer):
    class Meta:
        model = Chamber
        fields = ('chamber_id', 'chamber_code', 'chamber_type')


class DryerReadingIn(serializers.Serializer):
    hour_offset = serializers.IntegerField(required=False, allow_null=True)
    humidity_pct = serializers.DecimalField(max_digits=6, decimal_places=2,
                                            required=False, allow_null=True)
    temperature_c = serializers.DecimalField(max_digits=6, decimal_places=2,
                                             required=False, allow_null=True)


class DryerCycleIn(serializers.Serializer):
    chamber_id = serializers.IntegerField()
    load_date = serializers.CharField(max_length=10, required=False, allow_blank=True)
    load_time = serializers.TimeField(required=False, allow_null=True)
    unload_date = serializers.CharField(max_length=10, required=False, allow_blank=True)
    unload_time = serializers.TimeField(required=False, allow_null=True)
    load_operator_id = serializers.IntegerField(required=False, allow_null=True)
    unload_operator_id = serializers.IntegerField(required=False, allow_null=True)
    product_id = serializers.IntegerField(required=False, allow_null=True)
    finger_count = serializers.IntegerField(required=False, allow_null=True)
    readings = DryerReadingIn(many=True, required=False)

    def validate_chamber_id(self, value):
        if not Chamber.objects.filter(pk=value).exists():
            raise serializers.ValidationError(f'Unknown chamber id: {value}')
        return value
