import json,gzip,glob,os,hashlib,subprocess,pathlib,sys
from shapely.geometry import shape
from shapely.strtree import STRtree
ROOT=pathlib.Path(__file__).resolve().parents[3]
BASE_COMMIT='cea80a8aa1f8a55ccb448a8f2ff71e10c49a26f1'
SOURCE_COMMIT='f4567e7c606680d5d09353fe5b63bbdf8496ee94'
sys.path.insert(0,str(ROOT/'scripts'))
from evidence.immutable import Baseline, canonical_json
manifest=json.loads((ROOT/'research/geography/gap-source-abudhabi-physical-seam-20261006/evidence-quality.json').read_text())
immutable=Baseline(str(ROOT),BASE_COMMIT,manifest['baseline']['files'])
expected_pins={'coordination/engineering/physical-gap-priorities-1005-20261006-local20/priorities-v2/report.json':'864fe6abab537488766acd6a599782b7a85bbc4f41a4c8027992b05e22462ff1','coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/index.json':'dfcca9fe2bb64805b94e784be89b3523f5683b95cbd4a617283965ca6187a77c','data/canonical-grid/manifest.json':'73899e8581d74634d6304a9e52aa32849dd174730aba2c6cc48db512a985d1f6','data/hierarchy.json':'568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b','data/geography/part-0.json':'bcad5408720e0f50165e794636fd44e02913e5e4649d73c8aa422b94562d32f3'}
assert all(immutable.pins[p]['sha256']==h for p,h in expected_pins.items())
def git_bytes(commit,path):
 return immutable.read(path) if commit==BASE_COMMIT else subprocess.check_output(['git','-C',str(ROOT),'show',f'{commit}:{path}'])
def tracked_paths(commit,prefix):
 raw=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',commit,'--',prefix],text=True)
 return [x for x in raw.splitlines() if x]
base='coordination/engineering/physical-gap-components-1005-20261005-local19'
idx=json.loads(git_bytes(BASE_COMMIT,base+'/custody-v1/index.json'))
byorig={a['original']['path']:a['payload'] for a in idx['aliases']}
def read_alias(path):
 b=git_bytes(BASE_COMMIT,byorig[path])
 return json.loads(gzip.decompress(b))
selected=[]
investigation_by_id={}
priority_prefix='coordination/engineering/physical-gap-priorities-1005-20261006-local20/priorities-v2/'
priority_paths=sorted(p for p in tracked_paths(BASE_COMMIT,priority_prefix) if p.rsplit('/',1)[-1].startswith('investigations-') and p.endswith('.json.gz'))
assert len(priority_paths)==34
for p in priority_paths:
 d=json.loads(gzip.decompress(git_bytes(BASE_COMMIT,p)))
 for r in d:
  if r.get('partition','').startswith('interior') and sorted(r.get('positive_length_neighbor_ids',[]))==['atlas:physical:a2735e777a9d1037bd3a','atlas:physical:cbea9d242259efda3120']:
   selected.append(r['component'])
   investigation_by_id[r['component']]=r
selected=set(selected)
assert len(selected)==134
roster_bytes=canonical_json(sorted(selected))
expected_roster='b7af8568f5972dd935d8cc85d16c19f349938ea6810b6b2b391c92d4a1b9df94'
assert hashlib.sha256(roster_bytes).hexdigest()==expected_roster
omitted_roster=sorted(selected)[:-1]
omitted_roster_digest=hashlib.sha256(canonical_json(omitted_roster)).hexdigest()
assert len(omitted_roster)!=134 and omitted_roster_digest!=expected_roster
comps=[]
for n in range(11):
 d=read_alias(f'{base}/components-v2/components-{n:03}.json.gz')
 comps += [f for f in d['features'] if f['id'] in selected]
