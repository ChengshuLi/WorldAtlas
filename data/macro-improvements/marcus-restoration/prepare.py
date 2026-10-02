#!/usr/bin/env python3
"""One exact, water-masked omitted island; immutable baseline and archive scans."""
import argparse,gzip,hashlib,json,pathlib,shutil,sys,xml.etree.ElementTree as ET
from shapely import from_wkb,union_all
from shapely.geometry import Polygon,mapping,shape
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def read(p):return json.loads(gzip.decompress(p.read_bytes()) if str(p).endswith('.gz') else p.read_bytes())
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,separators=(',',':'),ensure_ascii=False))
def reconstruct(p):
 raw=gzip.decompress((HERE/p['source_geometry']['original_xml']).read_bytes())
 if sha(raw)!=p['source_geometry']['original_xml_sha256']:raise ValueError('Original OSM XML changed')
 xml=ET.fromstring(raw);nodes={n.attrib['id']:(float(n.attrib['lon']),float(n.attrib['lat'])) for n in xml.findall('node')};coasts=[];waters=[];versions=[]
 for w in xml.findall('way'):
  tags={t.attrib['k']:t.attrib['v'] for t in w.findall('tag')};refs=[n.attrib['ref'] for n in w.findall('nd')]
  coastal=tags.get('natural')=='coastline';water=(tags.get('natural')=='water' or tags.get('waterway')=='riverbank' or tags.get('landuse')=='reservoir') and tags.get('water')!='sea'
  if not coastal and not water:continue
  if len(refs)<4 or refs[0]!=refs[-1] or any(n not in nodes for n in refs):raise ValueError('Source land/water ring is incomplete')
  g=Polygon([nodes[n] for n in refs])
  if not g.is_valid:raise ValueError('Source ring is invalid')
  if coastal:coasts.append(g);versions.append({k:w.attrib[k] for k in ['id','version','timestamp']})
  else:waters.append(g)
 if any({t.attrib['k']:t.attrib['v'] for t in r.findall('tag')}.get('natural')=='water' for r in xml.findall('relation')):raise ValueError('Unreviewed inland-water relation')
 if len(coasts)!=1 or versions!=p['source_geometry']['way_versions'] or len(waters)!=p['source_geometry']['subtracted_closed_water_rings']:raise ValueError('Source land/water inventory changed')
 coast=union_all(coasts);water=union_all(waters).intersection(coast);rawdry=gzip.decompress((HERE/'dry-land.wkb.gz').read_bytes())
 if sha(rawdry)!=p['source_geometry']['wkb_sha256']:raise ValueError('Original dry-land WKB changed')
 dry=from_wkb(rawdry)
 if not dry.is_valid or not coast.difference(water).equals(dry):raise ValueError('Source coastline/water reconstruction differs from retained exact land')
 return dry,coast,water

