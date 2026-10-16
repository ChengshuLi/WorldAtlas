import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';

// Unplanned legacy callers keep their existing operating guard. Reviewed
// whole-file descriptors instead supply their own exact finite byte bounds.
export const LEGACY_FILE_BYTES = 32 * 1024 * 1024;
export function finiteBytes(value, label = 'byte bound') {
  if (!Number.isSafeInteger(value) || value < 0) throw Error('Invalid finite ' + label);
  return value;
}
export function addBytes(left, right, label = 'byte total') {
  finiteBytes(left, label); finiteBytes(right, label);
  return finiteBytes(left + right, label);
}
export function evidenceBytePlan(files) {
  let encodedBytes = 0, decodedBytes = 0, maxFileBytes = 0;
  const seen = new Set();
  for (const file of files) {
    const key = (file.commit ?? 'candidate') + ':' + file.path;
    if (seen.has(key)) throw Error('Duplicate file descriptor');
    seen.add(key);
    const encoded = finiteBytes(file.bytes, 'encoded descriptor');
    encodedBytes = addBytes(encodedBytes, encoded);
    maxFileBytes = Math.max(maxFileBytes, encoded);
    if (file.uncompressed_sha256 !== undefined || file.uncompressed_bytes !== undefined) {
      if (!/^[a-f0-9]{64}$/.test(file.uncompressed_sha256 ?? '')) throw Error('Invalid uncompressed descriptor');
      const decoded = finiteBytes(file.uncompressed_bytes, 'decoded descriptor');
      decodedBytes = addBytes(decodedBytes, decoded);
      maxFileBytes = Math.max(maxFileBytes, decoded);
    }
  }
  return {encodedBytes, decodedBytes, maxFileBytes, totalBytes: addBytes(encodedBytes, decodedBytes)};
}
export function decodeEvidenceGzip(raw, file, {maxFileBytes} = {}) {
  if (maxFileBytes !== undefined) finiteBytes(maxFileBytes, 'caller file budget');
  const declared = file?.uncompressed_bytes;
  const bound = declared === undefined ? maxFileBytes ?? LEGACY_FILE_BYTES : finiteBytes(declared, 'decoded descriptor');
  if (maxFileBytes !== undefined && bound > maxFileBytes) throw Error('Uncompressed file exceeds budget');
  const unpacked = gunzipSync(raw, {maxOutputLength: Math.max(1, bound)});
  if (declared !== undefined && unpacked.length !== declared) throw Error('Uncompressed bytes mismatch');
  if (file?.uncompressed_sha256 !== undefined && createHash('sha256').update(unpacked).digest('hex') !== file.uncompressed_sha256)
    throw Error('Uncompressed bytes mismatch');
  return unpacked;
}
export function immutableResponseBytes(bytes) {
  finiteBytes(bytes, 'immutable blob size');
  // Account for base64, escaped line breaks and the ordinary REST envelope.
  return addBytes(finiteBytes(8 * Math.ceil(bytes / 3), 'base64 response size'), 64 * 1024);
}
