"""Dispatch selected raw polygon sources to reviewed, pinned extractors.

This is an internal helper. The caller must authenticate the selected export,
raw source custody and run under an independent group memory/time watchdog.
OSM-derived geometry stays in memory and is never an R2 source object.
"""
import hashlib,types,xml.parsers.expat as expat
from decimal import Decimal,InvalidOperation
from pathlib import Path
import polygon_source
OSM_CODE=Path(__file__).resolve().parent.parent/'osm-relation-adapter-20261104/osm_outer_relation_v2.py'
OSM_CODE_SHA256='122616244cc7428b0c878aa9740b44934b0260abe0a25f239a4ff92398301690'
OSM_CODE_V3=Path(__file__).resolve().parent.parent/'osm-relation-adapter-20261104/osm_outer_relation_v3.py'
OSM_CODE_V3_SHA256='9b004d5822004110ff8d8fdaae958acf11bf49533353590293f38cdc33caba3d'
OSM_CODE_V4=Path(__file__).resolve().parent.parent/'osm-relation-adapter-20261104/osm_outer_relation_v4.py'
OSM_CODE_V4_SHA256='de81cfa04451f51b0917b12d412af371420e084fef17c95fd10f2db62683fe8a'
ANCHOR_CODE=Path(__file__).resolve().parent.parent/'aegean-rhodes-method-20261104/osm_anchored_outer_ring_v1.py'
ANCHOR_CODE_SHA256='3402b17dad6f7c1ab32cb8dd4666fcf151448ee76ab5bee535a2ba2046e217e3'
LABEL_CODE=Path(__file__).resolve().parent.parent/'osm-label-member-prototype-20261104/label_member_v2.py'
LABEL_CODE_SHA256='7a37d43bbb88a80671ea3cf74221606cc6d890f13343598fa52d455ba0d335b7'
def need(v,m):
 if not v:raise ValueError(m)
def read_anchor_code():
 with ANCHOR_CODE.open('rb') as f:code=f.read((1<<20)+1)
 need(len(code)<=1<<20,'anchored extractor too large');return code
def validate_map_export_bounds(path,expected,expected_sha256,guard):
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
   digest.update(b);parser.Parse(b,False);guard()
  parser.Parse(b'',True)
 need(len(found)==1,'map export bounds missing');need(digest.hexdigest()==expected_sha256,'map export source hash mismatch')
 return bounds
def validate_geometry_in_bounds(geometry,bounds):
 need(geometry.get('type')=='MultiPolygon','unexpected map geometry')
 for polygon in geometry['coordinates']:
  for ring in polygon:
   for lon,lat in ring:need(bounds['minlon']<=Decimal(str(lon))<=bounds['maxlon'] and bounds['minlat']<=Decimal(str(lat))<=bounds['maxlat'],'relation extends outside export bounds')
