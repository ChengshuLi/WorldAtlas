from worldatlas.map_build.water.tests.helpers import index_present
import unittest
import numpy as np
from worldatlas.map_build.water import coastal_core as c
from worldatlas.map_build.water.tests.helpers import rle


def snap(priority=(2, 1, 3, 4, 5, 6)):
    return {
        'decision_revision': {'id': 'draft', 'status': 'draft', 'entity_revision': 'entities'},
        'category_bindings': [
            {'entity_id': i, 'physical_class': k, 'code': i + (16 if k == 'land' else 0)}
            for i in range(1, 7)
            for k in ('land', 'water')
        ],
        'policies': [
            {
                'id': 'test-coast',
                'kind': 'coastline_assignment',
                'evidence': {},
                'definition': {
                    'method': 'nearest_final_shore_band_v2',
                    'band_metres': '120000',
                    'band_tolerance_metres': '0.000001',
                    'shore_geometry': 'physical_coastal_land_cell_centers_4_neighbor_v1',
                    'distance': 'wgs84_ellipsoidal_center_to_center',
                    'ellipsoid': 'WGS84',
                    'land_input': 'final_decision_assigned_land',
                    'water_input': 'physical_water',
                    'tie_rules': {
                        'method': 'within_minimum_distance_tolerance',
                        'tolerance_metres': '0.00001',
                        'tie_break': 'first_entity_in_priority_order',
                        'priority_entity_ids': list(priority),
                    },
                },
            }
        ],
    }


class CoastalTest(unittest.TestCase):
    def setUp(self):
        self.p = np.ones((180, 360), dtype=np.uint32)
        self.l = np.zeros((180, 360), dtype=np.uint32)
        self.p[89, 4] = self.p[89, 6] = 17
        self.l[89, 4] = 17
        self.l[89, 6] = 18
        self.bounds = (0, 360, 0, 180)
        _, self.pairs, self.tol, self.band, self.btol = c.policy(snap())
        self.edges = c.shore.centers_for_crop(
            rle(self.p), rle(self.l), self.bounds, 360, 180, 1, [17, 18, 19, 20, 21, 22]
        )
        self.idx = index_present(self.edges, self.pairs)

    def test_band_and_entity_tie(self):
        # Row 89, midpoint x5 and distant x8. Two shores are equidistant to x5.
        result, stats = c.classify(
            [0.5, 0.5],
            [-174.5, -171.5],
            self.bounds,
            360,
            180,
            1,
            self.pairs,
            self.tol,
            self.band,
            self.btol,
            self.idx,
        )
        self.assertEqual(result.tolist(), [2, 0])
        self.assertEqual(stats['exact'] + stats['bounded'], 2)
        _, pairs, t, b, bt = c.policy(snap((1, 2, 3, 4, 5, 6)))
        result, _ = c.classify(
            [0.5],
            [-174.5],
            self.bounds,
            360,
            180,
            1,
            pairs,
            t,
            b,
            bt,
            index_present(self.edges, pairs),
        )
        self.assertEqual(result.tolist(), [1])

    def test_missing_or_unsupported_policy_fails(self):
        x = snap()
        x['policies'] = []
        with self.assertRaisesRegex(ValueError, 'policy'):
            c.policy(x)
        x = snap()
        x['policies'][0]['definition']['distance'] = 'spherical_segment'
        with self.assertRaisesRegex(ValueError, 'distance'):
            c.policy(x)
        x = snap()
        x['policies'][0]['definition']['tie_rules']['priority_entity_ids'] = [1, 2]
        with self.assertRaises(ValueError):
            c.policy(x)

    def test_crop_boundary_or_missing_shore(self):
        with self.assertRaisesRegex(ValueError, 'increase halo'):
            c.classify(
                [0.5],
                [-176],
                (4, 8, 88, 91),
                360,
                180,
                1,
                self.pairs,
                self.tol,
                self.band,
                self.btol,
                self.idx,
            )
        with self.assertRaisesRegex(ValueError, 'increase halo'):
            c.classify(
                [0.5],
                [-176],
                (4, 8, 88, 91),
                360,
                180,
                1,
                self.pairs,
                self.tol,
                self.band,
                self.btol,
                {},
            )
        codes, _ = c.classify(
            [0.5],
            [-174.5],
            self.bounds,
            360,
            180,
            1,
            self.pairs,
            self.tol,
            self.band,
            self.btol,
            {},
        )
        self.assertEqual(codes.tolist(), [0])

    def test_missing_local_class_is_not_global_absence(self):
        # The unseen participant can be outside the crop and too close to certify.
        only = {17: self.idx[17]}
        with self.assertRaisesRegex(ValueError, 'increase halo'):
            c.classify(
                [0.5],
                [-174.5],
                (4, 6, 88, 91),
                360,
                180,
                1,
                self.pairs,
                self.tol,
                self.band,
                self.btol,
                only,
            )


if __name__ == '__main__':
    unittest.main()
