import unittest
from unittest.mock import patch
import numpy as np
from map_build.water import coastal_rect as rect
from map_build.water import coastal_core as core
from map_build.water import shared_nearest as shore

def rle(grid):
 rows=[0];runs=[]
 for row in grid:
  ends=np.r_[np.flatnonzero(row[1:]!=row[:-1])+1,len(row)]
  for end in ends:runs.extend([end,row[end-1]])
  rows.append(len(runs)//2)
 return np.asarray(rows,dtype=np.uint32),np.asarray(runs,dtype=np.uint32)

class RectangleTest(unittest.TestCase):
 def test_random_queries_at_pole_and_seam(self):
  rng=np.random.default_rng(6443);w=131072;h=54614;step=360/w;pairs=[(1,17,1),(2,18,2),(3,19,3)];bounds=(0,w,0,h)
  for y0 in (0,16384,32768,50000):
   for x0 in (0,60000,w-64):
    nr,nc=16,64;water=rng.random((nr,nc))<.6;lat0=90-(y0+nr/2)*step;lon0=-180+(x0+nc/2)*step
    slat=np.clip(lat0+rng.uniform(-.4,.4,60),-90,90);slon=((lon0+rng.uniform(-.4,.4,60)+180)%360)-180
    centers={'lat':slat,'lon':slon,'mids':shore.unit(slat,slon),'category':rng.choice(np.array([17,18,19],dtype=np.uint8),60)};idx=core.index_present(centers,pairs)
    yy,xx=np.nonzero(water);lat=90-(y0+yy+.5)*step;lon=-180+(x0+xx+.5)*step
    expected,_=core.classify(lat,lon,bounds,w,h,step,pairs,.00001,22224,.000001,idx)
    for block in (1,7,32,64):
     out,stats=rect.classify(water,x0,y0,bounds,w,h,step,pairs,.00001,22224,.000001,idx,block)
     np.testing.assert_array_equal(out[yy,xx],expected);self.assertEqual(stats['bounded']+stats['exact'],len(yy))
 def test_tie_and_omitted_shore_fallback(self):
  w=131072;h=54614;step=360/w;x=65536;y=32768;lat=90-(y+.5)*step;lon=-180+(x+.5)*step;water=np.ones((1,1),dtype=bool);pairs=[(1,17,1),(2,18,2)];bounds=(0,w,0,h)
  east=shore.GEOD.fwd(lon,lat,90,5000);west=shore.GEOD.fwd(lon,lat,-90,5000);slat=np.array([east[1],west[1]]);slon=np.array([east[0],west[0]]);idx=core.index_present({'lat':slat,'lon':slon,'mids':shore.unit(slat,slon),'category':np.array([17,18],dtype=np.uint8)},pairs)
  with patch.object(core,'classify',wraps=core.classify) as fallback:
   out,stats=rect.classify(water,x,y,bounds,w,h,step,pairs,.00001,22224,.000001,idx)
   self.assertTrue(fallback.called);self.assertEqual(out[0,0],1);self.assertEqual(stats['exact'],1)
  with self.assertRaises(ValueError):rect.classify(water,x,y,(x,x+1,y,y+1),w,h,step,pairs,.00001,22224,.000001,idx)
 def test_band_threshold_retains_reference_behavior(self):
  w=131072;h=54614;step=360/w;x=65536;y=32768;lat=90-(y+.5)*step;lon=-180+(x+.5)*step;pairs=[(1,17,1)];bounds=(0,w,0,h)
  target=shore.GEOD.fwd(lon,lat,90,22224);slat=np.array([target[1]]);slon=np.array([target[0]]);idx=core.index_present({'lat':slat,'lon':slon,'mids':shore.unit(slat,slon),'category':np.array([17],dtype=np.uint8)},pairs)
  try:expected,_=core.classify(np.array([lat]),np.array([lon]),bounds,w,h,step,pairs,.00001,22224,0.,idx)
  except RuntimeError as e:
   with self.assertRaisesRegex(RuntimeError,str(e)):rect.classify(np.ones((1,1),dtype=bool),x,y,bounds,w,h,step,pairs,.00001,22224,0.,idx)
  else:
   out,_=rect.classify(np.ones((1,1),dtype=bool),x,y,bounds,w,h,step,pairs,.00001,22224,0.,idx);np.testing.assert_array_equal(out.ravel(),expected)
 def test_radius_bounds_inverse_wgs84(self):
  rng=np.random.default_rng(103)
  for _ in range(1000):
   lat=rng.uniform(-90,90);dy=rng.uniform(0,min(2,90-abs(lat)));dx=rng.uniform(0,2);qlat=lat+rng.uniform(-dy,dy);qlon=rng.uniform(-dx,dx);rmax=shore.A/(1-shore.F);radius=np.hypot(rmax*np.deg2rad(dy),rmax*np.cos(np.deg2rad(max(0,abs(lat)-dy)))*np.deg2rad(dx))+.01
   self.assertLessEqual(shore.GEOD.inv(0.,lat,qlon,qlat)[2],radius)
 def test_rle_shores_match_dense_wrapped_and_full_width(self):
  rng=np.random.default_rng(49303)
  for case in range(50):
   w=int(rng.integers(16,80));h=w//2;step=360/w;p=np.where(rng.random((h,w))<rng.uniform(.02,.98),1,17);l=np.where(p==17,rng.integers(17,23,(h,w)),0);physical=rle(p);land=rle(l)
   if case%5==0:x0=0;x1=w
   else:x0=int(rng.integers(-w,w));x1=x0+int(rng.integers(1,w+1))
   y0=int(rng.integers(0,h));y1=int(rng.integers(y0+1,h+1));bounds=(x0,x1,y0,y1);codes=list(map(int,rng.choice(np.arange(17,23),size=int(rng.integers(1,7)),replace=False)))
   try:expected=shore.centers_for_crop(physical,land,bounds,w,h,step,codes)
   except ValueError as e:
    if str(e)!='no participant shorelines in crop':raise
    with self.assertRaisesRegex(ValueError,'no participant shorelines in crop'):rect.centers_for_crop(physical,land,bounds,w,h,step,codes)
    continue
   actual=rect.centers_for_crop(physical,land,bounds,w,h,step,codes)
   for key in expected:np.testing.assert_array_equal(actual[key],expected[key])
 def test_rejects_invalid_latitude(self):
  with self.assertRaisesRegex(ValueError,'latitude'):
   rect.classify(np.ones((1,1),dtype=bool),0,200,(0,360,0,360),360,360,1,[],0,22224,0,{})

if __name__=='__main__':unittest.main()
