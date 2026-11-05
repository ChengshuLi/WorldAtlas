import sys,json,hashlib,heapq,collections,numpy as np
from shapely.geometry import LineString,Point
from shapely.strtree import STRtree
from pyproj import Geod
sys.path.insert(0,'landed-1b494125')
from spring_connector_graph import basin_labels
geod=Geod(ellps='WGS84')
source_path='ural-watershed-first4954.json'
expected_source='0a1aee04c5d60fec6f039b709720f2c7e4ae7f2522d8224fdfe0d9086978ccb4'
if hashlib.sha256(open(source_path,'rb').read()).hexdigest()!=expected_source:raise ValueError('source hash mismatch')
source=json.load(open(source_path));print('source_file_sha256',expected_source,flush=True)
basins=[('/tmp/ural-hydro-eu.zip','21797d53e0792cae047d25f0c3cfb570c7ef43700ec962b35b2ac92467e29f03','/tmp/ural-hydro-eu/hybas_eu_lev12_v1c.shp'),('/tmp/ural-hydro-si.zip','67ea00df7d14a397f8f78e5b1dc31dcca036018ccbcb36e007ce6854b91d71bd','/tmp/ural-hydro-si/hybas_si_lev12_v1c.shp')]
inputs=[('00','arctic','/tmp/ural-gap00-12km-nearest.tif','3dbc4da15948791a70b78346eaba7174ccb464226bf9adf292184757f7c6af6b',[59.70,64.10,59.83,64.18],1627,1894),('00','cop','/tmp/ural-gap00-cop-30m-bilinear.tif','d661fee6218f9198f48cf3505a5303a4942cec602747fb82af3571c9548e4a86',[59.70,64.10,59.83,64.18],1627,1894),('02','arctic','/tmp/ural-gap02-16km-nearest.tif','dc04a55cdc1b742a21dfdb1f050f493c621a6ae0f3f66f7cdd0042c2cb893635',[59.40,61.92,59.52,62.02],2320,3547),('02','cop','/tmp/ural-gap02-cop-30m-bilinear.tif','b35eff9756b70096e6ea2f1090249b6a60a31d4b7cc47dfd9d72eec646a0e169',[59.40,61.92,59.52,62.02],2320,3547)]
for n,product,path,h,bounds,start,end in inputs:
 labels,t,geo,unknown=basin_labels(path,h,None,None,basins,bounds,[2120043720,3120001840,9999999999],15)
 edges=[];nodes=[]
 def add(u,v):
  a=geo.transform(*(t*(u[1],u[0])));b=geo.transform(*(t*(v[1],v[0])));edges.append(LineString([a,b]));nodes.append((u,v))
 a,b=labels[:,:-1],labels[:,1:];rr,cc=np.where(((a==1)&(b==2))|((a==2)&(b==1)))
 for r,c in zip(rr,cc):add((int(r),int(c+1)),(int(r+1),int(c+1)))
 a,b=labels[:-1,:],labels[1:,:];rr,cc=np.where(((a==1)&(b==2))|((a==2)&(b==1)))
 for r,c in zip(rr,cc):add((int(r+1),int(c)),(int(r+1),int(c+1)))
 tree=STRtree(edges);result={}
 for label,inds,anchor in [('north',range(max(0,start-100),start),source[start]),('south',range(end,min(len(source)-1,end+100)),source[end])]:
  hits=[]
  for i in inds:
   segment=LineString(source[i:i+2])
   for j in tree.query(segment):
    crossing=segment.intersection(edges[j])
    if crossing.is_empty:continue
    points=[crossing] if crossing.geom_type=='Point' else list(crossing.geoms) if crossing.geom_type=='MultiPoint' else []
    if not points:raise ValueError('ambiguous non-point source-interface overlap')
    for q in points:
     distance=geod.inv(*anchor,q.x,q.y)[2];hits.append({'source_segment_index':i,'wgs84_anchor_distance_m':distance,'edge':nodes[j],'point':[q.x,q.y]})
  hits.sort(key=lambda z:z['wgs84_anchor_distance_m']);result[label]={'hit_count':len(hits),'closest':hits[:3]}

 north=result['north']['closest'][0] if result['north']['closest'] else None; south=result['south']['closest'][0] if result['south']['closest'] else None
 if north and south:
  cuts={tuple(tuple(v) for v in north['edge']):('north',north['point']),tuple(tuple(v) for v in south['edge']):('south',south['point'])}
  if len(cuts)!=2:raise ValueError('source intersections share same interface edge')
  adj=collections.defaultdict(list);xyz={}
  for u,v in nodes:
   xyz[u]=geo.transform(*(t*(u[1],u[0])));xyz[v]=geo.transform(*(t*(v[1],v[0])))
  def add_weight(u,v):
   p,q=xyz[u],xyz[v];length=geod.inv(*p,*q)[2];adj[u].append((v,length));adj[v].append((u,length))
  for u,v in nodes:
   cut=cuts.get((u,v))
   if cut:
    name,point=cut;xyz[name]=point;add_weight(u,name);add_weight(name,v)
   else:add_weight(u,v)
  dist={'north':0.};prev={};queue=[(0.,0,'north')];serial=0
  while queue:
   length,_,u=heapq.heappop(queue)
   if length!=dist[u]:continue
   if u=='south':break
   for v,w in adj[u]:
    candidate=length+w
    if candidate<dist.get(v,float('inf')):
     dist[v]=candidate;prev[v]=u;serial+=1;heapq.heappush(queue,(candidate,serial,v))
  if 'south' not in dist:raise ValueError('closest crossings lie in disconnected components')
  path=['south']
  while path[-1]!='north':path.append(prev[path[-1]])
  path.reverse();coordinates=[list(xyz[k]) for k in path];i=north['source_segment_index'];j=south['source_segment_index']
  if i>=j:raise ValueError('source cut order is reversed')
  reconstructed=source[:i+1]+coordinates+source[j+1:]
  if not LineString(reconstructed).is_simple:raise ValueError('reconnected source self-intersects')
  out={'status':'exploratory-not-selected','gap':n,'product':product,'dem_sha256':h,'source_file_sha256':hashlib.sha256(open(source_path,'rb').read()).hexdigest(),'north':north,'south':south,'terrain_path_length_wgs84_segment_sum_m':dist['south'],'coordinates':coordinates,'reconnected_source_coordinates':reconstructed,'limitations':['Source line outside gap is the prior selected fallback, not a newly validated raw-source derivation.','D8 and MAIN_BAS outlet crosswalk are model-dependent; nearest intersections are a local heuristic.','Input/source intersection is planar; edge length sums geodesics of vertices without a formal path-length bound.','Crossing is mathematically continuous, not surveyed; candidate requires independent geographic review.']}
  with open('/tmp/ural-gap'+n+'-'+product+'-intersection-route-v2.json','x') as f:json.dump(out,f,sort_keys=True,allow_nan=False)
  result['path']={'length_m':dist['south'],'terrain_vertices':len(coordinates),'full_vertices':len(reconstructed),'status':'exploratory-not-selected'}
 print(json.dumps({'gap':n,'product':product,'dem_sha256':h,'bounds':bounds,'resolution_m':15,'unknown_valid':unknown,'edge_count':len(edges),'segments_each_side':100,'crossings':result,'limitation':'exploratory fallback selected source, planar source/edge intersection, WGS84 anchor geodesic, not a final supported terrain join'},sort_keys=True),flush=True)

if hashlib.sha256(open(source_path,'rb').read()).hexdigest()!=expected_source:raise ValueError('source changed during research')
