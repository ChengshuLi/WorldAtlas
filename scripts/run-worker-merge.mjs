import {gitBlobTransport} from './git-blob-transport.mjs';
import {quotaDelay,requestAccounting} from './github-quota.mjs';
import {loadGeographicReport} from './geographic-report-artifact.mjs';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {performance} from 'node:perf_hooks';
import {AsyncLocalStorage} from 'node:async_hooks';
import {loadJobDeadline, HTTP_ATTEMPT_MS, JOB_FINALIZATION_MS} from './job-deadline.mjs';
import {renderWorkerResult} from './worker-result.mjs';
import {githubAPI} from './issue-claim-contract.mjs';
import {loadEvidencePolicy} from './evidence-policy.mjs';
import {prepareIntegration, completeIntegration, cleanupCandidate} from './merge-integration.mjs';

const event = JSON.parse(fs.readFileSync(process.env.GITHUB_EVENT_PATH, 'utf8'));
const input = event.inputs ?? {}, repo = process.env.GITHUB_REPOSITORY;
if (process.env.GITHUB_REF !== 'refs/heads/main' || !/^[-\w.]+\/[-\w.]+$/.test(repo ?? '')) throw Error('Merges run only from trusted main');
const number = Number(input.pr_number), phase = process.env.MERGE_PHASE;
if (!['prepare','merge'].includes(phase) || !Number.isSafeInteger(number) || number < 1 ||
    !/^[a-f0-9]{40}$/.test(input.expected_head ?? '') || !/^[-a-zA-Z0-9]{16,100}$/.test(input.request_id ?? '')) throw Error('Invalid merge request');
const accounting=requestAccounting(phase);
const started = performance.now(), hosted = process.env.GITHUB_ACTIONS === 'true';
let deadline, bootstrapping = hosted;
const bootstrapRemaining = () => 2 * HTTP_ATTEMPT_MS + 1000 - (performance.now() - started);
const recovery = new AsyncLocalStorage();
// The same client owns quota state for work and its already-restricted recovery
// routes. Only those exact calls may consume the existing finalization reserve;
// concurrent authority reads never inherit that allowance.
const rawAPI = githubAPI(process.env.GH_TOKEN, {onRequest: accounting.observe,
  readWaitMs: phase === 'merge' ? 61 * 60 * 1000 : 8 * 60 * 1000,
  deadlineRemaining: () => {
    if (hosted && !bootstrapping && !deadline) return 0;
    const workRemaining = deadline ? deadline.remaining() : hosted ? bootstrapRemaining() :
      (phase === 'merge' ? 75 : 10) * 60_000 - JOB_FINALIZATION_MS - (performance.now() - started);
    return workRemaining + (recovery.getStore() ? JOB_FINALIZATION_MS : 0);
  }});
const recover = rawAPI.recovery;
rawAPI.recovery = (...args) => recovery.run(true, () => recover(...args));
const transport = gitBlobTransport(rawAPI, {repo, token: process.env.GH_TOKEN, directory: process.cwd(),
  onFetch: row => console.log(JSON.stringify({phase, immutable_transport: row}))});
const api = transport.api, options = {api, repo, number, expectedHead: input.expected_head, policy: loadEvidencePolicy(),
  integrationRequestId: input.request_id + (process.env.GITHUB_RUN_ID ? `-${process.env.GITHUB_RUN_ID}` : '')};
