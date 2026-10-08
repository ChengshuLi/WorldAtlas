import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {materializePackageInputs, runPackageBuild, verifyPackageDependencies, assertPackageStage} from '../scripts/package-build.mjs';
import {execFileSync} from 'node:child_process';

async function fixture(t, {program, promoted = false} = {}) {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'atlas-package-boundary-'));
  t.after(() => fs.rm(root, {recursive: true, force: true}));
  const definition = {version: 1, inputs: ['.github/package-inputs.json', 'scripts/build-static-inner.mjs', 'src/'],
    optional_inputs: [], verification_paths: [], generated_outputs: ['dist/']};
  if (promoted) definition.inputs.push('research/paper.json');
  const files = {'.github/package-inputs.json': JSON.stringify(definition), 'src/value.json': '42',
    'scripts/build-static-inner.mjs': program ?? "import fs from 'node:fs'; fs.mkdirSync('dist'); fs.writeFileSync('dist/value.json', fs.readFileSync('src/value.json'));",
    'research/paper.json': '99', 'research/secret.mjs': 'export default 99;'};
  for (const [name, value] of Object.entries(files)) {
    await fs.mkdir(path.dirname(path.join(root, name)), {recursive: true});
    await fs.writeFile(path.join(root, name), value);
  }
  await fs.mkdir(path.join(root, 'node_modules'));
  return {root, definition};
}

test('current-execution real plain-child package positives and hostile boundaries',()=>{
 const raw=execFileSync(process.execPath,['coordination/engineering/eastern-two-gap-repair-native-20261007/current-execution-controls.mjs'],{maxBuffer:32*1024*1024,env:{...process.env,NODE_OPTIONS:'',NODE_PATH:''}});
 const result=JSON.parse(raw);assert.equal(result.status,'PASS');assert.equal(result.authored_pins_unchanged,true);assert.equal(result.adverse_cases.length,12);
});

test('only declared files enter the source image; unrelated research cannot alter artifact bytes', async t => {
  const {root, definition} = await fixture(t);
  const stage = path.join(root, 'image');
  await materializePackageInputs({source: root, destination: stage, definition});
  await assert.rejects(fs.stat(path.join(stage, 'research/paper.json')), {code: 'ENOENT'});
  const first = await runPackageBuild('static', {root});
  assert.equal(await fs.readFile(path.join(root, 'dist/value.json'), 'utf8'), '42');
  await fs.writeFile(path.join(root, 'research/paper.json'), '1000');
  const second = await runPackageBuild('static', {root});
  assert.equal(await fs.readFile(path.join(root, 'dist/value.json'), 'utf8'), '42');
  assert.equal(first.source_bytes, second.source_bytes);
  assert.deepEqual((await fs.readdir(path.join(root, '.cache'))).filter(name => name.startsWith('package-input-image-')), []);
});

test('undeclared reads and imports fail before replacing caller outputs and clean the image', async t => {
  for (const statement of ["fs.readFileSync('research/paper.json')", "await import('../research/secret.mjs')"]) {
    const {root} = await fixture(t, {program: `import fs from 'node:fs'; ${statement}; fs.mkdirSync('dist');`});
    await fs.mkdir(path.join(root, 'dist'));
    await fs.writeFile(path.join(root, 'dist/previous'), 'preserved');
    await assert.rejects(runPackageBuild('static', {root}), /build failed/);
    assert.equal(await fs.readFile(path.join(root, 'dist/previous'), 'utf8'), 'preserved');
    assert.deepEqual(await fs.readdir(path.join(root, '.cache')), []);
  }
});

test('explicit research promotion makes the same read available', async t => {
  const {root} = await fixture(t, {promoted: true,
    program: "import fs from 'node:fs'; fs.mkdirSync('dist'); fs.writeFileSync('dist/value.json', fs.readFileSync('research/paper.json'));"});
  await runPackageBuild('static', {root});
  assert.equal(await fs.readFile(path.join(root, 'dist/value.json'), 'utf8'), '99');
});

test('input symlinks, including ancestor aliases, cannot expose undeclared files', async t => {
  const {root, definition} = await fixture(t);
  await fs.symlink('../research/paper.json', path.join(root, 'src/link.json'));
  await assert.rejects(materializePackageInputs({source: root, destination: path.join(root, 'image'), definition}), /symlink/);
  await fs.rm(path.join(root, 'src/link.json'));
  await fs.symlink('research', path.join(root, 'alias'));
  await assert.rejects(materializePackageInputs({source: root, destination: path.join(root, 'second-image'),
    definition: {...definition, inputs: [...definition.inputs, 'alias/paper.json']}}), /nonordinary parent/);
});

test('missing mandatory inputs fail; optional absent inputs are allowed', async t => {
  const {root, definition} = await fixture(t);
  const value = {...definition, inputs: [...definition.inputs, 'public/']};
  await assert.rejects(materializePackageInputs({source: root, destination: path.join(root, 'image'), definition: value}), /missing/);
  await materializePackageInputs({source: root, destination: path.join(root, 'image'), definition: {...value, optional_inputs: ['public/']}});
});

test('dependency links must stay within the installed dependency tree', async t => {
  const {root} = await fixture(t);
  const dependencies = path.join(root, 'node_modules');
  await fs.mkdir(path.join(dependencies, 'tool'));
  await fs.mkdir(path.join(dependencies, '.bin'));
  await fs.writeFile(path.join(dependencies, 'tool/run'), 'tool');
  await fs.symlink('../tool/run', path.join(dependencies, '.bin/run'));
  assert.equal(await verifyPackageDependencies(dependencies), await fs.realpath(dependencies));
  await fs.symlink('../research', path.join(dependencies, 'workspace'));
  await assert.rejects(verifyPackageDependencies(dependencies), /escapes/);
});

test('output and cache ancestor links are rejected', async t => {
  const {root} = await fixture(t);
  await fs.symlink('research', path.join(root, '.cache'));
  await assert.rejects(runPackageBuild('static', {root}), /cache must be/);
});

test('private builder requires the actual declared image identity', () => {
  const previous = process.env.WORLDATLAS_PACKAGE_STAGE;
  try {
    delete process.env.WORLDATLAS_PACKAGE_STAGE;
    assert.throws(() => assertPackageStage('/example'), /Private builder/);
    process.env.WORLDATLAS_PACKAGE_STAGE = '/other';
    assert.throws(() => assertPackageStage('/example'), /Private builder/);
    assertPackageStage('/other');
  } finally {
    if (previous === undefined) delete process.env.WORLDATLAS_PACKAGE_STAGE;
    else process.env.WORLDATLAS_PACKAGE_STAGE = previous;
  }
});
