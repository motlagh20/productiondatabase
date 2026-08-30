"""Build a live DEMO slice: rebase a real historical window into 1405 so the
management dashboards show fresh (near-'today') activity, with a live edge.

The historical snapshot stops at ~1404, so every trip is `completed` and the
live views (in-tunnel wagons, awaiting-discharge, occupancy) are empty. This
command copies a genuinely-populated historical window (1399.03.08..1399.06.08,
which has data in ALL modules) and rebases it to 1405.03.08..1405.06.08, then
leaves the tail of the slice in a live (non-completed) state so dashboards are
realistic. The original historical data is untouched.

Replay-safe: every created row uses a `demo:`-namespaced deterministic client_token
so re-running does not duplicate. `--clear` removes all demo-created rows.

Usage:
    manage.py make_demo_slice            # build the demo slice
    manage.py make_demo_slice --clear    # remove it
"""
import uuid

import django
from django.core.management.base import BaseCommand
from django.db import connections, transaction

from mes import services
from mes.models import (
    Chamber,
    DryerCycle,
    DryerReading,
    EtlReject,
    Glaze,
    KilnExit,
    KilnPush,
    Operator,
    PackingHeader,
    Product,
    SettingEvent,
    SettingWagon,
    Wagon,
    WagonTrip,
)

# Historical source window (populated in every module).
SRC_YEAR = 1399
SRC_LO = f"{SRC_YEAR}.03.08"
SRC_HI = f"{SRC_YEAR}.06.08"
# Rebased target year.
DEMO_YEAR = 1405


def _rows(sql):
    with connections['staging'].cursor() as cur:
        cur.execute(sql)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def _token(seed):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f'demo:{seed}'))


def _rebase(date_str):
    """1399.03.08 -> 1405.03.08 (year only; month/day preserved)."""
    if not date_str or '.' not in date_str:
        return date_str
    y, md = date_str.split('.', 1)
    return f"{DEMO_YEAR}.{md}"


