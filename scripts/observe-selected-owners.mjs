// Literal selected-product observation, not source/geometric qualification.
// No geometry resolver, qualification shortcut, or heavy/light mode belongs here.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {gunzipSync} from 'node:zlib';
import {selectedBootstrap, NativeAssetImage, decodeVisibilityLatitudes} from './check-effective-geographic-regression.mjs';
import {openNativeWordStore} from './native-word-store.mjs';
import {admitNativePatchStore} from './native-patch-store.mjs';
import {createAcquisition, githubTree} from './geography-prefetch.mjs';
import {packageInputs, packageIntervals, ROOT as queueDirectory} from '../coordination/engineering/global-current-cell-work-queue-20261014/source-batch-intervals.mjs';
import {ownershipRun} from '../src/pixel-ownership.js';
import {nativeBaseSelection, valueSha} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';

const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const relative = name => typeof name === 'string' && !path.posix.isAbsolute(name) &&
  name.split('/').every(p => p && p !== '.' && p !== '..') && !name.includes('\\');
const codeRoot = fileURLToPath(new URL('../', import.meta.url));
const ownCode = ['scripts/observe-selected-owners.mjs', 'scripts/geography-prefetch.mjs', 'scripts/native-word-store.mjs',
  'scripts/native-patch-store.mjs', 'src/pixel-ownership.js', 'src/pixel-grid.js',
  'coordination/engineering/global-current-cell-work-queue-20261014/source-batch-intervals.mjs'];

