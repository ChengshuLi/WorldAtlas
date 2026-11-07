import unittest
import numpy as np
from affine import Affine
from spring_intersect_interface import search


class Identity:
    def transform(self,x,y):return x,y


class SpringIntersectionTest(unittest.TestCase):
    def test_finds_actual_interface_intersection(self):
        labels=np.array([[1,2],[1,2]],dtype=np.uint8)
        result=search(labels,Affine(.001,0,0,0,-.001,.002),Identity(),[(0,.0015),(.002,.0015)],(.001,0))
        self.assertEqual(result['intersections'],1)
        self.assertAlmostEqual(result['candidate']['point'][0],.001)
        self.assertAlmostEqual(result['candidate']['point'][1],.0015)
        self.assertAlmostEqual(result['candidate']['spring_join_m_wgs84'],0)

    def test_no_crossing_is_explicit(self):
        labels=np.array([[1,2],[1,2]],dtype=np.uint8)
        result=search(labels,Affine(.001,0,0,0,-.001,.002),Identity(),[(.002,.0015),(.003,.0015)],(.001,0))
        self.assertEqual(result['intersections'],0)


if __name__=='__main__':unittest.main()
