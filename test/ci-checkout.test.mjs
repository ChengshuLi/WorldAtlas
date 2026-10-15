import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawn, spawnSync} from 'node:child_process';
import {inspectPackageInputs, inspectPackageExecutionInputs, materializePackageInputs} from '../scripts/package-build.mjs';

const helper = fileURLToPath(new URL('../scripts/acquire-ci-checkout.py', import.meta.url));
const realGit = spawnSync('which', ['git'], {encoding: 'utf8'}).stdout.trim();
const token = 'fixture-secret-only-checkout-1787';
const base64Token = Buffer.from('x-access-token:' + token).toString('base64');
const fixtureEnv = {...process.env, GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: os.devNull,
  PYTHONDONTWRITEBYTECODE: '1', INTEGRATION_PROFILE: '', INTEGRATION_TEST_SELECTION: ''};
const expectationsPath = 'coordination/engineering/current/selected-delivery-expectations.json';
const packageDefinition = {version: 1, inputs: ['.github/package-inputs.json', 'file.txt',
  'research/geography/required/body.txt', 'coordination/engineering/required/body.txt',
  'data/geography/required/body.txt'], optional_inputs: [], verification_paths: [], generated_outputs: []};
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
    '.github/package-inputs.json': JSON.stringify(packageDefinition) + '\n',
    [expectationsPath]: '{"trusted":"exact expectations"}\n',
    'coordination/engineering/unconsumed/payload.bin': 'unrelated archived payload bytes\n',
    'data/regional-review/source-only/body.txt': 'unconsumed regional source-only bytes\n',
    'research/campaigns/source-only/body.txt': 'unconsumed historical campaign bytes\n',
    'research/geography/required/body.txt': 'required original scientific source bytes\n',
    'research/geography/unconsumed/body.txt': 'unconsumed research body with distinct bytes\n',
    'coordination/engineering/required/body.txt': 'required archived engineering bytes\n',
    'data/geography/required/body.txt': 'required application bytes\n',
    'data/unconsumed/body.txt': 'unrelated undeclared data bytes\n',
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
    WORLDATLAS_CHECKOUT_TOKEN: token, GH_TOKEN: 'unrelated-secret', SELECTED_EXPECTATIONS_PATH: expectationsPath,
    GIT_CONFIG_GLOBAL: config, GIT_CONFIG_COUNT: '1', GIT_CONFIG_KEY_0: 'filter.malicious.smudge', GIT_CONFIG_VALUE_0: `touch ${sentinel}`};
  const args = (extra = []) => [helper, '--repository', 'ChengshuLi/WorldAtlas', '--sha', sha, '--tree', tree,
    '--workspace', workspace, ...extra];
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

for (const selection of ['complete', 'selected-data']) test(`${selection} software profile preserves exact tree and required inputs while omitting its unconsumed namespaces`, async t => {
  const f = fixture(t);
  Object.assign(f.env, {INTEGRATION_PROFILE: 'full', INTEGRATION_TEST_SELECTION: selection});
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
  assert.ok(f.rows().filter(row => row.auth).every(row => row.fetch || row.checkout ||
    selection === 'selected-data' && row.args.includes('cat-file') && row.args.includes('blob')));
  assert.ok(f.rows().every(row => !row.token && !row.gh && row.global === os.devNull));
  assert.ok(!fs.existsSync(f.sentinel));
  assert.doesNotMatch(fs.readFileSync(path.join(f.workspace, '.git/config'), 'utf8'), /extraheader|credential|AUTHORIZATION|fixture-secret|insteadOf/);
  assert.equal(f.events(result).at(-1).source_only_omitted, true);
  for (const name of ['research/geography/unconsumed/body.txt', 'coordination/engineering/unconsumed/payload.bin',
    'data/unconsumed/body.txt'])
    assert.equal(fs.existsSync(path.join(f.workspace, name)), selection === 'complete', name);
  assert.deepEqual(fs.readFileSync(path.join(f.workspace, expectationsPath)), fs.readFileSync(path.join(f.source, expectationsPath)));
  assert.deepEqual(inspectPackageInputs(f.workspace, packageDefinition).errors, []);
  const destination = path.join(f.directory, 'package-stage');
  const materialized = await materializePackageInputs({source: f.workspace, destination, definition: packageDefinition});
  assert.deepEqual(materialized.map(row => row.path).sort(), [...packageDefinition.inputs].sort());
  for (const name of packageDefinition.inputs) assert.deepEqual(fs.readFileSync(path.join(destination, name)), fs.readFileSync(path.join(f.source, name)), name);
  f.clean(); noSecrets(result);
});

