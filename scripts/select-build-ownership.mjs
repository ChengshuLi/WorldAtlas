import fs from 'node:fs/promises';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {ownershipMetadata, NATIVE_METHOD} from '../src/ownership-method.js';

const digest = bytes => createHash('sha256').update(bytes).digest('hex');

// A native build is an explicit offline selection of a reviewed whole-file
// candidate. The legacy default and all original release products remain intact.
export async function selectBuildOwnership({manifestPath = 'data/canonical-grid/manifest.json',
  expectedSha256, expectedReference, requireNative = false} = {}) {
  const bytes = await fs.readFile(manifestPath);
  const manifest = JSON.parse(bytes), sha256 = digest(bytes);
  const native = manifest.method === NATIVE_METHOD;
  if (requireNative && !native) throw Error('Explicit native build cannot select legacy ownership');
  if (expectedSha256 && sha256 !== expectedSha256) throw Error('Selected grid manifest checksum mismatch');
  if (native && !/^[a-f0-9]{64}$/.test(expectedSha256 ?? ''))
    throw Error('Explicit native build requires the reviewed manifest checksum');
  const metadata = ownershipMetadata(manifest, native ? {requireNative: true, expectedReference} : {});
  if (!native && expectedReference && (manifest.footprints_sha256 !== expectedReference.footprints_sha256 ||
    manifest.hierarchy_sha256 !== expectedReference.hierarchy_sha256))
    throw Error('Legacy grid differs from selected source reference');
  let bounds;
  if (native) {
    const pin = manifest.original_assets?.bounds;
    if (!pin || pin.role !== 'original-identity-parent-camera-context' ||
      !/^[a-f0-9]{40}$/.test(pin.commit ?? '') || pin.path !== 'data/canonical-grid/bounds.json.gz' ||
      pin.sha256 !== manifest.bounds?.sha256)
      throw Error('Native grid requires immutable original bounds context');
    bounds = execFileSync('git', ['show', `${pin.commit}:${pin.path}`], {maxBuffer: 32 * 1024 * 1024});
  } else {
    if (manifest.bounds?.path !== 'bounds.json.gz') throw Error('Unsupported original bounds path');
    bounds = await fs.readFile(path.join(path.dirname(manifestPath), manifest.bounds.path));
  }
  if (digest(bounds) !== manifest.bounds.sha256) throw Error('Selected grid bounds checksum mismatch');
  return {manifest, metadata, manifestPath, source: path.dirname(manifestPath), sha256, bounds};
}
