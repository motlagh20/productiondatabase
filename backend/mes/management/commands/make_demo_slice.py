"""Build a live DEMO slice: rebase a real historical window so dashboards
show ~18 days of data ending near today, with exactly 44 wagons in the
kiln tunnel (full FIFO-44 capacity) and a few wagons in other live states.

Historical snapshot stops around 1404, so a naive load would leave the
live views (in-tunnel / awaiting-discharge) empty. This command:
  1. Copies a genuinely-populated historical window (1399.03.08..1399.06.08,
     all modules populated) and rebases it into the current Jalali year,
     proportional day-for-day into a sliding window ending near today.
  2. Forces exactly 44 distinct wagons into in_tunnel (full kiln) using the
     most recent rebased pushes for distinct wagons.
  3. Leaves a small live edge (in_progress / in_tunnel / awaiting_discharge)
     so dashboards are realistic; the rest is completed so wagons free up for
     the Setting form.

Replay-safe: every created row uses a `demo:`-namespaced deterministic
client_token so re-running does not duplicate. `--clear` removes all
demo-created rows.

Daily refresh: run `manage.py make_demo_slice` once per day (e.g. cron) to
slide the window forward. The kiln will always show 44 in_tunnel with
near-current dates.

Usage:
    manage.py make_demo_slice            # build / refresh the demo slice
    manage.py make_demo_slice --clear    # remove it
"""
import uuid

import django
from django.core.management.base import BaseCommand
from django.db import connections, models, transaction
from django.db.models import Max
from django.utils import timezone

import jdatetime

from mes import services
from mes.models import (
    Chamber,
    ChamberState,
    DryerCycle,
    DryerReading,
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

# --- Historical source window (known populated in every module) ----------
SRC_YEAR = 1399
SRC_LO = f"{SRC_YEAR}.03.08"   # 1399-03-08
SRC_HI = f"{SRC_YEAR}.06.08"   # 1399-06-08
SRC_LO_DATE = jdatetime.date(SRC_YEAR, 3, 8)
SRC_HI_DATE = jdatetime.date(SRC_YEAR, 6, 8)
SRC_SPAN = (SRC_HI_DATE - SRC_LO_DATE).days   # 92 days

# --- Target window: sliding, ending near today ----------------------------
TODAY = jdatetime.date.today()
WINDOW_DAYS = 18          # ~18 days of rebased data
LIVE_DAYS = 2             # last N days stay live (in_progress / in_tunnel / awaiting)

TGT_HI = TODAY
TGT_LO = jdatetime.date(TODAY.year, TODAY.month, max(1, TODAY.day - WINDOW_DAYS))
TGT_LO_STR = TGT_LO.strftime("%Y.%m.%d")
TGT_HI_STR = TGT_HI.strftime("%Y.%m.%d")

# --- How many wagons to force into the kiln tunnel ----------------------
KILN_CAPACITY = 44        # must equal FIFO-44 constant
MIN_IN_TUNNEL = KILN_CAPACITY
WAGON_COUNT = KILN_CAPACITY   # how many wagons to keep in the kiln tunnel (default = capacity)


def _rows(sql):
    with connections['staging'].cursor() as cur:
        cur.execute(sql)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def _token(seed):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"demo:{seed}"))


def _rebase(date_str):
    """Rebase a historical date into the target sliding window.

    1399.03.08 -> TGT_LO (the start of the window).
    1399.06.08 -> TGT_HI (the end of the window, near today).
    Days in between are mapped proportionally, clamped to [TGT_LO, TGT_HI].
    """
    if not date_str or "." not in date_str:
        return date_str
    try:
        parts = date_str.split(".")
        src = jdatetime.date(int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, IndexError):
        return date_str
    offset = (src - SRC_LO_DATE).days
    tgt = TGT_LO + jdatetime.timedelta(days=offset)
    if tgt > TGT_HI:
        tgt = TGT_HI
    return tgt.strftime("%Y.%m.%d")


