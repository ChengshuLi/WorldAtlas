import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync, spawnSync} from 'node:child_process';
import {gzipSync, gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {staticModuleClosure} from './helpers/static-module-closure.mjs';
import {shuffledChunks} from './fixtures/native-word-store.mjs';
import {nativeAuthority, pinReader} from '../scripts/prepare-delivery-handoff.mjs';
import {valueSha} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';

const sha = raw => createHash('sha256').update(raw).digest('hex');
const command = 'scripts/observe-selected-owners.mjs';
const queueRoot = 'coordination/engineering/global-current-cell-work-queue-20261014';
const packageId = 'gb-TST-ADM2--repair-evaluation';
const sources = staticModuleClosure(process.cwd(), [command]);
const keys = [{x: 0, y: 0}, {x: 2, y: 0}, {x: 3, y: 0}, {x: 1, y: 1}, {x: 1, y: 2}];
function fixture({missingOrigins = false, changeManifest, changePatch, changeSide, changeOwners, changeArrays, changeQueue, changeOriginalGrid, splitCandidates = false} = {}) {
  const repo = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'owner-observation-')));
  const git = (...args) => execFileSync('git', ['-C', repo, ...args], {stdio: ['ignore', 'pipe', 'pipe']}).toString().trim();
  const write = (name, body) => {
    const raw = Buffer.isBuffer(body) ? body : Buffer.from(JSON.stringify(body));
    fs.mkdirSync(path.dirname(path.join(repo, name)), {recursive: true}); fs.writeFileSync(path.join(repo, name), raw); return raw;
  };
  const commit = () => { git('add', '.'); git('commit', '-m', 'Immutable synthetic ownership inputs'); return git('rev-parse', 'HEAD'); };
  for (const name of [...sources, 'scripts/run-geographic-check.py', 'package.json']) write(name, fs.readFileSync(name));
  // The actual exported geometry class is fatal in this fixture. No world index,
  // source bank, geographic release, proof certificate or ledger body is present.
  const checker = 'scripts/check-effective-geographic-regression.mjs';
  const body = fs.readFileSync(path.join(repo, checker), 'utf8');
  assert.ok(body.includes('export class SelectedGeometrySources {\n  constructor(snapshot) {'));
  write(checker, Buffer.from(body.replace('export class SelectedGeometrySources {\n  constructor(snapshot) {',
    'export class SelectedGeometrySources {\n  constructor(snapshot) {\n    throw Error("FORBIDDEN full geometry resolver");')));
  git('init'); git('config', 'user.name', 'Fixture'); git('config', 'user.email', 'fixture@example.invalid');
  const owners = [{index: 1, id: 'owner-A'}, {index: 2, id: 'owner-B'}];
  changeOwners?.(owners);
  write('inputs/owners.json', owners);
  const latitudeRaw = Buffer.alloc(4 * 8); [60, 20, -20, -60].forEach((v, i) => latitudeRaw.writeDoubleLE(v, i * 8));
  const latitudeBytes = write('inputs/latitudes.gz', gzipSync(latitudeRaw));
  const registry = {version: 1, kind: 'synthetic-registry', entries: []}; write('inputs/registry.json', registry);
  const featureRaw = Buffer.from(JSON.stringify([{family_index: 0, owners: [1]}, {family_index: 0, owners: [2]}]) + '\n');
  write(queueRoot + '/source-feature-roster.json.gz', gzipSync(featureRaw));
  const raster = write(queueRoot + '/source-raster-summary.json', {products: [{product: 'gb:TST:ADM2'}]});
  const block = (prefix, rows) => {
    const decoded = Buffer.from(JSON.stringify(rows) + '\n'), raw = gzipSync(decoded);
    write(queueRoot + '/' + prefix + '-block-000.json.gz', raw);
    return {kind: prefix, sha256: sha(raw), decoded_sha256: sha(decoded)};
  };
  const candidates = block('source-candidates', [
    {y: 0, runs: [[0, 1, [1], [1]], [2, 3, [2], [2]], [3, 4, [1], [1]]]},
    {y: 1, runs: [[1, 2, [2], [2]]]}, {y: 2, runs: [[1, 2, [1], [1]]]},
    {y: 3, runs: [[0, 1, [1, 2], [1, 2]]]}, // Different package, never silently included.
  ]);
  if (splitCandidates) {
    const rows = JSON.parse(gunzipSync(fs.readFileSync(path.join(repo, queueRoot, 'source-candidates-block-000.json.gz'))));
    candidates.parts = [rows.slice(0, 2), rows.slice(2)].map((part, i) => {
      const decoded = Buffer.from(JSON.stringify(part) + '\n'), raw = gzipSync(decoded), name = `source-split-${i}.json.gz`;
      write(queueRoot + '/' + name, raw); return {path: name, sha256: sha(raw), decoded_sha256: sha(decoded)};
    });
  }
  const land = block('physical-support', [0, 1, 2, 3].map(y => ({y, runs: [[0, 4]]})));
  const water = block('inland-water-support', []);
  const census = write(queueRoot + '/source-census-summary.json', {blocks: [candidates]});
  const physical = write(queueRoot + '/physical-unassigned-summary.json', {phases: [{files: [land, water]}]});
  const originalGrid = {size: 4, selection: {method: 'native-linear-evenodd-first-owner-v1', sha256: 'e'.repeat(64),
    additive_release: {path: 'historical-patch-not-read.json'}}, native_latitudes: {decoded_bytes: latitudeRaw.length, decoded_sha256: sha(latitudeRaw)}};
  changeOriginalGrid?.(originalGrid);
  const gridBinding = write(queueRoot + '/ownership-binding.json', originalGrid);
  const queue = {input_sha256: {'source-feature-roster.json': sha(featureRaw), 'source-raster-summary.json': sha(raster),
    'source-census-summary.json': sha(census), 'physical-unassigned-summary.json': sha(physical), 'ownership-binding.json': sha(gridBinding)},
    packages: [{package_id: packageId, native_blocks: [0], native_cells: 5, intervals: 5},
      {package_id: 'gb-TST-ADM2--source-conflict', native_blocks: [0], native_cells: 1, intervals: 1}]};
  changeQueue?.(queue); write(queueRoot + '/source-package-queue.json', queue);
  const origin = commit();
  const pin = (name, version = git('rev-parse', 'HEAD')) => {
    const raw = execFileSync('git', ['-C', repo, 'show', version + ':' + name]);
    return {commit: missingOrigins ? 'f'.repeat(40) : version, path: name, mode: '100644', git_blob_oid: git('rev-parse', version + ':' + name), bytes: raw.length, sha256: sha(raw)};
  };
  // Independent small numerical words: owner*2^bits+start and inclusive end.
  const arrays = [[0, 1, 1, 1, 2, 0, 2, 1], [4, 1, 9, 1], [7, 3]];
  changeArrays?.(arrays);
  const parts = [], files = [], fragments = []; let at = 0;
  for (let i = 0; i < arrays.length; i++) {
    const values = arrays[i], raw = Buffer.alloc(values.length * 4); values.forEach((v, n) => raw.writeUInt32LE(v, n * 4));
    const encoded = gzipSync(Buffer.concat([...shuffledChunks(values.length, {value: n => values[n]})]));
    const kind = i ? 'runs' : 'rows', name = `native-v1/ownership/${kind}-${i}.bin.gz`;
    parts.push({kind, offset: i === 2 ? 4 : 0, words: values.length, path: name, bytes: encoded.length,
      sha256: sha(encoded), decoded_bytes: raw.length, decoded_sha256: sha(raw), encoding: 'byte-shuffle'});
    files.push({path: name, offset: at, bytes: encoded.length, sha256: sha(encoded), mode: '100644'});
    const fragment = gzipSync(encoded), fragmentPath = `part-${i}.gz`;
    write('inputs/bank/' + fragmentPath, fragment);
    fragments.push({path: fragmentPath, offset: at, bytes: fragment.length, sha256: sha(fragment), decoded_bytes: encoded.length, decoded_sha256: sha(encoded)});
    at += encoded.length;
  }
  const index = write('inputs/bank/index.json', {version: 1, kind: 'ordered-exact-original-byte-fragments', files, parts: fragments,
    whole_bytes: at, whole_sha256: 'a'.repeat(64)});
  const manifest = {version: 2, method: 'native-linear-evenodd-first-owner-v1', size: 4, coordinateBits: 2,
    geographic_release: 'synthetic-native', footprints_sha256: 'b'.repeat(64), accounting: {owners: 2}, runWords: 6, parts,
    original_assets: {bounds: {sha256: pin('inputs/owners.json', origin).sha256}},
    native_latitudes: {root: 'repository', role: 'immutable-normative-rule-input', commit: missingOrigins ? 'f'.repeat(40) : origin, path: 'inputs/latitudes.gz',
      bytes: latitudeBytes.length, sha256: sha(latitudeBytes), decoded_bytes: latitudeRaw.length, decoded_sha256: sha(latitudeRaw)},
    native_asset_transport: {version: 1, kind: 'ordered-exact-original-byte-fragments', logical_assets: parts.length,
      original_compressed_bytes: at, index: {path: 'inputs/bank/index.json', bytes: index.length, sha256: sha(index)}}};
  changeManifest?.(manifest);
  const manifestRaw = write('inputs/native/manifest.json', manifest);
  const selection = {version: 1, method: manifest.method, release_id: manifest.geographic_release,
    manifest_path: 'inputs/native/manifest.json', sha256: sha(manifestRaw)};
  const baseReference = {footprints_sha256: manifest.footprints_sha256}, effectiveReference = {footprints_sha256: 'c'.repeat(64)};
  const ledger = {bytes: 37, sha256: 'd'.repeat(64)}; // Digest joined, body deliberately absent.
  const patch = {kind: 'unassigned-native-cells-v1', version: 2, size: 4, base_reference: baseReference,
    effective_reference: effectiveReference, ledger_sha256: ledger.sha256, authority_registry_sha256: valueSha(registry),
    rows: [{y: 0, runs: [[2, 3, 2]]}, {y: 1, runs: [[1, 2, 1]]}]};
  changePatch?.(patch); write('inputs/patch.json', patch);
  const products = commit();
  const assets = {base_manifest: pin(selection.manifest_path, products), owner_roster: pin('inputs/owners.json', origin), patch: pin('inputs/patch.json', products), ledger};
  write('inputs/envelope.json', {...assets, base_reference: baseReference, effective_reference: effectiveReference});
  const envelopeCommit = commit();
  const side = {kind: 'retained-native-additive-selection-v2', version: 2, base_selection: structuredClone(selection),
    logical_asset_map: assets, authority_registry: pin('inputs/registry.json', origin), runtime_envelope: pin('inputs/envelope.json', envelopeCommit)};
  changeSide?.(side);
  const sideRaw = write('inputs/sidecar.json', side);
  selection.additive_release = {path: 'inputs/sidecar.json', bytes: sideRaw.length, sha256: sha(sideRaw)};
  write('data/ownership-selection.json', selection); const head = commit();
  let n = 0;
  const run = (options = {}) => {
    const output = options.out ?? path.join(repo, 'observation-' + n++ + '.json');
    const result = spawnSync(process.execPath, [path.join(repo, command), '--repo', repo, '--commit', options.commit ?? git('rev-parse', 'HEAD'),
      '--package', options.packageId ?? packageId, '--out', output, ...(options.extra ?? [])], {encoding: 'utf8', env: {...process.env, GIT_NO_LAZY_FETCH: '1', GIT_NO_REPLACE_OBJECTS: '1'}});
    return {...result, output, report: result.status === 0 ? JSON.parse(fs.readFileSync(output)) : null};
  };
  return {repo, git, write, commit, pin, head, manifest, selection, side, run, cleanup: () => fs.rmSync(repo, {recursive: true})};
}

