import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {runMergeWake} from '../scripts/run-merge-wake.mjs';

const epoch = Date.parse('2026-10-11T00:00:00Z'), sha = 'a'.repeat(40);
const env = {GITHUB_REPOSITORY: 'o/r', GITHUB_REF: 'refs/heads/main', GITHUB_EVENT_NAME: 'workflow_dispatch',
  GITHUB_JOB: 'wake', GITHUB_WORKFLOW_REF: 'o/r/.github/workflows/worker-merge.yml@refs/heads/main',
  GITHUB_WORKFLOW_SHA: sha, GITHUB_RUN_ID: '77', GH_TOKEN: 'synthetic-token'};
async function execute({environment = {}, head = sha, capacity = 1000, failure, capacityMs = 0, headMs = 0} = {}) {
  const calls = [];let elapsed = 0;const original = globalThis.fetch;
  globalThis.fetch = async (url, options) => {
    const route = new URL(url).pathname;calls.push({route, method: options.method,
      ...(options.body ? {body: JSON.parse(options.body)} : {})});
    assert.equal(options.headers.Authorization, 'Bearer synthetic-token');
    const headers = {'x-ratelimit-resource': 'core', 'x-ratelimit-limit': '1000',
      'x-ratelimit-remaining': String(capacity), 'x-ratelimit-reset': String(epoch / 1000 + 600)};
    if (options.method === 'GET') {
      assert.equal(route, '/repos/o/r');elapsed += capacityMs;
      return new Response('{}', {status: 200, headers});
    }
    assert.equal(route, '/repos/o/r/actions/workflows/merge-scheduler.yml/dispatches');
    if (failure === 'transport') throw Error('uncertain dispatch transport');
    if (failure === 'quota' || failure === 'permission') return new Response('{}', {status: 403,
      headers: {...headers, ...(failure === 'quota' ? {'retry-after': '5'} : {})}});
    return new Response(null, {status: 204, headers});
  };
  try {
    const result = await runMergeWake({env: {...env, ...environment}, readHead: () => {elapsed += headMs;return head;},
      monotonicNow: () => elapsed, wallNow: () => epoch + elapsed});
    return {result, calls};
  } finally {globalThis.fetch = original;}
}
test('actual notifier sends one registration-free run hint with bounded HTTP accounting', async () => {
  const x = await execute();assert.equal(x.result.failed, false);
  assert.deepEqual(x.result.result, {status: 'wake-dispatched', run_id: 77});
  assert.deepEqual(x.calls, [{route: '/repos/o/r', method: 'GET'},
    {route: '/repos/o/r/actions/workflows/merge-scheduler.yml/dispatches', method: 'POST',
      body: {ref: 'main', inputs: {wake_run_id: '77'}}}]);
  assert.equal(x.result.request_accounting.actual_http_attempts, 2);
});
test('untrusted, mixed-vintage, malformed and candidate contexts cannot notify', async () => {
  for (const environment of [
    {GITHUB_REF: 'refs/heads/candidate'}, {GITHUB_EVENT_NAME: 'pull_request'}, {GITHUB_JOB: 'integration'},
    {GITHUB_WORKFLOW_REF: 'o/r/.github/workflows/other.yml@refs/heads/main'},
    {GITHUB_WORKFLOW_SHA: 'bad'}, {GITHUB_REPOSITORY: 'other/repo'},
    {GITHUB_RUN_ID: '0'}, {GITHUB_RUN_ID: '9007199254740992'}, {GITHUB_RUN_ID: 77}
  ]) {
    const x = await execute({environment});assert.equal(x.result.failed, true);assert.equal(x.calls.length, 0);
  }
  const mixed = await execute({head: 'b'.repeat(40)});assert.equal(mixed.result.failed, true);assert.equal(mixed.calls.length, 0);
});
test('quota, ordinary denial and ambiguous wake POSTs are never replayed', async () => {
  for (const failure of ['quota', 'permission', 'transport']) {
    const x = await execute({failure});assert.equal(x.result.failed, true);
    assert.equal(x.result.result.retryable, failure === 'quota');
    assert.equal(x.calls.filter(row => row.method === 'POST').length, 1);
    assert.equal(x.result.request_accounting.actual_http_attempts, 2);
    if (failure === 'quota') assert.equal(x.result.result.retry_at, new Date(epoch + 6000).toISOString());
  }
});
test('actual core floor and short process budget refuse before sending a wake', async () => {
  const floor = await execute({capacity: 16});assert.equal(floor.result.failed, true);
  assert.equal(floor.result.result.retryable, true);assert.equal(floor.calls.length, 1);
  assert.equal(floor.result.result.quota_admission.remaining, 16);
  assert.equal(floor.result.result.retry_at, new Date(epoch + 601_000).toISOString());
  for (const options of [{headMs: 26_000}, {capacityMs: 26_000}]) {
    const x = await execute(options);assert.equal(x.result.failed, true);
    assert.equal(x.result.result.job_deadline_exhausted, true);
    assert.equal(x.calls.filter(row => row.method === 'POST').length, 0);
  }
});
test('trusted wake job handles every settled worker path without candidate credentials or idle recursion', () => {
  const worker = fs.readFileSync(new URL('../.github/workflows/worker-merge.yml', import.meta.url), 'utf8');
  const scheduler = fs.readFileSync(new URL('../.github/workflows/merge-scheduler.yml', import.meta.url), 'utf8');
  const wake = worker.split('\n  wake:\n')[1];assert.ok(wake);
  assert.match(wake, /needs: \[prepare, integration, geography, merge\]/);
  assert.match(wake, /if: always\(\) && github.ref == 'refs\/heads\/main'/);
  assert.match(wake, /timeout-minutes: 2/);assert.match(wake, /ref: \$\{\{ github.workflow_sha \}\}/);
  assert.match(wake, /persist-credentials: false/);assert.match(wake, /run: node scripts\/run-merge-wake.mjs/);
  assert.doesNotMatch(wake, /secrets\.|needs\.prepare\.outputs\.candidate/);
  const integration = worker.split('\n  integration:\n')[1].split('\n  merge:\n')[0];
  assert.doesNotMatch(integration, /GH_TOKEN|actions: write|contents: write/);
  assert.match(scheduler, /inputs.wake_run_id == ''/);
  const admission = scheduler.split('\njobs:\n')[1].split('\n  schedule:\n')[1];
  assert.match(admission, /group: worldatlas-merge-admission[\s\S]*?queue: max\n      cancel-in-progress: false/);
  assert.match(scheduler, /needs.register.result == 'success' \|\| needs.register.result == 'skipped'/);
  assert.match(scheduler, /cron: '\*\/5 \* \* \* \*'/);
  assert.doesNotMatch(scheduler, /run-merge-wake/);
});
