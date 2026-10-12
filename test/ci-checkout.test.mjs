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
  PYTHONDONTWRITEBYTECODE: '1'};
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
  fs.writeFileSync(path.join(source, 'file.txt'), 'exact complete checkout\n');
  fs.writeFileSync(path.join(source, '.gitattributes'), '*.txt filter=malicious\n');
  fs.writeFileSync(path.join(source, '.hidden'), 'retained hidden file\n');
  fs.writeFileSync(path.join(source, 'execute.sh'), '#!/bin/sh\nexit 0\n', {mode: 0o755});
  fs.symlinkSync('file.txt', path.join(source, 'link'));
  git(['add', '.']); git(['commit', '--quiet', '-m', 'fixture']);
  const sha = git(['rev-parse', 'HEAD']), tree = git(['rev-parse', 'HEAD^{tree}']);
  const count = path.join(directory, 'attempts'), descendant = path.join(directory, 'descendant');
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
 if mode in ('transient','persistent') and (mode=='persistent' or n==1):
  sys.stderr.write('HTTP AUTHORIZATION ${token} ${base64Token}\\n')
  sys.exit(128)
 if mode in ('hang-once','hang-always') and (mode=='hang-always' or n==1):
  childcode="import os,signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);open("+repr(pidfile)+",'w').write(str(os.getpid()));time.sleep(120)"
  child=subprocess.Popen([sys.executable,'-c',childcode])
  signal.signal(signal.SIGTERM,signal.SIG_IGN)
  sys.stderr.write('Receiving objects:  50% (1/2), ${token} ${base64Token}\\r');sys.stderr.flush()
  time.sleep(120)
 if mode=='hang-once' and n==2:
  pid=int(open(pidfile).read())
  result=subprocess.run(['/bin/ps','-p',str(pid),'-o','stat='],stdout=subprocess.PIPE,universal_newlines=True)
  if result.stdout.strip() and not result.stdout.strip().startswith('Z'):
   sys.exit(99)
  with open(trace,'a') as out:out.write(json.dumps({'cleanup_before_retry':True})+'\\n')
 if mode=='foreign-workspace':open(os.path.join(workspace,'foreign'),'w').write('preserve me')
 if mode=='wrong-sha':args[-1]=${JSON.stringify(sha)}
 args[args.index('origin')]='file://${source}'
