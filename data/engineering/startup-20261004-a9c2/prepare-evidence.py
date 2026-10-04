"""Inventory actual bounded whole files; never execute submitted reproduction commands."""
import gzip, hashlib, json, os, subprocess
from pathlib import Path

ROOT = Path('data/engineering/startup-20261004-a9c2')
MANIFEST = Path('coordination/engineering/startup-20261004-a9c2/evidence-quality.json')
BASE = 'c81bdce3f6aee4944d0dbae1c848bf33c365124f'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
def git(*args):
    return subprocess.check_output(['git', *args])
def descriptor(name, baseline=False, role=None):
    raw = git('show', BASE + ':' + name) if baseline else Path(name).read_bytes()
    row = dict(path=name, bytes=len(raw), sha256=sha(raw), hash_kind='file-bytes')
    if role: row['role'] = role
    if raw[:2] == b'\x1f\x8b':
        expanded = gzip.decompress(raw)
        row.update(uncompressed_bytes=len(expanded), uncompressed_sha256=sha(expanded))
        assert len(expanded) <= 32 * 1024 * 1024, name
    assert len(raw) <= 32 * 1024 * 1024, name
    return row

changes = []
for line in git('diff', '--name-status', '--no-renames', BASE).decode().splitlines():
    status, name = line.split('\t')
    changes.append((dict(A='added', M='modified', D='removed')[status], name))
for name in git('ls-files', '--others', '--exclude-standard').decode().splitlines():
    if name not in [p for _, p in changes]: changes.append(('added', name))
if str(MANIFEST) not in [p for _, p in changes]: changes.append(('added', str(MANIFEST)))
changes.sort(key=lambda row:row[1])
baseline_paths = set()
for status, name in changes:
    if status != 'added': baseline_paths.add(name)
for prefix in ['data/canonical-grid', 'data/reference-attributes']:
    baseline_paths.update(git('ls-tree', '-r', '--name-only', BASE, prefix).decode().splitlines())
# Bounds are not consumed by the transport re-encoder; the original word parts
# and manifest are fully inventoried. Preserve immutable bounds in repository.
baseline_paths.discard('data/canonical-grid/bounds.json.gz')
baseline_paths.update(['data/hierarchy.json','data/geographic-releases/current-manifest.json','data/geographic-releases/index.json','data/prepared-evidence/index.json'])
baseline = [descriptor(p, True, 'original-source' if p.startswith('data/') else 'implementation-baseline') for p in sorted(baseline_paths)]
outputs = [descriptor(p) for status,p in changes if status != 'removed' and p != str(MANIFEST)]
by_path = {r['path']:r for r in outputs}
receipts = []
for status, name in changes:
    row = dict(path=name, status=status)
    if status != 'added': row['original_sha256'] = sha(git('show', BASE+':'+name))
    if status == 'removed': row['reason'] = 'Preserved immutable original vintage; inspect linked restoration receipt'
    receipts.append(row)
metrics, bindings = [], []
def metric(identifier, name, pointer, value, units, evaluated, input_path=None):
    input_path = input_path or name
    metrics.append(dict(id=identifier, value=value, unit=units, vintage='archived',
        evaluation_commit=evaluated, input_sha256=by_path[input_path]['sha256']))
    bindings.append(dict(metric_id=identifier,path=name,json_pointer=pointer))
experiments = ['site24-startup-before-01.json','main-preview-startup-before-01.json'] + [f'candidate-startup-0{i}.json' for i in range(1,5)]
for i, short in enumerate(experiments):
    name = str(ROOT/short); result=json.loads(Path(name).read_text())
    if i < 2: evaluated=git('rev-parse','f2f0884').decode().strip()
    else: evaluated=json.loads((ROOT/f'candidate-code-inventory-0{i-1}.json').read_text())['source_ancestry_commit']
    # Experiments include uncommitted measured code pinned by full inventories;
    # evaluation_commit records actual ancestry, not a claim of clean-tree use.
    for visit in ['initial','repeat']:
        metric(short+'-'+visit,name,'/'+visit+'/elapsed_ms',result[visit]['elapsed_ms'],'milliseconds',evaluated)
    for visit in ['initial','repeat']:
        for key in ['TaskDuration','ScriptDuration','JSHeapUsedSize']:
            if key in result[visit].get('metrics',{}): metric(short+'-'+visit+'-'+key,name,'/'+visit+'/metrics/'+key,result[visit]['metrics'][key],'bytes' if key=='JSHeapUsedSize' else 'seconds',evaluated)
    for n, sample in enumerate(result['navigation']):
        metric(short+'-navigation-'+str(n),name,f'/navigation/{n}/elapsed_ms',sample['elapsed_ms'],'milliseconds',evaluated)
for n in [1,2]:
    name=str(ROOT/f'ownership-transport-parity-0{n}.json');r=json.loads(Path(name).read_text())
    if 'new_run_bytes' in r: metric(f'ownership-0{n}-run-bytes',name,'/new_run_bytes',r['new_run_bytes'],'bytes',git('rev-parse','5482569').decode().strip())
name=str(ROOT/'varint-prototype-restoration.json');r=json.loads(Path(name).read_text())
for key in ['new_run_bytes','original_input_bytes']:
    metric('varint-archive-'+key,name,'/'+key,r[key],'bytes',git('rev-parse','5482569').decode().strip())
name=str(ROOT/'ownership-transport-parity-02.json');r=json.loads(Path(name).read_text())
metric('unchanged-canonical-run-words',name,'/ownership/pixelMap/runWords',r['ownership']['pixelMap']['runWords'],'words',git('rev-parse','5482569').decode().strip())
metric('unchanged-canonical-grid-size',name,'/ownership/pixelMap/size',r['ownership']['pixelMap']['size'],'grid size',git('rev-parse','5482569').decode().strip())
for short,keys in [('scoped-tests-receipt-07.json',['tests','passed','failed','skipped'])]:
    name=str(ROOT/short);r=json.loads(Path(name).read_text())
    for key in keys: metric(short+'-'+key,name,'/'+key,r[key],'tests',git('rev-parse','4a90be3').decode().strip())
