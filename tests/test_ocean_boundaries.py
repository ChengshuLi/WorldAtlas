import unittest,sys
import numpy as np
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from bering_strait_boundary import north_of_strait
from arctic_atlantic_boundary import arctic_side
class OceanBoundaryTest(unittest.TestCase):
 def test_bering_gateway(self):
  self.assertTrue(north_of_strait(-168.27484,66.05255))
  self.assertTrue(north_of_strait(-169,66.3))
  self.assertFalse(north_of_strait(-169,65.5))
 def test_barents_has_no_atlantic_pocket_east_of_north_cape(self):
  self.assertTrue(arctic_side(47,67.5))
  self.assertTrue(arctic_side(40,68))
 def test_norwegian_sea_stays_atlantic(self):
  self.assertFalse(arctic_side(5,68))

class TestExactArcPrecision(unittest.TestCase):
    def test_reported_submetre_centers(self):
        from arctic_atlantic_boundary import arctic_side
        for x,y in [(35831,2490),(36376,2901)]:
            lon=-180+(x+.5)*360/65536
            lat=90-(y+.5)*360/65536
            self.assertFalse(bool(arctic_side(np.array([lon]),np.array([lat]))[0]))

if __name__=='__main__':unittest.main()
