#!/usr/bin/env python3
"""Prepare only the three reviewed omissions in a separate sparse candidate directory."""
import argparse,gzip,hashlib,json,pathlib,tarfile,io,os,sys,shutil
import xml.etree.ElementTree as ET
sys.dont_write_bytecode=True
from shapely import from_wkb,to_wkb,union_all,normalize
from shapely.geometry import mapping,shape
HERE=pathlib.Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
read=lambda p:json.loads(pathlib.Path(p).read_bytes())
def packed(p):return from_wkb(gzip.decompress(p.read_bytes()))
def dump(p,obj):p.write_text(json.dumps(obj,separators=(',',':'),ensure_ascii=False))
def prepare(root,output):
 root=pathlib.Path(root).resolve();output=pathlib.Path(output).resolve();p=read(HERE/'proposal.json');manifest=read(HERE/'manifest.json')
 if output.exists() or output.is_relative_to(root) or root.is_relative_to(output):raise ValueError('Output must be fresh and outside source checkout')
 for file,expected in manifest['files'].items():
  if sha((HERE/file).read_bytes())!=expected['sha256']:raise ValueError('Evidence changed: '+file)
 for file,expected in {**p['baseline_inputs'],**p['source_inputs']}.items():
  if sha((root/file).read_bytes())!=expected:raise ValueError('Pinned input changed: '+file)
 if sha(gzip.decompress((HERE/'inaccessible-original-map.osm.gz').read_bytes()))!=p['original_inaccessible_xml_sha256']:raise ValueError('Original island XML changed')
 sys.path.insert(0,str(root/'scripts'));from ellipsoidal_area import area
 units=read(root/'data/hierarchy.json');groups={u['id']:u for u in units};index=read(root/'data/world-index.json');old=[f for part in index['parts'] for f in read(root/'data'/part)['features']]
 if len(old)!=p['baseline_location_count'] or len({f['id'] for f in old})!=len(old):raise ValueError('Unexpected baseline inventory')
 identity_index=read(root/'data/hosted-catalog/index.json');registry=[]
 for batch in identity_index['batches']:
  if batch['kind']!='entities':continue
  raw=(root/'data/hosted-catalog'/batch['path']).read_bytes()
  if sha(raw)!=batch['sha256']:raise ValueError('Archived identity batch changed')
  document=json.loads(raw);registry.extend(document if isinstance(document,list) else document['entities'])
 known={f['id'] for f in old}|{r['id'] for r in registry};archive=read(HERE/'identity-review.json')
 for expected in archive['entities']:
  if expected not in registry:raise ValueError('Original identity history no longer retained')
 with tarfile.open(HERE/'assembled-water-and-parent-geometries.tar.gz') as tf:
  geometries={m.name:from_wkb(gzip.decompress(tf.extractfile(m).read())) for m in tf if m.isfile()}
 water_rows=json.loads(gzip.decompress((HERE/'water-source-features.json.gz').read_bytes()))
 for w in water_rows:
  if w['id']==2184073:continue
  g=geometries[f'osm-{w["source_type"]}-{w["id"]}.wkb.gz']
  if not g.is_valid or sha(to_wkb(g))!=w['wkb_sha256']:raise ValueError('Assembled mapped-water/admin source changed')
 added=[];proofs=[];measurements=[]
 for row in p['locations']:
  if row['id'] in known:raise ValueError('New ID conflicts with current or archived identity')
  coast=packed(root/row['coast_path']);dry=packed(HERE/(row['slug']+'-dry-land.wkb.gz'));water=packed(HERE/(row['slug']+'-water-mask.wkb.gz'))
  for g,expected in [(coast,row['coast_wkb_sha256']),(dry,row['dry_wkb_sha256']),(water,row['water_wkb_sha256'])]:
   if not g.is_valid or sha(to_wkb(g))!=expected:raise ValueError('Exact coast/water/land geometry changed')
  if area(dry.intersection(water))>.001 or area(coast.symmetric_difference(dry.union(water)))>.001:raise ValueError('Inland-water conservation failed')
  if row['parent_osm_relation']:
   parent=geometries[f'osm-relation-{row["parent_osm_relation"]}.wkb.gz']
   if area(coast.difference(parent))>.001:raise ValueError('Whole island outside independently sourced municipality')
   candidates=[w for w in water_rows if w['tags'].get('boundary')=='administrative' and w['tags'].get('admin_level')=='4' and area(coast.intersection(geometries[f'osm-{w["source_type"]}-{w["id"]}.wkb.gz']))>0]
   if len(candidates)!=1 or candidates[0]['id']!=row['parent_osm_relation']:raise ValueError('Competing municipal parent')
   mapped=union_all([geometries[f'osm-{w["source_type"]}-{w["id"]}.wkb.gz'] for w in water_rows if row['slug'] in w.get('target_intersections_km2',{}) and w['tags'].get('boundary')!='administrative']).intersection(coast)
   if normalize(mapped).wkb!=normalize(water).wkb:raise ValueError('Water mask differs from complete selected mapped water')
  else:
   xml=ET.fromstring(gzip.decompress((HERE/'inaccessible-original-map.osm.gz').read_bytes()));nodes={n.attrib['id']:[float(n.attrib['lon']),float(n.attrib['lat'])] for n in xml.findall('node')};polygons=[]
   for way in xml.findall('way'):
    tags={t.attrib['k']:t.attrib['v'] for t in way.findall('tag')}
    if not (tags.get('natural')=='water' or tags.get('waterway')=='riverbank' or tags.get('landuse')=='reservoir') or tags.get('water')=='sea':continue
    refs=[n.attrib['ref'] for n in way.findall('nd')]
    if len(refs)<4 or refs[0]!=refs[-1]:raise ValueError('Source pond ring not explicitly closed')
    polygons.append(shape({'type':'Polygon','coordinates':[[nodes[r] for r in refs]]}))
   if len(polygons)!=row['water_count'] or any({t.attrib['k']:t.attrib['v'] for t in r.findall('tag')}.get('natural')=='water' for r in xml.findall('relation')):raise ValueError('Unreviewed pond multipolygon')
   if not union_all(polygons).intersection(coast).symmetric_difference(water).is_empty:raise ValueError('Pond water differs from original XML')
  parent=row['parent_chain'][0]
  for tier,identifier in zip(['province','area','region','subcontinent','continent'],row['parent_chain']):
   u=groups.get(parent)
   if not u or parent!=identifier or u['level']!=tier:raise ValueError('Incomplete reviewed adjacent-tier chain')
   parent=u['parent_id']
  if parent is not None or len(row['parent_chain'])!=5:raise ValueError('Incomplete terminal continent')
  same=sorted(f['id'] for f in old if f['properties']['name'].casefold()==row['name'].casefold())
  if same!=row['same_name_existing_ids']:raise ValueError('Existing name ambiguity changed')
  feature={'type':'Feature','id':row['id'],'properties':{'id':row['id'],'name':row['name'],'parent_id':row['parent_chain'][0],'reference_owner':None,'metadata':{'source_id':'osm-geonames:'+str(row['geonames_id']),'source_identity':str(row['geonames_id']),'source_name':'OpenStreetMap contributors / GeoNames','source_url':'https://www.openstreetmap.org/','license':'ODbL-1.0','reference_year':'2026','location_basis':row['new_local_role'],'semantic_review':{'status':'open','issue':503,'regional_interior_approval':False},'search_aliases':list(filter(None,row['geonames_original_row'][3].split(','))),'geometry_source_sha256':row['dry_wkb_sha256'],'supported_from':2026,'supported_to':2027,'historical_claims_transferred':False,'history_transfer':False,'source_raw_sha256':p['source_inputs']['data/macro-improvements/macro-coverage-africa-americas/osm/greenland-latest.osm.pbf'] if row['parent_osm_relation'] else p['original_inaccessible_xml_sha256'],'attribution':'OpenStreetMap contributors / GeoNames','representative_point':list(dry.representative_point().coords)[0]}},'geometry':mapping(dry)}
  # The shared stage validator compares exact source geometry and audits all old/new overlaps.
  source_feature={'type':'Feature','id':str(row['geonames_id']),'properties':{'geometry_method':'OSM source coast minus current mapped inland-water union; no invented closure or polygon inflation'},'geometry':mapping(dry)}
  added.append(feature);proofs.append({'location_id':row['id'],'parent_chain':row['parent_chain'],'source':{'path':'sources/'+row['slug']+'.geojson','url':'https://download.geofabrik.de/north-america/greenland.html' if row['parent_osm_relation'] else 'https://api.openstreetmap.org/api/0.6/map?bbox=-12.712,-37.33,-12.637,-37.276','identity':str(row['geonames_id']),'license':'ODbL-1.0','attribution':'OpenStreetMap contributors / Geofabrik; island identity GeoNames CC-BY-4.0','supported_from':2026,'supported_to':2027},'identity_review':{'status':'distinct-new-territory','evidence_url':'https://www.geonames.org/'+str(row['geonames_id'])+'/','rationale':row['new_local_role']+'; exact footprint absent from all published location polygons; preserved archived municipal entities are not reactivated. SHN-4865 source identity does not explicitly guarantee the entire archipelago, so Inaccessible is a distinct island. No historical claims transfer.','same_name_existing_ids':same}})
  proofs[-1]['source']['original_archive']={'path':'data/macro-improvements/macro-coverage-africa-americas/osm/greenland-latest.osm.pbf' if row['parent_osm_relation'] else 'data/macro-improvements/three-island-restoration/inaccessible-original-map.osm.gz','raw_sha256':p['source_inputs']['data/macro-improvements/macro-coverage-africa-americas/osm/greenland-latest.osm.pbf'] if row['parent_osm_relation'] else p['original_inaccessible_xml_sha256'],'gzip_wrapped':not bool(row['parent_osm_relation'])}
  measurements.append({'id':row['id'],'dry_land_area_m2':area(dry),'water_area_m2':area(water),'coast_area_m2':area(coast),'municipal_parent_relation':row['parent_osm_relation'],'whole_coast_parent_share':1 if row['parent_osm_relation'] else None})
 output.mkdir(parents=True);(output/'sources').mkdir();(output/'after/geography').mkdir(parents=True)
 for row,proof,feature in zip(p['locations'],proofs,added):
  target=output/proof['source']['path'];dump(target,{'type':'Feature','id':str(row['geonames_id']),'properties':{'geometry_method':'Current OSM whole coast minus mapped inland-water polygons'},'geometry':feature['geometry']});proof['source']['sha256']=sha(target.read_bytes())
 for part in index['parts']:
  destination=output/'after'/part;destination.parent.mkdir(parents=True,exist_ok=True);os.symlink(root/'data'/part,destination)
 dump(output/'after/geography/three-islands.json',{'type':'FeatureCollection','features':added});dump(output/'after/world-index.json',{**index,'parts':index['parts']+['geography/three-islands.json']});(output/'after/hierarchy.json').write_bytes((root/'data/hierarchy.json').read_bytes())
 dump(output/'creation-proofs.json',proofs);dump(output/'candidate-patch.json',{'version':1,'issue':503,'input_geography_version':3,'input_hierarchy_sha256':p['baseline_inputs']['data/hierarchy.json'],'input_part_sha256':{k:v for k,v in p['baseline_inputs'].items() if k.startswith('data/geography/')},'added_parent_chain':{r['id']:r['parent_chain'] for r in p['locations']},'existing_location_updates':[],'existing_group_updates':[],'added_groups':[],'publication_ready':False,'holds':[],'added_features':added,'changed_features':[],'removed_ids':[],'added_units':[],'history_transfer':False,'parent_chain_proofs':proofs});dump(output/'geometry-measurements.json',measurements)
 # Immutable full prior features are archived as proof, although pure additions mutate none.
 (output/'related-full-old-features.json.gz').write_bytes((HERE/'related-full-old-features.json.gz').read_bytes());dump(output/'preservation.json',{'old_location_count':len(old),'candidate_location_count':len(old)+len(added),'all_baseline_geography_bytes_preserved':True,'all_archived_entities_exhaustively_checked':len(registry),'no_existing_groups_renamed_or_reparented':True,'historical_attributes_added_or_transferred':False,'new_attributes':'explicit unknown; present-day provenance does not assign owner, population, habitation, culture, religion, rank or environment'})
 return {'output':str(output),'added_ids':[f['id'] for f in added],'old_count':len(old),'new_count':len(old)+len(added)}
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--root',required=True);a.add_argument('--output',required=True);args=a.parse_args();print(json.dumps(prepare(args.root,args.output)))
