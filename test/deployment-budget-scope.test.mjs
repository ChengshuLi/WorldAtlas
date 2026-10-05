import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {packageResearchInputs, BUILD_MODULE_PINS} from '../scripts/package-research-inputs.mjs';
import {classifyBudgetFiles, deploymentBudgetProfile, githubBudgetAPI} from '../scripts/classify-deployment-budget.mjs';

const repository = 'ChengshuLi/WorldAtlas', before = 'a'.repeat(40), after = 'b'.repeat(40);
const file = (filename, extra = {}) => ({filename, status: 'modified', ...extra});
const event = {repository: {full_name: repository}, pull_request: {number: 5, base: {sha: before}, head: {sha: after}}};
const profile = (api, extra = {}) => deploymentBudgetProfile({event, eventName: 'pull_request', repository, api, ...extra});
const metadata = count => ({base: {sha: before}, head: {sha: after}, changed_files: count});
const comparison = files => ({base_commit: {sha: before}, status: 'ahead', commits: [{sha: after}], files});

test('only explicit coordination controls, plain docs and engineering receipts avoid a package build', () => {
  assert.equal(classifyBudgetFiles([
    file('scripts/integration-proof.mjs'), file('scripts/run-worker-merge.mjs'),
    file('.github/workflows/worker-merge.yml'), file('.github/workflows/merge-integration-checks.yml'),
    file('test/merge-integration.test.mjs'), file('docs/WORKER_COORDINATION.md'),
    file('README.md'), file('coordination/engineering/example/result.json'),
  ]).full, false);
  for (const name of ['scripts/new-control.mjs', 'scripts/deployment-budget.mjs', 'scripts/classify-deployment-budget.mjs',
    'src/regional-import-gate.js', 'hosted/server.js', 'data/world-index.json', 'drizzle/0001.sql',
    '.openai/hosting.json', 'vite.config.mjs', 'arbitrary-root.js', 'package.json', 'package-lock.json',
    'requirements.txt', 'public/a.txt', 'docs/generated.json', '.github/workflows/deployment-budget.yml',
    '.github/workflows/neon-storage-migration.yml', '.github/workflows/unknown.yml',
    'coordination/engineering/example/run.mjs', 'docs/../src/main.md', 'README.md\n']) {
    assert.equal(classifyBudgetFiles([file(name)]).full, true, name);
  }
});

test('renamed or copied runtime origins cannot hide behind documentation or receipt destinations', () => {
  for (const status of ['renamed', 'copied']) {
    assert.equal(classifyBudgetFiles([file('docs/note.md', {status, previous_filename: 'src/main.js'})]).full, true);
    assert.throws(() => classifyBudgetFiles([file('docs/note.md', {status})]), /Missing rename/);
  }
  assert.equal(classifyBudgetFiles([file('docs/new.md', {status: 'renamed', previous_filename: 'docs/old.md'})]).full, false);
  assert.throws(() => classifyBudgetFiles([file('docs/x.md'), file('docs/x.md')]), /Invalid changed-file/);
});

test('PR inventory exhausts pages and catches a relevant path on a later page', async () => {
  const rows = Array.from({length: 100}, (_, n) => file(`docs/${n}.md`)), calls = [];
  const api = async route => {
    calls.push(route);
    if (!route.includes('/files?')) return metadata(101);
    return route.endsWith('page=1') ? rows : [file('docs/final.md')];
  };
  assert.equal((await profile(api)).full, false);
  assert.equal(calls.filter(route => route.includes('/files?')).length, 2);
  assert.equal(calls.filter(route => !route.includes('/files?')).length, 2);
  assert.equal((await profile(async route => !route.includes('/files?') ? metadata(101) :
    route.endsWith('page=1') ? rows : [file('docs/final.md', {status: 'renamed', previous_filename: 'hosted/server.js'})])).full, true);
});

