// Privileged merge jobs inspect bounded bytes in memory, never extract archives.
import {inflateRawSync, crc32} from 'node:zlib';
import {createHash} from 'node:crypto';
import {githubAPI, githubPages} from './issue-claim-contract.mjs';
import {successfulGeographyJob, WORKFLOW_PATH} from './integration-proof.mjs';

const MAX_REPORT = 32 * 1024 * 1024;
const MAX_ARCHIVE = 40 * 1024 * 1024;
const MAX_LOG = 2 * 1024 * 1024;
const need = (ok, message) => { if (!ok) throw Error(message); };
export const reportHash = raw => createHash('sha256').update(raw).digest('hex');
const positive = n => Number.isSafeInteger(n) && n > 0;
const hash = value => /^[a-f0-9]{64}$/.test(value ?? '');
const commit = value => /^[a-f0-9]{40}$/.test(value ?? '');

// These are trusted prepare outputs, not a caller-selected replacement report.
// Final validation still rechecks the original run/attempt/job, whole tree and
// artifact. Keep the original report candidate instead of relabeling its JSON.
export function validateGeographyProof(value) {
  const keys = ['run_id','run_attempt','job_id','tree','head','baseline','artifact_id',
    'artifact_name','artifact_digest','artifact_bytes','report_sha256','report_bytes'];
  const carried = value && (Object.hasOwn(value, 'current_run_attempt') || Object.hasOwn(value, 'current_job_id'));
  if (carried) keys.push('current_run_attempt', 'current_job_id');
  need(value && typeof value === 'object' && !Array.isArray(value) &&
    Object.keys(value).sort().join() === [...keys].sort().join() &&
    ['run_id','run_attempt','job_id','artifact_id','artifact_bytes','report_bytes'].every(key => positive(value[key])) &&
    ['tree','head','baseline'].every(key => commit(value[key])) &&
    hash(value.report_sha256) && hash(value.artifact_digest) && value.report_bytes <= MAX_REPORT &&
    value.artifact_bytes <= MAX_ARCHIVE && /^proposed-geography-[1-9]\d*-[1-9]\d*$/.test(value.artifact_name),
    'Invalid original geographic proof identity');
  need(!carried || (positive(value.current_run_attempt) && positive(value.current_job_id) &&
    value.run_attempt < value.current_run_attempt),
    'Invalid carried geographic proof identity');
  need(Number(value.artifact_name.split('-').at(-1)) === value.run_attempt,
    'Original geographic artifact attempt differs from its producer');
  return value;
}

export function readGeographyJobReceipt(raw, expected) {
  const discover = expected && typeof expected === 'object';
  const artifactName = discover ? null : expected;
  need(Buffer.isBuffer(raw) && raw.length > 0 && raw.length <= MAX_LOG &&
    (discover ? positive(expected.number) && positive(expected.runAttempt) :
      /^proposed-geography-[1-9]\d*-[1-9]\d*$/.test(artifactName ?? '')), 'Invalid bounded geography job log');
  const lines = raw.toString('utf8').split(/\r?\n/).map(line => line.replace(/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d+Z /, ''));
  const receipts = [];
  for (const line of lines) {
    if (!line.startsWith('{')) continue;
    let value; try { value = JSON.parse(line); } catch { continue; }
    if (Object.hasOwn(value, 'report_sha256') || Object.hasOwn(value, 'report_bytes')) receipts.push(value);
  }
  const uploadLines = lines.filter(line => line.startsWith('Artifact proposed-geography-') && line.includes('has been successfully uploaded!'));
  const uploads = uploadLines.map(line => /^Artifact (proposed-geography-([1-9]\d*)-([1-9]\d*)) has been successfully uploaded! Final size is ([1-9]\d*) bytes\. Artifact ID is ([1-9]\d*)$/.exec(line)).filter(Boolean);
  const digests = lines.map(line => /^SHA256 digest of uploaded artifact zip is ([a-f0-9]{64})$/.exec(line)).filter(Boolean);
  need(receipts.length === 1 && uploads.length === 1 && uploadLines.length === 1 && digests.length === 1 &&
    (discover ? Number(uploads[0][2]) === expected.number && positive(Number(uploads[0][3])) &&
      Number(uploads[0][3]) <= expected.runAttempt : uploads[0][1] === artifactName) &&
    hash(receipts[0].report_sha256) && positive(receipts[0].report_bytes) && receipts[0].report_bytes <= MAX_REPORT,
    'Missing, ambiguous or malformed original geographic job receipt');
  const result = {artifact_name: uploads[0][1], artifact_id: Number(uploads[0][5]),
    artifact_bytes: Number(uploads[0][4]), artifact_digest: digests[0][1],
    report_sha256: receipts[0].report_sha256, report_bytes: receipts[0].report_bytes};
  need(positive(result.artifact_id) && positive(result.artifact_bytes) && result.artifact_bytes <= MAX_ARCHIVE,
    'Invalid original geographic artifact receipt');
  return result;
}

