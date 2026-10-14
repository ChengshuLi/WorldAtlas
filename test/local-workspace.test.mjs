import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {execFileSync, spawn, spawnSync} from 'node:child_process';
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
  const manager = workspaceManager(repo, {freeBytes: () => 100 * GiB, limits: {minimumFree: 10 * GiB}, ...overrides});
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

test('low disk prevents allocation without creating a branch or reservation', t => {
  const {manager, git} = fixture(t, {freeBytes: () => 10 * GiB});
  assert.throws(() => manager.allocate({worker: 'one', branch: 'engineering/no-space'}), /headroom/);
  assert.throws(() => git('rev-parse', '--verify', 'engineering/no-space'));
  assert.deepEqual(manager.report().entries, []);
});

test('reservations and combined usage above 50 GiB are admitted with sufficient headroom', t => {
  const {manager, repo} = fixture(t);
  const first = manager.allocate({worker: 'one', branch: 'engineering/large-reservation', reserveGiB: 51});
  assert.equal(first.reservation, 51 * GiB);
  const second = manager.allocate({worker: 'two', branch: 'engineering/another-reservation', reserveGiB: 2});
  const report = manager.check();
  assert.ok(report.checkoutBytes >= 53 * GiB);
  assert.ok(report.worktrees.some(row => row.path === fs.realpathSync(repo) && !row.managed));
  manager.release({worker: 'two', token: second.token});
  manager.release({worker: 'one', token: first.token});
});

test('exactly 10 GiB after reservation is allowed, one byte less is refused', t => {
  let available = 11 * GiB;
  const {manager, git} = fixture(t, {freeBytes: () => available});
  const entry = manager.allocate({worker: 'one', branch: 'engineering/exact-headroom'});
  manager.release({worker: 'one', token: entry.token});
  available -= 1;
  assert.throws(() => manager.allocate({worker: 'one', branch: 'engineering/short-headroom'}), /headroom/);
  assert.throws(() => git('rev-parse', '--verify', 'engineering/short-headroom'));
  assert.deepEqual(manager.report().entries, []);
  available = 10 * GiB;
  assert.equal(manager.check().freeBytes, available);
  available -= 1;
  assert.throws(() => manager.check(), /breached/);
});

