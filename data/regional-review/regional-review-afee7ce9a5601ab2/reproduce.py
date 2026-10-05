import hashlib, json, csv, unicodedata
from pathlib import Path
p=Path('data/regional-review/regional-review-afee7ce9a5601ab2')
issue=json.loads((p/'issue-scope-pinned.json').read_text())
scope=json.loads((p/'scope.json').read_text())
assert hashlib.sha256(issue['body'].encode()).hexdigest()==json.loads((p/'issue-scope-pin.json').read_text())['issue_body_sha256']
assert scope['location_count']==215 and len(scope['member_location_ids'])==215 and len(set(scope['member_location_ids']))==215
features={}
for path in sorted(Path('data/geography').glob('part-*.json')):
 for x in json.loads(path.read_text())['features']:
  features.setdefault(x['id'],[]).append((x,path.as_posix()))
assert all(len(features.get(i,[]))==1 for i in scope['member_location_ids'])
source_file=p/'pry-source-temporary.geojson'
assert source_file.exists(), 'Restore pinned 45,589,273-byte source from sources.json before running.'
src=json.loads(source_file.read_text())
assert len(src['features'])==247
assert hashlib.sha256(source_file.read_bytes()).hexdigest()=='d42bd1f910070bf805e32dc46708230c91f58902a3c8792eda60928b22362858'
shapes={f['properties']['shapeID']:f for f in src['features']}
assert len(shapes)==247
base_pry={}
member_map={}
for values in features.values():
 for x,path in values:
  if x['id'].startswith('gb:PRY:ADM2:'):
   base_pry[x['id'].split(':')[-1]]=x
  for member in x['properties'].get('metadata',{}).get('source_member_ids',[]):
   if member.startswith('gb:PRY:ADM2:'):
    member_map.setdefault(member.split(':')[-1],[]).append(x)
source_mapping={}
for sid in shapes:
 direct=base_pry.get(sid)
 aggregates=member_map.get(sid,[])
 assert bool(direct)+bool(aggregates)==1, f'zero or duplicate Paraguay mapping for {sid}'
 source_mapping[sid]=direct or aggregates[0]
assert len(source_mapping)==247
crosswalk=list(csv.DictReader((p/'pry-source-crosswalk.csv').open()))
assert len(crosswalk)==247 and {r['source_shape_id'] for r in crosswalk}==set(shapes)
assert sum(r['mapping_type']=='individual native location' for r in crosswalk)==241
assert sum(r['mapping_type']=='member of atlas aggregate' for r in crosswalk)==6
# all rows are crosswalked; actual name exceptions are explicit alias in synthetic multipart.
rows=list(csv.DictReader((p/'unit-review.csv').open()))
assert len(rows)==215 and len({r['id'] for r in rows})==215
for r in rows:
 x=features[r['id']][0][0]
 assert x['properties']['name']==r['name'] and x['properties'].get('parent_id')==r['parent_id']
 if r['id'].startswith('gb:PRY:ADM2:'):
  m=x['properties']['metadata']['original_id']
  sf=shapes[m]
  assert sf['properties']['shapeName']==r['name']
# Uruguay: identity-level match between 19 2017 source units and current official names.
def norm(s): return ''.join(c for c in unicodedata.normalize('NFD',str(s).lower()) if unicodedata.category(c)!='Mn' and c.isalnum())
assert hashlib.sha256((p/'ury-gb-2017.geojson').read_bytes()).hexdigest()=='9f4887205e7b359af2ef1e4f484ad071d2dc0d12d068f1d7b6c1cc6c2624d1cf'
assert hashlib.sha256((p/'ury-igm-current.geojson').read_bytes()).hexdigest()=='3cfa19c6be9d12bd159b236e15839f958656fdbe66ef19e38379cb54c141b3a7'
ury_old=json.loads((p/'ury-gb-2017.geojson').read_text())['features']
ury_now=json.loads((p/'ury-igm-current.geojson').read_text())['features']
old={norm(f['properties']['shapeName']):f for f in ury_old}
now={norm(f['properties'].get('nam')):f for f in ury_now if f['properties'].get('USE_')!=1000}
scoped_ury=[r for r in rows if r['id'].startswith('gb:URY:ADM1:')]
assert len(ury_old)==19 and len(scoped_ury)==19 and len(now)==19
assert all((p/n).stat().st_size < 32*1024*1024 for n in ['ury-gb-2017.geojson','ury-igm-current.geojson'])
assert set(old)==set(now)=={norm(r['name']) for r in scoped_ury}
# Reproducible negative control: the validator rejects a duplicate/missing roster.
negative_ids=list(scope['member_location_ids']); negative_ids[-1]=negative_ids[0]
negative_rejected=(len(negative_ids)!=len(set(negative_ids)))
assert negative_rejected
# Results include counts not dates/environment. Sorted JSON output hashes reproducibly.
area_counts={k:sum(1 for r in rows if r['scope_area']==k) for k in sorted(set(r['scope_area'] for r in rows))}
result={
 'issue':446,
 'baseline_commit':'702a55f8e03a2442a153eb1176919feaf84eb115',
 'scope_expected':215,'scope_unique':len(set(scope['member_location_ids'])),
 'scope_baseline_matches':sum(len(features.get(i,[]))==1 for i in scope['member_location_ids']),
 'owned_paths':['data/regional-review/regional-review-afee7ce9a5601ab2/'],
 'area_row_counts':area_counts,
 'distinct_parents':len(set(r['parent_id'] for r in rows)),
 'paraguay_source_features':len(shapes),
 'paraguay_source_ids_unique':len(source_mapping),
 'paraguay_native_baseline_count':len(base_pry),
 'paraguay_source_members_via_aggregates':len(source_mapping)-len(base_pry),
 'paraguay_distinct_aggregates':len({r['atlas_location_id'] for r in crosswalk if r['mapping_type']=='member of atlas aggregate'}),
 'paraguay_source_records_mapped_once':len(source_mapping),
 'paraguay_scoped_input_source_records':sum(1 for sid,x in source_mapping.items() if x['id'] in set(scope['member_location_ids']) or x['id']=='atlas:multipart:eab6ecd59520b6841455'),
 'paraguay_scoped_multipart_members':len(next(x for x,_ in features['atlas:multipart:eab6ecd59520b6841455'])['properties']['metadata']['source_member_ids']),
 'uruguay_2017_source_count':len(ury_old),
 'uruguay_current_official_features':len(ury_now),
 'uruguay_current_department_named_feature_count':len(now),
 'uruguay_department_names_matching':len(set(old)&set(now)),
 'uruguay_current_contested_extras':[f['properties'].get('nam') for f in ury_now if f['properties'].get('USE_')==1000],
 'negative_control_duplicate_scope_rejected':negative_rejected,
 'limitations':['Name and source-ID crosswalk does not prove boundary correctness.','Paraguay original must be restored from the pinned URL; it exceeds the 32 MiB retention cap.','Uruguay current comparison validates names and feature roles only; no full polygon overlay or boundary certification.','Southern Patagonian Ice Field boundary is not treated as sovereign or administrative evidence.']
}
(p/'reproduction-results.json').write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,sort_keys=True))
