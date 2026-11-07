"""Dispatch selected raw polygon sources to reviewed, pinned extractors.

This is an internal helper. The caller must authenticate the selected export,
raw source custody before use.
OSM-derived geometry stays in memory and is never an R2 source object.
"""
import hashlib,types,xml.parsers.expat as expat
from decimal import Decimal,InvalidOperation
from pathlib import Path
import polygon_source
OSM_CODE=Path(__file__).resolve().parent.parent/'osm-relation-adapter-20261104/osm_outer_relation_v2.py'
OSM_CODE_SHA256='749027ae0ac3ae06c20a8ce87a0912b2481721cf773699525989b757beb051a8'
OSM_CODE_V3=Path(__file__).resolve().parent.parent/'osm-relation-adapter-20261104/osm_outer_relation_v3.py'
OSM_CODE_V3_SHA256='1ec2c1b224528698a0e2e5bf6bd6fecd657e659da30de8188e3a7b12497f3d6c'
OSM_CODE_V4=Path(__file__).resolve().parent.parent/'osm-relation-adapter-20261104/osm_outer_relation_v4.py'
OSM_CODE_V4_SHA256='618fece35eac7aa13cd05957a517f278004be8a6be5fd62d965e6d649cac10dd'
ANCHOR_CODE=Path(__file__).resolve().parent.parent/'aegean-rhodes-method-20261104/osm_anchored_outer_ring_v1.py'
ANCHOR_CODE_SHA256='1d7ba4312a3c08ff56272b2e2e392eda0ba5cf4e7c7e9afaa3ad7a895bcddd21'
LABEL_CODE=Path(__file__).resolve().parent.parent/'osm-label-member-prototype-20261104/label_member_v2.py'
LABEL_CODE_SHA256='ddb285bd1fdc198617f9e38f9efd3b46f62a4df6c74b828dce317c7e91a1b61f'
ADMIN_CODE=Path(__file__).resolve().parent.parent/'osm-relation-adapter-20261104/osm_admin_envelope_v1.py'
ADMIN_CODE_SHA256='27e8259ca26a58dd3f837a78e4b1aaed719abcdf30e310601003d60d3c952fe2'
REEF_CODE=Path(__file__).resolve().parent.parent/'osm-relation-adapter-20261104/osm_reef_envelope_v1.py'
REEF_CODE_SHA256='ee7e38b674b20f29e6a43834de7be0242bea1b2600c4581e247e804fe09f10b9'
WAY_CODE=Path(__file__).resolve().parent/'osm_closed_way.py'
WAY_CODE_SHA256='8527a43d13ec4203fc29d65e3fa2e52e92617847d98338b82e938386a88cbe4b'
LAND_CODE=Path(__file__).resolve().parent/'land_archive_source.py'
LAND_CODE_SHA256='54463745d57c0fb266103fc67c0c51c4b5d674f830c445b2fd7ba99a80937a72'
def need(v,m):
 if not v:raise ValueError(m)
def read_anchor_code():
 with ANCHOR_CODE.open('rb') as f:code=f.read((1<<20)+1)
 need(len(code)<=1<<20,'anchored extractor too large');return code
def validate_map_export_bounds(path,expected,expected_sha256):
 need(isinstance(expected,dict) and set(expected)=={'minlon','minlat','maxlon','maxlat'} and all(isinstance(v,str) and 0<len(v)<=24 for v in expected.values()),'invalid expected map export bounds')
 try:bounds={k:Decimal(v) for k,v in expected.items()}
 except (InvalidOperation,TypeError):raise ValueError('invalid expected map export bounds') from None
 need(all(v.is_finite() for v in bounds.values()) and -180<=bounds['minlon']<bounds['maxlon']<=180 and -90<=bounds['minlat']<bounds['maxlat']<=90 and bounds['maxlon']-bounds['minlon']<=1 and bounds['maxlat']-bounds['minlat']<=1 and (bounds['maxlon']-bounds['minlon'])*(bounds['maxlat']-bounds['minlat'])<=Decimal('0.25'),'invalid expected map export bounds')
 stack=[];found=[];digest=hashlib.sha256();parser=expat.ParserCreate()
 def reject(*args):raise ValueError('DTD and entity declarations are forbidden')
 parser.StartDoctypeDeclHandler=reject;parser.EntityDeclHandler=reject;parser.UnparsedEntityDeclHandler=reject;parser.NotationDeclHandler=reject;parser.ExternalEntityRefHandler=reject;parser.SkippedEntityHandler=reject;parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
 def start(name,attrs):
  stack.append(name)
  if len(stack)==1:need(name=='osm','expected OSM document')
  if len(stack)==2 and name in ('node','way','relation'):need(attrs.get('visible')=='true','map export contains non-visible object')
  if name=='bounds':
   need(len(stack)==2 and stack[0]=='osm' and not found and set(attrs)==set(expected),'invalid map bounds element')
   try:actual={k:Decimal(v) for k,v in attrs.items()}
   except InvalidOperation:raise ValueError('invalid map bounds element') from None
   need(actual==bounds,'map export bounds mismatch');found.append(True)
 def end(name):need(stack and stack.pop()==name,'invalid XML nesting')
 parser.StartElementHandler=start;parser.EndElementHandler=end
 with path.open('rb') as f:
  while True:
   b=f.read(1<<16)
   if not b:break
   digest.update(b);parser.Parse(b,False)
  parser.Parse(b'',True)
 need(len(found)==1,'map export bounds missing');need(digest.hexdigest()==expected_sha256,'map export source hash mismatch')
 return bounds
