import unittest
import numpy as np
from pyproj import Transformer
from ridge_connector_screen import compare

class RidgeScreenTest(unittest.TestCase):
    def test_nearest_joins_form_one_lobe_with_eight_centers(self):
        width=36000;height=18000;rows=np.arange(height+1,dtype='uint32');runs=np.tile(np.array([[width,17]],dtype='uint32'),(height,1))
        f=Transformer.from_crs(4326,3857,always_xy=True).transform;i=Transformer.from_crs(3857,4326,always_xy=True).transform
        out=compare([(-.018,.02),(.018,.02)],[(-.018,0),(.018,0)],f,i,rows,runs,width,height,.01)
        self.assertEqual(len(out['lobes']),1)
        self.assertEqual(len(out['lobes'][0]['land_center_cells']),8)
        self.assertEqual(out['coordinates'][0],(-.018,0))

if __name__=='__main__':unittest.main()
