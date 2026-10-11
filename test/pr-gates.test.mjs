import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import {checkPRGates, runPRGates} from '../scripts/check-pr-gates.mjs';
import {githubAPI, verifyClaimForPR} from '../scripts/issue-claim-contract.mjs';
import {integrationProfile} from '../scripts/integration-profile.mjs';
import {PROOF_PATHS, WORKFLOW_PATH} from '../scripts/integration-proof.mjs';
import {requestAccounting} from '../scripts/github-quota.mjs';
import {loadPackageInputs} from '../scripts/package-inputs.mjs';
import {checkPREvidence} from '../scripts/check-pr-evidence.mjs';
import {checkLinkedIssue} from '../scripts/check-linked-github-issue.mjs';
import {selectIntegrationProfile} from '../scripts/check-integration-profile.mjs';
import {deploymentBudgetProfile} from '../scripts/classify-deployment-budget.mjs';
import {reviewContractBinding} from '../scripts/premerge-evidence.mjs';
import {inspectMerge, prepareIntegration, completeIntegration} from '../scripts/merge-integration.mjs';

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
test('composed evidence keeps bulk transport, authenticates bytes and rechecks mutable authority', async () => {
  const exercise = async altered => {
    const f = fixture(), manifestPath = 'coordination/engineering/bounded-job/evidence-quality.json';
    const outputPath = 'coordination/engineering/bounded-job/result.json';
    const baseline = Buffer.from('independent original\n'), output = Buffer.from('{"valid":true}\n');
    const digest = raw => createHash('sha256').update(raw).digest('hex');
    const descriptor = (path, raw) => ({path, bytes: raw.length, sha256: digest(raw), hash_kind: 'file-bytes'});
    const spec = JSON.parse(f.issue.body.match(/\n(.+)\n/)[1]);
    spec.evidence_quality = {version: 1, manifest_path: manifestPath, subject_ids: [], pins: {}, review_kind: 'code'};
    f.issue.created_at = '2026-10-09T00:00:00Z';
    f.issue.body = '<!-- worldatlas-work:v1\n' + JSON.stringify(spec) + '\n-->';
    f.files.splice(0, f.files.length, {filename: outputPath, status: 'added'}, {filename: manifestPath, status: 'added'});
    f.pr.changed_files = 2;
    const manifest = {version: 1, issue: 10, lane: 'engineering', worker_id: 'author', subject_ids: [],
      subject_ids_sha256: digest('[]'), baseline: {commit: f.pr.base.sha, files: [descriptor('baseline.txt', baseline)], pins: {}},
      sources: [], outputs: [descriptor(outputPath, output)], methods: [{id: 'control', kind: 'code',
        description: 'Independent whole-byte control', software: 'Node 24', units: 'bytes'}], metrics: [], summaries: [],
      conclusions: [], stages: {research: 'complete', implementation: 'implemented', geographic_approval: 'not-requested'},
      commands: ['node --test test/pr-gates.test.mjs'], change_receipts: structuredClone(f.files).map(x => ({path: x.filename, status: x.status})),
      metric_bindings: []};
    const blobs = new Map(), row = (path, raw) => {
      const sha = createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
      blobs.set(sha, raw); return {path, sha, size: raw.length, type: 'blob', mode: '100644'};
    };
    const original = row('baseline.txt', baseline), result = row(outputPath, output), declaration = row(manifestPath, Buffer.from(JSON.stringify(manifest)));
    const known = new Set(); let paidBlobs = 0, batches = 0;
    const authority = f.api;
    const api = async route => {
      if (route.startsWith(f.root + '/git/commits/')) return {tree: {sha: route.endsWith(f.pr.head.sha) ? 'c'.repeat(40) : 'd'.repeat(40)}};
      if (route.startsWith(f.root + '/git/trees/')) return {truncated: false, tree: route.includes('c'.repeat(40)) ? [declaration, result] : [original]};
      if (route.startsWith(f.root + '/compare/')) return {status: 'identical'};
      if (route.startsWith(f.root + '/git/blobs/')) {
        const sha = route.split('/').at(-1); if (!known.has(sha)) paidBlobs++;
        const raw = altered && sha === result.sha ? Buffer.from('{"valid":null}\n') : blobs.get(sha);
        return {sha, encoding: 'base64', content: raw.toString('base64')};
      }
      return authority(route);
    };
    api.prefetchGitBlobs = async (repo, rows) => {
      assert.equal(repo, f.repo); assert.equal(rows.length, 2); batches++;
      for (const r of rows) {assert.equal(blobs.get(r.sha).length, r.size); known.add(r.sha);}
    };
    const outcome = await runPRGates({event: f.event, env: {GITHUB_REPOSITORY: f.repo, GH_TOKEN: 'fixture'},
      phase: 'evidence', apiFactory: () => api, transportFactory: api => ({api, close() {}})});
    assert.equal(batches, 1); assert.equal(paidBlobs, 1, 'Only the initial manifest should use REST; declared bodies use bulk transport');
    if (altered) {assert.equal(outcome.status, 'incomplete-or-invalid'); assert.match(outcome.reason, /Incomplete Git blob bytes|hash|bytes/i);}
    else {assert.equal(outcome.status, 'checked'); assert.equal(outcome.evidence.change_files_checked, 2);
      assert(f.calls.filter(x => x === f.root + '/pulls/20').length >= 2, 'Fresh final PR authority is required');}
  };
  await exercise(false); await exercise(true);
});
for (const lane of ['engineering', 'geography', 'research']) test(`real composed gates retain ${lane} focused selection without factual approval`, async () => {
  const f = fixture(lane), result = await f.run();
  assert.equal(result.status, 'checked'); assert.equal(result.profile, 'evidence');
  assert.deepEqual(result.shards, [0]); assert.equal(result.package.full, false);
  assert.equal(result.evidence.status, 'legacy-or-report-only');
  assert.deepEqual(result.owned_paths, f.claim.owned_paths ?? []);
});
// A fresh branch can publish its original issue-owned evidence without
// restoring the historical branch whose name matches the retained prefix.
function ownedEngineeringFixture() {
  const f = fixture(), owned = 'coordination/engineering/retained-job/';
  const spec = JSON.parse(f.issue.body.match(/\n(.+)\n/)[1]);
  spec.owned_paths = [owned];
  f.issue.body = '<!-- worldatlas-work:v1\n' + JSON.stringify(spec) + '\n-->';
  f.files.splice(0, f.files.length, {filename: owned + 'vintages/next/source-handoff.json', status: 'added'});
  f.owned = owned;
  return f;
}
async function currentEngineeringReservation(f) {
  const comments = await f.api(f.root + '/issues/10/comments?per_page=100&page=1');
  return verifyClaimForPR({branch: f.pr.head.ref, issue: f.issue, comments});
}
test('actual PR selector and merge profile share the authenticated retained engineering prefix', async () => {
  const f = ownedEngineeringFixture();
  assert.equal(integrationProfile(f.pr.head.ref, f.files), 'full', 'No unverified ownership shortcut');
  const selected = await selectIntegrationProfile({event: f.event, repo: f.repo, api: f.api});
  assert.equal(selected.profile, 'evidence'); assert.deepEqual(selected.shards, [0]);
  const reservation = await currentEngineeringReservation(f);
  // prepareIntegration and completeIntegration both use this exact exported
  // classifier with their freshly authenticated reservation.
  assert.equal(integrationProfile(f.pr.head.ref, f.files, reservation), selected.profile);
  const state = await inspectMerge({repo: f.repo, number: f.pr.number, expectedHead: f.pr.head.sha,
    api: async route => {
      if (route === f.root + '/git/ref/heads/main') return {object: {sha: f.pr.base.sha}};
      if (route.startsWith(f.root + '/commits/') && route.includes('/check-runs'))
        return {check_runs: [{id: 1, name: 'scope', app: {id: 1}, status: 'completed', conclusion: 'success'}]};
      if (route.startsWith(f.root + '/commits/') && route.endsWith('/status')) return {statuses: []};
      return f.api(route);
    }, policy: {version: 1, mode: 'enforce-new', activation_time: '2100-01-01T00:00:00Z'},
    evidenceCheck: async () => ({status: 'legacy'})});
  assert.deepEqual(state.reservation, reservation);
  assert.equal(integrationProfile(state.pr.head.ref, state.files, state.reservation), 'evidence');
});
test('actual prepare and final merge reuse only successful focused proof for retained engineering ownership', async () => {
  const f = ownedEngineeringFixture(), candidate = 'c'.repeat(40), testedTree = 'd'.repeat(40), baseTree = 'e'.repeat(40);
  Object.assign(f.pr, {draft: false, mergeable: true, merge_commit_sha: candidate, title: 'Publish retained evidence'});
  const workflow = Buffer.from('ref: ${{ github.event.pull_request.head.sha }}\nname: Complete regression shard\nname: Build hosted assets');
  const workflowOID = createHash('sha1').update(`blob ${workflow.length}\0`).update(workflow).digest('hex');
  const authorityRows = PROOF_PATHS.map(name => ({path: name, sha: name === WORKFLOW_PATH ? workflowOID : 'f'.repeat(40), mode: '100644', type: 'blob'}));
  const rows = [...authorityRows, {path: f.files[0].filename, sha: '1'.repeat(40), mode: '100644', type: 'blob'}];
  const run = {id: 12, run_attempt: 1, head_sha: f.pr.head.sha, event: 'pull_request', path: WORKFLOW_PATH,
    repository: {full_name: f.repo}, head_repository: {full_name: f.repo}, status: 'completed', conclusion: 'success',
    pull_requests: [{number: f.pr.number, head: {sha: f.pr.head.sha}}]};
  const jobs = [{name: 'profile', status: 'completed', conclusion: 'success'},
    {name: 'regression (0)', status: 'completed', conclusion: 'success', steps: [
      'Checkout reviewed head', 'Install browser dependencies only for tests that use Playwright', 'Complete regression shard'
    ].map(name => ({name, status: 'completed', conclusion: 'success'}))}];
  const writes = [], options = {repo: f.repo, number: f.pr.number, expectedHead: f.pr.head.sha,
    candidateSleep: async () => {}, policy: {version: 1, mode: 'enforce-new', activation_time: '2100-01-01T00:00:00Z'},
    evidenceCheck: async () => ({status: 'legacy'}), api: async (route, method = 'GET', body) => {
      if (method !== 'GET') {assert.equal(method, 'PUT');writes.push(body);return {merged: true, sha: '2'.repeat(40)};}
      if (route === f.root + '/git/ref/heads/main') return {object: {sha: f.pr.base.sha}};
      if (route.startsWith(f.root + '/commits/') && route.includes('/check-runs'))
        return {check_runs: [{id: 1, name: 'scope', app: {id: 1}, status: 'completed', conclusion: 'success'}]};
      if (route.startsWith(f.root + '/commits/') && route.endsWith('/status')) return {statuses: []};
      if (route === f.root + '/git/commits/' + candidate) return {tree: {sha: testedTree}, parents: [{sha: f.pr.base.sha}, {sha: f.pr.head.sha}]};
      if (route === f.root + '/git/commits/' + f.pr.head.sha) return {tree: {sha: testedTree}};
      if (route === f.root + '/git/commits/' + f.pr.base.sha) return {tree: {sha: baseTree}};
      if (route.startsWith(f.root + '/git/trees/')) return {truncated: false, tree: route.includes(baseTree) ? authorityRows : rows};
      if (route === f.root + '/git/blobs/' + workflowOID) return {sha: workflowOID, size: workflow.length, encoding: 'base64', content: workflow.toString('base64')};
      if (route.includes('/actions/workflows/')) return {workflow_runs: [run]};
      if (route.endsWith('/actions/runs/12')) return run;
      if (route.includes('/actions/runs/12/attempts/1/jobs')) return {jobs};
      return f.api(route);
    }};
  const prepared = await prepareIntegration(options);
  assert.equal(prepared.profile, 'evidence');assert.equal(prepared.proof.profile, 'evidence');
  assert.equal(prepared.proof.run_id, 12);assert.equal(writes.length, 0);
  const complete = () => completeIntegration({...options, integrationResult: 'skipped', geographyResult: 'success',
    testedBase: f.pr.base.sha, testedCandidate: candidate, proofRunId: 12, proofRunAttempt: 1,
    geographyReportLoader: async () => ({version: 1, method_id: 'worldatlas-trusted-geography-check-v1',
      baseline_commit: f.pr.base.sha, trusted_code_commit: f.pr.base.sha, candidate_commit: candidate,
      candidate_code_executed: false, published: false, source_approval: false, gate_status: 'passed', status: 'not-applicable'})});
  jobs[1].conclusion = 'failure';
  await assert.rejects(complete(), /proof is no longer valid/);assert.equal(writes.length, 0);
  jobs[1].conclusion = 'success';
  const result = await complete();assert.equal(result.accepted, true);assert.equal(result.proof.profile, 'evidence');
  assert.equal(writes.length, 1);assert.equal(writes[0].sha, f.pr.head.sha);
});