for (const namespace of ['research/geography', 'data']) test(`cold selected-data checkout retains declared ${namespace} leaves, directories and verification paths without sibling blobs`, async t => {
  const f = fixture(t), directory = `${namespace}/declared-directory/`;
  const verification = `${namespace}/verified/record.txt`;
  const required = namespace === 'data' ? 'data/geography/required/body.txt' : `${namespace}/required/body.txt`;
  const outside = namespace === 'data' ? 'data-other/body.txt' : `${namespace}-other/body.txt`;
  const definition = {...packageDefinition, description: 'retained metadata '.repeat(700),
    inputs: [...packageDefinition.inputs, directory], verification_paths: [verification]};
  const bodies = {
    '.github/package-inputs.json': JSON.stringify(definition) + '\n',
    [directory + 'nested/body.txt']: 'required directory descendant\n',
    [verification]: 'verification role original bytes\n',
    [required + '-sibling']: 'excluded exact-file prefix sibling\n',
    [`${namespace}/declared-directory-sibling/body.txt`]: 'excluded directory prefix sibling\n',
    [`${namespace}/verified/unlisted.txt`]: 'excluded verification sibling\n',
    [outside]: 'outside research namespace remains\n'
  };
  for (const [name, raw] of Object.entries(bodies)) {
    fs.mkdirSync(path.dirname(path.join(f.source, name)), {recursive: true}); fs.writeFileSync(path.join(f.source, name), raw);
  }
  f.git(['add', '.']); f.git(['commit', '--quiet', '-m', 'declared research retention']);
  const sha = f.git(['rev-parse', 'HEAD']), tree = f.git(['rev-parse', 'HEAD^{tree}']);
  Object.assign(f.env, {INTEGRATION_PROFILE: 'full', INTEGRATION_TEST_SELECTION: 'selected-data'});
  const result = f.run(['--sha', sha, '--tree', tree]);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.equal(command(realGit, ['-C', f.workspace, 'rev-parse', 'HEAD^{tree}']), tree);
  for (const name of [required, directory + 'nested/body.txt', verification,
    outside, 'test/current.test.mjs'])
    assert.deepEqual(fs.readFileSync(path.join(f.workspace, name)), fs.readFileSync(path.join(f.source, name)), name);
  for (const name of [`${namespace}/unconsumed/body.txt`, required + '-sibling',
    `${namespace}/declared-directory-sibling/body.txt`, `${namespace}/verified/unlisted.txt`]) {
    assert.ok(!fs.existsSync(path.join(f.workspace, name)), name);
    const oid = f.git(['rev-parse', `${sha}:${name}`]);
    assert.notEqual(spawnSync(realGit, ['-C', f.workspace, 'cat-file', '-e', oid],
      {encoding: 'utf8', env: {...fixtureEnv, GIT_NO_LAZY_FETCH: '1'}, timeout: 2000}).status, 0, 'cold omitted blob: ' + name);
  }
  assert.notEqual(spawnSync(realGit, ['-C', f.workspace, 'cat-file', '-e', f.sha + '^{commit}'],
    {encoding: 'utf8', env: {...fixtureEnv, GIT_NO_LAZY_FETCH: '1'}, timeout: 2000}).status, 0, 'no historical fixture objects');
  assert.deepEqual(inspectPackageInputs(f.workspace, definition).errors, []);
  const destination = path.join(f.directory, 'package-stage');
  const materialized = await materializePackageInputs({source: f.workspace, destination, definition});
  assert.ok(materialized.some(row => row.path === directory + 'nested/body.txt'));
  assert.ok(!fs.existsSync(path.join(destination, `${namespace}/unconsumed/body.txt`)));
  assert.equal(command(realGit, ['-C', f.workspace, 'config', '--get', 'remote.origin.promisor']), 'false');
  f.clean(); noSecrets(result);
});

