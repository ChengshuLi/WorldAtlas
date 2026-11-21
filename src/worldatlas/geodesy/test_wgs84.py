"""Test distances and shortest-path sampling on the WGS84 ellipsoid."""

from math import pi
import unittest

import numpy as np
from pyproj import Geod

from worldatlas.geodesy.wgs84 import geodesic, geodesic_distance, geodesic_distances

REFERENCE_GEOD = Geod(ellps="WGS84")


class GeodesicTests(unittest.TestCase):
    """Cover segment spacing, longitude wrapping, and invalid inputs."""

    def test_geodesic_distance_on_the_equator(self):
        self.assertAlmostEqual(geodesic_distance((0, 0), (1, 0)), pi * REFERENCE_GEOD.a / 180, places=6)
        self.assertEqual(geodesic_distance((0, 0), (0, 0)), 0)

    def test_geodesic_distance_rejects_invalid_latitude(self):
        with self.assertRaisesRegex(ValueError, "invalid WGS84 coordinates"):
            geodesic_distance((0, 0), (1, 91))

    def test_batch_distances_pair_coordinates_and_repeat_a_fixed_target(self):
        lon = np.array([[179.0, 0.0], [3.0, -120.0]])
        lat = np.array([[10.0, 0.0], [90.0, -35.0]])
        targets = np.array([[-179.0, 1.0], [55.0, 60.0]])
        expected = REFERENCE_GEOD.inv(lon, lat, targets, np.full_like(lat, 10))[2]
        result = geodesic_distances(lon, lat, targets, 10)
        np.testing.assert_array_equal(result, expected)
        self.assertEqual(result.shape, (2, 2))

    def test_batch_distances_keep_scalar_singleton_and_empty_shapes(self):
        for shape in ((), (1,), (1, 1), (0, 2)):
            with self.subTest(shape=shape):
                result = geodesic_distances(np.zeros(shape), 0, 1, 0)
                self.assertEqual(result.shape, shape)
                self.assertEqual(result.dtype, np.float64)
                np.testing.assert_array_equal(result, np.full(shape, geodesic_distance((0, 0), (1, 0))))

    def test_batch_distances_preserve_invalid_results_and_reject_incompatible_shapes(self):
        self.assertTrue(np.isnan(geodesic_distances(0, [91], 1, 0)[0]))
        with self.assertRaises(ValueError):
            geodesic_distances([0, 1], 0, [1, 2, 3], 0)

    def test_samples_the_short_geodesic_across_the_antimeridian(self):
        first, last = (179.0, 10.0), (-179.0, 10.0)
        path = geodesic(first, last, 50_000)
        self.assertEqual((path[0], path[-1]), (first, last))
        lengths = [REFERENCE_GEOD.inv(*start, *end)[2] for start, end in zip(path, path[1:])]
        self.assertLessEqual(max(lengths), 50_000)
        self.assertAlmostEqual(sum(lengths), REFERENCE_GEOD.inv(*first, *last)[2], places=6)

    def test_rejects_invalid_spacing(self):
        for spacing in (0, -1, float("inf"), float("nan")):
            with self.subTest(spacing=spacing), self.assertRaisesRegex(ValueError, "spacing"):
                geodesic((0, 0), (1, 0), spacing)

    def test_rejects_coincident_and_invalid_endpoints(self):
        for end in ((0, 0), (1, 91)):
            with self.subTest(end=end), self.assertRaisesRegex(ValueError, "endpoints"):
                geodesic((0, 0), end, 50_000)
