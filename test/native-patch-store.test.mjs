import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {admitNativePatchStore,admitNativeLedgerStore} from '../scripts/native-patch-store.mjs';
import {valueBytes} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const hash=body=>createHash('sha256').update(body).digest('hex');
const temporary=t=>{const dir=fs.mkdtempSync(path.join(os.tmpdir(),'patch-store-test-'));t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));return dir;};
const chunks=function*(body,width=7){for(let i=0;i<body.length;i+=width)yield body.subarray(i,i+width);};
const open=(directory,text,options={})=>{const body=Buffer.from(text);return admitNativePatchStore({directory,size:100,ownerCount:10,chunks:chunks(body),expected:{bytes:body.length,sha256:hash(body)},...options});};
const materialize=store=>({...store.metadata,rows:[...store.rowEntries()].map(row=>({y:row.y,runs:[...store.intervals(row)]}))});

test('native JSON disk store preserves complete bytes, canonical hash and private row cursors',async t=>{
 const directory=temporary(t),text=' {"rows": [ {"y": 0, "runs": []}, {"y": 3, "runs":[[0,2,1],[4,9,2]]} ], "z":"😀\\ud800", "2":null, "10":true,"a":{"b":2,"a":1}}\n';
 const value=JSON.parse(text),store=await open(directory,text);
 assert.deepEqual(materialize(store),value);assert.equal(store.canonical_sha256,hash(valueBytes(value)));
 assert.equal(store.rowCount,2);assert.equal(store.runCount,2);assert.equal(store.storedBytes,2*16+2*12);
 assert.equal(store.rowAt(2),null);assert.deepEqual([...store.intervals(store.rowAt(3))],value.rows[1].runs);
 assert.throws(()=>[...store.intervals({...store.rowAt(3)})],/Foreign/);
 const row=store.rowAt(3);store.close();assert.deepEqual(fs.readdirSync(directory),[]);
 assert.throws(()=>[...store.intervals(row)],/closed/);assert.throws(()=>store.rowAt(3),/closed/);store.close();
});

test('native JSON duplicate keys keep literal last-key-wins including overwritten invalid domain values',async t=>{
 const directory=temporary(t);
 for(const text of [
  '{"rows":null,"rows":[{"runs":[],"y":0}]}',
  '{"rows":[{"y":-4,"runs":[[3,1,100]]}],"rows":[{"y":3,"runs":[[1,2,1]]}]}',
  '{"rows":[{"y":false,"runs":null,"y":2,"runs":[[0,1,2]]}]}',
  '{"rows":[{"y":2,"runs":[[5,6,1]],"runs":[[0,1,2],[2,3,2]]}],"a":false,"a":{"__proto__":true}}',
  '{"rows":[{"extra":1}],"rows":[]}',
  '{"rows":[],"__proto__":{"x":1},"__proto__":{"x":2}}'
 ]){
  const store=await open(directory,text),value=JSON.parse(text);
  assert.deepEqual(materialize(store),value);assert.equal(store.canonical_sha256,hash(valueBytes(value)));store.close();
 }
 assert.deepEqual(fs.readdirSync(directory),[]);
});

test('native JSON parser rejects malformed full syntax even in overwritten fields and cleans partial stores',async t=>{
 const directory=temporary(t);
 for(const text of ['{"rows":[1,],"rows":[]}','{"rows":[],}','{"rows":[]} {}','{"rows":[],"x":01}',
  '{"rows":[],"x":1.}','{"rows":[{"runs":[[0,1,1],],"y":0}]}','{"rows":[],"x":"\\uZZZZ"}',
  '{"rows":[],"x":"a\u0001"}','{"rows":[]','{"rows":[],"x":Infinity}',
  '{"rows":[],"x":1 2}','{"rows":[],"x":{"a":1,}}']){
  assert.throws(()=>JSON.parse(text));await assert.rejects(open(directory,text));assert.deepEqual(fs.readdirSync(directory),[]);
 }
 const body=Buffer.from('{"rows":[{"y":0,"runs":[[0,1,1]]}]}');
 for(let cut=0;cut<body.length;cut++){
  const text=body.subarray(0,cut).toString();await assert.rejects(open(directory,text));assert.deepEqual(fs.readdirSync(directory),[]);
 }
});

