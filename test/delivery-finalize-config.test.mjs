import {createHash} from 'node:crypto';
import {selectedDataSelection, SELECTED_SMOKE} from '../scripts/integration-profile.mjs';
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync, spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {digest, jsonBytes, pinReader, resolveFinalizeConfig, finalizeDelivery, finalizedPackageInputs} from '../scripts/prepare-delivery-handoff.mjs';

const entry = fileURLToPath(new URL('../scripts/prepare-delivery-handoff.mjs', import.meta.url));
const PREFIX = 'coordination/engineering/finalize-config/';
const locator = ({commit, path}) => ({commit, path});
function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'delivery-finalize-config-'));
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  const env = {...process.env, GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: '/dev/null', GIT_NO_LAZY_FETCH: '1', NODE_OPTIONS: '', NODE_PATH: ''};
  const git = (...args) => execFileSync('git', args, {cwd: root, env, encoding: 'utf8'}).trim();
  git('init', '-q'); git('config', 'user.name', 'Fixture'); git('config', 'user.email', 'fixture@example.invalid');
  const write = (name, value) => {
    fs.mkdirSync(path.dirname(path.join(root, name)), {recursive: true});
    fs.writeFileSync(path.join(root, name), jsonBytes(value));
  };
  const commit = () => { git('add', '.'); git('commit', '-qm', 'Immutable fixture'); return git('rev-parse', 'HEAD'); };
  const reader = () => pinReader(root);
  const pin = (commit, name) => reader().pin(commit, name);
  const common = PREFIX + 'original/';
  write(common + 'body.json', {retained: true});
  const body = pin(commit(), common + 'body.json');
  const authority = {policy_id: 'retained-source-literal-additions', policy_version: 1,
    rule_preimage: body, rule_sha256: body.sha256, source_authority: body};
  const authorityEntry = {authority_sha256: digest(jsonBytes(authority)), ...authority};
  const registry = {version: 1, kind: 'retained-rule-authority-registry-v1', entries: [authorityEntry]};
  const reference = {id: 'geography:base', footprints_sha256: 'a'.repeat(64), hierarchy_sha256: 'b'.repeat(64)};
  write(common + 'registry.json', registry);
  write(common + 'manifest.json', {geographic_release: reference.id, footprints_sha256: reference.footprints_sha256,
    hierarchy_sha256: reference.hierarchy_sha256, original_assets: {bounds: {sha256: body.sha256}}});
  write(common + 'operating.json', {execution_custody: {terminal: body}});
  const originals = commit(), priorRegistry = pin(originals, common + 'registry.json'), manifest = pin(originals, common + 'manifest.json');
  write(common + 'rebind.json', {request: body, facts: body, publication: body, result: body,
    operating: pin(originals, common + 'operating.json')});
  const base = {version: 1, release_id: reference.id, sha256: manifest.sha256, selected_geography: {z: 1, a: 2}};
  const sidecar = {version: 2, kind: 'retained-native-additive-selection-v2', base_selection: base,
    authority_registry: priorRegistry, runtime_envelope: body,
    logical_asset_map: {base_manifest: manifest, owner_roster: body, ledger: body, patch: body}};
  write(common + 'sidecar.json', sidecar);
  const inherited = commit(), rebind = pin(inherited, common + 'rebind.json'), priorSidecar = pin(inherited, common + 'sidecar.json');
  write('data/ownership-selection.json', {...base, additive_release: {path: priorSidecar.path, bytes: priorSidecar.bytes, sha256: priorSidecar.sha256}});
  write('.github/package-inputs.json', {version: 1, inputs: ['public/', '.github/package-inputs.json'],
    optional_inputs: ['public/'], verification_paths: [], generated_outputs: []});
  const baseline = commit(), selector = pin(baseline, 'data/ownership-selection.json'), package_inputs = pin(baseline, '.github/package-inputs.json');
  const geometry = {type: 'Polygon', coordinates: [[[0, 0], [1, 0], [0, 1], [0, 0]]]};
  const row = {representation: 'native-cells', component_id: 'source-target:original', target_id: 'target:original', pixelIndex: 1,
    disposition: 'assigned', base_geometry: geometry, base_geometry_sha256: digest(jsonBytes(geometry)),
    native_rows: [{y: 0, runs: [[0, 1, 1]]}], native_bounds: [0, 0, 1, 1], native_cells: 1,
    source_receipt_sha256: body.sha256, authority_sha256: authorityEntry.authority_sha256, rule_sha256: authority.rule_sha256};
  const ledger = {version: 2, kind: 'native-additive-repair-ledger-v2', authority_registry_sha256: digest(jsonBytes(registry)),
    scope_ids: [row.component_id], rows: [row], current_rebind: rebind, current_targets: [{target_id: row.target_id}]};
  const effective = {...reference, id: 'geography:next'};
  const patch = {authority_registry_sha256: digest(jsonBytes(registry)), ledger_sha256: digest(jsonBytes(ledger)),
    base_reference: reference, effective_reference: effective, rows: row.native_rows};
  const descriptor = value => ({bytes: jsonBytes(value).length, sha256: digest(jsonBytes(value))});
  const envelope = {base_reference: reference, effective_reference: effective, base_manifest: {bytes: manifest.bytes, sha256: manifest.sha256},
    owner_roster: {bytes: body.bytes, sha256: body.sha256}, ledger: descriptor(ledger), patch: descriptor(patch)};
  const products = {'authority-registry.json': registry, 'selected-ledger.json': ledger, 'patch.json': patch, 'runtime-envelope.json': envelope};
  for (const [name, value] of Object.entries(products)) write(PREFIX + 'compose/' + name, value);
  const composed = commit();
  const full = {version: 1, selector, package_inputs, rebind, new_prefix: PREFIX, sidecar_output: PREFIX + 'sidecar.json',
    registry: pin(composed, PREFIX + 'compose/authority-registry.json'), ledger: pin(composed, PREFIX + 'compose/selected-ledger.json'),
    selected_ledger: pin(composed, PREFIX + 'compose/selected-ledger.json'), patch: pin(composed, PREFIX + 'compose/patch.json'),
    runtime_envelope: pin(composed, PREFIX + 'compose/runtime-envelope.json')};
  const compact = {version: full.version, selector: locator(selector), package_inputs: locator(package_inputs), rebind: locator(rebind),
    new_prefix: full.new_prefix, sidecar_output: full.sidecar_output,
    composition: locator(full.selected_ledger)};
  const run = (config, destination, ...flags) => {
    write('config.json', config);
    return spawnSync(process.execPath, [entry, 'finalize', 'config.json', destination, ...flags], {cwd: root, env, encoding: 'utf8'});
  };
  return {root, reader, full, compact, write, commit, baseline, products, run};
}