test('actual composed engineering gates reuse captured claim reads and keep package classification independent', async () => {
  const f = ownedEngineeringFixture();
  const result = await checkPRGates({event: f.event, repo: f.repo, token: 'fixture', api: f.api, phase: 'metadata'});
  assert.equal(result.profile, 'evidence'); assert.equal(result.package.full, false);
  assert.deepEqual(result.owned_paths, [f.owned]);
  assert.equal(f.calls.filter(route => route === f.root + '/issues/10').length, 2, 'One captured pass plus final fresh reconciliation');
  assert.equal(f.calls.filter(route => route === f.root + '/issues/10/comments?per_page=100&page=1').length, 2);
  f.files.push({filename: 'src/attributes.js', status: 'modified'});f.pr.changed_files++;
  const full = await checkPRGates({event: f.event, repo: f.repo, token: 'fixture', api: f.api, phase: 'metadata'});
  assert.equal(full.profile, 'full'); assert.equal(full.package.full, true);
});
for (const [name, mutate] of [
  ['expired', f => {f.claim.expires_at = '2020-01-01T00:00:00Z';}],
  ['inactive', f => {f.claim.active = false;}],
  ['wrong branch', f => {f.claim.branch = 'engineering/retained-job';}],
  ['not ready', f => {f.issue.labels = f.issue.labels.filter(x => x !== 'status:ready');}],
  ['blocked', f => {f.issue.labels.push('status:blocked');}],
  ['wrong issue type', f => {f.issue.labels[0] = 'type:geography';}],
  ['wrong scope mode', f => {f.issue.body = f.issue.body.replace('"mode":"engineering"', '"mode":"geography"');}],
  ['unsafe scope', f => {f.issue.body = f.issue.body.replace('coordination/engineering/retained-job/', 'coordination/engineering/../');}]
]) test(`actual retained-prefix PR selection rejects ${name} ownership`, async () => {
  const f = ownedEngineeringFixture();mutate(f);
  await assert.rejects(selectIntegrationProfile({event: f.event, repo: f.repo, api: f.api}));
});
test('retained-prefix classification does not accept namespace roots, exact files, foreign files or rename origins', async () => {
  const f = ownedEngineeringFixture(), reservation = await currentEngineeringReservation(f);
  for (const grant of ['coordination/engineering/', 'coordination/', 'src/', 'data/', '.github/',
    f.files[0].filename, f.owned + '../', f.owned + './', f.owned.slice(0, -1)])
    assert.equal(integrationProfile(f.pr.head.ref, f.files, {...reservation, owned_paths: [grant]}), 'full', grant);
  for (const value of [{}, {...reservation, mode: 'geography'}, {...reservation, owned_paths: []}])
    assert.equal(integrationProfile(f.pr.head.ref, f.files, value), 'full');
  for (const name of ['coordination/engineering/retained-job-other/result.json', 'coordination/engineering/foreign/result.json',
    'src/attributes.js', 'data/ownership-selection.json', '.github/workflows/arbitrary.yml']) {
    const files = [{filename: name, status: 'added'}];
    assert.equal(integrationProfile(f.pr.head.ref, files, reservation), 'full', name);
    assert.equal(integrationProfile(f.pr.head.ref, [{...f.files[0], status: 'renamed', previous_filename: name}], reservation), 'full', name);
  }
});
test('new retained-prefix exception cannot downgrade the actual selected scientific reader', async () => {
  const f = ownedEngineeringFixture(), prefix = 'coordination/engineering/selected-geography-effective-prevention-20261009/';
  f.issue.body = f.issue.body.replace(f.owned, prefix);
  f.files[0] = {filename: prefix + 'selected-neighbor-prevention.mjs', status: 'modified'};
  const reservation = await currentEngineeringReservation(f);
  assert.equal(reservation.mode, 'engineering');assert.deepEqual(reservation.owned_paths, [prefix]);
  assert.equal(integrationProfile(f.pr.head.ref, f.files, reservation), 'full');
  assert.equal((await selectIntegrationProfile({event: f.event, repo: f.repo, api: f.api})).profile, 'full');
});
test('new retained-prefix exception accepts additions and only the exact evidence manifest modification', async () => {
  const f = ownedEngineeringFixture(), reservation = await currentEngineeringReservation(f);
  const added = ['README.md', 'custody/build_handoff.py', 'custody/bind_current_neighbors.mjs',
    'vintages/components-005.jsonl.gz', 'vintages/source-handoff.json', 'logs/source.stderr']
    .map(name => ({filename: f.owned + name, status: 'added'}));
  assert.equal(integrationProfile(f.pr.head.ref, added, reservation), 'evidence');
  assert.equal(integrationProfile(f.pr.head.ref, [...added, {filename: f.owned + 'evidence-quality.json', status: 'modified'}], reservation), 'evidence');
  for (const filename of [f.owned + 'vintages/evidence-quality.json', f.owned + 'custody/build_handoff.py',
    f.owned + 'method.mjs', f.owned + 'package.json', f.owned + 'result.json']) {
    for (const status of ['modified', 'removed', 'renamed', 'copied', 'unknown'])
      assert.equal(integrationProfile(f.pr.head.ref, [{filename, status}], reservation), 'full', `${filename}/${status}`);
  }
  for (const status of ['removed', 'renamed', 'copied'])
    assert.equal(integrationProfile(f.pr.head.ref, [{filename: f.owned + 'evidence-quality.json', status}], reservation), 'full');
  assert.equal(integrationProfile(f.pr.head.ref, [{...added[0], previous_filename: f.owned + 'old.md'}], reservation), 'full');
  assert.equal(integrationProfile('engineering/retained-job', [{filename: f.owned + 'method.mjs', status: 'modified'}]), 'evidence',
    'Existing branch-aligned behavior is outside this narrow correction');
});
test('retained-prefix exception does not use old checked-out package roles after a PR base advance', async () => {
  const f = ownedEngineeringFixture();f.pr.base.sha = '9'.repeat(40);
  assert.notEqual(f.event.pull_request.base.sha, f.pr.base.sha);
  assert.equal((await selectIntegrationProfile({event: f.event, repo: f.repo, api: f.api})).profile, 'full');
});

