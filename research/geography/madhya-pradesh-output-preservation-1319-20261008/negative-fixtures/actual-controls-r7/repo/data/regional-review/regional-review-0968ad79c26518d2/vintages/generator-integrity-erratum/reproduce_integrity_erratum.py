#!/usr/bin/env python3
"""Reproduce exact subject/source identity and sibling partition checks for #82.
Reads the compressed original GeoJSON through gzip; it never writes decompressed source bytes.
"""
from pathlib import Path
import gzip, hashlib, json, re, platform, subprocess
import shapely, pyproj
from shapely.geometry import shape, Polygon
import sys
sys.path[:0]=[str(Path(__file__).resolve().parent/'methods')]
from geometry import land_area_m2, METHOD
from integrity_guards import verify_bound_input, require_new_output

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT.parents[2]

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

input_manifest=ROOT/'vintages'/'generator-integrity-erratum'/'evaluation-inputs.json'
assert sha(input_manifest)=='e2f9c442883ea10768dd8ae4946061c9681cb3b9e15e4c1ff442f80c04e3a098', 'Pinned evaluation manifest changed'
input_spec=json.loads(input_manifest.read_text())
assert input_spec['evaluation_commit']=='cbb829672d18801e4310c30896a7ddb13a79b451'
for descriptor in input_spec['inputs']:
    committed=subprocess.check_output(['git','show',input_spec['evaluation_commit']+':'+descriptor['path']],cwd=REPO)
    # The original geometry helper is archived as a new vintage because current main
    # has a different helper. All other inputs must match their exact checkout bytes.
    if descriptor['path']=='scripts/evidence/geometry.py': working=(Path(__file__).resolve().parent/'methods'/'geometry.py').read_bytes()
    elif descriptor['path']=='scripts/ellipsoidal_area.py': working=(Path(__file__).resolve().parent/'methods'/'ellipsoidal_area.py').read_bytes()
    else: working=(REPO/descriptor['path']).read_bytes()
    verify_bound_input(descriptor, committed, working)

def load(p): return json.loads(Path(p).read_text())
def canonical_ids(ids): return '\n'.join(ids).encode()

scope=load(ROOT/'issue-scope.json')
source_inventory=load(ROOT/'sources'/'source-inventory.json')
issue_input_hash=sha(ROOT/'issue-scope.json')
sibling_input_path=ROOT/'sources'/'sibling-scope-input.json'
assert next(x for x in source_inventory['scope_evidence'] if x['id']=='issue-82-exact-contract')['sha256']==issue_input_hash
assert next(x for x in source_inventory['scope_evidence'] if x['id']=='neighboring-packet-scopes-81-83')['sha256']==sha(sibling_input_path)
ids=scope['workload_scope']['member_location_ids']
assert len(ids)==224 and len(set(ids))==224
assert hashlib.sha256(canonical_ids(ids)).hexdigest()==scope['workload_scope']['member_location_ids_sha256']

metadata=load(REPO/'data/global-sources/IND-ADM3-metadata.json')
gz=REPO/'data/global-sources/IND-ADM3.geojson.gz'
assert sha(gz)==metadata['compressed_sha256']
source_descriptor=next(x for x in source_inventory['sources'] if x['id']=='geoBoundaries-IND-ADM3-2018')
assert source_descriptor['compressed_sha256']==sha(gz) and source_descriptor['metadata_sha256']==sha(REPO/'data/global-sources/IND-ADM3-metadata.json')
admin_rosters=load(ROOT/'sources'/'current-admin-rosters.json')
for entry in admin_rosters['rosters']:
    descriptor=next(x for x in source_inventory['sources'] if x['id']=='current-admin-roster:'+entry['district'])
    assert descriptor['url']==entry['url'] and descriptor['sha256']==entry['sha256']
# gzip.open streams compressed bytes; source is not materialized to a decoded file.
with gzip.open(gz,'rt',encoding='utf-8') as f: source=json.load(f)
features=source['features']
by_source={}
for feature in features:
    sid=feature.get('properties',{}).get('shapeID')
    if sid: by_source.setdefault(sid,[]).append(feature)

parts=[REPO/f'data/geography/part-{n}.json' for n in (30,31,32,33)]
atlas={}
for path in parts:
    data=load(path)
    rows=data if isinstance(data,list) else data.get('features',[])
    for feature in rows:
        row=feature.get('properties',feature)
        if row.get('id') in ids: atlas.setdefault(row['id'],[]).append((path,{**row,'_geometry':feature.get('geometry')}))
