import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawn, spawnSync} from 'node:child_process';

const helper = fileURLToPath(new URL('../scripts/acquire-ci-checkout.py', import.meta.url));
const realGit = spawnSync('which', ['git'], {encoding: 'utf8'}).stdout.trim();
const token = 'fixture-secret-only-checkout-1787';
const base64Token = Buffer.from('x-access-token:' + token).toString('base64');
const fixtureEnv = {...process.env, GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: os.devNull,
  PYTHONDONTWRITEBYTECODE: '1', INTEGRATION_PROFILE: '', INTEGRATION_TEST_SELECTION: ''};
function command(executable, args, options = {}) {
  const result = spawnSync(executable, args, {encoding: 'utf8', env: fixtureEnv, ...options});
  assert.equal(result.status, 0, result.stderr || result.error?.message);
  return result.stdout.trim();
}
function fixture(t, mode = 'success') {
  const directory = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'ci-checkout-')));
  t.after(() => fs.rmSync(directory, {recursive: true, force: true}));
  const source = path.join(directory, 'source'), workspace = path.join(directory, 'workspace');
  const shim = path.join(directory, 'shim'), trace = path.join(directory, 'calls.jsonl');
  fs.mkdirSync(source); fs.mkdirSync(workspace); fs.mkdirSync(shim);
  const git = args => command(realGit, ['-c', 'user.name=Checkout test', '-c', 'user.email=checkout@example.invalid', ...args], {cwd: source});
  git(['init', '--quiet', '--template=']);
  git(['config', 'uploadpack.allowFilter', 'true']);
  fs.writeFileSync(path.join(source, 'file.txt'), 'exact complete checkout\n');
  fs.writeFileSync(path.join(source, '.gitattributes'), '*.txt filter=malicious\n');
  fs.writeFileSync(path.join(source, '.hidden'), 'retained hidden file\n');
  fs.writeFileSync(path.join(source, 'execute.sh'), '#!/bin/sh\nexit 0\n', {mode: 0o755});
  fs.symlinkSync('file.txt', path.join(source, 'link'));
  for (const [name, text] of Object.entries({
    'data/regional-review/source-only/body.txt': 'unconsumed regional source-only bytes\n',
    'research/campaigns/source-only/body.txt': 'unconsumed historical campaign bytes\n',
    'research/geography/required/body.txt': 'required original scientific source bytes\n',
    'coordination/engineering/required/body.txt': 'required archived engineering bytes\n',
    'data/geography/required/body.txt': 'required application bytes\n',
    'test/current.test.mjs': 'required current software test inventory\n'
  })) { fs.mkdirSync(path.dirname(path.join(source, name)), {recursive: true}); fs.writeFileSync(path.join(source, name), text); }
  git(['add', '.']); git(['commit', '--quiet', '-m', 'fixture']);
  const sha = git(['rev-parse', 'HEAD']), tree = git(['rev-parse', 'HEAD^{tree}']);
  const count = path.join(directory, 'fetches'), descendant = path.join(directory, 'descendant');
  const sentinel = path.join(directory, 'smudge-ran');
  const config = path.join(directory, 'hostile.gitconfig');
  fs.writeFileSync(config, `[filter "malicious"]\n\tsmudge = touch ${sentinel}\n\trequired = true\n`);
  fs.writeFileSync(path.join(shim, 'git'), `#!/usr/bin/env python3
import json,os,signal,subprocess,sys,time
args=sys.argv[1:]
mode=${JSON.stringify(mode)}
count=${JSON.stringify(count)}
trace=${JSON.stringify(trace)}
pidfile=${JSON.stringify(descendant)}
workspace=${JSON.stringify(workspace)}
isfetch='fetch' in args
ischeckout='checkout' in args
with open(trace,'a') as out:
 out.write(json.dumps({'fetch':isfetch,'checkout':ischeckout,'auth':bool(os.environ.get('GIT_CONFIG_VALUE_0')),'token':bool(os.environ.get('WORLDATLAS_CHECKOUT_TOKEN')),'gh':bool(os.environ.get('GH_TOKEN')),'global':os.environ.get('GIT_CONFIG_GLOBAL'),'args':args})+'\\n')
if isfetch:
 try:n=int(open(count).read())+1
 except FileNotFoundError:n=1
 with open(count,'w') as out:out.write(str(n))
 if mode=='failure':
  sys.stderr.write('HTTP AUTHORIZATION ${token} ${base64Token}\\n')
  sys.exit(128)
 if mode=='hang':
  childcode="import os,signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);open("+repr(pidfile)+",'w').write(str(os.getpid()));time.sleep(120)"
  child=subprocess.Popen([sys.executable,'-c',childcode])
  signal.signal(signal.SIGTERM,signal.SIG_IGN)
  sys.stderr.write('Receiving objects:  50% (1/2), ${token} ${base64Token}\\r');sys.stderr.flush()
  time.sleep(120)
 if mode=='progressing':
  for percent in (25,50,75):
   sys.stderr.write('Receiving objects: %d%% (1/2), ${token} ${base64Token}\\r' % percent);sys.stderr.flush()
   time.sleep(1)
 if mode=='foreign-workspace':open(os.path.join(workspace,'foreign'),'w').write('preserve me')
 if mode=='wrong-sha':args[-1]=${JSON.stringify(sha)}
if ischeckout and mode=='materialize-hang':
 childcode="import os,signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);open("+repr(pidfile)+",'w').write(str(os.getpid()));time.sleep(120)"
 child=subprocess.Popen([sys.executable,'-c',childcode])
 signal.signal(signal.SIGTERM,signal.SIG_IGN)
 time.sleep(120)
if ischeckout and mode=='credential-leak':
 subprocess.check_call([${JSON.stringify(realGit)},'config','--local','http.https://github.com/.extraheader','untrusted-header'])
os.execv(${JSON.stringify(realGit)},[${JSON.stringify(realGit)},'-c',${JSON.stringify('url.file://')}+${JSON.stringify(source)}+'.insteadOf=https://github.com/ChengshuLi/WorldAtlas.git',*args])
`, {mode: 0o755});
  const env = {...fixtureEnv, PATH: shim + path.delimiter + process.env.PATH,
    WORLDATLAS_CHECKOUT_TOKEN: token, GH_TOKEN: 'unrelated-secret',
    GIT_CONFIG_GLOBAL: config, GIT_CONFIG_COUNT: '1', GIT_CONFIG_KEY_0: 'filter.malicious.smudge', GIT_CONFIG_VALUE_0: `touch ${sentinel}`};
  const args = (extra = []) => [helper, '--repository', 'ChengshuLi/WorldAtlas', '--sha', sha, '--tree', tree,
    '--workspace', workspace, '--total-timeout-seconds', '12', ...extra];
  const run = (extra = []) => spawnSync('python3', args(extra), {encoding: 'utf8', env, timeout: 16000});
  const rows = () => fs.existsSync(trace) ? fs.readFileSync(trace, 'utf8').trim().split('\n').map(JSON.parse) : [];
  const fetches = () => fs.existsSync(count) ? Number(fs.readFileSync(count, 'utf8')) : 0;
  const events = result => result.stdout.trim().split('\n').filter(Boolean).map(JSON.parse);
  const clean = () => assert.deepEqual(fs.readdirSync(directory).filter(name => name.startsWith('.worldatlas-ci-checkout-')), []);
  return {directory, workspace, source, sha, tree, run, args, env, rows, fetches, events, clean, descendant, sentinel, git};
}
function noSecrets(result) {
  assert.doesNotMatch(result.stdout + result.stderr, new RegExp(token + '|' + base64Token + '|unrelated-secret'));
}
function noLiveDescendant(file) {
  const pid = fs.readFileSync(file, 'utf8');
  const result = spawnSync('/bin/ps', ['-p', pid, '-o', 'stat='], {encoding: 'utf8'});
  assert.ok(!result.error, result.error?.message);
  assert.ok(!result.stdout.trim() || result.stdout.trim().startsWith('Z'), `descendant ${pid} remains live`);
}

