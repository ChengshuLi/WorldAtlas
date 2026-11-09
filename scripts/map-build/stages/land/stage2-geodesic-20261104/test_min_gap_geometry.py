import math,random,unittest
import numpy as np
from point_prototype import GEOD
from run_pair import run_pair,run_pairs_batch

class MinimumGapGeometryTests(unittest.TestCase):
 def test_exhaustive_integer_interval_gap_even_and_odd(self):
  for width in (11,12):
   intervals=[(a,b) for a in range(width) for b in range(a+1,width+1)]
   for a,b in intervals:
    for c,d in intervals:
     wrapped=min(min(abs(x-z),width-abs(x-z)) for x in range(a,b) for z in range(c,d))
     formula=min(max(0,c+shift-(b-1),a-(d-1+shift)) for shift in (-width,0,width))
     self.assertEqual(formula,wrapped,(width,a,b,c,d))
 def test_global_latitudes_antipodes_and_seams(self):
  width=360; rng=random.Random(874913);records=[]
  for yy in (0,1,44,89,90,135,178,179):
   for c,d in ((0,1),(1,4),(89,91),(178,182),(356,359),(359,360),(0,180),(180,360)):
    records.append((yy,c,d,17+len(records)%6))
  for y in (0,1,44,89,90,135,178,179):
   for a,b in ((0,1),(1,4),(89,91),(178,182),(356,359),(359,360),(0,180),(180,360)):
    expected={}
    for yy,c,d,code in records:
     dist,_=run_pair(y,a,b,yy,c,d,width,incumbent=21000000.,tol=1e-5)
     if dist is not None:expected[code]=min(expected.get(code,math.inf),dist)
    actual,n=run_pairs_batch(y,a,b,np.array(records,dtype=np.uint32),width,incumbent=21000000.,tol=1e-5)
    self.assertEqual(n,len(records));self.assertEqual(set(actual),set(expected))
    for code in expected:self.assertAlmostEqual(actual[code],expected[code],places=7)
 def test_native_grid_near_antipodes_and_poles(self):
  width=131072
  for y in (0,1,100,32767,32768,54613,65534,65535):
   yy=65535-y
   for a,b in ((0,1),(0,32),(65520,65540),(131040,131072)):
    opposite=(a+width//2)%width
    left=max(0,opposite-16);right=min(width,opposite+17)
    records=np.asarray([(yy,left,right,17)],dtype=np.uint32)
    original,_=run_pair(y,a,b,yy,left,right,width,incumbent=21000000.,tol=1e-5)
    actual,_=run_pairs_batch(y,a,b,records,width,incumbent=21000000.,tol=1e-5)
    self.assertAlmostEqual(actual[17],original,places=7)

 def test_exact_ties_survive_all_categories(self):
  records=np.asarray([(89,0,1,17),(89,0,1,22),(89,359,360,18)],dtype=np.uint32)
  got,_=run_pairs_batch(89,0,1,records,360,incumbent=1000000.,tol=1e-5)
  self.assertEqual(got[17],got[22]);self.assertEqual(got[17],0.)
  # Distinct, symmetric cells on opposite sides of a query are a real
  # equal-distance case; the two categories must both remain visible.
  records=np.asarray([(89,99,100,17),(89,101,102,22)],dtype=np.uint32)
  symmetric,_=run_pairs_batch(89,100,101,records,360,incumbent=1000000.,tol=1e-5)
  self.assertEqual(symmetric[17],symmetric[22]);self.assertGreater(symmetric[17],0.)

if __name__=='__main__':unittest.main()
