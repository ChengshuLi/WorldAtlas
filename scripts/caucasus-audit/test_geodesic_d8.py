import unittest
import numpy as np
from rasterio.transform import from_origin
from geodesic_d8 import trace

class GeodesicD8Tests(unittest.TestCase):
    def test_downhill_then_pit(self):
        values=np.full((7,7),100);values[3,3]=50;values[3,4]=40;values[3,5]=30
        coords,status=trace(values,np.ones((7,7),bool),from_origin(0,1,.0003,.0003),(3,3))
        self.assertEqual(status,'pit_or_flat');self.assertEqual(len(coords),3)
    def test_invalid_neighborhood(self):
        values=np.ones((5,5));valid=np.ones((5,5),bool);valid[1,1]=False
        coords,status=trace(values,valid,from_origin(0,1,.0003,.0003),(2,2))
        self.assertEqual((coords,status),([], 'invalid_neighbor'))
    def test_step_cap(self):
        values=np.full((7,7),100);values[3,3]=50;values[3,4]=40
        coords,status=trace(values,np.ones((7,7),bool),from_origin(0,1,.0003,.0003),(3,3),1)
        self.assertEqual(status,'step_cap');self.assertEqual(len(coords),1)

if __name__=='__main__':unittest.main()