test('new retained-prefix additions do not exempt package inputs, module configuration or unknown artifacts', async () => {
  const f = ownedEngineeringFixture(), reservation = await currentEngineeringReservation(f);
  for (const name of ['package.json', 'package-lock.json', 'npm-shrinkwrap.json', '__init__.py', 'sitecustomize.py', 'usercustomize.py',
    'requirements.txt', 'pyproject.toml', 'setup.py', 'setup.cfg', '.npmrc', '.pth', 'binding.node', 'plugin.so'])
    assert.equal(integrationProfile(f.pr.head.ref, [{filename: f.owned + 'custody/' + name, status: 'added'}], reservation), 'full', name);
  for (const mode of ['120000', '160000', '040000'])
    assert.equal(integrationProfile(f.pr.head.ref, [{filename: f.owned + 'new.py', status: 'added', mode}], reservation), 'full');
  const active = 'coordination/engineering/additive-native-activation-20261009/';
  const claimed = {...reservation, owned_paths: [active]};
  assert.equal(integrationProfile(f.pr.head.ref, [{filename: active + 'new-input.json', status: 'added'}], claimed), 'full',
    'Existing package directory grants remain active input authority');
  const selected = 'coordination/engineering/selected-geography-effective-prevention-20261009/';
  assert.equal(integrationProfile(f.pr.head.ref, [{filename: selected + 'selected-neighbor-prevention.mjs', status: 'added'}],
    {...reservation, owned_paths: [selected]}), 'full', 'Declared exact dependency cannot use a claimed-added status to waive full tests');
});

