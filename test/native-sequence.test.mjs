import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {nativeSequence,isNativeSequence,nativeRowAt} from '../src/native-grid.js';
import {mergeCompletedNativePatches,valueBytes,valueSha} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
import {compareIntervals} from '../scripts/check-effective-geographic-regression.mjs';

test('explicit native sequences retain exact canonical bytes and repeatable row lookup',()=>{
 const literal=[{y:0,runs:[[0,1,1],[2,3,1]]},{y:4,runs:[]}];
 const rows=nativeSequence(2,function*(){for(const row of literal)yield {y:row.y,runs:nativeSequence(row.runs.length,()=>row.runs.values())};});
 assert.equal(valueSha(rows),valueSha(literal));assert.deepEqual(valueBytes(rows),valueBytes(literal));
 assert.deepEqual(valueBytes(rows),valueBytes(rows));assert.equal(nativeRowAt(rows,4).y,4);assert.equal(nativeRowAt(rows,2),undefined);
 assert.equal(rows.at(-1).y,4);assert.equal(rows.at(2),undefined);assert.equal(rows.at(0).runs.at(1)[0],2);
 assert(isNativeSequence(rows));assert(!isNativeSequence({...rows}));assert(!isNativeSequence(structuredClone(rows)));
 assert(Object.isFrozen(rows));
});

test('native sequences reject count lies and propagate producer errors and cleanup',()=>{
 for(const [length,values]of [[1,[]],[0,[1]],[2,[1]]]){
  const sequence=nativeSequence(length,()=>values.values());assert.throws(()=>valueSha(sequence),/declared/);
 }
 let closed=0;
 const sequence=nativeSequence(3,function*(){try{yield 1;yield 2;yield 3;}finally{closed++;}});
 for(const value of sequence){assert.equal(value,1);break;}
 assert.equal(closed,1);assert.throws(()=>{for(const value of sequence)throw Error('consumer');},/consumer/);assert.equal(closed,2);
 assert.throws(()=>[...nativeSequence(2,function*(){try{yield 1;throw Error('storage failure');}finally{closed++;}})],/storage failure/);
 assert.equal(closed,3);
});

test('native interval consumers validate late malformed intervals and preserve literal loss segmentation',()=>{
 const before=[[0,5,1],[8,10,2]],after=[[1,2,1],[2,4,2],[8,9,1]],owners=[{id:'A'},{id:'B'}];
 const sequence=rows=>nativeSequence(rows.length,()=>rows.values());
 const options={row:3,ownersBefore:owners,ownersAfter:owners};
 assert.deepEqual(compareIntervals(sequence(before),sequence(after),options),compareIntervals(before,after,options));
 assert.throws(()=>compareIntervals(sequence(before),sequence([...after,[20,21,9]]),options),/owner interval/);
});

test('dense interval comparison and canonical hashing stay streaming under a 48MiB child heap',()=>{
 const sequence=new URL('../src/native-grid.js',import.meta.url).href;
 const checker=new URL('../scripts/check-effective-geographic-regression.mjs',import.meta.url).href;
 const hash=new URL('../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs',import.meta.url).href;
 const code=`import {nativeSequence} from ${JSON.stringify(sequence)};import {compareIntervals} from ${JSON.stringify(checker)};import {valueSha} from ${JSON.stringify(hash)};
 const rows=nativeSequence(500000,function*(){for(let i=0;i<500000;i++)yield [i*2,i*2+1,1];});
 const owners=[{id:'A'}];const result=compareIntervals(rows,rows,{row:0,ownersBefore:owners,ownersAfter:owners});
 if(result.length)throw Error('invented loss');console.log(JSON.stringify({sha:valueSha(rows),rss:process.resourceUsage().maxRSS}));`;
 const result=spawnSync(process.execPath,['--max-old-space-size=48','--input-type=module','-e',code],{encoding:'utf8',timeout:60000});
 assert.equal(result.status,0,result.stderr);assert.match(JSON.parse(result.stdout).sha,/^[a-f0-9]{64}$/);
});

test('mapped and filtered component cursors are repeatable without retaining complete component values',()=>{
 let live=0,closed=0;
 const rows=nativeSequence(4,function*(){live++;try{for(let i=0;i<4;i++)yield {id:i,metadata:'x'.repeat(4096)};}finally{live--;closed++;}});
 const selected=rows.filter(row=>row.id%2===0).map(row=>row.id);
 assert.equal(selected.length,2);assert.deepEqual([...selected],[0,2]);assert.deepEqual([...selected],[0,2]);
 assert.equal(selected.find(id=>id===2),2);assert(selected.some(id=>id===0));assert(selected.every(id=>id%2===0));
 assert.equal(live,0);assert(closed>=6);
 assert.throws(()=>rows.map(()=>{throw Error('consumer error');}).at(0),/consumer error/);assert.equal(live,0);
});