test('literal ownership entrypoint needs no geometry or qualification inputs and binds exact keys, head and latitude', () => {
  const f = fixture(); try {
    const r = f.run(); assert.equal(r.status, 0, r.stderr);
    assert.equal(r.report.kind, 'literal-selected-owner-observation-v1'); assert.equal(r.report.scientific_qualification, false);
    assert.equal(r.report.commit, f.head); assert.equal(r.report.query_count, 5);
    assert.equal(r.report.query_sha256, sha(Buffer.from(JSON.stringify(keys) + '\n')));
    assert.deepEqual(r.report.keys.map(k => [k.base_owner, k.accepted_additive_owner, k.effective_selected_owner, k.owner_id]),
      [[1, 0, 1, 'owner-A'], [0, 2, 2, 'owner-B'], [0, 0, 0, null], [2, 1, null, null], [0, 0, 0, null]]);
    assert.deepEqual(r.report.keys.map(k => k.latitude), [60, 60, 60, 20, -20]);
    assert.equal(r.report.keys[3].existing_product_overlap, true);
    assert.equal(r.report.run_members.length, 1);
    assert.ok(!r.report.consumed_inputs.some(p => /world-index|geography\/|ledger|part-2.gz/.test(p.path)));
    assert.equal(r.report.original_package.package_id, packageId);
    assert.equal(r.report.original_package.native_cells, 5);
    assert.match(r.report.limits.join(' '), /not source applicability, a package qualification certificate or complete repair acceptance/);
  } finally { f.cleanup(); }
});

