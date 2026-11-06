import json,numpy as np,rasterio
from shapely.geometry import LineString,Point
from geodesic_line import GeodesicLine
source=LineString(json.load(open('klukhor-gap-old-0-research.json'))['coordinates']);bridge=GeodesicLine(json.load(open('klukhor-north-gap-0-research.json'))['coordinates']);srcpts=[];altpts=[]
for s in range(0,int(bridge.length)+1,30):
 p=bridge.point(s);q=source.interpolate(source.project(Point(p)));srcpts.append((q.x,q.y));altpts.append(p)
for name in ('original/N043E041/ALPSMLC30_N043E041_DSM.tif','klukhor-cop30-DEM.tif'):
 with rasterio.open(name) as ds:
  a=np.array([x[0] for x in ds.sample(srcpts)],float);b=np.array([x[0] for x in ds.sample(altpts)],float);valid=np.isfinite(a)&np.isfinite(b)&(a!=ds.nodata)&(b!=ds.nodata);v=(b-a)[valid];print(name,'paired',len(v),'mean bridge minus current',round(float(v.mean()),1),'median',round(float(np.median(v)),1),'bridge higher',int((v>0).sum()),'lower',int((v<0).sum()),'tie',int((v==0).sum()))
base='original/N043E041/ALPSMLC30_N043E041_'
with rasterio.open(base+'MSK.tif') as ds,rasterio.open(base+'STK.tif') as st:
 for n,positions in [('current',srcpts),('bridge',altpts)]:
  m=np.array([int(x[0]) for x in ds.sample(positions)]);k=np.array([int(x[0]) for x in st.sample(positions)]);print(n,'JAXA valid',int(((((m==0)&(k>0))|(m==48))).sum()),'/',len(positions),'mask values',dict(zip(*np.unique(m,return_counts=True))))
