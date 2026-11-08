import math
import random
import unittest
from unittest.mock import patch

from osgeo import ogr

from extract_seavox_feature import coordinate_geometry, geojson_coordinate, canonical_hash
from seavox_coordinates import ring_coordinates, geometry_coordinates
import seavox_coordinates


class CoordinateTests(unittest.TestCase):
    def test_cleanup_signed_zero_and_binary_halfway_edges_match_scalar(self):
        values = [-0.0, 0.0, -180.0, 180.0, 90.0, -90.0, 1e-300, -1e-300,
            1.000000000000001, 179.99999999999997, -179.99999999999997,
            0.123456789999999, -0.123456789999999, 12.345670000000001,
            1.0987624561475371e-14, -1.2518996461569245e-14, 5.852103697365338e-14,
            math.nextafter(1.234567890123456, math.inf),
            math.nextafter(1.234567890123456, -math.inf)]
        values += [value / 65536 for value in range(-1000, 1001)]
        expected = [[geojson_coordinate(value), 0.0] for value in values]
        self.assertEqual(canonical_hash(ring_coordinates([(value, 0.0) for value in values], 2)),
                         canonical_hash(expected))

    def test_random_geographic_values_match_scalar_exactly(self):
        randomizer = random.Random(20261108)
        points = [(randomizer.uniform(-180, 180), randomizer.uniform(-90, 90)) for _ in range(50000)]
        expected = [[geojson_coordinate(value) for value in point] for point in points]
        self.assertEqual(canonical_hash(ring_coordinates(points, 2)), canonical_hash(expected))

    def test_scientific_notation_and_near_decimal_ties_match_scalar(self):
        randomizer = random.Random(20261108)
        values = [(-1 if randomizer.random() < .5 else 1) * 10 ** randomizer.uniform(-18, 2)
                  for _ in range(10000)]
        values += [(randomizer.randrange(-10**16, 10**16) + .5) * 1e-15 for _ in range(10000)]
        expected = [[geojson_coordinate(value), 0.0] for value in values]
        self.assertEqual(canonical_hash(ring_coordinates([(value, 0.0) for value in values], 2)),
                         canonical_hash(expected))

    def test_unsupported_values_fall_back_without_mutating_input(self):
        for value in (1000.0, float('inf'), float('nan')):
            points = [[1.1234567891234567, 1.0], [value, 2.0]]
            first = points[0][:]
            self.assertIsNone(ring_coordinates(points, 2))
            self.assertEqual(points[0], first)

    def test_polygons_holes_multipolygons_and_3d_match(self):
        for wkt in ('POLYGON ((0 0, 2.000000000000001 0, 2 2, 0 0),(0.1 0.1,0.2 0.1,0.1 0.2,0.1 0.1))',
                    'MULTIPOLYGON (((-179.99999999999997 0,-179 1,-178 0,-179.99999999999997 0)))',
                    'POLYGON Z ((1 1 2.000000000000001,2 1 3,1 2 4,1 1 2.000000000000001))'):
            geometry = ogr.CreateGeometryFromWkt(wkt)
            self.assertEqual(canonical_hash(coordinate_geometry(geometry, geometry_coordinates)),
                             canonical_hash(coordinate_geometry(geometry)))

    def test_empty_ring(self):
        self.assertEqual(ring_coordinates([], 2), [])

    def test_many_small_polygons_share_one_array_conversion(self):
        geometry = ogr.Geometry(ogr.wkbMultiPolygon)
        for offset in range(100):
            geometry.AddGeometry(ogr.CreateGeometryFromWkt(
                f'POLYGON (({offset} 0,{offset + .1} 0,{offset} .1,{offset} 0))'))
        with patch.object(seavox_coordinates, 'ring_coordinates', wraps=ring_coordinates) as convert:
            candidate = geometry_coordinates(geometry)
        self.assertEqual(convert.call_count, 1)
        self.assertEqual(canonical_hash(candidate), canonical_hash(coordinate_geometry(geometry)))


if __name__ == '__main__':
    unittest.main()
