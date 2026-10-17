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
# This fixed finite job's complete read closure was observed from the original
# immutable plan, then declared explicitly before reading any scientific body.
# Fresh candidate/base aliases bind exact caller tree entries; producer operands
# retain their actual literal commits. No file-size or dataset-size cap exists.
PLANNED_INPUTS = [
    (BASE, 'data/ownership-selection.json'),
    (BASE, 'coordination/engineering/greenland-repair-delivery-20261017/ownership-selection-greenland-current.json'),
    ('c8a5133bc78923b8ca78c6feeb992b87ceaa8c17', 'coordination/engineering/greenland-repair-delivery-20261017/composition-current-001/patch.json'),
    ('c8a5133bc78923b8ca78c6feeb992b87ceaa8c17', 'coordination/engineering/greenland-repair-delivery-20261017/composition-current-001/selected-ledger.json'),
    ('c8a5133bc78923b8ca78c6feeb992b87ceaa8c17', 'coordination/engineering/greenland-repair-delivery-20261017/composition-current-001/authority-registry.json'),
    ('ec8dd6711677fb77586441bbd5ef2d34488df2b6', 'coordination/engineering/russia-repair-delivery-20261017/config/compose.json'),
    ('86b089e2b82a2e85264c96b11188854f2d1bce4a', 'coordination/engineering/angola-repair-delivery-20261017/config/conservative-authority-quartet.json'),
    ('c76c45be06853204183bad2b858081ef37bd8d40', 'coordination/engineering/japan-native-repair-20261017/handoff/native-authority-quartet.json'),
    (HEAD, 'coordination/engineering/russia-angola-japan-delivery-20261017/config/compose.json'),
    ('ec8dd6711677fb77586441bbd5ef2d34488df2b6', 'coordination/engineering/russia-repair-delivery-20261017/source-stage/native-patch.json'),
    ('44b0b0d71e853ad0bebca4fffdd26b74c0a92e0c', 'coordination/engineering/russia-repair-delivery-20261017/native-partition-preaccept-001/supported-native-patch.json'),
    ('ec8dd6711677fb77586441bbd5ef2d34488df2b6', 'coordination/engineering/russia-repair-delivery-20261017/native-partition-preaccept-001/held-native-patch.json'),
    ('ec8dd6711677fb77586441bbd5ef2d34488df2b6', 'coordination/engineering/russia-repair-delivery-20261017/evidence-quality.json'),
    ('d3c74d563932b99deb695c5fff80a6e4dfb015a5', 'coordination/engineering/russia-repair-delivery-20261017/native-authority-001/constructor-result.json'),
    ('d3c74d563932b99deb695c5fff80a6e4dfb015a5', 'coordination/engineering/russia-repair-delivery-20261017/native-authority-001/original-rule-preimage.json'),
    ('d3c74d563932b99deb695c5fff80a6e4dfb015a5', 'coordination/engineering/russia-repair-delivery-20261017/native-authority-001/authority-binding.json'),
    ('86b089e2b82a2e85264c96b11188854f2d1bce4a', 'coordination/engineering/angola-repair-delivery-20261017/source-stage/native-patch.json'),
    ('a5e0e64e0b4c843f3821de13b46d7ad85cf3c265', 'coordination/engineering/angola-repair-delivery-20261017/conservative-002/native-patch.json'),
    ('86b089e2b82a2e85264c96b11188854f2d1bce4a', 'coordination/engineering/angola-repair-delivery-20261017/conservative-002/held-native-rows.json'),
    ('86b089e2b82a2e85264c96b11188854f2d1bce4a', 'coordination/engineering/angola-repair-delivery-20261017/evidence-quality.json'),
    ('49e6aa8a90a15f692c4309ac2de2b62357bf41f6', 'coordination/engineering/angola-repair-delivery-20261017/native-authority-002/constructor-result.json'),
    ('49e6aa8a90a15f692c4309ac2de2b62357bf41f6', 'coordination/engineering/angola-repair-delivery-20261017/native-authority-002/original-rule-preimage.json'),
    ('49e6aa8a90a15f692c4309ac2de2b62357bf41f6', 'coordination/engineering/angola-repair-delivery-20261017/native-authority-002/authority-binding.json'),
    ('c76c45be06853204183bad2b858081ef37bd8d40', 'coordination/engineering/japan-native-repair-20261017/source-stage/native-patch.json'),
    ('def4f95468aec4ede25beba6037ea7207e458622', 'coordination/engineering/japan-native-repair-20261017/source-stage/native-patch.json'),
    ('c76c45be06853204183bad2b858081ef37bd8d40', 'coordination/engineering/japan-native-repair-20261017/evidence-quality.json'),
    ('f6d7786d67a8b0ce76a525f63a055332f2e024b1', 'coordination/engineering/japan-native-repair-20261017/native-authority-001/constructor-result.json'),
    ('f6d7786d67a8b0ce76a525f63a055332f2e024b1', 'coordination/engineering/japan-native-repair-20261017/native-authority-001/original-rule-preimage.json'),
    ('f6d7786d67a8b0ce76a525f63a055332f2e024b1', 'coordination/engineering/japan-native-repair-20261017/native-authority-001/authority-binding.json'),
]
if MODE == 'final':
    PLANNED_INPUTS += [(HEAD,P+p) for p in ('composition-001/patch.json','composition-001/selected-ledger.json','composition-001/authority-registry.json')]
    PLANNED_INPUTS += [(HEAD,p) for p in ('data/ownership-selection.json','.github/package-inputs.json','data/selected-checkpoint.json')]
    PLANNED_INPUTS += [(BASE,'.github/package-inputs.json'),(RH,'data/selected-checkpoint.json')]

