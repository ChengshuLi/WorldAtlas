import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import vm from 'node:vm';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {prepareCurrentRebindDestination,writeCurrentRebindProducts,validateCurrentRebindPlan} from '../coordination/engineering/additive-native-composition-20261009/capture-current-rebind.mjs';
import {CURRENT_REBIND_CODE,valueBytes,valueSha,verifyCurrentRebindExecution} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
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
test('identity-only issued plan preserves original operands and rejects code or scope drift',()=>{
 const context={executionCommit:'1'.repeat(40),baseSelection:{release_id:'fixture'},registry:{entries:[{}]},originalRows:[{component_id:'original'}],executedCode:CURRENT_REBIND_CODE.map(path=>({path,bytes:1,sha256:'a'.repeat(64)}))};
 const plan={version:1,kind:'issued-current-rebind-acquisition-plan-v1',execution_commit:context.executionCommit,base_selection:context.baseSelection,authority_registry_sha256:valueSha(context.registry),original_rows_sha256:valueSha(context.originalRows),original_patch_sha256s:['b'.repeat(64)],target_sources:[{target_id:'target',path:'data/source.json'}],predecessor_proof:null,executed_code:context.executedCode};
 assert.strictEqual(validateCurrentRebindPlan(plan,context),plan);
 const bodyPin=(path,raw)=>({commit:'1'.repeat(40),path,mode:'100644',git_blob_oid:'2'.repeat(40),bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex')});
 const ordinary=(path)=>({path,bytes:1,sha256:'c'.repeat(64),mode:420});
 const dependencyRoot='coordination/engineering/additive-native-gap-batch-20261008/original-execution-custody/module-bodies/';
 const before={runtime:[['node','/fixture/node'],['git','/fixture/git'],['supervisor-python','/fixture/python']].map(([role,path])=>({role,...ordinary(path),mode:493}))
  .concat(context.executedCode.filter(p=>p.path.startsWith(dependencyRoot)).map(p=>({role:'installed-dependency',path:'/fixture/node_modules/@noble/hashes/'+p.path.slice(dependencyRoot.length),bytes:p.bytes,sha256:p.sha256,mode:420}))),
  code:context.executedCode,entry:ordinary('/fixture/entry'),supervisor:ordinary('/fixture/supervisor'),
  plan:{path:'/fixture/plan',bytes:valueBytes(plan).length,sha256:valueSha(plan),mode:420}};
 const command=['/fixture/node','/fixture/entry','/fixture/plan','/fixture/output'];
 const request={execution_commit:context.executionCommit,base_selection:context.baseSelection,authority_registry_sha256:plan.authority_registry_sha256,
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
