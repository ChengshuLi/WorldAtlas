"""Unconditioned WGS84 D8 cross-boundary probe near Klukhor, research only."""
import sys,json,numpy as np,rasterio
from shapely.geometry import LineString
from geodesic_line import GeodesicLine,GEOD
source=json.load(open('caucasus-line.json'))['coordinates'];line=GeodesicLine(source);bound=LineString(source);s=line.closest((41.86776666666667,43.244283333333335))['station_m'];p=line.point(s);az=GEOD.inv(*line.point(s-20),*line.point(s+20))[0]
if sys.argv[1]=='jaxa':
 base='original/N043E041/ALPSMLC30_N043E041_';paths=[base+'DSM.tif',base+'MSK.tif',base+'STK.tif']
else:paths=['klukhor-cop30-'+x+'.tif' for x in ('DEM','EDM','FLM','WBM')]
with rasterio.open(paths[0]) as ds:
 z=ds.read(1);data=[]
 for filename in paths[1:]:
  with rasterio.open(filename) as v:
   assert v.crs==ds.crs and v.transform==ds.transform and v.shape==ds.shape;data.append(v.read(1))
 valid=np.isfinite(z)&(z!=ds.nodata)
 if sys.argv[1]=='jaxa':valid &= (data[0]==0)&(data[1]>0)
 else:valid &= (data[0]==1)&(data[1]==2)&(data[2]==0)
 def trace(point):
  r,c=ds.index(*point);pts=[]
  for _ in range(1500):
   if r<1 or c<1 or r>=z.shape[0]-1 or c>=z.shape[1]-1:return pts,'tile_edge'
   if not valid[r-1:r+2,c-1:c+2].all():return pts,'quality_boundary'
   xy=ds.xy(r,c);pts.append(xy);best=0;dest=None
   for dr in (-1,0,1):
    for dc in (-1,0,1):
     if not(dr or dc):continue
     xy2=ds.xy(r+dr,c+dc);d=GEOD.inv(*xy,*xy2)[2];slope=(float(z[r,c])-float(z[r+dr,c+dc]))/d
     if slope>best:best=slope;dest=(r+dr,c+dc)
   if dest is None:return pts,'pit_or_flat'
   r,c=dest
  return pts,'step_cap'
 for off in (-500,-250,-100,100,250,500):
  pts,status=trace(GEOD.fwd(*p,az+(-90 if off<0 else 90),abs(off))[:2]);print('offset',off,'count',len(pts),'status',status,'crosses',len(pts)>1 and LineString(pts).crosses(bound),flush=True)
