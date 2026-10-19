import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {nativeRowLatitudes} from '../src/native-grid.js';
import test from 'node:test';
import assert from 'node:assert/strict';
import {applyNativeAdditiveRows,deriveEffectiveNativeRowDelta,compareEffectiveNativeRows} from '../scripts/selected-checkpoint-native.mjs';

// Synthetic numerical controls only. These helpers neither authenticate a
// selected snapshot nor establish producer/checkpoint custody or applicability.
const owners=[{index:1,id:'alpha',province_id:'parent',province_index:1},
 {index:2,id:'beta',province_id:'parent',province_index:1}];
const options={size:16,ownersBefore:owners,ownersAfter:owners};
const row=(y,runs=[])=>({y,runs});
const clone=value=>structuredClone(value);
const delta=(before,after,extra={})=>deriveEffectiveNativeRowDelta(before,after,{...options,...extra});
const compare=(before,after,rows,extra={})=>compareEffectiveNativeRows(before,after,{...options,...extra,rows});
const noLoss=checked_rows=>({checked_rows,lost_or_reassigned_cells:0,intervals:[]});

// The expected delta is derived from concrete row bodies, never aggregate counts.
test('synthetic exact unchanged complete rows yield zero numerical delta',async ()=>{
 const before=[row(0),row(3,[[1,4,1],[8,10,2]]),row(15,[[0,16,1]])];
 const after=clone(before);
 assert.deepEqual(delta(before,after),[]);
 assert.deepEqual(compare([],[],[]),noLoss(0));
 assert.deepEqual(compare(before,after,[0,3,15]),noLoss(3));
 assert.deepEqual(after,before);
});

test('synthetic append derives only actual new rows and preserves prior owners',async ()=>{
 const before=[row(2,[[1,3,1]]),row(4,[[8,9,2]])];
 const after=[...clone(before),row(7,[[5,6,1]])];
 assert.deepEqual(delta(before,after),[7]);
 // A missing sparse delta row is not a complete zero-interval projection.
 assert.throws(()=>compare([], [after[2]], [7]));
 assert.deepEqual(compare([row(7)],[after[2]],[7]),noLoss(1));
});

test('synthetic same-count reassignment and mutation cannot hide behind counts',async ()=>{
 const before=[row(3,[[1,4,1]]),row(9,[[7,9,2]])];
 const after=[row(3,[[1,4,2]]),row(9,[[8,10,2]])];
 assert.deepEqual(delta(before,after),[3,9]);
 assert.deepEqual(compare(before,after,[3,9]),{
  checked_rows:2,lost_or_reassigned_cells:4,intervals:[
   {row:3,start:1,end:4,previous_owner:'alpha',candidate_owner:'beta'},
   {row:9,start:7,end:8,previous_owner:'beta',candidate_owner:null}]});
});

test('synthetic removals require symmetric row delta and explicit empty projection',async ()=>{
 const before=[row(2,[[0,3,1]]),row(8,[[10,12,2]])];
 const after=[row(2,[[0,2,1]])];
 assert.deepEqual(delta(before,after),[2,8]);
 assert.throws(()=>compare(before,after,[2,8]));
 assert.deepEqual(compare(before,[...after,row(8)],[2,8]),{
  checked_rows:2,lost_or_reassigned_cells:3,intervals:[
   {row:2,start:2,end:3,previous_owner:'alpha',candidate_owner:null},
   {row:8,start:10,end:12,previous_owner:'beta',candidate_owner:null}]});
});

test('synthetic absent versus explicit empty row remains a presence delta',async ()=>{
 assert.deepEqual(delta([], [row(0)]),[0]);
 assert.deepEqual(delta([row(0)], []),[0]);
 assert.deepEqual(delta([row(0)], [row(0)]),[]);
 assert.deepEqual(compare([row(0)],[row(0)],[0]),noLoss(1));
 assert.throws(()=>compare([row(0)],[],[0]));
 assert.throws(()=>compare([],[row(0)],[0]));
});

