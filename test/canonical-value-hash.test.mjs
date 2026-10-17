import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {valueBytes,valueSha} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';

const reference=value=>createHash('sha256').update(valueBytes(value)).digest('hex');
const equal=value=>assert.equal(valueSha(value),reference(value));

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
  }
 }
 const cyclic={};cyclic.self=cyclic;
 assert.throws(()=>valueBytes(cyclic));assert.throws(()=>valueSha(cyclic),/Circular/);
 let deep=0;for(let i=0;i<20000;i++)deep=[deep];
 assert.throws(()=>valueBytes(deep));assert.throws(()=>valueSha(deep));
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
 }
});
