#!/usr/bin/env python3
"""Construct an exact HydroBASINS shared-edge research route; never edits a map."""
import argparse, hashlib, heapq, json, math, shutil, tempfile, zipfile
from collections import Counter, defaultdict, deque
from pathlib import Path

COMPONENT_LIMITS={'.shp':512<<20,'.shx':64<<20,'.dbf':128<<20,'.prj':65536}
MAX_ARCHIVE_UNCOMPRESSED=768<<20
MAX_FEATURES=20000
MAX_VERTICES=2000000
MAX_GRAPH_SEGMENTS=2000000
MAX_ARCHIVES=8
MAX_GAP_PAIRS=100000

def validate_bbox(b):
 require(len(b)==4 and all(type(x) in (int,float) and math.isfinite(x) for x in b) and -180<=b[0]<b[2]<=180 and -90<=b[1]<b[3]<=90 and b[2]-b[0]<=30 and b[3]-b[1]<=30,'bbox must be local, finite, nonwrapping and at most 30 degrees per axis')

def validate_rings(rings):
 count=0
 for ring in rings:
  require(len(ring)>=4 and ring[0]==ring[-1],'invalid basin ring');count+=len(ring)
  require(count<=MAX_VERTICES,'feature vertex limit exceeded')
  coords=[point(p) for p in ring]
  for a,b in zip(coords,coords[1:]):require(abs(a[0]-b[0])<=180,'antimeridian jump unsupported')
 return count

def extract_components(archive,local):
 infos=archive.infolist();require(len(infos)<=2048,'archive entry count exceeds limit');require(sum(i.file_size for i in infos)<=MAX_ARCHIVE_UNCOMPRESSED,'archive uncompressed size exceeds limit')
 shps=[i for i in infos if i.filename.lower().endswith('.shp')];require(len(shps)==1,'archive must contain exactly one shapefile');stem=shps[0].filename[:-4]
 for ext,limit in COMPONENT_LIMITS.items():
  matches=[i for i in infos if i.filename.lower()==(stem+ext).lower()];require(len(matches)==1,'missing or duplicate shapefile component: '+ext);info=matches[0];require(info.file_size<=limit,'shapefile component exceeds limit: '+ext)
  with archive.open(info) as src,open(str(local)+ext,'wb') as dst:
   count=0
   while True:
    block=src.read(min(1048576,limit-count+1))
    if not block:break
    count+=len(block);require(count<=limit,'shapefile component exceeds limit: '+ext);dst.write(block)
   require(count==info.file_size,'shapefile component size mismatch')

class AuditError(ValueError):
 def __init__(self, message, diagnostics=None):
  super().__init__(message); self.diagnostics=diagnostics or {}

def require(ok, message, diagnostics=None):
 if not ok: raise AuditError(message, diagnostics)

def file_sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()

def verify_pin(path, expected):
 require(isinstance(expected,str) and len(expected)==64 and all(c in '0123456789abcdef' for c in expected),'invalid SHA-256')
 require(file_sha(path)==expected,'archive checksum mismatch')

def point(p):
 require(isinstance(p,(tuple,list)) and len(p)>=2 and all(type(v) in (int,float) and math.isfinite(v) for v in p[:2]),'invalid coordinate')
 x,y=map(float,p[:2]);require(-180<=x<=180 and -90<=y<=90,'coordinate outside WGS84');return (x,y)

def load_archive(path, digest, bbox):
 """Read one complete standard HydroBASINS shapefile from a hash-pinned ZIP."""
 import shapefile
 verify_pin(path,digest)
 with tempfile.TemporaryDirectory(prefix='hydrograph-') as tmp, zipfile.ZipFile(path) as archive:
  local=Path(tmp)/'basins';extract_components(archive,local)
  # Only documented geographic coordinates are supported; never silently reproject.
  from pyproj import CRS
  prj=Path(str(local)+'.prj').read_text();crs=CRS.from_wkt(prj)
  require(crs.is_geographic and crs.equals(CRS.from_epsg(4326),ignore_axis_order=True),'shapefile must be geographic WGS84')
  reader=shapefile.Reader(str(local));fields=[f[0] for f in reader.fields[1:]]
  require('HYBAS_ID' in fields and 'MAIN_BAS' in fields,'missing HYBAS_ID or MAIN_BAS')
  ih,im=fields.index('HYBAS_ID'),fields.index('MAIN_BAS');result=[];vertex_count=0
  for rec in reader.iterShapeRecords():
   shape=rec.shape
   require(shape.shapeType in (5,15,25),'unsupported or null basin geometry')
   x0,y0,x1,y1=shape.bbox;require(all(math.isfinite(v) for v in shape.bbox),'nonfinite polygon bounds')
   if x1<bbox[0] or x0>bbox[2] or y1<bbox[1] or y0>bbox[3]:continue
   rid,bas=rec.record[ih],rec.record[im]
   require(type(rid) is int and type(bas) is int and rid>0 and bas>0,'invalid basin identifier')
   pts=[point(p) for p in shape.points];starts=list(shape.parts)+[len(pts)];rings=[]
   for a,b in zip(starts,starts[1:]):
    ring=pts[a:b];require(len(ring)>=4 and ring[0]==ring[-1],'invalid basin ring');rings.append(ring)
   vertex_count+=validate_rings(rings);require(vertex_count<=MAX_VERTICES and len(result)<MAX_FEATURES,'relevant source limits exceeded');result.append((rid,bas,rings))
  reader.close()
 verify_pin(path,digest)
 return result

