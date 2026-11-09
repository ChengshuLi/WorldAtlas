import unittest
import sqlite3
import tempfile
from pathlib import Path

import numpy as np
from pyproj import Geod
from scipy.spatial import cKDTree

from hints import (_xyz, lowest_code_for_min_distance, wgs84_nearest_distances,
                   wgs84_nearest_categories, inventory)


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

    def test_pooled_categories_match_six_independent_wgs84_searches(self):
        rng = np.random.default_rng(673)
        lat = rng.uniform(-89.9, 89.9, 240)
        lon = rng.uniform(-180, 180, 240)
        codes = np.tile(np.arange(17, 23), 40)
        qlat = np.r_[rng.uniform(-90, 90, 150), 89.99, -89.99, 0]
        qlon = np.r_[rng.uniform(-180, 180, 150), -180, 180, 0]
        expected = []
        for code in range(17, 23):
            selected = codes == code
            tree = cKDTree(_xyz(lat[selected], lon[selected]))
            expected.append(wgs84_nearest_distances(
                tree, lat[selected], lon[selected], qlat, qlon))
        expected = lowest_code_for_min_distance(np.stack(expected, axis=1), range(17, 23))
        actual = wgs84_nearest_categories(
            cKDTree(_xyz(lat, lon)), lat, lon, codes, qlat, qlon)
        np.testing.assert_array_equal(actual, expected)

    def test_pooled_ties_and_large_valid_neighborhood(self):
        lat = np.zeros(100001);lon = lat.copy()
        codes = np.full(len(lat), 22);codes[-1] = 17
        actual = wgs84_nearest_categories(
            cKDTree(_xyz(lat, lon)), lat, lon, codes, [0], [0])
        np.testing.assert_array_equal(actual, [17])

    def test_pooled_invalid_inputs_and_empty_query(self):
        tree = cKDTree(_xyz([0], [0]))
        for codes, qlat in [([0], [0]), ([17], [91]), ([17.5], [0])]:
            with self.assertRaises(ValueError):
                wgs84_nearest_categories(tree, [0], [0], codes, qlat, [0])
        self.assertEqual(len(wgs84_nearest_categories(tree, [0], [0], [17], [], [])), 0)


class InventoryTests(unittest.TestCase):
    def test_first_actual_cell_survives_repeated_roots_across_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td);height = 100003
            rows = np.arange(height + 1, dtype='<u4')
            runs = np.tile(np.array([2, 5, 7], dtype='<u4'), (height, 1))
            runs[1, 2] = 99;runs[100000, 2] = 8
            rows.tofile(root / 'rows');runs.tofile(root / 'runs')
            count = inventory(root / 'rows', root / 'runs', [99], 10, height, root / 'inventory')
            self.assertEqual(count, 2)
            with sqlite3.connect(root / 'inventory') as db:
                self.assertEqual(db.execute('SELECT * FROM roots ORDER BY id').fetchall(),
                                 [(7, 0, 2), (8, 100000, 2)])

    def test_overlap_across_input_block_boundary_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td);n = 100001
            runs = np.empty((n, 3), dtype='<u4');runs[:, 0] = np.arange(n) * 2
            runs[:, 1] = runs[:, 0] + 1;runs[:, 2] = 7
            runs[-1, 0] = runs[-2, 1] - 1
            np.array([0, n], dtype='<u4').tofile(root / 'rows');runs.tofile(root / 'runs')
            with self.assertRaisesRegex(ValueError, 'invalid component row'):
                inventory(root / 'rows', root / 'runs', [7], 300000, 1, root / 'inventory')


if __name__ == '__main__':
    unittest.main()
