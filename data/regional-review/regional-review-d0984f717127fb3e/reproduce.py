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
province_rows=readj('province-assessments.json')
area_rows=readj('area-assessments.json')
risk=readj('scope-risk-screen.json')
assert len(province_rows)==len(s['province_scopes'])==37
assert len(area_rows)==len(s['area_scopes'])==3
assert {x['id'] for x in province_rows}=={x['id'] for x in s['province_scopes']}
assert {x['id'] for x in area_rows}=={x['id'] for x in s['area_scopes']}
area_group_counts={aid:sum(x['area_id']==aid for x in province_rows) for aid in {x['area_id'] for x in province_rows}}
assert area_group_counts=={
 'atlas:area:IND:8170e1c79f28':28,
 'atlas:area:IND:5948131347f0':7,
 'atlas:macro-foundation:area:f54495a7a03aa7c3':2}
assert {aid:row['group_count'] for aid,row in risk['province_group_size_screen'].items()}==area_group_counts
with gzip.open(ROOT/'sources/geoBoundaries-IND-ADM3-2018-retained.geojson.gz','rt') as f: g3=json.load(f)
g2=readj('sources/geoBoundaries-IND-ADM2-2021.geojson')
def index(features):
    out={}
    for feature in features:
        sid=feature['properties'].get('shapeID')
        assert sid and sid not in out, f'missing or duplicate provider shapeID: {sid}'
        out[sid]=feature
    return out
features3=index(g3['features']); features2=index(g2['features'])
ids3=set(features3); ids2=set(features2)
for x in rows.values():
 shape=x['id'].rsplit(':',1)[-1]
 source_feature=(features3 if x['source_id']=='gb:IND:ADM3' else features2).get(shape)
 assert source_feature is not None, x['id']
 assert x['source_name']==source_feature['properties'].get('shapeName')==x['name'], x['id']
 assert x['geometry_type']==source_feature['geometry']['type'], x['id']
 assert x['geometry_components']==(len(source_feature['geometry']['coordinates']) if source_feature['geometry']['type']=='MultiPolygon' else 1), x['id']
assert sum(x['source_id']=='gb:IND:ADM3' for x in rows.values())==204
assert sum(x['source_id']=='gb:IND:ADM2' for x in rows.values())==26
inv=readj('source-inventory.json')
for f in inv['sources']:
 assert sha(f['path'])==f['sha256'], f['path']
print(json.dumps({'scope_ids':len(ids),'unique_scope_ids':len(set(ids)),'assessment_rows':len(rows),'province_rows':len(province_rows),'area_rows':len(area_rows),'province_groups_by_area':area_group_counts,'source_feature_id_matches':230,'source_name_equalities':230,'source_geometry_type_and_component_checks':230,'adm2_source_features':len(g2['features']),'adm3_source_features':len(g3['features']),'scoped_adm2':26,'scoped_adm3':204,'result':'PASS','meaning':'Exact scope, source identity, packet coverage and retained-byte hashes only; no proof of legal/current boundaries, source completeness, tier suitability, topological accuracy or geographic truth.'},indent=2))
