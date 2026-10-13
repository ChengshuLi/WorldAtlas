// Privileged merge jobs inspect bounded bytes in memory, never extract archives.
import {inflateRawSync, gunzipSync, crc32} from 'node:zlib';
import {createHash} from 'node:crypto';
import {githubAPI, githubPages} from './issue-claim-contract.mjs';
import {successfulGeographyJob, WORKFLOW_PATH, QUEUE_WORKFLOW_PATH} from './integration-proof.mjs';

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
  const extended = value && ['workflow_path', 'event', 'workflow_head', 'candidate_commit'].some(key => Object.hasOwn(value, key));
  if (extended) keys.push('workflow_path', 'event', 'workflow_head', 'candidate_commit');
  const queue = extended && value.workflow_path === QUEUE_WORKFLOW_PATH;
  const carried = value && (Object.hasOwn(value, 'current_run_attempt') || Object.hasOwn(value, 'current_job_id'));
  if (carried) keys.push('current_run_attempt', 'current_job_id');
  need(value && typeof value === 'object' && !Array.isArray(value) &&
    Object.keys(value).sort().join() === [...keys].sort().join() &&
    ['run_id','run_attempt','job_id','artifact_id','artifact_bytes','report_bytes'].every(key => positive(value[key])) &&
    ['tree','head','baseline'].every(key => commit(value[key])) &&
    hash(value.report_sha256) && hash(value.artifact_digest) && value.report_bytes <= MAX_REPORT &&
    value.artifact_bytes <= MAX_ARCHIVE && (queue ? /^geography-[-a-zA-Z0-9]{16,100}-[1-9]\d*$/ :
      /^proposed-geography-[1-9]\d*-[1-9]\d*$/).test(value.artifact_name),
    'Invalid original geographic proof identity');
  need(!extended || commit(value.workflow_head) && commit(value.candidate_commit) &&
    (queue ? value.event === 'workflow_dispatch' : value.workflow_path === WORKFLOW_PATH &&
      value.event === 'pull_request' && value.workflow_head === value.head), 'Invalid geographic workflow family');
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
      (/^(?:proposed-geography-[1-9]\d*|geography-[-a-zA-Z0-9]{16,100})-[1-9]\d*$/).test(artifactName ?? '')), 'Invalid bounded geography job log');
  const lines = raw.toString('utf8').split(/\r?\n/).map(line => line.replace(/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d+Z /, ''));
  const receipts = [];
  for (const line of lines) {
    if (!line.startsWith('{')) continue;
    let value; try { value = JSON.parse(line); } catch { continue; }
    if (Object.hasOwn(value, 'report_sha256') || Object.hasOwn(value, 'report_bytes')) receipts.push(value);
  }
  const uploadLines = lines.filter(line => /^Artifact (?:proposed-geography-|geography-)/.test(line) && line.includes('has been successfully uploaded!'));
  const uploads = uploadLines.map(line => /^Artifact ((?:proposed-geography-([1-9]\d*)|geography-[-a-zA-Z0-9]{16,100})-([1-9]\d*)) has been successfully uploaded! Final size is ([1-9]\d*) bytes\. Artifact ID is ([1-9]\d*)$/.exec(line)).filter(Boolean);
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
  if (Object.hasOwn(receipts[0], 'candidate_commit')) {
    need(commit(receipts[0].candidate_commit), 'Invalid geographic candidate receipt');
    result.candidate_commit = receipts[0].candidate_commit;
  }
  return result;
}

export const CHECKPOINT_MEMBERS = Object.freeze([
  'derived-certificate.json.gz', 'derived-facts.json', 'derived-publication.json',
  'facts.json', 'operands.json.gz', 'publication.json', 'checkpoint-routes.json'
]);
const MEMBER_NAMES = new Set(['geography-check.json', ...CHECKPOINT_MEMBERS, 'operating.json']);
const MAX_PHASE = 256 * 1024 * 1024;
const reportProducts = new WeakMap();
const exactKeys = (value, keys) => value && typeof value === 'object' && !Array.isArray(value) &&
  Object.keys(value).sort().join() === [...keys].sort().join();

