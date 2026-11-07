"""Compare current Klukhor boundary with JAXA-product modeled drainage."""
import json,xml.etree.ElementTree as E
from collections import defaultdict,deque,Counter
import numpy as np,rasterio
from rasterio.windows import from_bounds,transform
from rasterio.features import rasterize
from shapely.geometry import LineString,mapping
from seeded_flow_basins import flow_graph,trace_to_seeds
from geodesic_line import GeodesicLine,GEOD
root=E.parse('klukhor-broad-osm-research.xml').getroot();nodes={v.get('id'):(float(v.get('lon')),float(v.get('lat'))) for v in root.findall('node')};ways={};reverse=defaultdict(set)
for way in root.findall('way'):
 tags={v.get('k'):v.get('v') for v in way.findall('tag')};ids=[v.get('ref') for v in way.findall('nd')]
 if tags.get('waterway') not in ('river','stream') or len(ids)<2 or any(i not in nodes for i in ids):continue
 ways[way.get('id')]=ids
 for a,b in zip(ids,ids[1:]):reverse[b].add(a)
def ancestors(ids):
 seen=set(ids);todo=deque(ids)
 while todo:
  for p in reverse[todo.popleft()]:
   if p not in seen:seen.add(p);todo.append(p)
 return seen
reach=[ancestors(ways[k]) for k in ('86306314','86320040')];groups=[[],[]]
for wid,ids in ways.items():
 matches=[i for i,r in enumerate(reach) if ids[-1] in r]
 if len(matches)==1:groups[matches[0]].append((mapping(LineString([nodes[i] for i in ids])),1))
print('ways per river',list(map(len,groups)),flush=True)
base='original/N043E041/ALPSMLC30_N043E041_';paths=[base+'DSM.tif',base+'MSK.tif',base+'STK.tif']
with rasterio.open(paths[0]) as ds:
 win=from_bounds(41.76,43.18,41.99,43.34,ds.transform).round_offsets().round_lengths();aff=transform(win,ds.transform);z=ds.read(1,window=win);m=[]
 for path in paths[1:]:
  with rasterio.open(path) as f:
   if f.crs!=ds.crs or f.transform!=ds.transform or f.shape!=ds.shape:raise ValueError('unaligned raster')
   m.append(f.read(1,window=win))
 valid=np.isfinite(z)&(z!=ds.nodata)&((m[0]==0)|(m[0]==48));masks=[rasterize(g,out_shape=z.shape,transform=aff,all_touched=True).astype(bool) for g in groups];seed=np.zeros(z.shape,dtype='uint8');seed[masks[0]&~masks[1]&valid]=1;seed[masks[1]&~masks[0]&valid]=2
 print('shape',z.shape,'valid',int(valid.sum()),'seedcounts',[int((seed==i).sum()) for i in (1,2)],flush=True)
 _,graph=flow_graph(z,valid,aff,ds.crs);labels,stats=trace_to_seeds(graph,valid,seed);print('labels',[(i,int((labels==i).sum())) for i in (0,1,2,3)],'stats',stats,flush=True);np.savez_compressed('klukhor-jaxa-valid-mask-research.npz',labels=labels,seeds=seed,affine=np.array(tuple(aff)))
 l=GeodesicLine(json.load(open('caucasus-line.json'))['coordinates']);s=l.closest((41.86776666666667,43.244283333333335))['station_m']
 for offset in (100,250,500):
  count=Counter()
  for off in range(-2000,2001,100):
   p=l.point(s+off);a=l.point(s+off-100);b=l.point(s+off+100);az=GEOD.inv(*a,*b)[0];pair=[]
   for d in (-90,90):
    pt=GEOD.fwd(*p,az+d,offset)[:2];c,r=(~aff)*pt;c=int(c);r=int(r);pair.append(int(labels[r,c]) if 0<=r<z.shape[0] and 0<=c<z.shape[1] else -1)
   count[tuple(pair)]+=1
  print('offset',offset,'pairs',dict(count),flush=True)
