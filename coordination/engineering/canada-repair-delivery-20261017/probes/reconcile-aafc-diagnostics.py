#!/usr/bin/env python3
"""Reconcile immutable stock AAFC diagnostics to every original Canada key.

This verifies diagnostic accounting only. It emits no native authority or selected
ownership claim. The original six-column records remain the normative inventory.
"""
import argparse, gzip, hashlib, json, subprocess
from collections import Counter
from pathlib import Path

P = 'coordination/engineering/canada-repair-delivery-20261017/'
a = argparse.ArgumentParser()
a.add_argument('--repo', required=True)
a.add_argument('--input-commit', required=True)
a.add_argument('--output', required=True)
a.add_argument('--include-authorities', action='store_true')
args = a.parse_args()
repo = Path(args.repo).resolve()
assert len(args.input_commit) == 40 and all(c in '0123456789abcdef' for c in args.input_commit)
inputs = []

def read(name):
    path = P + name
    raw = subprocess.check_output(['git', '-c', 'protocol.allow=never', '-C', str(repo), 'show', args.input_commit + ':' + path])
    inputs.append({'commit': args.input_commit, 'path': path, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
    return json.loads(gzip.decompress(raw) if path.endswith('.gz') else raw)

def expand(rows):
    result = set()
    count = 0
    for row in rows:
        for lo, hi, owner in row['runs']:
            assert isinstance(owner, int) and 0 <= lo < hi
            for x in range(lo, hi):
                count += 1
                result.add((row['y'], x, owner))
    assert len(result) == count, 'Duplicate native requested/support keys'
    return result

package = read('frozen-original-001/package.json')
paths = subprocess.check_output(['git', '-C', str(repo), 'ls-tree', '-r', '--name-only', args.input_commit, '--', P + 'frozen-original-001/']).decode().splitlines()
original, intervals = {}, 0
for path in paths:
    if not path.endswith('.json.gz'):
        continue
    for y, lo, hi, owners, competitors, physical in read(path[len(P):]):
        assert len(owners) == 1 and isinstance(competitors, list)
        intervals += 1
        for x in range(lo, hi):
            key = (y, x, owners[0])
            assert key not in original, 'Duplicate original key'
            original[key] = physical
assert len(original) == package['native_cells'] == 438062
assert intervals == package['interval_segments'] == 139042
assert len({k[2] for k in original}) == len(package['owners']) == 209
assert Counter(original.values()) == {'land': 375635, 'inland-water': 62427}
app = read('aafc-native-operands-001/applicability-decision.json')
source_holds = {(r['y'], r['x'], r['owner']): r['reason'] for r in app['held']}
assert len(source_holds) == len(app['held']) == 103
assert source_holds.keys() <= original.keys()
physical_owners = set()
for batch in app['batches']:
    assert not physical_owners.intersection(batch['owners']), 'Repeated owner across native batches'
    physical_owners.update(batch['owners'])
assert len(physical_owners) == 72
physical_original = {k for k in original if k[2] in physical_owners}
physical_source_holds = set(source_holds) & physical_original
assert len(physical_original) == 144097 and len(physical_source_holds) == 50
supported, held, requested, observations = set(), set(), set(), []
for i, batch in enumerate(app['batches'], 1):
    b = f'{i:03d}'
    request = expand(read(f'aafc-native-operands-001/batch-{b}/requested-native-patch.json')['rows'])
    diag = read(f'aafc-native-diagnostic-{b}/native-diagnostic.json')
    assert diag['kind'] == 'source-target-native-diagnostic-v1'
    assert request == expand(diag['requested_rows'])
    good, bad = expand(diag['supported_rows']), expand(diag['held_rows'])
    assert not good & bad and good | bad == request
    assert len(request) == diag['requested_cells'] == batch['cells']
    assert len(good) == diag['supported_cells'] and len(bad) == diag['held_cells']
    assert not requested & request
    requested.update(request); supported.update(good); held.update(bad)
    observations.append({'batch': b, 'requested_cells': len(request), 'supported_cells': len(good), 'held_cells': len(bad)})
assert requested == physical_original - physical_source_holds
assert not supported.intersection(source_holds) and not held.intersection(source_holds)
admin_pending = original.keys() - physical_original - source_holds.keys()
assert len(admin_pending) == 293912
assert set(original) == supported | held | source_holds.keys() | admin_pending
qualified = set()
if args.include_authorities:
    components = set()
    for i in range(1, 6):
        b = f'{i:03d}'
        authority = read(f'aafc-native-authority-{b}/constructor-result.json')
        diag = read(f'aafc-native-diagnostic-{b}/native-diagnostic.json')
        assert authority['kind'] == 'existing-source-target-native-constructor-result'
        assert authority['rule_sha256'] == diag['rule_sha256']
        keys = set()
        assert authority['component_ids'] == [r['component_id'] for r in authority['ledger_rows']]
        for row in authority['ledger_rows']:
            assert row['disposition'] == 'assigned' and row['component_id'] not in components
            components.add(row['component_id'])
            members = expand(row['native_rows'])
            assert len(members) == row['native_cells'] and {k[2] for k in members} == {row['pixelIndex']}
            assert not keys & members
            keys.update(members)
        assert keys == expand(diag['supported_rows'])
        assert not qualified & keys
        qualified.update(keys)
    assert qualified == supported and len(components) == 72
categories = {('native_authority_qualified' if args.include_authorities else 'native_diagnostic_supported'): supported, 'native_diagnostic_held': held,
              'explicit_source_hold': set(source_holds), 'administrative_native_pending': admin_pending}
for name, keys in categories.items():
    for other, other_keys in categories.items():
        if name != other:
            assert not keys & other_keys
result = {'kind': ('complete-original-Canada-AAFC-authority-accounting' if args.include_authorities else 'complete-original-Canada-AAFC-diagnostic-accounting'), 'version': 1,
          'input_commit': args.input_commit, 'original_cells': len(original), 'original_intervals': intervals,
          'original_targets': 209, 'physical_original_cells': len(physical_original),
          'physical_source_holds': len(physical_source_holds), 'batches': observations,
          'categories': {name: {'cells': len(keys), 'physical_classes': dict(sorted(Counter(original[k] for k in keys).items())),
                               'targets': len({k[2] for k in keys})} for name, keys in categories.items()},
          'source_hold_reasons': dict(sorted(Counter(source_holds.values()).items())),
          'inputs': inputs, 'limits': [('Constructor qualification is not current-owner-zero or selected-output acceptance.' if args.include_authorities else 'Diagnostic accounting is not native authority, current-owner-zero or selected-output acceptance.'),
                                      'The complete original denominator is unchanged; administrative native work remains pending.']}
output = Path(args.output)
with output.open('x') as f:
    json.dump(result, f, indent=2, ensure_ascii=False); f.write('\n')
print(json.dumps({k: v for k, v in result.items() if k in ['original_cells','physical_original_cells','physical_source_holds','categories']}))
