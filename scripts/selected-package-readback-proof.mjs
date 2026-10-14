// Observational rollout proof only. A native readback never authorizes reuse of
// original output, scientific consumption, or omission of current consumers.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {getHeapStatistics} from 'node:v8';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';

const need = (ok, message) => { if (!ok) throw Error(message); };
const positive = value => Number.isSafeInteger(value) && value > 0;
const commit = value => typeof value === 'string' && /^[a-f0-9]{40}$/.test(value);
const digest = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const hash = raw => createHash('sha256').update(raw).digest('hex');
const object = value => value && typeof value === 'object' && !Array.isArray(value);
const safe = value => typeof value === 'string' && value.length > 0 && !/[\\\x00-\x1f\x7f]/.test(value) &&
  !value.startsWith('/') && value.split('/').every(part => part && part !== '.' && part !== '..');
const queueWorkflow = '.github/workflows/worker-merge.yml';
const authorWorkflow = '.github/workflows/merge-integration-checks.yml';
const reportName = 'native-normal-built-output.json';
// This established job-log metadata admission is independent of output size.
// The observed full integration log is 533 KiB; retain the original 8 MiB cap.
const maxLog = 8 * 1048576;
const queueSteps = [
  'Build the combined application once before asset-dependent tests',
  'Read back qualified native build outputs when selected',
  'Test applicable combined-tree invariants without publishing or live imports',
  'Retain native built-output readback'
];
const authorSteps = [
  'Verify full-regression package controls',
  'Build hosted assets',
  'Read back qualified native build outputs when selected',
  'Complete regression shard',
  'Verify full-regression package receipt',
  'Retain native built-output readback',
  'Retain full-regression package receipt'
];
const authorReceipt = 'Actual reviewed-head Cloudflare package and applicable native readback receipts verified.';

async function producerFor(run, repo, expectedHead, expectedPullRequest, api) {
  if (run.event === 'workflow_dispatch' && run.path === queueWorkflow && run.head_branch === 'main')
    return {workflow: queueWorkflow, job: 'integration (0)', steps: queueSteps, smoke: true};
  need(run.event === 'pull_request' && run.path === authorWorkflow,
    'Native author readback requires the pull_request full-regression workflow');
  need(Array.isArray(run.pull_requests) && run.pull_requests.length <= 1,
    'Native author readback requires zero or one unambiguous run PR link');
  need(expectedPullRequest === undefined || positive(expectedPullRequest),
    'Native author readback expected PR must be an exact positive number');
  const repositoryURL = `https://api.github.com/repos/${repo}`;
  let pr = run.pull_requests[0], linkage = {kind: 'run-pull-requests'};
  if (run.pull_requests.length === 0) {
    // GitHub can clear this mutable association after merge. The caller must
    // supply an independently selected PR; never search by branch or guess it
    // from an artifact. The actual run, successful job, receipts and complete
    // report below must still bind this exact source independently.
    need(positive(expectedPullRequest),
      'Native author readback has no run PR link; explicit expectedPullRequest required');
    pr = await api(`/repos/${repo}/pulls/${expectedPullRequest}`);
    need(pr?.number === expectedPullRequest && pr.merged === true && pr.state === 'closed' &&
      commit(pr.merge_commit_sha) && pr.head?.repo?.full_name === repo && pr.base?.repo?.full_name === repo,
      'Native author readback fallback requires the exact accepted same-repository PR');
    linkage = {kind: 'accepted-pull-request-lookup', merge_commit: pr.merge_commit_sha};
  }
  need(object(pr), 'Native author readback requires an ordinary PR identity');
  need(expectedPullRequest === undefined || pr.number === expectedPullRequest,
    'Native author run PR link contradicts the explicit expected PR');
  need(positive(pr?.number) && pr.url === `${repositoryURL}/pulls/${pr.number}` &&
    pr.head?.sha === expectedHead && typeof pr.head.ref === 'string' && pr.head.ref.length > 0 &&
    run.head_branch === pr.head.ref && pr.head.repo?.url === repositoryURL &&
    pr.base?.ref === 'main' && commit(pr.base.sha) && pr.base.repo?.url === repositoryURL,
    'Native author readback lacks exact reviewed pull-request linkage');
  // GitHub may run the workflow on a synthetic PR merge. The actual checked-out
  // reviewed head is independently bound by PR metadata, artifact name, the
  // full-receipt verification step/log, and the decoded native report.
  return {workflow: authorWorkflow, job: 'regression (0)', steps: authorSteps, smoke: false,
    pullRequest: pr.number, linkage, artifactName: `native-built-output-regression-${pr.number}-${expectedHead}`};
}

