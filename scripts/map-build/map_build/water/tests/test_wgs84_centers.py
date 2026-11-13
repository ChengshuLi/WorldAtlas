import unittest
import numpy as np
from pyproj import Geod
from map_build.water.tests.helpers import rle
from map_build.water import shared_nearest as s
class CenterSearch(unittest.TestCase):
 def test_random_against_brute_wgs84(self):
  rng=np.random.default_rng(2026);p=np.ones((180,360),dtype=np.uint32);l=np.zeros_like(p)
  choices=rng.choice(180*360,60,replace=False)
  for j,k in enumerate(choices):p[k//360,k%360]=17;l[k//360,k%360]=17+j%3
  pairs=[(1,17,1),(2,18,2),(3,19,3)];v=s.centers_for_crop(rle(p),rle(l),(0,360,0,180),360,180,1,[17,18,19]);idx=s.make_indexes(v,pairs)
  query=rng.choice(np.flatnonzero(p.ravel()==1),100,replace=False);lat=90-(query//360+.5);lon=-180+(query%360+.5)
  actual,_,_=s.classify(lat,lon,(0,360,0,180),360,180,1,pairs,1e-5,idx)
  g=Geod(ellps='WGS84');expected=[]
  for y,x in zip(lat,lon):
   _,_,ds=g.inv(np.full(len(v['lat']),x),np.full(len(v['lat']),y),v['lon'],v['lat']);mind=[np.min(ds[v['category']==c]) for c in (17,18,19)];expected.append(1+int(np.argmin(mind)))
  self.assertEqual(actual.tolist(),expected)
 def test_coast_centers_only_and_wrap(self):
  p=np.ones((180,360),dtype=np.uint32);l=np.zeros_like(p);p[88:91,358:]=17;l[88:91,358:]=17;p[88:91,:2]=17;l[88:91,:2]=17
  v=s.centers_for_crop(rle(p),rle(l),(-2,2,88,91),360,180,1,[17]);got=set(zip(v['lat'],v['lon']))
  self.assertNotIn((.5,-179.5),got);self.assertNotIn((.5,179.5),got)
  self.assertIn((1.5,179.5),got);self.assertIn((-.5,-179.5),got)
 def test_excluded_shore_fails_closed(self):
  p=np.ones((180,360),dtype=np.uint32);l=np.zeros_like(p);p[89,4]=p[89,8]=17;l[89,4]=17;l[89,8]=18
  bounds=(4,6,88,91);pairs=[(1,17,1),(2,18,2)];v=s.centers_for_crop(rle(p),rle(l),bounds,360,180,1,[17,18]);idx=s.make_indexes(v,[pairs[0]])
  with self.assertRaises(ValueError):s.classify_wgs84([.5],[-174.5],bounds,360,180,1,pairs,1e-5,idx,band=120000)
 def test_wide_crop_and_bad_data(self):
  p=np.ones((180,360),dtype=np.uint32);l=np.zeros_like(p);p[89,1]=17;l[89,1]=17
  v=s.centers_for_crop(rle(p),rle(l),(0,359,88,91),360,180,1,[17]);self.assertEqual(len(v['lat']),1)
  with self.assertRaises(ValueError):s.centers_for_crop(rle(p),rle(l),(0,361,88,91),360,180,1,[17])
 def test_deterministic_priority_and_ambiguous_tolerance(self):
  p=np.ones((180,360),dtype=np.uint32);l=np.zeros_like(p)
  p[89,4]=p[89,6]=17;l[89,4]=17;l[89,6]=18
  pairs=[(2,18,2),(1,17,1)];v=s.centers_for_crop(rle(p),rle(l),(0,360,0,180),360,180,1,[17,18]);idx=s.make_indexes(v,pairs)
  answer,_,_=s.classify([.5],[-174.5],(0,360,0,180),360,180,1,pairs,1e-5,idx)
  self.assertEqual(answer.tolist(),[2])
  with self.assertRaisesRegex(RuntimeError,'tie threshold'):
   s.classify([.5],[-174.5],(0,360,0,180),360,180,1,pairs,0,idx)
 def test_reject_query_outside_crop(self):
  p=np.ones((180,360),dtype=np.uint32);l=np.zeros_like(p);p[89,5]=17;l[89,5]=17
  bounds=(4,7,88,91);pair=[(1,17,1)];v=s.centers_for_crop(rle(p),rle(l),bounds,360,180,1,[17]);idx=s.make_indexes(v,pair)
  with self.assertRaisesRegex(ValueError,'outside crop'):
   s.classify([.5],[-170],bounds,360,180,1,pair,1e-5,idx)
 def test_ignores_bad_land_codes_on_physical_water_cells(self):
  p=np.ones((5,5),dtype=np.uint32);l=np.zeros_like(p)
  p[2,2]=17;l[2,2]=17;l[2,3]=255
  v=s.centers_for_crop(rle(p),rle(l),(0,5,0,5),5,5,72,[17])
  self.assertEqual(list(zip(v['lat'],v['lon'])),[( -90.0,0.0)])
 def test_diagonal_contact_not_coastal(self):
  p=np.full((180,360),17,dtype=np.uint32);l=np.full_like(p,17)
  p[88,4]=1;l[88,4]=0
  v=s.centers_for_crop(rle(p),rle(l),(3,7,87,91),360,180,1,[17])
  got=set(zip(v['lat'],v['lon']))
  self.assertNotIn((.5,-174.5),got) # water is diagonally adjacent only
  self.assertIn((.5,-175.5),got)    # directly south of water
  self.assertIn((1.5,-174.5),got)   # directly east of water
if __name__=='__main__':unittest.main()
