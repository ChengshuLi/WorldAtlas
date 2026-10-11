import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {performance} from 'node:perf_hooks';
import {githubAPI} from './issue-claim-contract.mjs';
import {quotaDelay, requestAccounting} from './github-quota.mjs';

const checkoutRoot = fileURLToPath(new URL('../', import.meta.url));
// One bounded notification, never a registration, merge authorization or retry.
// No startup Actions-job lookup is needed for this non-retrying, short-lived POST.
export async function runMergeWake({env = process.env, apiFactory = githubAPI,
  readHead = () => execFileSync('git', ['rev-parse', 'HEAD'], {cwd: checkoutRoot, encoding: 'utf8'}).trim(),
  monotonicNow = () => performance.now(), wallNow = Date.now} = {}) {
  const accounting = requestAccounting('completion-wake'), started = monotonicNow();
  const repo = env.GITHUB_REPOSITORY, run = env.GITHUB_RUN_ID;
  try {
    if (!/^[-\w.]+\/[-\w.]+$/.test(repo ?? '') || env.GITHUB_REF !== 'refs/heads/main' ||
      env.GITHUB_EVENT_NAME !== 'workflow_dispatch' || env.GITHUB_JOB !== 'wake' ||
      env.GITHUB_WORKFLOW_REF !== `${repo}/.github/workflows/worker-merge.yml@refs/heads/main` ||
      !/^[a-f0-9]{40}$/.test(env.GITHUB_WORKFLOW_SHA ?? '') || readHead() !== env.GITHUB_WORKFLOW_SHA ||
      typeof run !== 'string' || !/^[1-9]\d*$/.test(run) || !Number.isSafeInteger(Number(run))) {
      throw Error('Completion wake needs the executing trusted-main worker workflow');
    }
    const api = apiFactory(env.GH_TOKEN, {onRequest: accounting.observe, now: wallNow,
      minimumRemaining: 16, deadlineRemaining: () => {
        const elapsed = monotonicNow() - started;
        if (!Number.isFinite(elapsed) || elapsed < 0) throw Error('Invalid completion wake clock');
        return 45_000 - elapsed;
      }});
    await api(`/repos/${repo}/actions/workflows/merge-scheduler.yml/dispatches`, 'POST',
      {ref: 'main', inputs: {wake_run_id: run}});
    return {result: {status: 'wake-dispatched', run_id: Number(run)}, failed: false,
      request_accounting: accounting.receipt()};
  } catch (error) {
    const delay = quotaDelay(error, wallNow());
    return {result: {status: 'wake-refused', reason: error.message, retryable: delay !== null,
      ...(error.github ? {api_error: error.github} : {}),
      ...(error.quotaAdmission ? {quota_admission: error.quotaAdmission} : {}),
      ...(error.jobDeadline ? {job_deadline_exhausted: true} : {}),
      ...(delay !== null ? {retry_at: new Date(wallNow() + delay).toISOString()} : {})},
    failed: true, request_accounting: accounting.receipt()};
  }
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const execution = await runMergeWake();
  console.log(JSON.stringify(execution));
  if (execution.failed) process.exitCode = 1;
}