test('real Git checkout preserves exact tree, modes, symlinks and detached identity without credential inheritance', t => {
  const f = fixture(t), result = f.run();
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.equal(command(realGit, ['-C', f.workspace, 'rev-parse', 'HEAD']), f.sha);
  assert.equal(command(realGit, ['-C', f.workspace, 'rev-parse', 'HEAD^{tree}']), f.tree);
  assert.equal(spawnSync(realGit, ['-C', f.workspace, 'symbolic-ref', '-q', 'HEAD']).status, 1);
  assert.equal(fs.readFileSync(path.join(f.workspace, 'file.txt'), 'utf8'), 'exact complete checkout\n');
  assert.equal(fs.readlinkSync(path.join(f.workspace, 'link')), 'file.txt');
  assert.equal(fs.statSync(path.join(f.workspace, 'execute.sh')).mode & 0o111, 0o111);
  assert.ok(!fs.existsSync(f.sentinel));
  assert.ok(f.rows().filter(row => row.fetch).every(row => row.auth && row.args.includes('--progress') && row.args.includes('--depth=1')));
  assert.ok(f.rows().filter(row => !row.fetch).every(row => !row.auth));
  assert.ok(f.rows().every(row => !row.token && !row.gh && row.global === os.devNull));
  assert.doesNotMatch(fs.readFileSync(path.join(f.workspace, '.git/config'), 'utf8'), /extraheader|credential|AUTHORIZATION|fixture-secret/);
  assert.equal(f.events(result).at(-1).event, 'checkout-complete');
  f.clean(); noSecrets(result);
});