async function delivery(redirect, fetchImpl, maximum, destination) {
  need(redirect?.status === 302, 'Native readback delivery redirect unavailable');
  let url;
  try { url = new URL(redirect.headers.get('location')); } catch { throw Error('Invalid native readback delivery'); }
  need(url.protocol === 'https:' && !url.username && !url.password && !url.port &&
    url.hostname.endsWith('.blob.core.windows.net'), 'Unsupported native readback delivery');
  const response = await fetchImpl(url, {redirect: 'error', signal: AbortSignal.timeout(120000)});
  need(response.ok && response.body, 'Native readback delivery failed');
  const fd = destination ? fs.openSync(destination, 'wx', 0o600) : null;
  const chunks = [], checksum = createHash('sha256'); let bytes = 0;
  try {
    for await (const chunk of response.body) {
      bytes += chunk.length;
      need(bytes <= maximum, 'Native readback delivery exceeds admitted bytes');
      checksum.update(chunk);
      if (fd === null) chunks.push(Buffer.from(chunk));
      else { let offset = 0; while (offset < chunk.length) offset += fs.writeSync(fd, chunk, offset, chunk.length - offset); }
    }
  } finally { if (fd !== null) fs.closeSync(fd); }
  return {bytes, sha256: checksum.digest('hex'), raw: fd === null ? Buffer.concat(chunks, bytes) : null};
}

function receipts(raw) {
  const lines = raw.toString('utf8').split(/\r?\n/).map(line => line.replace(/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d+Z /, ''));
  const reports = [];
  for (const line of lines) {
    if (!line.startsWith('{')) continue;
    let value; try { value = JSON.parse(line); } catch { continue; }
    if (object(value) && Object.hasOwn(value, 'built_output_readback')) reports.push(value);
  }
  const uploads = lines.filter(line => line.startsWith('Artifact native-built-output-') && line.includes('has been successfully uploaded!'));
  need(reports.length === 1 && uploads.length === 1, 'Missing or ambiguous native readback receipts');
  const report = reports[0];
  need(Object.keys(report).sort().join() === 'built_output_readback,bytes,sha256' && positive(report.bytes) && digest(report.sha256) &&
    typeof report.built_output_readback === 'string' && report.built_output_readback.startsWith('/') &&
    safe(report.built_output_readback.slice(1)) && report.built_output_readback.endsWith('/.cache/' + reportName),
    'Invalid actual native readback receipt');
  const upload = /^Artifact (native-built-output-[-a-zA-Z0-9]{16,103}) has been successfully uploaded! Final size is ([1-9]\d*) bytes\. Artifact ID is ([1-9]\d*)$/.exec(uploads[0]);
  need(upload && positive(Number(upload[2])) && positive(Number(upload[3])), 'Invalid native readback upload receipt');
  return {report, artifact_name: upload[1], artifact_bytes: Number(upload[2]), artifact_id: Number(upload[3]), lines};
}