test('retained engineering scope changes during actual composed inspection still refuse', async () => {
  for (const mutate of [
    f => {f.claim.worker_id = 'another-worker';},
    f => {f.issue.body = f.issue.body.replace('retained-job/', 'foreign-job/');}
  ]) {
    const f = ownedEngineeringFixture();f.hooks[f.definitionRoute] = () => mutate(f);
    await assert.rejects(checkPRGates({event: f.event, repo: f.repo, token: 'fixture', api: f.api, phase: 'metadata'}));
  }
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
    assert.match(block, job === 'package' ? /needs: \[profile, regression\]/ : /needs: profile/);
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
test('draft readiness starts no duplicate run while code and edited events keep their actual gates', () => {
  const source = fs.readFileSync('.github/workflows/merge-integration-checks.yml', 'utf8');
  const events = source.match(/types: \[([^\]]+)\]/)[1].split(',').map(x=>x.trim());
  const groupLine = source.split('\n').find(line=>line.trim().startsWith('group:'));
  const expression = [...groupLine.matchAll(/\$\{\{ (.*?) \}\}/g)].at(-1)[1];
  const evaluate = (predicate, action, selection = 'complete', cancelled = false) => Function('action', 'selection', 'always', 'cancelled',
    `return (${predicate.replaceAll('github.event.action','action').replaceAll('needs.profile.outputs.test_selection','selection')});`)(action, selection, () => true, () => cancelled);
  const groups = Object.fromEntries(events.map(action=>[action,evaluate(expression,action)]));
  assert.equal(groups.opened, 'code');assert.equal(groups.synchronize, 'code');assert.equal(groups.reopened, 'code');
  assert.equal(groups.edited, 'metadata');
  assert.deepEqual(events, ['opened','synchronize','reopened','edited']);
  assert.equal(groups.ready_for_review, undefined, 'draft readiness changes no tested bytes or authority binding');
  assert.notEqual(groups.opened,groups.edited,'body edits must not cancel an unfinished code run');
  for (const name of ['geography','regression','package']) {
    const start=source.indexOf(`  ${name}:`), tail=source.slice(start), next=tail.slice(3).search(/\n  [a-z]+:/);
    const block=next<0?tail:tail.slice(0,next+3), predicate=block.match(/^    if: (.+)$/m)[1];
    const active=predicate.replace("needs.profile.result == 'success' && ",'');
    for(const action of events)assert.equal(evaluate(active,action),action !== 'edited',`${name}/${action}`);
    if(name==='package')for(const action of events)assert.equal(evaluate(active,action,'complete',true),false,'cancelled package never launches');
  }
  for(const name of ['profile','evidence','scope']) {
    const start=source.indexOf(`  ${name}:`),tail=source.slice(start),next=tail.slice(3).search(/\n  [a-z]+:/);
    const block=next<0?tail:tail.slice(0,next+3);assert.doesNotMatch(block,/^    if: /m,`${name} must refresh authority`);
  }
});

test('draft readiness preserves byte authority while both merge phases require current non-draft state', async () => {
  const f = fixture(); f.pr.draft = true;
  const binding = reviewContractBinding(f.issue, f.pr), draft = await f.run();
  f.pr.draft = false;
  assert.deepEqual(reviewContractBinding(f.issue, f.pr), binding);
  const ready = await f.run();
  assert.equal(ready.profile, draft.profile); assert.deepEqual(ready.shards, draft.shards);
  assert.notDeepEqual(reviewContractBinding(f.issue, {...f.pr, body: f.pr.body + '\nChanged disposition'}), binding);
  const original = f.api, options = {repo: f.repo, number: f.pr.number, expectedHead: f.pr.head.sha,
    policy: {version: 1, mode: 'enforce-new', activation_time: '2100-01-01T00:00:00Z'},
    evidenceCheck: async () => ({status: 'legacy'}),
    api: async (route, method = 'GET') => {
      assert.equal(method, 'GET', 'readiness must never substitute for a merge write gate');
      if (route === f.root + '/git/ref/heads/main') return {object: {sha: f.pr.base.sha}};
      if (route.startsWith(f.root + '/commits/') && route.includes('/check-runs'))
        return {check_runs: [{id: 1, name: 'scope', app: {id: 1}, status: 'completed', conclusion: 'success'}]};
      if (route.startsWith(f.root + '/commits/') && route.endsWith('/status')) return {statuses: []};
      return original(route);
    }};
  assert.equal((await inspectMerge(options)).pr.draft, false);
  f.pr.draft = true;
  await assert.rejects(prepareIntegration(options), /non-draft/);
  await assert.rejects(completeIntegration({...options, integrationResult: 'success', geographyResult: 'success',
    testedBase: f.pr.base.sha}), /non-draft/);
});

// Exercise the actual hosted entry and HTTP wrapper, including startup admission.
async function startup({phase = 'evidence', rows = [{status: 'queued', started_at: null}, {}],
  workflowMs = 0, jobMs = [], oversleep = 0, httpFailure, editInventory, rollback = false, staleConditional = false} = {}) {
  const f = fixture(), epoch = Date.parse('2026-10-11T00:00:00Z'), sha = 'd'.repeat(40);
  const workflow = Buffer.from('jobs:\n  profile:\n    timeout-minutes: 10\n  evidence:\n    timeout-minutes: 10\n');
  let time = 0, reads = 0, constructed = false, deadlineRemaining;
  const calls = [], waits = [], current = phase === 'evidence' ? 'evidence' : 'profile';
  const env = {GITHUB_ACTIONS: 'true', GITHUB_REPOSITORY: f.repo, GH_TOKEN: 'fixture',
    GITHUB_WORKFLOW_SHA: sha, GITHUB_WORKFLOW_REF: `${f.repo}/.github/workflows/merge-integration-checks.yml@refs/pull/20/merge`,
    GITHUB_JOB: current, GITHUB_RUN_ID: '30', GITHUB_RUN_ATTEMPT: '2'};
  const fetchImpl = async (url, options) => {
    assert.equal(new URL(url).origin, 'https://api.github.com');
    assert.equal(options.method, 'GET');
    const route = new URL(url).pathname + new URL(url).search;
    calls.push({route, at: time, conditional: options.headers['If-None-Match']});
    let payload;
    if (route.includes('/contents/.github/workflows/')) {
      time += workflowMs;
      payload = {type: 'file', path: '.github/workflows/merge-integration-checks.yml', encoding: 'base64',
        size: workflow.length, content: workflow.toString('base64'),
        sha: createHash('sha1').update(`blob ${workflow.length}\0`).update(workflow).digest('hex')};
    } else if (route.endsWith('/actions/runs/30/attempts/2/jobs?per_page=100&page=1')) {
      const i = reads++;time += jobMs[i] ?? 0;
      if (staleConditional && options.headers['If-None-Match']) return new Response(null, {status: 304});
      const failure = Array.isArray(httpFailure) ? httpFailure[i] : httpFailure;
      if (failure === 'transport') throw Error('synthetic transport refusal');
      if (failure) return new Response('{}', {status: failure, headers: {'retry-after': '1'}});
      const row = rows[Math.min(i, rows.length - 1)];
      payload = {total_count: row === null ? 0 : 1, jobs: row === null ? [] : [{
        id: 40, name: current, run_id: 30, run_attempt: 2, status: 'in_progress',
        started_at: new Date(epoch).toISOString(), ...row}]};
      payload = editInventory?.(payload, i) ?? payload;
    } else payload = await f.api(route);
    return new Response(JSON.stringify(payload), {status: 200, headers: staleConditional ? {etag: '"pending"'} : {}});
  };
  const result = await runPRGates({event: f.event, env, phase,
    wallNow: () => epoch + time, monotonicNow: () => time,
    sleep: async ms => {waits.push(ms);time += rollback ? -1 : ms + oversleep;},
    apiFactory: (token, options) => {deadlineRemaining = options.deadlineRemaining;return githubAPI(token, {...options, fetchImpl});},
    transportFactory: api => {constructed = true;return {api, close() {}};}});
  return {result, calls, waits, reads, time, constructed, inspected: f.calls, deadlineRemaining};
}

test('actual hosted evidence and profile recover pending same-job metadata before inspection', async () => {
  for (const phase of ['evidence', 'metadata']) {
    const x = await startup({phase});
    assert.equal(x.result.status, 'checked');assert.equal(x.reads, 2);assert.deepEqual(x.waits, [250]);
    assert.equal(x.result.job_deadline.job_id, 40);
    assert.equal(x.result.job_deadline.metadata_reads, 2);
    assert.equal(x.result.job_deadline.metadata_wait_ms, 250);
    assert.deepEqual(x.result.job_deadline.metadata_observations[0].mismatches, ['status', 'started_at']);
    assert.equal(x.result.job_deadline.metadata_observations[0].observed.started_at, null);
    assert.equal(x.deadlineRemaining(), 570000 - x.time);
    assert.equal(x.constructed, phase === 'evidence');assert.ok(x.inspected.length > 0);
    assert.ok(x.calls.slice(0, 3).every(row => /\/contents\/\.github\/workflows\/|\/attempts\/2\/jobs\?/.test(row.route)));
  }
});

test('actual startup recovers missing metadata and every pending state within three exact reads', async () => {
  for (const row of [null, {started_at: null}, {started_at: undefined}, {run_id: null, run_attempt: undefined},
    {status: null}, ...['queued', 'waiting', 'pending', 'requested'].map(status => ({status}))]) {
    const x = await startup({rows: [row, row, {}]});
    assert.equal(x.result.status, 'checked', JSON.stringify(row));assert.equal(x.reads, 3);
    assert.deepEqual(x.waits, [250, 750]);assert.equal(x.result.job_deadline.metadata_wait_ms, 1000);
    assert.equal(x.result.job_deadline.metadata_observations.length, 2);
    const paths = x.calls.filter(row => row.route.includes('/attempts/'));
    assert.equal(new Set(paths.map(row => row.route)).size, 1);assert.match(paths[0].route, /\/runs\/30\/attempts\/2\/jobs/);
    assert.equal(x.deadlineRemaining(), 569000);
  }
});

test('persistent pending startup remains failed and never constructs transport or inspects evidence', async () => {
  const x = await startup({rows: [{status: 'queued', started_at: null}]});
  assert.equal(x.result.status, 'incomplete-or-invalid');assert.equal(x.constructed, false);assert.deepEqual(x.inspected, []);
  assert.equal(x.reads, 8);assert.equal(x.calls.length, 9);assert.deepEqual(x.waits, [250, 750, 2000, 4000, 4000, 4000, 4000]);
  assert.deepEqual(x.result.deadline_binding.mismatches, ['status', 'started_at']);
  assert.equal(x.result.deadline_binding.metadata_reads, 8);assert.equal(x.result.deadline_binding.metadata_wait_ms, 19000);
  assert.equal(x.result.request_accounting.actual_http_attempts, 9);
});

test('explicit foreign identities, terminal states and malformed starts refuse without rereading', async () => {
  for (const [field, value] of [['run_id', 31], ['run_attempt', 1], ['run_id', '30'],
    ['status', 'completed'], ['status', 'injected-secret'], ['started_at', ''], ['started_at', 'injected-secret'],
    ['started_at', 17], ['started_at', {}], ['started_at', '2026-02-30T00:00:00Z'],
    ['started_at', '2026-10-11T00:00:01Z']]) {
    const x = await startup({rows: [{[field]: value}]});
    assert.equal(x.result.status, 'incomplete-or-invalid');assert.equal(x.reads, 1);assert.deepEqual(x.waits, []);
    assert.deepEqual(x.result.deadline_binding.mismatches, [field]);assert.deepEqual(x.inspected, []);
    assert.equal(x.constructed, false);assert.doesNotMatch(JSON.stringify(x.result), /injected-secret/);
  }
});

test('same-job startup pins the first ID and run identity rather than accepting a replacement', async () => {
  for (const [field, value] of [['id', 41], ['run_id', 31], ['run_attempt', 3]]) {
    const x = await startup({rows: [{status: 'queued'}, {[field]: value}]});
    assert.equal(x.result.status, 'incomplete-or-invalid');assert.equal(x.reads, 2);assert.deepEqual(x.waits, [250]);
    assert.deepEqual(x.result.deadline_binding.mismatches, [field === 'id' ? 'job_id' : field]);
    assert.equal(x.constructed, false);assert.deepEqual(x.inspected, []);
  }
});

test('ambiguous or incomplete startup inventories refuse before a metadata wait', async () => {
  for (const editInventory of [
    value => ({...value, total_count: 2}), value => ({...value, total_count: 101}),
    value => ({total_count: 2, jobs: [value.jobs[0], value.jobs[0]]}),
    value => ({total_count: 2, jobs: [value.jobs[0], {...value.jobs[0], id: 41}]}),
    value => ({total_count: 1, jobs: [null]})
  ]) {
    const x = await startup({editInventory});
    assert.equal(x.result.status, 'incomplete-or-invalid');assert.equal(x.reads, 1);assert.deepEqual(x.waits, []);
    assert.equal(x.constructed, false);assert.deepEqual(x.inspected, []);assert.ok(x.result.deadline_binding);
  }
});

test('same existing startup budget charges workflow time, slow reads and oversleep before any reread', async () => {
  for (const config of [{workflowMs: 20751}, {jobMs: [21000]}, {oversleep: 21000}]) {
    const x = await startup(config);
    assert.equal(x.result.status, 'incomplete-or-invalid');assert.equal(x.result.job_deadline_exhausted, true);
    assert.equal(x.reads, 1);assert.deepEqual(x.inspected, []);assert.equal(x.constructed, false);
  }
  const boundary = await startup({workflowMs: 20749});
  assert.equal(boundary.result.status, 'checked');assert.equal(boundary.reads, 2);
  assert.equal(boundary.deadlineRemaining(), 570000 - 20999);
  const second = await startup({jobMs: [0, 20000]});
  assert.equal(second.result.status, 'checked');assert.equal(second.deadlineRemaining(), 570000 - 20250);
  const late = await startup({jobMs: [0, 41000]});
  assert.equal(late.result.status, 'incomplete-or-invalid');assert.equal(late.result.job_deadline_exhausted, true);
  assert.equal(late.reads, 2);assert.equal(late.constructed, false);assert.deepEqual(late.inspected, []);
  assert.equal(late.result.deadline_binding.metadata_reads, 2);
  const rollback = await startup({rollback: true});
  assert.equal(rollback.result.status, 'incomplete-or-invalid');assert.match(rollback.result.reason, /clock/);
  assert.equal(rollback.reads, 1);assert.deepEqual(rollback.inspected, []);
});

test('metadata observations never retry HTTP quota, permission or uncertain transport failures', async () => {
  for (const failure of [403, 429, 500, 'transport']) {
    for (const second of [false, true]) {
      const x = await startup({httpFailure: second ? [null, failure] : failure});
      assert.equal(x.result.status, 'incomplete-or-invalid');assert.equal(x.reads, second ? 2 : 1);
      assert.deepEqual(x.waits, second ? [250] : []);assert.equal(x.constructed, false);assert.deepEqual(x.inspected, []);
      if (second) assert.equal(x.result.deadline_binding.metadata_reads, 2);
    }
  }
});


test('actual PR entry establishes the authoritative start after provisional queued timestamps', async () => {
  for (const phase of ['evidence', 'metadata']) {
    const x = await startup({phase, staleConditional: true, rows: [
      {status: 'queued', started_at: '2026-10-10T23:59:57Z'},
      {status: 'queued', started_at: '2026-10-10T23:59:58Z'},
      null, {status: 'queued'}, {status: 'queued'}, {},
    ]});
    assert.equal(x.result.status, 'checked');assert.equal(x.reads, 6);
    assert.equal(x.result.job_deadline.started_at, '2026-10-11T00:00:00.000Z');
    assert.equal(x.result.job_deadline.job_id, 40);assert.equal(x.deadlineRemaining(), 570000 - 11000);
    assert.deepEqual(x.waits, [250, 750, 2000, 4000, 4000]);
    assert.equal(x.result.job_deadline.metadata_observations[0].observed.started_at, '2026-10-10T23:59:57Z');
    assert(x.calls.filter(row => row.route.includes('/attempts/')).every(row => row.conditional === undefined));
  }
});

test('later startup reads retain identity, timestamp, terminal and HTTP refusal boundaries', async () => {
  for (const row of [{id: 41}, {run_id: 31}, {run_attempt: 3}, {status: 'completed'},
    {status: 'foreign'}, {started_at: 'bad'}, {started_at: '2026-10-11T00:00:01Z'}]) {
    const x = await startup({rows: [{status: 'queued'}, null, {status: 'waiting'}, row]});
    assert.equal(x.result.status, 'incomplete-or-invalid');assert.equal(x.reads, 4);
    assert.equal(x.constructed, false);assert.deepEqual(x.inspected, []);
  }
  const http = await startup({rows: [{status: 'queued'}], httpFailure: [null, null, null, 500]});
  assert.equal(http.result.status, 'incomplete-or-invalid');assert.equal(http.reads, 4);
  assert.equal(http.constructed, false);assert.deepEqual(http.inspected, []);
});

test('extended pending reads still charge the original startup deadline and full HTTP reserve', async () => {
  const x = await startup({rows: [{status: 'queued'}], workflowMs: 10000, jobMs: [0, 0, 0, 1000]});
  assert.equal(x.result.status, 'incomplete-or-invalid');assert.equal(x.result.job_deadline_exhausted, true);
  assert.equal(x.reads, 5);assert.equal(x.time, 18000);assert.deepEqual(x.waits, [250, 750, 2000, 4000]);
  assert.equal(x.constructed, false);assert.deepEqual(x.inspected, []);
});

test('only exact attempt-job inventory bypasses conditional snapshots; unsolicited 304 refuses', async () => {
  const inventory = '/repos/a/b/actions/runs/30/attempts/2/jobs';
  for (const route of [inventory, inventory + '?per_page=100&page=1',
    '/repos/a/b/actions/runs/30/jobs', inventory + '/other', '/repos/a/b/pulls/20']) {
    const conditional = ![inventory, inventory + '?per_page=100&page=1'].includes(route), seen = [];
    const api = githubAPI('fixture', {fetchImpl: async (_, options) => {
      seen.push(options.headers['If-None-Match']);
      return new Response(seen.at(-1) ? null : '{"status":"queued"}',
        {status: seen.at(-1) ? 304 : 200, headers: {etag: '"same"'}});
    }});
    await api(route);await api(route);assert.deepEqual(seen, [undefined, conditional ? '"same"' : undefined]);
  }
  let reads = 0;
  const api = githubAPI('fixture', {fetchImpl: async () => ++reads === 1
    ? new Response('{}', {headers: {etag: '"pending"'}}) : new Response(null, {status: 304})});
  await api(inventory);await assert.rejects(api(inventory), /Unrequested conditional/);assert.equal(reads, 2);
});
