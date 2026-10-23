import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {gzipSync,gunzipSync} from 'node:zlib';
import {sha256} from '../scripts/evidence-quality.mjs';
import {runSelectedDeliverySmoke, checkEmittedSelectedDelivery, verifySelectedDelivery, selectedStableOwnerControls} from '../scripts/selected-delivery-smoke.mjs';
import {packOwnership} from '../src/pixel-ownership.js';
import {shuffleOwnershipBytes} from '../src/ownership-codec.js';
import {loadOwnershipAssets} from '../src/ownership-assets.js';
import {packageStartupOwnership,packageFinalStartupOwnership,packagePreparedStartupOwnership} from '../scripts/package-startup-ownership.mjs';
import {prepareSelectedStartupOwnership} from '../scripts/prepare-startup-ownership.mjs';
import {footprintValueSha256 as geometryHash, loadedBaseFootprintSha256,
  additiveReleaseFootprintDigest, loadAdditiveNativePatch} from '../src/effective-footprint.js';

const script = fileURLToPath(new URL('../scripts/selected-delivery-smoke.mjs', import.meta.url));
const rectangle = (a, b, c, d) => ({type: 'Polygon', coordinates: [[[a,b],[c,b],[c,d],[a,d],[a,b]]]});
const json = value => Buffer.from(JSON.stringify(value) + '\n');
const asset = (name, bytes) => ({path: name, bytes: bytes.length, sha256: sha256(bytes)});
const pin = (name, bytes) => ({...asset(name, bytes), commit: '1'.repeat(40), mode: '100644', git_blob_oid: '2'.repeat(40)});