// This accessor returns data, never accepted-checkpoint authority. Qualification
// must separately authenticate the bot acceptance and independently merged PR.
export function geographicReportProducts(report) { return reportProducts.get(report) ?? null; }

function extraFields(raw, start, size) {
  const end = start + size;
  need(end <= raw.length, 'Truncated report archive extra field');
  while (start < end) {
    need(start + 4 <= end, 'Malformed report archive extra field');
    const id = raw.readUInt16LE(start), bytes = raw.readUInt16LE(start + 2);
    need(id !== 1 && start + 4 + bytes <= end, 'ZIP64 or malformed report archive extra field');
    start += 4 + bytes;
  }
}

// The complete small fixed roster is admitted before decoding. Nothing is
// extracted, and physical records must exactly tile the local-file area.
function archiveDirectory(raw) {
  need(Buffer.isBuffer(raw) && raw.length >= 22 && raw.length <= MAX_ARCHIVE, 'Invalid report archive');
  const end = raw.length - 22;
  const count = raw.readUInt16LE(end + 10);
  need(raw.readUInt32LE(end) === 0x06054b50 && raw.readUInt16LE(end + 20) === 0 &&
    raw.readUInt16LE(end + 4) === 0 && raw.readUInt16LE(end + 6) === 0 &&
    count >= 1 && count <= MEMBER_NAMES.size && raw.readUInt16LE(end + 8) === count,
    'Require bounded ordinary report archive entries');
  const centralSize = raw.readUInt32LE(end + 12), central = raw.readUInt32LE(end + 16);
  need(central >= 30 && central + centralSize === end, 'Invalid report archive directory');
  const entries = new Map(); let cursor = central;
  for (let index = 0; index < count; index++) {
    need(cursor + 46 <= end && raw.readUInt32LE(cursor) === 0x02014b50, 'Invalid report archive directory');
    const flags = raw.readUInt16LE(cursor + 8), method = raw.readUInt16LE(cursor + 10);
    const crc = raw.readUInt32LE(cursor + 16), packed = raw.readUInt32LE(cursor + 20);
    const size = raw.readUInt32LE(cursor + 24), nameLength = raw.readUInt16LE(cursor + 28);
    const extraLength = raw.readUInt16LE(cursor + 30), commentLength = raw.readUInt16LE(cursor + 32);
    const attributes = raw.readUInt32LE(cursor + 38), offset = raw.readUInt32LE(cursor + 42);
    need(raw.readUInt16LE(cursor + 6) <= 20 && (flags & ~0x808) === 0 && [0, 8].includes(method) &&
      size > 0 && size <= MAX_REPORT && packed > 0 && packed <= MAX_ARCHIVE && offset + 30 <= central &&
      raw.readUInt16LE(cursor + 34) === 0 && [0, 0x8000].includes((attributes >>> 16) & 0xf000) && !(attributes & 0x10) &&
      cursor + 46 + nameLength + extraLength + commentLength <= end,
      'Unsupported, unsafe or oversized report archive entry');
    const nameBytes = raw.subarray(cursor + 46, cursor + 46 + nameLength), name = nameBytes.toString('utf8');
    need(MEMBER_NAMES.has(name) && nameBytes.equals(Buffer.from(name)) && !entries.has(name), 'Unknown or duplicate report archive member');
    extraFields(raw, cursor + 46 + nameLength, extraLength);
    need(raw.readUInt32LE(offset) === 0x04034b50 && raw.readUInt16LE(offset + 4) === raw.readUInt16LE(cursor + 6) &&
      raw.readUInt16LE(offset + 6) === flags && raw.readUInt16LE(offset + 8) === method &&
      raw.readUInt32LE(offset + 10) === raw.readUInt32LE(cursor + 12), 'Report archive local entry differs from directory');
    const localNameLength = raw.readUInt16LE(offset + 26), localExtraLength = raw.readUInt16LE(offset + 28);
    const start = offset + 30 + localNameLength + localExtraLength;
    need(localNameLength === nameBytes.length && raw.subarray(offset + 30, offset + 30 + localNameLength).equals(nameBytes) &&
      start + packed <= central, 'Truncated report archive entry');
    extraFields(raw, offset + 30 + localNameLength, localExtraLength);
    for (const [field, expected] of [[14, crc], [18, packed], [22, size]]) {
      const local = raw.readUInt32LE(offset + field);
      need(local === expected || (flags & 8) && local === 0, 'Report archive local sizes differ');
    }
    entries.set(name, {name, flags, method, crc, packed, size, offset, start});
    cursor += 46 + nameLength + extraLength + commentLength;
  }
  need(cursor === end && entries.has('geography-check.json'), 'Incomplete report archive directory');
  const physical = [...entries.values()].sort((a, b) => a.offset - b.offset);
  need(physical[0].offset === 0, 'Report archive has unlisted local records');
  for (let index = 0; index < physical.length; index++) {
    const row = physical[index], next = physical[index + 1]?.offset ?? central, finish = row.start + row.packed;
    if (!(row.flags & 8)) need(finish === next, 'Overlapping or unlisted report archive records');
    else {
      const length = next - finish;
      need([12, 16].includes(length), 'Invalid report archive data descriptor');
      const descriptor = finish + (length === 16 ? 4 : 0);
      need((length !== 16 || raw.readUInt32LE(finish) === 0x08074b50) &&
        raw.readUInt32LE(descriptor) === row.crc && raw.readUInt32LE(descriptor + 4) === row.packed &&
        raw.readUInt32LE(descriptor + 8) === row.size, 'Report archive data descriptor differs');
    }
  }
  return entries;
}

