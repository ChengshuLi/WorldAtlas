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
const gitHelperArgv = [
  ['pack-objects', '--revs', '--thin', '--stdout', '--delta-base-offset'],
  ['rev-list', '--objects', '--stdin', '--not', '--exclude-hidden=fetch', '--all', '--quiet', '--alternate-refs'],
];
const exactGitHelper = args =>
  gitHelperArgv.some(expected => JSON.stringify(args) === JSON.stringify(expected)) ||
  (args.length === 5 && args[0] === 'index-pack' && args[1] === '--stdin' && args[2] === '--fix-thin' && args[3] === '--promisor' && /^--pack_header=2,[1-9][0-9]*$/.test(args[4]));
function fixture({missingOrigins = false, changeManifest, changePatch, changeSide, changeOwners, changeArrays, changeQueue, changeOriginalGrid, splitCandidates = false, multiBlock = false} = {}) {
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
  const block = (prefix, rows, b = 0) => {
    const decoded = Buffer.from(JSON.stringify(rows) + '\n'), raw = gzipSync(decoded);
    write(queueRoot + '/' + prefix + '-block-' + String(b).padStart(3, '0') + '.json.gz', raw);
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
  const blocks = [candidates], phases = [{files: [land, water]}];
  if (multiBlock) {
    assert.equal(splitCandidates, false);
    const rows = JSON.parse(gunzipSync(fs.readFileSync(path.join(repo, queueRoot, 'source-candidates-block-000.json.gz'))));
    blocks[0] = block('source-candidates', rows.filter(r => r.y < 2));
    blocks.push(block('source-candidates', rows.filter(r => r.y >= 2), 1));
    phases[0].files = [block('physical-support', [0, 1].map(y => ({y, runs: [[0, 4]]}))), water];
    phases.push({files: [block('physical-support', [2, 3].map(y => ({y, runs: [[0, 4]]})), 1), block('inland-water-support', [], 1)]});
  }
  const census = write(queueRoot + '/source-census-summary.json', {blocks});
  const physical = write(queueRoot + '/physical-unassigned-summary.json', {phases});
  const originalGrid = {size: 4, selection: {method: 'native-linear-evenodd-first-owner-v1', sha256: 'e'.repeat(64),
    additive_release: {path: 'historical-patch-not-read.json'}}, native_latitudes: {decoded_bytes: latitudeRaw.length, decoded_sha256: sha(latitudeRaw)}};
  changeOriginalGrid?.(originalGrid);
  const gridBinding = write(queueRoot + '/ownership-binding.json', originalGrid);
  const queue = {input_sha256: {'source-feature-roster.json': sha(featureRaw), 'source-raster-summary.json': sha(raster),
    'source-census-summary.json': sha(census), 'physical-unassigned-summary.json': sha(physical), 'ownership-binding.json': sha(gridBinding)},
    packages: [{package_id: packageId, native_blocks: multiBlock ? [0, 1] : [0], native_cells: 5, intervals: 5},
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
    const target = options.repo ?? repo;
    const result = spawnSync(process.execPath, [...(options.nodeArgs ?? []), path.join(target, command), '--repo', target, '--commit', options.commit ?? git('rev-parse', 'HEAD'),
      '--package', options.packageId ?? packageId, '--out', output, ...(options.extra ?? [])], {encoding: 'utf8', env: {...process.env, GIT_NO_LAZY_FETCH: '1', GIT_NO_REPLACE_OBJECTS: '1', ...options.env}});
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
  for (const name of ['src/pixel-ownership.js', 'scripts/geography-prefetch.mjs']) {
    const f = fixture(); try {
      fs.appendFileSync(path.join(f.repo, name), '\n// uncommitted source drift\n');
      const r = f.run(); assert.notEqual(r.status, 0); assert.match(r.stderr, /Executed source differs/); assert.equal(fs.existsSync(r.output), false);
    } finally { f.cleanup(); }
  }
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


test('retired extraction refuses while package observation supplies complete original intervals without materialized data', () => {
  const expectedPackage = {package_id: packageId, native_blocks: [0], native_cells: 5, intervals: 5};
  const expectedRows = [[0, 0, 1, [1], [1], 'land'], [0, 2, 3, [2], [2], 'land'],
    [0, 3, 4, [1], [1], 'land'], [1, 1, 2, [2], [2], 'land'], [2, 1, 2, [1], [1], 'land']];
  for (const splitCandidates of [false, true]) {
    const f = fixture({splitCandidates}); try {
      // Include the actual omitted-input role: its plain body is authenticated
      // from Git even when no .json or .json.gz sibling exists in the checkout.
      const seamName = queueRoot + '/normalized-source-seams.json';
      const seam = f.write(seamName, {version: 1, original: 'retained seam metadata'});
      const queue = JSON.parse(fs.readFileSync(path.join(f.repo, queueRoot, 'source-package-queue.json')));
      queue.input_sha256['normalized-source-seams.json'] = sha(seam);
      f.write(queueRoot + '/source-package-queue.json', queue); f.commit();
      const destination = path.join(f.repo, 'original-extraction');
      const result = spawnSync(process.execPath, [path.join(f.repo, queueRoot, 'source-batch-intervals.mjs'), packageId, destination], {encoding: 'utf8'});
      assert.notEqual(result.status, 0);
      assert.match(result.stderr, /Standalone extraction was removed; use scripts\/observe-selected-owners\.mjs/);
      assert.equal(result.stdout, '');
      assert.equal(fs.existsSync(destination), false);
      // Use real Git sparse selection, not a mock reader or copied extraction.
      f.git('sparse-checkout', 'set', '--no-cone', ...sources.map(name => '/' + name),
        '/scripts/run-geographic-check.py', '/package.json');
      for (const name of [seamName, seamName + '.gz', queueRoot + '/source-package-queue.json',
        queueRoot + '/source-feature-roster.json.gz', 'inputs/bank/part-0.gz'])
        assert.equal(fs.existsSync(path.join(f.repo, name)), false, name);
      const observed = f.run(); assert.equal(observed.status, 0, observed.stderr); assert.equal(observed.report.query_count, 5);
      assert.deepEqual(observed.report.original_package, expectedPackage);
      assert.deepEqual(observed.report.original_intervals, [{block: 0, rows: expectedRows}]);
      assert.equal(observed.report.original_intervals_sha256,
        sha(Buffer.from(JSON.stringify(observed.report.original_intervals) + '\n')));
      const expanded = observed.report.original_intervals.flatMap(({rows}) => rows.flatMap(([y, start, end]) =>
        Array.from({length: end - start}, (_, i) => ({x: start + i, y}))));
      assert.deepEqual(expanded, observed.report.keys.map(({x, y}) => ({x, y})));
      assert.ok(observed.report.consumed_inputs.some(pin => pin.path === seamName && pin.sha256 === sha(seam)));
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


// Genuine cold Git objects, not missing working-tree copies. Only committed code,
// commit/tree metadata and the test transport are installed before the CLI runs.
function coldFixture({splitCandidates = false} = {}) {
  const f = fixture({multiBlock: !splitCandidates, splitCandidates}), root = path.join(f.repo, 'cold'), bin = path.join(f.repo, 'bin');
  const forbidden = ['data/world-index.json', 'inputs/source-geometries.json', 'inputs/certificate.json', 'inputs/ledger.json'];
  for (const name of forbidden) f.write(name, {forbidden: name});
  const head = f.commit(), objects = f.git('cat-file', '--batch-all-objects', '--batch-check=%(objectname) %(objecttype)').split('\n').map(s => s.split(' '));
  const realGit = execFileSync('which', ['git'], {encoding: 'utf8'}).trim();
  const realGitExecPath = execFileSync(realGit, ['--exec-path'], {encoding: 'utf8'}).trim();
  const git = (args, input) => execFileSync(realGit, ['-C', root, ...args], {input, stdio: ['pipe', 'pipe', 'pipe']});
  fs.mkdirSync(root); fs.mkdirSync(bin); git(['init']);
  for (const [oid, kind] of objects.filter(([, kind]) => kind !== 'blob')) {
    const raw = execFileSync(realGit, ['-C', f.repo, 'cat-file', kind, oid]);
    assert.equal(git(['hash-object', '-w', '-t', kind, '--stdin'], raw).toString().trim(), oid);
  }
  const codeOids = new Set();
  for (const name of [...sources, 'scripts/run-geographic-check.py', 'package.json']) {
    const raw = execFileSync(realGit, ['-C', f.repo, 'show', head + ':' + name]);
    const oid = git(['hash-object', '-w', '--stdin'], raw).toString().trim(); codeOids.add(oid);
    fs.mkdirSync(path.dirname(path.join(root, name)), {recursive: true}); fs.writeFileSync(path.join(root, name), raw);
  }
  git(['update-ref', 'refs/heads/fixture', head]); git(['symbolic-ref', 'HEAD', 'refs/heads/fixture']);
  const log = path.join(f.repo, 'fetches.jsonl'), preload = path.join(f.repo, 'metadata.mjs');
  const implementation = path.join(bin, 'implementation'), launchLog = path.join(f.repo, 'git-launches.jsonl');
  fs.mkdirSync(path.join(implementation, 'bin'), {recursive: true});
  const helperExecPath = path.join(implementation, 'libexec', 'git-core');
  fs.mkdirSync(helperExecPath, {recursive: true});
  for (const command of ['pack-objects', 'rev-list', 'index-pack']) {
    fs.writeFileSync(path.join(helperExecPath, 'git-' + command), `#!${process.execPath}
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
const command = ${JSON.stringify(command)}, args = process.argv.slice(2), invocation = [command, ...args];
const gitHelperArgv = ${JSON.stringify(gitHelperArgv)};
const exactGitHelper = ${exactGitHelper.toString()};
fs.appendFileSync(${JSON.stringify(launchLog)}, JSON.stringify(invocation) + '\\n');
if (!exactGitHelper(invocation)) throw Error('Unexpected Git helper invocation: ' + JSON.stringify(invocation));
const target = ${JSON.stringify(realGitExecPath)} + '/git-' + command;
const r = spawnSync(target, args, {stdio: 'inherit', env: process.env});
process.exit(r.status ?? 1);
`, {mode: 0o755});
  }
  // The PATH launcher resolves an implementation but cannot serve as that implementation.
  // Resolve the implementation once; internal helpers are observed through GIT_EXEC_PATH
  // because newer Git versions bypass PATH when launching them.
  fs.writeFileSync(path.join(bin, 'git'), `#!${process.execPath}
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
const args = process.argv.slice(2);
const gitHelperArgv = ${JSON.stringify(gitHelperArgv)};
const exactGitHelper = ${exactGitHelper.toString()};
fs.appendFileSync(${JSON.stringify(launchLog)}, JSON.stringify(args) + '\\n');
if (args.length === 1 && args[0] === '--exec-path') {
  process.stdout.write(${JSON.stringify(path.join(implementation, 'libexec', 'git-core'))} + '\\n');
  process.exit(0);
}
const helper = exactGitHelper(args) ? args : null;
if (helper) {
  const env = {...process.env, GIT_EXEC_PATH: ${JSON.stringify(helperExecPath)}};
  const r = spawnSync(${JSON.stringify(realGit)}, args, {stdio: 'inherit', env});
  process.exit(r.status ?? 1);
}
throw Error('Unexpected Git launcher invocation: ' + JSON.stringify(args));
`, {mode: 0o755});
  const setup = {origin: f.repo, realGit, log, metadataLog: path.join(f.repo, 'metadata-requests.jsonl')};
  const transport = path.join(implementation, 'transport.mjs');
  // Only the local fetch interception needs Node; ordinary Git reads stay direct.
  fs.writeFileSync(path.join(implementation, 'bin', 'git'), `#!/bin/sh
for arg do
  if [ "$arg" = fetch ]; then exec ${JSON.stringify(process.execPath)} ${JSON.stringify(transport)} "$@"; fi
done
GIT_EXEC_PATH=${JSON.stringify(helperExecPath)} exec ${JSON.stringify(realGit)} "$@"
`, {mode: 0o755});
  fs.writeFileSync(transport, `#!${process.execPath}
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
const s = ${JSON.stringify(setup)}, args = process.argv.slice(2), input = fs.readFileSync(0);
if (args.includes('fetch')) {
  if (!['https://github.com/ChengshuLi/WorldAtlas.git','--stdin','--filter=blob:none','--no-auto-maintenance','--no-tags','--no-write-fetch-head','--no-recurse-submodules','fetch.negotiationAlgorithm=noop'].every(flag => args.includes(flag)) || process.env.GIT_NO_LAZY_FETCH !== '1' || process.env.GIT_NO_REPLACE_OBJECTS !== '1') throw Error('Unbounded transport');
  fs.appendFileSync(s.log, JSON.stringify(input.toString().trim().split('\\n')) + '\\n');
  if (Number(process.env.OBSERVATION_TEST_FAIL_FETCH) === fs.readFileSync(s.log, 'utf8').trim().split('\\n').length) process.exit(1);
  args[args.indexOf('https://github.com/ChengshuLi/WorldAtlas.git')] = s.origin;
}
const r = spawnSync(s.realGit, args, {input, stdio: ['pipe','inherit','inherit']}); process.exit(r.status ?? 1);
`, {mode: 0o755});
  fs.writeFileSync(preload, `import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
const s = ${JSON.stringify(setup)};
if (process.env.OBSERVATION_TEST_NO_SPACE) fs.statfsSync = () => ({bavail: 0, bsize: 4096});
globalThis.fetch = async url => {
  const u = new URL(url), match = new RegExp('^/repos/ChengshuLi/WorldAtlas/git/trees/([a-f0-9]{40})$').exec(u.pathname);
  if (u.origin !== 'https://api.github.com' || u.search !== '' || !match) throw Error('Forbidden network endpoint: ' + url);
  fs.appendFileSync(s.metadataLog, url + '\\n');
  const raw = execFileSync(s.realGit, ['-C',s.origin,'ls-tree','-tlz',match[1]]).toString();
  const tree = raw.split('\\0').filter(Boolean).map(line => {
    const [meta,path] = line.split('\\t'), [mode,type,sha,size] = meta.trim().split(/\\s+/);
    return {path,mode,type,sha,...(type === 'blob' ? {size:Number(size)} : {})};
  });
  if (process.env.OBSERVATION_TEST_BAD_DESCRIPTOR) tree.find(r => r.path === 'ownership-selection.json').sha = '0'.repeat(40);
  return {ok:true,json:async()=>({sha:match[1],truncated:false,tree})};
};
`);
  const inventory = () => git(['cat-file', '--batch-all-objects', '--batch-check=%(objectname) %(objecttype)']).toString().trim().split('\n').filter(Boolean).map(s => s.split(' '));
  const batches = () => fs.existsSync(log) ? fs.readFileSync(log, 'utf8').trim().split('\n').filter(Boolean).map(JSON.parse) : [];
  const run = options => f.run({repo: root, commit: head, nodeArgs: ['--import', preload], ...options,
    env: {PATH: bin + path.delimiter + process.env.PATH, ...options?.env}});
  return {...f, root, head, codeOids, forbidden, gitCold: git, inventory, batches, run,
    launches: () => fs.existsSync(launchLog) ? fs.readFileSync(launchLog, 'utf8').trim().split('\n').map(JSON.parse) : [],
    launcher: path.join(bin, 'git'),
    metadataRequests: () => fs.existsSync(setup.metadataLog) ? fs.readFileSync(setup.metadataLog, 'utf8') : ''};
}


test('cold Git launcher rejects an unrecognized invocation', () => {
  const f = coldFixture(); try {
    const r = spawnSync(f.launcher, ['unexpected-command'], {encoding: 'utf8', env: process.env});
    assert.notEqual(r.status, 0);
    assert.match(r.stderr, /Unexpected Git launcher invocation/);
    assert.deepEqual(f.launches(), [['unexpected-command']]);
  } finally { f.cleanup(); }
});

for (const splitCandidates of [false, true]) test('one cold ' + (splitCandidates ? 'split-member' : 'multiblock') + ' command acquires exactly its original and native inputs; warm reuse fetches nothing', t => {
  const f = coldFixture({splitCandidates}); try {
    assert.deepEqual(new Set(f.inventory().filter(([, kind]) => kind === 'blob').map(([oid]) => oid)), f.codeOids);
    const r = f.run();
    assert.deepEqual(f.launches().filter(args => args.length === 1 && args[0] === '--exec-path'), [['--exec-path']], 'cold bootstrap resolves the implementation once');
    const helpers = f.launches().filter(args => !(args.length === 1 && args[0] === '--exec-path'));
    assert(helpers.length > 0, 'cold fetch exercises internal Git helpers');
    assert(helpers.every(exactGitHelper), 'only exact supported Git helper argv is passed through');
    const coldHelperCalls = [...helpers];
    assert.equal(r.status, 0, r.stderr);
    assert.equal(r.report.query_count, 5); assert.deepEqual(r.report.keys.map(({x,y}) => ({x,y})), keys);
    assert.deepEqual(r.report.original_intervals.map(b => b.block), splitCandidates ? [0] : [0, 1]);
    assert.equal(r.report.code_commit, f.head); assert.equal(r.report.commit, f.head);
    const expectedPaths = ['data/ownership-selection.json', 'inputs/native/manifest.json', 'inputs/owners.json', 'inputs/latitudes.gz',
      'inputs/registry.json','inputs/sidecar.json','inputs/envelope.json','inputs/patch.json','inputs/bank/index.json',
      ...[0,1,2].map(i => 'inputs/bank/part-' + i + '.gz'),
      ...['source-package-queue.json','source-feature-roster.json.gz','source-raster-summary.json','source-census-summary.json','physical-unassigned-summary.json','ownership-binding.json'].map(n => queueRoot + '/' + n),
      ...(splitCandidates ? ['source-split-0.json.gz','source-split-1.json.gz','physical-support-block-000.json.gz','inland-water-support-block-000.json.gz']
        : [0,1].flatMap(b => ['source-candidates','physical-support','inland-water-support'].map(p => p + '-block-' + String(b).padStart(3,'0') + '.json.gz'))).map(n => queueRoot + '/' + n)];
    const expected = new Set(expectedPaths.map(p => f.git('rev-parse', f.head + ':' + p)));
    assert.deepEqual(new Set(f.batches().flat()), expected);
    assert.equal(f.batches().flat().length, expected.size, 'unchanged OIDs deduplicate across discovery phases');
    assert(f.batches().some(batch => batch.length >= (splitCandidates ? 4 : 5)), 'whole original member layer shares a batch');
    const imported = new Set(f.inventory().filter(([oid,kind]) => kind === 'blob' && !f.codeOids.has(oid)).map(([oid]) => oid));
    assert.deepEqual(imported, expected);
    const metadataUrls = f.metadataRequests().trim().split('\n');
    assert.equal(new Set(metadataUrls).size, metadataUrls.length, 'each containing tree is requested only once');
    const rootTree = f.git('rev-parse', f.head + '^{tree}');
    assert(!f.metadataRequests().includes(rootTree), 'never request unrelated repository-root metadata');
    for (const p of f.forbidden) assert(!imported.has(f.git('rev-parse', f.head + ':' + p)));
    assert.equal(r.report.acquisition.fetched_objects, expected.size);
    const declaredBytes = [...expected].reduce((n, oid) => n + Number(f.git('cat-file','-s',oid)), 0);
    assert.equal(r.report.acquisition.fetched_bytes, declaredBytes);
    assert.equal(r.report.acquisition.complete_scientific_closure, false);
    t.diagnostic(JSON.stringify({variant: splitCandidates ? 'split' : 'multiblock', acquired_objects: expected.size, declared_blob_bytes: declaredBytes, fetch_batches: f.batches().length}));
    const prior = f.batches().length, metadata = f.metadataRequests(), warm = f.run(); assert.equal(warm.status, 0, warm.stderr);
    assert.deepEqual(f.launches().filter(args => args.length === 1 && args[0] === '--exec-path'), [['--exec-path'], ['--exec-path']], 'warm acquisition also reuses resolved Git');
    assert.deepEqual(f.launches().filter(args => !(args.length === 1 && args[0] === '--exec-path')), coldHelperCalls, 'warm reuse invokes no additional Git helpers');
    assert.equal(warm.report.acquisition.fetched_objects, 0); assert.equal(warm.report.acquisition.fetched_bytes, 0);
    assert.equal(f.batches().length, prior); assert.equal(f.metadataRequests(), metadata); assert.deepEqual(warm.report.keys, r.report.keys);
    assert.deepEqual(warm.report.original_intervals, r.report.original_intervals);
    assert.equal(warm.report.original_intervals_sha256, r.report.original_intervals_sha256);
  } finally { f.cleanup(); }
});

for (const [name, env, expected] of [
  ['wrong immutable descriptor', {OBSERVATION_TEST_BAD_DESCRIPTOR:'1'}, /Remote descriptor differs/],
  ['failed exact transport', {OBSERVATION_TEST_FAIL_FETCH:'1'}, /Geography object acquisition failed/],
  ['insufficient disk', {OBSERVATION_TEST_NO_SPACE:'1'}, /Insufficient free disk/],
]) test('cold observation refuses ' + name + ' without a final receipt', () => {
  const f = coldFixture(); try {
    const before = f.inventory(), r = f.run({env});
    assert.notEqual(r.status, 0); assert.match(r.stderr, expected); assert.equal(fs.existsSync(r.output), false);
    assert.deepEqual(f.inventory(), before);
    if (!env.OBSERVATION_TEST_FAIL_FETCH) assert.equal(f.batches().length, 0);
  } finally { f.cleanup(); }
});


test('a partial acquisition failure leaves no receipt and an ordinary retry reuses imported bodies', () => {
  const f = coldFixture(); try {
    const failed = f.run({env: {OBSERVATION_TEST_FAIL_FETCH:'2'}});
    assert.notEqual(failed.status, 0); assert.match(failed.stderr, /Geography object acquisition failed/);
    assert.deepEqual(f.launches().filter(args => args.length === 1 && args[0] === '--exec-path'), [['--exec-path']], 'partial run resolves the implementation once');
    assert(f.launches().filter(args => !(args.length === 1 && args[0] === '--exec-path')).every(exactGitHelper), 'partial run rejects launcher drift');
    assert.equal(f.batches().length, 2, 'the second transport attempt is the injected failure');
    assert.equal(fs.existsSync(failed.output), false);
    const retained = f.inventory().filter(([oid,kind]) => kind === 'blob' && !f.codeOids.has(oid)).map(([oid]) => oid);
    assert.deepEqual(retained, [f.git('rev-parse', f.head + ':data/ownership-selection.json')]);
    const prior = f.batches().length, resumed = f.run(); assert.equal(resumed.status, 0, resumed.stderr);
    assert.deepEqual(f.launches().filter(args => args.length === 1 && args[0] === '--exec-path'), [['--exec-path'], ['--exec-path']], 'retry reuses the resolved implementation');
    assert(f.launches().filter(args => !(args.length === 1 && args[0] === '--exec-path')).every(exactGitHelper), 'retry keeps rejecting launcher drift');
    assert.equal(resumed.report.query_count, 5);
    assert(!f.batches().slice(prior).flat().some(oid => retained.includes(oid)));
    assert.equal(resumed.report.acquisition.fetched_objects,
      f.inventory().filter(([oid,kind]) => kind === 'blob' && !f.codeOids.has(oid)).length - retained.length);
  } finally { f.cleanup(); }
});
