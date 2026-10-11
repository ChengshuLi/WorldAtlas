import fs from 'node:fs';import os from 'node:os';import path from 'node:path';import test from 'node:test';import assert from 'node:assert/strict';import {createHash} from 'node:crypto';
import {supervise,assemblyStorage,scientificEnvironment} from './supervise-source-native-linux.mjs';
import {assemblyProducts} from './supervise-selected-assembly-linux.mjs';
const time='/workspace/scratch/127991fc8b8e/cloud-tools/gnu-time/time-1.9-0.2-amd64/usr/bin/time',ps='/usr/bin/ps',MiB=1048576;
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
  const result={execution_commit:head,complete_reader_phase_bytes:100,products,qualification:{z:{second:2,first:true},a:1}};assert.equal(assemblyProducts(root,JSON.stringify(result),head).execution_commit,head);
  for(const edit of [r=>r.execution_commit='b'.repeat(40),r=>r.products[0].sha256='c'.repeat(64),r=>r.products[0].bytes++,r=>r.products.push(r.products[0]),r=>r.qualification={changed:true},r=>r.complete_reader_phase_bytes=268435457]){const other=structuredClone(result);edit(other);assert.throws(()=>assemblyProducts(root,JSON.stringify(other),head),/Assembly|assembly/);}
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