function decodeMember(raw, row) {
  const packed = raw.subarray(row.start, row.start + row.packed);
  const inflated = row.method === 8 ? inflateRawSync(packed, {maxOutputLength: row.size, info: true}) : null;
  need(!inflated || inflated.engine.bytesWritten === packed.length, 'Report archive compressed member has trailing data');
  const body = inflated ? inflated.buffer : packed;
  need(body.length === row.size && crc32(body) === row.crc, 'Report archive bytes differ from trusted geography job digest');
  return body;
}

export function readReportArchive(raw, expectedHash, expectedBytes, {admit = () => {}} = {}) {
  need(hash(expectedHash) && (expectedBytes === undefined || positive(expectedBytes) && expectedBytes <= MAX_REPORT),
    'Invalid report archive or trusted report digest');
  const entries = archiveDirectory(raw), root = entries.get('geography-check.json');
  // Include transport, decoded report, UTF-16 parsing and conservative live JSON
  // room in the same phase. Each remaining member is admitted before allocation.
  let admitted = 2 * raw.length + 8 * root.size;
  // Preserve the legacy single-report 32 MiB contract. The tighter complete
  // product phase applies only to checkpoint bundles; caller admission still
  // observes the real root representation charge before any decoding.
  need(entries.size === 1 || admitted <= MAX_PHASE, 'Geographic checkpoint combined budget exceeded');
  admit(admitted);
  const reportBytes = decodeMember(raw, root);
  need((expectedBytes === undefined || reportBytes.length === expectedBytes) && reportHash(reportBytes) === expectedHash,
    'Report archive bytes differ from trusted geography job digest');
  const report = JSON.parse(reportBytes.toString('utf8'));
  need(report && typeof report === 'object' && !Array.isArray(report), 'Invalid geographic report object');
  const descriptor = report.checkpoint;
  if (descriptor === undefined) {
    need(entries.size === 1, 'Legacy report archive contains unlisted members');
    reportProducts.set(report, {report_bytes: reportBytes, members: new Map(), admitted_bytes: admitted});
    return report;
  }
  need(exactKeys(descriptor, ['version', 'kind', 'members']) && descriptor.version === 1 &&
    descriptor.kind === 'selected-checkpoint-products-v1' && Array.isArray(descriptor.members), 'Invalid checkpoint product descriptor');
  const names = descriptor.members.map(row => row?.name);
  need(names.length >= CHECKPOINT_MEMBERS.length && names.length <= CHECKPOINT_MEMBERS.length + 1 &&
    new Set(names).size === names.length && CHECKPOINT_MEMBERS.every(name => names.includes(name)) &&
    names.every(name => CHECKPOINT_MEMBERS.includes(name) || name === 'operating.json') &&
    entries.size === names.length + 1 && names.every(name => entries.has(name)), 'Checkpoint archive roster differs from authenticated report');
  for (const row of descriptor.members) {
    const gzip = row.name.endsWith('.gz');
    need(exactKeys(row, ['name', 'bytes', 'sha256', ...(gzip ? ['decoded_bytes', 'decoded_sha256'] : [])]) &&
      positive(row.bytes) && row.bytes <= MAX_REPORT && row.bytes === entries.get(row.name).size && hash(row.sha256) &&
      (!gzip || positive(row.decoded_bytes) && row.decoded_bytes <= MAX_REPORT && hash(row.decoded_sha256)),
      'Invalid checkpoint member bounds or digest');
    admitted += row.bytes + 8 * (gzip ? row.decoded_bytes : row.bytes);
  }
  need(admitted <= MAX_PHASE, 'Geographic checkpoint combined budget exceeded');
  admit(admitted);
  const members = new Map();
  for (const row of descriptor.members) {
    const body = decodeMember(raw, entries.get(row.name));
    need(reportHash(body) === row.sha256, 'Checkpoint member differs from authenticated report');
    if (row.name.endsWith('.gz')) {
      const decoded = gunzipSync(body, {maxOutputLength: row.decoded_bytes});
      need(decoded.length === row.decoded_bytes && reportHash(decoded) === row.decoded_sha256,
        'Checkpoint decoded member differs from authenticated report');
    }
    members.set(row.name, body);
  }
  reportProducts.set(report, {report_bytes: reportBytes, members, admitted_bytes: admitted});
  return report;
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
  const queue = source.workflow_path === QUEUE_WORKFLOW_PATH;
  const workflowHead = source.workflow_head ?? source.head;
  need(run.id === source.run_id && run.run_attempt === source.run_attempt && run.head_sha === workflowHead &&
    run.event === (queue ? 'workflow_dispatch' : 'pull_request') && run.path === (queue ? QUEUE_WORKFLOW_PATH : WORKFLOW_PATH) &&
    run.repository?.full_name === repo && run.head_repository?.full_name === repo &&
    (queue ? ['in_progress', 'completed'].includes(run.status) : run.status === 'completed') &&
    (queue || Array.isArray(run.pull_requests) && (!run.pull_requests.length ||
      run.pull_requests.some(pr => pr.number === number && pr.head?.sha === source.head))),
    'Original geographic run identity or state changed');
  // The current code proof already authenticates this run's PR. GitHub can
  // omit historical PR links, and an aggregate cancellation says nothing about
  // the completed geographic job. Authenticate that exact producer below.
  const jobs = await githubPages(async path => (await api(path)).jobs, `${route}/jobs`);
  const job = successfulGeographyJob(jobs, queue ? QUEUE_WORKFLOW_PATH : WORKFLOW_PATH);
  need(job && job.run_id === source.run_id &&
    job.run_attempt === source.run_attempt && job.head_sha === workflowHead,
    'Original geographic job identity or successful steps changed');
  return job;
}

