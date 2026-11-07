import json,sys,hashlib,numpy as np
from shapely.geometry import LineString
from shapely.strtree import STRtree
from pyproj import Geod
sys.path.insert(0,'landed-1b494125')
from terrain_basin_screen import checked_shapes
from spring_connector_graph import basin_labels
features=checked_shapes('/tmp/ural-hydro-eu.zip','21797d53e0792cae047d25f0c3cfb570c7ef43700ec962b35b2ac92467e29f03','/tmp/ural-hydro-eu/hybas_eu_lev12_v1c.shp',(58.95,54.71,67.17,68.74));raw=[]
for geom,_ in features:
 for poly in getattr(geom,'geoms',[geom]):
  for ring in [poly.exterior,*poly.interiors]:
   xy=list(ring.coords)
   for a,b in zip(xy,xy[1:]):
    if a!=b:raw.append(LineString([a,b]))
tree=STRtree(raw);g=Geod(ellps='WGS84');basins=[('/tmp/ural-hydro-eu.zip','21797d53e0792cae047d25f0c3cfb570c7ef43700ec962b35b2ac92467e29f03','/tmp/ural-hydro-eu/hybas_eu_lev12_v1c.shp'),('/tmp/ural-hydro-si.zip','67ea00df7d14a397f8f78e5b1dc31dcca036018ccbcb36e007ce6854b91d71bd','/tmp/ural-hydro-si/hybas_si_lev12_v1c.shp')]
for name,path,h,bounds in [('00','/tmp/ural-gap00-12km-nearest.tif','3dbc4da15948791a70b78346eaba7174ccb464226bf9adf292184757f7c6af6b',[59.70,64.10,59.83,64.18]),('02','/tmp/ural-gap02-16km-nearest.tif','dc04a55cdc1b742a21dfdb1f050f493c621a6ae0f3f66f7cdd0042c2cb893635',[59.40,61.92,59.52,62.02])]:
 p='/tmp/ural-gap'+name+'-arctic-intersection-route.json';v=json.load(open(p));labels,t,geo,_=basin_labels(path,h,None,None,basins,bounds,[2120043720,3120001840,9999999999],15);out={}
 for key in ('north','south'):
  edge=v[key]['edge'];pts=[geo.transform(*(t*(z[1],z[0]))) for z in edge];e=LineString(pts);hits=[]
  for j in tree.query(e):
   pnt=e.intersection(raw[j]);ps=[pnt] if pnt.geom_type=='Point' else list(pnt.geoms) if pnt.geom_type=='MultiPoint' else []
   for p0 in ps:
    d=g.inv(*v[key]['point'],p0.x,p0.y)[2];hits.append((d,[p0.x,p0.y],list(raw[j].coords)))
  hits.sort(key=lambda a:a[0]);out[key]={'n':len(hits),'closest':hits[:2]}
 print(json.dumps({'gap':name,'raw_edge_crossings':out},sort_keys=True),flush=True)