test('synthetic split intervals preserve owners while exact content delta remains visible',async ()=>{
 const before=[row(5,[[0,6,1]])],after=[row(5,[[0,2,1],[2,6,1]])];
 assert.deepEqual(delta(before,after),[5]);
 assert.deepEqual(compare(before,after,[5]),noLoss(1));
 assert.deepEqual(compare([row(5,[[0,8,1]])],
  [row(5,[[0,2,1],[3,5,2],[6,8,1]])],[5]),{
  checked_rows:1,lost_or_reassigned_cells:4,intervals:[
   {row:5,start:2,end:3,previous_owner:'alpha',candidate_owner:null},
   {row:5,start:3,end:5,previous_owner:'alpha',candidate_owner:'beta'},
   {row:5,start:5,end:6,previous_owner:'alpha',candidate_owner:null}]});
});

test('synthetic repeated, unordered and foreign rows are rejected on both sides',async ()=>{
 const invalid=[null,{},[row(1),row(1)],[row(2),row(1)],
  [row(-1)],[row(16)],[row(1.5)],[row(Number.NaN)],
  [{y:1}],[{y:1,runs:null}]];
 for(const rows of invalid){
  assert.throws(()=>delta(rows,[]));
  assert.throws(()=>delta([],rows));
  assert.throws(()=>compare(rows,[],[]));
  assert.throws(()=>compare([],rows,[]));
 }
});

test('synthetic complete interval validation rejects malformed or foreign ownership',async ()=>{
 const invalidRuns=[null,{},[[0,1]],[[0,1,1,4]],[[0,0,1]],[[2,1,1]],
  [[-1,1,1]],[[0,17,1]],[[0,1.5,1]],[[0,1,0]],[[0,1,-1]],
  [[0,1,3]],[[0,1,1.5]],[[0,1,Number.NaN]],
  [[0,3,1],[2,4,2]],[[5,7,1],[1,2,2]]];
 for(const runs of invalidRuns){
  const rows=[row(1,runs)];
  assert.throws(()=>delta(rows,[]));
  assert.throws(()=>delta([],rows));
  assert.throws(()=>compare(rows,[row(1)],[1]));
  assert.throws(()=>compare([row(1)],rows,[1]));
 }
 for(const size of [0,-1,1.5,Number.NaN,Number.POSITIVE_INFINITY,'16']){
  assert.throws(()=>delta([],[],{size}));
  assert.throws(()=>compare([],[],[],{size}));
 }
});

test('synthetic requested scope rejects omission, clipping, unknown IDs and duplicate rows',async ()=>{
 const before=[row(1,[[0,2,1]]),row(3,[[4,5,2]])],after=clone(before);
 for(const rows of [undefined,null,{},[],[1],[3],[1,2,3],[3,1],[1,1,3],[-1,1,3],[1,3,16]]){
  assert.throws(()=>compare(before,after,rows));
 }
 assert.throws(()=>compare(before,[after[0]],[1,3]));
 assert.throws(()=>compare([before[0]],after,[1,3]));
 assert.deepEqual(compare(before,after,[1,3]),noLoss(2));
});

test('synthetic owner identity changes cannot be classified as unchanged',async ()=>{
 const before=[row(1,[[0,2,1]])],after=clone(before);
 const changedOwners=[{...owners[0],id:'replacement'},owners[1]];
 // A helper may reject roster drift or conservatively include the row.
 // Either behavior prevents identical indices hiding an owner reassignment.
 let detected;
 try{detected=delta(before,after,{ownersAfter:changedOwners});}
 catch(error){assert.match(error.message,/owner|roster|identity/i);return;}
 assert.deepEqual(detected,[1]);
 assert.deepEqual(compare(before,after,[1],{ownersAfter:changedOwners}),{
  checked_rows:1,lost_or_reassigned_cells:2,intervals:[
   {row:1,start:0,end:2,previous_owner:'alpha',candidate_owner:'replacement'}]});
});


test('synthetic missing owner rosters and owner identities fail complete projections',async ()=>{
 const rows=[row(1,[[0,2,1]])];
 for(const roster of [null,{},[],[null],[{}],[{id:''}],[{id:7}]]){
  for(const key of ['ownersBefore','ownersAfter']){
   assert.throws(()=>delta(rows,rows,{[key]:roster}));
   assert.throws(()=>compare(rows,rows,[1],{[key]:roster}));
  }
 }
});

