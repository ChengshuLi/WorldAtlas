#!/usr/bin/env python3
"""Reproduce bounded source-only overlays for issue #1205 from pinned original bytes."""
import argparse, gzip, hashlib, json, pathlib, subprocess, sys
from shapely.geometry import shape, mapping
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[3]/'scripts'))
from physical_component_contacts import component_contacts
from source_input_integrity import verify_source_bytes

ROOT=pathlib.Path(__file__).resolve().parents[3]
PACKET=ROOT/'research/geography/gap-source-matanuska-physical-seam-20261006'
parser=argparse.ArgumentParser()
parser.add_argument('--run-id',required=True,choices=['run-one','run-two'])
RUN_DIR=PACKET/'results'/parser.parse_args().run_id
RUN_DIR.mkdir(parents=True,exist_ok=True)
BASE='cea80a8aa1f8a55ccb448a8f2ff71e10c49a26f1'
PRIOR='coordination/engineering/physical-gap-priorities-1005-20261006-local20/priorities-v2/'
CUSTODY='coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/index.json'
COMPONENTS='coordination/engineering/physical-gap-components-1005-20261005-local19/components-v2/'
SUBJECTS=['atlas:physical:2a15134ff18942dc8e5e','atlas:physical:6efac055720ebe84d7c2','atlas:physical:a20d41a6587ce2e2996b','gb:USA:ADM2:52423323B25289890288494']
TARGET=['atlas:physical:2a15134ff18942dc8e5e','atlas:physical:a20d41a6587ce2e2996b']

def blob(path): return subprocess.check_output(['git','show',f'{BASE}:{path}'],cwd=ROOT)
def parsed(path): return json.loads(blob(path))
def verified(path, descriptor):
    raw=blob(path)
    if len(raw)!=descriptor['bytes'] or sha(raw)!=descriptor['sha256']: raise SystemExit('Whole-file input pin mismatch: '+path)
    if path.endswith('.gz'):
        expanded=gzip.decompress(raw)
        if len(expanded)!=descriptor.get('uncompressed_bytes') or sha(expanded)!=descriptor.get('uncompressed_sha256'): raise SystemExit('Uncompressed input pin mismatch: '+path)
    return raw
def sha(b): return hashlib.sha256(b).hexdigest()
def write_json(name,obj):
    raw=(json.dumps(obj,ensure_ascii=False,separators=(',',':'),sort_keys=True)+'\n').encode()
    (RUN_DIR/name).write_bytes(raw)
    return {'path':str((RUN_DIR/name).relative_to(ROOT)).replace('/'+RUN_DIR.name+'/', '/{run-id}/'),'bytes':len(raw),'sha256':sha(raw)}

# Exact 282-component roster predicate declared in issue #1205, applied to every shard.
priority_path=PRIOR+'report.json'
priority_raw=blob(priority_path)
if len(priority_raw)!=433512 or sha(priority_raw)!='864fe6abab537488766acd6a599782b7a85bbc4f41a4c8027992b05e22462ff1': raise SystemExit('Pinned priority report mismatch')
priority_report=json.loads(priority_raw)
shard_descriptors={d['path']:d for d in priority_report['outputs']['investigations']}
if len(shard_descriptors)!=34: raise SystemExit('Priority report does not enumerate 34 complete shards')
rows=[]
for i in range(34):
    path=f'{PRIOR}investigations-{i:03}.json.gz'
    if path not in shard_descriptors: raise SystemExit('Priority report omits expected shard '+path)
    try: values=json.loads(gzip.decompress(verified(path,shard_descriptors[path])))
    except subprocess.CalledProcessError: raise SystemExit('Pinned investigation shard unavailable: '+path)
    for row in values:
        if row.get('partition','').startswith('interior') and sorted(row.get('positive_length_neighbor_ids',[]))==TARGET:
            rows.append(row)