import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {mergeCompletedNativePatches as eagerMerge} from './fixtures/completed-native-merge-eager.mjs';

test('completed authority merge exactly matches retained eager values and refusal ordering',()=>{
 assert.equal(createHash('sha256').update(fs.readFileSync(new URL('./fixtures/completed-native-merge-eager.mjs',import.meta.url))).digest('hex'),'53e3f345e059e030a4e53f7a70be79c07ecc376c354bf1ccc5b7e39a5760dc41');
 let seed=97637;const random=n=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed%n;};
 const check=patches=>{
  const stored=patches.map(patch=>({rows:nativeSequence(patch.rows.length,function*(){for(const row of patch.rows)
   yield {...row,runs:nativeSequence(row.runs.length,()=>row.runs.values())};})}));
  let expected;try{expected=eagerMerge(patches,32);}catch(error){
   for(const value of [patches,stored])assert.throws(()=>mergeCompletedNativePatches(value,32),{message:error.message});return;
  }
  assert.deepEqual(mergeCompletedNativePatches(patches,32),expected);
  const view=mergeCompletedNativePatches(stored,32);assert.equal(valueSha(view),valueSha(expected));assert.equal(valueSha(view),valueSha(expected));
 };
 for(let trial=0;trial<1000;trial++){
  const patches=Array.from({length:random(5)},()=>({rows:Array.from({length:random(6)},(_,y)=>{
   let end=0;const runs=[];for(let i=0,n=random(5);i<n;i++){
    const start=end+random(3),stop=start+1+random(3);runs.push([start,stop,1+random(3)]);end=stop;
   }return {y,runs};})}));check(patches);
 }
 for(const rows of [[{y:-1,runs:[[0,1,1]]}],[{y:0,runs:[[0,33,1]]}],[{y:0,runs:[[2,1,1]]}],
  [{y:0,runs:[[0,1,0]]}],[{y:0,runs:[[0,2,1],[1,3,1]]}],[{y:0,runs:[[0,1,1]]},{y:0,runs:[[2,3,1]]}]])check([{rows}]);
});

test('completed merge closes every acquired cursor and preserves primary producer failures',()=>{
 for(const layer of ['rows','runs'])for(const at of [0,1])for(const cleanupFailure of [false,true]){
  const primary=Error('initial or midstream producer sentinel'),secondary=Error('cleanup sentinel');let active=0;
  const tracked=(values,fail,cleanup)=>{let pass=0;return nativeSequence(values.length,function*(){
   const current=++pass;active++;
   try{for(let i=0;i<values.length;i++){if(fail&&current===2&&i===at)throw primary;yield values[i];}}
   finally{active--;if(cleanup&&current===2)throw secondary;}
  });};
  const a=[{y:0,runs:[[0,1,1],[4,5,1]]},{y:1,runs:[[0,1,1]]}],b=[{y:0,runs:[[2,3,1],[6,7,1]]},{y:1,runs:[[2,3,1]]}];
  const patches=layer==='rows'?[{rows:tracked(a,false,cleanupFailure)},{rows:tracked(b,true,false)}]:[
   {rows:[{y:0,runs:tracked(a[0].runs,false,cleanupFailure)}]},
   {rows:[{y:0,runs:tracked(b[0].runs,true,false)}]}];
  assert.throws(()=>mergeCompletedNativePatches(patches,32),error=>error===primary);
  assert.equal(active,0,layer+' '+at+' '+cleanupFailure);
 }
});

test('completed merge early row/interval return closes producers, including cleanup failure',()=>{
 for(const cleanupFailure of [false,true]){
  const secondary=Error('early cleanup sentinel');let active=0,failCleanup=false;
  const tracked=values=>nativeSequence(values.length,function*(){active++;try{yield* values;}finally{
   active--;if(failCleanup)throw secondary;
  }});
  const patches=[{rows:tracked([{y:0,runs:tracked([[0,1,1],[2,3,1]])}])},
   {rows:tracked([{y:0,runs:tracked([[4,5,1]])}])}];
  const view=mergeCompletedNativePatches(patches,32);assert.equal(active,0);
  const rows=view[Symbol.iterator](),row=rows.next().value,runs=row.runs[Symbol.iterator]();runs.next();
  if(cleanupFailure){failCleanup=true;assert.throws(()=>runs.return(),error=>error===secondary);
   assert.throws(()=>rows.return(),error=>error===secondary);}
  else{runs.return();rows.return();}
  assert.equal(active,0);
 }
});