test('synthetic exhaustive three-cell oracle independently checks 729 conservation pairs',async ()=>{
 const size=3;
 const states=Array.from({length:27},(_,n)=>Array.from({length:size},(_,x)=>Math.floor(n/3**x)%3));
 const intervals=cells=>{
  const runs=[];
  for(let x=0;x<size;x++){
   if(!cells[x])continue;
   const prior=runs.at(-1);
   if(prior&&prior[1]===x&&prior[2]===cells[x])prior[1]=x+1;
   else runs.push([x,x+1,cells[x]]);
  }
  return [row(1,runs)];
 };
 for(const old of states)for(const next of states){
  const before=intervals(old),after=intervals(next);
  assert.deepEqual(delta(before,after,{size}),old.every((owner,x)=>owner===next[x])?[]:[1]);
  const result=compare(before,after,[1],{size});
  const expected=old.flatMap((owner,x)=>owner&&owner!==next[x]?[{
   x,previous_owner:owners[owner-1].id,candidate_owner:next[x]?owners[next[x]-1].id:null}]:[]);
  const actual=result.intervals.flatMap(loss=>Array.from({length:loss.end-loss.start},(_,x)=>({
   x:loss.start+x,previous_owner:loss.previous_owner,candidate_owner:loss.candidate_owner})));
  assert.equal(result.checked_rows,1);
  assert.equal(result.lost_or_reassigned_cells,expected.length);
  assert.ok(result.intervals.every(loss=>loss.row===1));
  assert.deepEqual(actual,expected);
 }
});


const apply=(base,patch,extra={})=>applyNativeAdditiveRows(base,patch,{size:16,owners,...extra});
const freeze=value=>{
 if(value&&typeof value==='object'){Object.values(value).forEach(freeze);Object.freeze(value);}
 return value;
};
const assignedCells=rows=>rows.reduce((sum,{runs})=>sum+runs.reduce((n,[start,end])=>n+end-start,0),0);

test('synthetic cumulative before and candidate patches each apply once to original native rows',async ()=>{
 const base=freeze([row(2,[[0,2,1],[12,16,2]]),row(6)]);
 const beforePatch=freeze({rows:[row(2,[[4,6,1]])]});
 const candidatePatch=freeze({rows:[row(2,[[4,6,1],[8,10,2]]),row(6,[[1,3,1]])]});
 const original=clone({base,beforePatch,candidatePatch});
 const before=apply(base,beforePatch),candidate=apply(base,candidatePatch);
 assert.deepEqual(before,[row(2,[[0,2,1],[4,6,1],[12,16,2]]),row(6)]);
 assert.deepEqual(candidate,[row(2,[[0,2,1],[4,6,1],[8,10,2],[12,16,2]]),row(6,[[1,3,1]])]);
 assert.equal(assignedCells(before),8);
 assert.equal(assignedCells(candidate),12);
 assert.deepEqual(delta(before,candidate),[2,6]);
 assert.deepEqual(compare(before,candidate,[2,6]),noLoss(2));
 assert.deepEqual({base,beforePatch,candidatePatch},original);
});

test('synthetic repeated cumulative application rejects same-owner assignments',async ()=>{
 const base=[row(2,[[0,2,1]])],patch={rows:[row(2,[[4,6,1]])]};
 const once=apply(base,patch);
 assert.equal(assignedCells(once),4);
 assert.throws(()=>apply(once,patch));
 // A candidate cumulative patch must start from original native rows, too.
 assert.throws(()=>apply(once,{rows:[row(2,[[4,6,1],[8,10,2]])]}));
});

test('synthetic additive overlap rejects identical, partial, contained and enclosing runs for either owner',async ()=>{
 const base=freeze([row(3,[[4,8,1]])]);
 for(const owner of [1,2])for(const [start,end] of [[4,8],[2,5],[7,10],[5,7],[2,10]]){
  assert.throws(()=>apply(base,freeze({rows:[row(3,[[start,end,owner]])]})));
 }
 // Touching endpoints are legal, including assignments to a different owner.
 const adjacent=apply(base,{rows:[row(3,[[2,4,2],[8,10,2]])]});
 assert.deepEqual(adjacent,[row(3,[[2,4,2],[4,8,1],[8,10,2]])]);
 assert.equal(assignedCells(adjacent),8);
});

