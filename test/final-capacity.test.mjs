import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {waitForFinalCapacity, capacityObservation, finalRequestBound, inventoryFinalEvidence, paceFinalValidation,
  boundedFinalAPI, finalRequestBudget, beginFinalPlanning} from '../scripts/final-capacity.mjs';
import {memoizeImmutableGitBlobs} from '../scripts/immutable-git-blobs.mjs';
import {githubAPI, renderClaim} from '../scripts/issue-claim-contract.mjs';
import {loadGeographicReport} from '../scripts/geographic-report-artifact.mjs';
import {inspectMerge, completeIntegration} from '../scripts/merge-integration.mjs';
import {sha256, subjectsHash} from '../scripts/evidence-quality.mjs';
import {assertAdmission, queueBody, executionTitle} from '../scripts/merge-scheduler.mjs';
import {reviewContractBinding} from '../scripts/premerge-evidence.mjs';

const quota = (remaining, reset = 2, limit = 2000) => ({resources: {core: {remaining, reset, limit}}});
function clock() {
  let time = 0; const sleeps = [];
  return {now: () => time, wallNow: () => time, tick: ms => {time += ms;}, sleep: async ms => {sleeps.push(ms); time += ms;}, sleeps};
}
test('observed reset and early capacity progress without swapping token or accepting timing', async () => {
  for (const reset of [2, 999]) {
    const c = clock(), routes = [], observations = [];
    const result = await waitForFinalCapacity({...c, required: 100, pollMs: 1000,
      api: async route => {routes.push(route); return quota(routes.length === 3 ? 150 : 0, reset);},
      onObservation: row => observations.push(row)});
    assert.equal(result.observations, 3); assert.equal(result.waited_ms, 2000); assert.equal(result.reserved, false);
    assert.deepEqual(routes, ['/rate_limit', '/rate_limit', '/rate_limit']); assert.equal(observations.length, 3);
  }
});
test('no deficit causes no sleep and observed nondefault core limit owns admission', async () => {
  const c = clock(); const result = await waitForFinalCapacity({...c, required: 1200, api: async () => quota(1500)});
  assert.equal(result.limit, 2000); assert.equal(c.sleeps.length, 0);
  await assert.rejects(waitForFinalCapacity({...c, required: 2001, api: async () => quota(2000)}), /exceeds observed/);
});
test('invalid/null/rate denial data and disagreeing windows fail closed', async () => {
  for (const core of [null, {}, {limit: 1, remaining: null, reset: 2}, {limit: 1, remaining: 2, reset: 2},
    {limit: 1, remaining: 0, reset: NaN}, {limit: 1.5, remaining: 0, reset: 2}]) {
    assert.throws(() => capacityObservation({resources: {core}}), /Invalid/);
  }
  assert.throws(() => capacityObservation({...quota(1), capacity_headers: {limit: 2000, remaining: 1, reset: 3}}), /disagree/);
  assert.equal(capacityObservation({...quota(10), capacity_headers: {limit: 2000, remaining: 4, reset: 2}}).remaining, 4);
  const denial = Object.assign(Error('API rejected (HTTP 403)'), {github: {http_status: 403, rate_remaining: '0'}});
  await assert.rejects(waitForFinalCapacity({...clock(), required: 100, api: async () => {throw denial;}}), error => error === denial);
});
test('monotonic deadline bounds delayed reset despite wall-clock movement', async () => {
  const c = clock(); const wallNow = () => -999999;
  await assert.rejects(waitForFinalCapacity({...c, wallNow, required: 100, deadlineMs: 2500, pollMs: 1000,
    api: async () => quota(0, 999)}), /timed out/);
  assert.deepEqual(c.sleeps, [1000, 1000, 500]); assert.equal(c.now(), 2500);
});
test('final bound includes declared and original blobs, fresh guards and source gates', () => {
  const ordinary = {blob_calls: 474, water: false};
  const n = finalRequestBound({inventory: ordinary, metadataCalls: 23, admissionCalls: 12, artifactPages: 1});
  assert.equal(n, 581); assert.ok(finalRequestBound({inventory: {...ordinary, water: true}, metadataCalls: 23}) > n);
  assert.throws(() => finalRequestBound({inventory: ordinary, metadataCalls: Infinity}), /finite/);
});

