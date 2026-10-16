import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync, spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {digest, jsonBytes, pinReader, sourceEvidence} from '../scripts/prepare-delivery-handoff.mjs';

const helper = fileURLToPath(new URL('../scripts/prepare-delivery-handoff.mjs', import.meta.url));
const commit = 'a'.repeat(40), original = 'b'.repeat(40), prefix = 'coordination/engineering/control/';
const baselineKeys = ['native_contract', 'native_latitudes', 'owner_roster', 'base_reference'];
const contractKeys = ['size', 'coordinateBits', 'method', 'native_latitudes', 'hierarchy_sha256', 'original_assets'];
const withoutBaseline = value => Object.fromEntries(Object.entries(value).filter(([key]) => !baselineKeys.includes(key)));
const locator = pin => ({commit: pin.commit, path: pin.path});
function memoryReader() {
  const bodies = new Map(), pins = new Map(), reads = [];
  const reader = {bodies, pins, reads,
    add(name, value, version = commit) {
      const raw = Buffer.isBuffer(value) ? value : jsonBytes(value);
      const pin = {commit: version, path: name, mode: '100644', bytes: raw.length, sha256: digest(raw),
        git_blob_oid: createHash('sha1').update(Buffer.from(`blob ${raw.length}\0`)).update(raw).digest('hex')};
      bodies.set(version + ':' + name, raw); pins.set(version + ':' + name, pin); return {...pin};
    },
    pin(version, name) {
      const pin = pins.get(version + ':' + name); assert.ok(pin, 'Missing ordinary exact Git body: ' + name); return {...pin};
    },
    read(pin) {
      const actual = reader.pin(pin.commit, pin.path);
      for (const key of Object.keys(actual)) assert.equal(pin[key], actual[key], 'Whole pin identity differs: ' + key);
      reads.push(pin.path); return bodies.get(pin.commit + ':' + pin.path);
    },
    json(pin) { return JSON.parse(reader.read(pin)); }
  };
  return reader;
}
function fixture(change = {}) {
  const reader = memoryReader();
  const decodedLatitude = Buffer.alloc(32); [70, 20, -20, -70].forEach((n, i) => decodedLatitude.writeDoubleLE(n, i * 8));
  const latitudePin = reader.add(prefix + 'native-latitudes.f64le.gz', gzipSync(decodedLatitude), original);
  const native_latitudes = {...latitudePin, decoded_bytes: decodedLatitude.length, decoded_sha256: digest(decodedLatitude)};
  const decodedOwners = jsonBytes([{id: 'literal-owner-a', index: 1}, {id: 'literal-owner-b', index: 2}]);
  const ownerPin = reader.add(prefix + 'owners.json.gz', gzipSync(decodedOwners), original);
  const owner_roster = {...ownerPin, decoded_bytes: decodedOwners.length, decoded_sha256: digest(decodedOwners)};
  const manifest = {version: 2, size: 4, coordinateBits: 19, method: 'native-linear-evenodd-first-owner-v1',
    native_latitudes: {root: 'repository', role: 'immutable-normative-rule-input', commit: original,
      path: latitudePin.path, bytes: latitudePin.bytes, sha256: latitudePin.sha256,
      decoded_bytes: native_latitudes.decoded_bytes, decoded_sha256: native_latitudes.decoded_sha256},
    geographic_release: 'geography:review:literal', footprints_sha256: '1'.repeat(64), hierarchy_sha256: '2'.repeat(64),
    original_assets: {bounds: {commit: original, path: 'data/canonical-grid/bounds.json.gz', sha256: ownerPin.sha256,
      role: 'original-identity-parent-camera-context'}, province_membership: {commit: original,
      path: 'data/canonical-grid/province-membership.bin.gz', sha256: '3'.repeat(64), role: 'original-identity-crosswalk'}}};
  change.manifest?.(manifest);
  const base_manifest = reader.add(prefix + 'base-manifest.json', manifest, original);
  const selectedManifest = reader.add(prefix + 'selected-manifest.json', manifest);
  const assets = {base_manifest, owner_roster, ledger: reader.add(prefix + 'ledger.json', {version: 2, rows: []}),
    patch: reader.add(prefix + 'patch.json', {version: 2, rows: []})};
  const base_reference = {id: 'geography:review:literal', footprints_sha256: '1'.repeat(64), hierarchy_sha256: '2'.repeat(64)};
  const envelope = {version: 2, kind: 'retained-native-base-plus-delta-v2', base_reference,
    effective_reference: {...base_reference, id: 'geography:effective:literal'},
    ...Object.fromEntries(Object.entries(assets).map(([role, p]) => [role,
      {path: 'runtime/' + role, bytes: p.bytes, sha256: p.sha256,
        ...(p.decoded_bytes ? {decoded_bytes: p.decoded_bytes, decoded_sha256: p.decoded_sha256} : {})}]))};
  change.envelope?.(envelope);
  const runtime_envelope = reader.add(prefix + 'runtime-envelope.json', envelope);
  const base = {version: 1, manifest_path: selectedManifest.path, sha256: base_manifest.sha256,
    method: 'native-linear-evenodd-first-owner-v1', release_id: 'geography:review:literal'};
  const sidecar = {version: 2, kind: 'retained-native-additive-selection-v2', base_selection: {...base},
    logical_asset_map: assets, runtime_envelope, authority_registry: reader.add(prefix + 'registry.json', {version: 1})};
  change.sidecar?.(sidecar);
  const sidecarPin = reader.add(prefix + 'sidecar.json', sidecar);
  const selection = {...base, additive_release: {path: sidecarPin.path, bytes: sidecarPin.bytes, sha256: sidecarPin.sha256}};
  change.selection?.(selection);
  const selector = reader.add('data/ownership-selection.json', selection);
  const scientific = {version: 1, kind: 'source-target-native-evidence-v1',
    catalogue: {commit: original, path: 'human-supplied/catalogue.json', authority_note: 'Literal source claim'},
    families: [{source_id: 'literal-source', parts: [{path: 'human-supplied/source.gz', mode: '100644'}]}],
    physical_evidence: {path: 'human-supplied/physical.json', sha256: '4'.repeat(64)},
    physical_input: {path: 'human-supplied/input.json'}, physical_reproduction: {path: 'human-supplied/reproduce.py'},
    targets: [{id: 'literal-source-id', target_id: 'literal-owner-a', pixelIndex: 1, source_family: 'literal-source',
      base_geometry: {type: 'Polygon', coordinates: [[[1, 2], [3, 4], [5, 6], [1, 2]]]},
      source_receipt_sha256: '4'.repeat(64), native_contract: {human_nested_metadata: true}}],
    source_membership: {index: {path: 'human-supplied/index.json'}, parts: [], lineage: {path: 'human-supplied/lineage.json'}},
    limitations: ['Human supplied scope remains unchanged.']};
  const config = {version: 1, selector: locator(selector), source_evidence: scientific};
  return {reader, config, manifest, assets, sidecar, selection, envelope, native_latitudes, owner_roster, base_reference};
}

