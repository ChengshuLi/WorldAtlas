#!/usr/bin/env python3
"""Validate pinned Nigeria issue scope, source archives, and generated table receipts."""
import ast, csv, gzip, hashlib, json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parents[2]
def sha(data): return hashlib.sha256(data).hexdigest()
def require_hash(data, expected):
    if sha(data) != expected: raise ValueError('hash mismatch')
def require_unique_assignment(rows):
    result = {}
    for sid, issue in rows:
        if sid in result: raise ValueError(f'duplicate assignment: {sid}')
        result[sid] = issue
    return result
def read_json(path): return json.loads(path.read_text())
def csv_rows(path):
    with path.open(encoding='utf-8', newline='') as f: return list(csv.DictReader(f))

scope = read_json(ROOT/'scope.json')
assert scope['issue_number'] == 477 and scope['location_count'] == 210
assert len(scope['member_location_ids']) == len(set(scope['member_location_ids'])) == 210
assert sha((ROOT/'issue-scope-pinned.json').read_bytes()) == scope['issue_scope_sha256']
assert sha((ROOT/'issue-scope-original.json').read_bytes()) == scope['issue_scope_source_json_sha256']
try:
    require_hash(b'negative hash control', sha(b'positive hash control'))
except ValueError:
    negative_hash_control = 'passed: modified input rejected'
else:
    raise AssertionError('negative hash control did not reject modified input')
baseline = scope['published_region_baseline']; commit = baseline['baseline_git_commit']
for path, expected in baseline['authoritative_snapshot_hashes'].items():
    actual = subprocess.check_output(['git','show',f'{commit}:{path}'],cwd=REPO)
    assert sha(actual) == expected, path
projection = json.loads(gzip.decompress(subprocess.check_output(['git','show',f"{commit}:{baseline['current_projection_snapshot']}"],cwd=REPO)))
baseline_subjects = {x['id']:x for x in projection['locations']}
assert set(scope['member_location_ids']) <= set(baseline_subjects)
for member in read_json(ROOT/'baseline-members.json'):
    assert member['id'] in baseline_subjects
    b = baseline_subjects[member['id']]
    assert member['parent_id'] == b['parent_id'] and member['parent_chain'] == b['parent_chain']

acq = read_json(ROOT/'acquisition.json')
source_objects_checked = 0
for source in acq['sources']:
    for retained in source.values():
        if not isinstance(retained,dict) or not {'file','gzip_bytes','gzip_sha256','restored_bytes','restored_sha256'} <= retained.keys(): continue
        raw = (ROOT/retained['file']).read_bytes()
        assert len(raw) == retained['gzip_bytes'] and sha(raw) == retained['gzip_sha256'], (source['id'],retained['file'])
        restored = gzip.decompress(raw)
        assert len(restored) == retained['restored_bytes'] and sha(restored) == retained['restored_sha256'], (source['id'],retained['file'])
        source_objects_checked += 1
wca = read_json(ROOT/'sources/inherited-wca-register.json')
for subset in wca['subsets']:
    raw=(ROOT/subset['subset_file']).read_bytes()
    assert len(raw)==subset['gzip_bytes'] and sha(raw)==subset['gzip_sha256'],subset['subset_file']
    restored=gzip.decompress(raw)
    assert len(restored)==subset['restored_bytes'] and sha(restored)==subset['restored_sha256'],subset['subset_file']
    original=subprocess.check_output(['git','show',f"{wca['ancestor_packet_baseline_commit']}:{subset['original_archive']}"],cwd=REPO)
    assert sha(original)==subset['original_archive_gzip_sha256'],subset['original_archive']
    source_objects_checked += 1

