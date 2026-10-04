// Re-encode existing GPU words; never compile, coarsen or change the canonical grid.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {loadOwnershipAssets} from '../src/ownership-assets.js';
import {shuffleOwnershipBytes, unshuffleOwnershipBytes} from '../src/ownership-codec.js';

const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const validHash = value => /^[a-f0-9]{64}$/.test(value ?? '');
const WORDS_PER_PART = 4194304; // At most16MiB of decoded GPU words per new part.

export async function packageStartupOwnership({manifest, source, destination}) {
  if (manifest.version !== 2 || !Array.isArray(manifest.parts) ||
      manifest.parts.some(part => !/^ownership\/(?:rows|runs)-[0-9]+\.bin\.gz$/.test(part.path) ||
        !validHash(part.sha256) || !validHash(part.decoded_sha256)) ||
      new Set(manifest.parts.map(part => part.path)).size !== manifest.parts.length) throw Error('Invalid canonical ownership input');
  const inputs = [], byPath = new Map(manifest.parts.map(part => ['./' + part.path, part]));
  const original = await loadOwnershipAssets(manifest, async url => {
    const part = byPath.get(url);
    if (!part) throw Error('Ownership input outside declared roster');
    const bytes = await fs.readFile(path.join(source, part.path));
    if (bytes.length > 32 * 1024 * 1024 || digest(bytes) !== part.sha256) throw Error('Canonical ownership input changed');
    inputs.push({path: part.path, bytes: bytes.length, sha256: digest(bytes), decoded_sha256: part.decoded_sha256});
    return new Response(bytes);
  });
  const parts = manifest.parts.filter(part => part.kind === 'rows'), receipts = [];
  await fs.mkdir(path.join(destination, 'ownership'), {recursive: true});
  for (let offset = 0; offset < original.runs.length; offset += WORDS_PER_PART) {
    const words = original.runs.subarray(offset, Math.min(offset + WORDS_PER_PART, original.runs.length));
    const encoded = shuffleOwnershipBytes(words);
    if (encoded.length > 32 * 1024 * 1024) throw Error('Ownership transport exceeds decoded byte limit');
    const decoded = unshuffleOwnershipBytes(encoded, words.length);
    const originalBytes = Buffer.from(words.buffer, words.byteOffset, words.byteLength);
    const decodedBytes = Buffer.from(decoded.buffer, decoded.byteOffset, decoded.byteLength);
    if (!originalBytes.equals(decodedBytes)) throw Error('Ownership transport changed canonical GPU words');
    const bytes = gzipSync(encoded, {level: 9});
    if (bytes.length > 8 * 1024 * 1024) throw Error('Ownership transport exceeds compressed byte limit');
    const relative = `ownership/startup-runs-${offset}.bin.gz`;
    await fs.writeFile(path.join(destination, relative), bytes, {flag: 'wx'});
    parts.push({kind: 'runs', path: relative, offset, words: words.length, encoding: 'byte-shuffle',
      sha256: digest(bytes), decoded_sha256: digest(decodedBytes)});
    receipts.push({path: relative, bytes: bytes.length, sha256: digest(bytes),
      uncompressed_bytes: encoded.length, uncompressed_sha256: digest(encoded),
      decoded_gpu_word_bytes: decodedBytes.length, decoded_gpu_word_sha256: digest(decodedBytes),
      original_gpu_word_sha256: digest(originalBytes), outcome: 'passed'});
  }
  const pixelMap = Object.fromEntries(['version', 'coordinateBits', 'size', 'runWords'].map(key => [key, manifest[key]]));
  pixelMap.parts = parts;
  return {pixelMap, inputs: inputs.sort((a, b) => a.path.localeCompare(b.path)), outputs: receipts,
    rows_sha256: digest(Buffer.from(original.rows.buffer)), runs_word_stream_sha256: digest(Buffer.from(original.runs.buffer)),
    scope: 'Every decoded canonical GPU word preserved; stream digests are not containing-file hashes or geographic approval'};
}