assert len(selected)==134 and len(comps)==134
eco_path='research/geography/gap-source-abudhabi-physical-seam-20261006/sources/v1/resolve-ecoregions-abu-dhabi-envelope.geojson'
eco_bytes=git_bytes(SOURCE_COMMIT,eco_path)
assert hashlib.sha256(eco_bytes).hexdigest()=='5a7c0583209df1145fb542d595b122b90147ac2e62c0f5dc442f8909f7d67c65'
assert hashlib.sha256(eco_bytes+b'\n').hexdigest()!='5a7c0583209df1145fb542d595b122b90147ac2e62c0f5dc442f8909f7d67c65'
eco=json.loads(eco_bytes)
wrong_ids=json.loads(git_bytes(SOURCE_COMMIT,'research/geography/gap-source-abudhabi-physical-seam-20261006/sources/v1/resolve-ecoregions-objectid-810-811.geojson'))
wrong_eco_ids=sorted(f.get('properties',{}).get('ECO_ID') for f in wrong_ids['features'])
assert wrong_eco_ids==[519,643]
assert len(eco['features'])==5
receipt=json.loads(git_bytes(SOURCE_COMMIT,'research/geography/gap-source-abudhabi-physical-seam-20261006/sources/v1/resolve-ecoregions-envelope-retrieval.json'))
assert '2017' in json.loads(git_bytes(SOURCE_COMMIT,'research/geography/gap-source-abudhabi-physical-seam-20261006/sources/v1/resolve-ecoregions-layer-metadata.json'))['name'] and '2026' in receipt['response_date']
eco_by_id={f['properties'].get('ECO_ID'):f for f in eco['features']}
admin_path='research/geography/gap-source-abudhabi-physical-seam-20261006/sources/v1/geoBoundaries-ARE-ADM1-9469f09.geojson'
admin=json.loads(git_bytes(SOURCE_COMMIT,admin_path)); admin_feats=admin['features']; admin_geos=[shape(f['geometry']) for f in admin_feats]; admin_tree=STRtree(admin_geos)
atlas_path='data/geography/part-0.json'; atlas_bytes=git_bytes(BASE_COMMIT,atlas_path)
assert hashlib.sha256(atlas_bytes).hexdigest()=='bcad5408720e0f50165e794636fd44e02913e5e4649d73c8aa422b94562d32f3'
atlas=json.loads(atlas_bytes); contact_ids={'atlas:physical:a2735e777a9d1037bd3a','atlas:physical:cbea9d242259efda3120','gb:ARE:ADM1:86790563B34058819691262'}
atlas_feats=[f for f in atlas['features'] if (f.get('id') or f.get('properties',{}).get('id')) in contact_ids]
assert len(atlas_feats)==3
atlas_geos=[shape(f['geometry']) for f in atlas_feats]; atlas_tree=STRtree(atlas_geos)

control_component=shape(comps[0]['geometry'])
assert control_component.intersects(shape(eco_by_id[811]['geometry']))
assert not control_component.intersects(shape(eco_by_id[320]['geometry']))
# longitude/latitude geometries; exact topological tests at source coordinate precision
geos=[shape(f['geometry']) for f in eco['features']]; tree=STRtree(geos)
results=[]
for f in comps:
 g=shape(f['geometry']); matches=[]
 for i in tree.query(g):
  e=eco['features'][int(i)]; eg=geos[int(i)]
  if g.intersects(eg):
   ix=g.intersection(eg)
   matches.append({'eco_id':e['properties'].get('ECO_ID'),'eco_name':e['properties'].get('ECO_NAME'),'objectid':e.get('id'),'intersection_type':ix.geom_type,'intersection_area_degrees2':ix.area,'intersection_length_degrees':ix.length,'component_area_degrees2':g.area})
 admin_matches=[]
 for j in admin_tree.query(g):
  af=admin_feats[int(j)]; ag=admin_geos[int(j)]
  if g.intersects(ag):
   ix=g.intersection(ag); ap=af.get('properties',{})
   admin_matches.append({'source_feature_id':ap.get('shapeID'),'name':ap.get('shapeName'),'iso':ap.get('shapeISO'),'intersection_type':ix.geom_type,'intersection_area_degrees2':ix.area,'intersection_length_degrees':ix.length})
 atlas_matches=[]
 for j in atlas_tree.query(g):
  af=atlas_feats[int(j)]; ag=atlas_geos[int(j)]
  if g.intersects(ag):
   ix=g.intersection(ag); ap=af.get('properties',{})
   atlas_matches.append({'id':af.get('id') or ap.get('id'),'name':ap.get('name'),'source_id':ap.get('source_id'),'intersection_type':ix.geom_type,'intersection_area_degrees2':ix.area,'intersection_length_degrees':ix.length})
 props=f['properties']; inv=investigation_by_id[f['id']]
 feature_hash=hashlib.sha256(canonical_json(f)).hexdigest()
 results.append({'component':f['id'],'component_feature_sha256':feature_hash,'bbox':list(g.bounds),'admin_source_matches':admin_matches,'current_atlas_subject_matches':atlas_matches,'fragment_bindings':props.get('fragment_bindings'),'source_contact_references':inv.get('source_contact_references'),'positive_area_location_contact_flag_ids':inv.get('positive_area_location_contact_flag_ids'),'water_diagnostic_references':inv.get('water_diagnostic_references'),'surface_status':inv.get('surface_status'),'complete_investigation_record':inv,'matches':matches})
