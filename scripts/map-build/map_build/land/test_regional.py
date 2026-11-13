"""Small current-grid fixtures check source-neutral land selection and composition."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from map_build.core.grid import Grid
from map_build.core.layers import patch_rows, write_layer
from map_build.core.rle import open_grid
from map_build.land.affiliations import resolve_affiliations
from map_build.land.components import ComponentGrid
from map_build.land.composition import compose_land
from map_build.land.regional import build_regional
from map_build.water.shared_nearest import crop


def feature(ident, geometry, reference='OGC:CRS84'):
    checksum = hashlib.sha256(json.dumps(geometry, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return dict(feature_id=ident, geometry=geometry, geometry_sha256=checksum, coordinate_reference=reference)


def polygon(west, south, east, north):
    return {'type': 'Polygon', 'coordinates': [[[west, south], [east, south],
                                               [east, north], [west, north], [west, south]]]}


class RegionalTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.grid = Grid(8, 4, 45.)
        self.physical = np.ones((4, 8), dtype=np.uint32)
        self.physical[1, [1, 2, 5]] = self.physical[2, [0, 7]] = 17
        self.baseline = np.where(self.physical == 17, 301, 0).astype(np.uint32)
        for name, values in [('physical', self.physical), ('baseline', self.baseline)]:
            write_layer(self.root / name, self.grid, patch_rows(values, self.grid.bounds, self.grid))
        components = self.root / 'components'
        components.mkdir()
        np.array([0, 0, 2, 4, 4], dtype='<u4').tofile(components / 'rows.u32le')
        np.array([[1, 3, 7], [5, 6, 90000], [0, 1, 42], [7, 8, 42]], dtype='<u4').tofile(components / 'runs.u32le')
        self.bindings = [dict(entity_id=81, physical_class='land', code=301),
                         dict(entity_id=42, physical_class='land', code=999)]
        self.features = [feature('left', polygon(-130, 0, -50, 45)),
                         feature('partial', polygon(-100, 0, -50, 45)),
                         feature('right', {'type': 'Point', 'coordinates': [67.5, 22.5]})]
        self.rules = [dict(affiliation_id='left', entity_id=81, method='component_selection',
                          evidence={'component_selection': dict(combine='all', conditions=[
                              dict(feature_id='left', relation='contains_component')])}),
                      dict(affiliation_id='right', entity_id=42, method='component_selection',
                           evidence={'component_selection': dict(combine='all', conditions=[
                               dict(feature_id='right', relation='point_component')])})]

    def components(self):
        return ComponentGrid(self.root / 'physical', self.root / 'components', self.grid)

    def test_complete_structured_geometry_to_final_land(self):
        selection = {'domains': {'regional': dict(features=self.features, affiliations=self.rules,
                                                   category_bindings=self.bindings)}}
        report = build_regional(selection, self.grid, self.root / 'physical', self.root / 'components',
                                self.root / 'baseline', self.root / 'result')
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
            wrapped = {'type': 'MultiPolygon', 'coordinates': [
                polygon(-180, -45, -135, 0)['coordinates'], polygon(135, -45, 180, 0)['coordinates']]}
            self.assertEqual(components.profile(wrapped), {42: 2})
            with self.assertRaisesRegex(ValueError, 'physical land'):
                components.point(112.5, 22.5)
            with self.assertRaisesRegex(ValueError, 'grid edge'):
                components.point(90, 22.5)

    def test_scoped_partition_is_composed_once_and_cannot_change_water(self):
        partition = dict(geometry=polygon(-180, -45, -135, 0), entity_id=42, component_ids={42})
        with self.components() as components:
            compose_land(components, self.root / 'baseline', {90000: 42}, self.bindings,
                         self.root / 'partitioned', partitions=[partition])
        with open_grid(self.root / 'partitioned', self.grid) as data:
            self.assertEqual(crop(*data, 2, 0, 8, 8).tolist(), [999, 0, 0, 0, 0, 0, 0, 301])
        with self.components() as components, self.assertRaisesRegex(ValueError, 'conflicting'):
            compose_land(components, self.root / 'baseline', {42: 81}, self.bindings,
                         self.root / 'conflict', partitions=[partition])

    def test_projected_source_contact_uses_declared_operations_and_reports_unknown(self):
        from pyproj import Transformer
        from shapely.geometry import mapping, shape
        from shapely.ops import transform
        forward = Transformer.from_crs('OGC:CRS84', 'EPSG:3857', always_xy=True)
        geometry = mapping(transform(forward.transform, shape(polygon(-130, 0, -50, 45))))
        pipeline = Transformer.from_crs('EPSG:3857', 'OGC:CRS84', always_xy=True).to_proj4()
        operation = dict(id='native', pipeline=pipeline, area_bounds=dict(west=-180, east=180, south=-85, north=85))
        operations = dict(operations=[operation], operation_preference=['native'])
        with self.components() as components:
            counts = components.profile_projected(geometry, operations, {7, 90000})
            self.assertEqual(counts[7], dict(inside=2, boundary=0, unknown=0))
            self.assertEqual(counts[90000], dict(inside=0, boundary=0, unknown=0))
            operation['area_bounds'].update(west=-130, east=-50)
            self.assertEqual(components.profile_projected(geometry, operations, {90000})[90000]['unknown'], 1)

    def test_conflicting_targets_protected_components_and_bad_streams_fail(self):
        with self.components() as components:
            rules = [self.rules[0], dict(self.rules[0], affiliation_id='other', entity_id=42)]
            with self.assertRaisesRegex(ValueError, 'different entities'):
                resolve_affiliations(rules, self.features, components, self.bindings)
            with self.assertRaisesRegex(ValueError, 'protected'):
                resolve_affiliations(self.rules, self.features, components, self.bindings, protected={7})
        path = self.root / 'components/runs.u32le'
        values = np.fromfile(path, dtype='<u4')
        values[0] = 0
        values.tofile(path)
        with self.components() as components, self.assertRaisesRegex(ValueError, 'coverage'):
            components.row(1)


if __name__ == '__main__':
    unittest.main()