const result = async f => JSON.parse((await sourceEvidence(f.config, f.reader))['source-evidence.json']);

test('derivation copies the literal six-field manifest contract separately from real custody pins', async () => {
  const f = fixture(), originalConfig = structuredClone(f.config), actual = await result(f);
  assert.deepEqual(Object.keys(actual.native_contract).sort(), [...contractKeys].sort());
  assert.deepEqual(actual.native_contract, Object.fromEntries(contractKeys.map(key => [key, f.manifest[key]])));
  assert.deepEqual(actual.native_latitudes, f.native_latitudes);
  assert.deepEqual(actual.owner_roster, f.owner_roster);
  assert.deepEqual(actual.base_reference, f.base_reference);
  assert.equal(Object.hasOwn(actual.native_contract.native_latitudes, 'mode'), false);
  assert.equal(Object.hasOwn(actual.native_contract.native_latitudes, 'git_blob_oid'), false);
  assert.equal(actual.native_latitudes.mode, '100644');
  assert.deepEqual(withoutBaseline(actual), f.config.source_evidence);
  assert.deepEqual(f.config, originalConfig);
  assert.equal(f.reader.reads.some(name => name.startsWith('human-supplied/')), false);
  f.config.source_evidence = actual;
  assert.deepEqual(await result(f), actual, 'already canonical fields are accepted literally');
});

