import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {crc32} from 'node:zlib';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {gitBlobTransport} from '../scripts/git-blob-transport.mjs';
import {waitForFinalCapacity, capacityObservation, finalRequestBound, inventoryFinalEvidence, paceFinalValidation,
  boundedFinalAPI, finalRequestBudget, beginFinalPlanning} from '../scripts/final-capacity.mjs';
import {memoizeImmutableGitBlobs} from '../scripts/immutable-git-blobs.mjs';
import {githubAPI} from '../scripts/issue-claim-contract.mjs';
import {loadGeographicReport, prepareGeographyProof, reportHash} from '../scripts/geographic-report-artifact.mjs';
import {inspectMerge, prepareIntegration, completeIntegration} from '../scripts/merge-integration.mjs';
import {sha256, subjectsHash} from '../scripts/evidence-quality.mjs';
import {reviewContractBinding} from '../scripts/premerge-evidence.mjs';
import {PROOF_PATHS, WORKFLOW_PATH} from '../scripts/integration-proof.mjs';

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
  const n = finalRequestBound({inventory: ordinary, metadataCalls: 23, artifactPages: 1});
  assert.equal(n, 573); assert.ok(finalRequestBound({inventory: {...ordinary, water: true}, metadataCalls: 23}) > n);
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
  const f = {repo, head, base, candidate, issue, pr, files, review, manifest, blobs, authored, baseline, calls: [], writes: [], phase: 'before', checks: 'success'};
  f.api = async (route, method = 'GET', body) => {
    f.calls.push({route, method, phase: f.phase}); const name = route.split('?')[0];
    if (method !== 'GET') {f.writes.push({route, method, body}); return {merged: true, sha: 'd'.repeat(40)};}
    if (name === '/rate_limit') return quota(f.phase === 'before' ? f.startCapacity ?? 0 : 2000, 2);
    if (name === `/repos/${repo}/pulls`) return [structuredClone(f.pr)];
    if (name === `/repos/${repo}/pulls/23`) return structuredClone(f.pr);
    if (name === `/repos/${repo}/issues/1183`) return structuredClone(f.issue);
    if (name.endsWith('/timeline')) return [];
    if (name === `/repos/${repo}/pulls/23/files`) return structuredClone(f.files);
    if (name.endsWith('/check-runs')) return {check_runs: ['scope', 'evidence'].map((name, id) => ({name, id, status: 'completed', conclusion: f.checks}))};
    if (name.endsWith('/status')) return {statuses: []};
    if (name === `/repos/${repo}/git/ref/heads/main`) return {object: {sha: f.base}};
    if (name === `/repos/${repo}/issues/23/comments`) return [
      {id: 1, author_association: 'OWNER', body: `<!-- worldatlas-review:v1\n${JSON.stringify(f.review)}\n-->`}];
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
    artifactRunId: 12,
    capacityTiming: {...clock(), sleep: async () => {f.phase = 'after';}}});
  f.complete = (extra = {}) => completeIntegration({...f.options(), finalCapacity: true, integrationResult: 'success',
    geographyResult: 'success', testedCandidate: f.candidate,
    geographyReportLoader: async () => ({version: 1, method_id: 'worldatlas-trusted-geography-check-v1', baseline_commit: f.base,
      trusted_code_commit: f.base, candidate_commit: f.candidate, candidate_code_executed: false, published: false,
      source_approval: false, gate_status: 'passed', status: 'not-applicable'}), ...extra});
  return f;
}