test('PR missing pages, changed heads, unavailable lookup and malformed inventories default full', async () => {
  for (const api of [
    async route => route.includes('/files?') ? [] : metadata(1),
    async () => { throw Error('unavailable'); },
    async () => metadata(3000),
    async route => route.includes('/files?') ? [file('docs/x.md')] : {...metadata(1), head: {sha: before}},
    async route => route.includes('/files?') ? [file('docs/x.md', {status: 'renamed'})] : metadata(1),
  ]) assert.equal((await profile(api)).full, true);
  let reads = 0;
  assert.equal((await profile(async route => route.includes('/files?') ? [file('docs/x.md')] :
    ++reads === 1 ? metadata(1) : {...metadata(1), head: {sha: before}})).full, true);
});

test('push before/after comparison includes rename origins and fails full for missing or capped inventories', async () => {
  const push = {repository: {full_name: repository}, before, after};
  const run = (result, value = push) => profile(async () => result, {eventName: 'push', event: value});
  assert.equal((await run(comparison([file('scripts/issue-lease.mjs')]))).full, false);
  assert.equal((await run(comparison([file('docs/x.md', {status: 'renamed', previous_filename: 'data/world-index.json'})]))).full, true);
  for (const result of [undefined, {}, {...comparison([]), files: undefined}, {...comparison([]), commits: []},
    {...comparison([]), truncated: true}, comparison(Array.from({length: 300}, (_, n) => file(`docs/${n}.md`)))]) {
    assert.equal((await run(result)).full, true);
  }
  for (const value of [{...push, before: undefined}, {...push, before: '0'.repeat(40)}]) {
    assert.equal((await run(comparison([]), value)).full, true);
  }
  assert.equal((await profile(async () => { throw Error('network'); }, {eventName: 'push', event: push})).full, true);
});

test('API failures use bounded authenticated read-only requests', async () => {
  let request;
  await assert.rejects(githubBudgetAPI('/repos/ChengshuLi/WorldAtlas/pulls/5', {token: 'fixture',
    fetchImpl: async (url, options) => { request = {url, options}; return {ok: false, status: 503}; }}), /HTTP 503/);
  assert.equal(request.url, 'https://api.github.com/repos/ChengshuLi/WorldAtlas/pulls/5');
  assert.equal(request.options.headers.Authorization, 'Bearer fixture');
  assert.ok(request.options.signal);
  assert.equal(request.options.method, undefined);
});

test('workflow keeps trusted bootstrap fallback and runs package checks only when their inputs can change', () => {
  const source = fs.readFileSync('.github/workflows/deployment-budget.yml', 'utf8');
  const [trusted, candidate] = source.split('  package:\n');
  assert.match(candidate, /needs: classify\n    # .+\n    if: always\(\)/);
  assert.match(trusted, /ref: \$\{\{ github.event.pull_request.base.sha \|\| github.event.before \}\}/);
  assert.match(trusted, /node trusted\/scripts\/classify-deployment-budget.mjs/);
  assert.match(trusted, /echo 'full=true'/);
  assert.match(trusted, /persist-credentials: false/);
  assert.doesNotMatch(trusted, /cache: npm|setup-python|npm ci/);
  assert.match(trusted, /pull-requests: read/);
  assert.doesNotMatch(candidate, /GH_TOKEN|pull-requests: write|contents: write/);
  assert.match(candidate, /cache: \$\{\{ needs.classify.outputs.full != 'false' && 'npm' \|\| '' \}\}/);
  for (const step of ['npm ci --no-audit --no-fund', 'python -m pip install -r requirements.txt']) {
    assert.ok(candidate.includes(`run: ${step}\n        if: needs.classify.outputs.full != 'false'`));
  }
  assert.match(candidate, /Build and enforce archive\/file reserves without publishing\n        if: needs.classify.outputs.full != 'false'\n        run: npm run build:hosted/);
  assert.match(candidate, /run: node --test test\/deployment-budget.test.mjs test\/deployment-budget-scope.test.mjs\n        if: needs.classify.outputs.full != 'false'/);
  assert.doesNotMatch(candidate, /sparse-checkout:|Checkout only Node/);
  assert.match(candidate, /path: .cache\/deployment-budget.json/);
  const block = [...trusted.matchAll(/sparse-checkout: \|\n((?:            .+\n)+)/g)][0][1];
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'atlas-budget-focused-'));
  try {
    for (const entry of block.trim().split('\n').map(line => line.trim())) {
      assert.ok(!['package-lock.json', 'requirements.txt'].includes(entry));
      fs.mkdirSync(path.dirname(path.join(directory, entry)), {recursive: true});
      fs.copyFileSync(entry, path.join(directory, entry));
    }
    assert.equal(fs.existsSync(path.join(directory, 'node_modules')), false);
    assert.equal(fs.existsSync(path.join(directory, 'data')), false);
    const result = spawnSync(process.execPath, ['--input-type=module', '-e', "import {classifyBudgetFiles} from './scripts/classify-deployment-budget.mjs'; if (classifyBudgetFiles([{filename:'docs/test.md',status:'added'}]).full) process.exit(1);"], {
      cwd: directory, encoding: 'utf8', env: {PATH: process.env.PATH},
    });
    assert.equal(result.status, 0, result.stderr);
    assert.equal(result.stderr, '');
  } finally { fs.rmSync(directory, {recursive: true, force: true}); }
});