test('synthetic complete cumulative patch validates rows even outside requested projection scope',async ()=>{
 const base=[row(2,[[0,2,1]])];
 const invalidRows=[null,{},[row(1),row(1)],[row(3),row(1)],
  [row(-1)],[row(16)],[row(1.5)],[row(Number.NaN)],
  [null],[{y:1}],[{y:1,runs:null}]];
 for(const rows of invalidRows){
  assert.throws(()=>apply(base,{rows}));
  assert.throws(()=>apply(rows,{rows:[]}));
 }
 for(const patch of [{}, {rows:undefined}])assert.throws(()=>apply(base,patch));
});

test('synthetic additive intervals validate all raw bounds and ownership before scope selection',async ()=>{
 const invalidRuns=[null,{},[[0,1]],[[0,1,1,4]],[[0,0,1]],[[2,1,1]],
  [[-1,1,1]],[[0,17,1]],[[0,1.5,1]],[[0,1,0]],[[0,1,-1]],
  [[0,1,3]],[[0,1,1.5]],[[0,1,Number.NaN]],
  [[0,3,1],[2,4,2]],[[5,7,1],[1,2,2]]];
 for(const runs of invalidRuns){
  assert.throws(()=>apply([row(2)],{rows:[row(2,runs)]}));
  assert.throws(()=>apply([row(2)],{rows:[row(1,runs)]}));
  assert.throws(()=>apply([row(2,runs)],{rows:[]}));
 }
 for(const size of [0,-1,1.5,Number.NaN,Number.POSITIVE_INFINITY,'16']){
  assert.throws(()=>apply([],{rows:[]},{size}));
 }
 for(const roster of [null,{},[],[null],[{}],[{id:''}],[{id:7}]]){
  assert.throws(()=>apply([row(2,[[0,1,1]])],{rows:[]},{owners:roster}));
  assert.throws(()=>apply([row(2)],{rows:[row(2,[[0,1,1]])]},{owners:roster}));
 }
});

test('synthetic out-of-scope valid patch rows do not invent native projections',async ()=>{
 const patch=freeze({rows:[row(1,[[2,4,1]]),row(7,[[8,10,2]])]});
 assert.deepEqual(apply([],patch),[]);
 assert.deepEqual(apply([row(3,[[0,16,2]])],patch),[row(3,[[0,16,2]])]);
 const scoped=apply([row(1),row(3,[[0,16,2]])],patch);
 assert.deepEqual(scoped,[row(1,[[2,4,1]]),row(3,[[0,16,2]])]);
 assert.equal(assignedCells(scoped),18);
});

test('synthetic missing native row remains missing while explicit empty rows accept additive cells',async ()=>{
 const patch={rows:[row(5,[[2,4,1]])]};
 const missing=apply([],patch),explicit=apply([row(5)],patch);
 assert.deepEqual(missing,[]);
 assert.deepEqual(explicit,[row(5,[[2,4,1]])]);
 assert.deepEqual(apply([row(5)],{rows:[]}),[row(5)]);
 assert.throws(()=>compare(missing,explicit,[5]));
 assert.deepEqual(compare([row(5)],explicit,[5]),noLoss(1));
});

test('synthetic returned rows and intervals do not alias original base or cumulative patch',async ()=>{
 const base=freeze([row(1,[[0,2,1]]),row(3,[[8,10,2]]),row(5)]);
 const patch=freeze({rows:[row(1,[[4,6,2]])]});
 const original=clone({base,patch});
 const result=apply(base,patch);
 assert.notStrictEqual(result,base);
 for(let i=0;i<base.length;i++){
  assert.notStrictEqual(result[i],base[i]);
  assert.notStrictEqual(result[i].runs,base[i].runs);
 }
 result[0].runs[0][0]=1;
 result[0].runs[1][0]=5;
 result[1].runs[0][0]=9;
 result[2].runs.push([1,2,1]);
 assert.deepEqual({base,patch},original);
});


