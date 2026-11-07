import unittest
import numpy as np
from pyproj import Transformer
from rasterio.transform import from_origin
from spring_join_basin_profile import classify_pairs


class SpringJoinBasinTest(unittest.TestCase):
    def test_geodesic_pairs_in_single_group(self):
        labels=np.ones((12,12),dtype=np.uint8)
        transform=from_origin(400000,6100000,100,100)
        inverse=Transformer.from_crs(32640,4326,always_xy=True)
        start=inverse.transform(400500,6099900);end=inverse.transform(400500,6099000)
        result=classify_pairs(labels,transform,start,end,100,5)
        self.assertEqual(result['center_groups'],{'1':5})
        self.assertEqual(result['left_right_pairs'],{'1:1':5})


if __name__=='__main__':unittest.main()