function evidenceFailedProof(f) {
  const workflow='ref: ${{ github.event.pull_request.head.sha }}\nname: Complete regression shard\nname: Build hosted assets';
  for (const path of PROOF_PATHS) {
    const raw=Buffer.from(path===WORKFLOW_PATH ? workflow : path);
    const sha=createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
    f.blobs.set(sha,{sha,size:raw.length,encoding:'base64',content:raw.toString('base64')});
    const row={path,sha,size:raw.length,mode:'100644',type:'blob'};
    f.baseline.push(row);f.authored.push(row);
  }
  f.proofRun={id:44,run_attempt:1,head_sha:f.head,event:'pull_request',path:WORKFLOW_PATH,
    repository:{full_name:f.repo},head_repository:{full_name:f.repo},status:'completed',conclusion:'failure',
    pull_requests:[{number:23,head:{sha:f.head}}]};
  f.proofJobs=[...['profile','scope','geography','package'].map(name=>({name,status:'completed',conclusion:'success'})),
    {name:'evidence',status:'completed',conclusion:'failure'},
    {name:'regression (0)',status:'completed',conclusion:'success',steps:
      ['Checkout reviewed head','Install browser dependencies only for tests that use Playwright','Complete regression shard']
        .map(name=>({name,status:'completed',conclusion:'success'}))}];
  const original=f.api;f.proofReads=0;
  f.api=async(route,...args)=>{
    if(route.endsWith('/actions/runs/44')) {f.proofReads++;return structuredClone(f.proofRun);}
    if(route.includes('/actions/runs/44/attempts/1/jobs')) return {jobs:structuredClone(f.proofJobs)};
    return original(route,...args);
  };
  const complete=f.complete;
  f.complete=extra=>complete({integrationResult:'skipped',proofRunId:44,proofRunAttempt:1,...extra});
  return f;
}
test('real hosted final-capacity path accepts evidence-only run failure after full proof revalidation',async()=>{
  const f=evidenceFailedProof(fixture());
  const result=await f.complete();
  assert.equal(result.accepted,true);assert.equal(result.final_capacity.status,'observed-sufficient');
  assert.equal(result.proof.run_id,44);assert.equal(result.proof.run_attempt,1);
  assert.equal(f.proofReads,3,'inventory before and after capacity observation, then full final proof');
  assert.equal(f.writes.filter(row=>row.route.endsWith('/merge')).length,1);
});
test('hosted final-capacity inventory cannot authorize failed or missing code and science',async()=>{
  for (const mutate of [
    f=>f.proofJobs.find(job=>job.name==='regression (0)').conclusion='failure',
    f=>f.proofJobs.find(job=>job.name==='regression (0)').steps.pop(),
    f=>f.proofJobs.find(job=>job.name==='regression (0)').steps[0].conclusion='skipped',
    f=>f.proofJobs=f.proofJobs.filter(job=>job.name!=='geography'),
    f=>f.proofJobs.find(job=>job.name==='geography').conclusion='failure',
    f=>f.proofJobs.find(job=>job.name==='scope').conclusion='skipped',
    f=>f.proofRun.run_attempt=2,
    f=>f.proofRun.conclusion='cancelled',
    f=>f.proofRun.status='in_progress'
  ]) {
    const f=evidenceFailedProof(fixture());mutate(f);
    await assert.rejects(f.complete(),/Trusted (?:integration )?proof/);
    assert.equal(f.writes.length,0);
  }
});
test('hosted proof is rechecked after capacity inventory before any merge write',async()=>{
  for(const change of ['attempt','code-step']) {
    const f=evidenceFailedProof(fixture()), original=f.api;
    f.api=async(route,...args)=>{
      const result=await original(route,...args);
      if(route.endsWith('/actions/runs/44') && f.proofReads===2) {
        if(change==='attempt') {f.proofRun.run_attempt=2;return structuredClone(f.proofRun);}
        f.proofJobs.find(job=>job.name==='regression (0)').steps[0].conclusion='failure';
      }
      return result;
    };
    await assert.rejects(f.complete(),/Trusted (?:integration )?proof/);assert.equal(f.writes.length,0);
  }
});

function geographyReuseFixture() {
  const f = evidenceFailedProof(fixture());
  f.pr.mergeable = true; f.pr.merge_commit_sha = f.candidate;
  const job = f.proofJobs.find(job => job.name === 'geography');
  Object.assign(job, {id: 55, steps: ['Checkout trusted geographic checker', 'Install trusted geographic dependencies',
    'Check proposed geography with trusted baseline code',
    'Run actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02']
    .map(name => ({name, status: 'completed', conclusion: 'success'}))});
  f.source = {run_id: 44, run_attempt: 1, job_id: 55, tree: '2'.repeat(40), head: f.head, baseline: f.base,
    artifact_id: 77, artifact_name: 'proposed-geography-23-1', artifact_digest: 'a'.repeat(64), artifact_bytes: 100,
    report_sha256: 'b'.repeat(64), report_bytes: 200};
  f.report = {version: 1, method_id: 'worldatlas-trusted-geography-check-v1', baseline_commit: f.base,
    trusted_code_commit: f.base, candidate_commit: f.head, candidate_code_executed: false,
    published: false, source_approval: false, gate_status: 'passed', status: 'not-applicable'};
  const original = f.api;
  f.api = async (route, ...args) => route.includes('/actions/workflows/merge-integration-checks.yml/runs')
    ? {workflow_runs: [structuredClone(f.proofRun)]} : original(route, ...args);
  f.prepare = extra => prepareIntegration({...f.options(), geographyProofLoader: async () => ({source: f.source, report: f.report}), ...extra});
  const complete = f.complete;
  f.reuse = extra => complete({geographyResult: 'skipped', geographyProof: f.source,
    geographyReportLoader: async () => structuredClone(f.report), ...extra});
  return f;
}

test('prepare to actual final-capacity consumer reuses original geography with truthful identities', async () => {
  const f = geographyReuseFixture(), prepared = await f.prepare();
  assert.deepEqual(prepared.geography_proof, f.source); assert.equal(prepared.proof.geography_job_id, 55);
  const result = await f.reuse({geographyProof: prepared.geography_proof});
  assert.equal(result.accepted, true); assert.equal(result.final_capacity.status, 'observed-sufficient');
  assert.equal(result.tested_candidate, f.candidate); assert.equal(result.geography.candidate_commit, f.head);
  assert.equal(result.geography.execution, 'reused-original'); assert.deepEqual(result.geography.source, f.source);
  assert(f.calls.some(call => call.route.includes('/actions/runs/44/artifacts?')));
  assert(!f.calls.some(call => call.route.includes('/actions/runs/12/artifacts?')),
    'capacity must inventory the pinned source run, not the current queue run');
  assert.equal(f.writes.filter(row => row.route.endsWith('/merge')).length, 1);
});

