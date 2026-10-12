import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import {readGeographyReuseTree, receivingMetadataDelta, ordinaryOriginalGeography, reusePRGeography, acquireGeographyReuseGraphs} from '../scripts/reuse-pr-geography.mjs';
import {WORKFLOW_PATH, successfulGeographyJob} from '../scripts/integration-proof.mjs';

const H = 'a'.repeat(40), P = 'b'.repeat(40), B = 'c'.repeat(40);
const PREFIX = 'coordination/engineering/example/';
const manifest = PREFIX + 'evidence-quality.json', readme = PREFIX + 'README.md';
const sha = raw => createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
function fixture() {
  const repo = 'owner/repo', branch = 'engineering/example', blobs = new Map(), commits = new Map(), trees = new Map();
  function entry(name, raw) {
    raw = Buffer.from(typeof raw === 'string' ? raw : JSON.stringify(raw)); const id = sha(raw);
    blobs.set(id, {sha: id, size: raw.length, encoding: 'base64', content: raw.toString('base64')});
    return {path: name, type: 'blob', mode: '100644', sha: id, size: raw.length};
  }
  const definition = {version: 1, inputs: ['.github/package-inputs.json', 'scripts/', 'src/'], optional_inputs: [],
    verification_paths: ['test/'], generated_outputs: ['dist/']};
  const entries = new Map([entry(WORKFLOW_PATH, 'approved workflow'), entry('.github/package-inputs.json', definition),
    entry('scripts/science.mjs', 'unchanged computational code'), entry('data/selection.json', '{}'),
    entry(manifest, {version: 1, outputs: []}), entry(readme, 'old receiving prose')].map(row => [row.path, row]));
  const source = {object: {sha: P, tree: {sha: 'd'.repeat(40)}, parents: [{sha: B}]}, entries};
  const current = {object: {sha: H, tree: {sha: 'e'.repeat(40)}, parents: [{sha: P}]}, entries: new Map(entries)};
  current.entries.set(readme, entry(readme, 'new receiving prose'));
  current.entries.set(manifest, entry(manifest, {version: 1, outputs: [{path: readme}]}));
  const trusted = {object: {sha: B, tree: {sha: 'f'.repeat(40)}, parents: []}, entries: new Map(entries)};
  for (const t of [source, current, trusted]) {commits.set(t.object.sha, t.object); trees.set(t.object.tree.sha, t);}
  const pr = {number: 7, state: 'open', body: 'Refs #8', head: {sha: H, ref: branch, repo: {full_name: repo}},
    base: {sha: B, ref: 'main', repo: {full_name: repo}}};
  const spec = {max_prs: 1, depends_on: [], scope: 'bounded fixture', mode: 'engineering', evidence_quality: {manifest_path: manifest}};
  const issue = {number: 8, state: 'open', body: `<!-- worldatlas-work:v1\n${JSON.stringify(spec)}\n-->`};
  const run = {id: 101, run_attempt: 1, head_sha: P, head_branch: branch, event: 'pull_request', path: WORKFLOW_PATH,
    repository: {full_name: repo}, head_repository: {full_name: repo}, status: 'completed', conclusion: 'failure',
    pull_requests: [{number: 7, head: {sha: H}}]}; // GitHub updates this embedded head after synchronization.
  const job = {id: 201, run_id: 101, run_attempt: 1, head_sha: P, name: 'geography', status: 'completed', conclusion: 'success',
    steps: ['Checkout trusted geographic checker', 'Install trusted geographic dependencies',
      'Check proposed geography with trusted baseline code', 'Run actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02']
      .map(name => ({name, status: 'completed', conclusion: 'success'}))};
  const report = {version: 1, method_id: 'worldatlas-trusted-geography-check-v1', baseline_commit: B, trusted_code_commit: B,
    candidate_commit: P, candidate_code_executed: false, published: false, source_approval: false, gate_status: 'passed', status: 'not-applicable'};
  const origin = {run_id: 101, run_attempt: 1, job_id: 201, head: P, tree: source.object.tree.sha, baseline: B,
    artifact_id: 301, artifact_name: 'proposed-geography-7-1', artifact_digest: 'a'.repeat(64), artifact_bytes: 1024,
    report_sha256: 'b'.repeat(64), report_bytes: 512};
  const f = {repo, branch, blobs, commits, trees, source, current, trusted, definition, entry, pr, issue, spec, run, job, report, origin,
    jobs: [job, {name: 'scope', status: 'completed', conclusion: 'failure'}], calls: [], inspections: [], acquisitions: [], loads: []};
  f.api = async route => {
    f.calls.push(route);
    if (route.endsWith('/pulls/7')) return structuredClone(f.pr);
    if (route.endsWith('/issues/8')) return structuredClone(f.issue);
    if (route.includes('/git/commits/')) return structuredClone(commits.get(route.split('/').at(-1)));
    if (route.includes('/git/trees/')) {
      const id = route.split('/').at(-1).split('?')[0], tree = trees.get(id);
      return {sha: id, truncated: false, tree: structuredClone([...tree.entries.values()]), ...f.treeOverride};
    }
    if (route.includes('/git/blobs/')) return structuredClone(blobs.get(route.split('/').at(-1)));
    if (route.includes('/actions/workflows/')) return {workflow_runs: [structuredClone(f.run)]};
    if (route.includes('/jobs?')) return {jobs: structuredClone(f.jobs)};
    if (route.endsWith('/actions/runs/101')) return {...structuredClone(f.run), ...f.finalRun};
    throw Error('unexpected route: ' + route);
  };
  f.options = {event: {repository: {full_name: repo}, pull_request: structuredClone(pr)}, repo, api: f.api, token: 'fixture-token',
    acquire: args => f.acquisitions.push(args), loadProof: async args => {f.loads.push(args); return {source: f.origin, report: f.report};},
    inspect: async args => {f.inspections.push(args); return {status: 'unchanged-selected-inputs', baseline_commit: args.baseline,
      candidate_commit: args.candidate, trusted_reader_policy_commit: args.trusted, candidate_code_executed: false, science_reexecuted: false,
      ...f.applicability};}};
  f.delta = () => receivingMetadataDelta({...f, api: f.api, manifestPath: manifest});
  f.runReuse = () => reusePRGeography(f.options);
  return f;
}

