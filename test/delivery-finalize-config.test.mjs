import {gzipSync,gunzipSync} from 'node:zlib';
import {shuffleOwnershipBytes} from '../src/ownership-codec.js';
import {additiveReleaseFootprintDigest,footprintValueSha256,bindAdditiveLedgerFeatures} from '../src/effective-footprint.js';
import {packageStartupOwnership} from '../scripts/package-startup-ownership.mjs';
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


async function nativeFixture(t){
 const f=fixture(t),prefix=PREFIX+'native/',bank='data/canonical-grid/current-startup/';
 const save=(name,raw)=>{fs.mkdirSync(path.dirname(path.join(f.root,name)),{recursive:true});fs.writeFileSync(path.join(f.root,name),raw);};
 const pin=name=>f.reader().pin(f.commit(),name),reference=f.products['runtime-envelope.json'].base_reference;
 const size=262166,coordinateBits=19,rows=new Uint32Array(size*2);for(let y=1;y<size;y++)rows[y*2]=1;rows[1]=1;
 const encode=(kind,words)=>{const raw=gzipSync(shuffleOwnershipBytes(words)),name=`native-v1/ownership/${kind}-0.bin.gz`;save('data/'+name,raw);return {kind,path:name,offset:0,words:words.length,encoding:'byte-shuffle',sha256:digest(raw),decoded_sha256:digest(Buffer.from(words.buffer))};};
 const parts=[encode('rows',rows),encode('runs',Uint32Array.from([2*2**coordinateBits+2,2]))];
 const latitudePath='coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz';
 const latitudeBytes=fs.readFileSync(latitudePath),latitudes=gunzipSync(latitudeBytes);save(latitudePath,latitudeBytes);const latitude=pin(latitudePath);
 const owners=[{id:'target:original',index:1,province_id:'parent',bounds:[0,0,1,1]},
  {id:'untouched',index:2,province_id:'parent',bounds:[2,0,3,1]}],rosterBytes=gzipSync(jsonBytes(owners));
 save(prefix+'owners.json.gz',rosterBytes);const roster={...pin(prefix+'owners.json.gz'),encoding:'gzip',decoded_bytes:jsonBytes(owners).length,decoded_sha256:digest(jsonBytes(owners))};
 const manifest={version:2,size,coordinateBits,method:'native-linear-evenodd-first-owner-v1',runWords:2,
  geographic_release:reference.id,footprints_sha256:reference.footprints_sha256,hierarchy_sha256:reference.hierarchy_sha256,
  original_assets:{bounds:{sha256:roster.sha256}},native_latitudes:{...latitude,root:'repository',role:'immutable-normative-rule-input',decoded_bytes:latitudes.length,decoded_sha256:digest(latitudes)},parts};
 f.write('data/native-manifest.json',manifest);const manifestPin=pin('data/native-manifest.json');
 const packed=await packageStartupOwnership({manifest,source:path.join(f.root,'data'),destination:path.join(f.root,bank,'ownership-vintages/'+manifestPin.sha256)});
 for(const part of parts.filter(p=>p.kind==='rows'))save(bank+part.path,fs.readFileSync(path.join(f.root,'data',part.path)));
 save(bank+'native-v1/native-row-latitudes.f64le.gz',latitudeBytes);
 const pixelMap={...packed.pixelMap,canonical_grid_sha256:manifestPin.sha256,
  native_latitudes:{...manifest.native_latitudes,transport_path:'native-v1/native-row-latitudes.f64le.gz'},
  parts:packed.pixelMap.parts.map(p=>p.kind==='rows'?p:{...p,path:'ownership-vintages/'+manifestPin.sha256+'/'+p.path})};
 const files=[];function inventory(dir,relative=''){for(const e of fs.readdirSync(dir,{withFileTypes:true})){const name=relative+e.name,full=path.join(dir,e.name);if(e.isDirectory())inventory(full,name+'/');else{const raw=fs.readFileSync(full);files.push({path:name,bytes:raw.length,sha256:digest(raw)});}}}inventory(path.join(f.root,bank));
 const originalIndex={version:1,native_manifest_sha256:manifestPin.sha256,release_id:reference.id,footprints_sha256:reference.footprints_sha256,hierarchy_sha256:reference.hierarchy_sha256,pixelMap,files:files.sort((a,b)=>a.path.localeCompare(b.path))};
 f.write(bank+'index.json',originalIndex);
 const ledger=structuredClone(f.products['selected-ledger.json']),row=ledger.rows[0];row.base_geometry_sha256=footprintValueSha256(row.base_geometry);
 ledger.parent_inventory={components:1,report_sha256:'a'.repeat(64),roster_sha256:'b'.repeat(64)};ledger.current_targets=[{target_id:row.target_id,pixelIndex:row.pixelIndex,geometry:row.base_geometry,geometry_sha256:row.base_geometry_sha256}];
 f.write(prefix+'selected-ledger.json',ledger);const ledgerPin=pin(prefix+'selected-ledger.json');
 const descriptor=(name,p)=>({path:'additive-repairs/'+name,bytes:p.bytes,sha256:p.sha256,...(p.encoding?{encoding:p.encoding,decoded_bytes:p.decoded_bytes,decoded_sha256:p.decoded_sha256}:{})});
 const envelope={version:2,kind:'retained-native-base-plus-delta-v2',base_reference:reference,effective_reference:{...reference,id:'geography:finished'},
  base_manifest:descriptor('base.json',manifestPin),owner_roster:descriptor('owners.json.gz',roster),ledger:descriptor('ledger.json',ledgerPin)};
 const features=owners.map(o=>({id:o.id,pixelIndex:o.index,geometry:null,properties:{id:o.id,parent_id:o.province_id}}));
 envelope.effective_reference.footprints_sha256=additiveReleaseFootprintDigest(reference,bindAdditiveLedgerFeatures(features,ledger,envelope,reference));
 const patch={...f.products['patch.json'],version:2,kind:'unassigned-native-cells-v1',ledger_sha256:ledgerPin.sha256,effective_reference:envelope.effective_reference};
 f.write(prefix+'patch.json',patch);const patchPin=pin(prefix+'patch.json');envelope.patch=descriptor('patch.json',patchPin);
 f.write(prefix+'runtime-envelope.json',envelope);const envelopePin=pin(prefix+'runtime-envelope.json');
 const base={version:1,method:manifest.method,manifest_path:'data/native-manifest.json',sha256:manifestPin.sha256,release_id:reference.id};
 const sidecar={version:2,kind:'retained-native-additive-selection-v2',base_selection:base,authority_registry:f.full.registry,
  runtime_envelope:envelopePin,logical_asset_map:{base_manifest:manifestPin,owner_roster:roster,ledger:ledgerPin,patch:patchPin}};
 f.write(prefix+'old-sidecar.json',sidecar);const sidecarPin=pin(prefix+'old-sidecar.json');
 f.write('data/ownership-selection.json',{...base,additive_release:{path:sidecarPin.path,bytes:sidecarPin.bytes,sha256:sidecarPin.sha256}});
 const definition=f.reader().json(f.full.package_inputs);definition.inputs.push(bank);f.write('.github/package-inputs.json',definition);
 const baseline=f.commit(),reader=f.reader(),full={...f.full,selector:reader.pin(baseline,'data/ownership-selection.json'),package_inputs:reader.pin(baseline,'.github/package-inputs.json'),
  ledger:ledgerPin,selected_ledger:ledgerPin,patch:patchPin,runtime_envelope:envelopePin};
 return {...f,full,originalIndex,bank,baseline,save};
}