// New PR producers test a merge commit while code CI still tests reviewed head.
// The retained source tree is the actual geographic candidate tree; reuse is
// allowed only when the receiving proof independently establishes that tree.
export async function validatePRGeographyCandidate({api, repo, source}) {
  if (source.workflow_path !== WORKFLOW_PATH || !source.candidate_commit || source.candidate_commit === source.head) return;
  const candidate = await api(`/repos/${repo}/git/commits/${source.candidate_commit}`);
  need(candidate.sha === source.candidate_commit && candidate.tree?.sha === source.tree &&
    candidate.parents?.length === 2 && candidate.parents[0].sha === source.baseline &&
    candidate.parents[1].sha === source.head, 'Original geographic candidate parents or tree differ');
}

export async function validateGeographyOrigin(options) {
  const {source} = options;
  validateGeographyProof(source);
  if (!source.current_run_attempt && !source.workflow_path) return;
  const job = await readGeographyOriginJob(options);
  need(job.id === source.job_id, 'Original geographic job identity changed');
  await validatePRGeographyCandidate(options);
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
    job_id: jobId, tree: proof.tree, head, baseline, workflow_path: WORKFLOW_PATH,
    event: 'pull_request', workflow_head: head, candidate_commit: head, ...receipt,
    ...(originAttempt !== proof.run_attempt ? {current_run_attempt: proof.run_attempt, current_job_id: proof.geography_job_id} : {})});
  await validatePRGeographyCandidate({api, repo, source});
  if (source.current_run_attempt) {
    const originalResponse = await client.jobLogRedirect(`/repos/${repo}/actions/jobs/${source.job_id}/logs`);
    const original = readGeographyJobReceipt(await downloadRedirect(originalResponse, fetchImpl, MAX_LOG), source.artifact_name);
    need(JSON.stringify(original) === JSON.stringify(receipt), 'Carried geographic receipt differs from its originating job');
  }
  const report = await loadGeographicReport({api, repo, runId: source.run_id, artifactName: source.artifact_name,
    expectedHash: source.report_sha256, source, token, fetchImpl});
  if (receipt.candidate_commit) checkGeographicReport(report, baseline, source.candidate_commit);
  return {source, report};
}

