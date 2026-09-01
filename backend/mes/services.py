"""Domain services: trip lifecycle + FIFO-44 kiln rules.

All business rules live here (not in serializers/views) so they are testable in
isolation and reused by any caller. Rules are enforced positively — clean data in,
no Excel-era typo tolerance (ADR-0008).
"""
from django.db import transaction

from .models import (
    ChamberState,
    DryerCycle,
    DryerReading,
    KilnExit,
    KilnPush,
    KilnReading,
    KilnSensor,
    PackingHeader,
    PackingWagon,
    SettingEvent,
    SettingWagon,
    WagonTrip,
)

KILN_CAPACITY = 44  # fixed tunnel capacity; wagon entering at push_seq P exits at P+43.


def _sync_chamber_loaded(chamber, *, loaded, dryer_cycle=None, setting_event=None):
    """Keep ChamberState in step with the last event touching that chamber.

    loaded=True  -> dryer cycle registered (chamber now full of wet body)
    loaded=False -> setting batch discharged the chamber (now empty, ready for next)
    """
    from django.utils import timezone
    state, _ = ChamberState.objects.get_or_create(chamber=chamber)
    state.is_loaded = loaded
    if loaded:
        state.current_dryer_cycle = dryer_cycle
        state.current_setting_event = None
        if state.loaded_at is None:
            state.loaded_at = timezone.now()
    else:
        state.current_dryer_cycle = None
        state.current_setting_event = setting_event
        state.loaded_at = None
    state.save()


class RuleViolation(Exception):
    """Raised when a domain invariant would be broken (mapped to HTTP 409/400)."""


@transaction.atomic
def create_setting_batch(*, chamber, wagons, client_token=None, **event_fields):
    """F2 (CHAMBER-CENTRIC): register a Setting batch for one dryer chamber, then 1..4 wagons
    fed from THAT chamber. Each wagon gets its own trip at load START.
    `wagons` = list of {wagon, glaze?, start_time?, end_time?, packages?, khesht_count?}.
    Replay-safe: a repeated client_token returns the original event unchanged.
    """
    if client_token is not None:
        existing = SettingEvent.objects.filter(client_token=client_token).first()
        if existing is not None:
            return existing

    event = SettingEvent.objects.create(chamber=chamber, client_token=client_token, **event_fields)
    for i, w in enumerate(wagons, start=1):
        wagon = w.pop('wagon')
        trip = WagonTrip.objects.create(
            wagon=wagon, status=WagonTrip.STATUS_IN_PROGRESS, source_module='setting',
        )
        SettingWagon.objects.create(
            setting_event=event, wagon=wagon, trip=trip, position_in_event=i, **w,
        )
    _sync_chamber_loaded(chamber, loaded=False, setting_event=event)
    return event


@transaction.atomic
def create_dryer_cycle(*, chamber, readings=None, **cycle_fields):
    """F1 (FIRST production step): register a dryer chamber load/unload cycle and its
    hourly humidity/temp readings. Produces the dried body that Setting later loads.
    """
    cycle = DryerCycle.objects.create(chamber=chamber, **cycle_fields)
    for r in (readings or []):
        DryerReading.objects.create(
            dryer_cycle=cycle,
            hour_offset=r.get('hour_offset'),
            humidity_pct=r.get('humidity_pct'),
            temperature_c=r.get('temperature_c'),
        )
    _sync_chamber_loaded(chamber, loaded=True, dryer_cycle=cycle)
    return cycle


def _open_dryer_cycle(chamber):
    """Return the chamber's open dryer cycle (the one ChamberState points at)."""
    state = (ChamberState.objects
             .select_related('current_dryer_cycle')
             .filter(chamber=chamber).first())
    if state is None or not state.is_loaded or state.current_dryer_cycle is None:
        raise RuleViolation(f'Chamber {chamber.chamber_code} has no open dryer cycle.')
    return state.current_dryer_cycle


