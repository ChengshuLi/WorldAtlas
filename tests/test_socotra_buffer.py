import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from refine_socotra_buffer import gulf_gates
class SocotraBufferTest(unittest.TestCase):
    def test_shared_aden(self):
        self.assertTrue(gulf_gates(48,13))
        self.assertTrue(gulf_gates(49,14))
    def test_open_socotra_water(self):
        for lon,lat in [(53.97308,14.10370),(54.47845,14.78485),(55.95062,13.72467),(57.54364,14.10370)]:
            self.assertFalse(gulf_gates(lon,lat))
    def test_red_sea_excluded(self):self.assertFalse(gulf_gates(43,15))
if __name__=='__main__':unittest.main()
