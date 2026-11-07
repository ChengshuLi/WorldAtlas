"""Unconditioned quality-screened D8 at the mapped Jvari crossing; research only."""
import json,xml.etree.ElementTree as E, numpy as np,rasterio
from geodesic_line import GeodesicLine,GEOD
from shapely.geometry import LineString
r=E.parse('jvari-osm-map.xml').getroot();n={v.get('id'):(float(v.get('lon')),float(v.get('lat'))) for v in r.findall('node')};w=next(v for v in r.findall('way') if v.get('id')=='83809279');coords=[n[v.get('ref')] for v in w.findall('nd')];stream=GeodesicLine(coords)
boundary=LineString(json.load(open('caucasus-line.json'))['coordinates']);intersection=LineString(coords).intersection(boundary);assert intersection.geom_type=='Point'
station=stream.closest((intersection.x,intersection.y))['station_m'];print('intersection',intersection.wkt,'station_m',station)
base='original/N042E044/ALPSMLC30_N042E044_'
with rasterio.open(base+'DSM.tif') as ds,rasterio.open(base+'MSK.tif') as a,rasterio.open(base+'STK.tif') as b:
 z=ds.read(1);valid=(a.read(1)==0)&(b.read(1)>0)&(z!=ds.nodata)&np.isfinite(z)
 for off in (-500,-300,-200,-100,-50,0,50,100,200,300,500):
  point=stream.point(station+off); rr,cc=ds.index(*point); vv=valid[rr-2:rr+3,cc-2:cc+3]; print('profile_offset',off,'height',int(z[rr,cc]),'median5',float(np.median(z[rr-2:rr+3,cc-2:cc+3])),'valid5',bool(vv.shape==(5,5) and vv.all()),'stack',int(b.read(1,window=((rr,rr+1),(cc,cc+1)))[0,0]))
 def trace(p):
  r,col=ds.index(*p);path=[]
  for _ in range(1500):
   if r<1 or col<1 or r>=z.shape[0]-1 or col>=z.shape[1]-1:return path,'tile_edge'
   if not valid[r-1:r+2,col-1:col+2].all():return path,'quality_boundary'
   xy=ds.xy(r,col);path.append(xy);best=0;target=None
   for dr in (-1,0,1):
    for dc in (-1,0,1):
     if not(dr or dc):continue
     xy2=ds.xy(r+dr,col+dc);dist=GEOD.inv(*xy,*xy2)[2];slope=(float(z[r,col])-float(z[r+dr,col+dc]))/dist
     if slope>best:best=slope;target=(r+dr,col+dc)
   if target is None:return path,'pit_or_flat'
   r,col=target
  return path,'step_cap'
 for off in (-500,-400,-300,-200,-100,-50,50,100,200,300):
  path,status=trace(stream.point(station+off));print('start_offset',off,'steps',len(path),'status',status,'crosses',len(path)>1 and LineString(path).crosses(boundary))