test('synthetic no-additive state preserves complete native rows with fresh copies',async ()=>{
 const base=freeze([row(1,[[0,2,1],[4,6,2]]),row(3)]);
 for(const patch of [null,undefined]){
  const result=apply(base,patch);
  assert.deepEqual(result,base);
  assert.notStrictEqual(result,base);
  for(let i=0;i<base.length;i++){
   assert.notStrictEqual(result[i],base[i]);
   assert.notStrictEqual(result[i].runs,base[i].runs);
   for(let j=0;j<base[i].runs.length;j++)assert.notStrictEqual(result[i].runs[j],base[i].runs[j]);
  }
  assert.throws(()=>apply([row(1,[[0,17,1]])],patch));
 }
});

// Share only deterministic miniature history; each call owns its physical copy,
// imported native consumer, reader and private checkpoint state.
import {trustedFixture as sharedFixture} from './fixtures/selected-checkpoint.mjs';
const trustedFixture=t=>sharedFixture(t,{nativeConsumer:true});

test('native consumer seed copies isolate latitude bytes, private state and cleanup',async t=>{
 const a=await trustedFixture(t),b=await trustedFixture(t);
 assert.notEqual(a.root,b.root);assert.equal(a.selected,b.selected);
 const latitude='data/latitudes.f64le.gz',expected=fs.readFileSync(path.join(b.root,latitude));
 const ordinary=await sharedFixture(t);assert.notEqual(ordinary.selected,a.selected);
 assert.equal(fs.existsSync(path.join(ordinary.root,latitude)),false);
 const qualified=await a.api.qualifyCheckpoint({reader:a.reader});assert.equal(qualified.available,true);
 await assert.rejects(b.api.qualifyTransition({state:qualified.state,reader:b.reader}),/private qualified/);
 a.save(latitude,Buffer.from('changed only in the first consumer'));
 assert.deepEqual(fs.readFileSync(path.join(b.root,latitude)),expected);
 a.api.releaseCheckpoint(qualified.state);fs.rmSync(a.root,{recursive:true});
 assert.equal(b.git('status','--porcelain').toString(),'');
 const later=await b.api.qualifyCheckpoint({reader:b.reader});assert.equal(later.available,true);
 assert.deepEqual([...b.api.projectVisibilityLatitudes({state:later.state})],[...nativeRowLatitudes(4)]);
});

function candidateProducts(f,{ledger=f.ledger,patch=f.patch}={}){
 f.save('candidate/ledger.json',ledger);const l=f.commit();
 patch={...patch,ledger_sha256:f.pin('candidate/ledger.json',l).sha256};f.save('candidate/patch.json',patch);const p=f.commit();
 const assets={...f.sidecar.logical_asset_map,ledger:f.pin('candidate/ledger.json',l),patch:f.pin('candidate/patch.json',p)};
 f.save('candidate/envelope.json',{...f.envelope,...assets});const e=f.commit();
 f.save('candidate/sidecar.json',{...f.sidecar,logical_asset_map:assets,runtime_envelope:f.pin('candidate/envelope.json',e)});const sc=f.commit();
 const side=f.pin('candidate/sidecar.json',sc);
 f.save('data/ownership-selection.json',{...f.selection,additive_release:{path:side.path,bytes:side.bytes,sha256:side.sha256}});return f.commit();
}

async function nativeTransition(f,candidate=f.selected){
 const qualified=(await f.api.qualifyCheckpoint({reader:f.reader}));
 assert.equal(qualified.available,true);
 const reader=new f.native.ImmutableReader(f.root,candidate,{invocation:f.reader.invocation});
 const transition=(await f.api.qualifyTransition({state:qualified.state,reader}));
 return {transition,reader};
}

test('actual native consumer authenticates zero delta without a full selection or native body read',async t=>{
 const f=await trustedFixture(t),{transition,reader}=await nativeTransition(f);
 assert.equal(transition.available,true);assert.deepEqual(transition.changedNativeRows,[]);
 const inventory=[...f.reader.inventory,...reader.inventory];
 const report=await f.native.compareSelectedCheckpointNative({transition});
 assert.equal(report.status,'no-new-native-loss');assert.equal(report.affected_rows,0);
 assert.equal(report.lost_or_reassigned_cells,0);assert.deepEqual(report.intervals,[]);
 assert.deepEqual(report.native_row_scope.shared_base_acquired_rows,[]);
 assert.deepEqual([...f.reader.inventory,...reader.inventory],inventory);
 assert.equal(report.checkpoint_custody.shared_base.accepted_checkpoint.checkpoint_id,'fixture');
 f.api.releaseCheckpoint(transition.baseline);
});

