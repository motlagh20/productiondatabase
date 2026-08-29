"""Domain services: trip lifecycle + FIFO-44 kiln rules.

All business rules live here (not in serializers/views) so they are testable in
isolation and reused by any caller. Rules are enforced positively — clean data in,
no Excel-era typo tolerance (ADR-0008).
"""
from django.db import transaction

from .models import (
    KilnExit,
    KilnPush,
    KilnReading,
    KilnSensor,
    PackingHeader,
    PackingWagon,
    SettingLoad,
    WagonTrip,
)

KILN_CAPACITY = 44  # fixed tunnel capacity; wagon entering at push_seq P exits at P+43.


class RuleViolation(Exception):
    """Raised when a domain invariant would be broken (mapped to HTTP 409/400)."""


@transaction.atomic
def start_setting_load(*, wagon, client_token=None, **fields):
    """F2: register a wagon load and assign its trip at load START.

    Replay-safe: a repeated client_token returns the original load unchanged.
    """
    if client_token is not None:
        existing = SettingLoad.objects.filter(client_token=client_token).first()
        if existing is not None:
            return existing

    trip = WagonTrip.objects.create(
        wagon=wagon, status=WagonTrip.STATUS_IN_PROGRESS, source_module='setting',
    )
    load = SettingLoad.objects.create(
        trip=trip, wagon=wagon, client_token=client_token, **fields,
    )
    return load


def _next_push_seq():
    last = KilnPush.objects.order_by('-push_seq').first()
    return (last.push_seq + 1) if last else 1


def _in_tunnel_count():
    """Wagons currently inside the tunnel = pushed but not yet exited."""
    return WagonTrip.objects.filter(status=WagonTrip.STATUS_IN_TUNNEL).count()


@transaction.atomic
def push_wagon(*, trip, readings=None, client_token=None, **fields):
    """F3: register a kiln push. Enforces FIFO-44 occupancy ceiling.

    `readings` = list of {sensor_code, temperature_c}. `trip` moves to in_tunnel.
    """
    if client_token is not None:
        existing = KilnPush.objects.filter(client_token=client_token).first()
        if existing is not None:
            return existing

    if _in_tunnel_count() >= KILN_CAPACITY:
        raise RuleViolation(
            f'Kiln tunnel full ({KILN_CAPACITY}); cannot push until a wagon is discharged.'
        )

    push = KilnPush.objects.create(
        trip=trip, wagon=trip.wagon, push_seq=_next_push_seq(),
        client_token=client_token, **fields,
    )

    for r in (readings or []):
        sensor = KilnSensor.objects.filter(sensor_code=r['sensor_code']).first()
        if sensor is None:
            raise RuleViolation(f'Unknown kiln sensor code: {r["sensor_code"]}')
        KilnReading.objects.create(
            kiln_push=push, sensor=sensor, temperature_c=r.get('temperature_c'),
        )

    trip.status = WagonTrip.STATUS_IN_TUNNEL
    trip.save(update_fields=['status'])
    return push


@transaction.atomic
def exit_wagon(*, trip, exit_date=''):
    """F4: mark discharge. Enforces FIFO-44: exit_push_seq = entry_push_seq + 43."""
    push = trip.kiln_pushes.order_by('-push_seq').first()
    if push is None:
        raise RuleViolation('Trip has no kiln push; cannot exit.')

    entry = push.push_seq
    exit_seq = entry + (KILN_CAPACITY - 1)

    kiln_exit = KilnExit.objects.create(
        trip=trip, wagon=trip.wagon, entry_push_seq=entry, exit_push_seq=exit_seq,
        exit_date=exit_date, discharged=False,
    )
    trip.status = WagonTrip.STATUS_AWAITING_DISCHARGE
    trip.save(update_fields=['status'])
    return kiln_exit


@transaction.atomic
def register_packing(*, wagons, client_token=None, **header_fields):
    """F5: take 1+ wagons from awaiting-discharge; completing packing closes the trip.

    `wagons` = list of {trip_id, product_id?, total_count?, grade1_count?, grade2_count?, waste_count?}.
    """
    if client_token is not None:
        existing = PackingHeader.objects.filter(client_token=client_token).first()
        if existing is not None:
            return existing

    header = PackingHeader.objects.create(client_token=client_token, **header_fields)

    from django.utils import timezone
    for w in wagons:
        trip = WagonTrip.objects.select_for_update().get(pk=w['trip_id'])
        if trip.status != WagonTrip.STATUS_AWAITING_DISCHARGE:
            raise RuleViolation(
                f'Trip {trip.trip_id} is {trip.status}; only awaiting_discharge trips can be packed.'
            )
        PackingWagon.objects.create(
            packing_header=header, trip=trip, wagon=trip.wagon,
            product_id=w.get('product_id'),
            total_count=w.get('total_count'),
            grade1_count=w.get('grade1_count'),
            grade2_count=w.get('grade2_count'),
            waste_count=w.get('waste_count'),
        )
        trip.status = WagonTrip.STATUS_COMPLETED
        trip.completed_at = timezone.now()
        trip.save(update_fields=['status', 'completed_at'])

        KilnExit.objects.filter(trip=trip, discharged=False).update(discharged=True)

    return header


def wagon_journey(*, plate):
    """F7: full trip timeline(s) for a wagon plate name."""
    trips = (
        WagonTrip.objects
        .filter(wagon__wagon_name=plate)
        .prefetch_related('setting_loads', 'kiln_pushes', 'kiln_exits', 'packing_wagons')
        .order_by('trip_id')
    )
    result = []
    for t in trips:
        sl = t.setting_loads.first()
        kp = t.kiln_pushes.order_by('push_seq').first()
        ke = t.kiln_exits.order_by('exit_push_seq').first()
        pw = t.packing_wagons.first()
        result.append({
            'trip_id': t.trip_id,
            'status': t.status,
            'started_at': t.started_at,
            'completed_at': t.completed_at,
            'setting': {
                'date_jalali': sl.date_jalali, 'shift': sl.shift,
                'start_time': sl.start_time, 'end_time': sl.end_time,
            } if sl else None,
            'kiln_entry': {
                'push_seq': kp.push_seq, 'push_date': kp.push_date, 'push_time': kp.push_time,
            } if kp else None,
            'kiln_exit': {
                'entry_push_seq': ke.entry_push_seq, 'exit_push_seq': ke.exit_push_seq,
                'discharged': ke.discharged,
            } if ke else None,
            'packing': {
                'total_count': pw.total_count, 'grade1_count': pw.grade1_count,
                'grade2_count': pw.grade2_count, 'waste_count': pw.waste_count,
            } if pw else None,
        })
    return result