export function readReportArchive(raw, expectedHash, expectedBytes) {
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
  need(report.length === size && (expectedBytes === undefined || report.length === expectedBytes) &&
    crc32(report) === crc && reportHash(report) === expectedHash,
    'Report archive bytes differ from trusted geography job digest');
  return JSON.parse(report.toString('utf8'));
}

async function boundedBody(response, maximum = MAX_ARCHIVE) {
  need(response.ok && response.body, 'Geographic report download failed');
  const declared = response.headers.get('content-length');
  need(declared === null || (/^\d+$/.test(declared) && Number(declared) <= maximum),
    'Geographic report download exceeds archive budget');
  const chunks = []; let size = 0;
  for await (const chunk of response.body) {
    size += chunk.length;
    if (size > maximum) { throw Error('Geographic report download exceeds archive budget'); }
    chunks.push(Buffer.from(chunk));
  }
  return Buffer.concat(chunks, size);
}

async function downloadRedirect(response, fetchImpl, maximum = MAX_ARCHIVE) {
  need(response.status === 302, 'Geographic artifact API did not return a download');
  let destination;
  try { destination = new URL(response.headers.get('location')); } catch { throw Error('Invalid geographic artifact delivery address'); }
  need(destination.protocol === 'https:' && !destination.username && !destination.password &&
    destination.hostname.endsWith('.blob.core.windows.net'), 'Unsupported geographic artifact delivery host');
  try {
    const delivery = await fetchImpl(destination.href, {redirect: 'error', signal: AbortSignal.timeout(30000)});
    return await boundedBody(delivery, maximum);
  } catch { throw Error('Geographic report delivery failed or exceeded bounded archive budget'); }
}

// Only the originating attempt named by an already authenticated job receipt is
// inspected. A failed/cancelled code attempt can contain successful geography; its
// actual unique geography job and all required steps must still be successful.
async function readGeographyOriginJob({api, repo, number, source}) {
  const route = `/repos/${repo}/actions/runs/${source.run_id}/attempts/${source.run_attempt}`;
  const run = await api(route);
  need(run.id === source.run_id && run.run_attempt === source.run_attempt && run.head_sha === source.head &&
    run.event === 'pull_request' && run.path === WORKFLOW_PATH && run.repository?.full_name === repo &&
    run.head_repository?.full_name === repo && run.status === 'completed' &&
    Array.isArray(run.pull_requests) && (!run.pull_requests.length ||
      run.pull_requests.some(pr => pr.number === number && pr.head?.sha === source.head)),
    'Original geographic run identity or state changed');
  // The current code proof already authenticates this run's PR. GitHub can
  // omit historical PR links, and an aggregate cancellation says nothing about
  // the completed geographic job. Authenticate that exact producer below.
  const jobs = await githubPages(async path => (await api(path)).jobs, `${route}/jobs`);
  const job = successfulGeographyJob(jobs);
  need(job && job.run_id === source.run_id &&
    job.run_attempt === source.run_attempt && job.head_sha === source.head,
    'Original geographic job identity or successful steps changed');
  return job;
}