export async function loadGeographicReport({api, repo, runId, artifactName, expectedHash, source, fresh, retainedArchive, admit = () => {}, token, fetchImpl = fetch, onRequest = () => {}}) {
  if (fresh) {
    const originAttempt = Number(artifactName?.split('-').at(-1));
    need(!source && positive(Number(runId)) && positive(fresh.run_attempt) &&
      [fresh.head, fresh.baseline, fresh.candidate_commit, fresh.workflow_head].every(commit) &&
      /^[-a-zA-Z0-9]{16,100}$/.test(fresh.request_id ?? '') &&
      positive(originAttempt) && originAttempt <= fresh.run_attempt &&
      artifactName === `geography-${fresh.request_id}-${originAttempt}`, 'Invalid fresh queue geography identity');
    const identity = {run_id: Number(runId), run_attempt: originAttempt, head: fresh.head,
      baseline: fresh.baseline, candidate_commit: fresh.candidate_commit,
      workflow_path: QUEUE_WORKFLOW_PATH, event: 'workflow_dispatch', workflow_head: fresh.workflow_head};
    const job = await readGeographyOriginJob({api, repo, source: identity});
    const client = typeof api.jobLogRedirect === 'function' ? api : githubAPI(token, {fetchImpl, onRequest});
    const response = await client.jobLogRedirect(`/repos/${repo}/actions/jobs/${job.id}/logs`);
    const receipt = readGeographyJobReceipt(await downloadRedirect(response, fetchImpl, MAX_LOG), artifactName);
    need(receipt.report_sha256 === expectedHash, 'Fresh geographic job report differs from trusted output');
    const candidate = await api(`/repos/${repo}/git/commits/${fresh.candidate_commit}`);
    need(candidate.sha === fresh.candidate_commit && commit(candidate.tree?.sha), 'Fresh geographic candidate tree unavailable');
    source = validateGeographyProof({...identity, tree: candidate.tree.sha, job_id: job.id, ...receipt});
  }
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
  need(matches.length <= 1, 'Duplicate geographic artifact');
  if (source && matches.length) need(matches[0].id === source.artifact_id && matches[0].size_in_bytes === source.artifact_bytes &&
    matches[0].digest === `sha256:${source.artifact_digest}` && matches[0].workflow_run?.id === source.run_id &&
    matches[0].workflow_run?.head_sha === (source.workflow_head ?? source.head), 'Original geographic artifact identity changed');
  const unavailable = !matches.length || matches[0].expired;
  if (unavailable) {
    if (!source || typeof retainedArchive !== 'function') {
      const error = Error('Missing or expired geographic artifact; no exact retained copy supplied');
      error.geographyUnavailable = true; throw error;
    }
    // A retained location is only a hint. The accepted original digest remains
    // authority, including when Actions has deleted the original after expiry.
    need(source.artifact_bytes <= MAX_REPORT, 'Retained geographic archive exceeds ordinary file limit');
    admit(2 * source.artifact_bytes);
    const bytes = await retainedArchive(source.artifact_bytes);
    need(Buffer.isBuffer(bytes) && bytes.length === source.artifact_bytes && reportHash(bytes) === source.artifact_digest,
      'Retained geographic archive differs from accepted artifact digest');
    const report = readReportArchive(bytes, expectedHash, source.report_bytes, {admit});
    reportProducts.set(report, {...reportProducts.get(report), source, archive_bytes: bytes, archive_origin: 'retained-exact'});
    return report;
  }
  need(Number.isSafeInteger(matches[0].id) && matches[0].id > 0 &&
    positive(matches[0].size_in_bytes) && matches[0].size_in_bytes <= MAX_ARCHIVE,
    'Missing, duplicate, expired or oversized geographic artifact');

  // The initial fixed API host receives the token. Redirect delivery receives
  // no credentials, and its signed URL is never included in errors or logs.
  const client = typeof api.artifactRedirect === 'function' ? api : githubAPI(token, {fetchImpl, onRequest});
  const response = await client.artifactRedirect(`/repos/${repo}/actions/artifacts/${matches[0].id}/zip`);
  admit(2 * matches[0].size_in_bytes);
  const bytes = await downloadRedirect(response, fetchImpl, matches[0].size_in_bytes);
  if (source) need(bytes.length === source.artifact_bytes && reportHash(bytes) === source.artifact_digest,
    'Original geographic archive differs from trusted upload receipt');
  const report = readReportArchive(bytes, expectedHash, source?.report_bytes, {admit});
  reportProducts.set(report, {...reportProducts.get(report), source: source ?? null, archive_bytes: bytes, archive_origin: 'actions'});
  return report;
}

