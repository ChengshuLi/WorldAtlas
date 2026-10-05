#!/usr/bin/env python3
"""Scope, provenance and reproducibility checks for issue 71's owned packet."""
import csv, gzip, hashlib, json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
issue=json.load(open(ROOT/'issue-71-api.json'));body=issue['body']
scope=json.loads(body[body.index('{"area_scopes"'):body.index('\n```',body.index('{"area_scopes"'))])
rows=list(csv.DictReader(open(ROOT/'assessment.csv',newline='')))
scoped=set(scope['member_location_ids']);observed=[r['id'] for r in rows]
assert len(observed)==226 and len(set(observed))==226 and set(observed)==scoped
assert hashlib.sha256('\n'.join(scope['member_location_ids']).encode()).hexdigest()==scope['member_location_ids_sha256']
assert {r['classification'] for r in rows}=={'insufficient-evidence'}
scope_rows=list(csv.DictReader(open(ROOT/'scope-assessment.csv')))
assert len(scope_rows)==30 and sum(x['classification']=='correction-needed' for x in scope_rows)==1
istanbul_scope=next(x for x in scope_rows if x['id']=='framework:province:istanbul:69a618445c3d')
assert istanbul_scope['classification']=='correction-needed' and istanbul_scope['full_scope_count']=='7' and istanbul_scope['owned_count']=='7'
istanbul=json.load(open(ROOT/'sources/istanbul-official-district-roster.json'))['districts']
crosswalk=list(csv.DictReader(open(ROOT/'istanbul-completeness.csv',newline='')))
assert len(istanbul)==39 and len(crosswalk)==39 and len({x['geoBoundaries_shapeID'] for x in crosswalk})==39
assert sum(x['atlas_baseline_present']=='True' for x in crosswalk)==7
assert sum(x['atlas_baseline_present']=='False' for x in crosswalk)==32
profiles=json.load(open(ROOT/'source-inventory.json'))['source_profiles']
counts={p['source_id']:(p['feature_count'],p['pinned_metadata_count'],p['count_matches']) for p in profiles}
assert counts=={'gb:CYP:ADM1':(6,6,True),'gb:GRC:ADM3':(326,326,True),'gb:TUR:ADM2':(973,999,False)}
for path in [ROOT/'sources/geoBoundaries-CYP-ADM1.geojson.gz',ROOT/'sources/geoBoundaries-GRC-ADM3.geojson.gz',ROOT/'sources/geoBoundaries-TUR-ADM2.geojson.gz']:
    with gzip.open(path,'rt',encoding='utf-8') as f: data=json.load(f)
    iso=path.name.split('-')[1]; seen={str(f['properties']['shapeID']) for f in data['features']}
    expected={x.rsplit(':',1)[-1] for x in scoped if x.startswith('gb:'+iso+':')}
    assert expected<=seen,(iso,expected-seen)
assert len(list(csv.DictReader(open(ROOT/'greece-2021-crosswalk-screen.csv'))))==json.load(open(ROOT/'greece-2021-crosswalk-provenance.json'))['output_rows']
followups=json.load(open(ROOT/'follow-up-recommendations.json'))['created_followups']
assert [x['issue'] for x in followups]==[817,818,819,820,821]
assert [len(x['subject_ids']) for x in followups]==[1,6,19,4,39]
assert all(x['status']=='blocked' for x in followups)
for entry in json.load(open(ROOT/'source-files.json'))['files']:
    if entry['path'].startswith('sources/'):
        p=ROOT/entry['path'];assert p.is_file() and sha(p)==entry['sha256'],entry['path']
assert json.load(open(ROOT/'claim-receipt.json'))['claim_id']=='18b063dc-8716-4a3a-8dd6-605d6610ce3a'
print('PASS: 226 exact unique members, 30 area/province scope rows, all member sourceIDs matched, 39 official Istanbul district candidates crosswalked (7 present/32 absent), source counts/pins verified, Greek crosswalk output bound, follow-up contracts recorded.')
print('LIMIT: checks establish scope and reproducibility only; 226 locations remain insufficient-evidence, and one province scope is correction-needed pending #821.')