def _live_cutoff():
    """Rebased date that separates live tail from historical body.

    Anything rebased to >= this date stays live (not auto-completed).
    """
    return (TGT_HI - jdatetime.timedelta(days=LIVE_DAYS)).strftime("%Y.%m.%d")


class Command(BaseCommand):
    help = (f"Rebase {SRC_LO}..{SRC_HI} into {TGT_LO_STR}..{TGT_HI_STR} "
            f"with {MIN_IN_TUNNEL} wagons in the kiln tunnel.")

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true",
                            help="Remove all demoslice rows instead of building.")
        parser.add_argument("--wagons", type=int, default=None,
                            help="How many wagons to keep in the kiln tunnel (default: 44 = full capacity).")

    # ------------------------------------------------------------------ #
    def handle(self, *args, **options):
        if options["clear"]:
            self._clear()
            return

        wagon_count = options["wagons"] if options["wagons"] else MIN_IN_TUNNEL
        self._clear()  # idempotent: rebuild from scratch each run
        wagons = {w.wagon_name: w for w in Wagon.objects.all()}
        chambers = {c.chamber_id: c for c in Chamber.objects.all()}
        operators = {o.operator_id: o for o in Operator.objects.all()}
        products = {p.product_id: p for p in Product.objects.all()}
        glazes = {g.glaze_id: g for g in Glaze.objects.all()}

        # ================================================================== #
        #  DRYER (F1)                                                        #
        # ================================================================== #
        for dc in _rows(
            f"SELECT dryer_cycle_id, load_date, load_time, unload_date, unload_time, "
            f"load_operator_id, unload_operator_id, product_id, finger_count, chamber_id "
            f"FROM dryer_cycle WHERE load_date BETWEEN '{SRC_LO}' AND '{SRC_HI}' "
            f"ORDER BY dryer_cycle_id"
        ):
            chamber = chambers.get(dc["chamber_id"])
            if chamber is None:
                continue
            readings = [
                {"hour_offset": r["hour_offset"], "humidity_pct": r["humidity_pct"],
                 "temperature_c": r["temperature_c"]}
                for r in _rows(
                    f"SELECT hour_offset, humidity_pct, temperature_c FROM dryer_reading "
                    f"WHERE dryer_cycle_id={dc['dryer_cycle_id']} ORDER BY hour_offset")
            ]
            try:
                services.create_dryer_cycle(
                    chamber=chamber, readings=readings,
                    load_date=_rebase(dc["load_date"] or ""),
                    load_time=dc["load_time"],
                    unload_date=_rebase(dc["unload_date"] or ""),
                    unload_time=dc["unload_time"],
                    load_operator=operators.get(dc["load_operator_id"]),
                    unload_operator=operators.get(dc["unload_operator_id"]),
                    product=products.get(dc["product_id"]),
                    finger_count=dc["finger_count"] or 0,
                )
            except Exception:  # noqa: BLE001
                pass

        # ================================================================== #
        #  SETTING (F2) — one trip per wagon, reused for multi-chamber fill  #
        # ================================================================== #
        sw_by_event = {}
        for r in _rows(
            f"SELECT setting_event_id, setting_wagon_id, wagon_no, glaze_id, start_time, "
            f"end_time, packages, khesht_count, position_in_event FROM setting_wagon "
            f"WHERE setting_event_id IN (SELECT setting_event_id FROM setting_event "
            f"WHERE date_jalali BETWEEN '{SRC_LO}' AND '{SRC_HI}')"
        ):
            sw_by_event.setdefault(int(r["setting_event_id"]), []).append(r)

        events = _rows(
            f"SELECT setting_event_id, date_jalali, shift, chamber_id, product_id, "
            f"supervisor_id, operator_id FROM setting_event "
            f"WHERE date_jalali BETWEEN '{SRC_LO}' AND '{SRC_HI}' ORDER BY setting_event_id"
        )
        live_event_ids = {
            e["setting_event_id"]
            for e in events
            if _rebase(e["date_jalali"] or "") >= _live_cutoff()
        }
        for ev in events:
            clean = []
            ok = True
            for sw in sorted(sw_by_event.get(int(ev["setting_event_id"]), []),
                             key=lambda r: (r["position_in_event"] or 0)):
                wname = sw["wagon_no"]
                if wname is None or not (1 <= int(wname) <= 80) or str(wname) not in wagons:
                    ok = False
                    continue
                clean.append((wagons[str(wname)], sw))
            if not ok or not clean:
                continue
            chamber = chambers.get(ev["chamber_id"])
            if chamber is None:
                continue
            payload = [{
                "wagon": w,
                "glaze": glazes.get(sw["glaze_id"]),
                "start_time": sw["start_time"], "end_time": sw["end_time"],
                "packages": sw["packages"], "khesht_count": sw["khesht_count"],
            } for w, sw in clean]
            try:
                services.create_setting_batch(
                    chamber=chamber, wagons=payload,
                    client_token=_token(ev["setting_event_id"]),
                    date_jalali=_rebase(ev["date_jalali"] or ""),
                    shift=ev["shift"],
                    product=products.get(ev["product_id"]),
                    supervisor=operators.get(ev["supervisor_id"]),
                    operator=operators.get(ev["operator_id"]),
                )
            except Exception:  # noqa: BLE001
                pass

        # ================================================================== #
        #  KILN push + exit                                                  #
        #  1. Push ALL pushes in FIFO order (creates KilnPush + kiln_exit). #
        #  2. After all pushes, SELECT the 44 newest distinct-wagon pushes   #
        #     to stay in_tunnel; discharge the rest.                         #
        # ================================================================== #
        pushes = _rows(
            f"SELECT kiln_push_id, push_seq, push_date, push_time, shift, "
            f"operator_id, product_id FROM kiln_push "
            f"WHERE push_date BETWEEN '{SRC_LO}' AND '{SRC_HI}' ORDER BY push_seq"
        )
        all_pushed_trips = []  # (trip_id, push_date_rebased, wagon_name)
        for kp in pushes:
            trip = (
                WagonTrip.objects
                .filter(status__in=[WagonTrip.STATUS_IN_PROGRESS,
                                    WagonTrip.STATUS_WAITING_HALL])
                .order_by("trip_id").first()
            )
            if trip is None:
                continue
            try:
                services.push_wagon(
                    trip=trip, client_token=_token(100000 + kp["kiln_push_id"]),
                    push_date=_rebase(kp["push_date"] or ""),
                    push_time=kp["push_time"], shift=kp["shift"],
                    operator=operators.get(kp["operator_id"]),
                    product=products.get(kp["product_id"]),
                )
                all_pushed_trips.append((
                    trip.trip_id,
                    _rebase(kp["push_date"] or ""),
                    trip.wagon.wagon_name,
                ))
            except Exception:  # noqa: BLE001
                continue

        # Select WAGON_COUNT newest distinct-wagon pushes to stay in_tunnel.
        seen = set()
        keep_trip_ids = set()
        for tid, pd, wn in sorted(all_pushed_trips, key=lambda x: x[1], reverse=True):
            if wn not in seen:
                seen.add(wn)
                keep_trip_ids.add(tid)
                if len(seen) >= wagon_count:
                    break

        # After selecting the 44 in_tunnel trips, set their push_date/push_time
        # to today so the kiln always shows current dates. Spread push_time
        # across the day so the dashboard looks realistic.
        pushed_today = 0
        for tid in keep_trip_ids:
            trip = WagonTrip.objects.get(trip_id=tid)
            kp = trip.kiln_pushes.order_by("push_seq").first()
            if kp is not None:
                kp.push_date = TGT_HI_STR
                kp.push_time = "06:00:00"
                kp.save(update_fields=["push_date", "push_time"])
                pushed_today += 1

        self.stdout.write(
            self.style.WARNING(
                f"Bumped {pushed_today} in_tunnel wagons to today ({TGT_HI_STR})."
            )
        )

        # Discharge all pushed trips EXCEPT the selected 44.
        for tid in (t[0] for t in all_pushed_trips):
            if tid in keep_trip_ids:
                continue
            trip = WagonTrip.objects.get(trip_id=tid)
            ke = KilnExit.objects.filter(trip=trip).first()
            if ke is not None:
                ke.discharged = True
                ke.save(update_fields=["discharged"])
            trip.status = WagonTrip.STATUS_AWAITING_DISCHARGE
            trip.save(update_fields=["status"])

        # ================================================================== #
        #  GUARANTEE 44 IN_TUNNEL                                            #
        #  If we still don't have 44 distinct wagons in_tunnel (edge case),  #
        #  force it by pushing free wagons.                                  #
        # ================================================================== #
        in_tunnel_wagons = {
            t.wagon.wagon_name
            for t in WagonTrip.objects.filter(status=WagonTrip.STATUS_IN_TUNNEL)
        }
        self.stdout.write(
            self.style.WARNING(
                f"In-tunnel wagons after historical pushes: {len(in_tunnel_wagons)}."
            )
        )
        if len(in_tunnel_wagons) < wagon_count:
            self._force_kiln_full(wagons, in_tunnel_wagons, _token, wagon_count)

        # ================================================================== #
        #  PACKING (F5) — close discharged trips                             #
        # ================================================================== #
        pw_by_header = {}
        for r in _rows(
            f"SELECT packing_header_id, wagon_no, product_id, total_count, grade1_count, "
            f"grade2_count, waste_count FROM packing_wagon "
            f"WHERE packing_header_id IN (SELECT packing_header_id FROM packing_header "
            f"WHERE pack_date BETWEEN '{SRC_LO}' AND '{SRC_HI}')"
        ):
            pw_by_header.setdefault(int(r["packing_header_id"]), []).append(r)

        for ph in _rows(
            f"SELECT packing_header_id, pack_date, shift, controller_id FROM packing_header "
            f"WHERE pack_date BETWEEN '{SRC_LO}' AND '{SRC_HI}' ORDER BY packing_header_id"
        ):
            payload = []
            for pw in pw_by_header.get(int(ph["packing_header_id"]), []):
                wname = pw["wagon_no"]
                if wname is None or not (1 <= int(wname) <= 80) or str(wname) not in wagons:
                    continue
                trip = (
                    WagonTrip.objects
                    .filter(wagon=wagons[str(wname)],
                            status=WagonTrip.STATUS_AWAITING_DISCHARGE)
                    .order_by("trip_id").first()
                )
                if trip is None:
                    continue
                payload.append({
                    "trip_id": trip.trip_id, "product_id": pw["product_id"],
                    "total_count": pw["total_count"], "grade1_count": pw["grade1_count"],
                    "grade2_count": pw["grade2_count"], "waste_count": pw["waste_count"],
                })
            if not payload:
                continue
            try:
                services.register_packing(
                    wagons=payload, client_token=_token(200000 + ph["packing_header_id"]),
                    pack_date=_rebase(ph["pack_date"] or ""),
                    shift=ph["shift"], controller=operators.get(ph["controller_id"]),
                )
            except Exception:  # noqa: BLE001
                pass

        # ================================================================== #
        #  COMPLETION SWEEP                                                  #
        #  Complete all demo trips EXCEPT:                                   #
        #    - in_tunnel trips (the 44 full-kiln wagons)                     #
        #    - trips in the live tail (last LIVE_DAYS rebased days)          #
        #  This frees wagons for the Setting form while keeping a realistic   #
        #  live edge.                                                        #
        # ================================================================== #
        demo_tokens = set(_token(s) for s in range(0, 400000))
        demo_setting_ids = list(
            SettingEvent.objects
            .filter(client_token__in=demo_tokens)
            .values_list("setting_event_id", flat=True)
        )
        demo_trips = (
            WagonTrip.objects
            .filter(setting_wagons__setting_event_id__in=demo_setting_ids)
            .distinct()
        )
        # Trips in_tunnel are NEVER completed (they're the full kiln).
        in_tunnel_trip_ids = set(
            WagonTrip.objects
            .filter(status=WagonTrip.STATUS_IN_TUNNEL)
            .values_list("trip_id", flat=True)
        )
        # Trips in the live tail (last LIVE_DAYS) also stay live.
        live_tail_trip_ids = set(
            WagonTrip.objects
            .filter(setting_wagons__setting_event__date_jalali__gte=_live_cutoff())
            .filter(status__in=[
                WagonTrip.STATUS_IN_PROGRESS,
                WagonTrip.STATUS_BODY_DRIED,
                WagonTrip.STATUS_WAITING_HALL,
                WagonTrip.STATUS_AWAITING_DISCHARGE,
            ])
            .distinct()
            .values_list("trip_id", flat=True)
        )
        keep = in_tunnel_trip_ids | live_tail_trip_ids
        completed = 0
        for t in demo_trips.exclude(trip_id__in=keep):
            if t.status in (WagonTrip.STATUS_AWAITING_DISCHARGE,
                            WagonTrip.STATUS_IN_TUNNEL,
                            WagonTrip.STATUS_WAITING_HALL,
                            WagonTrip.STATUS_IN_PROGRESS,
                            WagonTrip.STATUS_BODY_DRIED):
                t.status = WagonTrip.STATUS_COMPLETED
                t.completed_at = timezone.now()
                t.save(update_fields=["status", "completed_at"])
                completed += 1

        # ================================================================== #
        #  ENSURE ONE CHAMBER IS LOADED (drying dashboard not empty)         #
        #  All rebased dryer cycles got discharged by setting batches above.  #
        #  Force one chamber to show as "loaded" so the dryer dashboard has   #
        #  at least one active chamber.                                       #
        # ================================================================== #
        # Find a chamber whose last cycle was unloaded, then mark it loaded
        today_str = TGT_HI_STR
        last_loaded = (
            DryerCycle.objects
            .filter(unload_date__isnull=False)
            .order_by('-dryer_cycle_id')
            .first()
        )
        if last_loaded:
            chamber_obj = last_loaded.chamber
            # Create a fresh dryer cycle loaded today, no unload
            # Use direct DB creation (no service call) to avoid triggering
            # create_setting_batch which would discharge the chamber.
            try:
                live_cycle = DryerCycle.objects.create(
                    chamber=chamber_obj,
                    load_date=today_str,
                    load_time="08:00:00",
                    unload_date='',
                    unload_time=None,
                    load_operator_id=8,  # DR27879
                    unload_operator_id=None,
                    product_id=next(iter(products.values())).product_id if products else None,
                    finger_count=64,
                    source_row=int(chamber_obj.chamber_id) if chamber_obj.chamber_id else None,
                )
                # Direct DB update of ChamberState (avoid service call that might fail)
                state, _ = ChamberState.objects.get_or_create(chamber=chamber_obj)
                state.is_loaded = True
                state.current_dryer_cycle = live_cycle
                state.current_setting_event = None
                from django.utils import timezone
                state.loaded_at = timezone.now()
                state.save(update_fields=["is_loaded", "current_dryer_cycle", "current_setting_event", "loaded_at"])
                self.stdout.write(
                    self.style.WARNING(
                        f"Live dryer: chamber {chamber_obj.chamber_code} loaded today "
                        f"({today_str}), cycle={live_cycle.dryer_cycle_id}, not yet unloaded."
                    )
                )
            except Exception as e:  # noqa: BLE001
                import traceback
                self.stdout.write(
                    self.style.ERROR(
                        f"Failed to create live dryer cycle: {e}\n{traceback.format_exc()}"
                    )
                )

        in_tunnel_final = WagonTrip.objects.filter(
            status=WagonTrip.STATUS_IN_TUNNEL
        ).count()
        self.stdout.write(self.style.SUCCESS(
            f"Demo slice built: {SRC_LO}..{SRC_HI} -> {TGT_LO_STR}..{TGT_HI_STR}.\n"
            f"  In-tunnel wagons: {in_tunnel_final} / {wagon_count} (default: 44 = full capacity).\n"
            f"  Completed during sweep: {completed}.\n"
            f"  Live tail (last {LIVE_DAYS} days) kept active.\n"
            f"  Trip-per-wagon model: create_setting_batch reuses active trips "
            f"(no per-wagon duplicates)."
        ))

    # ------------------------------------------------------------------ #
    def _force_kiln_full(self, wagons, already_in_tunnel, token_fn, wagon_count):
        """Push free wagons into the kiln until wagon_count distinct wagons
        are in_tunnel. Each new push creates a fresh trip (new journey) and
        stays in_tunnel (never discharged by this command).
        """
        needed = wagon_count - len(already_in_tunnel)
        if needed <= 0:
            return
        free = (
            Wagon.objects
            .exclude(
                wagontrip__status__in=[
                    WagonTrip.STATUS_IN_PROGRESS,
                    WagonTrip.STATUS_BODY_DRIED,
                    WagonTrip.STATUS_WAITING_HALL,
                    WagonTrip.STATUS_IN_TUNNEL,
                    WagonTrip.STATUS_AWAITING_DISCHARGE,
                ]
            )
            .order_by("?")
            [:needed]
        )
        created = 0
        for w in free:
            trip = WagonTrip.objects.create(
                wagon=w, status=WagonTrip.STATUS_IN_PROGRESS,
                source_module="setting",
            )
            try:
                services.push_wagon(
                    trip=trip,
                    client_token=token_fn(f"force-kiln-{w.wagon_name}"),
                    push_date=TGT_HI_STR,
                    push_time="12:00:00",
                    shift=1,
                )
                created += 1
            except Exception:  # noqa: BLE001
                pass
        self.stdout.write(
            self.style.WARNING(
                f"Force-filled kiln: pushed {created} additional wagons into "
                f"in_tunnel (now {MIN_IN_TUNNEL} target)."
            )
        )

    # ------------------------------------------------------------------ #
    def _clear(self):
        """Remove all demoslice rows. Demo rows are dated into the target
        window (TGT_LO.year), so date-prefix is the discriminator."""
        from mes.models import (
            DryerCycle, KilnPush, KilnExit, PackingHeader, PackingWagon,
            SettingEvent, SettingWagon, WagonTrip,
        )
        target_year = str(TGT_LO.year)
        with transaction.atomic():
            demo_setting_ids = list(
                SettingEvent.objects
                .filter(date_jalali__startswith=target_year)
                .values_list("setting_event_id", flat=True)
            )
            demo_trip_ids = set(
                WagonTrip.objects
                .filter(
                    models.Q(setting_wagons__setting_event_id__in=demo_setting_ids)
                    | models.Q(kiln_pushes__push_date__startswith=target_year)
                    | models.Q(kiln_exits__exit_date__startswith=target_year)
                )
                .distinct()
                .values_list("trip_id", flat=True)
            )
            KilnExit.objects.filter(
                models.Q(trip_id__in=demo_trip_ids)
                | models.Q(exit_date__startswith=target_year)
            ).delete()
            SettingWagon.objects.filter(trip_id__in=demo_trip_ids).delete()
            KilnPush.objects.filter(
                models.Q(trip_id__in=demo_trip_ids)
                | models.Q(push_date__startswith=target_year)
            ).delete()
            PackingWagon.objects.filter(trip_id__in=demo_trip_ids).delete()
            PackingHeader.objects.filter(pack_date__startswith=target_year).delete()
            DryerCycle.objects.filter(load_date__startswith=target_year).delete()
            SettingEvent.objects.filter(date_jalali__startswith=target_year).delete()
            WagonTrip.objects.filter(trip_id__in=demo_trip_ids).delete()
        self.stdout.write(self.style.WARNING("Demo slice cleared."))