test('scope-failed predecessor reuses only authenticated original geography with fresh current applicability', async () => {
  const f = fixture(), before = JSON.stringify(f.report), result = await f.runReuse();
  assert.equal(result.status, 'reused-original');
  assert.equal(result.reviewed_head, H); assert.equal(result.source.head, P);
  assert.deepEqual(result.metadata_paths, [readme, manifest].sort());
  assert.equal(result.transferable_geography_authority, false);
  assert.equal(result.science_reexecuted, false);
  assert.equal(JSON.stringify(f.report), before, 'original report must never be relabelled');
  assert.equal(f.inspections.length, 1);
  assert.equal(f.inspections[0].baseline, P); assert.equal(f.inspections[0].trusted, B);
  assert.deepEqual(f.inspections[0].metadataPaths, result.metadata_paths);
  assert.equal(f.acquisitions.length, 1);
  assert.ok(f.calls.some(route => route.includes('/runs/101/attempts/1/jobs')));
});

test('full immutable delta cannot hide code/data/dependency/add/delete/rename or nonordinary metadata', async () => {
  for (const mutate of [
    f => f.current.entries.set('scripts/science.mjs', f.entry('scripts/science.mjs', 'changed')),
    f => f.current.entries.set('data/selection.json', f.entry('data/selection.json', '{"changed":true}')),
    f => f.current.entries.set('package-lock.json', f.entry('package-lock.json', '{}')),
    f => f.current.entries.delete(readme),
    f => f.source.entries.delete(readme),
    f => {f.current.entries.delete(readme); f.current.entries.set(PREFIX + 'old-README.md', f.entry(PREFIX + 'old-README.md', 'renamed'));},
    f => f.current.entries.set(readme, {...f.current.entries.get(readme), mode: '120000'}),
    f => f.current.entries.set(manifest, {...f.current.entries.get(manifest), mode: '100755'}),
    f => f.current.object.parents.push({sha: B}),
    f => {f.current.object.parents[0].sha = B;},
    f => f.trusted.entries.set(WORKFLOW_PATH, f.entry(WORKFLOW_PATH, 'different trusted workflow'))
  ]) {
    const f = fixture(); mutate(f); await assert.rejects(f.runReuse());
    assert.equal(f.inspections.length, 0); assert.equal(f.acquisitions.length, 0);
  }
});

