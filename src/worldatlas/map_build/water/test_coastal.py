from worldatlas.map_build.water.tests.helpers import index_present
import unittest

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.water import coastal_core, coastal_rect, shared_nearest


class CoastalGeneralityTests(unittest.TestCase):
    def test_twenty_two_km_bands_overlap_across_a_thirty_km_strait(self):
        grid = Grid(131072, 54614, 360 / 131072)
        left, right, y = 65536, 65634, 32768
        lat = float(grid.latitude(y))
        shores = grid.longitude(np.array([left, right]))
        width_metres = shared_nearest.GEOD.inv(shores[0], lat, shores[1], lat)[2]
        self.assertAlmostEqual(width_metres, 30000, delta=50)
        pairs = [(81, 70000, 90000), (42, 300, 4321)]
        centers = dict(
            lat=np.array([lat, lat]),
            lon=shores,
            category=np.array([70000, 300]),
            mids=shared_nearest.unit(np.array([lat, lat]), shores),
        )
        indexes = index_present(centers, pairs)
        xs = np.arange(left + 1, right)
        actual, _ = coastal_rect.classify(
            np.ones((1, len(xs)), dtype=bool),
            left + 1,
            y,
            grid.bounds,
            grid.width,
            grid.height,
            grid.step,
            pairs,
            1e-5,
            22224,
            1e-6,
            indexes,
        )
        distances = np.array(
            [
                shared_nearest.GEOD.inv(
                    np.full(len(xs), shore),
                    np.full(len(xs), lat),
                    grid.longitude(xs),
                    np.full(len(xs), lat),
                )[2]
                for shore in shores
            ]
        )
        self.assertTrue(np.all(distances.min(axis=0) < 22224))
        expected = np.where(distances[0] <= distances[1] + 1e-5, 90000, 4321)
        np.testing.assert_array_equal(actual[0], expected)
        self.assertEqual(actual[0, len(xs) // 2], 90000)

    def test_single_entity_and_large_category_codes_need_no_status_fields(self):
        tie = dict(
            method='within_minimum_distance_tolerance',
            tie_break='first_entity_in_priority_order',
            priority_entity_ids=[81],
            tolerance_metres=1e-5,
        )
        policy = dict(
            method='nearest_final_shore_band_v2',
            band_metres=22224,
            band_tolerance_metres=1e-6,
            shore_geometry='physical_coastal_land_cell_centers_4_neighbor_v1',
            distance='wgs84_ellipsoidal_center_to_center',
            ellipsoid='WGS84',
            tie_rules=tie,
            land_input='final_decision_assigned_land',
            water_input='physical_water',
        )
        snapshot = {
            'category_bindings': [
                dict(entity_id=81, physical_class='land', code=70000),
                dict(entity_id=81, physical_class='water', code=90000),
            ],
            'policies': [dict(id='coast', kind='coastline_assignment', definition=policy)],
        }
        _, pairs, tolerance, band, bandtol = coastal_core.policy(snapshot)
        self.assertEqual(pairs, [(81, 70000, 90000)])
        grid = Grid(131072, 54614, 360 / 131072)
        x, y = 65536, 32768
        lon, lat = float(grid.longitude(x)), float(grid.latitude(y))
        sx, sy, _ = shared_nearest.GEOD.fwd(lon, lat, 90, 10000)
        centers = dict(
            lat=np.array([sy]),
            lon=np.array([sx]),
            category=np.array([70000]),
            mids=shared_nearest.unit(np.array([sy]), np.array([sx])),
        )
        indexes = index_present(centers, pairs)
        result, _ = coastal_rect.classify(
            np.ones((1, 1), dtype=bool),
            x,
            y,
            grid.bounds,
            grid.width,
            grid.height,
            grid.step,
            pairs,
            tolerance,
            band,
            bandtol,
            indexes,
        )
        self.assertEqual(int(result[0, 0]), 90000)
