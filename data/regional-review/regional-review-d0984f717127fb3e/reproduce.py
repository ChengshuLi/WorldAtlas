#!/usr/bin/env python3
"""Reproduce exact-scope/source identity screens for issue #81. Not a map accuracy test."""
import gzip, hashlib, json
from pathlib import Path
ROOT=Path(__file__).parent

def readj(p): return json.loads((ROOT/p).read_text())
def sha(p): return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
s=readj('issue-scope.json'); ids=s['member_location_ids']
assert len(ids)==230 and len(set(ids))==230
assert hashlib.sha256('\n'.join(sorted(ids)).encode()).hexdigest()==s['member_location_ids_sha256']
locations=readj('location-assessments.json'); rows={x['id']:x for x in locations}
assert len(rows)==230 and set(rows)==set(ids)
assert all(x['assessment'] in {'justified','correction-needed','insufficient_evidence'} for x in rows.values())
assert all(x['assessment']=='insufficient_evidence' for x in rows.values())
assert all(x['source_feature_found'] for x in rows.values())
assert all(x['source_name']==x['name'] for x in rows.values())
assert len(readj('province-assessments.json'))==len(s['province_scopes'])==37
assert len(readj('area-assessments.json'))==len(s['area_scopes'])==3
with gzip.open(ROOT/'sources/geoBoundaries-IND-ADM3-2018-retained.geojson.gz','rt') as f: g3=json.load(f)
g2=readj('sources/geoBoundaries-IND-ADM2-2021.geojson')
ids3={x['properties'].get('shapeID') for x in g3['features']}; ids2={x['properties'].get('shapeID') for x in g2['features']}
for x in rows.values():
 shape=x['id'].rsplit(':',1)[-1]
 assert shape in (ids3 if x['source_id']=='gb:IND:ADM3' else ids2), x['id']
assert sum(x['source_id']=='gb:IND:ADM3' for x in rows.values())==204
assert sum(x['source_id']=='gb:IND:ADM2' for x in rows.values())==26
inv=readj('source-inventory.json')
for f in inv['sources']:
 assert sha(f['path'])==f['sha256'], f['path']
print(json.dumps({'scope_ids':len(ids),'unique_scope_ids':len(set(ids)),'assessment_rows':len(rows),'province_rows':37,'area_rows':3,'source_feature_id_matches':230,'source_name_equalities':sum(x['source_name']==x['name'] for x in rows.values()),'adm2_source_features':len(g2['features']),'adm3_source_features':len(g3['features']),'scoped_adm2':26,'scoped_adm3':204,'result':'PASS','meaning':'Exact scope, source identity, packet coverage and retained-byte hashes only; no proof of legal/current boundaries, source completeness, tier suitability, topological accuracy or geographic truth.'},indent=2))