export function checkGeographicReport(geography, baseline, candidate, codeCommit = baseline) {
  need(codeCommit === baseline || codeCommit === candidate, 'Unsupported geographic checker code commit');
  need(geography?.version === 1 && geography.method_id === 'worldatlas-trusted-geography-check-v1' &&
    geography.baseline_commit === baseline && geography.trusted_code_commit === codeCommit &&
    geography.candidate_commit === candidate && geography.candidate_code_executed === (codeCommit !== baseline) &&
    geography.published === false && geography.source_approval === false && geography.gate_status === 'passed',
    'Geographic report does not bind exact trusted combined check');
  if (codeCommit !== baseline) need(!geography.checkpoint && !geography.reused_baseline_proof && !geography.unchanged_selected_inputs &&
    /^[a-f0-9]{64}$/.test(geography.trusted_code_inventory_sha256 ?? ''),
    'Software geography must bind actual execution inventory without baseline/checkpoint reuse');
  const ordinaryPass = ['not-applicable', 'no-footprint-change', 'no-new-regression'].includes(geography.status);
  const waterPass = geography.status === 'regressions-found' &&
    geography.adjudication?.status === 'all-findings-supported-and-reviewed' &&
    geography.adjudication.unresolved_findings === 0;
  need(ordinaryPass || waterPass, 'Combined geographic findings remain unresolved');
  return waterPass;
}
