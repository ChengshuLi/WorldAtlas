"""Reconcile every original Denmark key with the actual stock native authority.
Usage: python reconcile-authority.py REPO EXACT_INPUT_COMMIT FRESH_OUTPUT
This is accounting only; no source, physical or native science is replayed.
"""
import collections, gzip, hashlib, json, os, pathlib, re, subprocess, sys
assert len(sys.argv) == 4 and __debug__
W = pathlib.Path(sys.argv[1]).absolute()
C = sys.argv[2]
O = pathlib.Path(sys.argv[3]).absolute()
P = 'coordination/engineering/denmark-repair-delivery-20261017'
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
    assert len(owners) == 1 and physical_class in ('land','inland-water') and source_indices
    for x in range(a, z):
        key = y, x, owners[0]
        assert key not in original
        original[key] = physical_class
assert len(original) == 27783 and len(rows) == 7471
assert len({(y, x) for y, x, owner in original}) == len(original)
subjects = sorted(row['id'] for row in scope['owners'])
owner_ids = {row['index']: row['id'] for row in scope['owners']}
assert len(subjects) == len(set(subjects)) == len(owner_ids) == 69
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
assert component_keys == original.keys() and len(components) == 69 and targets == set(subjects)
for role in ('native_patch', 'source_evidence'):
    actual, body = pin(binding[role]['path'], binding[role]['commit'])
    assert actual == binding[role]
    if role == 'native_patch':
        assert expand(json.loads(body)['rows']) == original.keys()
source = read('native-inputs-001/source-evidence.json')
physical = read('physical-001/whole-target-support.json')
source_scope = read('source-stage-001/source-scope-assessment.json')
foreign = read('source-review/foreign-bounds-002/complete-foreign-bounds.json')
periodic = read('source-review/periodic-negatives-001/retained-periodic-negative-reconciliation.json')
request = read('native-config-001/native-request-accounting.json')
assert len(source['targets']) == len(physical['results']) == 69
assert {t['id'] for t in source['targets']} == set(subjects)
negative_instances = sum(len(t['territorial_exclusions']) for t in source['targets'])
assert negative_instances > 0
negative_provenance = read('native-inputs-001/territorial-exclusion-provenance.json')
assert set(negative_provenance['negative_families']) == set(foreign['whole_bounds_candidate_families'])
assert sum(len(t['exclusions']) for t in negative_provenance['targets']) == negative_instances
assert source_scope['whole_primary_features'] == 98 and source_scope['whole_context_features'] == 5
assert request['complete_Denmark_canonical_owners'] == 98 and request['complete_world_owner_ids'] == 49625
assert foreign['complete_foreign_families'] == periodic['complete_foreign_families'] == 366
assert foreign['complete_foreign_features'] == periodic['complete_foreign_features'] == 73464
assert foreign['unsupported_foreign_features'] == periodic['retained_periodic_frame_disjoint_features'] == 3
assert periodic['raw_whole_bounds_disjoint_features'] == 73449
assert periodic['unresolved_foreign_bound_features'] == 0 and foreign['selected_foreign_features'] == 12
issues = sum(len(row['issues']) for row in physical['results'])
issue_members = sum(bool(row['issues']) for row in physical['results'])
assert issues == 71 and issue_members > 0
counts = collections.Counter(key[2] for key in original)
owner_rows = [{'subject_id': owner_ids[owner], 'pixelIndex': owner, 'original_cells': count, 'qualified_cells': count, 'held_cells': 0, 'status': 'source-native-qualified'} for owner, count in sorted(counts.items())]
limits = [
    'All 27783 original cells, 7471 intervals, 69 owners and both original physical classes remain in the exact request/diagnostic/authority partition. Native held cells are zero.',
    'Source-relative qualification is not current-owner-zero, selected conservation, emitted-consumer acceptance or accepted map credit.',
    'Complete primary 98-feature and contextual 5-feature originals, their distinct represented 2018/2021 metadata and licensing declarations remain retained; incomplete upstream Wikimedia citation is explicitly limited in source-fitness.json.',
    'All 73464 complete foreign originals were screened without owner filtering. Twelve overlapping originals in five full German/Swedish families remain stock negative operands; three Fiji frame exceptions are explicitly reconciled against retained proof.',
    'All 69 whole physical members and all 71 geometric issues remain retained. Native support does not establish current physical truth.',
    'Nordic333/332, every-island and parent-region semantic obligations and separate mapping/physical companions remain open. Independent final review and selected integration remain required.'
]
result = {'kind': 'complete-original-Denmark-native-authority-accounting', 'version': 1, 'input_commit': C,
    'original_cells': len(original), 'original_intervals': len(rows), 'original_subjects': len(subjects),
    'qualified_cells': len(component_keys), 'qualified_components': len(components), 'held_cells': 0,
    'source_hold_cells': 0, 'new_native_hold_cells': 0, 'whole_held_owners': 0,
    'original_physical_classes': dict(collections.Counter(original.values())), 'qualified_physical_classes': dict(collections.Counter(original.values())), 'held_physical_classes': {'land': 0, 'inland-water': 0},
    'original_request_diagnostic_and_authority_keys_exact': True, 'original_keys_exactly_partitioned': True,
    'subject_ids': subjects, 'owners': owner_rows, 'held_keys': [],
    'full_physical_members': len(physical['results']), 'physical_issues': issues, 'physical_members_with_issues': issue_members,
    'whole_primary_source_features': 98, 'whole_context_source_features': 5, 'qualified_source_members': 69,
    'complete_foreign_families': 366, 'complete_foreign_features': 73464, 'foreign_raw_bounds_disjoint_features': 73449,
    'foreign_retained_periodic_disjoint_features': 3, 'unresolved_foreign_bound_features': 0, 'foreign_negative_instances': negative_instances,
    'inputs': inputs, 'limits': limits}
quartet = {'rule_preimage': rule_pin, 'source_authority': pin(P + '/native-authority-001/authority-binding.json')[0], 'ledger': pin(P + '/native-authority-001/constructor-result.json')[0], 'native_patch': binding['native_patch']}
handoff = {'kind': 'qualified-Denmark-original-native-authority-handoff', 'version': 1, 'input_commit': C,
    'original_cells': 27783, 'original_intervals': 7471, 'qualified_cells': 27783, 'explicit_held_cells': 0,
    'subject_ids': subjects, 'authorities': [quartet], 'qualified_owners': 69, 'limits': limits}
products = {'complete-native-authority-accounting.json': result, 'qualified-authority-handoff.json': handoff}
encoded = {name: (json.dumps(value, separators=(',', ':')) + '\n').encode() for name, value in products.items()}
O.mkdir()
for name, body in encoded.items():
    with (O / name).open('xb') as handle:
        handle.write(body)
print(json.dumps({key: result[key] for key in ('original_cells', 'original_intervals', 'original_subjects', 'qualified_cells', 'qualified_components', 'held_cells', 'original_request_diagnostic_and_authority_keys_exact')}))
