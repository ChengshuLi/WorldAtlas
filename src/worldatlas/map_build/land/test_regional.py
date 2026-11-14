"""Small current-grid fixtures check source-neutral land selection and composition."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.core.layers import patch_rows, write_layer
from worldatlas.map_build.core.rle import open_grid
from worldatlas.map_build.land.affiliations import resolve_affiliations
from worldatlas.map_build.land.components import ComponentGrid
from worldatlas.map_build.land.composition import compose_land
from worldatlas.map_build.land.regional import build_regional
from worldatlas.map_build.land.line_groups import LatitudeLine, buffered_bounds, collect_runs, scan_components
from worldatlas.map_build.land.partitions import build_partitions
from worldatlas.map_build.water.shared_nearest import crop


def feature(ident, geometry, reference='OGC:CRS84'):
    checksum = hashlib.sha256(
        json.dumps(geometry, sort_keys=True, separators=(',', ':')).encode()
    ).hexdigest()
    return dict(
        feature_id=ident,
        geometry=geometry,
        geometry_sha256=checksum,
        coordinate_reference=reference,
    )


def polygon(west, south, east, north):
    return {
        'type': 'Polygon',
        'coordinates': [
            [[west, south], [east, south], [east, north], [west, north], [west, south]]
        ],
    }


class RegionalTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.grid = Grid(8, 4, 45.0)
        self.physical = np.ones((4, 8), dtype=np.uint32)
        self.physical[1, [1, 2, 5]] = self.physical[2, [0, 7]] = 17
        self.baseline = np.where(self.physical == 17, 301, 0).astype(np.uint32)
        for name, values in [('physical', self.physical), ('baseline', self.baseline)]:
            write_layer(
                self.root / name, self.grid, patch_rows(values, self.grid.bounds, self.grid)
            )
        components = self.root / 'components'
        components.mkdir()
        np.array([0, 0, 2, 4, 4], dtype='<u4').tofile(components / 'rows.u32le')
        np.array([[1, 3, 7], [5, 6, 90000], [0, 1, 42], [7, 8, 42]], dtype='<u4').tofile(
            components / 'runs.u32le'
        )
        self.bindings = [
            dict(entity_id=81, physical_class='land', code=301),
            dict(entity_id=42, physical_class='land', code=999),
        ]
        self.features = [
            feature('left', polygon(-130, 0, -50, 45)),
            feature('partial', polygon(-100, 0, -50, 45)),
            feature('right', {'type': 'Point', 'coordinates': [67.5, 22.5]}),
        ]
        self.rules = [
            dict(
                affiliation_id='left',
                entity_id=81,
                method='component_selection',
                evidence={
                    'component_selection': dict(
                        combine='all',
                        conditions=[dict(feature_id='left', relation='contains_component')],
                    )
                },
            ),
            dict(
                affiliation_id='right',
                entity_id=42,
                method='component_selection',
                evidence={
                    'component_selection': dict(
                        combine='all',
                        conditions=[dict(feature_id='right', relation='point_component')],
                    )
                },
            ),
        ]

    def components(self):
        return ComponentGrid(self.root / 'physical', self.root / 'components', self.grid)

    def test_complete_structured_geometry_to_final_land(self):
        selection = {
            'domains': {
                'regional': dict(
                    features=self.features, affiliations=self.rules, category_bindings=self.bindings
                )
            }
        }
        report = build_regional(
            selection,
            self.grid,
            self.root / 'physical',
            self.root / 'components',
            self.root / 'baseline',
            self.root / 'result',
        )
        self.assertEqual(report['claims'][0]['component_ids'], [7])
        self.assertEqual(report['claims'][1]['component_ids'], [90000])
        self.assertEqual(report['counts'], {'301': 4, '999': 1})
        with open_grid(report['land'], self.grid) as output:
            self.assertEqual(crop(*output, 1, 0, 8, 8).tolist(), [0, 301, 301, 0, 0, 999, 0, 0])

    def test_partial_coverage_wrapping_and_native_point_queries(self):
        with self.components() as components:
            self.assertEqual(components.totals(), {7: 2, 42: 2, 90000: 1})
            self.assertEqual(components.profile(self.features[1]['geometry']), {7: 1})
            self.assertEqual(components.point(67.5, 22.5), 90000)
            wrapped = {
                'type': 'MultiPolygon',
                'coordinates': [
                    polygon(-180, -45, -135, 0)['coordinates'],
                    polygon(135, -45, 180, 0)['coordinates'],
                ],
            }
            self.assertEqual(components.profile(wrapped), {42: 2})
            with self.assertRaisesRegex(ValueError, 'physical land'):
                components.point(112.5, 22.5)
            with self.assertRaisesRegex(ValueError, 'grid edge'):
                components.point(90, 22.5)

    def test_scoped_partition_is_composed_once_and_cannot_change_water(self):
        partition = dict(geometry=polygon(-180, -45, -135, 0), entity_id=42, component_ids={42})
        with self.components() as components:
            compose_land(
                components,
                self.root / 'baseline',
                {90000: 42},
                self.bindings,
                self.root / 'partitioned',
                partitions=[partition],
            )
        with open_grid(self.root / 'partitioned', self.grid) as data:
            self.assertEqual(crop(*data, 2, 0, 8, 8).tolist(), [999, 0, 0, 0, 0, 0, 0, 301])
        with self.components() as components, self.assertRaisesRegex(ValueError, 'conflicting'):
            compose_land(
                components,
                self.root / 'baseline',
                {42: 81},
                self.bindings,
                self.root / 'conflict',
                partitions=[partition],
            )

    def test_partition_contacts_on_water_are_irrelevant_but_land_ties_fail(self):
        partition = dict(geometry=polygon(-22.5, -45, 45, 45), entity_id=42)
        with self.components() as components:
            compose_land(
                components,
                self.root / 'baseline',
                {},
                self.bindings,
                self.root / 'water-contact',
                partitions=[partition],
            )
        partition['geometry'] = polygon(-67.5, -45, 45, 45)
        with self.components() as components, self.assertRaisesRegex(ValueError, 'cell center'):
            compose_land(
                components,
                self.root / 'baseline',
                {},
                self.bindings,
                self.root / 'land-contact',
                partitions=[partition],
            )

    def test_geographic_partition_overrides_distance_default_but_not_an_explicit_claim(self):
        seed = self.baseline.copy()
        seed[2, [0, 7]] = 0
        write_layer(self.root / 'seeds', self.grid, patch_rows(seed, self.grid.bounds, self.grid))
        partition = dict(geometry=polygon(-180, -45, -135, 0), entity_id=42)
        with self.components() as components:
            compose_land(
                components,
                self.root / 'seeds',
                {},
                self.bindings,
                self.root / 'defaults',
                component_defaults={42: 81},
                partitions=[partition],
            )
        with open_grid(self.root / 'defaults', self.grid) as output:
            self.assertEqual(crop(*output, 2, 0, 8, 8).tolist(), [999, 0, 0, 0, 0, 0, 0, 301])
        with self.components() as components, self.assertRaisesRegex(ValueError, 'conflicting'):
            compose_land(
                components,
                self.root / 'seeds',
                {42: 81},
                self.bindings,
                self.root / 'explicit-conflict',
                component_defaults={42: 81},
                partitions=[partition],
            )

    def island_selection(self, targets=(42,)):
        line = feature('divider', {'type': 'LineString', 'coordinates': [[0, 80], [0, -80]]})
        line['line_id'] = 'divider'
        policy = dict(
            line_id='divider',
            boundary_tolerance_degrees=0,
            bounds_lon_lat=[-179, -44, 179, 44],
            side_entity_ids={'west': 81, 'east': 42},
            anchor_feature_ids=[],
            anchor_assignment_bases=['selected_affiliation', 'whole_component_line_side'],
            satellite_policy=dict(
                max_satellite_cells=1,
                max_gap_m=5000,
                tie_m=0,
                allow_anchored_over_unknown_nearer=True,
            ),
            groups=[
                dict(
                    group_id=f'source-group-{i}',
                    mode='geographic_extent',
                    bounds_lon_lat=[-130, 0, -50, 45],
                    target_entity_id=entity,
                )
                for i, entity in enumerate(targets)
            ],
        )
        return dict(
            domains={
                'regional': dict(
                    features=self.features,
                    affiliations=self.rules[1:],
                    category_bindings=self.bindings,
                )
            },
            regional_partition=dict(line=line, policy=policy),
            raw_sources=[],
        )

    def test_line_groups_and_affiliations_are_resolved_before_one_composition(self):
        report = build_regional(
            self.island_selection(),
            self.grid,
            self.root / 'physical',
            self.root / 'components',
            self.root / 'baseline',
            self.root / 'grouped',
        )
        self.assertEqual(report['counts'], {'301': 2, '999': 3})
        self.assertEqual(
            report['islands'][0]['proposals'][7]['basis'], 'inferred_source_extent_group_convention'
        )
        self.assertEqual(report['islands'][0]['review'][42], 'crosses_or_touches_line')

    def test_current_partition_references_one_shared_line_feature(self):
        selection = self.island_selection()
        selected = selection.pop('regional_partition')
        line = selected.pop('line')
        line.pop('line_id')
        line.pop('geometry_sha256')
        line.pop('coordinate_reference')
        selected['policy'].pop('line_id')
        selected['feature_id'] = line['feature_id']
        selection['domains']['regional']['features'].append(line)
        selection['regional_partitions'] = [selected]
        result = build_regional(selection, self.grid, self.root / 'physical',
            self.root / 'components', self.root / 'baseline', self.root / 'current-grouped')
        self.assertEqual(result['counts'], {'301': 2, '999': 3})

    def test_opposing_complete_group_choices_stop_before_final_land_is_written(self):
        for targets in ((81, 42), (42, 81)):
            with self.subTest(order=targets):
                output = self.root / f'conflict-{targets[0]}'
                with self.assertRaisesRegex(ValueError, 'conflicting regional assignments.*7'):
                    build_regional(
                        self.island_selection(targets),
                        self.grid,
                        self.root / 'physical',
                        self.root / 'components',
                        self.root / 'baseline',
                        output,
                    )
                self.assertFalse((output / 'land').exists())

    def test_agreeing_groups_and_explicit_affiliation_priority_still_build(self):
        for targets, affiliations, expected in (
            ((42, 42), self.rules[1:], 999),
            ((81, 42), self.rules, 301),
        ):
            with self.subTest(groups=targets):
                selected = self.island_selection(targets)
                selected['domains']['regional']['affiliations'] = affiliations
                report = build_regional(
                    selected,
                    self.grid,
                    self.root / 'physical',
                    self.root / 'components',
                    self.root / 'baseline',
                    self.root / f'valid-{expected}',
                )
                with open_grid(report['land'], self.grid) as data:
                    self.assertEqual(crop(*data, 1, 1, 3, 8).tolist(), [expected, expected])

    def test_line_scans_complete_counts_and_wrapped_competitor_runs(self):
        line = LatitudeLine({'type': 'LineString', 'coordinates': [[0, 80], [0, -80]]}, 0)
        with self.components() as components:
            stats = scan_components(components, [130, -44, -130, 44], line)
            self.assertEqual(
                stats[42], dict(total=2, in_scope=2, west=1, east=1, boundary=0, outside_latitude=0)
            )
            self.assertEqual(collect_runs(components, {42}), {42: [(2, 0, 1), (2, 7, 8)]})
        self.assertIsNone(line.longitude(81))
        self.assertEqual(line.longitude(0), 0)
        bounds = buffered_bounds([170, -10, 179, 10], 500000)
        self.assertGreater(bounds[0], bounds[2])

    def test_selected_lines_produce_two_witnessed_partition_faces(self):
        a = feature('a', {'type': 'LineString', 'coordinates': [[0, 80], [0, 0]]})
        b = feature('b', {'type': 'LineString', 'coordinates': [[0, 0], [0, -80]]})
        a['boundary_id'], b['route_id'] = 'a', 'b'
        definition = dict(
            bounds_lon_lat=[-120, -40, 120, 40],
            sections=[dict(kind='boundary', id='a'), dict(kind='route', id='b')],
            sides=[
                dict(coordinates=[-60, 10], entity_id=81),
                dict(coordinates=[60, 10], entity_id=42),
            ],
        )
        domain = dict(
            mainland_boundaries=[a],
            routes=[b],
            policies=[dict(id='scope', kind='scoped_land_partition', definition=definition)],
        )
        partitions = build_partitions(domain)
        from shapely.geometry import Point, shape

        self.assertTrue(shape(partitions[0]['geometry']).contains(Point(-60, 10)))
        self.assertTrue(shape(partitions[1]['geometry']).contains(Point(60, 10)))
        definition['sides'][1]['coordinates'] = [-30, 10]
        with self.assertRaisesRegex(ValueError, 'opposite'):
            build_partitions(domain)
        definition['sides'][1]['coordinates'] = [60, 10]
        b['geometry']['coordinates'][0] = [1, 0]
        b['geometry_sha256'] = feature('b', b['geometry'])['geometry_sha256']
        with self.assertRaisesRegex(ValueError, 'do not join'):
            build_partitions(domain)

    def test_projected_source_contact_uses_declared_operations_and_reports_unknown(self):
        from pyproj import Transformer
        from shapely.geometry import mapping, shape
        from shapely.ops import transform

        forward = Transformer.from_crs('OGC:CRS84', 'EPSG:3857', always_xy=True)
        geometry = mapping(transform(forward.transform, shape(polygon(-130, 0, -50, 45))))
        pipeline = Transformer.from_crs('EPSG:3857', 'OGC:CRS84', always_xy=True).to_proj4()
        operation = dict(
            id='native',
            pipeline=pipeline,
            area_bounds=dict(west=-180, east=180, south=-85, north=85),
        )
        operations = dict(operations=[operation], operation_preference=['native'])
        with self.components() as components:
            counts = components.profile_projected(geometry, operations, {7, 90000})
            self.assertEqual(counts[7], dict(inside=2, boundary=0, unknown=0))
            self.assertEqual(counts[90000], dict(inside=0, boundary=0, unknown=0))
            operation['area_bounds'].update(west=-130, east=-50)
            self.assertEqual(
                components.profile_projected(geometry, operations, {90000})[90000]['unknown'], 1
            )

    def test_conflicting_targets_protected_components_and_bad_streams_fail(self):
        with self.components() as components:
            rules = [self.rules[0], dict(self.rules[0], affiliation_id='other', entity_id=42)]
            with self.assertRaisesRegex(ValueError, 'different entities'):
                resolve_affiliations(rules, self.features, components, self.bindings)
            with self.assertRaisesRegex(ValueError, 'protected'):
                resolve_affiliations(
                    self.rules, self.features, components, self.bindings, protected={7}
                )
        path = self.root / 'components/runs.u32le'
        values = np.fromfile(path, dtype='<u4')
        values[0] = 0
        values.tofile(path)
        with self.components() as components, self.assertRaisesRegex(ValueError, 'coverage'):
            components.row(1)


if __name__ == '__main__':
    unittest.main()
