import math
import unittest

from osgeo import ogr

from build_seed import witness_boundary_ambiguous


class NumericalBoundaryGuard(unittest.TestCase):
    def test_coordinate_box_rejects_boundary_and_near_boundary(self):
        geometry = ogr.CreateGeometryFromWkt('POLYGON ((0 0, 2 0, 2 2, 0 2, 0 0))')
        for point, expected in [((1, 0), True), ((1, 5e-13), True),
                                ((1, 2e-12), False), ((1, 1), False)]:
            with self.subTest(point=point):
                self.assertEqual(witness_boundary_ambiguous(geometry, *point), expected)
        with self.assertRaises(ValueError):
            witness_boundary_ambiguous(geometry, float('nan'), 0)

    def test_high_longitude_threshold_is_conservative(self):
        geometry = ogr.CreateGeometryFromWkt('POLYGON ((179 0, 180 0, 180 2, 179 2, 179 0))')
        self.assertTrue(witness_boundary_ambiguous(geometry, math.nextafter(180 - 1e-12, math.inf), 1))
        self.assertFalse(witness_boundary_ambiguous(geometry, 180 - 2e-12, 1))

    def test_coordinate_box_rejects_a_point_near_a_diagonal_edge(self):
        geometry = ogr.CreateGeometryFromWkt('POLYGON ((0 0, 2 2, 0 2, 0 0))')
        self.assertTrue(witness_boundary_ambiguous(geometry, 1, 1 + 1.5e-12))


if __name__ == '__main__':
    unittest.main()
