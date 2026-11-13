import unittest
import numpy as np
from map_build.water import wrapped_bounds as w
from map_build.water import shared_nearest as s
from map_build.water import streamed_shore_fallback as sf
W,H=36,18;STEP=10.
def poly(a,b,c=-5,d=5):return [[[a,c],[b,c],[b,d],[a,d],[a,c]]]
def multi(*p):return {'geometry':{'type':'MultiPolygon','coordinates':list(p)}}
def rle(a):
 rows=[0];runs=[]
 for row in a:
  end=np.r_[np.flatnonzero(np.diff(row)!=0)+1,len(row)];start=np.r_[0,end[:-1]]
  for e,v in zip(end,row[start]):runs.extend([e,v])
  rows.append(len(runs)//2)
 return np.array(rows,dtype='u4'),np.array(runs,dtype='u4')
class TestBounds(unittest.TestCase):
 def test_seam_split_and_unsplit_preserves_projection(self):
  self.assertEqual(w.wrapped_grid_bounds(multi(poly(-180,-170),poly(170,180)),360,180,1),((350,370,85,95),((0,10),(350,360))))
  self.assertEqual(w.wrapped_grid_bounds(multi(poly(-170,170)),360,180,1)[0],(10,350,85,95))
  self.assertEqual(w.wrapped_grid_bounds(multi(poly(-180,180)),360,180,1)[0],(0,360,85,95))
 def test_streamed_fallback_and_error_propagation(self):
  calls=[]
  def classify(lat,lon,bounds,width,height,step,pairs,tolerance,index):
   if lat[0]==1:raise ValueError('crop cannot certify nearest shore; increase halo')
   if lat[0]==2:raise ValueError('invalid query coordinates')
   return np.array([3],dtype='u1'),1,0
  def stream(*args):calls.append(1);return 4
  c=w.StreamedWrappedClassifier(classify,stream,(33,39,6,12),(0,36,0,18),36,18,10,[],0,{'x':1},lambda code:())
  self.assertEqual(c.classify(np.array([0.]),np.array([0.]))[0].tolist(),[3]);self.assertEqual(c.classify(np.array([1.]),np.array([0.]))[0].tolist(),[4]);self.assertEqual(len(calls),1);self.assertEqual((c.narrow_cells,c.fallback_cells),(1,1))
  with self.assertRaisesRegex(ValueError,'invalid query'):c.classify(np.array([2.]),np.array([0.]))
 def test_wrapped_order_matches_original_full_crop_order(self):
  rng=np.random.default_rng(93);ph=np.where(rng.random((H,W))<.35,17,1).astype('u4');land=np.where(ph==17,rng.choice([18,20],size=(H,W)),0).astype('u4');P,L=rle(ph),rle(land);narrow=(34,38,2,16)
  for full_bounds in ((0,W,2,16),(-3,3,2,16)):
   full=s.centers_for_crop(P,L,full_bounds,W,H,STEP,[18,20]);cut=s.centers_for_crop(P,L,narrow,W,H,STEP,[18,20]);ordered=w.baseline_shore_order(cut,full_bounds,W,STEP)
   col=np.rint((full['lon']+180)/STEP-.5).astype(np.int64)%W;subset=(col-narrow[0])%W<narrow[1]-narrow[0]
   for key in ('lat','lon','category','mids'):self.assertTrue(np.array_equal(ordered[key],full[key][subset]),(full_bounds,key))
 def test_streamed_blocks_match_full_order_and_values(self):
  rng=np.random.default_rng(33);ph=np.where(rng.random((H,W))<.35,17,1).astype('u4');land=np.where(ph==17,rng.choice([18,20],size=(H,W)),0).astype('u4');P,L=rle(ph),rle(land)
  for bounds in ((0,W,0,H),(33,39,0,H)):
   for code in (18,20):
    full=s.centers_for_crop(P,L,bounds,W,H,STEP,[code])
    for size in (1,2,7,64):
     blocks=list(w.shore_blocks(s,P,L,bounds,W,H,STEP,code,size))
     for key in ('lat','lon','category','mids'):self.assertTrue(np.array_equal(np.concatenate([b[key] for b in blocks]),full[key]),(bounds,code,size,key))
 def test_streamed_without_narrow_index_matches_full_wgs84(self):
  rng=np.random.default_rng(88);bounds=(0,W,0,H);pairs=[(1,18,2),(2,20,4)]
  ph=np.where(rng.random((H,W))<.35,17,1).astype('u4');land=np.where(ph==17,rng.choice([18,20],size=(H,W)),0).astype('u4');P,L=rle(ph),rle(land);centers=s.centers_for_crop(P,L,bounds,W,H,STEP,[18,20]);indexes=s.make_indexes(centers,pairs)
  for lat0,lon0 in [(0,179.9),(0,-179.9),(85,175),(-85,-175)]+[(float(rng.uniform(-89,89)),float(rng.uniform(-180,180))) for _ in range(30)]:
   lat=np.array([lat0]);lon=np.array([lon0]);expected=s.classify(lat,lon,bounds,W,H,STEP,pairs,1e-5,indexes)[0][0]
   actual=sf.classify_one(lat0,lon0,bounds,W,H,STEP,pairs,1e-5,lambda code:w.shore_blocks(s,P,L,bounds,W,H,STEP,code,3),{})
   self.assertEqual(actual,expected,(lat0,lon0))
 def test_synthetic_wgs84_against_full_crop(self):
  rng=np.random.default_rng(615);nb=(33,39,6,12);fb=(0,36,0,18);pairs=[(1,18,2),(2,20,4)];proof=fallback=0
  for case in range(8):
   ph=np.where(rng.random((H,W))<.35,17,1).astype('u4');land=np.where(ph==17,rng.choice([18,20],size=(H,W)),0).astype('u4');P,L=rle(ph),rle(land)
   full=s.centers_for_crop(P,L,fb,W,H,STEP,[18,20]);narrow=s.centers_for_crop(P,L,nb,W,H,STEP,[18,20]);fi=s.make_indexes(full,pairs);ni=s.make_indexes(narrow,pairs)
   def blocks(code):
    mask=full['category']==code
    yield {k:v[mask] for k,v in full.items()}
   c=w.StreamedWrappedClassifier(s.classify,sf.classify_one,nb,fb,W,H,STEP,pairs,1e-5,ni,blocks)
   for _ in range(80):
    col=rng.uniform(nb[0]+.01,nb[1]-.01);row=rng.uniform(nb[2]+.01,nb[3]-.01);lon=np.array([((col*STEP-180+180)%360)-180]);lat=np.array([90-row*STEP])
    def run(fn):
     try:return ('ok',fn()[0].tolist())
     except (ValueError,RuntimeError) as e:return ('error',type(e).__name__,str(e))
    self.assertEqual(run(lambda:c.classify(lat,lon)),run(lambda:s.classify(lat,lon,fb,W,H,STEP,pairs,1e-5,fi)))
   proof+=c.narrow_cells;fallback+=c.fallback_cells
  self.assertGreater(proof,0);self.assertGreater(fallback,0)
if __name__=='__main__':unittest.main()
