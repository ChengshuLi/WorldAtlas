import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {parseTime,evaluateSupply,supervise,RUNTIME_BODIES,scientificEnvironment,requirePinnedGit,signalAuthenticatedGroup} from './supervise-source-native-linux.mjs';
import {externalOperatingReserve} from '../../../scripts/additive-gap-repair.mjs';
const MiB=1024*1024;
const text=' Maximum resident set size (kbytes): 1234\n Elapsed (wall clock) time (h:mm:ss or m:ss): 0:01.25\n Exit status: 0\n';
test('GNU time uses actual KiB, wall and terminal status; malformed/duplicate rows refuse',()=>{
 assert.deepEqual(parseTime(text),{rss_bytes:1234*1024,elapsed_seconds:1.25,exit_code:0});
 for(const bad of [text+text,text.replace('(kbytes)','(bytes)'),text.replace('0:01.25','bad'),text.replace('Exit status: 0','')])assert.throws(()=>parseTime(bad));
});
const supply=()=>({meminfo:'MemTotal: 8388608 kB\nMemAvailable: 6291456 kB\n',reserved:1024*MiB,aggregate_rss:1024*MiB,ancestors:[],limits:'Max address space         unlimited            unlimited            bytes\nMax data size             unlimited            unlimited            bytes\n',status:'VmSize: 100000 kB\nVmData: 50000 kB\n',unknown_limits:['hidden ancestors unknown']});
test('reported RAM subtracts other peaks and headroom, tightens known caps, retains uncertainty',()=>{
 const evidence=supply(),pass=evaluateSupply(evidence);assert.equal(pass.residual_reported_bytes,2*1024*MiB);assert.match(pass.uncertainty,/unknown/);
 for(const change of [s=>s.reserved=5*1024*MiB,s=>s.ancestors=[{maximum:String(2*1024*MiB),current:'0'}],s=>s.ancestors=[{maximum:'bad',current:'0'}],s=>s.meminfo+='MemAvailable: 100 kB\n',s=>s.limits=s.limits.replace('unlimited','1000')]){const altered=supply();change(altered);assert.throws(()=>evaluateSupply(altered));}
});
test('complete external closure and parent monitoring reserve also reduce the child phase',()=>{
 const runtime=RUNTIME_BODIES.map(p=>({...p,path:'/fixture/'+p.role,mode:0o755})),supervisor={path:'coordination/engineering/melanesia363-additive-delivery-20261010/supervise-source-native-linux.mjs',bytes:1000,sha256:'a'.repeat(64)};
 assert.equal(externalOperatingReserve({},100),0);
 const request={operating_runtime:{version:1,platform:'linux',runtime,supervisor}};
 assert.equal(externalOperatingReserve(request,100),4082768+154552+27384+1100+13*MiB);
 assert.throws(()=>externalOperatingReserve({...request,operating_runtime:{...request.operating_runtime,runtime:runtime.slice(1)}},100));
});
const runtime=JSON.parse(fs.readFileSync(process.env.WORLDATLAS_SOURCE_NATIVE_CONTROL_RUNTIME));
const env=scientificEnvironment(runtime);
const time=runtime.find(p=>p.role==='time').path,ps=runtime.find(p=>p.role==='process-inspector').path;
const base=fs.mkdtempSync(path.join(process.cwd(),'.cache/source-native-controls-'));
async function run(name,source,options={}){const result=await supervise([process.execPath,'-e',source],{time,ps,operation:path.join(base,name),env,...options});fs.writeFileSync(path.join(base,name,'receipt.json'),JSON.stringify(result,null,2)+'\n');return result;}
test('real GNU time successful plain Node child and no owned survivors',async()=>{
 const r=await run('positive','setTimeout(()=>console.log("real bounded child"),150)');assert.equal(r.qualified,true);assert(r.time_lifetime_max_rss_bytes>0);assert.deepEqual(r.owned_processes_remaining,[]);
});
test('real child nonzero exit remains refused',async()=>{const r=await run('nonzero','setTimeout(()=>process.exit(7),100)');assert.equal(r.qualified,false);assert.equal(r.exit.code,7);});
test('shorter test wall terminates the actual owned child and settles time',async()=>{
 const r=await run('wall','setInterval(()=>{},1000)',{wall:200});assert.equal(r.qualified,false);assert.equal(r.refusal,'wall-deadline');assert(r.termination_events.length>0);assert.deepEqual(r.owned_processes_remaining,[]);
});
test('lower fixture cap refuses actual RSS without allocating a stress payload',async()=>{
 const r=await run('rss','setInterval(()=>{},1000)',{cap:1});assert.equal(r.qualified,false);assert.equal(r.refusal,'sampled-group-plus-supervisor-rss-cap');assert.deepEqual(r.owned_processes_remaining,[]);
});
test('failed launcher records refusal and cannot invent a successful terminal',async()=>{
 const r=await supervise([process.execPath,'-e','0'],{time:path.join(base,'absent-time'),ps,operation:path.join(base,'launch-failure'),env});assert.equal(r.qualified,false);assert.match(r.refusal,/launch failed/);assert.deepEqual(r.owned_processes_remaining,[]);
});
process.on('exit',()=>process.stdout.write('# actual owned output: '+base+'\n'));

