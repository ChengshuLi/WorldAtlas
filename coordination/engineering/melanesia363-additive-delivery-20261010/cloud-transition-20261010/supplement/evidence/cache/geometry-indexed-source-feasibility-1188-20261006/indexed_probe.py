"""Private full-input feasibility. Sourcepoint evidence only, no owner or face approval."""
import collections,gzip,hashlib,json,pathlib,subprocess,sys,time
from fractions import Fraction as F
import numpy as np
import shapely,pyproj
from shapely.geometry import LineString,box
from shapely import STRtree
ROOT=pathlib.Path('/Users/chengshuli/world-atlas-workspace'); OUT=pathlib.Path(__file__).parent
A=ROOT/'.worldatlas-workspaces/8c86b01772c1c827/3d62cf18b0b42e3ae3cd26d42f5e7ac90b65e45ead741649cedd79762724f9e7/work'
P=A/'.cache/global-native-preflight-20261006'; BRIEF=ROOT/'.cache/integration-dependencies-972-20261006'; B=json.loads((BRIEF/'read-only-brief.json').read_bytes()); repo=ROOT/'WorldAtlas'; commit='1ba7ef86a046db62c2c19d731faf8118e6cee124'
preview_raw=(P/'portugal-spain-native-centres-preview-v1-report.json').read_bytes();preview=json.loads(preview_raw); centre_raw=(P/'portugal-spain-all-native-centres-preview-v1.json.gz').read_bytes();assert len(centre_raw)==preview['cell_rows']['bytes'] and hashlib.sha256(centre_raw).hexdigest()==preview['cell_rows']['sha256'];decoded=gzip.decompress(centre_raw);assert len(decoded)==preview['cell_rows']['decoded_bytes'] and hashlib.sha256(decoded).hexdigest()==preview['cell_rows']['decoded_sha256'];centres=json.loads(decoded);assert len(centres)==21575
native_verified=[]
for receipt in preview['native_input_receipts']:
 raw=subprocess.check_output(['git','-C',str(repo),'show',receipt['commit']+':'+receipt['path']]);assert len(raw)==receipt['bytes'] and hashlib.sha256(raw).hexdigest()==receipt['sha256'];native_verified.append(receipt)
def read(pin):
 raw=subprocess.check_output(['git','-C',str(repo),'show',commit+':'+pin['path']]);assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'];return json.loads(raw)
def polys(geom): return [geom['coordinates']] if geom['type']=='Polygon' else geom['coordinates']
tr=pyproj.Transformer.from_crs('OGC:CRS84','EPSG:25829',always_xy=True)
def sub(a,b):return a[0]-b[0],a[1]-b[1]
def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def ori(a,b,p):return cross(sub(b,a),sub(p,a))
def on(p,a,b):return ori(a,b,p)==0 and all(min(a[i],b[i])<=p[i]<=max(a[i],b[i]) for i in (0,1))
def contact(a,b,c,d):
 o=[ori(a,b,c),ori(a,b,d),ori(c,d,a),ori(c,d,b)]
 if o[0]*o[1]<0 and o[2]*o[3]<0:return 'proper-crossing'
 if any(on(p,x,y) for p,x,y in [(c,a,b),(d,a,b),(a,c,d),(b,c,d)]):return 'endpoint-or-collinear-contact'
 return None
source=[]
for pin in B['verified_official_polygon_inputs']:
 doc=read(pin);feature=doc['features'][0] if doc['type']=='FeatureCollection' else doc;source.append({'key':pin['key'],'pin':pin,'geometry':feature['geometry']})
