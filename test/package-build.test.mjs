import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {materializePackageInputs, runPackageBuild, verifyPackageDependencies, assertPackageStage, inspectPackageRuntime} from '../scripts/package-build.mjs';
import {execFileSync} from 'node:child_process';

const fixturePreflight = async () => ({passed: true, errors: [], synthetic_package_boundary_fixture: true});

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
 const result=JSON.parse(raw);assert.equal(result.status,'PASS');assert.equal(result.authored_pins_unchanged,true);assert.deepEqual(result.adverse_cases,['midrun body','unbranded receipt','wrong HEAD','wrong root','runtime mutation','omitted import','overbound body','mode mutation','new import','uncommitted source','receipt mutation']);
 assert.equal(result.actualInner.actual_spawn_without_execute_injection,true);
 assert.deepEqual(result.actualInner.actual_environment_boundary_cases,['positive','missing','hash','root','path','stale']);
});

test('only declared files enter the source image; unrelated research cannot alter artifact bytes', async t => {
  const {root, definition} = await fixture(t);
  const stage = path.join(root, 'image');
  await materializePackageInputs({source: root, destination: stage, definition});
  await assert.rejects(fs.stat(path.join(stage, 'research/paper.json')), {code: 'ENOENT'});
  const first = await runPackageBuild('static', {root, preflight: fixturePreflight});
  assert.equal(await fs.readFile(path.join(root, 'dist/value.json'), 'utf8'), '42');
  await fs.writeFile(path.join(root, 'research/paper.json'), '1000');
  const second = await runPackageBuild('static', {root, preflight: fixturePreflight});
  assert.equal(await fs.readFile(path.join(root, 'dist/value.json'), 'utf8'), '42');
  assert.equal(first.source_bytes, second.source_bytes);
  assert.deepEqual((await fs.readdir(path.join(root, '.cache'))).filter(name => name.startsWith('package-input-image-')), []);
});

test('undeclared reads and imports fail before replacing caller outputs and clean the image', async t => {
  for (const statement of ["fs.readFileSync('research/paper.json')", "await import('../research/secret.mjs')"]) {
    const {root} = await fixture(t, {program: `import fs from 'node:fs'; ${statement}; fs.mkdirSync('dist');`});
    await fs.mkdir(path.join(root, 'dist'));
    await fs.writeFile(path.join(root, 'dist/previous'), 'preserved');
    await assert.rejects(runPackageBuild('static', {root, preflight: fixturePreflight}), /build failed/);
    assert.equal(await fs.readFile(path.join(root, 'dist/previous'), 'utf8'), 'preserved');
    assert.deepEqual(await fs.readdir(path.join(root, '.cache')), []);
  }
});

