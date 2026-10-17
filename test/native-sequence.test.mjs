import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {nativeSequence,isNativeSequence,nativeRowAt} from '../src/native-grid.js';
import {valueBytes,valueSha} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
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