test('normal finalization adopts the complete finished native bank and selector together, with exact resume',async t=>{
 const f=await nativeFixture(t),before=fs.readFileSync(path.join(f.root,'data/ownership-selection.json'));
 const destination='.cache/delivery-handoff/native',result=f.run(f.full,destination);assert.equal(result.status,0,result.stderr);
 const selector=fs.readFileSync(path.join(f.root,'data/ownership-selection.json')),index=JSON.parse(fs.readFileSync(path.join(f.root,f.bank,'index.json')));
 assert.notDeepEqual(selector,before);assert.equal(index.version,2);assert.equal(index.preparedOwnership.selection_sha256,digest(selector));
 assert.equal(index.preparedOwnership.additive_added_cells,1);assert.equal(index.preparedOwnership.owners,2);
 assert.deepEqual(fs.readFileSync(path.join(f.root,f.bank,'index.json')),fs.readFileSync(path.join(f.root,destination,'startup-ownership.json')));
 for(const pin of index.files){const raw=fs.readFileSync(path.join(f.root,f.bank,pin.path));assert.equal(raw.length,pin.bytes);assert.equal(digest(raw),pin.sha256);}
 for(const pin of f.originalIndex.files)assert.deepEqual(index.files.find(p=>p.path===pin.path),pin,'Every original immutable URL remains exact');
 assert.equal(f.run(f.full,destination,'--resume').status,0);f.commit();assert.equal(f.run(f.full,destination,'--resume').status,0);
});

