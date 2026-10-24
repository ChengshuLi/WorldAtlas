import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {materializePackageInputs, runPackageBuild, verifyPackageDependencies, assertPackageStage, inspectPackageRuntime, inspectPackageInputs} from '../scripts/package-build.mjs';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {selectedDataCheckoutPatterns, validatePackageInputs} from '../scripts/package-inputs.mjs';
import {DatabaseSync} from 'node:sqlite';
import {workspaceManager} from '../scripts/local-workspace.mjs';
import {committedPackageInputs} from '../scripts/package-output-artifact.mjs';

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

test('current-execution historical fixtures retain exact accepted Git bodies',async()=>{
 const directory=new URL('./fixtures/current-execution-authored/',import.meta.url);
 const provenance=JSON.parse(await fs.readFile(new URL('provenance.json',directory)));
 assert.equal(provenance.version,1);
 assert.equal(provenance.kind,'literal-current-execution-authored-fixtures-v1');
 assert.equal(provenance.source_commit,'07c74ff101d4ab5e679255ed85c402356aa54a42');
 assert.deepEqual(provenance.files.map(pin=>[pin.file,pin.source_path,pin.git_blob_oid]),[
  ['index.json','coordination/engineering/eastern-two-gap-repair-native-20261007/current-consumer-code/index.json','1f371fc84190beee956e8475b873cfa77f542379'],
  ['part-000.bin.gz','coordination/engineering/eastern-two-gap-repair-native-20261007/current-consumer-code/part-000.bin.gz','39c0efee9c5e5470d305070496c59abd68a7ce39'],
  ['stage-manifest.json','data/native-context-migration/manifest.json','a42ac4c5b6962998fec81468795a1eb4d19affa3'],
 ]);
 for(const pin of provenance.files){
  const raw=await fs.readFile(new URL(pin.file,directory));
  assert.equal(raw.length,pin.bytes);
  assert.equal(createHash('sha256').update(raw).digest('hex'),pin.sha256);
  assert.equal(createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex'),pin.git_blob_oid);
 }
});

test('current-execution real plain-child package positives and hostile boundaries',()=>{
 const raw=execFileSync(process.execPath,['coordination/engineering/eastern-two-gap-repair-native-20261007/current-execution-controls.mjs'],{maxBuffer:32*1024*1024,env:{...process.env,NODE_OPTIONS:'',NODE_PATH:''}});
 const result=JSON.parse(raw);assert.equal(result.status,'PASS');assert.equal(result.authored_pins_unchanged,true);assert.deepEqual(result.adverse_cases,['midrun body','unbranded receipt','wrong HEAD','wrong root','runtime mutation','omitted import','overbound body','mode mutation','new import','uncommitted source','receipt mutation']);
 assert.equal(result.historical.authored_files,31);
 assert.equal(result.historical.all_50_authored_whole_bodies_restored,true);
 assert.equal(result.historical.immutable_historical_source_and_numerical_negatives,7);
 assert.equal(result.historical.exact_additive_restoration_extension,true);
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
  assert.equal(Object.hasOwn(second, 'generated_database'), false);
  assert.deepEqual((await fs.readdir(path.join(root, '.cache'))).filter(name => name.startsWith('package-input-image-')), []);
});

test('package publication preserves local imports and exports only its generated comparison database', async t => {
  const {root, definition} = await fixture(t, {program: `
    import fs from 'node:fs';
    import path from 'node:path';
    import assert from 'node:assert/strict';
    import {DatabaseSync} from 'node:sqlite';
    assert.equal(fs.existsSync('data/atlas.sqlite'), false, 'Persistent local data must not enter the package image');
    fs.mkdirSync('data');
    const db = new DatabaseSync('data/atlas.sqlite');
    db.exec("CREATE TABLE records(id TEXT PRIMARY KEY, value TEXT); INSERT INTO records VALUES ('seed', 'declared input');");
    db.close();
    const output = JSON.parse(fs.readFileSync('.github/package-inputs.json')).generated_outputs.find(name => name.endsWith('.sqlite'));
    fs.mkdirSync(path.dirname(output), {recursive:true});
    if (output !== 'data/atlas.sqlite') fs.renameSync('data/atlas.sqlite', output);
    fs.mkdirSync('dist'); fs.writeFileSync('dist/value.json', '42');
  `});
  definition.generated_outputs = JSON.parse(await fs.readFile(new URL('../.github/package-inputs.json', import.meta.url))).generated_outputs;
  await fs.writeFile(path.join(root, '.github/package-inputs.json'), JSON.stringify(definition));
  await fs.mkdir(path.join(root, 'data'));
  const localPath = path.join(root, 'data/atlas.sqlite'), local = new DatabaseSync(localPath);
  local.exec("CREATE TABLE records(id TEXT PRIMARY KEY, value TEXT); INSERT INTO records VALUES ('local-import', 'unique retained evidence');");
  local.close();
  const before = await fs.readFile(localPath);
  execFileSync('git', ['-C', root, 'init', '-q'], {stdio:'pipe'});
  const first = await runPackageBuild('static', {root, preflight: fixturePreflight});
  const second = await runPackageBuild('static', {root, preflight: fixturePreflight});
  assert.deepEqual(first.generated_database, second.generated_database);
  const databaseBytes = await fs.readFile(path.join(root, '.cache/package-atlas.sqlite'));
  assert.deepEqual(second.generated_database, {path: '.cache/package-atlas.sqlite', bytes: databaseBytes.length,
    git_blob_oid: createHash('sha1').update(`blob ${databaseBytes.length}\0`).update(databaseBytes).digest('hex')});
  assert.deepEqual((await fs.readdir(path.join(root, '.cache'))).sort(), ['package-atlas.sqlite', 'package-input-build.json']);
  assert.deepEqual(await fs.readFile(localPath), before, 'Every byte of the persistent local database is unchanged');
  for (const [file, expected] of [[localPath, 'local-import'], [path.join(root, '.cache/package-atlas.sqlite'), 'seed']]) {
    const db = new DatabaseSync(file, {readOnly:true});
    try { assert.deepEqual(db.prepare('SELECT id FROM records').all().map(row => row.id), [expected]); }
    finally { db.close(); }
  }
  assert.equal(await fs.readFile(path.join(root, 'dist/value.json'), 'utf8'), '42');
  assert.deepEqual((await fs.readdir(path.join(root, '.cache'))).filter(name => name.startsWith('package-input-image-')), []);
  assert.throws(() => validatePackageInputs({...definition, generated_outputs: ['data/atlas.sqlite']}), /Unsupported generated/);
  await assert.rejects(runPackageBuild('static', {root, preflight:fixturePreflight, execute:async () => { throw Error('controlled build failure'); }}), /controlled build failure/);
  assert.deepEqual(await fs.readFile(path.join(root, '.cache/package-atlas.sqlite')), databaseBytes);
  assert.deepEqual(await fs.readFile(localPath), before);
  assert.deepEqual(await fs.readdir(path.join(root, '.cache')), ['package-atlas.sqlite'], 'Failure keeps prior output but no successful receipt or temporary stage');
});

test('normal guarded release consumes only the unchanged database issued by the actual package builder', async t => {
  const {root, definition} = await fixture(t, {program: `
    import fs from 'node:fs';
    import {DatabaseSync} from 'node:sqlite';
    fs.mkdirSync('.cache');
    const db = new DatabaseSync('.cache/package-atlas.sqlite');
    db.exec("CREATE TABLE records(id TEXT PRIMARY KEY); INSERT INTO records VALUES ('generated seed');");
    db.close();
  `});
  definition.generated_outputs = ['.cache/package-atlas.sqlite'];
  await fs.writeFile(path.join(root, '.github/package-inputs.json'), JSON.stringify(definition));
  await fs.writeFile(path.join(root, '.gitignore'), '.cache/\nnode_modules/\n');
  await fs.writeFile(path.join(root, '.gitattributes'), '.cache/*.sqlite filter=must-not-run\n');
  const git = (...args) => execFileSync('git', ['-C', root, ...args], {encoding:'utf8', stdio:['pipe','pipe','pipe']});
  git('init', '-b', 'main'); git('config', 'user.name', 'Fixture'); git('config', 'user.email', 'fixture@example.org');
  git('config', 'filter.must-not-run.clean', 'false'); git('config', 'filter.must-not-run.required', 'true');
  git('add', '.'); git('commit', '-m', 'declared package fixture'); git('remote', 'add', 'origin', root);
  const manager = workspaceManager(root), entry = manager.allocate({worker:'generated-db', branch:'engineering/generated-db'});
  const head = git('rev-parse', 'HEAD').trim(), release = () => manager.release({worker:entry.worker, token:entry.token});
  const cache = path.join(entry.path, '.cache'), database = path.join(cache, 'package-atlas.sqlite'), receiptFile = path.join(cache, 'package-input-build.json');
  await fs.mkdir(path.join(entry.path, 'node_modules'));
  const inputs = inspectPackageInputs(entry.path, definition);
  assert.deepEqual(inputs.errors, []);
  const definitionHash = createHash('sha256').update(await fs.readFile(path.join(entry.path, '.github/package-inputs.json'))).digest('hex');
  const receipt = await runPackageBuild('static', {root:entry.path, preflight:async () => ({...await fixturePreflight(), inputs, input_definition_sha256:definitionHash})});
  await fs.rmdir(path.join(entry.path, 'node_modules'));
  const originalDatabase = await fs.readFile(database), originalReceipt = await fs.readFile(receiptFile);
  const descriptor = receipt.generated_database;
  assert.deepEqual(descriptor, {path:'.cache/package-atlas.sqlite', bytes:originalDatabase.length,
    git_blob_oid:createHash('sha1').update(`blob ${originalDatabase.length}\0`).update(originalDatabase).digest('hex')});
  assert.throws(() => git('cat-file', '-e', descriptor.git_blob_oid), 'Hashing must not add the database to shared Git');
  const assertRetained = async () => {
    assert.equal(manager.report().entries.find(row => row.token === entry.token)?.path, entry.path);
    assert.equal(await fs.readFile(path.join(entry.path, 'src/value.json'), 'utf8'), '42');
    assert.throws(() => git('rev-parse', '--verify', `refs/worldatlas-local-recovery/${entry.token}`));
  };
  assert.throws(() => manager.release({worker:entry.worker, token:'wrong'}), /ownership/);
  for (const mutate of [
    value => { delete value.generated_database; },
    value => { value.version = 0; },
    value => { value.kind = 'unknown'; },
    value => { delete value.preflight; },
    value => { value.preflight.passed = false; },
    value => { value.preflight.inputs.head = '0'.repeat(40); },
    value => { value.input_definition_sha256 = value.preflight.input_definition_sha256 = '0'.repeat(64); },
    value => { value.preflight.input_definition_sha256 = '0'.repeat(64); },
    value => { value.generated_database.path = 'data/atlas.sqlite'; },
    value => { value.generated_database.bytes++; },
    value => { value.generated_database.git_blob_oid = '0'.repeat(40); },
  ]) {
    const changed = JSON.parse(originalReceipt); mutate(changed);
    const raw = JSON.stringify(changed); await fs.writeFile(receiptFile, raw);
    assert.throws(release, /ignored/); await assertRetained();
    assert.equal(await fs.readFile(receiptFile, 'utf8'), raw);
    assert.deepEqual(await fs.readFile(database), originalDatabase);
    await fs.writeFile(receiptFile, originalReceipt);
  }
  const changed = Buffer.from(originalDatabase); changed[changed.length - 1] ^= 1;
  await fs.writeFile(database, changed);
  assert.throws(release, /ignored/); await assertRetained();
  assert.deepEqual(await fs.readFile(database), changed);
  await fs.writeFile(database, originalDatabase);
  for (const extra of ['package-atlas.sqlite-wal', 'package-atlas.sqlite-shm', 'valuable.json']) {
    const file = path.join(cache, extra); await fs.writeFile(file, 'retain');
    assert.throws(release, /ignored/); await assertRetained();
    assert.equal(await fs.readFile(file, 'utf8'), 'retain'); await fs.unlink(file);
  }
  for (const file of [database, receiptFile]) {
    const bytes = await fs.readFile(file), outside = path.join(root, '.cache', path.basename(file));
    await fs.mkdir(path.dirname(outside), {recursive:true}); await fs.writeFile(outside, bytes);
    await fs.unlink(file); await fs.symlink(outside, file);
    assert.throws(release, /ignored/); await assertRetained();
    assert.deepEqual(await fs.readFile(outside), bytes);
    await fs.unlink(file); await fs.writeFile(file, bytes);
  }
  const outside = path.join(root, '.cache/aliased-build'); await fs.rename(cache, outside); await fs.symlink(outside, cache);
  assert.throws(release, /ignored|Symlink|untracked/); await assertRetained();
  await fs.unlink(cache); await fs.rename(outside, cache);
  await fs.unlink(receiptFile);
  assert.throws(release, /ignored/); await assertRetained();
  await fs.writeFile(receiptFile, originalReceipt);
  // A later clean commit is not silently treated as this build's producer.
  execFileSync('git', ['-C', entry.path, 'commit', '--allow-empty', '-m', 'later task state'], {stdio:'pipe'});
  assert.throws(release, /ignored/); await assertRetained();
  execFileSync('git', ['-C', entry.path, 'reset', '--soft', head], {stdio:'pipe'});
  const result = release();
  assert.equal(result.released, true);
  assert.deepEqual(result.removed_generated_database, {...descriptor, producer_head:head, input_definition_sha256:definitionHash,
    build_receipt_sha256:createHash('sha256').update(originalReceipt).digest('hex')});
  assert.equal(git('rev-parse', result.preservedRef).trim(), head);
  assert.equal(git('rev-parse', 'engineering/generated-db').trim(), head);
  await assert.rejects(fs.stat(entry.path), {code:'ENOENT'});
  assert.throws(() => git('cat-file', '-e', descriptor.git_blob_oid), 'Release hashing must not archive the generated body');
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


test('cold selected-data checkout preserves the full fallback build image without verification-only fixtures', async t => {
  const verification = ['data/verification/body.json', 'research/geography/verification/body.json',
    'coordination/engineering/verification/body.json'];
  const required = ['data/current/value.json', 'research/geography/current/nested/value.json',
    'coordination/engineering/current/body.json', 'data/optional-present/value.json'];
  const program = `import fs from 'node:fs';
    const required=${JSON.stringify(required)}, excluded=${JSON.stringify(verification)};
    for(const name of excluded)if(fs.existsSync(name))throw Error('Verification fixture entered build image');
    fs.mkdirSync('dist/client',{recursive:true});
    fs.writeFileSync('dist/client/values.json',JSON.stringify(required.map(name=>fs.readFileSync(name,'utf8'))));`;
  const {root,definition}=await fixture(t,{program});
  await fs.rename(path.join(root,'scripts/build-static-inner.mjs'),path.join(root,'scripts/build-cloudflare-inner.mjs'));
  definition.inputs[1]='scripts/build-cloudflare-inner.mjs';
  definition.inputs.push('data/current/','research/geography/current/','coordination/engineering/current/body.json',
    'data/optional-present/','data/optional-absent/');
  definition.optional_inputs.push('data/optional-present/','data/optional-absent/');
  definition.verification_paths=verification;
  const expectations='coordination/engineering/current/selected-delivery-expectations.json';
  for(const name of [...required,...verification,expectations]){
    await fs.mkdir(path.dirname(path.join(root,name)),{recursive:true});await fs.writeFile(path.join(root,name),name+'\n');
  }
  await fs.writeFile(path.join(root,'.github/package-inputs.json'),JSON.stringify(definition));
  const git=(args,input)=>execFileSync('git',['-C',root,'-c','core.hooksPath='+os.devNull,
    '-c','user.name=Fixture','-c','user.email=fixture@example.invalid',...args],
    {encoding:'utf8',input,env:{...process.env,GIT_NO_LAZY_FETCH:'1',GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_GLOBAL:os.devNull}});
  git(['init','-q']);await fs.appendFile(path.join(root,'.git/info/exclude'),'\nnode_modules/\n.cache/\ndist/\n');
  git(['add','.']);git(['commit','-qm','Synthetic selected fallback input boundary']);
  const before=committedPackageInputs(root,definition),head=git(['rev-parse','HEAD']);
  assert.deepEqual(inspectPackageInputs(root,definition).errors,[]);
  const beforeImage=path.join(root,'.cache/image-before'),afterImage=path.join(root,'.cache/image-after');
  const inventory=await materializePackageInputs({source:root,destination:beforeImage,definition});
  const entries=new Map(git(['ls-tree','-rz','HEAD']).split('\0').filter(Boolean).map(line=>{
    const [metadata,name]=line.split('\t'),[mode,type,sha]=metadata.split(' ');return [name,{mode,type,sha}];
  }));
  git(['sparse-checkout','set','--no-cone','--stdin'],selectedDataCheckoutPatterns(definition,entries,expectations).join('\n')+'\n');
  git(['checkout','--detach','-q',head.trim()]);
  for(const name of verification)await assert.rejects(fs.stat(path.join(root,name)),{code:'ENOENT'});
  assert.equal(git(['rev-parse','HEAD']),head);
  assert.deepEqual(committedPackageInputs(root,definition),before);
  assert.deepEqual(inspectPackageInputs(root,definition).errors,[]);
  assert.deepEqual(await materializePackageInputs({source:root,destination:afterImage,definition}),inventory);
  for(const {path:name}of inventory)assert.deepEqual(await fs.readFile(path.join(afterImage,name)),await fs.readFile(path.join(beforeImage,name)));
  // Real private child and Cloudflare output admission, with only the existing
  // explicit synthetic runtime-preflight injection; no scientific producer.
  const result=await runPackageBuild('cloudflare',{root,preflight:fixturePreflight});
  assert.equal(result.source_files,inventory.length);
  assert.equal(result.source_bytes,inventory.reduce((sum,row)=>sum+row.bytes,0));
  assert.deepEqual(JSON.parse(await fs.readFile(path.join(root,'dist/client/values.json'))),required.map(name=>name+'\n'));
  await fs.unlink(path.join(root,required[0]));
  assert(inspectPackageInputs(root,definition).errors.some(error=>error.path===required[0]));
});

test('retired Site build has no latest-main entrypoint',async()=>{
 await assert.rejects(runPackageBuild('hosted'),/Unknown package build/);
});