test('cold selected-data checkout retains coordination execution files, exact roles and only trusted expectations', async t => {
  const f = fixture(t), prefix = 'coordination/engineering/';
  const directory = prefix + 'declared-directory/', verification = prefix + 'verified/record.json';
  const definition = {...packageDefinition, inputs: [...packageDefinition.inputs, directory], verification_paths: [verification]};
  const suffixes = ['mjs','js','cjs','py','sh','ts','tsx','jsx','html','css','sql','yml','yaml','c','h','cpp','hpp','wasm','bat','cmd','ps1'];
  const bodies = {
    '.github/package-inputs.json': JSON.stringify(definition),
    [directory + 'nested/original.bin']: 'complete declared directory descendant',
    [verification]: 'verification outside package inputs',
    [prefix + 'required/body.txt-sibling']: 'omitted exact-file sibling',
    [prefix + 'declared-directory-sibling/payload.bin']: 'omitted directory sibling',
    [prefix + 'verified/unlisted.json']: 'omitted verification sibling',
    [prefix + 'archive/package.json']: '{"type":"module"}',
    [prefix + 'archive/command']: '#!/bin/sh\nexit 0\n',
    [prefix + 'archive/selected-delivery-expectations.json']: 'untrusted alternate expectations',
    [prefix + 'archive/large.zip']: 'unrelated cold archive'.repeat(20000),
    ...Object.fromEntries(suffixes.map(suffix => [prefix + 'archive/helper.' + suffix, 'retained execution source: ' + suffix]))
  };
  for (const [name, raw] of Object.entries(bodies)) {
    fs.mkdirSync(path.dirname(path.join(f.source, name)), {recursive: true}); fs.writeFileSync(path.join(f.source, name), raw);
  }
  fs.chmodSync(path.join(f.source, prefix + 'archive/command'), 0o755);
  f.git(['add', '.']); f.git(['commit', '--quiet', '-m', 'coordination execution and role retention']);
  const sha = f.git(['rev-parse', 'HEAD']), tree = f.git(['rev-parse', 'HEAD^{tree}']);
  Object.assign(f.env, {INTEGRATION_PROFILE: 'full', INTEGRATION_TEST_SELECTION: 'selected-data'});
  const result = f.run(['--sha', sha, '--tree', tree]);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.equal(command(realGit, ['-C', f.workspace, 'rev-parse', 'HEAD']), sha);
  assert.equal(command(realGit, ['-C', f.workspace, 'rev-parse', 'HEAD^{tree}']), tree);
  for (const name of [directory + 'nested/original.bin', verification, expectationsPath,
    prefix + 'archive/package.json', prefix + 'archive/command', ...suffixes.map(suffix => prefix + 'archive/helper.' + suffix)])
    assert.deepEqual(fs.readFileSync(path.join(f.workspace, name)), fs.readFileSync(path.join(f.source, name)), name);
  assert.equal(fs.statSync(path.join(f.workspace, prefix + 'archive/command')).mode & 0o111, 0o111);
  for (const name of [prefix + 'required/body.txt-sibling', prefix + 'declared-directory-sibling/payload.bin',
    prefix + 'verified/unlisted.json', prefix + 'archive/selected-delivery-expectations.json', prefix + 'archive/large.zip']) {
    assert.ok(!fs.existsSync(path.join(f.workspace, name)), name);
    const oid = f.git(['rev-parse', `${sha}:${name}`]);
    assert.notEqual(spawnSync(realGit, ['-C', f.workspace, 'cat-file', '-e', oid],
      {env: {...fixtureEnv, GIT_NO_LAZY_FETCH: '1'}, timeout: 2000}).status, 0, 'omitted cold blob: ' + name);
  }
  assert.deepEqual(inspectPackageInputs(f.workspace, definition).errors, []);
  const destination = path.join(f.directory, 'full-package-fallback');
  await materializePackageInputs({source: f.workspace, destination, definition});
  assert.deepEqual(fs.readFileSync(path.join(destination, directory + 'nested/original.bin')),
    fs.readFileSync(path.join(f.source, directory + 'nested/original.bin')));
  assert.ok(!fs.existsSync(path.join(destination, expectationsPath)), 'Smoke expectations need no package role');
  f.clean(); noSecrets(result);
});

for (const role of ['inputs', 'verification_paths']) test(`selected-data ancestor coordination directory in ${role} retains complete history`, t => {
  const f = fixture(t), definition = {...packageDefinition,
    [role]: [...packageDefinition[role], 'coordination/']};
  fs.writeFileSync(path.join(f.source, '.github/package-inputs.json'), JSON.stringify(definition));
  f.git(['add', '.']); f.git(['commit', '--quiet', '-m', 'ancestor coordination declaration']);
  Object.assign(f.env, {INTEGRATION_PROFILE: 'full', INTEGRATION_TEST_SELECTION: 'selected-data'});
  const result = f.run(['--sha', f.git(['rev-parse', 'HEAD']), '--tree', f.git(['rev-parse', 'HEAD^{tree}'])]);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.deepEqual(fs.readFileSync(path.join(f.workspace, 'coordination/engineering/unconsumed/payload.bin')),
    fs.readFileSync(path.join(f.source, 'coordination/engineering/unconsumed/payload.bin')));
  assert.deepEqual(inspectPackageInputs(f.workspace, definition).errors, []);
  f.clean(); noSecrets(result);
});

