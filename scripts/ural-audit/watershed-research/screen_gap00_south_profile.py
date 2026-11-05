import sys,json,hashlib,math
import numpy as np,rasterio
from pyproj import Transformer
sys.path.insert(0,'landed-1b494125')
from projected_route import ProjectedRoute,GEOD
line='/tmp/ural-gap00-15m-entire-route.json'
if hashlib.sha256(open(line,'rb').read()).hexdigest() != 'a993a0bf22bf43ab9df7345b007463c713207d535290f969ee1ed72e69192889': raise ValueError('route hash mismatch')
route=ProjectedRoute(json.load(open(line)),'EPSG:3413');point=route.point(route.length)[:2];p0=route.point(route.length-50)[:2];az,_,_=GEOD.inv(*p0,*point)
products=[('arctic','/tmp/ural-gap00-12km-nearest.tif','3dbc4da15948791a70b78346eaba7174ccb464226bf9adf292184757f7c6af6b'),('copernicus','/tmp/ural-gap00-cop-30m-bilinear.tif','d661fee6218f9198f48cf3505a5303a4942cec602747fb82af3571c9548e4a86'),('alos','/tmp/ural-gap00-jaxa-30m-masked.tif','49bbd6b4413d991ebb871b9fb77dd339f30f50c890499a555c5c346bd6f4b14a')];out={}
for name,p,h in products:
 with open(p,'rb') as f:
  if hashlib.sha256(f.read()).hexdigest()!=h:raise ValueError('bad digest '+name)
 with rasterio.open(p) as ds:
  tr=Transformer.from_crs(4326,ds.crs,always_xy=True); offsets=list(range(-250,251,5)); coords=[tr.transform(*GEOD.fwd(*point,az-90,o)[:2]) for o in offsets]; vals=[]
  for v in ds.sample(coords,masked=True):
   z=v[0];vals.append(None if np.ma.is_masked(z) or not np.isfinite(z) or (ds.nodata is not None and z==ds.nodata) else float(z))
  ranges={}
  for half in (50,100,250):
   z=[(v,o) for v,o in zip(vals,offsets) if abs(o)<=half and v is not None];best=max(v for v,o in z);ranges[half]={'max_elevation':round(best,2),'offsets_at_max_m':[o for v,o in z if abs(v-best)<1e-6],'center_elevation':round(vals[50],2) if vals[50] is not None else None,'valid_samples':len(z)}
  out[name]={'raster_sha256':h,'ranges':ranges,'nodata':ds.nodata,'crs':str(ds.crs),'resolution':ds.res}
print(json.dumps({'method':'WGS84 cross section at gap00 southern anchor; tangent is chord from route point 50m upstream; nearest pixel raster samples; vertical datums/resolution may differ','point':point,'azimuth_degrees':az,'outputs':out},indent=2))