@transaction.atomic
def append_dryer_reading(*, chamber, temperature_c=None, humidity_pct=None,
                         hour_offset=None):
    """Append one hourly reading to the chamber's open cycle (split dryer UX:
    Load -> Readings -> Unload).

    hour_offset defaults to the next free slot (max+1; valid 0..21). Replay-safe
    by natural key: re-posting the SAME (hour, values) returns the stored reading;
    the same hour with DIFFERENT values is a rule violation.
    """
    cycle = _open_dryer_cycle(chamber)

    if hour_offset is None:
        last = cycle.readings.order_by('-hour_offset').first()
        hour_offset = (last.hour_offset + 1) if (last and last.hour_offset is not None) else 0
    if not (0 <= hour_offset <= 21):
        raise RuleViolation('hour_offset must be within 0..21.')

    existing = cycle.readings.filter(hour_offset=hour_offset).first()
    if existing is not None:
        if existing.temperature_c == temperature_c and existing.humidity_pct == humidity_pct:
            return existing
        raise RuleViolation(
            f'Reading for hour {hour_offset} already exists on this cycle with different values.'
        )
    return DryerReading.objects.create(
        dryer_cycle=cycle, hour_offset=hour_offset,
        humidity_pct=humidity_pct, temperature_c=temperature_c,
    )


@transaction.atomic
def unload_dryer_chamber(*, chamber, unload_date='', unload_time=None,
                         unload_operator_id=None, finger_count=None):
    """Complete the unload side of the chamber's open dryer cycle.

    The chamber STAYS loaded (the dryer dashboard shows it as 'dried') — the
    Setting batch discharge is the transition that empties it, because that is
    what creates the wagon trips. Replay-safe by value: re-posting the same
    unload date/time is an idempotent success.
    """
    cycle = _open_dryer_cycle(chamber)
    if cycle.unload_date:
        if cycle.unload_date == unload_date and (unload_time is None or cycle.unload_time == unload_time):
            return cycle
        raise RuleViolation(
            f'Cycle {cycle.dryer_cycle_id} on chamber {chamber.chamber_code} is already unloaded.'
        )
    cycle.unload_date = unload_date
    cycle.unload_time = unload_time
    if unload_operator_id is not None:
        cycle.unload_operator_id = unload_operator_id
    if finger_count is not None:
        cycle.finger_count = finger_count
    cycle.save(update_fields=['unload_date', 'unload_time', 'unload_operator_id', 'finger_count'])
    return cycle


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
    Replay-safe: a repeated (wagon_id + client_token) returns the original push.
    """
    if client_token is not None:
        existing = KilnPush.objects.filter(
            client_token=client_token, wagon=trip.wagon,
        ).first()
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

    # F4 (auto): derive the discharge record for FIFO-44 — no manual form.
    # exit_push_seq = entry_push_seq + 43 (tunnel fixed capacity 44).
    KilnExit.objects.update_or_create(
        trip=trip, wagon=trip.wagon,
        defaults={'entry_push_seq': push.push_seq, 'exit_push_seq': push.push_seq + (KILN_CAPACITY - 1)},
    )
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
        if trip.status not in (WagonTrip.STATUS_IN_TUNNEL, WagonTrip.STATUS_AWAITING_DISCHARGE):
            raise RuleViolation(
                f'Trip {trip.trip_id} is {trip.status}; only in_tunnel/awaiting_discharge trips can be packed.'
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
        .prefetch_related('setting_wagons', 'kiln_pushes', 'kiln_exits', 'packing_wagons')
        .order_by('trip_id')
    )
    result = []
    for t in trips:
        sw = t.setting_wagons.first()
        ev = sw.setting_event if sw else None
        kp = t.kiln_pushes.order_by('push_seq').first()
        ke = t.kiln_exits.order_by('exit_push_seq').first()
        pw = t.packing_wagons.first()
        result.append({
            'trip_id': t.trip_id,
            'status': t.status,
            'started_at': t.started_at,
            'completed_at': t.completed_at,
            'setting': {
                'date_jalali': ev.date_jalali, 'shift': ev.shift,
                'start_time': sw.start_time, 'end_time': sw.end_time,
                'chamber': ev.chamber.chamber_code if ev and ev.chamber else None,
            } if sw else None,
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