// Tiny synthetic world, full canonical row-table dimensions. All loaders,
// effective geometry validation, integer picking and sampling are production
// functions; no scientific result or real geography is inferred from fixtures.
function fixture(t, changes = {}) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'selected-delivery-smoke-'));
  t.after(() => fs.rmSync(directory, {recursive: true, force: true}));
  const root = path.join(directory, 'root'), emittedDirectory = path.join(directory, 'emitted');
  fs.mkdirSync(root); fs.mkdirSync(emittedDirectory);
  const write = (base, name, bytes) => {
    const filename = path.join(base, name); fs.mkdirSync(path.dirname(filename), {recursive: true});
    fs.writeFileSync(filename, bytes); return asset(name, bytes);
  };
  const originalFeatures = [
    {id: 'target', pixelIndex: 1, geometry: rectangle(0,0,1,1), properties: {parent_id: 'province-1'}},
    {id: 'stable', pixelIndex: 2, geometry: rectangle(5,0,6,1), properties: {parent_id: 'province-2'}}
  ];
  const baseReference = {id: 'geography:base', footprints_sha256: loadedBaseFootprintSha256(originalFeatures),
    hierarchy_sha256: 'a'.repeat(64)};
  // Historical provenance remains an inert pin; routine consumption never opens it.
  const certificateBytes = json({historical: 'not a routine smoke input'});
  const components = [
    {component_id: 'component-a', disposition: 'assigned', native_cells: 2, geometry: rectangle(1,0,2,1)},
    {component_id: 'component-b', disposition: 'zero-cell', native_cells: 0, geometry: rectangle(3,0,4,1)}
  ].map(row => ({...row, target_id: 'target', pixelIndex: 1, base_geometry: originalFeatures[0].geometry,
    base_geometry_sha256: geometryHash(originalFeatures[0].geometry), geometry_sha256: geometryHash(row.geometry),
    source_receipt_sha256: 'b'.repeat(64), authority_sha256: 'c'.repeat(64), rule_sha256: 'd'.repeat(64)}));
  const ledger = {version: 2, kind: 'native-additive-repair-ledger-v2', authority_registry_sha256: 'e'.repeat(64),
    parent_inventory: {components: 2, report_sha256: 'f'.repeat(64), roster_sha256: '0'.repeat(64)},
    scope_ids: components.map(row => row.component_id), rows: components,
    current_rebind: pin('rebind/certificate.json', certificateBytes),
    current_targets: [{target_id: 'target', pixelIndex: 1, geometry: originalFeatures[0].geometry,
      geometry_sha256: geometryHash(originalFeatures[0].geometry)}]};
  changes.ledger?.(ledger);
  const rawLedger = json(ledger);
  const ledgerBody = changes.ledgerBytes === undefined ? rawLedger
    : Buffer.concat([rawLedger, Buffer.alloc(changes.ledgerBytes - rawLedger.length, 32)]);
  const ledgerPin = write(emittedDirectory, 'additive-repairs/ledger.json', ledgerBody);
  const effectiveFeatures = structuredClone(originalFeatures);
  effectiveFeatures[0].additiveFootprint = {version: 2, kind: 'retained-base-plus-additions',
    baseline_release_sha256: baseReference.footprints_sha256, base_geometry_sha256: components[0].base_geometry_sha256,
    ledger_sha256: ledgerPin.sha256, authority_registry_sha256: ledger.authority_registry_sha256, components};
  // Keep fixture generation independent of candidate ledger mutations.
  const effectiveReference = {...baseReference, id: 'geography:effective',
    footprints_sha256: additiveReleaseFootprintDigest(baseReference, effectiveFeatures)};
  const patch = {version: 2, kind: 'unassigned-native-cells-v1', base_reference: baseReference,
    effective_reference: effectiveReference, ledger_sha256: ledgerPin.sha256,
    authority_registry_sha256: ledger.authority_registry_sha256, rows: [{y: 3, runs: [[3,5,1]]}]};
  changes.patch?.(patch);
  const patchPin = write(emittedDirectory, 'additive-repairs/patch.json', json(patch));
  const rows = Array(262166).fill(new Uint32Array());
  rows[3] = Uint32Array.from([1,2,1,8,10,2]); rows[4] = Uint32Array.from([7,8,2]);
  const packed = packOwnership({size: rows.length, rows});
  const parts = ['rows', 'runs'].map(kind => {
    const bytes = Buffer.from(packed[kind].buffer);
    return {...write(emittedDirectory, `ownership/${kind}.bin.gz`, gzipSync(bytes)), kind, offset: 0,
      words: packed[kind].length, encoding: 'uint32-le', decoded_bytes: bytes.length, decoded_sha256: sha256(bytes)};
  });
  const rosterBytes = json(originalFeatures.map(feature => ({id: feature.id, index: feature.pixelIndex,
    province_id: feature.properties.parent_id, bounds: [0,0,10,10]})));
  const rosterPin = {...write(emittedDirectory, 'additive-repairs/owners.json.gz', gzipSync(rosterBytes)),
    encoding: 'gzip', decoded_bytes: rosterBytes.length, decoded_sha256: sha256(rosterBytes)};
  const manifest = {...baseReference, geographic_release: baseReference.id, method: 'native-linear-evenodd-first-owner-v1',
    size: packed.size, coordinateBits: packed.coordinateBits, parts, original_assets: {bounds: {sha256: rosterPin.sha256}}};
  const manifestPin = write(emittedDirectory, 'additive-repairs/base-manifest.json', json(manifest));
  const envelope = {version: 2, kind: 'retained-native-base-plus-delta-v2', base_reference: baseReference,
    effective_reference: effectiveReference, ledger: ledgerPin, patch: patchPin, owner_roster: rosterPin, base_manifest: manifestPin};
  const envelopePin = write(root, 'selection/envelope.json', json(envelope));
  const sidecarPin = write(root, 'selection/sidecar.json', json({runtime_envelope: envelopePin}));
  write(root, 'data/ownership-selection.json', json({additive_release: sidecarPin}));
  const catalog = originalFeatures.map(feature => ({...feature, geometry: null}));
  changes.catalog?.(catalog);
  write(emittedDirectory, 'geography/catalog.json.gz', gzipSync(json(catalog)));
  const atlas = {parts: ['geography/catalog.json.gz'], reference_release: effectiveReference, additiveRelease: envelope,
    pixelMap: {...baseReference, geographic_release: baseReference.id, version: 2, size: packed.size,
      coordinateBits: packed.coordinateBits, method: manifest.method, runWords: packed.runs.length, parts,
      canonical_grid_sha256: manifestPin.sha256,
      native_latitudes: {root: 'repository', role: 'immutable-normative-rule-input',
        path: 'coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz',
        commit: '1'.repeat(40), sha256: '2'.repeat(64), bytes: 1, decoded_bytes: packed.size * 8,
        decoded_sha256: '66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23'}}};
  write(emittedDirectory, 'atlas-geography.json', json(atlas));
  const expectations = {version: 1, selected_ledger_sha256: ledgerPin.sha256, cumulative_native_cells: 2,
    cohorts: [{original_batch_id: 'original-batch-fixture', component_ids: components.map(row => row.component_id),
      members: components.map(({component_id,target_id,disposition,geometry_sha256}) =>
        ({component_id,target_id,disposition,geometry_sha256}))}]};
  changes.expectations?.(expectations);
  const expectationsPath = path.join(directory, 'expectations.json'), outputPath = path.join(directory, 'report.json');
  fs.writeFileSync(expectationsPath, json(expectations));
  return {directory, root, emittedDirectory, expectationsPath, outputPath, expectations, atlas, ledger, patch,
    options: {root, emittedDirectory, expectationsPath, outputPath},
    async kernel() {
      const fetcher = async name => new Response(fs.readFileSync(path.join(emittedDirectory, name)));
      const base = await loadOwnershipAssets(atlas.pixelMap, fetcher), features = structuredClone(catalog);
      const beforeControls = selectedStableOwnerControls(base, patch);
      const effective = await loadAdditiveNativePatch(atlas, features, base, {fetcher});
      return {expectations, ledger, ledgerSha256: ledgerPin.sha256, patch, patchSha256: patchPin.sha256,
        features, base, effective, beforeControls};
    }};
}