function fixture() {
  const repo = 'o/r', head = 'b'.repeat(40), base = 'a'.repeat(40), candidate = 'c'.repeat(40), branch = 'engineering/capacity-fixture';
  const manifestPath = 'coordination/engineering/capacity-fixture/evidence-quality.json', outputPath = 'coordination/engineering/capacity-fixture/result.json';
  const baselineRaw = Buffer.from('baseline\n'), outputRaw = Buffer.from('{"controlled":true}\n');
  const desc = (path, raw) => ({path, bytes: raw.length, sha256: sha256(raw), hash_kind: 'file-bytes'});
  const files = [{filename: outputPath, status: 'added'}, {filename: manifestPath, status: 'added'}];
  const quality = {version: 1, manifest_path: 'coordination/engineering/{job}/evidence-quality.json', subject_ids: [], pins: {}, review_kind: 'release'};
  const spec = {mode: 'engineering', max_prs: 1, scope: 'Synthetic final capacity controls', depends_on: [], evidence_quality: quality};
  const issue = {number: 1183, state: 'open', created_at: '2026-10-06T00:00:00Z', labels: ['type:engineering', 'kind:work-item', 'status:ready'],
    body: `<!-- worldatlas-work:v1\n${JSON.stringify(spec)}\n-->`};
  const pr = {number: 23, head: {sha: head, ref: branch, repo: {full_name: repo}}, base: {sha: base, ref: 'main'},
    state: 'open', draft: false, merged: false, title: 'Synthetic capacity', body: 'Refs #1183', changed_files: 2};
  const manifest = {version: 1, issue: 1183, lane: 'engineering', worker_id: 'author', subject_ids: [], subject_ids_sha256: subjectsHash([]),
    baseline: {commit: base, files: [desc('README.md', baselineRaw)]}, sources: [], outputs: [desc(outputPath, outputRaw)],
    methods: [{id: 'controlled', kind: 'code', description: 'Synthetic capacity controls', software: 'Node', units: 'pass/fail'}],
    validation: [], metrics: [], metric_bindings: [], summaries: [], conclusions: [], commands: ['node --test'],
    stages: {research: 'complete', implementation: 'implemented', geographic_approval: 'not-requested'},
    change_receipts: files.map(row => ({path: row.filename, status: row.status}))};
  const manifestRaw = Buffer.from(JSON.stringify(manifest));
  const claim = {version: 1, active: true, worker_id: 'author', claim_id: 'original-claim', branch, expires_at: '2030-01-01T00:00:00Z'};
  const review = {version: 1, pr_number: 23, head_sha: head, manifest_sha256: sha256(manifestRaw), author_worker_id: 'author',
    reviewer_worker_id: 'reviewer', inspected_files: files.map(row => row.filename), evidence_hashes: [sha256(baselineRaw), sha256(outputRaw)],
    outcome: 'accepted', limits: [], domains: {implementation: {outcome: 'accepted', scope: 'Synthetic controls', limits: []},
      release: {outcome: 'accepted', scope: 'Synthetic preservation', limits: []}}};
  const blobs = new Map(), tree = rows => rows.map(([path, raw]) => {
    const sha = createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
    blobs.set(sha, {sha, size: raw.length, encoding: 'base64', content: raw.toString('base64')});
    return {path, sha, size: raw.length, mode: '100644', type: 'blob'};
  });
  const authored = tree([['README.md', baselineRaw], [outputPath, outputRaw], [manifestPath, manifestRaw]]), baseline = tree([['README.md', baselineRaw]]);
  const f = {repo, head, base, candidate, issue, pr, files, claim, review, manifest, blobs, authored, baseline, calls: [], writes: [], phase: 'before', checks: 'success'};
  const request = {pr_number: 23, expected_head: head, request_id: 'durable-capacity-ticket'};
  f.api = async (route, method = 'GET', body) => {
    f.calls.push({route, method, phase: f.phase}); const name = route.split('?')[0];
    if (method !== 'GET') {f.writes.push({route, method, body}); return {merged: true, sha: 'd'.repeat(40)};}
    if (name === '/rate_limit') return quota(f.phase === 'before' ? f.startCapacity ?? 0 : 2000, 2);
    if (name === `/repos/${repo}/pulls`) return [structuredClone(f.pr)];
    if (name.endsWith('/actions/workflows/worker-merge.yml/runs')) return {workflow_runs:
      new URLSearchParams(route.split('?')[1]).get('status') === 'in_progress' ?
        [{id: 12, status: 'in_progress', display_title: executionTitle(request, 1)}] : []};
    if (name === `/repos/${repo}/pulls/23`) return structuredClone(f.pr);
    if (name === `/repos/${repo}/issues/1183`) return structuredClone(f.issue);
    if (name === `/repos/${repo}/issues/1183/comments`) return [{user: {login: 'github-actions[bot]'}, body: renderClaim(f.claim)}];
    if (name.endsWith('/timeline')) return [];
    if (name === `/repos/${repo}/pulls/23/files`) return structuredClone(f.files);
    if (name.endsWith('/check-runs')) return {check_runs: ['scope', 'evidence'].map((name, id) => ({name, id, status: 'completed', conclusion: f.checks}))};
    if (name.endsWith('/status')) return {statuses: []};
    if (name === `/repos/${repo}/git/ref/heads/main`) return {object: {sha: f.base}};
    if (name === `/repos/${repo}/issues/23/comments`) return [
      {id: 1, author_association: 'OWNER', body: `<!-- worldatlas-review:v1\n${JSON.stringify(f.review)}\n-->`},
      ...['request', 'dispatch'].map((kind, i) => ({id: i + 2, user: {login: 'github-actions[bot]'},
        body: queueBody({...request, kind, ...(kind === 'dispatch' ? {attempt: 1} : {})})}))];
    if (name.includes('/git/commits/')) {
      const commit = name.split('/').at(-1);
      return {tree: {sha: commit === base ? '1'.repeat(40) : '2'.repeat(40)}, parents: [{sha: base}, {sha: head}]};
    }
    if (name.includes('/git/trees/')) return {truncated: f.truncated ?? false, tree: name.endsWith('1'.repeat(40)) ? baseline : authored};
    if (name.includes('/git/blobs/')) return structuredClone(blobs.get(name.split('/').at(-1)));
    if (name.includes('/compare/')) return {status: 'identical'};
    if (name.endsWith('/artifacts')) return {total_count: 1, artifacts: [{id: 1, name: 'geo'}]};
    throw Error(`Unexpected route ${route}`);
  };
  f.options = () => ({api: memoizeImmutableGitBlobs(f.api), repo, number: 23, expectedHead: head,
    policy: {version: 1, mode: 'enforce-new', activation_time: '2026-01-01T00:00:00Z'}, testedBase: base,
    artifactRunId: 12, finalAdmission: api => assertAdmission({api, repo, request, attempt: 1, runId: 12}),
    capacityTiming: {...clock(), sleep: async () => {f.phase = 'after';}}});
  f.complete = (extra = {}) => completeIntegration({...f.options(), finalCapacity: true, integrationResult: 'success',
    geographyResult: 'success', testedCandidate: f.candidate,
    geographyReportLoader: async () => ({version: 1, method_id: 'worldatlas-trusted-geography-check-v1', baseline_commit: f.base,
      trusted_code_commit: f.base, candidate_commit: f.candidate, candidate_code_executed: false, published: false,
      source_approval: false, gate_status: 'passed', status: 'not-applicable'}), ...extra});
  return f;
}