function inputFixture(extra = {}) {
  const files = {
    'data/granularity-audit.json': {input_sha256: {}},
    'data/world-index.json': {parts: ['world-part.json']},
    'data/world-review.json': {location_parts: ['world-review/part.json']},
    'data/hierarchy-report.json': {change_parts: ['hierarchy-part.json']},
    'data/ownership-history/index.json': {execution_algorithms: [], initial_execution: {algorithms: []}},
    'data/reference-attributes/index.json': {},
    'data/ownership-runtime/index.json': {},
    ...extra,
  };
  if (files['data/ownership-history/index.json']) files['data/ownership-history/index.json'] = {execution_algorithms: [], initial_execution: {algorithms: []}, ...files['data/ownership-history/index.json']};
  const blobs = new Map(), tree = Object.entries(BUILD_MODULE_PINS).map(([name, sha]) => ({path: name, sha, size: 0, mode: '100644', type: 'blob'}));
  for (const [name, value] of Object.entries(files)) {
    const raw = Buffer.from(JSON.stringify(value));
    const sha = createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
    tree.push({path: name, sha, size: raw.length, mode: '100644', type: 'blob'});
    blobs.set(sha, {sha, size: raw.length, encoding: 'base64', content: raw.toString('base64')});
  }
  return {tree, blobs, api: async route => route.includes('/git/trees/')
    ? {truncated: false, tree} : blobs.get(route.split('/').at(-1))};
}

test('both research lanes skip package compilation only after immutable build-input proof', async () => {
  const fixture = inputFixture();
  for (const name of ['data/regional-review/example/source.json', 'research/geography/example/reproduce.py',
    'research/campaigns/example/observations.json']) {
    assert.equal(classifyBudgetFiles([file(name)]).full, true, 'proof required');
    const api = async route => route.includes('/git/') ? fixture.api(route) :
      route.includes('/files?') ? [file(name)] : metadata(1);
    assert.equal((await profile(api)).full, false, name);
    const push = {repository: {full_name: repository}, before, after};
    assert.equal((await profile(async route => route.includes('/git/') ? fixture.api(route) : comparison([file(name)]),
      {eventName: 'push', event: push})).full, false, name);
  }
});

