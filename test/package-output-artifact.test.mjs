import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {createPackageOutputManifest, snapshotPackageOutputSource, inventoryPackageOutput, validatePackageOutputManifest,
  verifyPackageOutput, streamedPackageFile, PACKAGE_OUTPUT_LIMITS, installedPackageIdentity} from '../scripts/package-output-artifact.mjs';

import {compareSelectedPackageOutput} from '../scripts/compare-selected-package-output.mjs';

const hash = raw => createHash('sha256').update(raw).digest('hex');
function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'atlas-package-output-'));
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  const write = (name, value) => { fs.mkdirSync(path.dirname(path.join(root, name)), {recursive: true});
    fs.writeFileSync(path.join(root, name), typeof value === 'string' ? value : JSON.stringify(value)); };
  const definition = {version: 1, inputs: ['.github/package-inputs.json','data/ownership-selection.json','package-lock.json'],
    optional_inputs: [], verification_paths: [], generated_outputs: ['dist/']};
  write('.github/package-inputs.json', definition); write('data/ownership-selection.json', {version: 1});
  write('package-lock.json', {lockfileVersion: 3});
  write('node_modules/example/index.js','original dependency body');
  const git = (...args) => execFileSync('git', ['-C', root, ...args], {encoding: 'utf8'}).trim();
  git('init','-q'); git('add','.'); git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixture');
  write('dist/client/atlas-geography.json', {original: true}); write('dist/client/assets/a.js', 'actual emitted bytes');
  write('dist/cloudflare/index.js', 'actual worker'); write('dist/cloudflare/wrangler.json', '{}');
  write('.cache/package-input-build.json', {version: 1, kind: 'cloudflare',
    preflight: {passed: true, errors: [], inputs: {head: git('rev-parse','HEAD')}},
    input_definition_sha256: hash(JSON.stringify(definition))});
  write('.cache/package-output-source.json', snapshotPackageOutputSource(root));
  return {root, write, git};
}

test('retains complete actual Cloudflare output and original input identity', t => {
  const {root, git} = fixture(t), manifest = createPackageOutputManifest(root);
  assert.equal(manifest.source.head, git('rev-parse','HEAD'));
  assert.equal(manifest.source.files.length, 3); assert.equal(manifest.output.files.length, 4);
  assert.equal(verifyPackageOutput(root, manifest), true);
  assert.match(manifest.semantics, /Original full/);
});

test('missing, extra, truncated and same-size substituted output cannot pass custody', t => {
  const {root, write} = fixture(t), manifest = createPackageOutputManifest(root);
  write('dist/client/assets/a.js', 'actual emittEd bytes');
  assert.throws(() => verifyPackageOutput(root, manifest), /output bytes differ/);
  write('dist/client/assets/a.js', 'actual emitted bytes');
  write('dist/client/extra.json', '{}');
  assert.throws(() => verifyPackageOutput(root, manifest), /output bytes differ/);
  fs.unlinkSync(path.join(root,'dist/client/extra.json'));
  fs.unlinkSync(path.join(root,'dist/cloudflare/index.js'));
  assert.throws(() => verifyPackageOutput(root, manifest), /Incomplete/);
});

test('ordinary ancestor and leaf requirements reject symlinks without modifying sentinels', t => {
  const {root} = fixture(t);
  fs.renameSync(path.join(root,'dist/client/assets'), path.join(root,'retained-assets'));
  fs.symlinkSync('../../retained-assets', path.join(root,'dist/client/assets'));
  const before = fs.readFileSync(path.join(root,'retained-assets/a.js'));
  assert.throws(() => inventoryPackageOutput(root), /links/);
  assert.throws(() => streamedPackageFile(root,'dist/client/assets/a.js'), /Nonordinary/);
  assert.deepEqual(fs.readFileSync(path.join(root,'retained-assets/a.js')), before);
});

test('malformed output rosters, duplicate paths, traversal and byte accounting fail closed', t => {
  const {root} = fixture(t), original = createPackageOutputManifest(root);
  for (const mutate of [
    value => value.output.files.push(value.output.files[0]),
    value => { value.output.files[0].path = 'dist/client/../../escape'; },
    value => { value.output.files[0].sha256 = '0'; },
    value => { value.output.bytes++; },
    value => { value.output.files[0].bytes = PACKAGE_OUTPUT_LIMITS.member_bytes + 1; },
    value => { value.source.files.push(value.source.files[0]); },
  ]) { const value = structuredClone(original); mutate(value); assert.throws(() => validatePackageOutputManifest(value)); }
});