gapref=B['existing_geometry_locations']['full_gap'];raw=subprocess.check_output(['git','-C',str(repo),'show',commit+':'+gapref['containing_path']]);assert hashlib.sha256(raw).hexdigest()==gapref['containing_sha256'];gap=next(f for f in json.loads(gzip.decompress(raw))['features'] if f['id']==gapref['feature_id'])['geometry']
points=np.asarray([c['native_centre_lonlat'] for c in centres]);results={};start_all=time.perf_counter()
for ctxt in ['CRS84-original-binary64','EPSG25829-projected-binary64']:
 xy=points if ctxt.startswith('CRS84') else np.column_stack(tr.transform(points[:,0],points[:,1]));states_by_source={};reports=[]
 for src in source+[{'key':'original_gap','geometry':gap}]:
  t0=time.perf_counter();rings=[];segments=[];metadata=[];corner_count=0;degenerate=[]
  for pi,poly in enumerate(polys(src['geometry'])):
   for ri,r in enumerate(poly):
    floats=[tuple(p[:2]) if ctxt.startswith('CRS84') else tr.transform(*p[:2]) for p in r];rats=[tuple(F(v) for v in p) for p in floats];ringid=len(rings);rings.append({'polygon_index':pi,'ring_index':ri,'float':floats,'rational':rats});corner_count+=len(r)-1
    for si,(a,b) in enumerate(zip(floats,floats[1:])):
     if a==b:degenerate.append([pi,ri,si])
     segments.append(LineString([a,b]));metadata.append((ringid,si,pi,ri,len(r)-1,rats[si],rats[si+1]))
  tree=STRtree(segments);hits=tree.query(segments);pairs=[(int(i),int(j)) for i,j in zip(*hits) if i<j];nonadj=[];adjacent_count=0
  for i,j in pairs:
   ai,bi=metadata[i],metadata[j]
   if ai[0]==bi[0] and (abs(ai[1]-bi[1])==1 or {ai[1],bi[1]}=={0,ai[4]-1}):adjacent_count+=1
   else:nonadj.append((i,j))
  topology_failures=[]
  for i,j in nonadj:
   failure=contact(metadata[i][-2],metadata[i][-1],metadata[j][-2],metadata[j][-1])
   if failure:topology_failures.append({'segments':[list(metadata[i][:5]),list(metadata[j][:5])],'contact':failure})
  # Ray bbox includes all p.y-straddling boundary candidates and every possible boundary point, before exact filtering.
  maxx=max(max(s.bounds[0],s.bounds[2]) for s in segments);boxes=[box(float(p[0]),float(p[1]),max(float(p[0]),maxx),float(p[1])) for p in xy];rays=tree.query(boxes)
  order=np.argsort(rays[0],kind='stable');rays=rays[:,order];ptr=0;states=[];boundary_points=[];candidate_count=len(rays[0]);exact_straddle_count=0;ring_bounds={i:(min(p[0] for p in r['float']),min(p[1] for p in r['float']),max(p[0] for p in r['float']),max(p[1] for p in r['float'])) for i,r in enumerate(rings)}
  for qi,p0 in enumerate(xy):
   p=tuple(F(float(v)) for v in p0);toggle=collections.defaultdict(bool);boundary=set()
   while ptr<len(rays[0]) and int(rays[0,ptr])==qi:
    si=int(rays[1,ptr]);ri,_,_,_,_,a,b=metadata[si];ptr+=1
    if on(p,a,b):boundary.add(ri)
    if (a[1]>p[1])!=(b[1]>p[1]):
     exact_straddle_count+=1; x=a[0]+(p[1]-a[1])*(b[0]-a[0])/(b[1]-a[1])
     if p[0]<x:toggle[ri]=not toggle[ri]
   status='outside'
   if boundary:status='boundary';boundary_points.append(qi)
   else:
    for pi,poly in enumerate(polys(src['geometry'])):
     memberrings=[i for i,r in enumerate(rings) if r['polygon_index']==pi];shell=memberrings[0]
     if toggle[shell] and not any(toggle[r] for r in memberrings[1:]):status='inside';break
   states.append(status)
  states_by_source[src['key']]=states
  report={'key':src['key'],'polygon_count':len(polys(src['geometry'])),'ring_count':len(rings),'original_segment_count':len(segments),'original_corner_count':corner_count,'zero_length_segments':degenerate,'bbox_candidate_pairs_unordered':len(pairs),'adjacent_pairs':adjacent_count,'nonadjacent_exact_pairs_tested':len(nonadj),'retained_nonadjacent_topology_contacts':topology_failures,'point_ray_bbox_candidates':candidate_count,'exact_y_straddling_candidates':exact_straddle_count,'boundary_point_indices':boundary_points,'point_counts':dict(collections.Counter(states)),'elapsed_seconds':time.perf_counter()-t0};reports.append(report);print(json.dumps({'context':ctxt,'source':src['key'],'segments':len(segments),'nonadjacent_candidates':len(nonadj),'topology_contacts':len(topology_failures),'ray_candidates':candidate_count,'elapsed':report['elapsed_seconds']}),flush=True)
 mismatches=[];categories=collections.Counter();rows=[]
 for i,c in enumerate(centres):
  pt=[s['key'] for s in source if s['key'].startswith('dgt_') and states_by_source[s['key']][i]=='inside'];es=[s['key'] for s in source if s['key'].startswith('ign_') and states_by_source[s['key']][i]=='inside'];boundary=[s['key'] for s in source if states_by_source[s['key']][i]=='boundary'];gapstate=states_by_source['original_gap'][i];category='both' if pt and es else 'portugal-only' if pt else 'spain-only' if es else 'neither';categories[category]+=1
  row={'cell':c['cell'],'point_lonlat':c['native_centre_lonlat'],'portugal_member_keys':pt,'spain_member_keys':es,'boundary_member_keys':boundary,'gap_state':gapstate,'source_class':category};rows.append(row)
  if pt!=c['official_portugal_member_keys'] or es!=c['official_spain_member_keys']:mismatches.append(row)
 results[ctxt]={'sources':reports,'sourcepoint_class_counts':dict(categories),'root_projected_preview_member_mismatches':mismatches,'gap_counts':dict(collections.Counter(states_by_source['original_gap']))};(OUT/(ctxt+'-rows.json')).write_text(json.dumps(rows,sort_keys=True,separators=(',',':'))+'\n')