name=str(ROOT/'candidate-controls-04.json');r=json.loads(Path(name).read_text())
metric('fallback-painted-pixels',name,'/fallback_pixels/painted_pixels',r['fallback_pixels']['painted_pixels'],'pixels',git('rev-parse','4a90be3').decode().strip())
for n in [1,2]:
    name=str(ROOT/f'deployment-budget-0{n}.json');r=json.loads(Path(name).read_text())
    for key in ['uncompressed_bytes','compressed_bytes']:
        metric(f'package-0{n}-'+key,name,'/archive/'+key,r['archive'][key],'bytes',git('rev-parse','4a90be3').decode().strip())
manifest = dict(version=1,issue=712,lane='engineering',worker_id='engineering-startup-a9c25e14-20261004',
    subject_ids=[],subject_ids_sha256=sha(b'[]'),baseline=dict(commit=BASE,files=baseline,pins={},pin_files={}),
    sources=[dict(id='existing-compiled-atlas',url='https://github.com/ChengshuLi/WorldAtlas',role='Existing reviewed compiled inputs; no new geographic factual assertions',
        vintage='Immutable main c81bdce3f6aee4944d0dbae1c848bf33c365124f plus separately pinned served Site24 release5',retrieved_at='2026-10-04',
        license=dict(status='unknown',terms='No new upstream redistribution grant established by this engineering change'),retention='restoration-only',verification='unverified',temporal_status='reference',
        restoration='Checkout baseline for canonical ownership/reference originals. Served source5 captures and exact original/root transport proofs are retained as engineering forensic outputs. Unselected full varint prototype remains at evidence-startup712-varint-20261004-a9c2 / 5482569ea17d16dfa972ddb5b436ed16f9b39bb7; follow varint-prototype-restoration.json. No silent source deletion. Unused32MiB packaging is reproducibly restored from owned prototypes/package-startup-ownership-32m.mjs and full original inputs; see ownership-32m-restoration.json.',
        limit='Existing geography/source assertions and reuse terms were not independently reapproved. This packet proves lossless transport, not geographic approval, original primary-source authenticity, installed assets or served acceptance. Unused32MiB compiled outputs are scratch-retained and reconstructable with whole-file hashes, not uploaded byte-checked payloads.')],
    outputs=outputs,change_receipts=receipts,metric_bindings=bindings,rendered_tables=[],
    methods=[dict(id='lossless-startup-transport',kind='code',description='Repackage complete original pinned reference records and canonical GPU words; preserve original encoding, decoded words, identities, provenance and half-open intervals. Existing packaging, loader and negative controls plus full-word receipts are inspected independently.',software='Node24.19.0; unchanged ownership-codec.js; zlib; pinned Python3.12.14 for full package',units='file bytes and exact decoded words'),
      dict(id='complete-startup-measurement',kind='measurement',description='Complete selected-year startup ends only when loader hidden and full canvas rendered; include preparing, geography/reference and historical snapshot, all repeated/outlier/failure vintages. One browser localhost HTTP1 proxy with production GET-only remaining inputs; locally served new bundles are an optimistic transport experiment, not equivalent hosted timing. Provider wake/query timing and physical phones unknown.',software='Node24.19.0, Playwright headless Chromium153.0.8010.12, Linux1440x1080, no CPU/network throttling',units='milliseconds')],
    metrics=metrics,summaries=[dict(metric_id=m['id'],value=m['value'],unit=m['unit']) for m in metrics],
    validation=[dict(method_id='complete-startup-measurement',kind=k,outcome='passed',evidence_path=str(ROOT/(k+'.json'))) for k in ['positive-control','negative-control']],
    conclusions=[dict(text='Complete preview startup improves but both 11.754s fresh and10.073s repeat still miss10s; new transports local, served performance remains unverified. All archived samples/outliers/failures retained; no physical-phone certificate. Experiments with uncommitted code are reconstructed by exact candidate inventories rather than falsely assigned clean commits.',status='unresolved',source_ids=['existing-compiled-atlas']),
        dict(text='No deployment, geographic approval, identity/claim migration or provider/schema changes. Publisher retains prior objects and separately verifies actual source/static/server/release/archive coherence.',status='unresolved',source_ids=['existing-compiled-atlas'])],
    stages=dict(research='partial',implementation='proposed',geographic_approval='not-requested'),
    commands=['npm ci','node --test test/package-startup-ownership.test.mjs test/reference-bundle.test.mjs test/compact-map-client.test.mjs test/reference-context.test.mjs test/ownership-assets.test.mjs','Use documented hidden-stdin startup-benchmark/modes/controls with exact pinned candidate input and frontend directory; never put private credentials in arguments/files/browser','PATH=<declared-pinned-python-bin>:$PATH ATLAS_PYTHON=<declared-pinned-python> npm run build:hosted','python3 data/engineering/startup-20261004-a9c2/prepare-evidence.py','node scripts/evidence-quality.mjs '+str(MANIFEST)])
assert len(baseline)+len(outputs)<=512
assert sum(r['bytes'] for r in baseline+outputs)<=256*1024*1024
MANIFEST.parent.mkdir(parents=True,exist_ok=True)
MANIFEST.write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(descriptors=len(baseline)+len(outputs),raw_bytes=sum(r['bytes'] for r in baseline+outputs),changed_files=len(changes),metrics=len(metrics))))
