import unittest

import numpy as np

from map_build.water import coastal_core, shared_nearest


class CoastalDistanceBoundTests(unittest.TestCase):
    def test_band_search_keeps_a_proven_finite_bound_for_distant_shores(self):
        pairs = [(81, 70000, 90000), (42, 300, 4321)]
        shore_lat = np.array([0., .2, 70., 72.])
        shore_lon = np.array([0., .2, 40., 42.])
        categories = np.array([70000, 70000, 300, 300])
        centers = dict(lat=shore_lat, lon=shore_lon, category=categories,
                       mids=shared_nearest.unit(shore_lat, shore_lon))
        indexes = coastal_core.index_present(centers, pairs)
        lat, lon = np.array([0., .1, 89.]), np.array([0., .1, 120.])
        lower, _, upper = shared_nearest.nearest_class_bounds(
            lat, lon, shared_nearest.unit(lat, lon), pairs, indexes, upper_limit=22224)
        for i in range(len(lat)):
            for col, (_, code, _) in enumerate(pairs):
                take = categories == code
                exact = shared_nearest.GEOD.inv(np.full(int(take.sum()), lon[i]),
                                               np.full(int(take.sum()), lat[i]),
                                               shore_lon[take], shore_lat[take])[2]
                self.assertLessEqual(lower[i, col], float(np.min(exact)))
        self.assertTrue(np.isfinite(lower).all())
        self.assertTrue(np.all(lower[2] > 22224))
        self.assertTrue(np.isinf(upper[2]))
