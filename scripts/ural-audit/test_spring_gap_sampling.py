import unittest
import numpy as np
from affine import Affine
from spring_gap_sampling import sampled_gap,G


class Identity:
    def transform(self,x,y):return x,y


class SpringGapSamplingTest(unittest.TestCase):
    def test_sampled_gap_and_wgs84_distance(self):
        labels=np.array([[1,2],[1,2]],dtype=np.uint8)
        t=Affine(.001,0,0,0,-.001,.002)
        result=sampled_gap(labels,t,Identity(),[(.003,0),(.003,.002)],[-.01,-.01,.01,.01],15)
        actual=G.inv(*result['retained_point'],*result['interface_point'])[2]
        self.assertAlmostEqual(result['sampled_gap_wgs84_m'],actual,places=8)
        self.assertGreater(actual,220);self.assertLess(actual,225)


if __name__=='__main__':unittest.main()