def prepare(root,output):
 root=pathlib.Path(root).resolve();output=pathlib.Path(output).resolve();p=read(HERE/'proposal.json');manifest=read(HERE/'manifest.json')
 if output.exists() or output.is_relative_to(root) or root.is_relative_to(output):raise ValueError('Output must be fresh and separate')
 for f,pin in manifest['files'].items():
  if sha((HERE/f).read_bytes())!=pin['sha256']:raise ValueError('Evidence bytes changed: '+f)
 for f,pin in p['baseline_inputs'].items():
  if sha((root/f).read_bytes())!=pin:raise ValueError('Pinned predecessor changed: '+f)
 sys.path.insert(0,str(root/'scripts'));from ellipsoidal_area import area;from majority import canonical
 research=read(HERE/'routing-research.json')
 for source in research['sources']:
  if source.get('retained_path'):
   raw=gzip.decompress((HERE/source['retained_path']).read_bytes())
   if sha(raw)!=source['original_sha256'] or len(raw)!=source['original_bytes']:raise ValueError('Original geographic evidence changed: '+source['id'])
 dry,coast,water=reconstruct(p);index=read(root/'data/world-index.json');old=[f for part in index['parts'] for f in read(root/'data'/part)['features']];units=read(root/'data/hierarchy.json');groups={u['id']:u for u in units}
 known=set(groups)|{f['id'] for f in old};registry=[];registry_pins={}
 for folder,entry in [('hosted-catalog',read(root/'data/hosted-catalog/index.json')),('geographic-releases',read(root/'data/geographic-releases/index.json'))]:
  for batch in entry['batches']:
   if folder=='hosted-catalog' and batch.get('kind')!='entities':continue
   file=root/'data'/folder/batch['path'];raw=file.read_bytes()
   if sha(raw)!=batch['sha256']:raise ValueError('Retained registry bytes changed')
   d=json.loads(raw);entities=d.get('entities',[]) if isinstance(d,dict) else d
   registry.extend(entities);known.update(e['id'] for e in entities);registry_pins[str(file.relative_to(root))]=sha(raw)
 if any(i in known for i in [p['location_id'],*p['parent_chain'][:2]]):raise ValueError('Candidate reuses an existing or archived identity')
 hits=[];counts={};name_matches=[];aliases={n.lower() for n in p['aliases']}|{p['name'].lower()}
 def scan(rows,label):
  count=0
  for f in rows:
   count+=1;g=canonical(shape(f['geometry']))
   if g.bounds[2]>=dry.bounds[0] and g.bounds[0]<=dry.bounds[2] and g.bounds[3]>=dry.bounds[1] and g.bounds[1]<=dry.bounds[3] and area(g.intersection(dry))>.001:hits.append({'inventory':label,'id':f['id']})
  counts[label]=count
 scan(old,'current')
 for f in ['data/geographic-migration-archive.json.gz','data/geographic-repair-evidence/archive.json.gz']:
  d=read(root/f);scan([r.get('feature',r) for r in d['locations']],f)
 if hits:raise ValueError('Current or archived land already represents candidate: '+str(hits))
 for e in registry:
  names=[e.get('name',''),*e.get('metadata',{}).get('aliases',[])];names=[n for n in names if isinstance(n,str)]
  if any(n.lower() in aliases for n in names):name_matches.append(e)
 if name_matches:raise ValueError('Retained name/alias matches require explicit identity adjudication')
 for level,ident in zip(['region','subcontinent','continent'],p['parent_chain'][2:]):
  if groups.get(ident,{}).get('level')!=level:raise ValueError('Existing macro tier missing')
 if [groups[p['parent_chain'][i]]['parent_id'] for i in [2,3]]!=p['parent_chain'][3:]:raise ValueError('Macro association differs from sourced decision')
 feature={'type':'Feature','id':p['location_id'],'properties':{'id':p['location_id'],'name':p['name'],'parent_id':p['parent_chain'][0],'reference_owner':None,'metadata':{'aliases':p['aliases'],'source_id':'osm-api-2026-10-02','source_identity':'osm:named-land:minamitorishima','source_url':p['source_geometry']['url'],'source_raw_sha256':p['source_geometry']['original_xml_sha256'],'source_way_versions':p['source_geometry']['way_versions'],'license':'ODbL 1.0','attribution':'© OpenStreetMap contributors','reference_year':2026,'supported_from':2026,'supported_to':2027,'semantic_review':{'status':'open','scope':'regional interior; isolated-island lower-tier exception'},'historical_claims_transferred':False}},'geometry':mapping(dry)}
 units.extend(p['new_groups']);children={}
 for r in [*[f['properties'] for f in old],feature['properties'],*units]:
  if r.get('parent_id'):children[r['parent_id']]=children.get(r['parent_id'],0)+1
 touched={g['id'] for g in p['new_groups']}|{g['parent_id'] for g in p['new_groups']}
 for u in units:
  if u['id'] in touched:u['metadata']={**u.get('metadata',{}),'child_count':children[u['id']]}
 try:
  output.mkdir(parents=True);after=output/'after';after.mkdir()
  for part in index['parts']:
   dest=after/part;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/'data'/part,dest)
  part='geography/marcus-restoration.json';save(after/part,{'type':'FeatureCollection','features':[feature]});save(after/'world-index.json',{**index,'parts':[*index['parts'],part]});save(after/'hierarchy.json',units)
  source={**feature,'id':'osm:named-land:minamitorishima'};save(output/'proof-input/source.geojson',source)
  proof={'location_id':feature['id'],'parent_chain':p['parent_chain'],'source':{'path':'source.geojson','sha256':sha((output/'proof-input/source.geojson').read_bytes()),'identity':source['id'],'url':p['source_geometry']['url'],'license':'ODbL 1.0','attribution':p['source_geometry']['attribution'],'supported_from':2026,'supported_to':2027,'original_archive':{'path':'data/macro-improvements/marcus-restoration/original-map.osm.xml.gz','raw_sha256':p['source_geometry']['original_xml_sha256']}},'identity_review':{'status':'distinct-new-territory','evidence_url':'https://www.jma-net.go.jp/minamitorishima/','rationale':'Named isolated coral island; exhaustive current and archived land scans find no physical predecessor or retained exact name/alias. Political sovereignty does not determine macro parent. Private preflight remains required.','same_name_existing_ids':[]}}
  save(output/'proof-input/proofs.json',[proof]);save(output/'candidate-patch.json',{'added_features':[feature],'new_groups':p['new_groups'],'macro_amendment':p['macro_amendment'],'history_transfer':False})
  save(output/'geometry-measurements.json',[{'id':feature['id'],'dry_land_area_m2':area(dry),'coast_area_m2':area(coast),'mapped_water_area_m2':area(water),'source_water_rings':len(list(dry.interiors)) if dry.geom_type=='Polygon' else sum(len(g.interiors) for g in dry.geoms)}])
  save(output/'identity-review.json',{'counts':counts,'physical_predecessors':hits,'retained_name_alias_matches':name_matches,'known_registry_ids':len(known),'registry_byte_pins':registry_pins,'private_live_registry_checked':False,'historical_claims_transferred':False})
  return {'output':str(output),'old_locations':len(old),'added_locations':1,'new_groups':2,'regional_interior_approved':False,'live_apply':False}
 except Exception:shutil.rmtree(output,ignore_errors=True);raise
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--root',required=True);a.add_argument('--output',required=True);v=a.parse_args();print(json.dumps(prepare(v.root,v.output)))
