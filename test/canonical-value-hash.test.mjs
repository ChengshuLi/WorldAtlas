import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {valueBytes,valueSha,valueIdentity} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';

const reference=value=>createHash('sha256').update(valueBytes(value)).digest('hex');
const equal=value=>{
 const bytes=valueBytes(value),sha256=reference(value);
 assert.equal(valueSha(value),sha256);
 assert.deepEqual(valueIdentity(value),{sha256,bytes:bytes.length});
};

test('bounded hash preserves canonical scalar, numeric and property-order bytes',()=>{
 for(const value of [null,true,false,0,-0,1,Number.MIN_VALUE,Number.MAX_VALUE,1e-7,1e21,
  '', '"\\\b\f\n\r\t', '\u0000\u001f\u2028\u2029', '\ud800','\udc00','\ud800\udc00',
  {z:1,a:2,'10':3,'2':4,'0':5,'01':6,'-0':7,'4294967294':8,'4294967295':9,'1e0':10},
  JSON.parse('{"__proto__":{"constructor":1},"a":null}'),Object.create(null),
  [[],{},[null,1]],new Uint8Array([7,8]),new Date(0)])equal(value);
 const sparse=[];sparse.length=5;sparse[3]='present';equal(sparse);
 const shared={x:[1,2,3]};equal([shared,shared]);
});

test('bounded hash preserves long Unicode strings across every chunk boundary',()=>{
 for(const start of [8190,8191,8192,8193,16382,16383,16384]){
  const value='a'.repeat(start)+'😀\ud800\udc00\ud800x\udc00\\"\n'+'漢字'.repeat(10000);
  equal(value);equal({[value]:[value]});
 }
 equal(String.fromCharCode(...Array.from({length:65536},(_,i)=>i)));
});

test('bounded hash matches literal serializer on deterministic nested values',()=>{
 let seed=0x8cf013a1;
 const random=()=>((seed=(Math.imul(seed,1664525)+1013904223)>>>0)/2**32);
 const scalar=()=>[null,random()<.5,Math.floor(random()*1e6)-5e5,'é\\"'+random()+'😀'][Math.floor(random()*4)];
 const value=depth=>{
  if(!depth||random()<.3)return scalar();
  const count=Math.floor(random()*8);
  if(random()<.5)return Array.from({length:count},()=>value(depth-1));
  const result=Object.create(null);
  for(let i=0;i<count;i++)result[['10','2','01','__proto__','4294967295','z','a'][i]]=value(depth-1);
  return result;
 };
 for(let i=0;i<500;i++)equal(value(5));
});

test('bounded hash keeps invalid JSON values refused and does not cache mutable input',()=>{
 for(const bad of [undefined,NaN,Infinity,-Infinity,1n,()=>1,Symbol('x')]){
  for(const value of [bad,[bad],{bad}]){
   assert.throws(()=>valueBytes(value),/Nonfinite\/missing\/non-JSON/);
   assert.throws(()=>valueSha(value),/Nonfinite\/missing\/non-JSON/);
   assert.throws(()=>valueIdentity(value),/Nonfinite\/missing\/non-JSON/);
  }
 }
 const cyclic={};cyclic.self=cyclic;
 assert.throws(()=>valueBytes(cyclic));assert.throws(()=>valueSha(cyclic),/Circular/);assert.throws(()=>valueIdentity(cyclic),/Circular/);
 let deep=0;for(let i=0;i<20000;i++)deep=[deep];
 assert.throws(()=>valueBytes(deep));assert.throws(()=>valueSha(deep));assert.throws(()=>valueIdentity(deep));
 const value={rows:[[1,2,3]]},before=valueSha(value);value.rows[0][2]=4;
 assert.notEqual(valueSha(value),before);equal(value);
 let nested=0;for(let i=0;i<256;i++)nested={value:[nested]};equal(nested);
});

test('bounded hash digests a large shared graph under the ordinary fixed child heap',()=>{
 const module=new URL('../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs',import.meta.url).href;
 const script=`import {valueSha} from ${JSON.stringify(module)};
  const leaf={geometry:{coordinates:Array.from({length:1000},(_,i)=>[i/10,-i/10])},id:'shared'};
  const value={rows:Array.from({length:2000},()=>leaf)};
  console.log(JSON.stringify({digest:valueSha(value),maxRSS:process.resourceUsage().maxRSS}));`;
 const result=spawnSync(process.execPath,['--max-old-space-size=64','--input-type=module','-e',script],
  {encoding:'utf8',timeout:60000,env:{...process.env,NODE_OPTIONS:'',NODE_PATH:''}});
 assert.equal(result.status,0,result.stderr);assert.equal(result.signal,null);
 assert.equal(JSON.parse(result.stdout).digest,'4cf767734719dc5519eba8ce6de316f4f0a860882b21b240ff305045f3e3ec0c');
});