test('the supported command derives all original keys and exposes no subset, certificate or qualification choice', () => {
  const f = fixture(); try {
    for (const extra of [['--keys', 'reduced.json'], ['--certificate', 'foreign.json'], ['--qualification', 'true'], ['--geometry', 'true']]) {
      const r = f.run({extra}); assert.notEqual(r.status, 0); assert.equal(fs.existsSync(r.output), false);
    }
    const unknown = f.run({packageId: 'wrong-package'}); assert.notEqual(unknown.status, 0); assert.match(unknown.stderr, /Unknown or duplicate package/);
    const conflict = f.run({packageId: 'gb-TST-ADM2--source-conflict'}); assert.equal(conflict.status, 0, conflict.stderr);
    assert.equal(conflict.report.query_count, 1); assert.deepEqual(conflict.report.keys.map(({x, y}) => ({x, y})), [{x: 0, y: 3}]);
    const missing = f.run({commit: 'e'.repeat(40)}); assert.notEqual(missing.status, 0); assert.equal(fs.existsSync(missing.output), false);
  } finally { f.cleanup(); }
});

test('immutable body and executed source drift fail before an observation is published', () => {
  for (const name of ['inputs/bank/part-0.gz', 'inputs/bank/part-1.gz', 'inputs/latitudes.gz', 'inputs/patch.json']) {
    const f = fixture({missingOrigins: true}); try {
      f.write(name, Buffer.from('corrupt immutable body')); f.commit();
      const r = f.run(); assert.notEqual(r.status, 0, name); assert.equal(fs.existsSync(r.output), false);
    } finally { f.cleanup(); }
  }
  const f = fixture(); try {
    fs.appendFileSync(path.join(f.repo, 'src/pixel-ownership.js'), '\n// uncommitted source drift\n');
    const r = f.run(); assert.notEqual(r.status, 0); assert.match(r.stderr, /Executed source differs/); assert.equal(fs.existsSync(r.output), false);
  } finally { f.cleanup(); }
});