if len(rows)!=282 or len({r['component'] for r in rows})!=282: raise SystemExit('Issue roster does not match 282 unique components')
roster_raw=(json.dumps(sorted(r['component'] for r in rows),ensure_ascii=False,separators=(',',':'))+'\n').encode()
if sha(roster_raw)!='37b5efeb08f407cd19cc098186659a01899d748d8dd73b3c26bfccbd1d35fc66': raise SystemExit('Exact sorted roster hash mismatch')
component_ids={r['component'] for r in rows}

# Resolve custody aliases without rewriting the historical originals.
index=parsed(CUSTODY)
component_features=[]
component_source_descriptors={}
for alias in index['aliases']:
    name=alias['original']['path']
    if not name.startswith(COMPONENTS) or not __import__('re').search(r'/components-\d{3}\.json\.gz$', name): continue
    if not name.endswith('.json.gz'): continue
    raw=verified(alias['payload'],alias['original'])
    component_source_descriptors[alias['payload']]=alias['original']
    features=json.loads(gzip.decompress(raw))
    component_features.extend(f for f in (features.get('features',[]) if isinstance(features,dict) else features) if f.get('id') in component_ids)
by_id={f['id']:f for f in component_features}
if set(by_id)!=component_ids: raise SystemExit('Selected component geometries incomplete')
fragment_ids={b['id'] for f in by_id.values() for b in f['properties']['fragment_bindings']}
detection_report_path='coordination/engineering/physical-gap-audit-1005-20261005-local18/detection-v4/report.json'
detection_report=json.loads(blob(detection_report_path))
detection_descriptors={d['path']:d for d in detection_report['outputs'] if '/detection-v4/candidates-' in d['path']}
fragments={}
for i in range(17):
    p=f'coordination/engineering/physical-gap-audit-1005-20261005-local18/detection-v4/candidates-{i:03}.geojson.gz'
    if p not in detection_descriptors: raise SystemExit('Detection report omits candidate shard '+p)
    try: bundle=json.loads(gzip.decompress(verified(p,detection_descriptors[p])))
    except subprocess.CalledProcessError: raise SystemExit('Pinned detection candidate unavailable: '+p)
    fragments.update({f['id']:f for f in bundle['features'] if f['id'] in fragment_ids})
if set(fragments)!=fragment_ids: raise SystemExit('Selected candidate fragment geometries incomplete')
contact_ledger=component_contacts(list(fragments.values()),list(by_id.values()))
if len(contact_ledger)!=282 or any(r['status']!='complete-recorded-contacts' for r in contact_ledger): raise SystemExit('Exact contact closure incomplete')
if sum(len(r['fragment_contacts']) for r in contact_ledger)!=283: raise SystemExit('Expected exact 283 fragment bindings')