report={'status':'private-indexed-exact-sourcepoint-feasibility-not-repair-or-owner-proposal','source_commit':commit,'source_pins':[s['pin'] for s in source],'gap_shard_sha256':gapref['containing_sha256'],'root_preview_report_sha256':hashlib.sha256(preview_raw).hexdigest(),'root_point_rows_sha256':hashlib.sha256(centre_raw).hexdigest(),'root_point_rows_decoded_sha256':hashlib.sha256(decoded).hexdigest(),'native_input_receipts_independently_verified':native_verified,'point_count':len(centres),'contexts':results,'runtime':{'python':sys.version,'shapely':shapely.__version__,'geos':shapely.geos_version_string,'pyproj':pyproj.__version__,'proj':pyproj.proj_version_str},'elapsed_seconds':time.perf_counter()-start_all,'limits':['Conservative STRtree bounding-box broadphase only; all crossing/incidence/ray decisions performed with exact Fraction arithmetic on unchanged contextual Float64 endpoints.','CRS84 straight segments and projected straight endpoint segments define different geometries; their classifications are compared without declaring one legal/physical truth.','Retained topology contact ledger covers nonadjacent segments. Adjacent backtracking, exact area, hole nesting, multipart containment and complete OGC validity are not yet independently validated.','Point membership uses complete original source geometries as interpreted, never first-owner or geometry assignment; invalidity and unresolved source ambiguity remain separate.','Normative points consumed from byte-verified root preview; its native original file receipts independently reverified, but no new full-grid extraction/ownership installation was done.']}
(OUT/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');print(json.dumps({k:{'counts':v['sourcepoint_class_counts'],'gap':v['gap_counts'],'mismatches':len(v['root_projected_preview_member_mismatches'])} for k,v in results.items()}),flush=True)
