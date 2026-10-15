import {test, mock} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gzipSync, gunzipSync} from 'node:zlib';
import {fileURLToPath, pathToFileURL} from 'node:url';

const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const script = fileURLToPath(new URL('../scripts/prepare-startup-ownership.mjs', import.meta.url));
async function absent(file) { await assert.rejects(fs.lstat(file), {code: 'ENOENT'}); }

async function syntheticPreparation() {
  const cache = path.resolve('.cache');
  await fs.mkdir(cache, {recursive: true});
  const root = await fs.mkdtemp(path.join(cache, 'prepare-startup-controls-'));
  try {
    const {shuffleOwnershipBytes} = await import('../src/ownership-codec.js');
    const {packageStartupOwnership, packagePreparedStartupOwnership} = await import('../scripts/package-startup-ownership.mjs');
    const {packageNativeLatitudes} = await import('../scripts/package-native-latitudes.mjs');
    const {loadOwnershipAssets} = await import('../src/ownership-assets.js');
    const {loadNativeLatitudes} = await import('../src/native-latitudes.js');
    const reference = {id: 'geography:synthetic-startup-preparation', footprints_sha256: '3'.repeat(64), hierarchy_sha256: '4'.repeat(64)};
    const selected = JSON.parse(await fs.readFile('data/ownership-selection.json'));
    const native = JSON.parse(await fs.readFile(selected.manifest_path));
    const source = path.join(root, 'selected'), previous = path.join(root, 'previous');
    const rows = new Uint32Array(262166 * 2);
    rows[1] = 1;
    for (let y = 1; y < 262166; y++) rows[y * 2] = 1;
    const runs = Uint32Array.of(12, 2 ** 19 + 19), parts = [], originals = new Map();
    for (const [kind, words] of [['rows', rows], ['runs', runs]]) {
      const name = `native-v1/ownership/${kind}-0.bin.gz`, bytes = gzipSync(shuffleOwnershipBytes(words), {level: 9});
      await fs.mkdir(path.dirname(path.join(source, name)), {recursive: true});
      await fs.writeFile(path.join(source, name), bytes);
      originals.set(name, bytes);
      parts.push({kind, path: name, offset: 0, words: words.length, encoding: 'byte-shuffle', bytes: bytes.length,
        sha256: sha(bytes), decoded_bytes: words.byteLength, decoded_sha256: sha(Buffer.from(words.buffer))});
    }
    const manifest = {version: 2, coordinateBits: 19, size: 262166, runWords: runs.length, parts,
      method: native.method, native_latitudes: native.native_latitudes, geographic_release: reference.id,
      footprints_sha256: reference.footprints_sha256, hierarchy_sha256: reference.hierarchy_sha256};
    // A four-fragment exact encoded image exercises the production restoration helper.
    const transportRoot = path.join(root, 'assets-bank'), members = [], chunks = [];
    let offset = 0;
    for (const pin of [...parts].sort((a, b) => a.path.localeCompare(b.path))) {
      const body = originals.get(pin.path);
      members.push({path: pin.path, bytes: body.length, sha256: sha(body), offset, mode: '100644'});
      chunks.push(body); offset += body.length;
    }
    const whole = Buffer.concat(chunks), fragments = [];
    await fs.mkdir(transportRoot);
    for (let i = 0, start = 0; i < 4; i++) {
      const end = Math.floor(whole.length * (i + 1) / 4), raw = whole.subarray(start, end), bytes = gzipSync(raw);
      const name = `fragment-${i}.bin.gz`;
      await fs.writeFile(path.join(transportRoot, name), bytes);
      fragments.push({path: name, offset: start, bytes: bytes.length, sha256: sha(bytes), decoded_bytes: raw.length, decoded_sha256: sha(raw)});
      start = end;
    }
    const transport = Buffer.from(JSON.stringify({version: 1, issue: 1295, kind: 'ordered-exact-original-byte-fragments',
      files: members, parts: fragments, whole_bytes: whole.length, whole_sha256: sha(whole)}));
    await fs.writeFile(path.join(transportRoot, 'index.json'), transport);
    manifest.native_asset_transport = {version: 1, kind: 'ordered-exact-original-byte-fragments',
      index: {path: path.relative(process.cwd(), path.join(transportRoot, 'index.json')), bytes: transport.length, sha256: sha(transport)},
      logical_assets: parts.length, original_compressed_bytes: whole.length};
    const manifestPath = path.relative(process.cwd(), path.join(source, 'manifest.json'));
    const manifestBytes = Buffer.from(JSON.stringify(manifest));
    await fs.writeFile(manifestPath, manifestBytes);
    const old = await packageStartupOwnership({manifest, source, destination: previous});
    await fs.copyFile(path.join(source, parts[0].path), path.join(previous, parts[0].path));
    const latitude = await packageNativeLatitudes({manifest, expectedReference: reference, destination: previous});
    const oldRun = old.pixelMap.parts.find(part => part.kind === 'runs');
    const oldVintage = 'ownership-vintages/' + 'f'.repeat(64) + '/' + oldRun.path;
    await fs.mkdir(path.dirname(path.join(previous, oldVintage)), {recursive: true});
    await fs.copyFile(path.join(previous, oldRun.path), path.join(previous, oldVintage));
    // Deliberately distinct compatibility bytes must survive a current repack.
    await fs.writeFile(path.join(previous, oldRun.path), gzipSync(shuffleOwnershipBytes(Uint32Array.of(12, 2 ** 19 + 18)), {level: 9}));
    const previousRows = new Uint32Array(rows);
    previousRows[1] = 0; previousRows[2] = 0; previousRows[3] = 1;
    const previousRowBytes = gzipSync(shuffleOwnershipBytes(previousRows), {level: 9});
    await fs.writeFile(path.join(previous, parts[0].path), previousRowBytes);
    const previousRow = {...parts[0], bytes: previousRowBytes.length, sha256: sha(previousRowBytes),
      decoded_sha256: sha(Buffer.from(previousRows.buffer))};
    assert.notEqual(previousRow.sha256, parts[0].sha256);
    async function inventory(directory, relative = '') {
      const pins = [];
      for (const entry of await fs.readdir(path.join(directory, relative), {withFileTypes: true})) {
        const name = relative ? relative + '/' + entry.name : entry.name;
        if (entry.isDirectory()) pins.push(...await inventory(directory, name));
        else { const bytes = await fs.readFile(path.join(directory, name)); pins.push({path: name, bytes: bytes.length, sha256: sha(bytes)}); }
      }
      return pins.sort((a, b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0);
    }
    const oldFiles = await inventory(previous);
    await fs.writeFile(path.join(previous, 'index.json'), JSON.stringify({version: 1, native_manifest_sha256: 'f'.repeat(64),
      release_id: reference.id, footprints_sha256: reference.footprints_sha256, hierarchy_sha256: reference.hierarchy_sha256,
      pixelMap: {...old.pixelMap, native_latitudes: latitude.native_latitudes,
        parts: old.pixelMap.parts.map(part => part.kind === 'runs' ? {...part, path: oldVintage} : previousRow)}, files: oldFiles}));
    // Only synthetic selection/qualification lookup is mocked. Packers and restore are real.
    mock.module(pathToFileURL(path.resolve('scripts/select-build-ownership.mjs')).href, {namedExports: {
      readBuildOwnershipSelection: async () => ({manifestPath, expectedSha256: sha(manifestBytes), requireNative: true, releaseId: reference.id}),
      selectBuildOwnership: async options => {
        assert.deepEqual(options.expectedReference, reference);
        const raw = await fs.readFile(options.manifestPath);
        assert.equal(sha(raw), options.expectedSha256);
        return {manifest: JSON.parse(raw), sha256: sha(raw), manifestPath: options.manifestPath, source: path.dirname(options.manifestPath)};
      }
    }});
    mock.module(pathToFileURL(path.resolve('scripts/read-geographic-release-manifest.mjs')).href,
      {namedExports: {readGeographicReleaseManifest: () => ({releases: [reference]})}});
    const {prepareStartupOwnership} = await import(pathToFileURL(script).href);
    const output = path.join(root, 'prepared');
    const first = await prepareStartupOwnership({output, previous});
    for (const pin of oldFiles) assert.equal(sha(await fs.readFile(path.join(output, pin.path))), pin.sha256);
    const prefix = 'ownership-vintages/' + sha(manifestBytes) + '/';
    assert.equal(first.pixelMap.parts.find(part => part.kind === 'rows').path, prefix + parts[0].path);
    assert.equal(first.pixelMap.native_latitudes.transport_path, latitude.native_latitudes.transport_path);
    const consumer = path.join(root, 'consumer');
    const consumed = await packagePreparedStartupOwnership({manifest, manifestSha: sha(manifestBytes),
      source: output, destination: consumer});
    assert.deepEqual(consumed.pixelMap, first.pixelMap);
    const decoded = await loadOwnershipAssets(consumed.pixelMap, async url => new Response(await fs.readFile(path.join(consumer, url.slice(2)))),
      {requireNative: true, expectedReference: reference});
    assert.deepEqual(decoded.rows, rows); assert.deepEqual(decoded.runs, runs);
    const latitudes = await loadNativeLatitudes(consumed.pixelMap, reference,
      async url => new Response(await fs.readFile(path.join(consumer, url.slice(2)))));
    assert.equal(latitudes.length, rows.length / 2);
    for (const [name, bytes] of originals) assert.deepEqual(await fs.readFile(path.join(source, name)), bytes);
    await assert.rejects(prepareStartupOwnership({output, previous}), /fresh/);
    for (const part of parts) await fs.unlink(path.join(source, part.path));
    const restoredOutput = path.join(root, 'prepared-from-fragments');
    const second = await prepareStartupOwnership({output: restoredOutput, previous});
    assert.deepEqual(second, first);
    for (const part of parts) await absent(path.join(source, part.path));
    const conflicting = path.join(root, 'conflicting-rows');
    await fs.cp(output, conflicting, {recursive: true});
    const oldIndex = JSON.parse(await fs.readFile(path.join(conflicting, 'index.json')));
    const changedRows = new Uint32Array(rows);
    changedRows[1] = 0; changedRows[2] = 0; changedRows[3] = 1;
    const changedBytes = gzipSync(shuffleOwnershipBytes(changedRows), {level: 9});
    await fs.writeFile(path.join(conflicting, prefix + parts[0].path), changedBytes);
    Object.assign(oldIndex.files.find(pin => pin.path === prefix + parts[0].path), {bytes: changedBytes.length, sha256: sha(changedBytes)});
    Object.assign(oldIndex.pixelMap.parts.find(pin => pin.kind === 'rows'), {bytes: changedBytes.length,
      sha256: sha(changedBytes), decoded_sha256: sha(Buffer.from(changedRows.buffer))});
    await fs.writeFile(path.join(conflicting, 'index.json'), JSON.stringify(oldIndex));
    const rebound = path.join(root, 'rebound');
    await assert.rejects(prepareStartupOwnership({output: rebound, previous: conflicting}), /Immutable startup URL would be rebound/);
    await absent(rebound);
    const conflictingLatitude = path.join(root, 'conflicting-latitude');
    await fs.cp(previous, conflictingLatitude, {recursive: true});
    const latitudeIndex = JSON.parse(await fs.readFile(path.join(conflictingLatitude, 'index.json')));
    const latitudePath = latitude.native_latitudes.transport_path;
    const changedLatitude = gzipSync(gunzipSync(await fs.readFile(path.join(conflictingLatitude, latitudePath))), {level: 1});
    assert.notEqual(sha(changedLatitude), latitude.native_latitudes.sha256);
    await fs.writeFile(path.join(conflictingLatitude, latitudePath), changedLatitude);
    Object.assign(latitudeIndex.files.find(pin => pin.path === latitudePath), {bytes: changedLatitude.length, sha256: sha(changedLatitude)});
    Object.assign(latitudeIndex.pixelMap.native_latitudes, {bytes: changedLatitude.length, sha256: sha(changedLatitude)});
    await fs.writeFile(path.join(conflictingLatitude, 'index.json'), JSON.stringify(latitudeIndex));
    const reboundLatitude = path.join(root, 'rebound-latitude');
    await assert.rejects(prepareStartupOwnership({output: reboundLatitude, previous: conflictingLatitude}), /Immutable startup URL would be rebound/);
    await absent(reboundLatitude);
    const retainedFile = path.join(previous, oldRun.path), retainedBytes = await fs.readFile(retainedFile);
    await fs.writeFile(retainedFile, Buffer.from('corrupted previous URL'));
    const badPrevious = path.join(root, 'bad-previous');
    await assert.rejects(prepareStartupOwnership({output: badPrevious, previous}), /roster or bytes changed/);
    await absent(badPrevious);
    await fs.writeFile(retainedFile, retainedBytes);
    await fs.writeFile(path.join(transportRoot, fragments[0].path), Buffer.from('corrupted fragment'));
    const badTransport = path.join(root, 'bad-transport');
    await assert.rejects(prepareStartupOwnership({output: badTransport, previous}));
    await absent(badTransport);
    assert.equal((await fs.readdir(path.dirname(output))).some(name => name.startsWith('.prepare-startup-')), false);
    assert.deepEqual(await fs.readFile(manifestPath), manifestBytes);
  } finally { await fs.rm(root, {recursive: true, force: true}); }
}

if (process.env.WORLDATLAS_STARTUP_SYNTHETIC === '1') {
  await syntheticPreparation();
} else {
  const {prepareStartupOwnership, parseStartupArguments} = await import(pathToFileURL(script).href);
  test('preparation CLI requires a fresh output and a complete explicit native pair', async t => {
    const root = await fs.mkdtemp(path.join(os.tmpdir(), 'atlas-startup-admission-'));
    t.after(() => fs.rm(root, {recursive: true, force: true}));
    for (const args of [['--unknown', 'x'], ['--output'], ['--output', 'a', '--output', 'b']])
      assert.throws(() => parseStartupArguments(args), /Expected unique/);
    assert.deepEqual(parseStartupArguments(['--output', 'a', '--previous', 'b']), {output: 'a', previous: 'b'});
    for (const options of [{}, {output: root}, {output: root + '/../escape'},
      {output: path.join(root, 'missing'), manifest: 'manifest.json'}, {output: path.join(root, 'missing'), sha256: '0'.repeat(64)}])
      await assert.rejects(prepareStartupOwnership(options), /fresh|traversal|both/);
    await fs.symlink(path.join(root, 'absent'), path.join(root, 'dangling'));
    await assert.rejects(prepareStartupOwnership({output: path.join(root, 'dangling')}), /fresh/);
    await fs.symlink(root, path.join(root, 'linked'));
    await assert.rejects(prepareStartupOwnership({output: path.join(root, 'linked', 'new')}), /ordinary/);
    await absent(path.join(root, 'missing'));
  });
  test('synthetic preparation preserves every URL, restores exact fragments and rejects corruption', {timeout: 60000}, () => {
    const result = spawnSync(process.execPath, ['--experimental-test-module-mocks', fileURLToPath(import.meta.url)],
      {env: {...process.env, WORLDATLAS_STARTUP_SYNTHETIC: '1'}, encoding: 'utf8', timeout: 60000});
    assert.equal(result.status, 0, result.stdout + result.stderr);
  });
  test('real CLI rejects stale checksums and foreign baseline identity before creating output', async t => {
    const root = await fs.mkdtemp(path.join(os.tmpdir(), 'atlas-startup-selection-'));
    await fs.mkdir('.cache', {recursive: true});
    const inputs = await fs.mkdtemp(path.resolve('.cache/prepare-startup-selection-'));
    t.after(async () => { await fs.rm(root, {recursive: true, force: true}); await fs.rm(inputs, {recursive: true, force: true}); });
    const selection = JSON.parse(await fs.readFile('data/ownership-selection.json'));
    const output = path.join(root, 'output');
    const stale = spawnSync(process.execPath, [script, '--output', output, '--manifest', selection.manifest_path, '--sha256', '0'.repeat(64)], {encoding: 'utf8'});
    assert.equal(stale.status, 1, stale.stdout + stale.stderr);
    assert.match(stale.stderr, /manifest checksum mismatch/);
    await absent(output);
    const manifest = JSON.parse(await fs.readFile(selection.manifest_path));
    manifest.geographic_release = 'geography:review:foreign-baseline';
    const bytes = Buffer.from(JSON.stringify(manifest)), name = path.relative(process.cwd(), path.join(inputs, 'manifest.json'));
    await fs.writeFile(name, bytes);
    const foreign = spawnSync(process.execPath, [script, '--output', output, '--manifest', name, '--sha256', sha(bytes)], {encoding: 'utf8'});
    assert.equal(foreign.status, 1, foreign.stdout + foreign.stderr);
    assert.match(foreign.stderr, /selected reference release/);
    await absent(output);
  });
}
