import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import {checkPRGates, runPRGates} from '../scripts/check-pr-gates.mjs';
import {githubAPI} from '../scripts/issue-claim-contract.mjs';
import {requestAccounting} from '../scripts/github-quota.mjs';
import {loadPackageInputs} from '../scripts/package-inputs.mjs';
import {checkPREvidence} from '../scripts/check-pr-evidence.mjs';
import {checkLinkedIssue} from '../scripts/check-linked-github-issue.mjs';
import {selectIntegrationProfile} from '../scripts/check-integration-profile.mjs';
import {deploymentBudgetProfile} from '../scripts/classify-deployment-budget.mjs';

function fixture(lane = 'engineering') {
  const repo = 'owner/repo', root = `/repos/${repo}`, branch = lane + '/bounded-job';
  const spec = {max_prs: 2, depends_on: [], mode: lane === 'research' ? 'source-only' : lane, scope: 'Inspect the retained bounded inputs',
    ...(lane === 'geography' ? {owned_paths: ['research/geography/bounded-job/']} : {})};
  const issue = {number: 10, state: 'open', created_at: '2020-01-01T00:00:00Z',
    labels: ['type:' + (lane === 'research' ? 'history-research' : lane), 'kind:work-item', 'status:ready'],
    body: '<!-- worldatlas-work:v1\n' + JSON.stringify(spec) + '\n-->'};
  const claim = {version: 1, active: true, issue_number: 10, worker_id: 'author', claim_id: 'unique-claim',
    branch, mode: spec.mode, expires_at: '2099-01-01T00:00:00Z', ...(spec.owned_paths ? {owned_paths: spec.owned_paths} : {})};
  const pr = {number: 20, state: 'open', changed_files: 1, body: 'Refs #10',
    head: {sha: 'a'.repeat(40), ref: branch, repo: {full_name: repo}},
    base: {sha: 'b'.repeat(40), ref: 'main', repo: {full_name: repo}}};
  const files = [{filename: lane === 'geography' ? spec.owned_paths[0] + 'sources.json' :
    lane === 'research' ? 'research/campaigns/bounded-job/sources.json' : 'docs/WORKER_COORDINATION.md', status: 'modified'}];
  const raw = Buffer.from(JSON.stringify(loadPackageInputs()));
  const definition = {type: 'file', path: '.github/package-inputs.json', encoding: 'base64', size: raw.length,
    sha: createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex'), content: raw.toString('base64')};
  const f = {repo, root, pr, issue, claim, files, definition, event: {repository: {full_name: repo}, pull_request: structuredClone(pr)}, calls: [], hooks: {}, timeline: []};
  f.api = async route => {
    f.calls.push(route); await f.hooks[route]?.();
    if (route === root + '/pulls/20') return structuredClone(pr);
    if (route === root + '/pulls/20/files?per_page=100&page=1') return structuredClone(files);
    if (route === root + '/issues/10') return structuredClone(issue);
    if (route === root + '/issues/10/comments?per_page=100&page=1') return [{id: 1, user: {login: 'github-actions[bot]'},
      body: '**Worker reservation:** claimed\n\n<!-- worldatlas-claim:v1\n' + JSON.stringify(claim) + '\n-->'},
      ...(f.progress ? [{id: 2, body: f.progress, user: {login: 'author'}}] : [])];
    if (route === root + '/issues/10/timeline?per_page=100&page=1') return structuredClone(f.timeline);
    if (route === root + '/pulls/19') return {number: 19, merged_at: '2026-10-01T00:00:00Z'};
    if (route === root + '/contents/.github/package-inputs.json?ref=' + pr.base.sha) return structuredClone(f.definition);
    throw Error('Unexpected fixture route ' + route);
  };
  f.definitionRoute = root + '/contents/.github/package-inputs.json?ref=' + pr.base.sha;
  f.run = () => checkPRGates({event: f.event, repo, token: 'fixture', api: f.api});
  return f;
}
for (const lane of ['engineering', 'geography', 'research']) test(`real composed gates retain ${lane} focused selection without factual approval`, async () => {
  const f = fixture(lane), result = await f.run();
  assert.equal(result.status, 'checked'); assert.equal(result.profile, 'evidence');
  assert.deepEqual(result.shards, [0]); assert.equal(result.package.full, false);
  assert.equal(result.evidence.status, 'legacy-or-report-only');
  assert.deepEqual(result.owned_paths, f.claim.owned_paths ?? []);
});
test('new required evidence cannot succeed using the legacy fixture', async () => {
  const f = fixture(); f.issue.created_at = '2026-10-08T00:00:00Z';
  await assert.rejects(f.run(), /evidence|Evidence|quality|subjects/i);
});
for (const [name, change] of [
  ['code head', f => {f.pr.head.sha = 'c'.repeat(40);}],
  ['contract', f => {f.issue.body = f.issue.body.replace('retained bounded', 'different bounded');}],
  ['disposition', f => {f.pr.body = 'Closes #10';}],
  ['ownership', f => {f.claim.worker_id = 'another-worker';}],
  ['ready label', f => {f.issue.labels.push('status:blocked');}],
  ['PR allowance', f => {f.timeline = [{source: {issue: {number: 19, body: 'Refs #10', pull_request: {}}}}]; f.issue.body = f.issue.body.replace('"max_prs":2', '"max_prs":1');}]
]) test(`${name} change during byte/selection work prevents a coherent success`, async () => {
  const f = fixture();
  f.hooks[f.definitionRoute] = () => change(f);
  await assert.rejects(f.run());
});
test('ordinary progress and same-holder renewal do not invalidate disposition', async () => {
  const f = fixture();
  f.hooks[f.definitionRoute] = () => {f.progress = 'Still checking the same evidence'; f.claim.expires_at = '2099-02-01T00:00:00Z';};
  assert.equal((await f.run()).status, 'checked');
});
test('authenticated conditional reads reduce paid repeats while changed authority is still read', async () => {
  const f = fixture(), original = globalThis.fetch, accounting = requestAccounting('composed'), headersSeen = [];
  globalThis.fetch = async (url, options) => {
    const body = JSON.stringify(await f.api(new URL(url).pathname + new URL(url).search));
    const etag = '"' + createHash('sha256').update(body).digest('hex') + '"';
    headersSeen.push(options.headers.Authorization);
    return new Response(options.headers['If-None-Match'] === etag ? null : body,
      {status: options.headers['If-None-Match'] === etag ? 304 : 200, headers: {etag}});
  };
  try {
    const result = await checkPRGates({event: f.event, repo: f.repo, token: 'fixture', api: githubAPI('fixture', {onRequest: accounting.observe})});
    assert.equal(result.status, 'checked');
    const counts = accounting.receipt().counts;
    assert(Object.entries(counts).filter(([key]) => key.endsWith(':304')).reduce((sum, [, n]) => sum + n, 0) >= 4);
    assert(headersSeen.every(value => value === 'Bearer fixture'));
  } finally {globalThis.fetch = original;}
});
test('a failed real gate closes transport and cannot publish profile outputs', async () => {
  const f = fixture(); f.claim.active = false; let closed = false;
  const result = await runPRGates({event: f.event, env: {GH_TOKEN: 'fixture', GITHUB_REPOSITORY: f.repo},
    apiFactory: () => f.api, transportFactory: api => ({api, close() {closed = true;}})});
  assert(closed); assert.equal(result.status, 'incomplete-or-invalid'); assert.equal(result.profile, undefined);
});
test('incomplete and duplicate changed-file inventories cannot produce focused success', async () => {
  for (const duplicate of [false, true]) {
    const f = fixture();
    if (duplicate) {f.pr.changed_files = 2; f.files.push({...f.files[0]});}
    else f.files.length = 0;
    await assert.rejects(f.run(), /Incomplete changed-path inventory/);
  }
});
test('unavailable package definition retains conservative full verification', async () => {
  const f = fixture(); f.definition.sha = '0'.repeat(40);
  const result = await f.run();
  assert.equal(result.package.full, true); assert.equal(result.package.fallback, true);
});
test('a changed disposition is fetched through the real conditional client and rejected', async () => {
  const f = fixture(), original = globalThis.fetch; let changedReads = 0;
  f.hooks[f.definitionRoute] = () => {f.pr.body = 'Closes #10';};
  globalThis.fetch = async (url, options) => {
    const route = new URL(url).pathname + new URL(url).search;
    const body = JSON.stringify(await f.api(route));
    const etag = '"' + createHash('sha256').update(body).digest('hex') + '"';
    const unchanged = options.headers['If-None-Match'] === etag;
    if (route.endsWith('/pulls/20') && !unchanged && f.pr.body === 'Closes #10') changedReads++;
    return new Response(unchanged ? null : body, {status: unchanged ? 304 : 200, headers: {etag}});
  };
  try {
    await assert.rejects(checkPRGates({event: f.event, repo: f.repo, token: 'fixture', api: githubAPI('fixture')}), /disposition changed/);
    assert(changedReads > 0);
  } finally {globalThis.fetch = original;}
});

async function hosted({phase = 'all', elapsed = 0, editFile = file => file, editJobs = jobs => jobs, workflow = 'jobs:\n  profile:\n    timeout-minutes: 10\n'} = {}) {
  const f = fixture(), epoch = Date.parse('2026-10-08T00:00:00Z'), workflowSHA = 'd'.repeat(40);
  const raw = Buffer.from(workflow), calls = []; let constructed = false, options;
  const file = {type: 'file', path: '.github/workflows/merge-integration-checks.yml', encoding: 'base64',
    size: raw.length, sha: createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex'), content: raw.toString('base64')};
  const env = {GITHUB_ACTIONS: 'true', GITHUB_REPOSITORY: f.repo, GH_TOKEN: 'fixture',
    GITHUB_WORKFLOW_SHA: workflowSHA, GITHUB_WORKFLOW_REF: `${f.repo}/.github/workflows/merge-integration-checks.yml@refs/pull/20/merge`,
    GITHUB_JOB: phase === 'evidence' ? 'evidence' : 'profile', GITHUB_RUN_ID: '30', GITHUB_RUN_ATTEMPT: '2'};
  const result = await runPRGates({event: f.event, env, phase, wallNow: () => epoch + elapsed, monotonicNow: () => elapsed,
    apiFactory: (token, value) => {
      options = value;
      return async route => {
        calls.push(route);
        if (route.includes('/contents/.github/workflows/')) return editFile(structuredClone(file));
        if (route.endsWith('/actions/runs/30/attempts/2/jobs?per_page=100&page=1')) return editJobs({total_count: 1,
          jobs: [{id: 40, name: env.GITHUB_JOB, run_id: 30, run_attempt: 2, status: 'in_progress', started_at: new Date(epoch).toISOString()}]});
        return f.api(route);
      };
    }, transportFactory: api => {constructed = true; return {api, close() {}};}});
  return {result, calls, constructed, options};
}
test('hosted gate timing charges actual setup and retains runner finalization margin', async () => {
  const x = await hosted({elapsed: 360000});
  assert.equal(x.result.status, 'checked'); assert.equal(x.result.job_deadline.timeout_minutes, 10);
  assert.equal(x.options.deadlineRemaining(), 210000);
  assert(x.calls[0].endsWith('?ref=' + 'd'.repeat(40)));
  assert.equal(x.result.job_deadline.run_attempt, 2);
});
test('exhausted actual job refuses before Git transport or PR work', async () => {
  const x = await hosted({elapsed: 560000});
  assert.equal(x.result.status, 'incomplete-or-invalid'); assert.match(x.result.reason, /deadline exhausted/);
  assert.equal(x.constructed, false); assert.equal(x.calls.length, 2);
});
for (const [name, config] of [
  ['changed immutable workflow', {editFile: file => ({...file, sha: '0'.repeat(40)})}],
  ['missing literal budget', {workflow: 'jobs:\n  profile:\n    runs-on: ubuntu-latest\n'}],
  ['incomplete current job inventory', {editJobs: jobs => ({...jobs, total_count: 101})}],
  ['wrong run attempt', {editJobs: jobs => ({...jobs, jobs: [{...jobs.jobs[0], run_attempt: 1}]})}],
  ['ambiguous phase', {editJobs: jobs => ({total_count: 2, jobs: [jobs.jobs[0], {...jobs.jobs[0], id: 41}]})}]
]) test(`deadline refuses ${name} before expensive or mutable work`, async () => {
  const x = await hosted(config); assert.equal(x.result.status, 'incomplete-or-invalid'); assert.equal(x.constructed, false);
});

for (const lane of ['engineering', 'geography', 'research']) test(`metadata-only ${lane} selection does not allocate evidence transport`, async () => {
  const f = fixture(lane);
  const result = await runPRGates({event: f.event, env: {GH_TOKEN: 'fixture', GITHUB_REPOSITORY: f.repo},
    phase: 'metadata', apiFactory: () => f.api,
    transportFactory: () => {throw Error('Metadata must never allocate evidence transport');}});
  assert.equal(result.status, 'checked'); assert.equal(result.profile, 'evidence');
  assert.deepEqual(result.shards, [0]); assert.equal(result.package.full, false);
  assert.equal(result.evidence, undefined); assert.deepEqual(result.immutable_transport, []);
});
test('independent evidence phase verifies bytes without selecting or waiting for tests', async () => {
  const f = fixture(); let closed = false;
  const result = await runPRGates({event: f.event, env: {GH_TOKEN: 'fixture', GITHUB_REPOSITORY: f.repo},
    phase: 'evidence', apiFactory: () => f.api,
    transportFactory: api => ({api, close() {closed = true;}})});
  assert.equal(result.status, 'checked'); assert.equal(result.evidence.status, 'legacy-or-report-only');
  assert.equal(result.profile, undefined); assert.equal(result.package, undefined); assert(closed);
  assert(!f.calls.some(route => route.includes('/contents/.github/package-inputs.json')));
});
test('independent evidence rejects unmet required evidence and changed ownership', async () => {
  for (const change of ['required', 'ownership']) {
    const f = fixture();
    if (change === 'required') f.issue.created_at = '2026-10-08T00:00:00Z';
    else f.hooks[f.root + '/pulls/20/files?per_page=100&page=1'] = () => {f.claim.worker_id = 'changed-author';};
    await assert.rejects(checkPRGates({event: f.event, repo: f.repo, token: 'fixture', api: f.api, phase: 'evidence'}));
  }
});
test('workflow starts real evidence independently, preserves test parallelism and separates edited-event cancellation', () => {
  const source = fs.readFileSync('.github/workflows/merge-integration-checks.yml', 'utf8');
  const profile = source.slice(source.indexOf('  profile:'), source.indexOf('  evidence:'));
  const evidence = source.slice(source.indexOf('  evidence:'), source.indexOf('  scope:'));
  assert.match(profile, /PR_GATE_PHASE: metadata/);
  assert.doesNotMatch(profile, /node scripts\/check-pr-evidence.mjs/);
  assert.match(evidence, /PR_GATE_PHASE: evidence/);
  assert.match(evidence, /node scripts\/check-pr-gates.mjs/);
  assert.doesNotMatch(evidence, /needs:|Evidence was validated/);
  assert.match(evidence, /ref: \$\{\{ github.event.pull_request.base.sha \}\}/);
  for (const job of ['scope', 'geography', 'regression', 'package']) {
    const start = source.indexOf(`  ${job}:`);
    const remainder = source.slice(start);
    const next = remainder.slice(3).search(/\n  [a-z]+:/);
    const block = next === -1 ? remainder : remainder.slice(0, next + 3);
    assert.match(block, /needs: profile/);
    assert.doesNotMatch(block, /needs: evidence/);
  }
  assert.match(source, /\(github.event.action == 'edited' \|\| github.event.action == 'ready_for_review'\) && 'metadata' \|\| 'code'/);
});

test('parallel evidence phase binds its own actual job start and deadline', async () => {
  const x = await hosted({phase: 'evidence', elapsed: 360000,
    workflow: 'jobs:\n  profile:\n    timeout-minutes: 5\n  evidence:\n    timeout-minutes: 10\n'});
  assert.equal(x.result.status, 'checked'); assert.equal(x.result.job_deadline.phase, 'evidence');
  assert.equal(x.options.deadlineRemaining(), 210000); assert.equal(x.result.profile, undefined);
});

test('real split gates reduce paid metadata repeats against independent old readers', async t => {
  const original = globalThis.fetch;
  async function measure(split) {
    const f = fixture('geography'); let attempts = 0, paid = 0, revalidated = 0;
    globalThis.fetch = async (url, options) => {
      attempts++;
      const value = await f.api(new URL(url).pathname + new URL(url).search);
      const body = JSON.stringify(value), etag = '"' + createHash('sha256').update(body).digest('hex') + '"';
      const same = options.headers['If-None-Match'] === etag;
      if (same) revalidated++; else paid++;
      return new Response(same ? null : body, {status: same ? 304 : 200, headers: {etag}});
    };
    const api = () => githubAPI('fixture');
    if (split) {
      await Promise.all([
        checkPRGates({event: f.event, repo: f.repo, token: 'fixture', api: api(), phase: 'metadata'}),
        checkPRGates({event: f.event, repo: f.repo, token: 'fixture', api: api(), phase: 'evidence'})
      ]);
    } else {
      await Promise.all([
        checkPREvidence({event: f.event, api: api()}),
        checkLinkedIssue({branch: f.pr.head.ref, event: f.event, token: 'fixture', api: api(), checkClaim: true}),
        selectIntegrationProfile({event: f.event, repo: f.repo, api: api()}),
        deploymentBudgetProfile({event: f.event, eventName: 'pull_request', repository: f.repo, api: api()})
      ]);
    }
    return {attempts, paid, revalidated};
  }
  try {
    const old = await measure(false), split = await measure(true);
    t.diagnostic(JSON.stringify({fixture_only: true, old, split}));
    assert(split.paid < old.paid, 'Consolidation must earn its additional reconciliation reads');
    assert(split.attempts <= old.attempts + 4, 'Only the independent final authority passes may add requests');
  } finally {globalThis.fetch = original;}
});

// Evaluate the actual workflow predicates for every declared PR event rather
// than asserting only that a desired substring exists in the configuration.
test('metadata-only draft readiness preserves code work and cannot replace its tests', () => {
  const source = fs.readFileSync('.github/workflows/merge-integration-checks.yml', 'utf8');
  const events = source.match(/types: \[([^\]]+)\]/)[1].split(',').map(x=>x.trim());
  const groupLine = source.split('\n').find(line=>line.trim().startsWith('group:'));
  const expression = [...groupLine.matchAll(/\$\{\{ (.*?) \}\}/g)].at(-1)[1];
  const evaluate = (predicate, action) => Function('action', `return (${predicate.replaceAll('github.event.action','action')});`)(action);
  const groups = Object.fromEntries(events.map(action=>[action,evaluate(expression,action)]));
  assert.equal(groups.opened, 'code');assert.equal(groups.synchronize, 'code');assert.equal(groups.reopened, 'code');
  assert.equal(groups.edited, 'metadata');assert.equal(groups.ready_for_review, 'metadata');
  assert.notEqual(groups.opened,groups.ready_for_review,'readiness must not cancel an unfinished opening run');
  for (const name of ['geography','regression','package']) {
    const start=source.indexOf(`  ${name}:`), tail=source.slice(start), next=tail.slice(3).search(/\n  [a-z]+:/);
    const block=next<0?tail:tail.slice(0,next+3), predicate=block.match(/^    if: (.+)$/m)[1];
    const active=predicate.replace("needs.profile.result == 'success' && ",'');
    for(const action of events)assert.equal(evaluate(active,action),!['edited','ready_for_review'].includes(action),`${name}/${action}`);
  }
  for(const name of ['profile','evidence','scope']) {
    const start=source.indexOf(`  ${name}:`),tail=source.slice(start),next=tail.slice(3).search(/\n  [a-z]+:/);
    const block=next<0?tail:tail.slice(0,next+3);assert.doesNotMatch(block,/^    if: /m,`${name} must refresh authority`);
  }
});
