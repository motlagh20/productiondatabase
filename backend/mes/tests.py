"""Slice acceptance tests (M5_SRS §8).

Covers: one-trip-across-days spine, FIFO-44 ceiling, exit = entry + 43,
replay idempotency, and the plate-range boundary.
"""
import uuid

from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from mes import services
from mes.models import (
    Chamber,
    Glaze,
    KilnPush,
    KilnSensor,
    Operator,
    Product,
    SettingEvent,
    SettingWagon,
    Wagon,
    WagonTrip,
)


class SliceTestBase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('op', password='x')
        self.client.force_authenticate(self.user)
        # Dimension fixtures: plates 1..80 only (clean core — no out-of-range plate exists).
        for n in range(1, 81):
            Wagon.objects.create(wagon_name=str(n))
        self.chamber = Chamber.objects.create(chamber_code='CH01', chamber_type='DRYER')
        self.product = Product.objects.create(product_name_setting='سفال')
        self.glaze = Glaze.objects.create(glaze_code='LAAB', glaze_name='لعاب')
        self.operator = Operator.objects.create(operator_code='OP001', full_name='بهرامپور')
        self.sensor = KilnSensor.objects.create(sensor_code='temp_Zone00', position_order=1)

    def _force_manager(self):
        """Re-authenticate the test client as a Manager so dashboard/journey reads pass."""
        mgr = User.objects.create_user('mgr', password='y')
        Operator.objects.create(operator_code='mgr', full_name='مدیر', role='manager')
        self.client.force_authenticate(mgr)

    def _load(self, plates=('1',), token=None):
        """Submit a chamber-centric Setting batch with the given wagon plates.
        Returns the response; use .data['trip_ids'][0] for the first wagon's trip."""
        resp = self.client.post('/api/setting/events/', {
            'chamber_id': self.chamber.chamber_id,
            'date_jalali': '1404.06.07',
            'shift': 1,
            'product_id': self.product.product_id,
            'operator_id': self.operator.operator_id,
            'wagons': [
                {'wagon_id': Wagon.objects.get(wagon_name=p).wagon_id,
                 'glaze_id': self.glaze.glaze_id,
                 'start_time': '14:30', 'end_time': '16:45',
                 'packages': 64, 'khesht_count': 120}
                for p in plates
            ],
            'client_token': str(token or uuid.uuid4()),
        }, format='json')
        return resp

    def _push(self, trip_id, **extra):
        """Push the ACTIVE trip of the wagon that owns `trip_id`.
        Resolves the wagon from the trip (the new API takes wagon_id)."""
        wagon_id = WagonTrip.objects.get(pk=trip_id).wagon_id
        payload = {'wagon_id': wagon_id, 'client_token': str(uuid.uuid4())}
        payload.update(extra)
        return self.client.post('/api/kiln/pushes/', payload, format='json')


class TripSpineTests(SliceTestBase):
    def test_one_trip_across_three_days(self):
        """SRS acceptance #2: loaded today, pushed tomorrow, packed day-after = ONE trip."""
        load = self._load()
        self.assertEqual(load.status_code, 201)
        trip_ids = load.data['trip_ids']
        self.assertEqual(len(trip_ids), 1)
        trip_id = trip_ids[0]
        self.assertEqual(load.data['wagon_count'], 1)

        push = self._push(trip_id, push_date='1404.06.08', operator_id=self.operator.operator_id,
                          readings=[{'sensor_code': 'temp_Zone00', 'temperature_c': '950.50'}])
        self.assertEqual(push.status_code, 201)
        self.assertEqual(push.data['trip_id'], trip_id)
        self.assertEqual(push.data['status'], 'in_tunnel')

        pack = self.client.post('/api/packing/headers/', {
            'pack_date': '1404.06.10',
            'shift': 1,
            'controller_id': self.operator.operator_id,
            'wagons': [{'trip_id': trip_id, 'total_count': 480, 'grade1_count': 450,
                        'grade2_count': 20, 'waste_count': 10}],
            'client_token': str(uuid.uuid4()),
        }, format='json')
        self.assertEqual(pack.status_code, 201)

        # F7: the journey is ONE trip carrying all four stages (Manager/Admin only).
        self._force_manager()
        journey = self.client.get('/api/dashboard/wagon-journey/?plate=1')
        self.assertEqual(journey.status_code, 200)
        trips = journey.data['trips']
        self.assertEqual(len(trips), 1)
        t = trips[0]
        self.assertEqual(t['trip_id'], trip_id)
        self.assertEqual(t['status'], 'completed')
        self.assertIsNotNone(t['setting'])
        self.assertIsNotNone(t['kiln_entry'])
        self.assertIsNotNone(t['kiln_exit'])
        self.assertIsNotNone(t['packing'])
        self.assertEqual(t['packing']['grade1_count'], 450)

    def test_exit_seq_is_entry_plus_43(self):
        """FIFO-44 rule: a wagon entering at push_seq P exits at P+43 (auto-derived on push)."""
        from mes.models import KilnExit
        trip_id = self._load().data['trip_ids'][0]
        push = self._push(trip_id)
        entry = push.data['push_seq']
        # exit is derived automatically on push (F4): no manual endpoint
        ke = KilnExit.objects.get(trip_id=trip_id)
        self.assertEqual(ke.entry_push_seq, entry)
        self.assertEqual(ke.exit_push_seq, entry + 43)


