import unittest,numpy as np
from compare import nearest_side,count_match
class CompareTests(unittest.TestCase):
 def test_prefix(self):
  end=np.array([3,6,10]);code=np.array([20,21,20]);starts=np.array([1,2,4,8]);stops=np.array([2,7,5,10]);self.assertEqual(count_match(end,code,starts,stops,20),1+2+0+2);self.assertEqual(count_match(end,code,starts,stops,21),0+3+1+0)
 def test_retired_nearest_and_entry_fail(self):
  import compare
  with self.assertRaisesRegex(RuntimeError,'planar nearest-side method retired'):nearest_side(0,0,[[0,0],[1,1]])
  with self.assertRaisesRegex(RuntimeError,'planar nearest-side method retired'):compare.main()
if __name__=='__main__':unittest.main()

