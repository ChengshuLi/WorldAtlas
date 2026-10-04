import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
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
    'coordination/engineering/example/run.mjs', 'docs/../src/main.md']) {
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

test('workflow keeps trusted bootstrap fallback, narrow focused inputs and mandatory real archive unit checks', () => {
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
  assert.match(candidate, /run: node --test test\/deployment-budget.test.mjs test\/deployment-budget-scope.test.mjs\n      - name:/);
  assert.match(candidate, /path: .cache\/deployment-budget.json/);
  const block = [...candidate.matchAll(/sparse-checkout: \|\n((?:            .+\n)+)/g)][0][1];
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'atlas-budget-focused-'));
  try {
    for (const entry of block.trim().split('\n').map(line => line.trim())) {
      assert.ok(!['package-lock.json', 'requirements.txt'].includes(entry));
      fs.mkdirSync(path.dirname(path.join(directory, entry)), {recursive: true});
      fs.copyFileSync(entry, path.join(directory, entry));
    }
    assert.equal(fs.existsSync(path.join(directory, 'node_modules')), false);
    assert.equal(fs.existsSync(path.join(directory, 'data')), false);
    const result = spawnSync(process.execPath, ['--test', 'test/deployment-budget.test.mjs'], {
      cwd: directory, encoding: 'utf8', env: {PATH: process.env.PATH},
    });
    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /pass 3/);
  } finally { fs.rmSync(directory, {recursive: true, force: true}); }
});