test('public review attachments, annotation plans, audited inputs and copied partitions remain package inputs', async () => {
  const attachment = 'data/regional-review/example/public.json';
  for (const fixture of [
    inputFixture({'data/source-quality-reviews/index.json': {parts: [{path: 'annotations.json'}]},
      'data/annotations.json': {feature_annotations: [{metadata_patch: {source_quality_review: {
        public_evidence_files: [{path: attachment.slice(5)}]}}}]}}),
    inputFixture({'data/source-quality-reviews/index.json': {parts: [{path: attachment.slice(5)}]}, [attachment]: {feature_annotations: []}}),
    inputFixture({'data/granularity-audit.json': {input_sha256: {[attachment.slice(5)]: 'a'.repeat(64)}}}),
    inputFixture({'data/world-index.json': {parts: [attachment.slice(5)]}}),
    inputFixture({'data/world-review.json': {location_parts: [attachment.slice(5)]}}),
    inputFixture({'data/macro-foundation/world-review-projection.json': {location_parts: [attachment.slice(5)]}}),
    inputFixture({'data/hierarchy-report.json': {change_parts: [attachment.slice(5)]}}),
    inputFixture({'data/reference-attributes/index.json': {parts: ['../regional-review/example/public.json']}}),
    inputFixture({'data/geographic-repair-evidence/index.json': {files: {'archive.json.gz': {archive_path: '../regional-review/example/public.json'}}}}),
    inputFixture({'data/ownership-history/index.json': {parts: [{path: '../%72egional-review/example/public.json'}]}}),
    inputFixture({'data/ownership-history/index.json': {parts: [{path: ' ../regional-review/example/public.json '} ]}}),
    inputFixture({'data/ownership-history/index.json': {parts: [{path: '../regional-re\tview/example/public.json'}]}}),
    inputFixture({'data/ownership-history/index.json': {parts: [{path: '../regional-review\\example\\public.json'}]}}),
  ]) {
    const inputs = await packageResearchInputs({route: `/repos/${repository}`, base: before, api: fixture.api});
    assert.equal(classifyBudgetFiles([file(attachment)], inputs).full, true);
    assert.equal(classifyBudgetFiles([file('research/geography/example/copy.json', {status: 'renamed', previous_filename: attachment})], inputs).full, true);
    assert.equal(classifyBudgetFiles([file('data/regional-review/example/private.json')], inputs).full, true, 'a referenced packet may have transitive inputs');
    assert.equal(classifyBudgetFiles([file('data/regional-review/unpublished/private.json')], inputs).full, false);
  }
  const inputs = new Set();
  for (const name of ['src/main.js', 'data/hierarchy.json', 'scripts/import-history.mjs', 'drizzle/0002.sql']) {
    assert.equal(classifyBudgetFiles([file('research/campaigns/example/note.md', {status: 'renamed', previous_filename: name})], inputs).full, true);
  }
});

