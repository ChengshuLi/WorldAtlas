"""Explore local drainage divide with mapped upstream networks and JAXA data."""
import sys,json,xml.etree.ElementTree as E
from collections import defaultdict,deque,Counter
import numpy as np,rasterio
from rasterio.windows import from_bounds,transform
from rasterio.features import rasterize
from shapely.geometry import LineString,mapping
from seeded_flow_basins import flow_graph,trace_to_seeds
from geodesic_line import GeodesicLine,GEOD
C=json.load(open(sys.argv[1]));root=E.parse(C['osm']).getroot();nodes={v.get('id'):(float(v.get('lon')),float(v.get('lat'))) for v in root.findall('node')};ways={};reverse=defaultdict(set)
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
reach=[]
for roots in C['groups']:
 all_nodes=set()
 for k in roots:
  if k not in ways:raise ValueError('missing OSM way '+k)
  all_nodes|=ancestors(ways[k])
 reach.append(all_nodes)
groups=[[],[]];amb=[]
for wid,ids in ways.items():
 match=[i for i,r in enumerate(reach) if ids[-1] in r]
 if len(match)==1:groups[match[0]].append((mapping(LineString([nodes[i] for i in ids])),1))
 elif len(match)>1:amb.append(wid)
print('ways per group',list(map(len,groups)),'ambiguous',len(amb),'total',len(ways),flush=True)
with rasterio.open(C['dsm']) as ds,rasterio.open(C['mask']) as ms:
 win=from_bounds(*C['bounds'],transform=ds.transform).round_offsets().round_lengths();aff=transform(win,ds.transform);z=ds.read(1,window=win);mask=ms.read(1,window=win);valid=np.isfinite(z)&(z!=ds.nodata)&((mask==0)|(mask==8)|(mask==48));masks=[rasterize(g,out_shape=z.shape,transform=aff,all_touched=True).astype(bool) for g in groups];seed=np.zeros(z.shape,dtype='uint8');seed[masks[0]&~masks[1]&valid]=1;seed[masks[1]&~masks[0]&valid]=2
 print('shape',z.shape,'valid',int(valid.sum()),'seeds',[int((seed==i).sum()) for i in (1,2)],'conflicts',int((masks[0]&masks[1]).sum()),flush=True)
 _,graph=flow_graph(z,valid,aff,ds.crs);labels,stats=trace_to_seeds(graph,valid,seed);print('labels',[(i,int((labels==i).sum())) for i in (0,1,2,3)],flush=True);np.savez_compressed(C['output'],labels=labels,seeds=seed,affine=np.array(tuple(aff)))
 l=GeodesicLine(json.load(open('caucasus-segment3-continuous-jaxa-research.json'))['coordinates']);s=l.closest(C['focus'])['station_m']
 for offset in (100,250,500):
  count=Counter()
  for d in range(-3000,3001,100):
   p=l.point(s+d);az=GEOD.inv(*l.point(s+d-100),*l.point(s+d+100))[0];pair=[]
   for q in (-90,90):
    x=GEOD.fwd(*p,az+q,offset)[:2];c,r=(~aff)*x;c=int(c);r=int(r);pair.append(int(labels[r,c]) if 0<=r<z.shape[0] and 0<=c<z.shape[1] else -1)
   count[tuple(pair)]+=1
  print('offset',offset,'pairs',dict(count),flush=True)
