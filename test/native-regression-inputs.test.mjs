import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {prepareNativeRegressionInputs,NATIVE_REGRESSION_COMMITS,integrationTestFiles} from '../scripts/run-integration-tests.mjs';
const manifestPath='coordination/engineering/native-grid-candidate-1010-20261005-local16/candidate-v1/manifest.json';
const stagePath='coordination/engineering/native-grid-integration-1010-20261005-local17/context-inputs-v1/evidence-quality.json';
const custodyRoot='coordination/engineering/physical-gap-components-1005-20261005-local19/';
function fixture({present=[],fetchFails=false,fetchIncomplete=false,bodiesPresent=true,bodyFetchFails=false,bodyFetchIncomplete=false}={}){
 const available=new Set(present),calls=[],documents=new Map(),descriptors=new Map();
 const pin=(commit,name,bytes=7)=>({commit,path:name,bytes,sha256:'a'.repeat(64)});
 const manifest={original_assets:{bounds:pin(NATIVE_REGRESSION_COMMITS[0],'data/bounds.json')},
  native_latitudes:pin(NATIVE_REGRESSION_COMMITS[4],'data/latitudes.gz')};
 const proof=pin(NATIVE_REGRESSION_COMMITS[1],'retained/proof.json');
 const stage={baseline:{commit:NATIVE_REGRESSION_COMMITS[3],files:[pin(undefined,'data/input.json'),pin(undefined,'scripts/not-consumed.js')]}};
 const custody={generations:NATIVE_REGRESSION_COMMITS.slice(-2).map(commit=>({executed_code_commit:commit,
  code:[pin(undefined,custodyRoot+'executed-code/'+commit+'/scripts/original.py')]}))};
 documents.set(manifestPath,manifest);documents.set(stagePath,stage);documents.set(custodyRoot+'custody-v1/index.json',custody);
 const manifestHash=createHash('sha256').update(JSON.stringify(manifest)).digest('hex');
 documents.set('scripts/native-ownership/verified-candidates.json',{candidates:{[manifestHash]:proof}});
 const declare=pin=>{
  const oid=createHash('sha1').update(pin.commit+':'+pin.path).digest('hex');
  descriptors.set(pin.commit+':'+pin.path,{...pin,oid,mode:'100644'});return oid;
 };
 for(const p of [manifest.original_assets.bounds,manifest.native_latitudes,proof,
  {...stage.baseline.files[0],commit:stage.baseline.commit},{...manifest.native_latitudes,commit:stage.baseline.commit},
  ...custody.generations.map(g=>pin(g.executed_code_commit,'scripts/original.py'))])declare(p);
 const bodyAvailable=new Set(bodiesPresent?[...descriptors.values()].map(p=>p.oid):[]);
 const run=(command,args,options={})=>{
  calls.push({command,args,options});assert.equal(command,'git');
  if(args[0]==='cat-file'&&args[1]==='-e')return {status:available.has(args[2].slice(0,-9))?0:1};
  if(args[0]==='ls-tree'){
   const p=descriptors.get(args[2]+':'+args[4]);
   return {status:0,stdout:p?`${p.mode} blob ${p.oid}\t${p.path}\0`:''};
  }
  if(args[0]==='cat-file'){
   const rows=options.input.trimEnd().split('\n').map(oid=>{
    const p=[...descriptors.values()].find(p=>p.oid===oid);assert(p);
    return bodyAvailable.has(oid)?`${oid} blob ${p.bytes}`:`${oid} missing`;
   });return {status:0,stdout:rows.join('\n')+'\n'};
  }
  assert.equal(args[0],'fetch');
  if(args.includes('--stdin')){
   assert.deepEqual(args,['fetch','--no-tags','--no-write-fetch-head','--no-recurse-submodules','--no-auto-maintenance','--filter=blob:none','--stdin','origin']);
   if(!bodyFetchFails&&!bodyFetchIncomplete)for(const oid of options.input.trimEnd().split('\n'))bodyAvailable.add(oid);
   return {status:bodyFetchFails?1:0,stderr:'synthetic body fetch failure'};
  }
  assert.deepEqual(args.slice(0,3),['fetch','--no-tags','--depth=1']);
  if(!fetchFails&&!fetchIncomplete)for(const commit of args.slice(args.indexOf('origin')+1))available.add(commit);
  return {status:fetchFails?1:0,stderr:fetchFails?'synthetic unavailable remote':''};
 };
 return {calls,documents,descriptors,declare,bodyAvailable,options:{exists:()=>true,readFile:name=>{
  assert(documents.has(name),'Undeclared fixture metadata '+name);return Buffer.from(JSON.stringify(documents.get(name)));
 },run}};
}
test('shallow PR and queue regressions obtain only missing immutable vintages and verify availability',()=>{
 const f=fixture({present:[NATIVE_REGRESSION_COMMITS[0]]});
 assert.deepEqual(prepareNativeRegressionInputs('full',f.options),{applicable:true,fetched:NATIVE_REGRESSION_COMMITS.slice(1)});
 assert.deepEqual(f.calls.find(c=>c.args[0]==='fetch').args,['fetch','--no-tags','--depth=1','origin',...NATIVE_REGRESSION_COMMITS.slice(1)]);
 const count=f.calls.filter(c=>c.args[0]==='fetch').length;
 assert.deepEqual(prepareNativeRegressionInputs('full',f.options),{applicable:true,fetched:[]});
 assert.equal(f.calls.filter(c=>c.args[0]==='fetch').length,count);
});
test('unpublished evidence and absent native implementation do not fetch or inspect Git',()=>{
 for(const [profile,exists] of [['evidence',()=>true],['full',()=>false]])
  assert.deepEqual(prepareNativeRegressionInputs(profile,{exists,run:()=>assert.fail('unexpected Git read')}),{applicable:false,fetched:[]});
});
test('failed or incomplete frozen input fetch cannot establish regression coverage',()=>{
 for(const options of [{fetchFails:true},{fetchIncomplete:true}]){
  const f=fixture(options);assert.throws(()=>prepareNativeRegressionInputs('full',f.options),/command failed|remain unavailable/);
 }
});

