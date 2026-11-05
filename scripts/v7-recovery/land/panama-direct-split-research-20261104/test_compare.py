import unittest,numpy as np
from compare import nearest_side,count_match
class CompareTests(unittest.TestCase):
 def test_prefix(self):
  end=np.array([3,6,10]);code=np.array([20,21,20]);starts=np.array([1,2,4,8]);stops=np.array([2,7,5,10]);self.assertEqual(count_match(end,code,starts,stops,20),1+2+0+2);self.assertEqual(count_match(end,code,starts,stops,21),0+3+1+0)
 def test_orientation_and_center_tie(self):
  line=[[0,0],[0,10]];self.assertEqual(nearest_side(-1,5,line)[0],1);self.assertEqual(nearest_side(1,5,line)[0],-1);self.assertEqual(nearest_side(0,5,line)[0],0)
 def test_no_endpoint_extrapolation(self):
  line=[[0,0],[0,10]]
  self.assertEqual(nearest_side(-1,-1,line)[0],0);self.assertEqual(nearest_side(1,11,line)[0],0)
 def test_opposed_tie(self):
  self.assertEqual(nearest_side(0,0,[[-1,-1],[-1,1],[3,2],[1,-1],[1,1]])[0],0)
if __name__=='__main__':unittest.main()