class FifoCapacityTests(SliceTestBase):
    def test_tunnel_never_exceeds_44(self):
        """SRS acceptance #3: occupancy never exceeds 44 — the 45th push is rejected."""
        trip_ids = []
        for n in range(1, 46):  # 45 wagons for a 44-capacity tunnel
            trip_ids.append(self._load(plates=(str(n),)).data['trip_ids'][0])

        for trip_id in trip_ids[:44]:
            r = self._push(trip_id)
            self.assertEqual(r.status_code, 201)

        self.assertEqual(
            WagonTrip.objects.filter(status=WagonTrip.STATUS_IN_TUNNEL).count(), 44,
        )

        overflow = self._push(trip_ids[44])
        self.assertEqual(overflow.status_code, 400)
        self.assertIn('full', overflow.data['detail'].lower())
        # Occupancy still exactly at capacity, never above.
        self.assertEqual(
            WagonTrip.objects.filter(status=WagonTrip.STATUS_IN_TUNNEL).count(), 44,
        )

    def test_discharge_frees_a_slot(self):
        """After a wagon exits the tunnel (auto-derived on push), a new push is accepted again."""
        from mes.models import WagonTrip, KilnExit
        trip_ids = [self._load(plates=(str(n),)).data['trip_ids'][0] for n in range(1, 46)]
        for trip_id in trip_ids[:44]:
            self._push(trip_id)
        # Simulate discharge: mark the first wagon's KilnExit as discharged + trip completed.
        KilnExit.objects.filter(trip_id=trip_ids[0]).update(discharged=True)
        WagonTrip.objects.filter(pk=trip_ids[0]).update(status=WagonTrip.STATUS_AWAITING_DISCHARGE)
        r = self._push(trip_ids[44])
        self.assertEqual(r.status_code, 201)


class ReplaySafetyTests(SliceTestBase):
    def test_repeated_setting_load_token_creates_one_trip(self):
        """N1 groundwork: a retried submission must not duplicate the trip."""
        token = uuid.uuid4()
        first = self._load(token=token)
        second = self._load(token=token)
        self.assertEqual(first.data['trip_ids'], second.data['trip_ids'])
        self.assertEqual(first.data['setting_event_id'], second.data['setting_event_id'])
        self.assertEqual(SettingEvent.objects.count(), 1)
        self.assertEqual(SettingWagon.objects.count(), 1)
        self.assertEqual(WagonTrip.objects.count(), 1)

    def test_repeated_push_token_creates_one_push(self):
        trip_id = self._load().data['trip_ids'][0]
        token = str(uuid.uuid4())
        a = self._push(trip_id, client_token=token)
        b = self._push(trip_id, client_token=token)
        # Replay-safe: both calls resolve to the SAME push row (same client_token).
        self.assertEqual(a.status_code, 201)
        self.assertEqual(b.status_code, 201)
        self.assertEqual(a.data['kiln_push_id'], b.data['kiln_push_id'])
        self.assertEqual(KilnPush.objects.count(), 1)


