import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync, execFileSync} from 'node:child_process';
import {checkGitScope} from '../scripts/check-handoff-scope.mjs';

const root = path.resolve(import.meta.dirname, '..');
const workflows = ['issue-claims.yml', 'worker-merge.yml', 'merge-integration-checks.yml', 'queue-readiness-audit.yml', 'merge-scheduler.yml'];

// Reproduce each declared sparse tree, including cone-mode root files. Load
// trusted modules without executing workflow entrypoints or contacting GitHub.
function probe(directories, {geography = false} = {}) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'worldatlas-checkout-'));
  try {
    fs.copyFileSync(path.join(root, 'package.json'), path.join(directory, 'package.json'));
    for (const relative of directories) {
      const source = path.join(root, relative);
      const destination = path.join(directory, relative);
      fs.mkdirSync(path.dirname(destination), {recursive: true});
      fs.cpSync(source, destination, {recursive: true});
    }
    return spawnSync(process.execPath, ['--input-type=module', '-e',
      "await import('./scripts/issue-claim-contract.mjs'); await import('./scripts/premerge-evidence.mjs'); await import('./scripts/queue-readiness-audit.mjs'); await import('./scripts/merge-scheduler.mjs'); await import('./scripts/check-pr-gates.mjs');" +
      (geography ? "await import('./scripts/check-effective-geographic-regression.mjs'); await import('./coordination/engineering/selected-geography-effective-prevention-20261009/selected-continuous-entry.mjs'); console.log('complete trusted geography closure imported');" : '')],
    {cwd: directory, encoding: 'utf8', env: {PATH: process.env.PATH}});
  } finally { fs.rmSync(directory, {recursive: true, force: true}); }
}

for (const workflow of ['worker-merge.yml', 'merge-integration-checks.yml']) {
  test(`${workflow}: actual geographic checkout imports its complete trusted closure`, () => {
    const source = fs.readFileSync(path.join(root, '.github/workflows', workflow), 'utf8');
    const match = source.match(/- name: Checkout trusted geographic checker[\s\S]*?sparse-checkout: \|\n((?:            .+\n)+)/);
    assert.ok(match, 'actual trusted geography checkout must be declared');
    const result = probe(match[1].trim().split('\n').map(row => row.trim()), {geography: true});
    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /complete trusted geography closure imported/);
  });
}

test('negative control: old geographic sparse tree omits mandatory coordinator bodies', () => {
  const result = probe(['scripts', 'src', '.github'], {geography: true});
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /ERR_MODULE_NOT_FOUND/);
  assert.match(result.stderr, /selected-geography-effective-prevention-20261009/);
});

for (const workflow of workflows) {
  test(`${workflow}: actual sparse declarations include trusted module dependencies`, () => {
    const source = fs.readFileSync(path.join(root, '.github/workflows', workflow), 'utf8');
    const blocks = [...source.matchAll(/^          sparse-checkout: \|\n((?:            .+\n)+)/gm)];
    assert.ok(blocks.length > 0, 'expected explicit sparse checkout declarations');
    for (const block of blocks) {
      const directories = block[1].trim().split('\n').map(row => row.trim());
      const result = probe(directories);
      assert.equal(result.status, 0, result.stderr);
    }
  });
}

test('negative control: old scripts-only tree cannot load relocated regional gate', () => {
  const result = probe(['scripts', '.github']);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /ERR_MODULE_NOT_FOUND/);
  assert.match(result.stderr, /src\/regional-import-gate\.js/);
});


test('sparse candidate still detects changes and rename sources outside the working tree', () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'worldatlas-sparse-scope-'));
  const git = args => execFileSync('git', args, {cwd: directory, encoding: 'utf8'});
  const run = (command, args, options) => execFileSync(command, args, {...options, cwd: directory});
  try {
    git(['init', '-q']); git(['config', 'user.email', 'test@example.invalid']); git(['config', 'user.name', 'test']);
    fs.mkdirSync(path.join(directory, 'src'), {recursive: true});
    fs.mkdirSync(path.join(directory, 'research/campaigns/example'), {recursive: true});
    fs.writeFileSync(path.join(directory, 'src/main.js'), 'original source\n');
    fs.writeFileSync(path.join(directory, 'research/campaigns/example/notes.txt'), 'original notes\n');
    git(['add', '.']); git(['commit', '-qm', 'baseline']); const base = git(['rev-parse', 'HEAD']).trim();
    fs.writeFileSync(path.join(directory, 'research/campaigns/example/notes.txt'), 'updated notes\n');
    git(['commit', '-qam', 'owned evidence']);
    git(['sparse-checkout', 'init', '--cone']); git(['sparse-checkout', 'set', 'src']);
    assert.equal(fs.existsSync(path.join(directory, 'research')), false);
    assert.equal(checkGitScope({branch: 'research/example', base, run}).changed_files, 1);
    git(['sparse-checkout', 'disable']);
    git(['mv', 'src/main.js', 'research/campaigns/example/copied.js']); git(['commit', '-qm', 'rename core source']);
    git(['sparse-checkout', 'set', 'src']);
    assert.equal(fs.existsSync(path.join(directory, 'research')), false);
    assert.throws(() => checkGitScope({branch: 'research/example', base, run}), /Research changes/);
  } finally { fs.rmSync(directory, {recursive: true, force: true}); }
});


for (const [workflow, expected] of [['merge-integration-checks.yml', 2], ['worker-merge.yml', 1]]) {
  test(`${workflow}: immutable normal routes build Cloudflare and retain the separate Site gate`, () => {
    const source = fs.readFileSync(path.join(root, '.github/workflows', workflow), 'utf8');
    const routes = [...source.matchAll(/^        run: (npm run build:cloudflare)$/gm)];
    assert.equal(routes.length, expected, 'all actual package/shard routes must be covered');
    assert.doesNotMatch(source, /WORLDATLAS_PACKAGE_PROFILE|run: npm run build:hosted/);
    const site = fs.readFileSync(path.join(root, '.github/workflows/deployment-budget.yml'), 'utf8');
    assert.match(site, /run: npm run build:hosted/);
    const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'worldatlas-package-routing-'));
    try {
      fs.writeFileSync(path.join(directory, 'npm'), '#!/bin/sh\nprintf "%s\\n" "$*"\n', {mode: 0o755});
      for (const route of routes) {
        const result = spawnSync('/bin/bash', ['-c', route[1]], {encoding: 'utf8', env: {PATH: directory, WORLDATLAS_PACKAGE_PROFILE: 'foreign'}});
        assert.equal(result.status, 0, result.stderr);assert.equal(result.stdout.trim(), 'run build:cloudflare');
      }
    } finally { fs.rmSync(directory, {recursive: true, force: true}); }
  });
}


test('actual scope candidate sparse declaration contains cold-checkout test imports', () => {
  const source = fs.readFileSync(path.join(root, '.github/workflows/merge-integration-checks.yml'), 'utf8');
  const scope = source.split('  scope:\n')[1].split('  geography:\n')[0];
  const candidate = scope.match(/path: candidate[\s\S]*?sparse-checkout: \|\n((?:            .+\n)+)/);
  assert.ok(candidate, 'actual scope candidate checkout must be declared');
  const directories = candidate[1].trim().split('\n').map(row => row.trim());
  const qualified = probe(directories, {geography: true});
  assert.equal(qualified.status, 0, qualified.stderr);
  const missing = probe(directories.filter(row => !row.startsWith('coordination/')), {geography: true});
  assert.notEqual(missing.status, 0);assert.match(missing.stderr, /selected-geography-effective-prevention-20261009/);
});
