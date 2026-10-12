import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';
import {gzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {shuffleOwnershipBytes} from '../src/ownership-codec.js';
import {valueBytes,valueSha,coordinateBounds} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
import {deriveCoordinateDelta} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint.mjs';
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

// Ordinary-Git fixture adapted from test/selected-checkpoint.test.mjs at
// shared PR1782 head34b23251737b55ad2fb0d19555cf451f78de150a. It exercises
// production private admission; no synthetic handle or authority hook exists.
const MODULE='coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint.mjs';
const CATALOGUE='coordination/engineering/selected-checkpoint-reuse-20261012/accepted-checkpoints.json';
const CODE=[MODULE,'coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs','scripts/check-effective-geographic-regression.mjs','src/ownership-codec.js'];
const sha=b=>createHash('sha256').update(b).digest('hex');
const polygon=(x,y=0)=>({type:'Polygon',coordinates:[[[x,y],[x+.2,y],[x+.2,y+.2],[x,y+.2],[x,y]]]});
const feature=(id,x)=>({type:'Feature',id,properties:{id,parent_id:'parent'},geometry:polygon(x)});
function fixtures(){
 const features=[feature('A',0),feature('B',1),feature('C',5)];
 const rows=features.map((f,i)=>[f.id,i+1,'parent',1,'data/source.json',i,valueSha(f),valueSha(f.geometry),valueSha({base_geometry_sha256:valueSha(f.geometry),additions:[]}),coordinateBounds(f.geometry)]);
 return {features,certificate:{version:2,kind:'selected-coordinate-neighbor-certificate-v2',entry_fields:['id','index','parent_id','parent_index','source','ordinal','whole_feature_sha256','geometry_sha256','effective_geometry_sha256','boxes'],binding:{selection:{old:true},sources:[],owners_sha256:valueSha(rows.map(r=>r.slice(0,4)))},entries:rows,inputs:[]}};
}
function addition(id,target,index,base,x){const geometry=polygon(x);return {component_id:id,target_id:target,pixelIndex:index,base_geometry_sha256:base,geometry,geometry_sha256:valueSha(geometry)};}

// This is a fresh miniature trusted repository, not a test-only authority hook.
// The real entry reads its ordinary committed catalogue and products exactly as
// production does. Candidate edits never control that executing catalogue.
async function trustedFixture(t,{incompleteNative=false}={}){
 const root=fs.mkdtempSync(path.join(process.cwd(),'.checkpoint-test-'));
 t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 const git=(...a)=>execFileSync('git',['-c','core.hooksPath=/dev/null','-c','user.name=Checkpoint fixture','-c','user.email=checkpoint@example.invalid','-C',root,...a],{env:{...process.env,GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_GLOBAL:'/dev/null',GIT_NO_LAZY_FETCH:'1'},stdio:['ignore','pipe','pipe']});
 const save=(name,value)=>{const f=path.join(root,name);fs.mkdirSync(path.dirname(f),{recursive:true});fs.writeFileSync(f,Buffer.isBuffer(value)?value:valueBytes(value));};
 const commit=()=>{git('add','.');git('commit','-qm','Checkpoint fixture');return git('rev-parse','HEAD').toString().trim();};
 git('init','-q');for(const name of CODE)save(name,fs.readFileSync(name));save('package.json',{type:'module'});
 const {features,certificate}=fixtures(), source={type:'FeatureCollection',features};save('data/source.json',source);
 const reference={id:'geography:fixture',hierarchy_sha256:'a'.repeat(64),footprints_sha256:'b'.repeat(64)};
 const encode=(name,kind,values)=>{const words=Uint32Array.from(values),canonical=Buffer.from(words.buffer),encoded=gzipSync(shuffleOwnershipBytes(words));save('data/'+name,encoded);return {path:name,kind,offset:0,bytes:encoded.length,sha256:sha(encoded),decoded_bytes:canonical.length,decoded_sha256:sha(canonical),words:words.length,encoding:'byte-shuffle'};};
 const parts=[encode('native/rows.bin.gz','rows',[0,1,incompleteNative?2:1,1,2,1,3,0]),encode('native/runs.bin.gz','runs',[4,0,8,0,13,1])];
 const compressedParts=parts.map(p=>fs.readFileSync(path.join(root,'data',p.path))),whole=Buffer.concat(compressedParts),fragment=gzipSync(whole);
 save('data/transport/fragment.gz',fragment);
 const index={version:1,kind:'ordered-exact-original-byte-fragments',whole_bytes:whole.length,whole_sha256:sha(whole),files:parts.map((p,i)=>({path:p.path,mode:'100644',offset:i?parts[0].bytes:0,bytes:p.bytes,sha256:p.sha256})),parts:[{path:'fragment.gz',offset:0,bytes:fragment.length,sha256:sha(fragment),decoded_bytes:whole.length,decoded_sha256:sha(whole)}]};save('data/transport/index.json',index);
 const manifest={version:1,size:4,coordinateBits:2,method:'native-linear-evenodd-first-owner-v1',native_latitudes:[],hierarchy_sha256:reference.hierarchy_sha256,original_assets:{},parts,runWords:6,native_asset_transport:{version:1,kind:index.kind,index:{path:'data/transport/index.json',bytes:valueBytes(index).length,sha256:valueSha(index)},logical_assets:2,original_compressed_bytes:whole.length}};
 save('data/manifest.json',manifest);save('data/owners.json',[{id:'A',index:1},{id:'B',index:2},{id:'C',index:3}]);
 const primitive=addition('old','A',1,certificate.entries[0][7],.3);
 const literal={...primitive,base_geometry:features[0].geometry,disposition:'assigned',native_cells:1,source_receipt_sha256:'c'.repeat(64)};
 const originalPatch={version:1,kind:'unassigned-native-cells-v1',rows:[{y:1,runs:[[2,3,1]]}]};
 save('original/patch-one.json',originalPatch);save('original/rule.json',{version:1});const one=commit();
 const pin=(name,at=git('rev-parse','HEAD').toString().trim())=>{const body=git('show',at+':'+name),tree=git('ls-tree',at,'--',name).toString().split(/\s+/);return {commit:at,path:name,mode:tree[0],git_blob_oid:tree[2],bytes:body.length,sha256:sha(body)};};
 save('original/publication.json',{assets:[{path:'patch-one.json',bytes:pin('original/patch-one.json').bytes,sha256:pin('original/patch-one.json').sha256}]});
 const two=commit();save('original/binding.json',{native_proof:{publication:pin('original/publication.json'),assets:[pin('original/patch-one.json',one)]}});const three=commit();
 const entry={policy_id:'retained-source-literal-additions',policy_version:1,rule_preimage:pin('original/rule.json',one),rule_sha256:pin('original/rule.json',one).sha256,source_authority:pin('original/binding.json',three)};entry.authority_sha256=valueSha(entry);
 const registry={version:1,kind:'retained-rule-authority-registry-v1',entries:[entry]};save('data/registry.json',registry);
 const baseSelection={version:1,method:manifest.method,manifest_path:'data/manifest.json',sha256:pin('data/manifest.json',one).sha256,release_id:reference.id,selected_geography:{version:1,kind:'complete-world-index-with-exact-encoded-overrides',path:'data/bank.json',bytes:1,sha256:'d'.repeat(64)}};
 const target={target_id:'A',pixelIndex:1,geometry:features[0].geometry,geometry_sha256:valueSha(features[0].geometry)};
 const currentRows=[{y:1,runs:[[0,1,2]]}];
 const request={base_selection:baseSelection,authority_registry_sha256:valueSha(registry),current_targets:[target],current_rows:currentRows,original_patch_sha256s:[valueSha(originalPatch)],acquisition:{predecessor_rows:[],predecessor_proof:null,native_inputs:[]}};
 const rebind={request,result:{native:{rows:originalPatch.rows}},facts:{acquisition_phases:[]},publication:{},operating:{}};
 for(const [name,body]of Object.entries(rebind))save('accepted-rebind/'+name+'.json',body);const four=commit();
 const rc={version:1,kind:'qualified-native-additive-current-bank-rebind-v1',execution_commit:one,base_selection:baseSelection,authority_registry_sha256:valueSha(registry),...Object.fromEntries(Object.keys(rebind).map(name=>[name,pin('accepted-rebind/'+name+'.json',four)]))};save('accepted-rebind/certificate.json',rc);const five=commit();
 const ledger={version:2,kind:'native-additive-repair-ledger-v2',authority_registry_sha256:valueSha(registry),scope_ids:['old','rejected'],rows:[{...literal,authority_sha256:entry.authority_sha256},{component_id:'rejected',disposition:'rejected',reason:'complete original exception',authority_sha256:entry.authority_sha256}],parent_inventory:{components:2,roster_sha256:'e'.repeat(64)},current_rebind:pin('accepted-rebind/certificate.json',five),current_targets:[target]};save('data/ledger.json',ledger);const six=commit();
 const normalized=[{...literal,authority_sha256:entry.authority_sha256,rule_sha256:entry.rule_sha256}];
 const effective={...reference,footprints_sha256:valueSha({domain:'worldatlas-effective-native-footprints:v2',base_reference:reference,authority_registry_sha256:valueSha(registry),ledger_sha256:pin('data/ledger.json',six).sha256,components:normalized})};
 const patch={version:2,kind:'unassigned-native-cells-v1',authority_registry_sha256:valueSha(registry),ledger_sha256:pin('data/ledger.json',six).sha256,base_reference:reference,effective_reference:effective,rows:originalPatch.rows};save('data/patch.json',patch);const seven=commit();
 const assets={base_manifest:pin('data/manifest.json',one),owner_roster:pin('data/owners.json',one),ledger:pin('data/ledger.json',six),patch:pin('data/patch.json',seven)};
 const envelope={version:2,kind:'retained-native-base-plus-delta-v2',base_reference:reference,effective_reference:effective,...assets};save('data/envelope.json',envelope);const eight=commit();
 const sidecar={version:2,kind:'retained-native-additive-selection-v2',base_selection:baseSelection,authority_registry:pin('data/registry.json',four),logical_asset_map:assets,runtime_envelope:pin('data/envelope.json',eight)};save('data/sidecar.json',sidecar);const nine=commit();
 const selection={...baseSelection,additive_release:{path:'data/sidecar.json',bytes:pin('data/sidecar.json',nine).bytes,sha256:pin('data/sidecar.json',nine).sha256}};save('data/ownership-selection.json',selection);const selected=commit();
 const sourcePin={...pin('data/source.json',one),kind:'ordinary-immutable-git-source'};
 const additions=normalized.map(row=>({...row,base_geometry:target.geometry,base_geometry_sha256:target.geometry_sha256}));
 const derived=deriveCoordinateDelta({certificate,oldAdditions:[],additions,selection}).certificate;
 const full={...derived,binding:{...derived.binding,release:reference,sources:[sourcePin]},inputs:[{path:'data/source.json',source:sourcePin,whole_body_sha256:sourcePin.sha256,bytes:sourcePin.bytes}]};
 const execution_code=CODE.map(name=>pin(name,one)),runtime=[{path:process.execPath,bytes:fs.statSync(process.execPath).size,sha256:'f'.repeat(64)}];
 const facts={version:1,kind:'trusted-selected-coordinate-stage-v1',candidate_code_executed:false,selected_commit:selected,executing_commit:one,execution_code,runtime,binding:full.binding,complete_owners:3,complete_sources:1};
 const compressed=gzipSync(valueBytes(full));save('accepted/certificate.json.gz',compressed);save('accepted/facts.json',facts);
 const publication={version:1,kind:facts.kind,complete:true,facts:{path:'facts.json',bytes:valueBytes(facts).length,sha256:valueSha(facts)},certificate:{path:'certificate.json.gz',bytes:compressed.length,sha256:sha(compressed),decoded_bytes:valueBytes(full).length,decoded_sha256:valueSha(full)}};save('accepted/publication.json',publication);
 const inventory=['data/source.json','data/manifest.json','data/owners.json','data/registry.json','data/ledger.json','data/patch.json','data/sidecar.json','data/envelope.json','data/native/rows.bin.gz','data/native/runs.bin.gz'].map(name=>pin(name,selected));
 save('accepted/custody.json',{complete_cold_custody:[{facts,publication,effective_additions:additions,inventory}]});
 save('accepted/routes.json',inventory.map(p=>p.path).sort().map(name=>({path:name,tree:git('ls-tree','-z',selected,'--',name).toString()})));const accepted=commit();
 const rootRow={id:'fixture',accepted_head:accepted,selected_commit:selected,selection_sha256:valueSha(selection),execution_commit:one,execution_code_sha256:valueSha(execution_code),runtime_sha256:valueSha(runtime),facts:pin('accepted/facts.json'),certificate:{...pin('accepted/certificate.json.gz'),decoded_bytes:valueBytes(full).length,decoded_sha256:valueSha(full)},publication:pin('accepted/publication.json'),custody:pin('accepted/custody.json'),routes:pin('accepted/routes.json')};
 save(CATALOGUE,{version:1,kind:'accepted-selected-checkpoints-v1',qualifier_code:CODE.map(name=>{const p=pin(name);return {path:name,bytes:p.bytes,sha256:p.sha256};}),checkpoints:[rootRow]});commit();
 const api=await import(pathToFileURL(path.join(root,MODULE))),native=await import(pathToFileURL(path.join(root,'scripts/check-effective-geographic-regression.mjs')));
 const reader=new native.ImmutableReader(root,selected,{allowance:{phaseBytes:512*1024**2,rssBytes:512*1024**2}}),budget={shared:reader.budget,carriedBytes:1024};
 return {api,native,reader,budget,selected,root,git,save,commit,pin,ledger,patch,sidecar,envelope,selection,rootRow};
}

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
 const qualified=f.api.qualifyCheckpoint({reader:f.reader,budget:f.budget});
 assert.equal(qualified.available,true);
 const reader=new f.native.ImmutableReader(f.root,candidate,{allowance:f.reader.allowance,budget:f.reader.budget});
 const transition=f.api.qualifyTransition({state:qualified.state,reader,budget:f.budget});
 return {transition,reader};
}