def build_graph(features, left, right, bbox, distance=None):
 """Only identical, unsplit source coordinate segments are considered shared."""
 validate_bbox(bbox)
 require(left and right and not left.intersection(right),'side sets must be nonempty and disjoint')
 edges=defaultdict(list); ids=set();present=set();geometry_owners={};unknown=[];stats=Counter();w,s,e,n=bbox
 require(len(features)<=MAX_FEATURES,'relevant feature limit exceeded');total_vertices=0
 for archive,rid,bas,rings in features:
  total_vertices+=validate_rings(rings);require(total_vertices<=MAX_VERTICES,'relevant vertex limit exceeded')
  key=(archive,rid);require(key not in ids,'duplicate basin ID within archive');ids.add(key)
  present.add(bas);label='A' if bas in left else 'B' if bas in right else '?';stats['polygons_'+label]+=1
  if label=='?':unknown.append((archive,rid,bas,rings))
  seen=set();full_edges=set()
  for ring in rings:
   require(len(ring)>=4 and ring[0]==ring[-1],'invalid basin ring')
   for a,b in zip(ring,ring[1:]):
    a,b=point(a),point(b);require(a!=b,'degenerate source segment')
    full_edge=tuple(sorted((a,b)));require(full_edge not in full_edges,'duplicate segment in basin geometry');full_edges.add(full_edge)
    # A segment must lie wholly inside: no invented clipped or snapped edge.
    if not (w<=a[0]<=e and w<=b[0]<=e and s<=a[1]<=n and s<=b[1]<=n):stats['segments_excluded_bbox']+=1;continue
    edge=tuple(sorted((a,b)));require(edge not in seen,'duplicate segment in basin geometry');seen.add(edge);edges[edge].append((archive,rid,bas,label))
  signature=frozenset(full_edges);owner=geometry_owners.get(signature)
  require(owner is None,'duplicate or cross-label basin geometry',{'first':owner,'second':(archive,rid,bas,label)})
  geometry_owners[signature]=(archive,rid,bas,label)
 missing=sorted((left|right)-present);require(not missing,'selected MAIN_BAS IDs missing in bounding box',{'missing_main_bas':missing,**dict(stats)})
 graph=defaultdict(set)
 for (a,b),inc in edges.items():
  require(len(inc)<=2,'duplicate or nonmanifold source segment',{'segment':[a,b],'incidence':inc})
  labels=[x[3] for x in inc]
  if len(inc)==1:stats['unpaired_segments']+=1
  elif '?' in labels:stats['unknown_side_segments']+=1
  elif labels[0]==labels[1]:stats['same_side_segments']+=1
  else:
   graph[a].add(b);graph[b].add(a);stats['shared_AB_segments']+=1;require(stats['shared_AB_segments']<=MAX_GRAPH_SEGMENTS,'graph segment limit exceeded')
 require(bool(graph),'no exact cross-side edges',dict(stats))
 if unknown:
  from shapely.geometry import LineString,Polygon
  from shapely.ops import unary_union
  shared=unary_union([LineString(edge) for edge in edges if len(edges[edge])==2 and {x[3] for x in edges[edge]}=={'A','B'}])
  for archive,rid,bas,rings in unknown:
   for ring in rings:
    polygon=Polygon(ring);require(polygon.is_valid,'invalid unknown-side polygon')
    require(not polygon.intersects(shared),'unknown-side polygon touches shared interface',{'archive':archive,'hybas_id':rid,'main_bas':bas,**dict(stats)})
 degrees=Counter(len(v) for v in graph.values());stats['vertices']=len(graph)
 stats['branch_vertices']=sum(v for k,v in degrees.items() if k>2)
 remaining=set(graph);components=[]
 while remaining:
  q=[min(remaining)];remaining.remove(q[0]);members=[]
  while q:
   u=q.pop();members.append(u)
   for v in graph[u]:
    if v in remaining:remaining.remove(v);q.append(v)
  components.append(members)
 stats['components']=len(components);stats['component_vertex_counts']=sorted((len(c) for c in components),reverse=True);stats['degree_counts']={str(k):v for k,v in sorted(degrees.items())}
 if len(components)>1 and distance is not None:
  endpoints=[[v for v in c if len(graph[v])==1] for c in components];candidates=[]
  for i in range(len(endpoints)):
   for j in range(i+1,len(endpoints)):
    for a in endpoints[i]:
     for b in endpoints[j]:
      require(len(candidates)<MAX_GAP_PAIRS,'component gap comparison limit exceeded',dict(stats));d=distance(a,b);require(math.isfinite(d),'invalid component gap distance');candidates.append((d,a,b))
  if candidates:
   d,a,b=min(candidates);stats['nearest_component_endpoint_gap']={'wgs84_m':d,'from_vertex':a,'to_vertex':b,'limitation':'Diagnostic between degree-one graph vertices only; no connector is created.'}
 require(stats['branch_vertices']==0 and len(components)==1 and degrees.get(1,0)==2,'shared graph is branched, cyclic or disconnected',dict(stats))
 return dict(graph),dict(stats)

