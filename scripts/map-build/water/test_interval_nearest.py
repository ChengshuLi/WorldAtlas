import unittest
from unittest.mock import patch
import numpy as np
import shared_nearest as s
import interval_nearest as x
class Intervals(unittest.TestCase):
 def test_exact_midpoint_minima_resolve_loose_spherical_bounds(self):
  width=131072;height=54614;step=360/width;pairs=[('a',17,1),('b',18,2)]
  lat=np.array([0.,0.]);lon=np.array([0.,.05]);cat=np.array([17,18],dtype='u1')
  indexes=s.make_indexes({'lat':lat,'lon':lon,'mids':s.unit(lat,lon),'category':cat},pairs)
  original=s.nearest_class_bounds
  def loose(lats,lons,points,pairs,indexes):
   lower,best,_=original(lats,lons,points,pairs,indexes)
   return lower,best,np.full(len(lats),1e9)
  source=[(72000,72100)];bounds=(0,width,0,height);row=30000
  with patch.object(s,'nearest_class_bounds',side_effect=loose):
   out,stats=x.classify_row(row,source,bounds,width,height,step,pairs,1e-5,indexes,leaf=1)
  self.assertGreater(stats['exact_interval_probes'],0)
  self.assertEqual(stats['certified_cells'],100)
  self.assertEqual(stats['leaf_cells'],0)
  self.assertEqual(out,[(72000,72100,2)])
 def test_optimistic_gap_gate_skips_impossible_exact_probes(self):
  lower=np.array([[1e6,1e6+500.]])
  self.assertFalse(x.exact_certificate_possible(lower,np.array([0]),np.array([1e6+100]),np.array([5e4]),1e-5,np.array([np.inf]))[0])
  self.assertTrue(x.exact_certificate_possible(lower,np.array([0]),np.array([1e6+100]),np.array([10.]),1e-5,np.array([np.inf]))[0])
 def test_global_random_and_seams(self):
  rng=np.random.default_rng(674); width=360;height=180;step=1.;pairs=[('a',17,1),('b',18,2),('c',19,3)]
  lat=rng.uniform(-89,89,600);lon=rng.uniform(-180,180,600);cat=np.tile([17,18,19],200).astype('u1')
  idx=s.make_indexes({'lat':lat,'lon':lon,'mids':s.unit(lat,lon),'category':cat},pairs)
  for y in [0,1,23,89,90,155,178,179]:
   ints=[(0,41),(51,310),(319,360)]; got,_=x.classify_row(y,ints,(0,360,0,180),width,height,step,pairs,1e-5,idx,leaf=8)
   out=np.zeros(width,dtype='u1')
   for a,b,c in got:out[a:b]=c
   for a,b in ints:
    xs=np.arange(a,b);ref=s.classify(np.full(b-a,90-(y+.5)*step),-180+(xs+.5)*step,(0,360,0,180),width,height,step,pairs,1e-5,idx)[0]
    np.testing.assert_array_equal(ref,out[a:b])
 def test_tie_priority_and_wrapped_crop(self):
  pairs=[('b',18,2),('a',17,1)]
  lat=np.array([.5,.5]);lon=np.array([-.5,1.5]);cat=np.array([17,18],dtype='u1')
  idx=s.make_indexes({'lat':lat,'lon':lon,'mids':s.unit(lat,lon),'category':cat},pairs)
  out,_=x.classify_row(89,[(175,187)],(160,200,70,110),360,180,1.,pairs,1e-5,idx,leaf=2)
  dense=np.zeros(12,dtype='u1')
  for a,b,c in out:dense[a-175:b-175]=c
  xs=np.arange(175,187);ref=s.classify(np.full(12,.5),-180+(xs+.5),(160,200,70,110),360,180,1.,pairs,1e-5,idx)[0]
  np.testing.assert_array_equal(dense,ref)
  self.assertEqual(dense[5],2)
  with self.assertRaises(ValueError):x.classify_row(89,[(0,1)],(160,200,70,110),360,180,1.,pairs,1e-5,idx)
 def test_invalid_input_and_full_fallback(self):
  pairs=[('a',17,1),('b',18,2)];calls=[]
  def full(lat,lon):
   calls.append(len(lat));return np.ones(len(lat),dtype='u1'),0,len(lat)
  with self.assertRaises(ValueError):x.classify_row(89,[(0.2,4)],(0,360,0,180),360,180,1.,pairs,1e-5,{})
  with self.assertRaises(ValueError):x.classify_row(89,[(0,4)],(0,360,0,180),360,180,1.,pairs,-1,{})
  with self.assertRaises(ValueError):x.classify_row(89,[(0,4)],(0,360,0,180),360,180,1.,pairs,True,{})
  with self.assertRaises(ValueError):x.classify_row(89,[(0,4)],(0,360,0,180),360,180,True,pairs,1e-5,{})
  with self.assertRaises(ValueError):x.classify_row(89,[(0,4)],(0,360,0,180),360,180,1.,pairs,1e-5,{})
  out,st=x.classify_row(89,[(0,4)],(160,200,70,110),360,180,1.,pairs,1e-5,{},point_classifier=full)
  self.assertEqual(out,[(0,4,1)]);self.assertEqual(calls,[4]);self.assertEqual(st['leaf_cells'],4)
  def badcount(lat,lon):return np.ones(len(lat),dtype='u1'),0,0
  with self.assertRaises(ValueError):x.classify_row(89,[(0,4)],(160,200,70,110),360,180,1.,pairs,1e-5,{},point_classifier=badcount)
  def bad(lat,lon):return np.full(len(lat),99,dtype='u1'),0,len(lat)
  with self.assertRaises(ValueError):x.classify_row(89,[(0,4)],(160,200,70,110),360,180,1.,pairs,1e-5,{},point_classifier=bad)
 def test_actual_wrapped_streamed_fallback(self):
  from wrapped_bounds import StreamedWrappedClassifier
  import streamed_shore_fallback as fallback
  from scipy.spatial import cKDTree
  def dataset(lats,lons):
   lat=np.array(lats,dtype=float);lon=np.array(lons,dtype=float)
   data={'lat':lat,'lon':lon,'mids':s.unit(lat,lon),'category':np.ones(len(lat),dtype='u1')}
   return data,cKDTree(data['mids'])
  pairs=[('a',17,1),('b',18,2)]
  full={17:dataset([0,20,-30],[179,0,40]),18:dataset([0,20,-30],[-179,40,0])}
  narrow={17:dataset([0],[179]),18:dataset([0],[-179])}
  wrapper=StreamedWrappedClassifier(s.classify,fallback.classify_one,(350,370,70,110),(0,360,0,180),360,180,1.,pairs,.01,narrow,lambda code: iter([full[code][0]]))
  row=69;lo,hi=178,183
  out,stats=x.classify_row(row,[(lo,hi)],(350,370,70,110),360,180,1.,pairs,.01,narrow,point_classifier=wrapper.classify)
  dense=np.zeros(hi-lo,dtype='u1')
  for a,b,c in out:dense[a-lo:b-lo]=c
  xs=np.arange(lo,hi);lats=np.full(len(xs),20.5);lons=-180+(xs+.5)
  ref=s.classify(lats,lons,(0,360,0,180),360,180,1.,pairs,.01,full)[0]
  np.testing.assert_array_equal(dense,ref)
  self.assertEqual(stats['leaf_cells'],5);self.assertEqual(wrapper.fallback_cells,5);self.assertEqual(stats['exact_cells'],5);self.assertEqual(stats['bounded_cells'],0)
 def test_wgs84_metric_bounds_over_global_pairs(self):
  rng=np.random.default_rng(347991);n=6000
  lat1=rng.uniform(-90,90,n);lon1=rng.uniform(-180,180,n)
  lat2=rng.uniform(-90,90,n);lon2=rng.uniform(-180,180,n)
  lat1=np.r_[lat1,[90.,-90.,89.999999,-89.999999,0.,0.]]
  lon1=np.r_[lon1,[0.,0.,179.999999,-179.999999,179.999999,-179.999999]]
  lat2=np.r_[lat2,[89.999999,-89.999999,89.999998,-89.999998,0.,0.]]
  lon2=np.r_[lon2,[180.,-180.,-179.999999,179.999999,-179.999999,179.999999]]
  a=s.unit(lat1,lon1);b=s.unit(lat2,lon2);chord=np.linalg.norm(a-b,axis=1)
  angles=2*np.arcsin(np.clip(chord/2,0,1));eligible=chord<1.99
  distances=s.geodesic_distances(lon1,lat1,lon2,lat2)
  lo=np.maximum(0,s.MIN_RADIUS*angles-.01);hi=x.MAX_RADIUS*angles+.01
  self.assertTrue(np.all(lo[eligible]<=distances[eligible]))
  self.assertTrue(np.all(distances[eligible]<=hi[eligible]))
 def test_native_grid_row_intervals_against_point_classifier(self):
  rng=np.random.default_rng(415);width=131072;height=54614;step=360/width;pairs=[('a',17,1),('b',18,2)]
  for y in (0,10000,32767,54613):
   lat0=90-(y+.5)*step;lat=np.clip(lat0+rng.uniform(-3,3,30),-90,90);lon=rng.uniform(-180,180,30);cat=np.tile([17,18],15).astype('u1')
   indexes=s.make_indexes({'lat':lat,'lon':lon,'mids':s.unit(lat,lon),'category':cat},pairs)
   source=[(0,257),(32497,32999),(130572,131072)];bounds=(0,width,0,height)
   out,_=x.classify_row(y,source,bounds,width,height,step,pairs,1e-5,indexes,leaf=8)
   for a,b in source:
    q=np.arange(a,b);ref=s.classify(np.full(len(q),lat0),-180+(q+.5)*step,bounds,width,height,step,pairs,1e-5,indexes)[0]
    got=np.zeros(b-a,dtype='u1')
    for left,right,code in out:
     lo=max(a,left);hi=min(b,right)
     if lo<hi:got[lo-a:hi-a]=code
    np.testing.assert_array_equal(got,ref)
 def test_overlap_rejected(self):
  with self.assertRaises(ValueError):x.classify_row(0,[(0,4),(3,5)],(0,360,0,180),360,180,1.,[],0,{})
if __name__=='__main__':unittest.main()
