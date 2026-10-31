import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from north_sea_limits import NORTH_SEA
class CoastalRulesTest(unittest.TestCase):
    def test_north_sea_northern_limit(self):
        self.assertTrue(NORTH_SEA.contains_point((2,60.9)))
        self.assertFalse(NORTH_SEA.contains_point((2,61.1)))
    def test_shetland_sides(self):
        self.assertTrue(NORTH_SEA.contains_point((0,60)))
        self.assertFalse(NORTH_SEA.contains_point((-3,60)))
    def test_ocean_islands_outside_bounded_sea(self):
        for p in [(-7,62),(-20,65),(-13.687,57.596),(-6.248,46.359)]:self.assertFalse(NORTH_SEA.contains_point(p))
    def test_nautical_mile_conversion(self):self.assertAlmostEqual(12*1.852,22.224)
if __name__=='__main__':unittest.main()
