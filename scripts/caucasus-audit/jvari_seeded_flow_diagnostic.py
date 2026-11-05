"""Research-only seeded D8 diagnostic; mapped channels and crop outlets are assumptions."""
import sys,json,xml.etree.ElementTree as ET
import numpy as np,rasterio
from rasterio.windows import from_bounds,transform
from rasterio.features import rasterize
from shapely.geometry import LineString,mapping
from seeded_flow_basins import flow_graph,trace_to_seeds
from geodesic_line import GeodesicLine,GEOD
root=ET.parse('jvari-osm-map.xml').getroot();nodes={v.get('id'):(float(v.get('lon')),float(v.get('lat'))) for v in root.findall('node')}
ways={}
for w in root.findall('way'):
 if w.get('id') in ('83809279','97503816'):
  ways[w.get('id')]=mapping(LineString([nodes[n.get('ref')] for n in w.findall('nd')]))
assert len(ways)==2
which=sys.argv[1]
if which=='jaxa':
 base='original/N042E044/ALPSMLC30_N042E044_';paths=[base+'DSM.tif',base+'MSK.tif',base+'STK.tif']
else:paths=['central-jvari-cop30-'+x+'.tif' for x in ('dem','EDM','FLM','WBM')]
with rasterio.open(paths[0]) as ds:
 w=from_bounds(44.42,42.48,44.49,42.53,ds.transform).round_offsets().round_lengths();aff=transform(w,ds.transform);z=ds.read(1,window=w);raw=[]
 for p in paths[1:]:
  with rasterio.open(p) as src:
   assert src.crs==ds.crs and src.transform==ds.transform and src.shape==ds.shape
   raw.append(src.read(1,window=w))
 valid=np.isfinite(z)&(z!=ds.nodata)
 if which=='jaxa':valid &= (raw[0]==0)&(raw[1]>0)
 else:valid &= (raw[0]==1)&(raw[1]==2)&(raw[2]==0)
 masks=[rasterize([(ways[k],1)],out_shape=z.shape,transform=aff,all_touched=True).astype(bool) for k in ('83809279','97503816')];seed=np.zeros(z.shape,dtype='uint8');seed[masks[0]&~masks[1]&valid]=1;seed[masks[1]&~masks[0]&valid]=2
 print('model',which,'shape',z.shape,'valid',valid.sum(),'seed_counts',[(seed==k).sum() for k in (1,2)],'overlap',(masks[0]&masks[1]).sum(),flush=True)
 filled,graph=flow_graph(z,valid,aff,ds.crs);labels,stats=trace_to_seeds(graph,valid,seed);print('label_counts',[(labels==k).sum() for k in (0,1,2,3)],'terminal_stats',stats,flush=True)
 l=GeodesicLine(json.load(open('caucasus-line.json'))['coordinates']);s=l.closest((44.45511099459589,42.50809094740639))['station_m']
 for off in range(-1000,1001,100):
  p=l.point(s+off);a=l.point(s+off-20);b=l.point(s+off+20);az=GEOD.inv(*a,*b)[0];points=[GEOD.fwd(*p,az+d,250)[:2] for d in (-90,90)];res=[]
  for xy in points:
   col,row=(~aff)*xy;col=int(col);row=int(row);res.append(int(labels[row,col]) if 0<=row<z.shape[0] and 0<=col<z.shape[1] else -1)
  print('offset',off,'labels',res,flush=True)
