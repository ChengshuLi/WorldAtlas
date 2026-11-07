import sys,json,math,hashlib,numpy as np
from shapely.geometry import LineString,box
from shapely.strtree import STRtree
from pyproj import Geod
from scipy.optimize import minimize_scalar
sys.path.insert(0,'landed-1b494125')
from terrain_basin_screen import checked_shapes,digest_file
p='ural-watershed-first4954.json';sha='0a1aee04c5d60fec6f039b709720f2c7e4ae7f2522d8224fdfe0d9086978ccb4'
with open(p,'rb') as f:
 if digest_file(f)!=sha:raise ValueError('line hash mismatch')
coords=json.load(open(p));features=checked_shapes('/tmp/ural-hydro-eu.zip','21797d53e0792cae047d25f0c3cfb570c7ef43700ec962b35b2ac92467e29f03','/tmp/ural-hydro-eu/hybas_eu_lev12_v1c.shp',(58.95,54.71,67.17,68.74));lines=[]
for geom,_ in features:
 for poly in getattr(geom,'geoms',[geom]):
  for ring in [poly.exterior,*poly.interiors]:
   xy=list(ring.coords)
   for a,b in zip(xy,xy[1:]):
    if a!=b:lines.append(LineString([a,b]))
tree=STRtree(lines);g=Geod(ellps='WGS84');out=[]
for i in list(range(4251,4259))+list(range(4673,4681)):
 a,b=coords[i:i+2]
 for t in (.25,.5,.75):
  lon=a[0]*(1-t)+b[0]*t;lat=a[1]*(1-t)+b[1]*t;d=.002;best=None
  for j in tree.query(box(lon-d,lat-d,lon+d,lat+d)):
   x,y=lines[j].coords
   def distance(t):return g.inv(lon,lat,x[0]+(y[0]-x[0])*t,x[1]+(y[1]-x[1])*t)[2]
   q=min(distance(0),distance(1),float(minimize_scalar(distance,bounds=(0,1),method='bounded',options={'xatol':1e-13}).fun))
   if best is None or q<best:best=q
  out.append({'source_segment_zero_based':i,'fraction':t,'nearest_wgs84_m':best})
print(json.dumps({'status':'research-only','selected_line_sha256':sha,'candidate_prefilter_degrees':.002,'method':'minimize WGS84 point-to-coordinate-linear source edge within angular prefilter, plus endpoints; no global/unimodality guarantee','samples':out,'max_wgs84_m':max(x['nearest_wgs84_m'] for x in out if x['nearest_wgs84_m'] is not None)},sort_keys=True))