const common=[
 'd55795e4c0ad01527029db0bd1d774124a12a61a','548c5f89f00271050823076a84695bb41e1b8454',
 'd70c5d86e345a225b6bc78d67451b3cbbf7a5eed','65cfcef5ffd7d8b98077b9058a374d1e27047430',
 '35d2d3ff48957d34ee8d4329824b268ecadc6d3c'
];
const custody=['8f6dc184d1a41b634cec4759bb57b3cc04dd980a','6ed6406f9fad4c7c468b06a376346b216cb50db7'];
const consumers=[
 ['test/select-build-ownership.test.mjs',[common[0],common[1]]],
 ['test/native-materialization-gate.test.mjs',[common[1]]],
 ['test/pinned-native-package-inputs.test.mjs',[common[3]]],
 ['test/native-latitudes.test.mjs',[common[4]]],
 ['test/physical-component-custody.test.mjs',custody],
 ['test/physical-component-report-binding.test.mjs',custody]
];
function requiredFor(files,options={}){
 const f=fixture(options),result=prepareNativeRegressionInputs('full',{...f.options,files});
 return {...f,result};
}
test('actual native and physical consumer files acquire only their complete original input unions',()=>{
 for(const [name,commits] of consumers){
  const f=requiredFor([name]),expected=commits;
  assert.deepEqual(f.result,{applicable:true,fetched:expected},name);
  assert.deepEqual(f.calls.filter(c=>c.args[0]==='fetch').map(c=>c.args),
   [['fetch','--no-tags','--depth=1','--filter=blob:none','origin',...expected]],name);
  assert.deepEqual(f.calls.filter(c=>c.args[0]==='cat-file'&&c.args[1]==='-e').map(c=>c.args[2]),
   [...expected,...expected].map(commit=>commit+'^{commit}'),name);
 }
});
test('unrelated and snapshot-only controls omit historical acquisition while unscoped callers retain it',()=>{
 for(const files of [['test/future-native-consumer.test.mjs'],[
  'test/physical-component-evidence-controls.test.mjs','test/physical-gap-priority-controls.test.mjs',
  'test/physical-gap-priority-evidence-controls.test.mjs','test/context-input-stage.test.mjs',
  'test/compact-context-inputs.test.mjs','test/build-context-validation-vintage.test.mjs',
  'test/current-rebind-product-custody.test.mjs','test/prepare-startup-ownership.test.mjs',
  'test/build-context-continuation.test.mjs','test/install-selected-native-reference.test.mjs',
  'test/native-preparation.test.mjs','test/worldwide-gap-inventory.test.mjs',
  'test/worldwide-native-batches-controls.test.mjs','test/install-macro-reference.test.mjs']]){
  const f=requiredFor(files);assert.deepEqual(f.result.fetched,[]);assert.deepEqual(f.calls,[]);
 }
 assert.deepEqual(requiredFor(undefined).result.fetched,[...common,...custody]);
 assert.deepEqual(NATIVE_REGRESSION_COMMITS,[...common,...custody]);
 for(const files of [[],null,'test/physical-component-custody.test.mjs',[null],['../test/physical-component-custody.test.mjs']])
  assert.throws(()=>requiredFor(files),/Actual regression file roster/);
 const f=fixture();
 assert.throws(()=>prepareNativeRegressionInputs('full',{...f.options,files:['test/deleted-consumer.test.mjs'],
  exists:name=>name==='scripts/native-ownership/validate-context-input-stage.mjs'}),/Actual regression file roster/);
 assert.deepEqual(f.calls,[],'A stale roster must fail before any Git read');
});
test('file order, duplicates and shard movement cannot drop or duplicate an archived requirement',()=>{
 const all=consumers.map(([name])=>name);
 for(const files of [all,[...all].reverse(),[...all,all[0]]])
  assert.deepEqual(requiredFor(files).result.fetched,[...common.filter((_,index)=>index!==2),...custody]);
 for(const shard of [0,1,2]){
  const files=integrationTestFiles('full',shard),expected=new Set();
  for(const [name,commits] of consumers)if(files.includes(name))for(const commit of commits)expected.add(commit);
  assert.deepEqual(new Set(requiredFor(files).result.fetched),expected);
 }
});
test('a missing required archived object still fails after a scoped fetch, and present ones are not fetched again',()=>{
 for(const [name,commits] of consumers){
  const files=[name],present=commits.slice(0,-1),missing=commits.at(-1);
  for(const options of [{present,fetchFails:true},{present,fetchIncomplete:true}])
   assert.throws(()=>requiredFor(files,options),/command failed|remain unavailable/,name);
  const f=requiredFor(files,{present});
  assert.deepEqual(f.result.fetched,[missing],name);
  assert.deepEqual(prepareNativeRegressionInputs('full',{...f.options,files}),{applicable:true,fetched:[]});
  assert.equal(f.calls.filter(c=>c.args[0]==='fetch').length,1,name);
 }
});


