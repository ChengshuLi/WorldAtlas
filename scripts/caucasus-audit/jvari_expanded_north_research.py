"""Research only: OSM-directed expanded basin seeds and quality-screened WGS84 flow."""
import sys,json,xml.etree.ElementTree as E
from collections import defaultdict,deque,Counter
import numpy as np,rasterio
from rasterio.windows import from_bounds,transform
from rasterio.features import rasterize
from shapely.geometry import LineString,mapping
from seeded_flow_basins import flow_graph,trace_to_seeds
from geodesic_line import GeodesicLine,GEOD
root=E.parse('jvari-expanded-merged-research.osm').getroot();nodes={v.get('id'):(float(v.get('lon')),float(v.get('lat'))) for v in root.findall('node')};ways={};reverse=defaultdict(set)
for way in root.findall('way'):
 tags={v.get('k'):v.get('v') for v in way.findall('tag')};ids=[v.get('ref') for v in way.findall('nd')]
 if tags.get('waterway') not in ('river','stream') or len(ids)<2 or any(i not in nodes for i in ids):continue
 ways[way.get('id')]=ids
 for a,b in zip(ids,ids[1:]):reverse[b].add(a)
assert all(k in ways for k in ('169427255','515458205'))
def ancestors(ids):
 seen=set(ids);todo=deque(ids)
 while todo:
  for p in reverse[todo.popleft()]:
   if p not in seen:seen.add(p);todo.append(p)
 return seen
reach=[set().union(*(ancestors(ways[k]) for k in ('169427255','963447482','83802248','83802666'))),ancestors(ways['515458205'])]; groups=[[],[]];ambiguous=[]
for id,ids in ways.items():
 matches=[i for i,r in enumerate(reach) if ids[-1] in r]
 if len(matches)==1:groups[matches[0]].append((mapping(LineString([nodes[i] for i in ids])),1))
 elif len(matches)>1:ambiguous.append(id)
print('ways',list(map(len,groups)),'ambiguous',len(ambiguous),'total',len(ways),flush=True)
model=sys.argv[1]
if model=='jaxa':
 base='original/N042E044/ALPSMLC30_N042E044_';paths=[base+'DSM.tif',base+'MSK.tif',base+'STK.tif']
else:paths=['central-jvari-cop30-'+x+'.tif' for x in ('dem','EDM','FLM','WBM')]
with rasterio.open(paths[0]) as ds:
 win=from_bounds(44.30,42.40,44.60,42.64,ds.transform).round_offsets().round_lengths();aff=transform(win,ds.transform);z=ds.read(1,window=win);m=[]
 for p in paths[1:]:
  with rasterio.open(p) as v:
   assert v.crs==ds.crs and v.transform==ds.transform and v.shape==ds.shape;m.append(v.read(1,window=win))
 valid=np.isfinite(z)&(z!=ds.nodata)
 if model=='jaxa':valid &= ((m[0]==0) | (m[0]==48))
 else:valid &= (m[0]==1)&(m[1]==2)&(m[2]==0)
 masks=[rasterize(g,out_shape=z.shape,transform=aff,all_touched=True).astype(bool) for g in groups];seed=np.zeros(z.shape,dtype='uint8');seed[masks[0]&~masks[1]&valid]=1;seed[masks[1]&~masks[0]&valid]=2
 print('model',model,'shape',z.shape,'valid',int(valid.sum()),'seeds',int((seed==1).sum()),int((seed==2).sum()),'conflicting',int((masks[0]&masks[1]).sum()),flush=True)
 _,graph=flow_graph(z,valid,aff,ds.crs);labels,stats=trace_to_seeds(graph,valid,seed);print('labels',[(k,int((labels==k).sum())) for k in (0,1,2,3)],'stats',stats,flush=True);np.savez_compressed('jvari-expanded-north-'+model+'-research.npz',labels=labels,seeds=seed,affine=np.array(tuple(aff)))
 l=GeodesicLine(json.load(open('caucasus-line.json'))['coordinates']);s=l.closest((44.45511099459589,42.50809094740639))['station_m'];count=Counter()
 for off in range(-5000,5001,100):
  p=l.point(s+off);a=l.point(s+off-20);b=l.point(s+off+20);az=GEOD.inv(*a,*b)[0];pair=[]
  for d in (-90,90):
   xy=GEOD.fwd(*p,az+d,250)[:2];col,row=(~aff)*xy;col=int(col);row=int(row);pair.append(int(labels[row,col]) if 0<=row<z.shape[0] and 0<=col<z.shape[1] else -1)
  count[tuple(pair)]+=1
 print('pairs_at_250m',sorted(count.items()),flush=True)