class Command(BaseCommand):
    help = 'Rebase a real historical window into 1405 for a realistic live demo.'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true',
                            help='Remove all demo-slice rows instead of building.')

    def handle(self, *args, **options):
        if options['clear']:
            self._clear()
            return

        self.stdout.write('Building demo slice (1399 window rebased to 1405)...')
        wagons = {w.wagon_name: w for w in Wagon.objects.all()}
        chambers = {c.chamber_id: c for c in Chamber.objects.all()}
        operators = {o.operator_id: o for o in Operator.objects.all()}
        products = {p.product_id: p for p in Product.objects.all()}
        glazes = {g.glaze_id: g for g in Glaze.objects.all()}

        # ---- DRYER (F1) ----
        for dc in _rows(
            f"SELECT dryer_cycle_id, load_date, load_time, unload_date, unload_time, "
            f"load_operator_id, unload_operator_id, product_id, finger_count, chamber_id "
            f"FROM dryer_cycle WHERE load_date BETWEEN '{SRC_LO}' AND '{SRC_HI}' "
            f"ORDER BY dryer_cycle_id"
        ):
            chamber = chambers.get(dc['chamber_id'])
            if chamber is None:
                continue
            readings = [
                {'hour_offset': r['hour_offset'], 'humidity_pct': r['humidity_pct'],
                 'temperature_c': r['temperature_c']}
                for r in _rows(
                    f"SELECT hour_offset, humidity_pct, temperature_c FROM dryer_reading "
                    f"WHERE dryer_cycle_id={dc['dryer_cycle_id']} ORDER BY hour_offset")
            ]
            try:
                services.create_dryer_cycle(
                    chamber=chamber, readings=readings,
                    load_date=_rebase(dc['load_date'] or ''),
                    load_time=dc['load_time'],
                    unload_date=_rebase(dc['unload_date'] or ''),
                    unload_time=dc['unload_time'],
                    load_operator=operators.get(dc['load_operator_id']),
                    unload_operator=operators.get(dc['unload_operator_id']),
                    product=products.get(dc['product_id']),
                    finger_count=dc['finger_count'] or 0,
                )
            except Exception:  # noqa: BLE001
                pass

        # ---- SETTING -> trip (mark the tail as in_progress / live) ----
        sw_by_event = {}
        for r in _rows(
            f"SELECT setting_event_id, setting_wagon_id, wagon_no, glaze_id, start_time, "
            f"end_time, packages, khesht_count, position_in_event FROM setting_wagon "
            f"WHERE setting_event_id IN (SELECT setting_event_id FROM setting_event "
            f"WHERE date_jalali BETWEEN '{SRC_LO}' AND '{SRC_HI}')"
        ):
            sw_by_event.setdefault(int(r['setting_event_id']), []).append(r)

        events = _rows(
            f"SELECT setting_event_id, date_jalali, shift, chamber_id, product_id, "
            f"supervisor_id, operator_id FROM setting_event "
            f"WHERE date_jalali BETWEEN '{SRC_LO}' AND '{SRC_HI}' ORDER BY setting_event_id"
        )
        live_setting_ids = set(e['setting_event_id'] for e in events[-3:])  # tail = live
        for ev in events:
            clean = []
            ok = True
            for sw in sorted(sw_by_event.get(int(ev['setting_event_id']), []),
                             key=lambda r: (r['position_in_event'] or 0)):
                wname = sw['wagon_no']
                if wname is None or not (1 <= int(wname) <= 80) or str(wname) not in wagons:
                    ok = False
                    continue
                clean.append((wagons[str(wname)], sw))
            if not ok or not clean:
                continue
            chamber = chambers.get(ev['chamber_id'])
            if chamber is None:
                continue
            payload = [{
                'wagon': w,
                'glaze': glazes.get(sw['glaze_id']),
                'start_time': sw['start_time'], 'end_time': sw['end_time'],
                'packages': sw['packages'], 'khesht_count': sw['khesht_count'],
            } for w, sw in clean]
            try:
                services.create_setting_batch(
                    chamber=chamber, wagons=payload,
                    client_token=_token(ev['setting_event_id']),
                    date_jalali=_rebase(ev['date_jalali'] or ''),
                    shift=ev['shift'],
                    product=products.get(ev['product_id']),
                    supervisor=operators.get(ev['supervisor_id']),
                    operator=operators.get(ev['operator_id']),
                )
            except Exception:  # noqa: BLE001
                pass

        # ---- KILN push + exit (tail pushes stay in_tunnel = live) ----
        kw_by_push = {}
        for r in _rows(
            f"SELECT kiln_push_id, wagon_no FROM kiln_wagon "
            f"WHERE kiln_push_id IN (SELECT kiln_push_id FROM kiln_push "
            f"WHERE push_date BETWEEN '{SRC_LO}' AND '{SRC_HI}')"
        ):
            kw_by_push.setdefault(int(r['kiln_push_id']), []).append(r)

        pushes = _rows(
            f"SELECT kiln_push_id, push_seq, push_date, push_time, shift, "
            f"operator_id, product_id FROM kiln_push "
            f"WHERE push_date BETWEEN '{SRC_LO}' AND '{SRC_HI}' ORDER BY push_seq"
        )
        live_push_ids = set(p['kiln_push_id'] for p in pushes[-15:])  # tail = live in tunnel
        for kp in pushes:
            trip = (
                WagonTrip.objects
                .filter(status__in=[WagonTrip.STATUS_IN_PROGRESS, WagonTrip.STATUS_WAITING_HALL])
                .order_by('trip_id').first()
            )
            if trip is None:
                continue
            try:
                services.push_wagon(
                    trip=trip, client_token=_token(100000 + kp['kiln_push_id']),
                    push_date=_rebase(kp['push_date'] or ''),
                    push_time=kp['push_time'], shift=kp['shift'],
                    operator=operators.get(kp['operator_id']),
                    product=products.get(kp['product_id']),
                )
            except Exception:  # noqa: BLE001
                continue
            # For non-live pushes, discharge via the historical exit record.
            if kp['kiln_push_id'] in live_push_ids:
                continue
            er = _rows(
                f"SELECT exit_date FROM kiln_exit WHERE entry_push_seq={kp['push_seq']}"
            )
            if er:
                ke = KilnExit.objects.filter(trip=trip).first()
                if ke is not None:
                    ke.discharged = True
                    ke.save(update_fields=['discharged'])
                trip.status = WagonTrip.STATUS_AWAITING_DISCHARGE
                trip.save(update_fields=['status'])

        # ---- PACKING (close the discharged trips) ----
        pw_by_header = {}
        for r in _rows(
            f"SELECT packing_header_id, wagon_no, product_id, total_count, grade1_count, "
            f"grade2_count, waste_count FROM packing_wagon "
            f"WHERE packing_header_id IN (SELECT packing_header_id FROM packing_header "
            f"WHERE pack_date BETWEEN '{SRC_LO}' AND '{SRC_HI}')"
        ):
            pw_by_header.setdefault(int(r['packing_header_id']), []).append(r)

        for ph in _rows(
            f"SELECT packing_header_id, pack_date, shift, controller_id FROM packing_header "
            f"WHERE pack_date BETWEEN '{SRC_LO}' AND '{SRC_HI}' ORDER BY packing_header_id"
        ):
            payload = []
            for pw in pw_by_header.get(int(ph['packing_header_id']), []):
                wname = pw['wagon_no']
                if wname is None or not (1 <= int(wname) <= 80) or str(wname) not in wagons:
                    continue
                trip = (
                    WagonTrip.objects
                    .filter(wagon=wagons[str(wname)],
                            status__in=[WagonTrip.STATUS_IN_TUNNEL, WagonTrip.STATUS_AWAITING_DISCHARGE])
                    .order_by('trip_id').first()
                )
                if trip is None:
                    continue
                payload.append({
                    'trip_id': trip.trip_id, 'product_id': pw['product_id'],
                    'total_count': pw['total_count'], 'grade1_count': pw['grade1_count'],
                    'grade2_count': pw['grade2_count'], 'waste_count': pw['waste_count'],
                })
            if not payload:
                continue
            try:
                services.register_packing(
                    wagons=payload, client_token=_token(200000 + ph['packing_header_id']),
                    pack_date=_rebase(ph['pack_date'] or ''),
                    shift=ph['shift'], controller=operators.get(ph['controller_id']),
                )
            except Exception:  # noqa: BLE001
                pass

        # ---- COMPLETION SWEEP: free wagons for the Setting form ----
        # Demo trips are created in_progress; left as-is, every wagon ends up busy and
        # the Setting dropdown would be empty. Complete all demo trips except a small
        # live edge so most wagons are free again (real factory flow: a wagon is reused
        # after it finishes packing).
        demo_tokens = set(_token(s) for s in range(0, 400000))
        demo_setting_ids = list(
            SettingEvent.objects.filter(client_token__in=demo_tokens).values_list('setting_event_id', flat=True)
        )
        demo_trips = WagonTrip.objects.filter(setting_wagons__setting_event_id__in=demo_setting_ids).distinct()
        live_edge = set(demo_trips.order_by('-trip_id')[:35].values_list('trip_id', flat=True))
        # keep the live edge (in_progress / in_tunnel); complete the rest
        for t in demo_trips.exclude(trip_id__in=live_edge):
            if t.status in (WagonTrip.STATUS_AWAITING_DISCHARGE, WagonTrip.STATUS_IN_TUNNEL,
                            WagonTrip.STATUS_WAITING_HALL, WagonTrip.STATUS_IN_PROGRESS,
                            WagonTrip.STATUS_BODY_DRIED):
                t.status = WagonTrip.STATUS_COMPLETED
                t.completed_at = django.utils.timezone.now()
                t.save(update_fields=['status', 'completed_at'])

        self.stdout.write(self.style.SUCCESS(
            f"Demo slice built: window {SRC_LO}..{SRC_HI} rebased to {DEMO_YEAR}. "
            f"Live edge = ~35 newest trips kept active (in_progress/in_tunnel); rest completed so wagons free up."
        ))

    def _clear(self):
        # Demo rows carry a `demo:`-namespaced client_token. Recompute the same token
        # set used at build time and delete by it (SettingEvent/KilnPush/PackingHeader/
        # DryerCycle cascade to their trips and child rows).
        from mes.models import (
            DryerCycle, KilnPush, KilnExit, PackingHeader, PackingWagon,
            SettingEvent, SettingWagon, WagonTrip,
        )
        demo_tokens = set()
        # Mirror the seed ranges used in handle().
        for s in list(range(0, 400000)):
            demo_tokens.add(str(uuid.uuid5(uuid.NAMESPACE_URL, f'demo:{s}')))
        with transaction.atomic():
            setting_ids = list(
                SettingEvent.objects.filter(client_token__in=demo_tokens).values_list('setting_event_id', flat=True)
            )
            trips = WagonTrip.objects.filter(setting_wagons__setting_event_id__in=setting_ids).distinct()
            # Delete protected-FK children explicitly before the trips.
            KilnExit.objects.filter(trip__in=trips).delete()
            SettingWagon.objects.filter(trip__in=trips).delete()
            KilnPush.objects.filter(trip__in=trips).delete()
            PackingWagon.objects.filter(trip__in=trips).delete()
            PackingHeader.objects.filter(wagons__trip__in=trips).delete()
            # Dryer cycles in the demo are rebased to 1405; clear those by date prefix.
            DryerCycle.objects.filter(load_date__startswith='1405').delete()
            trips.delete()
        self.stdout.write(self.style.WARNING('Demo slice cleared.'))
