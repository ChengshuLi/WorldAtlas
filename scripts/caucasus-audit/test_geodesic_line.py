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
    def test_preserves_coordinate_linear_geometry(self):
        line=GeodesicLine([(-1,60),(1,60)])
        lon,lat=line.point(line.length/2)
        self.assertAlmostEqual(lon,0,places=7);self.assertAlmostEqual(lat,60,places=12)
        self.assertLess(line.closest((0,60))["distance_m"],.02)
    def test_uncut_antimeridian_rejected(self):
        with self.assertRaises(ValueError):GeodesicLine([(179.9,0),(-179.9,0)])
    def test_equal_nearest_edges_are_flagged(self):
        line=GeodesicLine([(-.01,0),(-.01,.02),(.01,.02),(.01,0)])
        self.assertTrue(line.closest((0,.005))["ambiguous"])

    def test_zero_length_rejected(self):
        with self.assertRaises(ValueError):GeodesicLine([(0,0),(0,0)])

if __name__=='__main__':unittest.main()
