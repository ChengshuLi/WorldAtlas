import test from 'node:test';
import assert from 'node:assert/strict';
import {runMergeQueueClient} from '../scripts/merge-queue-client.mjs';
import {queueBody} from '../scripts/merge-scheduler.mjs';
import {renderWorkerResult} from '../scripts/worker-result.mjs';

const head = 'a'.repeat(40), merge = 'f'.repeat(40), requestId = 'stable-client-request';
const request = {kind: 'request', pr_number: 2, expected_head: head, request_id: requestId};
const bot = (body, id = 1) => ({id, user: {login: 'github-actions[bot]'}, body});
const registered = () => [bot(queueBody(request))];
const receipt = (overrides = {}) => bot(renderWorkerResult('merge', {
  request_id: requestId, pr_number: 2, accepted: true, status: 'merged', retryable: false,
  merge_commit: merge, reviewed_head: head, ...overrides}), 2);
function harness(handler, overrides = {}) {
  let time = 0;
  const calls = [], waits = [], submissions = [], progress = [];
  return {calls, waits, submissions, progress,
    run: () => runMergeQueueClient({repo: 'owner/repo', number: 2, head, requestId,
      resuming: true, now: () => time, random: () => 0,
      sleep: async ms => {waits.push(ms); time += ms;},
      api: async (route, options) => {calls.push({route, time, timeout: options.timeoutMs}); return handler(route, calls, time);},
      submit: async value => {submissions.push(value);}, progress: value => progress.push(value), ...overrides})};
}
const pr = (merged = false) => ({state: merged ? 'closed' : 'open', head: {sha: head}, merged, merge_commit_sha: merged ? merge : null});
test('an hour waiting on a durable request uses only result reads after initial identity check', async () => {
  const h = harness(route => route.includes('/pulls/') ? pr() : registered());
  assert.equal((await h.run()).status, 'pending');
  assert.equal(h.submissions.length, 0);
  assert.equal(h.calls.filter(c => c.route.includes('/pulls/')).length, 1);
  assert.ok(h.calls.length <= 18, h.calls.length);
  assert.equal(h.progress.find(p => p.status === 'observation-ended').read_requests, h.calls.length);
  assert.deepEqual(h.waits.slice(0, 4), [60_000, 120_000, 240_000, 300_000]);
  assert.ok(!h.calls.some(c => c.route.includes('/actions/')));
});
test('successful receipt requires fresh actual merge, exact head and merge commit', async () => {
  let pulls = 0;
  const h = harness(route => route.includes('/pulls/') ? pr(++pulls > 1) : [...registered(), receipt()]);
  assert.equal((await h.run()).accepted, true);
  assert.equal(pulls, 2); assert.equal(h.submissions.length, 0);
});
test('a completed merge can be observed after the original chat disappears', async () => {
  const h = harness(route => route.includes('/pulls/') ? pr(true) : [...registered(), receipt()], {observeOnly: true});
  assert.equal((await h.run()).accepted, true); assert.equal(h.submissions.length, 0);
});
test('mismatched merge receipt never reports success', async () => {
  const h = harness(route => route.includes('/pulls/') ? pr(true) : [receipt({merge_commit: 'b'.repeat(40)})]);
  await assert.rejects(h.run(), /differs from actual/);
});
test('malformed accepted receipts cannot authorize success', async () => {
  for (const overrides of [{status: 'not-merged'}, {merge_commit: null}, {expected_head: 'b'.repeat(40)}, {reviewed_head: 'b'.repeat(40)}]) {
    const h = harness(route => route.includes('/pulls/') ? pr(true) : [receipt(overrides)]);
    await assert.rejects(h.run(), /Malformed or mismatched/);
  }
});
test('jitter never exceeds the five-minute cap and reads receive bounded timeouts', async () => {
  const h = harness(route => route.includes('/pulls/') ? pr() : registered(), {random: () => 1});
  assert.equal((await h.run()).status, 'pending');
  assert.ok(h.waits.every(ms => ms <= 300_000));
  assert.ok(h.calls.every(c => c.timeout > 0 && c.timeout <= 20_000));
});
test('a response arriving after the observation deadline cannot authorize another action', async () => {
  let time = 0, submitted = 0, reads = 0;
  const result = await runMergeQueueClient({repo: 'owner/repo', number: 2, head, requestId,
    now: () => time, timeoutMs: 100, api: async () => {reads++; time = 101; return pr();},
    submit: async () => {submitted++;}});
  assert.equal(result.status, 'pending'); assert.equal(submitted, 0); assert.equal(reads, 1);
});
test('rate limit during final verification cannot turn a receipt into confirmed success', async () => {
  let pulls = 0;
  const h = harness(route => {
    if (route.includes('/comments')) return [receipt()];
    if (++pulls === 2) throw Object.assign(Error('rate'), {github: {http_status: 403, rate_remaining: '0', rate_reset: '9000'}});
    return pr();
  });
  assert.equal((await h.run()).status, 'pending'); assert.equal(pulls, 2);
});
test('changed reviewed head stops before submission', async () => {
  const h = harness(() => ({...pr(), head: {sha: 'b'.repeat(40)}}));
  await assert.rejects(h.run(), /Head changed/); assert.equal(h.submissions.length, 0);
});
test('known rejection ends observation without submission', async () => {
  const h = harness(route => route.includes('/pulls/') ? pr() : [receipt({accepted: false, status: 'not-merged'})]);
  assert.equal((await h.run()).accepted, false); assert.equal(h.submissions.length, 0);
});
test('rate exhaustion pauses every read until the actual reset before continuing', async () => {
  let comments = 0;
  const h = harness(route => {
    if (route.includes('/pulls/')) return pr();
    if (++comments === 1) throw Object.assign(Error('rate'), {github: {http_status: 403, rate_remaining: '0', rate_reset: '600'}});
    return registered();
  }, {timeoutMs: 700_000});
  assert.equal((await h.run()).status, 'pending');
  assert.equal(h.waits[0], 602_000);
  assert.equal(h.calls[2].time, 602_000);
  assert.equal(h.submissions.length, 0);
});
test('secondary throttling honors retry-after and does not redispatch', async () => {
  let calls = 0;
  const h = harness(route => {
    if (++calls === 1) throw Object.assign(Error('limited'), {github: {http_status: 429, retry_after: '180'}});
    return route.includes('/pulls/') ? pr() : registered();
  }, {timeoutMs: 240_000});
  assert.equal((await h.run()).status, 'pending'); assert.equal(h.waits[0], 180_000);
  assert.equal(h.submissions.length, 0);
});
test('secondary retry-after does not wait for a non-exhausted primary reset', async () => {
  let attempts = 0;
  const h = harness(route => {
    if (++attempts === 1) throw Object.assign(Error('limited'), {github: {http_status: 403, rate_remaining: '50', rate_reset: '9000', retry_after: '120'}});
    return route.includes('/pulls/') ? pr() : registered();
  }, {timeoutMs: 200_000});
  assert.equal((await h.run()).status, 'pending'); assert.equal(h.waits[0], 120_000);
});
test('repeated body-only secondary throttles have a finite exponential retry budget', async () => {
  const h = harness(() => {throw Object.assign(Error('secondary'), {github: {http_status: 403, rate_remaining: '50', secondary_limit: true}});});
  await assert.rejects(h.run(), /three bounded retries/);
  assert.deepEqual(h.waits, [60_000, 120_000, 240_000]); assert.equal(h.calls.length, 4);
  assert.equal(h.submissions.length, 0);
});
test('a reset beyond observation deadline returns pending without additional requests', async () => {
  const h = harness(() => {throw Object.assign(Error('rate'), {github: {http_status: 403, rate_remaining: '0', rate_reset: '9000'}});});
  assert.equal((await h.run()).status, 'pending'); assert.equal(h.calls.length, 1); assert.equal(h.waits.length, 0);
});
test('ordinary permission denial is not disguised as a rate limit', async () => {
  const h = harness(() => {throw Object.assign(Error('forbidden'), {github: {http_status: 403, rate_remaining: '50'}});});
  await assert.rejects(h.run(), /forbidden/); assert.equal(h.waits.length, 0);
});
test('read-only observation never submits an absent request', async () => {
  const h = harness(route => route.includes('/pulls/') ? pr() : route.includes('/comments') ? [] : {workflow_runs: []}, {observeOnly: true, timeoutMs: 130_000});
  assert.equal((await h.run()).status, 'pending'); assert.equal(h.submissions.length, 0);
});
test('resuming an uncertain request never submits even without explicit read-only mode', async () => {
  const h = harness(route => route.includes('/pulls/') ? pr() : route.includes('/comments') ? [] : {workflow_runs: []}, {timeoutMs: 130_000});
  assert.equal((await h.run()).status, 'pending'); assert.equal(h.submissions.length, 0);
});
test('an existing registration workflow prevents duplicate dispatch and is latched', async () => {
  let workflowLists = 0, statusReads = 0;
  const h = harness(route => {
    if (route.includes('/pulls/')) return pr();
    if (route.includes('/comments')) return [];
    if (route.includes('/actions/workflows/')) {workflowLists++; return {workflow_runs: [{id: 9, display_title: `queue #2 ${requestId}`, status: 'in_progress'}]};}
    statusReads++; return {id: 9, status: 'completed', conclusion: 'success'};
  }, {timeoutMs: 700_000});
  assert.equal((await h.run()).status, 'pending');
  assert.equal(workflowLists, 1); assert.equal(statusReads, 1); assert.equal(h.submissions.length, 0);
});
test('registration discovered on a later complete page is resumed without submission', async () => {
  const h = harness(route => {
    if (route.includes('/pulls/')) return pr();
    if (route.includes('/comments')) return [];
    if (route.endsWith('&page=1')) return {workflow_runs: Array.from({length: 100}, () => ({display_title: 'other'}))};
    return {workflow_runs: [{id: 9, display_title: `queue #2 ${requestId}`, status: 'completed', conclusion: 'success'}]};
  }, {timeoutMs: 130_000});
  assert.equal((await h.run()).status, 'pending'); assert.equal(h.submissions.length, 0);
  assert.equal(h.calls.filter(c => c.route.includes('/actions/workflows/')).length, 2);
});
test('new submission happens once, then durable registration eliminates workflow checks', async () => {
  let comments = 0, submitted = 0, pulls = 0;
  const h = harness(route => route.includes('/pulls/') ? pr(++pulls > 1) : route.includes('/comments') ? (++comments === 1 ? [] : [...registered(), receipt()]) : {workflow_runs: []},
    {resuming: false, submit: async () => {submitted++;}});
  assert.equal((await h.run()).accepted, true);
  assert.equal(submitted, 1);
  assert.ok(!h.calls.some(c => c.route.includes('/actions/')));
});
test('uncertain submission is never automatically repeated', async () => {
  let submitted = 0;
  const h = harness(route => route.includes('/pulls/') ? pr() : [], {resuming: false,
    submit: async () => {submitted++; throw Error('uncertain dispatch');}});
  await assert.rejects(h.run(), /uncertain dispatch/); assert.equal(submitted, 1);
  assert.equal(h.progress.find(p => p.status === 'submitting').request_id, requestId);
});
test('fresh submission refuses an already registered pending request for the same reviewed head', async () => {
  const h = harness(route => route.includes('/pulls/') ? pr() : registered(), {resuming: false, requestId: 'different-new-request'});
  await assert.rejects(h.run(), /Existing request stable-client-request/); assert.equal(h.submissions.length, 0);
});
test('incomplete registration search fails without dispatching a duplicate', async () => {
  const h = harness(route => route.includes('/pulls/') ? pr() : route.includes('/comments') ? [] : {workflow_runs: Array.from({length: 100}, () => ({display_title: 'other'}))});
  await assert.rejects(h.run(), /Incomplete registration inventory/); assert.equal(h.submissions.length, 0);
});
test('failed registration remains explicit rather than silently resubmitting', async () => {
  const h = harness(route => route.includes('/pulls/') ? pr() : route.includes('/comments') ? [] : {workflow_runs: [{id: 9, display_title: `queue #2 ${requestId}`, status: 'completed', conclusion: 'failure'}]});
  await assert.rejects(h.run(), /inspect the same request/); assert.equal(h.submissions.length, 0);
});

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

