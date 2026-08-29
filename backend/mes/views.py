"""API views for the vertical slice (F2–F5 write + F7 journey read)."""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import services
from .models import Chamber, Glaze, KilnSensor, Operator, Product, Wagon, WagonTrip
from .serializers import (
    ChamberOut,
    GlazeOut,
    KilnExitIn,
    KilnPushIn,
    OperatorOut,
    PackingHeaderIn,
    ProductOut,
    SettingLoadIn,
    WagonOut,
)

WRITE_PERMISSION = IsAuthenticated


def _as_lookup_objects(serializer, validated, wagon=None, trip=None):
    obj = dict(validated)
    plate = obj.pop('plate', None)
    chamber_code = obj.pop('chamber_code', None)
    if plate is not None:
        obj['wagon'] = Wagon.objects.get(wagon_name=plate)
    if chamber_code:
        obj['chamber'] = Chamber.objects.get(chamber_code=chamber_code)
    if trip is not None:
        obj['trip'] = trip
    return obj


@api_view(['POST'])
@permission_classes([WRITE_PERMISSION])
def setting_load_create(request):
    """F2: register a wagon load → creates the trip (system-assigned), status in_progress."""
    ser = SettingLoadIn(data=request.data)
    ser.is_valid(raise_exception=True)
    kwargs = _as_lookup_objects(ser, ser.validated_data)
    client_token = kwargs.pop('client_token', None)
    load = services.start_setting_load(wagon=kwargs.pop('wagon'), client_token=client_token, **kwargs)
    return Response({
        'trip_id': load.trip_id,
        'setting_load_id': load.setting_load_id,
        'status': load.trip.status,
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([WRITE_PERMISSION])
def kiln_push_create(request):
    """F3: register a kiln push (1 wagon, optional 18 sensor readings)."""
    ser = KilnPushIn(data=request.data)
    ser.is_valid(raise_exception=True)
    data = dict(ser.validated_data)
    trip = WagonTrip.objects.get(pk=data.pop('trip_id'))
    readings = data.pop('readings', None)
    client_token = data.pop('client_token', None)
    if data.get('operator_id'):
        data['operator'] = Operator.objects.get(pk=data.pop('operator_id'))
    if data.get('product_id'):
        data['product'] = Product.objects.get(pk=data.pop('product_id'))
    push = services.push_wagon(trip=trip, readings=readings, client_token=client_token, **data)
    return Response({
        'kiln_push_id': push.kiln_push_id,
        'trip_id': push.trip_id,
        'push_seq': push.push_seq,
        'status': push.trip.status,
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([WRITE_PERMISSION])
def kiln_exit_create(request):
    """F4: mark trip discharge → awaiting-discharge list (exit = entry + 43)."""
    ser = KilnExitIn(data=request.data)
    ser.is_valid(raise_exception=True)
    trip = WagonTrip.objects.get(pk=ser.validated_data['trip_id'])
    kiln_exit = services.exit_wagon(trip=trip, exit_date=ser.validated_data.get('exit_date', ''))
    return Response({
        'kiln_exit_id': kiln_exit.kiln_exit_id,
        'trip_id': trip.trip_id,
        'entry_push_seq': kiln_exit.entry_push_seq,
        'exit_push_seq': kiln_exit.exit_push_seq,
        'status': trip.status,
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([WRITE_PERMISSION])
def packing_header_create(request):
    """F5: packing session over 1+ awaiting-discharge wagons → trips completed."""
    ser = PackingHeaderIn(data=request.data)
    ser.is_valid(raise_exception=True)
    data = dict(ser.validated_data)
    wagons = data.pop('wagons')
    client_token = data.pop('client_token', None)
    if data.get('controller_id'):
        data['controller'] = Operator.objects.get(pk=data.pop('controller_id'))
    header = services.register_packing(wagons=wagons, client_token=client_token, **data)
    return Response({
        'packing_header_id': header.packing_header_id,
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([WRITE_PERMISSION])
def wagon_journey(request):
    """F7: full trip timeline for a wagon plate name."""
    plate = request.query_params.get('plate')
    if not plate:
        return Response({'detail': 'plate query param is required.'}, status=400)
    return Response({'plate': plate, 'trips': services.wagon_journey(plate=plate)})


# --- Dimension dropdowns (form options) ---
@api_view(['GET'])
@permission_classes([WRITE_PERMISSION])
def operator_list(request):
    return Response(OperatorOut(Operator.objects.all(), many=True).data)


@api_view(['GET'])
@permission_classes([WRITE_PERMISSION])
def product_list(request):
    return Response(ProductOut(Product.objects.all(), many=True).data)


@api_view(['GET'])
@permission_classes([WRITE_PERMISSION])
def glaze_list(request):
    return Response(GlazeOut(Glaze.objects.all(), many=True).data)


@api_view(['GET'])
@permission_classes([WRITE_PERMISSION])
def wagon_list(request):
    return Response(WagonOut(Wagon.objects.all(), many=True).data)


@api_view(['GET'])
@permission_classes([WRITE_PERMISSION])
def chamber_list(request):
    return Response(ChamberOut(Chamber.objects.all(), many=True).data)


@api_view(['GET'])
@permission_classes([WRITE_PERMISSION])
def sensor_list(request):
    sensors = KilnSensor.objects.all()
    return Response([
        {'sensor_id': s.sensor_id, 'sensor_code': s.sensor_code, 'sensor_name': s.sensor_name}
        for s in sensors
    ])


@api_view(['GET'])
@permission_classes([WRITE_PERMISSION])
def awaiting_discharge_list(request):
    trips = WagonTrip.objects.filter(status=WagonTrip.STATUS_AWAITING_DISCHARGE).order_by('trip_id')
    return Response([
        {'trip_id': t.trip_id, 'plate': t.wagon.wagon_name} for t in trips
    ])