test('complete software profile excludes only source-only files and blobs while preserving exact tree and all regression inputs', t => {
  const f = fixture(t);
  Object.assign(f.env, {INTEGRATION_PROFILE: 'full', INTEGRATION_TEST_SELECTION: 'complete'});
  const result = f.run();
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.equal(command(realGit, ['-C', f.workspace, 'rev-parse', 'HEAD']), f.sha);
  assert.equal(command(realGit, ['-C', f.workspace, 'rev-parse', 'HEAD^{tree}']), f.tree);
  for (const name of ['data/regional-review/source-only/body.txt', 'research/campaigns/source-only/body.txt']) {
    assert.ok(!fs.existsSync(path.join(f.workspace, name)), name);
    const blob = f.git(['rev-parse', `${f.sha}:${name}`]);
    const absent = spawnSync(realGit, ['-C', f.workspace, 'cat-file', '-e', blob],
      {encoding: 'utf8', env: {...fixtureEnv, GIT_NO_LAZY_FETCH: '1'}, timeout: 2000});
    assert.notEqual(absent.status, 0, 'excluded blob must not have been downloaded');
  }
  for (const name of ['research/geography/required/body.txt', 'coordination/engineering/required/body.txt',
    'data/geography/required/body.txt', 'test/current.test.mjs', 'file.txt', '.hidden', 'execute.sh']) {
    assert.deepEqual(fs.readFileSync(path.join(f.workspace, name)), fs.readFileSync(path.join(f.source, name)), name);
  }
  assert.equal(fs.readlinkSync(path.join(f.workspace, 'link')), 'file.txt');
  assert.equal(fs.statSync(path.join(f.workspace, 'execute.sh')).mode & 0o111, 0o111);
  assert.equal(command(realGit, ['-C', f.workspace, 'config', '--get', 'remote.origin.promisor']), 'false');
  assert.notEqual(spawnSync(realGit, ['-C', f.workspace, 'config', '--get', 'remote.origin.partialclonefilter']).status, 0);
  assert.ok(f.rows().some(row => row.fetch && row.args.includes('--filter=blob:none')));
  assert.ok(f.rows().filter(row => row.auth).every(row => row.fetch || row.checkout));
  assert.ok(f.rows().every(row => !row.token && !row.gh && row.global === os.devNull));
  assert.ok(!fs.existsSync(f.sentinel));
  assert.doesNotMatch(fs.readFileSync(path.join(f.workspace, '.git/config'), 'utf8'), /extraheader|credential|AUTHORIZATION|fixture-secret|insteadOf/);
  f.clean(); noSecrets(result);
});