test('modern compact config resolves exact full pins and preserves legacy objects and canonical outputs', t => {
  const f = fixture(t), before = jsonBytes(f.compact);
  assert.deepEqual(resolveFinalizeConfig(f.compact, f.reader()), f.full);
  assert.strictEqual(resolveFinalizeConfig(f.full, f.reader()), f.full);
  assert.deepEqual(finalizeDelivery(f.compact, f.reader()), finalizeDelivery(f.full, f.reader()));
  assert.deepEqual(jsonBytes(f.compact), before);
});

test('cold CLI emits identical final products and resumes compact configuration exactly', t => {
  const f = fixture(t), destinations = ['full', 'compact'].map(name => '.cache/delivery-handoff/' + name);
  for (const [i, config] of [f.full, f.compact].entries()) {
    const result = f.run(config, destinations[i]); assert.equal(result.status, 0, result.stderr);
  }
  const receipts = destinations.map(dir => JSON.parse(fs.readFileSync(path.join(f.root, dir, 'preparation.json'))));
  assert.deepEqual(receipts[0].outputs, receipts[1].outputs);
  for (const name of Object.keys(receipts[0].outputs))
    assert.deepEqual(fs.readFileSync(path.join(f.root, destinations[0], name)), fs.readFileSync(path.join(f.root, destinations[1], name)));
  assert.notEqual(receipts[0].binding.config_sha256, receipts[1].binding.config_sha256);
  const resumed = f.run(f.compact, destinations[1], '--resume'); assert.equal(resumed.status, 0, resumed.stderr);
  assert.equal(JSON.parse(resumed.stdout).resumed, true);
});

