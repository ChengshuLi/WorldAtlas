import unittest, numpy as np
from unittest import mock
import shared_nearest as s, coastal_core as core
from coastal_block import block_classify
class TestBlock(unittest.TestCase):
 def test_random_centers_and_global_edges(self):
  rng=np.random.default_rng(327);w=131072;h=54614;step=360/w;pairs=[(1,17,1),(2,18,2),(3,19,3)];bounds=(0,w,0,h)
  for y in [0,1,31,4000,16384,32768,50000,54612,54613]:
   lat=90-(y+.5)*step
   for x0 in (0,60000,130560):
    xs=np.sort(rng.choice(np.arange(x0,min(x0+512,w)),size=256,replace=False));q_lat=np.full(len(xs),lat);q_lon=-180+(xs+.5)*step
    slat=np.clip(lat+rng.uniform(-.5,.5,80),-89.999999,89.999999);slon=(((-180+(x0+rng.uniform(-500,1012,80))*step)+180)%360)-180
    centers={'lat':slat,'lon':slon,'mids':s.unit(slat,slon),'category':rng.choice(np.array([17,18,19],dtype=np.uint8),80)};idx=core.index_present(centers,pairs)
    try:ref=core.classify(q_lat,q_lon,bounds,w,h,step,pairs,.00001,22224,.000001,idx)[0]
    except RuntimeError as e:
     for block in (1,7,64,128,256):
      with self.assertRaisesRegex(RuntimeError,str(e)):block_classify(q_lat,q_lon,bounds,w,h,step,pairs,.00001,22224,.000001,idx,block)
    else:
     for block in (1,7,64,128,256):np.testing.assert_array_equal(block_classify(q_lat,q_lon,bounds,w,h,step,pairs,.00001,22224,.000001,idx,block),ref)
 def test_tie_and_near_band_threshold(self):
  w=131072;h=54614;step=360/w;y=32768;x0=65536;lat=90-(y+.5)*step;xs=np.arange(x0,x0+256);q_lat=np.full(len(xs),lat);q_lon=-180+(xs+.5)*step;pairs=[(2,18,2),(1,17,1)];bounds=(0,w,0,h)
  slat=np.array([lat,lat]);slon=np.array([q_lon[100]-.2,q_lon[100]+.2]);centers={'lat':slat,'lon':slon,'mids':s.unit(slat,slon),'category':np.array([17,18],np.uint8)};idx=core.index_present(centers,pairs)
  for threshold in (1000,22224,30000):
   ref=core.classify(q_lat,q_lon,bounds,w,h,step,pairs,.00001,threshold,.000001,idx)[0]
   for bs in (1,7,64,128,256):np.testing.assert_array_equal(block_classify(q_lat,q_lon,bounds,w,h,step,pairs,.00001,threshold,.000001,idx,bs),ref)
 def test_accounting_matches_water_cells(self):
  w=131072;h=54614;step=360/w;y=32768;xs=np.arange(64000,64512);lat=np.full(len(xs),90-(y+.5)*step);lon=-180+(xs+.5)*step;pairs=[(1,17,1)];slat=np.array([lat[0]]);slon=np.array([lon[100]]);centers={'lat':slat,'lon':slon,'mids':s.unit(slat,slon),'category':np.array([17],dtype=np.uint8)};idx=core.index_present(centers,pairs)
  out,stats=block_classify(lat,lon,(0,w,0,h),w,h,step,pairs,.00001,22224,.000001,idx,64,return_stats=True)
  self.assertEqual(stats['bounded']+stats['exact'],len(xs));np.testing.assert_array_equal(out,core.classify(lat,lon,(0,w,0,h),w,h,step,pairs,.00001,22224,.000001,idx)[0])
 def test_rejects_invalid_inputs_before_skip(self):
  w=360;h=180;step=1.;pairs=[(1,17,1)];bounds=(0,100,0,180);idx={}
  for lat,lon,b in [(np.array([0.]),np.array([0.]),bounds),(np.array([np.nan]),np.array([-170.]),bounds),(np.array([0.]),np.array([np.inf]),bounds),(np.array([91.]),np.array([-170.]),bounds)]:
   with self.assertRaises(ValueError):block_classify(lat,lon,b,w,h,step,pairs,0,22224,.000001,idx)
 def test_inside_shortcut_without_fallback(self):
  w=131072;h=54614;step=360/w;y=32768;xs=np.arange(65536,65600);lat=np.full(len(xs),90-(y+.5)*step);lon=-180+(xs+.5)*step;pairs=[(1,17,1)];slat=np.array([lat[0]]);slon=np.array([lon[32]]);centers={'lat':slat,'lon':slon,'mids':s.unit(slat,slon),'category':np.array([17],dtype=np.uint8)};idx=core.index_present(centers,pairs)
  with mock.patch.object(core,'classify',side_effect=AssertionError('unexpected fallback')):
   out,stats=block_classify(lat,lon,(0,w,0,h),w,h,step,pairs,.00001,22224,.000001,idx,64,return_stats=True)
  np.testing.assert_array_equal(out,np.ones(len(xs),dtype=np.uint8));self.assertEqual(stats,{'bounded':len(xs),'exact':0})
 def test_near_tie_forces_fallback(self):
  w=131072;h=54614;step=360/w;lat=np.array([0.]);lon=np.array([0.]);pairs=[(1,17,1),(2,18,2)];slat=np.array([0.,0.]);slon=np.array([-.05,.05]);centers={'lat':slat,'lon':slon,'mids':s.unit(slat,slon),'category':np.array([17,18],dtype=np.uint8)};idx=core.index_present(centers,pairs)
  with mock.patch.object(core,'classify',wraps=core.classify) as fallback:
   out=block_classify(lat,lon,(0,w,0,h),w,h,step,pairs,.00001,22224,.000001,idx,64)
  self.assertTrue(fallback.called);np.testing.assert_array_equal(out,np.array([1],dtype=np.uint8))
 def test_near_band_forces_fallback(self):
  w=131072;h=54614;step=360/w;lat=np.array([0.]);edge=s.GEOD.fwd(0,0,90,22224)[0];lon=np.array([edge]);pairs=[(1,17,1)];slat=np.array([0.]);slon=np.array([0.]);centers={'lat':slat,'lon':slon,'mids':s.unit(slat,slon),'category':np.array([17],dtype=np.uint8)};idx=core.index_present(centers,pairs)
  with mock.patch.object(core,'classify',wraps=core.classify) as fallback:
   try:block_classify(lat,lon,(0,w,0,h),w,h,step,pairs,.00001,22224,.000001,idx,64)
   except RuntimeError as e:self.assertIn('threshold',str(e))
  self.assertTrue(fallback.called)
if __name__=='__main__':unittest.main()
