// A candidate locator is data. Only the existing bot acceptance, independently
// merged PR and original authenticated geography artifact can issue this handle.
import {gunzipSync} from 'node:zlib';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {githubAPI, githubPages} from './issue-claim-contract.mjs';
import {readWorkerResult, verifyAcceptedMergeResult} from './worker-result.mjs';
import {WORKFLOW_PATH} from './integration-proof.mjs';
import {checkGeographicReport, loadGeographicReport, geographicReportProducts, validateGeographyProof,
  validateGeographyOrigin, reportHash} from './geographic-report-artifact.mjs';

const custody = new WeakMap(), archives = new WeakMap();
export const ACCEPTED_CHECKPOINT_LOCATOR = 'data/selected-checkpoint.json';
export const ACCEPTED_CHECKPOINT_CODE = Object.freeze([
  'scripts/accepted-selected-checkpoint.mjs', 'scripts/check-handoff-scope.mjs',
  'scripts/evidence-policy.mjs', 'scripts/evidence-quality.mjs', 'scripts/geographic-report-artifact.mjs',
  'scripts/github-quota.mjs', 'scripts/github-snapshots.mjs', 'scripts/integration-proof.mjs',
  'scripts/issue-claim-contract.mjs', 'scripts/research-import-gate.mjs',
  'scripts/worker-result.mjs', 'src/regional-import-gate.js'
]);
const need = (ok, message) => { if (!ok) throw Error(message); };
const commit = value => typeof value === 'string' && /^[a-f0-9]{40}$/.test(value);
const unavailable = reason => Object.freeze({available: false, reason});
const freeze = value => {
  if (value && typeof value === 'object' && !Object.isFrozen(value)) {
    Object.values(value).forEach(freeze); Object.freeze(value);
  }
  return value;
};

export function acceptedCheckpointAPI(token, {fetchImpl = fetch} = {}) {
  return githubAPI(token, {conditionalReads: false, fetchImpl});
}

export async function acquireAcceptedCheckpoint({api, repo, locator, token, retainedArchive, fetchImpl = fetch}) {
  need(/^[-\w.]+\/[-\w.]+$/.test(repo ?? '') && locator && Number.isSafeInteger(locator.pr_number) && locator.pr_number > 0 &&
    /^[-a-zA-Z0-9]{16,100}$/.test(locator.request_id ?? '') && commit(locator.head),
    'Invalid accepted checkpoint locator');
  api = api ?? acceptedCheckpointAPI(token, {fetchImpl});
  const comments = await githubPages(api, `/repos/${repo}/issues/${locator.pr_number}/comments`);
  const receipt = readWorkerResult(comments, 'merge', locator.request_id, locator.pr_number);
  if (!receipt || !receipt.accepted) return unavailable('No accepted merge receipt for checkpoint locator');
  const merged = await api(`/repos/${repo}/pulls/${locator.pr_number}`);
  verifyAcceptedMergeResult(receipt, merged, locator.head);
  need(merged.number === locator.pr_number && merged.base?.ref === 'main' && merged.base.repo?.full_name === repo &&
    merged.head.repo?.full_name === repo && receipt.reviewed_head === locator.head,
    'Accepted checkpoint belongs to another repository, PR or reviewed head');
  if (!receipt.geography?.source) return unavailable('Accepted merge predates complete checkpoint artifact provenance');
  const original = validateGeographyProof(receipt.geography.source);
  // Legacy PR receipts omitted these redundant family fields. Derive only the
  // fixed PR family, then independently verify the original run and job below.
  const source = validateGeographyProof(original.workflow_path ? original : {...original,
    workflow_path: WORKFLOW_PATH, event: 'pull_request', workflow_head: original.head, candidate_commit: original.head});
  need(receipt.geography.status === 'passed' && receipt.geography.report_sha256 === source.report_sha256 &&
    receipt.geography.trusted_code_commit === source.baseline && receipt.tested_base === source.baseline &&
    receipt.geography.candidate_commit === source.candidate_commit && source.head === locator.head &&
    commit(receipt.tested_candidate), 'Accepted checkpoint receipt/source identities differ');
  await validateGeographyOrigin({api, repo, number: locator.pr_number, source});
  const acceptedCommit = await api(`/repos/${repo}/git/commits/${receipt.merge_commit}`);
  const testedCommit = await api(`/repos/${repo}/git/commits/${receipt.tested_candidate}`);
  need(acceptedCommit.sha === receipt.merge_commit && testedCommit.sha === receipt.tested_candidate &&
    acceptedCommit.tree?.sha === source.tree && testedCommit.tree?.sha === source.tree,
    'Accepted checkpoint tree differs from actual merge or tested candidate');
  let report;
  try {
    report = await loadGeographicReport({api, repo, runId: source.run_id, artifactName: source.artifact_name,
      expectedHash: source.report_sha256, source, token, retainedArchive, fetchImpl});
  } catch (error) {
    if (error.geographyUnavailable) return unavailable(error.message);
    throw error;
  }
  checkGeographicReport(report, source.baseline, source.candidate_commit);
  if (!report.checkpoint) return unavailable('Accepted legacy report has no complete checkpoint products');
  const artifact = geographicReportProducts(report);
  const products = Object.create(null);
  for (const pin of report.checkpoint.members.filter(pin => artifact.members.has(pin.name))) {
    const encoded = artifact.members.get(pin.name);
    const body = pin.name.endsWith('.gz') ? gunzipSync(encoded, {maxOutputLength: pin.decoded_bytes}) : encoded;
    products[pin.name] = JSON.parse(body.toString('utf8'));
  }
  const handle = Object.freeze({});
  archives.set(handle, artifact.archive_bytes);
  custody.set(handle, freeze({receipt, source, report, products, member_pins: report.checkpoint.members,
    archive_origin: artifact.archive_origin}));
  return Object.freeze({available: true, handle});
}