test('compact form refuses mixed full pins, existing sidecar and handwritten locator descriptors', t => {
  const f = fixture(t);
  for (const key of ['registry', 'ledger', 'selected_ledger', 'patch', 'runtime_envelope', 'sidecar', 'unknown'])
    assert.throws(() => finalizeDelivery({...f.compact, [key]: f.full.ledger}, f.reader()), /cannot mix/);
  for (const key of ['selector', 'package_inputs', 'rebind', 'composition'])
    assert.throws(() => finalizeDelivery({...f.compact, [key]: {...f.compact[key], sha256: '0'.repeat(64)}}, f.reader()), /exact commit\/path locator/);
});

test('wrong commit, wrong path, missing product and changed product hash fail before writes', t => {
  const f = fixture(t);
  const cases = [
    {...f.compact, composition: {...f.compact.composition, commit: f.baseline}},
    {...f.compact, composition: {...f.compact.composition, path: PREFIX + 'compose/patch.json'}},
    {...f.compact, composition: {...f.compact.composition, path: '../selected-ledger.json'}},
    {...f.compact, rebind: {...f.compact.rebind, commit: f.full.ledger.commit}},
    {...f.full, patch: {...f.full.patch, sha256: '0'.repeat(64)}}
  ];
  f.write(PREFIX + 'incomplete/selected-ledger.json', f.products['selected-ledger.json']);
  const missing = f.commit(); cases.push({...f.compact, composition: {commit: missing, path: PREFIX + 'incomplete/selected-ledger.json'}});
  f.write(PREFIX + 'compose/patch.json', {...f.products['patch.json'], ledger_sha256: '0'.repeat(64)});
  const changed = f.commit(); cases.push({...f.compact, composition: {...f.compact.composition, commit: changed}});
  fs.chmodSync(path.join(f.root, PREFIX + 'compose/authority-registry.json'), 0o755);
  const executable = f.commit(); cases.push({...f.compact, composition: {...f.compact.composition, commit: executable}});
  for (const [i, config] of cases.entries()) {
    const destination = '.cache/delivery-handoff/refused-' + i, result = f.run(config, destination);
    assert.notEqual(result.status, 0, 'Invalid metadata must refuse');
    assert.match(result.stderr, /Missing ordinary exact Git body|committed selected-ledger|safe whole-file path|exact commit\/path locator|metadata joins differ|Whole body hash differs/);
    assert.equal(fs.existsSync(path.join(f.root, destination)), false, 'Refusal cannot create output');
  }
});

