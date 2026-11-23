from worldatlas.map_build.water.test_helpers import classify_points
from worldatlas.geodesy.wgs84 import unit_sphere

"""Independent dense/brute-force checks for sparse shore execution."""
import unittest
import numpy as np
from worldatlas.geodesy.wgs84 import geodesic_distances
from worldatlas.map_build.water import shared_nearest as shore


class SparseShoreTests(unittest.TestCase):
    def test_batch_minima_match_complete_wgs84_distances(self):
        rng = np.random.default_rng(98831)
        lat = rng.uniform(-89.9, 89.9, 300)
        lon = rng.uniform(-180, 180, 300)
        data = {
            "lat": lat,
            "lon": lon,
            "mids": unit_sphere(lat, lon),
            "category": np.full(len(lat), 17, dtype=np.uint8),
        }
        (_, tree) = shore.make_indexes(data, [17])[17]
        qlat = np.r_[rng.uniform(-90, 90, 50), 90.0, -90.0, 0.0, 0.0]
        qlon = np.r_[rng.uniform(-180, 180, 50), 180.0, -180.0, 180.0, -180.0]
        expected = np.array(
            [
                geodesic_distances(
                    np.full(len(lat), x), np.full(len(lat), y), lon, lat
                ).min()
                for (y, x) in zip(qlat, qlon)
            ]
        )
        actual = shore.exact_minima_by_ordered_chord(
            unit_sphere(qlat, qlon), qlon, qlat, data, tree
        )
        np.testing.assert_array_equal(actual, expected)

    def test_wide_equal_chord_prefix_does_not_cap_candidates(self):
        lat = np.r_[np.zeros(5000), 1.003]
        lon = np.r_[np.ones(5000), 0.0]
        data = {
            "lat": lat,
            "lon": lon,
            "mids": unit_sphere(lat, lon),
            "category": np.full(len(lat), 17, dtype=np.uint8),
        }
        (_, tree) = shore.make_indexes(data, [17])[17]
        expected = geodesic_distances([0.0], [0.0], [0.0], [1.003])[0]
        actual = shore.exact_minima_by_ordered_chord(
            unit_sphere([0.0], [0.0]), np.array([0.0]), np.array([0.0]), data, tree
        )
        self.assertEqual(actual[0], expected)

    def test_spherical_nearest_class_is_not_assumed_wgs84_winner(self):
        owners = [17, 18]
        (lat, lon) = (np.array([0.0, 1.003]), np.array([1.0, 0.0]))
        centers = {
            "lat": lat,
            "lon": lon,
            "mids": unit_sphere(lat, lon),
            "category": np.array([17, 18], dtype=np.uint8),
        }
        indexes = shore.make_indexes(centers, owners)
        (codes, _, exact) = classify_points(
            np.array([0.0]),
            np.array([0.0]),
            (0, 360, 0, 180),
            360,
            180,
            1.0,
            owners,
            indexes,
        )
        self.assertEqual(codes.tolist(), [18])
        self.assertEqual(exact, 1)

    def test_real_witnesses_bound_unlimited_searches(self):
        owners = [17, 18, 19]
        lat, lon = np.array([1.0, 2.0, 3.0]), np.array([1.0, 2.0, 3.0])
        centers = dict(
            lat=lat, lon=lon, mids=unit_sphere(lat, lon), category=np.array([17, 18, 19])
        )
        indexes = shore.make_indexes(centers, owners)
        checked = []

        class BoundedTree:
            def __init__(self, tree):
                self.tree = tree

            def query(self, *args, **kwargs):
                checked.append(kwargs.get("distance_upper_bound"))
                return self.tree.query(*args, **kwargs)

        for code, (data, tree) in list(indexes.items()):
            indexes[code] = (data, BoundedTree(tree))
        q = np.zeros(20)
        lower, best, upper = shore.nearest_class_bounds(
            q, q, unit_sphere(q, q), owners, indexes
        )
        self.assertEqual(len(checked), 3)
        self.assertTrue(all(0 < limit < 0.1 for limit in checked))
        self.assertTrue(np.all(np.isfinite(upper)))
        self.assertTrue(np.all(best == 0))


if __name__ == "__main__":
    unittest.main()
