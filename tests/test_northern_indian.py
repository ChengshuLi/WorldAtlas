import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from rebuild_northern_indian import oman_side,malacca_side
class NorthernIndianTest(unittest.TestCase):
    def test_oman(self):
        self.assertTrue(oman_side(58,24.5))
        self.assertTrue(oman_side(51,27))
        self.assertFalse(oman_side(65,15))
    def test_andaman_malacca(self):
        self.assertTrue(malacca_side(96,11))
        self.assertFalse(malacca_side(99,5))
if __name__=='__main__':unittest.main()