// The actual classifier/finalizer integration belongs with delivery helpers.
// Its original in-memory fixture is retained literally; no country history is needed.
{
const prefix = 'coordination/engineering/fixture-delivery/';
function fixture({mutate = () => {}, packetPrefix = prefix} = {}) {
  const prefix = packetPrefix;
  const blobs = new Map(), baseline = {entries:new Map()}, authored = {entries:new Map()}, reads=[];
  const put = (name, value, old=false) => {
    const bytes = Buffer.isBuffer(value) ? value : Buffer.from(typeof value === 'string' ? value : JSON.stringify(value));
    const sha = createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex');
    blobs.set(sha,bytes); const row={path:name,type:'blob',mode:'100644',size:bytes.length,sha};
    authored.entries.set(name,row); if(old)baseline.entries.set(name,row);
    return {path:name,bytes:bytes.length,sha256:digest(bytes),mode:'100644',git_blob_oid:sha,commit:'a'.repeat(40)};
  };
  const leaf = (name, old=false) => put((old?'coordination/engineering/prior/':prefix)+name,{opaque:true},old);
  put(SELECTED_SMOKE,'// Accepted generic helper',true);
  const authority = leaf('authority.json',true), rule = leaf('rule.json',true);
  const entry={authority_sha256:'a'.repeat(64),policy_id:'retained-source-literal-additions',policy_version:1,
    rule_preimage:rule,rule_sha256:rule.sha256,source_authority:authority};
  const registryBody={version:1,kind:'registry',entries:[entry]};
  const oldRegistry=put('coordination/engineering/prior/registry.json',registryBody,true);
  const base={version:1,method:'native-linear-evenodd-first-owner-v1',artifact_consumption:{certificate:{},review:{}},manifest_path:'unchanged.json',sha256:'a'.repeat(64)};
  const oldLedger=put('coordination/engineering/prior/ledger.json',{rows:[]},true);
  const oldSidecar=put('coordination/engineering/prior/sidecar.json',{authority_registry:oldRegistry,logical_asset_map:{ledger:oldLedger}},true);
  const hook=pin=>({path:pin.path,bytes:pin.bytes,sha256:pin.sha256});
  put('data/ownership-selection.json',{...base,additive_release:hook(oldSidecar)},true);
  const registry=put(prefix+'registry.json',registryBody);
  const original=leaf('composed-original-ledger.json');
  const plan=put(prefix+'issued-plan.json',{original_inputs:[{...registry,commit:'b'.repeat(40)},original]});
  const custody=Object.fromEntries(['code_source','terminal','stderr','stdout'].map(name=>[name,leaf(name+'.json')]));
  custody.issued_plan=plan;
  const operating=put(prefix+'operating.json',{execution_custody:custody});
  const certificateBody={version:1,kind:'qualified-native-additive-current-bank-rebind-v1',operating,
    ...Object.fromEntries(['request','facts','publication','result'].map(name=>[name,leaf(name+'.json')]))};
  const certificate=put(prefix+'certificate.json',certificateBody);
  const rows=[{component_id:'old',target_id:'target-old',disposition:'assigned',geometry_sha256:'1'.repeat(64),native_cells:2},
    {component_id:'new',target_id:'target-new',disposition:'zero-cell',geometry_sha256:'2'.repeat(64),native_cells:0}];
  const ledgerBody={version:2,kind:'native-additive-repair-ledger-v2',rows,current_rebind:certificate};
  const ledger=put(prefix+'ledger.json',ledgerBody);
  const sidecarBody={version:2,kind:'retained-native-additive-selection-v2',base_selection:base,
    authority_registry:registry,runtime_envelope:leaf('envelope.json'),
    logical_asset_map:{ledger,patch:leaf('patch.json'),owner_roster:leaf('owners.json',true),base_manifest:leaf('manifest.json',true)}};
  const sidecar=put(prefix+'selection-sidecar.json',sidecarBody);
  put('data/ownership-selection.json',{...base,additive_release:hook(sidecar)});
  const expected={version:1,selected_ledger_sha256:ledger.sha256,cumulative_native_cells:2,
    cohorts:[{original_batch_id:'complete-original',component_ids:['old','new'],members:rows.map(({native_cells,...member})=>member)}]};
  put(prefix+'selected-delivery-expectations.json',expected);
  const policy={version:1,inputs:['.github/package-inputs.json','data/ownership-selection.json'],optional_inputs:[],verification_paths:[],generated_outputs:[]};
  put('.github/package-inputs.json',policy,true);
  const definition={...policy,inputs:[...policy.inputs,...[...authored.entries.keys()].filter(name=>name.startsWith(prefix)&&!name.endsWith('selected-delivery-expectations.json'))]};
  put('.github/package-inputs.json',definition);
  const f={put,leaf,blobs,baseline,authored,reads,base,rows,expected,definition,policy,sidecarBody,ledgerBody,certificateBody,registryBody,plan,registry,operating};
  mutate(f);
  f.files=[...authored.entries].filter(([name,row])=>baseline.entries.get(name)?.sha!==row.sha).map(([filename])=>({filename,status:baseline.entries.has(filename)?'modified':'added'}));
  f.api=async route=>{const oid=route.split('/').at(-1),bytes=blobs.get(oid);assert(bytes,route);reads.push(oid);return {sha:oid,size:bytes.length,encoding:'base64',content:bytes.toString('base64')};};
  f.run=(options={})=>selectedDataSelection({api:f.api,repo:'owner/repo',branch:'engineering/fixture-delivery',files:f.files,baseline,authored,...options});
  return f;
}
test('delivery finalizer satisfies actual append-only selected-data classifier and rejects global sorting', async () => {
  const f=fixture(), paths=f.definition.inputs.filter(p=>p.startsWith(prefix));
  const definition=finalizedPackageInputs(f.policy,prefix,paths);
  assert.deepEqual(definition.inputs.slice(0,f.policy.inputs.length),f.policy.inputs);
  assert.deepEqual(finalizedPackageInputs(definition,prefix,paths),definition);
  f.put('.github/package-inputs.json',definition);
  assert.deepEqual(await f.run(),{test_selection:'selected-data',expectations_path:prefix+'selected-delivery-expectations.json',shards:[0]});
  f.put('.github/package-inputs.json',{...definition,inputs:definition.inputs.toSorted()});
  assert.equal(await f.run(),null,'the same globally sorted input set must not pass the accepted-prefix classifier');
});
}