// Fixed member names, no extractall, no network, and no inherited credentials.
// The archive is authenticated before this subprocess starts. Decoded admission
// comes from its actual roster and available memory/disk, not a package-size cap.
const extract = String.raw`
import hashlib, os, shutil, stat, struct, sys, zipfile
archive, target, expected_bytes, expected_hash, budget, allow_smoke = sys.argv[1:]
expected_bytes, budget = int(expected_bytes), int(budget)
def need(ok, message):
    if not ok: raise ValueError(message)
with zipfile.ZipFile(archive) as package:
    members = package.infolist()
    names = [member.filename for member in members]
    need(1 <= len(names) <= 2 and len(set(names)) == len(names)
         and 'native-normal-built-output.json' in names
         and set(names) <= {'native-normal-built-output.json', 'selected-delivery-smoke.json'}
         and (allow_smoke == 'yes' or names == ['native-normal-built-output.json']),
         'Native archive inventory differs')
    # No prepended/unlisted local member, overlapping body, or trailing payload.
    # Streaming Actions ZIPs use signed or unsigned data descriptors; accept
    # both ordinary and ZIP64 descriptors and verify their actual sizes/CRC.
    ordered = sorted(members, key=lambda member: member.header_offset)
    need(ordered[0].header_offset == 0, 'Native archive has an unlisted prefix')
    with open(archive, 'rb') as source:
        for index, member in enumerate(ordered):
            source.seek(member.header_offset)
            header = source.read(30)
            need(len(header) == 30, 'Truncated native local header')
            fields = struct.unpack('<4s5H3L2H', header)
            need(fields[0] == b'PK\x03\x04' and fields[2] == member.flag_bits
                 and fields[3] == member.compress_type, 'Native local and central headers differ')
            end = member.header_offset + 30 + fields[-2] + fields[-1] + member.compress_size
            following = ordered[index + 1].header_offset if index + 1 < len(ordered) else package.start_dir
            gap = following - end
            need(gap in ((12, 16, 20, 24) if member.flag_bits & 8 else (0,)),
                 'Native archive has overlapping or unlisted local data')
            if gap:
                source.seek(end)
                descriptor = source.read(gap)
                if gap in (16, 24):
                    need(descriptor[:4] == b'PK\x07\x08', 'Invalid native data descriptor')
                    descriptor = descriptor[4:]
                values = struct.unpack('<LLL' if len(descriptor) == 12 else '<LQQ', descriptor)
                need(values == (member.CRC, member.compress_size, member.file_size), 'Native data descriptor differs')
        source.seek(max(0, os.path.getsize(archive) - 65557))
        tail = source.read()
        end = tail.rfind(b'PK\x05\x06')
        need(end >= 0 and len(tail) >= end + 22 and end + 22 + struct.unpack_from('<H', tail, end + 20)[0] == len(tail),
             'Native archive has a truncated end record or trailing data')
    decoded = 0
    for member in members:
        need(not member.is_dir() and not member.flag_bits & 1
             and stat.S_IFMT(member.external_attr >> 16) in (0, stat.S_IFREG)
             and member.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
             and 0 < member.file_size <= budget, 'Nonordinary or unadmitted native archive member')
        decoded += member.file_size
    need(decoded <= budget and shutil.disk_usage(os.path.dirname(target)).free >= decoded,
         'Insufficient resources for actual decoded native archive')
    need(package.getinfo('native-normal-built-output.json').file_size == expected_bytes,
         'Native report decoded bytes differ from actual job receipt')
    for member in members:
        output = open(target, 'xb') if member.filename == 'native-normal-built-output.json' else None
        size, checksum = 0, hashlib.sha256()
        try:
            with package.open(member) as stream:
                for chunk in iter(lambda: stream.read(1048576), b''):
                    size += len(chunk)
                    need(size <= member.file_size, 'Native member expanded beyond its complete inventory')
                    checksum.update(chunk)
                    if output: output.write(chunk)
            need(size == member.file_size, 'Incomplete native archive member')
            if output: need(checksum.hexdigest() == expected_hash, 'Native report digest differs from actual job receipt')
        finally:
            if output: output.close()
`;