test('numeric triple fast path preserves JSON numeric formatting and generic refusals',()=>{
 for(const triple of [[-0,0,1],[1e-7,1e21,5e-324],[Number.MAX_VALUE,-Number.MAX_VALUE,1.0000000000000002],[null,1,2],[,1,2],[1,,2],[1,2,]])equal(triple);
 for(const bad of [[NaN,1,2],[1,Infinity,2],[1,2,undefined]]){
  assert.throws(()=>valueBytes(bad),/Nonfinite\/missing\/non-JSON/);
  assert.throws(()=>valueSha(bad),/Nonfinite\/missing\/non-JSON/);
  assert.throws(()=>valueIdentity(bad),/Nonfinite\/missing\/non-JSON/);
 }
});

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {nativeSequence,isNativeSequence} from '../src/native-grid.js';
import {admitNativeMetadataStore} from '../scripts/native-patch-store.mjs';

test('canonical identity traverses repeatable sequences once without whole-value serialization',()=>{
 const literal={coordinates:Array.from({length:65},(_,i)=>[i,-i]),label:'雪😀'.repeat(8193)};
 const bytes=valueBytes(literal),expected={bytes:bytes.length,sha256:reference(literal)};
 let visits=0;
 const value={...literal,coordinates:nativeSequence(literal.coordinates.length,function*(){for(const pair of literal.coordinates){visits++;yield pair;}})};
 const stringify=JSON.stringify;let actual;
 JSON.stringify=value=>{
  assert.ok(value===null||typeof value!=='object','identity must not reconstruct an entire graph for JSON.stringify');
  return stringify(value);
 };
 try{actual=valueIdentity(value);}finally{JSON.stringify=stringify;}
 assert.deepEqual(actual,expected);assert.equal(visits,65);
 literal.coordinates.at(-1)[1]=999;
 assert.notDeepEqual(valueIdentity(value),expected);equal(value);
 for(const [length,values]of [[2,[1]],[1,[1,2]]]){
  const sequence=nativeSequence(length,()=>values.values());
  assert.throws(()=>valueIdentity(sequence),/declared/);
 }
 for(const failure of [Error('iterator failure'),false,undefined]){
  let closed=false;
  const sequence=nativeSequence(2,function*(){try{yield 1;throw failure;}finally{closed=true;}});
  let caught=false;try{valueIdentity(sequence);}catch(error){caught=true;assert.strictEqual(error,failure);}
  assert.equal(caught,true);assert.equal(closed,true);
 }
});

test('canonical identity consumes genuine stored coordinates and rejects closed or nonfinite stores',async t=>{
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'canonical-identity-'));t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
 for(const count of [31,32,33,65]){
  const literal={coordinates:[Array.from({length:count},(_,i)=>[i===0?-0:i/10,-i/10])],label:'雪😀\ud800', '10':1,'2':2};
  const raw=Buffer.from(JSON.stringify(literal,null,2)),bytes=valueBytes(literal);
  const store=await admitNativeMetadataStore({directory,chunks:(function*(){for(let i=0;i<raw.length;i+=7)yield raw.subarray(i,i+7);})(),expected:{bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex')}});
  try{
   assert.deepEqual(valueIdentity(store.metadata),{bytes:bytes.length,sha256:reference(literal)});
   assert.deepEqual(valueBytes(store.metadata),bytes);
   if(count>32)assert.equal(Array.isArray(store.metadata.coordinates[0]),false);
   assert.ok(isNativeSequence(store.metadata.coordinates[0]));
  }finally{store.close();}
  if(count>32)assert.throws(()=>valueIdentity(store.metadata),/closed/);
  assert.deepEqual(fs.readdirSync(directory),[]);
 }
 const raw=Buffer.from('{"coordinates":['+Array.from({length:33},()=> '[1,2]').join(',')+',[1e400,2]]}');
 const store=await admitNativeMetadataStore({directory,chunks:[raw],expected:{bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex')}});
 try{assert.throws(()=>valueIdentity(store.metadata),/Nonfinite\/missing\/non-JSON/);}finally{store.close();}
 assert.deepEqual(fs.readdirSync(directory),[]);
});
