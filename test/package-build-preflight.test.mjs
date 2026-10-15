import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {inspectPackageInputs, inspectPackageAncestry, inspectPackageRuntime, inspectPackageBrowser, inspectPackageExecutionInputs, preflightPackageBuild, requirePackagePreflight} from '../scripts/package-build-preflight.mjs';
import {loadPackageInputs, containsPackagePath} from '../scripts/package-inputs.mjs';
import {runPackageBuild} from '../scripts/package-build.mjs';

function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'atlas-package-preflight-'));
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  const write = (name, value) => { fs.mkdirSync(path.dirname(path.join(root, name)), {recursive: true}); fs.writeFileSync(path.join(root, name), typeof value === 'string' ? value : JSON.stringify(value)); };
  const git = (...args) => execFileSync('git', ['-C', root, ...args], {encoding: 'utf8', env: {...process.env, GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: '/dev/null', GIT_NO_LAZY_FETCH: '1'}}).trim();
  const definition = {version: 1, inputs: ['.github/package-inputs.json', 'package.json', 'package-lock.json', 'requirements.txt', 'src/'], optional_inputs: [], verification_paths: [], generated_outputs: ['dist/']};
  const pin = {version: '1.2.3', resolved: 'https://registry.npmjs.org/example/-/example-1.2.3.tgz', integrity: 'sha512-fixture'};
  write('.github/package-inputs.json', definition); write('package.json', {engines: {node: '>=24'}});
  write('package-lock.json', {lockfileVersion: 3, packages: {'': {}, 'node_modules/example': pin}});
  write('node_modules/.package-lock.json', {lockfileVersion: 3, packages: {'node_modules/example': pin}});
  write('node_modules/example/package.json', {version: '1.2.3'});
  write('requirements.txt', 'numpy==2.3.5\nshapely==2.1.2\npyproj==3.7.2\n');
  write('src/first.txt', 'first'); write('src/second.txt', 'second');
  // This fixture declares and supplies its actual current executable roots.
  for(const name of ['scripts/build-cloudflare-inner.mjs','scripts/package-build.mjs','coordination/engineering/eastern-two-gap-repair-native-20261007/current-execution.mjs']){definition.inputs.push(name);write(name,'export const fixture=1;\n');}
  write('.github/package-inputs.json',definition);
  git('init', '-q'); git('add', '.'); git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture');
  // Synthetic runtime probe only; real installed imports are exercised by the
  // completed-output benchmark. No fixture report qualifies scientific work.
  const python = path.join(root, 'python-fixture');
  fs.writeFileSync(python, `#!${process.execPath}\nconsole.log(JSON.stringify({version:'fixture',executable:process.argv[1],imports:JSON.parse(process.argv.at(-1)).map(x=>({...x,actual:x.version}))}));\n`, {mode: 0o755});
  return {root, write, git, definition, python};
}

test('complete local object/materialization, ancestry and runtime preflight passes without downloads', async t => {
  const f = fixture(t);
  const report = await preflightPackageBuild({root: f.root, python: f.python, browser: 'off', requiredAncestors: [f.git('rev-parse', 'HEAD')]});
  assert.equal(report.passed, true, JSON.stringify(report.errors));
  assert.equal(report.runtime.npm_packages, 1); assert.equal(report.browser.status, 'not-requested');
  assert(report.inputs.committed_files >= 6); assert.equal(requirePackagePreflight(report), report);
});

test('one pass reports all missing blobs and materialized inputs rather than fetching or stopping at first', t => {
  const f = fixture(t);
  const oids = ['src/first.txt', 'src/second.txt'].map(name => f.git('rev-parse', `HEAD:${name}`));
  for (const [index, oid] of oids.entries()) {
    fs.unlinkSync(path.join(f.root, '.git/objects', oid.slice(0, 2), oid.slice(2)));
    fs.unlinkSync(path.join(f.root, index ? 'src/second.txt' : 'src/first.txt'));
  }
  const result = inspectPackageInputs(f.root, f.definition);
  assert.deepEqual(result.missing_objects.sort(), oids.sort());
  assert.equal(result.errors.filter(x => x.kind === 'git-object').length, 2);
  assert.equal(result.errors.filter(x => x.kind === 'materialized-input').length, 2);
  // Parent directory is present; committed paths must each be materialized too.
  assert.equal(fs.readdirSync(path.join(f.root, 'src')).length, 0);
});

test('missing declared paths, nonordinary input and unknown ancestry are reported together', async t => {
  const f = fixture(t);
  fs.unlinkSync(path.join(f.root, 'src/first.txt')); fs.symlinkSync('../package.json', path.join(f.root, 'src/first.txt'));
  fs.unlinkSync(path.join(f.root, 'requirements.txt'));
  const report = await preflightPackageBuild({root: f.root, python: f.python, browser: 'off', requiredAncestors: ['f'.repeat(40)]});
  assert.equal(report.passed, false);
  assert(report.errors.some(x => x.path === 'src/first.txt' && x.detail === 'symlink'));
  assert(report.errors.some(x => x.path === 'requirements.txt'));
  assert(report.errors.some(x => x.kind === 'source-ancestry'));
});

test('known accepted source must be an actual ancestor, not merely a present commit', t => {
  const f = fixture(t), first = f.git('rev-parse', 'HEAD');
  f.write('src/third.txt', 'third'); f.git('add', '.'); f.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'later');
  const later = f.git('rev-parse', 'HEAD'); f.git('checkout', '-q', first);
  assert.equal(inspectPackageAncestry(f.root, f.definition, [later]).errors[0].detail, 'Not an ancestor of HEAD');
});