test('real tree/path/vintage inventory includes nonadded originals and verified OID reuse', async () => {
  const f = fixture(), options = f.options();
  const inventory = await inventoryFinalEvidence({...options, pr: f.pr, issue: f.issue, files: f.files, reservation: {worker_id: 'author'}});
  assert.equal(inventory.blob_calls, 3); assert.equal(inventory.cache_fit, true); assert.equal(inventory.original_count, 0);
  f.files[0].status = 'modified'; f.baseline.push({...f.authored.find(row => row.path.endsWith('result.json'))});
  const next = await inventoryFinalEvidence({...options, pr: f.pr, issue: f.issue, files: f.files, reservation: {worker_id: 'author'}});
  assert.equal(next.original_count, 1); assert.equal(next.blob_calls, 3);
  f.truncated = true;
  await assert.rejects(inventoryFinalEvidence({...options, pr: f.pr, issue: f.issue, files: f.files, reservation: {worker_id: 'author'}}), /complete trees/);
});
// Different bytes at the same path, plus a path absent from the default baseline,
// exercise the actual inventory boundary rather than a version flag alone.
function historicalFixture() {
  const f = fixture(), old = 'd'.repeat(40), oldTree = '3'.repeat(40);
  const otherRaw = Buffer.from('older README with distinct bytes\n');
  const nativeRaw = Buffer.from('original-only input\n');
  const row = (path, raw) => {
    const sha = createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
    f.blobs.set(sha, {sha, size: raw.length, encoding: 'base64', content: raw.toString('base64')});
    return {path, sha, size: raw.length, type: 'blob', mode: '100644'};
  };
  const desc = (path, raw, commit) => ({path, commit, bytes: raw.length, sha256: sha256(raw), hash_kind: 'file-bytes'});
  f.manifest.baseline = {version: 2, commit: f.base, files: [
    {...f.manifest.baseline.files[0], commit: f.base},
    desc('README.md', otherRaw, old), desc('original-only.json', nativeRaw, old)]};
  f.historical = [row('README.md', otherRaw), row('original-only.json', nativeRaw)];
  f.old = old;
  f.refreshManifest = () => {
    const raw = Buffer.from(JSON.stringify(f.manifest));
    Object.assign(f.authored.find(entry => entry.path.endsWith('evidence-quality.json')),
      row('coordination/engineering/capacity-fixture/evidence-quality.json', raw));
    f.review.manifest_sha256 = sha256(raw);
    f.review.evidence_hashes = [...new Set([...f.manifest.baseline.files.map(file => file.sha256), ...f.manifest.outputs.map(file => file.sha256)])];
    return raw;
  };
  f.refreshManifest();
  const original = f.api;
  f.api = async (route, ...args) => {
    if (route === `/repos/${f.repo}/git/commits/${old}`) return {tree: {sha: oldTree}};
    if (route === `/repos/${f.repo}/git/trees/${oldTree}?recursive=1`)
      return {truncated: f.historicalTruncated ?? false, tree: f.historical};
    if (route === `/repos/${f.repo}/compare/${old}...${f.base}`)
      return {status: f.historicalStatus ?? 'ahead'};
    return original(route, ...args);
  };
  f.inventory = () => inventoryFinalEvidence({...f.options(), pr: f.pr, issue: f.issue,
    files: f.files, reservation: f.claim});
  return f;
}

