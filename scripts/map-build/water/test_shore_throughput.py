"""Independent dense/brute-force checks for sparse shore execution."""
import unittest
from unittest.mock import patch

import numpy as np

import shared_nearest as shore
from test_shared_nearest import rle


class SparseShoreTests(unittest.TestCase):
    def test_rle_centers_match_independent_dense_neighbor_oracle(self):
        rng = np.random.default_rng(117304)
        for case in range(100):
            width = int(rng.integers(8, 100))
            height = width // 2
            step = 360 / width
            physical = np.where(rng.random((height, width)) < rng.uniform(.01, .99), 1, 17)
            land = rng.integers(17, 23, (height, width))
            land[physical == 1] = 0
            x0 = int(rng.integers(-2 * width, 2 * width))
            x1 = x0 + (width if case % 5 == 0 else int(rng.integers(1, width + 1)))
            y0 = int(rng.integers(height))
            y1 = int(rng.integers(y0 + 1, height + 1))
            codes = rng.choice(np.arange(17, 23), int(rng.integers(1, 7)), replace=False).tolist()
            lats, lons, categories = [], [], []
            xs = np.arange(x0, x1)
            columns = xs % width
            for y in range(y0, y1):
                wet = (physical[y, (columns - 1) % width] == 1) | (physical[y, (columns + 1) % width] == 1)
                for ny in (y - 1, y + 1):
                    if 0 <= ny < height:
                        wet |= physical[ny, columns] == 1
                keep = wet & (physical[y, columns] == 17) & np.isin(land[y, columns], codes)
                chosen = xs[keep]
                lats.extend([90 - (y + .5) * step] * len(chosen))
                lons.extend(((-180 + (chosen + .5) * step + 180) % 360 - 180).tolist())
                categories.extend(land[y, columns[keep]].tolist())
            args = rle(physical), rle(land), (x0, x1, y0, y1), width, height, step, codes
            if not lats:
                with self.assertRaisesRegex(ValueError, 'no participant shorelines'):
                    shore.centers_for_crop(*args)
                continue
            result = shore.centers_for_crop(*args)
            lat, lon = np.array(lats), np.array(lons)
            np.testing.assert_array_equal(result['lat'], lat)
            np.testing.assert_array_equal(result['lon'], lon)
            np.testing.assert_array_equal(result['category'], categories)
            np.testing.assert_array_equal(result['mids'], shore.unit(lat, lon))

    def test_batch_minima_match_complete_wgs84_distances(self):
        rng = np.random.default_rng(98831)
        lat = rng.uniform(-89.9, 89.9, 300)
        lon = rng.uniform(-180, 180, 300)
        data = {'lat': lat, 'lon': lon, 'mids': shore.unit(lat, lon),
                'category': np.full(len(lat), 17, dtype=np.uint8)}
        _, tree = shore.make_indexes(data, [('a', 17, 1)])[17]
        qlat = np.r_[rng.uniform(-90, 90, 50), 90., -90., 0., 0.]
        qlon = np.r_[rng.uniform(-180, 180, 50), 180., -180., 180., -180.]
        expected = np.array([shore.geodesic_distances(np.full(len(lat), x), np.full(len(lat), y), lon, lat).min()
                             for y, x in zip(qlat, qlon)])
        actual = shore.exact_minima_by_ordered_chord(shore.unit(qlat, qlon), qlon, qlat, data, tree)
        np.testing.assert_array_equal(actual, expected)

    def test_wide_equal_chord_prefix_does_not_cap_candidates(self):
        # East is spherical-nearer, north is WGS84-nearer. Put north after
        # more than 4096 equal east candidates to force complete streaming.
        lat = np.r_[np.zeros(5000), 1.003]
        lon = np.r_[np.ones(5000), 0.]
        data = {'lat': lat, 'lon': lon, 'mids': shore.unit(lat, lon),
                'category': np.full(len(lat), 17, dtype=np.uint8)}
        _, tree = shore.make_indexes(data, [('a', 17, 1)])[17]
        expected = shore.geodesic_distances([0.], [0.], [0.], [1.003])[0]
        actual = shore.exact_minima_by_ordered_chord(shore.unit([0.], [0.]), np.array([0.]), np.array([0.]), data, tree)
        self.assertEqual(actual[0], expected)

    def test_spherical_nearest_class_is_not_assumed_wgs84_winner(self):
        pairs = [('east', 17, 1), ('north', 18, 2)]
        lat, lon = np.array([0., 1.003]), np.array([1., 0.])
        centers = {'lat': lat, 'lon': lon, 'mids': shore.unit(lat, lon),
                   'category': np.array([17, 18], dtype=np.uint8)}
        indexes = shore.make_indexes(centers, pairs)
        codes, _, exact = shore.classify(np.array([0.]), np.array([0.]),
                                         (0, 360, 0, 180), 360, 180, 1., pairs, 1e-5, indexes)
        self.assertEqual(codes.tolist(), [2])
        self.assertEqual(exact, 1)

    def test_class_bounds_use_only_one_inverse_per_query(self):
        pairs = [('a', 17, 1), ('b', 18, 2), ('c', 19, 3)]
        lat, lon = np.array([1., 2., 3.]), np.array([1., 2., 3.])
        centers = {'lat': lat, 'lon': lon, 'mids': shore.unit(lat, lon),
                   'category': np.array([17, 18, 19], dtype=np.uint8)}
        indexes = shore.make_indexes(centers, pairs)
        qlat, qlon = np.zeros(20), np.zeros(20)
        with patch.object(shore, 'geodesic_distances', wraps=shore.geodesic_distances) as inverse:
            shore.nearest_class_bounds(qlat, qlon, shore.unit(qlat, qlon), pairs, indexes)
        self.assertEqual(inverse.call_count, 1)
        self.assertEqual(len(inverse.call_args.args[0]), 20)


if __name__ == '__main__':
    unittest.main()
