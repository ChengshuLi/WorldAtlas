"""Extract hash-bound source polygon coordinates; no land decisions are made.

Run with external process-group memory/time supervision. OGR validation and
rasterization are separate mandatory steps. Accept only bounded raw GeoJSON.
Geometry hash uses parsed JSON numeric types, sorted keys, compact UTF-8 JSON,
and Python's finite float formatting. Integer and floating values are distinct.
"""
import hashlib,json,math
from pathlib import Path

def need(v,m):
 if not v:raise ValueError(m)
def no_dupes(pairs):
 d={}
 for k,v in pairs:need(k not in d,'duplicate JSON key');d[k]=v
 return d
def canonical(g):return json.dumps(g,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def extract(path,sha256,feature,max_bytes=16<<20,max_vertices=1000000):
 p=Path(path);need(type(max_bytes) is int and 0<max_bytes<=16<<20 and type(max_vertices) is int and 0<max_vertices<=1000000,'invalid bounds')
 need(p.is_file() and p.stat().st_size<=max_bytes,'source too large')
 with p.open('rb') as f:b=f.read(max_bytes+1)
 need(len(b)<=max_bytes and hashlib.sha256(b).hexdigest()==sha256,'source hash mismatch')
 d=json.loads(b,object_pairs_hook=no_dupes,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('nonfinite JSON')))
 need(isinstance(d,dict) and d.get('type')=='FeatureCollection' and isinstance(d.get('features'),list) and len(d['features'])<=100000,'invalid feature collection')
 need('crs' not in d or d['crs']=={'type':'name','properties':{'name':'urn:ogc:def:crs:OGC:1.3:CRS84'}},'unsupported CRS')
 key=feature['id_property'];target=feature['source_feature_id'];matches=[]
 for f in d['features']:
  need(isinstance(f,dict) and f.get('type')=='Feature' and isinstance(f.get('properties'),dict) and 'crs' not in f,'invalid source feature')
  v=f['properties'].get(key)
  if type(v) in (str,int) and str(v)==target:matches.append(f)
 need(len(matches)==1,'source feature is missing or ambiguous');expected=feature.get('expected_properties',{});need(isinstance(expected,dict) and all(matches[0]['properties'].get(k)==v for k,v in expected.items()),'source feature identity properties mismatch');g=matches[0].get('geometry');need(isinstance(g,dict) and set(g)=={'type','coordinates'} and g['type'] in ('Polygon','MultiPolygon'),'unsupported polygon geometry')
 polys=[g['coordinates']] if g['type']=='Polygon' else g['coordinates'];need(isinstance(polys,list) and polys,'empty polygon');count=0
 for poly in polys:
  need(isinstance(poly,list) and poly,'empty polygon part')
  for ring in poly:
   need(isinstance(ring,list) and len(ring)>=4 and ring[0]==ring[-1],'invalid polygon ring');prev=None
   for point in ring:
    need(isinstance(point,list) and len(point)==2 and all(type(v) in (int,float) and math.isfinite(v) for v in point),'invalid coordinate');lon,lat=point
    need(-180<=lon<=180 and -90<=lat<=90 and (prev is None or abs(lon-prev)<=180),'unsupported coordinate or dateline wrap');prev=lon;count+=1;need(count<=max_vertices,'vertex limit exceeded')
 digest=hashlib.sha256(canonical(g)).hexdigest();need(digest==feature['geometry_sha256'],'geometry hash mismatch');need(p.stat().st_size==len(b),'source size changed');return g,{'source_sha256':sha256,'geometry_sha256':digest,'vertices':count,'coordinate_reference':'OGC:CRS84','validity':'OGR validation required separately'}