function validateInventory(rows, label) {
  need(Array.isArray(rows) && rows.length > 0, 'Missing complete native ' + label + ' inventory');
  const paths = new Set(); let bytes = 0;
  for (const row of rows) {
    need(object(row) && Object.keys(row).sort().join() === 'bytes,path,sha256' && safe(row.path) && !paths.has(row.path) &&
      Number.isSafeInteger(row.bytes) && row.bytes >= 0 && digest(row.sha256), 'Invalid native ' + label + ' member');
    paths.add(row.path); bytes += row.bytes;
    need(Number.isSafeInteger(bytes), 'Native output total exceeds exact integer representation');
  }
  for (const name of paths) {
    const parts = name.split('/');
    for (let index = 1; index < parts.length; index++) need(!paths.has(parts.slice(0, index).join('/')), 'Native file/directory collision');
  }
  return {paths, bytes};
}

export async function loadSelectedPackageReadback({api, repo, runId, attempt, expectedHead, expectedPullRequest, fetchImpl = fetch}) {
  need(typeof api === 'function' && typeof api.artifactRedirect === 'function' && typeof api.jobLogRedirect === 'function' &&
    /^[-\w.]+\/[-\w.]+$/.test(repo ?? '') && positive(runId) && positive(attempt) && commit(expectedHead),
    'Exact authenticated native readback source required');
  const run = await api(`/repos/${repo}/actions/runs/${runId}/attempts/${attempt}`);
  need(run.id === runId && run.run_attempt === attempt && commit(run.head_sha) && run.status === 'completed' &&
    run.repository?.full_name === repo && run.head_repository?.full_name === repo,
    'Native readback run ID, attempt, completed status, head or repository identity differs');
  const producer = await producerFor(run, repo, expectedHead, expectedPullRequest, api);
  // Both fixed workflows fit one 100-row API page. Require the complete actual
  // inventory to establish uniqueness, without an open-ended discovery loop.
  const inventory = await api(`/repos/${repo}/actions/runs/${runId}/attempts/${attempt}/jobs?per_page=100&page=1`);
  need(Array.isArray(inventory.jobs) && positive(inventory.total_count) && inventory.total_count === inventory.jobs.length &&
    inventory.jobs.length <= 100 && new Set(inventory.jobs.map(row => row.id)).size === inventory.jobs.length,
    'Incomplete or duplicate native readback job inventory');
  const matches = inventory.jobs.filter(job => job.name === producer.job);
  need(matches.length === 1 && positive(matches[0].id), 'Exactly one native ' + producer.job + ' producer required');
  const job = await api(`/repos/${repo}/actions/jobs/${matches[0].id}`);
  need(job.id === matches[0].id && job.name === producer.job && job.run_id === runId && job.run_attempt === attempt &&
    job.head_sha === run.head_sha && job.status === 'completed' && job.conclusion === 'success' && Array.isArray(job.steps),
    'Native readback producer did not succeed on the exact attempt');
  const stepNumbers = producer.steps.map(name => {
    const rows = job.steps.filter(step => step.name === name);
    need(rows.length === 1 && rows[0].status === 'completed' && rows[0].conclusion === 'success' && positive(rows[0].number),
      'Native readback producer lacks successful actual step: ' + name);
    return rows[0].number;
  });
  need(stepNumbers.every((number, index) => index === 0 || number > stepNumbers[index - 1]), 'Native readback step order differs');
  const log = await delivery(await api.jobLogRedirect(`/repos/${repo}/actions/jobs/${job.id}/logs`), fetchImpl, maxLog);
  const receipt = receipts(log.raw);
  if (producer.artifactName) need(receipt.artifact_name === producer.artifactName &&
    receipt.lines.filter(line => line === authorReceipt).length === 1,
    'Native author full-build receipt or exact artifact name differs');
  const artifact = await api(`/repos/${repo}/actions/artifacts/${receipt.artifact_id}`);
  need(artifact.id === receipt.artifact_id && artifact.name === receipt.artifact_name && artifact.expired === false &&
    artifact.size_in_bytes === receipt.artifact_bytes && /^sha256:[a-f0-9]{64}$/.test(artifact.digest ?? '') &&
    artifact.workflow_run?.id === runId && artifact.workflow_run?.head_sha === run.head_sha,
    'Native readback artifact identity differs');
  const artifactDigest = artifact.digest.slice(7);
  need(receipt.lines.filter(line => line === `SHA256 digest of uploaded artifact zip is ${artifactDigest}`).length === 1,
    'Missing or ambiguous actual native archive digest');
  const heap = getHeapStatistics();
  // Reserve eight times the encoded metadata for JSON strings, object graphs,
  // archive-directory parsing and comparison; leave the rest to the caller.
  const budget = Math.floor(Math.min(process.availableMemory?.() ?? os.freemem(), heap.heap_size_limit - heap.used_heap_size) / 8);
  need(receipt.report.bytes <= budget && receipt.artifact_bytes <= budget, 'Insufficient memory for actual native metadata');
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'worldatlas-readback-'));
  try {
    const disk = fs.statfsSync(directory);
    need(disk.bavail * disk.bsize >= receipt.artifact_bytes + receipt.report.bytes, 'Insufficient disk for actual native archive');
    const archive = path.join(directory, 'readback.zip'), target = path.join(directory, reportName);
    const downloaded = await delivery(await api.artifactRedirect(`/repos/${repo}/actions/artifacts/${artifact.id}/zip`),
      fetchImpl, receipt.artifact_bytes, archive);
    need(downloaded.bytes === receipt.artifact_bytes && downloaded.sha256 === artifactDigest, 'Native archive bytes or digest differ');
    execFileSync('python3', ['-I', '-S', '-B', '-c', extract, archive, target, String(receipt.report.bytes), receipt.report.sha256, String(budget), producer.smoke ? 'yes' : 'no'],
      {env: {PATH: '/usr/bin:/bin', LANG: 'C.UTF-8'}, timeout: 120000, maxBuffer: 1048576, stdio: ['ignore', 'pipe', 'pipe']});
    const raw = fs.readFileSync(target);
    need(raw.length === receipt.report.bytes && hash(raw) === receipt.report.sha256, 'Extracted native readback changed');
    const report = JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(raw));
    need(report.version === 1 && report.kind === 'ordinary-cloudflare-built-output-readback' && report.head === expectedHead &&
      object(report.nativeContextInputStage) && object(report.nativeContextInputStage.current_execution) &&
      report.nativeContextInputStage.current_execution.source_head === expectedHead &&
      Array.isArray(report.nativeContextInputStage.current_execution.full_code_closure) &&
      report.nativeContextInputStage.current_execution.full_code_closure.length > 0, 'Native readback actual candidate or complete context differs');
    const assets = validateInventory(report.static_assets?.files, 'static asset');
    const worker = validateInventory(report.worker_bundle_files, 'worker bundle');
    need(report.static_assets.count === assets.paths.size && report.static_assets.bytes === assets.bytes &&
      assets.paths.has('atlas-geography.json') && worker.paths.has('index.js') && worker.paths.has('wrangler.json'),
      'Native readback complete output inventory differs');
    return {report, origin: {run_id: runId, run_attempt: attempt, job_id: job.id, head: expectedHead,
      workflow_head: run.head_sha, workflow_path: producer.workflow, event: run.event,
      ...(producer.pullRequest ? {pull_request: producer.pullRequest, pull_request_linkage: producer.linkage} : {}),
      artifact_id: artifact.id, artifact_name: artifact.name, artifact_bytes: artifact.size_in_bytes,
      artifact_digest: artifactDigest, report_bytes: raw.length, report_sha256: hash(raw),
      use: 'full-output-comparison-only'}};
  } finally { fs.rmSync(directory, {recursive: true, force: true}); }
}
