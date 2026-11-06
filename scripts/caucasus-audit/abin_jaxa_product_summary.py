import json,math
import numpy as np
from affine import Affine
from pyproj import Geod
from geodesic_line import GeodesicLine
G=Geod(ellps='WGS84')
line=GeodesicLine(json.load(open('west-abin-jaxa-product-cut-research.json'))['coordinates'])
models={}
for name in ('jaxa','srtm','copernicus'):
 v=np.load(('west-stream-seeded-jaxa-product-filled-abin-output.npz' if name=='jaxa' else 'west-stream-seeded-'+name+'-abin-output.npz')); models[name]=(v['labels'],~Affine(*v['affine'][:6]))
def pair(model,pts):
 arr, inv=model; out=[]
 for p in pts:
  c,r=inv*p;r,c=math.floor(r),math.floor(c)
  out.append(int(arr[r,c]) if 0<=r<arr.shape[0] and 0<=c<arr.shape[1] else -1)
 return out
from collections import Counter
counts={w:{n:Counter() for n in models} for w in (10,100,250)}
for s in range(0,int(line.length)+1,200):
 p=line.point(s)
 for w in counts:
  az=G.inv(*line.point(s-w),*line.point(s+w))[0]
  pts=[G.fwd(*p,az+a,100)[:2] for a in (-90,90)]
  for n,m in models.items(): counts[w][n][tuple(pair(m,pts))]+=1
for w,model in counts.items():
 print(w,{n:{'pass':int(c[(1,2)]),'total':sum(c.values()),'other':dict((str(k),int(v)) for k,v in c.items() if k!=(1,2))} for n,c in model.items()})
