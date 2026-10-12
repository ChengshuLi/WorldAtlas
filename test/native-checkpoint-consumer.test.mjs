import test from 'node:test';
import assert from 'node:assert/strict';
import {applyNativeAdditiveRows,deriveEffectiveNativeRowDelta,compareEffectiveNativeRows} from '../scripts/check-effective-geographic-regression.mjs';

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
test('synthetic exact unchanged complete rows yield zero numerical delta',()=>{
 const before=[row(0),row(3,[[1,4,1],[8,10,2]]),row(15,[[0,16,1]])];
 const after=clone(before);
 assert.deepEqual(delta(before,after),[]);
 assert.deepEqual(compare([],[],[]),noLoss(0));
 assert.deepEqual(compare(before,after,[0,3,15]),noLoss(3));
 assert.deepEqual(after,before);
});

test('synthetic append derives only actual new rows and preserves prior owners',()=>{
 const before=[row(2,[[1,3,1]]),row(4,[[8,9,2]])];
 const after=[...clone(before),row(7,[[5,6,1]])];
 assert.deepEqual(delta(before,after),[7]);
 // A missing sparse delta row is not a complete zero-interval projection.
 assert.throws(()=>compare([], [after[2]], [7]));
 assert.deepEqual(compare([row(7)],[after[2]],[7]),noLoss(1));
});

test('synthetic same-count reassignment and mutation cannot hide behind counts',()=>{
 const before=[row(3,[[1,4,1]]),row(9,[[7,9,2]])];
 const after=[row(3,[[1,4,2]]),row(9,[[8,10,2]])];
 assert.deepEqual(delta(before,after),[3,9]);
 assert.deepEqual(compare(before,after,[3,9]),{
  checked_rows:2,lost_or_reassigned_cells:4,intervals:[
   {row:3,start:1,end:4,previous_owner:'alpha',candidate_owner:'beta'},
   {row:9,start:7,end:8,previous_owner:'beta',candidate_owner:null}]});
});

test('synthetic removals require symmetric row delta and explicit empty projection',()=>{
 const before=[row(2,[[0,3,1]]),row(8,[[10,12,2]])];
 const after=[row(2,[[0,2,1]])];
 assert.deepEqual(delta(before,after),[2,8]);
 assert.throws(()=>compare(before,after,[2,8]));
 assert.deepEqual(compare(before,[...after,row(8)],[2,8]),{
  checked_rows:2,lost_or_reassigned_cells:3,intervals:[
   {row:2,start:2,end:3,previous_owner:'alpha',candidate_owner:null},
   {row:8,start:10,end:12,previous_owner:'beta',candidate_owner:null}]});
});

test('synthetic absent versus explicit empty row remains a presence delta',()=>{
 assert.deepEqual(delta([], [row(0)]),[0]);
 assert.deepEqual(delta([row(0)], []),[0]);
 assert.deepEqual(delta([row(0)], [row(0)]),[]);
 assert.deepEqual(compare([row(0)],[row(0)],[0]),noLoss(1));
 assert.throws(()=>compare([row(0)],[],[0]));
 assert.throws(()=>compare([],[row(0)],[0]));
});

test('synthetic split intervals preserve owners while exact content delta remains visible',()=>{
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

test('synthetic repeated, unordered and foreign rows are rejected on both sides',()=>{
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

test('synthetic complete interval validation rejects malformed or foreign ownership',()=>{
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

test('synthetic requested scope rejects omission, clipping, unknown IDs and duplicate rows',()=>{
 const before=[row(1,[[0,2,1]]),row(3,[[4,5,2]])],after=clone(before);
 for(const rows of [undefined,null,{},[],[1],[3],[1,2,3],[3,1],[1,1,3],[-1,1,3],[1,3,16]]){
  assert.throws(()=>compare(before,after,rows));
 }
 assert.throws(()=>compare(before,[after[0]],[1,3]));
 assert.throws(()=>compare([before[0]],after,[1,3]));
 assert.deepEqual(compare(before,after,[1,3]),noLoss(2));
});

test('synthetic owner identity changes cannot be classified as unchanged',()=>{
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


test('synthetic missing owner rosters and owner identities fail complete projections',()=>{
 const rows=[row(1,[[0,2,1]])];
 for(const roster of [null,{},[],[null],[{}],[{id:''}],[{id:7}]]){
  for(const key of ['ownersBefore','ownersAfter']){
   assert.throws(()=>delta(rows,rows,{[key]:roster}));
   assert.throws(()=>compare(rows,rows,[1],{[key]:roster}));
  }
 }
});

test('synthetic exhaustive three-cell oracle independently checks 729 conservation pairs',()=>{
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

test('synthetic cumulative before and candidate patches each apply once to original native rows',()=>{
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

test('synthetic repeated cumulative application rejects same-owner assignments',()=>{
 const base=[row(2,[[0,2,1]])],patch={rows:[row(2,[[4,6,1]])]};
 const once=apply(base,patch);
 assert.equal(assignedCells(once),4);
 assert.throws(()=>apply(once,patch));
 // A candidate cumulative patch must start from original native rows, too.
 assert.throws(()=>apply(once,{rows:[row(2,[[4,6,1],[8,10,2]])]}));
});

test('synthetic additive overlap rejects identical, partial, contained and enclosing runs for either owner',()=>{
 const base=freeze([row(3,[[4,8,1]])]);
 for(const owner of [1,2])for(const [start,end] of [[4,8],[2,5],[7,10],[5,7],[2,10]]){
  assert.throws(()=>apply(base,freeze({rows:[row(3,[[start,end,owner]])]})));
 }
 // Touching endpoints are legal, including assignments to a different owner.
 const adjacent=apply(base,{rows:[row(3,[[2,4,2],[8,10,2]])]});
 assert.deepEqual(adjacent,[row(3,[[2,4,2],[4,8,1],[8,10,2]])]);
 assert.equal(assignedCells(adjacent),8);
});

test('synthetic complete cumulative patch validates rows even outside requested projection scope',()=>{
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

test('synthetic additive intervals validate all raw bounds and ownership before scope selection',()=>{
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

test('synthetic out-of-scope valid patch rows do not invent native projections',()=>{
 const patch=freeze({rows:[row(1,[[2,4,1]]),row(7,[[8,10,2]])]});
 assert.deepEqual(apply([],patch),[]);
 assert.deepEqual(apply([row(3,[[0,16,2]])],patch),[row(3,[[0,16,2]])]);
 const scoped=apply([row(1),row(3,[[0,16,2]])],patch);
 assert.deepEqual(scoped,[row(1,[[2,4,1]]),row(3,[[0,16,2]])]);
 assert.equal(assignedCells(scoped),18);
});

test('synthetic missing native row remains missing while explicit empty rows accept additive cells',()=>{
 const patch={rows:[row(5,[[2,4,1]])]};
 const missing=apply([],patch),explicit=apply([row(5)],patch);
 assert.deepEqual(missing,[]);
 assert.deepEqual(explicit,[row(5,[[2,4,1]])]);
 assert.deepEqual(apply([row(5)],{rows:[]}),[row(5)]);
 assert.throws(()=>compare(missing,explicit,[5]));
 assert.deepEqual(compare([row(5)],explicit,[5]),noLoss(1));
});

test('synthetic returned rows and intervals do not alias original base or cumulative patch',()=>{
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


test('synthetic no-additive state preserves complete native rows with fresh copies',()=>{
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