test('unusable prepared report falls back to fresh geography without discarding application proof', async () => {
  for (const change of ['missing', 'wrong-report', 'wrong-source', 'download-failed']) {
    const f = geographyReuseFixture();
    const prepared = await f.prepare({geographyProofLoader: async () => {
      if (change === 'missing') return null;
      if (change === 'download-failed') throw Error('bounded original log unavailable');
      return {source: {...f.source, ...(change === 'wrong-source' ? {job_id: 66} : {})},
        report: {...f.report, ...(change === 'wrong-report' ? {candidate_commit: f.candidate} : {})}};
    }});
    assert.equal(prepared.proof.run_id, 44); assert.equal(prepared.geography_proof, null);
    await assert.rejects(f.reuse({geographyProof: null}), /Trusted combined geography check/);
    assert.equal(f.writes.length, 0);
  }
});

test('reused geography never accepts drift, unresolved science or failed current authority', async () => {
  for (const mutate of [
    f => {f.source.job_id++;}, f => {f.source.run_attempt++;}, f => {f.source.tree = '3'.repeat(40);},
    f => {f.source.baseline = 'd'.repeat(40);}, f => {f.source.head = 'd'.repeat(40);},
    f => {f.source.artifact_name = 'proposed-geography-24-1';},
    f => {f.report.candidate_commit = f.candidate;}, f => {f.report.trusted_code_commit = 'd'.repeat(40);},
    f => {f.report.status = 'regressions-found';}, f => {f.report.gate_status = 'blocked';},
    f => {f.proofJobs.find(job => job.name === 'geography').steps[2].conclusion = 'skipped';},
    f => {f.proofRun.run_attempt++;}, f => {f.checks = 'failure';},
    f => {f.issue.state = 'closed';}
  ]) {
    const f = geographyReuseFixture(); await f.prepare(); mutate(f);
    await assert.rejects(f.reuse()); assert.equal(f.writes.length, 0);
  }
});

test('final geography source is revalidated after capacity waiting before any write', async () => {
  const f = geographyReuseFixture(); await f.prepare(); const original = f.api;
  f.api = async (route, ...args) => {
    const result = await original(route, ...args);
    if (route.endsWith('/actions/runs/44') && f.proofReads === 2)
      f.proofJobs.find(job => job.name === 'geography').steps.pop();
    return result;
  };
  await assert.rejects(f.reuse(), /Original geographic proof/); assert.equal(f.writes.length, 0);
});

