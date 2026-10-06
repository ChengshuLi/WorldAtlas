#!/usr/bin/env python3
"""Reproduce bounded source-only overlays for issue #1205 from pinned original bytes."""
import argparse, gzip, hashlib, json, pathlib, subprocess, sys
from shapely.geometry import shape, mapping
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[3]/'scripts'))
from physical_component_contacts import component_contacts

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
def sha(b): return hashlib.sha256(b).hexdigest()
def write_json(name,obj):
    raw=(json.dumps(obj,ensure_ascii=False,separators=(',',':'),sort_keys=True)+'\n').encode()
    (RUN_DIR/name).write_bytes(raw)
    return {'path':str((RUN_DIR/name).relative_to(ROOT)),'bytes':len(raw),'sha256':sha(raw)}

# Exact 282-component roster predicate declared in issue #1205, applied to every shard.
rows=[]
for i in range(34):
    path=f'{PRIOR}investigations-{i:03}.json.gz'
    try: values=json.loads(gzip.decompress(blob(path)))
    except subprocess.CalledProcessError: continue
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
for alias in index['aliases']:
    name=alias['original']['path']
    if not name.startswith(COMPONENTS) or not __import__('re').search(r'/components-\d{3}\.json\.gz$', name): continue
    if not name.endswith('.json.gz'): continue
    raw=blob(alias['payload'])
    if sha(raw)!=alias['original']['sha256']: raise SystemExit('Custody alias payload hash mismatch')
    features=json.loads(gzip.decompress(raw))
    component_features.extend(f for f in (features.get('features',[]) if isinstance(features,dict) else features) if f.get('id') in component_ids)
by_id={f['id']:f for f in component_features}
if set(by_id)!=component_ids: raise SystemExit('Selected component geometries incomplete')
fragment_ids={b['id'] for f in by_id.values() for b in f['properties']['fragment_bindings']}
fragments={}
for i in range(17):
    p=f'coordination/engineering/physical-gap-audit-1005-20261005-local18/detection-v4/candidates-{i:03}.geojson.gz'
    try: bundle=json.loads(gzip.decompress(blob(p)))
    except subprocess.CalledProcessError: continue
    fragments.update({f['id']:f for f in bundle['features'] if f['id'] in fragment_ids})
if set(fragments)!=fragment_ids: raise SystemExit('Selected candidate fragment geometries incomplete')
contact_ledger=component_contacts(list(fragments.values()),list(by_id.values()))
if len(contact_ledger)!=282 or any(r['status']!='complete-recorded-contacts' for r in contact_ledger): raise SystemExit('Exact contact closure incomplete')
if sum(len(r['fragment_contacts']) for r in contact_ledger)!=283: raise SystemExit('Expected exact 283 fragment bindings')

# Retain only the two source ADM2 features and the two exact RESOLVE ecoregion features.
gb=json.loads((PACKET/'sources/geoboundaries-usa-adm2-selected.geojson').read_bytes())
resolve=json.loads((PACKET/'sources/resolve-ecoregions-2017-ecoids-371-405.geojson').read_bytes())
admin={f['properties']['shapeID']:shape(f['geometry']) for f in gb['features']}
eco={str(f['properties']['ECO_ID']):shape(f['geometry']) for f in resolve['features']}
if set(admin)!={'52423323B34523976645917','52423323B25289890288494'} or set(eco)!={'371','405'}: raise SystemExit('Selected sources have unexpected IDs')

out_features=[]; rows_out=[]
for cid in sorted(component_ids):
    feature=by_id[cid]; geom=shape(feature['geometry'])
    intersections={}
    for key,g in admin.items(): intersections['admin:'+key]={'intersects':geom.intersects(g),'covers_component':g.covers(geom),'positive_area_intersection':geom.intersection(g).area>0}
    for key,g in eco.items(): intersections['resolve:ECO_ID='+key]={'intersects':geom.intersects(g),'covers_component':g.covers(geom),'positive_area_intersection':geom.intersection(g).area>0}
    rows_out.append({'component':cid,'intersections':intersections,'finding':'unresolved-source-overlay-only'})
    out_features.append({'type':'Feature','id':cid,'geometry':mapping(geom),'properties':{'id':cid,'investigation_positive_length_neighbors':TARGET}})
summary={}
for source in ['admin:52423323B34523976645917','admin:52423323B25289890288494','resolve:ECO_ID=371','resolve:ECO_ID=405']:
    summary[source]={'intersects':sum(r['intersections'][source]['intersects'] for r in rows_out),'covers_component':sum(r['intersections'][source]['covers_component'] for r in rows_out),'positive_area_intersection':sum(r['intersections'][source]['positive_area_intersection'] for r in rows_out)}
summary.update({'roster_count':len(rows_out),'component_geometry_collection':write_json('selected-components.geojson',{'type':'FeatureCollection','features':out_features}), 'overlay_ledger':write_json('source-overlay-ledger.json',{'version':1,'baseline_commit':BASE,'roster_predicate':{'partition_prefix':'interior','positive_length_neighbor_ids_sorted':TARGET},'source_crs':'EPSG:4326 longitude-latitude','method':'unprojected planar Shapely intersects/covers/area>0; diagnostic only; no tolerance, repair, or authority inference','summary':summary,'components':rows_out,'exact_contact_ledgers':contact_ledger,'candidate_fragments':{'type':'FeatureCollection','features':[fragments[k] for k in sorted(fragments)]}})})
summary['exact_contact_rows']=sum(len(b['exact_location_contacts'] or []) for r in contact_ledger for b in r['fragment_contacts'])
write_json('source-overlay-summary.json',summary)
print(json.dumps(summary,sort_keys=True))
