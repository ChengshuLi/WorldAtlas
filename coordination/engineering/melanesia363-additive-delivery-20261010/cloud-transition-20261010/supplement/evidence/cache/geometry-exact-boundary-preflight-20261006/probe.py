import json, pathlib, subprocess, gzip, hashlib, sys, collections
from fractions import Fraction as F
import shapely, pyproj
from shapely.geometry import shape, LineString, Point, box, Polygon
from shapely.ops import transform
from shapely import STRtree
ROOT=pathlib.Path('/Users/chengshuli/world-atlas-workspace'); HOME=ROOT/'.cache/geometry-exact-boundary-preflight-20261006'; BRIEF=ROOT/'.cache/integration-dependencies-972-20261006'
brief=json.loads((BRIEF/'read-only-brief.json').read_bytes()); COMMIT='1ba7ef86a046db62c2c19d731faf8118e6cee124'; repo=ROOT/'WorldAtlas'
def read(path,sha=None):
 b=subprocess.check_output(['git','-C',str(repo),'show',COMMIT+':'+path]); assert sha is None or hashlib.sha256(b).hexdigest()==sha; return b
tr=pyproj.Transformer.from_crs('OGC:CRS84','EPSG:25829',always_xy=True)
def rings(geom):
 if geom['type']=='Polygon': return geom['coordinates']
 assert geom['type']=='MultiPolygon'; return [r for p in geom['coordinates'] for r in p]
def rat(p): return tuple(F(v) for v in p)
def cross(a,b): return a[0]*b[1]-a[1]*b[0]
def sub(a,b): return tuple(x-y for x,y in zip(a,b))
def intersection(a,b,c,d):
 a,b,c,d=map(rat,(a,b,c,d)); u=sub(b,a); v=sub(d,c); w=sub(c,a); den=cross(u,v)
 if not den: return None
 t=cross(w,v)/den; q=cross(w,u)/den
 if not (0<=t<=1 and 0<=q<=1): return None
 return tuple(a[i]+t*u[i] for i in range(2)),t,q
def fs(x): return {'numerator':str(x.numerator),'denominator':str(x.denominator)}
def dyadic(x): return x.denominator & (x.denominator-1)==0
sources=[]; pins=[]
for pin in brief['verified_official_polygon_inputs']:
 raw=read(pin['path'],pin['sha256']); assert len(raw)==pin['bytes']; obj=json.loads(raw); f=obj['features'][0] if obj['type']=='FeatureCollection' else obj
 pins.append({'path':pin['path'],'sha256':pin['sha256'],'bytes':len(raw),'feature_id':f.get('id')})
 for ri,ring in enumerate(rings(f['geometry'])):
  projected=[tr.transform(*p[:2]) for p in ring]
  for si,(a,b) in enumerate(zip(projected,projected[1:])):
   if a!=b: sources.append({'key':pin['key'],'path':pin['path'],'ring_index':ri,'segment_index':si,'geographic_endpoints':[ring[si][:2],ring[si+1][:2]],'projected_endpoints':[a,b]})
ginfo=brief['existing_geometry_locations']['full_gap']; raw=read(ginfo['containing_path'],ginfo['containing_sha256']); gf=next(f for f in json.loads(gzip.decompress(raw))['features'] if f['id']==ginfo['feature_id']); gr=rings(gf['geometry']); assert len(gr)==1
coords=[tr.transform(*p[:2]) for p in gr[0]]; g=Polygon(coords); edges=list(zip(coords,coords[1:])); lines=[LineString(s['projected_endpoints']) for s in sources]; tree=STRtree(lines)
# Candidate envelopes only: exact rational predicates decide crossings; no tolerance changes coordinates.
nodes=[]; boundary_by_edge=collections.defaultdict(list)
for ei,(a,b) in enumerate(edges):
 boundary_by_edge[ei]=[(F(0),rat(a)),(F(1),rat(b))]
 for si in tree.query(LineString([a,b])):
  src=sources[int(si)]; r=intersection(a,b,*src['projected_endpoints'])
  if r is None: continue
  xy,t,u=r; boundary_by_edge[ei].append((t,xy)); nodes.append({'gap_edge_index':ei,'source_index':int(si),'xy':xy,'gap_t':t,'source_t':u})