test('real tree/path/vintage inventory includes nonadded originals and verified OID reuse', async () => {
  const f = fixture(), options = f.options();
  const inventory = await inventoryFinalEvidence({...options, pr: f.pr, issue: f.issue, files: f.files});
  assert.equal(inventory.blob_calls, 3); assert.equal(inventory.cache_fit, true); assert.equal(inventory.original_count, 0);
  f.files[0].status = 'modified'; f.baseline.push({...f.authored.find(row => row.path.endsWith('result.json'))});
  const next = await inventoryFinalEvidence({...options, pr: f.pr, issue: f.issue, files: f.files});
  assert.equal(next.original_count, 1); assert.equal(next.blob_calls, 3);
  f.truncated = true;
  await assert.rejects(inventoryFinalEvidence({...options, pr: f.pr, issue: f.issue, files: f.files}), /complete trees/);
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
    files: f.files});
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
  const inventory = () => inventoryFinalEvidence({...options, pr: f.pr, issue: f.issue, files: f.files});
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
test('capacity wait rechecks current issue scope without scheduler admission', async () => {
  const f = fixture();
  const result = await paceFinalValidation(f.options(), {inspect: inspectMerge});
  assert.equal(result.receipt.reserved, false); assert.equal(result.receipt.status, 'observed-sufficient');
  assert.equal(f.writes.length, 0); assert.ok(f.calls.some(row => row.phase === 'after' && row.route === '/repos/o/r/issues/1183'));
});
for (const mutation of ['closed-issue', 'wrong-lane', 'review', 'head', 'base', 'checks', 'contract', 'tree-mode', 'tree-path']) test(`changed ${mutation} while waiting rejects before costly output blobs`, async () => {
  const f = fixture(), options = f.options();
  options.capacityTiming.sleep = async () => {
    f.phase = 'after';
    if (mutation === 'closed-issue') f.issue.state = 'closed';
    if (mutation === 'wrong-lane') f.issue.labels[0] = 'type:geography';
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
  assert.ok(!f.calls.some(row => row.route.includes('/worker-merge.yml/runs')), 'No scheduler inventory');
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

for (const exactCapacity of [true, false]) test(`real geographic artifact growth retains quota and structural limits: ${exactCapacity}`, async () => {
  const f = fixture(), original = f.api; let loading = false, artifactCalls = 0, downloads = 0;
  f.api = async (...args) => {
    if (loading && args[0].includes('/artifacts?')) {
      artifactCalls++;
      return {total_count: 10000, artifacts: Array.from({length: 100}, (_, i) => ({id: i + 1, name: 'other'}))};
    }
    return original(...args);
  };
  let probes = 0, required;
  f.api.readRepositoryCapacity = async () => ({limit: 2000, reset: 2,
    remaining: ++probes === 1 || !exactCapacity ? 2000 : probes === 2 ? 0 : required});
  await assert.rejects(f.complete({capacityObserver: row => {if (row.phase === 'final-capacity') required = row.required;},
    geographyReportLoader: async ({api}) => {
    assert.equal(typeof api, 'function'); assert.notEqual(api, f.api);
    loading = true;
    return loadGeographicReport({api, repo: f.options().repo, runId: 12,
      artifactName: 'geography-durable-capacity-ticket-12', expectedHash: 'a'.repeat(64), token: 'fixture-token',
      fetchImpl: async () => {downloads++; throw Error('Unexpected download');}});
  }}), exactCapacity ? /inventory grew beyond safe request bound/ : /Missing or expired geographic artifact/);
  if (exactCapacity) assert.ok(artifactCalls > 0 && artifactCalls < 100);
  else assert.equal(artifactCalls, 100, 'ordinary complete inventory remains bounded even with quota headroom');
  assert.equal(downloads, 0);
  assert.equal(f.writes.filter(row => row.method === 'PUT').length, 0);
});
test('capacity excludes blob REST requests only after exact transport proves the entire bound inventory',async()=>{
 for(const complete of [false,true]){
  const f=fixture();let rows;
  f.api.prefetchGitBlobs=async(repo,inventory)=>{assert.equal(repo,f.repo);rows=inventory;};
  f.api.hasGitBlobs=(repo,inventory)=>complete&&inventory===rows;
  const value=await inventoryFinalEvidence({api:f.api,repo:f.repo,pr:f.pr,issue:f.issue,files:f.files,policy:{version:1,mode:'enforce-new',activation_time:'2020-01-01T00:00:00Z'}});
  assert(rows.length>0);assert.equal(value.exact_git_transport,complete);assert.equal(value.blob_calls,complete?0:rows.length);
 }
});


// Execute the actual transport and final wrappers, substituting only the network
// fetch with exact fixture blobs written into the disposable bare Git store.
function finalTransportFixture(mode = 'complete', f = fixture()) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'final-planning-transport-'));
  const origin = f.api, events = []; let admission, fetches = 0;
  const http = async (route, method = 'GET', ...args) => {
    admission?.({route, method}); events.push({kind: 'http', route});
    return origin(route, method, ...args);
  };
  http.setHTTPAdmission = hook => {admission = hook; return () => {admission = null;};};
  const transport = gitBlobTransport(http, {repo: f.repo, token: 'synthetic-transport-token', directory,
    execute: (command, args, options) => {
      if (!args.includes('fetch')) return execFileSync(command, args, options);
      fetches++; events.push({kind: 'fetch'});
      const requested = args.slice(args.indexOf('https://github.com/' + f.repo + '.git') + 1);
      for (const sha of mode === 'incomplete' ? requested.slice(0, -1) : requested) {
        const blob = f.blobs.get(sha); assert.ok(blob, 'fetch must request only the tree-bound inventory');
        execFileSync('git', [args[0], 'hash-object', '-w', '--stdin'],
          {input: Buffer.from(blob.content, 'base64'), env: options.env});
      }
      return Buffer.alloc(0);
    }});
  f.api = (...args) => transport.api(...args);
  for (const name of ['setHTTPAdmission', 'prefetchGitBlobs', 'hasGitBlobs']) {
    if (mode === 'missing' && name !== 'setHTTPAdmission') continue;
    f.api[name] = function (...args) {
      assert.equal(this, f.api, `${name} must preserve its original receiver through every wrapper`);
      if (mode === 'declined' && name === 'prefetchGitBlobs') return;
      if (mode === 'declined' && name === 'hasGitBlobs') return false;
      return transport.api[name](...args);
    };
  }
  return {f, events, get fetches() {return fetches;}, close() {
    transport.close(); assert.deepEqual(fs.readdirSync(directory), []); fs.rmdirSync(directory);
  }};
}