test('actual CLI checks complete mixed assigned/zero-cell cohort, every new cell and stable rows', t => {
  const f = fixture(t);
  assert.equal(fs.existsSync(path.join(f.root,'rebind')),false,'Routine smoke fixture contains no historical rebind files');
  const stdout = execFileSync(process.execPath, [script, '--root', f.root, '--emitted-directory', f.emittedDirectory,
    '--expectations', f.expectationsPath, '--output', f.outputPath], {encoding: 'utf8'});
  const report = JSON.parse(fs.readFileSync(f.outputPath));
  assert.deepEqual(JSON.parse(stdout), report);
  assert.equal(report.passed, true); assert.equal(report.feature_count, 2);
  assert.equal(report.cumulative_native_cells_picked_and_sampled, 2);
  assert.equal(report.stable_owner_controls, 1); assert.equal(report.expected_components_verified, 2);
  assert.equal(report.expectations_sha256, sha256(fs.readFileSync(f.expectationsPath)));
  assert(report.inputs.some(input => input.path === 'ownership/runs.bin.gz'));
  for (const input of report.inputs) {
    const bytes = fs.readFileSync(path.join(input.scope === 'root' ? f.root : f.emittedDirectory, input.path));
    assert.equal(input.bytes, bytes.length); assert.equal(input.sha256, sha256(bytes));
  }
  assert.match(report.limitation, /GPU and Canvas/); assert.match(report.limitation, /supplied reviewed expectations/);
});

test('actual CLI admits an exact 34920857-byte emitted ledger and refuses whole-file drift', async t => {
  // Same-size synthetic ledger, padded with valid JSON whitespace. This tests
  // transport/consumer capacity; it is not the reviewed geographic ledger.
  const f = fixture(t, {ledgerBytes: 34920857});
  execFileSync(process.execPath, [script, '--root', f.root, '--emitted-directory', f.emittedDirectory,
    '--expectations', f.expectationsPath, '--output', f.outputPath], {stdio: 'pipe'});
  const report = JSON.parse(fs.readFileSync(f.outputPath));
  const name = 'additive-repairs/ledger.json', filename = path.join(f.emittedDirectory, name);
  const original = fs.readFileSync(filename), input = report.inputs.find(row => row.path === name);
  assert.equal(report.passed, true); assert.equal(report.cumulative_native_cells_picked_and_sampled, 2);
  assert.equal(input.bytes, 34920857); assert.equal(input.sha256, sha256(original));
  assert.equal(fs.existsSync(path.join(f.root, 'rebind')), false);
  const corrupt = Buffer.from(original); corrupt[corrupt.length - 1] = 9;
  for (const [label, body, error] of [
    ['truncated', original.subarray(0, -1), /exact file budget/],
    ['excess', Buffer.concat([original, Buffer.from(' ')]), /exact file budget/],
    ['hash', corrupt, /Whole asset hash differs/]
  ]) {
    fs.writeFileSync(filename, body);
    const outputPath = path.join(f.directory, label + '.json');
    await assert.rejects(runSelectedDeliverySmoke({...f.options, outputPath}), error);
    assert.equal(fs.existsSync(outputPath), false);
  }
  fs.writeFileSync(filename, original);
  assert.equal(sha256(fs.readFileSync(filename)), input.sha256);
});

const invalidExpectations = [
  ['wrong ledger hash', x => x.selected_ledger_sha256 = '9'.repeat(64), /ledger hash/],
  ['wrong cumulative count', x => x.cumulative_native_cells++, /native cell count/],
  ['duplicate member', x => x.cohorts[0].members.push(x.cohorts[0].members[0]), /duplicate expected member/],
  ['missing member', x => x.cohorts[0].members.pop(), /complete component roster/],
  ['duplicate roster', x => x.cohorts[0].component_ids.push('component-a'), /Duplicate/],
  ['duplicate batch', x => x.cohorts.push(structuredClone(x.cohorts[0])), /duplicate original batch/],
  ['wrong target', x => x.cohorts[0].members[0].target_id = 'stable', /target_id differs/],
  ['wrong disposition', x => x.cohorts[0].members[0].disposition = 'zero-cell', /disposition differs/],
  ['wrong geometry', x => x.cohorts[0].members[0].geometry_sha256 = '9'.repeat(64), /geometry_sha256 differs/],
  ['empty cohorts', x => x.cohorts = [], /Missing expected cohorts/],
  ['undeclared field', x => x.skip_missing_assets = true, /missing\/foreign/]
];
for (const [label, edit, error] of invalidExpectations) test(`smoke rejects ${label} without creating output`, async t => {
  const f = fixture(t, {expectations: edit});
  await assert.rejects(runSelectedDeliverySmoke(f.options), error);
  assert.equal(fs.existsSync(f.outputPath), false);
});

test('actual kernel rejects missing/duplicate selected rows, target drift and omitted effective primitive', async t => {
  const f = fixture(t);
  for (const edit of [
    state => {state.ledger.rows.pop(); state.ledger.scope_ids.pop();},
    state => {state.ledger.rows.push(state.ledger.rows[0]); state.ledger.scope_ids.push('component-a');},
    state => {state.features[0].id = 'foreign';},
    state => {state.features[0].additiveFootprint.components.pop();},
    state => {state.features[0].additiveFootprint.components[0].geometry = rectangle(20,0,21,1);}
  ]) {
    const state = structuredClone(await f.kernel()); edit(state);
    assert.throws(() => verifySelectedDelivery(state));
  }
});

