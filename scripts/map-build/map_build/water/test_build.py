"""Exercise the complete water calculation with independent expected labels."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from map_build.core.grid import Grid
from map_build.core.layers import file_hash, patch_rows, write_layer
from map_build.core.rle import open_grid
from map_build.water.build import build_water
from map_build.water.remaining import water_snapshot
from map_build.water.coastal_core import policy
from map_build.water.ocean.engine import load_config
from map_build.water.shared_nearest import crop, GEOD


def selection():
    tie = dict(
        method='within_minimum_distance_tolerance',
        tie_break='first_entity_in_priority_order',
        priority_entity_ids=[81, 42],
        tolerance_metres=1e-5,
    )
    bindings = [
        dict(entity_id=e, physical_class=k, code=c)
        for e, lc, wc in [(81, 301, 17), (42, 999, 4321)]
        for k, c in [('land', lc), ('water', wc)]
    ]
    bindings.append(dict(entity_id=808, physical_class='water', code=98765))
    geometry = {
        'type': 'Polygon',
        'coordinates': [[[-70, -30], [-10, -30], [-10, 30], [-70, 30], [-70, -30]]],
    }
    checksum = hashlib.sha256(
        json.dumps(geometry, sort_keys=True, separators=(',', ':')).encode()
    ).hexdigest()
    water = {
        'entity_revision': {'id': 'entities'},
        'category_bindings': bindings,
        'features': [
            dict(
                feature_id='sea',
                geometry=geometry,
                geometry_sha256=checksum,
                coordinate_reference='OGC:CRS84',
                source_id='provider',
                source_version='one',
                source_feature_id='bay',
            )
        ],
        'basins': [
            dict(
                id='basin',
                feature_id='sea',
                geometry_sha256=checksum,
                assignment_method='nearest_participating_shore',
                tie_rules={'policy_id': 'coast'},
            )
        ],
        'policies': [
            dict(
                id='coast',
                kind='coastline_assignment',
                definition=dict(
                    method='nearest_final_shore_band_v2',
                    band_metres=1200000.0,
                    band_tolerance_metres=1e-6,
                    distance='wgs84_ellipsoidal_center_to_center',
                    ellipsoid='WGS84',
                    land_input='final_decision_assigned_land',
                    water_input='physical_water',
                    tie_rules=tie,
                    shore_geometry='physical_coastal_land_cell_centers_4_neighbor_v1',
                ),
            ),
            dict(
                id='order',
                kind='layer_precedence',
                definition={'order': ['coastal', 'named_basins', 'ocean', 'enclosed_water']},
            ),
            dict(
                id='closed',
                kind='closed_water_assignment',
                definition=dict(
                    method='closed_water_component_v2',
                    boundary_participants='adjacent_final_water_or_assigned_land',
                    distance='wgs84_ellipsoidal_center_to_center',
                    ellipsoid='WGS84',
                    latitude_grid_edge_contacts='report_only',
                    multiple_participants='nearest_assigned_land_shore',
                    no_participants='report_only',
                    one_participant='direct_fill',
                    source_cut_contacts='retain_ocean_parent_source_cut_review',
                    tie_rules=tie,
                    unresolved_zero_neighbors='report_only',
                    shore_geometry='physical_coastal_land_cell_centers_4_neighbor_v1',
                ),
            ),
        ],
    }
    ocean = {
        'entity_revision': {'id': 'entities'},
        'category_bindings': bindings,
        'endpoints': [
            dict(endpoint_id='top', longitude='-180', latitude='90'),
            dict(endpoint_id='bottom', longitude='-180', latitude='-90'),
            dict(endpoint_id='seed', longitude='100', latitude='80'),
        ],
        'routes': [
            dict(
                route_id='edge',
                route_type='meridian',
                parameters={},
                points=[dict(ordinal=0, endpoint_id='top'), dict(ordinal=1, endpoint_id='bottom')],
            )
        ],
        'ocean_seeds': [dict(seed_id='ocean', endpoint_id='seed', entity_id=808)],
        'policies': [
            dict(
                id='ocean',
                kind='ocean_fill',
                definition=dict(
                    connectivity=4,
                    wrap_longitude=True,
                    barrier_tie_rule='left-of-oriented-route',
                    unseeded_policy='report-only',
                    route_ids=['edge'],
                    seed_ids=['ocean'],
                ),
            )
        ],
    }
    return {'schema': 'worldatlas-input-selection-v1', 'domains': {'water': water, 'ocean': ocean}}


class WaterBuildTests(unittest.TestCase):
    def test_actual_coast_basin_ocean_and_composition_are_repeatable(self):
        grid = Grid(36, 18, 10.0)
        physical = np.ones((grid.height, grid.width), dtype=np.uint32)
        land = np.zeros_like(physical)
        physical[6:12, 8:11] = physical[6:12, 16:19] = 17
        land[6:12, 8:11], land[6:12, 16:19] = 301, 999
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, array in [('physical', physical), ('land', land)]:
                write_layer(root / name, grid, patch_rows(array, grid.bounds, grid))
            reports = [
                build_water(selection(), grid, root / 'physical', root / 'land', root / name)
                for name in ('one', 'two')
            ]
            shared = selection()
            water, ocean = (shared['domains'][key] for key in ('water', 'ocean'))
            combined = {**water, **ocean, 'policies': water['policies'] + ocean['policies']}
            shared['domains'] = {'water': deepcopy(combined), 'ocean': deepcopy(combined)}
            reports.append(build_water(shared, grid, root / 'physical', root / 'land', root / 'shared'))
            with open_grid(reports[0]['final'], grid) as data:
                actual = np.stack(
                    [crop(*data, y, 0, grid.width, grid.width) for y in range(grid.height)]
                )
            np.testing.assert_array_equal(actual[physical == 17], land[physical == 17])
            self.assertEqual(actual[0, 25], 98765)  # Open ocean.
            self.assertEqual(actual[8, 11], 17)  # Western coastal band.
            self.assertEqual(actual[8, 15], 4321)  # Eastern coastal band.
            self.assertEqual(actual[8, 12], 17)  # Basin interior beyond the band.
            self.assertEqual(actual[8, 14], 4321)
            self.assertFalse(np.any(actual == 0))
            self.assertEqual(reports[0]['basins'][0]['participant_shore_edges'], {81: 6, 42: 6})
            for name in ('rows.u32le', 'runs.u32le'):
                for report in reports[1:]:
                    self.assertEqual(file_hash(Path(reports[0]['final']) / name),
                                     file_hash(Path(report['final']) / name))
            self.assertEqual(sum(reports[0]['counts'].values()), grid.width * grid.height)
            self.assertEqual(reports[0]['download_seconds'], 0)

    def test_policies_come_from_their_selected_domain_without_hiding_missing_or_duplicate_rules(self):
        chosen = selection()
        expected = water_snapshot(chosen)
        water, ocean = (chosen['domains'][key] for key in ('water', 'ocean'))
        water['policies'].append(dict(id='wrong-ocean', kind='ocean_fill', definition={}))
        ocean['policies'].append(dict(id='wrong-coast', kind='coastline_assignment', definition={}))
        before = deepcopy(chosen)
        self.assertEqual(water_snapshot(chosen)['policies'], expected['policies'])
        self.assertEqual(chosen, before)
        policy(water_snapshot(chosen))
        load_config(water_snapshot(chosen), 36, 18)
        water['policies'].append(deepcopy(water['policies'][0]))
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            policy(water_snapshot(chosen))
        water['policies'] = [p for p in water['policies'] if p['kind'] != 'coastline_assignment']
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            policy(water_snapshot(chosen))
        ocean['policies'].append(deepcopy(ocean['policies'][0]))
        with self.assertRaisesRegex(ValueError, 'one ocean_fill'):
            load_config(water_snapshot(chosen), 36, 18)
        ocean['policies'] = [p for p in ocean['policies'] if p['kind'] != 'ocean_fill']
        with self.assertRaisesRegex(ValueError, 'one ocean_fill'):
            load_config(water_snapshot(chosen), 36, 18)

    def test_enclosed_water_uses_registry_codes_and_shared_complete_shores(self):
        grid = Grid(36, 18, 10.0)
        physical = np.ones((18, 36), dtype=np.uint32)
        land = np.zeros_like(physical)
        physical[6:12, 8:11] = physical[6:12, 16:19] = 17
        land[6:12, 8:11], land[6:12, 16:19] = 301, 999
        # A lake enclosed by land belonging to two entities, away from the basin.
        physical[3:8, 24:31] = 17
        land[3:8, 24:28], land[3:8, 28:31] = 301, 999
        physical[5, 26:29], land[5, 26:29] = 1, 0
        chosen = selection()
        chosen['domains']['water']['policies'][0]['definition']['band_metres'] = 22224.0
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, array in [('physical', physical), ('land', land)]:
                write_layer(root / name, grid, patch_rows(array, grid.bounds, grid))
            report = build_water(chosen, grid, root / 'physical', root / 'land', root / 'water')
            manifest = json.loads((root / 'water/remaining/enclosed/manifest.json').read_text())
            self.assertEqual(manifest['mixed_components'], 1)
            self.assertEqual(manifest['assigned_cells'], 3)
            self.assertEqual(manifest['pending_cells'], 0)
            with open_grid(report['final'], grid) as data:
                result = crop(*data, 5, 26, 29, grid.width)
            # Exhaustive independent distances to every four-edge land shore.
            shore = np.zeros_like(physical, dtype=bool)
            water = physical == 1
            shore |= np.roll(water, 1, axis=1) | np.roll(water, -1, axis=1)
            shore[1:] |= water[:-1]
            shore[:-1] |= water[1:]
            shore &= physical == 17
            for x, code in zip(range(26, 29), result):
                minima = []
                for lc in (301, 999):
                    yy, xx = np.nonzero(shore & (land == lc))
                    distances = GEOD.inv(
                        np.full(len(xx), float(grid.longitude(x))),
                        np.full(len(yy), float(grid.latitude(5))),
                        grid.longitude(xx),
                        grid.latitude(yy),
                    )[2]
                    minima.append(float(distances.min()))
                expected = 17 if minima[0] <= min(minima) + 1e-5 else 4321
                self.assertEqual(code, expected)


if __name__ == '__main__':
    unittest.main()