def validate_geometry_in_bounds(geometry,bounds):
 need(geometry.get('type')=='MultiPolygon','unexpected map geometry')
 for polygon in geometry['coordinates']:
  for ring in polygon:
   for lon,lat in ring:need(bounds['minlon']<=Decimal(str(lon))<=bounds['maxlon'] and bounds['minlat']<=Decimal(str(lat))<=bounds['maxlat'],'relation extends outside export bounds')
def extract_land_many(features,source_pin):
 need(isinstance(features,list) and features and all(isinstance(f,dict) and f.get('extractor_version')=='osm-split-land-archive-v1' and f.get('source_format')=='osm-split-land-shapefile' for f in features) and isinstance(source_pin,dict) and isinstance(source_pin.get('shapefile_path'),str),'invalid land archive source')
 p=Path(source_pin['path']).resolve(strict=True);need(p.is_file() and type(source_pin.get('size_bytes')) is int and source_pin['size_bytes']>0 and p.stat().st_size==source_pin['size_bytes'],'source size mismatch')
 with LAND_CODE.open('rb') as f:code=f.read((1<<20)+1)
 need(len(code)<=1<<20 and hashlib.sha256(code).hexdigest()==LAND_CODE_SHA256,'land archive extractor code mismatch');module=types.ModuleType('trusted_land_archive');exec(compile(code,str(LAND_CODE),'exec'),module.__dict__)
 pins=[{'source_feature_id':f['source_feature_id'],'geometry_sha256':f['geometry_sha256']} for f in features];result=module.extract(p,source_pin['shapefile_path'],source_pin['sha256'],pins)
 with LAND_CODE.open('rb') as f:after=f.read((1<<20)+1)
 need(after==code and p.stat().st_size==source_pin['size_bytes'] and len(result)==len(features),'land archive source or extractor changed');return result

