"""Validate pinned WFS administrative features as evidence, never selectors.

The GeoJSON x/y coordinate-order assertion must be supplied by the selected
revision and independently justified from provider behavior. The source's CRS
and 3D zero-height representation are preserved; only OGR's XY plane is used.
Run inside an externally supervised process and pin/recheck all code and bytes.
The raw 3D geometry hash serializes parsed JSON using Python json.dumps with
sorted keys, compact separators, UTF-8 and non-finite numbers forbidden. Integer
and float values remain distinct. This parser does not authenticate custody.
"""
import hashlib,json,math
from pathlib import Path

METHOD='wfs-geojson-epsg4326-xy-zeroz-v1'
HASH_METHOD='python-json-sorted-compact-raw3d-v1'
CRS={'type':'name','properties':{'name':'urn:ogc:def:crs:EPSG::4326'}}

def need(x,m):
 if not x:raise ValueError(m)
def no_dupes(pairs):
 out={}
 for k,v in pairs:need(k not in out,'duplicate JSON key');out[k]=v
 return out
def extract(path,source_sha256,features,coordinate_method,guard,max_bytes=16<<20,max_vertices=1000000):
 from osgeo import ogr
 need(callable(guard) and coordinate_method==METHOD,'unsupported coordinate assertion');need(type(max_bytes) is int and 0<max_bytes<=16<<20 and type(max_vertices) is int and 0<max_vertices<=1000000,'invalid limits')
 need(isinstance(features,list) and 0<len(features)<=1000,'invalid feature descriptors');by_id={}
 for f in features:
  need(isinstance(f,dict) and set(f)=={'feature_id','source_feature_id','name','geometry_sha256','geometry_hash_method'} and all(isinstance(f.get(k),str) and f[k] for k in f) and f['geometry_hash_method']==HASH_METHOD,'bad feature descriptor');need(f['source_feature_id'] not in by_id and len(f['geometry_sha256'])==64 and all(c in '0123456789abcdef' for c in f['geometry_sha256']),'duplicate feature or invalid geometry pin');by_id[f['source_feature_id']]=f
 need(len({x['feature_id'] for x in features})==len(features) and len({x['name'] for x in features})==len(features),'duplicate feature ID or name');p=Path(path).resolve(strict=True);guard();need(p.is_file() and 0<p.stat().st_size<=max_bytes,'bad source size')
 with p.open('rb') as f:b=f.read(max_bytes+1)
 need(len(b)<=max_bytes and hashlib.sha256(b).hexdigest()==source_sha256,'source hash mismatch');d=json.loads(b,object_pairs_hook=no_dupes,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('nonfinite JSON')));need(isinstance(d,dict) and d.get('type')=='FeatureCollection' and d.get('crs')==CRS and isinstance(d.get('features'),list) and len(d['features'])==len(features),'source collection or CRS mismatch');result={};count=0
 for f in d['features']:
  guard();need(isinstance(f,dict) and f.get('type')=='Feature' and 'crs' not in f and isinstance(f.get('properties'),dict),'invalid feature');props=f['properties'];id=props.get('cistat');want=by_id.get(id);need(isinstance(id,str) and want is not None and id not in result and props.get('nome')==want['name'],'missing, duplicate or misnamed administrative feature');g=f.get('geometry');need(isinstance(g,dict) and set(g)=={'type','coordinates'} and g['type'] in ('Polygon','MultiPolygon'),'invalid geometry');polys=[g['coordinates']] if g['type']=='Polygon' else g['coordinates'];need(isinstance(polys,list) and polys,'empty polygons')
  for poly in polys:
   need(isinstance(poly,list) and poly,'empty polygon')
   for ring in poly:
    need(isinstance(ring,list) and len(ring)>=4 and ring[0]==ring[-1],'invalid ring');last=None
    for xyz in ring:
     count+=1
     if count%1024==0:guard()
     need(count<=max_vertices and isinstance(xyz,list) and len(xyz)==3 and all(type(v) in (int,float) and math.isfinite(v) for v in xyz) and xyz[2]==0,'invalid position or vertex limit');x,y,_=xyz;need(-180<=x<=180 and -90<=y<=90 and (last is None or abs(x-last)<=180),'unsupported coordinate or antimeridian');last=x
  raw=json.dumps(g,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode();h=hashlib.sha256(raw).hexdigest();need(h==want['geometry_sha256'],'geometry hash mismatch');ogr_geom=ogr.CreateGeometryFromJson(raw.decode());need(ogr_geom is not None and not ogr_geom.IsEmpty() and ogr_geom.IsValid(),'invalid OGR geometry');result[id]={'geometry':g,'feature_id':want['feature_id'],'source_feature_id':id,'name':want['name'],'geometry_sha256':h}
 need(set(result)==set(by_id) and p.stat().st_size==len(b),'missing feature or source size changed');h=hashlib.sha256();size=0
 with p.open('rb') as stream:
  while True:
   guard();chunk=stream.read(1<<20)
   if not chunk:break
   size+=len(chunk);need(size<=max_bytes,'source size exceeded');h.update(chunk)
 need(size==len(b) and h.hexdigest()==source_sha256,'source changed')
 return result,{'source_sha256':source_sha256,'coordinate_method':METHOD,'declared_crs':'EPSG:4326','coordinate_order_status':'selected_provider_specific_assertion','geometry_hash_method':HASH_METHOD,'source_geometry_dimensions':'longitude, latitude, zero height','feature_ids':[result[k]['feature_id'] for k in sorted(result)],'limitations':['Provider-original custody is not authenticated by this parser.','Geometry hashes retain raw three-dimensional JSON; coverage measures only the XY plane.','Administrative geometry corroborates location but does not itself prove geographic island identity.','The provider-specific GeoJSON longitude/latitude axis interpretation is a selected source assertion.']}
