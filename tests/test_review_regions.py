import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from refine_review_regions import ATLANTIC, SINAI, ISLAND_GROUPS, PolygonPath

class ReviewRegionsTest(unittest.TestCase):
    def test_atlantic_reports(self):
        points=[(-68.22235,23.42560),(-68.15643,31.04462),(-67.96967,42.86041),(-30,-30)]
        self.assertTrue(ATLANTIC.contains_points(points).all())
    def test_pacific_stays_outside(self):
        points=[(-123,40),(-110,20),(-84,8),(-79,7),(-80,-20),(147.45026,-47.56805)]
        self.assertFalse(ATLANTIC.contains_points(points).any())
    def test_sinai_seam(self):
        p=PolygonPath(SINAI+[SINAI[0]])
        self.assertFalse(p.contains_point((33.54950,27.90253)))
        self.assertTrue(p.contains_point((34.2,28.5)))
        for point in [(32.83539,29.32526),(32.74750,29.47357),(32.69257,29.60541),(32.59918,29.94598)]:
            self.assertTrue(p.contains_point(point))
        self.assertFalse(p.contains_point((32.28607,31.20392)))
        self.assertFalse(p.contains_point((33.92853,27.52899)))
    def test_island_group_scope(self):
        for name,point in [('Mapia',(134.32709,.75531)),('Asia and Ayau islands',(131.25641,1.06293)),('Marcus Island',(153.94867,24.31000))]:
            w,s,e,n=ISLAND_GROUPS[name];x,y=point
            self.assertTrue(w<=x<=e and s<=y<=n)
if __name__=='__main__':unittest.main()