test('lock mismatch and all Python import failures appear before a build', t => {
  const f = fixture(t);
  f.write('node_modules/example/package.json', {version: '9.9.9'});
  fs.writeFileSync(f.python, `#!${process.execPath}\nconsole.log(JSON.stringify({version:'fixture',imports:JSON.parse(process.argv.at(-1)).map(x=>({...x,error:'module missing'}))}));\n`, {mode: 0o755});
  const report = inspectPackageRuntime(f.root, {python: f.python});
  assert.equal(report.errors.filter(x => x.kind === 'python-import').length, 3);
  assert(report.errors.some(x => x.kind === 'npm-package'));
});

test('platform-compatible optional runtime missing from npm installation fails', t => {
  const f = fixture(t), lock = JSON.parse(fs.readFileSync(path.join(f.root, 'package-lock.json')));
  lock.packages['node_modules/native-required'] = {version: '1', optional: true, os: [process.platform], cpu: [process.arch]};
  f.write('package-lock.json', lock);
  assert(inspectPackageRuntime(f.root, {python: f.python}).errors.some(x => x.path === 'node_modules/native-required'));
});

test('unavailable browser remains an explicit limit, and required-browser mode fails', async t => {
  const f = fixture(t);
  const probe = await inspectPackageBrowser(f.root, 'probe'), required = await inspectPackageBrowser(f.root, 'required');
  assert.equal(probe.status, 'unavailable'); assert.equal(probe.errors.length, 0);
  assert.equal(required.status, 'unavailable'); assert.equal(required.errors.length, 1);
});

test('failed preflight never starts image copying/build or alters prior output', async t => {
  const f = fixture(t); f.write('dist/previous', 'preserved'); let launched = false;
  await assert.rejects(runPackageBuild('static', {root: f.root, preflight: async () => ({passed: false, errors: [{kind: 'missing-input'}]}), execute: () => { launched = true; }}), /before image creation/);
  assert.equal(launched, false); assert.equal(fs.existsSync(path.join(f.root, '.cache')), false);
  assert.equal(fs.readFileSync(path.join(f.root, 'dist/previous'), 'utf8'), 'preserved');
});

test('ordinary build always runs real preflight before creating its image', async t => {
  const f = fixture(t); fs.unlinkSync(path.join(f.root, 'requirements.txt')); let launched = false;
  await assert.rejects(runPackageBuild('static', {root: f.root, execute: () => { launched = true; }}), /Package preflight failed/);
  assert.equal(launched, false); assert.equal(fs.existsSync(path.join(f.root, '.cache')), false);
});

test('actual current package import closure rejects an undeclared new helper before image creation', () => {
  const root = process.cwd(), definition = loadPackageInputs(root);
  const actual = inspectPackageExecutionInputs(root, definition);
  assert.equal(actual.errors.length, 0, JSON.stringify(actual.errors));
  assert(actual.files.includes('scripts/package-build.mjs'));
  assert(!actual.files.includes('scripts/package-build-preflight.mjs'));
  const missing = inspectPackageExecutionInputs(root, {...definition, inputs: definition.inputs.filter(x => x !== 'scripts/package-inputs.mjs')});
  assert(missing.errors.some(x => x.kind === 'execution-declaration' && x.path === 'scripts/package-inputs.mjs'));
});

test('CLI preserves occupied and dangling-symlink report destinations', t => {
  const f = fixture(t), entry = path.resolve('scripts/package-build-preflight.mjs'), out = path.join(f.root, 'result.json');
  fs.writeFileSync(out, 'sentinel');
  assert.throws(() => execFileSync(process.execPath, [entry, '--root', f.root, '--out', out], {stdio: 'pipe'}));
  assert.equal(fs.readFileSync(out, 'utf8'), 'sentinel');
  fs.unlinkSync(out); fs.symlinkSync('absent', out);
  assert.throws(() => execFileSync(process.execPath, [entry, '--root', f.root, '--browser', 'off', '--python', f.python, '--out', out], {stdio: 'pipe'}));
  assert.equal(fs.readlinkSync(out), 'absent'); assert.equal(fs.existsSync(path.join(f.root, 'absent')), false);
});

test('all actual package entries expose their complete declared current import closures',()=>{
 const root=process.cwd(),definition=loadPackageInputs(root);
 for(const kind of ['static','hosted','cloudflare']){
  const actual=inspectPackageExecutionInputs(root,definition,kind),entry=`scripts/build-${kind}-inner.mjs`;
  assert.deepEqual(actual.errors,[]);
  assert(actual.files.includes(entry));assert(actual.files.includes('scripts/package-build.mjs'));
  assert(actual.files.includes('scripts/native-ownership/validate-build-context-stage.mjs'));
  assert.deepEqual(actual.files,[...new Set(actual.files)].sort());
  for(const name of actual.files)assert(containsPackagePath(definition.inputs,name),name);
 }
});

test('ambient Node injection is refused during runtime preflight',t=>{
 const f=fixture(t),before=process.env.NODE_OPTIONS;
 try{process.env.NODE_OPTIONS='--no-warnings';const result=inspectPackageRuntime(f.root,{python:f.python});assert(result.errors.some(e=>e.kind==='node-execution'));}
 finally{if(before===undefined)delete process.env.NODE_OPTIONS;else process.env.NODE_OPTIONS=before;}
});