test('foreign PATH Git resolution refuses before any command launch',()=>{
 const directory=path.join(base,'foreign-bin');fs.mkdirSync(directory);fs.writeFileSync(path.join(directory,'git'),'#!/bin/sh\nexit 0\n',{mode:0o755});
 assert.throws(()=>requirePinnedGit({...env,PATH:directory+path.delimiter+env.PATH},runtime.find(p=>p.role==='git')),/pinned Git/);
 assert.equal(env.GIT_NO_LAZY_FETCH,'1');assert.equal(env.GIT_CONFIG_GLOBAL,'/dev/null');assert.equal(env.GH_TOKEN,undefined);
});
test('changed original root birth or group never authorizes a foreign group signal',()=>{
 const original={pid:123,pgid:123,started_ticks:'10'},sent=[];
 for(const current of [null,{...original,started_ticks:'11'},{...original,pgid:124}])assert.equal(signalAuthenticatedGroup(original,current,'SIGTERM',(...args)=>sent.push(args)),false);
 assert.deepEqual(sent,[]);assert.equal(signalAuthenticatedGroup(original,original,'SIGTERM',(...args)=>sent.push(args)),true);assert.deepEqual(sent,[[-123,'SIGTERM']]);
});
test('terminal stdout burst beyond raw reserve cannot qualify between polls',async()=>{
 const r=await run('terminal-burst',"require('fs').writeSync(1,Buffer.alloc(5*1024*1024));",{interval:200});assert.equal(r.qualified,false);assert.equal(r.refusal,'raw-output-reserve');assert.deepEqual(r.owned_processes_remaining,[]);
});

test('approved one GiB cap is admitted only with matching fresh supply and never expands',async()=>{
 const r=await run('one-gib','console.log("bounded real child")',{cap:1024*MiB});assert.equal(r.qualified,true);assert.equal(r.rss_cap_bytes,1024*MiB);
 const refused=path.join(base,'above-one-gib');await assert.rejects(supervise([process.execPath,'-e','0'],{time,ps,operation:refused,env,cap:1024*MiB+1}),/Limits cannot be expanded/);assert.equal(fs.existsSync(refused),false);
 const low=supply();low.reserved=0;low.aggregate_rss=0;low.meminfo='MemTotal: 8388608 kB\nMemAvailable: 2916352 kB\n';assert.throws(()=>evaluateSupply(low),/residual supply/);
 const exact=supply();exact.reserved=0;exact.aggregate_rss=0;exact.meminfo='MemTotal: 8388608 kB\nMemAvailable: 3932160 kB\n';const admitted=evaluateSupply(exact);assert.equal(admitted.required_bytes,768*MiB);assert.equal(admitted.residual_reported_bytes,768*MiB);assert.equal(admitted.process_peak_reservation_bytes,1024*MiB);
});
