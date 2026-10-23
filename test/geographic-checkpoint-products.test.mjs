import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {spawnSync} from 'node:child_process';
import {gzipSync} from 'node:zlib';
import {CHECKPOINT_MEMBERS, reportHash} from '../scripts/geographic-report-artifact.mjs';
const modulePath = path.resolve('scripts/geographic_checkpoint_products.py');
const canonical = value => Array.isArray(value) ? value.map(canonical) : value && typeof value === 'object' ? Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])])) : value;
const bytes = value => Buffer.from(JSON.stringify(canonical(value)) + '\n');
function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'checkpoint-retention-'));
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  const source = path.join(root, 'source'), out = path.join(root, 'out');
  fs.mkdirSync(source); fs.mkdirSync(out);
  const put = (name, raw) => {fs.writeFileSync(path.join(source, name), raw, {mode: 0o644}); return {path: name, bytes: raw.length, sha256: reportHash(raw)};};
  const gzip = (name, value) => {const raw = bytes(value); return {...put(name, gzipSync(raw)), decoded_bytes: raw.length, decoded_sha256: reportHash(raw)};};
  const native = {method: 'selected-native-owner-conservation-v1', status: 'no-new-native-loss',
    candidate_code_executed: false, intervals: [], lost_or_reassigned_cells: 0};
  const routes = put('checkpoint-routes.json', bytes([]));
  const facts = {native_result_sha256: reportHash(bytes(native)), checkpoint_routes: routes};
  const derived = {version: 1, complete: true, kind: 'derived-selected-checkpoint-candidate-v1', accepted_checkpoint: false,
    validation_stage: 'native-passed', certificate: gzip('derived-certificate.json.gz', {version: 1, entries: []}),
    facts: put('derived-facts.json', bytes(facts)), routes};
  put('derived-publication.json', bytes(derived));
  const issued = {native: {...native, runtime: {notPartOfInnerHash: true}}, derived_checkpoint: derived};
  return {root, source, out, issued, put};
}
function run(f, extra = '') {
  const code = `import json,runpy,sys\nm=runpy.run_path(sys.argv[1])\nissued=json.loads(sys.argv[4])\n${extra}\nresult=m['retain_checkpoint_products'](sys.argv[2],sys.argv[3],issued)\nprint(json.dumps(result))`;
  const env = {...process.env}; delete env.GH_TOKEN; delete env.GITHUB_TOKEN;
  return spawnSync(process.env.PYTHON ?? 'python3', ['-I', '-B', '-c', code, modulePath, f.source, f.out, JSON.stringify(f.issued)], {encoding: 'utf8', env});
}
test('actual native-only retention copies exactly four bound provisional products', t => {
  const f = fixture(t), result = run(f);
  assert.equal(result.status, 0, result.stderr);
  const descriptor = JSON.parse(result.stdout);
  assert.deepEqual(descriptor.members.map(row => row.name), [...CHECKPOINT_MEMBERS].sort());
  assert.deepEqual(fs.readdirSync(f.out).sort(), [...CHECKPOINT_MEMBERS].sort());
  for (const row of descriptor.members) assert(fs.readFileSync(path.join(f.out, row.name)).equals(fs.readFileSync(path.join(f.source, row.name))));
  const derived = JSON.parse(fs.readFileSync(path.join(f.out, 'derived-publication.json')));
  assert.equal(derived.accepted_checkpoint, false); assert.equal(derived.validation_stage, 'native-passed');
  assert.equal(f.issued.continuous, undefined); assert.equal(f.issued.continuous_result, undefined);
});
test('ordinary and dangling-symlink collisions refuse before writing and preserve original sentinels', t => {
  for (const name of [...CHECKPOINT_MEMBERS, 'operating.json']) for (const symbolic of [false, true]) {
    const f = fixture(t), target = path.join(f.out, name);
    if (symbolic) fs.symlinkSync(path.join(f.root, 'missing'), target); else fs.writeFileSync(target, 'original sentinel');
    const result = run(f); assert.notEqual(result.status, 0); assert.match(result.stderr, /already exists/);
    assert.equal(fs.readdirSync(f.out).length, 1);
    if (symbolic) assert(fs.lstatSync(target).isSymbolicLink()); else assert.equal(fs.readFileSync(target, 'utf8'), 'original sentinel');
  }
});
test('missing or failed native evidence, forged bindings, incomplete publications and extra products refuse', t => {
  for (const alter of [f => delete f.issued.native, f => delete f.issued.native.method, f => f.issued.native.status = 'native-regressions-found',
    f => f.issued.native.candidate_code_executed = true, f => delete f.issued.native.intervals,
    f => f.issued.native.intervals.push({row: 1}), f => f.issued.native.lost_or_reassigned_cells = 1,
    f => f.issued.native.extra = 'not in the issued native digest', f => delete f.issued.derived_checkpoint,
    f => f.issued.derived_checkpoint.accepted_checkpoint = true,
    f => f.issued.derived_checkpoint.complete = false, f => f.issued.derived_checkpoint.validation_stage = 'native-pending',
    f => f.put('extra.json', bytes({})), f => f.put('publication.json', bytes({})),
    f => fs.unlinkSync(path.join(f.source, 'checkpoint-routes.json'))]) {
    const f = fixture(t); alter(f); const result = run(f);
    assert.notEqual(result.status, 0); assert.deepEqual(fs.readdirSync(f.out), []);
  }
});
test('certificate body drift and symlink sources refuse without copying partial products', t => {
  for (const symbolic of [false, true]) {
    const f = fixture(t), target = path.join(f.source, 'derived-certificate.json.gz');
    if (symbolic) {fs.renameSync(target, path.join(f.root, 'original.gz')); fs.symlinkSync(path.join(f.root, 'original.gz'), target);}
    else fs.writeFileSync(target, gzipSync(bytes({forged: true})));
    const result = run(f); assert.notEqual(result.status, 0); assert.deepEqual(fs.readdirSync(f.out), []);
  }
});
test('bounded certificate gzip rejects trailer size lies and concatenated hidden bodies', t => {
  for (const concatenate of [false, true]) {
    const f = fixture(t), file = path.join(f.source, 'derived-certificate.json.gz');
    const body = fs.readFileSync(file);
    if (concatenate) fs.writeFileSync(file, Buffer.concat([body, gzipSync(Buffer.from('x'))]));
    else {body.writeUInt32LE(1, body.length - 4); fs.writeFileSync(file, body);}
    const result = run(f); assert.notEqual(result.status, 0); assert.deepEqual(fs.readdirSync(f.out), []);
  }
});
test('partial write failure yields no completion descriptor and preserves failed output evidence', t => {
  const f = fixture(t);
  const code = `import pathlib\noriginal=pathlib.Path.open\ndef fail(self,*args,**kwargs):\n    if self.parent==pathlib.Path(sys.argv[3]) and self.name=='derived-facts.json': raise OSError('injected write failure')\n    return original(self,*args,**kwargs)\npathlib.Path.open=fail`;
  const result = run(f, code); assert.notEqual(result.status, 0); assert.match(result.stderr, /injected write failure/);
  assert.equal(result.stdout, ''); assert(fs.readdirSync(f.out).length > 0); assert(!fs.existsSync(path.join(f.out, 'geography-check.json'))); assert(!fs.existsSync(path.join(f.out, 'derived-publication.json')));
});
test('actual joint parent retains native products before temporary cleanup and withholds failed results', t => {
  for (const loss of [false, true]) {
    const f = fixture(t), runner = path.resolve('scripts/run-geographic-check.py');
    Object.assign(f.issued, {kind: 'trusted-selected-joint-comparison-v1', mode: 'authenticated-checkpoint-append-v1', candidate_code_executed: false});
    if (loss) Object.assign(f.issued.native, {status: 'native-regressions-found', lost_or_reassigned_cells: 1, intervals: [{row: 1}]});
    const code = `import importlib.util,json,pathlib,shutil,sys\nspec=importlib.util.spec_from_file_location('joint_parent',sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)\nissued=json.loads(sys.argv[5]);destinations=[]\ndef child(command,**kwargs):\n    assert command[1].endswith('/selected-joint-entry.mjs')\n    destination=pathlib.Path(command[-2]);shutil.copytree(sys.argv[3],destination);destinations.append(destination);return json.dumps(issued).encode()\nm.subprocess.check_output=child\nresult=m.selected_joint(pathlib.Path(sys.argv[2]),'a'*40,'b'*40,checkpoint_destination=pathlib.Path(sys.argv[4]))\nassert len(destinations)==1 and all(not p.exists() for p in destinations)\nassert not any(name=='shapely' or name.startswith('shapely.') for name in sys.modules)\nprint(json.dumps(result))`;
    const result = spawnSync(process.env.PYTHON ?? 'python3', ['-I', '-B', '-c', code, runner, process.cwd(), f.source, f.out, JSON.stringify(f.issued)], {encoding: 'utf8'});
    assert.equal(result.status, 0, result.stderr); const actual = JSON.parse(result.stdout);
    assert.equal(actual.continuous, undefined); assert.equal(actual.continuous_result, undefined);
    if (loss) {assert.equal(actual.checkpoint, undefined); assert.deepEqual(fs.readdirSync(f.out), []);}
    else {assert.equal(actual.checkpoint.members.length, 4); assert(fs.existsSync(path.join(f.out, 'derived-certificate.json.gz')));}
  }
});
test('joint parent collision admission precedes launching its native child', t => {
  for (const symbolic of [false, true]) {
    const f = fixture(t), target = path.join(f.out, 'derived-facts.json');
    if (symbolic) fs.symlinkSync(path.join(f.root, 'missing'), target); else fs.writeFileSync(target, 'original sentinel');
    const runner = path.resolve('scripts/run-geographic-check.py');
    const code = `import importlib.util,pathlib,sys\nspec=importlib.util.spec_from_file_location('joint_parent',sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)\ndef child(*args,**kwargs): raise AssertionError('native child started before collision admission')\nm.subprocess.check_output=child\nm.selected_joint(pathlib.Path(sys.argv[2]),'a'*40,'b'*40,checkpoint_destination=pathlib.Path(sys.argv[3]))`;
    const result = spawnSync(process.env.PYTHON ?? 'python3', ['-I', '-B', '-c', code, runner, process.cwd(), f.out], {encoding: 'utf8'});
    assert.notEqual(result.status, 0); assert.match(result.stderr, /Checkpoint output already exists/); assert.doesNotMatch(result.stderr, /native child started/);
    if (symbolic) assert(fs.lstatSync(target).isSymbolicLink()); else assert.equal(fs.readFileSync(target, 'utf8'), 'original sentinel');
  }
});
