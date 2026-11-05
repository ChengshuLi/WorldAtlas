import unittest
import numpy as np
from grid_land_diff import diff_row

class GridDiffTest(unittest.TestCase):
    def test_clipped_intersections_and_excluded_water(self):
        a=np.array([[3,17],[6,18],[8,1]],dtype='uint32')
        b=np.array([[2,17],[5,19],[7,18],[8,1]],dtype='uint32')
        self.assertEqual(list(diff_row(a,b,1,8,8,{17,18,19})),[(2,3,17,19),(3,5,18,19)])

    def test_no_difference_for_matching_labels(self):
        row=np.array([[2,17],[8,18]],dtype='uint32')
        self.assertEqual(list(diff_row(row,row,0,8,8,{17,18})),[])

    def test_invalid_row_and_window_fail_closed(self):
        row=np.array([[2,17],[8,18]],dtype='uint32')
        for bad in (np.array([[0,17],[8,18]],dtype='uint32'),
                    np.array([[2,17],[2,18],[8,18]],dtype='uint32'),
                    np.array([[2,17],[7,18]],dtype='uint32')):
            with self.assertRaises(ValueError):list(diff_row(bad,row,0,8,8,{17,18}))
        with self.assertRaises(ValueError):list(diff_row(row,row,3,3,8,{17,18}))

if __name__=='__main__':unittest.main()
