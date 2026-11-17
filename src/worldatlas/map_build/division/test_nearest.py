"""Compare the common distance kernels with complete independent WGS84 searches."""

import unittest
import numpy as np
from pyproj import Geod

from worldatlas.map_build.water import shared_nearest as nearest
from worldatlas.map_build.water.rectangle_nearest import classify


class StrictNearest(unittest.TestCase):
    bounds = (0, 360, 0, 180)

    def references(self, latitude, longitude, owners):
        centers = dict(
            lat=np.asarray(latitude, dtype=float),
            lon=np.asarray(longitude, dtype=float),
            category=np.asarray(owners, dtype=np.uint32),
        )
        centers["mids"] = nearest.unit(centers["lat"], centers["lon"])
        pairs = [(owner, owner, owner) for owner in dict.fromkeys(owners)]
        return centers, pairs, nearest.make_indexes(centers, pairs)

    def query(self, latitude, longitude, pairs, indexes, **kwargs):
        return nearest.classify_wgs84(
            latitude, longitude, self.bounds, 360, 180, 1, pairs, indexes, **kwargs
        )

    def test_random_queries_match_all_reference_distances(self):
        rng = np.random.default_rng(1927)
        centers, pairs, indexes = self.references(
            rng.uniform(-70, 70, 72), rng.uniform(-180, 180, 72), [101, 807, 99] * 24
        )
        lat, lon = rng.uniform(-75, 75, 160), rng.uniform(-180, 180, 160)
        actual, stats = self.query(lat, lon, pairs, indexes)
        expected = []
        geod = Geod(ellps="WGS84")
        for y, x in zip(lat, lon):
            distance = np.asarray(
                geod.inv(
                    np.full(72, x), np.full(72, y), centers["lon"], centers["lat"]
                )[2]
            )
            minima = [
                distance[centers["category"] == owner].min() for owner, _, _ in pairs
            ]
            expected.append(pairs[int(np.argmin(minima))][0])
        self.assertEqual(actual.tolist(), expected)
        self.assertEqual(stats["bounded"] + stats["exact"], len(lat))

    def test_exact_equality_uses_supplied_order(self):
        _, pairs, indexes = self.references([0, 0], [-1, 1], [807, 101])
        self.assertEqual(self.query([0], [0], pairs, indexes)[0].tolist(), [807])

    def test_a_smaller_distance_wins_even_when_difference_is_tiny(self):
        _, pairs, indexes = self.references([0, 0], [-1, 1], [807, 101])
        answer, _ = self.query([0], [1e-11], pairs, indexes)
        self.assertEqual(answer.tolist(), [101])

    def test_coastal_limit_includes_exact_threshold(self):
        _, pairs, indexes = self.references([0], [1], [101])
        limit = Geod(ellps="WGS84").inv(0, 0, 1, 0)[2]
        self.assertEqual(
            self.query([0], [0], pairs, indexes, band=limit)[0].tolist(), [101]
        )
        self.assertEqual(
            self.query([0], [0], pairs, indexes, band=limit - 1e-6)[0].tolist(), [0]
        )

    def test_rectangle_acceleration_preserves_point_results(self):
        _, pairs, indexes = self.references(
            [12, -13, 20], [-30, 60, 170], [101, 807, 99]
        )
        mask = np.ones((10, 15), dtype=bool)
        mask[::2, ::3] = False

        def points(lat, lon):
            codes, stats = self.query(lat, lon, pairs, indexes)
            return codes, stats["bounded"], stats["exact"]

        actual, stats = classify(
            mask, 170, 80, self.bounds, 360, 180, 1, pairs, indexes, points
        )
        y, x = np.nonzero(mask)
        expected, _ = self.query(
            90 - (80 + y + 0.5), -180 + (170 + x + 0.5), pairs, indexes
        )
        self.assertEqual(actual[mask].tolist(), expected.tolist())
        self.assertTrue(np.all(actual[~mask] == 0))
        self.assertEqual(stats["bounded_cells"] + stats["exact_cells"], int(mask.sum()))