class CleanCoreBoundaryTests(SliceTestBase):
    def test_out_of_range_plate_is_not_selectable(self):
        """SRS acceptance #4: plate 81 does not exist as a dimension row, so a batch
        referencing it is rejected (clean-core: dropdown prevents typos at source)."""
        self.assertFalse(Wagon.objects.filter(wagon_name='81').exists())
        r = self.client.post('/api/setting/events/', {
            'chamber_id': self.chamber.chamber_id,
            'wagons': [{'wagon_id': 99999}],  # non-existent wagon FK
            'client_token': str(uuid.uuid4()),
        }, format='json')
        self.assertEqual(r.status_code, 400)

    def test_plate_dropdown_exposes_exactly_1_to_80(self):
        r = self.client.get('/api/dimensions/wagons/')
        names = sorted(int(w['wagon_name']) for w in r.data)
        self.assertEqual(names, list(range(1, 81)))

    def test_packing_rejects_a_trip_not_awaiting_discharge(self):
        """A trip still in Setting cannot be packed — no silent state skipping."""
        trip_id = self._load().data['trip_ids'][0]
        r = self.client.post('/api/packing/headers/', {
            'wagons': [{'trip_id': trip_id}], 'client_token': str(uuid.uuid4()),
        }, format='json')
        self.assertEqual(r.status_code, 400)

    def test_unauthenticated_requests_are_rejected(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self._load().status_code, 401)
        # Journey is Manager-only → unauthenticated gets 401 (not 403, per DRF).
        self.assertEqual(
            self.client.get('/api/dashboard/wagon-journey/?plate=1').status_code, 401,
        )

    def test_operator_cannot_read_journey(self):
        """SRS §2.2: only Manager/Admin may read the journey dashboard, not a plain Operator."""
        # client is already authenticated as 'op' (Operator, no manager role) from setUp.
        r = self.client.get('/api/dashboard/wagon-journey/?plate=1')
        self.assertEqual(r.status_code, 403)


class ServiceLayerTests(SliceTestBase):
    def test_exit_without_push_is_a_rule_violation(self):
        trip = WagonTrip.objects.create(wagon=Wagon.objects.get(wagon_name='5'))
        with self.assertRaises(services.RuleViolation):
            services.exit_wagon(trip=trip)


class DryerReadingTests(SliceTestBase):
    """Tests for POST /api/dryer/readings/ (append reading to open cycle)."""

    def _load_chamber(self):
        """Create a dryer cycle on self.chamber so it has an open cycle."""
        return self.client.post('/api/dryer/cycles/', {
            'chamber_id': self.chamber.chamber_id,
            'load_date': '1405.03.01',
        }, format='json')

    def test_append_reading_happy_path(self):
        self._load_chamber()
        r = self.client.post('/api/dryer/readings/', {
            'chamber_id': self.chamber.chamber_id,
            'temperature_c': '45.50',
            'humidity_pct': '82.00',
            'hour_offset': 0,
        }, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['hour_offset'], 0)

    def test_auto_hour_offset(self):
        self._load_chamber()
        # First reading auto-assigns hour 0
        r1 = self.client.post('/api/dryer/readings/', {
            'chamber_id': self.chamber.chamber_id,
            'temperature_c': '40.00',
        }, format='json')
        self.assertEqual(r1.data['hour_offset'], 0)
        # Second auto-assigns hour 1
        r2 = self.client.post('/api/dryer/readings/', {
            'chamber_id': self.chamber.chamber_id,
            'temperature_c': '42.00',
        }, format='json')
        self.assertEqual(r2.data['hour_offset'], 1)

    def test_duplicate_hour_rejected(self):
        self._load_chamber()
        self.client.post('/api/dryer/readings/', {
            'chamber_id': self.chamber.chamber_id,
            'hour_offset': 3,
            'temperature_c': '50.00',
        }, format='json')
        r = self.client.post('/api/dryer/readings/', {
            'chamber_id': self.chamber.chamber_id,
            'hour_offset': 3,
            'temperature_c': '55.00',
        }, format='json')
        self.assertEqual(r.status_code, 400)

    def test_no_open_cycle_rejected(self):
        # Chamber has no dryer cycle at all
        r = self.client.post('/api/dryer/readings/', {
            'chamber_id': self.chamber.chamber_id,
            'temperature_c': '40.00',
        }, format='json')
        self.assertEqual(r.status_code, 400)


