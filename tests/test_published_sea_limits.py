import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from refine_published_sea_limits import ocean_connected_overhang

class PublishedSeaLimitsTests(unittest.TestCase):
    def test_enclosed_source_difference_is_preserved(self):
        self.assertEqual(ocean_connected_overhang({11,12,13,66},{11},10),{11,12,13})
    def test_longitude_wrap_connects(self):
        self.assertEqual(ocean_connected_overhang({20,29,28},{20},10),{20,29,28})
    def test_corner_contact_does_not_connect(self):
        self.assertEqual(ocean_connected_overhang({11,22},{11},10),{11})
    def test_no_ocean_seed_changes_nothing(self):
        self.assertEqual(ocean_connected_overhang({11,12},set(),10),set())
if __name__=='__main__':unittest.main()