test('explicit research promotion makes the same read available', async t => {
  const {root} = await fixture(t, {promoted: true,
    program: "import fs from 'node:fs'; fs.mkdirSync('dist'); fs.writeFileSync('dist/value.json', fs.readFileSync('research/paper.json'));"});
  await runPackageBuild('static', {root, preflight: fixturePreflight});
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
  await assert.rejects(runPackageBuild('static', {root, preflight: fixturePreflight}), /cache must be/);
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


test('producer and selected runtime probes genuinely import without Python startup hooks',async t=>{
  const prior=new Map(['NODE_OPTIONS','NODE_PATH'].map(name=>[name,process.env[name]]));
  for(const name of prior.keys())delete process.env[name];
  t.after(()=>{for(const [name,value]of prior)value===undefined?delete process.env[name]:process.env[name]=value;});
  const {root}=await fixture(t),venv=path.join(root,'venv'),marker=path.join(root,'startup-hook-ran');
  execFileSync('python3',['-I','-S','-B','-m','venv','--without-pip',venv],{stdio:'pipe'});
  const python=path.join(venv,'bin/python3');
  const version=execFileSync(python,['-I','-S','-B','-c','import sys;print(str(sys.version_info.major)+"."+str(sys.version_info.minor))'],{encoding:'utf8'}).trim();
  const site=path.join(venv,'lib','python'+version,'site-packages');await fs.mkdir(site,{recursive:true});
  for(const name of ['numpy','shapely','pyproj'])await fs.writeFile(path.join(site,name+'.py'),'__version__="1.0"\n');
  const hook='import pathlib;pathlib.Path('+JSON.stringify(marker)+').write_text("executed")\n';
  await fs.writeFile(path.join(site,'probe.pth'),hook);await fs.writeFile(path.join(site,'sitecustomize.py'),hook);
  await fs.writeFile(path.join(root,'requirements.txt'),'numpy==1.0\nshapely==1.0\npyproj==1.0\n');
  await fs.writeFile(path.join(root,'package.json'),JSON.stringify({engines:{node:'>=24'}}));
  const lock=JSON.stringify({lockfileVersion:3,packages:{}});
  await fs.writeFile(path.join(root,'package-lock.json'),lock);await fs.writeFile(path.join(root,'node_modules/.package-lock.json'),lock);
  await fs.copyFile(new URL('../scripts/package-python-runtime.py',import.meta.url),path.join(root,'scripts/package-python-runtime.py'));
  const isolated=inspectPackageRuntime(root,{python,isolatedPython:true});
  assert.deepEqual(isolated.errors,[]);assert.equal(isolated.python.imports.length,3);
  assert.ok(isolated.python.imports.every(row=>row.actual==='1.0'));
  await assert.rejects(fs.stat(marker),{code:'ENOENT'});
  assert.deepEqual(inspectPackageRuntime(root,{python}).errors,[]);
  await assert.rejects(fs.stat(marker),{code:'ENOENT'});
  // Genuine ordinary startup proves the hostile fixture is active.
  execFileSync(python,['-c','pass']);
  assert.equal(await fs.readFile(marker,'utf8'),'executed');
});


test('the actual build caller validates prepared products once and retains release/grid comparisons', async () => {
  const source = await fs.readFile(new URL('../scripts/build-static-inner.mjs', import.meta.url), 'utf8');
  const start = source.indexOf('  reference.pixelMissing='), end = source.indexOf('    const bytes=selectedGrid.bounds;', start);
  assert(start > 0 && end > start);
  // Execute the actual caller statements before allocation/build, with explicit
  // fixture dependencies. The real checker/Python path has its own control.
  const run = new (Object.getPrototypeOf(async function() {}).constructor)('context', `with(context){${source.slice(start, end)}}}`);
  const {createHash} = await import('node:crypto'), hierarchy = Buffer.from('fixture hierarchy');
  const hierarchySHA = createHash('sha256').update(hierarchy).digest('hex');
  const fixture = () => {
    const value = {calls: 0, fs: {readFile: async name => {assert.equal(name, 'data/hierarchy.json');return hierarchy;}}, createHash,
      reference: {features: []}, pixelAudit: {missing: []}, preparedEvidence: {}, currentContext: null,
      geographicRelease: {footprints_sha256: 'actual-footprints', hierarchy_sha256: hierarchySHA},
      fixedGrid: {footprints_sha256: 'actual-footprints', hierarchy_sha256: hierarchySHA}, selectedGrid: {},
      validatePreparedEvidenceIndex: () => {}};
    value.checkPrepared = features => {assert.equal(features, value.reference.features);value.calls++;return 'actual-footprints';};
    return value;
  };
  for (const fixed of [true, false]) {const f=fixture();if(!fixed)f.fixedGrid=null;await run(f);assert.equal(f.calls,1);}
  for (const [target, key] of [['geographicRelease','footprints_sha256'],['geographicRelease','hierarchy_sha256'],['fixedGrid','footprints_sha256'],['fixedGrid','hierarchy_sha256']]) {
    const f=fixture();f[target][key]='changed';await assert.rejects(run(f),/Reference release|canonical grid/);assert.equal(f.calls,1);
  }
  const projected=fixture();projected.fixedGrid.hierarchy_sha256='original';projected.selectedGrid.applicationReference={hierarchy_sha256:hierarchySHA};await run(projected);assert.equal(projected.calls,1);
  const invalid=fixture();invalid.checkPrepared=()=>{throw Error('actual prepared bytes changed');};await assert.rejects(run(invalid),/actual prepared bytes changed/);
});


test('actual fresh Cloudflare package admits 25 MiB and refuses one extra byte before replacing outputs',async t=>{
 const {root,definition}=await fixture(t);
 definition.inputs.push('scripts/build-cloudflare-inner.mjs');
 await fs.writeFile(path.join(root,'.github/package-inputs.json'),JSON.stringify(definition));
 const program=bytes=>`import fs from 'node:fs'; fs.mkdirSync('dist/client',{recursive:true}); const fd=fs.openSync('dist/client/asset.bin','w'); fs.ftruncateSync(fd,${bytes}); fs.closeSync(fd);`;
 await fs.writeFile(path.join(root,'scripts/build-cloudflare-inner.mjs'),program(26214400));
 await runPackageBuild('cloudflare',{root,preflight:fixturePreflight});
 assert.equal((await fs.stat(path.join(root,'dist/client/asset.bin'))).size,26214400);
 await fs.writeFile(path.join(root,'dist/client/preserved'),'accepted previous output');
 await fs.writeFile(path.join(root,'scripts/build-cloudflare-inner.mjs'),program(26214401));
 await assert.rejects(runPackageBuild('cloudflare',{root,preflight:fixturePreflight}),/Cloudflare static asset exceeds 25 MiB/);
 assert.equal(await fs.readFile(path.join(root,'dist/client/preserved'),'utf8'),'accepted previous output');
 assert.equal((await fs.stat(path.join(root,'dist/client/asset.bin'))).size,26214400);
});