test('v2 derivation authenticates and retains the exact dated-support pin with unchanged scientific claims', async () => {
  const f = fixture(), support = f.reader.add(prefix + 'dated-support.json', {version: 1,
    kind: 'adopted-dated-native-centre-land-support-v1', provenance: [], records: []});
  Object.assign(f.config.source_evidence, {version: 2, kind: 'source-target-native-evidence-v2', dated_land_support: support});
  const originalConfig = structuredClone(f.config), actual = await result(f);
  assert.deepEqual(withoutBaseline(actual), originalConfig.source_evidence);
  assert.deepEqual(actual.dated_land_support, support);
  assert.ok(f.reader.reads.includes(support.path));
  assert.deepEqual(f.config, originalConfig);
  f.config.source_evidence.dated_land_support = {...support, sha256: '0'.repeat(64)};
  await assert.rejects(sourceEvidence(f.config, f.reader), /Whole pin identity differs/);
  delete f.config.source_evidence.dated_land_support;
  await assert.rejects(sourceEvidence(f.config, f.reader));
});

test('v3 derivation authenticates the adopted revised-source pin without rewriting scientific operands', async () => {
  const f = fixture(), adoption = f.reader.add(prefix + 'revised-source-adoption.json', {
    version: 1, kind: 'adopted-osm-revised-source-native-v1', members: [], records: []});
  Object.assign(f.config.source_evidence, {version: 3, kind: 'source-target-native-evidence-v3', revised_source_adoption: adoption});
  const actual = await result(f);
  assert.deepEqual(withoutBaseline(actual), f.config.source_evidence);
  assert.ok(f.reader.reads.includes(adoption.path));
  f.config.source_evidence.revised_source_adoption = {...adoption, sha256: '0'.repeat(64)};
  await assert.rejects(sourceEvidence(f.config, f.reader), /Whole pin identity differs/);
});

test('every supplied baseline difference refuses, including the original nested descriptor contamination', async t => {
  const changes = {
    'Git mode inside normative latitudes': e => { e.native_contract.native_latitudes.mode = '100644'; },
    'Git blob inside normative latitudes': e => { e.native_contract.native_latitudes.git_blob_oid = e.native_latitudes.git_blob_oid; },
    size: e => { e.native_contract.size++; },
    coordinateBits: e => { e.native_contract.coordinateBits--; },
    method: e => { e.native_contract.method = 'foreign'; },
    latitudes: e => { e.native_contract.native_latitudes.decoded_sha256 = '0'.repeat(64); },
    hierarchy: e => { e.native_contract.hierarchy_sha256 = '0'.repeat(64); },
    assets: e => { e.native_contract.original_assets.province_membership.sha256 = '0'.repeat(64); },
    base: e => { e.base_reference.id = 'geography:foreign'; },
    custody: e => { e.native_latitudes.git_blob_oid = '0'.repeat(40); },
    owner: e => { e.owner_roster.commit = '0'.repeat(40); }
  };
  for (const [name, change] of Object.entries(changes)) await t.test(name, async () => {
    const f = fixture(); f.config.source_evidence = await result(f); change(f.config.source_evidence);
    await assert.rejects(sourceEvidence(f.config, f.reader), /Supplied source evidence changes accepted baseline/);
  });
});

