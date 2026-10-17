import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {admitNativeLedgerStore} from '../scripts/native-patch-store.mjs';
import {valueBytes} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const hash=body=>createHash('sha256').update(body).digest('hex');
const temporary=t=>{const dir=fs.mkdtempSync(path.join(os.tmpdir(),'ledger-store-test-'));t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));return dir;};
const chunks=function*(body,width=29){for(let i=0;i<body.length;i+=width)yield body.subarray(i,i+width);};
const open=(directory,text,options={})=>{const body=Buffer.from(text);return admitNativeLedgerStore({directory,size:100,ownerCount:10,chunks:chunks(body),expected:{bytes:body.length,sha256:hash(body)},...options});};
const materialize=(store,component)=>({...store.componentMetadata(component),...(component.hasNativeRows?{native_rows:[...store.componentRows(component)].map(row=>({y:row.y,runs:[...store.intervals(row)]}))}:{})});

test('ledger stores complete ordered components, metadata, native rows and both raw/normalized canonical identities',async t=>{
 const directory=temporary(t),value={version:3,scope_ids:['A','B','C'],rows:[
  {component_id:'A',geometry:{type:'Polygon',coordinates:[[[0,0],[1,1]]]},native_rows:[{y:1,runs:[[0,2,1]]}],pixelIndex:1},
  {component_id:'B',base_geometry:{type:'Polygon',coordinates:[]},disposition:'held',extra:{unknown:'kept'}},
  {component_id:'C',native_rows:[{y:0,runs:[]},{y:2,runs:[[3,9,2]]}],pixelIndex:2}
 ]};
 const store=await open(directory,JSON.stringify(value,null,2));
 assert.equal(store.canonical_sha256,hash(valueBytes(value)));assert.equal(store.componentCount,3);assert.equal(store.nativeRowCount,3);assert.equal(store.runCount,2);
 const all=[...store.componentEntries()];assert.deepEqual(all.map(c=>materialize(store,c)),value.rows);
 for(const component of all){
  assert.equal(component.canonical_sha256,hash(valueBytes(value.rows[component.ordinal])));
  assert.equal([...store.componentCanonicalChunks(component)].join(''),valueBytes(value.rows[component.ordinal]).toString());
  const overrides={rule_sha256:'a'.repeat(64),authority_sha256:'b'.repeat(64)};
  assert.equal([...store.componentCanonicalChunks(component,{overrides})].join(''),valueBytes({...value.rows[component.ordinal],...overrides}).toString());
  assert.equal([...store.componentCanonicalChunks(component,{newline:false})].join('')+'\n',valueBytes(value.rows[component.ordinal]).toString());
  assert(Object.isFrozen(store.componentMetadata(component)));
 }
 assert.throws(()=>store.componentMetadata({...all[0]}),/Foreign/);
 assert.throws(()=>[...store.componentCanonicalChunks(all[0],{overrides:{native_rows:[]}})],/cannot replace/);
 const first=store.componentEntries(),second=store.componentEntries();assert.deepEqual(first.next().value,second.next().value);
 store.close();assert.throws(()=>first.next(),/closed/);assert.throws(()=>store.componentMetadata(all[0]),/closed/);assert.deepEqual(fs.readdirSync(directory),[]);
});

test('ledger duplicate root/component/native row fields preserve final JSON semantics without materializing dense rows',async t=>{
 const directory=temporary(t);
 for(const text of [
  '{"rows":false,"rows":[{"component_id":"A"}]}',
  '{"rows":[2,{"native_rows":false}],"rows":[]}',
  '{"rows":[{"native_rows":false,"native_rows":[{"y":-2,"y":0,"runs":null,"runs":[[0,1,1]]}],"component_id":"old","component_id":"new"}]}',
  '{"rows":[{"native_rows":[{"y":0,"runs":[[0,2,1]]}],"native_rows":[]}],"rows":[{"native_rows":[],"x":{"__proto__":1}}]}',
  '{"rows":[{"bad":1e400}],"rows":[{"native_rows":[],"bad":1}]}',
  '{"rows":[{"pixelIndex":1,"native_rows":[{"y":2,"runs":[[8,9,1]]}],"disposition":"held","native_rows":[{"y":0,"runs":[[1,3,2]]}],"pixelIndex":2,"disposition":"assigned"}]}',
  '{"rows":[],"__proto__":{"x":2},"rows":[{"__proto__":{"y":3},"2":false,"10":true}]}'
 ]){
  const store=await open(directory,text),value=JSON.parse(text);
  assert.equal(store.canonical_sha256,hash(valueBytes(value)));assert.deepEqual([...store.componentEntries()].map(c=>materialize(store,c)),value.rows);store.close();
 }
 assert.deepEqual(fs.readdirSync(directory),[]);
});

