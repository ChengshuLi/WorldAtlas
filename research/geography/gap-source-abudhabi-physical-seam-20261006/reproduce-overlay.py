import json,gzip,glob,os,hashlib
from shapely.geometry import shape
from shapely.strtree import STRtree
base='coordination/engineering/physical-gap-components-1005-20261005-local19'
idx=json.load(open(base+'/custody-v1/index.json'))
byorig={a['original']['path']:a['payload'] for a in idx['aliases']}
def read_alias(path):
 b=open(byorig[path],'rb').read()
 return json.loads(gzip.decompress(b))
selected=[]
investigation_by_id={}
for p in sorted(glob.glob('coordination/engineering/physical-gap-priorities-1005-20261006-local20/priorities-v2/investigations-*.json.gz')):
 d=json.load(gzip.open(p,'rb'))
 for r in d:
  if r.get('partition','').startswith('interior') and sorted(r.get('positive_length_neighbor_ids',[]))==['atlas:physical:a2735e777a9d1037bd3a','atlas:physical:cbea9d242259efda3120']:
   selected.append(r['component'])
   investigation_by_id[r['component']]=r
selected=set(selected)
assert len(selected)==134
roster_bytes=(json.dumps(sorted(selected),separators=(',',':'))+'\n').encode()
assert hashlib.sha256(roster_bytes).hexdigest()=='b7af8568f5972dd935d8cc85d16c19f349938ea6810b6b2b391c92d4a1b9df94'
comps=[]
for n in range(11):
 d=read_alias(f'{base}/components-v2/components-{n:03}.json.gz')
 comps += [f for f in d['features'] if f['id'] in selected]
assert len(selected)==134 and len(comps)==134
eco_path='research/geography/gap-source-abudhabi-physical-seam-20261006/sources/v1/resolve-ecoregions-abu-dhabi-envelope.geojson'
eco_bytes=open(eco_path,'rb').read()
assert hashlib.sha256(eco_bytes).hexdigest()=='5a7c0583209df1145fb542d595b122b90147ac2e62c0f5dc442f8909f7d67c65'
assert hashlib.sha256(eco_bytes+b'\n').hexdigest()!='5a7c0583209df1145fb542d595b122b90147ac2e62c0f5dc442f8909f7d67c65'
eco=json.loads(eco_bytes)
assert len(eco['features'])==5
eco_by_id={f['properties'].get('ECO_ID'):f for f in eco['features']}
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
 props=f['properties']; inv=investigation_by_id[f['id']]
 feature_hash=hashlib.sha256((json.dumps(f,sort_keys=True,ensure_ascii=False,separators=(',',':'))+'\n').encode()).hexdigest()
 results.append({'component':f['id'],'component_feature_sha256':feature_hash,'bbox':list(g.bounds),'fragment_bindings':props.get('fragment_bindings'),'source_contact_references':inv.get('source_contact_references'),'positive_area_location_contact_flag_ids':inv.get('positive_area_location_contact_flag_ids'),'water_diagnostic_references':inv.get('water_diagnostic_references'),'surface_status':inv.get('surface_status'),'complete_investigation_record':inv,'matches':matches})
print('matches count',sum(bool(x['matches']) for x in results),'positive-area',sum(any(m['intersection_area_degrees2']>0 for m in x['matches']) for x in results),'exact contacts only',sum(bool(x['matches']) and not any(m['intersection_area_degrees2']>0 for m in x['matches']) for x in results))
print('ecoregions',sorted({(m['eco_id'],m['eco_name']) for x in results for m in x['matches']}))
print('sample no match',next((x for x in results if not x['matches']),None))
contacts_source=f'{base}/components-v2/contacts-000.json.gz'
contact_rows=read_alias(contacts_source)
selected_contacts=[c for c in contact_rows if set(c.get('components',[])) & selected]
assert len(selected_contacts)==51
assert len(selected_contacts)-1 != 51
assert sum(c.get('kind')=='point-only-ambiguous' for c in selected_contacts)==45
assert sum(c.get('kind')=='shared-edge' for c in selected_contacts)==6
out={'version':'abudhabi-physical-seam-source-overlay-v1','source_note':'Exact source-coordinate topological intersections only; EPSG:4326; no buffering or snapping. Current Ecoregion ECO_ID values and names match Atlas stable IDs; current service bytes are not a frozen historical source snapshot.','component_count':len(comps),'subject_roster_sha256':hashlib.sha256(roster_bytes).hexdigest(),'ecoregion_feature_count':len(eco['features']),'source_service_response_sha256':hashlib.sha256(eco_bytes).hexdigest(),'source_layer_title':'Biomes and Ecoregions 2017','source_response_vintage':'current hosted service response retrieved 2026-10-06','positive_area_overlap_count':sum(any(m['intersection_area_degrees2']>0 for m in x['matches']) for x in results),'zero_area_intersection_count':sum(bool(x['matches']) and not any(m['intersection_area_degrees2']>0 for m in x['matches']) for x in results),'no_intersection_count':sum(not x['matches'] for x in results),'controls':{'positive_selected_component_intersects_ECO_ID_811':True,'negative_selected_component_does_not_intersect_ECO_ID_320':True,'changed_source_bytes_rejected_by_hash':True,'omitted_component_or_contact_fails_exact_count_and_roster_checks':True,'historical_vintage_not_laundered_as_current_snapshot':True},'component_contact_records':selected_contacts,'component_contact_record_count':len(selected_contacts),'components':results}
p='research/geography/gap-source-abudhabi-physical-seam-20261006/overlay-v1.json';open(p,'w').write(json.dumps(out,sort_keys=True,separators=(',',':'))+'\n')