test('failed, stale and assembled receipts cannot mint original full output', t => {
  const {root, write} = fixture(t), file = path.join(root,'.cache/package-input-build.json');
  const original = JSON.parse(fs.readFileSync(file));
  for (const mutate of [
    value => { value.preflight.passed = false; },
    value => { value.preflight.inputs.head = '0'.repeat(40); },
    value => { value.input_definition_sha256 = '0'.repeat(64); },
    value => { value.assembly = {mode:'retained'}; },
  ]) { const value = structuredClone(original); mutate(value); write('.cache/package-input-build.json', value);
    assert.throws(() => createPackageOutputManifest(root)); }
});

test('unknown output roots and oversized members fail before complete body allocation', t => {
  const {root, write} = fixture(t); write('dist/unknown', 'unexpected');
  assert.throws(() => inventoryPackageOutput(root), /roots/); fs.unlinkSync(path.join(root,'dist/unknown'));
  assert.throws(() => streamedPackageFile(root,'dist/client/assets/a.js',4), /admitted bytes/);
});

 test('pre-build source snapshot rejects dirty consumed inputs', t => {
  const {root, write} = fixture(t); write('data/ownership-selection.json', {changed:true});
  assert.throws(() => snapshotPackageOutputSource(root));
});

test('original-to-current admission covers base, programme, optional and directory identities', async t => {
  const {admitPackageOutputTransition} = await import('../scripts/package-output-artifact.mjs');
  const {root} = fixture(t), original = createPackageOutputManifest(root);
  original.source.selection = {version:1,base:'fixed',additive_release:{path:'coordination/engineering/old/release.json'}};
  const name='coordination/engineering/new/assembly/ledger.json';
  const current={...structuredClone(original.source),head:'f'.repeat(40)};
  current.selection.additive_release={path:'coordination/engineering/new/release.json'};
  current.definition.inputs.push(name);current.files.push({path:name,mode:'100644',oid:'1'.repeat(40)});
  assert.deepEqual(admitPackageOutputTransition(original,current,[name]).added_selected_inputs,[name]);
  for(const mutate of [
    value=>{value.selection.base='changed';},
    value=>{value.programme[0].oid='a'.repeat(40);},
    value=>{value.programme.push({path:'test/new.test.mjs',mode:'100644',oid:'b'.repeat(40)});},
    value=>{value.files.find(row=>row.path==='package-lock.json').oid='c'.repeat(40);},
    value=>{value.files=value.files.filter(row=>row.path!=='package-lock.json');},
    value=>{value.files.push({path:'public/new.json',mode:'100644',oid:'d'.repeat(40)});},
    value=>{value.files.at(-1).mode='120000';},
    value=>{value.definition.optional_inputs.push(name);},
    value=>{value.definition.inputs.push('coordination/engineering/new/');},
  ]){const candidate=structuredClone(current);mutate(candidate);assert.throws(()=>admitPackageOutputTransition(original,candidate,[name]));}
  assert.throws(()=>admitPackageOutputTransition(original,current,[]),/authenticated selected data/);
});

