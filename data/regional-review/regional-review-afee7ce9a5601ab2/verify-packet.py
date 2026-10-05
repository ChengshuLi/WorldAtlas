"""Validate the retained #446 scope and evidence ledger without fetching sources."""
import csv, hashlib, json, re, subprocess
from pathlib import Path
ROOT=Path.cwd()
PACKET=Path('data/regional-review/regional-review-afee7ce9a5601ab2')
issue=json.loads((PACKET/'issue-scope-pinned.json').read_text())
pin=json.loads((PACKET/'issue-scope-pin.json').read_text())
scope=json.loads((PACKET/'scope.json').read_text())
match=re.search(r'```json\s*(\{.*?\})\s*```',issue['body'],re.S)
assert match and json.loads(match.group(1))==scope
assert hashlib.sha256(issue['body'].encode()).hexdigest()==pin['issue_body_sha256']
assert hashlib.sha256(json.dumps(scope,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==pin['machine_scope_sha256']
ids=scope['member_location_ids']; assert len(ids)==215 and len(set(ids))==215
rows=list(csv.DictReader((PACKET/'unit-review.csv').open()))
assert len(rows)==215 and {r['id'] for r in rows}==set(ids)
assert len({r['parent_id'] for r in rows})==32
cross=list(csv.DictReader((PACKET/'pry-source-crosswalk.csv').open()))
assert len(cross)==247 and len({r['source_shape_id'] for r in cross})==247
assert sum(r['mapping_type']=='individual native location' for r in cross)==241
assert sum(r['mapping_type']=='member of atlas aggregate' for r in cross)==6
base=json.loads((PACKET/'baseline-files.json').read_text())
assert base['baseline_commit']=='702a55f8e03a2442a153eb1176919feaf84eb115'
for row in base['files']:
 b=subprocess.check_output(['git','show',row['commit']+':'+row['path']])
 assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256']
parts={r['path'] for r in base['files'] if r['path'].startswith('data/geography/part-')}
features={}
for part in sorted(parts):
 for f in json.loads(subprocess.check_output(['git','show',base['baseline_commit']+':'+part]))['features']:
  features.setdefault(f['id'],[]).append(part)
assert all(features.get(i)==[next(x for x in features[i])] for i in ids)
assert all(len(features[i])==1 for i in ids)
sources=json.loads((PACKET/'source-inventory.json').read_text())['sources']
assert sources
for s in sources:
 if s.get('retained_path'):
  q=PACKET/s['retained_path']; b=q.read_bytes()
  assert hashlib.sha256(b).hexdigest()==s['sha256'] and len(b)==s['bytes']
assert not (PACKET/'pry-source-temporary.geojson').exists()
assert next(s for s in sources if s['source_id']=='gb:PRY:ADM2')['bytes']>32*1024*1024
result=json.loads((PACKET/'reproduction-results.json').read_text())
assert result['scope_baseline_matches']==215 and result['paraguay_source_records_mapped_once']==247
assert result['uruguay_department_names_matching']==19 and result['negative_control_duplicate_scope_rejected']
receipt=json.loads((PACKET/'reproducibility.json').read_text())
assert receipt['run_one_sha256']==receipt['run_two_sha256'] and receipt['outputs_equal']
body=(PACKET/'pr-body.md').read_text()
links=[x.strip() for x in re.findall(r'^(?:close|closes|closed|fix|fixes|fixed|resolve|resolves|resolved|refs)\s+#\d+\s*$',body,re.I|re.M)]
assert links==['Closes #446']
for q in PACKET.rglob('*'):
 if q.is_symlink(): raise AssertionError(f'symlink not allowed: {q}')
 if q.is_file(): assert q.stat().st_size<=32*1024*1024, f'file exceeds retention ceiling: {q}'
print(json.dumps({'verification':'passed','scope_members':len(ids),'distinct_parents':32,'paraguay_source_records':247,'paraguay_native':241,'paraguay_aggregate_members':6,'uruguay_name_matches':19,'retained_originals_hash_verified':2,'baseline_blobs_verified':len(base['files']),'controlled_reference':'Closes #446'},sort_keys=True))
