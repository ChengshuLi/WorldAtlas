import unittest
import numpy as np
from osgeo import gdal, osr
import terrain_screen as module


class ScreenTest(unittest.TestCase):
    def test_classification(self):
        self.assertEqual(module.classify(1, 3, 2), 'higher_than_both')
        self.assertEqual(module.classify(3, 1, 2), 'lower_than_both')
        self.assertEqual(module.classify(1, 2, 3), 'monotonic')
        self.assertEqual(module.classify(1, 1, 2), 'tie')
        self.assertEqual(module.classify(None, 1, 2), 'excluded')

    def test_reject_geographic_offset_crs(self):
        with self.assertRaises(ValueError):
            module.transformer(4326)

    def test_raster_index_and_mask(self):
        driver = gdal.GetDriverByName('MEM')
        rasters = []
        for data in (np.array([[20, 21], [22, -9999]], dtype=np.int16), np.array([[0, 8], [48, 0]], dtype=np.int16)):
            ds = driver.Create('', 2, 2, 1, gdal.GDT_Int16)
            ds.SetGeoTransform((10, .5, 0, 51, 0, -.5))
            ds.GetRasterBand(1).WriteArray(data)
            rasters.append(ds)
        tiles = {(50, 10): tuple(rasters)}
        self.assertEqual(module.sample_point(tiles, 10.1, 50.9)['height_m'], 20)
        self.assertEqual(module.sample_point(tiles, 10.6, 50.9)['status'], 'excluded_mask_or_nodata')
        self.assertEqual(module.sample_point(tiles, 10.1, 50.1)['status'], 'excluded_mask_or_nodata')
        self.assertEqual(module.sample_point(tiles, 10.6, 50.1)['status'], 'excluded_mask_or_nodata')
        self.assertEqual(module.sample_point(tiles, 11.1, 50.9)['status'], 'missing_tile')

if __name__ == '__main__':
    unittest.main()
