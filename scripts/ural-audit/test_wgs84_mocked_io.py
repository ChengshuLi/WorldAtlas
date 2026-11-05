"""Synthetic algorithm tests with a rasterio protocol stub, not real raster I/O."""
import importlib.util,math,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from pyproj import Geod,Transformer

class Transform:
 a=.0002;b=0.;c=0.;d=0.;e=-.0002;f=.02
class Window:
 def __init__(self,left,bottom,right,top,t):
  self.col_off=math.floor((left-t.c)/t.a);self.row_off=math.floor((top-t.f)/t.e)
  self.width=round((right-left)/t.a);self.height=round((bottom-top)/t.e)
 def round_offsets(self):return self
 def round_lengths(self):return self
class Dataset:
 crs='EPSG:4326';transform=Transform();shape=(100,100);nodata=-9999
 def __init__(self,array):self.array=array
 def __enter__(self):return self
 def __exit__(self,*args):pass
 def read(self,n,window=None):return self.array.copy()
 def window_transform(self,w):return self.transform

def load(z,m,seen):
 rasterio=types.ModuleType('rasterio');windows=types.ModuleType('rasterio.windows')
 rasterio.open=lambda p:Dataset(z if p=='dsm' else m)
 def rowcol(t,lon,lat):
  seen.append((lon,lat));return math.floor((lat-t.f)/t.e),math.floor((lon-t.c)/t.a)
 rasterio.transform=types.SimpleNamespace(rowcol=rowcol)
 windows.from_bounds=lambda *args,**kwargs:Window(*args,kwargs['transform']);rasterio.windows=windows
 spec=importlib.util.spec_from_file_location('ural_wgs84_tested',Path(__file__).with_name('local_flow_screen.py'));mod=importlib.util.module_from_spec(spec)
 with patch.dict(sys.modules,{'rasterio':rasterio,'rasterio.windows':windows}):spec.loader.exec_module(mod)
 return mod

class GeodesicTests(unittest.TestCase):
 def test_cell_center_separation_is_wgs84(self):
  mod=load(None,None,[]);geod=Geod(ellps='WGS84');t=Transform()
  a=mod.cell_center(t,20,30);b=mod.cell_center(t,30,40)
  self.assertAlmostEqual(mod.cell_distance(t,(20,30),(30,40)),geod.inv(*a,*b)[2],delta=1e-8)
 def test_run_offsets_and_flows_with_mocked_raster_io(self):
  rows,cols=np.indices((100,100));z=(100-cols+2*np.abs(rows-50)).astype('float32');m=np.zeros((100,100),dtype='uint8');seen=[];mod=load(z,m,seen)
  out=mod.run('dsm','mask',(0,0,.02,.02),100,(.004,.01),(.016,.01),'EPSG:3857')
  self.assertEqual(out['distance_method'],'wgs84-ellipsoidal-geodesic-v1');self.assertEqual(out['source_geometry_crs'],'EPSG:3857');self.assertEqual(out['excluded'],0);self.assertEqual(out['same_outlet'],19)
  tx=Transformer.from_crs(4326,3857,always_xy=True);inv=Transformer.from_crs(3857,4326,always_xy=True);a=tx.transform(.004,.01);b=tx.transform(.016,.01);center=inv.transform(a[0]+.05*(b[0]-a[0]),a[1]+.05*(b[1]-a[1]));geod=Geod(ellps='WGS84')
  bearings=[]
  for point in seen[:2]:
   azi,_,distance=geod.inv(*center,*point);bearings.append(azi);self.assertAlmostEqual(distance,100,delta=.00001)
  self.assertAlmostEqual(abs((bearings[0]-bearings[1]+180)%360-180),180,delta=1e-6)
 def test_high_latitude_diagonal_slope_uses_geodesic(self):
  mod=load(None,None,[]);geod=Geod(ellps='WGS84')
  class HighLatitude: a=.01; e=-.01; f=70.005
  t=HighLatitude();east=mod.neighbor_distance(t,0,0,1);diagonal=mod.neighbor_distance(t,0,1,1)
  _,_,reference=geod.inv(0,70,.01,69.99)
  self.assertAlmostEqual(diagonal,reference,delta=1e-8)
  self.assertGreater(diagonal,east)
  self.assertGreater(100/east,100/diagonal)
 def test_outside_window_fails_before_raster_read(self):
  rows,cols=np.indices((100,100));z=(100-cols+2*np.abs(rows-50)).astype('float32');m=np.zeros((100,100),dtype='uint8');mod=load(z,m,[])
  with self.assertRaisesRegex(ValueError,'outside source grid'):
   mod.run('dsm','mask',(-.001,0,.02,.02),100,(.004,.01),(.016,.01),'EPSG:3857')
if __name__=='__main__':unittest.main()
