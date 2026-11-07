import sys, unittest
from pathlib import Path
import numpy as np
from rasterio.features import rasterize
from rasterio.transform import from_origin
from shapely.geometry import Polygon,mapping
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from refine_inland_water_mask import apply_lake_mask

class InlandWaterMaskTests(unittest.TestCase):
    def test_only_land_inside_lake_changes(self):
        cells=np.array([[20,20,7],[18,2,22]],dtype='uint8')
        lakes=np.array([[1,0,1],[1,1,0]],dtype='uint8')
        actual=apply_lake_mask(cells,lakes)
        np.testing.assert_array_equal(actual,[[4,20,7],[2,2,22]])
        np.testing.assert_array_equal(actual&15,cells&15)
    def test_island_hole_stays_land(self):
        lake=Polygon([(0,0),(3,0),(3,3),(0,3)],holes=[[(1,1),(2,1),(2,2),(1,2)]])
        mask=rasterize([(mapping(lake),1)],out_shape=(3,3),transform=from_origin(0,3,1,1),dtype='uint8')
        result=apply_lake_mask(np.full((3,3),20,dtype='uint8'),mask)
        self.assertEqual(result[1,1],20)
        self.assertEqual(np.count_nonzero(result==4),8)
if __name__=='__main__':unittest.main()
