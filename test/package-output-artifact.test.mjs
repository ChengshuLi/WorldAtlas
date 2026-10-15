import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {createPackageOutputManifest, snapshotPackageOutputSource, inventoryPackageOutput, validatePackageOutputManifest,
  verifyPackageOutput, streamedPackageFile, installedPackageIdentity, admitPackageInputTransition, admitPackageOutputTransition, committedPackageInputs, committedPackageProducer, packageWorkflowExecution} from '../scripts/package-output-artifact.mjs';

import {compareSelectedPackageOutput,compareSelectedPackageReadback,normalizeDeclarationReadAccounting} from '../scripts/compare-selected-package-output.mjs';

const hash = raw => createHash('sha256').update(raw).digest('hex');
function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'atlas-package-output-'));
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  const write = (name, value) => { fs.mkdirSync(path.dirname(path.join(root, name)), {recursive: true});
    fs.writeFileSync(path.join(root, name), typeof value === 'string' ? value : JSON.stringify(value)); };
  const definition = {version: 1, inputs: ['.github/package-inputs.json','data/ownership-selection.json','package-lock.json','scripts/package-output-artifact.mjs','scripts/package-node-runtime.mjs'],
    optional_inputs: [], verification_paths: [], generated_outputs: ['dist/']};
  write('.github/package-inputs.json', definition); write('data/ownership-selection.json', {version: 1});
  write('package-lock.json', {lockfileVersion: 3});
  write('scripts/package-output-artifact.mjs','synthetic capture writer');
  write('scripts/package-node-runtime.mjs','synthetic runtime inventory');
  write('.github/workflows/merge-integration-checks.yml', 'genuine package build and immediate capture');
  write('.github/workflows/worker-merge.yml','genuine final-worker package producer');
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
  assert.equal(manifest.source.files.length, 5); assert.equal(manifest.output.files.length, 4);
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
    value => { value.output.files[0].bytes = Number.MAX_SAFE_INTEGER + 1; },
    value => { value.source.files.push(value.source.files[0]); },
    value => { value.source.producer.workflows[0].oid='broken'; },
    value => { delete value.source.producer.workflows; },
    value => { value.source.producer.kind='legacy'; },
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

test('unknown output roots fail before complete custody', t => {
  const {root, write} = fixture(t); write('dist/unknown', 'unexpected');
  assert.throws(() => inventoryPackageOutput(root), /roots/); fs.unlinkSync(path.join(root,'dist/unknown'));
});

 test('pre-build source snapshot rejects dirty consumed inputs', t => {
  const {root, write} = fixture(t); write('data/ownership-selection.json', {changed:true});
  assert.throws(() => snapshotPackageOutputSource(root));
});

