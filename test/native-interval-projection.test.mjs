import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {trustedFixture} from './fixtures/selected-checkpoint.mjs';
function layout(count=2048,runPartWords=1024){
 const size=count*2+4,bits=Math.ceil(Math.log2(size)),runs=[];
 for(let x=0;x<count;x++)runs.push(2**bits+x*2,x*2);
 runs.push(2*2**bits,0); // Genuine retained row 1 remains [0,1,2].
 const rows=[0,count,count,1];for(let y=2;y<size;y++)rows.push(count+1,0);
 return {size,rows,runs,runPartWords};
}
function scratchTrace(){
 const mkdir=fs.mkdtempSync,remove=fs.rmSync,live=new Set();let peak=0,created=0;
 fs.mkdtempSync=(prefix,...args)=>{const result=mkdir(prefix,...args);if(path.basename(prefix)==='worldatlas-native-'){live.add(result);created++;peak=Math.max(peak,live.size);}return result;};
 fs.rmSync=(name,...args)=>{const result=remove(name,...args);live.delete(name);return result;};
 return {live,get peak(){return peak;},get created(){return created;},restore(){fs.mkdtempSync=mkdir;fs.rmSync=remove;}};
}
for(const runPartWords of [1024,256,64])test(`private interval visitor crosses ${4096/runPartWords} dense-row containers with only table and one body live`,async t=>{
 const nativeLayout=layout(2048,runPartWords),f=await trustedFixture(t,{nativeLayout}),{state}=(await f.api.qualifyCheckpoint({reader:f.reader}));
 const trace=scratchTrace(),stream=f.reader.stream.bind(f.reader),reads=[];
 f.reader.stream=function(name,options){reads.push(name);return stream(name,options);};
 try{
  const inspect=async()=>{let count=0;
   const projection=await f.api.visitNativeIntervals({state,rows:[0,1,nativeLayout.size-1],visit:async ({y,runs})=>{
    let ordinal=0;for await(const run of runs){assert.deepEqual(run,y===0?[ordinal*2,ordinal*2+1,1]:[0,1,2]);ordinal++;count++;}
    assert.equal(ordinal,y===0?2048:y===1?1:0);
   }});
   assert.equal(count,2049);assert.deepEqual(projection.reused_rows,[1]);assert.deepEqual(projection.acquired_rows,[0,nativeLayout.size-1]);
   assert.equal(trace.live.size,0);return projection;
  };
  const first=await inspect(),firstReads=reads.slice();assert.equal(firstReads.filter(n=>n.includes('/runs-')).length,4096/runPartWords);assert.equal(trace.peak,2);
  for(const name of firstReads)assert.equal(f.reader.inventory.get(f.reader.version+':'+name).whole_body_consumed,true);
  const second=await inspect();assert.deepEqual(reads.slice(firstReads.length),firstReads,'next visit must reread rather than retain decoded containers');
  assert.deepEqual(second.acquired_rows,first.acquired_rows);assert.equal(trace.peak,2);assert.equal(trace.created,2*(1+4096/runPartWords));
 }finally{trace.restore();f.api.releaseCheckpoint(state);}
});
test('private interval visitor closes both stores on early return throw or corrupt later container',async t=>{
 const f=await trustedFixture(t,{nativeLayout:layout()}),{state}=(await f.api.qualifyCheckpoint({reader:f.reader})),trace=scratchTrace();
 const stream=f.reader.stream.bind(f.reader);
 try{
  await assert.rejects(f.api.visitNativeIntervals({state,rows:[0],visit:async ({runs})=>{for await(const run of runs){assert.ok(run);break;}}}),/omitted complete row/);assert.equal(trace.live.size,0);
  await assert.rejects(f.api.visitNativeIntervals({state,rows:[0],visit:async ({runs})=>{for await(const run of runs){assert.ok(run);throw Error('visitor sentinel');}}}),/visitor sentinel/);assert.equal(trace.live.size,0);
  f.reader.stream=async function*(name,options){let first=true;for await(const chunk of stream(name,options)){if(first&&name.endsWith('/runs-2048.bin.gz')){const bad=Buffer.from(chunk);bad[0]^=1;yield bad;}else yield chunk;first=false;}};
  await assert.rejects(f.api.visitNativeIntervals({state,rows:[0],visit:async ({runs})=>{for await(const run of runs)void run;}}));assert.equal(trace.live.size,0);
  f.reader.stream=stream;await f.api.visitNativeIntervals({state,rows:[0],visit:async ({runs})=>{for await(const run of runs)void run;}});assert.equal(trace.live.size,0);
 }finally{f.reader.stream=stream;trace.restore();f.api.releaseCheckpoint(state);}
});
test('native layout seed snapshots caller words and separates distinct partitions',async t=>{
 const nativeLayout=layout(16,8),pending=trustedFixture(t,{nativeLayout});nativeLayout.runs[0]=0;nativeLayout.rows[1]=0;
 const first=await pending,second=await trustedFixture(t,{nativeLayout:layout(16,8)}),third=await trustedFixture(t,{nativeLayout:layout(16,16)});
 assert.deepEqual(first.manifest,second.manifest);assert.notDeepEqual(first.manifest.parts,third.manifest.parts);
 const {state}=(await first.api.qualifyCheckpoint({reader:first.reader}));let count=0;
 try{await first.api.visitNativeIntervals({state,rows:[0],visit:async ({runs})=>{for await(const run of runs){assert.equal(run[0],count*2);count++;}}});assert.equal(count,16);}finally{first.api.releaseCheckpoint(state);}
});