export async function validateGeographyOrigin(options) {
  const {source} = options;
  validateGeographyProof(source);
  if (!source.current_run_attempt) return;
  const job = await readGeographyOriginJob(options);
  need(job.id === source.job_id, 'Original geographic job identity changed');
}

export async function prepareGeographyProof({api, repo, number, head, baseline, proof, token, fetchImpl = fetch}) {
  if (!proof?.geography_job_id) return null;
  need(/^[-\w.]+\/[-\w.]+$/.test(repo ?? '') && positive(number) && positive(proof.geography_job_id) &&
    positive(proof.run_id) && positive(proof.run_attempt) && commit(proof.tree) && commit(head) && commit(baseline),
    'Invalid original geography proof source');
  const client = typeof api.jobLogRedirect === 'function' ? api : githubAPI(token, {fetchImpl});
  const response = await client.jobLogRedirect(`/repos/${repo}/actions/jobs/${proof.geography_job_id}/logs`);
  const receipt = readGeographyJobReceipt(await downloadRedirect(response, fetchImpl, MAX_LOG),
    {number, runAttempt: proof.run_attempt});
  const originAttempt = Number(receipt.artifact_name.split('-').at(-1));
  let jobId = proof.geography_job_id;
  if (originAttempt !== proof.run_attempt) {
    jobId = (await readGeographyOriginJob({api, repo, number, source: {run_id: proof.run_id,
      run_attempt: originAttempt, head}})).id;
  }
  const source = validateGeographyProof({run_id: proof.run_id, run_attempt: originAttempt,
    job_id: jobId, tree: proof.tree, head, baseline, ...receipt,
    ...(originAttempt !== proof.run_attempt ? {current_run_attempt: proof.run_attempt, current_job_id: proof.geography_job_id} : {})});
  if (source.current_run_attempt) {
    const originalResponse = await client.jobLogRedirect(`/repos/${repo}/actions/jobs/${source.job_id}/logs`);
    const original = readGeographyJobReceipt(await downloadRedirect(originalResponse, fetchImpl, MAX_LOG), source.artifact_name);
    need(JSON.stringify(original) === JSON.stringify(receipt), 'Carried geographic receipt differs from its originating job');
  }
  const report = await loadGeographicReport({api, repo, runId: source.run_id, artifactName: source.artifact_name,
    expectedHash: source.report_sha256, source, token, fetchImpl});
  return {source, report};
}

export async function loadGeographicReport({api, repo, runId, artifactName, expectedHash, source, token, fetchImpl = fetch, onRequest = () => {}}) {
  if (source) {
    validateGeographyProof(source);
    need(Number(runId) === source.run_id && artifactName === source.artifact_name && expectedHash === source.report_sha256,
      'Original geographic artifact outputs changed');
  }
  need(/^[-\w.]+\/[-\w.]+$/.test(repo ?? '') && /^[1-9]\d*$/.test(String(runId)) &&
    (source || /^geography-[-a-zA-Z0-9]{16,100}-[1-9]\d*$/.test(artifactName ?? '')) &&
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
  if (source) need(matches[0].id === source.artifact_id && matches[0].size_in_bytes === source.artifact_bytes &&
    matches[0].digest === `sha256:${source.artifact_digest}` && matches[0].workflow_run?.id === source.run_id &&
    matches[0].workflow_run?.head_sha === source.head, 'Original geographic artifact identity changed');
  // The initial fixed API host receives the token. Redirect delivery receives
  // no credentials, and its signed URL is never included in errors or logs.
  const client = typeof api.artifactRedirect === 'function' ? api : githubAPI(token, {fetchImpl, onRequest});
  const response = await client.artifactRedirect(`/repos/${repo}/actions/artifacts/${matches[0].id}/zip`);
  const bytes = await downloadRedirect(response, fetchImpl);
  if (source) need(bytes.length === source.artifact_bytes && reportHash(bytes) === source.artifact_digest,
    'Original geographic archive differs from trusted upload receipt');
  return readReportArchive(bytes, expectedHash, source?.report_bytes);
}
