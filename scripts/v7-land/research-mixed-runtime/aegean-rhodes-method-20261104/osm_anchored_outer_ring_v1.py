#!/usr/bin/env python3
"""Select one topology-connected outer ring by a verified tagged OSM node.

The raw OSM relation, anchor ID/version/tags, member way ID, and resulting
geometry hash must all be selected and pinned by the caller. This returns an
ephemeral polygon, never a replacement raw source or a physical-root selector.
"""
import hashlib,json,re,types,xml.parsers.expat as expat
from pathlib import Path

GRAPH=Path(__file__).resolve().parent.parent/'osm-relation-adapter-20261104/osm_outer_relation_v3.py'
GRAPH_SHA256='1ec2c1b224528698a0e2e5bf6bd6fecd657e659da30de8188e3a7b12497f3d6c'

def need(c,m):
 if not c:raise ValueError(m)
def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  while True:
   b=f.read(1<<20)
   if not b:break
   h.update(b)
 return h.hexdigest()
def read_code():
 with GRAPH.open('rb') as f:code=f.read((1<<20)+1)
 need(len(code)<=1<<20,'graph extractor too large');return code
def read_anchor(path,source_sha256,node_id,node_version,expected_tags):
 parser=expat.ParserCreate();stack=[];anchor=None;current=None;h=hashlib.sha256()
 def reject(*_):raise ValueError('DTD and entity declarations forbidden')
 parser.StartDoctypeDeclHandler=reject;parser.EntityDeclHandler=reject;parser.UnparsedEntityDeclHandler=reject;parser.NotationDeclHandler=reject;parser.ExternalEntityRefHandler=reject;parser.SkippedEntityHandler=reject;parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
 def start(name,attrs):
  nonlocal anchor,current
  stack.append(name)
  if len(stack)==1:need(name=='osm','not OSM XML')
  elif len(stack)==2 and name=='node' and attrs.get('id')==str(node_id):
   need(anchor is None and current is None,'duplicate anchor node');need(attrs.get('version')==str(node_version) and attrs.get('visible')=='true','anchor version or visibility');current={}
  elif len(stack)==3 and stack[-2]=='node' and current is not None and name=='tag':
   k=attrs.get('k');need(isinstance(k,str) and k and k not in current,'duplicate anchor tag');current[k]=attrs.get('v')
 def end(name):
  nonlocal current,anchor
  need(stack and stack[-1]==name,'invalid XML nesting')
  if len(stack)==2 and name=='node' and current is not None:anchor=current;current=None
  stack.pop()
 parser.StartElementHandler=start;parser.EndElementHandler=end
 with Path(path).open('rb') as f:
  while True:
   b=f.read(1<<20)
   if not b:break
   h.update(b);parser.Parse(b,False)
  parser.Parse(b'',True)
 need(h.hexdigest()==source_sha256,'anchor source hash mismatch');need(anchor is not None,'anchor missing');need(all(anchor.get(k)==v for k,v in expected_tags.items()),'anchor tags mismatch');return anchor

