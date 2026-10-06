"""Exact structure controls: ordering may vary; original coordinates may not."""
import copy
import importlib.util
import math
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('validator', ROOT / 'scripts/validate-physical-component-evidence.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def row(kind, coordinates):
    return {'id': 'original', 'kind': 'contact', 'dateline': False,
            'components': ['a', 'b'], 'geometry': {'type': kind, 'coordinates': coordinates}}


class Controls(unittest.TestCase):
    def test_actual_linux_member_permutation(self):
        a = row('MultiPoint', [[55.77461304, 24.50888876], [55.77461304, 24.50888877]])
        b = copy.deepcopy(a)
        b['geometry']['coordinates'].reverse()
        v.require_exact_reconstruction([a], [b], 'changed')

    def test_line_direction_only(self):
        a = row('LineString', [[0, 0], [1, 2], [3, 1], [4, 0]])
        b = copy.deepcopy(a)
        b['geometry']['coordinates'].reverse()
        self.assertTrue(v.same_structural_row(a, b))
        b['geometry']['coordinates'][1:3] = reversed(b['geometry']['coordinates'][1:3])
        self.assertFalse(v.same_structural_row(a, b))

    def test_ring_rotations_direction_and_hole_permutation(self):
        shell = [[0, 0], [9, 0], [9, 9], [0, 9], [0, 0]]
        holes = [[[1, 1], [2, 1], [2, 2], [1, 1]], [[4, 4], [5, 4], [5, 5], [4, 4]]]
        a = row('Polygon', [shell] + holes)
        for offset in range(4):
            cycle = shell[:-1]
            rotated = cycle[offset:] + cycle[:offset]
            b = row('Polygon', [list(reversed(rotated + rotated[:1]))] + list(reversed(holes)))
            self.assertTrue(v.same_structural_row(a, b))
        self.assertFalse(v.same_structural_row(a, row('Polygon', [holes[0], shell, holes[1]])))

    def test_collection_and_multipart_permutation_preserve_duplicates(self):
        point = {'type': 'Point', 'coordinates': [1, 2]}
        line = {'type': 'LineString', 'coordinates': [[0, 0], [1, 2]]}
        a = {'geometry': {'type': 'GeometryCollection', 'geometries': [point, line, point]}}
        b = {'geometry': {'type': 'GeometryCollection', 'geometries': [line, point, point]}}
        self.assertTrue(v.same_structural_row(a, b))
        b['geometry']['geometries'].pop()
        self.assertFalse(v.same_structural_row(a, b))
        a = row('MultiLineString', [[[0, 0], [1, 2]], [[3, 4], [5, 6]]])
        b = row('MultiLineString', [[[5, 6], [3, 4]], [[1, 2], [0, 0]]])
        self.assertTrue(v.same_structural_row(a, b))

    def test_tiny_coordinate_change_is_rejected(self):
        a = row('Point', [1.0, 2.0])
        b = row('Point', [math.nextafter(1.0, 2.0), 2.0])
        self.assertFalse(v.same_structural_row(a, b))

    def test_numeric_representation_and_dimension_remain_exact(self):
        self.assertFalse(v.same_structural_row(row('Point', [0.0, 1.0]), row('Point', [-0.0, 1.0])))
        self.assertFalse(v.same_structural_row(row('Point', [1, 2]), row('Point', [1.0, 2.0])))
        self.assertFalse(v.same_structural_row(row('Point', [1, 2]), row('Point', [1, 2, 0])))

    def test_extra_collinear_or_repeated_vertex_is_rejected(self):
        a = row('LineString', [[0, 0], [2, 0]])
        for points in ([[0, 0], [1, 0], [2, 0]], [[0, 0], [0, 0], [2, 0]]):
            self.assertFalse(v.same_structural_row(a, row('LineString', points)))
        shell = [[0, 0], [2, 0], [2, 2], [0, 0]]
        self.assertFalse(v.same_structural_row(row('Polygon', [shell]), row('Polygon', [shell[:-1] + [[0, 0], [0, 0]]])))

    def test_member_multiplicity_and_type_are_preserved(self):
        self.assertFalse(v.same_structural_row(row('MultiPoint', [[1, 2]]), row('MultiPoint', [[1, 2], [1, 2]])))
        self.assertFalse(v.same_structural_row(row('Point', [1, 2]), row('MultiPoint', [[1, 2]])))
        self.assertFalse(v.same_structural_row(row('LineString', [[0, 0], [1, 2]]), row('MultiLineString', [[[0, 0], [1, 2]]])))

    def test_metadata_and_extra_geometry_fields_remain_exact(self):
        a = row('MultiPoint', [[1, 2], [3, 4]])
        for key, value in [('id', 'other'), ('kind', 'shared-edge'), ('dateline', True), ('components', ['b', 'a'])]:
            b = copy.deepcopy(a)
            b[key] = value
            self.assertFalse(v.same_structural_row(a, b))
        b = copy.deepcopy(a)
        b['geometry']['bbox'] = [1, 2, 3, 4]
        self.assertFalse(v.same_structural_row(a, b))

    def test_roster_count_and_order_are_exact(self):
        a, b = row('Point', [1, 2]), row('Point', [3, 4])
        with self.assertRaisesRegex(ValueError, 'different complete row count'):
            v.require_exact_reconstruction([a, b], [a], 'changed')
        with self.assertRaisesRegex(ValueError, 'changed'):
            v.require_exact_reconstruction([a, b], [b, a], 'changed')

    def test_positive_area_or_ring_closure_cannot_disappear(self):
        a = row('Polygon', [[[0, 0], [1e-12, 0], [0, 1e-12], [0, 0]]])
        self.assertFalse(v.same_structural_row(a, row('LineString', [[0, 0], [1e-12, 0]])))
        b = copy.deepcopy(a)
        b['geometry']['coordinates'][0][-1] = [1e-20, 0]
        with self.assertRaisesRegex(ValueError, 'closure'):
            v.same_structural_row(a, b)


if __name__ == '__main__':
    unittest.main(verbosity=2)
