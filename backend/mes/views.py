"""API views for the vertical slice (F2–F5 write + F7 journey read)."""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import services
from .exceptions import IsManager
from .models import Chamber, Glaze, KilnPush, KilnSensor, Operator, Product, Wagon, WagonTrip
from .serializers import (
    ChamberOut,
    DryerCycleIn,
    GlazeOut,
    KilnPushIn,
    OperatorOut,
    PackingHeaderIn,
    ProductOut,
    SettingEventIn,
    SettingWagonIn,
    WagonOut,
)

WRITE_PERMISSION = IsAuthenticated


@api_view(['POST'])
@permission_classes([WRITE_PERMISSION])
def dryer_cycle_create(request):
    """F1 (FIRST step): register a dryer cycle + hourly humidity/temp readings."""
    ser = DryerCycleIn(data=request.data)
    ser.is_valid(raise_exception=True)
    d = ser.validated_data
    chamber = Chamber.objects.get(pk=d['chamber_id'])
    cycle = services.create_dryer_cycle(
        chamber=chamber,
        readings=d.get('readings'),
        load_date=d.get('load_date', ''),
        load_time=d.get('load_time'),
        unload_date=d.get('unload_date', ''),
        unload_time=d.get('unload_time'),
        load_operator_id=d.get('load_operator_id'),
        unload_operator_id=d.get('unload_operator_id'),
        product_id=d.get('product_id'),
        finger_count=d.get('finger_count'),
    )
    return Response(
        {'dryer_cycle_id': cycle.dryer_cycle_id, 'readings': cycle.readings.count()},
        status=status.HTTP_201_CREATED,
    )


def _as_lookup_objects(serializer, validated, wagon=None, trip=None):
    obj = dict(validated)
    if trip is not None:
        obj['trip'] = trip
    return obj


@api_view(['POST'])
@permission_classes([WRITE_PERMISSION])
def setting_event_create(request):
    """F2 (CHAMBER-CENTRIC): register a Setting batch (one chamber + 1..4 wagons)."""
    ser = SettingEventIn(data=request.data)
    ser.is_valid(raise_exception=True)
    data = dict(ser.validated_data)
    chamber = Chamber.objects.get(pk=data.pop('chamber_id'))
    wagons = data.pop('wagons')
    client_token = data.pop('client_token', None)
    # resolve wagon FKs inside each wagon payload
    wagon_objs = []
    for w in wagons:
        w['wagon'] = Wagon.objects.get(pk=w.pop('wagon_id'))
        if w.get('glaze_id'):
            w['glaze'] = Glaze.objects.get(pk=w.pop('glaze_id'))
        wagon_objs.append(w)
    if data.get('product_id'):
        data['product'] = Product.objects.get(pk=data.pop('product_id'))
    if data.get('supervisor_id'):
        data['supervisor'] = Operator.objects.get(pk=data.pop('supervisor_id'))
    if data.get('operator_id'):
        data['operator'] = Operator.objects.get(pk=data.pop('operator_id'))
    event = services.create_setting_batch(chamber=chamber, wagons=wagon_objs,
                                           client_token=client_token, **data)
    return Response({
        'setting_event_id': event.setting_event_id,
        'chamber': event.chamber_id,
        'wagon_count': event.wagons.count(),
        'trip_ids': [w.trip_id for w in event.wagons.all()],
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([WRITE_PERMISSION])
def kiln_push_create(request):
    """F3: register a kiln push for an ACTIVE wagon (1 wagon, optional 18 sensor readings).
    Auto-derives the FIFO-44 discharge (no manual exit form)."""
    ser = KilnPushIn(data=request.data)
    ser.is_valid(raise_exception=True)
    data = dict(ser.validated_data)
    wagon = Wagon.objects.get(pk=data.pop('wagon_id'))
    client_token = data.pop('client_token', None)

    # Replay-safe: if this exact (wagon + token) was already pushed, return it.
    if client_token is not None:
        existing = KilnPush.objects.filter(client_token=client_token, wagon=wagon).first()
        if existing is not None:
            return Response({
                'kiln_push_id': existing.kiln_push_id,
                'trip_id': existing.trip_id,
                'push_seq': existing.push_seq,
                'exit_push_seq': existing.push_seq + 43,
                'status': existing.trip.status,
            }, status=status.HTTP_201_CREATED)

    # Find the active trip for this wagon (the one not yet packed).
    trip = (
        WagonTrip.objects
        .filter(wagon=wagon, status__in=[WagonTrip.STATUS_IN_PROGRESS, WagonTrip.STATUS_WAITING_HALL])
        .order_by('trip_id')
        .first()
    )
    if trip is None:
        return Response(
            {'detail': f'Wagon {wagon.wagon_name} has no active (setting/waiting-hall) trip to push.'},
            status=status.HTTP_409_CONFLICT,
        )
    readings = data.pop('readings', None)
    if data.get('operator_id'):
        data['operator'] = Operator.objects.get(pk=data.pop('operator_id'))
    if data.get('product_id'):
        data['product'] = Product.objects.get(pk=data.pop('product_id'))
    push = services.push_wagon(trip=trip, readings=readings, client_token=client_token, **data)
    return Response({
        'kiln_push_id': push.kiln_push_id,
        'trip_id': push.trip_id,
        'push_seq': push.push_seq,
        'exit_push_seq': push.push_seq + 43,
        'status': push.trip.status,
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
@permission_classes([IsManager])
def wagon_journey(request):
    """F7: full trip timeline for a wagon plate name. Manager/Admin only (SRS §2.2)."""
    plate = request.query_params.get('plate')
    if not plate:
        return Response({'detail': 'plate query param is required.'}, status=400)
    return Response({'plate': plate, 'trips': services.wagon_journey(plate=plate)})


# --- Dimension dropdowns (form options — any authenticated user) ---
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
def active_wagons_list(request):
    """Wagons with an active (setting/waiting-hall) trip — the ones eligible for a kiln push."""
    trips = WagonTrip.objects.filter(
        status__in=[WagonTrip.STATUS_IN_PROGRESS, WagonTrip.STATUS_WAITING_HALL]
    ).order_by('trip_id')
    return Response([
        {'trip_id': t.trip_id, 'wagon_id': t.wagon.wagon_id, 'plate': t.wagon.wagon_name}
        for t in trips
    ])


@api_view(['GET'])
@permission_classes([IsManager])
def awaiting_discharge_list(request):
    """Trips ready to pack — feeds the Packing form. Manager/Admin only (dashboard data)."""
    trips = WagonTrip.objects.filter(status=WagonTrip.STATUS_AWAITING_DISCHARGE).order_by('trip_id')
    return Response([
        {'trip_id': t.trip_id, 'plate': t.wagon.wagon_name} for t in trips
    ])
