"""Reconstruct one named closed OSM coastline way from a pinned map export.

The source must be independently authenticated as a provider-original export.
Geometry is derived at runtime; this helper never selects a grid component.
"""
import hashlib,json,math,xml.parsers.expat as expat
from decimal import Decimal,InvalidOperation
from pathlib import Path

def need(v,m):
 if not v:raise ValueError(m)

def extract(path,expected_sha,way_id,way_version,expected_tags,expected_bounds,expected_geometry_sha):
 need(isinstance(expected_sha,str) and len(expected_sha)==64 and all(c in '0123456789abcdef' for c in expected_sha) and isinstance(expected_geometry_sha,str) and len(expected_geometry_sha)==64 and all(c in '0123456789abcdef' for c in expected_geometry_sha),'invalid digest')
 need(isinstance(way_id,str) and way_id.isdigit() and int(way_id)>0 and isinstance(way_version,str) and way_version.isdigit() and int(way_version)>0,'invalid way identity')
 need(isinstance(expected_tags,dict) and set(expected_tags)<={'name','name:en','place','natural','wikidata'} and expected_tags.get('natural')=='coastline' and expected_tags.get('place') in ('island','islet') and any(isinstance(expected_tags.get(k),str) and expected_tags[k] for k in ('name','name:en')) and all(isinstance(v,str) and v for v in expected_tags.values()),'invalid expected identity tags')
 keys={'minlon','minlat','maxlon','maxlat'};need(isinstance(expected_bounds,dict) and set(expected_bounds)==keys and all(isinstance(v,str) and 0<len(v)<=24 for v in expected_bounds.values()),'invalid bounds')
 try:bounds={k:Decimal(v) for k,v in expected_bounds.items()}
 except InvalidOperation:raise ValueError('invalid bounds') from None
 need(all(v.is_finite() for v in bounds.values()) and -180<=bounds['minlon']<bounds['maxlon']<=180 and -90<=bounds['minlat']<bounds['maxlat']<=90 and bounds['maxlon']-bounds['minlon']<=1 and bounds['maxlat']-bounds['minlat']<=1 and (bounds['maxlon']-bounds['minlon'])*(bounds['maxlat']-bounds['minlat'])<=Decimal('0.25'),'invalid bounds')
 stack=[];nodes={};target=None;current=None;found=[];parser=expat.ParserCreate();digest=hashlib.sha256()
 def reject(*args):raise ValueError('DTD and entity declarations forbidden')
 parser.StartDoctypeDeclHandler=reject;parser.EntityDeclHandler=reject;parser.UnparsedEntityDeclHandler=reject;parser.NotationDeclHandler=reject;parser.ExternalEntityRefHandler=reject;parser.SkippedEntityHandler=reject;parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
 def start(name,attrs):
  nonlocal current,target
  stack.append(name);depth=len(stack)
  if depth==1:need(name=='osm','expected OSM document')
  elif depth==2 and name=='bounds':
   need(not found and set(attrs)==keys,'invalid map bounds')
   try:actual={k:Decimal(v) for k,v in attrs.items()}
   except InvalidOperation:raise ValueError('invalid map bounds') from None
   need(actual==bounds,'map bounds mismatch');found.append(True)
  elif depth==2 and name in ('node','way','relation'):
   need(attrs.get('visible')=='true','non-visible map object')
   if name=='node':
    i=attrs.get('id');need(isinstance(i,str) and i.isdigit() and int(i)>0 and i not in nodes and len(nodes)<1000000,'invalid or duplicate node')
    try:lon=float(attrs['lon']);lat=float(attrs['lat'])
    except (KeyError,ValueError,OverflowError):raise ValueError('invalid node coordinate') from None
    need(math.isfinite(lon) and math.isfinite(lat) and -180<=lon<=180 and -90<=lat<=90,'invalid node coordinate');nodes[i]=(lon,lat)
   elif name=='way' and attrs.get('id')==way_id:
    need(target is None and current is None and attrs.get('version')==way_version,'duplicate way or version mismatch');current={'refs':[],'tags':{}}
  elif depth==3 and stack[-2]=='way' and current is not None:
   if name=='nd':
    ref=attrs.get('ref');need(isinstance(ref,str) and ref.isdigit() and int(ref)>0 and len(current['refs'])<1000000,'invalid way node');current['refs'].append(ref)
   elif name=='tag':
    k=attrs.get('k');v=attrs.get('v');need(isinstance(k,str) and isinstance(v,str) and k not in current['tags'],'invalid or duplicate way tag');current['tags'][k]=v
 def end(name):
  nonlocal current,target
  need(stack and stack[-1]==name,'invalid XML nesting')
  if len(stack)==2 and name=='way' and current is not None:target=current;current=None
  stack.pop()
 parser.StartElementHandler=start;parser.EndElementHandler=end
 p=Path(path)
 with p.open('rb') as f:
  while True:
   block=f.read(1<<16)
   if not block:break
   digest.update(block);parser.Parse(block,False)
  parser.Parse(b'',True)
 need(digest.hexdigest()==expected_sha,'source hash mismatch');need(len(found)==1 and isinstance(target,dict),'missing bounds or target way');refs=target['refs'];need(len(refs)>=4 and refs[0]==refs[-1] and all(a!=b for a,b in zip(refs,refs[1:])) and all(i in nodes for i in refs),'open, degenerate or incomplete way');need(all(target['tags'].get(k)==v for k,v in expected_tags.items()),'way identity mismatch')
 coords=[list(nodes[i]) for i in refs];need(all(bounds['minlon']<=Decimal(str(lon))<=bounds['maxlon'] and bounds['minlat']<=Decimal(str(lat))<=bounds['maxlat'] for lon,lat in coords),'way extends outside export bounds');need(all(abs(a[0]-b[0])<=180 for a,b in zip(coords,coords[1:])),'unsupported antimeridian crossing');geometry={'type':'MultiPolygon','coordinates':[[coords]]};encoded=json.dumps(geometry,sort_keys=True,separators=(',',':'),allow_nan=False).encode();gh=hashlib.sha256(encoded).hexdigest();need(gh==expected_geometry_sha,'geometry hash mismatch')
 from osgeo import ogr
 g=ogr.CreateGeometryFromJson(encoded.decode());need(g is not None and not g.IsEmpty() and g.IsValid(),'invalid way polygon')
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1<<20),b''):h.update(block)
 need(h.hexdigest()==expected_sha,'source changed')
 return geometry,{'source_sha256':expected_sha,'way_id':way_id,'way_version':way_version,'geometry_sha256':gh,'verified_identity_tags':expected_tags,'limitation':'OSM map-export custody requires independent authentication; historical source-byte equivalence is not established.'}