test('saved before-state controls reject real owner mutation without changing added cells', async t => {
  const f = fixture(t);
  for (const role of ['base','effective']) {
    const state = await f.kernel();
    const control = state.beforeControls[0], grid = state[role];
    if (role === 'base') grid.runs[grid.rows[control.y * 2] * 2] += 2 ** grid.coordinateBits;
    else {
      // The runtime coalesces old/new equal-owner intervals. Split only the
      // before-state interval so corrupting it leaves both added cells correct.
      const rows = Array(grid.size).fill(new Uint32Array());
      rows[3] = Uint32Array.from([1,3,2,3,5,1,8,10,2]);
      rows[4] = Uint32Array.from([7,8,2]);
      Object.assign(grid, packOwnership({size:grid.size, rows}));
    }
    assert.throws(() => verifySelectedDelivery(state), /Stable (base|effective) owner changed/);
  }
  const state = await f.kernel(); state.beforeControls = [];
  assert.throws(() => verifySelectedDelivery(state), /Missing occupied base owner control/);
});

test('current base controls use every affected occupied row and a nonvacuous fallback', async t => {
  const f = fixture(t), {base} = await f.kernel();
  assert.deepEqual(selectedStableOwnerControls(base,{rows:[{y:3},{y:4}]}),
    [{x:1,y:3,id:1},{x:7,y:4,id:2}]);
  assert.deepEqual(selectedStableOwnerControls(base,{rows:[{y:1}]}),[{x:1,y:3,id:1}]);
  assert.throws(() => selectedStableOwnerControls({...base,rows:new Uint32Array(base.rows.length)},
    {rows:[{y:1}]}), /Missing occupied base owner control/);
});

test('actual loaded target custody agrees with the current pinned roster', async t => {
  const wrongParent = fixture(t, {catalog: features => features[0].properties.parent_id = 'foreign'});
  await assert.rejects(runSelectedDeliverySmoke(wrongParent.options), /owner or parent/);
  assert.equal(fs.existsSync(wrongParent.outputPath), false);
});

test('actual loader rejects additions over already occupied native cells', async t => {
  const f = fixture(t, {patch: patch => patch.rows[0].runs = [[1,4,1]]});
  await assert.rejects(runSelectedDeliverySmoke(f.options), /replace an assigned cell/);
  assert.equal(fs.existsSync(f.outputPath), false);
});

test('whole-file checks reject corrupted assets, absent assets, path traversal and symlinks', async t => {
  for (const name of ['ownership/runs.bin.gz', 'additive-repairs/ledger.json', 'additive-repairs/base-manifest.json']) {
    const f = fixture(t), filename = path.join(f.emittedDirectory, name), bytes = fs.readFileSync(filename);
    bytes[0] ^= 1; fs.writeFileSync(filename, bytes);
    await assert.rejects(runSelectedDeliverySmoke(f.options), /Whole asset hash differs/);
    assert.equal(fs.existsSync(f.outputPath), false);
  }
  const missing = fixture(t); fs.unlinkSync(path.join(missing.emittedDirectory, 'ownership/rows.bin.gz'));
  await assert.rejects(runSelectedDeliverySmoke(missing.options), /ENOENT/);
  const traversal = fixture(t); traversal.atlas.parts = ['../expectations.json'];
  fs.writeFileSync(path.join(traversal.emittedDirectory, 'atlas-geography.json'), json(traversal.atlas));
  await assert.rejects(runSelectedDeliverySmoke(traversal.options), /Unsafe evidence path/);
  const linked = fixture(t), name = path.join(linked.emittedDirectory, 'ownership/runs.bin.gz');
  fs.renameSync(name, name + '.original'); fs.symlinkSync(name + '.original', name);
  await assert.rejects(runSelectedDeliverySmoke(linked.options), /without symlinks/);
});

test('every output collision and symlink rejects before work and preserves originals', async t => {
  for (const mode of ['file', 'dangling', 'directory', 'parent']) {
    const f = fixture(t), sentinel = path.join(f.directory, 'sentinel'); fs.writeFileSync(sentinel, 'unchanged');
    if (mode === 'file') fs.writeFileSync(f.outputPath, 'unchanged');
    if (mode === 'dangling') fs.symlinkSync(path.join(f.directory, 'absent'), f.outputPath);
    if (mode === 'directory') fs.mkdirSync(f.outputPath);
    if (mode === 'parent') {
      const link = path.join(f.directory, 'linked'); fs.symlinkSync(f.directory, link);
      f.options.outputPath = path.join(link, 'new-report.json');
    }
    await assert.rejects(runSelectedDeliverySmoke(f.options), /Output collision|symlink parent/);
    assert.equal(fs.readFileSync(sentinel, 'utf8'), 'unchanged');
    if (mode === 'file') assert.equal(fs.readFileSync(f.outputPath, 'utf8'), 'unchanged');
    if (mode === 'dangling') assert(fs.lstatSync(f.outputPath).isSymbolicLink());
    assert.equal(fs.existsSync(path.join(f.directory, 'new-report.json')), false);
  }
});

test('CLI fails on missing required arguments and duplicate/unknown options', () => {
  for (const args of [[], ['--unknown', 'x'], ['--output'], ['--root', 'a', '--root', 'b']])
    assert.throws(() => execFileSync(process.execPath, [script, ...args], {stdio: 'pipe'}));
});

