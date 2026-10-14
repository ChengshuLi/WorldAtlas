import test from 'node:test';
import assert from 'node:assert/strict';
import {gzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {nativeRowLatitudes} from '../src/native-grid.js';
import {screenNativeGapCandidates,newVisibleRepairCandidates,repairVisibilityWitnesses,
  decodeVisibilityLatitudes,visibilityDigest} from '../scripts/check-effective-geographic-regression.mjs';

const size=16,latitudes=nativeRowLatitudes(size);
const selection={current_selection_sha256:'a'.repeat(64),patch_sha256:'b'.repeat(64),containing_native_asset_ids:['part0']};
const rows=(first=0,end=size,runs=[])=>Array.from({length:end-first},(_,i)=>({y:first+i,runs:structuredClone(runs)}));
const polygon=(x,y,halfWidth=.00001)=>({type:'Polygon',coordinates:[[
  [x-halfWidth,y-halfWidth],[x+halfWidth,y-halfWidth],[x+halfWidth,y+halfWidth],
  [x-halfWidth,y+halfWidth],[x-halfWidth,y-halfWidth]]]});
const at=(x,y)=>[(x+.5)/size*360-180,latitudes[y]];
const candidate=(id,x=8,y=8)=>({component_id:id,geometry:polygon(...at(x,y)),pixelIndex:1,disposition:'assigned',native_cells:1});
const screen=(c,more={})=>screenNativeGapCandidates({candidates:[c],size,latitudes,rows:rows(),rowStart:0,rowEnd:size,selection,...more})[0];

test('subcell geometry is visible if and only if exact sample changes owner',()=>{
 const c=candidate('tiny'),result=screen(c);
 assert.equal(result.status,'visible');assert.equal(result.native_candidate_cells,1);
 assert.equal(result.current_unassigned_cells,1);assert.deepEqual(result.witness,{x:8,y:8,current_owner:0});
 assert.equal(result.geometry_sha256,visibilityDigest(c.geometry));
 assert.equal(result.current_selection_sha256,selection.current_selection_sha256);
 const offset={...c,geometry:polygon(at(8,8)[0]+.01,latitudes[8])};
 assert.equal(screen(offset).status,'invisible');assert.equal(screen(offset).reason,'no-native-cell');
});
test('occupied current cell is excluded and stale archived witness cannot pass',()=>{
 const owned=rows();owned[8].runs=[[8,9,3]];
 const result=screen({...candidate('occupied'),witness:{x:8,y:8,current_owner:0}},{rows:owned});
 assert.equal(result.status,'invisible');assert.equal(result.reason,'already-covered-native-cells');
 assert.equal(result.repair_eligible,false);assert.equal(result.witness,null);
});
test('partial negative remains unknown; partial positive gives a lower bound only',()=>{
 const c=candidate('partial');
 const negative=screen(c,{rowStart:0,rowEnd:2,rows:rows(0,2)});
 assert.equal(negative.status,'unknown');assert.equal(negative.current_unassigned_cells,null);
 // Two separate native rows, only one observed.
 const second=candidate('other',8,12).geometry;
 const compound={...c,geometry:{type:'MultiPolygon',coordinates:[c.geometry.coordinates,second.coordinates]}};
 const positive=screen(compound,{rowStart:8,rowEnd:9,rows:rows(8,9)});
 assert.equal(positive.status,'visible');assert.equal(positive.complete_native_scope,false);
 assert.equal(positive.current_unassigned_cells,null);assert.equal(positive.witnessed_unassigned_cells,1);
});
test('holes and duplicate polygon coverage retain exact even-odd/native semantics',()=>{
 const c=candidate('hole');c.geometry.coordinates.push(structuredClone(c.geometry.coordinates[0]));
 assert.equal(screen(c).status,'invisible');
 const d=candidate('duplicate');d.geometry={type:'MultiPolygon',coordinates:[d.geometry.coordinates,d.geometry.coordinates]};
 assert.equal(screen(d).current_unassigned_cells,1);
});
test('native vertical boundary convention is used without epsilon or tiny-island fill',()=>{
 const [x,y]=at(8,8);
 const lower=polygon(x,y+.1,.1),upper=polygon(x,y-.1,.1);
 assert.equal(screen({component_id:'lower-exclusive',geometry:lower}).native_candidate_cells,0);
 assert.equal(screen({component_id:'upper-inclusive',geometry:upper}).native_candidate_cells,1);
});
test('screening refuses incomplete current owner rows and altered geometry digest',()=>{
 assert.throws(()=>screen(candidate('bad'),{rows:rows(1,size)}),/every complete/);
 assert.throws(()=>screen({...candidate('bad'),geometry_sha256:'0'.repeat(64)}),/geometry binding/);
 const bad=rows();bad[8].runs=[[9,10,1],[8,9,2]];
 assert.throws(()=>screen(candidate('bad'),{rows:bad}),/owner interval/);
});
test('zero-cell exclusion is permanent for new additions; accepted history survives unchanged',()=>{
 const old={...candidate('old'),disposition:'zero-cell',native_cells:0};
 assert.deepEqual(newVisibleRepairCandidates([old],[old]),[]);
 assert.throws(()=>newVisibleRepairCandidates([],[old]),/must change map cells/);
 assert.deepEqual(newVisibleRepairCandidates([old],[old,candidate('new')]).map(x=>x.component_id),['new']);
 assert.throws(()=>newVisibleRepairCandidates([],[{...candidate('fake'),native_cells:0}]),/must change map cells/);
});
test('actual transition needs a per-primitive unowned-to-correct-owner witness',()=>{
 const c=candidate('new'),before=rows(),after=rows();after[8].runs=[[8,9,1]];
 const check=(b,a,cs=[c])=>repairVisibilityWitnesses({candidates:cs,size,latitudes,beforeRows:b,afterRows:a});
 assert.equal(check(before,after)[0].candidate_owner,1);
 assert.deepEqual(check(after,after),[null]);
 const foreign=rows();foreign[8].runs=[[8,9,2]];assert.deepEqual(check(before,foreign),[null]);
 const unrelated=rows();unrelated[8].runs=[[9,10,1]];assert.deepEqual(check(before,unrelated),[null]);
 const sibling=candidate('sibling',9,8);assert.deepEqual(check(before,after,[sibling]),[null]);
 assert.throws(()=>check(before,after.slice(1)),/scope differs/);
});
test('normative table loading checks whole encoded and decoded bytes',()=>{
 const raw=Buffer.alloc(size*8);latitudes.forEach((x,y)=>raw.writeDoubleLE(x,y*8));
 const sha=b=>createHash('sha256').update(b).digest('hex'),encoded=gzipSync(raw);
 const pin={bytes:encoded.length,sha256:sha(encoded),decoded_bytes:raw.length,decoded_sha256:sha(raw)};
 assert.deepEqual([...decodeVisibilityLatitudes(encoded,pin,size)],[...latitudes]);
 assert.throws(()=>decodeVisibilityLatitudes(encoded,{...pin,sha256:'0'.repeat(64)},size),/encoded binding/);
 assert.throws(()=>decodeVisibilityLatitudes(encoded,{...pin,decoded_sha256:'0'.repeat(64)},size),/normative/);
});