for(const primary of [Error('visitor primary'),undefined,null,false,0])
test('private interval visitor attempts both owned closes and preserves primary '+String(primary),async t=>{
 const f=await trustedFixture(t,{nativeLayout:layout(4,8)}),{state}=await f.api.qualifyCheckpoint({reader:f.reader});
 const open=fs.openSync,close=fs.closeSync,remove=fs.rmSync,trace=scratchTrace(),fds=new Set();let attempts=0;
 fs.openSync=function(name,...args){const fd=open.call(this,name,...args);if(path.basename(String(name))==='shuffled')fds.add(fd);return fd;};
 fs.closeSync=function(fd){const owned=fds.delete(fd);close(fd);if(owned){attempts++;throw Error('secondary close');}};
 try{
  await assert.rejects(f.api.visitNativeIntervals({state,rows:[0],visit:async({runs})=>{for await(const run of runs){assert.ok(run);throw primary;}}}),error=>Object.is(error,primary));
  assert.equal(attempts,2);assert.equal(trace.live.size,0);assert.equal(fds.size,0);
  fs.closeSync=close;
  await f.api.visitNativeIntervals({state,rows:[0],visit:async({runs})=>{for await(const run of runs)assert.ok(run);}});
  assert.equal(trace.live.size,0);
 }finally{fs.openSync=open;fs.closeSync=close;for(const fd of fds)try{close(fd);}catch{}for(const name of trace.live)remove(name,{recursive:true});trace.restore();f.api.releaseCheckpoint(state);}
});
for(const first of [Error('cleanup primary'),undefined,null,false,0])
test('private interval visitor preserves first cleanup failure and releases active visit '+String(first),async t=>{
 const f=await trustedFixture(t,{nativeLayout:layout(4,8)}),{state}=await f.api.qualifyCheckpoint({reader:f.reader});
 const open=fs.openSync,close=fs.closeSync,remove=fs.rmSync,trace=scratchTrace(),fds=new Set();let attempts=0;
 fs.openSync=function(name,...args){const fd=open.call(this,name,...args);if(path.basename(String(name))==='shuffled')fds.add(fd);return fd;};
 fs.closeSync=function(fd){const owned=fds.delete(fd);close(fd);if(owned)throw ++attempts===1?first:Error('later cleanup');};
 try{
  await assert.rejects(f.api.visitNativeIntervals({state,rows:[0],visit:async({runs})=>{for await(const run of runs)assert.ok(run);}}),error=>Object.is(error,first));
  assert.equal(attempts,2);assert.equal(trace.live.size,0);assert.equal(fds.size,0);
  fs.closeSync=close;
  await f.api.visitNativeIntervals({state,rows:[0],visit:async({runs})=>{for await(const run of runs)assert.ok(run);}});
  assert.equal(trace.live.size,0);
 }finally{fs.openSync=open;fs.closeSync=close;for(const fd of fds)try{close(fd);}catch{}for(const name of trace.live)remove(name,{recursive:true});trace.restore();f.api.releaseCheckpoint(state);}
});
