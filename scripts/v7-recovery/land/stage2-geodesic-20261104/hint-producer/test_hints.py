import unittest

import numpy as np
from pyproj import Geod
from scipy.spatial import cKDTree

from hints import _xyz, lowest_code_for_min_distance, wgs84_nearest_distances


class Wgs84HintDistanceTests(unittest.TestCase):
    def test_conservative_index_matches_exhaustive_wgs84(self):
        reps = np.array([
            [179.9, 83.0], [-179.8, 83.0], [0.0, 0.0], [90.0, 45.0],
            [-90.0, -45.0], [35.0, 70.0], [34.8, 69.9], [35.2, 70.1],
        ])
        queries = np.array([
            [180.0, 83.0], [34.9, 70.0], [0.0, 0.0], [45.0, 89.0],
        ])
        tree = cKDTree(_xyz(reps[:, 1], reps[:, 0]))
        actual = wgs84_nearest_distances(
            tree, reps[:, 1], reps[:, 0], queries[:, 1], queries[:, 0])
        geod = Geod(ellps='WGS84')
        expected = []
        for lon, lat in queries:
            expected.append(min(
                geod.inv(lon, lat, rlon, rlat)[2] for rlon, rlat in reps))
        np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-6)

    def test_invalid_queries_fail_closed(self):
        reps = np.array([[0.0, 0.0]])
        tree = cKDTree(_xyz(reps[:, 1], reps[:, 0]))
        with self.assertRaises(ValueError):
            wgs84_nearest_distances(tree, reps[:, 1], reps[:, 0], [91.0], [0.0])

    def test_more_than_one_hundred_thousand_valid_candidates(self):
        reps = np.zeros((100001, 2), dtype=float)
        tree = cKDTree(_xyz(reps[:, 1], reps[:, 0]))
        result = wgs84_nearest_distances(tree, reps[:, 1], reps[:, 0], [0.0], [0.0])
        np.testing.assert_array_equal(result, [0.0])

    def test_exact_distance_tie_uses_lowest_code_even_when_unsorted(self):
        result = lowest_code_for_min_distance([[12.0, 4.0, 4.0]], [22, 41, 17])
        np.testing.assert_array_equal(result, [17])


if __name__ == '__main__':
    unittest.main()