function run(scenario, observe = false) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'worldatlas-queue-cli-'));
  const stateFile = path.join(directory, 'state.json'), clock = path.join(directory, 'clock.mjs');
  fs.writeFileSync(stateFile, JSON.stringify({scenario, calls: [], polls: 0, request: 'stable-client-request'}));
  fs.writeFileSync(clock, `const native=Date.now;let elapsed=0;Date.now=()=>native()+elapsed;globalThis.setTimeout=(f,ms)=>{elapsed+=ms;f();};`);
  fs.writeFileSync(path.join(directory, 'gh'), `#!${process.execPath}\n` + String.raw`
import fs from 'node:fs';
const file=process.env.WORLDATLAS_FAKE_GH_STATE,s=JSON.parse(fs.readFileSync(file)),args=process.argv.slice(2),route=args.at(-1);
s.calls.push(args);let result={},failure=false,headers='HTTP/2.0 200 OK\r\nContent-Type: application/json\r\n\r\n';
if(args[0]==='workflow') {s.request=args.find(x=>x.startsWith('request_id=')).slice(11);s.submitted=true;if(s.scenario==='uncertain')failure=true;}
else if(route.includes('/pulls/2')) result={state:s.finished?'closed':'open',head:{sha:'a'.repeat(40)},merged:!!s.finished,merge_commit_sha:s.finished?'f'.repeat(40):null};
else if(route.includes('/issues/2/comments')) {
 s.polls++;
 if(s.scenario==='permission'){failure=true;headers='HTTP/2.0 403 Forbidden\r\nX-Ratelimit-Remaining: 50\r\n\r\n';result={message:'Forbidden'};}
 else if(s.scenario==='rate'&&s.polls===1){failure=true;headers='HTTP/2.0 403 Forbidden\r\nX-Ratelimit-Remaining: 0\r\nX-Ratelimit-Reset: '+Math.floor(Date.now()/1000+180)+'\r\n\r\n';result={message:'Rate limit'};}
 else if(s.scenario==='secondary'&&s.polls===1){failure=true;headers='HTTP/2.0 403 Forbidden\r\nX-Ratelimit-Remaining: 50\r\n\r\n';result={message:'You have exceeded a secondary rate limit.'};}
 else if(s.scenario==='new'&&!s.submitted||s.scenario==='uncertain')result=[];
 else {
  result=[{id:1,user:{login:'github-actions[bot]'},body:'**Merge queue:** request\n\n<!-- worldatlas-merge-queue:v1\n'+JSON.stringify({kind:'request',request_id:s.request,pr_number:2,expected_head:'a'.repeat(40)})+'\n-->'}];
  if(s.scenario!=='timeout'&&(s.polls>1||s.scenario==='existing')){s.finished=true;result.push({id:2,user:{login:'github-actions[bot]'},body:'**Merge result:** accepted\n\n<!-- worldatlas-merge-result:v1\n'+JSON.stringify({request_id:s.request,pr_number:2,accepted:true,status:'merged',retryable:false,merge_commit:'f'.repeat(40)})+'\n-->'});}
 }
} else if(route.includes('/actions/workflows/'))result={workflow_runs:[]};
else throw Error('Unexpected route '+route);
fs.writeFileSync(file,JSON.stringify(s));if(args[0]==='api')console.log(headers+JSON.stringify(result));if(failure)process.exitCode=1;
`, {mode: 0o700});
  try {
    const args = ['--import', clock, path.resolve(import.meta.dirname, '../scripts/queue-pr-merge.mjs'), '--pr', '2', '--head', 'a'.repeat(40)];
    if (scenario !== 'new' && scenario !== 'uncertain') args.push('--request-id', 'stable-client-request');
    if (observe) args.push('--observe');
    const result = spawnSync(process.execPath, args, {cwd: path.resolve(import.meta.dirname, '..'), encoding: 'utf8', timeout: 30_000,
      env: {...process.env, PATH: directory + path.delimiter + process.env.PATH, WORLDATLAS_FAKE_GH_STATE: stateFile}});
    return {result, state: JSON.parse(fs.readFileSync(stateFile))};
  } finally {fs.rmSync(directory, {recursive: true, force: true});}
}
test('CLI read-only resume confirms actual merged receipt without a write', () => {
  const {result, state} = run('existing', true);
  assert.equal(result.status, 0, result.stderr);
  assert.ok(!state.calls.some(args => args[0] === 'workflow'));
  assert.doesNotMatch(result.stdout, /local_cleanup/);
});
test('CLI parses actual rate headers and recovers without resubmission', () => {
  const {result, state} = run('rate', true);
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /rate-limited/);
  assert.ok(!state.calls.some(args => args[0] === 'workflow'));
});
test('CLI recognizes explicit body-only secondary throttling without treating ordinary permission denial as throttling', () => {
  const {result, state} = run('secondary', true);
  assert.equal(result.status, 0, result.stderr); assert.match(result.stdout, /rate-limited/);
  assert.ok(!state.calls.some(args => args[0] === 'workflow'));
});
test('CLI prints request identity before uncertain submission and never repeats it', () => {
  const {result, state} = run('uncertain');
  assert.notEqual(result.status, 0);
  assert.equal(state.calls.filter(args => args[0] === 'workflow').length, 1);
  assert.match(result.stdout, /submitting/);
  assert.match(result.stdout, new RegExp(state.request));
});
test('CLI only claims registration after reading the durable request', () => {
  const {result, state} = run('new');
  assert.equal(result.status, 0, result.stderr);
  assert.equal(state.calls.filter(args => args[0] === 'workflow').length, 1);
  assert.match(result.stdout, /submitted/);
});
test('CLI ordinary permission errors stop without false rate-limit recovery', () => {
  const {result, state} = run('permission', true);
  assert.notEqual(result.status, 0);
  assert.doesNotMatch(result.stdout, /rate-limited/);
  assert.ok(!state.calls.some(args => args[0] === 'workflow'));
});
test('CLI waiting timeout returns pending, avoids cleanup and has bounded reads', () => {
  const {result, state} = run('timeout', true);
  assert.equal(result.status, 3, result.stderr);
  assert.match(result.stdout, /pending/);
  assert.doesNotMatch(result.stdout, /local_cleanup/);
  assert.ok(state.calls.length <= 18, state.calls.length);
});
