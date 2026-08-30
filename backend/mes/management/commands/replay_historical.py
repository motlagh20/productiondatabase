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

        stats = {'setting': 0, 'setting_reject': 0, 'kiln': 0, 'kiln_reject': 0,
                 'packing': 0, 'packing_reject': 0}

        # ---- 1) SETTING: event + wagons + trip ----
        events = _rows(
            'SELECT setting_event_id, date_jalali, shift, chamber_id, product_id, '
            'supervisor_id, operator_id FROM setting_event ORDER BY setting_event_id'
        )
        for ev in events:
            sw_rows = _rows(
                'SELECT setting_wagon_id, wagon_no, glaze_id, start_time, end_time, '
                'packages, khesht_count, position_in_event FROM setting_wagon '
                'WHERE setting_event_id = %s ORDER BY position_in_event'
                % ev['setting_event_id']
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

        # ---- 2) KILN: push wagons in FIFO order (push_seq) ----
        pushes = _rows(
            'SELECT kiln_push_id, push_seq, push_date, push_time, shift, '
            'operator_id, product_id FROM kiln_push ORDER BY push_seq'
        )
        for kp in pushes:
            kw_rows = _rows(
                'SELECT wagon_no FROM kiln_wagon WHERE kiln_push_id = %s' % kp['kiln_push_id']
            )
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

        # ---- 2b) KILN EXIT: free tunnel capacity (FIFO-44 discharge) ----
        # Historical kiln_exit rows drive discharge so the 44-capacity ceiling does not
        # jam. Without this, pushes after the 44th are all rejected ("tunnel full").
        # staging kiln_exit uses wagon_id (FK to wagon.wagon_id), not wagon_no.
        exits = _rows(
            'SELECT wagon_id, exit_push_seq, exit_date, discharged FROM kiln_exit '
            'ORDER BY exit_push_seq'
        )
        wagon_by_id = {w.wagon_id: w for w in Wagon.objects.all()}
        for ke in exits:
            w = wagon_by_id.get(ke['wagon_id'])
            if w is None:
                EtlReject.objects.create(
                    module='kiln', source_row=None,
                    reason=f"invalid wagon_id={ke['wagon_id']} in kiln_exit", raw=str(ke))
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
            try:
                from mes.models import KilnExit
                ke = KilnExit.objects.filter(trip=trip).first()
                if ke is not None:
                    ke.discharged = True
                    ke.save(update_fields=['discharged'])
                trip.status = WagonTrip.STATUS_AWAITING_DISCHARGE
                trip.save(update_fields=['status'])
            except Exception as e:  # noqa: BLE001
                EtlReject.objects.create(
                    module='kiln', source_row=None,
                    reason=f"exit update error: {e}", raw=str(ke))
                stats['kiln_reject'] += 1

        # ---- 3) PACKING: close trips ----
        headers = _rows(
            'SELECT packing_header_id, pack_date, shift, controller_id FROM packing_header '
            'ORDER BY packing_header_id'
        )
        for ph in headers:
            pw_rows = _rows(
                'SELECT wagon_no, product_id, total_count, grade1_count, grade2_count, '
                'waste_count FROM packing_wagon WHERE packing_header_id = %s'
                % ph['packing_header_id']
            )
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
            f"Replay complete: setting={stats['setting']} (reject {stats['setting_reject']}), "
            f"kiln_pushes={stats['kiln']} (reject {stats['kiln_reject']}), "
            f"packing={stats['packing']} (reject {stats['packing_reject']})"
        ))
