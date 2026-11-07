"""Five-pixel medians and quality masks near Klukhor; diagnostic only."""
import numpy as np,rasterio,json
from geodesic_line import GeodesicLine,GEOD
line=GeodesicLine(json.load(open('caucasus-line.json'))['coordinates']);s=line.closest((41.86776666666667,43.244283333333335))['station_m'];q=line.point(s);az=GEOD.inv(*line.point(s-20),*line.point(s+20))[0]
def evalset(kind,ds,masks):
 for d in (100,250,500):
  pts=[GEOD.fwd(*q,az-90,d)[:2],q,GEOD.fwd(*q,az+90,d)[:2]];out=[]
  for p in pts:
   r,c=ds.index(*p);w=((r-2,r+3),(c-2,c+3));z=ds.read(1,window=w);v=[m.read(1,window=w) for m in masks]
   valid=((v[0]==0)&(v[1]>0)) if kind=='jaxa' else ((v[0]==1)&(v[1]==2)&(v[2]==0))
   out.append({'center':float(z[2,2]),'median5':float(np.median(z)),'valid5':bool(valid.shape==(5,5) and valid.all()),'quality_center':[int(x[2,2]) for x in v]})
  print(kind,'offset_m',d,out)
base='original/N043E041/ALPSMLC30_N043E041_'
with rasterio.open(base+'DSM.tif') as ds,rasterio.open(base+'MSK.tif') as a,rasterio.open(base+'STK.tif') as b:evalset('jaxa',ds,[a,b])
with rasterio.open('klukhor-cop30-DEM.tif') as ds,rasterio.open('klukhor-cop30-EDM.tif') as a,rasterio.open('klukhor-cop30-FLM.tif') as b,rasterio.open('klukhor-cop30-WBM.tif') as c:evalset('copernicus',ds,[a,b,c])