members = read_json(ROOT/'baseline-members.json')
assess = csv_rows(ROOT/'assessment.csv')
assert [r['id'] for r in assess] == [m['id'] for m in members]
assert all(ast.literal_eval(r['complete_baseline_parent_chain']) == m['parent_chain'] for r,m in zip(assess,members))
assert all(r['assessment_status'] in ('insufficient-evidence','correction-needed') for r in assess)
assert len(csv_rows(ROOT/'administrative-scope.csv')) == 10
scope_rows=csv_rows(ROOT/'administrative-scope.csv')
area_scope=next(r for r in scope_rows if r['scope_level']=='area')
assert json.loads(area_scope['related_followup_issue_ids']) == [755,756,757,759]
province_followups={r['name']:json.loads(r['related_followup_issue_ids']) for r in scope_rows if r['scope_level']=='province'}
assert province_followups['Nasarawa'] == [755,757,759]
assert province_followups['Kaduna'] == [755,756,759]
assert province_followups['Cross River'] == [755,756,759]
assert all(755 in followups and 759 in followups for followups in province_followups.values())
city_rows = csv_rows(ROOT/'city-name-spatial-screen.csv')
assert city_rows and all(('does not define an urban' in r['interpretation'] or 'does not establish urban' in r['interpretation']) for r in city_rows)
part = read_json(ROOT/'sibling-area-partition.json')
assign = {}
for item in part['issue_scopes']:
    raw = item['source_scope_json'].encode()
    assert sha(raw) == item['source_scope_json_sha256']
    full = json.loads(raw)['member_location_ids']
    assert full == item['member_location_ids']
    for sid in item['nigeria_member_location_ids']:
        assert sid not in assign, sid
        assign[sid] = item['issue_number']
try:
    require_unique_assignment([('duplicate-subject',475),('duplicate-subject',476)])
except ValueError:
    negative_partition_control = 'passed: duplicate owner rejected'
else:
    raise AssertionError('negative sibling partition control did not reject overlap')
assert len(assign) == 774
assert sum(issue == 477 for issue in assign.values()) == 210
assert {sid for sid,issue in assign.items() if issue == 477} == set(scope['member_location_ids'])
published_nigeria={x['id'] for x in projection['locations'] if x.get('region_id')==scope['region_id'] and x.get('owner')=='Nigeria'}
assert set(assign) == published_nigeria
area = csv_rows(ROOT/'area-partition-inventory.csv')
assert len(area) == 774 and {r['location_id'] for r in area} == set(assign)
assert {r['location_id']:int(r['review_issue']) for r in area} == assign
groups=csv_rows(ROOT/'administrative-scope.csv')
for province in scope['province_scopes']:
    row=next(r for r in groups if r['scope_level']=='province' and r['scope_id']==province['id'])
    expected={m['id'] for m in members if m['parent_id']==province['id']}
    assert int(row['baseline_full_location_count'])==province['full_province_locations']
    assert int(row['owned_location_count'])==len(expected)
    assert set(json.loads(row['owned_subject_ids']))==expected

ledger = read_json(ROOT/'generated-data-accounting.json')
for row in ledger['outputs']:
    data = (ROOT/row['path']).read_bytes()
    assert len(data) == row['bytes'] and sha(data) == row['sha256'], row['path']
    with (ROOT/row['path']).open(encoding='utf-8',newline='') as f: count = sum(1 for _ in csv.reader(f))-1
    assert count == row['rows_excluding_header'], row['path']
assert {'assessment.csv','area-partition-inventory.csv'} <= {r['path'] for r in ledger['outputs']}
access_limits=read_json(ROOT/'sources/access-limitations.json')
assert access_limits['fresh_external_access_recheck_performed'] is False
print(json.dumps({'status':'passed','issue':477,'subjects':len(assess),'area_partition':len(area),'capital_point_screen_rows':len(city_rows),'retained_source_objects_checked':source_objects_checked,'generated_outputs_checked':len(ledger['outputs']),'negative_controls':[negative_hash_control,negative_partition_control]},indent=2))

if '--rebuild' in sys.argv:
    output_paths = [r['path'] for r in ledger['outputs']]
    def run_and_hash():
        subprocess.run([sys.executable,str(ROOT/'build_assessment.py')],check=True,cwd=REPO)
        return {name:sha((ROOT/name).read_bytes()) for name in output_paths}
    first = run_and_hash(); second = run_and_hash()
    assert first == second, 'builder outputs are not deterministic across two runs'
    print(json.dumps({'status':'reproduced','run_one_sha256':sha(json.dumps(first,sort_keys=True).encode()),'run_two_sha256':sha(json.dumps(second,sort_keys=True).encode())},indent=2))
