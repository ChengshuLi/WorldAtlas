"""Compare both original packages and selected output using immutable whole Git bodies.
Usage: python check-combined-conservation.py REPO BASE HEAD OUTPUT
No geographic producer, per-cell expansion or network request is performed.
"""
import collections, hashlib, json, os, pathlib, re, subprocess, sys
W, BASE, HEAD, OUTPUT = sys.argv[1:]
P = 'coordination/engineering/russia-angola-delivery-20261017/'
R = 'coordination/engineering/russia-repair-delivery-20261017/'
A = 'coordination/engineering/angola-repair-delivery-20261017/'
RH = 'ec8dd6711677fb77586441bbd5ef2d34488df2b6'
AH = '86b089e2b82a2e85264c96b11188854f2d1bce4a'
output = pathlib.Path(OUTPUT)
assert not os.path.lexists(output), 'Fresh output required'
assert output.parent.is_dir() and output.parent.resolve() == output.parent.absolute()
assert all(re.fullmatch('[a-f0-9]{40}', c) for c in [BASE, HEAD])
def raw(commit, name):
    return subprocess.check_output(['git', '-c', 'protocol.allow=never', '-C', W, 'show', commit + ':' + name])
def data(commit, name):
    return json.loads(raw(commit, name))
def pin_data(pin):
    body = raw(pin['commit'], pin['path'])
    assert len(body) == pin['bytes'] and hashlib.sha256(body).hexdigest() == pin['sha256']
    return json.loads(body)
def normal(rows):
    grouped = collections.defaultdict(list)
    for row in rows:
        grouped[row['y']].extend(row['runs'])
    result = []
    for y, runs in sorted(grouped.items()):
        merged = []
        for a, z, owner in sorted(runs):
            assert a < z
            assert not merged or a >= merged[-1][1], ('overlap', y, a, z, owner)
            if merged and a == merged[-1][1] and owner == merged[-1][2]:
                merged[-1][1] = z
            else:
                merged.append([a, z, owner])
        if merged:
            result.append({'y': y, 'runs': merged})
    return result

def owners(rows):
    counts = collections.Counter()
    for row in rows:
        for a, z, owner in row['runs']:
            counts[owner] += z - a
    return counts

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
selector = data(BASE, 'data/ownership-selection.json')
sidebody = raw(BASE, selector['additive_release']['path'])
assert len(sidebody) == selector['additive_release']['bytes'] and hashlib.sha256(sidebody).hexdigest() == selector['additive_release']['sha256']
side = json.loads(sidebody)
before = pin_data(side['logical_asset_map']['patch'])['rows']
prior_ledger = pin_data(side['logical_asset_map']['ledger'])
prior_registry = pin_data(side['authority_registry'])
russia_quartet = data(RH, R + 'config/compose.json')['authorities'][0]
angola_quartet = data(AH, A + 'config/conservative-authority-quartet.json')
assert data(HEAD, P + 'config/compose.json')['authorities'] == [russia_quartet, angola_quartet]
packages = []
all_original = []
all_supported = []
all_subjects = []
for name, h, prefix, quartet, held_path, expected in [
    ('Russia', RH, R, russia_quartet, 'native-partition-preaccept-001/held-native-patch.json', (2566967, 2557516, 9451, 334, 327, 66, 7)),
    ('Angola', AH, A, angola_quartet, 'conservative-002/held-native-rows.json', (170526, 141263, 29263, 47, 46, 28, 1))
]:
    original = data(h, prefix + 'source-stage/native-patch.json')['rows']
    supported = pin_data(quartet['native_patch'])['rows']
    held = data(h, prefix + held_path)['rows']
    assert normal(supported + held) == normal(original)
    oc, sc, hc = owners(original), owners(supported), owners(held)
    actual = (sum(oc.values()), sum(sc.values()), sum(hc.values()), len(oc), len(sc), len(hc), len(set(oc) - set(sc)))
    assert actual == expected, (name, actual)
    subjects = data(h, prefix + 'evidence-quality.json')['subject_ids']
    assert len(subjects) == len(set(subjects)) == len(oc)
    constructed = pin_data(quartet['ledger'])
    assert sum(row['native_cells'] for row in constructed['ledger_rows']) == sum(sc.values())
    for key in ('rule_preimage', 'source_authority'):
        pin_data(quartet[key])
    all_original += original
    all_supported += supported
    all_subjects += subjects
    packages.append(dict(zip(['name', 'requested_cells', 'supported_cells', 'held_cells', 'original_subjects', 'supported_owners', 'held_owners', 'wholly_held_owners'], [name, *actual]), per_owner=[{'owner':o,'requested':oc[o],'supported':sc[o],'held':hc[o]} for o in sorted(oc)]))