def snap(graph, anchor, max_m, distance):
 a=point(anchor);d=sorted((distance(a,p),p) for p in graph)
 require(d and math.isfinite(d[0][0]) and d[0][0]<=max_m,'anchor exceeds maximum vertex snap distance')
 require(len(d)==1 or abs(d[1][0]-d[0][0])>1e-6,'ambiguous anchor vertex snap')
 return d[0][1],d[0][0]

def route(graph, start, end, distance):
 require(start!=end,'anchors snap to same vertex');dist={start:0.0};prev={};heap=[(0.0,start)];ties=set()
 while heap:
  d,u=heapq.heappop(heap)
  if d!=dist[u]:continue
  for v in sorted(graph[u]):
   length=distance(u,v);require(math.isfinite(length) and length>0,'invalid edge distance');nd=d+length
   if v not in dist or nd<dist[v]-1e-8:dist[v]=nd;prev[v]=u;heapq.heappush(heap,(nd,v));ties.discard(v)
   elif abs(nd-dist[v])<=1e-8 and prev.get(v)!=u:ties.add(v)
 require(end in dist,'anchors disconnected');path=[end]
 while path[-1]!=start:
  require(path[-1] not in ties,'ambiguous equal-length route');path.append(prev[path[-1]])
 path.reverse();return path,dist[end]

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',nargs=2,action='append',metavar=('ZIP','SHA256'),required=True);p.add_argument('--bbox',nargs=4,type=float,required=True);p.add_argument('--side-a',nargs='+',type=int,required=True);p.add_argument('--side-b',nargs='+',type=int,required=True);p.add_argument('--start',nargs=2,type=float,required=True);p.add_argument('--end',nargs=2,type=float,required=True);p.add_argument('--max-snap-m',type=float,required=True);p.add_argument('--output',required=True);a=p.parse_args()
 code_before=file_sha(__file__);bbox=a.bbox;validate_bbox(bbox);require(len(a.archive)<=MAX_ARCHIVES,'archive count limit exceeded');require(math.isfinite(a.max_snap_m) and a.max_snap_m>=0,'invalid snap limit');require(len(a.side_a)==len(set(a.side_a)) and len(a.side_b)==len(set(a.side_b)) and all(x>0 for x in a.side_a+a.side_b),'invalid side IDs')
 import pyproj, shapefile
 from pyproj import Geod
 geod=Geod(ellps='WGS84');distance=lambda x,y:geod.inv(x[0],x[1],y[0],y[1])[2]
 features=[]
 for name,digest in a.archive:
  features.extend((digest,rid,bas,rings) for rid,bas,rings in load_archive(name,digest,bbox))
 require(len(features)<=MAX_FEATURES,'relevant feature limit exceeded');graph,diagnostics=build_graph(features,set(a.side_a),set(a.side_b),bbox,distance);start,sd=snap(graph,a.start,a.max_snap_m,distance);end,ed=snap(graph,a.end,a.max_snap_m,distance);path,length=route(graph,start,end,distance)
 result={'schema':'hydrobasins-exact-shared-edge-route-research-v1','status':'research-only','publishable':False,'code_sha256':code_before,'runtime':{'pyproj':pyproj.__version__,'proj':pyproj.proj_version_str,'pyshp':shapefile.__version__},'inputs':{'archives':[{'path':str(Path(n).resolve()),'sha256':h} for n,h in a.archive],'bbox':bbox,'side_a_main_bas':sorted(a.side_a),'side_b_main_bas':sorted(a.side_b),'start':a.start,'end':a.end,'max_snap_m':a.max_snap_m},'diagnostics':diagnostics,'snaps':{'start_vertex':start,'start_wgs84_m':sd,'end_vertex':end,'end_wgs84_m':ed},'route_wgs84_segment_sum_m':length,'geometry':{'type':'LineString','coordinates':path},'limitations':['Exact matching of complete source segments only; differently segmented or near-coincident boundaries are not noded or snapped.','Bounding box discards segments with either endpoint outside; unpaired and unknown-side edges are not proof of topology.','MAIN_BAS membership and anchors are caller choices, not validated geographic destinations.','Vertex snaps and omitted connector geometries are not part of the route; disconnected, branched and cyclic graphs fail closed.','Not a surveyed divide, continent assignment, map rebuild or historical reconstruction.']}
 require(file_sha(__file__)==code_before,'code changed during route derivation')
 for name,digest in a.archive:verify_pin(name,digest)
 with open(a.output,'x') as f:json.dump(result,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')

if __name__=='__main__':
 try:main()
 except Exception as e:
  import sys
  print(json.dumps({'status':'failed','error':str(e),'diagnostics':getattr(e,'diagnostics',{})},sort_keys=True),file=sys.stderr);raise SystemExit(1)