test('ledger metadata larger than writer windows is retained exactly one component at a time',async t=>{
 const directory=temporary(t),value={rows:[{component_id:'large',text:'x😀'.repeat(30000),native_rows:[{y:0,runs:[[0,1,1]]}]}]};
 const store=await open(directory,JSON.stringify(value));const [component]=store.componentEntries();
 assert.equal(store.canonical_sha256,hash(valueBytes(value)));assert.deepEqual(materialize(store,component),value.rows[0]);store.close();
 assert.deepEqual(fs.readdirSync(directory),[]);
});

test('ledger malformed syntax, final domain errors and late identity failures return no admitted component',async t=>{
 const directory=temporary(t);
 for(const text of ['{"rows":[{"native_rows":[],}],"rows":[]}','{"rows":[{"x":01}],"rows":[]}',
  '{"rows":[{"native_rows":[{"y":0,"runs":[[0,1,1]]}]}]} true','{"rows":[null]}',
  '{"rows":[{"native_rows":false}]}','{"rows":[{"native_rows":[{"y":0,"runs":[[0,101,1]]}]}]}',
  '{"rows":[{"x":1e400}]}']){
  await assert.rejects(open(directory,text));assert.deepEqual(fs.readdirSync(directory),[]);
 }
 const text='{"rows":[{"native_rows":[{"y":0,"runs":[[0,1,1]]}]}]}';
 await assert.rejects(open(directory,text,{expected:{bytes:Buffer.byteLength(text),sha256:'0'.repeat(64)}}),/identity/);
 assert.deepEqual(fs.readdirSync(directory),[]);
});

test('ledger runtime read/write failures cannot be excused by a later duplicate rows field',async t=>{
 const directory=temporary(t),text='{"rows":[{"native_rows":[{"y":0,"runs":[[0,1,1]]}]}],"rows":[]}';
 for(const method of ['readSync','writeSync']){
  t.mock.method(fs,method,()=>{throw Error('real disk failure '+method);});
  await assert.rejects(open(directory,text),/real disk failure/);t.mock.restoreAll();
  assert.deepEqual(fs.readdirSync(directory),[]);
 }
});

test('ledger component and dense-row ingestion retains bounded working graphs under a 64MiB child heap',async t=>{
 const directory=temporary(t),module=new URL('../scripts/native-patch-store.mjs',import.meta.url).href;
 const script=`import {admitNativeLedgerStore} from ${JSON.stringify(module)};import {createHash} from 'node:crypto';
  function* chunks(){yield Buffer.from('{"rows":[');for(let c=0;c<4;c++){yield Buffer.from((c?',':'')+'{"component_id":"'+c+'","native_rows":[{"runs":[');
   for(let i=0;i<100000;i++)yield Buffer.from((i?',':'')+JSON.stringify([i*2,i*2+1,c+1]));yield Buffer.from('],"y":0}]}');}yield Buffer.from(']}\\n');}
  let bytes=0;const hash=createHash('sha256');for(const chunk of chunks()){bytes+=chunk.length;hash.update(chunk);}const sha256=hash.digest('hex');
  const store=await admitNativeLedgerStore({directory:${JSON.stringify(directory)},size:200000,ownerCount:4,chunks:chunks(),expected:{bytes,sha256}});
  let count=0;for(const component of store.componentEntries())for(const row of store.componentRows(component))for(const run of store.intervals(row))count++;
  console.log(JSON.stringify({count,componentCount:store.componentCount,sha256,canonical:store.canonical_sha256,maxRSS:process.resourceUsage().maxRSS}));store.close();`;
 const result=spawnSync(process.execPath,['--max-old-space-size=64','--input-type=module','-e',script],{encoding:'utf8',timeout:120000,env:{...process.env,NODE_OPTIONS:'',NODE_PATH:''}});
 assert.equal(result.status,0,result.stderr);const observed=JSON.parse(result.stdout);
 assert.equal(observed.count,400000);assert.equal(observed.componentCount,4);assert.equal(observed.canonical,observed.sha256);assert.deepEqual(fs.readdirSync(directory),[]);
});