test('sparse software acquisition preserves explicit complete historical commit fetch without later lazy hydration', t => {
  const f = fixture(t), original = f.sha;
  fs.writeFileSync(path.join(f.source, 'file.txt'), 'new current software bytes\n');
  fs.writeFileSync(path.join(f.source, 'data/geography/required/body.txt'), 'new current application bytes\n');
  f.git(['add', '.']); f.git(['commit', '--quiet', '-m', 'current']);
  const current = f.git(['rev-parse', 'HEAD']), tree = f.git(['rev-parse', 'HEAD^{tree}']);
  Object.assign(f.env, {INTEGRATION_PROFILE: 'full', INTEGRATION_TEST_SELECTION: 'complete'});
  const result = f.run(['--sha', current, '--tree', tree]);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.notEqual(spawnSync(realGit, ['-C', f.workspace, 'cat-file', '-e', original + '^{commit}'],
    {env: {...fixtureEnv, GIT_NO_LAZY_FETCH: '1'}, timeout: 2000}).status, 0);
  command(realGit, ['-C', f.workspace, 'fetch', '--no-tags', '--depth=1', 'file://' + f.source, original],
    {env: {...fixtureEnv, GIT_NO_LAZY_FETCH: '1'}, timeout: 2000});
  assert.equal(command(realGit, ['-C', f.workspace, 'show', original + ':data/geography/required/body.txt'],
    {env: {...fixtureEnv, GIT_NO_LAZY_FETCH: '1'}, timeout: 2000}), 'required application bytes');
  assert.ok(!fs.existsSync(path.join(f.workspace, 'data/regional-review')));
  assert.equal(command(realGit, ['-C', f.workspace, 'rev-parse', 'HEAD']), current);
  f.clean(); noSecrets(result);
});

for (const [profile, selection] of [['full', 'selected-data'], ['full', 'selected-output'], ['evidence', 'complete']]) {
  test(`non-complete software route ${profile}/${selection} retains complete checkout`, t => {
    const f = fixture(t); Object.assign(f.env, {INTEGRATION_PROFILE: profile, INTEGRATION_TEST_SELECTION: selection});
    const result = f.run(); assert.equal(result.status, 0, result.stdout + result.stderr);
    assert.ok(fs.existsSync(path.join(f.workspace, 'data/regional-review/source-only/body.txt')));
    assert.ok(fs.existsSync(path.join(f.workspace, 'research/campaigns/source-only/body.txt')));
    assert.ok(!f.rows().some(row => row.args.includes('--filter=blob:none')));
    assert.ok(f.rows().filter(row => !row.fetch).every(row => !row.auth));
    f.clean(); noSecrets(result);
  });
}

test('progressing fetch beyond the previous scaled cutoff completes once within the total deadline', t => {
  const f = fixture(t, 'progressing'), result = f.run();
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.equal(f.fetches(), 1); assert.equal(f.rows().filter(row => row.args?.includes('init')).length, 1);
  const events = f.events(result), fetch = events.find(row => row.event === 'phase-complete' && row.phase === 'fetch');
  assert.ok(fetch.phase_seconds >= 3, 'actual fetch exceeds the former 2-second fixture cutoff');
  assert.equal(fetch.status, 'success');
  assert.ok(events.some(row => row.event === 'git-progress' && row.phase === 'fetch'
    && row.activity === 'Receiving objects' && [25, 50, 75].includes(row.percent)));
  assert.ok(events.every(row => !Object.hasOwn(row, 'attempt') && !Object.hasOwn(row, 'attempts')));
  assert.ok(!events.some(row => row.event === 'acquisition-retry'));
  f.clean(); noSecrets(result);
});

test('one command failure stops after one fetch without publishing or leaking Git stderr', t => {
  const f = fixture(t, 'failure'), result = f.run();
  assert.equal(result.status, 1); assert.equal(f.fetches(), 1);
  assert.equal(f.rows().filter(row => row.args?.includes('init')).length, 1);
  assert.match(result.stdout, /command-failed/);
  assert.deepEqual(fs.readdirSync(f.workspace), []); f.clean(); noSecrets(result);
});

