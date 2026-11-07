import unittest
from unittest.mock import patch

from geodesic_line import GEOD, GeodesicLine
from klukhor_full_gap_splice import (
    assemble_splice_coordinates, nearest_source_location, require_exact_join,
    validated_splice_measures,
)
from klukhor_gap_elevation import paired_sample_points


class KlukhorGeodesicProjectionTests(unittest.TestCase):
    def setUp(self):
        self.source = [(1.0, 60.0), (1.0, 60.01), (30.0, 60.01),
                       (30.0, 60.6), (0.0, 60.6)]
        self.query = (0.0, 60.0)

    def test_splice_endpoint_uses_wgs84_nearest_not_lonlat_projection(self):
        result = nearest_source_location(self.source, self.query)
        planar_choice = (0.0, 60.6)
        self.assertAlmostEqual(result['point'][0], 1.0, places=6)
        self.assertLess(result['distance_m'], GEOD.inv(*self.query, *planar_choice)[2])
        self.assertFalse(result['ambiguous'])

    def test_elevation_pairing_uses_wgs84_nearest_source_location(self):
        current_points, bridge_points = paired_sample_points(
            self.source, [self.query, (0.0, 60.01)], interval_m=1000)
        self.assertEqual(len(current_points), len(bridge_points))
        self.assertGreaterEqual(len(current_points), 1)
        self.assertAlmostEqual(current_points[0][0], 1.0, places=6)

    def test_ambiguous_splice_location_fails_closed(self):
        source = [(-0.01, 0.0), (0.01, 0.0), (0.01, 0.01), (-0.01, 0.01)]
        with self.assertRaisesRegex(ValueError, 'ambiguous WGS84'):
            nearest_source_location(source, (0.0, 0.005))

    def test_splice_requires_exact_topological_joins_and_forward_order(self):
        class Point:
            def __init__(self, x, y): self.x, self.y = x, y

        class SourceGeometry:
            def distance(self, point):
                return 0.0 if point.y == 0.0 else abs(point.y)
            def project(self, point): return point.x

        class StableLine:
            def __init__(self, coords): pass
            def closest(self, point):
                return {'ambiguous': False, 'station_m': point[0], 'distance_m': 0.0,
                        'point': point}

        source_coords = [(0.0, 0.0), (1.0, 0.0)]
        geometry = SourceGeometry()
        with patch('klukhor_full_gap_splice.GeodesicLine', StableLine):
            start_m, end_m, nearest = validated_splice_measures(
                geometry, source_coords, Point(.2, 0), Point(.8, 0))
            self.assertEqual((start_m, end_m), (.2, .8))
            self.assertFalse(nearest['ambiguous'])
            with self.assertRaisesRegex(ValueError, 'not topologically'):
                validated_splice_measures(geometry, source_coords, Point(.2, 0), Point(.8, 1e-9))
            with self.assertRaisesRegex(ValueError, 'not ordered'):
                validated_splice_measures(geometry, source_coords, Point(.9, 0), Point(.2, 0))

    def test_splice_interface_join_does_not_snap(self):
        require_exact_join((1.0, 2.0), [1.0, 2.0], 'mismatch')
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            require_exact_join((1.0, 2.0), (1.0, 2.000000000001), 'mismatch')

    def test_splice_assembly_preserves_suffix_and_exact_junctions(self):
        prefix = [(0, 0), (1, 0)]
        interface = [(1, 0), (2, 0)]
        bridge = [(2, 0), (3, 0), (4, 0)]
        suffix = [(4, 0), (5, 0), (6, 0)]
        cut, full = assemble_splice_coordinates(prefix, interface, bridge, suffix)
        self.assertEqual(cut, [(1, 0), (2, 0), (3, 0), (4, 0)])
        self.assertEqual(full, [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0)])
        with self.assertRaisesRegex(ValueError, 'bridge/suffix'):
            assemble_splice_coordinates(prefix, interface, bridge, [(4, 1), (5, 0)])


if __name__ == '__main__':
    unittest.main()