test('native JSON final domains reject incomplete rows, interval counts, ordering and owners',async t=>{
 const directory=temporary(t);
 for(const value of [[1,2],{},{rows:null},{rows:[1]},{rows:[{y:0,runs:[],extra:true}]},{rows:[{y:0}]},
  {rows:[{y:-1,runs:[]}]},{rows:[{y:100,runs:[]}]},{rows:[{y:2,runs:[]},{y:2,runs:[]}]},
  ...[[0,0,1],[-1,2,1],[0,101,1],[0,1,0],[0,1,11],[0,1.5,1],[0,1,1,1],['0',1,1],null].map(run=>({rows:[{y:0,runs:[run]}]})),
  {rows:[{y:0,runs:[[0,3,1],[2,4,1]]}]}, {rows:[],unknown:Infinity}]){
  // Infinity is serialized as null by JSON, so use its genuine JSON numeric form.
  const text=value.unknown===Infinity?'{"rows":[],"unknown":1e400}':JSON.stringify(value);
  await assert.rejects(open(directory,text));assert.deepEqual(fs.readdirSync(directory),[]);
 }
});

test('native JSON full stream identity and producer failure precede admission',async t=>{
 const directory=temporary(t),text='{"rows":[{"y":0,"runs":[[0,1,1]]}]}',body=Buffer.from(text);
 for(const expected of [{bytes:body.length,sha256:'0'.repeat(64)},{bytes:body.length+1,sha256:hash(body)},
  {bytes:body.length-1,sha256:hash(body)}]){
  await assert.rejects(open(directory,text,{expected}));assert.deepEqual(fs.readdirSync(directory),[]);
 }
 async function* failed(){yield body;throw Error('producer failed after valid JSON');}
 await assert.rejects(open(directory,text,{chunks:failed()}),/producer failed/);assert.deepEqual(fs.readdirSync(directory),[]);
 const source={async *[Symbol.asyncIterator](){try{yield body;}finally{throw Error('iterator cleanup failed');}}};
 await assert.rejects(open(directory,text,{chunks:source}),/iterator cleanup failed/);assert.deepEqual(fs.readdirSync(directory),[]);
});

test('native component row field retains independent metadata and canonical identity',async t=>{
 const directory=temporary(t),value={native_rows:[{y:1,runs:[[0,2,3]]}],target_id:'A',pixelIndex:3};
 const store=await open(directory,JSON.stringify(value),{rowField:'native_rows'});
 assert.deepEqual({...store.metadata,native_rows:materialize(store).rows},value);
 assert.equal(store.canonical_sha256,hash(valueBytes(value)));store.close();
});

test('native JSON scalar and surrogate semantics survive every byte split',async t=>{
 const directory=temporary(t),text='{"rows":[{"runs":[[0e0,1e1,2]],"y":-0}],"s":"😀\\ud800\\udc00\\ud800x\\udc00","n":9007199254740993,"proto":{"__proto__":1}}';
 const body=Buffer.from(text),value=JSON.parse(text);
 for(let width=1;width<=body.length;width++){
  const store=await open(directory,text,{chunks:chunks(body,width)});
  assert.equal(store.canonical_sha256,hash(valueBytes(value)));
  // Private integer cursors normalize negative zero exactly as canonical JSON does.
  assert.deepEqual(materialize(store),JSON.parse(valueBytes(value)));store.close();
 }
});

test('dense native row ingestion and iteration stay within a fixed 64MiB child heap',async t=>{
 const directory=temporary(t),module=new URL('../scripts/native-patch-store.mjs',import.meta.url).href;
 const script=`import {admitNativePatchStore,admitNativeLedgerStore} from ${JSON.stringify(module)};import {createHash} from 'node:crypto';
  function* chunks(){yield Buffer.from('{"rows":[{"runs":[');for(let i=0;i<250000;i++)yield Buffer.from((i?',':'')+JSON.stringify([i*2,i*2+1,1]));yield Buffer.from('],"y":0}]}\\n');}
  let bytes=0;const hash=createHash('sha256');for(const chunk of chunks()){bytes+=chunk.length;hash.update(chunk);}const sha256=hash.digest('hex');
  const store=await admitNativePatchStore({directory:${JSON.stringify(directory)},size:500000,ownerCount:1,chunks:chunks(),expected:{bytes,sha256}});
  let count=0,last;for(const row of store.rowEntries())for(const run of store.intervals(row)){count++;last=run;}
  console.log(JSON.stringify({count,last,sha256,canonical:store.canonical_sha256,maxRSS:process.resourceUsage().maxRSS}));store.close();`;
 const result=spawnSync(process.execPath,['--max-old-space-size=64','--input-type=module','-e',script],
  {encoding:'utf8',timeout:120000,env:{...process.env,NODE_OPTIONS:'',NODE_PATH:''}});
 assert.equal(result.status,0,result.stderr);const observed=JSON.parse(result.stdout);
 assert.equal(observed.count,250000);assert.deepEqual(observed.last,[499998,499999,1]);assert.equal(observed.canonical,observed.sha256);
 assert.deepEqual(fs.readdirSync(directory),[]);
});


