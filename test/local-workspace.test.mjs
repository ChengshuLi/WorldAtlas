import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync, spawn} from 'node:child_process';
import {workspaceManager, GiB} from '../scripts/local-workspace.mjs';

function fixture(t, overrides = {}) {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'atlas-storage-test-'));
  t.after(() => fs.rmSync(temporary, {recursive: true, force: true}));
  const repo = path.join(temporary, 'repo');
  fs.mkdirSync(repo);
  const git = (...args) => execFileSync('git', ['-C', repo, ...args], {encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe']});
  git('init', '-b', 'main');
  git('config', 'user.email', 'fixture@example.org');
  git('config', 'user.name', 'Fixture');
  for (const [file, bytes] of Object.entries({'README.md': 'root', 'scripts/tool.mjs': 'tool', 'docs/guide.md': 'guide',
    'data/needed/input.json': 'input', 'data/other/large.json': 'unrelated', 'data/one.json': 'individual',
    'research/campaigns/old/source.txt': 'old', '.gitignore': '.scratch/\n'})) {
    fs.mkdirSync(path.dirname(path.join(repo, file)), {recursive: true});
    fs.writeFileSync(path.join(repo, file), bytes);
  }
  git('add', '.'); git('commit', '-m', 'fixture'); git('remote', 'add', 'origin', repo);
  const head = git('rev-parse', 'HEAD').trim();
  const manager = workspaceManager(repo, {freeBytes: () => 100 * GiB, limits: {minimumFree: 50 * GiB, maximumCheckouts: 50 * GiB}, ...overrides});
  return {repo, git, manager, head, temporary};
}

test('sparse work is isolated and contains required directories and individual inputs only', t => {
  const {manager, head, git} = fixture(t);
  const entry = manager.allocate({worker: 'worker-one', branch: 'geography/first', include: ['data/needed', 'data/one.json']});
  assert.equal(entry.head, head);
  assert.equal(fs.readFileSync(path.join(entry.path, 'data/needed/input.json'), 'utf8'), 'input');
  assert.ok(fs.existsSync(path.join(entry.path, 'data/one.json')));
  assert.ok(fs.existsSync(path.join(entry.path, 'scripts/tool.mjs')));
  assert.ok(!fs.existsSync(path.join(entry.path, 'data/other')));
  assert.ok(!fs.existsSync(path.join(entry.path, 'research/campaigns/old')));
  assert.throws(() => manager.allocate({worker: 'worker-one', branch: 'geography/second'}), /occupied/);
  const review = manager.allocate({worker: 'worker-one', slot: 'review', commit: head});
  assert.notEqual(review.path, entry.path);
  assert.throws(() => manager.release({worker: 'worker-one', token: review.token}), /ownership/);
  const result = manager.release({worker: 'worker-one', token: entry.token});
  assert.equal(git('rev-parse', result.preservedRef).trim(), head);
  assert.ok(!fs.existsSync(entry.path));
  const next = manager.allocate({worker: 'worker-one', branch: 'geography/second'});
  assert.equal(next.path, entry.path);
  assert.notEqual(next.token, entry.token);
  assert.throws(() => manager.release({worker: 'worker-one', token: entry.token}), /ownership/);
});

test('low disk and existing legacy checkouts prevent allocation without creating a branch', t => {
  const {manager, git, repo} = fixture(t, {freeBytes: () => 50 * GiB});
  assert.throws(() => manager.allocate({worker: 'one', branch: 'engineering/no-space'}), /headroom/);
  assert.throws(() => git('rev-parse', '--verify', 'engineering/no-space'));
  const capped = workspaceManager(repo, {freeBytes: () => 100 * GiB, limits: {minimumFree: 50 * GiB, maximumCheckouts: 1}});
  assert.ok(capped.report().worktrees.some(row => row.path === fs.realpathSync(repo) && !row.managed));
  assert.throws(() => capped.allocate({worker: 'one', branch: 'engineering/over-budget'}), /budget/);
  assert.throws(() => capped.check(), /breached/);
});

test('dirty tracked, untracked and ignored work cannot be discarded', t => {
  const {manager} = fixture(t);
  const entry = manager.allocate({worker: 'one', branch: 'engineering/dirty'});
  const release = () => manager.release({worker: 'one', token: entry.token});
  fs.writeFileSync(path.join(entry.path, 'README.md'), 'valuable');
  assert.throws(release, /uncommitted/);
  fs.writeFileSync(path.join(entry.path, 'README.md'), 'root');
  fs.writeFileSync(path.join(entry.path, 'new.txt'), 'unique');
  assert.throws(release, /untracked/);
  fs.unlinkSync(path.join(entry.path, 'new.txt'));
  fs.mkdirSync(path.join(entry.path, '.scratch'));
  fs.writeFileSync(path.join(entry.path, '.scratch/result.txt'), 'ignored unique');
  assert.throws(release, /ignored/);
  assert.equal(fs.readFileSync(path.join(entry.path, '.scratch/result.txt'), 'utf8'), 'ignored unique');
});

test('invalid scopes and identities are rejected; explicit full profile includes all inputs', t => {
  const {manager, head} = fixture(t);
  for (const include of ['data/../outside', '/tmp', 'data/*', 'data//two', 'data']) {
    assert.throws(() => manager.allocate({worker: 'one', branch: 'engineering/scoped', include: [include]}), /literal/);
  }
  assert.throws(() => manager.allocate({worker: '../other', branch: 'engineering/a'}), /worker/);
  assert.throws(() => manager.allocate({worker: 'one', slot: 'extra', branch: 'engineering/a'}), /worker/);
  assert.throws(() => manager.allocate({worker: 'one', branch: 'main'}), /fresh lane/);
  assert.throws(() => manager.allocate({worker: 'one', slot: 'review', commit: 'main'}), /exact detached/);
  const entry = manager.allocate({worker: 'one', slot: 'review', commit: head, profile: 'full'});
  assert.ok(fs.existsSync(path.join(entry.path, 'data/other/large.json')));
});

test('allocation lock is exclusive and never broken automatically', t => {
  const {manager} = fixture(t);
  const {registry} = manager.report();
  fs.mkdirSync(path.join(registry, 'lock'), {recursive: true});
  assert.throws(() => manager.allocate({worker: 'one', branch: 'engineering/locked'}), /locked/);
  assert.ok(fs.existsSync(path.join(registry, 'lock')));
});

test('an interrupted Git mutation is recorded and occupies its slot', t => {
  const {manager, git} = fixture(t);
  git('branch', 'engineering/already-exists');
  assert.throws(() => manager.allocate({worker: 'one', branch: 'engineering/already-exists'}));
  const entry = manager.report().entries[0];
  assert.equal(entry.status, 'preparing');
  assert.throws(() => manager.allocate({worker: 'one', branch: 'engineering/new'}), /occupied/);
  assert.throws(() => manager.release({worker: 'one', token: entry.token}), /inspection/);
});

test('symlink root cannot redirect allocation or release outside the managed directory', t => {
  const {manager, temporary} = fixture(t);
  const {root} = manager.report();
  fs.mkdirSync(path.dirname(root), {recursive: true});
  const outside = path.join(temporary, 'outside'); fs.mkdirSync(outside);
  fs.symlinkSync(outside, root);
  assert.throws(() => manager.allocate({worker: 'one', branch: 'engineering/escape'}), /Symlink/);
  assert.deepEqual(fs.readdirSync(outside), []);
});

test('two simultaneous allocation processes cannot acquire the same worker slot', async t => {
  const {repo, manager} = fixture(t);
  const moduleURL = new URL('../scripts/local-workspace.mjs', import.meta.url).href;
  const run = branch => new Promise(resolve => {
    const source = `import {workspaceManager,GiB} from ${JSON.stringify(moduleURL)};
      try {workspaceManager(${JSON.stringify(repo)},{freeBytes:()=>100*GiB}).allocate({worker:'parallel',branch:${JSON.stringify(branch)}});}
      catch(error){process.exitCode=1;}`;
    const child = spawn(process.execPath, ['--input-type=module', '-e', source], {stdio: 'ignore'});
    child.on('exit', code => resolve(code));
    child.on('error', () => resolve(1));
  });
  const exits = await Promise.all([run('engineering/parallel-one'), run('engineering/parallel-two')]);
  assert.deepEqual(exits.sort(), [0, 1]);
  assert.equal(manager.report().entries.length, 1);
  assert.equal(manager.report().entries[0].status, 'ready');
});

test('new sparse packet paths permit ordinary creation and staging', t => {
  const {manager} = fixture(t);
  const entry = manager.allocate({worker: 'one', branch: 'research/new', include: ['research/campaigns/new']});
  const file = path.join(entry.path, 'research/campaigns/new/result.json');
  fs.mkdirSync(path.dirname(file), {recursive: true}); fs.writeFileSync(file, '{}');
  execFileSync('git', ['-C', entry.path, 'add', 'research/campaigns/new/result.json']);
  assert.match(execFileSync('git', ['-C', entry.path, 'status', '--porcelain'], {encoding: 'utf8'}), /A  research\/campaigns\/new\/result.json/);
});
