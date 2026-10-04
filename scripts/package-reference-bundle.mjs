import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gzipSync, gunzipSync} from 'node:zlib';

const MAX_DECODED = 32 * 1024 * 1024;
const digest = bytes => createHash('sha256').update(bytes).digest('hex');

export async function packageReferenceBundle({source, destination, expectedFootprints}) {
  const indexBytes = await fs.readFile(path.join(source, 'index.json'));
  if (indexBytes.length > MAX_DECODED) throw Error('Reference index exceeds byte limit');
  const index = JSON.parse(indexBytes);
  if (![1, 2].includes(index.version) || !/^[a-f0-9]{64}$/.test(expectedFootprints ?? '') ||
      index.footprints_sha256 !== expectedFootprints || !Array.isArray(index.parts) ||
      index.parts.length < 1 || index.parts.length > 256 || new Set(index.parts).size !== index.parts.length ||
      index.parts.some(name => !/^[a-zA-Z0-9_-]+\.json(?:\.gz)?$/.test(name))) throw Error('Invalid reference input roster');
  const sources = [{path: 'index.json', bytes: indexBytes.length, sha256: digest(indexBytes)}], parts = [];
  let decodedBytes = indexBytes.length;
  for (const name of index.parts) {
    const bytes = await fs.readFile(path.join(source, name));
    if (bytes.length > 8 * 1024 * 1024) throw Error('Reference part exceeds byte limit');
    const raw = bytes[0] === 31 && bytes[1] === 139 ? gunzipSync(bytes, {maxOutputLength: MAX_DECODED}) : bytes;
    decodedBytes += raw.length;
    if (decodedBytes > MAX_DECODED) throw Error('Reference input total exceeds byte limit');
    const rows = JSON.parse(raw);
    if (!Array.isArray(rows)) throw Error('Reference part must contain rows');
    parts.push(rows); sources.push({path: name, bytes: bytes.length, sha256: digest(bytes)});
  }
  const raw = Buffer.from(JSON.stringify({version: 1, index_sha256: digest(indexBytes), index, parts}));
  if (raw.length > MAX_DECODED) throw Error('Reference bundle exceeds decoded byte limit');
  const bytes = gzipSync(raw, {level: 9});
  if (bytes.length > 8 * 1024 * 1024) throw Error('Reference bundle exceeds compressed byte limit');
  await fs.mkdir(destination, {recursive: true});
  await fs.writeFile(path.join(destination, 'startup-bundle.json.gz'), bytes, {flag: 'wx'});
  return {descriptor: {version: 1, path: 'reference-attributes/startup-bundle.json.gz',
    sha256: digest(bytes), bytes: bytes.length, decoded_sha256: digest(raw), decoded_bytes: raw.length,
    index_sha256: digest(indexBytes), footprints_sha256: expectedFootprints, part_count: parts.length}, sources};
}
