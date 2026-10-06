import {ownershipMetadata, LATITUDE_DIGEST} from './ownership-method.js';

const sha256 = async bytes => Array.from(new Uint8Array(
  await crypto.subtle.digest('SHA-256', bytes)), byte => byte.toString(16).padStart(2, '0')).join('');

async function boundedBytes(stream, limit) {
  if (!stream) throw Error('Native latitude response has no body');
  const reader = stream.getReader(), chunks = [];
  let length = 0;
  try {
    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      length += value.byteLength;
      if (length > limit) throw Error('Native latitude stream exceeds declared byte limit');
      chunks.push(value);
    }
  } catch (error) {
    await reader.cancel().catch(() => {});
    throw error;
  } finally { reader.releaseLock(); }
  const bytes = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
  return bytes;
}

// Transport addresses are separate from immutable repository provenance. Never
// regenerate the numerical rule using the receiving platform's Math functions.
export async function loadNativeLatitudes(manifest, expectedReference, fetcher = fetch, {signal} = {}) {
  const metadata = ownershipMetadata(manifest, {requireNative: true, expectedReference});
  const input = metadata.native_latitudes;
  if (input.transport_path !== 'native-v1/native-row-latitudes.f64le.gz')
    throw Error('Native latitude transport is missing or incompatible');
  signal?.throwIfAborted();
  const response = await fetcher('./' + input.transport_path, {signal});
  if (!response.ok) throw Error('Native latitude input could not load');
  const bytes = await boundedBytes(response.body, Math.max(input.bytes, input.decoded_bytes));
  const compressed = bytes[0] === 31 && bytes[1] === 139;
  if (compressed && (bytes.length !== input.bytes || await sha256(bytes) !== input.sha256))
    throw Error('Native latitude compressed checksum mismatch');
  const decoded = compressed ? await boundedBytes(new Blob([bytes]).stream()
    .pipeThrough(new DecompressionStream('gzip')), input.decoded_bytes) : bytes;
  if (decoded.length !== input.decoded_bytes || await sha256(decoded) !== LATITUDE_DIGEST)
    throw Error('Native latitude decoded checksum mismatch');
  signal?.throwIfAborted();
  const view = new DataView(decoded.buffer, decoded.byteOffset, decoded.byteLength);
  const latitudes = new Float64Array(metadata.size);
  for (let y = 0; y < latitudes.length; y++) {
    const latitude = view.getFloat64(y * 8, true);
    if (!Number.isFinite(latitude) || Math.abs(latitude) > 90 || y > 0 && latitude >= latitudes[y - 1])
      throw Error('Invalid native latitude table');
    latitudes[y] = latitude;
  }
  return latitudes;
}