test('invalid or unsafe reservation sizes fail before branch or slot creation', t => {
  const {manager, git} = fixture(t);
  for (const reserveGiB of [0, -1, NaN, Infinity, 1e20]) {
    assert.throws(() => manager.allocate({worker: 'one', branch: 'engineering/invalid-reserve', reserveGiB}), /Reserve/);
    assert.throws(() => git('rev-parse', '--verify', 'engineering/invalid-reserve'));
    assert.deepEqual(manager.report().entries, []);
  }
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

test('large sparse indexes release only clean owned work and preserve recovery', t => {
  const {repo, git, manager} = fixture(t);
  const blob = git('rev-parse', 'HEAD:README.md').trim();
  const rows = Array.from({length: 9000}, (_, i) =>
    `100644 ${blob}\tdata/large-index/${String(i).padStart(5, '0')}-${'x'.repeat(120)}.json\n`).join('');
  execFileSync('git', ['-C', repo, 'update-index', '--index-info'], {input: rows});
  git('commit', '-q', '-m', 'large sparse index fixture');
  const head = git('rev-parse', 'HEAD').trim();
  const entry = manager.allocate({worker: 'large-index', branch: 'engineering/large-index'});
  const inventory = execFileSync('git', ['-C', entry.path, 'ls-files', '-vz'], {maxBuffer: 32 * 1024 * 1024});
  assert.ok(inventory.length > 1024 * 1024, 'fixture reproduces the real repository inventory size');
  assert.ok(!fs.existsSync(path.join(entry.path, 'data/large-index')));
  assert.throws(() => manager.release({worker: 'large-index', token: 'wrong-token'}), /ownership/);
  fs.mkdirSync(path.join(entry.path, '.scratch'));
  const valuable = path.join(entry.path, '.scratch/valuable.txt');
  fs.writeFileSync(valuable, 'preserve');
  assert.throws(() => manager.release({worker: 'large-index', token: entry.token}), /ignored/);
  assert.equal(fs.readFileSync(valuable, 'utf8'), 'preserve');
  fs.unlinkSync(valuable);
  const result = manager.release({worker: 'large-index', token: entry.token});
  assert.equal(git('rev-parse', result.preservedRef).trim(), head);
  assert.ok(!fs.existsSync(entry.path));
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

test('assume-unchanged cannot hide unique tracked bytes from cleanup', t => {
  const {manager} = fixture(t);
  const entry = manager.allocate({worker: 'one', branch: 'engineering/hidden-edits'});
  execFileSync('git', ['-C', entry.path, 'update-index', '--assume-unchanged', 'README.md']);
  fs.writeFileSync(path.join(entry.path, 'README.md'), 'unique hidden work');
  assert.equal(execFileSync('git', ['-C', entry.path, 'status', '--porcelain'], {encoding: 'utf8'}), '');
  assert.throws(() => manager.release({worker: 'one', token: entry.token}), /trust flags/);
  assert.equal(fs.readFileSync(path.join(entry.path, 'README.md'), 'utf8'), 'unique hidden work');
});

// Actual local blobless clone: commit/tree objects arrive via Git's promisor
// protocol; selected fixture blobs are seeded locally without warming exclusions.
function partialFixture(t, missing, {packSource = false, configureSource} = {}) {
  const source = fixture(t);
  if (configureSource) {
    configureSource(source);
    source.head = source.git('rev-parse', 'HEAD').trim();
  }
  if (packSource) {
    source.git('repack', '-ad');
    assert.match(source.git('count-objects', '-v'), /^count: 0$/m, 'packed source has no loose objects');
  }
  source.git('config', 'uploadpack.allowFilter', 'true');
  const repo = path.join(source.temporary, 'partial');
  execFileSync('git', ['clone', '--filter=blob:none', '--no-checkout', pathToFileURL(source.repo).href, repo], {stdio: 'pipe'});
  const git = (...args) => execFileSync('git', ['-C', repo, ...args], {
    encoding: 'utf8', stdio: 'pipe', env: {...process.env, GIT_NO_LAZY_FETCH: '1'}
  });
  assert.equal(git('config', '--get', 'remote.origin.promisor').trim(), 'true');
  const absent = (Array.isArray(missing) ? missing : [missing]).map(name => source.git('rev-parse', `HEAD:${name}`).trim());
  for (const line of source.git('ls-tree', '-rz', 'HEAD').split('\0').filter(Boolean)) {
    const oid = line.slice(0, line.indexOf('\t')).split(' ')[2];
    if (absent.includes(oid)) continue;
    // Git may pack source objects during ordinary maintenance. Transfer the
    // exact blob bytes through Git rather than assuming loose-object storage.
    const env = {...process.env, GIT_NO_LAZY_FETCH: '1'};
    const bytes = execFileSync('git', ['-C', source.repo, 'cat-file', 'blob', oid], {env});
    const written = execFileSync('git', ['-C', repo, 'hash-object', '-w', '--stdin'], {
      input: bytes, encoding: 'utf8', env
    }).trim();
    assert.equal(written, oid, 'seeded blob preserves its exact object identity');
  }
  const objectState = () => fs.readdirSync(path.join(repo, '.git/objects'), {recursive: true}).sort();
  const objects = objectState();
  const trace = path.join(source.temporary, 'partial-git-trace.log');
  const run = (options, action = 'allocate') => {
    const moduleURL = new URL('../scripts/local-workspace.mjs', import.meta.url).href;
    const code = `import {workspaceManager,GiB} from ${JSON.stringify(moduleURL)};
      try { console.log(JSON.stringify(workspaceManager(${JSON.stringify(repo)},{freeBytes:()=>100*GiB})[${JSON.stringify(action)}](${JSON.stringify({worker: 'partial', slot: 'review', commit: source.head, ...options})}))); }
      catch(error) { console.error(error.message); process.exitCode=1; }`;
    // Deliberately permit lazy fetch in the caller: allocator sizing must disable
    // it itself. Any accidental fetch is observable, even if Git recovers.
    return execFileSync(process.execPath, ['--input-type=module', '-e', code], {
      encoding: 'utf8', stdio: 'pipe', env: {...process.env, GIT_NO_LAZY_FETCH: '0', GIT_TRACE: trace}
    });
  };
  const checkUnfetched = (allowMainFetch = false) => {
    let log = fs.readFileSync(trace, 'utf8');
    if (allowMainFetch) {
      assert.equal(log.match(/built-in: git fetch origin main/g)?.length, 1, 'only the ordinary main refresh is allowed');
      log = log.split('\n').filter(line => !line.includes('built-in: git fetch origin main')).join('\n');
    }
    assert.doesNotMatch(log, /(?:built-in: git|run_command:) .*fetch/);
    assert.match(log, /ls-tree -rz/);
    assert.doesNotMatch(log, /ls-tree -rlz/);
    assert.deepEqual(objectState(), objects, 'sizing/checkout must not hydrate an excluded or missing blob');
    const response = execFileSync('git', ['-C', repo, '-c', 'core.commitGraph=false', 'rev-list', '--objects',
      '--filter=tree:0', '--missing=print', '--ignore-missing', '--no-walk=unsorted', '--no-object-names', '--stdin'], {
      input: absent.join('\n') + '\n', encoding: 'utf8', env: {...process.env, GIT_NO_LAZY_FETCH: '1'}
    });
    assert.equal(response, '', 'absent object tips remain absent without entering promisor fetch');
  };
  return {...source, repo, git, trace, run, checkUnfetched,
    manager: workspaceManager(repo, {freeBytes: () => 100 * GiB})};
}

test('actual promisor clone allocates selected sparse inputs without sizing or fetching excluded missing blobs', t => {
  const {run, repo, manager, checkUnfetched} = partialFixture(t, 'data/other/large.json');
  const entry = JSON.parse(run({include: ['data/needed', 'data/one.json']}));
  assert.equal(fs.readFileSync(path.join(entry.path, 'data/needed/input.json'), 'utf8'), 'input');
  assert.equal(fs.readFileSync(path.join(entry.path, 'data/one.json'), 'utf8'), 'individual');
  assert.equal(fs.readFileSync(path.join(entry.path, 'scripts/tool.mjs'), 'utf8'), 'tool');
  assert.ok(!fs.existsSync(path.join(entry.path, 'data/other')));
  checkUnfetched();
  manager.release({worker: 'partial', slot: 'review', token: entry.token});
  assert.equal(execFileSync('git', ['-C', repo, 'worktree', 'list', '--porcelain'], {encoding: 'utf8'}).match(/^worktree /gm).length, 1);
});

test('packed-source promisor fixture preserves selected blobs and leaves excluded blobs missing', t => {
  const {run, manager, checkUnfetched} = partialFixture(t, 'data/other/large.json', {packSource: true});
  const entry = JSON.parse(run({include: ['data/needed', 'data/one.json']}));
  assert.equal(fs.readFileSync(path.join(entry.path, 'data/needed/input.json'), 'utf8'), 'input');
  assert.equal(fs.readFileSync(path.join(entry.path, 'data/one.json'), 'utf8'), 'individual');
  assert.ok(!fs.existsSync(path.join(entry.path, 'data/other')));
  checkUnfetched();
  manager.release({worker: 'partial', slot: 'review', token: entry.token});
});

test('actual promisor clone rejects missing root, support and explicitly selected blobs before allocation', t => {
  for (const missing of ['README.md', 'scripts/tool.mjs', 'data/one.json']) {
    const {run, manager, git, checkUnfetched} = partialFixture(t, missing);
    const before = git('worktree', 'list', '--porcelain');
    const refs = git('show-ref');
    assert.throws(() => run({include: ['data/one.json']}), error => /Unknown input size/.test(error.stderr));
    assert.equal(git('worktree', 'list', '--porcelain'), before);
    assert.equal(git('show-ref'), refs);
    assert.deepEqual(manager.report().entries, []);
    assert.ok(!fs.existsSync(manager.report().root), 'no checkout directory is created');
    assert.ok(!fs.existsSync(path.join(manager.report().registry, 'state.json')), 'no reservation is written');
    checkUnfetched();
  }
});

test('author allocation refreshes main but missing selected blobs create no branch, reservation or checkout', t => {
  const {run, manager, git, checkUnfetched} = partialFixture(t, 'scripts/tool.mjs');
  const before = git('worktree', 'list', '--porcelain');
  assert.throws(() => run({slot: 'work', commit: undefined, branch: 'engineering/missing-selected'}),
    error => /Unknown input size/.test(error.stderr));
  assert.equal(git('worktree', 'list', '--porcelain'), before);
  assert.throws(() => git('rev-parse', '--verify', 'refs/heads/engineering/missing-selected'));
  assert.deepEqual(manager.report().entries, []);
  assert.ok(!fs.existsSync(manager.report().root));
  assert.ok(!fs.existsSync(path.join(manager.report().registry, 'state.json')));
  checkUnfetched(true);
});

test('full profile requires every promisor blob and fails before reservation or checkout', t => {
  const {run, manager, git, checkUnfetched} = partialFixture(t, 'data/other/large.json');
  const before = git('worktree', 'list', '--porcelain');
  assert.throws(() => run({profile: 'full'}), error => /Unknown input size/.test(error.stderr));
  assert.equal(git('worktree', 'list', '--porcelain'), before);
  assert.deepEqual(manager.report().entries, []);
  assert.ok(!fs.existsSync(manager.report().root));
  checkUnfetched();
});

test('bounded selected batches count duplicate blob paths, empty files and full-profile bytes exactly', t => {
  const {repo, git, manager} = fixture(t);
  const blob = git('rev-parse', 'HEAD:README.md').trim();
  const rows = Array.from({length: 2100}, (_, i) => `100644 ${blob}\tscripts/duplicate-${i}.txt\n`).join('');
  execFileSync('git', ['-C', repo, 'update-index', '--index-info'], {input: rows});
  fs.writeFileSync(path.join(repo, 'empty.txt'), '');
  git('add', 'empty.txt'); git('commit', '-m', 'multiple size batches');
  const head = git('rev-parse', 'HEAD').trim();
  for (const profile of ['sparse', 'full']) {
    const include = ['data/needed', 'data/one.json'];
    const expected = git('ls-tree', '-rlz', head).split('\0').filter(Boolean).reduce((total, line) => {
      const [metadata, name] = line.split('\t');
      return total + (profile === 'full' || !name.includes('/') || name.startsWith('scripts/') || name.startsWith('docs/')
        || name.startsWith('data/needed/') || name === 'data/one.json' ? Number(metadata.trim().split(/\s+/)[3]) : 0);
    }, 0);
    const inventory = manager.inspect({commit: head, profile, include});
    assert.deepEqual(inventory.missing, []);
    assert.equal(inventory.availableBytes, expected);
    assert.equal(inventory.selectedBytes, expected);
    assert.equal(inventory.inputs.reduce((sum, row) => sum + row.bytes, 0), expected);
    const entry = manager.allocate({worker: profile, slot: 'review', commit: head, profile, include, reserveGiB: 1 / GiB});
    assert.equal(entry.reservation, expected);
    assert.equal(fs.readFileSync(path.join(entry.path, 'scripts/duplicate-2099.txt'), 'utf8'), 'root');
    manager.release({worker: profile, slot: 'review', token: entry.token});
  }
});

test('selected submodules remain refused while excluded submodule metadata is harmless', t => {
  const {repo, git, manager, head} = fixture(t);
  execFileSync('git', ['-C', repo, 'update-index', '--add', '--cacheinfo', `160000,${head},data/vendor`]);
  git('commit', '-m', 'submodule fixture');
  const commit = git('rev-parse', 'HEAD').trim();
  const entry = manager.allocate({worker: 'excluded', slot: 'review', commit});
  manager.release({worker: 'excluded', slot: 'review', token: entry.token});
  for (const options of [{include: ['data/vendor']}, {profile: 'full'}]) {
    assert.throws(() => manager.inspect({commit, ...options}), /Submodule/);
    assert.throws(() => manager.allocate({worker: 'selected', slot: 'review', commit, ...options}), /Submodule/);
    assert.deepEqual(manager.report().entries, []);
  }
});


test('read-only inspection retains required scopes and creates no registry, lock, branch or checkout', t => {
  const {manager, git, head} = fixture(t);
  const before = git('worktree', 'list', '--porcelain');
  const refs = git('show-ref');
  const scope = {commit: head, include: ['data/needed', 'data/one.json', 'research/new-owned-path']};
  const result = manager.inspect(scope);
  assert.equal(result.head, head);
  assert.deepEqual(result.include, scope.include);
  assert.deepEqual(result.inputs.map(row => row.path).sort(), [
    '.gitignore', 'README.md', 'data/needed/input.json', 'data/one.json', 'docs/guide.md', 'scripts/tool.mjs'
  ]);
  assert.equal(result.inputCount, 6);
  assert.deepEqual(result.missing, []);
  assert.equal(result.selectedBytes, result.inputs.reduce((sum, row) => sum + row.bytes, 0));
  const {registry, root} = manager.report();
  assert.ok(!fs.existsSync(registry));
  assert.ok(!fs.existsSync(root));
  assert.equal(git('worktree', 'list', '--porcelain'), before);
  assert.equal(git('show-ref'), refs);
  assert.throws(() => manager.inspect({commit: 'main'}), /exact locally available/);
  assert.throws(() => manager.inspect({commit: head, include: ['data/../foreign']}), /literal/);
  assert.throws(() => manager.inspect({commit: head, profile: 'other'}), /sparse\/full/);
});

test('promisor inspection lists every missing required path while leaving excluded missing blobs untouched', t => {
  const {run, manager, git, head, checkUnfetched} = partialFixture(t, [
    'README.md', 'scripts/tool.mjs', 'data/one.json', 'data/other/large.json'
  ]);
  const before = git('worktree', 'list', '--porcelain');
  const refs = git('show-ref');
  const result = JSON.parse(run({include: ['data/needed', 'data/one.json']}, 'inspect'));
  assert.equal(result.head, head);
  assert.equal(result.selectedBytes, null);
  assert.deepEqual(result.missing.flatMap(row => row.paths).sort(), ['README.md', 'data/one.json', 'scripts/tool.mjs']);
  assert.equal(result.missing.length, 3);
  assert.equal(result.inputs.filter(row => row.bytes === null).length, 3);
  assert.equal(result.availableBytes, result.inputs.reduce((sum, row) => sum + (row.bytes ?? 0), 0));
  assert.ok(!result.inputs.some(row => row.path === 'data/other/large.json'));
  assert.equal(git('worktree', 'list', '--porcelain'), before);
  assert.equal(git('show-ref'), refs);
  assert.ok(!fs.existsSync(manager.report().registry));
  assert.ok(!fs.existsSync(manager.report().root));
  checkUnfetched();
});

test('full promisor inspection includes excluded missing inputs and CLI exposes the same exact inventory', t => {
  const {repo, run, head, checkUnfetched} = partialFixture(t, 'data/other/large.json');
  const result = JSON.parse(run({profile: 'full'}, 'inspect'));
  assert.equal(result.selectedBytes, null);
  assert.deepEqual(result.missing.flatMap(row => row.paths), ['data/other/large.json']);
  const cli = execFileSync(process.execPath, [new URL('../scripts/local-workspace.mjs', import.meta.url).pathname,
    'inspect', '--commit', head, '--profile', 'full'], {
    cwd: repo, encoding: 'utf8', env: {...process.env, GIT_NO_LAZY_FETCH: '0'}
  });
  assert.deepEqual(JSON.parse(cli), result);
  checkUnfetched();
});


test('inspection groups missing duplicate OIDs without omitting materialized paths', t => {
  const {run, checkUnfetched} = partialFixture(t, 'README.md', {configureSource: ({repo, git}) => {
    const oid = git('rev-parse', 'HEAD:README.md').trim();
    execFileSync('git', ['-C', repo, 'update-index', '--add', '--cacheinfo', `100644,${oid},data/needed/alias.txt`]);
    git('commit', '-m', 'required path alias');
  }});
  const result = JSON.parse(run({include: ['data/needed']}, 'inspect'));
  assert.equal(result.missing.length, 1);
  assert.deepEqual(result.missing[0].paths, ['README.md', 'data/needed/alias.txt']);
  assert.equal(result.inputs.filter(row => row.bytes === null).length, 2);
  assert.equal(result.selectedBytes, null);
  checkUnfetched();
});

test('missing selected OIDs stay complete across batches without invoking cat-file on absent objects', t => {
  const {run, checkUnfetched} = partialFixture(t, ['README.md', 'scripts/tool.mjs'], {configureSource: ({repo, git}) => {
    const oid = git('rev-parse', 'HEAD:README.md').trim();
    const rows = Array.from({length: 2100}, (_, i) => `100644 ${oid}\tscripts/missing-alias-${i}.txt\n`).join('');
    execFileSync('git', ['-C', repo, 'update-index', '--index-info'], {input: rows});
    git('commit', '-m', 'missing aliases across batches');
  }});
  const result = JSON.parse(run({}, 'inspect'));
  assert.equal(result.missing.length, 2);
  assert.equal(result.missing.flatMap(row => row.paths).length, 2102);
  assert.equal(result.inputs.filter(row => row.bytes === null).length, 2102);
  assert.equal(result.selectedBytes, null);
  assert.equal(result.availableBytes, result.inputs.reduce((sum, row) => sum + (row.bytes ?? 0), 0));
  checkUnfetched();
});

test('old-Git promisor fatal is avoided even when every selected blob is absent', t => {
  const {repo, git, run, trace, checkUnfetched} = partialFixture(t, [
    '.gitignore', 'README.md', 'docs/guide.md', 'scripts/tool.mjs', 'data/one.json'
  ]);
  const absent = git('rev-parse', 'HEAD:README.md').trim();
  const legacy = spawnSync('git', ['-C', repo, 'cat-file', '--batch-check'], {
    input: absent + '\n', encoding: 'utf8', env: {...process.env, GIT_NO_LAZY_FETCH: '1', GIT_TRACE: trace}
  });
  if (legacy.status === 0) assert.equal(legacy.stdout, absent + ' missing\n');
  else {
    assert.equal(legacy.status, 128);
    assert.match(legacy.stderr, /lazy fetching disabled[\s\S]*could not fetch .* from promisor remote/);
  }
  fs.writeFileSync(trace, '');
  const result = JSON.parse(run({include: ['data/one.json']}, 'inspect'));
  assert.equal(result.inputCount, 5);
  assert.equal(result.missing.length, 5);
  assert.equal(result.availableBytes, 0);
  assert.equal(result.selectedBytes, null);
  assert.ok(result.inputs.every(row => row.bytes === null));
  assert.doesNotMatch(fs.readFileSync(trace, 'utf8'), /cat-file/);
  checkUnfetched();
});

test('unavailable exact commit fails without fetching or claiming a complete selected inventory', t => {
  const {repo, git, manager, head} = fixture(t);
  git('commit-graph', 'write', '--reachable');
  const object = path.join(repo, '.git/objects', head.slice(0, 2), head.slice(2));
  fs.unlinkSync(object);
  const trace = path.join(repo, 'commit-inspection.trace');
  const before = fs.readdirSync(path.join(repo, '.git/objects'), {recursive: true}).sort();
  const result = spawnSync(process.execPath, [new URL('../scripts/local-workspace.mjs', import.meta.url).pathname,
    'inspect', '--commit', head], {cwd: repo, encoding: 'utf8', env: {...process.env, GIT_NO_LAZY_FETCH: '0', GIT_TRACE: trace}});
  assert.equal(result.status, 1);
  assert.equal(result.stdout, '');
  assert.match(result.stderr, new RegExp(`Exact commit unavailable locally: ${head}`));
  assert.doesNotMatch(fs.readFileSync(trace, 'utf8'), /(?:built-in: git|run_command:) .*fetch/);
  assert.deepEqual(fs.readdirSync(path.join(repo, '.git/objects'), {recursive: true}).sort(), before);
  assert.ok(!fs.existsSync(manager.report().registry));
  assert.ok(!fs.existsSync(manager.report().root));
});

test('exact commit inspection refuses non-commits and ignores replacement-object bytes', t => {
  const {repo, git, manager, head} = fixture(t);
  const oid = git('rev-parse', 'HEAD:README.md').trim();
  assert.throws(() => manager.inspect({commit: oid}), /missing or not a commit/);
  const replacement = execFileSync('git', ['-C', repo, 'hash-object', '-w', '--stdin'], {
    input: 'foreign replacement contents', encoding: 'utf8'
  }).trim();
  git('replace', oid, replacement);
  const inspected = manager.inspect({commit: head});
  const root = inspected.inputs.find(row => row.path === 'README.md');
  assert.equal(root.oid, oid);
  assert.equal(root.bytes, 4);
  for (const profile of ['sparse', 'full']) {
    const entry = manager.allocate({worker: profile, slot: 'review', commit: head, profile});
    assert.equal(fs.readFileSync(path.join(entry.path, 'README.md'), 'utf8'), 'root');
    manager.release({worker: profile, slot: 'review', token: entry.token});
  }
});

test('missing root and descendant tree metadata are classified before any blob sizing', t => {
  for (const treePath of ['', 'scripts', 'data/other']) {
    const {repo, git, manager, head} = fixture(t);
    const oid = git('rev-parse', treePath ? `HEAD:${treePath}` : 'HEAD^{tree}').trim();
    fs.unlinkSync(path.join(repo, '.git/objects', oid.slice(0, 2), oid.slice(2)));
    const trace = path.join(repo, 'tree-inspection.trace');
    const refs = git('show-ref');
    const before = fs.readdirSync(path.join(repo, '.git/objects'), {recursive: true}).sort();
    const result = spawnSync(process.execPath, [new URL('../scripts/local-workspace.mjs', import.meta.url).pathname,
      'inspect', '--commit', head], {cwd: repo, encoding: 'utf8', env: {...process.env, GIT_NO_LAZY_FETCH: '0', GIT_TRACE: trace}});
    assert.equal(result.status, 1);
    assert.equal(result.stdout, '');
    assert.match(result.stderr, new RegExp(`Missing tree metadata:.*${oid}`));
    assert.match(result.stderr, /selected inventory cannot be enumerated/);
    assert.doesNotMatch(fs.readFileSync(trace, 'utf8'), /cat-file|(?:built-in: git|run_command:) .*fetch/);
    assert.deepEqual(fs.readdirSync(path.join(repo, '.git/objects'), {recursive: true}).sort(), before);
    assert.equal(git('show-ref'), refs);
    assert.throws(() => manager.allocate({worker: 'missing-tree', slot: 'review', commit: head}), /Missing tree metadata/);
    assert.ok(!fs.existsSync(path.join(manager.report().registry, 'state.json')));
    assert.ok(!fs.existsSync(manager.report().root));
  }
});

test('unreadable and corrupt selected objects remain read failures, never missing-blob inventories', t => {
  for (const fault of ['permission', 'corrupt']) {
    const {repo, git, run, manager, trace} = partialFixture(t, 'data/other/large.json');
    const oid = git('rev-parse', 'HEAD:README.md').trim();
    const object = path.join(repo, '.git/objects', oid.slice(0, 2), oid.slice(2));
    const original = fs.readFileSync(object);
    fs.chmodSync(object, fault === 'permission' ? 0 : 0o644);
    if (fault === 'corrupt') fs.writeFileSync(object, 'corrupt git object bytes');
    try {
      assert.throws(() => run({}, 'inspect'), error => {
        assert.equal(error.stdout, '');
        // Older Git may report an unreadable existing loose object as corrupt.
        // Preserve that read failure rather than reclassifying it as absent.
        assert.match(error.stderr, /Permission denied|corrupt|inflate|unable to unpack/i);
        assert.doesNotMatch(error.stderr, /selected inventory cannot be enumerated|Unknown input size/);
        return true;
      });
      assert.doesNotMatch(fs.readFileSync(trace, 'utf8'), /(?:built-in: git|run_command:) .*fetch/);
      assert.ok(!fs.existsSync(manager.report().registry));
      assert.ok(!fs.existsSync(manager.report().root));
    } finally {
      fs.chmodSync(object, 0o644);
      fs.writeFileSync(object, original);
    }
  }
});

test('coordinated exact-OID acquisition imports only inspected missing required blobs before normal allocation', t => {
  const {repo, git, run, manager, head, checkUnfetched} = partialFixture(t, [
    'README.md', 'scripts/tool.mjs', 'data/one.json', 'data/other/large.json'
  ], {configureSource: ({git}) => git('config', 'uploadpack.allowAnySHA1InWant', 'true')});
  const scope = {include: ['data/needed', 'data/one.json']};
  const before = JSON.parse(run(scope, 'inspect'));
  checkUnfetched();
  const refs = git('show-ref');
  const fetchHead = path.join(repo, '.git/FETCH_HEAD');
  assert.ok(!fs.existsSync(fetchHead));
  execFileSync('git', ['-C', repo, '-c', 'fetch.negotiationAlgorithm=noop', 'fetch', '--no-tags',
    '--no-write-fetch-head', '--no-recurse-submodules', '--no-auto-maintenance', '--filter=blob:none', '--stdin', 'origin'], {
    input: before.missing.map(row => row.oid).join('\n') + '\n', stdio: 'pipe', env: {...process.env, GIT_NO_LAZY_FETCH: '1'}
  });
  assert.equal(git('show-ref'), refs);
  assert.ok(!fs.existsSync(fetchHead));
  const after = JSON.parse(run(scope, 'inspect'));
  assert.deepEqual(after.missing, []);
  assert.equal(after.inputs.length, before.inputs.length);
  assert.equal(after.selectedBytes, after.inputs.reduce((sum, row) => sum + row.bytes, 0));
  const excluded = git('rev-parse', `${head}:data/other/large.json`).trim();
  const response = execFileSync('git', ['-C', repo, 'rev-list', '--objects', '--filter=tree:0', '--missing=print',
    '--ignore-missing', '--no-walk=unsorted', '--no-object-names', '--stdin'], {
    input: excluded + '\n', encoding: 'utf8', env: {...process.env, GIT_NO_LAZY_FETCH: '1'}
  });
  assert.equal(response, '');
  const entry = JSON.parse(run(scope));
  assert.equal(fs.readFileSync(path.join(entry.path, 'README.md'), 'utf8'), 'root');
  assert.equal(fs.readFileSync(path.join(entry.path, 'scripts/tool.mjs'), 'utf8'), 'tool');
  assert.equal(fs.readFileSync(path.join(entry.path, 'data/one.json'), 'utf8'), 'individual');
  assert.ok(!fs.existsSync(path.join(entry.path, 'data/other')));
  manager.release({worker: 'partial', slot: 'review', token: entry.token});
});

test('documented pinned bootstrap executes both accepted helpers and preserves stale working files', t => {
  const {repo, git, manager} = fixture(t);
  const helper = fs.readFileSync(new URL('../scripts/local-workspace.mjs', import.meta.url));
  const identity = fs.readFileSync(new URL('../scripts/worker-identity.mjs', import.meta.url));
  fs.writeFileSync(path.join(repo, 'scripts/local-workspace.mjs'), helper);
  fs.writeFileSync(path.join(repo, 'scripts/worker-identity.mjs'), identity);
  git('add', 'scripts'); git('commit', '-m', 'accepted helpers');
  const head = git('rev-parse', 'HEAD').trim();
  const stale = "throw Error('stale helper must not execute');\n";
  fs.writeFileSync(path.join(repo, 'scripts/local-workspace.mjs'), stale);
  fs.writeFileSync(path.join(repo, 'scripts/worker-identity.mjs'), stale);
  const before = git('status', '--porcelain');
  const refs = git('show-ref');
  const docs = fs.readFileSync(new URL('../docs/LOCAL_WORKSPACES.md', import.meta.url), 'utf8');
  const bootstrap = docs.split("<<'PYTHON'\n")[1].split('\nPYTHON')[0];
  const run = () => execFileSync('python3', ['-', head, 'inspect', '--commit', head, '--include', 'data/one.json'], {
    cwd: repo, input: bootstrap, encoding: 'utf8', stdio: 'pipe', env: {...process.env, GIT_NO_LAZY_FETCH: '1'}
  });
  const result = JSON.parse(run());
  assert.deepEqual(result, manager.inspect({commit: head, include: ['data/one.json']}));
  assert.equal(git('status', '--porcelain'), before);
  assert.equal(git('show-ref'), refs);
  assert.equal(fs.readFileSync(path.join(repo, 'scripts/local-workspace.mjs'), 'utf8'), stale);
  assert.equal(fs.readFileSync(path.join(repo, 'scripts/worker-identity.mjs'), 'utf8'), stale);
  assert.ok(!fs.readdirSync(path.join(repo, '.git')).some(name => name.startsWith('worldatlas-helper-')));
  const oid = git('rev-parse', `${head}:scripts/worker-identity.mjs`).trim();
  fs.unlinkSync(path.join(repo, '.git/objects', oid.slice(0, 2), oid.slice(2)));
  assert.throws(run, error => /Pinned helper missing/.test(error.stderr));
  assert.equal(fs.readFileSync(path.join(repo, 'scripts/local-workspace.mjs'), 'utf8'), stale);
  assert.ok(!fs.readdirSync(path.join(repo, '.git')).some(name => name.startsWith('worldatlas-helper-')));
  assert.ok(!fs.existsSync(manager.report().registry));
});

test('documented bootstrap refuses an absent promisor helper without an old-Git lazy-fetch fatal', t => {
  const {repo, git, head, trace, manager} = partialFixture(t, ['scripts/worker-identity.mjs', 'data/other/large.json'], {
    configureSource: ({repo, git}) => {
      for (const name of ['local-workspace.mjs', 'worker-identity.mjs'])
        fs.writeFileSync(path.join(repo, 'scripts', name), fs.readFileSync(new URL('../scripts/' + name, import.meta.url)));
      git('add', 'scripts'); git('commit', '-m', 'accepted promisor helpers');
    }
  });
  const docs = fs.readFileSync(new URL('../docs/LOCAL_WORKSPACES.md', import.meta.url), 'utf8');
  const bootstrap = docs.split("<<'PYTHON'\n")[1].split('\nPYTHON')[0];
  const refs = git('show-ref');
  const before = fs.readdirSync(path.join(repo, '.git/objects'), {recursive: true}).sort();
  assert.throws(() => execFileSync('python3', ['-', head, 'inspect', '--commit', head], {
    cwd: repo, input: bootstrap, encoding: 'utf8', stdio: 'pipe', env: {...process.env, GIT_NO_LAZY_FETCH: '0', GIT_TRACE: trace}
  }), error => {
    assert.equal(error.stdout, '');
    assert.match(error.stderr, /Pinned helper missing/);
    assert.doesNotMatch(error.stderr, /could not fetch|lazy fetching disabled/);
    return true;
  });
  assert.doesNotMatch(fs.readFileSync(trace, 'utf8'), /(?:built-in: git|run_command:) .*fetch/);
  assert.deepEqual(fs.readdirSync(path.join(repo, '.git/objects'), {recursive: true}).sort(), before);
  assert.equal(git('show-ref'), refs);
  assert.ok(!fs.readdirSync(path.join(repo, '.git')).some(name => name.startsWith('worldatlas-helper-')));
  assert.ok(!fs.existsSync(manager.report().registry));
});

test('inspection and allocation share every support prefix without suppressing an existing allocation lock', t => {
  const {repo, git, manager} = fixture(t);
  const required = ['src/main.js', 'hosted/api.mjs', 'drizzle/0001.sql', '.github/workflows/check.yml',
    '.agents/skills/example/SKILL.md', 'coordination/templates/example.json'];
  for (const name of required) {
    fs.mkdirSync(path.dirname(path.join(repo, name)), {recursive: true});
    fs.writeFileSync(path.join(repo, name), name);
  }
  git('add', '.'); git('commit', '-m', 'every support prefix');
  const head = git('rev-parse', 'HEAD').trim();
  const result = manager.inspect({commit: head});
  for (const name of required) assert.ok(result.inputs.some(row => row.path === name), name);
  const {registry} = manager.report();
  const lock = path.join(registry, 'lock');
  fs.mkdirSync(lock, {recursive: true});
  assert.deepEqual(manager.inspect({commit: head}), result);
  assert.throws(() => manager.allocate({worker: 'one', slot: 'review', commit: head}), /locked/);
  assert.ok(fs.existsSync(lock));
  fs.rmdirSync(lock);
  const entry = manager.allocate({worker: 'one', slot: 'review', commit: head, reserveGiB: 1 / GiB});
  assert.equal(entry.reservation, result.selectedBytes);
  for (const row of result.inputs) assert.ok(fs.existsSync(path.join(entry.path, row.path)), row.path);
  assert.ok(!fs.existsSync(path.join(entry.path, 'data/other')));
  manager.release({worker: 'one', slot: 'review', token: entry.token});
});


test('complete documented shell bootstrap refuses failed refresh instead of executing cached main', t => {
  const {repo, git} = fixture(t);
  for (const name of ['local-workspace.mjs', 'worker-identity.mjs'])
    fs.writeFileSync(path.join(repo, 'scripts', name), fs.readFileSync(new URL('../scripts/' + name, import.meta.url)));
  git('add', 'scripts'); git('commit', '-m', 'cached accepted helpers');
  const head = git('rev-parse', 'HEAD').trim();
  git('update-ref', 'refs/remotes/origin/main', head);
  git('remote', 'set-url', 'origin', path.join(repo, 'unavailable-origin'));
  const refs = git('show-ref');
  const status = git('status', '--porcelain');
  const docs = fs.readFileSync(new URL('../docs/LOCAL_WORKSPACES.md', import.meta.url), 'utf8');
  const block = docs.split('## Refresh a stale checkout without changing its files')[1].split('```sh\n')[1].split('\n```')[0]
    .replace('data/YOUR-REQUIRED-PATH', 'data/one.json');
  assert.throws(() => execFileSync('bash', ['-c', block], {cwd: repo, encoding: 'utf8', stdio: 'pipe'}), error => {
    assert.doesNotMatch(error.stdout, /inputCount|selectedBytes/);
    assert.match(error.stderr, /does not appear to be a git repository/);
    return error.status !== 0;
  });
  assert.equal(git('show-ref'), refs);
  assert.equal(git('status', '--porcelain'), status);
  assert.ok(!fs.readdirSync(path.join(repo, '.git')).some(name => name.startsWith('worldatlas-helper-')));
  git('remote', 'set-url', 'origin', repo);
  git('config', 'uploadpack.allowFilter', 'true');
  const result = JSON.parse(execFileSync('bash', ['-c', block], {cwd: repo, encoding: 'utf8', stdio: 'pipe'}));
  assert.equal(result.head, head);
  assert.ok(result.inputs.some(row => row.path === 'data/one.json'));
  assert.ok(!fs.readdirSync(path.join(repo, '.git')).some(name => name.startsWith('worldatlas-helper-')));
  git('config', '--unset-all', 'remote.origin.fetch');
  git('update-ref', '-d', 'refs/remotes/origin/main');
  assert.throws(() => execFileSync('bash', ['-c', block], {cwd: repo, encoding: 'utf8', stdio: 'pipe'}), error => {
    assert.doesNotMatch(error.stdout, /inputCount|selectedBytes/);
    assert.match(error.stderr, /Needed a single revision/);
    return error.status !== 0;
  });
  assert.ok(!fs.readdirSync(path.join(repo, '.git')).some(name => name.startsWith('worldatlas-helper-')));
});