test('receiving roles must be issue-owned ordinary bounded JSON/text and outside actual package roles', async () => {
  for (const mutate of [
    f => {f.issue.body = f.issue.body.replace(manifest, 'coordination/engineering/foreign/evidence-quality.json');},
    f => {f.definition.inputs.push(readme); for (const t of [f.source, f.current]) t.entries.set('.github/package-inputs.json', f.entry('.github/package-inputs.json', f.definition));},
    f => {f.definition.verification_paths.push(PREFIX); for (const t of [f.source, f.current]) t.entries.set('.github/package-inputs.json', f.entry('.github/package-inputs.json', f.definition));},
    f => f.current.entries.set(readme, f.entry(readme, 'x'.repeat(128 * 1024 + 1))),
    f => f.current.entries.set(readme, f.entry(readme, 'a\0b')),
    f => f.current.entries.set(manifest, f.entry(manifest, '{invalid')),
    f => {f.blobs.get(f.current.entries.get(readme).sha).content = Buffer.from('different bytes').toString('base64');}
  ]) {const f = fixture(); mutate(f); await assert.rejects(f.runReuse()); assert.equal(f.inspections.length, 0);}
});

test('tree completeness, duplicate identities and immutable commit identity are required', async () => {
  for (const mutate of [
    f => {f.treeOverride = {truncated: true};},
    f => {f.treeOverride = {sha: P};},
    f => {f.treeOverride = {tree: [...f.current.entries.values(), f.current.entries.get(readme)]};},
    f => {f.commits.set(H, {...f.current.object, sha: P});}
  ]) {const f = fixture(); mutate(f); await assert.rejects(readGeographyReuseTree({api: f.api, repo: f.repo, commit: H}));}
});

test('failed/skipped/missing/ambiguous original geography never becomes a reusable execution', async () => {
  for (const mutate of [
    f => {f.job.conclusion = 'failure';}, f => {f.job.status = 'in_progress';},
    f => {f.job.steps[2].conclusion = 'skipped';}, f => {f.job.steps.pop();},
    f => {f.job.steps.push({...f.job.steps[2]});}, f => {f.jobs.push(structuredClone(f.job));},
    f => {f.jobs = [];}, f => {f.job.head_sha = H;}, f => {f.job.run_attempt = 2;},
    f => {f.run.head_sha = H;}, f => {f.run.event = 'push';}, f => {f.run.path = 'foreign.yml';},
    f => {f.run.repository.full_name = 'foreign/repo';}, f => {f.run.pull_requests = [{number: 99}];},
    f => {f.run.head_branch = 'engineering/foreign';}, f => {f.run.status = 'in_progress';}
  ]) {const f = fixture(); mutate(f); await assert.rejects(f.runReuse()); assert.equal(f.inspections.length, 0);}
});

test('original report/source identities, baseline and ordinary unadjudicated pass remain mandatory', async () => {
  for (const mutate of [
    f => {f.report.baseline_commit = P;}, f => {f.report.trusted_code_commit = P;},
    f => {f.report.candidate_commit = H;}, f => {f.report.gate_status = 'failed';},
    f => {f.report.candidate_code_executed = true;}, f => {f.report.adjudication = {status: 'accepted'};},
    f => {f.origin.head = H;}, f => {f.origin.tree = f.current.object.tree.sha;},
    f => {f.origin.artifact_name = 'proposed-geography-8-1';},
    f => {f.options.loadProof = async () => null;},
    f => {f.options.loadProof = async () => {throw Error('missing or corrupt artifact');};}
  ]) {const f = fixture(); mutate(f); await assert.rejects(f.runReuse()); assert.equal(f.inspections.length, 0);}
});