let result = {accepted: false, request_id: input.request_id, pr_number: number, phase};
try {
  if (hosted) {
    try {
      const workflowPath = '.github/workflows/worker-merge.yml';
      if (process.env.GITHUB_WORKFLOW_REF !== `${repo}/${workflowPath}@refs/heads/main` ||
          !/^[a-f0-9]{40}$/.test(process.env.GITHUB_WORKFLOW_SHA ?? '')) throw Error('Missing executing merge workflow authority');
      // The checkout follows current main; the executing workflow may be older.
      // Bind its literal timeout to its own immutable bytes, not the checkout.
      const file = await api(`/repos/${repo}/contents/${workflowPath}?ref=${process.env.GITHUB_WORKFLOW_SHA}`);
      if (file?.type !== 'file' || file.path !== workflowPath || file.encoding !== 'base64' ||
          !/^[a-f0-9]{40}$/.test(file.sha ?? '') || !Number.isSafeInteger(file.size) ||
          file.size <= 0 || file.size > 128 * 1024 || typeof file.content !== 'string') throw Error('Executing merge workflow unavailable');
      const bytes = Buffer.from(file.content, 'base64');
      if (bytes.length !== file.size || createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex') !== file.sha)
        throw Error('Executing merge workflow bytes changed');
      deadline = await loadJobDeadline({api, repo, phase, workflow: bytes.toString('utf8'), metadataRemaining: bootstrapRemaining});
      const {remaining, ...binding} = deadline;
      result.job_deadline = binding;
    } finally {
      // Refused or unbound job metadata cannot reopen a fresh startup clock,
      // even for recovery. Only an admitted authenticated deadline owns time.
      bootstrapping = false;
    }
  }
  if (phase === 'prepare') {
    const state = await prepareIntegration(options);
    result = {...result, accepted: Boolean(state.replayed), ...(state.replayed ? {merge_commit: state.pr.merge_commit_sha} : {}), status: state.replayed ? 'already-merged' : 'testing',
      tested_base: state.base, tested_candidate: state.candidate, reviewed_head: input.expected_head, profile: state.profile, geography_required: state.geography_required, geography_software: state.geography_software, test_selection: state.test_selection ?? 'complete', expectations_path: state.expectations_path,
      candidate_ref: state.candidate_ref};
    // Only validated commit IDs and owned ref identifiers become job outputs.
    fs.appendFileSync(process.env.GITHUB_OUTPUT, `geography_required=${state.geography_required !== false}\ngeography_software=${state.geography_software === true}\ncandidate_ref=${state.candidate_ref ?? ''}\ncandidate=${state.candidate ?? ''}\nbase=${state.base ?? ''}\nprofile=${state.profile ?? 'evidence'}\nshards=${JSON.stringify(state.shards ?? (state.profile === 'full' ? [0,1,2] : [0]))}\ntest_selection=${state.test_selection ?? 'complete'}\nexpectations_path=${state.expectations_path ?? ''}\n`);
  } else {
    const completed = await completeIntegration({...options, integrationResult: process.env.INTEGRATION_RESULT,
      geographyResult: process.env.GEOGRAPHY_RESULT,
      geographyReportHash: process.env.GEOGRAPHY_REPORT_SHA256,
      geographyReportLoader: ({api: reportAPI = api} = {}) => loadGeographicReport({api: reportAPI, repo,
        runId: process.env.GITHUB_RUN_ID,
        fresh: {run_attempt: Number(process.env.GITHUB_RUN_ATTEMPT),
          workflow_head: process.env.GITHUB_SHA, head: input.expected_head, baseline: process.env.TESTED_BASE,
          candidate_commit: process.env.TESTED_CANDIDATE, request_id: input.request_id},
        artifactName: process.env.GEOGRAPHY_ARTIFACT_NAME,
        expectedHash: process.env.GEOGRAPHY_REPORT_SHA256,
        token: process.env.GH_TOKEN}),
      testedBase: process.env.TESTED_BASE, testedCandidate: process.env.TESTED_CANDIDATE});
    result = {...result, ...completed, status: 'merged'};
  }
} catch (error) {
  result.reason = error.message;
  if (error.github) result.api_error = error.github;
  if (error.quotaCause?.github)result.quota_cause=error.quotaCause.github;
  if (error.jobDeadline || error.message === 'Job deadline exhausted during metadata admission') result.job_deadline_exhausted = true;
  if (error.deadlineBinding) result.deadline_binding = error.deadlineBinding;
  if (error.candidateCleanup) result.candidate_cleanup = error.candidateCleanup;
  if (error.candidateDiagnostics) result.candidate_diagnostics = error.candidateDiagnostics;
  result.status = /conflict|changes reviewed bytes|substantive review/.test(error.message) ? 'intervention-required' : 'not-merged';
  result.retryable = /resubmit unchanged head/.test(error.message) || (quotaDelay(error)??quotaDelay(error.quotaCause))!==null;
  if((quotaDelay(error)??quotaDelay(error.quotaCause))!==null)result.quota_retry_at=new Date(Date.now()+(quotaDelay(error)??quotaDelay(error.quotaCause))).toISOString();
  // A lost merge response or canceled predecessor can still have committed.
  // Reconcile the actual PR once; never repeat the merge write here.
  if (phase === 'merge') {
    try {
      const pr = await api(`/repos/${repo}/pulls/${number}`);
      if (pr.merged === true && pr.head?.sha === input.expected_head && /^[a-f0-9]{40}$/.test(pr.merge_commit_sha ?? ''))
        result = {...result, accepted: true, status: 'already-merged', merge_commit: pr.merge_commit_sha};
    } catch { /* The original failure remains; inspect the actual PR before retrying. */ }
  }
  if (!result.accepted) process.exitCode = 1;
}
if (phase === 'merge' && process.env.CANDIDATE_REF) {
  try { result.candidate_cleanup = await cleanupCandidate(options, process.env.CANDIDATE_REF, process.env.TESTED_CANDIDATE); }
  catch (error) { result.candidate_cleanup = {status: 'pending', reference: process.env.CANDIDATE_REF, reason: error.message}; }
}
result.request_accounting=accounting.receipt();
fs.writeFileSync('merge-result.json', JSON.stringify(result, null, 2) + '\n');
fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, `${result.status} PR #${number}: ${result.reason ?? ''}\n`);
console.log(JSON.stringify(result));
transport.close();
// Preserve the decision before attempting its remote notification. A comment
// permission/network failure must not discard the original result or reason.
try { await (api.recovery ?? api)(`/repos/${repo}/issues/${number}/comments`, 'POST', {body: renderWorkerResult('merge', result)}); }
catch (error) {
  result.notification_error = error.message;
  if (error.github) result.notification_api_error = error.github;
  // Failed preparation notification prevents the downstream final job from
  // running, so dispose of a confirmed owned candidate here rather than leak it.
  if (phase === 'prepare' && !result.accepted && result.candidate_ref) {
    try { result.candidate_cleanup = await cleanupCandidate(options, result.candidate_ref, result.tested_candidate); }
    catch (cleanupError) { result.candidate_cleanup = {status: 'pending', reference: result.candidate_ref, reason: cleanupError.message}; }
  }
  result.request_accounting=accounting.receipt();
  fs.writeFileSync('merge-result.json', JSON.stringify(result, null, 2) + '\n');
  console.log(JSON.stringify(result));
  if (!result.accepted) throw error;
}

result.request_accounting=accounting.receipt();
fs.writeFileSync('merge-result.json',JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify({request_accounting:accounting.receipt()}));