test('final capacity resolves each v2 historical path at its own ancestor commit and counts distinct bytes', async () => {
  const f = historicalFixture();
  const inventory = await f.inventory();
  assert.equal(inventory.descriptor_count, 4);
  assert.equal(inventory.immutable_oids, 5);
  assert.equal(inventory.blob_calls, 5);
  assert.equal(inventory.cache_fit, true);
  assert.equal(f.writes.length, 0);
  // The default/base tree is reused only inside this fresh inventory call.
  assert.equal(f.calls.filter(row => row.route.endsWith(`/git/commits/${f.base}`)).length, 1);
});

for (const status of ['behind', 'diverged', undefined]) test(`historical ancestry rejects ${status}`, async () => {
  const f = historicalFixture();
  const original = f.api;
  f.api = (route, ...args) => route.includes(`/compare/${f.old}...`) ? Promise.resolve({status}) : original(route, ...args);
  await assert.rejects(f.inventory(), /not an ancestor/);
  assert.equal(f.writes.length, 0);
});

for (const kind of ['unsupported-version', 'missing-commit', 'v1-per-file', 'duplicate', 'too-many-commits', 'truncated', 'symlink', 'missing-path', 'large-file'])
test(`historical capacity rejects ${kind} before publication`, async () => {
  const f = historicalFixture();
  const expected = {
    'unsupported-version': /Unsupported baseline version/, 'missing-commit': /immutable commit/,
    'v1-per-file': /requires baseline version 2/, duplicate: /Duplicate historical/,
    'too-many-commits': /commit inventory exceeds/, truncated: /complete trees/,
    symlink: /invalid file binding/, 'missing-path': /invalid file binding/, 'large-file': /invalid file binding/
  };
  if (kind === 'unsupported-version') f.manifest.baseline.version = 3;
  if (kind === 'missing-commit') delete f.manifest.baseline.files[1].commit;
  if (kind === 'v1-per-file') f.manifest.baseline.version = 1;
  if (kind === 'duplicate') f.manifest.baseline.files.push({...f.manifest.baseline.files[1]});
  if (kind === 'too-many-commits') f.manifest.baseline.files = Array.from({length: 17}, (_, i) =>
    ({...f.manifest.baseline.files[0], commit: (i + 1).toString(16).padStart(40, '0')}));
  if (kind === 'truncated') f.historicalTruncated = true;
  if (kind === 'symlink') f.historical[0].mode = '120000';
  if (kind === 'missing-path') f.historical.pop();
  if (kind === 'large-file') f.historical[0].size = 32 * 1024 * 1024 + 1;
  f.refreshManifest();
  await assert.rejects(f.inventory(), expected[kind]);
  assert.equal(f.writes.length, 0);
});

