import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync, spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {gzipSync} from 'node:zlib';
import {sourceEvidence, jsonBytes, digest, pinReader} from '../scripts/prepare-delivery-handoff.mjs';
import {candidateBudget} from '../scripts/native-ownership/native-preparation-guards.mjs';

// Reuse the accepted delivery-handoff.test memoryReader contract and modern
// finalization fixture's base manifest/selector/envelope asset layout. This
// exercises metadata derivation through sourceEvidence, never native science.
function fixture(t, gitFixture = false) {
  const bodies = new Map(), pins = new Map();
  let ordinal = 0, head = 'a'.repeat(40);
  const budget = candidateBudget([], {reserveBytes: 0, reserveDescriptors: 0});
  const memoryReader = {
    budget,
    pin(commit, name) { assert.equal(commit, head); assert.ok(pins.has(name), name); return pins.get(name); },
    read(pin) { const raw = bodies.get(pin.sha256); assert.ok(raw); assert.equal(raw.length, pin.bytes); return raw; },
    json(pin) { return JSON.parse(this.read(pin)); },
  };
  const root = gitFixture ? fs.mkdtempSync(path.join(os.tmpdir(), 'worldatlas-original-rows-')) : null;
  const git = (...args) => execFileSync('git', args, {cwd: root, encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe']}).trim();
  if (gitFixture) {
    t.after(() => fs.rmSync(root, {recursive: true, force: true}));
    git('init', '--quiet');
  }
  const reader = gitFixture ? pinReader(root) : memoryReader;
  function save(name, value) {
    const raw = Buffer.isBuffer(value) ? value : jsonBytes(value);
    if (gitFixture) {
      fs.mkdirSync(path.dirname(path.join(root, name)), {recursive: true});
      fs.writeFileSync(path.join(root, name), raw);
    } else {
      bodies.set(digest(raw), raw);
      pins.set(name, {path: name, commit: head, mode: '100644',
        git_blob_oid: (++ordinal).toString(16).padStart(40, '0'), bytes: raw.length, sha256: digest(raw)});
    }
  }
  function commit() {
    if (gitFixture) {
      git('add', '.');
      git('-c', 'user.name=Original request fixture', '-c', 'user.email=fixture@example.invalid',
        'commit', '--quiet', '-m', 'Disposable original request metadata fixture');
      head = git('rev-parse', 'HEAD');
    }
  }
  const pin = name => reader.pin(head, name);
  const locator = name => ({commit: head, path: name});
  const data = 'coordination/engineering/control/';
  const ownerRaw = jsonBytes([{id: 'target', index: 1}]);
  const latitudeRaw = Buffer.alloc(8 * 8);
  save(data + 'owners.json.gz', gzipSync(ownerRaw));
  save(data + 'latitudes.f64le.gz', gzipSync(latitudeRaw));
  save(data + 'ledger.json', {retained: 'ledger'});
  save(data + 'patch.json', {retained: 'patch'});
  save(data + 'original-rows.json', {columns: ['category', 'y', 'start', 'end', 'owners', 'source_feature_indices', 'physical'],
    rows: [['repair', 2, 1, 3, [1], [11], 'land'],
      ['repair', 2, 3, 4, [1], [10, 11], 'inland-water'],
      ['physical', 2, 5, 7, [1], [11], 'source-relative'],
      ['physical', 3, 1, 2, [1], [11], 'unknown']]});
  commit();
  const owners = {...pin(data + 'owners.json.gz'), decoded_bytes: ownerRaw.length, decoded_sha256: digest(ownerRaw)};
  const latitudes = {...pin(data + 'latitudes.f64le.gz'), decoded_bytes: latitudeRaw.length, decoded_sha256: digest(latitudeRaw)};
  const native_contract = {size: 8, coordinateBits: 3, method: 'native-linear-evenodd-first-owner-v1',
    native_latitudes: {commit: latitudes.commit, path: latitudes.path, bytes: latitudes.bytes, sha256: latitudes.sha256,
      decoded_bytes: latitudes.decoded_bytes, decoded_sha256: latitudes.decoded_sha256},
    hierarchy_sha256: 'c'.repeat(64), original_assets: {bounds: {sha256: owners.sha256}}};
  const reference = {id: 'geography:fixture', footprints_sha256: 'b'.repeat(64), hierarchy_sha256: 'c'.repeat(64)};
  save(data + 'manifest.json', {...native_contract, geographic_release: reference.id, footprints_sha256: reference.footprints_sha256});
  commit();
  const manifest = pin(data + 'manifest.json');
  const assets = {base_manifest: manifest, ledger: pin(data + 'ledger.json'), owner_roster: owners, patch: pin(data + 'patch.json')};
  const base = {method: native_contract.method, manifest_path: manifest.path, sha256: manifest.sha256, release_id: reference.id};
  save(data + 'envelope.json', {version: 2, kind: 'retained-native-base-plus-delta-v2', base_reference: reference,
    ...Object.fromEntries(Object.entries(assets).map(([role, p]) => [role, {...p}]))});
  commit();
  save(data + 'sidecar.json', {version: 2, kind: 'retained-native-additive-selection-v2', base_selection: base,
    logical_asset_map: assets, runtime_envelope: pin(data + 'envelope.json')});
  commit();
  const sidecar = pin(data + 'sidecar.json');
  save('data/ownership-selection.json', {...base, additive_release: {path: sidecar.path, bytes: sidecar.bytes, sha256: sidecar.sha256}});
  commit();
  const config = {version: 1, selector: locator('data/ownership-selection.json'),
    source_evidence: {version: 1, kind: 'source-target-native-evidence-v1',
      targets: [{id: 'target', pixelIndex: 1, territorial_exclusions: [], source_receipt_sha256: 'd'.repeat(64)}]},
    original_request: {rows: locator(data + 'original-rows.json'), owner: 1, size: 8}};
  return {reader, config, native_contract, reference, owners, save, commit, root, locator,
    originalRows: () => reader.json(pin(data + 'original-rows.json'))};
}

test('existing sourceEvidence call derives baseline and both mixed original-request outputs together', async t => {
  const f = fixture(t), before = structuredClone(f.config);
  const outputs = await sourceEvidence(f.config, f.reader);
  assert.deepEqual(Object.keys(outputs).sort(), ['native-patch.json', 'source-evidence.json']);
  assert.deepEqual(JSON.parse(outputs['native-patch.json']), {rows: [{y: 2, runs: [[1, 3, 1], [3, 4, 1]]}]});
  const source = JSON.parse(outputs['source-evidence.json']);
  assert.deepEqual(source.targets[0], {...before.source_evidence.targets[0],
    coverage_classes: ['mapped_land_support', 'mapped_inland_water_support'],
    coverage_rows: [{y: 2, runs: [[1, 3, 'mapped_land_support'], [3, 4, 'mapped_inland_water_support']]}]});
  assert.deepEqual(source.native_contract, f.native_contract);
  assert.deepEqual(source.base_reference, f.reference);
  assert.deepEqual(source.owner_roster, f.owners);
  assert.deepEqual(f.config, before);
  assert.deepEqual(f.originalRows().rows[2], ['physical', 2, 5, 7, [1], [11], 'source-relative']);
  assert.deepEqual(f.originalRows().rows[3], ['physical', 3, 1, 2, [1], [11], 'unknown']);
});

test('same-call original preparation refuses competing manual class/patch fields', async t => {
  for (const field of ['coverage_rows', 'coverage_classes', 'native_patch']) {
    const f = fixture(t);
    if (field === 'native_patch') f.config.native_patch = {commit: 'a'.repeat(40), path: 'manual.json'};
    else f.config.source_evidence.targets[0][field] = [];
    await assert.rejects(sourceEvidence(f.config, f.reader), /manual native patch|manual native coverage/);
  }
});

test('owner/size binding, actual row ownership and unsupported labels fail at the real sourceEvidence boundary', async t => {
  for (const [mutate, message] of [
    [f => { f.config.original_request.owner = 2; }, /sole source target/],
    [f => { f.config.original_request.size = 16; }, /native size/],
    [f => { const rows = f.originalRows(); rows.rows[0][4] = [2]; f.save('coordination/engineering/control/original-rows.json', rows); }, /original owner/],
    [f => { const rows = f.originalRows(); rows.rows[0][6] = 'probably-land'; f.save('coordination/engineering/control/original-rows.json', rows); }, /physical class/],
  ]) {
    const f = fixture(t); mutate(f);
    await assert.rejects(sourceEvidence(f.config, f.reader), message);
  }
});

test('existing manual source-evidence behavior stays one-output when no original packet is requested', async t => {
  const f = fixture(t); delete f.config.original_request;
  f.config.source_evidence.targets[0].coverage_classes = ['mapped_land_support'];
  const outputs = await sourceEvidence(f.config, f.reader);
  assert.deepEqual(Object.keys(outputs), ['source-evidence.json']);
  assert.deepEqual(JSON.parse(outputs['source-evidence.json']).targets, f.config.source_evidence.targets);
});

test('plain existing source-evidence CLI publishes both products once and refuses conflict before destination creation', t => {
  const f = fixture(t, true);
  const script = fileURLToPath(new URL('../scripts/prepare-delivery-handoff.mjs', import.meta.url));
  const env = {...process.env}; delete env.NODE_OPTIONS; delete env.NODE_PATH;
  const run = (config, destination) => {
    fs.writeFileSync(path.join(f.root, 'config.json'), jsonBytes(config));
    return spawnSync(process.execPath, [script, 'source-evidence', 'config.json', destination], {cwd: f.root, env, encoding: 'utf8'});
  };
  const good = '.cache/delivery-handoff/original-once';
  const actual = run(f.config, good);
  assert.equal(actual.status, 0, actual.stderr);
  const names = fs.readdirSync(path.join(f.root, good));
  assert.deepEqual(names.sort(), ['native-patch.json', 'preparation.json', 'source-evidence.json']);
  const preparation = JSON.parse(fs.readFileSync(path.join(f.root, good, 'preparation.json')));
  assert.equal(preparation.binding.phase, 'source-evidence');
  assert.deepEqual(Object.keys(preparation.outputs).sort(), ['native-patch.json', 'source-evidence.json']);
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(f.root, good, 'native-patch.json'))),
    {rows: [{y: 2, runs: [[1, 3, 1], [3, 4, 1]]}]});
  const altered = structuredClone(f.config); altered.source_evidence.targets[0].coverage_classes = [];
  const destination = '.cache/delivery-handoff/conflicted';
  const refused = run(altered, destination);
  assert.notEqual(refused.status, 0);
  assert.match(refused.stderr, /manual native coverage/);
  assert.equal(fs.existsSync(path.join(f.root, destination)), false);
});
