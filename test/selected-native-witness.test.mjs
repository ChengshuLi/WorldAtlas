import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {nativeRowLatitudes} from '../src/native-grid.js';
import {nativeLiteral} from './helpers/native-literal.mjs';
import {trustedFixture,appendNativeAuthority} from './fixtures/selected-checkpoint.mjs';

const size=262166,y=nativeRowLatitudes(size).findIndex(v=>v<.1),x=Math.floor((.1+180)/360*size);
async function consumer(f){
 f.save('scripts/selected-checkpoint-native.mjs',fs.readFileSync('scripts/selected-checkpoint-native.mjs'));f.commit();
 return import(pathToFileURL(path.join(f.root,'scripts/selected-checkpoint-native.mjs')));
}

for(const completedConstructor of [false,true])for(const [name,prior,next,union] of [
 ['full same-owner overlap',[x-2,x+3,1],[x-1,x+2,1],[x-2,x+3,1]],
 ['left partial same-owner overlap',[x,x+3,1],[x-2,x+1,1],[x-2,x+3,1]],
 ['right partial same-owner overlap',[x-2,x+1,1],[x,x+3,1],[x-2,x+3,1]]
])test(`genuine ${completedConstructor?'completed':'original'} authority transition rejects ${name}`,async t=>{
 const f=await trustedFixture(t,{nativeAppend:true,originalPatchRows:[{y,runs:[prior]}]});
 const {state}=await f.api.qualifyCheckpoint({reader:f.reader});
 const appended=await appendNativeAuthority(f,{completedConstructor,nativePatchRows:[{y,runs:[next]}],
  mutatePatch:patch=>{patch.rows=[{y,runs:[union]}];}});
 const reader=new f.native.ImmutableReader(f.root,appended.candidate,{invocation:f.reader.invocation});
 await assert.rejects(f.api.qualifyTransition({state,reader}),/New native assignment overlaps a previously selected owner/);
 assert.deepEqual(nativeLiteral(state.patch.rows),[{y,runs:[prior]}]);
});

test('genuine native witness preserves exact eager result with multiple rows and unchanged legacy primitive',async t=>{
 const f=await trustedFixture(t,{nativeAppend:true}),c=await consumer(f),{state}=await f.api.qualifyCheckpoint({reader:f.reader});
 const appended=await appendNativeAuthority(f,{completedConstructor:true,nativePatchRows:[
  {y,runs:[[x-2,x-1,1],[x+1,x+3,1]]},{y:y+1,runs:[[x,x+1,1]]}]});
 const reader=new f.native.ImmutableReader(f.root,appended.candidate,{invocation:f.reader.invocation});
 const transition=await f.api.qualifyTransition({state,reader});assert.equal(transition.available,true);
 const projection=f.api.projectNativeRows({state:transition.candidate,rows:transition.changedNativeRows});
 const owners=state.certificate.entries.map(row=>({id:row[0],index:row[1]}));
 const expected=f.native.repairVisibilityWitnesses({candidates:f.native.newVisibleRepairCandidates(nativeLiteral(state.additions),nativeLiteral(transition.candidate.additions)),
  size,latitudes:f.api.projectVisibilityLatitudes({state:transition.candidate}),
  beforeRows:c.applyNativeAdditiveRows(projection.rows,state.patch,{size,owners}),
  afterRows:c.applyNativeAdditiveRows(projection.rows,transition.candidate.patch,{size,owners})});
 const actual=await c.compareSelectedCheckpointNative({transition});
 assert.deepEqual(actual.repair_visibility.witnesses,expected);assert.equal(actual.repair_visibility.new_components,1);
 assert.deepEqual(actual.native_row_scope.changed_rows,[y,y+1]);
 for(const witness of expected)assert(actual.native_row_scope.changed_rows.includes(witness.y));
 assert.deepEqual([...actual.native_row_scope.shared_base_reused_rows,...actual.native_row_scope.shared_base_acquired_rows].sort((a,b)=>a-b),[y,y+1]);
 assert.equal(expected[0].x,x-2);assert.equal(expected[0].y,y);
 assert.equal(actual.status,'no-new-native-loss');assert.equal(actual.lost_or_reassigned_cells,0);
 assert.equal(state.additions.at(0).component_id,'old');
 await assert.rejects(c.compareSelectedCheckpointNative({transition:{...transition}}),/private qualified selected transition/);
 f.api.releaseCheckpoint(state);
 await assert.rejects(c.compareSelectedCheckpointNative({transition}),/private qualified selected transition/);
});

test('genuine transition cannot hide a new native component under an old authority',async t=>{
 const f=await trustedFixture(t,{nativeAppend:true}),{state}=await f.api.qualifyCheckpoint({reader:f.reader});
 const appended=await appendNativeAuthority(f,{completedConstructor:true,mutateLedger:ledger=>{
  ledger.rows.find(row=>row.representation==='native-cells').authority_sha256=f.registry.entries[0].authority_sha256;
 }});
 const reader=new f.native.ImmutableReader(f.root,appended.candidate,{invocation:f.reader.invocation});
 await assert.rejects(f.api.qualifyTransition({state,reader}),/Candidate changed original appended primitive or exception/);
});

test('genuine source-qualified native first cell still fails current base owner-zero',async t=>{
 const bits=Math.ceil(Math.log2(size)),rows=[];let offset=0;
 for(let at=0;at<size;at++){const count=at<3||at===y?1:0;rows.push(offset,count);offset+=count;}
 const f=await trustedFixture(t,{nativeAppend:true,nativeLayout:{size,rows,
  runs:[2**bits,0,2*2**bits,0,3*2**bits+1,1,2**bits+x,x]}});
 const c=await consumer(f),{state}=await f.api.qualifyCheckpoint({reader:f.reader});
 const appended=await appendNativeAuthority(f,{completedConstructor:true});
 const reader=new f.native.ImmutableReader(f.root,appended.candidate,{invocation:f.reader.invocation});
 const transition=await f.api.qualifyTransition({state,reader});assert.equal(transition.available,true);
 await assert.rejects(c.compareSelectedCheckpointNative({transition}),/overlaps preexisting assigned native cells/);
});

test('genuine transition refuses a new native component with no cells',async t=>{
 const f=await trustedFixture(t,{nativeAppend:true}),{state}=await f.api.qualifyCheckpoint({reader:f.reader});
 const appended=await appendNativeAuthority(f,{mutateLedger:ledger=>{
  const row=ledger.rows.find(row=>row.representation==='native-cells');row.native_rows=[];row.native_cells=0;
 }});
 const reader=new f.native.ImmutableReader(f.root,appended.candidate,{invocation:f.reader.invocation});
 await assert.rejects(f.api.qualifyTransition({state,reader}),/Missing native component rows|cell count/);
});
