import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync, execFileSync} from 'node:child_process';
import {runScheduler, executingWorkflow} from '../scripts/run-merge-scheduler.mjs';
import {githubAPI} from '../scripts/issue-claim-contract.mjs';
import {queueBody} from '../scripts/merge-scheduler.mjs';
import {schedulerJobMinutes, HTTP_ATTEMPT_MS, JOB_FINALIZATION_MS} from '../scripts/job-deadline.mjs';

const workflow = fs.readFileSync(new URL('../.github/workflows/merge-scheduler.yml', import.meta.url), 'utf8');
const workflowSha = 'b'.repeat(40);
const workflowRef = 'a/b/.github/workflows/merge-scheduler.yml@refs/heads/main';
const readGit = args => args[0] === 'rev-parse' ? workflowSha + '\n' : workflow;
const epoch = Date.parse('2026-10-07T00:00:00Z');
const request = {pr_number: 2, expected_head: 'a'.repeat(40), request_id: 'deadline-test-stable-request'};
const event = {inputs: request};
const response = (status, payload, headers = {}) => new Response(JSON.stringify(payload), {status, headers});

async function execute({phase = 'register', elapsed = 0, rejection = [], requestMs = 0, bodyMs = 0,
  metadataMs = 0, editJobs = value => value, replay = false, ambiguousWrite = false,
  oversleepMs = 0, bootstrapReject = false, afterReadMs = 0, clockRollback = false, dispatchAfterQuota = false} = {}) {
  let time = elapsed, wallOffset = 0, reads = 0, inventories = 0;
  const calls = [], waits = [], posted = [];
  const original = globalThis.fetch;
  globalThis.fetch = async (url, options) => {
    const route = new URL(url).pathname, method = options.method;
    assert.equal(new URL(url).origin, 'https://api.github.com');
    assert.equal(options.headers.Authorization, 'Bearer synthetic-test-token');
    calls.push({route, method, at: time});
    if (route.endsWith('/attempts/1/jobs')) {
      time += metadataMs;
      if (bootstrapReject) return response(403, {message: 'secondary limit'}, {'retry-after': '180'});
      return response(200, editJobs({total_count: 1, jobs: [{id: 20, name: phase, run_id: 10,
        run_attempt: 1, status: 'in_progress', started_at: new Date(epoch).toISOString()}]}));
    }
    if (phase === 'schedule' && route === '/repos/a/b') return response(200, {}, {
      'x-ratelimit-limit': '1000', 'x-ratelimit-remaining': dispatchAfterQuota ? '1000' : '0',
      'x-ratelimit-reset': String((epoch + 600_000) / 1000), 'x-ratelimit-resource': 'core'});
    if (dispatchAfterQuota && route.endsWith('/actions/workflows/worker-merge.yml/runs')) return response(200, {workflow_runs: []});
    if (dispatchAfterQuota && route === '/repos/a/b/pulls') {
      if (++inventories === 1) return response(403, {}, {'retry-after': '5'});
      return response(200, [{number: 2, state: 'open', head: {sha: request.expected_head}}]);
    }
    if (method === 'POST') {
      posted.push(JSON.parse(options.body));
      if (ambiguousWrite) throw Error('uncertain transport');
      return response(201, {id: 30, body: posted.at(-1).body});
    }
    if (route.endsWith('/pulls/2')) {
      time += requestMs;
      if (clockRollback) wallOffset = -60_000;
      const rejected = rejection[reads++];
      if (rejected) return response(rejected.status ?? 403, {message: rejected.message ?? 'rate limit exceeded'}, rejected.headers);
      const r = response(200, {number: 2, state: 'open', head: {sha: request.expected_head}});
      if (bodyMs) {const json = r.json.bind(r);r.json = async () => {time += bodyMs;return json();};}
      return r;
    }
    if (route.endsWith('/issues/2/comments')) {
      time += afterReadMs;
      return response(200, replay || dispatchAfterQuota ? [{id: 1, user: {login: 'github-actions[bot]'}, body: queueBody({...request, kind: 'request'})}] : []);
    }
    throw Error('Unexpected HTTP route: ' + route);
  };
  try {
    const result = await runScheduler({event, workflow, readGit,
      env: {GH_TOKEN: 'synthetic-test-token', GITHUB_REF: 'refs/heads/main', GITHUB_REPOSITORY: 'a/b',
        GITHUB_WORKFLOW_SHA: workflowSha, GITHUB_WORKFLOW_REF: workflowRef,
        GITHUB_RUN_ID: '10', GITHUB_RUN_ATTEMPT: '1', GITHUB_JOB: phase, QUEUE_PHASE: phase},
      wallNow: () => epoch + time + wallOffset, monotonicNow: () => time,
      sleep: async ms => {waits.push(ms);time += ms + oversleepMs;}});
    return {result, calls, waits, posted, time};
  } finally {globalThis.fetch = original;}
}

