import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {Writable} from 'node:stream';
import {wordAt,wordPin,gzipChunks,digest,collect} from './fixtures/native-word-store.mjs';
import {openNativeWordStore} from '../scripts/native-word-store.mjs';
const root=fs.mkdtempSync(path.join(os.tmpdir(),'ci-native-scale-controls-'));
test.after(()=>fs.rmSync(root,{recursive:true,force:true}));
const empty=()=>assert.deepEqual(fs.readdirSync(root),[],'owned native spool must be removed');
async function reject(chunks,pin,pattern){await assert.rejects(openNativeWordStore(chunks,pin,{directory:root}),pattern);empty();}
for(const words of [1,2,3,16383,16384,16385,32769])test(`all ${words} words equal independent oracle across plane/window boundaries`,async()=>{
  const pin=await wordPin(words,{chunkBytes:997}),store=await openNativeWordStore(gzipChunks(words,{chunkBytes:997}),pin,{directory:root});
  try{
    assert.equal(store.length,words);assert.ok(Object.isFrozen(store));
    for(let i=0;i<words;i++)assert.equal(store.get(i),wordAt(i));
    for(let i=words-1;i>=0;i--)assert.equal(store.get(i),wordAt(i));
    for(const index of [-1,words,.5,NaN,Infinity,Number.MAX_SAFE_INTEGER])assert.throws(()=>store.get(index),/index/);
  }finally{store.close();store.close();}
  assert.throws(()=>store.get(0),/closed/);empty();
});
test('every uint32 boundary, including high bit, stays exact',async()=>{
  const values=[0,1,255,256,65535,65536,0x7fffffff,0x80000000,0xfffffffe,0xffffffff],value=i=>values[i%values.length],words=20001;
  const pin=await wordPin(words,{value}),store=await openNativeWordStore(gzipChunks(words,{value}),pin,{directory:root});
  try{for(let i=0;i<words;i++)assert.equal(store.get(i),value(i));}finally{store.close();}empty();
});
test('wrong encoded or canonical identity and size refuse without a spool',async()=>{
  const words=32769,pin=await wordPin(words),encoded=await collect(gzipChunks(words));
  for(const changed of [{bytes:pin.bytes-1},{bytes:pin.bytes+1},{sha256:'0'.repeat(64)},{decoded_sha256:'f'.repeat(64)},{decoded_bytes:pin.decoded_bytes-4},{words:words-1,decoded_bytes:(words-1)*4},{words:words+1,decoded_bytes:(words+1)*4}])await reject([encoded],{...pin,...changed});
});
test('corrupt beginning middle and final compressed bytes even with rebound encoded hash refuse',async()=>{
  const words=32769,pin=await wordPin(words),encoded=await collect(gzipChunks(words));
  for(const index of [0,Math.floor(encoded.length/2),encoded.length-1]){const bad=Buffer.from(encoded);bad[index]^=1;await reject([bad],{...pin,sha256:digest(bad)});}
  for(const count of [1,7,8,Math.floor(encoded.length/2),encoded.length-1]){const bad=encoded.subarray(0,count);await reject([bad],{...pin,bytes:bad.length,sha256:digest(bad)});}
});
test('valid gzip with changed first middle or last word refuses canonical identity',async()=>{
  const words=32769,pin=await wordPin(words);
  for(const changed of [0,16384,words-1]){const value=i=>i===changed?wordAt(i)^1:wordAt(i),bad=await collect(gzipChunks(words,{value}));await reject([bad],{...pin,bytes:bad.length,sha256:digest(bad)});}
});
test('no store is exposed before source EOF and late source failure clears spool',async()=>{
  const words=16385,pin=await wordPin(words),encoded=await collect(gzipChunks(words));let release,finished=false;
  const boundary=new Promise(resolve=>release=resolve);
  async function* delayed(){yield encoded;await boundary;}
  const pending=openNativeWordStore(delayed(),pin,{directory:root}).then(store=>{finished=true;return store;});
  await new Promise(resolve=>setTimeout(resolve,25));assert.equal(finished,false);release();const store=await pending;store.close();empty();
  let finalized=false;async function* fails(){try{yield encoded;throw Error('late source sentinel');}finally{finalized=true;}}
  await reject(fails(),pin,/late source sentinel/);assert.equal(finalized,true);
});
test('concurrent independent stores retain no shared mutable window',async()=>{
  const words=20003,pin=await wordPin(words),other=await wordPin(words,{value:i=>(wordAt(i)+1)>>>0});
  const a=await openNativeWordStore(gzipChunks(words),pin,{directory:root}),b=await openNativeWordStore(gzipChunks(words,{value:i=>(wordAt(i)+1)>>>0}),other,{directory:root});
  try{for(const i of [0,16383,16384,20002,1]){assert.equal(a.get(i),wordAt(i));assert.equal(b.get(i),(wordAt(i)+1)>>>0);}a.close();assert.equal(b.get(0),(wordAt(0)+1)>>>0);}finally{a.close();b.close();}empty();
});
test('invalid counts and inaccessible scratch destination refuse',async()=>{
  for(const words of [0,-1,.5,NaN,Infinity,Number.MAX_SAFE_INTEGER+1])await reject([],{words,decoded_bytes:words*4});
  const pin=await wordPin(1);await assert.rejects(openNativeWordStore(gzipChunks(1),pin,{directory:path.join(root,'absent')}),/ENOENT/);empty();
});

test('disk write failure rejects and closes the input instead of returning a partial store',async()=>{
  const pin=await wordPin(65536);let closed=false;
  async function* source(){try{yield* gzipChunks(65536);}finally{closed=true;}}
  const original=fs.createWriteStream;
  fs.createWriteStream=()=>new Writable({write(chunk,encoding,done){const e=Error('synthetic ENOSPC');e.code='ENOSPC';done(e);}});
  try{await reject(source(),pin,/synthetic ENOSPC/);}finally{fs.createWriteStream=original;}
  assert.equal(closed,true);
});