test('original-to-current admission covers base, producer workflow, optional and directory identities', async t => {
  const {admitPackageOutputTransition} = await import('../scripts/package-output-artifact.mjs');
  const {root} = fixture(t), original = createPackageOutputManifest(root);
  original.source.selection = {version:1,base:'fixed',additive_release:{path:'coordination/engineering/old/release.json'}};
  const name='coordination/engineering/new/assembly/ledger.json';
  const current={...structuredClone(original.source),head:'f'.repeat(40)};
  current.selection.additive_release={path:'coordination/engineering/new/release.json'};
  current.definition.inputs.push(name);current.files.push({path:name,mode:'100644',oid:'1'.repeat(40)});
  assert.deepEqual(admitPackageOutputTransition(original,current).added_selected_inputs,[name]);
  for(const mutate of [
    value=>{value.selection.base='changed';},
    value=>{value.producer.workflows[0].oid='a'.repeat(40);},
    value=>{delete value.producer;},
    value=>{value.files.find(row=>row.path==='package-lock.json').oid='c'.repeat(40);},
    value=>{value.files=value.files.filter(row=>row.path!=='package-lock.json');},
    value=>{value.files.push({path:'public/new.json',mode:'100644',oid:'d'.repeat(40)});},
    value=>{value.files.at(-1).mode='120000';},
    value=>{value.definition.optional_inputs.push(name);},
    value=>{value.definition.inputs.push('coordination/engineering/new/');},
  ]){const candidate=structuredClone(current);mutate(candidate);assert.throws(()=>admitPackageOutputTransition(original,candidate));}
  const absent=structuredClone(current);absent.definition.inputs.push('coordination/engineering/new/absent.json');
  assert.throws(()=>admitPackageOutputTransition(original,absent),/New selected declaration is absent/);
  const executable=structuredClone(current);executable.definition.inputs.push('coordination/engineering/new/helper.mjs');
  executable.files.push({path:'coordination/engineering/new/helper.mjs',mode:'100644',oid:'e'.repeat(40)});
  assert.throws(()=>admitPackageOutputTransition(original,executable),/not unchanged on trusted base/);
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
  if mode=='missing-manifest' and name=='.cache/package-output-manifest.json': continue
  if mode=='manifest-symlink' and name=='.cache/package-output-manifest.json':
   info=zipfile.ZipInfo(name);info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(info,base64.b64decode(body));continue
  if mode=='symlink' and name=='dist/client/assets/a.js':
   info=zipfile.ZipInfo(name);info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(info,b'actual emitted bytes');continue
  z.writestr(name,base64.b64decode(body) if mode!='corrupt' or name!='dist/client/assets/a.js' else b'actual emittEd bytes')
 if mode=='extra': z.writestr('dist/client/extra.json',b'{}')
 if mode=='traversal': z.writestr('../sentinel',b'changed')
 if mode=='duplicate': z.writestr('dist/client/assets/a.js',b'actual emitted bytes')
 if mode=='duplicate-manifest': z.writestr('.cache/package-output-manifest.json',base64.b64decode(rows['.cache/package-output-manifest.json']))
`;
  const extractor=path.resolve('scripts/extract-package-output.py');
  fs.writeFileSync(path.join(root,'sentinel'),'original');
  for(const mode of ['valid','missing','symlink','corrupt','extra','traversal','duplicate','missing-manifest','manifest-symlink','duplicate-manifest']){
    const archive=path.join(root,mode+'.zip'),target=path.join(root,'extracted-'+mode);
    execFileSync('python3',['-c',writer,archive,JSON.stringify(expected),mode],{stdio:'pipe'});
    const args=[extractor,archive,target,hash(fs.readFileSync(archive)),hash(fs.readFileSync(manifestPath)),String(fs.statSync(manifestPath).size)];
    if(mode==='valid'){
      execFileSync('python3',args,{stdio:'pipe'});assert.equal(verifyPackageOutput(target,manifest),true);
      assert.throws(()=>execFileSync('python3',args,{stdio:'pipe'}));
      assert.equal(verifyPackageOutput(target,manifest),true);
    }else {assert.throws(()=>execFileSync('python3',args,{stdio:'pipe'}));assert.equal(fs.existsSync(target),false);}
    assert.equal(fs.readFileSync(path.join(root,'sentinel'),'utf8'),'original');
  }
  const valid=path.join(root,'valid.zip'),archiveRaw=fs.readFileSync(valid),manifestRaw=fs.readFileSync(manifestPath);
  // The real CLI must reject both independent identities before creating output.
  for(const [archiveHash,manifestHash,manifestBytes]of [
    ['0'.repeat(64),hash(manifestRaw),manifestRaw.length],
    [hash(archiveRaw),'0'.repeat(64),manifestRaw.length],
    [hash(archiveRaw),hash(manifestRaw),manifestRaw.length+1],
  ]){
    const target=path.join(root,'bad-authority');
    assert.throws(()=>execFileSync('python3',[extractor,valid,target,archiveHash,manifestHash,String(manifestBytes)],{stdio:'pipe'}));
    assert.equal(fs.existsSync(target),false);
  }
  const probe=`import hashlib,os,pathlib,runpy,sys,zipfile
extractor,archive,target,archive_hash,manifest_hash,manifest_bytes,mode=sys.argv[1:]
module=runpy.run_path(extractor)
original=pathlib.Path(archive).read_bytes()
original_zip=zipfile.ZipFile
original_hash=hashlib.sha256
observations=[]
class ObservedHash:
 def __init__(self,body=b''):
  self.hash=original_hash(body);self.bytes=len(body);observations.append(self)
 def update(self,body): self.bytes+=len(body);self.hash.update(body)
 def hexdigest(self): return self.hash.hexdigest()
def write_same_byte():
 before=os.stat(archive)
 with open(archive,'r+b') as output:
  first=output.read(1);output.seek(0);output.write(first)
 os.utime(archive,ns=(before.st_atime_ns,before.st_mtime_ns))
class AlteredZip(original_zip):
 def __init__(self,*args,**kwargs):
  if mode=='replace-after-hash':
   os.rename(archive,archive+'.retained');pathlib.Path(archive).write_bytes(original)
  elif mode=='rewrite-after-hash': write_same_byte()
  self.mutated=False
  super().__init__(*args,**kwargs)
 def open(self,name,*args,**kwargs):
  result=super().open(name,*args,**kwargs)
  member=name.filename if hasattr(name,'filename') else name
  if mode=='write-during-extraction' and member.startswith('dist/') and not self.mutated:
   self.mutated=True;write_same_byte()
  return result
hashlib.sha256=ObservedHash
zipfile.ZipFile=AlteredZip
try:
 result=module['extract'](archive,target,archive_hash,manifest_hash,manifest_bytes)
 assert mode=='unchanged', 'Mutation passed consumption'
 assert result['files']>0
except ValueError as error:
 assert mode!='unchanged', str(error)
 assert 'Archive identity changed during consumption' in str(error), str(error)
 assert not pathlib.Path(target).exists(), 'Failed consumption retained output'
assert pathlib.Path(archive).read_bytes()==original
if mode=='replace-after-hash': assert pathlib.Path(archive+'.retained').read_bytes()==original
passes=[item for item in observations if item.hexdigest()==archive_hash]
assert len(passes)==1 and passes[0].bytes==len(original), 'Archive was not authenticated exactly once'
print(mode+': one authenticated archive pass; mutation/cleanup controls passed')
`;
  for(const mode of ['unchanged','replace-after-hash','rewrite-after-hash','write-during-extraction']){
    const archive=path.join(root,mode+'.zip'),target=path.join(root,mode+'-output');fs.writeFileSync(archive,archiveRaw);
    const result=execFileSync('python3',['-I','-S','-B','-c',probe,extractor,archive,target,hash(archiveRaw),hash(manifestRaw),String(manifestRaw.length),mode],{encoding:'utf8'});
    assert.match(result,/one authenticated archive pass/);
    if(mode==='unchanged')assert.equal(verifyPackageOutput(target,manifest),true);
    else assert.equal(fs.existsSync(target),false);
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


for(const retainedCode of [false,true])test('changed-declaration full/readback comparison authenticates '+(retainedCode?'retained typed code':'inert data')+' and the actual current delta',t=>{
  const source=fixture(t),full=fixture(t),assembled=fixture(t);
  const declaration='.github/package-inputs.json',added=retainedCode?'scripts/accepted-source.py':'coordination/engineering/next/selected.json';
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
    consumed_input_bytes:{encoded:42+pin.bytes,decoded:80}},additiveRelease:{ledger:'current'}});
  source.write('.cache/package-input-build.json',{version:1,kind:'cloudflare',input_definition_sha256:descriptor(originalHead).sha256,
    preflight:{passed:true,errors:[],inputs:{head:originalHead}}});
  source.write('.cache/package-output-source.json',snapshotPackageOutputSource(source.root));
  const manifest=createPackageOutputManifest(source.root),originalManifest=path.join(source.root,'.cache/original.json');
  source.write('.cache/original.json',manifest);const manifestSha=hash(fs.readFileSync(originalManifest));
  let trustedBase,acceptedInputs;
  if(retainedCode){
    source.write(added,'accepted source code');source.git('add',added);commit();trustedBase=source.git('rev-parse','HEAD');
    acceptedInputs={commit:trustedBase,files:[{path:added,mode:'100644',oid:source.git('rev-parse','HEAD:'+added),bytes:fs.statSync(path.join(source.root,added)).size}]};
  }
  source.write(declaration,{...definition,inputs:[...definition.inputs,added]});if(!retainedCode)source.write(added,{selected:true});
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
      transition:admitPackageOutputTransition(manifest,current,{acceptedInputs,typedInputs:[pin]}),current_selected_inputs:[pin]}};
  const originalAtlas=atlas(originalHead,descriptor(originalHead)),currentAtlas=atlas(currentHead,descriptor(currentHead));
  const reset=()=>{full.write('dist/client/atlas-geography.json',currentAtlas);
    assembled.write('dist/client/atlas-geography.json',originalAtlas);assembled.write('.cache/package-input-build.json',receipt);};
  const args={full:full.root,assembled:assembled.root,originalHead,currentHead,sourceRoot:source.root,originalManifest,trustedBase};
  reset();assert.equal(compareSelectedPackageOutput(args).exact_byte_files,3);
  if(retainedCode){
    assert.throws(()=>compareSelectedPackageOutput({...args,trustedBase:undefined}),/Exact trusted comparison base/);
    assert.throws(()=>compareSelectedPackageOutput({...args,trustedBase:originalHead}),/Ordinary unchanged trusted comparison input/);
    const forged=structuredClone(receipt);forged.assembly.transition.accepted_selected_inputs.commit=currentHead;
    assembled.write('.cache/package-input-build.json',forged);
    assert.throws(()=>compareSelectedPackageOutput(args),/Assembly delta transition differs/);reset();
  }
  const fullInventory=inventoryPackageOutput(full.root).files;
  const client=fullInventory.filter(row=>row.path.startsWith('dist/client/')).map(row=>({...row,path:row.path.slice('dist/client/'.length)}));
  const readback={version:1,kind:'ordinary-cloudflare-built-output-readback',head:currentHead,
    static_assets:{files:client,count:client.length,bytes:client.reduce((sum,row)=>sum+row.bytes,0)},
    worker_bundle_files:fullInventory.filter(row=>row.path.startsWith('dist/cloudflare/')).map(row=>({...row,path:row.path.slice('dist/cloudflare/'.length)})),
    nativeContextInputStage:structuredClone(currentAtlas.nativeContextInputStage)};
  assert.equal(compareSelectedPackageReadback({...args,readback}).atlas_exact_after_authenticated_provenance,true);
  if(retainedCode)assert.throws(()=>compareSelectedPackageReadback({...args,readback,trustedBase:undefined}),/Exact trusted comparison base/);
  for(const mutate of [value=>value.head=originalHead,value=>value.static_assets.files.pop(),
    value=>value.static_assets.files.push(value.static_assets.files[0]),value=>value.static_assets.files[0].sha256='0'.repeat(64),
    value=>value.worker_bundle_files[0].bytes++,value=>value.nativeContextInputStage.consumed_input_bytes.encoded++,
    value=>value.nativeContextInputStage.consumed_input_bytes.decoded++,
    value=>value.static_assets.files[0].path='../escape',value=>value.static_assets.bytes++]){
    const changed=structuredClone(readback);mutate(changed);assert.throws(()=>compareSelectedPackageReadback({...args,readback:changed}));
  }
  const unknownField=structuredClone(originalAtlas);unknownField.unreported_extra_field='must still fail exact full atlas hash';
  assembled.write('dist/client/atlas-geography.json',unknownField);
  assert.throws(()=>compareSelectedPackageReadback({...args,readback}),/Complete atlas bytes/);
  reset();

  for(const mutate of [
    value=>value.nativeContextInputStage.consumed_input_bytes.encoded++,
    value=>value.nativeContextInputStage.consumed_input_bytes.decoded++,
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
  reset();source.write('.github/workflows/merge-integration-checks.yml','changed build command');source.git('add','.github/workflows/merge-integration-checks.yml');commit();
  const changedHead=source.git('rev-parse','HEAD'),changedFull=structuredClone(currentAtlas),changedReceipt=structuredClone(receipt);
  changedFull.nativeContextInputStage.current_execution.source_head=changedHead;
  changedReceipt.preflight.inputs.head=changedHead;changedReceipt.assembly.current_execution.source_commit=changedHead;
  changedReceipt.assembly.current_execution.source_tree=source.git('rev-parse','HEAD^{tree}');
  changedReceipt.assembly.transition.current_head=changedHead;
  full.write('dist/client/atlas-geography.json',changedFull);assembled.write('.cache/package-input-build.json',changedReceipt);
  assert.throws(()=>compareSelectedPackageOutput({...args,currentHead:changedHead}),/producer workflow required/);
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


test('installed identity admits ordinary scoped and punctuated filenames without weakening package paths', t => {
  const f=fixture(t);
  for (const name of ['@scope/package/index.js','@scope/package/LICENSE (MIT).txt',
    'example/Unicode-é+file.js','example/file#?.json']) f.write('node_modules/'+name, name);
  const before=installedPackageIdentity(f.root);
  assert.equal(before.dependencies.files, 5);
  f.write('node_modules/@scope/package/index.js', 'changed scoped dependency');
  assert.notEqual(installedPackageIdentity(f.root).dependencies.sha256,before.dependencies.sha256);
  assert.throws(()=>streamedPackageFile(f.root,'node_modules/@scope/package/index.js'),/Safe ordinary package path/);
  fs.symlinkSync('/tmp',path.join(f.root,'node_modules/escape'));
  assert.throws(()=>installedPackageIdentity(f.root),/link escapes/);
});


test('declaration accounting preserves actual observations and every nondeclaration byte', () => {
  const original={consumed_input_bytes:{encoded:321352440,decoded:192828074}};
  const current={consumed_input_bytes:{encoded:321356198,decoded:192828074}};
  const a={bytes:92514},b={bytes:96272};
  const observed=structuredClone(current),result=normalizeDeclarationReadAccounting(current,original,b,a);
  assert.deepEqual(current,observed);assert.deepEqual(result.normalized,original);
  assert.equal(result.accounting.unchanged_other_encoded_bytes,321259926);
  for (const delta of [-1,1,3758]) {
    const wrong=structuredClone(current);wrong.consumed_input_bytes.encoded+=delta;
    assert.throws(()=>normalizeDeclarationReadAccounting(wrong,original,b,a),/Consumed bytes/);
  }
  for (const descriptor of [{bytes:0},{bytes:96273},{bytes:96271},{bytes:0.5}])
    assert.throws(()=>normalizeDeclarationReadAccounting(current,original,descriptor,a));
  const changedDecoded=structuredClone(current);changedDecoded.consumed_input_bytes.decoded++;
  assert.notDeepEqual(normalizeDeclarationReadAccounting(changedDecoded,original,b,a).normalized,original);
});

test('versioned runtime evidence requires complete bound inventories before summary equality',async t=>{
  const {installedPackageDifferences,validateInstalledPackageIdentity}=await import('../scripts/package-output-artifact.mjs');
  const f=fixture(t),identity=installedPackageIdentity(f.root);
  assert.equal(identity.version,2);assert.equal(validateInstalledPackageIdentity(identity),identity);
  assert.deepEqual(installedPackageDifferences(identity,structuredClone(identity)),[]);
  const legacy={node:identity.node,dependencies:{files:identity.dependencies.files,sha256:identity.dependencies.sha256},python:null};
  assert.equal(installedPackageDifferences(legacy,identity)[0].component,'identity-policy');
  assert.throws(()=>installedPackageDifferences({...legacy,version:2},identity));
  for(const mutate of [
    value=>delete value.dependencies.inventory,
    value=>value.dependencies.inventory[0].sha256='f'.repeat(64),
    value=>value.dependencies.inventory.push(structuredClone(value.dependencies.inventory[0])),
    value=>value.dependencies.files++,
    value=>delete value.python,
  ]){const changed=structuredClone(identity);mutate(changed);assert.throws(()=>installedPackageDifferences(changed,identity));}
  f.write('node_modules/example/index.js','actually changed execution bytes');
  const current=installedPackageIdentity(f.root),diff=installedPackageDifferences(identity,current);
  assert.deepEqual(diff.map(row=>row.component),['dependencies']);
  assert.deepEqual(diff[0].changed_files,['node_modules/example/index.js']);
});

test('scientific identity roots follow every exact declared requirement',async t=>{
  const {declaredPackagePythonRoots}=await import('../scripts/package-output-artifact.mjs');
  const f=fixture(t);assert.deepEqual(declaredPackagePythonRoots(f.root),[]);
  f.write('requirements.txt','# scientific roots\nnumpy==2.3.5\nshapely==2.1.2\npyproj==3.7.2\nrasterio==1.4.3\nscipy==1.17.0\n');
  assert.deepEqual(declaredPackagePythonRoots(f.root).map(row=>row.name),['numpy','shapely','pyproj','rasterio','scipy']);
  for(const unknown of ['numpy>=2','-r elsewhere.txt','package @ https://example.invalid/file']){
    f.write('requirements.txt',unknown);assert.throws(()=>declaredPackagePythonRoots(f.root),/Exact pinned/);
  }
});


test('parent independently binds Python executable before any consumer identity process',async t=>{
  const {resolvePackagePythonExecutable}=await import('../scripts/package-output-artifact.mjs');
  const observed=resolvePackagePythonExecutable();assert.equal(resolvePackagePythonExecutable(observed.sha256).executable,observed.executable);
  const f=fixture(t),bin=path.join(f.root,'bin'),marker=path.join(f.root,'forged-executable-ran');fs.mkdirSync(bin);
  fs.writeFileSync(path.join(bin,'python3'),'#!/bin/sh\necho forged > '+JSON.stringify(marker)+'\n',{mode:0o755});
  const before=process.env.PATH;process.env.PATH=bin;
  try{assert.throws(()=>resolvePackagePythonExecutable(observed.sha256),/differs from authenticated original/);assert.equal(fs.existsSync(marker),false);}
  finally{process.env.PATH=before;}
});

test('assembly admits original custody and installed bytes before scientific imports',()=>{
  const source=fs.readFileSync(new URL('../scripts/assemble-selected-package.mjs',import.meta.url),'utf8');
  const custody=source.indexOf('const original=await authenticateOriginalPackageOutput('),identity=source.indexOf('const installed=installedPackageIdentity('),admission=source.indexOf('if(differences.length)recordAndRequireRuntime();'),probe=source.indexOf('const runtime=inspectPackageRuntime(root)');
  assert.ok(custody>0&&identity>custody&&admission>identity&&probe>admission);
  assert.match(source,/expectedParser:manifest\.runtime\.installed\.python\.parser/);
  assert.match(source,/expectedExecutable:manifest\.runtime\.installed\.python\.executable_sha256/);
  assert.ok(source.indexOf('if(runtime.errors.length)')<source.indexOf('const actualRuntime='));
});

test('declared build image rejects real producer changes but ignores incidental programmes', t => {
  const f=fixture(t), commit=()=>{f.git('add','.');f.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','change');};
  const definition=JSON.parse(fs.readFileSync(path.join(f.root,'.github/package-inputs.json')));
  const inputs={'scripts/build-cloudflare.mjs':'actual builder','src/main.js':'actual UI',
    'hosted/cloudflare-worker.js':'actual worker','package.json':'actual npm scripts',
    'public/input.json':'actual asset'};
  for(const [name,raw]of Object.entries(inputs)){definition.inputs.push(name);f.write(name,raw);}
  f.write('.github/package-inputs.json',definition);
  f.write('data/ownership-selection.json',{version:1,additive_release:{path:'coordination/engineering/base/release.json'}});
  commit();
  f.write('.cache/package-input-build.json',{version:1,kind:'cloudflare',preflight:{passed:true,errors:[],inputs:{head:f.git('rev-parse','HEAD')}},
    input_definition_sha256:hash(JSON.stringify(definition))});
  f.write('.cache/package-output-source.json',snapshotPackageOutputSource(f.root));
  const original=createPackageOutputManifest(f.root);
  const current=()=>({...original.source,head:f.git('rev-parse','HEAD'),
    files:committedPackageInputs(f.root,definition),producer:committedPackageProducer(f.root)});
  const incidental=['test/new.test.mjs','scripts/read-only-observer.mjs','.github/workflows/unrelated.yml','README.md'];
  for(const name of incidental){
    f.write(name,'observer version one');commit();assert.doesNotThrow(()=>admitPackageOutputTransition(original,current()),name+' added');
    f.write(name,'observer version two');commit();assert.doesNotThrow(()=>admitPackageOutputTransition(original,current()),name+' changed');
    fs.unlinkSync(path.join(f.root,name));commit();assert.doesNotThrow(()=>admitPackageOutputTransition(original,current()),name+' deleted');
  }
  for(const name of [...Object.keys(inputs),'package-lock.json','scripts/package-output-artifact.mjs','scripts/package-node-runtime.mjs','.github/workflows/merge-integration-checks.yml','.github/workflows/worker-merge.yml']){
    const prior=fs.readFileSync(path.join(f.root,name));f.write(name,'changed consumed bytes');commit();
    assert.throws(()=>admitPackageOutputTransition(original,current()),/input changed|producer workflow required/,name);
    f.write(name,prior.toString());commit();
  }
  for(const name of ['scripts/package-output-artifact.mjs','scripts/package-node-runtime.mjs']){
    const prior=fs.readFileSync(path.join(f.root,name),'utf8');f.write(name,'dirty capture code');
    assert.throws(()=>snapshotPackageOutputSource(f.root),/complete immutable inventory/,name+' dirty');
    f.write(name,prior);
  }
  const legacy=structuredClone(original);delete legacy.source.producer;
  legacy.source.programme=[{path:'scripts/old-observer.mjs',mode:'100644',oid:'a'.repeat(40)}];
  assert.doesNotThrow(()=>validatePackageOutputManifest(legacy),'Legacy remains honest retained history');
  assert.throws(()=>admitPackageOutputTransition(legacy,current()),/Immediate original build capture/);
});

test('final queue captures genuine build output immediately and uploads only after checks', () => {
  const workflow=fs.readFileSync(new URL('../.github/workflows/worker-merge.yml',import.meta.url),'utf8');
  const steps=workflow.split(/^      - name: /m).slice(1).map(raw=>({name:raw.split('\n')[0],raw}));
  const at=steps.findIndex(step=>step.name==='Build the combined application once before asset-dependent tests');
  assert(at>=0,'The actual final package build remains required');
  assert.equal(steps[at+1].name,'Inventory original final-worker package output',
    'No observer/test may intervene before original capture');
  const end=steps.findIndex(step=>step.name==='Retain original final-worker package output');
  for(const name of ['Install browser dependencies only for tests that use Playwright',
    'Read back qualified native build outputs when selected',
    'Test applicable combined-tree invariants without publishing or live imports']){
    const control=steps.findIndex(step=>step.name===name);
    assert(control>at+1&&control<end,name+' must run between original capture and upload');
  }
  assert.match(steps[end].raw,/if: success\(\)/,'Failed checks cannot upload an original');
});

test('capture logs actual workflow-file commit and ref independently of source checkout',()=>{
  const workflow='.github/workflows/merge-integration-checks.yml';
  const env={GITHUB_REPOSITORY:'ChengshuLi/WorldAtlas',GITHUB_WORKFLOW_SHA:'b'.repeat(40),
    GITHUB_SHA:'a'.repeat(40),GITHUB_WORKFLOW_REF:'ChengshuLi/WorldAtlas/'+workflow+'@refs/pull/17/merge',
    GITHUB_REF:'refs/pull/17/merge',GITHUB_EVENT_NAME:'pull_request'};
  assert.deepEqual(packageWorkflowExecution(env),{sha:'b'.repeat(40),path:workflow,ref:env.GITHUB_REF});
  assert.equal(packageWorkflowExecution({}),undefined,'Local historical capture grants no workflow provenance');
  for(const patch of [{GITHUB_WORKFLOW_SHA:'main'},{GITHUB_WORKFLOW_REF:'other/repo/'+workflow+'@refs/pull/17/merge'},
    {GITHUB_EVENT_NAME:'push'},{GITHUB_REF:'refs/heads/main'},
    {GITHUB_WORKFLOW_REF:'ChengshuLi/WorldAtlas/.github/workflows/other.yml@refs/pull/17/merge'}])
    assert.throws(()=>packageWorkflowExecution({...env,...patch}));
  const worker='.github/workflows/worker-merge.yml';
  assert.deepEqual(packageWorkflowExecution({...env,GITHUB_WORKFLOW_REF:'ChengshuLi/WorldAtlas/'+worker+'@refs/heads/main',
    GITHUB_REF:'refs/heads/main',GITHUB_EVENT_NAME:'workflow_dispatch'}),{sha:'b'.repeat(40),path:worker,ref:'refs/heads/main'});
});


// Same32 appended paths as accepted b73 versus the actual1939 trusted baseline.
// Contents below are bounded synthetic controls, not replayed scientific data.
const retainedAssemblyAdditions = [
  "coordination/engineering/myanmar-adm3-current-cells-20261014/unresolved-evidence-001/coastal-candidate-cell-preparation-001/kawthoung/parent-sid-narrow/candidate-native-patch.json",
  "coordination/engineering/myanmar-adm3-current-cells-20261014/unresolved-evidence-001/coastal1928-physical-001/whole-target-support.json",
  "coordination/engineering/myanmar-adm3-current-cells-20261014/unresolved-evidence-001/kawthoung/original-stage-inputs.json",
  "coordination/engineering/myanmar-adm3-current-cells-20261014/unresolved-evidence-001/tanintharyi6-authority-001/authority-binding.json",
  "coordination/engineering/myanmar-adm3-current-cells-20261014/unresolved-evidence-001/tanintharyi6-authority-001/original-rule-preimage.json",
  "coordination/engineering/myanmar-adm3-current-cells-20261014/unresolved-evidence-001/tanintharyi6-source-preparation/candidate-native-patch.json",
  "coordination/engineering/myanmar-adm3-current-cells-20261014/unresolved-evidence-001/tanintharyi6-source-preparation/source-evidence.json",
  "coordination/engineering/myanmar-vietnam-current-cells-20261015/composition/authority-registry.json",
  "coordination/engineering/myanmar-vietnam-current-cells-20261015/composition/patch.json",
  "coordination/engineering/myanmar-vietnam-current-cells-20261015/composition/runtime-envelope.json",
  "coordination/engineering/myanmar-vietnam-current-cells-20261015/composition/selected-ledger.json",
  "coordination/engineering/myanmar-vietnam-current-cells-20261015/kawthoung-contract-repair/authority-001/authority-binding.json",
  "coordination/engineering/myanmar-vietnam-current-cells-20261015/kawthoung-contract-repair/authority-001/original-rule-preimage.json",
  "coordination/engineering/myanmar-vietnam-current-cells-20261015/kawthoung-contract-repair/source-evidence.json",
  "coordination/engineering/myanmar-vietnam-current-cells-20261015/ownership-selection-v2.json",
  "coordination/engineering/vietnam-current-cell-20261014/cell-refinement-001/next557/inland295/authority/authority-binding.json",
  "coordination/engineering/vietnam-current-cell-20261014/cell-refinement-001/next557/inland295/authority/original-rule-preimage.json",
  "coordination/engineering/vietnam-current-cell-20261014/cell-refinement-001/next557/inland295/native-patch.json",
  "coordination/engineering/vietnam-current-cell-20261014/cell-refinement-001/next557/inland295/source-evidence.json",
  "coordination/engineering/vietnam-current-cell-20261014/cell-refinement-001/next557/mongcai262/authority/authority-binding.json",
  "coordination/engineering/vietnam-current-cell-20261014/cell-refinement-001/next557/mongcai262/authority/original-rule-preimage.json",
  "coordination/engineering/vietnam-current-cell-20261014/cell-refinement-001/next557/mongcai262/native-patch.json",
  "coordination/engineering/vietnam-current-cell-20261014/cell-refinement-001/next557/mongcai262/source-evidence.json",
  "coordination/engineering/vietnam-current-cell-20261014/cell-refinement-001/next557/original-stage-inputs.json",
  "coordination/engineering/vietnam-current-cell-20261014/cell-refinement-001/next557/physical/whole-target-support.json",
  "coordination/engineering/vietnam-current-cell-20261014/cell-refinement-001/que-phong/authority/authority-binding.json",
  "coordination/engineering/vietnam-current-cell-20261014/cell-refinement-001/que-phong/authority/original-rule-preimage.json",
  "coordination/engineering/vietnam-current-cell-20261014/cell-refinement-001/que-phong/native-patch.json",
  "coordination/engineering/vietnam-current-cell-20261014/cell-refinement-001/que-phong/original-stage-inputs.json",
  "coordination/engineering/vietnam-current-cell-20261014/cell-refinement-001/que-phong/physical/whole-target-support.json",
  "coordination/engineering/vietnam-current-cell-20261014/cell-refinement-001/que-phong/source-evidence.json",
  "scripts/qualify-source-cohort.py"
];
test('all32 selected appends retain unchanged typed code across original/trusted baseline vintages', t => {
  const f=fixture(t),original=createPackageOutputManifest(f.root);
  original.source.selection={version:1,base:'fixed',additive_release:{path:'coordination/engineering/old/release.json'}};
  const name='scripts/qualify-source-cohort.py',raw=Buffer.from('accepted source-only implementation\n');
  f.write(name,raw.toString());f.git('add',name);f.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','accepted source-only role');
  const acceptedHead=f.git('rev-parse','HEAD'),oid=f.git('rev-parse',acceptedHead+':'+name);
  assert.notEqual(acceptedHead,original.source.head,'Accepted role may postdate the original package');
  const acceptedInputs={commit:acceptedHead,files:[{path:name,mode:'100644',oid,bytes:raw.length}]};
  const typedInputs=[{commit:acceptedHead,path:name,mode:'100644',git_blob_oid:oid,bytes:raw.length,sha256:hash(raw),whole_body_consumed:true}];
  const current=structuredClone(original.source);current.head='f'.repeat(40);
  current.selection.additive_release={path:'coordination/engineering/new/release.json'};
  current.definition.inputs.push(...retainedAssemblyAdditions);
  current.files.push(...retainedAssemblyAdditions.map(path=>({path,mode:'100644',oid:path===name?oid:'1'.repeat(40)})));
  assert.doesNotThrow(()=>admitPackageInputTransition(original.source,current,{acceptedInputs,preliminary:true}));
  assert.throws(()=>admitPackageOutputTransition(original,current,{acceptedInputs}),/authenticated typed consumption/);
  const result=admitPackageOutputTransition(original,current,{acceptedInputs,typedInputs});
  assert.equal(result.added_selected_inputs.length,32);
  assert.deepEqual(result.accepted_selected_inputs,acceptedInputs);
  const opaque=structuredClone(typedInputs);delete opaque[0].sha256;delete opaque[0].whole_body_consumed;
  assert.doesNotThrow(()=>admitPackageOutputTransition(original,current,{acceptedInputs,typedInputs:opaque}),
    'Existing exact opaque descriptor roles do not require a new whole-body read');
  for(const mutate of [
    value=>{value.options.acceptedInputs.files=[];},
    value=>{value.current.files.find(row=>row.path===name).oid='2'.repeat(40);},
    value=>{value.current.files.find(row=>row.path===name).mode='100755';},
    value=>{value.current.files.find(row=>row.path===name).mode='120000';},
    value=>{value.options.typedInputs=[];},
    value=>{value.options.typedInputs[0].git_blob_oid='2'.repeat(40);},
    value=>{value.options.typedInputs[0].bytes++;},
    value=>{value.options.typedInputs[0].mode='100755';},
    value=>{value.current.files=value.current.files.filter(row=>row.path!==name);},
  ]){
    const value={current:structuredClone(current),options:structuredClone({acceptedInputs,typedInputs})};mutate(value);
    assert.throws(()=>admitPackageOutputTransition(original,value.current,value.options));
  }
  const unrelated=structuredClone(current),other='scripts/unreferenced-reader.py';
  unrelated.definition.inputs.push(other);unrelated.files.push({path:other,mode:'100644',oid});
  const acceptedExtra=structuredClone(acceptedInputs);acceptedExtra.files.push({...acceptedExtra.files[0],path:other});
  assert.throws(()=>admitPackageOutputTransition(original,unrelated,{acceptedInputs:acceptedExtra,typedInputs}),/authenticated typed consumption/,
    'Unchanged code and arbitrary pin-shaped metadata do not establish a typed reader role');
  for(const unsafe of ['scripts/new-reader.py','scripts/../escape.py','scripts/readers/']){
    const changed=structuredClone(current);changed.definition.inputs.push(unsafe);
    changed.files.push({path:unsafe,mode:'100644',oid});
    assert.throws(()=>admitPackageOutputTransition(original,changed,{acceptedInputs,typedInputs}));
  }
});
