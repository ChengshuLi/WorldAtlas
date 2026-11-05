import unittest
from geodesic_line import GeodesicLine,distance,GEOD

class LineTests(unittest.TestCase):
    def test_nearest_and_side(self):
        line=GeodesicLine([(0,0),(1,0)])
        p=(.5,.01);v=line.closest(p)
        self.assertAlmostEqual(v['distance_m'],1105.7428,delta=.05)
        self.assertEqual(line.side(p,v['station_m']),'left')
        self.assertEqual(line.side((.5,-.01),v['station_m']),'right')
    def test_endpoint_and_duplicate(self):
        line=GeodesicLine([(0,0),(0,0),(1,0)])
        v=line.closest((-1,0));self.assertEqual(v['station_m'],0)
    def test_dateline_and_tie(self):
        line=GeodesicLine([(179.9,0),(-179.9,0)])
        v=line.closest((180,.01));self.assertAlmostEqual(v['distance_m'],1105.7428,delta=.05)
        self.assertEqual(line.side((180,.01),v['station_m']),'left')
    def test_zero_length_rejected(self):
        with self.assertRaises(ValueError):GeodesicLine([(0,0),(0,0)])

if __name__=='__main__':unittest.main()
