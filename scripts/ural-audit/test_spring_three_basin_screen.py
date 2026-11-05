import unittest
import numpy as np
from spring_three_basin_screen import nearest_transitions


class Identity:
    def transform(self,x,y): return x,y


class SpringThreeBasinTest(unittest.TestCase):
    def test_each_root_pair_and_unknown_cell(self):
        labels=np.array([[1,2,3],[1,0,3]],dtype=np.uint8)
        result=nearest_transitions(labels,[11,22,33],0,20,10,5,15,Identity())
        self.assertEqual(set(result),{'11:22','22:33'})
        self.assertEqual(result['11:22']['point_lonlat'],[10,15])
        self.assertEqual(result['11:22']['distance_m'],5)
        self.assertEqual(result['22:33']['distance_m'],15)


if __name__=='__main__': unittest.main()
