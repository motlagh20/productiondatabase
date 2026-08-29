"""DRF serializers for the slice endpoints.

Input serializers validate clean-core rules (wagon plate must exist in the dimension,
chamber 1..40) so typos cannot enter — the frontend uses dropdowns, and the backend
double-checks the FK exists.
"""
from rest_framework import serializers

from .models import Chamber, Glaze, Operator, Product, Wagon


class ReadingIn(serializers.Serializer):
    sensor_code = serializers.CharField(max_length=30)
    temperature_c = serializers.DecimalField(max_digits=6, decimal_places=2,
                                              required=False, allow_null=True)


class SettingLoadIn(serializers.Serializer):
    plate = serializers.CharField(max_length=20)
    chamber_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    product_id = serializers.IntegerField(required=False, allow_null=True)
    glaze_id = serializers.IntegerField(required=False, allow_null=True)
    operator_id = serializers.IntegerField(required=False, allow_null=True)
    shift = serializers.IntegerField(required=False, allow_null=True)
    date_jalali = serializers.CharField(max_length=10, required=False, allow_blank=True)
    start_time = serializers.TimeField(required=False, allow_null=True)
    end_time = serializers.TimeField(required=False, allow_null=True)
    packages = serializers.IntegerField(required=False, allow_null=True)
    khesht_count = serializers.IntegerField(required=False, allow_null=True)
    client_token = serializers.UUIDField(required=False, allow_null=True)

    def validate_plate(self, value):
        if not Wagon.objects.filter(wagon_name=value).exists():
            raise serializers.ValidationError(f'Unknown wagon plate: {value}')
        return value

    def validate_chamber_code(self, value):
        if value and not Chamber.objects.filter(chamber_code=value).exists():
            raise serializers.ValidationError(f'Unknown chamber: {value}')
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
    total_count = serializers.IntegerField(required=False, allow_null=True)
    grade1_count = serializers.IntegerField(required=False, allow_null=True)
    grade2_count = serializers.IntegerField(required=False, allow_null=True)
    waste_count = serializers.IntegerField(required=False, allow_null=True)


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
