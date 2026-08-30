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
            'chamber_code': self.chamber.chamber_code,
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


class TripSpineTests(SliceTestBase):
    def test_one_trip_across_three_days(self):
        """SRS acceptance #2: loaded today, pushed tomorrow, packed day-after = ONE trip."""
        load = self._load()
        self.assertEqual(load.status_code, 201)
        trip_ids = load.data['trip_ids']
        self.assertEqual(len(trip_ids), 1)
        trip_id = trip_ids[0]
        self.assertEqual(load.data['wagon_count'], 1)

        push = self.client.post('/api/kiln/pushes/', {
            'trip_id': trip_id,
            'push_date': '1404.06.08',
            'operator_id': self.operator.operator_id,
            'readings': [{'sensor_code': 'temp_Zone00', 'temperature_c': '950.50'}],
            'client_token': str(uuid.uuid4()),
        }, format='json')
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
        push = self.client.post('/api/kiln/pushes/', {
            'trip_id': trip_id, 'client_token': str(uuid.uuid4()),
        }, format='json')
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
            r = self.client.post('/api/kiln/pushes/', {
                'trip_id': trip_id, 'client_token': str(uuid.uuid4()),
            }, format='json')
            self.assertEqual(r.status_code, 201)

        self.assertEqual(
            WagonTrip.objects.filter(status=WagonTrip.STATUS_IN_TUNNEL).count(), 44,
        )

        overflow = self.client.post('/api/kiln/pushes/', {
            'trip_id': trip_ids[44], 'client_token': str(uuid.uuid4()),
        }, format='json')
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
            self.client.post('/api/kiln/pushes/',
                             {'trip_id': trip_id, 'client_token': str(uuid.uuid4())}, format='json')
        # Simulate discharge: mark the first wagon's KilnExit as discharged + trip completed.
        KilnExit.objects.filter(trip_id=trip_ids[0]).update(discharged=True)
        WagonTrip.objects.filter(pk=trip_ids[0]).update(status=WagonTrip.STATUS_AWAITING_DISCHARGE)
        r = self.client.post('/api/kiln/pushes/',
                             {'trip_id': trip_ids[44], 'client_token': str(uuid.uuid4())},
                             format='json')
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
        a = self.client.post('/api/kiln/pushes/', {'trip_id': trip_id, 'client_token': token},
                             format='json')
        b = self.client.post('/api/kiln/pushes/', {'trip_id': trip_id, 'client_token': token},
                             format='json')
        self.assertEqual(a.data['kiln_push_id'], b.data['kiln_push_id'])
        self.assertEqual(KilnPush.objects.count(), 1)


class CleanCoreBoundaryTests(SliceTestBase):
    def test_out_of_range_plate_is_not_selectable(self):
        """SRS acceptance #4: plate 81 does not exist as a dimension row, so a batch
        referencing it is rejected (clean-core: dropdown prevents typos at source)."""
        self.assertFalse(Wagon.objects.filter(wagon_name='81').exists())
        r = self.client.post('/api/setting/events/', {
            'chamber_code': self.chamber.chamber_code,
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