test('real pacing prefetches complete bound blobs before proof classifier reads without losing call accounting', async () => {
  const t = finalTransportFixture('complete', evidenceFailedProof(fixture())), {f} = t;
  f.startCapacity = 2000; let classifierReads = 0;
  const output = f.authored.find(row => row.path.endsWith('/result.json'));
  try {
    const options = {...f.options(), proofRunId: 44, proofRunAttempt: 1,
      proofApplicabilityInventory: async ({api}) => {
        classifierReads++; assert.equal(t.fetches, 1, 'initial inventory must prefetch before the classifier');
        const before = t.events.length;
        assert.equal((await api(`/repos/${f.repo}/git/blobs/${output.sha}`)).sha, output.sha);
        assert.equal(t.events.length, before, 'classifier must reuse authenticated transport without REST');
      }};
    const result = await paceFinalValidation(options, {inspect: inspectMerge});
    assert.equal(classifierReads, 2); assert.equal(t.fetches, 1);
    assert.equal(result.receipt.inventory.exact_git_transport, true);
    assert.equal(result.receipt.inventory.blob_calls, 0);
    assert.equal(result.receipt.proof_calls, 3, 'run, jobs and classifier logical reads remain counted');
    assert.ok(result.receipt.metadata_calls > 0); assert.equal(Object.hasOwn(result.receipt, 'admission_calls'), false);
    assert.equal(t.events.filter(row => row.kind === 'http' && row.route.includes('/git/blobs/')).length, 1,
      'only the manifest is fetched by REST before the complete inventory is known');
    assert.ok(f.calls.filter(row => row.route.endsWith('/pulls/23')).length >= 3,
      'mutable PR authority is reread after capacity observation');
    assert.equal(f.writes.length, 0, 'pacing alone does not merge');
  } finally {t.close();}
});

test('actual final completion retains bulk prefetch across planning retry and declines absent/incomplete capability', async () => {
  for (const mode of ['complete', 'missing', 'declined']) {
    const t = finalTransportFixture(mode), {f} = t;
    f.startCapacity = 24;
    try {
      const result = await f.complete();
      assert.equal(result.accepted, true); assert.equal(result.final_capacity.planning_attempts, 2);
      const inventory = result.final_capacity.inventory;
      assert.equal(inventory.exact_git_transport, mode === 'complete');
      assert.equal(inventory.blob_calls, mode === 'complete' ? 0 : f.blobs.size);
      assert.equal(t.fetches, mode === 'complete' ? 1 : 0);
      assert.equal(t.events.filter(row => row.kind === 'http' && row.route.includes('/git/blobs/')).length,
        mode === 'complete' ? 1 : f.blobs.size);
      assert.equal(f.writes.filter(row => row.route.endsWith('/merge')).length, 1);
    } finally {t.close();}
  }
});

test('incomplete actual transport and changed mutable authority cannot reach merge after feature forwarding', async () => {
  for (const mode of ['incomplete', 'complete']) {
    const t = finalTransportFixture(mode), {f} = t;
    f.startCapacity = 2000;
    try {
      await assert.rejects(f.complete({capacityObserver: row => {
        if (mode === 'complete' && row.phase === 'final-capacity') f.issue.body += '\nChanged acceptance';
      }}), mode === 'incomplete' ? /Exact immutable Git transport failed/ : /Authority or tested base changed/);
      assert.equal(t.fetches, 1); assert.equal(f.writes.length, 0);
    } finally {t.close();}
  }
});

