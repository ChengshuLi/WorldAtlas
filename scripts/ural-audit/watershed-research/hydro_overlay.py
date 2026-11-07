#!/usr/bin/env python3
"""Research-only noded HydroBASINS boundary intersection; no synthetic gap joins."""
import argparse,hashlib,json,math,shutil,tempfile,zipfile
from collections import Counter,defaultdict
from pathlib import Path
from hydro_graph import AuditError, file_sha, point, require, route, snap, verify_pin, validate_bbox, validate_rings, extract_components, MAX_FEATURES, MAX_VERTICES, MAX_GRAPH_SEGMENTS, MAX_ARCHIVES, MAX_GAP_PAIRS

def load_archive(path,digest,bbox):
 import shapefile
 from pyproj import CRS
 from shapely.geometry import shape
 verify_pin(path,digest)
 with tempfile.TemporaryDirectory(prefix='hydro-overlay-') as tmp,zipfile.ZipFile(path) as z:
  local=Path(tmp)/'basins';extract_components(z,local)
  crs=CRS.from_wkt(Path(str(local)+'.prj').read_text());require(crs.is_geographic and crs.equals(CRS.from_epsg(4326),ignore_axis_order=True),'archive CRS must be WGS84')
  reader=shapefile.Reader(str(local));fields=[x[0] for x in reader.fields[1:]];require('HYBAS_ID' in fields and 'MAIN_BAS' in fields,'missing required source fields');ih=fields.index('HYBAS_ID');im=fields.index('MAIN_BAS');features=[];vertices=0
  for rec in reader.iterShapeRecords():
   sh=rec.shape;require(sh.shapeType in (5,15,25),'invalid polygon source');x0,y0,x1,y1=sh.bbox;require(all(math.isfinite(x) for x in sh.bbox),'nonfinite polygon bounds')
   if x1<bbox[0] or x0>bbox[2] or y1<bbox[1] or y0>bbox[3]:continue
   rid,bas=rec.record[ih],rec.record[im];require(type(rid) is int and rid>0 and type(bas) is int and bas>0,'invalid basin identifier')
   starts=list(sh.parts)+[len(sh.points)];rings=[sh.points[a:b] for a,b in zip(starts,starts[1:])];vertices+=validate_rings(rings);require(vertices<=MAX_VERTICES and len(features)<MAX_FEATURES,'relevant source limits exceeded')
   geom=shape(sh.__geo_interface__);require(not geom.is_empty and geom.is_valid and geom.geom_type in ('Polygon','MultiPolygon'),'invalid basin geometry')
   features.append((digest,rid,bas,geom))
  reader.close()
 verify_pin(path,digest);return features

def line_parts(geom):
 if geom.is_empty:return
 if geom.geom_type in ('LineString','LinearRing'):
  yield geom
 elif geom.geom_type in ('MultiLineString','GeometryCollection'):
  for child in geom.geoms:yield from line_parts(child)
 elif geom.geom_type not in ('Point','MultiPoint'):raise AuditError('unexpected overlay geometry: '+geom.geom_type)

