import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from apply_open_sea_coastal_rule import parent_ocean
from repartition_red_sea_aden import aden_groups
class OpenWaterRuleTests(unittest.TestCase):
    def test_tasmania_meridian(self):
        np.testing.assert_array_equal(parent_ocean('Tasman Sea',np.array([146.8,147.1,160]),np.array([-45,-45,-40])),[9,8,8])
    def test_bight_indian_parent(self):
        np.testing.assert_array_equal(parent_ocean('Great Australian Bight',np.array([120,130,140]),np.array([-35,-36,-40])),[9,9,9])
    def test_aden_island_priority_only_inside_band(self):
        np.testing.assert_array_equal(aden_groups(np.array([True,False]),np.array([1,1]),np.array([2,2])),[1,2])
if __name__=='__main__':unittest.main()
