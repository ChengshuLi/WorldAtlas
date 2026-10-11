import fs from 'node:fs';import os from 'node:os';import path from 'node:path';import test from 'node:test';import assert from 'node:assert/strict';import {createHash} from 'node:crypto';
import {supervise,assemblyStorage,scientificEnvironment,assemblyOperatingLimits,evaluateSupply,monitoringSampleBytes,writeMonitoringSamples,sourceNativeStorage,sourceNativeStockAdmission} from './supervise-source-native-linux.mjs';
import {assemblyProducts,assemblyProcessingAllowance,assemblyStockAdmission} from './supervise-selected-assembly-linux.mjs';
const time='/workspace/scratch/127991fc8b8e/cloud-tools/gnu-time/time-1.9-0.2-amd64/usr/bin/time',ps='/usr/bin/ps',MiB=1048576;
const issued={rss_bytes:1024*MiB,wall_seconds:1200,output_bytes:4*MiB,retained_bytes:12*MiB,log_bytes:4*MiB,monitor_bytes:8*MiB,receipt_bytes:MiB};
const env=scientificEnvironment([{role:'git',path:'/usr/bin/git'},{role:'process-inspector',path:ps}]);
test('fixed assembly profile admits genuine tiny child and refuses expanded limits before launch',async()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'assembly-profile-'));
 try{
  const output=path.join(root,'output'),operation=path.join(root,'operation');
  const result=await supervise([process.execPath,'-e','process.stdout.write("fixture\\n")'],{time,ps,operation,env,profile:'selected-assembly-v1',outputDirectory:output,cap:1024*MiB,wall:1200000});
  assert.equal(result.qualified,true);assert.equal(result.wall_deadline_seconds,1200);assert.equal(result.rss_cap_bytes,1024*MiB);assert.deepEqual(result.owned_processes_remaining,[]);
  for(const options of [{cap:1024*MiB+1},{wall:1200001},{profile:'source-native-v1',wall:600001},{profile:'unknown'}]){
   const denied=path.join(root,'not-created');await assert.rejects(supervise([process.execPath,'-e','process.exit(0)'],{time,ps,operation:denied,env,profile:'selected-assembly-v1',outputDirectory:output,...options}),/Limits|Unknown/);assert.equal(fs.existsSync(denied),false);
  }
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
test('assembly terminal storage checks exact stderr, product union and original growth bounds',()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'assembly-storage-')),output=path.join(root,'output'),operation=path.join(root,'operation');fs.mkdirSync(output);fs.mkdirSync(operation);
 try{
  fs.writeFileSync(path.join(operation,'stderr.txt'),Buffer.alloc(40960));assert.equal(assemblyStorage(output,operation).retainedBytes,40960);
  fs.appendFileSync(path.join(operation,'stderr.txt'),'x');assert.throws(()=>assemblyStorage(output,operation),/stderr/);fs.truncateSync(path.join(operation,'stderr.txt'),0);
  fs.writeFileSync(path.join(output,'ledger.json'),Buffer.alloc(4*MiB));assert.equal(assemblyStorage(output,operation).productBytes,4*MiB);
  fs.writeFileSync(path.join(output,'patch.json'),'x');assert.throws(()=>assemblyStorage(output,operation),/product/);fs.unlinkSync(path.join(output,'patch.json'));
  assert.equal(assemblyStorage(output,operation,8*MiB).retainedBytes,12*MiB);assert.throws(()=>assemblyStorage(output,operation,8*MiB+1),/growth/);
  fs.writeFileSync(path.join(output,'unexpected'),'x');assert.throws(()=>assemblyStorage(output,operation),/Unexpected/);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
test('assembly final entry binds all four actual product bytes and qualified summary',()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'assembly-products-')),head='a'.repeat(40),products=[];
 try{
  for(const name of ['ledger','patch','envelope','qualification']){const raw=Buffer.from(name==='qualification'?'{"a":1,"z":{"first":true,"second":2}}\n':'{}\n');fs.writeFileSync(path.join(root,name+'.json'),raw);products.push({path:name+'.json',bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex')});}
  const allowance={phaseBytes:512*MiB,rssBytes:768*MiB};
  const result={execution_commit:head,processing_allowance:allowance,operating_limits:issued,complete_reader_phase_bytes:300*MiB,products,qualification:{z:{second:2,first:true},a:1}};assert.equal(assemblyProducts(root,JSON.stringify(result),head,allowance,issued).execution_commit,head);
  for(const edit of [r=>r.execution_commit='b'.repeat(40),r=>r.products[0].sha256='c'.repeat(64),r=>r.products[0].bytes++,r=>r.products.push(r.products[0]),r=>r.qualification={changed:true},r=>r.complete_reader_phase_bytes=allowance.phaseBytes+1,r=>r.processing_allowance.phaseBytes++,r=>r.processing_allowance.rssBytes--,r=>delete r.processing_allowance,r=>r.operating_limits.output_bytes++,r=>r.operating_limits.rss_bytes++,r=>delete r.operating_limits]){const other=structuredClone(result);edit(other);assert.throws(()=>assemblyProducts(root,JSON.stringify(other),head,allowance,issued),/Assembly|assembly/);}
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});

test('assembly current allowance is explicit, finite and bounded by its actual group guard',()=>{
 for(const phaseBytes of [256*MiB,512*MiB,640*MiB])assert.deepEqual(assemblyProcessingAllowance({phaseBytes,rssBytes:768*MiB},issued.rss_bytes),{phaseBytes,rssBytes:768*MiB});
 for(const profile of [null,{}, {phaseBytes:0,rssBytes:768*MiB},{phaseBytes:512*MiB,rssBytes:Infinity},{phaseBytes:512*MiB,rssBytes:1024*MiB+1},{phaseBytes:1024*MiB+1,rssBytes:768*MiB},{phaseBytes:512*MiB,rssBytes:768*MiB,availableBytes:2**40}])assert.throws(()=>assemblyProcessingAllowance(profile,issued.rss_bytes),/assembly|Assembly/);
});


test('issued assembly v2 changes only parameters and retains actual process guards',async()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'assembly-issued-'));
 try{
  const limits={...issued,rss_bytes:1024*MiB+1,wall_seconds:1201,output_bytes:6*MiB,retained_bytes:20*MiB};
  const result=await supervise([process.execPath,'-e','process.stdout.write("issued\\n")'],{time,ps,operation:path.join(root,'operation'),env:{...env,WORLDATLAS_CONCURRENT_RESERVED_BYTES:'0'},profile:'selected-assembly-v2',outputDirectory:path.join(root,'output'),cap:limits.rss_bytes,wall:limits.wall_seconds*1000,operatingLimits:limits});
  assert.equal(result.qualified,true);assert.equal(result.rss_cap_bytes,limits.rss_bytes);assert.equal(result.wall_deadline_seconds,1201);assert.deepEqual(result.operating_limits,limits);assert.deepEqual(result.owned_processes_remaining,[]);
  for(const mutation of [l=>l.rss_bytes=Number.MAX_SAFE_INTEGER,l=>l.wall_seconds=0,l=>l.output_bytes=l.retained_bytes,l=>l.rss_bytes=Infinity]){
   const denied=path.join(root,'not-created'),changed=structuredClone(limits);mutation(changed);
   await assert.rejects(supervise([process.execPath,'-e','process.exit(0)'],{time,ps,operation:denied,env:{...env,WORLDATLAS_CONCURRENT_RESERVED_BYTES:'0'},profile:'selected-assembly-v2',outputDirectory:path.join(root,'output'),cap:changed.rss_bytes,wall:changed.wall_seconds*1000,operatingLimits:changed}),/assembly|Assembly|supply|Finite/);
   assert.equal(fs.existsSync(denied),false);
  }
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});

