"""Research-only screen; requires locally regenerated experimental labels and geometry.

This reports samples, not an accepted line or a field-verified watershed.
"""
import json,math,numpy as np
from affine import Affine
from pyproj import Geod
from geodesic_line import GeodesicLine
from shapely.geometry import LineString,shape
G=Geod(ellps='WGS84'); coords=json.load(open('caucasus-line.json'))['coordinates']; source=GeodesicLine(coords[107:210]);feature=json.load(open('west-seeded-divide-srtm-abin-research.json'))['features'][0]; candidate=GeodesicLine(feature['geometry']['coordinates']); p=(38.31791666666666,44.59583333333336); ss=source.closest(p)['station_m'];cs=candidate.closest(p)['station_m'];print('stations',ss,cs,'distance',candidate.closest(p)['distance_m'])
rasters=[]
for n in ('jaxa','copernicus','srtm'):
 f=np.load('west-stream-seeded-'+n+'-abin-output.npz');rasters.append((n,f['labels'],~Affine(*f['affine'][:6])))
def pair(line,s):
 a,b=line.point(s-10),line.point(s+10); p=line.point(s); az=G.inv(*a,*b)[0];pts=[G.fwd(*p,az+z,250)[:2] for z in (-90,90)]; result=[]
 for name,arr,inv in rasters:
  val=[]
  for xy in pts:
   c,r=inv*xy;r,c=math.floor(r),math.floor(c);val.append(int(arr[r,c]) if 0<=r<arr.shape[0] and 0<=c<arr.shape[1] else -1)
  result.append(name+str(tuple(val)))
 return ' '.join(result)
for n,line,s in [('source',source,ss),('candidate',candidate,cs)]:
 for d in (-2000,-1500,-1000,-500,-300,-100,0,100,300,500,1000,1500,2000):
  if 0<=s+d<=line.length:print(n,d,pair(line,s+d))
