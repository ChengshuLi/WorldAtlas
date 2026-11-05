import unittest
import numpy as np
from priority_d8 import drainage

class DrainageTest(unittest.TestCase):
    def test_gradient_and_void_barrier(self):
        r,c=np.indices((9,9));z=(20-c+2*np.abs(r-4)).astype(float);valid=np.ones((9,9),dtype=bool);valid[2,2]=False
        roots,flood,flow=drainage(z,valid,1.)
        self.assertEqual(roots[2,2],-2)
        self.assertEqual(roots[4,4],4*9+8)
        self.assertEqual(roots[3,3],roots[5,3])
        self.assertTrue(np.isinf(flood[2,2]))

if __name__=='__main__':unittest.main()