test('actual workflow binds distinct five/ten minute budgets, with explicit finalization and attempt margins', () => {
  assert.equal(schedulerJobMinutes(workflow, 'register'), 5);
  assert.equal(schedulerJobMinutes(workflow, 'schedule'), 10);
  assert.equal(HTTP_ATTEMPT_MS, 20_000);assert.equal(JOB_FINALIZATION_MS, 30_000);
  const register = workflow.split('  register:\n')[1].split('  schedule:\n')[0];
  assert.match(register, /actions: read/);
  assert.match(workflow, /cron: '\*\/5 \* \* \* \*'/);
  assert.throws(() => schedulerJobMinutes(workflow.replace('timeout-minutes: 5', 'timeout-minutes: ${{ inputs.limit }}'), 'register'), /literal/);
  assert.throws(() => schedulerJobMinutes(workflow.replace('    runs-on: ubuntu-latest', '    name: renamed\n    runs-on: ubuntu-latest'), 'register'), /naming/);
});

test('actual registration refuses a second 181-second wait inside its real remaining job budget', async () => {
  const x = await execute({elapsed: 10_000, rejection: [{headers: {'retry-after': '180'}}, {headers: {'retry-after': '180'}}]});
  assert.deepEqual(x.waits, [181_000]);assert.equal(x.time, 191_000);
  assert.equal(x.result.failed, true);assert.equal(x.result.result.request_id, request.request_id);
  assert.equal(x.result.result.job_deadline_exhausted, true);
  assert.equal(x.result.result.api_error.retry_after, '180');assert.equal(x.result.result.retryable, true);
  assert.equal(x.posted.length, 0);assert.equal(x.result.request_accounting.actual_http_attempts, 3);
});

test('361-second wait is rejected before sleeping; short explicit GET retry succeeds and registers the same identity once', async () => {
  const long = await execute({rejection: [{headers: {'retry-after': '360'}}]});
  assert.deepEqual(long.waits, []);assert.equal(long.posted.length, 0);assert.equal(long.result.result.job_deadline_exhausted, true);
  const short = await execute({elapsed: 10_000, rejection: [{headers: {'retry-after': '2'}}]});
  assert.deepEqual(short.waits, [3000]);assert.equal(short.result.failed, false);assert.equal(short.posted.length, 1);
  assert.match(short.posted[0].body, new RegExp(request.request_id));
  assert.equal(short.result.request_accounting.actual_http_attempts, 5);
});

test('setup, metadata and earlier requests are charged before another read or write is admitted', async () => {
  const bootstrap = await execute({elapsed: 240_000, metadataMs: 15_000});
  assert.equal(bootstrap.calls.length, 1);assert.equal(bootstrap.result.failed, true);assert.equal(bootstrap.posted.length, 0);
  const previous = await execute({elapsed: 220_000, afterReadMs: 35_000});
  assert.equal(previous.result.result.job_deadline_exhausted, true);assert.equal(previous.posted.length, 0);
  assert.equal(previous.result.request_accounting.actual_http_attempts, 3);
  const slow = await execute({elapsed: 230_000, requestMs: 15_000, rejection: [{headers: {'retry-after': '8'}}]});
  assert.deepEqual(slow.waits, []);assert.equal(slow.posted.length, 0);
});

test('primary reset shares the actual deadline and ordinary permission denial never retries', async () => {
  const primary = await execute({elapsed: 220_000, rejection: [{headers: {'x-ratelimit-remaining': '0',
    'x-ratelimit-reset': String((epoch + 260_000) / 1000)}}]});
  assert.deepEqual(primary.waits, []);assert.equal(primary.result.result.retryable, true);
  const permission = await execute({rejection: [{headers: {'x-ratelimit-remaining': '900'}}]});
  assert.deepEqual(permission.waits, []);assert.equal(permission.result.result.retryable, false);
  assert.equal(permission.calls.length, 2);assert.equal(permission.posted.length, 0);
});

test('oversleep rechecks admission and preserves the original quota cause without sending another HTTP attempt', async () => {
  const x = await execute({elapsed: 220_000, rejection: [{headers: {'retry-after': '2'}}], oversleepMs: 30_000});
  assert.equal(x.calls.length, 2);assert.equal(x.result.result.job_deadline_exhausted, true);
  assert.equal(x.result.result.quota_cause.retry_after, '2');assert.equal(x.result.result.retryable, true);
  assert.equal(x.result.request_accounting.actual_http_attempts, 2);assert.equal(x.posted.length, 0);
});

