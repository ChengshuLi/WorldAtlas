import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {githubAPI} from '../scripts/issue-claim-contract.mjs';
import {workflowJobMinutes, loadJobDeadline, HTTP_ATTEMPT_MS, JOB_FINALIZATION_MS} from '../scripts/job-deadline.mjs';

const response = (status, payload) => new Response(JSON.stringify(payload), {status});
const workflow = fs.readFileSync(new URL('../.github/workflows/worker-merge.yml', import.meta.url), 'utf8');
const epoch = Date.parse('2026-10-07T00:00:00Z');
const env = {GITHUB_JOB: 'prepare', GITHUB_RUN_ID: '10', GITHUB_RUN_ATTEMPT: '1'};
const job = {id: 20, name: 'prepare', run_id: 10, run_attempt: 1,
  status: 'in_progress', started_at: new Date(epoch).toISOString()};

test('shared timeout parser retains literal budgets and rejects ambiguous workflow phases', () => {
  assert.equal(workflowJobMinutes(workflow, 'prepare'), 10);
  assert.equal(HTTP_ATTEMPT_MS, 20_000);
  assert.equal(JOB_FINALIZATION_MS, 30_000);
  assert.throws(() => workflowJobMinutes(workflow, 'missing'), /unique workflow phase/);
  assert.throws(() => workflowJobMinutes(workflow.replace('timeout-minutes: 10', 'timeout-minutes: ${{ inputs.limit }}'), 'prepare'), /literal/);
  assert.throws(() => workflowJobMinutes(workflow.replace('    runs-on: ubuntu-latest', '    name: renamed\n    runs-on: ubuntu-latest'), 'prepare'), /naming/);
});

test('shared job deadline charges setup and metadata time and advances only with the monotonic clock', async () => {
  let time = 10_000, wallOffset = 0, calls = 0;
  const deadline = await loadJobDeadline({api: async route => {
    calls++;
    assert.equal(route, '/repos/a/b/actions/runs/10/attempts/1/jobs?per_page=100&page=1');
    time += 15_000;
    return {total_count: 1, jobs: [job]};
  }, repo: 'a/b', phase: 'prepare', workflow, env,
  wallNow: () => epoch + time + wallOffset, monotonicNow: () => time});
  assert.equal(calls, 1);
  assert.equal(deadline.remaining(), 545_000);
  wallOffset = -60_000;time += 5_000;
  assert.equal(deadline.remaining(), 540_000);
  assert.equal(deadline.job_id, 20);
  assert.equal(deadline.timeout_minutes, 10);
  assert.equal(deadline.metadata_reads, 1);
});

test('shared deadline refuses incomplete, mismatched, ambiguous or expired execution metadata', async () => {
  for (const inventory of [
    {total_count: 2, jobs: [job]},
    {total_count: 2, jobs: [job, {...job, id: 21}]},
    {total_count: 1, jobs: [{...job, run_id: 11}]},
    {total_count: 1, jobs: [{...job, run_attempt: 2}]},
    {total_count: 1, jobs: [{...job, status: 'queued'}]},
    {total_count: 1, jobs: [{...job, started_at: '2026-02-30T00:00:00Z'}]}
  ]) {
    let calls = 0;
    await assert.rejects(loadJobDeadline({api: async () => {calls++;return inventory;},
      repo: 'a/b', phase: 'prepare', workflow, env,
      wallNow: () => epoch + 10_000, monotonicNow: () => 0}));
    assert.equal(calls, 1);
  }
  await assert.rejects(loadJobDeadline({api: async () => ({total_count: 1, jobs: [job]}),
    repo: 'a/b', phase: 'prepare', workflow, env,
    wallNow: () => epoch + 550_000, monotonicNow: () => 0}), /deadline exhausted/);
});

test('existing final HTTP-admission hook composes with job timing rather than replacing it', async () => {
  const old = globalThis.fetch;let calls = 0, left = 40_000, budget = 0;
  globalThis.fetch = async () => {calls++;return response(200, {});};
  try {
    const api = githubAPI('synthetic', {deadlineRemaining: () => left});
    const dispose = api.setHTTPAdmission(() => {budget++;});
    await api('/repos/a/b');assert.equal(calls, 1);assert.equal(budget, 1);
    left = 20_000;await assert.rejects(api('/repos/a/b'), /deadline/);assert.equal(calls, 1);assert.equal(budget, 1);
    dispose();left = 40_000;await api('/repos/a/b');assert.equal(calls, 2);assert.equal(budget, 1);
    left = Infinity;await assert.rejects(api('/repos/a/b'), /Invalid job deadline/);assert.equal(calls, 2);
    left = 40_000;const slowHook = githubAPI('synthetic', {deadlineRemaining: () => left});
    slowHook.setHTTPAdmission(() => {left = 19_000;});
    await assert.rejects(slowHook('/repos/a/b'), /deadline/);assert.equal(calls, 2);
  } finally {globalThis.fetch = old;}
});
