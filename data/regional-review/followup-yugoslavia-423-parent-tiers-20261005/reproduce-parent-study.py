#!/usr/bin/env python3
"""Reproduce the exact #1018 scoped parent/child source crosswalk.

This joins pinned #423 scope and assessments to retained geoBoundaries layers. It
checks identities, grouping, full source collection counts, and source feature
availability. It does not perform polygon overlay and does not infer legal
completeness or geography approval.
"""
import csv, hashlib, io, json, pathlib, subprocess, unicodedata
ROOT = pathlib.Path(__file__).resolve().parents[3]
OLD = ROOT / 'data/regional-review/regional-review-d282e62cf0209796'
OUT = pathlib.Path(__file__).resolve().parent / 'parent-study.json'
EXPECTED = {
'framework:province:ankaran-ancarano:3995388bc628',
'framework:province:bor-district:bcc3f7cd47cb',
'framework:province:branicevo-district:8cca74a50478',
'framework:province:izola-isola:bc2149bec285',
'framework:province:jablanica-district:e84aa5c8e2dd',
'framework:province:nisava-district:ac978fa5e54b',
'framework:province:pcinja-district:c70e78a0f661',
'framework:province:piran-pirano:1d929956088b',
'framework:province:pirot-district:ce075dca01df',
'framework:province:podunavlje-district:2b58b07c63e8',
'framework:province:pomoravlje-district:21d27b2672d2',
'framework:province:rasina-district:e0e6fad35903',
'framework:province:south-banat-district:b205db771f84',
'framework:province:toplica-district:05291e06d303',
'framework:province:vzhodna:d0d1788c155c',
'framework:province:zahodna-slovenija:52f5c9765039',
'framework:province:zajecar-district:9380a7a06e84',
}
def read(p): return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def digest(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def norm(s):
    s=unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().casefold()
    return ''.join(c for c in s if c.isalnum())
scope=read(OLD/'scope.json'); units=read(OLD/'unit-assessments.json'); provinces=read(OLD/'province-assessments.json')
rows=units['rows']; assessments=provinces['assessments']; ids=scope['member_location_ids']
world_index=read(ROOT/'data/world-index.json'); assert 'geography/part-22.json' in world_index['parts']
world_features=read(ROOT/'data/geography/part-22.json')['features']
world_by_id={f.get('id',f.get('properties',{}).get('id')):f for f in world_features if f.get('id',f.get('properties',{}).get('id')) in set(ids)}
assert len(world_by_id)==278
for r in rows:
    f=world_by_id[r['location_id']]; props=f.get('properties',{})
    assert props.get('parent_id')==r['parent_id'], f"Atlas parent mismatch for {r['location_id']}"
hierarchy=read(ROOT/'data/hierarchy.json'); hierarchy_by_id={x['id']:x for x in hierarchy}
area_id='framework:area:yugoslavia:cff5e9ba6c8e'
assert all(pid in hierarchy_by_id for pid in EXPECTED)
assert all(hierarchy_by_id[pid]['level']=='province' and hierarchy_by_id[pid]['parent_id']==area_id for pid in EXPECTED)
assert all(hierarchy_by_id[a['province_id']]['metadata']['child_count']==a['packet_member_count'] for a in assessments)
assert len(ids)==278 and len(set(ids))==278 and len(rows)==278
assert set(r['location_id'] for r in rows)==set(ids)
assert {a['province_id'] for a in assessments}==EXPECTED and len(assessments)==17
features={}
for code,level in [('SRB','ADM1'),('SRB','ADM2'),('SVN','ADM1'),('SVN','ADM2')]:
    p=OLD/f'source/geoboundaries-9469f09/geoBoundaries-{code}-{level}.geojson'
    fc=read(p)
    for f in fc['features']:
        sid=f['properties']['shapeID']; assert sid not in features
        features[sid]=(code,level,f['properties'])
assert len([r for r in rows if r['source_shape_id'] in features])==278
assert all(features[r['source_shape_id']][0:2]==(r['location_id'].split(':')[1], 'ADM2') for r in rows)
by_parent={}
for r in rows: by_parent.setdefault(r['parent_id'],[]).append(r)
assert set(by_parent)==EXPECTED
parent_names={a['province_id']:a['name'] for a in assessments}
source_parent_layers=[]
for key,code in [('SRB-ADM1','SRB'),('SVN-ADM1','SVN')]:
    p=OLD/f'source/geoboundaries-9469f09/geoBoundaries-{code}-ADM1.geojson'
    for f in read(p)['features']:
        source_parent_layers.append({'collection':key, **f['properties']})
source_children=[]
for key,code in [('SRB-ADM2','SRB'),('SVN-ADM2','SVN')]:
    p=OLD/f'source/geoboundaries-9469f09/geoBoundaries-{code}-ADM2.geojson'
    for f in read(p)['features']:
        source_children.append({'collection':key, **f['properties']})
parents=[]
for a in sorted(assessments,key=lambda x:x['province_id']):
    pid=a['province_id']; children=sorted(by_parent[pid],key=lambda x:x['location_id'])
    country='SRB' if pid in {r['parent_id'] for r in rows if r['location_id'].startswith('gb:SRB:')} else 'SVN'
    layer=f'{country}-ADM1'
    candidates=[x for x in source_parent_layers if x['collection']==layer and norm(x['shapeName'])==norm(a['name'])]
    child_records=[]
    for r in children:
        src=features[r['source_shape_id']]
        child_records.append({'id':r['location_id'],'name':r['name'],'source_collection':r['source_collection'],
            'source_shape_id':r['source_shape_id'],'source_shape_name':r['source_shape_name'],
            'source_parent_id':r['parent_id'],'source_parent_collection':r['province_source'],
            'role_finding':r['current_territorial_role_finding'],'boundary_finding':r['boundary_finding'],
            'feature_available_in_complete_retained_adm2_layer':True})
    parents.append({'parent_id':pid,'name':a['name'],'scoped_child_count':len(children),
        'scoped_child_ids':[x['id'] for x in child_records],'children':child_records,
        'source_parent_collection':a.get('source','geoBoundaries source assignment'),
        'matching_same_named_adm1_source_features':len(candidates),
        'matching_adm1_source_feature_ids':[x['shapeID'] for x in candidates],
        'source_parent_polygon_available_by_same_name':bool(candidates),
        'full_current_official_membership_proven':False,
        'packet_assessment':a['assessment'],'packet_unresolved':a['unresolved'],'packet_recommendation':a['recommendation']})
source_counts={}
for code,level in [('SRB','ADM1'),('SRB','ADM2'),('SVN','ADM1'),('SVN','ADM2')]:
    key=f'{code}-{level}'; p=OLD/f'source/geoboundaries-9469f09/geoBoundaries-{code}-{level}.geojson'
    fc=read(p); meta=read(OLD/f'source/geoboundaries-9469f09/geoBoundaries-{code}-{level}-metaData.json')
    source_counts[key]={'feature_count':len(fc['features']),'metadata_admUnitCount':int(meta['admUnitCount']),
       'metadata_boundary_year':meta['boundaryYear'],'boundary_type':meta['boundaryType'],
       'boundary_canonical':meta.get('boundaryCanonical'),'boundary_source':meta['boundarySource'],
       'license':meta['boundaryLicense'],'data_update_date':meta['sourceDataUpdateDate'],
       'build_date':meta['buildDate'],'geojson_sha256':digest(p),
       'metadata_sha256':digest(OLD/f'source/geoboundaries-9469f09/geoBoundaries-{code}-{level}-metaData.json')}
assert all(x['feature_count']==x['metadata_admUnitCount'] for x in source_counts.values())
svn_shapes=[f['properties'] for f in read(OLD/'source/geoboundaries-9469f09/geoBoundaries-SVN-ADM2.geojson')['features']]
from collections import Counter
svn_dups={n:sorted(x['shapeID'] for x in svn_shapes if norm(x['shapeName'])==n) for n,c in Counter(norm(x['shapeName']) for x in svn_shapes).items() if c>1}
# Reproduce the 53 exact location overlaps with #1016's retained official GURS history assessment.
name_path='data/regional-review/followup-yugoslavia-423-slovenia-names-20261005/2017-name-assessment.csv'
name_bytes=subprocess.check_output(['git','show',f'7646e0962afab6cc4f566439bb2f96890ae4b91e:{name_path}'],cwd=ROOT)
scoped_svn={r['location_id'] for r in rows if r['location_id'].startswith('gb:SVN:')}
name_rows=[r for r in csv.DictReader(io.StringIO(name_bytes.decode('utf-8'))) if r['location_id'] in scoped_svn]
assert len(name_rows)==53 and len({r['location_id'] for r in name_rows})==53
crosswalk_path=pathlib.Path(__file__).resolve().parent/'issue-1016-overlap.csv'
with crosswalk_path.open('w',encoding='utf-8',newline='') as f:
    w=csv.writer(f,lineterminator='\n'); w.writerow(['location_id','municipality_code','atlas_2017_reference_name','official_name_2017_01_01','official_name_2017_07_01','names_stable','historical_geometry_available'])
    for r in sorted(name_rows,key=lambda x:x['location_id']):
        w.writerow([r['location_id'],r['municipality_code'],r['atlas_2017_reference_name'],r['gurs_official_name_2017_01_01'],r['gurs_official_name_2017_07_01'],r['official_names_same_at_both_2017_dates'],'false'])
output={'version':1,'issue':1018,'baseline_commit':'7646e0962afab6cc4f566439bb2f96890ae4b91e',
 'atlas_repository_parent_check':{'world_index_sha256':digest(ROOT/'data/world-index.json'),'containing_feature_file':'data/geography/part-22.json','containing_file_sha256':digest(ROOT/'data/geography/part-22.json'),'subjects_found':len(world_by_id),'all_parent_ids_present_as_province_children_of_yugoslavia':True,'declared_child_counts_match_issue_scoped_count':True},
 'scope':{'issue_423_batch':scope['batch_id'],'location_count':len(ids),'parent_count':len(parents),'children_by_country':{'SRB':sum(r['location_id'].startswith('gb:SRB:') for r in rows),'SVN':sum(r['location_id'].startswith('gb:SVN:') for r in rows)},'member_location_ids_sha256':scope['member_location_ids_sha256'],
          'parent_count':len(parents),'parent_id_set_sha256':hashlib.sha256(json.dumps(sorted(EXPECTED),separators=(',',':')).encode()).hexdigest()},
 'source_collection_counts':source_counts,'parents':parents,'cross_packet_name_evidence':{'issue':1016,'candidate_rows_overlapping_scoped_SVN_ids':len(name_rows),'official_names_resolved_at_2017_01_01':sum(bool(r['gurs_official_name_2017_01_01']) for r in name_rows),'official_names_resolved_at_2017_07_01':sum(bool(r['gurs_official_name_2017_07_01']) for r in name_rows),'stable_between_dates':sum(r['official_names_same_at_both_2017_dates']=='True' for r in name_rows),'historical_geometry_available':False,'output':'issue-1016-overlap.csv','source_assessment_sha256':hashlib.sha256(name_bytes).hexdigest()},
 'source_roster_anomalies':{'SVN-ADM2_duplicate_normalized_names':svn_dups,
  'scope_members_for_duplicate_Maribor':[r['location_id'] for r in rows if 'Maribor' in r['name']],
  'note':'A second, 740 m2 2017 source feature named Maribor is outside the pinned 278 IDs. Current GURS has one Maribor municipality. This source anomaly is disclosed but out-of-scope for location identity changes.'},
 'overall_limits':['IDs and groups reproduce the pinned packet; source feature availability is checked by exact shapeID.',
 'No polygon clipping, union, intersection, or area comparison is performed here.',
 'Matching same-source collection counts and parent labels do not prove boundary correctness or current official completeness.',
 '2017 Serbia/Slovenia ADM2 polygons are OpenStreetMap-derived, not current national authoritative boundary vintages.',
 'Slovenia ADM1 is 2021 NUTS2/GISCO; same-named cohesion source geometries are not municipal provinces.',
 'Current GURS municipality/statistical-region geometries are retained in the prior packet but are not independently overlaid by this reproduction.',
 'Full current unit roster correspondence requires per-unit official registers and complete geometry crosswalks; issue packet offers current 212 GURS Slovenian municipality features and only RZS national aggregate counts for Serbia.'],
 'reproduction':{'script':pathlib.Path(__file__).name,'inputs':{
  'scope.json':digest(OLD/'scope.json'),'unit-assessments.json':digest(OLD/'unit-assessments.json'),
  'province-assessments.json':digest(OLD/'province-assessments.json')},
  'method':'Exact ID and source shapeID joins; same-name normalization for source parent feature availability; collection counts checked against retained metadata. No geometry predicate.'}}
encoded=json.dumps(output,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n'
OUT.write_text(encoded,encoding='utf-8')
print(f'wrote {OUT.relative_to(ROOT)} sha256={hashlib.sha256(encoded.encode()).hexdigest()} parents={len(parents)} children={sum(len(p["children"]) for p in parents)}')