test('delayed body cannot turn an exhausted job into successful registration; wall clock rollback grants no extra time', async () => {
  // The response mock deliberately ignores real timeout signals. The final
  // elapsed-time check must still reject it; this is not a real 20-second sleep.
  const body = await execute({elapsed: 160_000, bodyMs: 120_000});
  assert.equal(body.result.result.job_deadline_exhausted, true);assert.equal(body.posted.length, 0);
  const rollback = await execute({elapsed: 230_000, requestMs: 15_000, clockRollback: true,
    rejection: [{headers: {'retry-after': '8'}}]});
  assert.deepEqual(rollback.waits, []);assert.equal(rollback.posted.length, 0);
});

test('ambiguous write is attempted once; existing durable request replays without another POST', async () => {
  const ambiguous = await execute({ambiguousWrite: true});
  assert.equal(ambiguous.posted.length, 1);assert.equal(ambiguous.result.failed, true);
  assert.equal(ambiguous.result.result.retryable, false);assert.equal(ambiguous.result.result.request_id, request.request_id);
  assert.equal(ambiguous.result.request_accounting.actual_http_attempts, 4);
  const replay = await execute({replay: true});assert.equal(replay.result.failed, false);assert.equal(replay.posted.length, 0);
  assert.equal(replay.result.result.request_id, request.request_id);assert.equal(replay.result.request_accounting.actual_http_attempts, 3);
});

test('bootstrap quota is not retried; complete unambiguous run/attempt authority is required before queue work', async () => {
  const quota = await execute({bootstrapReject: true});assert.deepEqual(quota.waits, []);assert.equal(quota.calls.length, 1);
  assert.equal(quota.result.result.api_error.retry_after, '180');assert.equal(quota.result.request_accounting.actual_http_attempts, 1);
  for (const editJobs of [
    x => ({...x, total_count: 2}), x => ({...x, total_count: 101}),
    x => ({total_count: 2, jobs: [x.jobs[0], {...x.jobs[0], id: 21}]}),
    x => ({...x, jobs: [{...x.jobs[0], run_id: 11}]}),
    x => ({...x, jobs: [{...x.jobs[0], run_attempt: 2}]}),
    x => ({...x, jobs: [{...x.jobs[0], name: 'other-job'}]}),
    x => ({...x, jobs: [{...x.jobs[0], status: 'completed'}]}),
    x => ({...x, jobs: [{...x.jobs[0], started_at: '2026-02-30T00:00:00Z'}]}),
    x => ({...x, jobs: [{...x.jobs[0], started_at: new Date(epoch + 60_000).toISOString()}]})]) {
    const x = await execute({editJobs});assert.equal(x.result.failed, true);assert.equal(x.calls.length, 1);assert.equal(x.posted.length, 0);
  }
});

test('scheduler capacity refusal stays distinct and consumes no dispatch attempt', async () => {
  const x = await execute({phase: 'schedule'});assert.equal(x.result.failed, false);
  assert.equal(x.result.job_deadline.timeout_minutes, 10);assert.equal(x.result.result.status, 'waiting-quota');
  assert.equal(x.calls.length, 2);assert.equal(x.posted.length, 0);
});