test('remaining custody pins agree with the actual retained component generations',()=>{
 const read=name=>JSON.parse(fs.readFileSync(name));
 const index=read('coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/index.json');
 assert.deepEqual(new Set(index.generations.map(generation=>generation.executed_code_commit)),new Set(custody));
});


test('scoped acquisition fetches only the missing declared body union through stdin',()=>{
 const f=fixture({present:NATIVE_REGRESSION_COMMITS,bodiesPresent:false}),files=consumers.map(([name])=>name);
 prepareNativeRegressionInputs('full',{...f.options,files});
 const trees=f.calls.filter(c=>c.args[0]==='ls-tree'),fetches=f.calls.filter(c=>c.args[0]==='fetch');
 assert.equal(fetches.length,1);assert(fetches[0].args.includes('--stdin'));
 const expected=new Set(trees.map(c=>f.descriptors.get(c.args[2]+':'+c.args[4]).oid));
 assert.deepEqual(new Set(fetches[0].options.input.trimEnd().split('\n')),expected);
 assert(!trees.some(c=>c.args[4]==='scripts/not-consumed.js'));
 const before=f.calls.length;prepareNativeRegressionInputs('full',{...f.options,files});
 assert(!f.calls.slice(before).some(c=>c.args[0]==='fetch'));
 assert(f.calls.every(c=>c.options.env.GIT_NO_LAZY_FETCH==='1'));
});
test('existing source-roster additions are acquired without a second body inventory',()=>{
 const f=fixture({present:NATIVE_REGRESSION_COMMITS,bodiesPresent:false});
 const baseline=f.documents.get(stagePath).baseline,pin={path:'data/new-original.json',bytes:13};
 baseline.files.push(pin);const oid=f.declare({...pin,commit:baseline.commit});
 prepareNativeRegressionInputs('full',{...f.options,files:['test/pinned-native-package-inputs.test.mjs']});
 assert(f.calls.find(c=>c.args.includes('--stdin')).options.input.split('\n').includes(oid));
});
test('failed or incomplete exact body fetch is a hard failure',()=>{
 for(const option of [{bodyFetchFails:true},{bodyFetchIncomplete:true}]){
  const f=fixture({present:NATIVE_REGRESSION_COMMITS,bodiesPresent:false,...option});
  assert.throws(()=>prepareNativeRegressionInputs('full',{...f.options,files:['test/native-latitudes.test.mjs']}),/command failed|bodies remain unavailable/);
 }
});
test('missing, linked, altered and ambiguous original tree descriptors fail before body fetch',()=>{
 for(const change of ['missing','linked','wrong-path','extra','oid','mode']){
  const f=fixture({present:NATIVE_REGRESSION_COMMITS,bodiesPresent:false}),run=f.options.run;
  f.options.run=(command,args,options)=>{
   const result=run(command,args,options);if(args[0]!=='ls-tree')return result;
   if(change==='missing')result.stdout='';
   if(change==='linked')result.stdout=result.stdout.replace('100644','120000');
   if(change==='wrong-path')result.stdout=result.stdout.replace('data/latitudes.gz','data/wrong.gz');
   if(change==='extra')result.stdout+=result.stdout;
   return result;
  };
  if(change==='oid')f.documents.get(manifestPath).native_latitudes.git_blob_oid='f'.repeat(40);
  if(change==='mode')f.documents.get(manifestPath).native_latitudes.mode='100755';
  assert.throws(()=>prepareNativeRegressionInputs('full',{...f.options,files:['test/native-latitudes.test.mjs']}),/tree identity differs/,change);
  assert(!f.calls.some(c=>c.args[0]==='fetch'));
 }
});
test('partial, reordered, foreign, wrong-type and wrong-length body inventories refuse',()=>{
 for(const change of ['empty','unterminated','foreign','type','size','extra','error','signal']){
  const f=fixture({present:NATIVE_REGRESSION_COMMITS}),run=f.options.run;
  f.options.run=(command,args,options)=>{
   const r=run(command,args,options);if(!args[1]?.startsWith('--batch-check'))return r;
   if(change==='empty')r.stdout='';if(change==='unterminated')r.stdout=r.stdout.trimEnd();
   if(change==='foreign')r.stdout=r.stdout.replace(/^[a-f0-9]{40}/,'f'.repeat(40));
   if(change==='type')r.stdout=r.stdout.replace(' blob ',' tree ');
   if(change==='size')r.stdout=r.stdout.replace(/ 7\n$/,' 8\n');
   if(change==='extra')r.stdout+=r.stdout;if(change==='error')r.error=Error('body inspection failed');
   if(change==='signal'){r.status=null;r.signal='SIGTERM';}
   return r;
  };
  assert.throws(()=>prepareNativeRegressionInputs('full',{...f.options,files:['test/native-latitudes.test.mjs']}),/inventory|type or length|command failed/,change);
 }
});
test('invalid or absent original-role declarations do not broaden acquisition',()=>{
 for(const change of ['commit','path','length','absent-proof','custody-prefix','empty-custody']){
  const f=fixture(),manifest=f.documents.get(manifestPath);
  let files=['test/native-latitudes.test.mjs'];
  if(change==='commit')manifest.native_latitudes.commit='f'.repeat(40);
  if(change==='path')manifest.native_latitudes.path='../outside';
  if(change==='length')manifest.native_latitudes.bytes=-1;
  if(change==='absent-proof'){files=['test/native-materialization-gate.test.mjs'];f.documents.get('scripts/native-ownership/verified-candidates.json').candidates={};}
  if(change==='custody-prefix'){files=['test/physical-component-custody.test.mjs'];f.documents.get(custodyRoot+'custody-v1/index.json').generations[0].code[0].path='scripts/foreign.py';}
  if(change==='empty-custody'){files=['test/physical-component-custody.test.mjs'];f.documents.get(custodyRoot+'custody-v1/index.json').generations=[];}
  assert.throws(()=>prepareNativeRegressionInputs('full',{...f.options,files}),/declaration|custody code path|roster is incomplete/,change);
  assert.deepEqual(f.calls,[]);
 }
});