for (const unsafe of ['', '../selected-delivery-expectations.json', '/absolute/selected-delivery-expectations.json',
  'coordination/engineering/../selected-delivery-expectations.json', 'coordination//selected-delivery-expectations.json',
  'coordination/*/selected-delivery-expectations.json', 'coordination/current/other.json', expectationsPath + '/']) {
  test(`selected-data unsafe trusted expectations ${JSON.stringify(unsafe)} fail closed`, t => {
    const f = fixture(t);
    Object.assign(f.env, {INTEGRATION_PROFILE: 'full', INTEGRATION_TEST_SELECTION: 'selected-data', SELECTED_EXPECTATIONS_PATH: unsafe});
    const result = f.run();
    assert.equal(result.status, 1, result.stdout + result.stderr); assert.match(result.stdout, /invalid-selected-expectations/);
    assert.ok(!f.rows().some(row => row.checkout)); assert.deepEqual(fs.readdirSync(f.workspace), []);
    f.clean(); noSecrets(result);
  });
}
for (const mode of ['missing', 'symlink', 'directory', 'executable']) test(`selected-data ${mode} trusted expectations fail closed`, t => {
  const f = fixture(t), file = path.join(f.source, expectationsPath);
  fs.unlinkSync(file);
  if (mode === 'symlink') fs.symlinkSync('../../../file.txt', file);
  if (mode === 'directory') { fs.mkdirSync(file); fs.writeFileSync(path.join(file, 'body'), 'foreign directory'); }
  if (mode === 'executable') fs.writeFileSync(file, '{}', {mode: 0o755});
  f.git(['add', '.']); f.git(['commit', '--quiet', '-m', 'nonordinary expectations']);
  Object.assign(f.env, {INTEGRATION_PROFILE: 'full', INTEGRATION_TEST_SELECTION: 'selected-data'});
  const result = f.run(['--sha', f.git(['rev-parse', 'HEAD']), '--tree', f.git(['rev-parse', 'HEAD^{tree}'])]);
  assert.equal(result.status, 1, result.stdout + result.stderr); assert.match(result.stdout, /invalid-selected-expectations/);
  assert.ok(!f.rows().some(row => row.checkout)); assert.deepEqual(fs.readdirSync(f.workspace), []);
  f.clean(); noSecrets(result);
});

test('selected-data retains an exact trusted expectations file in the filtered research namespace', t => {
  const f = fixture(t), name = 'research/geography/current/selected-delivery-expectations.json';
  fs.mkdirSync(path.dirname(path.join(f.source, name)), {recursive: true}); fs.writeFileSync(path.join(f.source, name), 'exact trusted research expectations');
  f.git(['add', '.']); f.git(['commit', '--quiet', '-m', 'trusted research expectations']);
  Object.assign(f.env, {INTEGRATION_PROFILE: 'full', INTEGRATION_TEST_SELECTION: 'selected-data', SELECTED_EXPECTATIONS_PATH: name});
  const result = f.run(['--sha', f.git(['rev-parse', 'HEAD']), '--tree', f.git(['rev-parse', 'HEAD^{tree}'])]);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.equal(fs.readFileSync(path.join(f.workspace, name), 'utf8'), 'exact trusted research expectations');
  assert.ok(!fs.existsSync(path.join(f.workspace, expectationsPath)), 'No implicit other expectations retention');
  f.clean(); noSecrets(result);
});

test('selected-data refuses a nonordinary coordination execution source instead of silently omitting it', t => {
  const f = fixture(t), name = 'coordination/engineering/archive/helper.mjs';
  fs.mkdirSync(path.dirname(path.join(f.source, name)), {recursive: true}); fs.symlinkSync('../../../file.txt', path.join(f.source, name));
  f.git(['add', '.']); f.git(['commit', '--quiet', '-m', 'nonordinary coordination source']);
  Object.assign(f.env, {INTEGRATION_PROFILE: 'full', INTEGRATION_TEST_SELECTION: 'selected-data'});
  const result = f.run(['--sha', f.git(['rev-parse', 'HEAD']), '--tree', f.git(['rev-parse', 'HEAD^{tree}'])]);
  assert.equal(result.status, 1, result.stdout + result.stderr); assert.match(result.stdout, /nonordinary-coordination-execution-input/);
  assert.ok(!f.rows().some(row => row.checkout)); assert.deepEqual(fs.readdirSync(f.workspace), []);
  f.clean(); noSecrets(result);
});

test('trusted workflow passes the exact prepare expectations output to checkout', () => {
  const workflow = fs.readFileSync(new URL('../.github/workflows/worker-merge.yml', import.meta.url), 'utf8');
  const step = workflow.slice(workflow.indexOf('      - name: Acquire full checkout'), workflow.indexOf('      - name: Legacy full checkout'));
  assert.match(step, /SELECTED_EXPECTATIONS_PATH: \$\{\{ needs\.prepare\.outputs\.expectations_path \}\}/);
});