test('existing files, symlinks and nonordinary output parents are not overwritten', () => {
  const f = fixture(); try {
    const sentinel = path.join(f.repo, 'sentinel.json'); fs.writeFileSync(sentinel, 'preserved');
    const dangling = path.join(f.repo, 'dangling.json'); fs.symlinkSync('absent-target', dangling);
    const parent = path.join(f.repo, 'output-alias'); fs.symlinkSync(f.repo, parent);
    for (const out of [sentinel, dangling, path.join(parent, 'new.json')]) {
      const r = f.run({out}); assert.notEqual(r.status, 0); assert.match(r.stderr, /Output parent|output already exists/);
    }
    assert.equal(fs.readFileSync(sentinel, 'utf8'), 'preserved'); assert.equal(fs.readlinkSync(dangling), 'absent-target');
    assert.equal(fs.existsSync(path.join(f.repo, 'absent-target')), false); assert.equal(fs.existsSync(path.join(f.repo, 'new.json')), false);
  } finally { f.cleanup(); }
});


test('whole same-path aliases retain honest normative provenance when original commits are absent', () => {
  const f = fixture({missingOrigins: true}); try {
    const r = f.run(); assert.equal(r.status, 0, r.stderr);
    assert.equal(r.report.latitude_whole_body_alias, true);
    assert.equal(r.report.native_latitudes.commit, 'f'.repeat(40));
    assert.equal(r.report.consumed_latitudes.commit, f.head);
    assert.equal(r.report.consumed_latitudes.sha256, r.report.native_latitudes.sha256);
  } finally { f.cleanup(); }
});

