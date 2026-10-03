import fs from 'node:fs';
import {renderWorkerResult} from './worker-result.mjs';
import {githubAPI} from './issue-claim-contract.mjs';
import {loadEvidencePolicy} from './evidence-policy.mjs';
import {prepareIntegration, completeIntegration} from './merge-integration.mjs';

const event = JSON.parse(fs.readFileSync(process.env.GITHUB_EVENT_PATH, 'utf8'));
const input = event.inputs ?? {}, repo = process.env.GITHUB_REPOSITORY;
if (process.env.GITHUB_REF !== 'refs/heads/main' || !/^[-\w.]+\/[-\w.]+$/.test(repo ?? '')) throw Error('Merges run only from trusted main');
const number = Number(input.pr_number), phase = process.env.MERGE_PHASE;
if (!['prepare','merge'].includes(phase) || !Number.isSafeInteger(number) || number < 1 ||
    !/^[a-f0-9]{40}$/.test(input.expected_head ?? '') || !/^[-a-zA-Z0-9]{16,100}$/.test(input.request_id ?? '')) throw Error('Invalid merge request');
const api = githubAPI(process.env.GH_TOKEN), options = {api, repo, number, expectedHead: input.expected_head, policy: loadEvidencePolicy()};
let result = {accepted: false, request_id: input.request_id, pr_number: number, phase};
try {
  if (phase === 'prepare') {
    const state = await prepareIntegration(options);
    result = {...result, status: state.replayed ? 'already-merged' : 'testing',
      tested_base: state.base, tested_candidate: state.candidate, reviewed_head: input.expected_head, profile: state.profile};
    // Only validated hexadecimal IDs are exposed to the isolated candidate job.
    fs.appendFileSync(process.env.GITHUB_OUTPUT, `candidate=${state.candidate ?? ''}\nbase=${state.base ?? ''}\nprofile=${state.profile ?? 'evidence'}\nshards=${JSON.stringify(state.profile === 'full' ? [0,1,2] : [0])}\n`);
  } else {
    const completed = await completeIntegration({...options, integrationResult: process.env.INTEGRATION_RESULT,
      testedBase: process.env.TESTED_BASE, testedCandidate: process.env.TESTED_CANDIDATE});
    result = {...result, ...completed, status: 'merged'};
  }
} catch (error) {
  result.reason = error.message;
  result.status = /conflict|changes reviewed bytes|substantive review/.test(error.message) ? 'intervention-required' : 'not-merged';
  result.retryable = /resubmit unchanged head/.test(error.message);
  if (phase === 'prepare') process.exitCode = 1;
}
fs.writeFileSync('merge-result.json', JSON.stringify(result, null, 2) + '\n');
fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, `${result.status} PR #${number}: ${result.reason ?? ''}\n`);
console.log(JSON.stringify(result));
// Preserve the decision before attempting its remote notification. A comment
// permission/network failure must not discard the original result or reason.
await api(`/repos/${repo}/issues/${number}/comments`, 'POST', {body: renderWorkerResult('merge', result)});