test('issued assembly output and retained storage are parameterized, with exact refusal',()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'assembly-issued-storage-')),output=path.join(root,'output'),operation=path.join(root,'operation');fs.mkdirSync(output);fs.mkdirSync(operation);
 try{
  const limits={...issued,output_bytes:6*MiB,retained_bytes:20*MiB};fs.writeFileSync(path.join(output,'ledger.json'),Buffer.alloc(5*MiB));
  assert.throws(()=>assemblyStorage(output,operation),/product reserve/);
  assert.equal(assemblyStorage(output,operation,0,limits).productBytes,5*MiB);
  assert.throws(()=>assemblyStorage(output,operation,16*MiB,limits),/retained growth/);
  for(const bad of [{...limits,extra:1},{...limits,monitor_bytes:0},{...limits,log_bytes:Infinity},{...limits,wall_seconds:Number.MAX_SAFE_INTEGER}])assert.throws(()=>assemblyOperatingLimits(bad),/issued|Finite/);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});


test('assembly growth uses cooperative reservation and measured footprint without a quota',()=>{
 const GiB=1024**3,root='/owned',stock={freeBytes:20*GiB,limits:{minimumFree:10*GiB},entries:[{path:root,slot:'work',status:'ready',reservation:GiB},{path:'/peer',slot:'work',status:'ready',reservation:2*GiB}],worktrees:[{path:root,managed:true,bytes:2*GiB},{path:'/peer',managed:true,bytes:GiB}]};
 const actual=assemblyStockAdmission(stock,root,12*MiB);assert.equal(actual.own_remaining_reservation_bytes,0);assert.equal(actual.peer_remaining_reservation_bytes,GiB);assert.equal(actual.admitted_growth_bytes,12*MiB);
 for(const mutate of [s=>s.freeBytes=11*GiB,s=>s.entries[0].status='preparing',s=>s.worktrees[0].managed=false,s=>s.entries[1].reservation=Number.MAX_SAFE_INTEGER]){const bad=structuredClone(stock);mutate(bad);assert.throws(()=>assemblyStockAdmission(bad,root,12*MiB),/assembly|Assembly|Measured/);}
});


