import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import * as cold from '../scripts/check-effective-geographic-regression.mjs';
import {applyNativeAdditiveRows,deriveEffectiveNativeRowDelta,compareSelectedCheckpointNative,compareEffectiveNativeRows} from '../scripts/selected-checkpoint-native.mjs';

import * as eager from './fixtures/native-checkpoint-eager.mjs';
import {nativeSequence} from '../src/native-grid.js';
const sha=body=>createHash('sha256').update(body).digest('hex');

test('cursor native derivation matches the pinned eager oracle while conservation remains joint-only',()=>{
 const source=fs.readFileSync('test/fixtures/native-checkpoint-eager.mjs','utf8'), start=source.indexOf('// Numerical consumers of complete row projections.');
 assert(start>0);
 assert.equal(sha(source),'28ecdede78265a3f68b6e8e3ec07d15b4cd4de6bef1a5c924bac382de92397f0');
 // Keep the original array implementation as an independently pinned oracle.
 // Production now accepts disk cursors through the same domain checks.
 assert.equal(sha(source.slice(start)),'46573049a336d665a80a1e4478c32a498c7ea1cb46f263a8b82467f035c43cc1');
 const owners=[{id:'original-owner'},{id:'other-owner'}];
 assert.deepEqual(compareEffectiveNativeRows([{y:1,runs:[[0,4,1]]}],[{y:1,runs:[[0,2,1],[2,3,2]]}],{size:8,ownersBefore:owners,ownersAfter:owners,rows:[1]}),{checked_rows:1,lost_or_reassigned_cells:2,intervals:[{row:1,start:2,end:3,previous_owner:'original-owner',candidate_owner:'other-owner'},{row:1,start:3,end:4,previous_owner:'original-owner',candidate_owner:null}]});
 assert.equal(typeof cold.screenNativeGapCandidates,'function');
 assert.equal(typeof cold.repairVisibilityWitnesses,'function');
 assert.equal(cold.compareSelectedCheckpointNative,undefined);
 assert.equal(typeof compareSelectedCheckpointNative,'function');
});





// Deterministic differential matrix contributed by the independent reviewer.
test('ordered cursor/array shapes and exact refusals match the immutable eager preimage',()=>{
let seed=2396,passes=0,refusals=0;const rand=n=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed%n;};
const owners=[{id:'a'},{id:'b'},{id:'c'}],options={size:32,owners,ownersBefore:owners,ownersAfter:owners};
const make=()=>{let rows=[];for(let y=0;y<8;y++){let runs=[],x=0;while(x<32){x+=rand(4);let end=Math.min(32,x+rand(5)+1);if(x<end)runs.push([x,end,rand(3)+1]);x=end;}if(rand(3))rows.push({y,runs});}return rows;};
const cursor=rows=>Array.isArray(rows)?nativeSequence(rows.length,function*(){for(const row of rows)yield row&&Array.isArray(row.runs)?{...row,runs:nativeSequence(row.runs.length,()=>row.runs.values())}:row;}):rows;
const outcome=fn=>{try{return {value:fn()};}catch(e){return {error:e.message};}};
function compare(name,a,b){const before=outcome(()=>eager[name](a,name==='applyNativeAdditiveRows'?b&&{rows:b}:b,options));for(const wrap of [x=>x,cursor]){const after=outcome(()=>({applyNativeAdditiveRows,deriveEffectiveNativeRowDelta})[name](wrap(a),name==='applyNativeAdditiveRows'?b&&{rows:wrap(b)}:wrap(b),options));assert.deepEqual(after,before);passes++;if(before.error)refusals++;}}
for(let i=0;i<2000;i++){const a=make(),b=make();compare('applyNativeAdditiveRows',a,b);compare('deriveEffectiveNativeRowDelta',a,b);}
for(const bad of [null,{},[{y:-1,runs:[]}],[{y:32,runs:[]}],[{y:1,runs:null}],[{y:1,runs:[[0,0,1]]}],[{y:1,runs:[[0,33,1]]}],[{y:1,runs:[[0,1,0]]}],[{y:1,runs:[[0,1,4]]}],[{y:1,runs:[[0,2,1],[1,3,2]]}],[{y:1,runs:[]},{y:1,runs:[]}],[{y:1,runs:[[0,1.5,1]]}]]){compare('applyNativeAdditiveRows',bad,null);compare('deriveEffectiveNativeRowDelta',bad,[]);}
assert.equal(passes,8048);assert.equal(refusals,4004);
});