assert set(atlas)==set(ids), f"Atlas scope mismatch missing={set(ids)-set(atlas)} extra={set(atlas)-set(ids)}"
assert all(len(v)==1 for v in atlas.values()), 'Atlas subject duplicated across source parts'

hierarchy=load(REPO/'data/hierarchy.json')
hier={x['id']:x for x in hierarchy}
rows=[]; source_memberships=[]
for aid in ids:
    part,row=atlas[aid][0]
    source_ids=row.get('metadata',{}).get('source_member_ids',row.get('source_member_ids',row.get('source_ids',[])))
    assert len(source_ids)==1, f'{aid}: expected one retained source member, got {source_ids}'
    sid=source_ids[0]
    matches=by_source.get(sid,[])
    assert len(matches)==1, f'{aid}: native source id {sid} resolves {len(matches)} times'
    feat=matches[0]; props=feat['properties']; parent=hier.get(row.get('parent_id'),{})
    name=row.get('name')
    atlas_geom=shape(row['_geometry']); native_geom=shape(feat['geometry'])
    assert props.get('shapeName')==name, f'{aid}: Atlas/source name mismatch {name!r}/{props.get("shapeName")!r}'
    assert props.get('shapeGroup')=='IND' and props.get('shapeType')=='ADM3', f'{aid}: unexpected source group/type'
    rows.append({'id':aid,'name':name,'province_id':row.get('parent_id'),'province_name':parent.get('name'),
                 'source_id':sid,'source_name':props.get('shapeName'),'source_group':props.get('shapeGroup'),
                 'source_type':props.get('shapeType'),'atlas_recorded_location_basis':row.get('metadata',{}).get('location_basis'),'prior_location_semantic_status':row.get('metadata',{}).get('semantic_review',{}).get('status'),'prior_province_semantic_status':parent.get('metadata',{}).get('semantic_review',{}).get('status'),'geometry_type':row.get('_geometry',{}).get('type'),
                 'geometry_component_count':len(atlas_geom.geoms) if atlas_geom.geom_type=='MultiPolygon' else 1,
                 'polygon_hole_count':sum(len(g.interiors) for g in atlas_geom.geoms) if atlas_geom.geom_type=='MultiPolygon' else len(atlas_geom.interiors),
                 'geometry_exactly_matches_retained_source':row.get('_geometry')==feat.get('geometry'),
                 'geometry_topologically_equals_retained_source':atlas_geom.equals(native_geom),
                 'geometry_valid':atlas_geom.is_valid and native_geom.is_valid,
                 'atlas_area_m2':land_area_m2(atlas_geom),'source_area_m2':land_area_m2(native_geom),
                 'symmetric_difference_area_m2':land_area_m2(atlas_geom.symmetric_difference(native_geom)) if not atlas_geom.equals(native_geom) else 0.0})
    source_memberships.append(sid)
assert len(set(source_memberships))==224
assert all(row['geometry_valid'] for row in rows)
assert all(row['prior_location_semantic_status']=='open' for row in rows), 'Prior geographic-review status changed from open'
exact_geometry_matches=sum(1 for row in rows if row['geometry_exactly_matches_retained_source'])
topological_geometry_matches=sum(1 for row in rows if row['geometry_topologically_equals_retained_source'])
valid_geometry_pairs=sum(1 for row in rows if row['geometry_valid'])
geometry_positive_control=land_area_m2(shape({'type':'Polygon','coordinates':[[[0,0],[1,0],[1,1],[0,1],[0,0]]]}))
try:
    land_area_m2(Polygon([(0,0),(1,1),(1,0),(0,1),(0,0)]))
    geometry_negative_control='failed'
except ValueError:
    geometry_negative_control='passed'
assert 12_000_000_000 < geometry_positive_control < 13_000_000_000
assert geometry_negative_control=='passed'
assert len(features)==6822 and int(metadata['admUnitCount'])==6836

siblings=load(sibling_input_path)['siblings']
mp_area='atlas:area:IND:5948131347f0'
def mp_scope_ids(sc):
    return {aid for province in sc['province_scopes'] if hier.get(province['id'],{}).get('parent_id')==mp_area for aid in province['owned_location_ids']}
