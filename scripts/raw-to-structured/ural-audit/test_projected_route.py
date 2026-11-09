import unittest
from pyproj import Geod
import numpy as np
from projected_route import ProjectedRoute, GEOD

class RouteTest(unittest.TestCase):
    def test_station_and_offsets(self):
        route=ProjectedRoute([[45,60],[45.01,60]],'EPSG:32638')
        lon,lat,az=route.point(route.length/2)
        self.assertAlmostEqual(lon,45.005,places=5)
        for signed in (-100,100):
            x,y,_=GEOD.fwd(lon,lat,az+90,signed)
            self.assertAlmostEqual(GEOD.inv(lon,lat,x,y)[2],100,delta=1e-6)
    def test_invalid(self):
        with self.assertRaises(ValueError):ProjectedRoute([[0,0],[1,1]],'EPSG:4326')
        with self.assertRaises(ValueError):ProjectedRoute([[45,60],[45,60]],'EPSG:32638')
        with self.assertRaises(ValueError):ProjectedRoute([[45,60],[45.01,60]],'EPSG:32638').point(-1)
    def test_nearest_is_wgs84_to_projected_line(self):
        route=ProjectedRoute([[45,60],[45.01,60]],'EPSG:32638')
        d,xy,ll=route.nearest(45.005,60.001)
        self.assertAlmostEqual(d,GEOD.inv(45.005,60.001,*ll)[2],delta=1e-7)
        self.assertLess(d,112);self.assertGreater(d,110)
        self.assertAlmostEqual(ll[0],45.005,places=5)
    def test_duplicate_consecutive_vertices(self):
        a=ProjectedRoute([[45,60],[45,60],[45.01,60]],'EPSG:32638')
        self.assertGreater(a.length,0)
    def test_nearest_against_dense_independent_samples(self):
        route=ProjectedRoute([[45,75],[45.03,75.005],[45.06,75]],'EPSG:32638')
        for query in [(45.01,75.01),(45.04,74.99),(44.99,75.0),(45.07,75.0)]:
            d,_,_=route.nearest(*query);dense=[]
            for edge in range(2):
                for t in np.linspace(0,1,1001):dense.append(GEOD.inv(*query,*route._at(edge,float(t)))[2])
            self.assertLessEqual(d,min(dense)+1e-5)
            self.assertGreaterEqual(d,min(dense)-2.)
if __name__=='__main__':unittest.main()