test('issued monitoring accounts actual 311-byte sample as 314-byte array with newline',()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'monitor-serialization-'));try{
  const sample={x:'x'.repeat(303)};assert.equal(Buffer.byteLength(JSON.stringify(sample)),311);assert.equal(monitoringSampleBytes(311,1),314);assert.equal(monitoringSampleBytes(0,0),3);
  const denied=path.join(root,'denied.json');assert.throws(()=>writeMonitoringSamples(denied,[sample],311),/monitoring-output-reserve/);assert.equal(fs.statSync(denied).size,314);
  const accepted=path.join(root,'accepted.json');writeMonitoringSamples(accepted,[sample],314);assert.equal(fs.statSync(accepted).size,314);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});


test('source/native v2 uses issued process/output limits while literal v1 refuses expansion',async()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'source-native-issued-'));
 try{
  const limits={...issued,rss_bytes:1024*MiB+1,wall_seconds:601,output_bytes:6*MiB,retained_bytes:20*MiB};
  for(const [name,outputBytes,qualified]of [['accepted',6*MiB,true],['refused',4*MiB,false]]){
   const output=path.join(root,name+'-output'),operation=path.join(root,name+'-operating'),bound={...limits,output_bytes:outputBytes};
   const code='const fs=require("node:fs");fs.mkdirSync('+JSON.stringify(output)+');fs.writeFileSync('+JSON.stringify(path.join(output,'facts.json'))+',JSON.stringify({padding:"x".repeat(5*1024**2)}));';
   const result=await supervise([process.execPath,'-e',code],{time,ps,operation,env:{...env,WORLDATLAS_CONCURRENT_RESERVED_BYTES:'0'},profile:'source-native-v2',outputDirectory:output,cap:bound.rss_bytes,wall:bound.wall_seconds*1000,operatingLimits:bound});
   assert.equal(result.qualified,qualified);assert.equal(result.rss_cap_bytes,bound.rss_bytes);assert.equal(result.wall_deadline_seconds,601);assert.deepEqual(result.owned_processes_remaining,[]);if(!qualified)assert.match(result.refusal,/output\/retained/);
  }
  await assert.rejects(supervise([process.execPath,'-e','process.exit(0)'],{time,ps,operation:path.join(root,'legacy-denied'),env,profile:'source-native-v1',cap:limits.rss_bytes}),/cannot be expanded/);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
