from pathlib import Path
import tempfile
import unittest

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.rle import open_grid
from worldatlas.map_build.water.basins import Shorelines
from worldatlas.map_build.water.coastal import build_coastal
from worldatlas.map_build.water.shared_nearest import crop, GEOD
from worldatlas.map_build.water.test_basins import rle


class CoastalBuildTests(unittest.TestCase):
    def test_complete_stream_matches_independent_distances_across_batches(self):
        grid = Grid(36, 18, 10.0)
        physical = np.ones((18, 36), dtype=np.uint32)
        land = np.zeros_like(physical)
        physical[8:10, 0] = physical[8:10, 18] = 17
        land[8:10, 0], land[8:10, 18] = 70000, 300
        pairs = [(81, 70000, 90000), (42, 300, 4321)]
        definition = dict(
            method='nearest_final_shore_band_v2',
            band_metres=1600000,
            band_tolerance_metres=1e-6,
            shore_geometry='physical_coastal_land_cell_centers_4_neighbor_v1',
            distance='wgs84_ellipsoidal_center_to_center',
            ellipsoid='WGS84',
            land_input='final_decision_assigned_land',
            water_input='physical_water',
            tie_rules=dict(
                method='within_minimum_distance_tolerance',
                tie_break='first_entity_in_priority_order',
                priority_entity_ids=[81, 42],
                tolerance_metres=1e-5,
            ),
        )
        snapshot = {
            'category_bindings': [
                dict(entity_id=e, physical_class=k, code=c)
                for e, lc, wc in pairs
                for k, c in [('land', lc), ('water', wc)]
            ],
            'policies': [dict(id='coast', kind='coastline_assignment', definition=definition)],
        }
        p, l = rle(physical), rle(land)
        shores = Shorelines(p, l, grid, pairs)
        expected = np.zeros_like(physical)
        for y, x in zip(*np.nonzero(physical == 1)):
            distances = []
            for _, code, _ in pairs:
                yy, xx = np.nonzero(land == code)
                ds = GEOD.inv(
                    np.full(len(xx), float(grid.longitude(x))),
                    np.full(len(yy), float(grid.latitude(y))),
                    grid.longitude(xx),
                    grid.latitude(yy),
                )[2]
                distances.append(float(np.min(ds)))
            if min(distances) <= definition['band_metres'] + definition['band_tolerance_metres']:
                winner = next(
                    i for i, value in enumerate(distances) if value <= min(distances) + 1e-5
                )
                expected[y, x] = pairs[winner][2]
        with tempfile.TemporaryDirectory() as directory:
            for batch in (1, 7, 18):
                path = Path(directory) / str(batch)
                report = build_coastal(snapshot, grid, p, shores, path, rows_per_batch=batch)
                with open_grid(path, grid) as data:
                    actual = np.stack(
                        [crop(*data, y, 0, grid.width, grid.width) for y in range(grid.height)]
                    )
                np.testing.assert_array_equal(actual, expected)
                self.assertEqual(report['physical_water_cells'], int((physical == 1).sum()))
                self.assertEqual(sum(report['counts'].values()), int((expected != 0).sum()))