test('actual ZIP extraction preserves exact complete bytes and rejects hostile archives before publishing', t => {
  const {root} = fixture(t), manifest=createPackageOutputManifest(root);
  const manifestPath=path.join(root,'manifest.json');fs.writeFileSync(manifestPath,JSON.stringify(manifest)+'\n');
  const expected={};
  for(const row of manifest.output.files)expected[row.path]=fs.readFileSync(path.join(root,row.path)).toString('base64');
  expected['.cache/package-output-manifest.json']=fs.readFileSync(manifestPath).toString('base64');
  expected['.cache/package-input-build.json']=fs.readFileSync(path.join(root,'.cache/package-input-build.json')).toString('base64');
  const writer=`import sys,json,zipfile,base64,stat
rows=json.loads(sys.argv[2]);mode=sys.argv[3]
with zipfile.ZipFile(sys.argv[1],'w',compression=zipfile.ZIP_DEFLATED) as z:
 for name,body in rows.items():
  if mode=='missing' and name=='dist/client/assets/a.js': continue
  if mode=='symlink' and name=='dist/client/assets/a.js':
   info=zipfile.ZipInfo(name);info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(info,b'actual emitted bytes');continue
  z.writestr(name,base64.b64decode(body) if mode!='corrupt' or name!='dist/client/assets/a.js' else b'actual emittEd bytes')
 if mode=='extra': z.writestr('dist/client/extra.json',b'{}')
 if mode=='traversal': z.writestr('../sentinel',b'changed')
 if mode=='duplicate': z.writestr('dist/client/assets/a.js',b'actual emitted bytes')
`;
  const extractor=path.resolve('scripts/extract-package-output.py');
  fs.writeFileSync(path.join(root,'sentinel'),'original');
  for(const mode of ['valid','missing','symlink','corrupt','extra','traversal','duplicate']){
    const archive=path.join(root,mode+'.zip'),target=path.join(root,'extracted-'+mode);
    execFileSync('python3',['-c',writer,archive,JSON.stringify(expected),mode],{stdio:'pipe'});
    const args=[extractor,archive,manifestPath,target,hash(fs.readFileSync(archive))];
    if(mode==='valid'){
      execFileSync('python3',args,{stdio:'pipe'});assert.equal(verifyPackageOutput(target,manifest),true);
      assert.throws(()=>execFileSync('python3',args,{stdio:'pipe'}));
      assert.equal(verifyPackageOutput(target,manifest),true);
    }else {assert.throws(()=>execFileSync('python3',args,{stdio:'pipe'}));assert.equal(fs.existsSync(target),false);}
    assert.equal(fs.readFileSync(path.join(root,'sentinel'),'utf8'),'original');
  }
});

test('source snapshot rejects untracked declared-directory inputs',t=>{
  const f=fixture(t),definition=JSON.parse(fs.readFileSync(path.join(f.root,'.github/package-inputs.json')));
  definition.inputs=definition.inputs.filter(name=>name!=='data/ownership-selection.json');definition.inputs.push('data/');
  f.write('.github/package-inputs.json',definition);f.git('add','.github/package-inputs.json');
  f.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','directory');
  snapshotPackageOutputSource(f.root);
  f.write('data/untracked.json','unknown consumed input');
  assert.throws(()=>snapshotPackageOutputSource(f.root),/complete immutable inventory/);
});


test('installed identity detects dependency body substitution under unchanged lock metadata',t=>{
  const f=fixture(t),before=installedPackageIdentity(f.root);
  f.write('node_modules/example/index.js','modified dependency body');
  const after=installedPackageIdentity(f.root);
  assert.deepEqual(before.node,after.node);
  assert.notEqual(before.dependencies.sha256,after.dependencies.sha256);
});


test('full-output comparison permits only the explicitly preserved original source head',t=>{
  const full=fixture(t),assembled=fixture(t),originalHead='a'.repeat(40),currentHead='b'.repeat(40);
  const atlas=head=>({nativeContextInputStage:{current_execution:{source_head:head,runtime:{sha256:'c'.repeat(64)}},consumed_input_bytes:{encoded:42}},additiveRelease:{ledger:'current'}});
  full.write('dist/client/atlas-geography.json',atlas(currentHead));assembled.write('dist/client/atlas-geography.json',atlas(originalHead));
  const args={full:full.root,assembled:assembled.root,originalHead,currentHead};
  assert.equal(compareSelectedPackageOutput(args).exact_byte_files,3);
  const changed=atlas(originalHead);changed.nativeContextInputStage.consumed_input_bytes.encoded++;
  assembled.write('dist/client/atlas-geography.json',changed);
  assert.throws(()=>compareSelectedPackageOutput(args),/beyond preserved original/);
  assembled.write('dist/client/atlas-geography.json',atlas(originalHead));assembled.write('dist/client/assets/a.js','different bytes');
  assert.throws(()=>compareSelectedPackageOutput(args),/Output bytes differ/);
});


test('original installed input identity is captured before generated consumer caches',t=>{
  const f=fixture(t),before=JSON.parse(fs.readFileSync(path.join(f.root,'.cache/package-output-source.json'))).installed_runtime;
  f.write('node_modules/.vite/deps/generated-cache.js','generated consumer cache');
  const manifest=createPackageOutputManifest(f.root);
  assert.deepEqual(manifest.runtime.installed,before);
  assert.notDeepEqual(installedPackageIdentity(f.root),before,'Control establishes actual post-consumer tree differs');
});
