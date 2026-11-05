import unittest
from geodesic_line import GeodesicLine
from grid_line_side import side

class SideTests(unittest.TestCase):
    def test_orientation_and_distance(self):
        line=GeodesicLine([(0,0),(1,0)])
        self.assertEqual(side(line,(.5,.01),5)[0],'left')
        self.assertEqual(side(line,(.5,-.01),5)[0],'right')
        self.assertEqual(side(line,(.5,0),5)[0],'on')
        self.assertEqual(side(GeodesicLine([(1,0),(0,0)]),(.5,.01),5)[0],'right')

if __name__=='__main__':unittest.main()