def tree_descriptor(commit,name):
    assert re.fullmatch('[a-f0-9]{40}',commit)
    assert not name.startswith('/') and all(p not in ('','.','..') for p in name.split('/'))
    row=subprocess.check_output(['git','-c','protocol.allow=never','-C',W,'ls-tree','-z',commit,'--',name]).rstrip(b'\0')
    meta,actual_name=row.split(b'\t');mode,kind,oid=meta.decode().split()
    assert actual_name.decode()==name and mode=='100644' and kind=='blob'
    size=int(subprocess.check_output(['git','-c','protocol.allow=never','-C',W,'cat-file','-s',oid]))
    assert size>=0
    return dict(commit=commit,path=name,mode=mode,git_blob_oid=oid,bytes=size)

planned={c+':'+p:tree_descriptor(c,p) for c,p in PLANNED_INPUTS}
planned_total=sum(x['bytes'] for x in planned.values());largest=max(x['bytes'] for x in planned.values())
# Cooperative memory admission, not a scientific/data cap: immutable whole-byte
# totals plus an explicit JSON/interval workspace estimate are compared with the
# actual currently available memory. Peak process RSS is measured after the proof.
import resource
meminfo=dict(line.split(':',1) for line in pathlib.Path('/proc/meminfo').read_text().splitlines())
available=int(meminfo['MemAvailable'].strip().split()[0])*1024
cg=pathlib.Path('/sys/fs/cgroup')
if (cg/'memory.max').exists() and (cg/'memory.current').exists():
    cap=(cg/'memory.max').read_text().strip()
    if cap!='max':available=min(available,max(0,int(cap)-int((cg/'memory.current').read_text())))
initial_rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
# Calibrated against the first complete 37-file proof: 1,524,166,656 peak RSS
# for 129,799,362 immutable bytes. This is an admission estimate, not a hard
# memory bound or a scientific file/dataset cap. The actual peak is reported.
estimated_workspace=planned_total*12+largest*4+initial_rss
assert estimated_workspace<=available, 'Actual available memory does not admit the measured finite input plan and estimated interval workspace'
print(json.dumps(dict(memory_admission='cooperative-measured-input-plan',planned_input_files=len(planned),planned_encoded_bytes=planned_total,largest_file_bytes=largest,estimated_workspace_bytes=estimated_workspace,available_memory_bytes=available)),flush=True)
inputs={}
def raw(commit,name):
    key=commit+':'+name
    assert key in planned,'Undeclared scientific input'
    desc=planned[key]
    assert tree_descriptor(commit,name)==desc,'Immutable input tree changed'
    # Read exactly the authenticated immutable object size plus one overflow byte.
    with subprocess.Popen(['git','-c','protocol.allow=never','-C',W,'cat-file','blob',desc['git_blob_oid']],stdout=subprocess.PIPE) as process:
        body=process.stdout.read(desc['bytes']+1)
        assert len(body)==desc['bytes'] and not process.stdout.read(1)
        assert process.wait()==0
    assert hashlib.sha1(('blob '+str(len(body))+'\0').encode()+body).hexdigest()==desc['git_blob_oid']
    actual={**desc,'sha256':hashlib.sha256(body).hexdigest()}
    assert key not in inputs or inputs[key]==actual
    inputs[key]=actual
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
assert set(inputs)==set(planned), 'Planned input closure was not fully consumed'
report['measured_input_bytes'] = sum(d['bytes'] for d in inputs.values())
report['planned_input_files'] = len(planned)
report['largest_input_bytes'] = largest
with output.open('x') as f:json.dump(report,f,sort_keys=True,separators=(',',':'));f.write('\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('packages','inputs')}))
print(json.dumps(dict(observed_process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)))
