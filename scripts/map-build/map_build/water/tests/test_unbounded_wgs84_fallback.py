import math, unittest
import numpy as np
from scipy.spatial import cKDTree
from map_build.water import shared_nearest as s


def run(lat, lon, qlat, qlon):
    d = {'lat': np.asarray(lat, dtype=float), 'lon': np.asarray(lon, dtype=float)}
    d['mids'] = s.unit(d['lat'], d['lon'])
    t = cKDTree(d['mids'])
    p = s.unit([qlat], [qlon])[0]

    class Track:
        n = t.n

        def __init__(self):
            self.max_k = 0

        def query(self, *args, **kwargs):
            self.max_k = max(self.max_k, kwargs['k'])
            return t.query(*args, **kwargs)

    t2 = Track()
    got = s.exact_minimum_by_ordered_chord(p, qlon, qlat, d, t2)
    expect = float(
        np.min(
            s.geodesic_distances(
                np.full(len(lat), qlon), np.full(len(lat), qlat), d['lon'], d['lat']
            )
        )
    )
    return got, expect, t2.max_k


class Tests(unittest.TestCase):
    def test_more_than_one_block_of_identical_shores(self):
        got, expected, k = run([20] * 10001, [30] * 10001, 20, 30)
        self.assertEqual(got, expected)
        self.assertLessEqual(k, 4097)

    def test_more_than_old_limit_is_complete_and_tie_priority_is_preserved(self):
        n = 100_005
        data = {'lat': np.zeros(n), 'lon': np.zeros(n)}
        data['mids'] = s.unit(data['lat'], data['lon'])
        tree = cKDTree(data['mids'])
        pairs = [('first', 17, 1), ('second', 18, 2)]
        indexes = {17: (data, tree), 18: (data, tree)}
        codes, stats = s.classify_wgs84(
            np.array([0.0]), np.array([0.0]), (0, 360, 0, 180), 360, 180, 1.0, pairs, 0.01, indexes
        )
        self.assertEqual(codes.tolist(), [1])
        self.assertEqual(stats['exact'], 1)

    def test_tied_chord_order_can_change_between_prefix_queries(self):
        lat = np.zeros(33)
        lon = np.full(33, 10.0)
        lat[16] = 10.0
        lon[16] = 0.0
        data = {'lat': lat, 'lon': lon}
        data['mids'] = s.unit(lat, lon)
        point = s.unit([0.0], [0.0])[0]
        chord = float(np.linalg.norm(data['mids'][0] - point))

        class TiedTree:
            n = 33

            def query(self, point, k, workers):
                order = list(range(33)) if k < 33 else [16] + list(range(16)) + list(range(17, 33))
                return np.full(k, chord), np.asarray(order[:k])

        got = s.exact_minimum_by_ordered_chord(point, 0.0, 0.0, data, TiedTree())
        expected = float(s.geodesic_distances([0.0], [0.0], [0.0], [10.0])[0])
        self.assertAlmostEqual(got, expected, places=6)

    def test_antipodal_near_ties_and_poles(self):
        rng = np.random.default_rng(77)
        for qlat, qlon in [(0, 179.999999), (89.999999, -179.9), (-89.999999, 20), (0, 0)]:
            lat = qlat + rng.normal(0, 1e-8, 9000)
            lon = qlon + rng.normal(0, 1e-8, 9000)
            lat = np.clip(lat, -90, 90)
            lon = (lon + 180) % 360 - 180
            lat[-1] = -qlat
            lon[-1] = (qlon + 360) % 360 - 180
            got, expected, k = run(lat, lon, qlat, qlon)
            self.assertAlmostEqual(got, expected, places=6)

    def test_mixed_global_population(self):
        rng = np.random.default_rng(89)
        lat = np.r_[np.full(9000, 4.0), rng.uniform(-90, 90, 6000)]
        lon = np.r_[np.full(9000, 8.0), rng.uniform(-180, 180, 6000)]
        got, expected, k = run(lat, lon, 4, 8)
        self.assertEqual(got, expected)


if __name__ == '__main__':
    unittest.main()