assert len(all_subjects) == len(set(all_subjects)) == 381
normal(before + all_original)
after = data(HEAD, P + 'composition-001/patch.json')['rows']
ledger = data(HEAD, P + 'composition-001/selected-ledger.json')
registry = data(HEAD, P + 'composition-001/authority-registry.json')
assert normal(after) == normal(before + all_supported)
for old, new in [(prior_ledger['rows'], ledger['rows']), (prior_registry['entries'], registry['entries'])]:
    assert not (collections.Counter(map(canonical, old)) - collections.Counter(map(canonical, new)))
def held_rows(rows):
    return [row for row in rows if row.get('disposition') not in ('assigned', 'zero-cell')]
assert collections.Counter(map(canonical, held_rows(prior_ledger['rows']))) == collections.Counter(map(canonical, held_rows(ledger['rows'])))
current = data(HEAD, 'data/ownership-selection.json')
assert {k:v for k,v in current.items() if k != 'additive_release'} == {k:v for k,v in selector.items() if k != 'additive_release'}
p0 = data(BASE, '.github/package-inputs.json')
p1 = data(HEAD, '.github/package-inputs.json')
assert {k:v for k,v in p0.items() if k != 'inputs'} == {k:v for k,v in p1.items() if k != 'inputs'}
assert p1['inputs'][:len(p0['inputs'])] == p0['inputs']
assert all(path.startswith((R, A, P)) for path in p1['inputs'][len(p0['inputs']):])
checkpoint = data(HEAD, 'data/selected-checkpoint.json')
assert checkpoint == data(RH, 'data/selected-checkpoint.json')
report = {'kind':'exact-combined-russia-angola-conservation','baseline_commit':BASE,'candidate_commit':HEAD,
    'packages':packages,'original_subjects':len(all_subjects),'requested_cells':sum(owners(all_original).values()),
    'supported_cells':sum(owners(all_supported).values()),'held_cells':sum(p['held_cells'] for p in packages),
    'prior_cells':sum(owners(before).values()),'proposed_cumulative_cells':sum(owners(after).values()),
    'removed_cells':0,'reassigned_cells':0,'prior_ledger_rows':len(prior_ledger['rows']),'proposed_ledger_rows':len(ledger['rows']),
    'prior_authorities':len(prior_registry['entries']),'proposed_authorities':len(registry['entries']),
    'prior_held_rows':len(held_rows(prior_ledger['rows'])),'proposed_held_rows':len(held_rows(ledger['rows'])),
    'literal_quartets_preserved':True,'literal_prior_rows_preserved':True,'literal_prior_authorities_preserved':True,
    'whole_original_packages_disjoint_from_each_other_and_prior_patch':True,'nonadditive_selector_unchanged':True,
    'package_declaration_prefix_preserved':True,'authenticated_greenland_locator_preserved':True,
    'limits':['Exact immutable interval and metadata comparison only; genuine selected-native and emitted asset/GPU/Canvas consumer checks remain mandatory.',
              'Both original scientific packages remain separately incomplete. Held intervals, source uncertainty, historical component questions and excluded companions receive no delivery credit.']}
assert (report['requested_cells'], report['supported_cells'], report['held_cells'], report['proposed_cumulative_cells']) == (2737493,2698779,38714,4908365)
with output.open('x') as f:
    json.dump(report,f,sort_keys=True,separators=(',',':')); f.write('\n')
print(json.dumps({k:v for k,v in report.items() if k != 'packages'}))