def overlay_graph(features,left,right,bbox,distance):
 """Intersect dissolved side boundaries; exact GEOS overlay, no buffer or bridge."""
 from shapely.geometry import box
 from shapely.ops import unary_union
 require(left and right and not left.intersection(right),'side sets must be nonempty and disjoint')
 validate_bbox(bbox);require(len(features)<=MAX_FEATURES,'relevant feature limit exceeded');clip=box(*bbox);groups={'A':[],'B':[]};unknown=[];ids=set();present=set();stats=Counter();unique={'A':set(),'B':set()};vertices=0
 for archive,rid,bas,geom in features:
  key=(archive,rid);require(key not in ids,'duplicate basin ID within archive');ids.add(key);present.add(bas)
  label='A' if bas in left else 'B' if bas in right else '?';stats['polygons_'+label]+=1
  require(not geom.is_empty and geom.is_valid and geom.geom_type in ('Polygon','MultiPolygon'),'invalid basin geometry')
  polygons=[geom] if geom.geom_type=='Polygon' else list(geom.geoms)
  for poly in polygons:
   vertices+=validate_rings([list(poly.exterior.coords)]+[list(r.coords) for r in poly.interiors]);require(vertices<=MAX_VERTICES,'relevant vertex limit exceeded')
  if label=='?':unknown.append((archive,rid,bas,geom));continue
  clipped=geom.intersection(clip)
  if clipped.is_empty:stats['empty_after_clip']+=1;continue
  require(clipped.geom_type in ('Polygon','MultiPolygon') and clipped.is_valid,'non-polygonal or invalid clipped basin')
  # Normalization makes orientation, component order, and ring start irrelevant.
  import shapely
  signature=shapely.normalize(clipped).wkb
  if signature in unique[label]:stats['duplicate_same_side_polygons']+=1;continue
  unique[label].add(signature);groups[label].append(clipped)
 missing=sorted((left|right)-present);require(not missing,'selected MAIN_BAS IDs missing',{'missing_main_bas':missing,**dict(stats)})
 require(groups['A'] and groups['B'],'one side has no clipped polygons',dict(stats))
 aa=unary_union(groups['A']);bb=unary_union(groups['B']);require(aa.is_valid and bb.is_valid,'invalid dissolved basin geometry')
 require(not aa.relate_pattern(bb,'T********'),'cross-label basin polygon area overlap (interior intersection)',dict(stats))
 # Boundary shared only due to clipping is not sourced as a watershed edge.
 shared=aa.boundary.intersection(bb.boundary).difference(clip.boundary)
 for archive,rid,bas,geom in unknown:
  require(not geom.intersects(shared),'unknown-side polygon touches shared interface',{'archive':archive,'hybas_id':rid,'main_bas':bas,**dict(stats)})
 noded=unary_union(shared);graph=defaultdict(set);segment_set=set()
 for ln in line_parts(noded):
  coords=[point(c) for c in ln.coords]
  for a,b in zip(coords,coords[1:]):
   require(a!=b,'zero-length noded segment');edge=tuple(sorted((a,b)))
   if edge in segment_set:stats['duplicate_noded_segments']+=1;continue
   segment_set.add(edge);require(len(segment_set)<=MAX_GRAPH_SEGMENTS,'graph segment limit exceeded');graph[a].add(b);graph[b].add(a)
 require(bool(graph),'no shared line segments',dict(stats))
 degrees=Counter(map(len,graph.values()));remain=set(graph);components=[]
 while remain:
  q=[min(remain)];remain.remove(q[0]);vertices=[]
  while q:
   v=q.pop();vertices.append(v)
   for u in graph[v]:
    if u in remain:remain.remove(u);q.append(u)
  components.append(vertices)
 stats.update({'shared_noded_segments':len(segment_set),'vertices':len(graph),'components':len(components),'branch_vertices':sum(v for k,v in degrees.items() if k>2)})
 diagnostics=dict(stats);diagnostics['degree_counts']={str(k):v for k,v in sorted(degrees.items())};diagnostics['component_vertex_counts']=sorted((len(c) for c in components),reverse=True)
 if len(components)>1:
  ends=[[v for v in c if len(graph[v])==1] for c in components];candidates=[]
  for i in range(len(ends)):
   for j in range(i+1,len(ends)):
    for a in ends[i]:
     for b in ends[j]:
      require(len(candidates)<MAX_GAP_PAIRS,'component gap comparison limit exceeded',diagnostics);candidates.append((distance(a,b),a,b))
  if candidates:
   d,a,b=min(candidates);require(math.isfinite(d),'invalid endpoint gap distance');diagnostics['nearest_component_endpoint_gap']={'wgs84_m':d,'from_vertex':a,'to_vertex':b,'limitation':'Degree-one endpoints only; no connection is created.'}
 require(len(components)==1 and diagnostics['branch_vertices']==0 and degrees.get(1,0)==2,'shared graph is branched, cyclic or disconnected',diagnostics)
 return dict(graph),diagnostics

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',nargs=2,action='append',required=True,metavar=('ZIP','SHA256'));p.add_argument('--bbox',nargs=4,type=float,required=True);p.add_argument('--side-a',nargs='+',type=int,required=True);p.add_argument('--side-b',nargs='+',type=int,required=True);p.add_argument('--start',nargs=2,type=float,required=True);p.add_argument('--end',nargs=2,type=float,required=True);p.add_argument('--max-snap-m',type=float,required=True);p.add_argument('--output',required=True);a=p.parse_args()
 code_before=file_sha(__file__);helper_path=Path(__file__).with_name('hydro_graph.py');helper_before=file_sha(helper_path)
 bbox=a.bbox;validate_bbox(bbox);require(len(a.archive)<=MAX_ARCHIVES,'archive count limit exceeded');require(math.isfinite(a.max_snap_m) and a.max_snap_m>=0,'invalid snap distance');require(len(a.side_a)==len(set(a.side_a)) and len(a.side_b)==len(set(a.side_b)) and all(x>0 for x in a.side_a+a.side_b),'invalid side IDs')
 import pyproj,shapefile,shapely
 from pyproj import Geod
 geod=Geod(ellps='WGS84');distance=lambda a,b:geod.inv(a[0],a[1],b[0],b[1])[2]
 features=[]
 for name,digest in a.archive:features.extend(load_archive(name,digest,bbox))
 require(len(features)<=MAX_FEATURES,'relevant feature limit exceeded');graph,diagnostics=overlay_graph(features,set(a.side_a),set(a.side_b),bbox,distance);start,sd=snap(graph,a.start,a.max_snap_m,distance);end,ed=snap(graph,a.end,a.max_snap_m,distance);vertices,length=route(graph,start,end,distance)
 result={'schema':'hydrobasins-noded-overlay-route-research-v1','status':'research-only','publishable':False,'code_sha256':code_before,'helper_sha256':helper_before,'runtime':{'shapely':shapely.__version__,'geos':shapely.geos_version_string,'pyproj':pyproj.__version__,'proj':pyproj.proj_version_str,'pyshp':shapefile.__version__},'inputs':{'archives':[{'path':str(Path(n).resolve()),'sha256':h} for n,h in a.archive],'bbox':bbox,'side_a_main_bas':sorted(a.side_a),'side_b_main_bas':sorted(a.side_b),'start':a.start,'end':a.end,'max_snap_m':a.max_snap_m},'diagnostics':diagnostics,'snaps':{'start_vertex':start,'start_wgs84_m':sd,'end_vertex':end,'end_wgs84_m':ed},'route_wgs84_segment_sum_m':length,'geometry':{'type':'LineString','coordinates':vertices},'limitations':['GEOS planar coordinate overlay; no fuzzy tolerance, gaps are not bridged.','Segments on the bounding-box boundary are excluded as clipping artifacts.','Only selected MAIN_BAS polygons are dissolved; unknown groups are counted but not used.','Vertex-only snap; connector geometries are not included.','Route length sums WGS84 inverse geodesics between source vertices and approximates the coordinate-linear edges without a formal error bound.','MAIN_BAS groups, anchors and box are user inputs, not proof of destinations or geographic authority.','This is not a selected boundary, historical reconstruction, map rebuild, or surveyed divide.']}
 require(file_sha(__file__)==code_before and file_sha(helper_path)==helper_before,'code changed during route derivation')
 for name,digest in a.archive:verify_pin(name,digest)
 with open(a.output,'x') as f:json.dump(result,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
if __name__=='__main__':
 try:main()
 except Exception as e:
  import sys
  print(json.dumps({'status':'failed','error':str(e),'diagnostics':getattr(e,'diagnostics',{})},sort_keys=True),file=sys.stderr);raise SystemExit(1)