test('a quota wait during actual scheduling cannot backdate a new dispatch/recovery discovery window', async () => {
  const x = await execute({phase: 'schedule', elapsed: 10_000, dispatchAfterQuota: true});
  assert.equal(x.result.failed, false);assert.equal(x.result.result.status, 'dispatched');
  assert.deepEqual(x.waits, [6000]);assert.equal(x.result.result.request_id, request.request_id);
  const dispatch = JSON.parse(x.posted[0].body.match(/<!-- worldatlas-merge-queue:v1\n([\s\S]*?)\n-->/)[1]);
  const posting = x.calls.find(row => row.method === 'POST' && row.route.endsWith('/comments'));
  assert.equal(dispatch.dispatched_at, new Date(epoch + posting.at).toISOString());
  assert.equal(dispatch.dispatched_at, new Date(epoch + 16_000).toISOString());
  assert.equal(dispatch.attempt, 1);assert.equal(x.posted.length, 2);
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

test('actual CLI emits a controlled quota refusal and accounting with failing exit status before registration can advance', () => {
  const directory = fs.mkdtempSync(path.join(process.cwd(), '.deadline-cli-'));
  try {
    fs.writeFileSync(path.join(directory, 'event.json'), JSON.stringify(event));
    fs.writeFileSync(path.join(directory, 'mock.mjs'), `
      import fs from 'node:fs';import {performance} from 'node:perf_hooks';
      const epoch=${epoch};let time=10000,reads=0;const calls=[],waits=[];
      Date.now=()=>epoch+time;Object.defineProperty(performance,'now',{value:()=>time});
      globalThis.setTimeout=(fn,ms)=>{time+=ms;waits.push(ms);queueMicrotask(fn);};
      globalThis.fetch=async(url,options)=>{const route=new URL(url).pathname;calls.push({route,method:options.method});
        if(route.endsWith('/attempts/1/jobs'))return new Response(JSON.stringify({total_count:1,jobs:[{id:20,name:'register',run_id:10,run_attempt:1,status:'in_progress',started_at:new Date(epoch).toISOString()}]}));
        if(route.endsWith('/pulls/2')){reads++;return new Response('{}',{status:403,headers:{'retry-after':'180'}});}
        throw Error('Forbidden unexpected request');
      };
      process.on('exit',()=>fs.writeFileSync(${JSON.stringify(path.join(directory, 'trace.json'))},JSON.stringify({calls,waits,time,reads})));
    `);
    const child = spawnSync(process.execPath, ['--import', path.join(directory, 'mock.mjs'),
      path.resolve('scripts/run-merge-scheduler.mjs')], {cwd: directory, encoding: 'utf8', timeout: 10_000,
      env: {PATH: process.env.PATH, GH_TOKEN: 'synthetic-test-token', GITHUB_REF: 'refs/heads/main',
        GITHUB_WORKFLOW_SHA: execFileSync('git', ['rev-parse', 'HEAD'], {encoding: 'utf8'}).trim(), GITHUB_WORKFLOW_REF: workflowRef,
        GITHUB_REPOSITORY: 'a/b', GITHUB_RUN_ID: '10', GITHUB_RUN_ATTEMPT: '1', GITHUB_JOB: 'register',
        QUEUE_PHASE: 'register', GITHUB_EVENT_PATH: path.join(directory, 'event.json')}});
    assert.equal(child.status, 1, child.stderr);
    const rows = child.stdout.trim().split('\n').map(row => JSON.parse(row));
    assert.equal(rows[0].status, 'refused');assert.equal(rows[0].request_id, request.request_id);
    assert.equal(rows[0].job_deadline_exhausted, true);assert.equal(rows[0].api_error.retry_after, '180');
    assert.equal(rows[2].request_accounting.actual_http_attempts, 3);
    const trace = JSON.parse(fs.readFileSync(path.join(directory, 'trace.json')));
    assert.deepEqual(trace.waits, [181_000]);assert.equal(trace.time, 191_000);
    assert.equal(trace.calls.filter(row => row.method === 'POST').length, 0);
  } finally {fs.rmSync(directory, {recursive: true, force: true});}
});


test('executing workflow commit rejects newer-main timeout and mixed-vintage checkout before HTTP', async () => {
  const env = {GH_TOKEN: 'synthetic', GITHUB_REF: 'refs/heads/main', GITHUB_REPOSITORY: 'a/b',
    QUEUE_PHASE: 'register', GITHUB_JOB: 'register', GITHUB_RUN_ID: '10', GITHUB_RUN_ATTEMPT: '1',
    GITHUB_WORKFLOW_SHA: workflowSha, GITHUB_WORKFLOW_REF: workflowRef};
  let requests = 0;
  const apiFactory = () => async () => {requests++;throw Error('HTTP must not execute');};
  const drift = await runScheduler({event, env, readGit, apiFactory,
    workflow: workflow.replace('timeout-minutes: 5', 'timeout-minutes: 10')});
  assert.equal(drift.failed, true);assert.match(drift.result.reason, /differ from executing commit/);
  const mixed = await runScheduler({event, env, apiFactory,
    readGit: args => args[0] === 'rev-parse' ? 'c'.repeat(40) : workflow});
  assert.equal(mixed.failed, true);assert.match(mixed.result.reason, /Checkout does not match/);
  for (const invalid of [{GITHUB_WORKFLOW_SHA: undefined}, {GITHUB_WORKFLOW_SHA: 'main'},
    {GITHUB_WORKFLOW_REF: 'a/b/.github/workflows/other.yml@refs/heads/main'},
    {GITHUB_WORKFLOW_REF: workflowRef.replace('main', 'untrusted')}]) {
    assert.throws(() => executingWorkflow({...env, ...invalid}, readGit), /authority/);
  }
  assert.equal(requests, 0);
  assert.match(workflow, /ref: \$\{\{ github.workflow_sha \}\}/);
  assert.doesNotMatch(workflow, /ref: main/);
  assert.equal(schedulerJobMinutes(executingWorkflow(env, readGit), 'register'), 5);
});