test('selected-data declaration of the entire research namespace retains all its original bodies', t => {
  const f = fixture(t), definition = {...packageDefinition,
    inputs: [...packageDefinition.inputs.filter(name => !name.startsWith('research/geography/')), 'research/geography/']};
  fs.writeFileSync(path.join(f.source, '.github/package-inputs.json'), JSON.stringify(definition) + '\n');
  f.git(['add', '.']); f.git(['commit', '--quiet', '-m', 'whole declared research directory']);
  Object.assign(f.env, {INTEGRATION_PROFILE: 'full', INTEGRATION_TEST_SELECTION: 'selected-data'});
  const result = f.run(['--sha', f.git(['rev-parse', 'HEAD']), '--tree', f.git(['rev-parse', 'HEAD^{tree}'])]);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.deepEqual(fs.readFileSync(path.join(f.workspace, 'research/geography/unconsumed/body.txt')),
    fs.readFileSync(path.join(f.source, 'research/geography/unconsumed/body.txt')));
  assert.deepEqual(inspectPackageInputs(f.workspace, definition).errors, []);
  f.clean(); noSecrets(result);
});

for (const role of ['inputs', 'verification_paths']) test(`cold selected-data ancestor research directory in ${role} retains required descendants`, async t => {
  const f = fixture(t), definition = {...packageDefinition,
    inputs: role === 'inputs' ? [...packageDefinition.inputs.filter(name => !name.startsWith('research/')), 'research/']
      : [...packageDefinition.inputs],
    verification_paths: role === 'verification_paths' ? ['research/'] : []};
  // Existing campaigns omission remains a separate fail-closed source-only
  // policy; this fixture isolates the new geography boundary's ancestor case.
  fs.rmSync(path.join(f.source, 'research/campaigns'), {recursive: true});
  fs.writeFileSync(path.join(f.source, '.github/package-inputs.json'), JSON.stringify(definition) + '\n');
  f.git(['add', '.']); f.git(['commit', '--quiet', '-m', 'ancestor declared research role']);
  const sha = f.git(['rev-parse', 'HEAD']), tree = f.git(['rev-parse', 'HEAD^{tree}']);
  Object.assign(f.env, {INTEGRATION_PROFILE: 'full', INTEGRATION_TEST_SELECTION: 'selected-data'});
  const result = f.run(['--sha', sha, '--tree', tree]);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.equal(command(realGit, ['-C', f.workspace, 'rev-parse', 'HEAD^{tree}']), tree);
  for (const name of ['research/geography/required/body.txt', 'research/geography/unconsumed/body.txt']) {
    assert.deepEqual(fs.readFileSync(path.join(f.workspace, name)), fs.readFileSync(path.join(f.source, name)), name);
    const oid = f.git(['rev-parse', `${sha}:${name}`]);
    assert.equal(command(realGit, ['-C', f.workspace, 'cat-file', '-t', oid]), 'blob');
  }
  assert.notEqual(spawnSync(realGit, ['-C', f.workspace, 'cat-file', '-e', f.sha + '^{commit}'],
    {encoding: 'utf8', env: {...fixtureEnv, GIT_NO_LAZY_FETCH: '1'}, timeout: 2000}).status, 0);
  assert.deepEqual(inspectPackageInputs(f.workspace, definition).errors, []);
  const destination = path.join(f.directory, 'package-stage');
  await materializePackageInputs({source: f.workspace, destination, definition});
  assert.deepEqual(fs.readFileSync(path.join(destination, 'research/geography/required/body.txt')),
    fs.readFileSync(path.join(f.source, 'research/geography/required/body.txt')));
  assert.equal(fs.existsSync(path.join(destination, 'research/geography/unconsumed/body.txt')), role === 'inputs');
  f.clean(); noSecrets(result);
});

for (const role of ['inputs', 'verification_paths']) test(`cold selected-data data ancestor in ${role} retains every original descendant`, t => {
  const f = fixture(t);
  // A whole-data grant includes regional evidence as well as current assets.
  const definition = {...packageDefinition,
    inputs: role === 'inputs' ? [...packageDefinition.inputs.filter(name => !name.startsWith('data/')), 'data/']
      : [...packageDefinition.inputs], verification_paths: role === 'verification_paths' ? ['data/'] : []};
  fs.writeFileSync(path.join(f.source, '.github/package-inputs.json'), JSON.stringify(definition) + '\n');
  f.git(['add', '.']); f.git(['commit', '--quiet', '-m', 'whole declared data namespace']);
  Object.assign(f.env, {INTEGRATION_PROFILE: 'full', INTEGRATION_TEST_SELECTION: 'selected-data'});
  const result = f.run(['--sha', f.git(['rev-parse', 'HEAD']), '--tree', f.git(['rev-parse', 'HEAD^{tree}'])]);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  for (const name of ['data/geography/required/body.txt', 'data/unconsumed/body.txt', 'data/regional-review/source-only/body.txt'])
    assert.deepEqual(fs.readFileSync(path.join(f.workspace, name)), fs.readFileSync(path.join(f.source, name)), name);
  assert.deepEqual(inspectPackageInputs(f.workspace, definition).errors, []);
  f.clean(); noSecrets(result);
});