test('native JSON deterministic bounded patches equal the materialized canonical reference',async t=>{
 const directory=temporary(t);let seed=981723;
 const next=max=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed%max;};
 for(let sample=0;sample<180;sample++){
  const rows=[];let y=-1;
  for(let r=0,n=next(12);r<n;r++){
   y+=1+next(4);const runs=[];let end=0;
   for(let i=0,n=next(12);i<n;i++){const start=end+next(3);end=start+1+next(3);runs.push([start,end,1+next(10)]);}
   rows.push(sample%2?{runs,y}:{y,runs});
  }
  const value={version:1,rows,note:{'10':10,'2':2,'01':'key',nested:[null,false,'\"\\😀']}};
  const text=JSON.stringify(value,null,sample%3?0:2),store=await open(directory,text);
  assert.deepEqual(materialize(store),value);assert.equal(store.canonical_sha256,hash(valueBytes(value)));store.close();
 }
 assert.deepEqual(fs.readdirSync(directory),[]);
});

test('native scratch must be ordinary and cursor read failures remain visible',async t=>{
 const directory=temporary(t),link=directory+'-link';fs.symlinkSync(directory,link);t.after(()=>fs.rmSync(link,{force:true}));
 await assert.rejects(open(link,'{"rows":[]}'),/Nonordinary/);assert.deepEqual(fs.readdirSync(directory),[]);
 const store=await open(directory,'{"rows":[{"y":0,"runs":[[0,1,1]]}]}');
 const row=store.rowAt(0),root=path.join(directory,fs.readdirSync(directory)[0]);
 fs.truncateSync(path.join(root,'runs.bin'),0);
 assert.throws(()=>[...store.intervals(row)],/Incomplete native interval store/);
 store.close();assert.deepEqual(fs.readdirSync(directory),[]);
});


test('native JSON hashes and parses the same snapshot when a producer later mutates a yielded buffer',async t=>{
 const directory=temporary(t),text='{"rows":[{"y":0,"runs":[[0,1,1]]}]}',body=Buffer.from(text);
 const source={ [Symbol.asyncIterator](){let first=true;return {next(){if(!first)return {done:true};first=false;
  // This runs after Input.available has resumed and copied/hashed the chunk,
  // while its parser is suspended at the next ordinary async boundary.
  queueMicrotask(()=>queueMicrotask(()=>body.fill(32)));
  return {done:false,value:body};}};}};
 const store=await open(directory,text,{chunks:source});assert.deepEqual(materialize(store),JSON.parse(text));
 assert.equal(store.canonical_sha256,hash(valueBytes(JSON.parse(text))));store.close();
 assert.deepEqual(fs.readdirSync(directory),[]);
});


test('native scratch allocation and admission setup failures acquire no leaked producer or files',async t=>{
 const directory=temporary(t);let acquisitions=0;
 const source={[Symbol.iterator](){acquisitions++;return [Buffer.from('{"rows":[]}')][Symbol.iterator]();}};
 t.mock.method(fs,'mkdtempSync',()=>{throw Object.assign(Error('scratch full'),{code:'ENOSPC'});});
 await assert.rejects(open(directory,'{"rows":[]}',{chunks:source}),/scratch full/);
 assert.equal(acquisitions,0);assert.deepEqual(fs.readdirSync(directory),[]);
 t.mock.restoreAll();
 await assert.rejects(open(directory,'{"rows":[]}',{chunks:source,expected:{bytes:-1,sha256:'bad'}}),/identity/);
 assert.equal(acquisitions,0);assert.deepEqual(fs.readdirSync(directory),[]);
});


