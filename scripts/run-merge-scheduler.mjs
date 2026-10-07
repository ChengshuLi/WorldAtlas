import {requestAccounting} from './github-quota.mjs';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {githubAPI} from './issue-claim-contract.mjs';
import {registerRequest, scheduleNext} from './merge-scheduler.mjs';
import {loadSchedulerDeadline} from './job-deadline.mjs';
import {quotaDelay} from './github-quota.mjs';

const workflowPath = '.github/workflows/merge-scheduler.yml';
const checkoutRoot = fileURLToPath(new URL('../', import.meta.url));
export function executingWorkflow(env, readGit = (args) => execFileSync('git', args,
  {cwd: checkoutRoot, encoding: 'utf8', maxBuffer: 1024 * 1024})) {
  if (!/^[a-f0-9]{40}$/.test(env.GITHUB_WORKFLOW_SHA ?? '') ||
    env.GITHUB_WORKFLOW_REF !== `${env.GITHUB_REPOSITORY}/${workflowPath}@refs/heads/main`) {
    throw Error('Missing executing workflow commit/ref authority');
  }
  // Read the immutable executing workflow, never newer checked-out main bytes.
  // Checkout is pinned to this commit too; refuse mixed-vintage executable code.
  if (readGit(['rev-parse', 'HEAD']).trim() !== env.GITHUB_WORKFLOW_SHA) {
    throw Error('Checkout does not match executing workflow commit');
  }
  return readGit(['show', `${env.GITHUB_WORKFLOW_SHA}:${workflowPath}`]);
}

// Tests call the same entry point with isolated HTTP and clocks, not a second
// implementation of registration or the quota classifier.
export async function runScheduler({event, env = process.env, apiFactory = githubAPI,
  workflow, readGit,
  wallNow = Date.now, monotonicNow, sleep}) {
  const repo = env.GITHUB_REPOSITORY, phase = env.QUEUE_PHASE;
  const accounting = requestAccounting(phase), options = {onRequest: accounting.observe, now: wallNow,
    ...(sleep ? {sleep} : {})};
  let request, deadline;
  try {
    if (env.GITHUB_REF !== 'refs/heads/main' || !/^[-\w.]+\/[-\w.]+$/.test(repo ?? '') ||
      !['register', 'schedule'].includes(phase)) throw Error('Scheduler runs only from a trusted main phase');
    if (phase === 'register') {
      const input = event.inputs ?? {};
      request = {pr_number: Number(input.pr_number), expected_head: input.expected_head, request_id: input.request_id};
      if (!Number.isSafeInteger(request.pr_number) || request.pr_number < 1 || !/^[a-f0-9]{40}$/.test(request.expected_head ?? '') ||
        !/^[-a-zA-Z0-9]{16,100}$/.test(request.request_id ?? '')) throw Error('Invalid queue request');
    }
    const authenticatedWorkflow = executingWorkflow(env, readGit);
    if (workflow !== undefined && workflow !== authenticatedWorkflow) throw Error('Workflow bytes differ from executing commit');
    const bootstrap = apiFactory(env.GH_TOKEN, options); // No quota retry before authenticated timing.
    deadline = await loadSchedulerDeadline({api: bootstrap, repo, phase, workflow: authenticatedWorkflow, env, wallNow, monotonicNow});
    deadline.workflow_commit = env.GITHUB_WORKFLOW_SHA;
    deadline.workflow_ref = env.GITHUB_WORKFLOW_REF;
    const api = apiFactory(env.GH_TOKEN, {...options, readWaitMs: Math.min(8 * 60_000, deadline.remaining()),
      deadlineRemaining: deadline.remaining});
    const result = phase === 'register' ? await registerRequest({api, repo, request}) : await scheduleNext({api, repo, clock: wallNow});
    const {remaining, ...job} = deadline;
    return {result, job_deadline: job, request_accounting: accounting.receipt(), failed: false};
  } catch (error) {
    const quota = error.github ? error : error.quotaCause;
    const retry = quotaDelay(quota, wallNow());
    const {remaining, ...job} = deadline ?? {};
    return {result: {accepted: false, status: 'refused', phase,
      ...(request && /^[-a-zA-Z0-9]{16,100}$/.test(request.request_id ?? '') ? {request_id: request.request_id} : {}),
      reason: error.message, ...(error.github ? {api_error: error.github} : {}),
      ...(error.quotaCause?.github ? {quota_cause: error.quotaCause.github} : {}),
      ...(error.jobDeadline ? {job_deadline_exhausted: true} : {}),
      retryable: retry !== null, ...(retry !== null ? {retry_at: new Date(wallNow() + retry).toISOString()} : {})},
    ...(deadline ? {job_deadline: job} : {}), request_accounting: accounting.receipt(), failed: true};
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const event = JSON.parse(fs.readFileSync(process.env.GITHUB_EVENT_PATH, 'utf8'));
  const execution = await runScheduler({event});
  console.log(JSON.stringify(execution.result));
  if (execution.job_deadline) console.log(JSON.stringify({job_deadline: execution.job_deadline}));
  console.log(JSON.stringify({request_accounting: execution.request_accounting}));
  // A registration refusal must not advance scheduling as though a durable
  // request were written. Recovery inspects the same identity before retrying.
  if (execution.failed) process.exitCode = 1;
}