for (const unsafe of ['../escape', '/absolute', 'research/geography/../escape',
  'research/geography//escape', 'research/geography/escape//', 'research/geography/*', 'research/geography/x\n/*']) {
  test(`selected-data unsafe package retention path ${JSON.stringify(unsafe)} refuses before checkout`, t => {
    const f = fixture(t), definition = {...packageDefinition, inputs: [...packageDefinition.inputs, unsafe]};
    fs.writeFileSync(path.join(f.source, '.github/package-inputs.json'), JSON.stringify(definition) + '\n');
    f.git(['add', '.']); f.git(['commit', '--quiet', '-m', 'invalid declared path']);
    Object.assign(f.env, {INTEGRATION_PROFILE: 'full', INTEGRATION_TEST_SELECTION: 'selected-data'});
    const result = f.run(['--sha', f.git(['rev-parse', 'HEAD']), '--tree', f.git(['rev-parse', 'HEAD^{tree}'])]);
    assert.equal(result.status, 1, result.stdout + result.stderr);
    assert.match(result.stdout, /invalid-package-inputs/);
    assert.ok(!f.rows().some(row => row.checkout));
    assert.deepEqual(fs.readdirSync(f.workspace), []); f.clean(); noSecrets(result);
  });
}

for (const namespace of ['research/geography', 'coordination/engineering', 'data']) test(`selected-data missing declared ${namespace} input still fails real package admission and fallback materialization`, async t => {
  const f = fixture(t), required = namespace === 'data' ? 'data/geography/required/body.txt' : namespace + '/required/body.txt';
  fs.unlinkSync(path.join(f.source, required));
  f.git(['add', '.']); f.git(['commit', '--quiet', '-m', 'missing declared research input']);
  Object.assign(f.env, {INTEGRATION_PROFILE: 'full', INTEGRATION_TEST_SELECTION: 'selected-data'});
  const result = f.run(['--sha', f.git(['rev-parse', 'HEAD']), '--tree', f.git(['rev-parse', 'HEAD^{tree}'])]);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.ok(inspectPackageInputs(f.workspace, packageDefinition).errors.some(row => row.path === required));
  await assert.rejects(materializePackageInputs({source: f.workspace, destination: path.join(f.directory, 'package-stage'), definition: packageDefinition}),
    error => error.code === 'ENOENT' || /Declared package input missing/.test(error.message));
  f.clean(); noSecrets(result);
});

test('selected-data symlink package declaration refuses before checkout', t => {
  const f = fixture(t), file = path.join(f.source, '.github/package-inputs.json');
  fs.unlinkSync(file); fs.symlinkSync('../file.txt', file);
  f.git(['add', '.']); f.git(['commit', '--quiet', '-m', 'nonordinary package declaration']);
  Object.assign(f.env, {INTEGRATION_PROFILE: 'full', INTEGRATION_TEST_SELECTION: 'selected-data'});
  const result = f.run(['--sha', f.git(['rev-parse', 'HEAD']), '--tree', f.git(['rev-parse', 'HEAD^{tree}'])]);
  assert.equal(result.status, 1, result.stdout + result.stderr);
  assert.match(result.stdout, /invalid-package-inputs/);
  assert.ok(!f.rows().some(row => row.checkout));
  assert.deepEqual(fs.readdirSync(f.workspace), []); f.clean(); noSecrets(result);
});