test('native finalization refuses a missing bank or unknown/missing selector method before any output or adoption',async t=>{
 for(const change of ['missing-bank','missing-method','unknown-method']){
  const f=await nativeFixture(t);
  if(change==='missing-bank')fs.rmSync(path.join(f.root,f.bank),{recursive:true});
  else{const value=JSON.parse(fs.readFileSync(path.join(f.root,'data/ownership-selection.json')));if(change==='missing-method')delete value.method;else value.method='other';
   // Keep the prior sidecar base coherent so the ordinary native method guard,
   // rather than a stale whole pin, is the decisive refusal.
   const sidecar=f.reader().json(f.reader().pin(f.baseline,value.additive_release.path));sidecar.base_selection={...value};delete sidecar.base_selection.additive_release;
   f.write(value.additive_release.path,sidecar);const at=f.commit(),pin=f.reader().pin(at,value.additive_release.path);value.additive_release={path:pin.path,bytes:pin.bytes,sha256:pin.sha256};f.write('data/ownership-selection.json',value);
  }
  const at=f.commit(),config={...f.full,selector:f.reader().pin(at,'data/ownership-selection.json')};
  const before=fs.readFileSync(path.join(f.root,'data/ownership-selection.json')),definition=fs.readFileSync(path.join(f.root,'.github/package-inputs.json'));
  const result=f.run(config,'.cache/delivery-handoff/native-refused');assert.notEqual(result.status,0);assert.match(result.stderr,/Missing ordinary exact Git body|selector\/manifest method differs/);
  assert.equal(fs.existsSync(path.join(f.root,'.cache/delivery-handoff/native-refused')),false);
  assert.deepEqual(fs.readFileSync(path.join(f.root,'data/ownership-selection.json')),before);assert.deepEqual(fs.readFileSync(path.join(f.root,'.github/package-inputs.json')),definition);
  assert.equal(fs.existsSync(path.join(f.root,config.sidecar_output)),false);
 }
});

test('modern compact config resolves exact full pins and preserves legacy objects and canonical outputs', t => {
  const f = fixture(t), before = jsonBytes(f.compact);
  assert.deepEqual(resolveFinalizeConfig(f.compact, f.reader()), {...f.full,
    restored_read_roles: {commit: f.compact.composition.commit}});
  assert.strictEqual(resolveFinalizeConfig(f.full, f.reader()), f.full);
  assert.deepEqual(finalizeDelivery(f.compact, f.reader()), finalizeDelivery(f.full, f.reader()));
  assert.deepEqual(jsonBytes(f.compact), before);
});