// A real single-entry stored ZIP exercises the production report loader through
// prepare, measured capacity waiting and final integration; no GIS is executed.
function storedReportArchive(raw) {
  const name = Buffer.from('geography-check.json'), crc = crc32(raw);
  const local = Buffer.alloc(30); local.writeUInt32LE(0x04034b50); local.writeUInt16LE(20, 4);
  local.writeUInt32LE(crc, 14); local.writeUInt32LE(raw.length, 18); local.writeUInt32LE(raw.length, 22);
  local.writeUInt16LE(name.length, 26);
  const central = Buffer.alloc(46); central.writeUInt32LE(0x02014b50); central.writeUInt16LE(20, 6);
  central.writeUInt32LE(crc, 16); central.writeUInt32LE(raw.length, 20); central.writeUInt32LE(raw.length, 24);
  central.writeUInt16LE(name.length, 28);
  const end = Buffer.alloc(22); end.writeUInt32LE(0x06054b50); end.writeUInt16LE(1, 8); end.writeUInt16LE(1, 10);
  end.writeUInt32LE(46 + name.length, 12); end.writeUInt32LE(30 + name.length + raw.length, 16);
  return Buffer.concat([local, name, raw, central, name, end]);
}
function carriedGeographyFixture() {
  const f = geographyReuseFixture();
  f.originRun = {...structuredClone(f.proofRun), conclusion: 'cancelled', pull_requests: []};
  f.originJobs = [structuredClone(f.proofJobs.find(job => job.name === 'geography'))];
  Object.assign(f.originJobs[0], {run_id: 44, run_attempt: 1, head_sha: f.head});
  f.proofRun.run_attempt = 2;
  f.proofJobs.find(job => job.name === 'geography').id = 66;
  f.publishReport = report => {
  const raw = Buffer.from(JSON.stringify(report) + '\n');
  f.zip = storedReportArchive(raw);
  f.artifact = {id: 77, name: 'proposed-geography-23-1', expired: false, size_in_bytes: f.zip.length,
    digest: 'sha256:' + reportHash(f.zip), workflow_run: {id: 44, head_sha: f.head}};
  f.log = Buffer.from([JSON.stringify({report_bytes: raw.length, report_sha256: reportHash(raw)}),
    'SHA256 digest of uploaded artifact zip is ' + reportHash(f.zip),
    `Artifact proposed-geography-23-1 has been successfully uploaded! Final size is ${f.zip.length} bytes. Artifact ID is 77`].join('\n'));
  };
  f.publishReport(f.report);
  const previous = f.api; f.transportCalls = []; let admission;
  f.api = async (route, method = 'GET', body) => {
    admission?.({route, method}); f.transportCalls.push(route);
    if (route === '/rate_limit') {
      f.capacityReads = (f.capacityReads ?? 0) + 1;
      // Planning starts admitted, the final measured bound waits once, then
      // receives exactly the observed requirement rather than arbitrary slack.
      return quota(f.capacityReads === 2 ? 0 : f.capacityReads > 2 ? f.required : 2000);
    }
    if (route.endsWith('/actions/runs/44/attempts/1')) return structuredClone(f.originRun);
    if (route.includes('/actions/runs/44/attempts/1/jobs')) return {jobs: structuredClone(f.originJobs)};
    if (route.includes('/actions/runs/44/attempts/2/jobs')) return {jobs: structuredClone(f.proofJobs)};
    if (route.includes('/actions/runs/44/artifacts?')) return {total_count: 1, artifacts: [structuredClone(f.artifact)]};
    if (route.endsWith('/logs') || route.endsWith('/zip')) return new Response(null, {status: 302, headers: {
      location: `https://results.blob.core.windows.net/${route.endsWith('/zip') ? 'zip' : route.includes('/55/') ? 'origin' : 'carried'}?fixture`
    }});
    return previous(route, method, body);
  };
  f.api.setHTTPAdmission = hook => {admission = hook; return () => {admission = null;};};
  f.api.jobLogRedirect = route => f.api(route);
  f.api.artifactRedirect = route => f.api(route);
  f.fetchImpl = async (url, init) => {
    assert.equal(init.headers, undefined); assert.equal(init.redirect, 'error');
    return new Response(url.includes('/zip?') ? f.zip : url.includes('/origin?') ? f.originLog ?? f.log : f.log);
  };
  f.prepare = () => prepareIntegration({...f.options(), geographyProofLoader: args => prepareGeographyProof({
    ...args, token: 'synthetic', fetchImpl: f.fetchImpl})});
  f.reuse = (prepared, extra = {}) => completeIntegration({...f.options(), finalCapacity: true,
    integrationResult: 'skipped', geographyResult: 'skipped', testedCandidate: f.candidate,
    proofRunId: prepared.proof.run_id, proofRunAttempt: prepared.proof.run_attempt,
    geographyProof: prepared.geography_proof,
    capacityObserver: row => {if (row.phase === 'final-capacity') f.required = row.required;},
    capacityTiming: {...clock(), sleep: async () => {f.phase = 'after'; f.mutateOnWait?.();}},
    geographyReportLoader: ({api}) => loadGeographicReport({api, repo: f.repo, token: 'synthetic',
      runId: prepared.geography_proof.run_id, artifactName: prepared.geography_proof.artifact_name,
      expectedHash: prepared.geography_proof.report_sha256, source: prepared.geography_proof, fetchImpl: f.fetchImpl}), ...extra});
  return f;
}
test('actual loaders preserve attempt-one geography through attempt-two code, measured capacity wait and merge', async () => {
  const f = carriedGeographyFixture(), prepared = await f.prepare();
  assert.equal(prepared.proof.run_attempt, 2); assert.equal(prepared.proof.geography_job_id, 66);
  assert.equal(prepared.geography_proof.run_attempt, 1); assert.equal(prepared.geography_proof.job_id, 55);
  assert.equal(prepared.geography_proof.current_run_attempt, 2); assert.equal(prepared.geography_proof.current_job_id, 66);
  const result = await f.reuse(prepared);
  assert.equal(result.accepted, true); assert.equal(result.proof.run_attempt, 2);
  assert.equal(result.geography.source.run_attempt, 1); assert.equal(result.geography.source.job_id, 55);
  assert.equal(result.geography.candidate_commit, f.head); assert.equal(result.tested_candidate, f.candidate);
  assert.equal(result.final_capacity.remaining, result.final_capacity.required);
  assert.equal(result.final_capacity.proof_calls, 4, 'two current-proof reads plus exact original run and jobs');
  assert.equal(result.final_capacity.observations, 2);
  assert.equal(f.transportCalls.filter(route => route.endsWith('/attempts/1')).length, 4,
    'origin is authenticated at prepare, before and after capacity wait, and final validation');
  assert.equal(f.writes.filter(row => row.route.endsWith('/merge')).length, 1);
});

test('actual carried prepare rejects missing, multiple, future and foreign receipts but keeps valid latest code', async () => {
  for (const mutate of [
    f => {f.log = Buffer.from('missing');},
    f => {f.log = Buffer.concat([f.log, Buffer.from('\n'), f.log]);},
    f => {f.log = Buffer.from(f.log.toString().replace('proposed-geography-23-1', 'proposed-geography-23-3'));},
    f => {f.log = Buffer.from(f.log.toString().replace('proposed-geography-23-1', 'proposed-geography-24-1'));},
    f => {f.originLog = Buffer.from(f.log.toString().replace('Artifact ID is 77', 'Artifact ID is 78'));},
    f => {f.originJobs[0].steps.pop();}, f => {f.originRun.head_sha = 'e'.repeat(40);},
    f => {f.publishReport({...f.report, baseline_commit: 'e'.repeat(40)});},
    f => {f.publishReport({...f.report, trusted_code_commit: 'e'.repeat(40)});},
    f => {f.publishReport({...f.report, candidate_commit: f.candidate});}
  ]) {
    const f = carriedGeographyFixture(); mutate(f); const prepared = await f.prepare();
    assert.equal(prepared.proof.run_attempt, 2); assert.equal(prepared.geography_proof, null);
    assert.equal(f.writes.length, 0);
  }
});