# Retain only the two source ADM2 features and the two exact RESOLVE ecoregion features.
registry=json.loads((PACKET/'source-registry.json').read_bytes())
source_by_id={source['id']:source for source in registry['sources']}
gb_path='sources/geoboundaries-usa-adm2-selected.geojson'
resolve_path='sources/resolve-ecoregions-2017-ecoids-371-405.geojson'
gb_raw=verify_source_bytes(gb_path,(PACKET/gb_path).read_bytes(),source_by_id['geoboundaries-us-adm2-2018'])
resolve_raw=verify_source_bytes(resolve_path,(PACKET/resolve_path).read_bytes(),source_by_id['resolve-ecoregions-biomes-2017'])
gb=json.loads(gb_raw)
gb_full_original_path='data/regional-review/regional-review-93f8f3bee8e205be/sources/geoboundaries-USA-ADM2.geojson'
gb_full_original=json.loads(blob(gb_full_original_path))
full_original_selected={f['properties']['shapeID']:f for f in gb_full_original['features'] if f.get('properties',{}).get('shapeID') in {'52423323B34523976645917','52423323B25289890288494'}}
if sha(blob(gb_full_original_path))!='81fdd384df8012e5007ed2994a8ab306352f3c48e32cd8ea99182195e8647f43' or {f['properties']['shapeID']:f for f in gb['features']}!=full_original_selected: raise SystemExit('Full-resolution selected features do not match the complete pinned #486 source')
resolve=json.loads(resolve_raw)
gb_simplified_source=source_by_id['geoboundaries-us-adm2-2018-simplified']
gb_simplified_full_path='sources/geoboundaries-usa-adm2-simplified-full.geojson'
gb_simplified_selected_path='sources/geoboundaries-usa-adm2-simplified-selected.geojson'
gb_simplified_meta_path='sources/geoboundaries-usa-adm2-2018-metadata.json'
gb_simplified_full_raw=verify_source_bytes(gb_simplified_full_path,(PACKET/gb_simplified_full_path).read_bytes(),gb_simplified_source)
gb_simplified_selected_raw=verify_source_bytes(gb_simplified_selected_path,(PACKET/gb_simplified_selected_path).read_bytes(),gb_simplified_source)
gb_simplified_meta_raw=verify_source_bytes(gb_simplified_meta_path,(PACKET/gb_simplified_meta_path).read_bytes(),gb_simplified_source)
gb_simplified_full=json.loads(gb_simplified_full_raw)
gb_simplified=json.loads(gb_simplified_selected_raw)
gb_simplified_meta=json.loads(gb_simplified_meta_raw)
full_by_id={f['properties']['shapeID']:f for f in gb_simplified_full['features'] if f['properties'].get('shapeID') in {'52423323B34523976645917','52423323B25289890288494'}}
if len(gb_simplified_full.get('features',[]))!=3233 or gb_simplified_meta.get('boundaryYear')!='2018' or gb_simplified_meta.get('boundaryLicense')!='Public Domain': raise SystemExit('Simplified source capture metadata or complete feature roster mismatch')
if {f['properties']['shapeID']:f for f in gb_simplified['features']}!=full_by_id: raise SystemExit('Selected simplified features differ from exact full-source product features')
admin={f['properties']['shapeID']:shape(f['geometry']) for f in gb['features']}
admin_simplified={f['properties']['shapeID']:shape(f['geometry']) for f in gb_simplified['features']}
eco={str(f['properties']['ECO_ID']):shape(f['geometry']) for f in resolve['features']}
if set(admin)!={'52423323B34523976645917','52423323B25289890288494'} or set(admin_simplified)!=set(admin) or set(eco)!={'371','405'}: raise SystemExit('Selected sources have unexpected IDs')

out_features=[]; rows_out=[]
for cid in sorted(component_ids):
    feature=by_id[cid]; geom=shape(feature['geometry'])
    intersections={}
    for key,g in admin.items(): intersections['admin:'+key]={'intersects':geom.intersects(g),'covers_component':g.covers(geom),'positive_area_intersection':geom.intersection(g).area>0}
    for key,g in admin_simplified.items(): intersections['admin_simplified:'+key]={'intersects':geom.intersects(g),'covers_component':g.covers(geom),'positive_area_intersection':geom.intersection(g).area>0}
    for key,g in eco.items(): intersections['resolve:ECO_ID='+key]={'intersects':geom.intersects(g),'covers_component':g.covers(geom),'positive_area_intersection':geom.intersection(g).area>0}
    fragment_extents=[{'fragment':b['id'],'bounds_lon_lat':list(shape(fragments[b['id']]['geometry']).bounds)} for b in sorted(feature['properties']['fragment_bindings'],key=lambda x:x['id'])]
    rows_out.append({'component':cid,'coordinate_bounds_lon_lat':list(geom.bounds),'bound_fragment_extents_lon_lat':fragment_extents,'intersections':intersections,'classification':'unknown','supported_source_footprint_omission':False,'supported_source_disagreement':False,'independent_water_or_ice_support':False,'reason':'Available overlay polygons, recorded contacts, and incomplete Rock-and-Ice query do not establish a complete physical class or the cause of this component.'})
    out_features.append({'type':'Feature','id':cid,'geometry':mapping(geom),'properties':{**feature['properties'],'investigation_positive_length_neighbors':TARGET}})
