import {loadGeographicReport} from './geographic-report-artifact.mjs';
import fs from 'node:fs';
import {assertAdmission} from './merge-scheduler.mjs';
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
const api = githubAPI(process.env.GH_TOKEN), options = {api, repo, number, expectedHead: input.expected_head, policy: loadEvidencePolicy(),
  prepareFallback: process.env.PREPARE_FALLBACK === 'true',
  integrationRequestId: input.request_id + (process.env.GITHUB_RUN_ID ? `-${process.env.GITHUB_RUN_ID}` : '')};
let result = {accepted: false, request_id: input.request_id, pr_number: number, phase, ...(input.queue_attempt ? {queue_attempt: Number(input.queue_attempt)} : {})};
try {
  if (process.env.QUEUE_ADMISSION === 'required') {
    await assertAdmission({api, repo, request: {pr_number: number, expected_head: input.expected_head, request_id: input.request_id},
      attempt: Number(input.queue_attempt), runId: process.env.GITHUB_RUN_ID});
  }
  if (phase === 'prepare') {
    const state = await prepareIntegration(options);
    result = {...result, status: state.replayed ? 'already-merged' : 'testing',
      tested_base: state.base, tested_candidate: state.candidate, reviewed_head: input.expected_head, profile: state.profile, proof: state.proof, candidate_refresh_attempts: state.candidate_refresh_attempts, candidate_ref: state.candidate_ref};
    // Only validated commit IDs and owned ref identifiers become job outputs.
    fs.appendFileSync(process.env.GITHUB_OUTPUT, `candidate_ref=${state.candidate_ref ?? ''}\nproof_attempt=${state.proof?.run_attempt ?? ''}\nproof_run=${state.proof?.run_id ?? ''}\ncandidate=${state.candidate ?? ''}\nbase=${state.base ?? ''}\nprofile=${state.profile ?? 'evidence'}\nshards=${JSON.stringify(state.profile === 'full' ? [0,1,2] : [0])}\n`);
  } else {
    const completed = await completeIntegration({...options, integrationResult: process.env.INTEGRATION_RESULT,
      geographyResult: process.env.GEOGRAPHY_RESULT,
      geographyReportHash: process.env.GEOGRAPHY_REPORT_SHA256,
      geographyReportLoader: () => loadGeographicReport({api, repo, runId: process.env.GITHUB_RUN_ID,
        artifactName: process.env.GEOGRAPHY_ARTIFACT_NAME, expectedHash: process.env.GEOGRAPHY_REPORT_SHA256,
        token: process.env.GH_TOKEN}),
      proofRunAttempt: process.env.PROOF_RUN_ATTEMPT ? Number(process.env.PROOF_RUN_ATTEMPT) : undefined,
      proofRunId: process.env.PROOF_RUN_ID ? Number(process.env.PROOF_RUN_ID) : undefined,
      testedBase: process.env.TESTED_BASE, testedCandidate: process.env.TESTED_CANDIDATE});
    result = {...result, ...completed, status: 'merged'};
  }
} catch (error) {
  result.reason = error.message;
  if (error.github) result.api_error = error.github;
  if (error.candidateCleanup) result.candidate_cleanup = error.candidateCleanup;
  if (error.candidateDiagnostics) result.candidate_diagnostics = error.candidateDiagnostics;
  result.status = /conflict|changes reviewed bytes|substantive review/.test(error.message) ? 'intervention-required' : 'not-merged';
  result.retryable = /resubmit unchanged head/.test(error.message);
  if (phase === 'prepare') process.exitCode = 1;
}
if (phase === 'merge' && process.env.CANDIDATE_REF) {
  try { result.candidate_cleanup = await cleanupCandidate(options, process.env.CANDIDATE_REF, process.env.TESTED_CANDIDATE); }
  catch (error) { result.candidate_cleanup = {status: 'pending', reference: process.env.CANDIDATE_REF, reason: error.message}; }
}
fs.writeFileSync('merge-result.json', JSON.stringify(result, null, 2) + '\n');
fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, `${result.status} PR #${number}: ${result.reason ?? ''}\n`);
console.log(JSON.stringify(result));
// Preserve the decision before attempting its remote notification. A comment
// permission/network failure must not discard the original result or reason.
try { await api(`/repos/${repo}/issues/${number}/comments`, 'POST', {body: renderWorkerResult('merge', result)}); }
catch (error) {
  result.notification_error = error.message;
  if (error.github) result.notification_api_error = error.github;
  // Failed preparation notification prevents the downstream final job from
  // running, so dispose of a confirmed owned candidate here rather than leak it.
  if (phase === 'prepare' && result.candidate_ref) {
    try { result.candidate_cleanup = await cleanupCandidate(options, result.candidate_ref, result.tested_candidate); }
    catch (cleanupError) { result.candidate_cleanup = {status: 'pending', reference: result.candidate_ref, reason: cleanupError.message}; }
  }
  fs.writeFileSync('merge-result.json', JSON.stringify(result, null, 2) + '\n');
  console.log(JSON.stringify(result));
  throw error;
}
