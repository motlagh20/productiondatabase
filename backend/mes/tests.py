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
    SettingLoad,
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

    def _load(self, plate='1', token=None):
        return self.client.post('/api/setting/loads/', {
            'plate': plate,
            'chamber_code': self.chamber.chamber_code,
            'product_id': self.product.product_id,
            'glaze_id': self.glaze.glaze_id,
            'operator_id': self.operator.operator_id,
            'shift': 1,
            'client_token': str(token or uuid.uuid4()),
        }, format='json')


class TripSpineTests(SliceTestBase):
    def test_one_trip_across_three_days(self):
        """SRS acceptance #2: loaded today, pushed tomorrow, packed day-after = ONE trip."""
        load = self._load()
        self.assertEqual(load.status_code, 201)
        trip_id = load.data['trip_id']
        self.assertEqual(load.data['status'], 'in_progress')

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

        exit_ = self.client.post('/api/kiln/exits/', {
            'trip_id': trip_id, 'exit_date': '1404.06.09',
        }, format='json')
        self.assertEqual(exit_.status_code, 201)
        self.assertEqual(exit_.data['status'], 'awaiting_discharge')

        pack = self.client.post('/api/packing/headers/', {
            'pack_date': '1404.06.10',
            'shift': 1,
            'controller_id': self.operator.operator_id,
            'wagons': [{'trip_id': trip_id, 'total_count': 480, 'grade1_count': 450,
                        'grade2_count': 20, 'waste_count': 10}],
            'client_token': str(uuid.uuid4()),
        }, format='json')
        self.assertEqual(pack.status_code, 201)

        # F7: the journey is ONE trip carrying all four stages.
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
        """FIFO-44 rule: a wagon entering at push_seq P exits at P+43."""
        trip_id = self._load().data['trip_id']
        push = self.client.post('/api/kiln/pushes/', {
            'trip_id': trip_id, 'client_token': str(uuid.uuid4()),
        }, format='json')
        entry = push.data['push_seq']
        exit_ = self.client.post('/api/kiln/exits/', {'trip_id': trip_id}, format='json')
        self.assertEqual(exit_.data['entry_push_seq'], entry)
        self.assertEqual(exit_.data['exit_push_seq'], entry + 43)


class FifoCapacityTests(SliceTestBase):
    def test_tunnel_never_exceeds_44(self):
        """SRS acceptance #3: occupancy never exceeds 44 — the 45th push is rejected."""
        trip_ids = []
        for n in range(1, 46):  # 45 wagons for a 44-capacity tunnel
            trip_ids.append(self._load(plate=str(n)).data['trip_id'])

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
        """After a wagon exits the tunnel, a new push is accepted again."""
        trip_ids = [self._load(plate=str(n)).data['trip_id'] for n in range(1, 46)]
        for trip_id in trip_ids[:44]:
            self.client.post('/api/kiln/pushes/',
                             {'trip_id': trip_id, 'client_token': str(uuid.uuid4())}, format='json')
        self.client.post('/api/kiln/exits/', {'trip_id': trip_ids[0]}, format='json')
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
        self.assertEqual(first.data['trip_id'], second.data['trip_id'])
        self.assertEqual(first.data['setting_load_id'], second.data['setting_load_id'])
        self.assertEqual(SettingLoad.objects.count(), 1)
        self.assertEqual(WagonTrip.objects.count(), 1)

    def test_repeated_push_token_creates_one_push(self):
        trip_id = self._load().data['trip_id']
        token = str(uuid.uuid4())
        a = self.client.post('/api/kiln/pushes/', {'trip_id': trip_id, 'client_token': token},
                             format='json')
        b = self.client.post('/api/kiln/pushes/', {'trip_id': trip_id, 'client_token': token},
                             format='json')
        self.assertEqual(a.data['kiln_push_id'], b.data['kiln_push_id'])
        self.assertEqual(KilnPush.objects.count(), 1)


class CleanCoreBoundaryTests(SliceTestBase):
    def test_out_of_range_plate_is_not_selectable(self):
        """SRS acceptance #4: plate 81 does not exist as a dimension row, so it is rejected."""
        self.assertFalse(Wagon.objects.filter(wagon_name='81').exists())
        r = self._load(plate='81')
        self.assertEqual(r.status_code, 400)
        self.assertIn('plate', r.data)

    def test_plate_dropdown_exposes_exactly_1_to_80(self):
        r = self.client.get('/api/dimensions/wagons/')
        names = sorted(int(w['wagon_name']) for w in r.data)
        self.assertEqual(names, list(range(1, 81)))

    def test_packing_rejects_a_trip_not_awaiting_discharge(self):
        """A trip still in Setting cannot be packed — no silent state skipping."""
        trip_id = self._load().data['trip_id']
        r = self.client.post('/api/packing/headers/', {
            'wagons': [{'trip_id': trip_id}], 'client_token': str(uuid.uuid4()),
        }, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('awaiting_discharge', r.data['detail'])

    def test_unauthenticated_requests_are_rejected(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self._load().status_code, 401)
        self.assertEqual(
            self.client.get('/api/dashboard/wagon-journey/?plate=1').status_code, 401,
        )


class ServiceLayerTests(SliceTestBase):
    def test_exit_without_push_is_a_rule_violation(self):
        trip = WagonTrip.objects.create(wagon=Wagon.objects.get(wagon_name='5'))
        with self.assertRaises(services.RuleViolation):
            services.exit_wagon(trip=trip)