test('overall deadline stops actual TERM-resistant Git child and grandchild with terminal cleanup', t => {
  const f = fixture(t, 'hang'), start = Date.now(), result = f.run(['--total-timeout-seconds', '7']);
  assert.equal(result.status, 1, result.stdout + result.stderr);
  assert.equal(f.fetches(), 1); assert.match(result.stdout, /acquisition-deadline/);
  assert.ok(Date.now() - start < 8500, 'cleanup stays inside the overall deadline');
  noLiveDescendant(f.descendant); assert.deepEqual(fs.readdirSync(f.workspace), []); f.clean(); noSecrets(result);
});

test('software blob materialization shares the unchanged total deadline and cleans TERM-resistant descendants', t => {
  const f = fixture(t, 'materialize-hang');
  Object.assign(f.env, {INTEGRATION_PROFILE: 'full', INTEGRATION_TEST_SELECTION: 'complete'});
  const start = Date.now(), result = f.run(['--total-timeout-seconds', '7']);
  assert.equal(result.status, 1, result.stdout + result.stderr);
  assert.equal(f.fetches(), 1); assert.match(result.stdout, /acquisition-deadline/);
  assert.ok(Date.now() - start < 8500);
  assert.ok(f.events(result).some(row => row.phase === 'materialize' && row.status === 'acquisition-deadline'));
  noLiveDescendant(f.descendant); assert.deepEqual(fs.readdirSync(f.workspace), []); f.clean(); noSecrets(result);
});

test('SIGTERM cancels an actual hanging process group, cleans it and performs no second fetch', async t => {
  const f = fixture(t, 'hang');
  const child = spawn('python3', f.args(), {env: f.env});
  let stdout = '', stderr = '';
  child.stdout.on('data', value => { stdout += value; }); child.stderr.on('data', value => { stderr += value; });
  const completed = new Promise(resolve => child.once('close', (status, signal) => resolve({status, signal, stdout, stderr})));
  const start = Date.now();
  while (!fs.existsSync(f.descendant) && Date.now() - start < 3000) await new Promise(resolve => setTimeout(resolve, 20));
  assert.ok(fs.existsSync(f.descendant));
  child.kill('SIGTERM');
  const result = await completed;
  assert.equal(result.status, 130, result.stdout + result.stderr); assert.equal(f.fetches(), 1);
  noLiveDescendant(f.descendant); assert.deepEqual(fs.readdirSync(f.workspace), []); f.clean(); noSecrets(result);
});

test('unverifiable process cleanup preserves private staging, performs no second fetch and preserves the workspace', t => {
  const f = fixture(t, 'hang');
  const driver = path.join(f.directory, 'unavailable-inspection.py');
  fs.writeFileSync(driver, `import importlib.util,os,sys
spec=importlib.util.spec_from_file_location('acquisition',${JSON.stringify(helper)})
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
ordinary=module.live_group
def unavailable(pgid):
 if os.path.exists(${JSON.stringify(f.descendant)}):raise OSError('fixture process inspection unavailable')
 return ordinary(pgid)
module.live_group=unavailable
sys.exit(module.main())
`);
  const result = spawnSync('python3', [driver, ...f.args(['--total-timeout-seconds', '7']).slice(1)],
    {encoding: 'utf8', env: f.env, timeout: 16000});
  assert.equal(result.status, 1, result.stdout + result.stderr);
  assert.equal(f.fetches(), 1); assert.match(result.stdout, /process-cleanup-failed/);
  const retained = f.events(result).find(row => row.event === 'staging-preserved');
  assert.ok(retained); assert.ok(fs.existsSync(path.join(retained.owned_directory, '.git')));
  assert.deepEqual(fs.readdirSync(f.workspace), []);
  // Our independent observer can confirm the best-effort kill before the fixture
  // removes retained staging; the helper correctly could not certify that fact.
  noLiveDescendant(f.descendant); noSecrets(result);
});