test('unavailable, capped, malformed, symlinked or hash-mismatched package dependencies fail full', async () => {
  const fixture = inputFixture();
  for (const source of [
    async () => { throw Error('unavailable'); },
    async () => ({truncated: true, tree: fixture.tree}),
    async () => ({truncated: false, tree: []}),
    ...['vite.config.mjs', 'postcss.config.js', 'tsconfig.json', 'hosted/package.json', 'src/nested/package.json', 'src/nested/tsconfig.json', 'src/.postcssrc', 'public/new-asset.json', 'data/ownership-history/algorithms/exact/ellipsoidal_area.so'].map(file => async () => ({truncated: false, tree: [...fixture.tree, {path: file, type: 'blob', mode: '100644', sha: 'f'.repeat(40), size: 0}]})),
    ...['100644','120000','160000'].map(mode => async () => ({truncated:false,tree:[...fixture.tree,{path:'public',type:mode==='160000'?'commit':'blob',mode,sha:'f'.repeat(40),size:0}]})),
    ...['120000', '160000'].map(mode => async () => ({truncated: false, tree: [...fixture.tree, {path: 'data/typed-prepared-v1.json', type: mode === '120000' ? 'blob' : 'commit', mode, sha: 'f'.repeat(40), size: 0}]})),
    inputFixture({'data/ownership-history/index.json': {parts: [{path: 'file:../external.json'}]}}).api,
    inputFixture({'data/ownership-history/index.json': {parts: [{path: ' FILE:../external.json '}]}}).api,
    inputFixture({'data/ownership-history/index.json': {execution_algorithms: [{path: '../regional-review/example/majority.py', sha256: 'a'.repeat(64)}]}}).api,
    inputFixture({'data/ownership-history/index.json': {execution_algorithms: [{path: 'unknown/majority.py', sha256: 'a'.repeat(64)}]}}).api,
    ...['hosted/worker.js', 'src/main.js', 'src/pixel-worker.js', 'src/pixel-gpu-worker.js', 'database.mjs', 'scripts/boundary-version-hash.py', 'data/ownership-history/algorithms/exact/majority.py'].map(file => async route => route.includes('/git/trees/') ? {truncated: false, tree: fixture.tree.map(row => row.path === file ? {...row, sha: 'f'.repeat(40)} : row)} : fixture.api(route)),
    async route => route.includes('/git/trees/') ? {truncated: false, tree: fixture.tree.map(row => ({...row, mode: '120000'}))} : fixture.api(route),
    async route => route.includes('/git/trees/') ? fixture.api(route) : {...await fixture.api(route), content: Buffer.from('{}').toString('base64')},
    inputFixture({'data/world-review.json': 'invalid manifest'}).api,
    inputFixture({'data/world-index.json': {parts: 'invalid inventory'}}).api,
    inputFixture({'data/source-quality-reviews/index.json': {parts: [{path: '../research.json'}]}}).api,
    inputFixture({'data/source-quality-reviews/index.json': {parts: [{path: 'missing.json'}]}}).api,
  ]) {
    const result = await profile(async route => route.includes('/git/') ? source(route) :
      route.includes('/files?') ? [file('research/campaigns/example/source.json')] : metadata(1));
    assert.equal(result.full, true); assert.equal(result.fallback, true);
  }
});


test('unreachable ordinary source modules do not invalidate unchanged package readers', async () => {
  const fixture = inputFixture();
  const files = ['hosted/cloudflare-access.js', 'hosted/cloudflare-worker.js', 'hosted/footprint-versions.js',
    'hosted/records-constraints.sql', 'hosted/retirement-constraints.sql', 'src/typed-client.js',
    'src/unimported.js', 'hosted/unimported.ts'];
  for (const file of files) assert.equal(Object.hasOwn(BUILD_MODULE_PINS, file), false, file);
  const api = async route => route.includes('/git/trees/') ? {truncated:false, tree:[...fixture.tree,
    ...files.map(file => ({path:file, type:'blob', mode:'100644', sha:'f'.repeat(40), size:0}))]} : fixture.api(route);
  const result = await profile(async route => route.includes('/git/') ? api(route) :
    route.includes('/files?') ? [file('research/campaigns/example/source.json')] : metadata(1));
  assert.equal(result.full, false);
  // Runtime edits themselves retain full checks, even if their module is absent
  // from the hosted package graph; this only permits later unrelated research.
  assert.equal(classifyBudgetFiles([file('hosted/cloudflare-access.js')], new Set()).full, true);
  for (const mode of ['120000','160000']) {
    const bad = async route => route.includes('/git/trees/') ? {truncated:false, tree:[...fixture.tree,
      {path:'src/redirect', type:mode==='120000'?'blob':'commit',mode,sha:'f'.repeat(40),size:0}]} : fixture.api(route);
    const selected = await profile(async route => route.includes('/git/') ? bad(route) :
      route.includes('/files?') ? [file('research/geography/example/source.json')] : metadata(1));
    assert.equal(selected.full,true); assert.equal(selected.fallback,true);
  }
});