async function startupFixture(t) {
  const f = fixture(t);
  fs.mkdirSync(path.join(f.emittedDirectory, 'native-v1/ownership'), {recursive: true});
  for (const part of f.atlas.pixelMap.parts) {
    const name = `native-v1/ownership/${part.kind}-0.bin.gz`;
    fs.renameSync(path.join(f.emittedDirectory, part.path), path.join(f.emittedDirectory, name));
    part.path = name;
  }
  const packaged = await packageStartupOwnership({manifest: f.atlas.pixelMap,
    source: f.emittedDirectory, destination: f.emittedDirectory});
  f.atlas.pixelMap = {...packaged.pixelMap, canonical_grid_sha256: f.atlas.pixelMap.canonical_grid_sha256};
  fs.writeFileSync(path.join(f.emittedDirectory, 'atlas-geography.json'), json(f.atlas));
  return f;
}

test('genuine startup native descriptor without encoded bytes passes with actual whole-file hash and size', async t => {
  const f = await startupFixture(t), run = f.atlas.pixelMap.parts.find(part => part.kind === 'runs');
  assert.equal(Object.hasOwn(run, 'bytes'), false);
  const report = await runSelectedDeliverySmoke(f.options);
  const observed = report.inputs.find(input => input.scope === 'emitted' && input.path === run.path);
  const bytes = fs.readFileSync(path.join(f.emittedDirectory, run.path));
  assert.equal(observed.bytes, bytes.length); assert.equal(observed.sha256, sha256(bytes));
  assert.equal(observed.sha256, run.sha256); assert.equal(report.cumulative_native_cells_picked_and_sampled, 2);
});

test('genuine startup native descriptor still rejects wrong encoded SHA and missing selected custody bytes', async t => {
  const f = await startupFixture(t), run = f.atlas.pixelMap.parts.find(part => part.kind === 'runs');
  run.sha256 = '9'.repeat(64);
  fs.writeFileSync(path.join(f.emittedDirectory, 'atlas-geography.json'), json(f.atlas));
  await assert.rejects(runSelectedDeliverySmoke(f.options), /Whole asset hash differs/);
  assert.equal(fs.existsSync(f.outputPath), false);
  const custody = fixture(t);
  const selectionFile = path.join(custody.root, 'data/ownership-selection.json');
  const selection = JSON.parse(fs.readFileSync(selectionFile)); delete selection.additive_release.bytes;
  fs.writeFileSync(selectionFile, json(selection));
  await assert.rejects(runSelectedDeliverySmoke(custody.options), /Missing whole-file asset pin/);
  assert.equal(fs.existsSync(custody.outputPath), false);
});


test('actual emitted smoke keeps distinct authority pointsets with the same original component label', async t => {
  const f = fixture(t, {
    ledger: ledger => {
      ledger.rows[1].component_id = ledger.rows[0].component_id;
      ledger.rows[1].authority_sha256 = 'f'.repeat(64);
      ledger.scope_ids = ledger.rows.map(row => row.component_id);
    },
    expectations: expected => {
      expected.cohorts = expected.cohorts[0].members.map((member, i) => ({
        original_batch_id: 'retained-authority-scope:' + (i ? 'f' : 'c').repeat(64),
        component_ids: [member.component_id], members: [member]
      }));
    }
  });
  const options = {root:f.root,emittedDirectory:f.emittedDirectory,expectationsPath:f.expectationsPath,outputPath:f.outputPath};
  const report = await runSelectedDeliverySmoke(options);
  assert.equal(report.expected_components_verified, 2);
  assert.equal(report.cumulative_native_cells_picked_and_sampled, 2);
  const args = await f.kernel();
  const ambiguous = structuredClone(args.expectations); ambiguous.cohorts[0].original_batch_id = 'legacy-ambiguous';
  assert.throws(() => verifySelectedDelivery({...args,expectations:ambiguous}), /ambiguous/);
  const wrong = structuredClone(args.expectations); wrong.cohorts[0].original_batch_id = 'retained-authority-scope:' + 'a'.repeat(64);
  assert.throws(() => verifySelectedDelivery({...args,expectations:wrong}), /ambiguous/);
});

function gzipEmittedLedgerPatch(f){
 for(const role of ['ledger','patch']){
  const original=f.atlas.additiveRelease[role],file=path.join(f.emittedDirectory,original.path),body=fs.readFileSync(file),raw=gzipSync(body),name=original.path+'.gz';
  f.atlas.additiveRelease[role]={...asset(name,raw),encoding:'gzip',decoded_bytes:body.length,decoded_sha256:sha256(body)};
  fs.writeFileSync(path.join(f.emittedDirectory,name),raw);fs.unlinkSync(file);
 }
 fs.writeFileSync(path.join(f.emittedDirectory,'atlas-geography.json'),json(f.atlas));
}

