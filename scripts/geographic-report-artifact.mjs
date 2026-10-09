// Privileged merge jobs inspect bounded bytes in memory, never extract archives.
import {inflateRawSync, crc32} from 'node:zlib';
import {createHash} from 'node:crypto';
import {githubAPI} from './issue-claim-contract.mjs';

const MAX_REPORT = 32 * 1024 * 1024;
const MAX_ARCHIVE = 40 * 1024 * 1024;
const need = (ok, message) => { if (!ok) throw Error(message); };
export const reportHash = raw => createHash('sha256').update(raw).digest('hex');

export function readReportArchive(raw, expectedHash) {
  need(Buffer.isBuffer(raw) && raw.length >= 22 && raw.length <= MAX_ARCHIVE &&
    /^[a-f0-9]{64}$/.test(expectedHash ?? ''), 'Invalid report archive or trusted report digest');
  // EOCD must terminate the archive. ZIP64, multiple entries/disks and comments
  // are unnecessary for this single small ordinary JSON artifact.
  const end = raw.length - 22;
  need(raw.readUInt32LE(end) === 0x06054b50 && raw.readUInt16LE(end + 20) === 0 &&
    raw.readUInt16LE(end + 4) === 0 && raw.readUInt16LE(end + 6) === 0 &&
    raw.readUInt16LE(end + 8) === 1 && raw.readUInt16LE(end + 10) === 1,
    'Require one ordinary report archive entry');
  const centralSize = raw.readUInt32LE(end + 12), central = raw.readUInt32LE(end + 16);
  need(central >= 30 && central + centralSize === end && centralSize >= 46 &&
    raw.readUInt32LE(central) === 0x02014b50, 'Invalid report archive directory');
  const flags = raw.readUInt16LE(central + 8), method = raw.readUInt16LE(central + 10);
  const crc = raw.readUInt32LE(central + 16), packed = raw.readUInt32LE(central + 20);
  const size = raw.readUInt32LE(central + 24), nameLength = raw.readUInt16LE(central + 28);
  const extraLength = raw.readUInt16LE(central + 30), commentLength = raw.readUInt16LE(central + 32);
  const attributes = raw.readUInt32LE(central + 38), offset = raw.readUInt32LE(central + 42);
  need((flags & ~0x808) === 0 && [0, 8].includes(method) && size > 0 && size <= MAX_REPORT &&
    packed <= MAX_ARCHIVE && offset === 0 && raw.readUInt16LE(central + 34) === 0 &&
    [0, 0x8000].includes((attributes >>> 16) & 0xf000) && !(attributes & 0x10) &&
    46 + nameLength + extraLength + commentLength === centralSize,
    'Unsupported, unsafe or oversized report archive entry');
  const name = raw.subarray(central + 46, central + 46 + nameLength);
  need(name.equals(Buffer.from('geography-check.json')) && raw.readUInt32LE(0) === 0x04034b50 &&
    raw.readUInt16LE(6) === flags && raw.readUInt16LE(8) === method,
    'Report archive local entry differs from directory');
  const localNameLength = raw.readUInt16LE(26), localExtraLength = raw.readUInt16LE(28);
  const start = 30 + localNameLength + localExtraLength;
  need(localNameLength === name.length && raw.subarray(30, 30 + localNameLength).equals(name) &&
    start + packed <= central, 'Truncated report archive entry');
  if (!(flags & 8)) need(start + packed === central && raw.readUInt32LE(14) === crc &&
    raw.readUInt32LE(18) === packed && raw.readUInt32LE(22) === size, 'Report archive local sizes differ');
  else {
    const descriptorSize = central - start - packed;
    need([12, 16].includes(descriptorSize), 'Invalid report archive data descriptor');
    const descriptor = start + packed + (descriptorSize === 16 ? 4 : 0);
    need((descriptorSize !== 16 || raw.readUInt32LE(start + packed) === 0x08074b50) &&
      raw.readUInt32LE(descriptor) === crc && raw.readUInt32LE(descriptor + 4) === packed &&
      raw.readUInt32LE(descriptor + 8) === size, 'Report archive data descriptor differs');
  }
  const compressed = raw.subarray(start, start + packed);
  const report = method === 0 ? compressed : inflateRawSync(compressed, {maxOutputLength: MAX_REPORT});
  need(report.length === size && crc32(report) === crc && reportHash(report) === expectedHash,
    'Report archive bytes differ from trusted geography job digest');
  return JSON.parse(report.toString('utf8'));
}

async function boundedBody(response) {
  need(response.ok && response.body, 'Geographic report download failed');
  const declared = response.headers.get('content-length');
  need(declared === null || (/^\d+$/.test(declared) && Number(declared) <= MAX_ARCHIVE),
    'Geographic report download exceeds archive budget');
  const chunks = []; let size = 0;
  for await (const chunk of response.body) {
    size += chunk.length;
    if (size > MAX_ARCHIVE) { await response.body.cancel().catch(() => {}); throw Error('Geographic report download exceeds archive budget'); }
    chunks.push(Buffer.from(chunk));
  }
  return Buffer.concat(chunks, size);
}

export async function loadGeographicReport({api, repo, runId, artifactName, expectedHash, token, fetchImpl = fetch, onRequest = () => {}}) {
  need(/^[-\w.]+\/[-\w.]+$/.test(repo ?? '') && /^[1-9]\d*$/.test(String(runId)) &&
    /^geography-[-a-zA-Z0-9]{16,100}-[1-9]\d*$/.test(artifactName ?? '') &&
    /^[a-f0-9]{64}$/.test(expectedHash ?? '') && token, 'Missing trusted geographic artifact outputs');
  const matches = []; let total = 0;
  for (let page = 1; page <= 100; page++) {
    const result = await api(`/repos/${repo}/actions/runs/${runId}/artifacts?per_page=100&page=${page}`);
    need(Array.isArray(result.artifacts) && Number.isSafeInteger(result.total_count) && result.total_count <= 10000,
      'Incomplete geographic artifact inventory');
    total += result.artifacts.length;
    matches.push(...result.artifacts.filter(row => row.name === artifactName));
    if (total === result.total_count) break;
    need(result.artifacts.length === 100 && page < 100 && total < result.total_count,
      'Incomplete geographic artifact inventory');
  }
  need(matches.length === 1 && !matches[0].expired && Number.isSafeInteger(matches[0].id) &&
    matches[0].id > 0 && matches[0].size_in_bytes > 0 && matches[0].size_in_bytes <= MAX_ARCHIVE,
    'Missing, duplicate, expired or oversized geographic artifact');
  // The initial fixed API host receives the token. Redirect delivery receives
  // no credentials, and its signed URL is never included in errors or logs.
  const client = typeof api.artifactRedirect === 'function' ? api : githubAPI(token, {fetchImpl, onRequest});
  const response = await client.artifactRedirect(`/repos/${repo}/actions/artifacts/${matches[0].id}/zip`);
  need(response.status === 302, 'Geographic artifact API did not return a download');
  let destination;
  try { destination = new URL(response.headers.get('location')); } catch { throw Error('Invalid geographic artifact delivery address'); }
  need(destination.protocol === 'https:' && !destination.username && !destination.password &&
    destination.hostname.endsWith('.blob.core.windows.net'), 'Unsupported geographic artifact delivery host');
  let bytes;
  try {
    const delivery = await fetchImpl(destination.href, {redirect: 'error', signal: AbortSignal.timeout(30000)});
    bytes = await boundedBody(delivery);
  } catch { throw Error('Geographic report delivery failed or exceeded bounded archive budget'); }
  return readReportArchive(bytes, expectedHash);
}