for (const mismatch of ['sha', 'tree']) test(`wrong authenticated ${mismatch} refuses before checkout and with one fetch`, t => {
  const f = fixture(t, mismatch === 'sha' ? 'wrong-sha' : 'success');
  const result = f.run(['--' + mismatch, '0'.repeat(40)]);
  assert.equal(result.status, 1); assert.equal(f.fetches(), 1);
  assert.match(result.stdout, /git-identity-mismatch/); assert.ok(!f.rows().some(row => row.checkout));
  assert.deepEqual(fs.readdirSync(f.workspace), []); f.clean(); noSecrets(result);
});

test('initial nonempty and symlink destinations preserve foreign files before any Git command', t => {
  const f = fixture(t); fs.writeFileSync(path.join(f.workspace, 'foreign'), 'preserved');
  assert.equal(f.run().status, 1); assert.equal(f.fetches(), 0);
  const link = path.join(f.directory, 'alias'); fs.symlinkSync(f.workspace, link);
  assert.equal(f.run(['--workspace', link]).status, 1); assert.equal(f.fetches(), 0);
  assert.equal(fs.readFileSync(path.join(link, 'foreign'), 'utf8'), 'preserved');
});

test('foreign contents arriving during fetch are preserved and prevent publication', t => {
  const f = fixture(t, 'foreign-workspace'), result = f.run();
  assert.equal(result.status, 1); assert.match(result.stdout, /workspace-changed/);
  assert.deepEqual(fs.readdirSync(f.workspace), ['foreign']);
  assert.equal(fs.readFileSync(path.join(f.workspace, 'foreign'), 'utf8'), 'preserve me'); f.clean();
});

test('invalid and already-spent bootstrap budgets refuse before filesystem mutation', t => {
  const f = fixture(t);
  for (const args of [['--elapsed-seconds', 'nan'], ['--elapsed-seconds', '-1'], ['--elapsed-seconds', '12'],
    ['--total-timeout-seconds', 'inf'], ['--total-timeout-seconds', '-1'], ['--total-timeout-seconds', '1801'],
    ['--elapsed-seconds', 'inf'], ['--total-timeout-seconds', '4']]) {
    assert.equal(f.run(args).status, 1, args.join(' '));
  }
  assert.equal(f.fetches(), 0); assert.deepEqual(fs.readdirSync(f.workspace), []); f.clean();
});

test('trusted finite budgets above the measured default are configurable without waiting for their deadline', t => {
  const f = fixture(t), result = f.run(['--total-timeout-seconds', '600']);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.equal(f.events(result).at(-1).event, 'checkout-complete');
  assert.ok(f.events(result).at(-1).remaining_seconds > 580);
  f.clean(); noSecrets(result);
});

test('bootstrap elapsed time reduces the single total budget, including terminal cleanup', t => {
  const f = fixture(t, 'hang');
  const start = Date.now();
  const result = f.run(['--total-timeout-seconds', '10', '--elapsed-seconds', '4']);
  assert.equal(result.status, 1); assert.equal(f.fetches(), 1);
  assert.ok(Date.now() - start < 6500, 'spent bootstrap time must not be granted again');
  noLiveDescendant(f.descendant); assert.deepEqual(fs.readdirSync(f.workspace), []); f.clean(); noSecrets(result);
});

for (const option of ['--fetch-timeout-seconds', '--max-attempts']) test('removed '+option+' refuses before mutation', t => {
  const f = fixture(t), result = f.run([option, '2']);
  assert.equal(result.status, 2); assert.match(result.stderr, /unrecognized arguments/);
  assert.equal(f.fetches(), 0); assert.deepEqual(fs.readdirSync(f.workspace), []); f.clean(); noSecrets(result);
});

test('credential audit refuses contaminated local configuration without promotion', t => {
  const f = fixture(t, 'credential-leak'), result = f.run();
  assert.equal(result.status, 1); assert.equal(f.fetches(), 1);
  assert.match(result.stdout, /checkout-verification-failed/);
  assert.deepEqual(fs.readdirSync(f.workspace), []); f.clean(); noSecrets(result);
});
