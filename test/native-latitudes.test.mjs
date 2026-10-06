import test, {after} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {gunzipSync} from 'node:zlib';
import {fileURLToPath} from 'node:url';
import {packageNativeLatitudes} from '../scripts/package-native-latitudes.mjs';
import {loadNativeLatitudes} from '../src/native-latitudes.js';
import {NATIVE_METHOD} from '../src/ownership-method.js';

const scratch = fileURLToPath(new URL('../.cache/native-latitude-controls/', import.meta.url));
await fs.mkdir(scratch, {recursive: true});
const root = await fs.mkdtemp(path.join(scratch, 'run-'));
after(() => fs.rm(root, {recursive: true}));
const reference = {id: 'geography:synthetic-table-transport', footprints_sha256: '3'.repeat(64), hierarchy_sha256: '4'.repeat(64)};
const input = {
  root: 'repository', role: 'immutable-normative-rule-input',
  path: 'coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz',
  commit: '35d2d3ff48957d34ee8d4329824b268ecadc6d3c',
  bytes: 1851757, sha256: 'ab0becdda100da3473d7bb5d34ccda6510aa1c0490c407082072c7201ad1e147',
  decoded_bytes: 2097328, decoded_sha256: '66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23'
};
const manifest = {version: 2, coordinateBits: 19, size: 262166, runWords: 0, parts: [],
  method: NATIVE_METHOD, native_latitudes: input, geographic_release: reference.id,
  footprints_sha256: reference.footprints_sha256, hierarchy_sha256: reference.hierarchy_sha256};

test('exact pinned latitude table survives packaging and both compressed and host-decoded transport', async () => {
  const packaged = await packageNativeLatitudes({manifest, expectedReference: reference, destination: path.join(root, 'positive')});
  assert.deepEqual(packaged.native_latitudes, {...input, transport_path: 'native-v1/native-row-latitudes.f64le.gz'});
  const encoded = await fs.readFile(path.join(root, 'positive', packaged.native_latitudes.transport_path));
  const decoded = gunzipSync(encoded), view = new DataView(decoded.buffer, decoded.byteOffset, decoded.byteLength);
  for (const bytes of [encoded, decoded]) {
    const table = await loadNativeLatitudes({...manifest, native_latitudes: packaged.native_latitudes}, reference,
      async url => {assert.equal(url, './native-v1/native-row-latitudes.f64le.gz'); return new Response(bytes);});
    assert.equal(table.length, manifest.size);
    // Check every Float64 row against the immutable little-endian input.
    for (let y = 0; y < table.length; y++) assert.equal(table[y], view.getFloat64(y * 8, true));
  }
});

test('rule transport rejects missing paths, mixed release, corruption, truncation, oversized bodies and cancellation', async () => {
  let fetched = false;
  const fetcher = async () => {fetched = true; return new Response(new Uint8Array(1));};
  await assert.rejects(loadNativeLatitudes(manifest, reference, fetcher), /transport/);
  assert.equal(fetched, false);
  const selected = {...manifest, native_latitudes: {...input, transport_path: 'native-v1/native-row-latitudes.f64le.gz'}};
  await assert.rejects(loadNativeLatitudes(selected, {...reference, id: 'geography:different'}, fetcher), /reference release/);
  assert.equal(fetched, false);
  const encoded = await fs.readFile(path.join(root, 'positive', selected.native_latitudes.transport_path));
  const damaged = Buffer.from(encoded); damaged[damaged.length - 8] ^= 1;
  for (const bytes of [damaged, encoded.subarray(0, encoded.length - 1), new Uint8Array(input.decoded_bytes + 1)])
    await assert.rejects(loadNativeLatitudes(selected, reference, async () => new Response(bytes)), /checksum|byte limit/);
  const decoded = gunzipSync(encoded); decoded[10] ^= 1;
  await assert.rejects(loadNativeLatitudes(selected, reference, async () => new Response(decoded)), /decoded checksum/);
  const controller = new AbortController(); controller.abort();
  await assert.rejects(loadNativeLatitudes(selected, reference, fetcher, {signal: controller.signal}), {name: 'AbortError'});
});

test('packager rejects altered pinned input metadata without creating output', async () => {
  const destination = path.join(root, 'negative');
  await assert.rejects(packageNativeLatitudes({manifest: {...manifest, native_latitudes: {...input, sha256: '0'.repeat(64)}},
    expectedReference: reference, destination}), /input changed/);
  await assert.rejects(fs.access(destination));
});