test('optional source lengths remain optional while duplicate declared identities agree',()=>{
 const f=fixture({present:NATIVE_REGRESSION_COMMITS});
 delete f.documents.get(manifestPath).native_latitudes.bytes;
 prepareNativeRegressionInputs('full',{...f.options,files:['test/native-latitudes.test.mjs']});
 const g=fixture({present:NATIVE_REGRESSION_COMMITS});
 const baseline=g.documents.get(stagePath).baseline;
 baseline.files.push({...baseline.files[0]});
 prepareNativeRegressionInputs('full',{...g.options,files:['test/pinned-native-package-inputs.test.mjs']});
 assert.equal(g.calls.filter(c=>c.args[0]==='ls-tree'&&c.args[4]==='data/input.json').length,1);
 baseline.files.at(-1).sha256='f'.repeat(64);
 assert.throws(()=>prepareNativeRegressionInputs('full',{...g.options,files:['test/pinned-native-package-inputs.test.mjs']}),/Conflicting original regression input declarations/);
});


test('commit inspection errors and interrupted tree reads refuse without a fetch retry',()=>{
 for(const phase of ['commit','tree']){
  const f=fixture({present:NATIVE_REGRESSION_COMMITS}),run=f.options.run;
  f.options.run=(command,args,options)=>{
   if(phase==='commit'&&args[1]==='-e'||phase==='tree'&&args[0]==='ls-tree')return {status:null,error:Error('interrupted read')};
   return run(command,args,options);
  };
  assert.throws(()=>prepareNativeRegressionInputs('full',{...f.options,files:['test/native-latitudes.test.mjs']}),/inspection failed|command failed/);
  assert(!f.calls.some(c=>c.args[0]==='fetch'));
 }
});
