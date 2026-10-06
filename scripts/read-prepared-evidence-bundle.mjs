import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {validatePreparedEvidenceIndex, verifyPreparedEvidencePart} from '../src/prepared-evidence.js';

const digest = bytes => createHash('sha256').update(bytes).digest('hex');
// Grid-only builds retain completed evidence bytes. This checks their complete
// declared transport rather than regenerating them with another gzip runtime.
export async function readPreparedEvidenceBundle(directory = 'data/prepared-evidence') {
  const index = JSON.parse(await fs.readFile(directory + '/index.json'));
  validatePreparedEvidenceIndex(index);
  for (const part of index.parts) {
    const bytes = await fs.readFile(directory + '/' + part.path);
    if (digest(bytes) !== part.sha256 || bytes.length !== part.bytes)
      throw Error('Retained prepared evidence bytes changed: ' + part.path);
    await verifyPreparedEvidencePart(part, JSON.parse(gunzipSync(bytes)));
  }
  if (index.imports?.path !== 'imports/index.json') throw Error('Retained import manifest missing');
  const bytes = await fs.readFile(directory + '/' + index.imports.path);
  if (digest(bytes) !== index.imports.sha256) throw Error('Retained import manifest changed');
  const imports = JSON.parse(bytes);
  if (!Array.isArray(imports.batches) || imports.batches.length !== index.imports.batches)
    throw Error('Retained import batch inventory changed');
  for (const batch of imports.batches) {
    if (!/^batch-\d+\.json$/.test(batch.path)) throw Error('Unsafe retained import path');
    if (digest(await fs.readFile(directory + '/imports/' + batch.path)) !== batch.sha256)
      throw Error('Retained import batch changed: ' + batch.path);
  }
  return index;
}
