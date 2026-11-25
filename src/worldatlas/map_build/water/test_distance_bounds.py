from worldatlas.geodesy.wgs84 import unit_sphere
from worldatlas.map_build.water.test_helpers import index_present
import unittest
from unittest.mock import patch

import numpy as np
from pyproj import Geod

from worldatlas.map_build.water import shared_nearest

REFERENCE_GEOD = Geod(ellps="WGS84")


class CoastalDistanceBoundTests(unittest.TestCase):
    def test_empty_query_returns_empty_distance_arrays(self):
        empty = np.empty(0)
        centers = dict(lat=[0.0], lon=[0.0], category=np.array([17]),
                       mids=unit_sphere([0], [0]))
        owners = [17]
        indexes = index_present({k: np.asarray(v) for k, v in centers.items()}, owners)
        lower, best, upper = shared_nearest.nearest_class_bounds(
            empty, empty, np.empty((0, 3)), owners, indexes, upper_limit=22224,
        )
        self.assertEqual((lower.shape, best.shape, upper.shape), ((0, 1), (0,), (0,)))

    def test_shore_distance_paths_reject_failed_inverse_geodesics(self):
        latitude = longitude = np.array([0.0])
        points = unit_sphere(latitude, longitude)
        centers = dict(lat=latitude, lon=longitude, category=np.array([17]), mids=points)
        owners = [17]
        indexes = index_present(centers, owners)
        data, tree = indexes[17]
        with patch.object(shared_nearest, "geodesic_distances", return_value=np.array([np.nan])):
            with self.assertRaisesRegex(ValueError, "invalid inverse geodesic"):
                shared_nearest.nearest_class_bounds(
                    latitude, longitude, points, owners, indexes, upper_limit=22224,
                )
            with self.assertRaisesRegex(ValueError, "invalid inverse geodesic"):
                shared_nearest.exact_minima_by_ordered_chord(
                    points, longitude, latitude, data, tree,
                )
            with self.assertRaisesRegex(ValueError, "invalid inverse geodesic"):
                shared_nearest.scan_exact_minimum(points[0], 0.0, 0.0, data, 100)

    def test_band_search_keeps_a_proven_finite_bound_for_distant_shores(self):
        owners = [70000, 300]
        shore_lat = np.array([0.0, 0.2, 70.0, 72.0])
        shore_lon = np.array([0.0, 0.2, 40.0, 42.0])
        categories = np.array([70000, 70000, 300, 300])
        centers = dict(
            lat=shore_lat,
            lon=shore_lon,
            category=categories,
            mids=unit_sphere(shore_lat, shore_lon),
        )
        indexes = index_present(centers, owners)
        lat, lon = np.array([0.0, 0.1, 89.0]), np.array([0.0, 0.1, 120.0])
        lower, _, upper = shared_nearest.nearest_class_bounds(
            lat, lon, unit_sphere(lat, lon), owners, indexes, upper_limit=22224
        )
        for i in range(len(lat)):
            for col, code in enumerate(owners):
                take = categories == code
                exact = REFERENCE_GEOD.inv(
                    np.full(int(take.sum()), lon[i]),
                    np.full(int(take.sum()), lat[i]),
                    shore_lon[take],
                    shore_lat[take],
                )[2]
                self.assertLessEqual(lower[i, col], float(np.min(exact)))
        self.assertTrue(np.isfinite(lower).all())
        self.assertTrue(np.all(lower[2] > 22224))
        self.assertTrue(np.isinf(upper[2]))
