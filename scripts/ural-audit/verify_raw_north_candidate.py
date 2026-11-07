import sys,json,hashlib,math
from shapely.geometry import LineString
from pyproj import Geod
sys.path.insert(0,'landed-1b494125')
from terrain_basin_screen import checked_shapes
G=Geod(ellps='WGS84')
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
files={'selector':('ural-watershed-first4954.json','0a1aee04c5d60fec6f039b709720f2c7e4ae7f2522d8224fdfe0d9086978ccb4'),'gap00':('/tmp/ural-gap00-arctic-intersection-route.json','d07c10176b68d740c3f6c7d584badc5367b974d2704cb28ea2933ed784ea22b6'),'gap02':('/tmp/ural-gap02-arctic-intersection-route.json','f04de00934fcbd59bb68e1385997b0650a8e879c2fdf4f53dc13a467a5b955bd'),'raw_crossings':('/tmp/ural-gap-raw-edge-crossings.jsonl','97cbca7c797dbc3fa047360b2ee6cc74a6db70076dd73a72f6a59944a49d048f'),'coverage':('/tmp/ural-raw-chord-coverage.json','c14ea539567985a5ff76be2f0eb065b7d2f2bfbba4cfeba375793d7bf872fa67'),'raw_template':('/tmp/ural-raw-chord-template.json','87c92c1490692fd79a33c48fe365c9f44ffcc4c9705c243fae343f5185939705'),'snapshot':('/tmp/review_snapshot.json','615bc1aaa67d099ebd140dc172fd54885d66e82ef595a57a97e5a284f483f7cc')}
for k,(p,h) in files.items():
 if sha(p)!=h:raise ValueError('bad pin '+k)
s=json.load(open(files['selector'][0]));snap=json.load(open(files['snapshot'][0]));boundary=next(b for b in snap['mainland_boundaries'] if b['boundary_id']=='ural_kara_coast_to_caspian');closure=next(r for r in snap['routes'] if r['route_id']=='europe_exterior_closure_v1');start=closure['geometry']['coordinates'][0]
if start!=s[0]:raise ValueError('closure start is not the selected northern terminal')
coverage=json.load(open(files['coverage'][0]));
if coverage['source_line_sha256'] != files['raw_template'][1]: raise ValueError('coverage refers to different raw template')
counts=[v['counts'] for v in coverage['ranges'].values()]
if sum(c.get('segments',0) for c in counts)!=3437 or any(c.get('uncovered_over_1mm',0) or c.get('collapsed',0) for c in counts):raise ValueError('raw-edge coverage is incomplete')
raw={v['gap']:v for v in (json.loads(line) for line in open(files['raw_crossings'][0]))};gaps={n:json.load(open(files['gap'+n][0])) for n in ('00','02')}
features=checked_shapes('/tmp/ural-hydro-eu.zip','21797d53e0792cae047d25f0c3cfb570c7ef43700ec962b35b2ac92467e29f03','/tmp/ural-hydro-eu/hybas_eu_lev12_v1c.shp',(58.95,54.71,67.17,68.74));vertex=set()
for geom,_ in features:
 for poly in getattr(geom,'geoms',[geom]):
  for ring in [poly.exterior,*poly.interiors]:vertex.update(ring.coords)
raw_edges=set()
for geom,_ in features:
 for poly in getattr(geom,'geoms',[geom]):
  for ring in [poly.exterior,*poly.interiors]:
   points=list(ring.coords)
   for a,b in zip(points,points[1:]): raw_edges.add((tuple(a),tuple(b))); raw_edges.add((tuple(b),tuple(a)))
for n in ('00','02'):
 for side in ('north','south'):
  for hit in raw[n]['raw_edge_crossings'][side]['closest']:
   if tuple(map(tuple,hit[2])) not in raw_edges: raise ValueError('cut edge is absent from raw HydroBASINS')
   if LineString(hit[2]).distance(__import__('shapely').geometry.Point(hit[1])) > 1e-12: raise ValueError('cut not on source edge')
for i in (4,5,1626,1895,2318,3548,4251,4259,4673,4683):
 if tuple(s[i]) not in vertex:
  # A 1e-12-degree normalized topology is used only for matching, not distance.
  if not any(abs(a-s[i][0])<=1e-12 and abs(b-s[i][1])<=1e-12 for a,b in vertex):raise ValueError('not a raw source vertex '+str(i))
shore=LineString([s[4],s[5]]);x0=min(s[4][0],s[5][0])-.01;x1=max(s[4][0],s[5][0])+.01;z=shore.intersection(LineString([(x0,start[1]),(x1,start[1])]))
if z.geom_type!='Point':raise ValueError('ambiguous northern source-coast crossing')
shorepoint=[z.x,z.y];prefix=[start,shorepoint]+s[5:1627];paths={}
for n in ('00','02'):
 v=gaps[n];coords=[x[:] for x in v['coordinates']]
 for side,idx in [('north',0),('south',-1)]:
  hits=raw[n]['raw_edge_crossings'][side]['closest']
  if len(hits)!=1 or hits[0][0]>0.1:raise ValueError('ambiguous or distant raw crossing '+n+side)
  coords[idx]=hits[0][1]
 if not LineString(coords).is_simple:raise ValueError('terrain path self-intersects')
 paths[n]=coords
omit=set(range(4252,4259))|set(range(4674,4681));tail=[v for i,v in enumerate(s) if i>=3548 and i not in omit]
coords=prefix+paths['00']+s[1895:2319]+paths['02']+tail
if not LineString(coords).is_simple:raise ValueError('raw-backed northern line is not simple')
for k,(p,h) in files.items():
 if sha(p)!=h:raise ValueError('input changed '+k)
geometry={'type':'LineString','coordinates':coords};digest=hashlib.sha256(json.dumps(geometry,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
with open('/tmp/ural-raw-backed-north-verified.geometry.json','x') as f:json.dump(geometry,f,separators=(',',':'),sort_keys=True,allow_nan=False);f.write('\n')
report={'status':'research-not-selected','geometry_sha256':digest,'coordinate_count':len(coords),'source_selector_sha256':files['selector'][1],'raw_eu_sha256':'21797d53e0792cae047d25f0c3cfb570c7ef43700ec962b35b2ac92467e29f03','raw_edge_coverage_report_sha256':files['coverage'][1],'raw_cut_report_sha256':files['raw_crossings'][1],'gap_route_sha256':[files['gap00'][1],files['gap02'][1]],'coast_connector_wgs84_m':G.inv(*start,*shorepoint)[2],'source_cut_adjustment_wgs84_m':{n:{side:raw[n]['raw_edge_crossings'][side]['closest'][0][0] for side in ('north','south')} for n in ('00','02')},'limits':['Prior structured northern line selects raw source edges; this is a policy/selector input, not historical derivation.','Raw edge coverage uses normalized 1e-12-degree topology and <=1 mm residual test; cut/source joins are planar floating-point intersections.','Two prior geodesic-interpolated spans are replaced by their verified raw-source chords.','Kara coast attachment is a documented physically-derived construction, not surveyed boundary; physical closure must be revalidated.','Terrain gap algorithms remain model-dependent.','No Neon selection or map build.']}
with open('/tmp/ural-raw-backed-north-verified.report.json','x') as f:json.dump(report,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
print(json.dumps(report,sort_keys=True))
