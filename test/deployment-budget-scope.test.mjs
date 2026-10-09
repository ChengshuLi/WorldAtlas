import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {loadPackageInputs} from '../scripts/package-inputs.mjs';
import {classifyBudgetFiles, deploymentBudgetProfile, githubBudgetAPI} from '../scripts/classify-deployment-budget.mjs';

const repository = 'ChengshuLi/WorldAtlas', before = 'a'.repeat(40), after = 'b'.repeat(40);
const file = (filename, extra = {}) => ({filename, status: 'modified', ...extra});
const event = {repository: {full_name: repository}, pull_request: {number: 5, base: {sha: before}, head: {sha: after}}};
const profile = (api, extra = {}) => deploymentBudgetProfile({event, eventName: 'pull_request', repository, api: withDefinition(api), ...extra});
const metadata = count => ({base: {sha: before}, head: {sha: after}, changed_files: count});
const comparison = files => ({base_commit: {sha: before}, status: 'ahead', commits: [{sha: after}], files});

const definition = loadPackageInputs();
const raw = Buffer.from(JSON.stringify(definition));
const blob = {type: 'file', path: '.github/package-inputs.json', encoding: 'base64', size: raw.length,
  sha: createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex'), content: raw.toString('base64')};
const withDefinition = api => route => route.includes('/contents/') ? blob : api(route);

test('package applicability comes only from the enforced declaration', () => {
  for (const name of ['docs/generated.json', 'scripts/new-control.mjs', 'README.md',
    'coordination/engineering/example/result.json', 'research/new-paper.json',
    'research/geography/example/source.json', 'research/campaigns/example/source.json',
    'data/regional-review/example/source.json']) {
    assert.equal(classifyBudgetFiles([file(name)]).full, false, name);
  }
  for (const name of ['scripts/deployment-budget.mjs', 'scripts/classify-deployment-budget.mjs',
    'src/main.js', 'hosted/server.js', 'data/world-index.json', 'drizzle/0001.sql',
    '.openai/hosting.json', 'package.json', 'package-lock.json', 'requirements.txt',
    'public/a.txt', '.github/workflows/deployment-budget.yml', '.github/package-inputs.json']) {
    assert.equal(classifyBudgetFiles([file(name)]).full, true, name);
  }
  for (const name of ['docs/../src/main.js', 'README.md\n', '/src/main.js', 'src\\main.js']) {
    assert.throws(() => classifyBudgetFiles([file(name)]), /Invalid changed-file path/);
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
  assert.match(candidate, /run: node --test test\/deployment-budget.test.mjs test\/deployment-budget-scope.test.mjs test\/package-inputs.test.mjs test\/package-build.test.mjs\n        if: needs.classify.outputs.full != 'false'/);
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

test('promoting research is explicit and exact, without freezing implementation bytes', async () => {
  const promoted = {...definition, inputs: [...definition.inputs, 'research/geography/example/public.json']};
  assert.equal(classifyBudgetFiles([file('research/geography/example/public.json')], promoted).full, true);
  assert.equal(classifyBudgetFiles([file('research/geography/example/private.json')], promoted).full, false);
  assert.equal(classifyBudgetFiles([file('research/new-paper.json', {status: 'renamed',
    previous_filename: 'research/geography/example/public.json'})], promoted).full, true);
  const result = await profile(async route => route.includes('/files?') ? [file('research/new-paper.json')] : metadata(1));
  assert.equal(result.full, false);
});

test('unavailable or altered declaration bytes conservatively require the package build', async () => {
  for (const value of [undefined, {...blob, type: 'symlink'}, {...blob, size: 999999},
    {...blob, content: Buffer.from('{}').toString('base64')}, {...blob, sha: 'f'.repeat(40)}]) {
    const result = await deploymentBudgetProfile({event, eventName: 'pull_request', repository,
      api: async route => route.includes('/contents/') ? value : route.includes('/files?') ? [file('research/new-paper.json')] : metadata(1)});
    assert.equal(result.full, true); assert.equal(result.fallback, true);
  }
});

test('quota-blocked classification fails the required package job before expensive setup',()=>{
 const yaml=fs.readFileSync(new URL('../.github/workflows/deployment-budget.yml',import.meta.url),'utf8');
 const refusal=yaml.indexOf('      - name: Refuse package verification while Actions API quota is unavailable');
 const checkout=yaml.indexOf('      - name: Checkout complete package inputs');
 assert(refusal>0&&refusal<checkout);
 assert.match(yaml.slice(refusal,checkout),/if: needs\.classify\.outputs\.blocked == 'true'/);
 assert.match(yaml.slice(refusal,checkout),/exit 1/);
 assert.match(yaml,/blocked: \$\{\{ steps\.profile\.outputs\.blocked \}\}/);
 assert.match(yaml,/package:\n    needs: classify[\s\S]*?if: always\(\)/);
});

test('only read-only superseded PR work is cancelled; main package and merge scheduling remain separate',()=>{
 const budget=fs.readFileSync(new URL('../.github/workflows/deployment-budget.yml',import.meta.url),'utf8');
 const regression=fs.readFileSync(new URL('../.github/workflows/merge-integration-checks.yml',import.meta.url),'utf8');
 const handoff=fs.readFileSync(new URL('../.github/workflows/handoff-scope.yml',import.meta.url),'utf8');
 assert.match(budget,/group: worldatlas-package-\$\{\{ github\.event_name \}\}-\$\{\{ github\.event\.pull_request\.number \|\| github\.ref \}\}/);
 assert.match(budget,/cancel-in-progress: \$\{\{ github\.event_name == 'pull_request' \}\}/);
 for(const yaml of [regression,handoff])assert.match(yaml,/concurrency:[\s\S]*?github\.event\.pull_request\.number[\s\S]*?cancel-in-progress: true/);
});
