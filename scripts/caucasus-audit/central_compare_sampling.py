import sys,json,math
import numpy as np
from affine import Affine
from pyproj import Geod
from collections import Counter
from geodesic_line import GeodesicLine
G=Geod(ellps='WGS84');d=np.load(sys.argv[1]);L=d['labels'];inv=~Affine(*d['affine'][:6])
for path in sys.argv[2:]:
 line=GeodesicLine(json.load(open(path))['coordinates']);print(path,'length',round(line.length))
 for offset in (100,250,500):
  count=Counter()
  for s in range(0,int(line.length)+1,100):
   p=line.point(s);az=G.inv(*line.point(s-100),*line.point(s+100))[0];vals=[]
   for x in (-90,90):
    q=G.fwd(*p,az+x,offset)[:2];c,r=inv*q;r,c=math.floor(r),math.floor(c);vals.append(int(L[r,c]) if 0<=r<L.shape[0] and 0<=c<L.shape[1] else -1)
   count[tuple(vals)]+=1
  print(offset,dict(count))