test('actual CLI authenticates derived gzip against unchanged selected science and all native cells',t=>{
 const f=fixture(t),source=fs.readFileSync(path.join(f.root,'selection/envelope.json'));
 gzipEmittedLedgerPatch(f);
 const stdout=execFileSync(process.execPath,[script,'--root',f.root,'--emitted-directory',f.emittedDirectory,'--expectations',f.expectationsPath,'--output',f.outputPath],{encoding:'utf8'});
 const report=JSON.parse(stdout);assert.equal(report.passed,true);assert.equal(report.cumulative_native_cells_picked_and_sampled,2);
 assert.equal(report.selected_ledger_sha256,f.expectations.selected_ledger_sha256);
 assert.deepEqual(fs.readFileSync(path.join(f.root,'selection/envelope.json')),source);
 for(const role of ['ledger','patch'])assert(report.inputs.some(pin=>pin.path===f.atlas.additiveRelease[role].path&&pin.sha256===f.atlas.additiveRelease[role].sha256));
});

test('emitted gzip refuses changed source identity, encoded bytes, decoded bytes and semantic envelope',async t=>{
 const f=fixture(t);gzipEmittedLedgerPatch(f);const atlasFile=path.join(f.emittedDirectory,'atlas-geography.json'),original=structuredClone(f.atlas);
 const role='ledger',pin=original.additiveRelease[role],file=path.join(f.emittedDirectory,pin.path),encoded=fs.readFileSync(file),body=json(f.ledger);
 let count=0;
 const refuse=async error=>{const outputPath=path.join(f.directory,'refusal-'+(++count)+'.json');await assert.rejects(runSelectedDeliverySmoke({...f.options,outputPath}),error);assert.equal(fs.existsSync(outputPath),false);};
 fs.writeFileSync(file,encoded.subarray(0,-1));await refuse(/exact file budget/);fs.writeFileSync(file,encoded);
 for(const changed of [body.subarray(0,-1),Buffer.concat([body,Buffer.from(' ')]),Buffer.concat([body.subarray(0,-1),Buffer.from('\t')])]){
  const raw=gzipSync(changed),atlas=structuredClone(original);Object.assign(atlas.additiveRelease.ledger,{bytes:raw.length,sha256:sha256(raw)});
  fs.writeFileSync(file,raw);fs.writeFileSync(atlasFile,json(atlas));await refuse(/Decoded whole asset (bytes|hash) differ/);
 }
 fs.writeFileSync(file,encoded);
 for(const change of [a=>a.additiveRelease.ledger.decoded_sha256='0'.repeat(64),a=>a.additiveRelease.ledger.path='additive-repairs/foreign.json.gz',a=>a.additiveRelease.base_reference.id='geography:foreign']){
  const atlas=structuredClone(original);change(atlas);fs.writeFileSync(atlasFile,json(atlas));await refuse(/differs/);
 }
 fs.writeFileSync(atlasFile,json(original));
});


for(const gzip of [false,true])test('shared full-output consumer authenticates actual cells without inventing reviewed expectations, gzip='+gzip,async t=>{
 const f=fixture(t),source=fs.readFileSync(path.join(f.root,'selection/envelope.json'));
 if(gzip)gzipEmittedLedgerPatch(f);
 const options={root:f.root,emittedDirectory:f.emittedDirectory};
 const generic=await checkEmittedSelectedDelivery(options);
 assert.equal(generic.kind,'actual-emitted-additive-consumer');
 assert.equal(generic.cumulative_native_cells_picked_and_sampled,2);
 assert.equal(generic.stable_owner_controls,1);
 assert.equal(generic.selected_ledger_sha256,f.expectations.selected_ledger_sha256);
 for(const field of ['cohorts','expected_components_verified','expectations_sha256'])assert.equal(Object.hasOwn(generic,field),false);
 assert.equal(fs.existsSync(f.outputPath),false,'Generic verification writes no receipt');
 const reviewed=await runSelectedDeliverySmoke(f.options);
 for(const field of ['feature_count','selected_ledger_sha256','selected_patch_sha256','cumulative_native_cells_picked_and_sampled','stable_owner_controls','inputs'])
  assert.deepEqual(generic[field],reviewed[field]);
 assert.equal(reviewed.expected_components_verified,2);
 assert.deepEqual(fs.readFileSync(path.join(f.root,'selection/envelope.json')),source);
 const descriptor=f.atlas.additiveRelease.ledger,filename=path.join(f.emittedDirectory,descriptor.path),body=fs.readFileSync(filename);
 const corrupt=Buffer.from(body);corrupt[corrupt.length-1]^=1;fs.writeFileSync(filename,corrupt);
 await assert.rejects(checkEmittedSelectedDelivery(options),/Whole asset hash differs/);
});

test('selected-map CLI and kernel still require independent expectations',async t=>{
 const f=fixture(t);
 await assert.rejects(runSelectedDeliverySmoke({...f.options,expectationsPath:undefined}),/Missing expectations path/);
 assert.equal(fs.existsSync(f.outputPath),false);
 assert.throws(()=>verifySelectedDelivery({expectations:undefined}),/Expectations must be an object/);
});


