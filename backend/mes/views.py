"""API views for the vertical slice (F2–F5 write + F7 journey read)."""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from . import services
from .exceptions import IsManager
from .models import (
    Chamber, ChamberState, DryerCycle, Glaze, KilnPush, KilnSensor,
    Operator, Product, SettingEvent, Wagon, WagonTrip,
)
from .serializers import (
    ChamberOut,
    DryerCycleIn,
    DryerCycleOut,
    DryerReadingPostIn,
    DryerUnloadIn,
    DryerChamberStatusOut,
    GlazeOut,
    KilnPushIn,
    KilnPushOut,
    OperatorOut,
    PackingHeaderIn,
    ProductOut,
    SettingEventIn,
    SettingEventOut,
    SettingWagonIn,
    WagonOut,
)

WRITE_PERMISSION = IsAuthenticated
# Reference/dimension dropdowns are public: static form options, not sensitive,
# and must load before login so forms render. Writes + manager dashboards stay auth'd.
PUBLIC = AllowAny


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


# --- New UI-merge endpoints (2 writes + 4 reads) ---

@api_view(['POST'])
@permission_classes([WRITE_PERMISSION])
def dryer_reading_create(request):
    """Append one hourly reading to the chamber's open dryer cycle."""
    ser = DryerReadingPostIn(data=request.data)
    ser.is_valid(raise_exception=True)
    d = ser.validated_data
    chamber = Chamber.objects.get(pk=d['chamber_id'])
    reading = services.append_dryer_reading(
        chamber=chamber,
        temperature_c=d.get('temperature_c'),
        humidity_pct=d.get('humidity_pct'),
        hour_offset=d.get('hour_offset'),
    )
    return Response({
        'dryer_reading_id': reading.dryer_reading_id,
        'hour_offset': reading.hour_offset,
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([WRITE_PERMISSION])
def dryer_unload(request):
    """Complete the unload side of the chamber's open dryer cycle."""
    ser = DryerUnloadIn(data=request.data)
    ser.is_valid(raise_exception=True)
    d = ser.validated_data
    chamber = Chamber.objects.get(pk=d['chamber_id'])
    cycle = services.unload_dryer_chamber(
        chamber=chamber,
        unload_date=d.get('unload_date', ''),
        unload_time=d.get('unload_time'),
        unload_operator_id=d.get('unload_operator_id'),
        finger_count=d.get('finger_count'),
    )
    return Response({
        'dryer_cycle_id': cycle.dryer_cycle_id,
        'unload_date': cycle.unload_date,
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dryer_chamber_status(request):
    """Per-chamber status feed for the dryer dashboard (empty/drying/dried)."""
    chambers = Chamber.objects.filter(chamber_type='DRYER').order_by('chamber_id')
    result = []
    for ch in chambers:
        state = ChamberState.objects.filter(chamber=ch).select_related('current_dryer_cycle').first()
        is_loaded = state.is_loaded if state else False
        cycle = state.current_dryer_cycle if (state and state.is_loaded) else None

        if not is_loaded:
            derived = 'empty'
        elif cycle and cycle.unload_date:
            derived = 'dried'
        else:
            derived = 'drying'

        cycle_data = None
        if cycle:
            latest_r = cycle.readings.order_by('-hour_offset').first()
            cycle_data = {
                'dryer_cycle_id': cycle.dryer_cycle_id,
                'load_date': cycle.load_date,
                'load_time': str(cycle.load_time) if cycle.load_time else None,
                'product_name': cycle.product.product_name_setting if cycle.product else '',
                'finger_count': cycle.finger_count,
                'unload_date': cycle.unload_date,
                'latest_reading': {
                    'hour_offset': latest_r.hour_offset,
                    'temperature_c': str(latest_r.temperature_c) if latest_r.temperature_c else None,
                    'humidity_pct': str(latest_r.humidity_pct) if latest_r.humidity_pct else None,
                } if latest_r else None,
            }
        result.append({
            'chamber_id': ch.chamber_id,
            'chamber_code': ch.chamber_code,
            'chamber_type': ch.chamber_type,
            'is_loaded': is_loaded,
            'derived_status': derived,
            'current_cycle': cycle_data,
        })
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dryer_cycle_list(request):
    """List dryer cycles with nested readings. ?chamber_id= filter, newest-first."""
    qs = DryerCycle.objects.select_related('chamber', 'product').prefetch_related('readings').order_by('-dryer_cycle_id')
    chamber_id = request.query_params.get('chamber_id')
    if chamber_id:
        qs = qs.filter(chamber_id=chamber_id)
    limit = int(request.query_params.get('limit', 50))
    return Response(DryerCycleOut(qs[:limit], many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def setting_event_list(request):
    """List setting events with nested wagons + resolved names. Newest-first."""
    qs = (SettingEvent.objects
          .select_related('chamber', 'product', 'supervisor', 'operator')
          .prefetch_related('wagons__wagon', 'wagons__glaze')
          .order_by('-setting_event_id'))
    limit = int(request.query_params.get('limit', 50))
    return Response(SettingEventOut(qs[:limit], many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def kiln_push_list(request):
    """List kiln pushes with nested readings + exit info. Newest-first."""
    qs = (KilnPush.objects
          .select_related('wagon', 'operator', 'product', 'trip')
          .prefetch_related('readings__sensor', 'trip__kiln_exits')
          .order_by('-push_seq'))
    limit = int(request.query_params.get('limit', 50))
    return Response(KilnPushOut(qs[:limit], many=True).data)


# --- Dimension dropdowns (public form options — no auth required) ---
@api_view(['GET'])
@permission_classes([PUBLIC])
def operator_list(request):
    return Response(OperatorOut(Operator.objects.all(), many=True).data)


@api_view(['GET'])
@permission_classes([PUBLIC])
def product_list(request):
    """Products. ?chamber_id= -> only products used with that chamber (derived from
    historical setting_event data). No param -> all products."""
    qs = Product.objects.all()
    chamber_id = request.query_params.get('chamber_id')
    if chamber_id:
        qs = qs.filter(
            settingevent__chamber_id=chamber_id
        ).distinct()
    return Response(ProductOut(qs, many=True).data)


@api_view(['GET'])
@permission_classes([PUBLIC])
def glaze_list(request):
    return Response(GlazeOut(Glaze.objects.all(), many=True).data)


@api_view(['GET'])
@permission_classes([PUBLIC])
def chamber_list(request):
    """Chambers. ?loaded=true -> only currently-loaded (full) chambers; ?loaded=false
    -> only empty chambers. No param -> all. The Setting form requests loaded=true
    (you can only discharge a chamber that is full)."""
    qs = Chamber.objects.all()
    loaded = request.query_params.get('loaded')
    if loaded in ('true', '1', 'yes'):
        qs = qs.filter(state__is_loaded=True)
    elif loaded in ('false', '0', 'no'):
        qs = qs.filter(state__is_loaded=False)
    return Response(ChamberOut(qs, many=True).data)


@api_view(['GET'])
@permission_classes([PUBLIC])
def wagon_list(request):
    """Wagons. ?available=true -> only wagons whose LAST trip is completed/abandoned/none
    (free to be loaded in a Setting batch). A wagon with an active trip is excluded.
    No param -> all."""
    qs = Wagon.objects.all()
    if request.query_params.get('available') in ('true', '1', 'yes'):
        busy = WagonTrip.objects.filter(
            status__in=[
                WagonTrip.STATUS_IN_PROGRESS, WagonTrip.STATUS_BODY_DRIED,
                WagonTrip.STATUS_WAITING_HALL, WagonTrip.STATUS_IN_TUNNEL,
                WagonTrip.STATUS_AWAITING_DISCHARGE,
            ]
        ).values_list('wagon_id', flat=True)
        qs = qs.exclude(wagon_id__in=busy)
    return Response(WagonOut(qs, many=True).data)


@api_view(['GET'])
@permission_classes([PUBLIC])
def sensor_list(request):
    sensors = KilnSensor.objects.all()
    return Response([
        {'sensor_id': s.sensor_id, 'sensor_code': s.sensor_code, 'sensor_name': s.sensor_name}
        for s in sensors
    ])


@api_view(['GET'])
@permission_classes([PUBLIC])
def active_wagons_list(request):
    """Wagons with an active (setting/waiting-hall) trip — feeds the Kiln push form."""
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
