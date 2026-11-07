"""Unselected divide sample with WGS84 distances and research seed raster labels."""
import json,math,numpy as np
from collections import Counter
from affine import Affine
from pyproj import Geod
from geodesic_line import GeodesicLine
G=Geod(ellps='WGS84');line=GeodesicLine(json.load(open('west-abin-splice-second-cut-research.json'))['coordinates']);data=[]
for n in ('jaxa','copernicus','srtm'):
 f=np.load('west-stream-seeded-'+n+'-abin-output.npz');data.append((n,f['labels'],~Affine(*f['affine'][:6])))
for offset in [100,250,500]:
 counts={n:Counter() for n,_,_ in data};stations=range(0,int(line.length)+1,200)
 for s in stations:
  p=line.point(s); a=line.point(s-10);b=line.point(s+10); az=G.inv(*a,*b)[0]; pts=[G.fwd(*p,az+angle,offset)[:2] for angle in (-90,90)]
  for n,arr,inv in data:
   vals=[]
   for xy in pts:
    c,r=inv*xy;r,c=math.floor(r),math.floor(c);vals.append(int(arr[r,c]) if 0<=r<arr.shape[0] and 0<=c<arr.shape[1] else -1)
   counts[n][tuple(vals)]+=1
 print(offset, {k:dict(v) for k,v in counts.items()})