def extract(feature,source_pin,guard):
 need(isinstance(feature,dict) and isinstance(source_pin,dict) and callable(guard),'invalid polygon loader request')
 p=Path(source_pin['path']).resolve(strict=True);need(p.is_file() and type(source_pin.get('size_bytes')) is int and 0<source_pin['size_bytes']<=64<<20 and p.stat().st_size==source_pin['size_bytes'],'source size mismatch')
 if feature.get('source_format')=='geojson':return polygon_source.extract(p,source_pin['sha256'],feature)
 version=feature.get('extractor_version')
 if version=='osm-multipolygon-outer-label-v1':
  need(feature.get('source_format')=='osm-xml' and feature.get('source_class')=='archipelago' and str(feature.get('source_feature_id','')).isdigit() and str(feature.get('relation_version','')).isdigit(),'invalid label source')
  guard()
  with LABEL_CODE.open('rb') as f:code=f.read((1<<20)+1)
  need(len(code)<=1<<20 and hashlib.sha256(code).hexdigest()==LABEL_CODE_SHA256,'label extractor code mismatch')
  module=types.ModuleType('trusted_osm_label');module.__file__=str(LABEL_CODE);exec(compile(code,str(LABEL_CODE),'exec'),module.__dict__)
  g,trace=module.extract(p,source_pin['sha256'],feature['source_feature_id'],feature['relation_version'],feature['label_node_id'],feature['label_node_version'],feature['expected_label_tags'],feature['geometry_sha256'],guard)
  tags=feature['expected_identity_tags'];need(isinstance(tags,dict) and set(tags)<={'name','name:en','place','wikidata'} and tags.get('place')=='archipelago' and any(isinstance(tags.get(k),str) and tags[k] for k in ('name','name:en')) and all(isinstance(v,str) and v and trace['tags'].get(k)==v for k,v in tags.items()),'OSM relation identity tags mismatch')
  with LABEL_CODE.open('rb') as f:after=f.read((1<<20)+1)
  need(after==code and p.stat().st_size==source_pin['size_bytes'],'label source or extractor changed');trace.update(extractor_version=version,extractor_sha256=LABEL_CODE_SHA256,verified_identity_tags=tags,limitation='Label node is authenticated but is not a geographic selector; source custody and historical byte identity require separate proof.')
  return g,trace
 if version=='osm-anchored-outer-rings-v1':
  need(feature.get('source_format')=='osm-xml' and feature.get('source_class')=='archipelago' and str(feature.get('source_feature_id','')).isdigit() and str(feature.get('relation_version','')).isdigit(),'invalid anchored source');guard();code=read_anchor_code();need(hashlib.sha256(code).hexdigest()==ANCHOR_CODE_SHA256,'anchored extractor code mismatch');module=types.ModuleType('trusted_osm_anchor');module.__file__=str(ANCHOR_CODE);exec(compile(code,str(ANCHOR_CODE),'exec'),module.__dict__);g,trace=module.extract_many(p,source_pin['sha256'],feature['source_feature_id'],feature['relation_version'],feature['expected_relation_tags'],feature['anchors'],feature['geometry_sha256'],guard);need(read_anchor_code()==code and p.stat().st_size==source_pin['size_bytes'],'anchored extractor or source changed');trace.update(extractor_version=version,extractor_sha256=ANCHOR_CODE_SHA256);return g,trace
 need(feature.get('source_format')=='osm-xml' and version in ('osm-multipolygon-outer-v2','osm-multipolygon-outer-v3','osm-multipolygon-outer-v4') and str(feature.get('source_feature_id','')).isdigit() and str(feature.get('relation_version','')).isdigit(),'unsupported OSM extractor')
 codepath,expected={'osm-multipolygon-outer-v2':(OSM_CODE,OSM_CODE_SHA256),'osm-multipolygon-outer-v3':(OSM_CODE_V3,OSM_CODE_V3_SHA256),'osm-multipolygon-outer-v4':(OSM_CODE_V4,OSM_CODE_V4_SHA256)}[version]
 guard()
 with codepath.open('rb') as f:code=f.read((1<<20)+1)
 need(len(code)<=1<<20 and hashlib.sha256(code).hexdigest()==expected,'OSM extractor code mismatch')
 module=types.ModuleType('trusted_osm_outer');exec(compile(code,str(codepath),'exec'),module.__dict__)
 bounds=feature.get('map_export_bounds')
 if bounds is not None:need(version=='osm-multipolygon-outer-v4' and feature.get('source_class')=='archipelago','map export requires v4 archipelago');bounds=validate_map_export_bounds(p,bounds,source_pin['sha256'],guard)
 g,trace=module.extract(p,source_pin['sha256'],feature['source_feature_id'],feature['relation_version'],feature['geometry_sha256'],guard)
 if bounds is not None:validate_geometry_in_bounds(g,bounds);trace['map_export_bounds']={k:str(v) for k,v in bounds.items()}
 if version in ('osm-multipolygon-outer-v3','osm-multipolygon-outer-v4'):
  tags=feature.get('expected_identity_tags');allowed={'name','name:en','place','wikidata'}|({'alt_name'} if version=='osm-multipolygon-outer-v4' else set());need(isinstance(tags,dict) and set(tags)<=allowed and tags.get('place')==('archipelago' if feature.get('source_class')=='archipelago' else 'island') and (feature.get('source_class')!='archipelago' or version=='osm-multipolygon-outer-v4') and any(isinstance(tags.get(k),str) and tags[k] for k in ('name','name:en')) and all(isinstance(v,str) and v and trace.get('tags',{}).get(k)==v for k,v in tags.items()),'OSM relation identity tags mismatch');trace['verified_identity_tags']=tags
 with codepath.open('rb') as f:after=f.read((1<<20)+1)
 need(after==code and p.stat().st_size==source_pin['size_bytes'],'source or extractor changed');trace.update(extractor_version=feature['extractor_version'],extractor_sha256=expected,limitation='Source geometry is runtime-derived; historical V7 source-byte identity must be assessed separately.')
 return g,trace