test('actual final carried reuse rejects identity, source, artifact and report substitutions', async () => {
  for (const mutate of [
    (f, p) => {p.geography_proof.tree = 'e'.repeat(40);},
    (f, p) => {p.geography_proof.head = 'e'.repeat(40);},
    (f, p) => {p.geography_proof.baseline = 'e'.repeat(40);},
    (f, p) => {p.geography_proof.current_job_id++;},
    (f, p) => {p.geography_proof.job_id++;},
    f => {f.originJobs[0].id++;}, f => {f.originJobs[0].run_id++;},
    f => {f.originJobs[0].run_attempt++;}, f => {f.originJobs[0].head_sha = 'e'.repeat(40);},
    f => {f.originRun.id++;}, f => {f.originRun.run_attempt++;},
    f => {f.originRun.head_sha = 'e'.repeat(40);},
    f => {f.originJobs[0].steps[2].conclusion = 'failure';},
    f => {f.proofJobs.find(job => job.name === 'geography').conclusion = 'failure';},
    f => {f.proofRun.run_attempt++;}, f => {f.artifact.expired = true;},
    f => {f.artifact.id++;}, f => {f.artifact.workflow_run.head_sha = 'e'.repeat(40);},
    f => {f.zip = storedReportArchive(Buffer.from('{}'));}
  ]) {
    const f = carriedGeographyFixture(), prepared = await f.prepare(); mutate(f, prepared);
    await assert.rejects(f.reuse(prepared)); assert.equal(f.writes.length, 0);
  }
});

test('origin identity and latest successful geography remain fresh across actual final capacity waiting', async () => {
  for (const mutate of [f => {f.originJobs[0].id++;}, f => {f.originRun.head_sha = 'e'.repeat(40);},
    f => {f.originJobs[0].steps.pop();}, f => {f.proofRun.run_attempt++;},
    f => {f.proofJobs.find(job => job.name === 'geography').steps[2].conclusion = 'skipped';},
    f => {f.artifact.expired = true;}]) {
    const f = carriedGeographyFixture(), prepared = await f.prepare();
    f.mutateOnWait = () => mutate(f);
    await assert.rejects(f.reuse(prepared)); assert.equal(f.phase, 'after'); assert.equal(f.writes.length, 0);
  }
});


// Real HTTP admission and ETag revalidation, with only the network replaced.
// Current issue authority is still reread after capacity is observed.
function quotaCompletionFixture({retry = false, deplete = false} = {}) {
  const f = fixture(), original = f.api, timing = clock(), attempts = [], observations = [];
  let remaining = 2000, probes = 0, retried = false, validationStart = 0, finalAuthority = false;
  const headers = () => ({'x-ratelimit-limit': '2000', 'x-ratelimit-remaining': String(remaining),
    'x-ratelimit-reset': '3600', 'x-ratelimit-resource': 'core', etag: '"unchanged"'});
  f.api = githubAPI('synthetic-quota-token', {...timing, minimumRemaining: 16, readWaitMs: 60000,
    onRequest: row => attempts.push({route: row.route, status: row.status, remaining: row.capacity.remaining}),
    fetchImpl: async (url, init) => {
      const route = url.slice('https://api.github.com'.length), name = route.split('?')[0];
      if (name === `/repos/${f.repo}`) {
        probes++; remaining--; if (probes === 2) validationStart = attempts.length + 1;
        return Response.json({}, {headers: headers()});
      }
      const validation = probes >= 2;
      if (retry && validation && !retried && name.endsWith('/pulls/23')) {
        retried = true; remaining--;
        return Response.json({message: 'secondary rate limit'}, {status: 403,
          headers: {...headers(), 'retry-after': '1'}});
      }
      if (validation && name.endsWith('/issues/1183')) {
        finalAuthority = true;
        if (deplete) remaining = 16; // Another consumer exhausted most shared capacity.
      }
      if (init.headers['If-None-Match']) return new Response(null, {status: 304, headers: headers()});
      remaining--;
      const value = await original(route, init.method, init.body ? JSON.parse(init.body) : undefined);
      return Response.json(value, {headers: headers()});
    }});
  const complete = extra => f.complete({capacityTiming: timing, capacityObserver: row => observations.push(row), ...extra});
  return {f, attempts, observations, complete, get validationAttempts() {return attempts.slice(validationStart);},
    get remaining() {return remaining;}, get finalAuthority() {return finalAuthority;}};
}