// The private entry is minted only above. A JSON copy or a fabricated object
// cannot supply a capability. Release bounds it to the owning joint invocation.
export function readAcceptedCheckpoint(handle) {
  const proof = custody.get(handle);
  need(proof, 'Missing private accepted checkpoint custody');
  return proof;
}
export function releaseAcceptedCheckpoint(handle) { custody.delete(handle); archives.delete(handle); }

export function validateAcceptedCheckpointLocator(value) {
  const expected = ['version', 'kind', 'acceptance', ...(value && Object.hasOwn(value, 'retained_artifact') ? ['retained_artifact'] : [])];
  need(value && typeof value === 'object' && Object.keys(value).sort().join() === expected.sort().join() &&
    value.version === 1 && value.kind === 'accepted-selected-checkpoint-locator-v1', 'Invalid checkpoint locator document');
  const source = value.acceptance;
  need(source && Object.keys(source).sort().join() === 'head,pr_number,request_id' &&
    Number.isSafeInteger(source.pr_number) && source.pr_number > 0 && commit(source.head) &&
    /^[-a-zA-Z0-9]{16,100}$/.test(source.request_id ?? ''), 'Invalid checkpoint acceptance locator');
  if (Object.hasOwn(value, 'retained_artifact')) need(value.retained_artifact && Object.keys(value.retained_artifact).join() === 'path' &&
    /^coordination\/engineering\/[a-z0-9][a-z0-9-]{0,63}\/(?:[a-zA-Z0-9_.-]+\/)*geography-artifact\.zip$/.test(value.retained_artifact.path ?? '') &&
    value.retained_artifact.path.split('/').every(part => part !== '.' && part !== '..'), 'Invalid batch-owned retained artifact path');
  return value;
}

// The fresh batch-owned directory is a durable copy, not an authority registry.
// Its final locator appears only after the exact accepted ZIP has been written.
export function retainAcceptedCheckpoint(handle, {repo, directory}) {
  const proof = readAcceptedCheckpoint(handle), bytes = archives.get(handle);
  need(Buffer.isBuffer(bytes) && bytes.length === proof.source.artifact_bytes &&
    reportHash(bytes) === proof.source.artifact_digest, 'Exact accepted artifact unavailable for ordinary retained copy');
  need(/^coordination\/engineering\/[a-z0-9][a-z0-9-]{0,63}\/[a-zA-Z0-9_-][a-zA-Z0-9_.-]{0,99}$/.test(directory ?? ''),
    'Retained checkpoint needs a fresh batch-owned evidence directory');
  const root = fs.realpathSync(repo), destination = path.join(root, directory);
  for (let parent = path.dirname(destination);; parent = path.dirname(parent)) {
    const stat = fs.lstatSync(parent);
    need(stat.isDirectory() && !stat.isSymbolicLink(), 'Nonordinary retained checkpoint parent');
    if (parent === root) break;
  }
  need(!fs.lstatSync(destination, {throwIfNoEntry: false}), 'Retained checkpoint destination already exists');
  const locator = validateAcceptedCheckpointLocator({version: 1, kind: 'accepted-selected-checkpoint-locator-v1',
    acceptance: {pr_number: proof.receipt.pr_number, request_id: proof.receipt.request_id, head: proof.source.head},
    retained_artifact: {path: directory + '/geography-artifact.zip'}});
  fs.mkdirSync(destination);
  fs.writeFileSync(path.join(destination, 'geography-artifact.zip'), bytes, {flag: 'wx', mode: 0o644});
  fs.writeFileSync(path.join(destination, 'selected-checkpoint.json'), JSON.stringify(locator, null, 2) + '\n', {flag: 'wx', mode: 0o644});
  return locator;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [repository, number, request_id, head, directory] = process.argv.slice(2);
  need(directory && process.argv.length === 7,
    'Use accepted-selected-checkpoint.mjs owner/repo PR REQUEST_ID HEAD coordination/engineering/BATCH/FRESH_DIRECTORY');
  const token = process.env.GH_TOKEN ?? execFileSync('gh', ['auth', 'token'], {encoding: 'utf8', timeout: 20000, maxBuffer: 16384}).trim();
  const result = await acquireAcceptedCheckpoint({repo: repository,
    locator: {pr_number: Number(number), request_id, head}, token});
  need(result.available, result.reason);
  try { console.log(JSON.stringify(retainAcceptedCheckpoint(result.handle, {repo: process.cwd(), directory}))); }
  finally { releaseAcceptedCheckpoint(result.handle); }
}
