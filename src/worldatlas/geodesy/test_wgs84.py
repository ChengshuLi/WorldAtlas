"""Test distances and shortest-path sampling on the WGS84 ellipsoid."""

from math import pi
import unittest

from worldatlas.geodesy.wgs84 import GEOD, geodesic, geodesic_distance


class GeodesicTests(unittest.TestCase):
    """Cover segment spacing, longitude wrapping, and invalid inputs."""

    def test_geodesic_distance_on_the_equator(self):
        self.assertAlmostEqual(geodesic_distance((0, 0), (1, 0)), pi * GEOD.a / 180, places=6)
        self.assertEqual(geodesic_distance((0, 0), (0, 0)), 0)

    def test_geodesic_distance_rejects_invalid_latitude(self):
        with self.assertRaisesRegex(ValueError, "invalid WGS84 coordinates"):
            geodesic_distance((0, 0), (1, 91))

    def test_samples_the_short_geodesic_across_the_antimeridian(self):
        first, last = (179.0, 10.0), (-179.0, 10.0)
        path = geodesic(first, last, 50_000)
        self.assertEqual((path[0], path[-1]), (first, last))
        lengths = [GEOD.inv(*start, *end)[2] for start, end in zip(path, path[1:])]
        self.assertLessEqual(max(lengths), 50_000)
        self.assertAlmostEqual(sum(lengths), GEOD.inv(*first, *last)[2], places=6)

    def test_rejects_invalid_spacing(self):
        for spacing in (0, -1, float("inf"), float("nan")):
            with self.subTest(spacing=spacing), self.assertRaisesRegex(ValueError, "spacing"):
                geodesic((0, 0), (1, 0), spacing)

    def test_rejects_coincident_and_invalid_endpoints(self):
        for end in ((0, 0), (1, 91)):
            with self.subTest(end=end), self.assertRaisesRegex(ValueError, "endpoints"):
                geodesic((0, 0), end, 50_000)
