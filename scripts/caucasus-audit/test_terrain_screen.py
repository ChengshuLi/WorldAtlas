import unittest
import numpy as np
from osgeo import gdal, osr
import terrain_screen as module
import sample_line
from geodesic_tools import GEOD
from unittest.mock import patch


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

    def test_offsets_are_wgs84_and_old_samples_fail(self):
        line=[[1,1],[1.01,1]];doc=sample_line.generate(line,0,1,7,500,32631)
        def dummy(tiles,lon,lat,require_stack=False):
            return {'status':'valid_mask_0','longitude':lon,'latitude':lat,'height_m':100}
        with patch.object(module,'sample_point',side_effect=dummy):
            result=module.screen(doc,line,{},7,0,1,32631)
        center=result[0]['coordinates']
        for offset in (-1000,-500,100,500,1000):
            sample=result[0]['offsets'][str(offset)]
            self.assertAlmostEqual(GEOD.inv(*center,sample['longitude'],sample['latitude'])[2],abs(offset),delta=1e-5)
        with self.assertRaisesRegex(ValueError,'regenerate'):
            module.screen({'type':'FeatureCollection','features':doc['features']},line,{},7,0,1,32631)
        with self.assertRaisesRegex(ValueError,'regenerate'):
            module.screen(doc,line,{},7,0,1,32632)

    def test_earlier_edge_change_or_section_bounds_reject_stale_samples(self):
        line=[[1,1],[1.01,1],[1.02,1]]
        doc=sample_line.generate(line,0,2,7,1500,32631)
        self.assertEqual(doc['features'][1]['properties']['source_edge_index'],1)
        changed=[[.99,1],*line[1:]]
        with self.assertRaisesRegex(ValueError,'regenerate'):
            module.screen(doc,changed,{},7,0,2,32631)
        with self.assertRaisesRegex(ValueError,'section bounds'):
            module.screen(doc,line,{},7,1,2,32631)

    def test_raster_index_and_mask(self):
        driver = gdal.GetDriverByName('MEM')
        rasters = []
        for data in (np.array([[20, 21], [22, -9999]], dtype=np.int16), np.array([[0, 8], [48, 0]], dtype=np.int16)):
            ds = driver.Create('', 2, 2, 1, gdal.GDT_Int16)
            ds.SetGeoTransform((10, .5, 0, 51, 0, -.5))
            ds.GetRasterBand(1).WriteArray(data)
            rasters.append(ds)
        tiles = {(50, 10): (*rasters, None)}
        self.assertEqual(module.sample_point(tiles, 10.1, 50.9)['height_m'], 20)
        self.assertEqual(module.sample_point(tiles, 10.6, 50.9)['status'], 'excluded_mask_or_nodata')
        self.assertIsNone(module.sample_point(tiles, 10.6, 50.9)['height_m'])
        self.assertEqual(module.sample_point(tiles, 10.1, 50.1)['status'], 'excluded_mask_or_nodata')
        self.assertEqual(module.sample_point(tiles, 10.6, 50.1)['status'], 'excluded_mask_or_nodata')
        self.assertIsNone(module.sample_point(tiles, 10.6, 50.1)['height_m'])
        self.assertEqual(module.sample_point(tiles, 11.1, 50.9)['status'], 'missing_tile')
        self.assertEqual(module.sample_point(tiles, 10.1, 50.9, True)['status'], 'excluded_stack')
        stack = driver.Create('', 2, 2, 1, gdal.GDT_Int16)
        stack.SetGeoTransform((10, .5, 0, 51, 0, -.5))
        stack.GetRasterBand(1).WriteArray(np.array([[0, 1], [1, 2]], dtype=np.int16))
        with_stack = {(50, 10): (*rasters, stack)}
        zero = module.sample_point(with_stack, 10.1, 50.9, True)
        self.assertEqual(zero['status'], 'excluded_stack')
        self.assertIsNone(zero['height_m'])
        self.assertEqual(zero['stack'], 0)

if __name__ == '__main__':
    unittest.main()