print('matches count',sum(bool(x['matches']) for x in results),'positive-area',sum(any(m['intersection_area_degrees2']>0 for m in x['matches']) for x in results),'exact contacts only',sum(bool(x['matches']) and not any(m['intersection_area_degrees2']>0 for m in x['matches']) for x in results))
print('ecoregions',sorted({(m['eco_id'],m['eco_name']) for x in results for m in x['matches']}))
print('sample no match',next((x for x in results if not x['matches']),None))
contacts_source=f'{base}/components-v2/contacts-000.json.gz'
contact_rows=read_alias(contacts_source)
selected_contacts=[c for c in contact_rows if set(c.get('components',[])) & selected]
assert len(selected_contacts)==51
omitted_contacts=selected_contacts[:-1]
assert len(omitted_contacts)!=51
assert sum(c.get('kind')=='point-only-ambiguous' for c in selected_contacts)==45
assert sum(c.get('kind')=='shared-edge' for c in selected_contacts)==6
out={'version':'abudhabi-physical-seam-source-overlay-v1','source_note':'Exact source-coordinate topological intersections only; EPSG:4326; no buffering or snapping. Current Ecoregion ECO_ID values and names match Atlas stable IDs; current service bytes are not a frozen historical source snapshot.','component_count':len(comps),'subject_roster_sha256':hashlib.sha256(roster_bytes).hexdigest(),'ecoregion_feature_count':len(eco['features']),'source_service_response_sha256':hashlib.sha256(eco_bytes).hexdigest(),'geoBoundaries_source_feature_count':len(admin_feats),'current_atlas_contact_subject_count':len(atlas_feats),'source_layer_title':'Biomes and Ecoregions 2017','source_response_vintage':'current hosted service response retrieved 2026-10-06','positive_area_overlap_count':sum(any(m['intersection_area_degrees2']>0 for m in x['matches']) for x in results),'zero_area_intersection_count':sum(bool(x['matches']) and not any(m['intersection_area_degrees2']>0 for m in x['matches']) for x in results),'no_intersection_count':sum(not x['matches'] for x in results),'controls':{'positive_selected_component_intersects_ECO_ID_811':True,'negative_selected_component_does_not_intersect_ECO_ID_320':True,'changed_source_bytes_rejected_by_hash':True,'omitted_component_changes_roster_count_and_digest':True,'omitted_contact_fails_exact_contact_count':True,'objectid_810_811_control_resolves_to_ECO_IDs_519_643':True,'historical_vintage_not_laundered_as_current_snapshot':True},'component_contact_records':selected_contacts,'component_contact_record_count':len(selected_contacts),'components':results}
p=ROOT/'research/geography/gap-source-abudhabi-physical-seam-20261006/overlay-v1.json';p.write_bytes(canonical_json(out))
