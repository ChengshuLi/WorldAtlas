import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from shapely.geometry import box,Polygon
from add_verified_island_sources import contained_cells

class IslandSourceTests(unittest.TestCase):
    def test_no_center_means_no_forced_cell(self):
        x,y=contained_cells(box(.01,.01,.2,.2),360,180,1)
        self.assertEqual(len(x),0)
    def test_exact_native_center(self):
        x,y=contained_cells(box(.4,.4,.6,.6),360,180,1)
        self.assertEqual(list(zip(x,y)),[(180,89)])
    def test_lagoon_hole_stays_water(self):
        g=Polygon([(0,0),(3,0),(3,3),(0,3)],holes=[[(1,1),(2,1),(2,2),(1,2)]])
        x,y=contained_cells(g,360,180,1)
        self.assertEqual(len(x),8)
        self.assertNotIn((181,88),list(zip(x,y)))
if __name__=='__main__':unittest.main()
