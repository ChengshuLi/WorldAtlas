import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import vm from 'node:vm';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {prepareCurrentRebindDestination,writeCurrentRebindProducts,validateCurrentRebindPlan} from '../coordination/engineering/additive-native-composition-20261009/capture-current-rebind.mjs';
import {CURRENT_REBIND_CODE,LEGACY_CURRENT_REBIND_CODE,currentRebindCodePaths,valueBytes,valueSha,verifyCurrentRebindExecution} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
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
