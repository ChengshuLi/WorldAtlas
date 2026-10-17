"""Authenticate complete original packages and exact interval conservation without polygons.
Usage: python check-combined-conservation.py REPO BASE HEAD plan|final FRESH_OUTPUT
Bounded whole Git reads only; no network, per-cell expansion, geometry edits or science replay.
"""
import collections, hashlib, json, os, pathlib, re, subprocess, sys
W, BASE, HEAD, MODE, OUTPUT = sys.argv[1:]
assert MODE in ('plan', 'final')
output = pathlib.Path(OUTPUT)
assert not os.path.lexists(output), 'Fresh output required'
assert output.parent.is_dir() and output.parent.resolve() == output.parent.absolute(), 'Ordinary existing output parent required'
assert all(re.fullmatch('[a-f0-9]{40}', c) for c in [BASE, HEAD])
P = 'coordination/engineering/russia-angola-japan-delivery-20261017/'
R = 'coordination/engineering/russia-repair-delivery-20261017/'
A = 'coordination/engineering/angola-repair-delivery-20261017/'
J = 'coordination/engineering/japan-native-repair-20261017/'
RH = 'ec8dd6711677fb77586441bbd5ef2d34488df2b6'
AH = '86b089e2b82a2e85264c96b11188854f2d1bce4a'
JH = 'c76c45be06853204183bad2b858081ef37bd8d40'
MAX_FILE = 64 * 1024**2
MAX_TOTAL = 256 * 1024**2
inputs = {}
def raw(commit, name):
    assert re.fullmatch('[a-f0-9]{40}', commit)
    assert not name.startswith('/') and all(p not in ('', '.', '..') for p in name.split('/'))
    row = subprocess.check_output(['git', '-c', 'protocol.allow=never', '-C', W, 'ls-tree', '-z', commit, '--', name]).rstrip(b'\0')
    meta, actual_name = row.split(b'\t'); mode, kind, oid = meta.decode().split()
    assert actual_name.decode() == name and mode == '100644' and kind == 'blob'
    size = int(subprocess.check_output(['git', '-c', 'protocol.allow=never', '-C', W, 'cat-file', '-s', oid]))
    assert 0 <= size <= MAX_FILE
    key = commit + ':' + name
    assert sum(x['bytes'] for x in inputs.values()) + (size if key not in inputs else 0) <= MAX_TOTAL
    body = subprocess.check_output(['git', '-c', 'protocol.allow=never', '-C', W, 'cat-file', 'blob', oid])
    assert len(body) == size and hashlib.sha1(('blob '+str(size)+'\0').encode()+body).hexdigest() == oid
    desc = dict(commit=commit, path=name, mode=mode, git_blob_oid=oid, bytes=size, sha256=hashlib.sha256(body).hexdigest())
    assert key not in inputs or inputs[key] == desc
    inputs[key] = desc
    return body

def data(commit, name):
    return json.loads(raw(commit, name))
def pin_data(pin):
    body = raw(pin['commit'], pin['path']); actual = inputs[pin['commit']+':'+pin['path']]
    assert all(actual[k] == v for k,v in pin.items() if k in actual)
    assert len(body) == pin['bytes'] and hashlib.sha256(body).hexdigest() == pin['sha256']
    return json.loads(body)
def normal(rows):
    grouped = collections.defaultdict(list)
    for row in rows:
        assert type(row['y']) is int
        grouped[row['y']].extend(row['runs'])
    result = []
    for y, runs in sorted(grouped.items()):
        merged = []
        for a, z, owner in sorted(runs):
            assert all(type(v) is int for v in (a,z,owner)) and a < z and owner > 0
            assert not merged or a >= merged[-1][1], ('overlap', y, a, z, owner)
            if merged and a == merged[-1][1] and owner == merged[-1][2]:
                merged[-1][1] = z
            else:
                merged.append([a, z, owner])
        if merged: result.append({'y': y, 'runs': merged})
    return result

