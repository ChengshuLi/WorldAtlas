"""Unselected eastern splice: seed-group screening at the actual intersections."""
import json,math,numpy as np
from affine import Affine
from pyproj import Geod
from geodesic_line import GeodesicLine
G=Geod(ellps='WGS84');src=GeodesicLine(json.load(open('caucasus-line.json'))['coordinates']);cut=GeodesicLine(json.load(open('east-connected-splice-cut-research.json'))['coordinates']);data=[]
for n,fn in [('jaxa','east-stream-seeded-dem-broad-output.npz'),('copernicus90','east-stream-seeded-copernicus90-output.npz')]:
 f=np.load(fn);data.append((n,f['labels'],~Affine(*f['affine'][:6])))
def pair(line,s):
 p=line.point(s);az=G.inv(*line.point(s-10),*line.point(s+10))[0];points=[G.fwd(*p,az+a,250)[:2] for a in (-90,90)];out={}
 for n,z,inv in data:
  val=[]
  for xy in points:
   c,r=inv*xy;r,c=math.floor(r),math.floor(c);val.append(int(z[r,c]) if 0<=r<z.shape[0] and 0<=c<z.shape[1] else -1)
  out[n]=val
 return out
for n,s,sgn in [('west',0,1),('east',cut.length,-1)]:
 p=cut.point(s);ss=src.closest(p)['station_m'];print(n,'source_station',ss,'coordinate',p)
 for delta in (100,300,500,1000):
  print('dist',delta,'source',pair(src,ss-sgn*delta),'candidate',pair(cut,s+sgn*delta))