test('canonical originals remain in the candidate while absent historical roles require explicit exact restoration', t => {
  const f = fixture(t), read = () => pinReader(f.root), config = {...f.full,
    new_prefix: PREFIX + 'compose/', sidecar_output: PREFIX + 'compose/sidecar.json'};
  const original = read().json(config.registry).entries[0].rule_preimage;
  const filename = path.join(f.root, original.path), raw = fs.readFileSync(filename);
  const retained = f.run(config, '.cache/delivery-handoff/canonical');
  assert.equal(retained.status, 0, retained.stderr);
  const products = JSON.parse(fs.readFileSync(path.join(f.root, '.cache/delivery-handoff/canonical/preparation.json'))).outputs;
  assert.ok(Object.keys(products).every(name => !name.includes('/')));
  assert.deepEqual(fs.readFileSync(filename), raw);

  // This snapshot intentionally lacks one required original. The candidate then
  // restores its exact canonical path, without a second local-output copy.
  fs.unlinkSync(filename);
  const missing = f.commit();
  config.package_inputs = read().pin(missing, '.github/package-inputs.json');
  fs.writeFileSync(filename, raw, {flag: 'wx'});
  const restored = f.commit();
  config.restored_read_roles = {commit: restored, paths: [original.path]};
  const result = f.run(config, '.cache/delivery-handoff/restored');
  assert.equal(result.status, 0, result.stderr);
  const receipt = JSON.parse(fs.readFileSync(path.join(f.root, '.cache/delivery-handoff/restored/preparation.json')));
  assert.ok(Object.keys(receipt.outputs).every(name => !name.includes('/')));
  assert.deepEqual(fs.readFileSync(filename), raw);

  const withoutSnapshot = {...config}; delete withoutSnapshot.restored_read_roles;
  const refused = f.run(withoutSnapshot, '.cache/delivery-handoff/missing-snapshot');
  assert.notEqual(refused.status, 0); assert.match(refused.stderr, /accepted path identity/);
  assert.equal(fs.existsSync(path.join(f.root, '.cache/delivery-handoff/missing-snapshot')), false);
  assert.deepEqual(fs.readFileSync(filename), raw);
  f.write(original.path, {retained: false});
  const changed = f.commit(), changedRaw = fs.readFileSync(filename);
  config.restored_read_roles = {commit: changed, paths: [original.path]};
  const divergent = f.run(config, '.cache/delivery-handoff/changed-snapshot');
  assert.notEqual(divergent.status, 0); assert.match(divergent.stderr, /Restored snapshot differs/);
  assert.equal(fs.existsSync(path.join(f.root, '.cache/delivery-handoff/changed-snapshot')), false);
  assert.deepEqual(fs.readFileSync(filename), changedRaw);
});