def owners(rows):
    counts = collections.Counter()
    for row in rows:
        for a,z,owner in row['runs']: counts[owner] += z-a
    return counts

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)
selector = data(BASE, 'data/ownership-selection.json')
sidebody = raw(BASE, selector['additive_release']['path'])
assert len(sidebody) == selector['additive_release']['bytes'] and hashlib.sha256(sidebody).hexdigest() == selector['additive_release']['sha256']
side = json.loads(sidebody)
before = pin_data(side['logical_asset_map']['patch'])['rows']
prior_ledger = pin_data(side['logical_asset_map']['ledger'])
prior_registry = pin_data(side['authority_registry'])
russia_quartet = data(RH, R+'config/compose.json')['authorities'][0]
angola_quartet = data(AH, A+'config/conservative-authority-quartet.json')
japan_quartet = data(JH, J+'handoff/native-authority-quartet.json')
quartets = [russia_quartet, angola_quartet, japan_quartet]
assert data(HEAD,P+'config/compose.json')['authorities'] == quartets
packages=[]; all_original=[]; all_supported=[]; all_subjects=[]
for name,h,prefix,quartet,held_path,expected in [
    ('Russia',RH,R,russia_quartet,'native-partition-preaccept-001/held-native-patch.json',(2566967,2557516,9451,334,327,66,7)),
    ('Angola',AH,A,angola_quartet,'conservative-002/held-native-rows.json',(170526,141263,29263,47,46,28,1)),
    ('Japan',JH,J,japan_quartet,None,(106333,106333,0,556,556,0,0))
]:
    original = data(h,prefix+'source-stage/native-patch.json')['rows']
    supported = pin_data(quartet['native_patch'])['rows']
    held = data(h,prefix+held_path)['rows'] if held_path else []
    assert normal(supported+held) == normal(original)
    oc,sc,hc = owners(original),owners(supported),owners(held)
    actual = (sum(oc.values()),sum(sc.values()),sum(hc.values()),len(oc),len(sc),len(hc),len(set(oc)-set(sc)))
    assert actual == expected,(name,actual)
    subjects = data(h,prefix+'evidence-quality.json')['subject_ids']
    assert len(subjects) == len(set(subjects)) == len(oc)
    constructed = pin_data(quartet['ledger'])
    assert sum(row['native_cells'] for row in constructed['ledger_rows']) == sum(sc.values())
    for key in ('rule_preimage','source_authority'): pin_data(quartet[key])
    all_original += original;all_supported += supported;all_subjects += subjects
    packages.append(dict(zip(['name','requested_cells','supported_cells','held_cells','original_subjects','supported_owners','held_owners','wholly_held_owners'],[name,*actual]),per_owner=[{'owner':o,'requested':oc[o],'supported':sc[o],'held':hc[o]} for o in sorted(oc)]))
assert len(all_subjects) == len(set(all_subjects)) == 937
normal(before+all_original)
proposed = normal(before+all_supported)
report = dict(kind='exact-three-package-interval-conservation',mode=MODE,baseline_commit=BASE,candidate_commit=HEAD,packages=packages,
    original_subjects=len(all_subjects),requested_cells=sum(owners(all_original).values()),supported_cells=sum(owners(all_supported).values()),
    held_cells=sum(p['held_cells'] for p in packages),prior_cells=sum(owners(before).values()),proposed_cumulative_cells=sum(owners(proposed).values()),
    original_package_sets_disjoint_from_each_other_and_prior_patch=True,literal_quartets_preserved=True,
    limits=['Exact whole-file and native interval comparison only. Actual current owner-zero, selected-native, emitted assets and GPU/Canvas checks remain mandatory.',
    'Russia and Angola remain incomplete with explicit holds and source/physical/historical limits. Japan becomes delivered only after genuine final acceptance; its separate physical companion stays excluded.'])
assert (report['requested_cells'],report['supported_cells'],report['held_cells'],report['prior_cells'],report['proposed_cumulative_cells']) == (2843826,2805112,38714,2209586,5014698)
if MODE == 'final':
    after = data(HEAD,P+'composition-001/patch.json')['rows']
    ledger = data(HEAD,P+'composition-001/selected-ledger.json')
    registry = data(HEAD,P+'composition-001/authority-registry.json')
    assert normal(after) == proposed
    for old,new in [(prior_ledger['rows'],ledger['rows']),(prior_registry['entries'],registry['entries'])]:
        assert not (collections.Counter(map(canonical,old))-collections.Counter(map(canonical,new)))
    def held_rows(rows):return [r for r in rows if r.get('disposition') not in ('assigned','zero-cell')]
    assert collections.Counter(map(canonical,held_rows(prior_ledger['rows']))) == collections.Counter(map(canonical,held_rows(ledger['rows'])))
    current = data(HEAD,'data/ownership-selection.json')
    assert {k:v for k,v in current.items() if k!='additive_release'} == {k:v for k,v in selector.items() if k!='additive_release'}
    p0,p1 = data(BASE,'.github/package-inputs.json'),data(HEAD,'.github/package-inputs.json')
    assert {k:v for k,v in p0.items() if k!='inputs'} == {k:v for k,v in p1.items() if k!='inputs'}
    assert p1['inputs'][:len(p0['inputs'])] == p0['inputs']
    assert all(p.startswith((R,A,J,P)) for p in p1['inputs'][len(p0['inputs']):])
    assert data(HEAD,'data/selected-checkpoint.json') == data(RH,'data/selected-checkpoint.json')
    report.update(removed_cells=0,reassigned_cells=0,prior_ledger_rows=len(prior_ledger['rows']),proposed_ledger_rows=len(ledger['rows']),
        prior_authorities=len(prior_registry['entries']),proposed_authorities=len(registry['entries']),prior_held_rows=len(held_rows(prior_ledger['rows'])),proposed_held_rows=len(held_rows(ledger['rows'])),
        literal_prior_rows_preserved=True,literal_prior_authorities_preserved=True,literal_prior_held_rows_preserved=True,
        nonadditive_selector_unchanged=True,package_declaration_prefix_preserved=True,authenticated_greenland_locator_preserved=True)
report['inputs'] = list(inputs.values())
report['bounded_input_bytes'] = sum(d['bytes'] for d in inputs.values())
with output.open('x') as f:json.dump(report,f,sort_keys=True,separators=(',',':'));f.write('\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('packages','inputs')}))
