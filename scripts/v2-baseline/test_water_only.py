import unittest,sys,numpy as np
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(0,str(Path(__file__).resolve().parent.parent / 'v7-replay'))
from water_only import water_only_crop
from shared_nearest import edges_for_crop

def rle(a):
 rows=[0];runs=[]
 for row in a:
  ends=np.r_[np.flatnonzero(row[1:]!=row[:-1])+1,len(row)]
  starts=np.r_[0,ends[:-1]]
  for x,v in zip(ends,row[starts]):runs.extend([x,v])
  rows.append(len(runs)//2)
 return np.array(rows,dtype=np.uint32),np.array(runs,dtype=np.uint32)
class Test(unittest.TestCase):
 def test_random_soundness(self):
  rng=np.random.default_rng(723);w=36;h=18;step=10
  for i in range(300):
   a=np.where(rng.random((h,w))<.02,17,1).astype(np.uint32); l=np.where(a==17,17,0).astype(np.uint32)
   x=int(rng.integers(-w,w));n=int(rng.integers(1,w+1));y=int(rng.integers(h));z=int(rng.integers(y+1,h+1));box=(x,x+n,y,z)
   p=rle(a);land=rle(l); fast=water_only_crop(p,land,box,w,h)
   if fast:
    with self.assertRaisesRegex(ValueError,'no participant shorelines in crop'):edges_for_crop(p,land,box,w,h,step,[17])
 def test_extra_rows_and_wrap(self):
  a=np.ones((4,10),dtype=np.uint32);a[0,9]=17;p=rle(a)
  self.assertFalse(water_only_crop(p,p,(-1,2,1,2),10,4))
  self.assertTrue(water_only_crop(p,p,(1,4,1,2),10,4))
 def test_bad_rle_fails(self):
  rows=np.array([0,2],dtype=np.uint32);runs=np.array([3,1,2,1],dtype=np.uint32)
  with self.assertRaisesRegex(ValueError,'invalid RLE row'):water_only_crop((rows,runs),(rows,runs),(0,2,0,1),2,1)
 def test_bad_land_rle_fails(self):
  p=rle(np.ones((1,2),dtype=np.uint32)); rows=np.array([0,2],dtype=np.uint32);runs=np.array([3,0,2,0],dtype=np.uint32)
  with self.assertRaisesRegex(ValueError,'invalid RLE row'):water_only_crop(p,(rows,runs),(0,2,0,1),2,1)
if __name__=='__main__':unittest.main()