async function finalFixture(t,{gzipProducts=false}={}) {
  const f=fixture(t);if(gzipProducts)gzipEmittedLedgerPatch(f);
  const bank=path.join(f.directory,'bank'),nativeSource=path.join(f.directory,'native');
  const write=(root,name,bytes)=>{const file=path.join(root,name);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,bytes);return asset(name,bytes);};
  const read=name=>fs.readFileSync(path.join(f.emittedDirectory,name));
  const manifest=JSON.parse(read(f.atlas.additiveRelease.base_manifest.path));
  manifest.version=2;manifest.runWords=f.atlas.pixelMap.runWords;
  manifest.parts=manifest.parts.map(part=>({...part,...write(nativeSource,`native-v1/ownership/${part.kind}-0.bin.gz`,read(part.path))}));
  const latitudeName=f.atlas.pixelMap.native_latitudes.path;
  const latitudeRaw=fs.readFileSync(fileURLToPath(new URL('../'+latitudeName,import.meta.url)));
  manifest.native_latitudes={...f.atlas.pixelMap.native_latitudes,bytes:latitudeRaw.length,sha256:sha256(latitudeRaw)};
  manifest.original_assets.bounds=pin('additive-repairs/owners.json.gz',read('additive-repairs/owners.json.gz'));
  const envelope=structuredClone(f.atlas.additiveRelease),manifestRaw=json(manifest);
  envelope.base_manifest=asset(envelope.base_manifest.path,manifestRaw);
  const prefix='ownership-vintages/'+envelope.base_manifest.sha256+'/';
  const packaged=await packageStartupOwnership({manifest,source:nativeSource,destination:path.join(bank,prefix)});
  for(const part of manifest.parts.filter(p=>p.kind==='rows'))write(bank,part.path,fs.readFileSync(path.join(nativeSource,part.path)));
  write(bank,'native-v1/native-row-latitudes.f64le.gz',latitudeRaw);
  const nativePixelMap={...packaged.pixelMap,canonical_grid_sha256:envelope.base_manifest.sha256,
    native_latitudes:{...manifest.native_latitudes,transport_path:'native-v1/native-row-latitudes.f64le.gz'},
    parts:packaged.pixelMap.parts.map(part=>part.kind==='rows'?part:{...part,path:prefix+part.path})};
  const assets={};
  for(const role of ['base_manifest','owner_roster','ledger','patch']){
    const a=envelope[role],raw=role==='base_manifest'?manifestRaw:read(a.path);
    const name='coordination/fixture-science/'+role+(a.path.endsWith('.gz')?'.json.gz':'.json');
    write(f.root,name,raw);assets[role]={...pin(name,raw),...(a.encoding?{decoded_bytes:a.decoded_bytes,decoded_sha256:a.decoded_sha256}:{})};
  }
  let selection={version:1,method:manifest.method,manifest_path:'data/native.json',sha256:envelope.base_manifest.sha256,release_id:manifest.geographic_release};
  const sidecar={version:2,kind:'retained-native-additive-selection-v2',base_selection:{...selection},logical_asset_map:assets,
    runtime_envelope:pin('selection/envelope.json',json(envelope))};
  write(f.root,'selection/envelope.json',json(envelope));write(f.root,'selection/sidecar.json',json(sidecar));
  selection.additive_release=pin('selection/sidecar.json',json(sidecar));const selectionBytes=json(selection);
  write(f.root,'data/ownership-selection.json',selectionBytes);write(f.root,'data/native.json',manifestRaw);
  const inventory=(directory,relative='')=>fs.readdirSync(path.join(directory,relative),{withFileTypes:true}).flatMap(entry=>{
    const name=relative+entry.name;return entry.isDirectory()?inventory(directory,name+'/'):[asset(name,fs.readFileSync(path.join(directory,name)))];
  }).sort((a,b)=>a.path.localeCompare(b.path));
  const index=await prepareSelectedStartupOwnership({selectionBytes,manifest,previous:{version:1,pixelMap:nativePixelMap,files:inventory(bank)},
    readNative:name=>fs.readFileSync(path.join(bank,name)),readPin:p=>fs.readFileSync(path.join(f.root,p.path)),destination:bank});
  index.files=inventory(bank);write(bank,'index.json',json(index));
  const selected={selection,selectionBytes,sidecar,envelope,base:envelope.base_reference};
  const output=path.join(f.directory,'copied');
  const prepared=await packagePreparedStartupOwnership({manifest,manifestSha:selection.sha256,source:bank,destination:output,selected,features:JSON.parse(gunzipSync(read(f.atlas.parts[0])))});
  fs.cpSync(output,f.emittedDirectory,{recursive:true});
  fs.rmSync(path.join(f.emittedDirectory,'additive-repairs'),{recursive:true});
  const atlas={...f.atlas,additiveRelease:envelope,pixelMap:prepared.pixelMap,preparedOwnership:prepared.preparedOwnership};
  write(f.emittedDirectory,'atlas-geography.json',json(atlas));
  return {...f,atlas,index,bank,write,selected,manifest};
}

