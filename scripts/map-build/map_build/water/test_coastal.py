import unittest

import numpy as np

from map_build.core.grid import Grid
from map_build.water import coastal_core, coastal_rect, shared_nearest


class CoastalGeneralityTests(unittest.TestCase):
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
        indexes = coastal_core.index_present(centers, pairs)
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
