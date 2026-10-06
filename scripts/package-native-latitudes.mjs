import fs from 'node:fs/promises';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {ownershipMetadata} from '../src/ownership-method.js';

const digest = bytes => createHash('sha256').update(bytes).digest('hex');

// Resolve the exact reviewed Git input, not a mutable working-tree substitute.
// Preserve its provenance and attach a separate deployment transport address.
export async function packageNativeLatitudes({manifest, expectedReference, destination}) {
  const metadata = ownershipMetadata(manifest, {requireNative: true, expectedReference});
  const input = metadata.native_latitudes;
  const bytes = execFileSync('git', ['show', `${input.commit}:${input.path}`],
    {maxBuffer: 32 * 1024 * 1024});
  if (bytes.length !== input.bytes || digest(bytes) !== input.sha256)
    throw Error('Pinned native latitude input changed');
  const decoded = gunzipSync(bytes, {maxOutputLength: input.decoded_bytes});
  if (decoded.length !== input.decoded_bytes || digest(decoded) !== input.decoded_sha256)
    throw Error('Pinned native latitude decoded bytes changed');
  const transport_path = 'native-v1/native-row-latitudes.f64le.gz';
  await fs.mkdir(path.join(destination, 'native-v1'), {recursive: true});
  await fs.writeFile(path.join(destination, transport_path), bytes, {flag: 'wx'});
  return {native_latitudes: {...input, transport_path}, receipt: {
    source: `${input.commit}:${input.path}`, path: transport_path,
    bytes: bytes.length, sha256: digest(bytes), decoded_bytes: decoded.length,
    decoded_sha256: digest(decoded), scope: 'Exact immutable numerical rule transport; no geographic source approval'
  }};
}
