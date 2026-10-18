import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {stageProduct,admitPublication,publish} from '../scripts/prepare-delivery-handoff.mjs';
const temporary=()=>fs.mkdtempSync(path.join(os.tmpdir(),'authority-publication-test-'));
test('owned staged output publishes and resumes byte-identically with Buffer products',()=>{
 const root=temporary(),scratch=temporary();let product;
 try{const body=Buffer.alloc(200001,61);product=stageProduct([body.subarray(0,65535),body.subarray(65535)],{directory:scratch});
  const products={'large.json':product,'small.json':Buffer.from('{}\n')},destination='.cache/delivery-handoff/result';
  assert.equal(publish(root,destination,products,{test:1}).resumed,false);
  assert.deepEqual(fs.readFileSync(path.join(root,destination,'large.json')),body);
  assert.equal(publish(root,destination,products,{test:1},true).resumed,true);
  fs.writeFileSync(path.join(root,destination,'large.json'),Buffer.alloc(body.length,62));
  assert.throws(()=>publish(root,destination,products,{test:1},true),/Resumed bytes/);
 }finally{product?.close();assert.deepEqual(fs.readdirSync(scratch),[]);fs.rmSync(root,{recursive:true});fs.rmdirSync(scratch);}
});
for(const when of ['before admission','after admission'])test('staged product mutation refuses '+when,()=>{
 const root=temporary(),scratch=temporary();let product;
 try{product=stageProduct(['authentic'],{directory:scratch});const prepare=()=>admitPublication(root,'.cache/delivery-handoff/result',{'body.json':product},{});
  const complete=when==='after admission'?prepare():null;fs.writeFileSync(product.file,'corrupted');
  assert.throws(()=>complete?complete():prepare(),/Staged product/);
  assert.equal(fs.existsSync(path.join(root,'.cache/delivery-handoff/result')),false);
 }finally{product?.close();fs.rmSync(root,{recursive:true});fs.rmdirSync(scratch);}
});
test('staged products reject lookalikes and closed handles and clean failed producers',()=>{
 const root=temporary(),scratch=temporary();let product;
 try{product=stageProduct(['authentic'],{directory:scratch});
  assert.throws(()=>publish(root,'.cache/delivery-handoff/fake',{'body.json':{...product}},{}),/Safe flat/);
  product.close();assert.throws(()=>publish(root,'.cache/delivery-handoff/closed',{'body.json':product},{}),/closed/);
  const sentinel=Error('late serialization');assert.throws(()=>stageProduct((function*(){yield 'first';throw sentinel;})(),{directory:scratch}),error=>error===sentinel);
  assert.deepEqual(fs.readdirSync(scratch),[]);
 }finally{product?.close();fs.rmSync(root,{recursive:true});fs.rmdirSync(scratch);}
});
for(const resume of [false,true])test('staged publication preserves primary I/O failure when descriptor cleanup also fails: '+resume,()=>{
 const root=temporary(),scratch=temporary(),destination='.cache/delivery-handoff/result';let product;
 const original={open:fs.openSync,close:fs.closeSync,read:fs.readSync,write:fs.writeSync};let targetFd;
 const primary=Error('publication I/O sentinel'),cleanup=Error('publication close sentinel');
 try{product=stageProduct(['authentic'],{directory:scratch});const products={'body.json':product};
  if(resume)publish(root,destination,products,{});
  fs.openSync=function(file,...args){const fd=original.open.call(this,file,...args);if(file===path.join(root,destination,'body.json'))targetFd=fd;return fd;};
  fs.closeSync=function(fd){original.close.call(this,fd);if(fd===targetFd)throw cleanup;};
  fs[resume?'readSync':'writeSync']=function(fd,...args){if(fd===targetFd)throw primary;return original[resume?'read':'write'].call(this,fd,...args);};
  assert.throws(()=>publish(root,destination,products,{},resume),error=>error===primary);
 }finally{fs.openSync=original.open;fs.closeSync=original.close;fs.readSync=original.read;fs.writeSync=original.write;product?.close();fs.rmSync(root,{recursive:true});fs.rmdirSync(scratch);}
});
