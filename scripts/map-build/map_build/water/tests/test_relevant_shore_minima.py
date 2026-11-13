"""Exact fallback excludes a class only after a conservative distance proof."""
import unittest
from unittest.mock import patch

import numpy as np
from map_build.water import coastal_core as core
from map_build.water import shared_nearest as s


class RelevantMinimaTest(unittest.TestCase):
    width, height, step = 131072, 65536, 360 / 131072
    pairs = [(1, 17, 1), (2, 18, 2), (3, 19, 3)]

    def indexes(self, lat, lon, categories):
        lat, lon = np.asarray(lat), np.asarray(lon)
        return core.index_present({'lat': lat, 'lon': lon, 'mids': s.unit(lat, lon),
                                   'category': np.asarray(categories)}, self.pairs)

    def classify(self, lat, lon, indexes, **kwargs):
        return s.classify_wgs84(lat, lon, (0, self.width, 0, self.height),
                                self.width, self.height, self.step,
                                self.pairs, .00001, indexes, **kwargs)

    def test_near_tie_excludes_distant_class_with_or_without_band(self):
        east = s.GEOD.fwd(0., 0., 90., 10000.)
        west = s.GEOD.fwd(0., 0., -90., 10000.)
        indexes = self.indexes([east[1], west[1], 45.], [east[0], west[0], 120.], [17, 18, 19])
        for kwargs in ({}, {'band': 22224., 'bandtol': .000001}):
            with patch.object(s, 'exact_minima_by_ordered_chord', wraps=s.exact_minima_by_ordered_chord) as exact:
                result, stats = self.classify([0.], [0.], indexes, **kwargs)
            self.assertEqual(result.tolist(), [1])
            self.assertEqual(stats['exact'], 1)
            self.assertEqual(len(exact.call_args_list), 2)
            self.assertTrue(all(call.args[3] is not indexes[19][0] for call in exact.call_args_list))

    def test_outside_band_retains_candidate_and_threshold_checks(self):
        for distance in (22224.02, 22224.):
            near = s.GEOD.fwd(0., 0., 90., distance)
            indexes = self.indexes([near[1], 40., -50.], [near[0], 100., -140.], [17, 18, 19])
            with patch.object(s, 'exact_minima_by_ordered_chord', wraps=s.exact_minima_by_ordered_chord) as exact:
                if distance == 22224.:
                    with self.assertRaisesRegex(RuntimeError, 'band threshold numerically ambiguous'):
                        self.classify([0.], [0.], indexes, band=22224.)
                else:
                    result, stats = self.classify([0.], [0.], indexes, band=22224.)
                    self.assertEqual(result.tolist(), [0])
                    self.assertEqual(stats['exact'], 1)
            self.assertEqual(len(exact.call_args_list), 1)

    def test_matches_complete_search_near_band_and_between_classes(self):
        rng = np.random.default_rng(654818)
        for latitude, longitude in ((0., 0.), (72., 179.95), (-85., -179.95)):
            query_lat = latitude + rng.uniform(-.001, .001, 80)
            query_lon = ((longitude + rng.uniform(-.01, .01, 80) + 180) % 360) - 180
            bearings = np.tile([90., -90., 90.], 12)
            distances = np.tile([22224., 22224.01, 2000000.], 12)
            shore_lon, shore_lat, _ = s.GEOD.fwd(np.full(36, longitude), np.full(36, latitude),
                                               bearings, distances + rng.uniform(-100., 100., 36))
            categories = np.tile([17, 18, 19], 12)
            indexes = self.indexes(shore_lat, shore_lon, categories)
            exact = np.column_stack([
                np.min(s.geodesic_distances(query_lon[:, None].repeat(12, axis=1).ravel(),
                                             query_lat[:, None].repeat(12, axis=1).ravel(),
                                             np.tile(shore_lon[categories == code], 80),
                                             np.tile(shore_lat[categories == code], 80)).reshape(80, 12), axis=1)
                for _, code, _ in self.pairs])
            minimum = exact.min(axis=1)
            expected = np.argmax(exact <= minimum[:, None] + .00001, axis=1).astype(np.uint8) + 1
            for band in (None, 22224.):
                reference = expected.copy()
                if band is not None:
                    reference[minimum > band] = 0
                result, _ = self.classify(query_lat, query_lon, indexes, band=band)
                np.testing.assert_array_equal(result, reference)


if __name__ == '__main__':
    unittest.main()
