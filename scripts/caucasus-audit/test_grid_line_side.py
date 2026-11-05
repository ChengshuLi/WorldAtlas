import unittest
from shapely.geometry import LineString, Point
from grid_line_side import side

class SideTests(unittest.TestCase):
    def test_orientation_and_distance(self):
        line=LineString([(0,0),(10,0)])
        self.assertEqual(side(line,Point(4,2),1),('left',2))
        self.assertEqual(side(line,Point(4,-3),1),('right',3))
        self.assertEqual(side(line,Point(4,0),1),('on',0))
        self.assertEqual(side(LineString(list(line.coords)[::-1]),Point(4,2),1),('right',2))

if __name__=='__main__':unittest.main()