test('cold CLI emits identical final products and resumes compact configuration exactly', t => {
  const f = fixture(t), destinations = ['full', 'compact'].map(name => '.cache/delivery-handoff/' + name);
  for (const [i, config] of [f.full, f.compact].entries()) {
    const result = f.run(config, destinations[i]); assert.equal(result.status, 0, result.stderr);
    f.commit(); // The next independent finalization starts with committed adoption.
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

test('compact finalization uses its committed composition for exact absent original roles', t => {
  const f = fixture(t), original = f.reader().json(f.full.registry).entries[0].rule_preimage;
  const filename = path.join(f.root, original.path), raw = fs.readFileSync(filename);
  fs.unlinkSync(filename);
  const missing = f.commit();
  fs.writeFileSync(filename, raw, {flag: 'wx'});
  f.write('coordination/engineering/unbound/snapshot-file.json', {unrelated: true});
  const restored = f.commit();
  const config = {...f.compact, new_prefix: PREFIX + 'compose/', sidecar_output: PREFIX + 'compose/sidecar.json',
    package_inputs: {...f.compact.package_inputs, commit: missing},
    composition: {...f.compact.composition, commit: restored}};
  const before = jsonBytes(config), destination = '.cache/delivery-handoff/composition-restoration';
  const result = f.run(config, destination); assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(jsonBytes(config), before, 'The caller does not supply or receive a second snapshot choice');
  const explicit = finalizeDelivery({...config, restored_read_roles: {commit: restored}}, f.reader());
  const output = name => fs.readFileSync(path.join(f.root, destination, name));
  const receipt = JSON.parse(output('preparation.json'));
  assert.deepEqual(Object.keys(receipt.outputs).sort(), Object.keys(explicit).sort());
  for (const [name, body] of Object.entries(explicit)) assert.deepEqual(output(name), body);
  const roles = JSON.parse(output('package-roles.json')).paths;
  assert.ok(roles.some(pin => pin.path === original.path && pin.sha256 === original.sha256));
  assert.ok(!roles.some(pin => pin.path.includes('/unbound/')));
  assert.ok(Object.keys(explicit).every(name => !name.includes('/')), 'No original-body copying');
  assert.deepEqual(fs.readFileSync(filename), raw);

  // The following independent snapshot refusals start from original selection,
  // not a committed sidecar generated by the preceding successful case.
  for (const pin of [f.full.selector, f.full.package_inputs])
    fs.writeFileSync(path.join(f.root, pin.path), f.reader().read(pin));
  fs.unlinkSync(path.join(f.root, config.sidecar_output));
  fs.unlinkSync(path.join(f.root, config.new_prefix, 'selected-delivery-expectations.json'));
  f.write(original.path, {retained: false});
  const changed = f.commit();
  fs.writeFileSync(filename, raw); fs.chmodSync(filename, 0o755);
  const executable = f.commit();
  const cases = [
    ['missing', {...config, composition: {...config.composition, commit: missing}}],
    ['changed', {...config, composition: {...config.composition, commit: changed}}],
    ['nonordinary', {...config, composition: {...config.composition, commit: executable}}],
    ['accepted-conflict', {...config, package_inputs: {...config.package_inputs, commit: changed}}],
    ['explicit-null', {...config, restored_read_roles: null}],
    ['explicit-missing', {...config, restored_read_roles: {commit: missing}}],
    ['explicit-incomplete', {...config, restored_read_roles: {commit: restored, paths: []}}]
  ];
  for (const [name, refusedConfig] of cases) {
    const refusedDestination = '.cache/delivery-handoff/composition-refused-' + name;
    const refused = f.run(refusedConfig, refusedDestination);
    assert.notEqual(refused.status, 0, name);
    assert.match(refused.stderr, /accepted path identity|restored read-role inventory/i, name);
    assert.equal(fs.existsSync(path.join(f.root, refusedDestination)), false, name);
  }
  // Start the independent override case from its original canonical preimages,
  // not the intervening deliberately invalid snapshot or a third selection.
  fs.chmodSync(filename, 0o644); fs.writeFileSync(filename, raw);
  for (const pin of [f.full.selector, f.full.package_inputs])
    fs.writeFileSync(path.join(f.root, pin.path), f.reader().read(pin));
  f.commit();
  const override = {...config, composition: {...config.composition, commit: missing},
    restored_read_roles: {commit: restored}};
  const overridden = f.run(override, '.cache/delivery-handoff/explicit-other-snapshot');
  assert.equal(overridden.status, 0, overridden.stderr);
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
test('actual selected-data classifier derives final-bank additions and exact prior-v2 retirements',async()=>{
  const bank='data/canonical-grid/current-startup/';
  const f=fixture({mutate(f){
    const fixed=['rows','runs','latitudes','old-promised'].map(name=>{
      const p=f.put(bank+name+'.bin',Buffer.from(name),true);return {path:name+'.bin',bytes:p.bytes,sha256:p.sha256};});
    const base={id:'geography:base',footprints_sha256:'b'.repeat(64),hierarchy_sha256:'c'.repeat(64)};
    for(const old of [true,false]){
      const label=old?'before':'after',tree=old?f.baseline:f.authored;
      const selectionRaw=f.blobs.get(tree.entries.get('data/ownership-selection.json').sha),selection=JSON.parse(selectionRaw);
      const active=['runs','context'].map(name=>{
        const p=f.put(bank+label+'/'+name+'.bin',Buffer.from(label+name),old);
        if(old)f.authored.entries.delete(p.path);
        return {path:label+'/'+name+'.bin',bytes:p.bytes,sha256:p.sha256};});
      const effective={...base,id:'geography:'+label,footprints_sha256:digest(Buffer.from(label))};
      f.put(bank+'index.json',{version:2,native_manifest_sha256:selection.sha256,
        release_id:effective.id,footprints_sha256:effective.footprints_sha256,hierarchy_sha256:effective.hierarchy_sha256,
        compatibility_files:fixed,files:[...fixed,...active],pixelMap:{parts:[fixed[0],active[0]]},
        additiveRelease:{base_reference:base,effective_reference:effective},preparedOwnership:{version:2,
          selection_sha256:digest(selectionRaw),native_manifest_sha256:selection.sha256,
          native_pixel_map:{canonical_grid_sha256:selection.sha256,parts:fixed.slice(0,2),
            native_latitudes:{transport_path:fixed[2].path,sha256:fixed[2].sha256}},
          context_parts:[active[1]],base_reference:base,effective_reference:effective}},old);
    }
    const additions=f.definition.inputs.slice(f.policy.inputs.length);
    f.policy.inputs.push(bank);f.definition.inputs=[...f.policy.inputs,...additions];
    f.put('.github/package-inputs.json',f.policy,true);f.put('.github/package-inputs.json',f.definition);
  }});
  f.files.push(...[...f.baseline.entries.keys()].filter(name=>!f.authored.entries.has(name)).map(filename=>({filename,status:'removed'})));
  const reasons=[];
  assert.deepEqual(await f.run({onReject:r=>reasons.push(r)}),{test_selection:'selected-data',expectations_path:prefix+'selected-delivery-expectations.json',shards:[0]},reasons.join('; '));
  const old=f.authored.entries.get(bank+'old-promised.bin');f.authored.entries.delete(old.path);
  f.files.push({filename:old.path,status:'removed'});
  assert.equal(await f.run(),null,'A fixed prior URL cannot be removed with the derived retirement set');
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
  f.write('coordination/engineering/unbound/snapshot-file.json', {unrelated: true});
  const restored = f.commit();
  config.restored_read_roles = {commit: restored, paths: [original.path]};
  const result = f.run(config, '.cache/delivery-handoff/restored');
  assert.equal(result.status, 0, result.stderr);
  const receipt = JSON.parse(fs.readFileSync(path.join(f.root, '.cache/delivery-handoff/restored/preparation.json')));
  assert.ok(Object.keys(receipt.outputs).every(name => !name.includes('/')));
  assert.deepEqual(fs.readFileSync(filename), raw);

  f.commit(); // Preserve exact adopted outputs before a fresh finalization.
  const derivedConfig = {...config, restored_read_roles: {commit: restored}};
  const derived = f.run(derivedConfig, '.cache/delivery-handoff/derived-restoration');
  assert.equal(derived.status, 0, derived.stderr);
  const derivedRoot = path.join(f.root, '.cache/delivery-handoff/derived-restoration');
  const derivedReceipt = JSON.parse(fs.readFileSync(path.join(derivedRoot, 'preparation.json')));
  assert.deepEqual(derivedReceipt.outputs, receipt.outputs);
  for (const name of Object.keys(receipt.outputs))
    assert.deepEqual(fs.readFileSync(path.join(derivedRoot, name)),
      fs.readFileSync(path.join(f.root, '.cache/delivery-handoff/restored', name)));
  assert.ok(!JSON.parse(fs.readFileSync(path.join(derivedRoot, 'package-roles.json'))).paths
    .some(pin => pin.path.includes('/unbound/')));
  const missingDerived = f.run({...derivedConfig, restored_read_roles: {commit: missing}},
    '.cache/delivery-handoff/derived-missing');
  assert.notEqual(missingDerived.status, 0);
  assert.equal(fs.existsSync(path.join(f.root, '.cache/delivery-handoff/derived-missing')), false);

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
  const changedDerived = f.run({...derivedConfig, restored_read_roles: {commit: changed}},
    '.cache/delivery-handoff/derived-changed');
  assert.notEqual(changedDerived.status, 0);
  assert.match(changedDerived.stderr, /Restored snapshot differs/);
  assert.equal(fs.existsSync(path.join(f.root, '.cache/delivery-handoff/derived-changed')), false);

  const currentConflict = f.run({...derivedConfig, package_inputs: read().pin(changed, '.github/package-inputs.json')},
    '.cache/delivery-handoff/derived-current-conflict');
  assert.notEqual(currentConflict.status, 0);
  assert.match(currentConflict.stderr, /Original consumed role differs from accepted path/);
  assert.equal(fs.existsSync(path.join(f.root, '.cache/delivery-handoff/derived-current-conflict')), false);
  assert.deepEqual(fs.readFileSync(filename), changedRaw);
});


test('next native finalization retires only prior v2 context with exact preimages and resumable selector-last adoption',async t=>{
 const f=await nativeFixture(t),first=f.run(f.full,'.cache/delivery-handoff/first');assert.equal(first.status,0,first.stderr);f.commit();
 const indexPath=f.bank+'index.json',index=JSON.parse(fs.readFileSync(path.join(f.root,indexPath)));
 const originalPart=index.preparedOwnership.context_parts[0],oldBody=fs.readFileSync(path.join(f.root,f.bank,originalPart.path));
 // A valid prior encoder emitted the exact same context at another gzip level.
 // The current encoder will restore its existing encoding and retire this URL.
 const alternate=gzipSync(gunzipSync(oldBody),{level:1}),oldPath='geography/effective-context-'+digest(alternate)+'.json.gz';
 assert.notEqual(digest(alternate),digest(oldBody));
 const previousPart={...originalPart,path:oldPath,bytes:alternate.length,sha256:digest(alternate)};
 f.save(f.bank+oldPath,alternate);fs.unlinkSync(path.join(f.root,f.bank,originalPart.path));
 index.preparedOwnership.context_parts[0]=previousPart;
 index.files=index.files.filter(p=>p.path!==originalPart.path).concat({path:oldPath,bytes:alternate.length,sha256:digest(alternate)}).sort((a,b)=>a.path.localeCompare(b.path));
 f.write(indexPath,index);const accepted=f.commit(),reader=f.reader();
 const config={...f.full,selector:reader.pin(accepted,'data/ownership-selection.json'),package_inputs:reader.pin(accepted,'.github/package-inputs.json'),
   new_prefix:PREFIX+'next/',sidecar_output:PREFIX+'next/sidecar.json'};
 const baseline=new Map(['data/ownership-selection.json','.github/package-inputs.json',indexPath].map(name=>[name,fs.readFileSync(path.join(f.root,name))]));
 const oldFile=path.join(f.root,f.bank,oldPath);
 for(const kind of ['edited','linked','missing']){
   if(kind==='edited')fs.writeFileSync(oldFile,Buffer.concat([alternate,Buffer.from('changed')]));
   if(kind==='linked'){fs.unlinkSync(oldFile);fs.symlinkSync(path.join(f.root,'data/ownership-selection.json'),oldFile);}
   if(kind==='missing')fs.unlinkSync(oldFile);
   const destination='.cache/delivery-handoff/retire-'+kind,result=f.run(config,destination);
   assert.notEqual(result.status,0,result.stdout);assert.match(result.stderr,/Canonical output|Nonordinary|Missing canonical/);
   assert.equal(fs.existsSync(path.join(f.root,destination)),false,'Complete retirement preflight precedes staging');
   for(const [name,raw]of baseline)assert.deepEqual(fs.readFileSync(path.join(f.root,name)),raw);
   if(fs.existsSync(oldFile)||kind==='linked')fs.unlinkSync(oldFile);f.save(f.bank+oldPath,alternate);
 }
 const destination='.cache/delivery-handoff/retire',result=f.run(config,destination);assert.equal(result.status,0,result.stderr);
 assert.equal(fs.existsSync(oldFile),false);assert.deepEqual(fs.readFileSync(path.join(f.root,f.bank,originalPart.path)),oldBody);
 const finalIndex=JSON.parse(fs.readFileSync(path.join(f.root,indexPath)));
 assert.deepEqual(finalIndex.compatibility_files,f.originalIndex.files);
 for(const pin of finalIndex.compatibility_files)assert.equal(digest(fs.readFileSync(path.join(f.root,f.bank,pin.path))),pin.sha256);
 // Simulate the published-output/exact-adoption mixture an interrupted writer
 // leaves before its final selector rename, including an already removed member.
 for(const [name,raw]of baseline)f.save(name,raw);
 assert.notEqual(f.run(config,destination).status,0);
 const resumed=f.run(config,destination,'--resume');assert.equal(resumed.status,0,resumed.stderr);
 assert.equal(fs.existsSync(oldFile),false);
 const selector=fs.readFileSync(path.join(f.root,'data/ownership-selection.json'));
 assert.equal(JSON.parse(fs.readFileSync(path.join(f.root,indexPath))).preparedOwnership.selection_sha256,digest(selector));
 f.commit();assert.equal(f.run(config,destination,'--resume').status,0,'Committed exact retirement is idempotent');
});
