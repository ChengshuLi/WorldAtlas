"""Reconcile every original Cuba key with the actual stock native authority.
Usage: python reconcile-authority.py REPO EXACT_INPUT_COMMIT FRESH_OUTPUT
This is accounting only; no source, physical or native science is replayed.
"""
import collections, gzip, hashlib, json, os, pathlib, re, subprocess, sys
assert len(sys.argv) == 4 and __debug__
W = pathlib.Path(sys.argv[1]).absolute()
C = sys.argv[2]
O = pathlib.Path(sys.argv[3]).absolute()
P = 'coordination/engineering/cuba-repair-delivery-20261017'
assert re.fullmatch('[0-9a-f]{40}', C)
assert O.parent.is_dir() and not O.exists()
assert all(not p.is_symlink() for p in (O, *O.parents))
inputs = []
ENV = {**os.environ, 'GIT_NO_LAZY_FETCH': '1', 'GIT_NO_REPLACE_OBJECTS': '1', 'GIT_TERMINAL_PROMPT': '0'}
def git(*args):
    return subprocess.check_output(['git', '-c', 'protocol.allow=never', '-C', str(W), *args], env=ENV)
def pin(path, commit=C):
    assert re.fullmatch('[0-9a-f]{40}', commit)
    assert not path.startswith('/') and '..' not in path.split('/')
    row = git('ls-tree', '-z', commit, '--', path).rstrip(b'\0')
    meta, name = row.split(b'\t')
    mode, kind, oid = meta.decode().split()
    assert mode == '100644' and kind == 'blob' and name.decode() == path
    size = int(git('cat-file', '-s', oid))
    body = git('cat-file', 'blob', oid)
    assert len(body) == size
    assert hashlib.sha1(b'blob ' + str(size).encode() + b'\0' + body).hexdigest() == oid
    return {'path': path, 'commit': commit, 'mode': mode, 'git_blob_oid': oid, 'bytes': size, 'sha256': hashlib.sha256(body).hexdigest()}, body
def read(name):
    descriptor, body = pin(P + '/' + name)
    inputs.append(descriptor)
    return json.loads(gzip.decompress(body) if name.endswith('.gz') else body)
def expand(rows):
    keys = set()
    count = 0
    for row in rows:
        assert isinstance(row['y'], int)
        for a, z, owner in row['runs']:
            assert all(isinstance(v, int) for v in (a, z, owner)) and 0 <= a < z
            for x in range(a, z):
                keys.add((row['y'], x, owner))
                count += 1
    assert len(keys) == count
    return keys
assert pin(P + '/probes/reconcile-authority.py')[1] == pathlib.Path(__file__).read_bytes()
rows = read('original-scope/original-intervals.json.gz')
scope = read('original-scope/scope-screen.json')
original = {}
for y, a, z, owners, source_indices, physical_class in rows:
    assert len(owners) == 1 and physical_class == 'land' and source_indices
    for x in range(a, z):
        key = y, x, owners[0]
        assert key not in original
        original[key] = physical_class
assert len(original) == 26459 and len(rows) == 8489
assert len({(y, x) for y, x, owner in original}) == len(original)
subjects = sorted(row['id'] for row in scope['owners'])
owner_ids = {row['index']: row['id'] for row in scope['owners']}
assert len(subjects) == len(set(subjects)) == len(owner_ids) == 87
assert set(owner_ids) == {k[2] for k in original}
patch = read('source-stage-001/original-native-patch.json')
requested_patch = read('native-config-001/native-requested-patch.json')
diagnostic = read('native-diagnostic-001/native-diagnostic.json')
assert patch == requested_patch
assert expand(patch['rows']) == expand(diagnostic['requested_rows']) == expand(diagnostic['supported_rows']) == original.keys()
assert diagnostic['held_rows'] == [] and diagnostic['held_cells'] == 0 and diagnostic['first_failure'] is None
assert diagnostic['requested_cells'] == diagnostic['supported_cells'] == len(original)
authority = read('native-authority-001/constructor-result.json')
binding = read('native-authority-001/authority-binding.json')
preimage = read('native-authority-001/original-rule-preimage.json')
rule_pin, rule_body = pin(P + '/native-authority-001/original-rule-preimage.json')
assert authority['kind'] == 'existing-source-target-native-constructor-result'
assert authority['rule_sha256'] == diagnostic['rule_sha256'] == hashlib.sha256(rule_body).hexdigest()
assert {**binding, 'kind': 'source-target-native-rule-v1'} == preimage
assert authority['component_ids'] == [row['component_id'] for row in authority['ledger_rows']]
component_keys = set()
components = set()
targets = set()
for row in authority['ledger_rows']:
    assert row['disposition'] == 'assigned' and row['component_id'] not in components
    components.add(row['component_id'])
    targets.add(row['target_id'])
    keys = expand(row['native_rows'])
    assert len(keys) == row['native_cells'] and {key[2] for key in keys} == {row['pixelIndex']}
    assert owner_ids[row['pixelIndex']] == row['target_id'] and not component_keys & keys
    component_keys |= keys
assert component_keys == original.keys() and len(components) == 87 and targets == set(subjects)
for role in ('native_patch', 'source_evidence'):
    actual, body = pin(binding[role]['path'], binding[role]['commit'])
    assert actual == binding[role]
    if role == 'native_patch':
        assert expand(json.loads(body)['rows']) == original.keys()
