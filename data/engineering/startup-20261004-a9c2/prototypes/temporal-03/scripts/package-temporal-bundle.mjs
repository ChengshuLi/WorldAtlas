import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';

const digest = bytes => createHash('sha256').update(bytes).digest('hex');
export async function packageTemporalBundle({entities, history, footprints, hierarchy, destination}) {
  if (!Array.isArray(entities) || !Array.isArray(history) ||
      ![footprints, hierarchy].every(value => /^[a-f0-9]{64}$/.test(value ?? ''))) throw Error('Invalid temporal bundle input');
  const raw = Buffer.from(JSON.stringify({version: 1, footprints_sha256: footprints, hierarchy_sha256: hierarchy, entities, history}));
  if (raw.length > 32 * 1024 * 1024) throw Error('Temporal bundle exceeds decoded byte limit');
  const bytes = gzipSync(raw, {level: 9});
  if (bytes.length > 8 * 1024 * 1024) throw Error('Temporal bundle exceeds compressed byte limit');
  await fs.mkdir(destination, {recursive: true});
  await fs.writeFile(path.join(destination, 'startup-temporal.json.gz'), bytes, {flag: 'wx'});
  return {version: 1, path: 'geography/startup-temporal.json.gz', footprints_sha256: footprints, hierarchy_sha256: hierarchy,
    entities: entities.length, history: history.length, bytes: bytes.length, sha256: digest(bytes),
    decoded_bytes: raw.length, decoded_sha256: digest(raw)};
}
