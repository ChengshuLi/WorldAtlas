import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import vm from 'node:vm';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {prepareCurrentRebindDestination,writeCurrentRebindProducts,validateCurrentRebindPlan} from '../coordination/engineering/additive-native-composition-20261009/capture-current-rebind.mjs';
import {CURRENT_REBIND_CODE,LEGACY_CURRENT_REBIND_CODE,currentRebindCodePaths,valueBytes,valueSha,verifyCurrentRebindExecution,verifyCurrentRebindProducts,currentRebindResult} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
import {selectedBootstrap} from '../scripts/check-effective-geographic-regression.mjs';
import {BUILD_CONTEXT_VALIDATOR_SOURCES,BUILD_CONTEXT_STAGE_PATH,validateBuildContextStage} from '../scripts/native-ownership/validate-build-context-stage.mjs';
import {CONTEXT_STAGE_PATH} from '../scripts/native-ownership/validate-context-input-stage.mjs';
import {JOINT_CODE} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-joint-entry.mjs';
const root=process.cwd(),entry='coordination/engineering/additive-native-composition-20261009/run-current-rebind.mjs';
function fixture(t){
 const dir=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'rebind-custody-')));
 t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));fs.mkdirSync(path.join(dir,'.cache'));
 const destination=path.join(dir,'.cache','products');
 return {dir,destination,token:prepareCurrentRebindDestination(dir,destination)};
}
const products=()=>({publication:{kind:'synthetic-publication'},facts:{inputs:[]},result:{native:[]},request:{payload:['é\u0000','quote"','\\','雪😀','\ud800',-0,1e21,true,null]}});
test('complete canonical products retain Unicode and write publication last',t=>{
 const f=fixture(t),bodies=products(),opened=[],open=fs.openSync;
 fs.openSync=(name,...args)=>{if(path.dirname(String(name))===f.destination)opened.push(path.basename(String(name)));return open(name,...args);};
 try{writeCurrentRebindProducts(f.token,bodies);}finally{fs.openSync=open;}
 assert.deepEqual(opened,['request.json','result.json','facts.json','publication.json']);
 for(const [name,body]of Object.entries(bodies))assert.deepEqual(fs.readFileSync(path.join(f.destination,name+'.json')),valueBytes(body));
});
test('invalid or incomplete product data creates no publication',t=>{
 for(const mutate of [b=>delete b.result,b=>b.request.invalid=undefined,b=>b.facts.invalid=Infinity]){
  const f=fixture(t),b=products();mutate(b);assert.throws(()=>writeCurrentRebindProducts(f.token,b));assert.equal(fs.existsSync(f.destination),false);
 }
 const f=fixture(t);assert.throws(()=>writeCurrentRebindProducts({...f.token},products()),/prepared/);
});
test('collisions and dangling symlinks preserve existing output',t=>{
 const f=fixture(t);fs.mkdirSync(f.destination);fs.writeFileSync(path.join(f.destination,'sentinel'),'original');
 assert.throws(()=>writeCurrentRebindProducts(f.token,products()),/Destination appeared/);
 assert.equal(fs.readFileSync(path.join(f.destination,'sentinel'),'utf8'),'original');
 const s=fixture(t);fs.symlinkSync(path.join(s.dir,'missing'),s.destination);
 assert.throws(()=>writeCurrentRebindProducts(s.token,products()),/Destination appeared/);
 assert.equal(fs.lstatSync(s.destination).isSymbolicLink(),true);assert.equal(fs.existsSync(path.join(s.dir,'missing')),false);
});
test('interrupted output retains complete written bodies and cannot publish or overwrite partial result',t=>{
 const f=fixture(t),bodies=products(),open=fs.openSync;
 fs.openSync=(name,...args)=>{if(name===path.join(f.destination,'facts.json'))throw Error('simulated interrupted publication');return open(name,...args);};
 try{assert.throws(()=>writeCurrentRebindProducts(f.token,bodies),/interrupted/);}finally{fs.openSync=open;}
 const retained=fs.readFileSync(path.join(f.destination,'request.json'));
 assert.deepEqual(retained,valueBytes(bodies.request));assert.equal(fs.existsSync(path.join(f.destination,'publication.json')),false);
 assert.throws(()=>writeCurrentRebindProducts(f.token,bodies),/Destination appeared/);
 assert.deepEqual(fs.readFileSync(path.join(f.destination,'request.json')),retained);
});
test('current producers reject old profiles while external custody authenticates both literal execution generations',()=>{
 for(const profile of [CURRENT_REBIND_CODE,LEGACY_CURRENT_REBIND_CODE]){
 const context={executionCommit:'1'.repeat(40),baseSelection:{release_id:'fixture'},registry:{entries:[{}]},originalRows:[{component_id:'original'}],executedCode:profile.map(path=>({path,bytes:1,sha256:'a'.repeat(64)}))};
 const plan={version:1,kind:'issued-current-rebind-acquisition-plan-v1',execution_commit:context.executionCommit,base_selection:context.baseSelection,authority_registry_sha256:valueSha(context.registry),original_rows_sha256:valueSha(context.originalRows),original_patch_sha256s:['b'.repeat(64)],target_sources:[{target_id:'target',path:'data/source.json'}],predecessor_proof:null,executed_code:context.executedCode};
 if(profile===CURRENT_REBIND_CODE)assert.strictEqual(validateCurrentRebindPlan(plan,context),plan);
 else assert.throws(()=>validateCurrentRebindPlan(plan,context),/Foreign\/incomplete/);
 const bodyPin=(path,raw)=>({commit:'1'.repeat(40),path,mode:'100644',git_blob_oid:'2'.repeat(40),bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex')});
 const ordinary=(path)=>({path,bytes:1,sha256:'c'.repeat(64),mode:420});
 const dependencyRoot='coordination/engineering/additive-native-gap-batch-20261008/original-execution-custody/module-bodies/';
 const before={runtime:[['node','/fixture/node'],['git','/fixture/git'],['supervisor-python','/fixture/python']].map(([role,path])=>({role,...ordinary(path),mode:493}))
  .concat(context.executedCode.filter(p=>p.path.startsWith(dependencyRoot)).map(p=>({role:'installed-dependency',path:'/fixture/node_modules/@noble/hashes/'+p.path.slice(dependencyRoot.length),bytes:p.bytes,sha256:p.sha256,mode:420}))),
  code:context.executedCode,entry:ordinary('/fixture/entry'),supervisor:ordinary('/fixture/supervisor'),
  plan:{path:'/fixture/plan',bytes:valueBytes(plan).length,sha256:valueSha(plan),mode:420}};
 const command=['/fixture/node','/fixture/entry','/fixture/plan','/fixture/output'];
 const request={execution_commit:context.executionCommit,executed_code:context.executedCode,base_selection:context.baseSelection,authority_registry_sha256:plan.authority_registry_sha256,
  original_rows:context.originalRows,original_patch_sha256s:plan.original_patch_sha256s,acquisition:{target_sources:plan.target_sources,predecessor_proof:null},execution:{command,pre_use:before}};
 const code_source=valueBytes({version:1,kind:'whole-current-rebind-execution-custody-v1',execution_commit:context.executionCommit,command,pre_use:before,post_use:before});
 const operating={request_sha256:'d'.repeat(64),publication_sha256:'e'.repeat(64),elapsed_seconds:1};
 const bodies={code_source,issued_plan:valueBytes(plan),stderr:Buffer.alloc(0),
  terminal:valueBytes({version:1,kind:'current-rebind-external-terminal-v1',execution_commit:context.executionCommit,command,
   request_sha256:operating.request_sha256,publication_sha256:operating.publication_sha256,code_source_sha256:bodyPin('source',code_source).sha256,
   exit_code:0,signal:null,guard_reason:null,elapsed_seconds:1,owned_processes_remaining:[],termination_events:[]}),
  stdout:valueBytes({version:1,kind:'current-rebind-child-publication-v1',execution_commit:context.executionCommit,request_sha256:operating.request_sha256,publication_sha256:operating.publication_sha256,result_sha256:'f'.repeat(64)})};
 operating.execution_custody=Object.fromEntries(Object.entries(bodies).map(([name,raw])=>[name,bodyPin(name,raw)]));
 const check=custody=>verifyCurrentRebindExecution({request,operating,expectedCode:context.executedCode,custody:{...custody,result_sha256:'f'.repeat(64)}});
 assert.equal(check(bodies).command.length,4);
 assert.throws(()=>check({...bodies,stderr:Buffer.from('changed')}),/whole body differs/);
 for(const mutate of [p=>p.original_rows_sha256='f'.repeat(64),p=>p.executed_code.pop(),p=>p.extra='unbound']){
  const p=structuredClone(plan);mutate(p);assert.throws(()=>validateCurrentRebindPlan(p,context),/differs|Foreign/);
 }
 }
});
test('historical rebind code vectors remain literal while new producers require the complete expanded profile',()=>{
 assert.equal(LEGACY_CURRENT_REBIND_CODE.length,28);assert.equal(CURRENT_REBIND_CODE.length,30);
 assert.equal(valueSha(LEGACY_CURRENT_REBIND_CODE),'0bfe5d9c12b0f650b405932e440ca5a8ce494a66e18ac31cdf795f5d33b43f7d');
 assert.deepEqual(CURRENT_REBIND_CODE.slice(0,28),LEGACY_CURRENT_REBIND_CODE);
 assert.deepEqual(CURRENT_REBIND_CODE.slice(28),['scripts/selected-reference-metadata.mjs','src/reference-metadata.js']);
 assert.deepEqual(JSON.parse(fs.readFileSync('coordination/engineering/additive-native-composition-20261009/execution-code-paths.json')),CURRENT_REBIND_CODE);
 const code=profile=>profile.map(path=>({path,bytes:1,sha256:'a'.repeat(64)}));
 for(const profile of [LEGACY_CURRENT_REBIND_CODE,CURRENT_REBIND_CODE]){
  const rows=code(profile),before=structuredClone(rows);
  assert.strictEqual(currentRebindCodePaths(rows),profile);assert.deepEqual(rows,before);
 }
 assert.strictEqual(currentRebindCodePaths(code(CURRENT_REBIND_CODE),{requireCurrent:true}),CURRENT_REBIND_CODE);
 assert.throws(()=>currentRebindCodePaths(code(LEGACY_CURRENT_REBIND_CODE),{requireCurrent:true}),/Foreign\/incomplete/);
 for(const edit of [rows=>rows.pop(),rows=>rows.splice(28,1),rows=>rows.push(rows[0]),rows=>rows.reverse(),rows=>rows[0].path='foreign.mjs',rows=>rows[0]=null]){
  const rows=code(CURRENT_REBIND_CODE);edit(rows);assert.throws(()=>currentRebindCodePaths(rows),/Foreign\/incomplete/);
 }
 const executedCode=code(LEGACY_CURRENT_REBIND_CODE),context={executionCommit:'1'.repeat(40),baseSelection:{release_id:'fixture'},registry:{entries:[{}]},originalRows:[{component_id:'original'}],executedCode};
 const plan={version:1,kind:'issued-current-rebind-acquisition-plan-v1',execution_commit:context.executionCommit,base_selection:context.baseSelection,authority_registry_sha256:valueSha(context.registry),original_rows_sha256:valueSha(context.originalRows),original_patch_sha256s:['b'.repeat(64)],target_sources:[{target_id:'target',path:'data/source.json'}],predecessor_proof:null,executed_code:executedCode};
 assert.throws(()=>validateCurrentRebindPlan(plan,context),/Foreign\/incomplete/,'A new producer cannot publish a historical28-file method as current');
});
test('every actual trusted entry inventories both imported metadata modules',()=>{
 const modules=['scripts/selected-reference-metadata.mjs','src/reference-metadata.js'];
 for(const name of modules)assert.ok(JOINT_CODE.includes(name),name);
 assert.ok(BUILD_CONTEXT_VALIDATOR_SOURCES.includes('src/reference-metadata.js'));
 const inventorySource=fs.readFileSync('scripts/additive-gap-repair.mjs','utf8'),begin=inventorySource.indexOf('  const codeNames = [',inventorySource.indexOf('export function inventoryCommand')),end=inventorySource.indexOf('];',begin);
 assert.ok(begin>=0&&end>begin);const inventoryPaths=vm.runInNewContext(inventorySource.slice(begin,end+2)+';codeNames');
 for(const name of modules)assert.ok(inventoryPaths.includes(name),name);
 const run=spawnSync('python3',['-c',"import ast,json,sys; tree=ast.parse(open(sys.argv[1]).read()); value=next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='TRUSTED_PATHS' for t in n.targets)); print(json.dumps(ast.literal_eval(value)))",'scripts/run-geographic-check.py'],{encoding:'utf8'});
 assert.equal(run.status,0,run.stderr);const paths=JSON.parse(run.stdout);for(const name of modules)assert.ok(paths.includes(name),name);
 const head=spawnSync('git',['-c','core.hooksPath=/dev/null','rev-parse','HEAD'],{encoding:'utf8'});assert.equal(head.status,0,head.stderr);
 const {executionCode}=selectedBootstrap(root,head.stdout.trim(),head.stdout.trim());
 for(const name of modules){const pin=executionCode.find(row=>row.path===name);assert.ok(pin,name);const body=fs.readFileSync(name);assert.equal(pin.bytes,body.length);assert.equal(pin.sha256,createHash('sha256').update(body).digest('hex'));}
});
test('current build-context validation authenticates the new pure helper before any scientific stage input',async()=>{
 const sources=BUILD_CONTEXT_VALIDATOR_SOURCES.map(path=>{const raw=fs.readFileSync(path);return {path,bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex')};});
 const stage={version:1,issue:1,lane:'engineering',kind:'retained-identity-context-migration-v1',original_stage:{path:CONTEXT_STAGE_PATH,bytes:1,sha256:'a'.repeat(64)},validator_sources:sources};
 const run=(value,{corrupt=false}={})=>{const reads=[];const promise=validateBuildContextStage({readFile:name=>{if(name===BUILD_CONTEXT_STAGE_PATH)return valueBytes(value);reads.push(name);if(name===CONTEXT_STAGE_PATH)throw Error('current closure complete; scientific data deliberately not supplied');const raw=fs.readFileSync(name);return corrupt&&name==='src/reference-metadata.js'?Buffer.concat([raw,Buffer.from('changed')]):raw;}});return {promise,reads};};
 const old={...stage,validator_sources:sources.filter(pin=>pin.path!=='src/reference-metadata.js')},missing=run(old);
 await assert.rejects(missing.promise,/Incomplete or duplicate migrated context validator closure/);assert.deepEqual(missing.reads,[]);
 const current=run(stage);await assert.rejects(current.promise,/current closure complete/);assert.ok(current.reads.includes('src/reference-metadata.js'));
 const changed=run(stage,{corrupt:true});await assert.rejects(changed.promise,/Context migration input bytes differ: src\/reference-metadata.js/);assert.equal(changed.reads.includes(CONTEXT_STAGE_PATH),false);
});
test('plain actual entry authenticates its whole input before any import',()=>{
 const source=fs.readFileSync(entry,'utf8'),begin=source.indexOf('const demand='),end=source.indexOf('const {ImmutableReader,');
 assert.ok(begin>=0&&end>begin);const prefix=source.slice(begin,end);assert.equal(prefix.includes('await import('),false);
 const raw=Buffer.from(JSON.stringify({execution_commit:'1'.repeat(40)}));
 const base={dev:1,ino:2,size:raw.length,mode:0o100644,mtimeMs:1,ctimeMs:1,isSymbolicLink:()=>false,isFile:()=>true};
 const execute=(mutate=()=>{})=>{
  let opens=0;const input={command:['/fixture/node','/fixture/entry','/fixture/plan.json','/fixture/output'],pre_use:{plan:{path:'/fixture/plan.json',bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex'),mode:420}}};
  const state={raw,stat:{...base},input,head:'1'.repeat(40),execArgv:[]};mutate(state);
  const processFixture={execArgv:state.execArgv,env:{WORLDATLAS_REBIND_EXECUTION_COMMIT:state.head,WORLDATLAS_REBIND_EXECUTION_PRE_USE:JSON.stringify(input)},execPath:'/fixture/node',argv:['/fixture/node','/fixture/entry','/fixture/plan.json','/fixture/output'],cwd:()=>'/fixture'};
  const file={lstatSync:()=>state.stat,constants:fs.constants,openSync:()=>{opens++;return 3;},readFileSync:()=>state.raw,fstatSync:()=>state.stat,closeSync:()=>{},realpathSync:x=>x};
  let error;try{vm.runInNewContext(prefix,{fs:file,path,createHash,Buffer,process:processFixture});}catch(e){error=e;}return {error,opens};
 };
 assert.equal(execute().error,undefined);
 for(const mutate of [s=>s.head='invalid',s=>s.input.pre_use.plan.mode=493,s=>s.stat.mode=0o100755,s=>s.stat.isSymbolicLink=()=>true,s=>s.input.command[1]='/foreign/entry',s=>s.execArgv=['--inspect']]){
  const observed=execute(mutate);assert.ok(observed.error);assert.equal(observed.opens,0);
 }
 assert.ok(execute(s=>s.raw=Buffer.from('foreign')).error);
 const actual=spawnSync(process.execPath,[path.join(root,entry)],{cwd:root,env:{PATH:process.env.PATH},encoding:'utf8'});
 assert.equal(actual.status,1);assert.match(actual.stderr,/Missing\/plain actual execution identity/);
});

import {nativeSequence} from '../src/native-grid.js';
test('full rebind verifier checks canonical count and hash without materializing producer bodies',t=>{
 const literal={coordinates:Array.from({length:65},(_,i)=>[i/10,-i/10]),label:'雪😀\ud800'};
 const bodies={request:literal,facts:{},publication:{},operating:{},result:literal};
 const bodyPins=Object.fromEntries(Object.entries(bodies).map(([name,body])=>[name,{bytes:valueBytes(body).length,sha256:valueSha(body)}]));
 let visits=0;
 const stored={...literal,coordinates:nativeSequence(literal.coordinates.length,function*(){for(const pair of literal.coordinates){visits++;yield pair;}})};
 const input={...bodies,request:stored,result:stored,certificate:{},bodyPins};
 const stringify=JSON.stringify;let wholeObjects=0;
 JSON.stringify=value=>{
  if(value!==null&&typeof value==='object')wholeObjects++;return stringify(value);
 };
 try{
  // Complete descriptor verification succeeds; this deliberately incomplete
  // certificate must still fail its next independent semantic boundary.
  assert.throws(()=>verifyCurrentRebindProducts(input),/^Error: Foreign current rebind certificate$/);
 }finally{JSON.stringify=stringify;}
 t.diagnostic('Request/result canonical bytes: '+bodyPins.request.bytes+'/'+bodyPins.result.bytes+'; pair visits: '+visits+'; complete object serializations: '+wholeObjects);
 assert.equal(wholeObjects,0,'Verifier must not rebuild whole producer JSON');
 assert.equal(visits,130,'Each request/result geometry is traversed once');
 for(const name of Object.keys(bodies))for(const change of [{bytes:bodyPins[name].bytes+1},{sha256:'0'.repeat(64)}])
  assert.throws(()=>verifyCurrentRebindProducts({...input,bodyPins:{...bodyPins,[name]:{...bodyPins[name],...change}}}),new RegExp('Whole canonical rebind product bytes differ: '+name));
 const utf16=JSON.stringify(literal).length+1;assert.notEqual(utf16,bodyPins.request.bytes);
 assert.throws(()=>verifyCurrentRebindProducts({...input,bodyPins:{...bodyPins,request:{...bodyPins.request,bytes:utf16}}}),/Whole canonical rebind product bytes differ: request/);
 assert.throws(()=>verifyCurrentRebindProducts({...input,request:null}),/Whole canonical rebind product bytes differ: request/);
 assert.throws(()=>verifyCurrentRebindProducts({...input,result:{tail:Infinity}}),/Nonfinite\/missing\/non-JSON/);
});

test('full rebind product acceptance preserves exact literal and owned-store results',async t=>{
 const {admitNativeMetadataStore}=await import('../scripts/native-patch-store.mjs');
 const polygon=x=>{const ring=Array.from({length:32},(_,i)=>[x+.2*Math.cos(i*Math.PI/16),.2*Math.sin(i*Math.PI/16)]);return {type:'Polygon',coordinates:[[...ring,ring[0]]]};};
 const base=polygon(0),primitive=polygon(2),execution_commit='1'.repeat(40);
 const operands={baseSelection:{version:1},registry:{version:1},size:16,
  originalRows:[{component_id:'new',target_id:'A',pixelIndex:1,disposition:'assigned',base_geometry:base,base_geometry_sha256:valueSha(base),geometry:primitive,geometry_sha256:valueSha(primitive)}],
  originalPatches:[{version:1,kind:'unassigned-native-cells-v1',rows:[{y:3,runs:[[4,5,1]]}]}],
  currentTargets:[{target_id:'A',pixelIndex:1,geometry:base,geometry_sha256:valueSha(base)}],currentRows:[{y:3,runs:[[0,2,2]]}]};
 const expectedCode=CURRENT_REBIND_CODE.map(path=>({path,bytes:1,sha256:'a'.repeat(64)}));
 const pin=(path,body)=>({commit:execution_commit,path,mode:'100644',git_blob_oid:'2'.repeat(40),bytes:body.length,sha256:createHash('sha256').update(body).digest('hex')});
 const identity=(name,value)=>pin(name+'.json',valueBytes(value));
 const acquisition={version:1,kind:'complete-selected-rebind-inputs-v1',target_sources:[{target_id:'A',path:'data/source.json'}],source_inputs:[],native_inputs:[],predecessor_proof:null,predecessor_rows:[],manifest_sha256:'b'.repeat(64)};
 const phases=[{kind:'complete-current-target-source',path:'data/source.json'}];
 const acquired={base_selection:operands.baseSelection,current_targets:operands.currentTargets,current_rows:operands.currentRows,acquisition,acquisition_phases:phases};
 const plan={version:1,kind:'issued-current-rebind-acquisition-plan-v1',execution_commit,base_selection:operands.baseSelection,authority_registry_sha256:valueSha(operands.registry),original_rows_sha256:valueSha(operands.originalRows),original_patch_sha256s:operands.originalPatches.map(valueSha),target_sources:acquisition.target_sources,predecessor_proof:null,executed_code:expectedCode};
 const ordinary=path=>({path,bytes:1,sha256:'c'.repeat(64),mode:420}),dependencyRoot='coordination/engineering/additive-native-gap-batch-20261008/original-execution-custody/module-bodies/';
 const before={runtime:[['node','/fixture/node'],['git','/fixture/git'],['supervisor-python','/fixture/python']].map(([role,path])=>({role,...ordinary(path),mode:493}))
  .concat(expectedCode.filter(p=>p.path.startsWith(dependencyRoot)).map(p=>({role:'installed-dependency',path:'/fixture/node_modules/@noble/hashes/'+p.path.slice(dependencyRoot.length),bytes:p.bytes,sha256:p.sha256,mode:420}))),
  code:expectedCode,entry:ordinary('/fixture/entry'),supervisor:ordinary('/fixture/supervisor'),plan:{path:'/fixture/plan',bytes:valueBytes(plan).length,sha256:valueSha(plan),mode:420}};
 const command=['/fixture/node','/fixture/entry','/fixture/plan','/fixture/output'];
 const request={version:1,kind:'issued-native-additive-current-bank-rebind-v1',execution_commit,executed_code:expectedCode,base_selection:operands.baseSelection,authority_registry_sha256:valueSha(operands.registry),original_rows:operands.originalRows,original_patch_sha256s:operands.originalPatches.map(valueSha),current_targets:operands.currentTargets,current_rows:operands.currentRows,acquisition,execution:{command,pre_use:before},size:operands.size};
 const result=currentRebindResult(operands),requestPin=identity('request',request),resultPin=identity('result',result);
 const facts={version:1,kind:'native-additive-current-bank-rebind-facts-v1',execution_commit,request_sha256:requestPin.sha256,result_sha256:resultPin.sha256,acquisition_sha256:valueSha(acquisition),acquisition_phases:phases},factsPin=identity('facts',facts);
 const publication={version:1,kind:'native-additive-current-bank-rebind-publication-v1',execution_commit,request_sha256:requestPin.sha256,outputs:{facts:{path:'facts.json',bytes:factsPin.bytes,sha256:factsPin.sha256},result:{path:'result.json',bytes:resultPin.bytes,sha256:resultPin.sha256}}},publicationPin=identity('publication',publication);
 const code_source=valueBytes({version:1,kind:'whole-current-rebind-execution-custody-v1',execution_commit,command,pre_use:before,post_use:before});
 const executionCustody={code_source,issued_plan:valueBytes(plan),stderr:Buffer.alloc(0),
  terminal:valueBytes({version:1,kind:'current-rebind-external-terminal-v1',execution_commit,command,request_sha256:requestPin.sha256,publication_sha256:publicationPin.sha256,code_source_sha256:pin('code-source',code_source).sha256,exit_code:0,signal:null,guard_reason:null,elapsed_seconds:1,owned_processes_remaining:[],termination_events:[]}),
  stdout:valueBytes({version:1,kind:'current-rebind-child-publication-v1',execution_commit,request_sha256:requestPin.sha256,publication_sha256:publicationPin.sha256,result_sha256:resultPin.sha256})};
 const operating={version:1,kind:'native-additive-current-bank-rebind-operating-v1',execution_commit,request_sha256:requestPin.sha256,publication_sha256:publicationPin.sha256,exit_code:0,signal:null,owned_processes_remaining:[],elapsed_seconds:1,execution_custody:Object.fromEntries(Object.entries(executionCustody).map(([name,raw])=>[name,pin(name,raw)]))};
 const bodyPins={request:requestPin,result:resultPin,facts:factsPin,publication:publicationPin,operating:identity('operating',operating)};
 const certificate={version:1,kind:'qualified-native-additive-current-bank-rebind-v1',execution_commit,base_selection:operands.baseSelection,authority_registry_sha256:valueSha(operands.registry),...bodyPins};
 const input={...operands,request,result,facts,publication,operating,bodyPins,certificate,expectedCode,acquired,executionCustody};
 assert.strictEqual(verifyCurrentRebindProducts(input),result);
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'full-rebind-identity-'));t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
 const stores=[];
 try{
  const stored={...input};
  for(const name of ['request','result']){
   const raw=valueBytes(input[name]),store=await admitNativeMetadataStore({directory,chunks:[raw],expected:bodyPins[name]});stores.push(store);stored[name]=store.metadata;
  }
  assert.equal(Array.isArray(stored.request.current_targets[0].geometry.coordinates[0]),false);
  assert.strictEqual(verifyCurrentRebindProducts(stored),stored.result);
  assert.deepEqual(valueBytes(stored.result),valueBytes(result));
  const changed={...stored,result:{...stored.result,geometry:[]}};
  changed.bodyPins={...bodyPins,result:identity('result',changed.result)};
  assert.throws(()=>verifyCurrentRebindProducts(changed),/Complete current rebind result\/inverse differs/);
 }finally{for(const store of stores)store.close();}
 assert.deepEqual(fs.readdirSync(directory),[]);
});
