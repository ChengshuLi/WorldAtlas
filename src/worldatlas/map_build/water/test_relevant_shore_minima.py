"""Exact fallback excludes a class only after a conservative distance proof."""

from worldatlas.geodesy.wgs84 import unit_sphere
from worldatlas.map_build.water.test_helpers import index_present
import unittest
from unittest.mock import patch
import numpy as np
from pyproj import Geod
from worldatlas.map_build.water import shared_nearest as s

REFERENCE_GEOD = Geod(ellps="WGS84")


class RelevantMinimaTest(unittest.TestCase):
    (width, height, step) = (131072, 65536, 360 / 131072)
    owners = [17, 18, 19]

    def indexes(self, lat, lon, categories):
        (lat, lon) = (np.asarray(lat), np.asarray(lon))
        return index_present(
            {
                "lat": lat,
                "lon": lon,
                "mids": unit_sphere(lat, lon),
                "category": np.asarray(categories),
            },
            self.owners,
        )

    def classify(self, lat, lon, indexes, **kwargs):
        return s.classify_wgs84(
            lat,
            lon,
            (0, self.width, 0, self.height),
            self.width,
            self.height,
            self.step,
            self.owners,
            indexes,
            **kwargs,
        )

    def test_near_tie_excludes_distant_class_with_or_without_band(self):
        east = REFERENCE_GEOD.fwd(0.0, 0.0, 90.0, 10000.0)
        west = REFERENCE_GEOD.fwd(0.0, 0.0, -90.0, 10000.0)
        indexes = self.indexes(
            [east[1], west[1], 45.0], [east[0], west[0], 120.0], [17, 18, 19]
        )
        for kwargs in ({}, {"band": 22224.0}):
            with patch.object(
                s,
                "exact_minima_by_ordered_chord",
                wraps=s.exact_minima_by_ordered_chord,
            ) as exact:
                (result, stats) = self.classify([0.0], [0.0], indexes, **kwargs)
            self.assertEqual(result.tolist(), [17])
            self.assertEqual(stats["exact"], 1)
            self.assertEqual(len(exact.call_args_list), 2)
            self.assertTrue(
                all(
                    (
                        call.args[3] is not indexes[19][0]
                        for call in exact.call_args_list
                    )
                )
            )

    def test_outside_band_retains_candidate_and_threshold_checks(self):
        for distance in (22224.02, 22224.0):
            near = REFERENCE_GEOD.fwd(0.0, 0.0, 90.0, distance)
            indexes = self.indexes(
                [near[1], 40.0, -50.0], [near[0], 100.0, -140.0], [17, 18, 19]
            )
            with patch.object(
                s,
                "exact_minima_by_ordered_chord",
                wraps=s.exact_minima_by_ordered_chord,
            ) as exact:
                result, stats = self.classify([0.0], [0.0], indexes, band=22224.0)
                computed = REFERENCE_GEOD.inv(0.0, 0.0, near[0], near[1])[2]
                self.assertEqual(result.tolist(), [17 if computed <= 22224.0 else 0])
            self.assertEqual(len(exact.call_args_list), 1)

    def test_matches_complete_search_near_band_and_between_classes(self):
        rng = np.random.default_rng(654818)
        for latitude, longitude in ((0.0, 0.0), (72.0, 179.95), (-85.0, -179.95)):
            query_lat = latitude + rng.uniform(-0.001, 0.001, 80)
            query_lon = (longitude + rng.uniform(-0.01, 0.01, 80) + 180) % 360 - 180
            bearings = np.tile([90.0, -90.0, 90.0], 12)
            distances = np.tile([22224.0, 22224.01, 2000000.0], 12)
            (shore_lon, shore_lat, _) = REFERENCE_GEOD.fwd(
                np.full(36, longitude),
                np.full(36, latitude),
                bearings,
                distances + rng.uniform(-100.0, 100.0, 36),
            )
            categories = np.tile([17, 18, 19], 12)
            indexes = self.indexes(shore_lat, shore_lon, categories)
            exact = np.column_stack(
                [
                    np.min(
                        REFERENCE_GEOD.inv(
                            query_lon[:, None].repeat(12, axis=1).ravel(),
                            query_lat[:, None].repeat(12, axis=1).ravel(),
                            np.tile(shore_lon[categories == code], 80),
                            np.tile(shore_lat[categories == code], 80),
                        )[2].reshape(80, 12),
                        axis=1,
                    )
                    for code in self.owners
                ]
            )
            minimum = exact.min(axis=1)
            expected = np.asarray(self.owners)[np.argmin(exact, axis=1)]
            for band in (None, 22224.0):
                reference = expected.copy()
                if band is not None:
                    reference[minimum > band] = 0
                (result, _) = self.classify(query_lat, query_lon, indexes, band=band)
                np.testing.assert_array_equal(result, reference)


if __name__ == "__main__":
    unittest.main()