test('coherently repinned inputs cannot hide invalid joins, decoded words, normative bytes or row partitions', () => {
  const cases = [
    {changeQueue: q => q.packages[0].native_cells = 4},
    {changeQueue: q => q.packages[0].native_blocks = []},
    {changeQueue: q => q.input_sha256['source-feature-roster.json'] = '0'.repeat(64)},
    {changeManifest: m => m.parts[1].decoded_sha256 = '0'.repeat(64)},
    {changeManifest: m => m.native_latitudes.decoded_sha256 = '0'.repeat(64),
      changeOriginalGrid: g => g.native_latitudes.decoded_sha256 = '0'.repeat(64)},
    {changeManifest: m => m.native_latitudes.decoded_bytes++},
    {changeManifest: m => m.parts[2].offset = 2},
    {changeArrays: arrays => arrays[0][2] = 0},
    {changeArrays: arrays => arrays[1][1] = 4},
    {changeOwners: owners => owners[1].id = owners[0].id},
    {changeSide: side => side.base_selection.release_id = 'foreign'},
    {changeSide: side => side.logical_asset_map.patch.sha256 = '0'.repeat(64)},
    {changePatch: patch => patch.ledger_sha256 = '0'.repeat(64)},
    {changePatch: patch => patch.authority_registry_sha256 = '0'.repeat(64)},
    {changePatch: patch => patch.rows[0].runs.push([2, 4, 1])},
  ];
  for (const options of cases) {
    const f = fixture(options); try {
      const r = f.run(); assert.notEqual(r.status, 0, String(Object.values(options)[0]));
      assert.equal(fs.existsSync(r.output), false);
    } finally { f.cleanup(); }
  }
});


test('explicit data head is independent of executable checkout and cannot qualify as source evidence', async () => {
  const f = fixture(); try {
    f.write('unrelated.txt', Buffer.from('Later checkout, unchanged executable code')); const later = f.commit();
    const r = f.run({commit: f.head}); assert.equal(r.status, 0, r.stderr);
    assert.equal(r.report.commit, f.head); assert.equal(r.report.code_commit, later);
    assert.equal(f.git('rev-parse', 'HEAD'), later, 'Observing an older exact head never switches the checkout');
    f.write('ordinary-patch.json', {rows: [{y: 0, runs: [[2, 3, 2]]}]}); const observationHead = f.commit();
    const config = {version: 1, source_evidence: {commit: observationHead, path: path.basename(r.output)},
      native_patch: {commit: observationHead, path: 'ordinary-patch.json'}};
    await assert.rejects(() => nativeAuthority(config, pinReader(f.repo), f.repo), /Incomplete source-target evidence/);
  } finally { f.cleanup(); }
});


test('the original extraction CLI preserves independently specified package and interval bytes', () => {
  const expectedPackage = {package_id: packageId, native_blocks: [0], native_cells: 5, intervals: 5};
  const expectedRows = [[0, 0, 1, [1], [1], 'land'], [0, 2, 3, [2], [2], 'land'],
    [0, 3, 4, [1], [1], 'land'], [1, 1, 2, [2], [2], 'land'], [2, 1, 2, [1], [1], 'land']];
  for (const splitCandidates of [false, true]) {
    const f = fixture({splitCandidates}); try {
      const observed = f.run(); assert.equal(observed.status, 0, observed.stderr); assert.equal(observed.report.query_count, 5);
      const destination = path.join(f.repo, 'original-extraction');
      const result = spawnSync(process.execPath, [path.join(f.repo, queueRoot, 'source-batch-intervals.mjs'), packageId, destination], {encoding: 'utf8'});
      assert.equal(result.status, 0, result.stderr);
      assert.deepEqual(fs.readdirSync(destination).sort(), ['block-000.json.gz', 'package.json']);
      assert.deepEqual(fs.readFileSync(path.join(destination, 'package.json')), Buffer.from(JSON.stringify(expectedPackage, null, 2) + '\n'));
      assert.deepEqual(fs.readFileSync(path.join(destination, 'block-000.json.gz')), gzipSync(JSON.stringify(expectedRows) + '\n'));
    } finally { f.cleanup(); }
  }
});


test('original queue grid identity is joined before native body reads, not the changing historical selector', () => {
  for (const changeOriginalGrid of [g => g.size = 8, g => g.selection.method = 'foreign-grid-rule',
    g => g.native_latitudes.decoded_sha256 = '0'.repeat(64), g => g.native_latitudes.decoded_bytes = 64]) {
    const f = fixture({changeOriginalGrid}); try {
      // If the early identity join is absent, this missing body gives a different
      // failure. A coherent original metadata hash must not reinterpret grid keys.
      f.git('rm', 'inputs/bank/part-0.gz'); f.commit();
      const r = f.run(); assert.notEqual(r.status, 0); assert.match(r.stderr, /Original package grid\/method\/normative latitude identity differs/);
      assert.equal(fs.existsSync(r.output), false);
    } finally { f.cleanup(); }
  }
  const f = fixture(); try {
    // The fixture's historical selector SHA and patch differ intentionally.
    const r = f.run(); assert.equal(r.status, 0, r.stderr); assert.equal(r.report.query_count, 5);
  } finally { f.cleanup(); }
});
