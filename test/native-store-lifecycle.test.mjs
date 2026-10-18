import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {admitNativeMetadataStore,authenticatedDecodedNativeChunks} from '../scripts/native-patch-store.mjs';
const sha=raw=>createHash('sha256').update(raw).digest('hex');
for(const primary of ['read','syntax','hash','none'])for(const cleanup of ['none','iterator','descriptors','both'])
 test(`store preserves ${primary} failure with ${cleanup} cleanup`,async()=>{
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'store-lifecycle-'));
  const raw=Buffer.from(primary==='syntax'?'{"x":}':'{"x":1}');
  const readError=Error('primary read'),iteratorError=Error('iterator close'),fdError=Error('descriptor close');
  const original={open:fs.openSync,close:fs.closeSync,rm:fs.rmSync};const handles=new Set();let closes=0,returns=0,step=0;
  fs.openSync=(...args)=>{const fd=original.open(...args);handles.add(fd);return fd;};
  fs.closeSync=fd=>{original.close(fd);handles.delete(fd);closes++;if(['descriptors','both'].includes(cleanup))throw fdError;};
  fs.rmSync=(...args)=>{original.rm(...args);if(cleanup==='both')throw Error('remove close');};
  const chunks={ [Symbol.asyncIterator](){return this;},async next(){if(primary==='read')throw readError;return step++?{done:true}:{done:false,value:raw};},async return(){returns++;if(['iterator','both'].includes(cleanup))throw iteratorError;return {done:true};}};
  let caught,failed=false,store;
  try{try{store=await admitNativeMetadataStore({directory,chunks,expected:{bytes:raw.length,sha256:primary==='hash'?'0'.repeat(64):sha(raw)}});store.close();}catch(error){failed=true;caught=error;}
   if(primary==='read')assert.equal(caught,readError);
   else if(primary==='syntax')assert.ok(caught instanceof SyntaxError);
   else if(primary==='hash')assert.equal(caught.message,'Complete native JSON identity differs');
   else if(['iterator','both'].includes(cleanup))assert.equal(caught,iteratorError);
   else if(cleanup==='descriptors')assert.equal(caught,fdError);
   else assert.equal(failed,false);
   assert.equal(returns,1);assert.ok(closes>=4);assert.equal(handles.size,0);assert.deepEqual(fs.readdirSync(directory),[]);
  }finally{fs.openSync=original.open;fs.closeSync=original.close;fs.rmSync=original.rm;original.rm(directory,{recursive:true});}
 });
test('falsy primary failure survives cleanup failure',async()=>{
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'store-falsy-'));
 const chunks={[Symbol.asyncIterator](){return this;},async next(){throw false;},async return(){throw Error('cleanup');}};
 try{let failed=false;try{await admitNativeMetadataStore({directory,chunks,expected:{bytes:10,sha256:"0".repeat(64)}});}catch(error){failed=true;assert.equal(error,false);}assert.ok(failed);assert.deepEqual(fs.readdirSync(directory),[]);}
 finally{fs.rmSync(directory,{recursive:true});}
});
test('pending input cancellation keeps abort and cleans spill despite iterator close error',async()=>{
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'store-abort-'));const controller=new AbortController();const abort=new DOMException('cancelled','AbortError');let requested;const ready=new Promise(r=>requested=r);let step=0;
 const chunks={[Symbol.asyncIterator](){return this;},async next(){if(!step++)return {value:Buffer.from('{"x":'),done:false};requested();return new Promise((resolve,reject)=>controller.signal.addEventListener('abort',()=>reject(abort),{once:true}));},async return(){throw Error('cleanup');}};
 try{const admission=admitNativeMetadataStore({directory,chunks,expected:{bytes:10,sha256:"0".repeat(64)}});const observed=admission.then(()=>assert.fail('accepted cancellation'),error=>assert.equal(error,abort));await ready;controller.abort();await observed;assert.deepEqual(fs.readdirSync(directory),[]);}
 finally{fs.rmSync(directory,{recursive:true});}
});
test('encoded custody keeps primary producer error and attempts every cleanup',async()=>{
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'custody-cleanup-'));const primary=Error('encoded producer');const original={close:fs.closeSync,rm:fs.rmSync};let closes=0,removes=0;
 fs.closeSync=fd=>{original.close(fd);closes++;throw Error('close');};fs.rmSync=(...args)=>{original.rm(...args);removes++;throw Error('remove');};
 try{await assert.rejects(async()=>{for await(const chunk of authenticatedDecodedNativeChunks((async function*(){yield Buffer.from('x');throw primary;})(),{decoded_bytes:1},{directory}))void chunk;},error=>error===primary);assert.equal(closes,1);assert.equal(removes,1);assert.deepEqual(fs.readdirSync(directory),[]);}
 finally{fs.closeSync=original.close;fs.rmSync=original.rm;original.rm(directory,{recursive:true});}
});
