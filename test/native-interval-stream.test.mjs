import test from 'node:test';import assert from 'node:assert/strict';
import {compareNativeAdditiveIntervals,applyNativeAdditiveRows,compareEffectiveNativeRows} from '../scripts/selected-checkpoint-native.mjs';
const owners=[{id:'A'},{id:'B'}],options={y:0,size:8,owners,before:[],after:[]};
const run=(base,patch={})=>compareNativeAdditiveIntervals(base,{...options,...patch});
test('exact original full-row contract holds across boundary touches reassignment and empty scopes',async()=>{
 const baseCases=[[],[[0,1,1]],[[0,2,1],[4,6,2]],[[1,2,2],[3,4,1],[7,8,2]]],patches=[[],[[2,3,1]],[[2,3,2]],[[6,7,1]],[[2,3,1],[6,7,2]]];let checked=0;
 for(const base of baseCases)for(const before of patches)for(const after of patches){
  let old,next;try{old=applyNativeAdditiveRows([{y:0,runs:base}],{rows:[{y:0,runs:before}]},{size:8,owners});next=applyNativeAdditiveRows([{y:0,runs:base}],{rows:[{y:0,runs:after}]},{size:8,owners});}catch{await assert.rejects(run(base,{before,after}),/overlaps/);continue;}
  assert.deepEqual(await run(base,{before,after}),compareEffectiveNativeRows(old,next,{size:8,ownersBefore:owners,ownersAfter:owners,rows:[0]}));checked++;
 }
 assert.ok(checked>0);
});
test('late corrupt base interval still refuses when both patches are empty',async()=>{
 for(const tail of [[0,1,1],[3,3,1],[3,9,1],[3,4,0],[3,4,3],[3,4.5,1],[3,4],null])await assert.rejects(run([[0,1,1],[2,3,2],tail]),/Invalid/);
});
test('old and new same-owner overlaps both refuse rather than cancel',async()=>{
 for(const key of ['before','after'])await assert.rejects(run([[2,4,1]],{[key]:[[3,5,1]]}),/overlaps/);
});
test('overlap closes source iterator and late source errors cannot return success',async()=>{
 let closed=false;async function* source(){try{yield [2,4,1];yield [5,6,1];}finally{closed=true;}}
 await assert.rejects(run(source(),{after:[[3,5,1]]}),/overlaps/);assert.equal(closed,true);
 async function* late(){yield [0,1,1];throw Error('late source sentinel');}
 await assert.rejects(run(late()),/late source sentinel/);
});
test('invalid duplicate unordered and foreign patch rows refuse before accepting base work',async()=>{
 for(const before of [[[2,3,1],[2,3,1]],[[4,5,1],[2,3,1]],[[1,1,1]],[[0,9,1]],[[0,1,3]]])await assert.rejects(run([],{before}),/Invalid/);
});

import {repairVisibilityWitnesses,visibilityDigest} from '../scripts/check-effective-geographic-regression.mjs';
import {nativeRowLatitudes} from '../src/native-grid.js';
const rectangle={type:'Polygon',coordinates:[[[-180,-85],[180,-85],[180,85],[-180,85],[-180,-85]]]};
const visibility=candidates=>repairVisibilityWitnesses({candidates,size:8,latitudes:nativeRowLatitudes(8),beforeRows:[{y:1,runs:[]}],afterRows:[{y:1,runs:[[0,8,1]]}]});
const polygonCandidate=(i,geometry=rectangle)=>({component_id:`component-${i}`,pixelIndex:1,geometry,geometry_sha256:visibilityDigest(geometry)});
test('polygon visibility preserves every primitive beyond old component cap and preparation boundary',()=>{
 const candidates=Array.from({length:8193},(_,i)=>polygonCandidate(i)),witnesses=visibility(candidates);
 assert.equal(witnesses.length,candidates.length);
 for(let i=0;i<candidates.length;i++)assert.deepEqual(witnesses[i],{component_id:candidates[i].component_id,geometry_sha256:candidates[i].geometry_sha256,x:0,y:1,previous_owner:0,candidate_owner:1});
});
test('duplicate component and corrupt geometry after a preparation boundary still refuse',()=>{
 const candidates=Array.from({length:6555},(_,i)=>polygonCandidate(i));
 candidates[candidates.length-1]={...candidates.at(-1),component_id:candidates[0].component_id};assert.throws(()=>visibility(candidates),/Duplicate/);
 candidates[candidates.length-1]={...polygonCandidate(6554),geometry_sha256:'0'.repeat(64)};assert.throws(()=>visibility(candidates),/binding differs/);
});
test('one original geometry larger than the preparation window remains fully checked',()=>{
 const ring=Array.from({length:32768},()=>[-180,-85]);ring.push([180,-85],[180,85],[-180,85],[-180,-85]);
 const candidate=polygonCandidate('large',{type:'Polygon',coordinates:[ring]});assert.ok(ring.length*2>65536);
 assert.deepEqual(visibility([candidate])[0],{component_id:candidate.component_id,geometry_sha256:candidate.geometry_sha256,x:0,y:1,previous_owner:0,candidate_owner:1});
 const changed={...candidate,geometry:{type:'Polygon',coordinates:[ring.map((p,i)=>i===ring.length-2?[181,85]:p)]}};assert.throws(()=>visibility([changed]),/binding differs/);
});