test('same-path historical vintages retain the aggregate remote-byte limit', async () => {
  const f = historicalFixture();
  const paths = Array.from({length: 9}, (_, i) => `bounded-${i}.json`);
  f.manifest.baseline.files = paths.flatMap((path, i) => [{...f.manifest.baseline.files[0], path, commit: f.base},
    {...f.manifest.baseline.files[1], path, commit: f.old}]);
  const entries = (commit) => paths.map((path, i) => ({path, sha: (i + (commit === f.base ? 100 : 200)).toString(16).padStart(40, '0'),
    type: 'blob', mode: '100644', size: 16 * 1024 * 1024}));
  f.baseline.splice(0, f.baseline.length, ...entries(f.base));
  f.historical.splice(0, f.historical.length, ...entries(f.old));
  f.refreshManifest();
  await assert.rejects(f.inventory(), /remote byte budget/);
  assert.equal(f.writes.length, 0);
});

test('costly evidence inventory requires current issue and disposition bindings after activation', async () => {
  const f = fixture(), options = f.options();
  f.pr.created_at = '2026-10-07T00:00:00Z';
  options.policy.review_contract_activation_time = '2026-10-06T20:45:00Z';
  const inventory = () => inventoryFinalEvidence({...options, pr: f.pr, issue: f.issue, files: f.files, reservation: {worker_id: 'author'}});
  await assert.rejects(inventory(), /Missing current exact-head review/);
  Object.assign(f.review, reviewContractBinding(f.issue, f.pr));
  assert.equal((await inventory()).blob_calls, 3);
  f.issue.body += '\nUnfinished production acceptance';
  await assert.rejects(inventory(), /Missing current exact-head review/);
  Object.assign(f.review, reviewContractBinding(f.issue, f.pr));
  f.pr.body = 'Closes #1183';
  await assert.rejects(inventory(), /Missing current exact-head review/);
  assert.equal(f.writes.length, 0);
});
test('capacity wait preserves same live ticket and invokes fresh FIFO authority', async () => {
  const f = fixture(); let admissionReads = 0;
  const result = await paceFinalValidation(f.options(), {inspect: inspectMerge, admission: async () => {admissionReads++;}});
  assert.equal(admissionReads, 2); assert.equal(result.receipt.reserved, false); assert.equal(result.receipt.status, 'observed-sufficient');
  assert.equal(f.writes.length, 0); assert.ok(f.calls.some(row => row.phase === 'after' && row.route.includes('/issues/1183/comments')));
});
for (const mutation of ['claim', 'claim-id', 'review', 'head', 'base', 'checks', 'contract', 'tree-mode', 'tree-path']) test(`changed ${mutation} while waiting rejects before costly output blobs`, async () => {
  const f = fixture(), options = f.options();
  options.capacityTiming.sleep = async () => {
    f.phase = 'after';
    if (mutation === 'claim') f.claim.expires_at = '2000-01-01T00:00:00Z';
    if (mutation === 'claim-id') f.claim.claim_id = 'changed-claim';
    if (mutation === 'review') f.review.outcome = 'changes-requested';
    if (mutation === 'head') f.pr.head.sha = 'e'.repeat(40);
    if (mutation === 'base') f.base = 'e'.repeat(40);
    if (mutation === 'checks') f.checks = 'failure';
    if (mutation === 'contract') f.issue.body += ' changed';
    if (mutation === 'tree-mode') f.authored.find(row => row.path.endsWith('result.json')).mode = '120000';
    if (mutation === 'tree-path') f.authored.find(row => row.path.endsWith('result.json')).path = 'different.json';
  };
  await assert.rejects(paceFinalValidation(options, {inspect: inspectMerge}));
  assert.equal(f.phase, 'after', 'denial must follow the actual capacity wait');
  assert.equal(f.writes.length, 0);
  assert.equal(f.calls.filter(row => row.phase === 'after' && row.route.includes('/git/blobs/')).length, 0);
});
test('paid-call bound sits below immutable reuse and reserves writes instead of charging cached passes', async () => {
  const raw = Buffer.from('immutable capacity control'), sha = createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
  let paid = 0; const budget = finalRequestBudget(async () => {
    paid++; return {sha, size: raw.length, encoding: 'base64', content: raw.toString('base64')};
  });
  budget.setLimit(2); const api = memoizeImmutableGitBlobs(budget.api);
  for (let n = 0; n < 100; n++) await api(`/repos/o/r/git/blobs/${sha}`);
  assert.equal(paid, 1); await api('/repos/o/r/pulls/23'); assert.equal(paid, 2);
  await assert.rejects(api('/repos/o/r/pulls/23'), /grew beyond/); assert.equal(paid, 2);
});
for (const deadline of [100000, 1000]) test(`planning retries retain original monotonic deadline and finite attempt bound: ${deadline}`, async () => {
  const c = clock(); let rateReads = 0, prReads = 0;
  const head = 'b'.repeat(40), base = 'a'.repeat(40);
  const budget = finalRequestBudget(async route => {
    if (route === '/rate_limit') return quota(Math.min(60, 24 + 16 * rateReads++));
    c.tick(20);
    if (route.endsWith('/pulls/23')) {prReads++; return {head: {sha: head}, merged: false};}
    if (route.endsWith('/main')) return {object: {sha: base}};
    return {};
  });
  const options = await beginFinalPlanning({api: budget.api, capacityBudget: budget, repo: 'o/r', number: 23,
    expectedHead: head, testedBase: base, capacityTiming: {...c, deadlineMs: deadline}});
  await assert.rejects(paceFinalValidation(options, {inspect: async ({api}) => {
    for (let n = 0; n < 100; n++) await api(`/metadata/${n}`);
    throw Error('Partial planning must never finish');
  }}), deadline === 1000 ? /deadline exhausted/ : /grew beyond/);
  assert.equal(prReads, 3); assert.equal(rateReads, 3); assert.ok(c.now() <= deadline + 20);
});
test('complete final still validates every evidence byte after waiting and rejects changed authority', async () => {
  const f = fixture(); const result = await f.complete();
  assert.equal(result.accepted, true); assert.equal(result.final_capacity.status, 'observed-sufficient');
  assert.ok(f.calls.some(row => row.phase === 'after' && row.route.includes('/git/blobs/')));
  assert.equal(f.writes.filter(row => row.method === 'PUT').length, 1);
  assert.ok(f.calls.filter(row => row.phase === 'before').every(row => row.route === '/rate_limit'),
    'zero capacity must wait before the first repository GET');
  assert.ok(f.calls.some(row => row.phase === 'after' && row.route.includes('/worker-merge.yml/runs')));
});
test('modest planning capacity restarts the entire fresh inventory after observed reset in the same ticket', async () => {
  const f = fixture(); f.startCapacity = 24;
  const result = await f.complete();
  assert.equal(result.accepted, true); assert.equal(result.final_capacity.planning_attempts, 2);
  assert.equal(result.final_capacity.planning_retry.required, 25);
  assert.equal(f.writes.filter(row => row.route.endsWith('/dispatches')).length, 0);
  assert.ok(f.calls.some(row => row.phase === 'before' && row.route.includes('/pulls/23')));
  assert.ok(f.calls.some(row => row.phase === 'after' && row.route.includes('/pulls/23')));
});
test('competing consumption after probe and inventory growth never bypass calls or original denial', async () => {
  let calls = 0; const denial = Object.assign(Error('competing consumption (HTTP 403)'), {github: {http_status: 403}});
  const api = boundedFinalAPI(async () => {calls++; throw denial;}, 1);
  await assert.rejects(api('/repos/o/r/pulls/23'), error => error === denial);
  await assert.rejects(api('/repos/o/r/pulls/23'), /grew beyond/); assert.equal(calls, 1);
});
test('same-token success capacity metadata never logs arbitrary bodies or headers', async () => {
  const fetchOriginal = globalThis.fetch, token = 'synthetic-known-private-token';
  globalThis.fetch = async (_url, options) => {
    assert.equal(options.headers.Authorization, `Bearer ${token}`);
    return new Response(JSON.stringify({...quota(1500), secret: token}), {status: 200,
      headers: {'x-ratelimit-limit': '2000', 'x-ratelimit-remaining': '1400', 'x-ratelimit-reset': '2', Authorization: token}});
  };
  try {
    const records = []; await waitForFinalCapacity({...clock(), api: githubAPI(token), required: 500, onObservation: row => records.push(row)});
    const output = JSON.stringify(records); assert.equal(output.includes(token), false); assert.equal(output.includes('Authorization'), false);
    assert.equal(records[0].remaining, 1400); assert.equal(records[0].reserved, false);
  } finally {globalThis.fetch = fetchOriginal;}
});

 test('real geographic artifact adapter cannot grow pagination outside final paid-call guard', async () => {
  const f = fixture(), original = f.api; let loading = false, artifactCalls = 0, downloads = 0;
  f.api = async (...args) => {
    if (loading && args[0].includes('/artifacts?')) {
      artifactCalls++;
      return {total_count: 10000, artifacts: Array.from({length: 100}, (_, i) => ({id: i + 1, name: 'other'}))};
    }
    return original(...args);
  };
  await assert.rejects(f.complete({geographyReportLoader: async ({api}) => {
    assert.equal(typeof api, 'function'); assert.notEqual(api, f.api);
    loading = true;
    return loadGeographicReport({api, repo: f.options().repo, runId: 12,
      artifactName: 'geography-durable-capacity-ticket-12', expectedHash: 'a'.repeat(64), token: 'fixture-token',
      fetchImpl: async () => {downloads++; throw Error('Unexpected download');}});
  }}), /inventory grew beyond safe request bound/);
  assert.ok(artifactCalls > 0 && artifactCalls < 100); assert.equal(downloads, 0);
  assert.equal(f.writes.filter(row => row.method === 'PUT').length, 0);
});
test('capacity excludes blob REST requests only after exact transport proves the entire bound inventory',async()=>{
 for(const complete of [false,true]){
  const f=fixture();let rows;
  f.api.prefetchGitBlobs=async(repo,inventory)=>{assert.equal(repo,f.repo);rows=inventory;};
  f.api.hasGitBlobs=(repo,inventory)=>complete&&inventory===rows;
  const value=await inventoryFinalEvidence({api:f.api,repo:f.repo,pr:f.pr,issue:f.issue,reservation:f.claim,files:f.files,policy:{version:1,mode:'enforce-new',activation_time:'2020-01-01T00:00:00Z'}});
  assert(rows.length>0);assert.equal(value.exact_git_transport,complete);assert.equal(value.blob_calls,complete?0:rows.length);
 }
});
