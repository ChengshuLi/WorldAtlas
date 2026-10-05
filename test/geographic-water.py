import pathlib
import sys
import unittest

import numpy as np
from rasterio.io import MemoryFile
from rasterio.transform import from_origin
from shapely.geometry import box, mapping, Polygon

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
from geographic_water import monthly_diagnostics, compare_months


def raster(values, transform=None, crs='EPSG:4326', nodata=None):
    a = np.array(values, dtype='uint8')
    with MemoryFile() as m:
        with m.open(driver='GTiff', width=a.shape[1], height=a.shape[0], count=1,
                    dtype='uint8', crs=crs, nodata=nodata,
                    transform=transform or from_origin(0, 3, 1, 1)) as r:
            r.write(a, 1)
        return m.read()


def feature(g):
    return {'type': 'Feature', 'id': 'gap:fixture', 'geometry': mapping(g),
            'properties': {'administrative_assignment': None}}


class WaterTests(unittest.TestCase):
    def run_case(self, a, g=None, anchor=(1.5, 1.5), **kwargs):
        return monthly_diagnostics(raster(a, **kwargs), feature(g or box(0, 0, 3, 3)),
                                   '2017-01', anchor)

    def test_water_support_is_not_polygon_approval(self):
        r = self.run_case([[2] * 3] * 3)
        self.assertEqual(r['centre_counts']['water_detected'], 9)
        self.assertEqual(r['signal'], 'sampled-water-support')
        self.assertEqual(r['component_water_status'], 'unknown')
        self.assertIsNone(r['administrative_assignment'])
        self.assertIsNone(r['registration_error_bound_m'])

    def test_dry_contradiction(self):
        self.assertEqual(self.run_case([[1] * 3] * 3)['signal'],
                         'sampled-not-water-contradiction')

    def test_no_observations_is_not_dry(self):
        r = self.run_case([[0] * 3] * 3)
        self.assertEqual(r['centre_counts']['not_water'], 0)
        self.assertEqual(r['signal'], 'unknown-no-observed-centres')

    def test_mixed_raw_classes(self):
        r = self.run_case([[0, 1, 2]] * 3)
        self.assertEqual(r['centre_counts'],
                         {'no_observations': 3, 'not_water': 3, 'water_detected': 3, 'total': 9})
        self.assertEqual(r['signal'], 'mixed-water-and-not-water')

    def test_hole_centres_excluded(self):
        g = Polygon([(0, 0), (3, 0), (3, 3), (0, 3)],
                    [[(1, 1), (2, 1), (2, 2), (1, 2)]])
        r = self.run_case([[1, 1, 1], [1, 2, 1], [1, 1, 1]], g, (.5, .5))
        self.assertEqual(r['centre_counts']['water_detected'], 0)
        self.assertEqual(r['centre_counts']['total'], 8)

    def test_no_centre_in_subpixel_seam_stays_unknown(self):
        r = self.run_case([[2] * 3] * 3, box(1.1, 0, 1.2, 3), (1.15, 1.5))
        self.assertEqual(r['centre_counts']['total'], 0)
        self.assertFalse(r['anchor']['pixel_centre_inside_component'])
        self.assertEqual(r['component_water_status'], 'unknown')

    def test_exact_boundary_centres_excluded(self):
        r = self.run_case([[2] * 3] * 3, box(.5, .5, 2.5, 2.5))
        self.assertEqual(r['centre_counts']['total'], 1)

    def test_unknown_class_rejected(self):
        with self.assertRaises(ValueError):
            self.run_case([[255] * 3] * 3)

    def test_component_not_clipped_to_source(self):
        with self.assertRaises(ValueError):
            self.run_case([[1] * 3] * 3, box(-.01, 0, 2, 2))

    def test_crs_not_assumed(self):
        with self.assertRaises(ValueError):
            self.run_case([[1] * 3] * 3, crs='EPSG:3857')

    def test_nodata_not_reinterpreted(self):
        with self.assertRaises(ValueError):
            self.run_case([[1] * 3] * 3, nodata=1)

    def test_invalid_geometry_not_fixed(self):
        with self.assertRaises(ValueError):
            self.run_case([[1] * 3] * 3,
                          Polygon([(0, 0), (3, 3), (0, 3), (3, 0), (0, 0)]))

    def test_missing_and_invalid_dates_rejected(self):
        for month in ('', '2017', '2017-13'):
            with self.assertRaises(ValueError):
                monthly_diagnostics(raster([[1]]), feature(box(0, 2, 1, 3)), month, (.5, 2.5))

    def test_two_months_cannot_invent_seasonality(self):
        a = self.run_case([[1] * 3] * 3)
        b = self.run_case([[2] * 3] * 3)
        b['source_month'] = '2017-07'
        r = compare_months([a, b])
        self.assertTrue(r['signals_differ'])
        self.assertEqual(r['seasonality'], 'unknown')
        self.assertTrue(r['unsampled_months_unknown'])

    def test_duplicate_month_rejected(self):
        a = self.run_case([[1] * 3] * 3)
        with self.assertRaises(ValueError):
            compare_months([a, a])

    def test_shifted_native_grid_requires_review(self):
        a = self.run_case([[1] * 3] * 3)
        b = self.run_case([[1] * 3] * 3)
        b['source_month'] = '2017-07'
        b['native_raster']['transform'][2] += .0001
        with self.assertRaises(ValueError):
            compare_months([a, b])

    def test_deterministic_native_counts(self):
        a = [[0, 1, 2], [2, 0, 1], [1, 2, 0]]
        self.assertEqual(self.run_case(a), self.run_case(a))


if __name__ == '__main__':
    unittest.main()