test('native merge cursors can share a fixed prefetch budget using single-record windows',async t=>{
 const directory=temporary(t),value={rows:[{y:0,runs:[[0,1,1],[2,3,2]]},{y:2,runs:[[4,5,3]]}]};
 const store=await open(directory,JSON.stringify(value));
 const rows=[...store.rowEntries({windowRecords:1})].map(row=>({y:row.y,runs:[...store.intervals(row,{windowRecords:1})]}));
 assert.deepEqual(rows,value.rows);assert.throws(()=>[...store.rowEntries({windowRecords:0})],/cursor window/);
 store.close();assert.deepEqual(fs.readdirSync(directory),[]);
});

// The complete-chunk case actually exercises synchronous tuple admission; every
// two-chunk cut exercises the unchanged grammar whenever that tuple is split.
const chunkCuts=function*(body){yield [body];for(let cut=0;cut<=body.length;cut++)yield [body.subarray(0,cut),body.subarray(cut)];};
test('native inline triples preserve exact records and metadata at every chunk cut',async t=>{
 const directory=temporary(t),text=' {"rows":[{"y":0,"runs":[ [0,10,1],\t[10, 4294967295,\r\n4294967295] ]}],"[0,1,1]":"[0,1,1] 😀\\ud800","array":[0,1,1],"__proto__":{"runs":"[0,1,1]"}}\n';
 const body=Buffer.from(text),value=JSON.parse(text),expected=Buffer.alloc(24);
 [0,10,1,10,4294967295,4294967295].forEach((n,i)=>expected.writeUInt32LE(n,i*4));
 for(const parts of chunkCuts(body)){
  const store=await open(directory,text,{chunks:parts,size:0xffffffff,ownerCount:0xffffffff});
  try{
   assert.deepEqual({...materialize(store),array:[...store.metadata.array]},value);assert.equal(store.canonical_sha256,hash(valueBytes(value)));
   assert.equal(store.rowCount,1);assert.equal(store.runCount,2);
   assert.deepEqual(fs.readFileSync(path.join(directory,fs.readdirSync(directory)[0],'runs.bin')),expected);
  }finally{store.close();}
 }
 assert.deepEqual(fs.readdirSync(directory),[]);
});

test('native inline triples leave noncanonical numbers to the complete JSON grammar',async t=>{
 const directory=temporary(t);
 for(const tuple of ['[-0,1.0,1e0]','[0e99,10e-1,0.1e1]','[1e-324,1.00000000000000001,1E+0]',
  '[0,4294967295.0000001,4294967295]','[0,1,4294967295.0]']){
  const text='{"rows":[{"y":0,"runs":['+tuple+']}]}',body=Buffer.from(text),value=JSON.parse(valueBytes(JSON.parse(text)));
  for(const parts of chunkCuts(body)){
   const store=await open(directory,text,{chunks:parts,size:0xffffffff,ownerCount:0xffffffff});
   assert.deepEqual(materialize(store),value);assert.equal(store.canonical_sha256,hash(valueBytes(value)));store.close();
  }
 }
 assert.deepEqual(fs.readdirSync(directory),[]);
});

test('native inline triples defer invalid domains until final duplicate fields win',async t=>{
 const directory=temporary(t);
 for(const tuple of ['[0,0,1]','[3,2,1]','[0,101,1]','[0,1,0]','[0,1,11]',
  '[0,4294967296,1]','[0,1,9007199254740993]','[0,1e400,1]','[0,1.5,1]']){
  for(const text of [
   '{"rows":[{"y":0,"runs":['+tuple+',[0,1,1]],"runs":[[2,3,2]]}]}',
   '{"rows":[{"y":0,"runs":['+tuple+']}],"rows":[{"y":0,"runs":[[0,1,1]]}]}']){
   const body=Buffer.from(text),value=JSON.parse(text);
   for(const parts of chunkCuts(body)){
    const store=await open(directory,text,{chunks:parts});assert.deepEqual(materialize(store),value);
    assert.equal(store.canonical_sha256,hash(valueBytes(value)));store.close();
   }
  }
  const text='{"rows":[{"y":0,"runs":['+tuple+']}]}';
  await assert.rejects(open(directory,text,{chunks:[Buffer.from(text)]}),/Invalid complete native interval\/owner/);
  assert.deepEqual(fs.readdirSync(directory),[]);
 }
});