test('actual native consumer authenticates zero delta without a full selection or native body read',async t=>{
 const f=await trustedFixture(t),{transition,reader}=await nativeTransition(f);
 assert.equal(transition.available,true);assert.deepEqual(transition.changedNativeRows,[]);
 const inventory=[...f.reader.inventory,...reader.inventory];
 const report=await f.native.compareSelectedCheckpointNative({transition,budget:f.budget});
 assert.equal(report.status,'no-new-native-loss');assert.equal(report.affected_rows,0);
 assert.equal(report.lost_or_reassigned_cells,0);assert.deepEqual(report.intervals,[]);
 assert.deepEqual(report.native_row_scope.shared_base_acquired_rows,[]);
 assert.deepEqual([...f.reader.inventory,...reader.inventory],inventory);
 assert.ok(report.phases[0].retained_phase_bytes<=f.reader.allowance.phaseBytes);
 assert.equal(report.checkpoint_custody.shared_base.accepted_checkpoint.checkpoint_id,'fixture');
 f.api.releaseCheckpoint(transition.baseline);
});

test('actual native consumer rejects forged, foreign-budget and expired zero-delta transitions',async t=>{
 const f=await trustedFixture(t),{transition}=await nativeTransition(f);
 for(const fake of [{...transition},JSON.parse(JSON.stringify(transition)),{available:true,changedNativeRows:[]}]){
  const carry=f.budget.carriedBytes;
  await assert.rejects(f.native.compareSelectedCheckpointNative({transition:fake,budget:f.budget}),/private qualified selected transition/);
  assert.equal(f.budget.carriedBytes,carry);
 }
 await assert.rejects(f.native.compareSelectedCheckpointNative({transition,budget:{...f.budget}}),/Foreign, expired or independently budgeted/);
 assert.throws(()=>transition.changedNativeRows.push(1),TypeError);
 f.api.releaseCheckpoint(transition.baseline);
 await assert.rejects(f.native.compareSelectedCheckpointNative({transition,budget:f.budget}),/private qualified selected transition/);
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
 await assert.rejects(f.native.compareSelectedCheckpointNative({transition,budget:f.budget}),/private qualified selected transition/);
 f.api.releaseCheckpoint(transition.baseline);
});

test('actual native consumer admits caller carry before returning an empty success',async t=>{
 const f=await trustedFixture(t),{transition}=await nativeTransition(f);
 f.budget.carriedBytes+=f.reader.allowance.phaseBytes;
 await assert.rejects(f.native.compareSelectedCheckpointNative({transition,budget:f.budget}),/exceeds current allowance/);
});