def extract(path,source_sha256,relation_id,relation_version,anchor_node_id,anchor_node_version,anchor_way_id,expected_relation_tags,expected_anchor_tags,expected_geometry_sha256):
 from osgeo import ogr
 p=Path(path).resolve(strict=True);need(p.is_file() and 0<p.stat().st_size<=64<<20,'source size');need(isinstance(source_sha256,str) and re.fullmatch(r'[a-f0-9]{64}',source_sha256) and isinstance(expected_geometry_sha256,str) and re.fullmatch(r'[a-f0-9]{64}',expected_geometry_sha256),'missing or invalid hash');need(all(str(v).isdigit() and int(v)>0 for v in (relation_id,relation_version,anchor_node_id,anchor_node_version,anchor_way_id)),'invalid selected ID/version');need(isinstance(expected_relation_tags,dict) and set(expected_relation_tags)<={'name','name:en','place','wikidata'} and expected_relation_tags.get('place')=='archipelago' and any(expected_relation_tags.get(k) for k in ('name','name:en')) and all(isinstance(v,str) and v for v in expected_relation_tags.values()) and isinstance(expected_anchor_tags,dict) and set(expected_anchor_tags)<={'name','name:en','amenity'} and expected_anchor_tags.get('amenity')=='ferry_terminal' and any(expected_anchor_tags.get(k) for k in ('name','name:en')) and all(isinstance(v,str) and v for v in expected_anchor_tags.values()),'identity tags incomplete');need(digest(p)==source_sha256,'source hash mismatch')
 code=read_code();need(hashlib.sha256(code).hexdigest()==GRAPH_SHA256,'graph extractor pin');m=types.ModuleType('pinned_outer_graph');exec(compile(code,str(GRAPH),'exec'),m.__dict__)
 nodes,ways,tags=m.read_graph(p,int(relation_id),int(relation_version),source_sha256);need(all(tags.get(k)==v for k,v in expected_relation_tags.items()),'relation identity mismatch');node=int(anchor_node_id);way=int(anchor_way_id);need(node in nodes and way in ways,'anchor member missing');need([wid for wid,refs in ways.items() if node in refs]==[way],'anchor must occur in exactly selected outer way');need(ways[way].count(node)==1,'anchor repeated in selected way');anchor=read_anchor(p,source_sha256,node,anchor_node_version,expected_anchor_tags);rings=m.assemble_rings(ways);matches=[ring for ring in rings if node in ring];need(len(matches)==1 and matches[0].count(node)==1,'anchor ring ambiguous');ring=matches[0];geometry={'type':'Polygon','coordinates':[[list(nodes[n]) for n in ring]]};need(all(abs(a[0]-b[0])<=180 for a,b in zip(geometry['coordinates'][0],geometry['coordinates'][0][1:])),'antimeridian unsupported');canonical=json.dumps(geometry,sort_keys=True,separators=(',',':'),allow_nan=False).encode();gh=hashlib.sha256(canonical).hexdigest();need(gh==expected_geometry_sha256,'geometry hash mismatch');g=ogr.CreateGeometryFromJson(canonical.decode());need(g is not None and not g.IsEmpty() and g.IsValid(),'invalid selected ring');need(digest(p)==source_sha256 and read_code()==code,'source or graph code changed')
 return geometry,{'source_sha256':source_sha256,'relation_id':str(relation_id),'relation_version':str(relation_version),'relation_tags':expected_relation_tags,'anchor_node_id':str(node),'anchor_node_version':str(anchor_node_version),'anchor_way_id':str(way),'anchor_tags':{k:anchor[k] for k in expected_anchor_tags},'geometry_sha256':gh,'ring_vertices':len(ring),'unselected_other_rings':len(rings)-1,'graph_extractor_sha256':GRAPH_SHA256,'limitations':['The tagged node anchors exactly one outer coastline ring; it is not an independently authenticated full island roster.','Other relation rings are not selected.','Source custody is verified against the pinned OSM capture.']}


def extract_many(path,source_sha256,relation_id,relation_version,expected_relation_tags,anchors,expected_geometry_sha256):
 """Select an explicit finite set of separately source-anchored rings."""
 from osgeo import ogr
 need(isinstance(anchors,list) and 1<=len(anchors)<=32,'invalid anchor set')
 need(isinstance(expected_geometry_sha256,str) and re.fullmatch(r'[a-f0-9]{64}',expected_geometry_sha256),'invalid aggregate geometry hash')
 needed={'node_id','node_version','way_id','expected_tags','geometry_sha256'}
 need(all(isinstance(a,dict) and set(a)==needed for a in anchors),'invalid anchor fields')
 ids=[str(a['node_id']) for a in anchors];need(all(x.isdigit() and int(x)>0 for x in ids) and len(set(ids))==len(ids),'duplicate or invalid anchors')
 geometries=[];traces=[]
 for a in sorted(anchors,key=lambda a:int(a['node_id'])):
  g,t=extract(path,source_sha256,relation_id,relation_version,a['node_id'],a['node_version'],a['way_id'],expected_relation_tags,a['expected_tags'],a['geometry_sha256']);geometries.append(g['coordinates']);traces.append(t)
 hashes=[t['geometry_sha256'] for t in traces];need(len(set(hashes))==len(hashes),'anchors select duplicate rings')
 geometry={'type':'MultiPolygon','coordinates':geometries};canonical=json.dumps(geometry,sort_keys=True,separators=(',',':'),allow_nan=False).encode();gh=hashlib.sha256(canonical).hexdigest();need(gh==expected_geometry_sha256,'aggregate geometry hash mismatch');g=ogr.CreateGeometryFromJson(canonical.decode());need(g is not None and not g.IsEmpty() and g.IsValid(),'invalid aggregate geometry')
 return geometry,{'source_sha256':source_sha256,'relation_id':str(relation_id),'relation_version':str(relation_version),'geometry_sha256':gh,'selected_anchor_traces':traces,'limitations':['Only selected tagged-source anchor rings are included; the broader archipelago is not assigned wholesale.','Source custody is verified against the pinned OSM capture.']}
