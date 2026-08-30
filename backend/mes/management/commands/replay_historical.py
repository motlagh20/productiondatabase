"""Replay the historical (staging) production data into the clean app core.

Read-only from staging (`staging` alias), writes to `default` (mes_app).
Reuses the real domain services (create_setting_batch / push_wagon /
register_packing) so the spine logic (FIFO-44, capacity, journey) is
exercised at real volume.

Dirty rows (invalid wagon plate, missing chamber, bad date) are NOT admitted
into the app — they are quarantined in EtlReject for human adjudication
(ADR-0008). The app clean core stays unpolluted.
"""
import uuid

from django.core.management.base import BaseCommand
from django.db import connections, transaction

from mes import services
from mes.models import (
    Chamber,
    DryerCycle,
    DryerReading,
    EtlReject,
    Glaze,
    Operator,
    Product,
    SettingWagon,
    Wagon,
    WagonTrip,
)


def _rows(sql):
    with connections['staging'].cursor() as cur:
        cur.execute(sql)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def _token(seed_int):
    """Deterministic UUID from a staging source key → replay-safe retries."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f'replay:{seed_int}'))


class Command(BaseCommand):
    help = 'Replay historical staging data into the app core (cleanse + load).'

    def handle(self, *args, **options):
        self.stdout.write('Replaying historical data into app core...')

        # Resolve dimension maps once.
        wagons = {w.wagon_name: w for w in Wagon.objects.all()}
        chambers = {c.chamber_id: c for c in Chamber.objects.all()}
        operators = {o.operator_id: o for o in Operator.objects.all()}
        products = {p.product_id: p for p in Product.objects.all()}
        glazes = {g.glaze_id: g for g in Glaze.objects.all()}

        stats = {'dryer': 0, 'dryer_reject': 0, 'setting': 0, 'setting_reject': 0, 'kiln': 0, 'kiln_reject': 0,
                 'packing': 0, 'packing_reject': 0}

        # ---- 0) DRYER (F1, first production step): cycle + hourly readings ----
        # Reuses create_dryer_cycle so the F1 path is exercised like every other module.
        d_cycles = _rows(
            'SELECT dryer_cycle_id, load_date, load_time, unload_date, unload_time, '
            'load_operator_id, unload_operator_id, product_id, finger_count, chamber_id '
            'FROM dryer_cycle ORDER BY dryer_cycle_id'
        )
        d_readings = _rows(
            'SELECT dryer_cycle_id, hour_offset, humidity_pct, temperature_c '
            'FROM dryer_reading ORDER BY dryer_cycle_id, hour_offset'
        )
        d_read_by_cycle = {}
        for r in d_readings:
            d_read_by_cycle.setdefault(int(r['dryer_cycle_id']), []).append(r)

        for dc in d_cycles:
            chamber = chambers.get(dc['chamber_id'])
            if chamber is None:
                EtlReject.objects.create(
                    module='dryer', source_row=dc['dryer_cycle_id'],
                    reason=f"missing chamber_id={dc['chamber_id']}", raw=str(dc))
                stats['dryer_reject'] += 1
                continue
            readings = []
            for dr in d_read_by_cycle.get(int(dc['dryer_cycle_id']), []):
                readings.append({
                    'hour_offset': dr['hour_offset'],
                    'humidity_pct': dr['humidity_pct'],
                    'temperature_c': dr['temperature_c'],
                })
            try:
                services.create_dryer_cycle(
                    chamber=chamber,
                    readings=readings,
                    load_date=dc['load_date'] or '',
                    load_time=dc['load_time'],
                    unload_date=dc['unload_date'] or '',
                    unload_time=dc['unload_time'],
                    load_operator=operators.get(dc['load_operator_id']),
                    unload_operator=operators.get(dc['unload_operator_id']),
                    product=products.get(dc['product_id']),
                    finger_count=dc['finger_count'] or 0,
                )
                stats['dryer'] += 1
            except Exception as e:  # noqa: BLE001
                EtlReject.objects.create(
                    module='dryer', source_row=dc['dryer_cycle_id'],
                    reason=f"service error: {e}", raw=str(dc))
                stats['dryer_reject'] += 1

        # ---- 1) SETTING: event + wagons + trip ----
        # Pre-load ALL setting_wagon rows once (avoids a SQL round-trip per event).
        sw_all = _rows(
            'SELECT setting_event_id, setting_wagon_id, wagon_no, glaze_id, start_time, '
            'end_time, packages, khesht_count, position_in_event FROM setting_wagon'
        )
        sw_by_event = {}
        for r in sw_all:
            sw_by_event.setdefault(int(r['setting_event_id']), []).append(r)

        events = _rows(
            'SELECT setting_event_id, date_jalali, shift, chamber_id, product_id, '
            'supervisor_id, operator_id FROM setting_event ORDER BY setting_event_id'
        )
        for ev in events:
            sw_rows = sorted(
                sw_by_event.get(int(ev['setting_event_id']), []),
                key=lambda r: (r['position_in_event'] or 0),
            )
            # Validate + resolve wagons first; if any wagon is dirty, reject the event.
            clean = []
            dirty = False
            for sw in sw_rows:
                wname = sw['wagon_no']
                if wname is None or not (1 <= int(wname) <= 80) or str(wname) not in wagons:
                    EtlReject.objects.create(
                        module='setting', source_row=ev['setting_event_id'],
                        reason=f"invalid wagon_no={wname} in setting_event {ev['setting_event_id']}",
                        raw=str(sw),
                    )
                    stats['setting_reject'] += 1
                    dirty = True
                    continue
                clean.append((wagons[str(wname)], sw))
            if dirty or not clean:
                continue
            chamber = chambers.get(ev['chamber_id'])
            if chamber is None:
                EtlReject.objects.create(
                    module='setting', source_row=ev['setting_event_id'],
                    reason=f"missing chamber_id={ev['chamber_id']}", raw=str(ev))
                stats['setting_reject'] += 1
                continue

            wagons_payload = []
            for w, sw in clean:
                glaze = glazes.get(sw['glaze_id'])
                wagons_payload.append({
                    'wagon': w,
                    'glaze': glaze,
                    'start_time': sw['start_time'],
                    'end_time': sw['end_time'],
                    'packages': sw['packages'],
                    'khesht_count': sw['khesht_count'],
                })

            try:
                with transaction.atomic():
                    services.create_setting_batch(
                        chamber=chamber,
                        wagons=wagons_payload,
                        client_token=_token(ev['setting_event_id']),
                        date_jalali=ev['date_jalali'] or '',
                        shift=ev['shift'],
                        product=products.get(ev['product_id']),
                        supervisor=operators.get(ev['supervisor_id']),
                        operator=operators.get(ev['operator_id']),
                    )
                stats['setting'] += 1
            except Exception as e:  # noqa: BLE001
                EtlReject.objects.create(
                    module='setting', source_row=ev['setting_event_id'],
                    reason=f"service error: {e}", raw=str(ev))
                stats['setting_reject'] += 1

        # ---- 2) KILN: interleave pushes and exits by sequence ----
        # Pushes and exits MUST be interleaved, NOT run as two separate passes: running
        # every push before any exit fills the 44-wagon tunnel and jams (the "tunnel
        # full" rejects). Discharging a wagon frees its slot before the next push needs
        # it. We walk a single timeline ordered by push_seq / exit_push_seq.
        from mes.models import KilnExit

        # Pre-load ALL kiln_wagon rows once (avoids a SQL round-trip per push).
        kw_all = _rows('SELECT kiln_push_id, wagon_no FROM kiln_wagon')
        kw_by_push = {}
        for r in kw_all:
            kw_by_push.setdefault(int(r['kiln_push_id']), []).append(r)

        pushes = _rows(
            'SELECT kiln_push_id, push_seq, push_date, push_time, shift, '
            'operator_id, product_id FROM kiln_push ORDER BY push_seq'
        )
        # staging kiln_exit links by (entry_push_seq, exit_push_seq); wagon via wagon_id.
        exit_rows = _rows(
            'SELECT wagon_id, entry_push_seq, exit_push_seq, exit_date FROM kiln_exit '
            'ORDER BY exit_push_seq'
        )
        wagon_by_id = {w.wagon_id: w for w in Wagon.objects.all()}

        # Build a merged, ordered timeline of events.
        # (+1 push at its push_seq, -1 exit at its exit_push_seq)
        timeline = []
        for kp in pushes:
            timeline.append((int(kp['push_seq']), 'push', kp))
        for er in exit_rows:
            timeline.append((int(er['exit_push_seq']), 'exit', er))
        timeline.sort(key=lambda t: (t[0], 0 if t[1] == 'exit' else 1))

        for seq, kind, row in timeline:
            if kind == 'push':
                kp = row
                kw_rows = kw_by_push.get(int(kp['kiln_push_id']), [])
                pushed_any = False
                for kw in kw_rows:
                    wname = kw['wagon_no']
                    if wname is None or not (1 <= int(wname) <= 80) or str(wname) not in wagons:
                        EtlReject.objects.create(
                            module='kiln', source_row=kp['kiln_push_id'],
                            reason=f"invalid wagon_no={wname} in kiln_push {kp['kiln_push_id']}",
                            raw=str(kw))
                        stats['kiln_reject'] += 1
                        continue
                    wagon = wagons[str(wname)]
                    trip = (
                        WagonTrip.objects
                        .filter(wagon=wagon,
                                status__in=[WagonTrip.STATUS_IN_PROGRESS, WagonTrip.STATUS_WAITING_HALL])
                        .order_by('trip_id').first()
                    )
                    if trip is None:
                        # Wagon has no active (setting/waiting-hall) trip. Two legit cases:
                        #  (a) its setting batch was dirty and never created a trip -> reject.
                        #  (b) the push belongs to a wagon whose trip completed via packing
                        #      already and this is a duplicate/late push -> reject (not an error).
                        # We do NOT jam the tunnel for it.
                        EtlReject.objects.create(
                            module='kiln', source_row=kp['kiln_push_id'],
                            reason=f"no active trip for wagon {wname} at kiln_push {kp['kiln_push_id']}",
                            raw=str(kw))
                        stats['kiln_reject'] += 1
                        continue
                    try:
                        services.push_wagon(
                            trip=trip,
                            client_token=_token(100000 + kp['kiln_push_id']),
                            push_date=kp['push_date'] or '',
                            push_time=kp['push_time'],
                            shift=kp['shift'],
                            operator=operators.get(kp['operator_id']),
                            product=products.get(kp['product_id']),
                        )
                        pushed_any = True
                    except Exception as e:  # noqa: BLE001
                        EtlReject.objects.create(
                            module='kiln', source_row=kp['kiln_push_id'],
                            reason=f"service error: {e}", raw=str(kp))
                        stats['kiln_reject'] += 1
                if pushed_any:
                    stats['kiln'] += 1
            else:  # 'exit'
                er = row
                w = wagon_by_id.get(er['wagon_id'])
                if w is None:
                    EtlReject.objects.create(
                        module='kiln', source_row=None,
                        reason=f"invalid wagon_id={er['wagon_id']} in kiln_exit", raw=str(er))
                    stats['kiln_reject'] += 1
                    continue
                trip = (
                    WagonTrip.objects
                    .filter(wagon=w, status=WagonTrip.STATUS_IN_TUNNEL)
                    .order_by('trip_id').first()
                )
                if trip is None:
                    continue  # already discharged or never pushed; not an error in replay
                # The push already auto-created a KilnExit (discharged=False, FIFO-44 seq).
                # Historical kiln_exit only needs to mark it discharged + advance the trip.
                ke = KilnExit.objects.filter(trip=trip).first()
                if ke is not None:
                    ke.discharged = True
                    ke.save(update_fields=['discharged'])
                trip.status = WagonTrip.STATUS_AWAITING_DISCHARGE
                trip.save(update_fields=['status'])

        # ---- 3) PACKING: close trips ----
        # Pre-load ALL packing_wagon rows once (avoids a SQL round-trip per header).
        pw_all = _rows(
            'SELECT packing_header_id, wagon_no, product_id, total_count, grade1_count, '
            'grade2_count, waste_count FROM packing_wagon'
        )
        pw_by_header = {}
        for r in pw_all:
            pw_by_header.setdefault(int(r['packing_header_id']), []).append(r)

        headers = _rows(
            'SELECT packing_header_id, pack_date, shift, controller_id FROM packing_header '
            'ORDER BY packing_header_id'
        )
        for ph in headers:
            pw_rows = pw_by_header.get(int(ph['packing_header_id']), [])
            packed_any = False
            wagon_payloads = []
            for pw in pw_rows:
                wname = pw['wagon_no']
                if wname is None or not (1 <= int(wname) <= 80) or str(wname) not in wagons:
                    EtlReject.objects.create(
                        module='packing', source_row=ph['packing_header_id'],
                        reason=f"invalid wagon_no={wname} in packing_header {ph['packing_header_id']}",
                        raw=str(pw))
                    stats['packing_reject'] += 1
                    continue
                wagon = wagons[str(wname)]
                trip = (
                    WagonTrip.objects
                    .filter(wagon=wagon,
                            status__in=[WagonTrip.STATUS_IN_TUNNEL, WagonTrip.STATUS_AWAITING_DISCHARGE])
                    .order_by('trip_id').first()
                )
                if trip is None:
                    EtlReject.objects.create(
                        module='packing', source_row=ph['packing_header_id'],
                        reason=f"no discharge-ready trip for wagon {wname}",
                        raw=str(pw))
                    stats['packing_reject'] += 1
                    continue
                wagon_payloads.append({
                    'trip_id': trip.trip_id,
                    'product_id': pw['product_id'],
                    'total_count': pw['total_count'],
                    'grade1_count': pw['grade1_count'],
                    'grade2_count': pw['grade2_count'],
                    'waste_count': pw['waste_count'],
                })
            if wagon_payloads:
                try:
                    services.register_packing(
                        wagons=wagon_payloads,
                        client_token=_token(200000 + ph['packing_header_id']),
                        pack_date=ph['pack_date'] or '',
                        shift=ph['shift'],
                        controller=operators.get(ph['controller_id']),
                    )
                    stats['packing'] += 1
                    packed_any = True
                except Exception as e:  # noqa: BLE001
                    EtlReject.objects.create(
                        module='packing', source_row=ph['packing_header_id'],
                        reason=f"service error: {e}", raw=str(ph))
                    stats['packing_reject'] += 1

        self.stdout.write(self.style.SUCCESS(
            f"Replay complete: dryer={stats['dryer']} (reject {stats['dryer_reject']}), "
            f"setting={stats['setting']} (reject {stats['setting_reject']}), "
            f"kiln_pushes={stats['kiln']} (reject {stats['kiln_reject']}), "
            f"packing={stats['packing']} (reject {stats['packing_reject']})"
        ))