export async function observeSelectedPackage({repo, commit, packageId}) {
  assert.match(commit ?? '', /^[a-f0-9]{40}$/, 'An exact committed revision is required');
  assert.equal(process.env.GIT_NO_LAZY_FETCH, '1', 'Set GIT_NO_LAZY_FETCH=1; only explicit pinned acquisition is allowed');
  assert.equal(process.env.GIT_NO_REPLACE_OBJECTS, '1', 'Set GIT_NO_REPLACE_OBJECTS=1');
  const {beforeReader: reader, executionCode} = selectedBootstrap(repo, commit, commit);
  try { reader.git('--no-lazy-fetch', '--version'); }
  catch { throw Error('Use a Git implementation supporting --no-lazy-fetch; no compatibility fallback is allowed'); }
  const codeCommit = reader.git('rev-parse', 'HEAD').toString().trim();
  const requireHead = () => assert.equal(reader.git('rev-parse', 'HEAD').toString().trim(), codeCommit,
    'Executable checkout changed during observation');
  requireHead();
  const code = [...executionCode, ...ownCode.map(name => {
    const file = path.join(codeRoot, name);
    assert.ok(fs.lstatSync(file).isFile() && fs.realpathSync(file) === file, 'Nonordinary observation code');
    const body = fs.readFileSync(file);
    return {path: name, bytes: body.length, sha256: sha(body)};
  })];
  for (const p of code) assert.equal(sha(reader.read(p.path, {version: codeCommit})), p.sha256, 'Executed source differs: ' + p.path);

  // Reuse exact-OID transport, never Git lazy fetching or the full geography driver.
  // Warm bodies need no remote metadata. A cold size is bound to this same tree.
  const missing = new Set();
  const acquisition = createAcquisition({repo, execute: (_command, args, options) => execFileSync(reader.gitExecutable, args, options),
    loadTree: tree => githubTree(tree, false), loadDescriptor: async (version, name) => {
    const line = reader.treeRoute(name, version), match = /^(100644|100755) blob ([a-f0-9]{40})\t/.exec(line);
    assert.ok(match && line.slice(line.indexOf('\t') + 1) === name + '\0', 'Require ordinary observation input: ' + name);
    const oid = match[2], status = reader.gitBatch(['--no-lazy-fetch', 'cat-file', '--batch-check=%(objectname) %(objecttype) %(objectsize)'], oid + '\n', 128).toString();
    if (status === oid + ' missing\n') {
      missing.add(oid);
      const parent = path.posix.dirname(name);
      const tree = reader.git('rev-parse', parent === '.' ? version + '^{tree}' : version + ':' + parent).toString().trim();
      return (await acquisition.tree(tree)).get(path.posix.basename(name));
    }
    const size = new RegExp('^' + oid + ' blob (0|[1-9][0-9]*)\\n$').exec(status);
    assert.ok(size && Number.isSafeInteger(Number(size[1])), 'Invalid local immutable input: ' + name);
    return {type: 'blob', mode: match[1], sha: oid, size: Number(size[1])};
  }});
  const acquire = async pins => {
    const rows = [];
    for (const p of pins) rows.push(await acquisition.pin(commit, p));
    const growth = [...new Map(rows.filter(p => missing.has(p.oid)).map(p => [p.oid, p.bytes])).values()].reduce((a, b) => a + b, 0);
    if (growth) {
      const disk = fs.statfsSync(repo);
      assert.ok(Number.isSafeInteger(growth) && growth < disk.bavail * disk.bsize, 'Insufficient free disk for declared missing observation inputs');
    }
    acquisition.acquire(rows);
    for (const row of rows) missing.delete(row.oid);
  };
  await acquire([{path: 'data/ownership-selection.json'}]);
  const selection = reader.json('data/ownership-selection.json');
  await acquire([{path: selection.manifest_path, sha256: selection.sha256}]);
  const manifest = reader.json(selection.manifest_path, {expected: selection.sha256});
  assert.equal(selection.method, 'native-linear-evenodd-first-owner-v1');
  assert.equal(manifest.method, selection.method);
  assert.equal(manifest.geographic_release, selection.release_id);
  assert.equal(manifest.version, 2);
  assert.ok(Number.isSafeInteger(manifest.size) && manifest.size > 1);
  assert.equal(manifest.coordinateBits, Math.ceil(Math.log2(manifest.size)));
  // The existing original queue/extractor owns scope. There is no arbitrary-key,
  // supported-subset, certificate, latitude-file or geometry-mode CLI option.
  assert.ok(typeof packageId === 'string' && packageId.length, 'Supply the exact original package ID');
  const queueRoot = path.relative(codeRoot, queueDirectory).split(path.sep).join('/'), bodies = new Map();
  const queuePath = name => {
    assert.ok(relative(name), 'Unsafe original queue input');
    const file = queueRoot + '/' + name;
    return reader.treeRoute(file) ? file : file + '.gz';
  };
  const loadQueue = name => {
    if (!bodies.has(name)) {
      const file = queuePath(name), raw = reader.read(file);
      bodies.set(name, file === queueRoot + '/' + name ? raw : gunzipSync(raw));
    }
    return bodies.get(name);
  };
  await acquire([{path: queuePath('source-package-queue.json')}]);
  const queue = JSON.parse(loadQueue('source-package-queue.json'));
  assert.equal(queue.packages.filter(p => p.package_id === packageId).length, 1, 'Unknown or duplicate package');
  await acquire(Object.keys(queue.input_sha256 ?? {}).map(name => ({path: queuePath(name)})));
  const originalInputs = packageInputs(packageId, loadQueue);
  await acquire(originalInputs.inputs.map(p => ({...p, path: queuePath(p.path)})));
  const original = packageIntervals(packageId, loadQueue);
  const originalGrid = JSON.parse(bodies.get('ownership-binding.json') ?? 'null');
  assert.ok(originalGrid && originalGrid.size === manifest.size && originalGrid.selection?.method === manifest.method &&
    originalGrid.native_latitudes?.decoded_bytes === manifest.native_latitudes?.decoded_bytes &&
    originalGrid.native_latitudes?.decoded_sha256 === manifest.native_latitudes?.decoded_sha256,
  'Original package grid/method/normative latitude identity differs from the selected product');
  const requested = [];
  for (const {rows: intervals} of original.blocks) for (const [y, start, end] of intervals) {
    assert.ok([y, start, end].every(Number.isSafeInteger) && y >= 0 && y < manifest.size &&
      start >= 0 && end > start && end <= manifest.size, 'Original interval outside the selected native grid');
    for (let x = start; x < end; x++) requested.push({x, y});
  }
  assert.ok(requested.length > 0 && requested.length === original.package.native_cells, 'Complete original package required');
  assert.equal(new Set(requested.map(k => k.y + ':' + k.x)).size, requested.length, 'Duplicate original package key');
  const rows = [...new Set(requested.map(k => k.y))].sort((a, b) => a - b);

  function readPin(p) {
    const raw = reader.readPinned([p])[0];
    if (p.decoded_bytes === undefined) return raw;
    const decoded = gunzipSync(raw, {maxOutputLength: p.decoded_bytes});
    assert.equal(decoded.length, p.decoded_bytes);
    assert.equal(sha(decoded), p.decoded_sha256, 'Pinned decoded body differs');
    return decoded;
  }
  const hook = selection.additive_release;
  assert.ok(hook, 'This observation entrypoint requires the selected retained additive product');
  await acquire([hook]);
  const sideRaw = reader.read(hook.path, {expected: hook.sha256});
  assert.equal(sideRaw.length, hook.bytes);
  const side = JSON.parse(sideRaw);
  assert.equal(side.kind, 'retained-native-additive-selection-v2');
  assert.equal(side.version, 2);
  assert.deepEqual(side.base_selection, nativeBaseSelection(selection));
  const assets = side.logical_asset_map;
  await acquire([assets.base_manifest, assets.owner_roster, side.runtime_envelope, side.authority_registry]);
  assert.equal(assets.base_manifest.sha256, selection.sha256);
  assert.deepEqual(JSON.parse(readPin(assets.base_manifest)), manifest);
  assert.equal(assets.owner_roster.sha256, manifest.original_assets.bounds.sha256);
  const owners = JSON.parse(readPin(assets.owner_roster));
  assert.equal(owners.length, manifest.accounting.owners);
  assert.ok(owners.every((o, i) => o.index === i + 1 && typeof o.id === 'string' && o.id.length));
  assert.equal(new Set(owners.map(o => o.id)).size, owners.length);
  const envelope = JSON.parse(readPin(side.runtime_envelope));
  const registry = JSON.parse(readPin(side.authority_registry));
  for (const role of ['base_manifest', 'owner_roster', 'patch', 'ledger']) {
    for (const field of ['bytes', 'sha256', 'decoded_bytes', 'decoded_sha256'])
      assert.equal(assets[role][field], envelope[role][field], role + ' ' + field);
  }
  assert.equal(envelope.base_reference.footprints_sha256, manifest.footprints_sha256);

  // Same original-commit/same-path whole-hash alias rule as inspectSelected.
  const latitudePin = manifest.native_latitudes;
  assert.equal(latitudePin.root, 'repository');
  assert.equal(latitudePin.role, 'immutable-normative-rule-input');
  assert.match(latitudePin.commit, /^[a-f0-9]{40}$/);
  let latitudeVersion = latitudePin.commit;
  try { reader.git('--no-lazy-fetch', 'cat-file', '-e', latitudeVersion + '^{commit}'); }
  catch { latitudeVersion = commit; }
  await acquire([latitudePin]);
  const latitudes = decodeVisibilityLatitudes(reader.read(latitudePin.path,
    {version: latitudeVersion, expected: latitudePin.sha256}), latitudePin, manifest.size);
  assert.ok(latitudes.every(Number.isFinite), 'Nonfinite normative latitude');

  const transport = manifest.native_asset_transport;
  assert.ok(transport?.index, 'Missing selected native transport index');
  await acquire([transport.index]);
  const index = reader.json(transport.index.path, {expected: transport.index.sha256});
  assert.ok(Array.isArray(index.parts), 'Missing native transport fragments');
  await acquire([assets.patch, ...index.parts.map(p => {
    assert.ok(relative(p.path), 'Unsafe native transport fragment');
    return {...p, path: path.posix.join(path.posix.dirname(transport.index.path), p.path)};
  })]);
  const image = new NativeAssetImage(reader, manifest, selection.manifest_path);
  const logicalRoot = path.posix.dirname(selection.manifest_path), stores = [];
  let patchStore;
  try {
    const rowPins = manifest.parts.filter(p => p.kind === 'rows');
    assert.equal(rowPins.length, 1);
    assert.equal(rowPins[0].offset, 0);
    assert.equal(rowPins[0].words, manifest.size * 2);
    const open = async pin => {
      assert.equal(pin.encoding, 'byte-shuffle');
      const store = await openNativeWordStore(image.logicalStream(path.posix.join(logicalRoot, pin.path), pin), pin, {directory: os.tmpdir()});
      stores.push(store); return store;
    };
    const table = await open(rowPins[0]);
    let cursor = 0;
    for (let y = 0; y < manifest.size; y++) {
      assert.equal(table.get(y * 2), cursor, 'Native row partition differs');
      cursor += table.get(y * 2 + 1);
    }
    assert.equal(cursor * 2, manifest.runWords, 'Native rows omit run words');
    const ranges = rows.map(y => ({y, start: table.get(y * 2) * 2,
      end: (table.get(y * 2) + table.get(y * 2 + 1)) * 2}));
    let offset = 0;
    const runPins = manifest.parts.filter(p => p.kind === 'runs');
    for (const p of runPins) {
      assert.equal(p.offset, offset);
      assert.ok(Number.isSafeInteger(p.words) && p.words > 0 && p.words % 2 === 0);
      offset += p.words;
    }
    assert.equal(offset, manifest.runWords);
    assert.equal(rowPins.length + runPins.length, manifest.parts.length, 'Unknown native part kind');
    const needed = runPins.filter(p => ranges.some(r => r.start < p.offset + p.words && p.offset < r.end));
    const baseRows = new Map(rows.map(y => [y, []]));
    for (const p of needed) {
      const words = await open(p);
      for (const r of ranges) for (let i = Math.max(r.start, p.offset); i < Math.min(r.end, p.offset + p.words); i += 2) {
        const v = ownershipRun({version: 2, coordinateBits: manifest.coordinateBits,
          runs: Uint32Array.of(words.get(i - p.offset), words.get(i - p.offset + 1))}, 0);
        baseRows.get(r.y).push([v.start, v.end, v.id]);
      }
      words.close();
    }
    for (const r of ranges) {
      const intervals = baseRows.get(r.y); let end = 0;
      assert.equal(intervals.length, (r.end - r.start) / 2);
      for (const [a, b, owner] of intervals) {
        assert.ok(a >= end && b > a && b <= manifest.size && owner > 0 && owner <= owners.length, 'Invalid selected native row'); end = b;
      }
    }
    const p = assets.patch;
    patchStore = await admitNativePatchStore({chunks: [readPin(p)], directory: os.tmpdir(),
      size: manifest.size, ownerCount: owners.length,
      expected: {bytes: p.decoded_bytes ?? p.bytes, sha256: p.decoded_sha256 ?? p.sha256}});
    assert.equal(patchStore.metadata.kind, 'unassigned-native-cells-v1');
    assert.equal(patchStore.metadata.version, 2);
    assert.deepEqual(patchStore.metadata.base_reference, envelope.base_reference);
    assert.deepEqual(patchStore.metadata.effective_reference, envelope.effective_reference);
    assert.equal(patchStore.metadata.ledger_sha256, assets.ledger.decoded_sha256 ?? assets.ledger.sha256);
    assert.equal(patchStore.metadata.authority_registry_sha256, valueSha(registry));
    const patchRows = new Map(rows.map(y => {
      const row = patchStore.rowAt(y); return [y, row ? Array.from(patchStore.intervals(row)) : []];
    }));
    const contacts = (runs, x) => runs.filter(([a, b]) => a <= x && x < b).map(r => r[2]);
    const observations = requested.map(k => {
      const b = contacts(baseRows.get(k.y), k.x), a = contacts(patchRows.get(k.y), k.x);
      assert.ok(b.length <= 1 && a.length <= 1);
      const overlap = b.length > 0 && a.length > 0, index = overlap ? null : (a[0] ?? b[0] ?? 0);
      return {...k, latitude: latitudes[k.y], base_owner: b[0] ?? 0, accepted_additive_owner: a[0] ?? 0,
        effective_selected_owner: index, owner_id: index ? owners[index - 1].id : null, existing_product_overlap: overlap};
    });
    requireHead();
    return {version: 1, kind: 'literal-selected-owner-observation-v1', scientific_qualification: false,
      commit, code_commit: codeCommit, original_package: original.package,
      acquisition: {...acquisition.stats, scope: 'original-package-and-selected-native-observation'},
      original_intervals: original.blocks,
      original_intervals_sha256: sha(Buffer.from(JSON.stringify(original.blocks) + '\n')), query_count: requested.length,
      query_encoding: 'JSON.stringify([{x,y},...]) in input order, followed by LF',
      query_sha256: sha(Buffer.from(JSON.stringify(requested) + '\n')),
      selector_pin: reader.inventory.get(commit + ':data/ownership-selection.json'),
      native_manifest_sha256: selection.sha256, patch_pin: p, row_member: rowPins[0], run_members: needed,
      native_latitudes: latitudePin, consumed_latitudes: reader.inventory.get(latitudeVersion + ':' + latitudePin.path),
      latitude_whole_body_alias: latitudeVersion !== latitudePin.commit, keys: observations,
      execution_code: code, consumed_inputs: [...reader.inventory.values()].filter(p => p.whole_body_consumed),
      limits: ['Literal selected-product observation of this original queue package; not source applicability, a package qualification certificate or complete repair acceptance.',
        'Original interval classes retain the queue mask observations, not current physical qualification.',
        'No current physical water/land classification, source applicability, geometric overlay, repair acceptance or publication approval is asserted.',
        'Base and patch remain separate; an existing overlap reports null, never invented precedence. Intervals are [start,end-exclusive,owner-index].',
        'Ledger body and source authorities are not reread; only the selected ledger digest is joined to authenticated patch metadata.']};
  } finally { patchStore?.close(); for (const store of stores) store.close(); }
}