set_by_issue={str(x['issue']):mp_scope_ids(x['scope']) for x in siblings}
set_by_issue['82']=mp_scope_ids(scope['workload_scope'])
mp_province_ids={x['id'] for x in hierarchy if x.get('level')=='province' and x.get('parent_id')==mp_area}
mp_current={feature['properties']['id'] for path in parts for feature in load(path)['features'] if feature['properties'].get('parent_id') in mp_province_ids}
combined=set().union(*set_by_issue.values())
assert sum(map(len,set_by_issue.values()))==422
assert set_by_issue['81'].isdisjoint(set_by_issue['82']) and set_by_issue['82'].isdisjoint(set_by_issue['83']) and set_by_issue['81'].isdisjoint(set_by_issue['83'])
assert len(mp_current)==422 and combined==mp_current, f'MP partition discrepancy missing={len(mp_current-combined)} extra={len(combined-mp_current)}'

# Current IGOD evidence is captured per fetched official page. Unfetched district lists remain explicit gaps.
roster_source=load(ROOT/'sources'/'current-admin-rosters.json')
current={item['district']:item for item in roster_source['rosters']}

findings=[]
province_groups={}
for r in rows: province_groups.setdefault(r['province_name'],[]).append(r['name'])
province_assessments=[]
for province,names in sorted(province_groups.items()):
    page=current.get(province) or current.get(province.replace(' (West Nimar)','')) or (current.get('Agar-Malwa') if province=='Agar' else None) or (current.get('Narmadapuram') if province=='Hoshangabad' else None)
    if page:
        norm=lambda n: re.sub(r'[^a-z0-9]','',n.casefold())
        atlas_norm={norm(n):n for n in names}; lgd_norm={norm(n):n for n in page['listed_names']}
        province_assessments.append({'province':province,'atlas_scoped_count':len(names),'lgd_listed_count':page['page_count'],'current_roster_source_system':page['system'],'lgd_source_url':page['url'],'lgd_source_sha256':page['sha256'],'exact_text_matches':sorted(set(names)&set(page['listed_names'])), 'atlas_not_exactly_listed':sorted(set(names)-set(page['listed_names'])),'lgd_not_exactly_in_packet':sorted(set(page['listed_names'])-set(names)),'normalized_atlas_only':sorted(atlas_norm[k] for k in set(atlas_norm)-set(lgd_norm)),'normalized_lgd_only':sorted(lgd_norm[k] for k in set(lgd_norm)-set(atlas_norm)),'classification':'correction-needed' if province in ('Chhindwara','Hoshangabad') else 'insufficient-evidence','interpretation':'Administrative roster differences are reconciliation leads; they do not establish polygon membership or omitted territory.'})
    else: province_assessments.append({'province':province,'atlas_scoped_count':len(names),'lgd_listed_count':None,'current_roster_source_system':None,'lgd_source_url':None,'lgd_source_sha256':None,'exact_text_matches':[],'atlas_not_exactly_listed':names,'lgd_not_exactly_in_packet':None,'normalized_atlas_only':None,'normalized_lgd_only':None,'classification':'correction-needed' if province in ('Chhindwara','Hoshangabad') else 'insufficient-evidence','interpretation':'No retained exact current roster; completeness and current local unit correspondence remain open.'})
for r in rows:
    p=r['province_name']; matching=current.get(p) or current.get(p.replace(' (West Nimar)','')) or (current.get('Agar-Malwa') if p=='Agar' else None) or (current.get('Narmadapuram') if p=='Hoshangabad' else None)
    classification='insufficient-evidence'; reason='2018 ADM3 source identity/name is reproduced, but current boundary correspondence, source completeness for this district, and territorial purpose beyond the directory label are not established.'
    if r['name'] in ('Pandhurna','Sausar'):
        classification='correction-needed'; reason='Official 2023 order transfers this exact subdistrict out of Chhindwara into newly formed Pandhurna district; current Atlas parent is Chhindwara. Exact polygon-to-current legal boundary correspondence remains unverified.'
    if p=='Hoshangabad':
        classification='correction-needed'; reason='Official district source states Hoshangabad district was renamed Narmadapuram effective 2022-02-07; all nine Atlas subjects retain the old province label. Individual current tehsil and polygon correspondence remains unresolved.'
    findings.append({**r,'classification':classification,'finding':reason,
                     'current_roster_source_url':matching.get('url') if matching else None,
                     'current_roster_source_sha256':matching.get('sha256') if matching else None,'current_roster_source_system':matching.get('system') if matching else None,
                     'current_roster_name_exact_match':(r['name'] in matching['listed_names']) if matching else None})