test('native inline triples reject malformed tuples and partials even before replacement',async t=>{
 const directory=temporary(t);
 for(const tuple of ['[00,1,1]','[+0,1,1]','[0,01,1]','[0,1.,1]','[0,1e,1]','[0,1,1,]',
  '[0,1,,1]','[0,1 2,1]','[0,1,1]true','[0,1,1}','[0,1,1\u000b]']){
  const text='{"rows":[{"y":0,"runs":['+tuple+']}],"rows":[]}',body=Buffer.from(text);
  assert.throws(()=>JSON.parse(text));
  for(const parts of chunkCuts(body)){
   await assert.rejects(open(directory,text,{chunks:parts}));assert.deepEqual(fs.readdirSync(directory),[]);
  }
 }
 const text='{"rows":[{"y":0,"runs":[[0,1,1],[2,3,1]]}]}',body=Buffer.from(text);
 for(let cut=0;cut<body.length;cut++){
  const partial=body.subarray(0,cut);await assert.rejects(open(directory,partial.toString(),{chunks:[partial]}));
  assert.deepEqual(fs.readdirSync(directory),[]);
 }
});

test('native inline triples avoid per-run JSON arrays, strings and promise dispatch',t=>{
 const directory=temporary(t),module=new URL('../scripts/native-patch-store.mjs',import.meta.url).href;
 const script=`import assert from 'node:assert/strict';import {createHash} from 'node:crypto';import {createHook} from 'node:async_hooks';
  import {admitNativePatchStore,admitNativeLedgerStore} from ${JSON.stringify(module)};
  const parse=JSON.parse,toString=Buffer.prototype.toString;let observed=null,parsing=false;
  JSON.parse=function(value,...rest){const before=parsing;parsing=!!observed&&Buffer.isBuffer(value)&&value[0]===91;
   try{const result=Reflect.apply(parse,this,[value,...rest]);if(parsing&&Array.isArray(result)&&result.length===3)observed.arrays++;return result;}finally{parsing=before;}};
  Buffer.prototype.toString=function(...args){if(observed&&parsing)observed.strings++;return Reflect.apply(toString,this,args);};
  const hook=createHook({init(_id,type){if(observed&&type==='PROMISE')observed.promises++;}}),results=[];
  const warm=Buffer.from('{"rows":[]}');
  (await admitNativePatchStore({directory:${JSON.stringify(directory)},chunks:[warm],size:256,ownerCount:3,expected:{bytes:warm.length,sha256:createHash('sha256').update(warm).digest('hex')}})).close();
  for(const count of [1,8]){
   const value={rows:Array.from({length:64},(_,y)=>({runs:Array.from({length:count},(_,i)=>[i*2,i*2+1,i%3+1]),y})),version:2};
   const body=Buffer.from(JSON.stringify(value)+'\\n'),sha256=createHash('sha256').update(body).digest('hex'),record={count,arrays:0,strings:0,promises:0};
   let store;try{observed=record;hook.enable();store=await admitNativePatchStore({directory:${JSON.stringify(directory)},chunks:[body],size:256,ownerCount:3,expected:{bytes:body.length,sha256}});
    hook.disable();observed=null;assert.equal(store.canonical_sha256,sha256);assert.equal(store.runCount,64*count);
    assert.deepEqual([...store.rowEntries()].map(row=>({runs:[...store.intervals(row)],y:row.y})),value.rows);results.push(record);
   }finally{hook.disable();observed=null;store?.close();}
  }
  JSON.parse=parse;Buffer.prototype.toString=toString;console.log(JSON.stringify(results));`;
 const result=spawnSync(process.execPath,['--input-type=module','-e',script],{encoding:'utf8',timeout:30000,env:{...process.env,NODE_OPTIONS:'',NODE_PATH:''}});
 assert.equal(result.status,0,result.stderr);const observations=JSON.parse(result.stdout);
 assert.deepEqual({allocations:observations.map(({arrays,strings})=>({arrays,strings})),extraPromises:observations[1].promises-observations[0].promises},
  {allocations:[{arrays:0,strings:0},{arrays:0,strings:0}],extraPromises:0},result.stdout);
 assert.deepEqual(fs.readdirSync(directory),[]);
});