test('actual input collector refusal and drift during validation require fresh scientific execution', async () => {
  for (const mutate of [
    f => {f.applicability = {status: 'full-check-required'};},
    f => {f.applicability = {baseline_commit: B};},
    f => {f.applicability = {candidate_commit: P};},
    f => {f.applicability = {trusted_reader_policy_commit: P};},
    f => {f.applicability = {science_reexecuted: true};},
    f => {f.finalRun = {run_attempt: 2};}, f => {f.finalRun = {status: 'in_progress'};},
    f => {f.finalRun = {conclusion: 'cancelled'};},
    f => {const inspect = f.options.inspect; f.options.inspect = async args => {const result = await inspect(args); f.pr.base.sha = P; return result;};},
    f => {const inspect = f.options.inspect; f.options.inspect = async args => {const result = await inspect(args); f.issue.body += '\nchanged acceptance'; return result;};}
  ]) {const f = fixture(); mutate(f); await assert.rejects(f.runReuse());}
});

test('workflow keeps source report upload separate and never advertises reused execution as fresh', () => {
  const text = fs.readFileSync(new URL('../.github/workflows/merge-integration-checks.yml', import.meta.url), 'utf8');
  const geography = text.slice(text.indexOf('  geography:\n'), text.indexOf('  regression:\n'));
  assert.match(geography, /timeout --kill-after=5s 180s node scripts\/reuse-pr-geography\.mjs/);
  assert.match(geography, /name: Check proposed geography with trusted baseline code\n\s+if: steps\.metadata_reuse\.outputs\.reused != 'true'/);
  assert.match(geography, /if: always\(\) && steps\.metadata_reuse\.outputs\.reused != 'true'/);
  assert.match(geography, /path: geography-reuse\.json/);
  assert.match(geography, /name: reused-geography-/);
  const f = fixture(); f.job.steps[2].conclusion = 'skipped';
  assert.equal(successfulGeographyJob([f.job]), null, 'new reused job grants no transferable original geography producer authority');
  assert.equal(ordinaryOriginalGeography(f.report, {baseline: B, head: P}), true);
});


test('graph acquisition proves warm parent/complete trees and scopes cold fetch credentials', () => {
  const warm = [];
  acquireGeographyReuseGraphs({directory: '/fixture', repo: 'owner/repo', head: H, token: 'fixture-token',
    execute: (cmd, args, options) => {warm.push({cmd, args, options}); return Buffer.from('');}});
  assert.equal(warm.length, 3);
  assert(warm.every(call => call.options.env.GIT_NO_LAZY_FETCH === '1'));
  assert(warm.some(call => call.args.includes(`${H}^`)));
  assert.equal(warm.filter(call => call.args.includes('ls-tree')).length, 2);
  const cold = [];
  acquireGeographyReuseGraphs({directory: '/fixture', repo: 'owner/repo', head: H, token: 'fixture-token',
    execute: (cmd, args, options) => {
      cold.push({cmd, args, options});
      if (args.includes('cat-file')) throw Error('cold immutable graph');
      return Buffer.from('');
    }});
  assert.equal(cold.length, 2);
  const fetch = cold[1];
  for (const flag of ['--no-replace-objects', '--no-tags', '--no-write-fetch-head', '--no-recurse-submodules',
    '--no-auto-maintenance', '--filter=blob:none', '--depth=2']) assert(fetch.args.includes(flag), flag);
  assert.deepEqual(fetch.args.slice(-2), ['https://github.com/owner/repo.git', H]);
  assert(fetch.args.includes('core.hooksPath=/dev/null'));
  assert(fetch.args.includes('credential.helper='));
  assert.equal(fetch.options.timeout, 30000);
  assert.equal(fetch.options.env.GIT_CONFIG_KEY_0, 'http.https://github.com/.extraheader');
  assert(!fetch.args.some(arg => arg.includes('fixture-token')));
});