os.execv(${JSON.stringify(realGit)},[${JSON.stringify(realGit)},*args])
`, {mode: 0o755});
  const env = {...fixtureEnv, PATH: shim + path.delimiter + process.env.PATH,
    WORLDATLAS_CHECKOUT_TOKEN: token, GH_TOKEN: 'unrelated-secret',
    GIT_CONFIG_GLOBAL: config, GIT_CONFIG_COUNT: '1', GIT_CONFIG_KEY_0: 'filter.malicious.smudge', GIT_CONFIG_VALUE_0: `touch ${sentinel}`};
  const args = (extra = []) => [helper, '--repository', 'ChengshuLi/WorldAtlas', '--sha', sha, '--tree', tree,
    '--workspace', workspace, '--fetch-timeout-seconds', '2', '--total-timeout-seconds', '12', ...extra];
  const run = (extra = []) => spawnSync('python3', args(extra), {encoding: 'utf8', env, timeout: 16000});
  const rows = () => fs.existsSync(trace) ? fs.readFileSync(trace, 'utf8').trim().split('\n').map(JSON.parse) : [];
  const attempts = () => fs.existsSync(count) ? Number(fs.readFileSync(count, 'utf8')) : 0;
  const events = result => result.stdout.trim().split('\n').filter(Boolean).map(JSON.parse);
  const clean = () => assert.deepEqual(fs.readdirSync(directory).filter(name => name.startsWith('.worldatlas-ci-checkout-')), []);
  return {directory, workspace, source, sha, tree, run, args, env, rows, attempts, events, clean, descendant, sentinel};
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

test('transient fetch retries once in a fresh repository and publishes only the complete second attempt', t => {
  const f = fixture(t, 'transient'), result = f.run();
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.equal(f.attempts(), 2); assert.equal(f.events(result).filter(row => row.event === 'acquisition-retry').length, 1);
  assert.equal(f.events(result).at(-1).attempts, 2); f.clean(); noSecrets(result);
});

test('persistent failure stops at two fetches without publishing or leaking Git stderr', t => {
  const f = fixture(t, 'persistent'), result = f.run();
  assert.equal(result.status, 1); assert.equal(f.attempts(), 2);
  assert.deepEqual(fs.readdirSync(f.workspace), []); f.clean(); noSecrets(result);
});

test('an actual TERM-resistant Git child and grandchild are dead before the next fetch', t => {
  const f = fixture(t, 'hang-once'), result = f.run(['--fetch-timeout-seconds', '1']);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.equal(f.attempts(), 2); assert.ok(f.rows().some(row => row.cleanup_before_retry));
  assert.ok(f.events(result).some(row => row.event === 'git-progress' && row.percent === 50));
  noLiveDescendant(f.descendant); f.clean(); noSecrets(result);
});

test('SIGTERM cancels an actual hanging process group, cleans it and never retries', async t => {
  const f = fixture(t, 'hang-always');
  const child = spawn('python3', f.args(), {env: f.env});
  let stdout = '', stderr = '';
  child.stdout.on('data', value => { stdout += value; }); child.stderr.on('data', value => { stderr += value; });
  const completed = new Promise(resolve => child.once('close', (status, signal) => resolve({status, signal, stdout, stderr})));
  const start = Date.now();
  while (!fs.existsSync(f.descendant) && Date.now() - start < 3000) await new Promise(resolve => setTimeout(resolve, 20));
  assert.ok(fs.existsSync(f.descendant));
  child.kill('SIGTERM');
  const result = await completed;
  assert.equal(result.status, 130, result.stdout + result.stderr); assert.equal(f.attempts(), 1);
  noLiveDescendant(f.descendant); assert.deepEqual(fs.readdirSync(f.workspace), []); f.clean(); noSecrets(result);
});

test('unverifiable process cleanup preserves private staging, refuses retry and preserves the workspace', t => {
  const f = fixture(t, 'hang-always');
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
  const result = spawnSync('python3', [driver, ...f.args(['--fetch-timeout-seconds', '1']).slice(1)],
    {encoding: 'utf8', env: f.env, timeout: 16000});
  assert.equal(result.status, 1, result.stdout + result.stderr);
  assert.equal(f.attempts(), 1); assert.match(result.stdout, /process-cleanup-failed/);
  const retained = f.events(result).find(row => row.event === 'staging-preserved');
  assert.ok(retained); assert.ok(fs.existsSync(path.join(retained.owned_directory, '.git')));
  assert.deepEqual(fs.readdirSync(f.workspace), []);
  // Our independent observer can confirm the best-effort kill before the fixture
  // removes retained staging; the helper correctly could not certify that fact.
  noLiveDescendant(f.descendant); noSecrets(result);
});

for (const mismatch of ['sha', 'tree']) test(`wrong authenticated ${mismatch} refuses before checkout and without retry`, t => {
  const f = fixture(t, mismatch === 'sha' ? 'wrong-sha' : 'success');
  const result = f.run(['--' + mismatch, '0'.repeat(40)]);
  assert.equal(result.status, 1); assert.equal(f.attempts(), 1);
  assert.match(result.stdout, /git-identity-mismatch/); assert.ok(!f.rows().some(row => row.checkout));
  assert.deepEqual(fs.readdirSync(f.workspace), []); f.clean(); noSecrets(result);
});

test('initial nonempty and symlink destinations preserve foreign files before any Git command', t => {
  const f = fixture(t); fs.writeFileSync(path.join(f.workspace, 'foreign'), 'preserved');
  assert.equal(f.run().status, 1); assert.equal(f.attempts(), 0);
  const link = path.join(f.directory, 'alias'); fs.symlinkSync(f.workspace, link);
  assert.equal(f.run(['--workspace', link]).status, 1); assert.equal(f.attempts(), 0);
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
    ['--fetch-timeout-seconds', '0'], ['--fetch-timeout-seconds', '13'], ['--fetch-timeout-seconds', 'nan'],
    ['--elapsed-seconds', 'inf'], ['--max-attempts', '3']]) {
    assert.equal(f.run(args).status, 1, args.join(' '));
  }
  assert.equal(f.attempts(), 0); assert.deepEqual(fs.readdirSync(f.workspace), []); f.clean();
});

test('trusted finite budgets above the measured default are configurable without waiting for their deadline', t => {
  const f = fixture(t), result = f.run(['--total-timeout-seconds', '600', '--fetch-timeout-seconds', '500']);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.equal(f.events(result).at(-1).event, 'checkout-complete');
  assert.ok(f.events(result).at(-1).remaining_seconds > 580);
  f.clean(); noSecrets(result);
});

test('bootstrap elapsed time reduces the single total budget, including cleanup and retry admission', t => {
  const f = fixture(t, 'hang-always');
  const start = Date.now();
  const result = f.run(['--total-timeout-seconds', '10', '--elapsed-seconds', '4', '--fetch-timeout-seconds', '5']);
  assert.equal(result.status, 1); assert.equal(f.attempts(), 1);
  assert.ok(Date.now() - start < 6500, 'spent bootstrap time must not be granted again');
  noLiveDescendant(f.descendant); assert.deepEqual(fs.readdirSync(f.workspace), []); f.clean(); noSecrets(result);
});