test('altered selector, sidecar, base, method, latitude, hierarchy and asset joins refuse', async t => {
  const changes = {
    'selector sidecar digest': {selection: x => { x.additive_release.sha256 = '0'.repeat(64); }},
    'selector method': {selection: x => { x.method = 'foreign'; }},
    'selector release': {selection: x => { x.release_id = 'geography:foreign'; }},
    'selected base copy': {sidecar: x => { x.base_selection.release_id = 'geography:foreign'; }},
    'selected manifest digest': {selection: x => { x.sha256 = '0'.repeat(64); }},
    'manifest method': {manifest: x => { x.method = 'foreign'; }},
    'manifest hierarchy': {manifest: x => { x.hierarchy_sha256 = '0'.repeat(64); }},
    'manifest assets': {manifest: x => { x.original_assets.bounds.sha256 = '0'.repeat(64); }},
    'manifest latitude encoded': {manifest: x => { x.native_latitudes.sha256 = '0'.repeat(64); }},
    'manifest latitude decoded': {manifest: x => { x.native_latitudes.decoded_sha256 = '0'.repeat(64); }},
    'envelope base': {envelope: x => { x.base_reference.id = 'geography:foreign'; }},
    'envelope owner digest': {envelope: x => { x.owner_roster.sha256 = '0'.repeat(64); }},
    'envelope owner decoded digest': {envelope: x => { x.owner_roster.decoded_sha256 = '0'.repeat(64); }},
    'envelope patch bytes': {envelope: x => { x.patch.bytes++; }},
    'missing logical asset': {sidecar: x => { delete x.logical_asset_map.ledger; }},
    'corrupt original pin': {sidecar: x => { x.logical_asset_map.base_manifest.git_blob_oid = '0'.repeat(40); }},
    'unsupported envelope': {envelope: x => { x.kind = 'foreign'; }},
    'decoded latitude cap': {manifest: x => { x.native_latitudes.decoded_bytes = 33554433; }}
  };
  for (const [name, change] of Object.entries(changes)) await t.test(name, async () => {
    const f = fixture(change); await assert.rejects(sourceEvidence(f.config, f.reader));
  });
});

test('present null and partial baseline fields refuse rather than being silently repaired', async t => {
  for (const key of baselineKeys) for (const value of [null, {}]) await t.test(key + ':' + JSON.stringify(value), async () => {
    const f = fixture(); f.config.source_evidence[key] = value;
    await assert.rejects(sourceEvidence(f.config, f.reader), /Supplied source evidence changes accepted baseline/);
  });
});

test('equivalent decoded latitude bytes cannot replace the normative encoded body', async () => {
  const f = fixture(), p = f.native_latitudes, key = p.commit + ':' + p.path;
  const originalRaw = f.reader.bodies.get(key), reencoded = Buffer.from(originalRaw);
  reencoded[9] = originalRaw[9] === 3 ? 0 : 3; // gzip OS header only; the decoded latitude body is identical.
  assert.notEqual(digest(reencoded), p.sha256);
  f.reader.add(p.path, reencoded, p.commit);
  await assert.rejects(sourceEvidence(f.config, f.reader), /Original native latitude body differs/);
});

test('coherently declared owner decoded identities must still match the actual decoded body', async () => {
  const f = fixture({sidecar: sidecar => {
    sidecar.logical_asset_map.owner_roster.decoded_sha256 = '0'.repeat(64);
  }, envelope: envelope => { envelope.owner_roster.decoded_sha256 = '0'.repeat(64); }});
  await assert.rejects(sourceEvidence(f.config, f.reader), /Decoded baseline identity differs: owner_roster/);
});

test('every consumed accepted pin must exist; caller-written selector descriptors are refused', async t => {
  for (const name of ['data/ownership-selection.json', prefix + 'sidecar.json', prefix + 'runtime-envelope.json',
    prefix + 'base-manifest.json', prefix + 'selected-manifest.json', prefix + 'native-latitudes.f64le.gz', prefix + 'owners.json.gz'])
    await t.test(name, async () => {
      const f = fixture();
      for (const key of f.reader.pins.keys()) if (key.endsWith(':' + name)) f.reader.pins.delete(key);
      await assert.rejects(sourceEvidence(f.config, f.reader), /Missing ordinary exact Git body/);
    });
  const f = fixture(); f.config.selector.sha256 = '0'.repeat(64);
  await assert.rejects(sourceEvidence(f.config, f.reader), /without handwritten derived descriptors/);
});