class DryerUnloadTests(SliceTestBase):
    """Tests for POST /api/dryer/unload/."""

    def _load_chamber(self):
        self.client.post('/api/dryer/cycles/', {
            'chamber_id': self.chamber.chamber_id,
            'load_date': '1405.03.01',
        }, format='json')

    def test_unload_completes_cycle(self):
        self._load_chamber()
        r = self.client.post('/api/dryer/unload/', {
            'chamber_id': self.chamber.chamber_id,
            'unload_date': '1405.03.02',
            'client_token': str(uuid.uuid4()),
        }, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['unload_date'], '1405.03.02')

    def test_double_unload_with_token_is_idempotent(self):
        self._load_chamber()
        token = str(uuid.uuid4())
        r1 = self.client.post('/api/dryer/unload/', {
            'chamber_id': self.chamber.chamber_id,
            'unload_date': '1405.03.02',
            'client_token': token,
        }, format='json')
        r2 = self.client.post('/api/dryer/unload/', {
            'chamber_id': self.chamber.chamber_id,
            'unload_date': '1405.03.02',
            'client_token': token,
        }, format='json')
        self.assertEqual(r1.data['dryer_cycle_id'], r2.data['dryer_cycle_id'])

    def test_double_unload_without_token_rejected(self):
        self._load_chamber()
        self.client.post('/api/dryer/unload/', {
            'chamber_id': self.chamber.chamber_id,
            'unload_date': '1405.03.02',
        }, format='json')
        r = self.client.post('/api/dryer/unload/', {
            'chamber_id': self.chamber.chamber_id,
            'unload_date': '1405.03.03',
        }, format='json')
        self.assertEqual(r.status_code, 400)

    def test_unload_keeps_chamber_loaded(self):
        """Unload does NOT flip is_loaded — setting discharge does that."""
        from mes.models import ChamberState
        self._load_chamber()
        self.client.post('/api/dryer/unload/', {
            'chamber_id': self.chamber.chamber_id,
            'unload_date': '1405.03.02',
        }, format='json')
        state = ChamberState.objects.get(chamber=self.chamber)
        self.assertTrue(state.is_loaded)


class ListEndpointTests(SliceTestBase):
    """Tests for the 4 new GET list endpoints."""

    def test_dryer_chamber_status_requires_auth(self):
        self.client.force_authenticate(user=None)
        r = self.client.get('/api/dryer/chambers/status/')
        self.assertEqual(r.status_code, 401)

    def test_dryer_chamber_status_shows_states(self):
        # Load a chamber → should show 'drying'
        self.client.post('/api/dryer/cycles/', {
            'chamber_id': self.chamber.chamber_id,
            'load_date': '1405.03.01',
        }, format='json')
        r = self.client.get('/api/dryer/chambers/status/')
        self.assertEqual(r.status_code, 200)
        statuses = {ch['chamber_code']: ch['derived_status'] for ch in r.data}
        self.assertEqual(statuses.get('CH01'), 'drying')

    def test_dryer_chamber_status_dried(self):
        self.client.post('/api/dryer/cycles/', {
            'chamber_id': self.chamber.chamber_id,
            'load_date': '1405.03.01',
        }, format='json')
        self.client.post('/api/dryer/unload/', {
            'chamber_id': self.chamber.chamber_id,
            'unload_date': '1405.03.02',
        }, format='json')
        r = self.client.get('/api/dryer/chambers/status/')
        statuses = {ch['chamber_code']: ch['derived_status'] for ch in r.data}
        self.assertEqual(statuses.get('CH01'), 'dried')

    def test_dryer_cycle_list_newest_first(self):
        self.client.post('/api/dryer/cycles/', {
            'chamber_id': self.chamber.chamber_id,
            'load_date': '1405.03.01',
        }, format='json')
        r = self.client.get('/api/dryer/cycles/list/')
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(len(r.data), 1)
        self.assertIn('readings', r.data[0])

    def test_setting_event_list(self):
        self._load()  # create a setting event
        r = self.client.get('/api/setting/events/list/')
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(len(r.data), 1)
        self.assertIn('wagons', r.data[0])
        self.assertIn('chamber_code', r.data[0])

    def test_kiln_push_list(self):
        trip_id = self._load().data['trip_ids'][0]
        self._push(trip_id)
        r = self.client.get('/api/kiln/pushes/list/')
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(len(r.data), 1)
        self.assertIn('plate', r.data[0])
        self.assertIn('readings', r.data[0])

    def test_lists_require_auth(self):
        self.client.force_authenticate(user=None)
        for url in ['/api/dryer/cycles/list/', '/api/setting/events/list/', '/api/kiln/pushes/list/']:
            r = self.client.get(url)
            self.assertEqual(r.status_code, 401, f'{url} should require auth')
