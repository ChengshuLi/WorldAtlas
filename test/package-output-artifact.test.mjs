import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {createPackageOutputManifest, snapshotPackageOutputSource, inventoryPackageOutput, validatePackageOutputManifest,
  verifyPackageOutput, streamedPackageFile, PACKAGE_OUTPUT_LIMITS, installedPackageIdentity, admitPackageOutputTransition} from '../scripts/package-output-artifact.mjs';

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


test('changed-declaration full-output comparison authenticates both sources and the actual current delta',t=>{
  const source=fixture(t),full=fixture(t),assembled=fixture(t);
  const declaration='.github/package-inputs.json',added='coordination/engineering/next/selected.json';
  const definition=JSON.parse(fs.readFileSync(path.join(source.root,declaration)));
  const commit=()=>source.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','selection');
  source.write('data/ownership-selection.json',{version:1,additive_release:{state:'original'}});
  source.git('add','data/ownership-selection.json');commit();
  const originalHead=source.git('rev-parse','HEAD');
  const descriptor=head=>{
    const raw=execFileSync('git',['-C',source.root,'show',head+':'+declaration]);
    return {path:declaration,mode:'100644',bytes:raw.length,sha256:hash(raw),
      git_blob:createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex')};
  };
  const atlas=(head,pin)=>({nativeContextInputStage:{current_execution:{source_head:head,
    runtime:{sha256:'c'.repeat(64)},full_code_closure:[pin,{path:'scripts/invariant.mjs',sha256:'d'.repeat(64)}]},
    consumed_input_bytes:{encoded:42}},additiveRelease:{ledger:'current'}});
  source.write('.cache/package-input-build.json',{version:1,kind:'cloudflare',input_definition_sha256:descriptor(originalHead).sha256,
    preflight:{passed:true,errors:[],inputs:{head:originalHead}}});
  source.write('.cache/package-output-source.json',snapshotPackageOutputSource(source.root));
  const manifest=createPackageOutputManifest(source.root),originalManifest=path.join(source.root,'.cache/original.json');
  source.write('.cache/original.json',manifest);const manifestSha=hash(fs.readFileSync(originalManifest));
  source.write(declaration,{...definition,inputs:[...definition.inputs,added]});source.write(added,{selected:true});
  source.write('data/ownership-selection.json',{version:1,additive_release:{state:'current'}});
  source.git('add',declaration,added,'data/ownership-selection.json');commit();
  const currentHead=source.git('rev-parse','HEAD'),current=snapshotPackageOutputSource(source.root);
  const pin={commit:currentHead,path:added,mode:'100644',git_blob_oid:source.git('rev-parse','HEAD:'+added),
    bytes:fs.statSync(path.join(source.root,added)).size,sha256:hash(fs.readFileSync(path.join(source.root,added))),whole_body_consumed:true};
  const receipt={version:1,kind:'cloudflare',input_definition_sha256:descriptor(currentHead).sha256,
    preflight:{passed:true,errors:[],inputs:{head:currentHead}},assembly:{kind:'retained-original-output-plus-current-additive',
      origin:{head:originalHead},original_manifest_sha256:manifestSha,
      current_execution:{source_commit:currentHead,source_tree:current.tree},
      original_base_context_retained:true,base_restoration_invoked:false,invariant_build_invoked:false,
      transition:admitPackageOutputTransition(manifest,current,[added]),current_selected_inputs:[pin]}};
  const originalAtlas=atlas(originalHead,descriptor(originalHead)),currentAtlas=atlas(currentHead,descriptor(currentHead));
  const reset=()=>{full.write('dist/client/atlas-geography.json',currentAtlas);
    assembled.write('dist/client/atlas-geography.json',originalAtlas);assembled.write('.cache/package-input-build.json',receipt);};
  const args={full:full.root,assembled:assembled.root,originalHead,currentHead,sourceRoot:source.root,originalManifest};
  reset();assert.equal(compareSelectedPackageOutput(args).exact_byte_files,3);
  for(const mutate of [
    value=>value.nativeContextInputStage.consumed_input_bytes.encoded++,
    value=>value.nativeContextInputStage.current_execution.runtime.sha256='e'.repeat(64),
    value=>value.nativeContextInputStage.current_execution.full_code_closure[1].sha256='e'.repeat(64),
    value=>value.nativeContextInputStage.current_execution.full_code_closure[0].sha256='e'.repeat(64),
    value=>value.nativeContextInputStage.current_execution.full_code_closure.shift(),
    value=>value.nativeContextInputStage.current_execution.full_code_closure.push(value.nativeContextInputStage.current_execution.full_code_closure[0])]){
    reset();const changed=structuredClone(originalAtlas);mutate(changed);assembled.write('dist/client/atlas-geography.json',changed);
    assert.throws(()=>compareSelectedPackageOutput(args));
  }
  for(const mutate of [value=>value.assembly.original_manifest_sha256='0'.repeat(64),
    value=>value.assembly.current_selected_inputs[0].git_blob_oid='0'.repeat(40),
    value=>value.assembly.current_selected_inputs[0].bytes++,
    value=>value.assembly.current_selected_inputs[0].sha256='0'.repeat(64),
    value=>value.assembly.current_selected_inputs[0].whole_body_consumed=false,
    value=>value.assembly.current_selected_inputs=[],value=>value.assembly.transition.added_selected_inputs=[],
    value=>value.assembly.current_execution.source_tree='0'.repeat(40)]){
    reset();const changed=structuredClone(receipt);mutate(changed);assembled.write('.cache/package-input-build.json',changed);
    assert.throws(()=>compareSelectedPackageOutput(args));
  }
  reset();const alteredManifest=structuredClone(manifest);
  alteredManifest.source.definition.inputs.push('coordination/engineering/forged/source.json');
  source.write('.cache/original.json',alteredManifest);
  const alteredReceipt=structuredClone(receipt);alteredReceipt.assembly.original_manifest_sha256=hash(fs.readFileSync(originalManifest));
  assembled.write('.cache/package-input-build.json',alteredReceipt);
  assert.throws(()=>compareSelectedPackageOutput(args),/immutable Git/);
  source.write('.cache/original.json',manifest);
  reset();source.write('scripts/unrelated.mjs','export const changed = true;');source.git('add','scripts/unrelated.mjs');commit();
  const changedHead=source.git('rev-parse','HEAD'),changedFull=structuredClone(currentAtlas),changedReceipt=structuredClone(receipt);
  changedFull.nativeContextInputStage.current_execution.source_head=changedHead;
  changedReceipt.preflight.inputs.head=changedHead;changedReceipt.assembly.current_execution.source_commit=changedHead;
  changedReceipt.assembly.current_execution.source_tree=source.git('rev-parse','HEAD^{tree}');
  changedReceipt.assembly.transition.current_head=changedHead;
  full.write('dist/client/atlas-geography.json',changedFull);assembled.write('.cache/package-input-build.json',changedReceipt);
  assert.throws(()=>compareSelectedPackageOutput({...args,currentHead:changedHead}),/programme changed/);
  reset();assembled.write('dist/client/assets/a.js','different bytes');
  assert.throws(()=>compareSelectedPackageOutput(args),/Output bytes differ/);
});


test('original installed input identity is captured before generated consumer caches',t=>{
  const f=fixture(t),before=JSON.parse(fs.readFileSync(path.join(f.root,'.cache/package-output-source.json'))).installed_runtime;
  f.write('node_modules/.vite/deps/generated-cache.js','generated consumer cache');
  const manifest=createPackageOutputManifest(f.root);
  assert.deepEqual(manifest.runtime.installed,before);
  assert.notDeepEqual(installedPackageIdentity(f.root),before,'Control establishes actual post-consumer tree differs');
});