function observeWriterIO({shortWrites=false,writeError,truncateError}={}){
 const original={open:fs.openSync,write:fs.writeSync,truncate:fs.ftruncateSync},files=new Map(),writes=[],truncates=[];
 fs.openSync=function(name,...args){const fd=original.open.call(this,name,...args);files.set(fd,String(name));return fd;};
 fs.writeSync=function(fd,buffer,offset,length,position){
  writes.push({path:files.get(fd),length,position});
  if(writeError&&files.get(fd)?.endsWith('/runs.bin'))throw writeError;
  return original.write.call(this,fd,buffer,offset,shortWrites?Math.min(length,5):length,position);
 };
 fs.ftruncateSync=function(fd,length){truncates.push({path:files.get(fd),length});if(truncateError)throw truncateError;return original.truncate.call(this,fd,length);};
 return {writes,truncates,restore(){fs.openSync=original.open;fs.writeSync=original.write;fs.ftruncateSync=original.truncate;}};
}
test('store reset at buffered logical end keeps sequential writes batched',async t=>{
 const directory=temporary(t),value={rows:Array.from({length:64},(_,y)=>({y,runs:[[0,2,1]]}))},trace=observeWriterIO();let store;
 try{store=await open(directory,JSON.stringify(value));
  assert.deepEqual(materialize(store),value);assert.equal(store.canonical_sha256,hash(valueBytes(value)));
  assert.equal(trace.truncates.length,0,'No first-field reset may truncate an unchanged logical end');
  assert.equal(trace.writes.filter(p=>p.path.endsWith('/runs.bin')).length,1);
  assert.equal(trace.writes.filter(p=>p.path.endsWith('/rows.bin')).length,1);
 }finally{trace.restore();store?.close();}
});
test('store reset at already flushed component end preserves complete ledger projections',async t=>{
 const directory=temporary(t),value={rows:[0,1,2].map(i=>({component_id:String(i),native_rows:[{y:i,runs:[[i,i+1,1]]}]}))};
 const body=Buffer.from(JSON.stringify(value)),trace=observeWriterIO();let store;
 try{store=await admitNativeLedgerStore({directory,size:100,ownerCount:10,chunks:[body],expected:{bytes:body.length,sha256:hash(body)}});
  assert.equal(store.canonical_sha256,hash(valueBytes(value)));
  assert.equal(trace.truncates.length,0);
  assert.equal(trace.writes.filter(p=>p.path.endsWith('/runs.bin')).length,3,'Each completed component still flushes for genuine canonical readback');
  for(const c of store.componentEntries())assert.equal([...store.componentCanonicalChunks(c)].join(''),valueBytes(value.rows[c.ordinal]).toString());
 }finally{trace.restore();store?.close();}
});
test('store actual duplicate-field rewind retains flush and truncate',async t=>{
 const directory=temporary(t),text='{"rows":[{"y":0,"runs":[[0,9,1]],"runs":[[2,3,2]]}],"rows":[{"y":1,"runs":[[4,5,3]]}]}';
 const trace=observeWriterIO();let store;
 try{store=await open(directory,text);assert.deepEqual(materialize(store),JSON.parse(text));
  assert.equal(store.canonical_sha256,hash(valueBytes(JSON.parse(text))));
  assert(trace.truncates.some(p=>p.path.endsWith('/runs.bin')));assert(trace.truncates.some(p=>p.path.endsWith('/rows.bin')));
 }finally{trace.restore();store?.close();}
});
test('store deferred end flush handles partial writes without changing bytes',async t=>{
 const directory=temporary(t),value={rows:[{y:1,runs:[[0,2,1],[3,4,2]]}]},trace=observeWriterIO({shortWrites:true});let store;
 try{store=await open(directory,JSON.stringify(value));assert.deepEqual(materialize(store),value);assert.equal(store.canonical_sha256,hash(valueBytes(value)));
  assert(trace.writes.filter(p=>p.path.endsWith('/runs.bin')).length>=5);
 }finally{trace.restore();store?.close();}
});
for(const mode of ['final-flush','rewind-flush','rewind-truncate'])test('store reset preserves '+mode+' failure and cleanup',async t=>{
 const directory=temporary(t),failure=Error(mode),trace=observeWriterIO(mode==='rewind-truncate'?{truncateError:failure}:{writeError:failure});
 const text=mode==='final-flush'?'{"rows":[{"y":0,"runs":[[0,1,1]]}]}':'{"rows":[{"y":0,"runs":[[0,1,1]],"runs":[]}]}';
 try{await assert.rejects(open(directory,text),error=>error===failure);assert.deepEqual(fs.readdirSync(directory),[]);}
 finally{trace.restore();}
});
