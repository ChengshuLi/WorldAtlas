import json,hashlib,rasterio,numpy as np
from pyproj import Transformer,Geod
p='/tmp/ural-spring-flow-candidates-v3.jsonl';rows=[json.loads(s) for s in open(p)];c=next(x for x in rows if x['dem']=='cop')['radius_cell_square']['0']['candidate'];points=[c['interface_edge_midpoint']]+c['terrain_centers']+[[59.4185198,54.7035941]]
for name,path,h,mask,mh in [('alos','/tmp/ural-dsm.tif','542c51c1cd7f79fcf5677ed4977ba086e1864aab49e6375ad371de44ceb3488b','/tmp/ural-msk.tif','a6ad6691b1b00d61a866b6413de40ce9abd9df6d9903b61623bbc1eec0e7adf7'),('cop','/tmp/ural-copernicus-dem.tif','d1d0a6b65e0fc19695f9414fd5bcece8a2f508a6f7790c70bb20677f20be3ef6',None,None)]:
 def check(p,h):
  z=hashlib.sha256()
  with open(p,'rb') as f:
   for b in iter(lambda:f.read(1048576),b''):z.update(b)
  if z.hexdigest()!=h:raise ValueError('bad pin')
 check(path,h)
 if mask:check(mask,mh)
 with rasterio.open(path) as ds:
  tr=Transformer.from_crs(4326,ds.crs,always_xy=True);xy=[tr.transform(*p) for p in points];vals=[float(v[0]) if not np.ma.is_masked(v[0]) and np.isfinite(v[0]) else None for v in ds.sample(xy,masked=True)]
  if mask:
   with rasterio.open(mask) as md:
    mt=Transformer.from_crs(4326,md.crs,always_xy=True);mv=[int(v[0]) if not np.ma.is_masked(v[0]) else -1 for v in md.sample([mt.transform(*p) for p in points],masked=True)]
    vals=[z if m==0 else None for z,m in zip(vals,mv)]
 rises=[(i,vals[i+1]-vals[i]) for i in range(len(vals)-1) if vals[i] is not None and vals[i+1] is not None and vals[i+1]-vals[i]>.01]
 print(json.dumps({'model':name,'count':len(vals),'valid_count':sum(x is not None for x in vals),'start_z':vals[0],'end_z':vals[-1],'uphill_edges':len(rises),'uphill_sum_m':sum(v for _,v in rises),'maximum_uphill_m':max((v for _,v in rises),default=0),'limits':'nearest pixel DSM samples; vertical datums may differ; multi-pixel D8 routing uses filled elevation, not raw surface; adjacent samples and source products are not independent field surveys'},sort_keys=True))