test('selected-data explicit regional evidence declaration retains exact current input without undeclared siblings', async t => {
  const f = fixture(t), name = 'data/regional-review/source-only/body.txt';
  const sibling = 'data/regional-review/source-only/undeclared.txt';
  const definition = {...packageDefinition, inputs: [...packageDefinition.inputs, name]};
  fs.writeFileSync(path.join(f.source, sibling), 'undeclared cold regional evidence');
  fs.writeFileSync(path.join(f.source, '.github/package-inputs.json'), JSON.stringify(definition) + '\n');
  f.git(['add', '.']); f.git(['commit', '--quiet', '-m', 'require exact current regional evidence']);
  const sha = f.git(['rev-parse', 'HEAD']), tree = f.git(['rev-parse', 'HEAD^{tree}']);
  Object.assign(f.env, {INTEGRATION_PROFILE: 'full', INTEGRATION_TEST_SELECTION: 'selected-data'});
  const result = f.run(['--sha', sha, '--tree', tree]);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.deepEqual(fs.readFileSync(path.join(f.workspace, name)), fs.readFileSync(path.join(f.source, name)));
  assert.deepEqual(inspectPackageInputs(f.workspace, definition).errors, []);
  const destination = path.join(f.directory, 'package-stage');
  await materializePackageInputs({source: f.workspace, destination, definition});
  assert.deepEqual(fs.readFileSync(path.join(destination, name)), fs.readFileSync(path.join(f.source, name)));
  assert.ok(!fs.existsSync(path.join(f.workspace, sibling)));
  assert.ok(!fs.existsSync(path.join(destination, sibling)));
  assert.notEqual(spawnSync(realGit, ['-C', f.workspace, 'cat-file', '-e', f.git(['rev-parse', `${sha}:${sibling}`])],
    {env: {...fixtureEnv, GIT_NO_LAZY_FETCH: '1'}, timeout: 2000}).status, 0);
  f.clean(); noSecrets(result);
});

for (const name of ['research/campaigns/source-only/body.txt']) {
  test(`selected-data future required input ${name} fails existing package admission and fallback materialization`, async t => {
    const f = fixture(t), definition = {...packageDefinition, inputs: [...packageDefinition.inputs, name]};
    fs.writeFileSync(path.join(f.source, '.github/package-inputs.json'), JSON.stringify(definition) + '\n');
    f.git(['add', '.']); f.git(['commit', '--quiet', '-m', 'require source-only input']);
    const sha = f.git(['rev-parse', 'HEAD']), tree = f.git(['rev-parse', 'HEAD^{tree}']);
    Object.assign(f.env, {INTEGRATION_PROFILE: 'full', INTEGRATION_TEST_SELECTION: 'selected-data'});
    const result = f.run(['--sha', sha, '--tree', tree]);
    assert.equal(result.status, 0, result.stdout + result.stderr);
    const inspection = inspectPackageInputs(f.workspace, definition);
    assert.ok(inspection.errors.some(row => row.kind === 'materialized-input' && row.path === name));
    assert.ok(inspection.missing_objects.includes(f.git(['rev-parse', `${sha}:${name}`])));
    const destination = path.join(f.directory, 'package-stage');
    await assert.rejects(materializePackageInputs({source: f.workspace, destination, definition}),
      error => error.code === 'ENOENT' || /Declared package input missing/.test(error.message));
    assert.ok(!fs.existsSync(path.join(destination, name)));
    assert.ok(!fs.existsSync(path.join(f.workspace, name)));
    f.clean(); noSecrets(result);
  });
}

test('selected-data future execution import from an omitted namespace fails the actual closure reader', t => {
  const f = fixture(t), required = 'research/campaigns/source-only/required.mjs';
  const bodies = {
    'package.json': '{"type":"module"}\n',
    'data/native-context-migration/manifest.json': JSON.stringify({version: 2, kind: 'retained-identity-context-continuation-v2', issue: 1295}),
    'scripts/native-ownership/validate-build-context-stage.mjs': 'export {};\n',
    'coordination/engineering/eastern-two-gap-repair-native-20261007/current-execution.mjs': 'export {};\n',
    'scripts/package-build.mjs': 'export {};\n',
    'scripts/build-cloudflare-inner.mjs': `import '../${required}';\n`,
    [required]: 'export const required = true;\n'
  };
  const definition = {...packageDefinition, inputs: [...packageDefinition.inputs, ...Object.keys(bodies)]};
  for (const [name, raw] of Object.entries({...bodies, '.github/package-inputs.json': JSON.stringify(definition)})) {
    fs.mkdirSync(path.dirname(path.join(f.source, name)), {recursive: true}); fs.writeFileSync(path.join(f.source, name), raw);
  }
  f.git(['add', '.']); f.git(['commit', '--quiet', '-m', 'require source-only executing input']);
  assert.deepEqual(inspectPackageExecutionInputs(f.source, definition).errors, []);
  Object.assign(f.env, {INTEGRATION_PROFILE: 'full', INTEGRATION_TEST_SELECTION: 'selected-data'});
  const result = f.run(['--sha', f.git(['rev-parse', 'HEAD']), '--tree', f.git(['rev-parse', 'HEAD^{tree}'])]);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  const inspection = inspectPackageExecutionInputs(f.workspace, definition);
  assert.ok(inspection.errors.some(row => row.kind === 'execution-inputs' && row.detail.includes(required)));
  f.clean(); noSecrets(result);
});

