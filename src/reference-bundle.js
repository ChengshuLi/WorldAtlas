// Lossless reference transport; original records and dictionaries stay unchanged.
const MAX_COMPRESSED = 8 * 1024 * 1024;
const MAX_DECODED = 32 * 1024 * 1024;
const hash = value => /^[a-f0-9]{64}$/.test(value ?? '');
const digest = async bytes => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), byte => byte.toString(16).padStart(2, '0')).join('');

async function boundedBytes(stream, maximum) {
  const reader = stream.getReader(), chunks = [];
  let total = 0;
  try {
    for (;;) {
      const {done, value} = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > maximum) throw Error('Reference bundle exceeds byte limit');
      chunks.push(value);
    }
  } catch (error) { await reader.cancel().catch(() => {}); throw error; }
  const bytes = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  return bytes;
}

export async function loadReferenceBundle(proof, footprints, fetcher = fetch) {
  if (proof?.version !== 1 || proof.path !== 'reference-attributes/startup-bundle.json.gz' ||
      !hash(footprints) || proof.footprints_sha256 !== footprints ||
      ![proof.sha256, proof.decoded_sha256, proof.index_sha256].every(hash) ||
      !Number.isSafeInteger(proof.bytes) || proof.bytes < 1 || proof.bytes > MAX_COMPRESSED ||
      !Number.isSafeInteger(proof.decoded_bytes) || proof.decoded_bytes < 1 || proof.decoded_bytes > MAX_DECODED ||
      !Number.isSafeInteger(proof.part_count) || proof.part_count < 1 || proof.part_count > 256) {
    throw Error('Invalid reference bundle proof');
  }
  const response = await fetcher('./' + proof.path);
  if (!response.ok || !response.body) throw Error('Reference bundle unavailable');
  // Hosts may decode Content-Encoding:gzip before delivering the response.
  const bytes = await boundedBytes(response.body, MAX_DECODED);
  const compressed = bytes[0] === 31 && bytes[1] === 139;
  if (compressed && (bytes.length !== proof.bytes || await digest(bytes) !== proof.sha256)) throw Error('Reference bundle checksum mismatch');
  const raw = compressed ? await boundedBytes(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip')), proof.decoded_bytes) : bytes;
  if (raw.length !== proof.decoded_bytes || await digest(raw) !== proof.decoded_sha256) throw Error('Reference bundle decoded checksum mismatch');
  const bundle = JSON.parse(new TextDecoder().decode(raw));
  if (bundle.version !== 1 || bundle.index_sha256 !== proof.index_sha256 ||
      bundle.index?.footprints_sha256 !== footprints || ![1, 2].includes(bundle.index?.version) ||
      !Array.isArray(bundle.index.parts) || bundle.index.parts.length !== proof.part_count ||
      new Set(bundle.index.parts).size !== proof.part_count ||
      !Array.isArray(bundle.parts) || bundle.parts.length !== proof.part_count || !bundle.parts.every(Array.isArray)) {
    throw Error('Reference bundle roster mismatch');
  }
  return {index: bundle.index, parts: bundle.parts};
}