test('finished-bank emitted consumer uses E directly and independently checks every word against original science',async t=>{
  const f=await finalFixture(t);
  assert.equal(fs.existsSync(path.join(f.emittedDirectory,'additive-repairs')),false);
  const report=await runSelectedDeliverySmoke(f.options);
  assert.equal(report.cumulative_native_cells_picked_and_sampled,2);
  assert.equal(report.expected_components_verified,2);assert.equal(report.stable_owner_controls,1);
  assert(report.inputs.some(p=>p.path==='coordination/fixture-science/ledger.json'&&p.scope==='root'));
  assert(!report.inputs.some(p=>p.path.startsWith('additive-repairs/')));
  const {loadNativeLatitudes}=await import('../src/native-latitudes.js');
  const {nativeReferenceForData}=await import('../src/effective-footprint.js');
  const fetchLatitude=async name=>new Response(fs.readFileSync(path.join(f.emittedDirectory,name.replace(/^\.\//,''))));
  const nativeReference=nativeReferenceForData(f.atlas);
  const latitudes=await loadNativeLatitudes(f.atlas.preparedOwnership.native_pixel_map,nativeReference,fetchLatitude);
  assert.equal(latitudes.length,f.atlas.pixelMap.size);
  await assert.rejects(loadNativeLatitudes(f.atlas.pixelMap,nativeReference,fetchLatitude),/Native ownership differs from the selected reference release/);
  fs.unlinkSync(f.outputPath);
  const fetcher=async name=>new Response(fs.readFileSync(path.join(f.emittedDirectory,name.replace(/^\.\//,''))));
  const words=await loadOwnershipAssets(f.atlas.pixelMap,fetcher);
  // Change an unrelated occupied owner, outside every repair and held component.
  words.runs[words.rows[4*2]+2]=1;
  const forged=await packageFinalStartupOwnership({ownership:words,expectedReference:f.atlas.reference_release,destination:path.join(f.directory,'forged')});
  fs.cpSync(path.join(f.directory,'forged'),f.emittedDirectory,{recursive:true});
  const atlas=structuredClone(f.atlas);atlas.pixelMap=forged.pixelMap;
  atlas.preparedOwnership.rows_sha256=forged.rows_sha256;atlas.preparedOwnership.runs_word_stream_sha256=forged.runs_word_stream_sha256;
  f.write(f.emittedDirectory,'atlas-geography.json',json(atlas));
  await assert.rejects(runSelectedDeliverySmoke(f.options),/Complete emitted (rows|runs) differ/);
  assert.equal(fs.existsSync(f.outputPath),false,'Forged unrelated words cannot publish success');
  const native=await loadOwnershipAssets(atlas.preparedOwnership.native_pixel_map,fetcher);
  native.runs[native.rows[4*2]+2]=1;
  const part=atlas.preparedOwnership.native_pixel_map.parts.find(p=>p.kind==='runs');
  assert.equal(part.words,native.runs.length);
  const raw=gzipSync(shuffleOwnershipBytes(native.runs));
  f.write(f.emittedDirectory,part.path,raw);part.sha256=sha256(raw);part.bytes=raw.length;part.decoded_sha256=sha256(Buffer.from(native.runs.buffer));
  f.write(f.emittedDirectory,'atlas-geography.json',json(atlas));
  await assert.rejects(runSelectedDeliverySmoke(f.options),/Decoded native ownership differs from original selected manifest/,
    'A mutually forged N and E cannot authorize each other');
  assert.equal(fs.existsSync(f.outputPath),false);
});


test('finished-bank physical pins use envelope encoding and preserve every encoded and decoded identity',async t=>{
  const f=await finalFixture(t,{gzipProducts:true});
  for(const role of ['owner_roster','ledger','patch']){
    assert.equal(Object.hasOwn(f.selected.sidecar.logical_asset_map[role],'encoding'),false);
    assert.equal(f.selected.envelope[role].encoding,'gzip');
  }
  const report=await runSelectedDeliverySmoke(f.options);
  assert.equal(report.cumulative_native_cells_picked_and_sampled,2);
  assert.equal(report.expected_components_verified,2);
  assert.equal(report.selected_ledger_sha256,f.expectations.selected_ledger_sha256);
  fs.unlinkSync(f.outputPath);
  const selectorFile=path.join(f.root,'data/ownership-selection.json');
  const selectorBytes=fs.readFileSync(selectorFile),selector=JSON.parse(selectorBytes);
  const sidecarFile=path.join(f.root,selector.additive_release.path),sidecarBytes=fs.readFileSync(sidecarFile);
  for(const role of ['owner_roster','ledger','patch'])for(const field of ['bytes','sha256','decoded_bytes','decoded_sha256']){
    const altered=JSON.parse(sidecarBytes),bodyPin=altered.logical_asset_map[role];
    bodyPin[field]=field.endsWith('sha256')?'0'.repeat(64):bodyPin[field]+1;
    const raw=json(altered);fs.writeFileSync(sidecarFile,raw);
    fs.writeFileSync(selectorFile,json({...selector,additive_release:pin(selector.additive_release.path,raw)}));
    await assert.rejects(runSelectedDeliverySmoke(f.options),/Original scientific identity differs/);
    assert.equal(fs.existsSync(f.outputPath),false);
  }
  fs.writeFileSync(sidecarFile,sidecarBytes);fs.writeFileSync(selectorFile,selectorBytes);
  const ownerFile=path.join(f.root,f.selected.sidecar.logical_asset_map.owner_roster.path);
  const corrupt=Buffer.from(fs.readFileSync(ownerFile));corrupt[corrupt.length-1]^=1;fs.writeFileSync(ownerFile,corrupt);
  await assert.rejects(runSelectedDeliverySmoke(f.options),/Whole asset hash differs/);
  assert.equal(fs.existsSync(f.outputPath),false);
});