for (const retry of [false, true]) test(`actual final HTTP uses fresh quota and retains 304/retry guards: ${retry}`, async t => {
  const q = quotaCompletionFixture({retry}), result = await q.complete();
  const capacity = result.final_capacity;
  assert.equal(result.accepted, true);
  assert.equal(capacity.validation_call_bound, capacity.remaining - 16);
  assert.equal(capacity.validation_call_bound_source, 'observed-remaining-minus-recovery-reserve');
  assert.equal(capacity.recovery_call_reserve, 16);
  assert(q.validationAttempts.length < capacity.validation_call_bound);
  assert(q.validationAttempts.some(row => row.status === 304), 'authority was actually conditionally reread');
  assert.equal(q.validationAttempts.filter(row => row.status === 403).length, retry ? 1 : 0);
  assert.equal(q.f.writes.filter(row => row.method === 'PUT').length, 1);
  assert(q.remaining >= 16);
  t.diagnostic(JSON.stringify({estimated_required: capacity.required, observed_remaining: capacity.remaining,
    validation_call_bound: capacity.validation_call_bound, actual_validation_attempts: q.validationAttempts.length,
    conditional_revalidations: q.validationAttempts.filter(row => row.status === 304).length,
    retry_rejections: q.validationAttempts.filter(row => row.status === 403).length}));
});

test('actual final authority stops on newly observed concurrent depletion and preserves recovery', async () => {
  const q = quotaCompletionFixture({deplete: true});
  await assert.rejects(q.complete(), error => error.quotaAdmission?.remaining === 16);
  assert(q.finalAuthority, 'depletion must happen after final capacity observation');
  assert.equal(q.f.writes.length, 0);
  assert(q.validationAttempts.length < q.observations.at(-1).remaining - 16,
    'live quota must refuse before the otherwise sufficient fixed attempt allowance');
});


test('direct pacing adapter also uses the observed finite allowance and retains exhaustion', async () => {
  const f = fixture(); f.startCapacity = 2000;
  const {api, receipt} = await paceFinalValidation(f.options(), {inspect: inspectMerge});
  assert.equal(receipt.validation_call_bound, receipt.remaining - 16);
  let reads = 0;
  for (;;) {
    try {await api(`/repos/${f.repo}/pulls/23`); reads++;}
    catch (error) {assert.equal(error.requestBudget, true); break;}
  }
  assert(reads > receipt.required - 16);
  assert(reads < receipt.validation_call_bound, 'fresh post-observation gates consume the same allowance');
  assert.equal(f.writes.length, 0);
});

test('predecessor applicability retains authenticated redirect capabilities and budgets each log/archive read',async()=>{
  const f=evidenceFailedProof(fixture());f.startCapacity=2000;const redirects=[];let inventories=0;
  for(const name of ['artifactRedirect','jobLogRedirect'])f.api[name]=async route=>{redirects.push({name,route});return {status:302,location:'https://example.invalid/fixture'};};
  const options={...f.options(),proofRunId:44,proofRunAttempt:1,
    proofApplicabilityInventory:async({api,run,jobs})=>{
      inventories++;assert.equal(run.id,44);assert.ok(Array.isArray(jobs));
      await api.jobLogRedirect(`/repos/${f.repo}/actions/jobs/7/logs`);
      await api.artifactRedirect(`/repos/${f.repo}/actions/artifacts/9/zip`);
    }};
  const result=await paceFinalValidation(options,{inspect:inspectMerge});
  assert.equal(inventories,2);assert.equal(redirects.length,4);
  assert.equal(result.receipt.proof_calls,4,'run, jobs, original log and original archive are budgeted');
});

test('original PR merge candidate survives prepare and final acceptance without becoming reviewed head', async () => {
  const f = geographyReuseFixture(), originCandidate = 'e'.repeat(40), original = f.api;
  Object.assign(f.source, {workflow_path: WORKFLOW_PATH, event: 'pull_request', workflow_head: f.head,
    candidate_commit: originCandidate});
  f.report.candidate_commit = originCandidate;
  Object.assign(f.proofJobs.find(job => job.name === 'geography'), {run_id: 44, run_attempt: 1, head_sha: f.head});
  f.api = async (route, ...args) => {
    if (route.endsWith('/actions/runs/44/attempts/1')) return structuredClone(f.proofRun);
    if (route.endsWith(`/git/commits/${originCandidate}`)) return {sha: originCandidate,
      tree: {sha: f.source.tree}, parents: [{sha: f.base}, {sha: f.head}]};
    return original(route, ...args);
  };
  const prepared = await f.prepare();
  assert.equal(prepared.geography_proof.candidate_commit, originCandidate);
  const result = await f.reuse({geographyProof: prepared.geography_proof});
  assert.equal(result.accepted, true);
  assert.equal(result.reviewed_head, f.head);
  assert.equal(result.tested_candidate, f.candidate);
  assert.equal(result.geography.candidate_commit, originCandidate);
  assert.equal(result.geography.source.candidate_commit, originCandidate);
  assert.equal(result.geography.source.head, f.head);
  assert.equal(f.writes.filter(row => row.route.endsWith('/merge')).length, 1);
});
