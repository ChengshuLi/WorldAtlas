import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {shuffleOwnershipBytes} from '../../../src/ownership-codec.js';
import {admitPhase} from './phase-admission.mjs';
import {decodeInstalledWords} from './selected-native-inputs.mjs';
import {selectedDestination} from './selected-native-producer.mjs';
const sha = value => createHash('sha256').update(value).digest('hex');
const root = fs.mkdtempSync(path.join(fs.realpathSync(os.tmpdir()), 'selected-native-controls-'));
try {
  const words = Uint32Array.from([0, 3, 11, 27]);
  const raw = Buffer.alloc(words.length * 4);
  words.forEach((word, i) => raw.writeUInt32LE(word, i * 4));
  const encoded = gzipSync(shuffleOwnershipBytes(words), {mtime: 0});
  const file = path.join(root, 'words.gz'); fs.writeFileSync(file, encoded, {mode: 0o644});
  const pin = {path: file, bytes: encoded.length, sha256: sha(encoded), mode: 0o644,
    decoded_bytes: raw.length, decoded_sha256: sha(raw), words: words.length, encoding: 'byte-shuffle'};
  // Fixture runtime is an ordinary tiny file, explicitly no installed Node claim.
  const runtimeFile = path.join(root, 'fixture-runtime'); fs.writeFileSync(runtimeFile, 'x', {mode: 0o644});
  const runtime = {path: runtimeFile, bytes: 1, sha256: sha('x'), mode: 0o644};
  const admission = admitPhase({inputs: [pin], runtime, outputReserve: 0});
  assert.deepEqual(decodeInstalledWords(admission, pin), words);
  for (const changed of [{...pin, encoding: 'unknown'}, {...pin, words: 3},
    {...pin, decoded_sha256: '0'.repeat(64)}, {...pin, decoded_bytes: 8}])
    assert.throws(() => decodeInstalledWords(admission, changed));
  const sourceRoot = path.resolve(import.meta.dirname, '../../..');
  for (const destination of [sourceRoot + '/.cache/../../outside', root,
    path.join(sourceRoot, '.cache')]) assert.throws(() => selectedDestination(destination));
  console.log(JSON.stringify({positive: 1, negative: 7,
    actual_decoder_and_destination: true, fixture_runtime_only: true, native_grid_rows_computed: 0}));
} finally { fs.rmSync(root, {recursive: true}); }