function directory(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'source-evidence-derivation-'));
  t.after(() => fs.rmSync(root, {recursive: true, force: true})); return root;
}
function write(root, name, raw) {
  fs.mkdirSync(path.dirname(path.join(root, name)), {recursive: true}); fs.writeFileSync(path.join(root, name), raw, {flag: 'wx'});
}
function git(root, ...args) {
  return execFileSync('git', args, {cwd: root, env: {...process.env, GIT_CONFIG_GLOBAL: '/dev/null', GIT_CONFIG_NOSYSTEM: '1'}, encoding: 'utf8'}).trim();
}
function gitFixture(t) {
  const root = directory(t), f = fixture();
  git(root, 'init', '-q'); git(root, 'config', 'user.name', 'Control'); git(root, 'config', 'user.email', 'control@example.invalid');
  const commitBodies = names => {
    for (const name of names) write(root, name, f.reader.bodies.get(original + ':' + name));
    git(root, 'add', '.'); git(root, 'commit', '-qm', 'Immutable original bodies'); return git(root, 'rev-parse', 'HEAD');
  };
  const originalCommit = commitBodies([prefix + 'native-latitudes.f64le.gz', prefix + 'owners.json.gz']);
  const replaceCommit = value => JSON.parse(JSON.stringify(value).replaceAll(original, originalCommit));
  const manifest = replaceCommit(f.manifest);
  write(root, prefix + 'base-manifest.json', jsonBytes(manifest)); write(root, prefix + 'selected-manifest.json', jsonBytes(manifest));
  write(root, prefix + 'ledger.json', jsonBytes({version: 2, rows: []})); write(root, prefix + 'patch.json', jsonBytes({version: 2, rows: []}));
  git(root, 'add', '.'); git(root, 'commit', '-qm', 'Immutable baseline assets'); const assetCommit = git(root, 'rev-parse', 'HEAD');
  const reader = pinReader(root), assets = {};
  for (const [role, pin] of Object.entries(f.assets)) assets[role] = {...reader.pin(assetCommit, pin.path),
    ...(pin.decoded_bytes ? {decoded_bytes: pin.decoded_bytes, decoded_sha256: pin.decoded_sha256} : {})};
  const envelope = {...f.envelope, ...Object.fromEntries(Object.entries(assets).map(([role, pin]) => [role,
    {...f.envelope[role], bytes: pin.bytes, sha256: pin.sha256}]))};
  write(root, prefix + 'runtime-envelope.json', jsonBytes(envelope)); git(root, 'add', '.'); git(root, 'commit', '-qm', 'Immutable envelope');
  const envelopeCommit = git(root, 'rev-parse', 'HEAD');
  const base = {...f.sidecar.base_selection, sha256: assets.base_manifest.sha256};
  const sidecar = {...f.sidecar, base_selection: base, logical_asset_map: assets,
    runtime_envelope: reader.pin(envelopeCommit, prefix + 'runtime-envelope.json')};
  const sidecarRaw = jsonBytes(sidecar); write(root, prefix + 'sidecar.json', sidecarRaw);
  write(root, 'data/ownership-selection.json', jsonBytes({...base, additive_release: {path: prefix + 'sidecar.json', bytes: sidecarRaw.length, sha256: digest(sidecarRaw)}}));
  git(root, 'add', '.'); git(root, 'commit', '-qm', 'Accepted selector');
  const config = {...f.config, selector: {commit: git(root, 'rev-parse', 'HEAD'), path: 'data/ownership-selection.json'}};
  write(root, 'config.json', jsonBytes(config));
  const run = (destination, resume = false) => spawnSync(process.execPath, [helper, 'source-evidence', 'config.json', destination, ...(resume ? ['--resume'] : [])],
    {cwd: root, encoding: 'utf8', env: {...process.env, NODE_OPTIONS: '', NODE_PATH: ''}});
  const expected = {...f.config.source_evidence,
    native_contract: Object.fromEntries(contractKeys.map(key => [key, manifest[key]])),
    native_latitudes: {...reader.pin(originalCommit, f.native_latitudes.path),
      decoded_bytes: f.native_latitudes.decoded_bytes, decoded_sha256: f.native_latitudes.decoded_sha256},
    owner_roster: assets.owner_roster, base_reference: f.base_reference};
  return {root, config, run, expected};
}