def extract(feature,source_pin):
 need(isinstance(feature,dict) and isinstance(source_pin,dict),'invalid polygon loader request')
 if feature.get('extractor_version')=='osm-split-land-archive-v1':return extract_land_many([feature],source_pin)[0]
 p=Path(source_pin['path']).resolve(strict=True);need(p.is_file() and type(source_pin.get('size_bytes')) is int and source_pin['size_bytes']>0 and p.stat().st_size==source_pin['size_bytes'],'source size mismatch')
 need(source_pin['size_bytes']<=64<<20,'source size mismatch')
 if feature.get('source_format')=='geojson':return polygon_source.extract(p,source_pin['sha256'],feature)
 if feature.get('source_format')=='federal-register-pdf-rectangle-v1':
  import federal_register_rectangle
  params=feature['rectangle_extraction'];g=federal_register_rectangle.extract_pdf_rectangle(p,source_pin['sha256'],source_pin['size_bytes'],feature['geometry_sha256'],params['page'],params['crop'],params['heading'],params['next_heading']);need(g==feature['expected_geometry'],'structured exclusion geometry/source mismatch');return g,{'source_sha256':source_pin['sha256'],'geometry_sha256':feature['geometry_sha256'],'extractor_version':'federal-register-pdf-rectangle-v1','page':params['page'],'limitations':['The extracted management footprint is not a physical island boundary.']}
 version=feature.get('extractor_version')
 if version=='osm-admin-envelope-v1':
  need(feature.get('source_format')=='osm-xml' and feature.get('source_class')=='admin_envelope','invalid administrative source');code=ADMIN_CODE.read_bytes();need(len(code)<=1<<20 and hashlib.sha256(code).hexdigest()==ADMIN_CODE_SHA256,'administrative extractor code mismatch');module=types.ModuleType('trusted_admin_envelope');exec(compile(code,str(ADMIN_CODE),'exec'),module.__dict__);g,trace=module.extract(p,source_pin['sha256'],feature['source_feature_id'],feature['relation_version'],feature['geometry_sha256']);tags=feature['expected_identity_tags'];need(isinstance(tags,dict) and tags.get('boundary')=='administrative' and tags.get('admin_level') in ('2','3') and all(trace['tags'].get(k)==v for k,v in tags.items()),'administrative relation identity tags mismatch');need(ADMIN_CODE.read_bytes()==code and p.stat().st_size==source_pin['size_bytes'],'administrative source or extractor changed');trace.update(extractor_version=version,extractor_sha256=ADMIN_CODE_SHA256,verified_identity_tags=tags);return g,trace
 if version=='osm-reef-envelope-v1':
  need(feature.get('source_format')=='osm-xml' and feature.get('source_class')=='reef_envelope','invalid reef source');code=REEF_CODE.read_bytes();need(len(code)<=1<<20 and hashlib.sha256(code).hexdigest()==REEF_CODE_SHA256,'reef extractor code mismatch');module=types.ModuleType('trusted_reef_envelope');exec(compile(code,str(REEF_CODE),'exec'),module.__dict__);g,trace=module.extract(p,source_pin['sha256'],feature['source_feature_id'],feature['relation_version'],feature['geometry_sha256']);tags=feature['expected_identity_tags'];need(isinstance(tags,dict) and tags.get('natural')=='reef' and any(tags.get(k) for k in ('name','name:en')) and all(trace['tags'].get(k)==v for k,v in tags.items()),'reef relation identity tags mismatch');need(REEF_CODE.read_bytes()==code and p.stat().st_size==source_pin['size_bytes'],'reef source or extractor changed');trace.update(extractor_version=version,extractor_sha256=REEF_CODE_SHA256,verified_identity_tags=tags);return g,trace
 if version=='osm-closed-way-map-export-v1':
  need(feature.get('source_format')=='osm-xml' and feature.get('source_class')=='island','invalid closed-way source')
  with WAY_CODE.open('rb') as f:code=f.read((1<<20)+1)
  need(len(code)<=1<<20 and hashlib.sha256(code).hexdigest()==WAY_CODE_SHA256,'closed-way extractor code mismatch');module=types.ModuleType('trusted_osm_closed_way');exec(compile(code,str(WAY_CODE),'exec'),module.__dict__)
  g,trace=module.extract(p,source_pin['sha256'],feature['source_feature_id'],feature['way_version'],feature['expected_identity_tags'],feature['map_export_bounds'],feature['geometry_sha256'])
  with WAY_CODE.open('rb') as f:after=f.read((1<<20)+1)
  need(after==code and p.stat().st_size==source_pin['size_bytes'],'closed-way source or extractor changed');trace.update(extractor_version=version,extractor_sha256=WAY_CODE_SHA256);return g,trace
 if version=='osm-multipolygon-outer-label-v1':
  need(feature.get('source_format')=='osm-xml' and feature.get('source_class')=='archipelago' and str(feature.get('source_feature_id','')).isdigit() and str(feature.get('relation_version','')).isdigit(),'invalid label source')
  with LABEL_CODE.open('rb') as f:code=f.read((1<<20)+1)
  need(len(code)<=1<<20 and hashlib.sha256(code).hexdigest()==LABEL_CODE_SHA256,'label extractor code mismatch')
  module=types.ModuleType('trusted_osm_label');module.__file__=str(LABEL_CODE);exec(compile(code,str(LABEL_CODE),'exec'),module.__dict__)
  g,trace=module.extract(p,source_pin['sha256'],feature['source_feature_id'],feature['relation_version'],feature['label_node_id'],feature['label_node_version'],feature['expected_label_tags'],feature['geometry_sha256'])
  tags=feature['expected_identity_tags'];need(isinstance(tags,dict) and set(tags)<={'name','name:en','place','wikidata'} and tags.get('place')=='archipelago' and any(isinstance(tags.get(k),str) and tags[k] for k in ('name','name:en')) and all(isinstance(v,str) and v and trace['tags'].get(k)==v for k,v in tags.items()),'OSM relation identity tags mismatch')
  with LABEL_CODE.open('rb') as f:after=f.read((1<<20)+1)
  need(after==code and p.stat().st_size==source_pin['size_bytes'],'label source or extractor changed');trace.update(extractor_version=version,extractor_sha256=LABEL_CODE_SHA256,verified_identity_tags=tags,limitation='Label node is authenticated but is not a geographic selector; source custody and historical byte identity require separate proof.')
  return g,trace
 if version=='osm-anchored-outer-rings-v1':
  need(feature.get('source_format')=='osm-xml' and feature.get('source_class')=='archipelago' and str(feature.get('source_feature_id','')).isdigit() and str(feature.get('relation_version','')).isdigit(),'invalid anchored source');code=read_anchor_code();need(hashlib.sha256(code).hexdigest()==ANCHOR_CODE_SHA256,'anchored extractor code mismatch');module=types.ModuleType('trusted_osm_anchor');module.__file__=str(ANCHOR_CODE);exec(compile(code,str(ANCHOR_CODE),'exec'),module.__dict__);g,trace=module.extract_many(p,source_pin['sha256'],feature['source_feature_id'],feature['relation_version'],feature['expected_relation_tags'],feature['anchors'],feature['geometry_sha256']);need(read_anchor_code()==code and p.stat().st_size==source_pin['size_bytes'],'anchored extractor or source changed');trace.update(extractor_version=version,extractor_sha256=ANCHOR_CODE_SHA256);return g,trace
 need(feature.get('source_format')=='osm-xml' and version in ('osm-multipolygon-outer-v2','osm-multipolygon-outer-v3','osm-multipolygon-outer-v4') and str(feature.get('source_feature_id','')).isdigit() and str(feature.get('relation_version','')).isdigit(),'unsupported OSM extractor')
 codepath,expected={'osm-multipolygon-outer-v2':(OSM_CODE,OSM_CODE_SHA256),'osm-multipolygon-outer-v3':(OSM_CODE_V3,OSM_CODE_V3_SHA256),'osm-multipolygon-outer-v4':(OSM_CODE_V4,OSM_CODE_V4_SHA256)}[version]
 with codepath.open('rb') as f:code=f.read((1<<20)+1)
 need(len(code)<=1<<20 and hashlib.sha256(code).hexdigest()==expected,'OSM extractor code mismatch')
 module=types.ModuleType('trusted_osm_outer');exec(compile(code,str(codepath),'exec'),module.__dict__)
 bounds=feature.get('map_export_bounds')
 if bounds is not None:need(version=='osm-multipolygon-outer-v4' and feature.get('source_class') in ('archipelago','island'),'map export requires v4 relation');bounds=validate_map_export_bounds(p,bounds,source_pin['sha256'])
 g,trace=module.extract(p,source_pin['sha256'],feature['source_feature_id'],feature['relation_version'],feature['geometry_sha256'])
 if bounds is not None:validate_geometry_in_bounds(g,bounds);trace['map_export_bounds']={k:str(v) for k,v in bounds.items()}
 if version in ('osm-multipolygon-outer-v3','osm-multipolygon-outer-v4'):
  tags=feature.get('expected_identity_tags');allowed={'name','name:en','place','wikidata'}|({'alt_name'} if version=='osm-multipolygon-outer-v4' else set());need(isinstance(tags,dict) and set(tags)<=allowed and tags.get('place')==('archipelago' if feature.get('source_class')=='archipelago' else 'island') and (feature.get('source_class')!='archipelago' or version=='osm-multipolygon-outer-v4') and any(isinstance(tags.get(k),str) and tags[k] for k in ('name','name:en')) and all(isinstance(v,str) and v and trace.get('tags',{}).get(k)==v for k,v in tags.items()),'OSM relation identity tags mismatch');trace['verified_identity_tags']=tags
 with codepath.open('rb') as f:after=f.read((1<<20)+1)
 need(after==code and p.stat().st_size==source_pin['size_bytes'],'source or extractor changed');trace.update(extractor_version=feature['extractor_version'],extractor_sha256=expected,limitation='Source geometry is runtime-derived; historical V7 source-byte identity must be assessed separately.')
 return g,trace