summary={}
for source in ['admin:52423323B34523976645917','admin:52423323B25289890288494','resolve:ECO_ID=371','resolve:ECO_ID=405']:
    summary[source]={'intersects':sum(r['intersections'][source]['intersects'] for r in rows_out),'covers_component':sum(r['intersections'][source]['covers_component'] for r in rows_out),'positive_area_intersection':sum(r['intersections'][source]['positive_area_intersection'] for r in rows_out)}
for source in ['admin_simplified:52423323B34523976645917','admin_simplified:52423323B25289890288494']:
    summary[source]={'intersects':sum(r['intersections'][source]['intersects'] for r in rows_out),'covers_component':sum(r['intersections'][source]['covers_component'] for r in rows_out),'positive_area_intersection':sum(r['intersections'][source]['positive_area_intersection'] for r in rows_out)}
for shape_id in sorted(admin):
    full_key='admin:'+shape_id; simple_key='admin_simplified:'+shape_id
    summary['admin_product_predicate_differences:'+shape_id]={field:sum(r['intersections'][full_key][field]!=r['intersections'][simple_key][field] for r in rows_out) for field in ['intersects','covers_component','positive_area_intersection']}
summary.update({'roster_count':len(rows_out),'component_geometry_collection':write_json('selected-components.geojson',{'type':'FeatureCollection','features':out_features}), 'overlay_ledger':write_json('source-overlay-ledger.json',{'version':1,'baseline_commit':BASE,'detector_vintage':{'report_path':'coordination/engineering/physical-gap-audit-1005-20261005-local18/detection-v4/report.json','report_sha256':sha(blob('coordination/engineering/physical-gap-audit-1005-20261005-local18/detection-v4/report.json')),'version':detection_report.get('version'),'baseline_commit':detection_report.get('baseline_commit'),'executed_code_commit':detection_report.get('executed_code_commit'),'release_ids':detection_report.get('release_ids'),'canonical_grid_sha256':detection_report.get('canonical_grid_sha256')},'coordinate_order':'longitude-latitude; EPSG:4326/CRS84; extents are [west,south,east,north]','roster_predicate':{'partition_prefix':'interior','positive_length_neighbor_ids_sorted':TARGET},'source_crs':'EPSG:4326 longitude-latitude','source_products':{'geoboundaries_full_resolution':{'url':source_by_id['geoboundaries-us-adm2-2018']['url'],'baseline_source_path':gb_full_original_path,'baseline_source_sha256':sha(blob(gb_full_original_path)),'retained_selected_sha256':source_by_id['geoboundaries-us-adm2-2018']['retained_source_sha256']},'geoboundaries_simplified_administrative_input':{'url':gb_simplified_source['url'],'complete_dataset_sha256':gb_simplified_source['original_sha256'],'selected_features_sha256':gb_simplified_source['retained_source_sha256'],'metadata_sha256':gb_simplified_source['metadata_sha256'],'metadata':{'boundaryYear':gb_simplified_meta['boundaryYear'],'boundarySource':gb_simplified_meta['boundarySource'],'boundaryLicense':gb_simplified_meta['boundaryLicense'],'sourceDataUpdateDate':gb_simplified_meta['sourceDataUpdateDate'],'buildDate':gb_simplified_meta['buildDate']}}},'method':'Unprojected planar Shapely predicates computed independently against full-resolution and simplified ADM2 polygons, plus RESOLVE ECO_ID 371/405; no tolerance, repair, or authority inference.','summary':summary,'components':rows_out,'exact_contact_ledgers':contact_ledger,'candidate_fragments':{'type':'FeatureCollection','features':[fragments[k] for k in sorted(fragments)]}})})
summary['exact_contact_rows']=sum(len(b['exact_location_contacts'] or []) for r in contact_ledger for b in r['fragment_contacts'])
write_json('source-overlay-summary.json',summary)
print(json.dumps(summary,sort_keys=True))
