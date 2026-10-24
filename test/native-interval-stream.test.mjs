import test from 'node:test';import assert from 'node:assert/strict';
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