print('segments',len(sources),'crossings',len(nodes),flush=True)
vertices=json.loads((BRIEF/'root-exact-four-way-vertex-preflight-v1.json').read_bytes())['all_exact_outside_vertices']; provenance=[]
for v in vertices:
 p=Point(v['xy_epsg25829']); ei=min(range(len(edges)),key=lambda i:LineString(edges[i]).distance(p)); near=[n for n in nodes if n['gap_edge_index']==ei]; n=min(near,key=lambda n:Point(tuple(float(x) for x in n['xy'])).distance(p)); rounded=tuple(float(x) for x in n['xy']); xy=rat(v['xy_epsg25829']); a,b=map(rat,edges[ei]); src=sources[n['source_index']]; c,d=map(rat,src['projected_endpoints']); provenance.append({'output_vertex':v,'gap_edge_index':ei,'gap_projected_endpoints':edges[ei],'source_segment':src,'exact_intersection':[fs(x) for x in n['xy']],'exact_gap_t':fs(n['gap_t']),'exact_source_t':fs(n['source_t']),'nearest_ieee64_xy':rounded,'nearest_round_equals_geos_output':rounded==tuple(v['xy_epsg25829']),'round_geos_covers':g.covers(Point(rounded)),'output_on_gap_exact':cross(sub(xy,a),sub(b,a))==0,'output_on_source_exact':cross(sub(xy,c),sub(d,c))==0,'intersection_coordinate_dyadic':[dyadic(x) for x in n['xy']],'nearest_round_distance_to_output_m':Point(rounded).distance(p)})
# Rational boundary split prototype: preserve every original corner and exact source crossing.
split=[]; signed_twice=F(0); original_twice=F(0); failures=[]
for ei,(a,b) in enumerate(edges):
 seq=sorted(set(boundary_by_edge[ei])); ar,br=rat(a),rat(b); original_twice+=cross(ar,br)
 for (ta,aa),(tb,bb) in zip(seq,seq[1:]):
  signed_twice+=cross(aa,bb)
  if not(ta<tb and cross(sub(aa,ar),sub(br,ar))==0 and cross(sub(bb,ar),sub(br,ar))==0): failures.append(ei)
 split.append({'original_gap_edge_index':ei,'nodes':[{'t':fs(t),'xy':[fs(x) for x in xy]} for t,xy in seq]})
# Controlled unavoidable non-dyadic node: horizontal segment y=1/3 created by diagonal (0,0)-(1,1) and (0,1)-(1,0.0?) use (0,1)-(1,-1).
r=intersection((0.,0.),(1.,1.),(0.,1.),(1.,-1.)); rr=tuple(float(x) for x in r[0]); rrF=rat(rr)
controlled={'segments':[[[0,0],[1,1]],[[0,1],[1,-1]]],'rational_intersection':[fs(x) for x in r[0]],'nearest_ieee64':rr,'exact_float_on_first_segment':cross(sub(rrF,(F(0),F(0))),(F(1),F(1)))==0,'exact_float_on_second_segment':cross(sub(rrF,(F(0),F(1))),(F(1),F(-2)))==0,'second_line_residual_x_times_2_plus_y_minus_1':fs(2*rrF[0]+rrF[1]-1)}
result={'source_commit':COMMIT,'source_pins':pins,'gap_shard_sha256':ginfo['containing_sha256'],'gap_geometry_sha256':hashlib.sha256(json.dumps(gf['geometry'],sort_keys=True,separators=(',',':')).encode()).hexdigest(),'runtime':{'python':sys.version,'shapely':shapely.__version__,'geos':shapely.geos_version_string,'pyproj':pyproj.__version__,'proj':pyproj.proj_version_str},'source_segment_count':len(sources),'gap_segment_count':len(edges),'exact_source_gap_crossing_count':len(nodes),'unique_rational_crossing_count':len(set(n['xy'] for n in nodes)),'non_dyadic_crossing_count':sum(any(not dyadic(x) for x in n['xy']) for n in nodes),'outside_vertex_provenance':provenance,'outside_summary':{'count':len(provenance),'all_matched_geos_rounding':sum(v['nearest_round_equals_geos_output'] for v in provenance),'exact_gap_incident_count':sum(v['output_on_gap_exact'] for v in provenance),'exact_source_incident_count':sum(v['output_on_source_exact'] for v in provenance),'rational_crossing_with_any_nondyadic_coord_count':sum(any(not d for d in v['intersection_coordinate_dyadic']) for v in provenance)},'rational_boundary_split':{'edge_count':len(split),'segment_count':sum(len(s['nodes'])-1 for s in split),'exact_collinearity_or_order_failures':failures,'twice_signed_area_equal':signed_twice==original_twice,'all_original_corners_retained':all(s['nodes'][0]['xy']==[fs(x) for x in rat(edges[i][0])] and s['nodes'][-1]['xy']==[fs(x) for x in rat(edges[i][1])] for i,s in enumerate(split))},'controlled_counterexample':controlled,'limits':['Exact arithmetic here means exact rational interpretation of pinned projected IEEE64 endpoints, not exact geodetic projection or legal ground truth.','Rational boundary splitting is executed; full rational planar face assembly/classification is not implemented by this bounded preflight.','Candidate bounding boxes identify possible original source segments; Fraction intersections perform every final incidence and range test.','Original inputs and existing GEOS partition untouched; no float64 repair produced.']}
(HOME/'rational-boundary-split.json').write_text(json.dumps(split,sort_keys=True,separators=(',',':'))+'\n'); (HOME/'report.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n'); print(json.dumps({k:v for k,v in result.items() if k in ['outside_summary','rational_boundary_split','controlled_counterexample','exact_source_gap_crossing_count','non_dyadic_crossing_count']}),flush=True)