test('actual CLI derives once from local config and safely resumes exact completed bytes', t => {
  const {root, config, run} = gitFixture(t), destination = '.cache/delivery-handoff/baseline';
  const first = run(destination); assert.equal(first.status, 0, first.stderr);
  const evidence = fs.readFileSync(path.join(root, destination, 'source-evidence.json'));
  assert.deepEqual(withoutBaseline(JSON.parse(evidence)), config.source_evidence);
  const receipt = JSON.parse(fs.readFileSync(path.join(root, destination, 'preparation.json')));
  assert.equal(receipt.binding.phase, 'source-evidence'); assert.equal(receipt.binding.config_sha256, digest(jsonBytes(config)));
  assert.equal(JSON.parse(run(destination, true).stdout).resumed, true);
  assert.match(run(destination).stderr, /Occupied destination/);
  config.source_evidence.targets[0].target_id = 'changed-human-claim'; fs.writeFileSync(path.join(root, 'config.json'), jsonBytes(config));
  assert.match(run(destination, true).stderr, /Resumed bytes\/binding changed/);
  assert.deepEqual(fs.readFileSync(path.join(root, destination, 'source-evidence.json')), evidence);
  fs.unlinkSync(path.join(root, destination, 'preparation.json'));
  assert.match(run(destination, true).stderr, /Incomplete or foreign/);
  assert.equal(fs.existsSync(path.join(root, destination, 'preparation.json')), false);
});

test('CLI refusal preserves collision and dangling-symlink destinations and creates nothing on bad authority', t => {
  const {root, config, run} = gitFixture(t), prefixPath = '.cache/delivery-handoff';
  write(root, prefixPath + '/occupied/sentinel', Buffer.from('original sentinel'));
  assert.match(run(prefixPath + '/occupied').stderr, /Occupied destination/);
  assert.equal(fs.readFileSync(path.join(root, prefixPath, 'occupied/sentinel'), 'utf8'), 'original sentinel');
  fs.symlinkSync('/missing-source-evidence-control', path.join(root, prefixPath, 'link'));
  assert.match(run(prefixPath + '/link').stderr, /Nonordinary/);
  assert.match(run(prefixPath + '/link/child').stderr, /Nonordinary/);
  assert.match(run(prefixPath + '/../escape').stderr, /fresh owned/);
  config.selector.commit = '0'.repeat(40); fs.writeFileSync(path.join(root, 'config.json'), jsonBytes(config));
  assert.notEqual(run(prefixPath + '/refused').status, 0);
  assert.equal(fs.existsSync(path.join(root, prefixPath, 'refused')), false);
});

test('cold Git fixture reconstructs all baseline fields and scientific claims without historical objects', async t => {
  const {root, config, expected} = gitFixture(t);
  assert.equal(git(root, 'remote'), '', 'fixture must have no source of historical objects');
  assert.equal(fs.existsSync(path.join(root, '.git/objects/info/alternates')), false);
  assert.equal(git(root, 'rev-list', '--all').split('\n').length, 4, 'only fixture-authored history exists');
  // The former optional country case depended on this commit's complete tree,
  // although checking for its commit object alone could not establish that.
  const historical = spawnSync('git', ['-c', 'protocol.allow=never', 'cat-file', '-e',
    '73edb1d13f416266930327e559296fcc17f90c02^{commit}'],
  {cwd: root, env: {...process.env, GIT_NO_LAZY_FETCH: '1', GIT_CONFIG_GLOBAL: '/dev/null', GIT_CONFIG_NOSYSTEM: '1'}});
  assert.equal(historical.error, undefined);
  assert.notEqual(historical.status, 0, 'historical accepted commit must be absent');

  const outputs = await sourceEvidence(config, pinReader(root)), actual = JSON.parse(outputs['source-evidence.json']);
  for (const key of baselineKeys) assert.deepEqual(actual[key], expected[key], key);
  assert.deepEqual(withoutBaseline(actual), config.source_evidence, 'all supplied scientific claims survive literally');
  assert.deepEqual(outputs['source-evidence.json'], jsonBytes(expected), 'complete independently constructed expected body');

  const invalid = structuredClone(config);
  invalid.source_evidence.native_contract = structuredClone(expected.native_contract);
  invalid.source_evidence.native_contract.native_latitudes.mode = '100644';
  await assert.rejects(sourceEvidence(invalid, pinReader(root)), /Supplied source evidence changes accepted baseline/,
    'a present contaminated contract must fail through the real Git reader');
});