function newOutput(filename) {
  const destination = path.resolve(filename), parent = path.dirname(destination);
  assert.equal(fs.realpathSync(parent), parent, 'Output parent must be an existing ordinary directory');
  try { fs.lstatSync(destination); throw Error('Observation output already exists'); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  return destination;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const options = {};
  for (let i = 2; i < process.argv.length; i += 2) {
    const key = process.argv[i], value = process.argv[i + 1];
    assert.ok(['--repo', '--commit', '--package', '--out'].includes(key) && value && !Object.hasOwn(options, key.slice(2)), 'Use --repo, --commit, --package and --out once, each with a value');
    options[key.slice(2)] = value;
  }
  assert.ok(options.commit && options.package && options.out, 'Require --commit EXACT_DATA_HEAD --package ORIGINAL_PACKAGE_ID --out NEW_OBSERVATION.json');
  options.repo ??= process.cwd();
  const output = newOutput(options.out);
  const report = await observeSelectedPackage({...options, packageId: options.package});
  newOutput(output);
  const temporary = fs.mkdtempSync(path.join(path.dirname(output), '.owner-observation-'));
  try {
    const staged = path.join(temporary, 'observation.json');
    fs.writeFileSync(staged, JSON.stringify(report, null, 2) + '\n', {flag: 'wx'});
    fs.linkSync(staged, output); // Atomic no-replace publication of the complete observation.
  } finally { fs.rmSync(temporary, {recursive: true}); }
  process.stdout.write(JSON.stringify({kind: report.kind, commit: report.commit, query_count: report.query_count, output}) + '\n');
}