source = read('native-inputs-001/source-evidence.json')
physical = read('physical-001/whole-target-support.json')
source_scope = read('source-stage-001/source-scope-assessment.json')
foreign = read('source-review/foreign-bounds-001/complete-foreign-bounds.json')
periodic = read('source-review/periodic-negatives-001/retained-periodic-negative-reconciliation.json')
request = read('native-config-001/native-request-accounting.json')
assert len(source['targets']) == len(physical['results']) == 87
assert {t['id'] for t in source['targets']} == set(subjects)
assert all(t['territorial_exclusions'] == [] for t in source['targets'])
assert source_scope['whole_primary_features'] == 168 and source_scope['whole_context_features'] == 16
assert request['complete_Cuba_canonical_owners'] == 168 and request['complete_world_owner_ids'] == 49625
assert foreign['complete_foreign_families'] == periodic['complete_foreign_families'] == 366
assert foreign['complete_foreign_features'] == periodic['complete_foreign_features'] == 73383
assert foreign['unsupported_foreign_features'] == periodic['retained_periodic_frame_disjoint_features'] == 3
assert periodic['raw_whole_bounds_disjoint_features'] == 73380
assert periodic['unresolved_foreign_bound_features'] == foreign['selected_foreign_features'] == 0
issues = sum(len(row['issues']) for row in physical['results'])
issue_members = sum(bool(row['issues']) for row in physical['results'])
assert issues == 28 and issue_members == 17
counts = collections.Counter(key[2] for key in original)
owner_rows = [{'subject_id': owner_ids[owner], 'pixelIndex': owner, 'original_cells': count, 'qualified_cells': count, 'held_cells': 0, 'status': 'source-native-qualified'} for owner, count in sorted(counts.items())]
limits = [
    'Source-relative native qualification is not current-owner-zero, selected-bank conservation, emitted-consumer acceptance or accepted repair credit.',
    'All 26,459 original land cells, 8,489 original intervals and 87 original subjects are retained. The native partition has zero holds; source and review limits are not erased by that result.',
    'The complete consumed simplified CUB ADM2 product has 168 original features; CUB ADM1 has 16 contextual features. ODbL 1.0, represented 2017 and unknown original retrieval/effective dates remain explicit.',
    'The 366-family foreign corpus contains 73,383 complete original features, including ownerless features. 73,380 raw whole bounds are disjoint; three original Fiji periodic-coordinate failures are retained and reconciled only through exact previously retained periodic-frame and full-native-span evidence.',
    'No foreign family operand is needed for this exact source-relative Cuba scope within the retained corpus. No current sovereignty, Guantanamo status, territorial title or historical boundary sufficiency is inferred.',
    'All 87 whole physical members and all 28 geometric issues across 17 members remain retained. Native support is not current physical truth.',
    'Original issues 177 and 179 and separate ADM1 mapping and ADM2 physical-interpretation package obligations remain. No regional certificate, publication or historical import approval is supplied.',
    'Independent final source/native review and later selected delivery remain required.'
]
result = {'kind': 'complete-original-Cuba-native-authority-accounting', 'version': 1, 'input_commit': C,
    'original_cells': len(original), 'original_intervals': len(rows), 'original_subjects': len(subjects),
    'qualified_cells': len(component_keys), 'qualified_components': len(components), 'held_cells': 0,
    'source_hold_cells': 0, 'new_native_hold_cells': 0, 'whole_held_owners': 0,
    'original_physical_classes': {'land': 26459, 'inland-water': 0}, 'qualified_physical_classes': {'land': 26459, 'inland-water': 0}, 'held_physical_classes': {'land': 0, 'inland-water': 0},
    'original_request_diagnostic_and_authority_keys_exact': True, 'original_keys_exactly_partitioned': True,
    'subject_ids': subjects, 'owners': owner_rows, 'held_keys': [],
    'full_physical_members': len(physical['results']), 'physical_issues': issues, 'physical_members_with_issues': issue_members,
    'whole_primary_source_features': 168, 'whole_context_source_features': 16, 'qualified_source_members': 87,
    'complete_foreign_families': 366, 'complete_foreign_features': 73383, 'foreign_raw_bounds_disjoint_features': 73380,
    'foreign_retained_periodic_disjoint_features': 3, 'unresolved_foreign_bound_features': 0, 'foreign_negative_instances': 0,
    'inputs': inputs, 'limits': limits}
quartet = {'rule_preimage': rule_pin, 'source_authority': pin(P + '/native-authority-001/authority-binding.json')[0], 'ledger': pin(P + '/native-authority-001/constructor-result.json')[0], 'native_patch': binding['native_patch']}
handoff = {'kind': 'qualified-Cuba-original-native-authority-handoff', 'version': 1, 'input_commit': C,
    'original_cells': 26459, 'original_intervals': 8489, 'qualified_cells': 26459, 'explicit_held_cells': 0,
    'subject_ids': subjects, 'authorities': [quartet], 'qualified_owners': 87, 'limits': limits}
products = {'complete-native-authority-accounting.json': result, 'qualified-authority-handoff.json': handoff}
encoded = {name: (json.dumps(value, separators=(',', ':')) + '\n').encode() for name, value in products.items()}
O.mkdir()
for name, body in encoded.items():
    with (O / name).open('xb') as handle:
        handle.write(body)
print(json.dumps({key: result[key] for key in ('original_cells', 'original_intervals', 'original_subjects', 'qualified_cells', 'qualified_components', 'held_cells', 'original_request_diagnostic_and_authority_keys_exact')}))