input_paths=[ROOT/'issue-scope.json',ROOT/'sources'/'sibling-scope-input.json',ROOT/'sources'/'current-admin-rosters.json',ROOT/'sources'/'source-inventory.json',REPO/'data/global-sources/IND-ADM3.geojson.gz',REPO/'data/global-sources/IND-ADM3-metadata.json',REPO/'data/hierarchy.json',REPO/'data/geographic-decisions/asia.json',*[REPO/f'data/geography/part-{n}.json' for n in (30,31,32,33)],REPO/'scripts/evidence/geometry.py',REPO/'scripts/ellipsoidal_area.py',Path(__file__)]
input_files=[{'path':str(p.relative_to(REPO)),'sha256':sha(p),'bytes':p.stat().st_size} for p in input_paths]
out={'version':1,'issue':82,'reproduction_runtime':{'python':platform.python_version(),'shapely':shapely.__version__,'pyproj':pyproj.__version__,'geometry_method_version':METHOD['version']},'input_files':input_files,'retrieved_scope':{'issue_url':scope['issue_url'],'issue_body_sha256':scope['issue_body_sha256'],'base_commit':scope['base_commit'],'subjects':len(ids),'subjects_sha256':hashlib.sha256(canonical_ids(ids)).hexdigest()},
     'geometry_method':METHOD,'geometry_controls':{'positive_wgs84_one_degree_square_area_m2':geometry_positive_control,'positive_control_outcome':'passed','negative_self_intersection_outcome':geometry_negative_control},
     'source':{'path':'data/global-sources/IND-ADM3.geojson.gz','compressed_sha256':sha(gz),'metadata_sha256':sha(REPO/'data/global-sources/IND-ADM3-metadata.json'),'vintage':metadata['boundaryYearRepresented'],'update_date':metadata['sourceDataUpdateDate'],'built':metadata['buildDate'],'declared_role':metadata['boundaryCanonical'],'declared_license':metadata['boundaryLicense'],'features_actual':len(features),'features_metadata':int(metadata['admUnitCount']),'count_difference':int(metadata['admUnitCount'])-len(features)},
     'scope_reproduction':{'atlas_exact_once':len(atlas),'native_source_ids_unique':len(set(source_memberships)),'native_source_ids_found_once':len(source_memberships),'atlas_geometries_coordinate_identical_to_native_source_geometry':exact_geometry_matches,'atlas_geometries_topologically_equal_native_source_geometry':topological_geometry_matches,'valid_geometry_pairs':valid_geometry_pairs,'sibling_packet_union':len(combined),'sibling_packet_sum':sum(map(len,set_by_issue.values())),'mp_area_location_count':len(mp_current),'sibling_packet_union_equals_mp_area':combined==mp_current,'neighboring_issue_counts':{k:len(v) for k,v in set_by_issue.items()},'sibling_issue_body_sha256':{str(x['issue']):x['body_sha256'] for x in siblings}},
     'province_assessments':province_assessments,
     'limitations':['Identity, name, hierarchy scope, and partition reproduction do not establish legal territorial role or boundary correctness.','geoBoundaries metadata says 2018 Sub-District, but actual boundary derivation/current ADM role and full district completeness remain unverified.','Metadata reports 6,836 units while retained GeoJSON contains 6,822 (14-unit mismatch).','Current IGOD roster counts/names are administrative directory evidence only; any district absent from captured pages remains unverified.','No geometry repair, legal-boundary overlay, or topological completeness claim was made.','Current administrative roster sources are retained for 26 of 27 scoped provinces; Sheopur current roster is an explicit gap. Roster names/counts do not prove polygon membership.'],
     'exact_subjects':findings}
output_path=Path(sys.argv[1])
require_new_output(output_path)
output_path.parent.mkdir(parents=True,exist_ok=True)
raw=json.dumps(out,ensure_ascii=False,indent=2).encode('utf-8')+b'\n'
output_path.write_bytes(gzip.compress(raw,mtime=0))
print(json.dumps({'subjects':len(findings),'source_actual_features':len(features),'source_metadata_features':int(metadata['admUnitCount']),'scope_partition':out['scope_reproduction'],'classification_counts':{c:sum(1 for x in findings if x['classification']==c) for c in ('justified','correction-needed','insufficient-evidence')}},indent=2))
