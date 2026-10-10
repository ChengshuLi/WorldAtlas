// Exact production pre-import entry prefix: delegated tiny ordinary-file calls.
// This does not execute the selected-bank loader or confer private identity.
import fs from 'node:fs';import vm from 'node:vm';import assert from 'node:assert/strict';import {createHash} from 'node:crypto';import path from 'node:path';import {spawnSync} from 'node:child_process';
const root=process.cwd(),name='coordination/engineering/additive-native-composition-20261009/run-current-rebind.mjs',source=fs.readFileSync(name,'utf8');
const begin=source.indexOf('const demand='),end=source.indexOf('const {ImmutableReader,');assert(begin>=0&&end>begin);
const prefix=source.slice(begin,end);assert(!prefix.includes('await import('));
const raw=Buffer.from(JSON.stringify({execution_commit:'1'.repeat(40),limits:{complete_phase_bytes:230000000,output_bytes:4194304}}));
const stat={dev:1,ino:2,size:raw.length,mode:0o100644,mtimeMs:1,ctimeMs:1,isSymbolicLink:()=>false,isFile:()=>true};
let negatives=0;function execute(mutate=()=>{}){let opens=0;const input={command:['/fixture/time','-l','/fixture/node','--expose-gc','/fixture/entry','/fixture/plan.json','/fixture/output'],pre_use:{plan:{path:'/fixture/plan.json',bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex'),mode:420}}},state={raw,stat:{...stat},input,head:'1'.repeat(40)};mutate(state);const processFixture={execArgv:['--expose-gc'],env:{WORLDATLAS_REBIND_EXECUTION_COMMIT:state.head,WORLDATLAS_REBIND_EXECUTION_PRE_USE:JSON.stringify(input)},execPath:'/fixture/node',argv:['/fixture/node','/fixture/entry','/fixture/plan.json','/fixture/output'],cwd:()=>'/fixture'};
 const file={lstatSync:()=>state.stat,constants:fs.constants,openSync:()=>{opens++;return 3;},readFileSync:()=>state.raw,fstatSync:()=>state.stat,closeSync:()=>{},realpathSync:x=>x};
 let error;try{vm.runInNewContext(prefix,{fs:file,path,createHash,Buffer,process:processFixture,gc:globalThis.gc});}catch(e){error=e;}return {error,opens};}
assert.equal(typeof globalThis.gc,'function','Run this control with actual Node --expose-gc');
assert.equal(execute().error,undefined);
for(const f of [s=>s.head='not-a-head',s=>s.input.pre_use.plan.bytes=1048577,s=>s.input.pre_use.plan.mode=493,s=>s.stat.mode=0o100755,s=>s.stat.isSymbolicLink=()=>true,s=>s.input.command[4]='/foreign/entry',s=>s.input.pre_use.plan.path='/foreign/plan']){const r=execute(f);assert(r.error);assert.equal(r.opens,0);negatives++;}
for(const f of [s=>s.raw=Buffer.from('foreign'),s=>s.raw=Buffer.from(JSON.stringify({execution_commit:'2'.repeat(40),limits:{complete_phase_bytes:230000000,output_bytes:4194304}}))]){assert(execute(f).error);negatives++;}
// Two real plain CLI executions reject their injected environment before data
// opens/imports. No selected data destination or actual bank is supplied.
let real=0;for(const env of [{},{NODE_PATH:'/foreign/modules'}]){const result=spawnSync(process.execPath,[path.join(root,name)],{cwd:root,env:{PATH:process.env.PATH,...env},encoding:'utf8',maxBuffer:16384});assert.equal(result.status,1);assert.match(result.stderr,/Missing\/plain bounded actual execution identity/);real++;}
const report={version:1,kind:'actual-cold-entry-preimport-controls',positive_plan_prefix:1,negative_prefix:negatives,real_cli_refusals:real,limits:['Exact production source prefix with delegated tiny file operations and2 actual CLI refusals. No positive dynamic import/whole frozen execution/cold acquisition qualified.']};console.log(JSON.stringify(report));
