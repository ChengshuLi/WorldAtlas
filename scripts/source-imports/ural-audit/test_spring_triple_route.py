import unittest
import numpy as np
from affine import Affine
from spring_triple_route import route


class Identity:
    def transform(self,x,y):return x,y


class TripleRouteTest(unittest.TestCase):
    def test_retained_intersection_and_triple_are_connected(self):
        labels=np.array([[1,1,3],[1,2,3],[1,2,2]],dtype=np.uint8)
        t=Affine(.001,0,0,0,-.001,.003)
        result=route(labels,t,Identity(),[(.0015,.0025),(.0025,.0025)],(.001,0))
        self.assertGreater(result['intersections'],0)
        self.assertGreater(result['triple_nodes'],0)
        self.assertGreater(result['viable_paths'],0)
        self.assertAlmostEqual(result['candidate']['retained_intersection_lonlat'][0],.002)
        self.assertAlmostEqual(result['candidate']['retained_intersection_lonlat'][1],.0025)

    def test_missing_junction_is_not_invented(self):
        labels=np.array([[1,2],[1,2]],dtype=np.uint8)
        result=route(labels,Affine(.001,0,0,0,-.001,.002),Identity(),[(0,.001),(.002,.001)],(.001,0))
        self.assertEqual(result['triple_nodes'],0)
        self.assertNotIn('candidate',result)


if __name__=='__main__':unittest.main()