for (const selection of ['complete', 'selected-data']) test(`${selection} sparse acquisition preserves explicit complete historical commit fetch without later lazy hydration`, t => {
  const f = fixture(t), original = f.sha;
  fs.writeFileSync(path.join(f.source, 'file.txt'), 'new current software bytes\n');
  fs.writeFileSync(path.join(f.source, 'data/geography/required/body.txt'), 'new current application bytes\n');
  f.git(['add', '.']); f.git(['commit', '--quiet', '-m', 'current']);
  const current = f.git(['rev-parse', 'HEAD']), tree = f.git(['rev-parse', 'HEAD^{tree}']);
  Object.assign(f.env, {INTEGRATION_PROFILE: 'full', INTEGRATION_TEST_SELECTION: selection});
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

for (const [profile, selection] of [['full', 'selected-output'], ['full', 'unknown'], ['full', ''],
  ['evidence', 'complete'], ['evidence', 'selected-data'], ['', 'selected-data']]) {
  test(`other route ${profile}/${selection} retains complete checkout`, t => {
    const f = fixture(t); Object.assign(f.env, {INTEGRATION_PROFILE: profile, INTEGRATION_TEST_SELECTION: selection});
    const result = f.run(); assert.equal(result.status, 0, result.stdout + result.stderr);
    assert.ok(fs.existsSync(path.join(f.workspace, 'data/regional-review/source-only/body.txt')));
    assert.ok(fs.existsSync(path.join(f.workspace, 'research/campaigns/source-only/body.txt')));
    assert.ok(!f.rows().some(row => row.args.includes('--filter=blob:none')));
    assert.ok(f.rows().filter(row => !row.fetch).every(row => !row.auth));
    assert.equal(f.events(result).at(-1).source_only_omitted, false);
    f.clean(); noSecrets(result);
  });
}

test('progressing fetch completes once without an acquisition deadline', t => {
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

for(const selection of ['complete','selected-data']) for(const mode of ['hang','materialize-hang']) test(`SIGTERM cancels ${selection} ${mode} process group, cleans it and performs no second fetch`, async t => {
  const f = fixture(t, mode);
  Object.assign(f.env,{INTEGRATION_PROFILE:'full',INTEGRATION_TEST_SELECTION:selection});
  const child = spawn('python3', f.args(), {env: f.env});
  let stdout = '', stderr = '';
  child.stdout.on('data', value => { stdout += value; }); child.stderr.on('data', value => { stderr += value; });
  const completed = new Promise(resolve => child.once('close', (status, signal) => resolve({status, signal, stdout, stderr})));
  const start = Date.now();
  let observed, signaled, result;
  try {
    while (!fs.existsSync(f.descendant) && Date.now() - start < 10000) await new Promise(resolve => setTimeout(resolve, 20));
    observed = fs.existsSync(f.descendant);
  } finally {
    signaled = Date.now();
    child.kill('SIGTERM');
    result = await completed;
  }
  assert.ok(observed, 'fixture descendant started within the bounded startup wait');
  assert.equal(result.status, 130, result.stdout + result.stderr); assert.equal(f.fetches(), 1);
  assert.ok(Date.now()-signaled<5000,'cancellation and cleanup remain bounded from SIGTERM');
  noLiveDescendant(f.descendant); assert.deepEqual(fs.readdirSync(f.workspace), []); f.clean(); noSecrets(result);
});

test('unverifiable process cleanup preserves private staging, performs no second fetch and preserves the workspace', t => {
  const f = fixture(t, 'hang');
  const driver = path.join(f.directory, 'unavailable-inspection.py');
  fs.writeFileSync(driver, `import importlib.util,os,sys,signal,threading,time
spec=importlib.util.spec_from_file_location('acquisition',${JSON.stringify(helper)})
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
ordinary=module.live_group
def unavailable(pgid):
 if os.path.exists(${JSON.stringify(f.descendant)}):raise OSError('fixture process inspection unavailable')
 return ordinary(pgid)
module.live_group=unavailable
def cancel():
 while not os.path.exists(${JSON.stringify(f.descendant)}) : time.sleep(0.02)
 os.kill(os.getpid(),signal.SIGTERM)
threading.Thread(target=cancel,daemon=True).start()
sys.exit(module.main())
`);
  const result = spawnSync('python3', [driver, ...f.args().slice(1)],
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

for (const option of ['--fetch-timeout-seconds', '--max-attempts', '--total-timeout-seconds', '--elapsed-seconds']) test('removed '+option+' refuses before mutation', t => {
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
