import unittest
import numpy as np
from map_build.water import rectangle_nearest as r
from map_build.water import shared_nearest as s
from map_build.water import coastal_core as coast


class RectangleNearest(unittest.TestCase):
    def test_optional_coastal_band_and_missing_classes(self):
        pairs = [('a', 17, 1), ('b', 18, 2), ('absent', 19, 3)]
        lat, lon = np.array([.5, .5]), np.array([-.5, 5.5])
        indexes = s.make_indexes({'lat': lat, 'lon': lon, 'mids': s.unit(lat, lon),
                                  'category': np.array([17, 18], dtype='u1')}, pairs[:2])
        bounds = (0, 360, 0, 180)
        def point(lat, lon):
            codes, stats = coast.classify(lat, lon, bounds, 360, 180, 1., pairs, 1e-5, 100000., .01, indexes)
            return codes, stats['bounded'], stats['exact']
        water = np.ones((7, 40), dtype=bool)
        actual, stats = r.classify(water, 160, 86, bounds, 360, 180, 1., pairs, 1e-5,
                                   indexes, point, band=100000., band_tolerance=.01)
        yy, xx = np.indices(water.shape)
        expected = point((90 - (86 + yy + .5)).ravel(), (-180 + (160 + xx + .5)).ravel())[0].reshape(water.shape)
        np.testing.assert_array_equal(actual, expected)
        self.assertTrue(np.any(actual == 0))
        self.assertTrue(np.any(actual != 0))
        self.assertEqual(stats['bounded_cells'] + stats['exact_cells'], int(water.sum()))

    def test_global_masks_and_seams_against_complete_point_classifier(self):
        rng = np.random.default_rng(29485)
        pairs = [('b', 18, 2), ('a', 17, 1), ('c', 19, 3)]
        lat = rng.uniform(-85, 85, 120)
        lon = rng.uniform(-180, 180, 120)
        categories = np.tile([17, 18, 19], 40).astype('u1')
        indexes = s.make_indexes({'lat': lat, 'lon': lon, 'mids': s.unit(lat, lon), 'category': categories}, pairs)
        bounds = (0, 360, 0, 180)
        point = lambda lat, lon: s.classify(lat, lon, bounds, 360, 180, 1., pairs, 1e-5, indexes)
        for x0, y0, nr, nc in ((0, 0, 5, 30), (350, 20, 11, 10), (0, 150, 13, 10), (160, 80, 9, 30)):
            water = rng.random((nr, nc)) > .2
            actual, stats = r.classify(water, x0, y0, bounds, 360, 180, 1., pairs, 1e-5, indexes, point, block=8)
            yy, xx = np.nonzero(water)
            expected = point(90 - (y0 + yy + .5), -180 + (x0 + xx + .5))[0]
            np.testing.assert_array_equal(actual[water], expected)
            self.assertTrue(np.all(actual[~water] == 0))
            self.assertEqual(stats['bounded_cells'] + stats['exact_cells'], int(water.sum()))

    def test_complete_fallback_and_selection_window_validation(self):
        pairs = [('a', 17, 1), ('b', 18, 2)]
        def point(lat, lon):
            return np.ones(len(lat), dtype='u1'), 0, len(lat)
        selected = {10: [(0, 3), (357, 360)], 11: [(1, 4)]}
        assigned, stats = r.classify_rows(selected, [(0, 4), (357, 360)], (350, 370, 0, 180),
                                         360, 180, 1., pairs, 1e-5, {}, point)
        self.assertEqual(assigned, {10: [(0, 3, 1), (357, 360, 1)], 11: [(1, 4, 1)]})
        self.assertEqual(stats['exact_cells'], 9)
        with self.assertRaisesRegex(ValueError, 'complete selected input'):
            r.classify_rows(selected, [(0, 2), (357, 360)], (350, 370, 0, 180),
                            360, 180, 1., pairs, 1e-5, {}, point)

    def test_coastal_band_accepts_one_or_no_participant(self):
        bounds = (0, 360, 0, 180)
        data = {'lat': np.array([.5]), 'lon': np.array([.5]),
                'mids': s.unit(np.array([.5]), np.array([.5])), 'category': np.array([17], dtype='u1')}
        for pairs in ([('a', 17, 1)], []):
            indexes = s.make_indexes(data, pairs)
            def point(lat, lon):
                codes, stats = coast.classify(lat, lon, bounds, 360, 180, 1., pairs, 1e-5, 100000., .01, indexes)
                return codes, stats['bounded'], stats['exact']
            water = np.ones((5, 8), dtype=bool)
            actual, stats = r.classify(water, 177, 87, bounds, 360, 180, 1., pairs, 1e-5,
                                       indexes, point, band=100000., band_tolerance=.01)
            yy, xx = np.indices(water.shape)
            expected = point((90 - (87 + yy + .5)).ravel(), (-180 + (177 + xx + .5)).ravel())[0].reshape(water.shape)
            np.testing.assert_array_equal(actual, expected)
            self.assertEqual(stats['bounded_cells'] + stats['exact_cells'], int(water.sum()))

    def test_tie_priority_matches_point_reference(self):
        pairs = [('b', 18, 2), ('a', 17, 1)]
        lat, lon = np.array([.5, .5]), np.array([-.5, 1.5])
        indexes = s.make_indexes({'lat': lat, 'lon': lon, 'mids': s.unit(lat, lon),
                                  'category': np.array([17, 18], dtype='u1')}, pairs)
        bounds = (0, 360, 0, 180)
        point = lambda lat, lon: s.classify(lat, lon, bounds, 360, 180, 1., pairs, 1e-5, indexes)
        actual, _ = r.classify(np.ones((3, 12), dtype=bool), 175, 88, bounds,
                               360, 180, 1., pairs, 1e-5, indexes, point)
        self.assertEqual(actual[1, 5], 2)


if __name__ == '__main__':
    unittest.main()
