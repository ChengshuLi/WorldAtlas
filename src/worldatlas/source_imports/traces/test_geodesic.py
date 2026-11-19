import unittest

from pyproj import Geod
from shapely.geometry import LineString

from worldatlas.source_imports.traces.geodesic import construct


class GeodesicTraceTests(unittest.TestCase):
    def test_keeps_every_control_point_and_limits_segment_spacing(self):
        points = [[10., 1.], [9., 0.], [8., -1.]]
        coordinates = construct(points, 1000)["coordinates"]
        self.assertEqual(coordinates[0], points[0])
        self.assertEqual(coordinates[-1], points[-1])
        positions = [coordinates.index(point) for point in points]
        self.assertEqual(positions, sorted(positions))
        geod = Geod(ellps="WGS84")
        for a, b in zip(coordinates, coordinates[1:]):
            self.assertLessEqual(geod.inv(*a, *b)[2], 1000.000001)
        for a, b, start, end in zip(points, points[1:], positions, positions[1:]):
            length = sum(geod.inv(*x, *y)[2] for x, y in
                         zip(coordinates[start:end], coordinates[start+1:end+1]))
            self.assertAlmostEqual(length, geod.inv(*a, *b)[2], places=6)

    def test_east_west_and_northward_sections_are_supported(self):
        points = [[0, 0], [2, 0], [2, 1]]
        coordinates = construct(points, 50000)["coordinates"]
        for point in points:
            self.assertIn(point, coordinates)
        self.assertTrue(all(p[1] == 0 for p in coordinates[:coordinates.index([2, 0])]))

    def test_long_geodesic_bows_toward_the_pole(self):
        coordinates = construct([[0, 50], [30, 50]], 100000)["coordinates"]
        self.assertGreater(max(p[1] for p in coordinates), 50)

    def test_short_segment_needs_no_intermediate_points(self):
        points = [[1, 1], [1.001, 1]]
        self.assertEqual(construct(points, 1000)["coordinates"], points)

    def test_rejects_invalid_coordinates(self):
        for points in ([], [[0, 0]], [[181, 1], [1, 0]], [[0, 91], [1, 0]],
                       [[0, 1], [float("nan"), 0]], [[0, 1], [True, 0]]):
            with self.subTest(points=points), self.assertRaises(ValueError):
                construct(points, 1000)

    def test_rejects_invalid_spacing(self):
        for value in (0, -1, True, float("inf"), float("nan"), None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                construct([[0, 1], [1, 0]], value)

    def test_rejects_coincident_points_and_retracing(self):
        with self.assertRaises(ValueError):
            construct([[0, 0], [0, 0]], 100000)
        with self.assertRaisesRegex(ValueError, "must not cross or retrace itself"):
            construct([[0, 0], [1, 1], [0, 0]], 100000)

    def test_accepts_a_geodesic_that_avoids_a_crossing_between_control_points(self):
        points = [[-60, 30], [60, 30], [0, 28], [0, 32]]
        self.assertFalse(LineString(points).is_simple)
        coordinates = construct(points, 100000)["coordinates"]
        self.assertTrue(LineString(coordinates).is_simple)
        self.assertEqual(coordinates[-1], points[-1])

    def test_rejects_a_crossing_introduced_by_the_geodesic(self):
        points = [[-60, 30], [60, 30], [0, 48], [0, 51]]
        self.assertTrue(LineString(points).is_simple)
        with self.assertRaisesRegex(ValueError, "must not cross or retrace itself"):
            construct(points, 100000)

    def test_longitude_seam_requires_split_geometry(self):
        with self.assertRaisesRegex(ValueError, "longitude-seam"):
            construct([[179, 1], [-179, 0]], 10000)