test('actual native consumer rejects forged, foreign-invocation and expired zero-delta transitions',async t=>{
 const f=await trustedFixture(t),{transition}=await nativeTransition(f);
 for(const fake of [{...transition},JSON.parse(JSON.stringify(transition)),{available:true,changedNativeRows:[]}]){
  await assert.rejects(f.native.compareSelectedCheckpointNative({transition:fake}),/private qualified selected transition/);
 }
 const foreignReader=new f.native.ImmutableReader(f.root,f.selected);
 await assert.rejects(async()=>(await f.api.qualifyTransition({state:transition.baseline,reader:foreignReader})),/Foreign or expired checkpoint invocation/);
 assert.throws(()=>transition.changedNativeRows.push(1),TypeError);
 f.api.releaseCheckpoint(transition.baseline);
 await assert.rejects(f.native.compareSelectedCheckpointNative({transition}),/private qualified selected transition/);
});

test('actual unchanged native rows cannot hide missing complete ledger exceptions',async t=>{
 const f=await trustedFixture(t);
 const candidate=candidateProducts(f,{ledger:{...f.ledger,scope_ids:['old'],rows:[f.ledger.rows[0]]}});
 await assert.rejects(nativeTransition(f,candidate),/Old complete ledger/);
});

test('actual changed transport bytes with unchanged declarations require explicit cold validation',async t=>{
 const f=await trustedFixture(t);
 f.save('data/native/runs.bin.gz',Buffer.from('changed transport despite unchanged manifest'));const candidate=f.commit();
 const {transition}=await nativeTransition(f,candidate);
 assert.equal(transition.available,false);assert.equal(transition.cold,'candidate');
 assert.match(transition.reason,/routing|input/i);
 await assert.rejects(f.native.compareSelectedCheckpointNative({transition}),/private qualified selected transition/);
 f.api.releaseCheckpoint(transition.baseline);
});


test('actual visibility projection authenticates the selected whole normative latitude table',async t=>{
 const f=await trustedFixture(t),qualified=(await f.api.qualifyCheckpoint({reader:f.reader}));
 assert.equal(qualified.available,true);
 const result=f.api.projectVisibilityLatitudes({state:qualified.state});
 assert.deepEqual([...result],[...nativeRowLatitudes(4)]);
 assert.ok([...f.reader.inventory.values()].some(p=>p.path==='data/latitudes.f64le.gz'&&p.whole_body_consumed));
 assert.throws(()=>f.api.projectVisibilityLatitudes({state:structuredClone(qualified.state)}),/private qualified/);
});

import {referenceCheckpointFixture} from './fixtures/selected-checkpoint.mjs';
test('validated reference metadata changes parents while native owners and cells stay conserved',async t=>{
 const f=await referenceCheckpointFixture(t),reader=new f.native.ImmutableReader(f.repo,f.candidate,{invocation:f.reader.invocation});
 const transition=(await f.api.qualifyTransition({state:f.state,reader}));
 assert.equal(transition.available,true);
 const before=transition.baseline.certificate,after=transition.candidate.certificate;
 assert.equal(before.entries[0][2],'P');assert.equal(after.entries[0][2],'Q');
 assert.deepEqual(after.entries.map(row=>[row[0],row[1],row[7],row[8],row[9]]),before.entries.map(row=>[row[0],row[1],row[7],row[8],row[9]]));
 assert.notEqual(after.entries[0][6],before.entries[0][6]);
 const projected=f.api.projectSourceFeatures({state:transition.candidate,ids:['A']});
 assert.equal(projected.features[0].properties.parent_id,'Q');
 const consumer=await import(pathToFileURL(path.join(f.repo,'scripts/selected-checkpoint-native.mjs')));
 const result=await consumer.compareSelectedCheckpointNative({transition});
 assert.equal(result.status,'no-new-native-loss');assert.equal(result.affected_rows,0);
 const census=f.api.checkpointRouteCensus({transition});
 for(const name of ['data/hierarchy.json','data/geography/fixture.json','data/geographic-releases/current-manifest.json'])
  assert.equal(census.routes.find(p=>p.path===name).tree,reader.treeRoute(name));
});
