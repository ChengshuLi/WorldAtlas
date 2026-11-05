import json,math,numpy as np
from affine import Affine
from pyproj import Geod
from geodesic_line import GeodesicLine
G=Geod(ellps='WGS84');src=GeodesicLine(json.load(open('caucasus-line.json'))['coordinates']);alt=GeodesicLine(json.load(open('west-abin-splice-cut-research.json'))['coordinates']);data=[]
for n in ('jaxa','copernicus','srtm'):
 f=np.load('west-stream-seeded-'+n+'-abin-output.npz');data.append((n,f['labels'],~Affine(*f['affine'][:6])))
def pair(line,s):
 p=line.point(s);a=line.point(s-10);b=line.point(s+10);az=G.inv(*a,*b)[0];xy=[G.fwd(*p,az+t,250)[:2] for t in (-90,90)];out={}
 for n,z,inv in data:
  v=[]
  for pt in xy:
   c,r=inv*pt;r,c=math.floor(r),math.floor(c);v.append(int(z[r,c]) if 0<=r<z.shape[0] and 0<=c<z.shape[1] else -1)
  out[n]=v
 return out
for name,p,dsrc,dalt in [('west',alt.point(0),-300,300),('east',alt.point(alt.length),300,-300)]:
 s=src.closest(p)['station_m']; print(name,'source',pair(src,s+dsrc),'candidate',pair(alt,0+dalt if name=='west' else alt.length+dalt))
