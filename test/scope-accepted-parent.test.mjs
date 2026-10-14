import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync, spawnSync} from 'node:child_process';

const root = path.resolve(import.meta.dirname, '..');
const workflow = fs.readFileSync(path.join(root, '.github/workflows/merge-integration-checks.yml'), 'utf8');
const scope = workflow.slice(workflow.indexOf('\n  scope:\n'), workflow.indexOf('\n  geography:\n'));
const checker = scope.match(/node --input-type=module <<'NODE'\n([\s\S]*?)\n          NODE/)[1];

test('actual scope execution excludes inherited main changes but rejects new foreign edits', t => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'atlas-scope-parent-'));
  t.after(() => fs.rmSync(directory, {recursive: true, force: true}));
  const repo = path.join(directory, 'repo');
  fs.mkdirSync(repo);
  const env = {...process.env, GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: os.devNull, GIT_NO_LAZY_FETCH: '1'};
  const git = (...args) => execFileSync('git', ['-C', repo, ...args], {encoding: 'utf8', env, stdio: ['pipe', 'pipe', 'pipe']}).trim();
  const write = (file, bytes) => {
    fs.mkdirSync(path.dirname(path.join(repo, file)), {recursive: true});
    fs.writeFileSync(path.join(repo, file), bytes);
  };
  git('init', '-b', 'main');
  git('config', 'user.name', 'Scope fixture');
  git('config', 'user.email', 'scope@example.invalid');
  write('src/main.js', 'original\n');
  write('scripts/check-handoff-scope.mjs', fs.readFileSync(path.join(root, 'scripts/check-handoff-scope.mjs')));
  git('add', '.'); git('commit', '-m', 'opening base');
  const opening = git('rev-parse', 'HEAD');
  const foreign = 'coordination/engineering/other-worker/result.json';
  write(foreign, 'accepted main evidence\n');
  git('add', '.'); git('commit', '-m', 'independent accepted main change');
  const accepted = git('rev-parse', 'HEAD');
  git('checkout', '-b', 'engineering/scope-fixture', opening);
  write('src/main.js', 'owned author change\n');
  git('add', '.'); git('commit', '-m', 'owned author change');
  git('merge', '--no-edit', accepted);
  const head = git('rev-parse', 'HEAD');
  git('checkout', '-b', 'event-candidate', accepted);
  git('merge', '--no-ff', '--no-edit', head);
  assert.deepEqual(git('show', '-s', '--format=%P', 'HEAD').split(' '), [accepted, head]);

  const bindings = {'${{ needs.profile.outputs.geography_baseline }}': accepted,
    '${{ github.event.pull_request.base.sha }}': opening};
  const trustedExpression = scope.match(/ref: ([^\n]+)\n          path: trusted/)[1];
  const baseExpression = scope.match(/BASE_SHA: ([^\n]+)/)[1];
  assert.equal(trustedExpression, '${{ needs.profile.outputs.geography_baseline }}');
  assert.equal(baseExpression, trustedExpression);
  const trusted = path.join(directory, 'trusted'), candidate = path.join(directory, 'candidate');
  git('worktree', 'add', '--detach', trusted, bindings[trustedExpression]);
  git('worktree', 'add', '--detach', candidate, head);
  const invoke = base => spawnSync(process.execPath, ['--input-type=module', '-e', checker], {
    cwd: candidate, encoding: 'utf8', env: {...env, LANE_BRANCH: 'engineering/scope-fixture',
      BASE_SHA: base, OWNED_PATHS: '[]', PR_BODY_JSON: JSON.stringify('Refs #42')}
  });
  const stale = invoke(opening);
  assert.notEqual(stale.status, 0);
  assert.match(stale.stderr, /Engineering must preserve other lanes/);
  const result = invoke(bindings[baseExpression]);
  assert.equal(result.status, 0, result.stderr);
  const checked = JSON.parse(result.stdout);
  assert.equal(checked.base, accepted);
  assert.equal(checked.merge_base, accepted);
  assert.equal(checked.head, head);
  assert.equal(checked.changed_files, 1);
  assert.equal(checked.github_issue, 42);

  git('checkout', 'engineering/scope-fixture');
  write(foreign, 'genuinely new foreign author edit\n');
  git('add', '.'); git('commit', '-m', 'new foreign edit');
  const badHead = git('rev-parse', 'HEAD');
  execFileSync('git', ['-C', candidate, 'checkout', '--detach', badHead], {env, stdio: ['pipe', 'pipe', 'pipe']});
  const rejected = invoke(bindings[baseExpression]);
  assert.notEqual(rejected.status, 0);
  assert.match(rejected.stderr, /Engineering must preserve other lanes/);
  assert.equal(fs.readFileSync(path.join(trusted, foreign), 'utf8'), 'accepted main evidence\n');
  assert.equal(fs.readFileSync(path.join(candidate, foreign), 'utf8'), 'genuinely new foreign author edit\n');
});
