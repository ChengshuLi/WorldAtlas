import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import assert from 'node:assert/strict';
import {registeredOriginalPhysicalProduct,readRegisteredAdministrativeHandoff,registeredAdministrativeHandoff,registeredAdministrativeViews,originalAdministrativeCandidateHash,retainedAdministrativeSourcePremises,retainedAdministrativeFragmentPremises,combineNativeBatch,retainedCountySourcePremises,retainedLandSourcePremises,wholePrimitivePointsetEqual,inventoryRows,joinInventoryFacts,restoreInventoryRow,candidateDisposition,admitInventoryDestination,selectedBankResolutions,inventoryGroup,restoreGroupedInventoryRow} from '../scripts/additive-gap-repair.mjs';
import {footprintValueSha256 as hash} from '../src/effective-footprint.js';
const row=(id,status='mapped-land-support')=>({component_id:id,candidate_feature_sha256:hash(id),candidate_geometry_sha256:hash([id]),status,
 physical_authority:'unapproved',physical_status:'unknown-source-fitness-and-observation-date',physical_limits:['original retained source limits'],complete_support:{whole_original_geometry:true}});
const all=[row('one'),row('water','mapped-inland-water-support'),row('mixed','mixed-source-support'),row('unknown','unknown')];
const roster=rows=>hash(rows.map(r=>({id:r.component_id,feature_sha256:r.candidate_feature_sha256})));
const parent={version:1,components:4,report_sha256:'a'.repeat(64),roster_sha256:roster(all)};
const source={commit:'b'.repeat(40),path:'original.gz',sha256:'c'.repeat(64)};
const rawRows=rows=>rows.map(row=>Buffer.from(JSON.stringify(row)+'\n'));
const child=rows=>inventoryRows(rows,{source,parent,expectedIds:rows.map(r=>r.component_id),expectedRosterSha256:roster(rows),originalRecordBytes:rawRows(rows)});
const batchSource=(id,owner=1,compatible=true)=>({component_id:id,target_id:'target-'+owner,pixelIndex:owner,source_compatible:compatible,
 physical_authority:'unapproved',physical_status:'source-relative-only',failed_premises:compatible?[]:['parent-coverage'],limits:['synthetic mechanism fixture']});
const batchCandidate=(id,owner,runs)=>({component_id:id,target_id:'target-'+owner,pixelIndex:owner,row_start:1,row_end:2,rows:[{y:1,runs:runs.map(([start,end])=>[start,end,owner])}]});
const batch=(sources,candidates,old=[],scope=sources.map(row=>row.component_id))=>combineNativeBatch({scopeIds:scope,sourceRows:sources,candidates,
 ownerRows:[{y:1,complete_owner_intervals:old}],size:8});
test('shared batch preserves every source exception and distinguishes positive geometry with zero native cells',()=>{
 const sources=[batchSource('a'),batchSource('zero'),batchSource('b'),batchSource('parent-1',1,false),batchSource('parent-2',1,false)];
 const result=batch(sources,[batchCandidate('a',1,[[0,2]]),batchCandidate('zero',1,[]),batchCandidate('b',1,[[4,7]])]);
 assert.deepEqual(result.decisions.map(row=>[row.component_id,row.disposition]),[['a','assigned'],['zero','zero-cell'],['b','assigned'],['parent-1','rejected'],['parent-2','rejected']]);
 assert.equal(result.assigned_cells,5);assert.equal(result.assigned_components,2);assert.equal(result.zero_cell_components,1);assert.equal(result.source_exceptions,2);
 assert(result.decisions.every(row=>row.physical_authority==='unapproved'));assert.equal(result.removed_cells,0);assert.equal(result.reassigned_cells,0);
});
test('same-owner additions are aggregated and shared cells counted once, independent of candidate order',()=>{
 const sources=[batchSource('a'),batchSource('b')],candidates=[batchCandidate('a',1,[[1,4]]),batchCandidate('b',1,[[2,5]])];
 const result=batch(sources,candidates);assert.deepEqual(result,batch([...sources].reverse(),[...candidates].reverse(),[],['a','b']));
 assert.deepEqual(result.rows,[{y:1,runs:[[1,5,1]]}]);assert.equal(result.assigned_cells,4);assert.equal(result.candidate_cell_contributions,6);assert.equal(result.shared_same_owner_cells,2);
});
test('competing batch owners are both refused, never assigned by first-target ordering',()=>{
 const sources=[batchSource('a'),batchSource('b',2)],candidates=[batchCandidate('a',1,[[1,4]]),batchCandidate('b',2,[[3,5]])];
 const result=batch(sources,candidates);assert.deepEqual(result,batch([...sources].reverse(),[...candidates].reverse(),[],['a','b']));
 assert.equal(result.assigned_cells,0);assert.equal(result.native_conflicts,2);assert(result.decisions.every(row=>row.native_conflicts.includes('competing-batch-owner')));
});
test('complete old owners survive virtual interval split/merge; only previously empty cells are emitted',()=>{
 const result=batch([batchSource('a')],[batchCandidate('a',1,[[0,5]])],[[2,4,1]]);
 assert.deepEqual(result.rows,[{y:1,runs:[[0,2,1],[4,5,1]]}]);assert.deepEqual(result.virtual_owner_rows,[{y:1,complete_owner_intervals:[[0,5,1]]}]);assert.equal(result.assigned_cells,3);
 const foreign=batch([batchSource('a')],[batchCandidate('a',1,[[0,5]])],[[2,4,2]]);assert.equal(foreign.assigned_cells,0);assert.equal(foreign.native_conflicts,1);
});
test('batch rejects omitted, duplicate, foreign or incompletely measured candidates and owner windows',()=>{
 const sources=[batchSource('a')],candidate=batchCandidate('a',1,[[1,2]]);
 assert.throws(()=>batch(sources,[]),/no actual native/);
 assert.throws(()=>batch(sources,[candidate,candidate]),/Foreign\/duplicate/);
 assert.throws(()=>batch(sources,[{...candidate,component_id:'foreign'}]),/Foreign\/duplicate/);
 assert.throws(()=>batch(sources,[{...candidate,rows:[]}]),/target\/window join/);
 assert.throws(()=>combineNativeBatch({scopeIds:['a'],sourceRows:sources,candidates:[candidate],ownerRows:[],size:8}),/Missing full owner/);
 assert.throws(()=>batch([sources[0],sources[0]],[candidate],[],['a']),/source decision/);
 assert.throws(()=>batch([{...sources[0],source_compatible:undefined}],[candidate]),/incomplete source/);
 assert.throws(()=>batch(sources,[{...candidate,pixelIndex:2}]),/target\/window join/);
});
test('all provisional candidates preserved exactly once; land is not repair permission, water rejected',()=>{
 const one=child(all.slice(0,2)),two=child(all.slice(2)); const result=joinInventoryFacts([one,two],parent);
 assert.equal(result.components,4);assert.deepEqual(result.counts,{eligible:0,assigned:0,'zero-cell':0,'already-resolved':0,rejected:1,'awaiting-evidence':3});
 all.forEach((r,i)=>assert.equal(restoreInventoryRow(child(all).rows[i],all,source,rawRows(all)),r));
 assert.equal(candidateDisposition({...all[0],approved:true}).disposition,'awaiting-evidence');
});
test('whole original roster/alias and parent joins reject omission, duplicate, order and coherent field drift',()=>{
 assert.throws(()=>joinInventoryFacts([child(all.slice(0,2))],parent),/Incomplete/);
 assert.throws(()=>joinInventoryFacts([child(all),child(all)],parent),/Duplicate/);
 assert.throws(()=>joinInventoryFacts([child(all.slice(2)),child(all.slice(0,2))],parent),/reordered/);
 assert.throws(()=>inventoryRows([all[0],all[0]],{source,parent,expectedIds:['one','two'],expectedRosterSha256:roster(all),originalRecordBytes:rawRows([all[0],all[0]])}),/duplicate/);
 assert.throws(()=>inventoryRows(all.slice(1),{source,parent,expectedIds:all.map(r=>r.component_id),expectedRosterSha256:roster(all),originalRecordBytes:rawRows(all.slice(1))}),/Missing/);
 const alias=child(all).rows[0],changed=structuredClone(all);changed[0].complete_support.whole_original_geometry=false;
 assert.throws(()=>restoreInventoryRow(alias,changed,source,rawRows(all)),/inverse/);
 assert.throws(()=>restoreInventoryRow(alias,all,{...source,commit:'d'.repeat(40)},rawRows(all)),/source/);
 const wrong=child(all);wrong.facts.counts.assigned=1;assert.throws(()=>joinInventoryFacts([wrong],parent),/totals/);
});


test('output collision, dangling link and foreign parent rejected before acquisition; sentinels preserved',()=>{
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'additive-admission-fixture-'));
 try {
  fs.mkdirSync(path.join(directory,'.cache','native-grid-candidates'),{recursive:true});
  const target=path.join(directory,'.cache','native-grid-candidates','existing');fs.writeFileSync(target,'sentinel');
  assert.throws(()=>admitInventoryDestination(directory,'.cache/native-grid-candidates/existing'),/collision/);
  assert.equal(fs.readFileSync(target,'utf8'),'sentinel');
  fs.symlinkSync('missing',path.join(directory,'.cache','native-grid-candidates','dangling'));
  assert.throws(()=>admitInventoryDestination(directory,'.cache/native-grid-candidates/dangling'),/collision/);
  assert.equal(fs.readlinkSync(path.join(directory,'.cache','native-grid-candidates','dangling')),'missing');
  fs.rmSync(path.join(directory,'.cache','native-grid-candidates'),{recursive:true});
  fs.symlinkSync(os.tmpdir(),path.join(directory,'.cache','native-grid-candidates'));
  assert.throws(()=>admitInventoryDestination(directory,'.cache/native-grid-candidates/new'),/symlink/);
 } finally {fs.rmSync(directory,{recursive:true,force:true});}
});


test('selected baseline accepted repairs remain resolved/idempotent; stale target and unverified resolution maps reject',()=>{
 const geometry={type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,0]]]};
 const correction={component_id:'one',subject_id:'target',component_geometry_sha256:all[0].candidate_geometry_sha256,
  geometry_sha256_after:hash(geometry),pointsets:{new:geometry},historical_transfer:'none'};
 const manifest={version:2,method:'native-linear-evenodd-first-owner-v1',accounting:{owners:49625},footprints_sha256:'a'.repeat(64),
  provenance:{source_migration:{history_transfer:'none',after_footprints_sha256:'a'.repeat(64),changed_ids:['target']}}};
 const args={features:[{id:'target',geometry}],corrections:[correction],selectedManifest:manifest,
  selectionReceipt:{method:manifest.method,owners:49625,unchecked_cells:0,products:[{path:'manifest.json',sha256:'b'.repeat(64)}]},
  selectedManifestSha256:'b'.repeat(64),bankDecodedSha256:'c'.repeat(64),expectedBankDecodedSha256:'c'.repeat(64)};
 const resolutions=selectedBankResolutions(args);
 for(let i=0;i<2;i++)assert.equal(candidateDisposition(all[0],resolutions).disposition,'already-resolved');
 assert.throws(()=>candidateDisposition(all[0],new Map()),/Unverified/);
 assert.throws(()=>selectedBankResolutions({...args,bankDecodedSha256:'d'.repeat(64)}),/Stale/);
 const changed=structuredClone(args);changed.features[0].geometry=structuredClone(changed.features[0].geometry);changed.features[0].geometry.coordinates[0][1][0]=2;
 assert.throws(()=>selectedBankResolutions(changed),/full target/);
 assert.throws(()=>candidateDisposition({...all[0],candidate_geometry_sha256:'e'.repeat(64)},resolutions),/pointset/);
});


test('bounded groups join every original identity and preserve two-level complete inverse',()=>{
 const group1=inventoryGroup([child(all.slice(0,2))],parent),group2=inventoryGroup([child(all.slice(2))],parent);
 const final=inventoryGroup([group1,group2],parent,{complete:true});
 assert.equal(final.facts.components,all.length);
 for(const row of final.rows){const grouped=restoreGroupedInventoryRow(row,[group1,group2]);
  const groupIndex=row.original_ledger.stage;
  const original=restoreGroupedInventoryRow(grouped,[child(groupIndex===0?all.slice(0,2):all.slice(2))]);
  assert.equal(original.component_id,row.component_id);
 }
 assert.throws(()=>inventoryGroup([group1],parent,{complete:true}),/Incomplete/);
 assert.throws(()=>inventoryGroup([group1,group1],parent,{complete:true}),/Duplicate/);
 assert.throws(()=>inventoryGroup([group2,group1],parent,{complete:true}),/reordered/);
 const wrong=structuredClone(group1);wrong.rows[0].source_relative_category='unknown';
 assert.throws(()=>inventoryGroup([wrong,group2],parent,{complete:true}),/counts/);
 assert.throws(()=>restoreGroupedInventoryRow({...final.rows[0],disposition:'assigned'},[group1,group2]),/inverse/);
});


test('actual whole source-supported shared-edge pilot derives source premises without producer approval flags',()=>{
 const root='coordination/engineering/additive-native-gap-repair-20261008/source-supported-pilot/';
 const roster=JSON.parse(fs.readFileSync(root+'original-input-roster.json'));
 const read=name=>{const raw=fs.readFileSync(root+name),pin=roster.inputs.find(pin=>pin.retained_copy.endsWith('/'+name));
  assert.ok(pin);assert.equal(raw.length,pin.bytes);assert.equal(createHash('sha256').update(raw).digest('hex'),pin.sha256);
  const decoded=name.endsWith('.gz')?gunzipSync(raw):raw;assert.equal(decoded.length,pin.decoded_bytes);
  assert.equal(createHash('sha256').update(decoded).digest('hex'),pin.decoded_sha256);return decoded;};
 const pilot=JSON.parse(read('add031-construction-failure.json')),scope=JSON.parse(read('source-fit-seven-cases.json'));
 const sourceCase=scope.results.find(row=>row.component_id===pilot.component_id);
 const record=read('original-scientific-products/components-047.jsonl.gz').toString().trimEnd().split('\n').map(JSON.parse).find(row=>row.component_id===pilot.component_id);
 const input={record,candidate:pilot.candidate,sourceCase,sourceScope:scope,target:pilot.before};
 const facts=retainedLandSourcePremises(input);assert.equal(facts.source_compatible,true);assert.equal(facts.authority,'unapproved');assert.equal(facts.status,record.physical_status);
 const originalGeometry=JSON.stringify(pilot.before.geometry);assert.equal(wholePrimitivePointsetEqual(record.complete_support.mapped_land_support.geometry,pilot.candidate),true);
 for(const alter of [x=>x.record.status='mapped-inland-water-support',x=>x.record.complete_support.mapped_inland_water_support.geometry={type:'Polygon',coordinates:pilot.candidate.coordinates},
  x=>x.sourceCase.candidate_valid=false,x=>x.sourceScope.active_feature_count--,x=>x.sourceCase.native_covering_named_envelopes.push(x.sourceCase.native_covering_named_envelopes[0]),
  x=>x.sourceCase.new_neighbor_intersections=[{id:'foreign',geometry:pilot.candidate}],x=>x.target.properties.parent_id='foreign',
  x=>x.sourceCase.retired_administrative_reference_context.pop(),x=>x.sourceCase.gain_candidate_symmetric_difference_area_deg2=1e-16]){
  const changed=structuredClone(input);alter(changed);assert.equal(retainedLandSourcePremises(changed).source_compatible,false);
 }
 const foreign=structuredClone(input);foreign.record.component_id='foreign';assert.throws(()=>retainedLandSourcePremises(foreign),/component join/);
 assert.equal(JSON.stringify(pilot.before.geometry),originalGeometry);
 // Neither these premises nor the independent source PASS labels release cells:
 assert.equal(candidateDisposition(record).disposition,'awaiting-evidence');
});

// These are complete immutable source observations, not synthetic source
// approvals. The two original parent failures must remain exceptions.
test('actual thirteen county sources derive eleven support decisions and two parent exceptions; contextual disjoint queries stay valid',()=>{
 const base='research/geography/alaska-thirteen-source-fitness-20261008/sources/';
 const measurement=JSON.parse(fs.readFileSync('research/geography/alaska-thirteen-geometry-measurement-20261008/vintages/run-fourteen/measurement.json'));
 const candidates=JSON.parse(fs.readFileSync(base+'candidate-components.geojson')).features;
 const records=fs.readFileSync(base+'physical-query-rows.jsonl','utf8').trimEnd().split('\n').map(JSON.parse);
 const targets=JSON.parse(fs.readFileSync(base+'native-atlas-target-features.geojson')).features;
 const inputs=measurement.cases.map(sourceCase=>({sourceCase,sourceScope:measurement,
  record:records.find(row=>row.component_id===sourceCase.component_id),
  candidate:candidates.find(feature=>feature.id===sourceCase.component_id).geometry,
  target:targets.find(feature=>feature.id===sourceCase.county_target.atlas_target_id)}));
 const decisions=inputs.map(retainedCountySourcePremises);
 assert.equal(decisions.length,13);assert.equal(decisions.filter(row=>row.source_compatible).length,11);
 assert.equal(decisions.filter(row=>!row.source_compatible).length,2);
 for(const row of decisions.filter(row=>!row.source_compatible))assert.ok(row.failed_premises.includes('original-parent-coverage'));
 assert.equal(inputs[0].record.query_relations[0].disjoint,true);assert.equal(decisions[0].source_compatible,true);
 const altered=(mutate)=>{const value=structuredClone(inputs[0]);mutate(value);return retainedCountySourcePremises(value);};
 for(const mutation of [v=>v.record.complete_support.mapped_inland_water_support.kind='whole-operation-pointset',
  v=>v.sourceCase.county_target.represented_year_claim='2026',v=>v.sourceCase.native_land_relations[0].record_sha256='0'.repeat(64),
  v=>v.sourceCase.linked_gshhg_native_ids=[2],v=>v.sourceCase.measured_actual_atlas_intersecting_neighbor_ids.push('foreign'),
  v=>v.sourceCase.candidate_to_target_intersections_and_uncovered.candidate_vs_full_county.candidate_uncovered_area_projected_m2_exact=1])
   assert.equal(altered(mutation).source_compatible,false);
 assert.throws(()=>altered(v=>v.sourceCase.native_land_relations.pop()),/Incomplete original county queries/);
});

test('continuous different-owner overlap is refused even when no native cell is sampled; same-owner primitive sets may overlap',()=>{
 const sources=[batchSource('a',1),batchSource('b',2)],candidates=[batchCandidate('a',1,[]),batchCandidate('b',2,[])];
 const result=combineNativeBatch({scopeIds:['a','b'],sourceRows:sources,candidates,ownerRows:[{y:1,complete_owner_intervals:[]}],continuousConflicts:[['a','b']],size:32});
 assert.equal(result.native_conflicts,2);assert.equal(result.assigned_cells,0);assert.equal(result.zero_cell_components,0);
 assert.throws(()=>combineNativeBatch({scopeIds:['a','b'],sourceRows:sources,candidates,ownerRows:[{y:1,complete_owner_intervals:[]}],continuousConflicts:[['a','foreign']],size:32}),/Foreign continuous/);
 const same=combineNativeBatch({scopeIds:['a','b'],sourceRows:[batchSource('a'),batchSource('b')],candidates:[batchCandidate('a',1,[]),batchCandidate('b',1,[])],ownerRows:[{y:1,complete_owner_intervals:[]}],continuousConflicts:[['a','b']],size:32});
 assert.equal(same.zero_cell_components,2);assert.equal(same.native_conflicts,0);
});

// Linux compatibility is an exact runtime-byte transition, not a method waiver.
import {compatibleCurrentRebindCode,CURRENT_REBIND_CODE,valueSha} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const linuxHistory=JSON.parse(fs.readFileSync('coordination/engineering/melanesia363-additive-delivery-20261010/linux-runner-portability-20261010/historical-code-vectors.json'));
const linuxRuntimePaths=['issue-current-rebind-execution.py','supervise-current-rebind.py'].map(name=>'coordination/engineering/additive-native-composition-20261009/'+name);
const actualLinuxRuntime=linuxRuntimePaths.map(path=>{const body=fs.readFileSync(path);return {path,bytes:body.length,sha256:createHash('sha256').update(body).digest('hex')};});
test('Linux runtime compatibility keeps complete historical vectors and exact byte pairs',()=>{
 assert.equal(linuxHistory.length,6);
 for(const row of linuxHistory){
  const historical=row.code;assert.equal(valueSha(historical),row.vector_sha256);assert.deepEqual(historical.map(p=>p.path),CURRENT_REBIND_CODE);
  const current=historical.map(p=>actualLinuxRuntime.find(r=>r.path===p.path)??{...p});
  assert.deepEqual(compatibleCurrentRebindCode(row.commit,current,historical),historical);
  for(const path of linuxRuntimePaths){
   for(const key of ['bytes','sha256']){const wrong=structuredClone(current),pin=wrong.find(p=>p.path===path);pin[key]=key==='bytes'?pin.bytes+1:'f'.repeat(64);assert.throws(()=>compatibleCurrentRebindCode(row.commit,wrong,historical),/runtime body differs/);}
  }
  const numerical=structuredClone(current);numerical.find(p=>p.path==='src/native-grid.js').sha256='f'.repeat(64);assert.throws(()=>compatibleCurrentRebindCode(row.commit,numerical,historical),/runtime body differs/);
  assert.throws(()=>compatibleCurrentRebindCode('a'.repeat(40),current,historical),/Unknown historical/);
  assert.deepEqual(compatibleCurrentRebindCode('a'.repeat(40),historical,historical),historical);
  const missing=current.slice(1);assert.throws(()=>compatibleCurrentRebindCode(row.commit,missing,historical),/Incomplete/);
  const forged=structuredClone(historical);forged[0].bytes++;assert.throws(()=>compatibleCurrentRebindCode(row.commit,current,forged),/Unknown historical/);
 }
});
test('Linux runtime pairs preserve only the existing visibility and schema transitions',()=>{
 const transitions=[
  {path:'scripts/check-effective-geographic-regression.mjs',old:'992257b3a50f790c5f859104c67a3e6f4cf75f8c341440fff78b0dd32b95fab9',bytes:75074,sha256:'801ad9f05a8d7f34ae591ee78a09b71c87090acd4d20c92c9831152528a9c039'},
  {path:'src/effective-footprint.js',old:'30c524aba3e556d4d92508306a6b76b760a51cf08715457ece72646ee9b5921c',bytes:44682,sha256:'0f971449c093ad728495dc05da9a047872c4b57c55bc75fd79012fbcb3db7e65'},
  {commit:'16c35b9188d130b060fc2dcf4e917983d42d9db1',path:'src/effective-footprint.js',old:'0f971449c093ad728495dc05da9a047872c4b57c55bc75fd79012fbcb3db7e65',bytes:44784,sha256:'29a2d9867aa8ffae8645559b34e1638a007cc1504f99ef766ef9c44176491e91'},
  {commit:'bb73f014366ed7e7b10a54a4fb3b2113e8743d66',path:'src/effective-footprint.js',old:'29a2d9867aa8ffae8645559b34e1638a007cc1504f99ef766ef9c44176491e91',bytes:45330,sha256:'28edb52a2befd80b73e0ce62fa3f7de51cada4f9894aab32e5ff2761f1fe0745'}
 ];
 for(const transition of transitions){
  let exercised=0;
  for(const row of linuxHistory){
   if(transition.commit&&row.commit!==transition.commit||row.code.find(p=>p.path===transition.path)?.sha256!==transition.old)continue;
   const current=row.code.map(p=>actualLinuxRuntime.find(r=>r.path===p.path)??{...p});Object.assign(current.find(p=>p.path===transition.path),{bytes:transition.bytes,sha256:transition.sha256});
   assert.deepEqual(compatibleCurrentRebindCode(row.commit,current,row.code),row.code);exercised++;
   current.find(p=>p.path===transition.path).bytes++;assert.throws(()=>compatibleCurrentRebindCode(row.commit,current,row.code),/runtime body differs/);
  }
  assert(exercised>0,'Every named preexisting transition must be exercised');
 }
});

// This is a tiny serialization-boundary fixture, not a source qualification.
function candidateAliasFixture(){
 const geometry={type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,0]]]},feature={type:'Feature',id:'component',properties:{area:1e-7},geometry};
 const raw=Buffer.from(JSON.stringify(feature).replace('1e-7','1e-07')+'\n'),expected=createHash('sha256').update(raw).digest('hex');
 const binding={component_id:'component',feature_sha256:expected,feature_bytes_base64:raw.toString('base64'),derived_js_canonical_sha256:hash(feature)};
 return {geometry,feature,expected,scope:{original_candidate_canonical_bindings:[binding]}};
}
test('original candidate alias preserves whole historical bytes and exact complete parsed values',()=>{
 const f=candidateAliasFixture(),check=(scope=f.scope,candidate=f.feature,expected=f.expected)=>originalAdministrativeCandidateHash({sourceScope:scope,componentId:'component',candidate,expected});
 assert.notEqual(f.expected,hash(f.feature));assert.equal(check(),true);
 assert.equal(check({},f.feature,hash(f.feature)),true);
 for(const change of [x=>x.original_candidate_canonical_bindings[0].component_id='other',x=>x.original_candidate_canonical_bindings.push({...x.original_candidate_canonical_bindings[0]}),x=>x.original_candidate_canonical_bindings[0].feature_sha256='a'.repeat(64),x=>x.original_candidate_canonical_bindings[0].derived_js_canonical_sha256='b'.repeat(64),x=>x.original_candidate_canonical_bindings[0].feature_bytes_base64=Buffer.from('{}').toString('base64')]){
  const scope=structuredClone(f.scope);change(scope);assert.equal(check(scope),false);
 }
 const numeric=structuredClone(f.feature);numeric.properties.area=2e-7;assert.equal(check(f.scope,numeric),false);
 const extra=structuredClone(f.feature);extra.properties.extra=true;assert.equal(check(f.scope,extra),false);
 // Even a matching derived digest cannot authorize a changed parsed object.
 const rebound=structuredClone(f.scope);rebound.original_candidate_canonical_bindings[0].derived_js_canonical_sha256=hash(extra);assert.equal(check(rebound,extra),false);
});
test('both full and fragment source predicates consume the original candidate byte binding',()=>{
 const f=candidateAliasFixture(),empty={kind:'empty',area_m2:0,planar_area:0,geometry:{type:'Polygon',coordinates:[]}};
 const record={component_id:'component',candidate_feature_sha256:f.expected,candidate_geometry_sha256:hash(f.geometry),status:'mapped-land-support',complete_support:{mapped_land_support:{kind:'whole-operation-pointset',geometry:f.geometry},hierarchy_disagreements:Object.fromEntries(['L2-outside-L1','L3-outside-L2','L4-outside-L3'].map(k=>[k,empty])),...Object.fromEntries(['mapped_inland_water_support','outside_mapped_L1_context','contradictory_land_water_support','missing_reconstruction','extra_reconstruction'].map(k=>[k,empty]))}};
 const sourceCase={component_id:'component',original_candidate_feature:f.feature,retained_payload:{}},target={id:'target',properties:{},geometry:f.geometry};
 for(const fn of [retainedAdministrativeSourcePremises,retainedAdministrativeFragmentPremises]){
  const args={record,candidate:f.geometry,fragment:f.geometry,sourceCase,sourceScope:f.scope,target};
  assert.equal(fn(args).failed_premises.includes('original-full-candidate-binding'),false);
  assert.equal(fn({...args,sourceScope:{}}).failed_premises.includes('original-full-candidate-binding'),true);
 }
});

test('registered administrative handoff binds exact complete merged source roster without a cohort code exception',()=>{
 const source={path:'research/geography/fixture/handoff.json',mode:'100644',blob:'b'.repeat(40),bytes:100,sha256:'c'.repeat(64)},commit='a'.repeat(40);
 const entry={id:'fixture',format:'source-native-handoff-v1',accepted_source_commit:commit,source,original_batch_id:'batch',original_component_count:1,cohort_ids:['component'],target_ids:['target']};
 const registry={version:1,kind:'accepted-administrative-handoffs-v1',entries:[entry]},rule={cases_path:source.path,outcomes_path:source.path,inputs:[{commit,...source}],cohort_ids:['component'],geometry_scope:'full-component'};
 assert.equal(registeredAdministrativeHandoff(registry,rule),entry);
 const scope={candidate_source_native_bindings:[{component_id:'component',retained_payload:{target_stable_location_id:'target'},retained_source_operation_row:{}}],scopeIds:['component'],original_batch_id:'batch',original_batch_component_count:1,unknowns:['fixture only']};
 const views=registeredAdministrativeViews(scope,entry);assert.equal(views.cohort,scope.candidate_source_native_bindings);assert.equal(views.payloads[0],scope.candidate_source_native_bindings[0].retained_payload);
 for(const edit of [r=>r.entries.push(structuredClone(r.entries[0])),r=>r.entries[0].source.blob='d'.repeat(40),r=>r.entries[0].accepted_source_commit='e'.repeat(40),r=>r.entries[0].cohort_ids=['other'],r=>r.entries[0].target_ids=['target','target'],r=>r.entries[0].original_component_count=2]){
  const other=structuredClone(registry);edit(other);assert.throws(()=>registeredAdministrativeHandoff(other,rule),/Unknown\/ambiguous|Incomplete/);
 }
 assert.throws(()=>registeredAdministrativeHandoff(registry,{...rule,geometry_scope:'supported-fragment'}),/Incomplete/);
 for(const edit of [s=>s.scopeIds=[],s=>s.original_batch_id='other',s=>s.original_batch_component_count=2,s=>s.candidate_source_native_bindings[0].retained_payload.target_stable_location_id='other']){
  const other=structuredClone(scope);edit(other);assert.throws(()=>registeredAdministrativeViews(other,entry),/Registered handoff changed/);
 }
});

// Tiny actual Git provenance fixture; no geography operator is invoked.
test('registered handoff provenance requires exact HEAD body and merged source ancestry',()=>{
 const repo=fs.mkdtempSync(path.join(os.tmpdir(),'administrative-registry-'));
 const git=(...args)=>execFileSync('git',['-C',repo,'-c','core.hooksPath=/dev/null','-c','user.name=Fixture','-c','user.email=fixture@example.invalid',...args],{encoding:'utf8',stdio:['ignore','pipe','pipe']}).trim();
 try{
  git('init','-q');fs.writeFileSync(path.join(repo,'initial'),'initial');git('add','.');git('commit','-qm','initial');const initial=git('rev-parse','HEAD');
  const sourceName='research/geography/fixture/handoff.json';fs.mkdirSync(path.dirname(path.join(repo,sourceName)),{recursive:true});fs.writeFileSync(path.join(repo,sourceName),'{}\n');git('add','.');git('commit','-qm','source');const sourceCommit=git('rev-parse','HEAD');
  const source={path:sourceName,mode:'100644',blob:git('rev-parse','HEAD:'+sourceName),bytes:3,sha256:createHash('sha256').update('{}\n').digest('hex')};
  const registryPath='coordination/engineering/melanesia363-additive-delivery-20261010/accepted-administrative-handoffs.json';
  const entry={id:'fixture',format:'source-native-handoff-v1',accepted_source_commit:sourceCommit,source,original_batch_id:'batch',original_component_count:1,cohort_ids:['component'],target_ids:['target']};
  const body=Buffer.from(JSON.stringify({version:1,kind:'accepted-administrative-handoffs-v1',entries:[entry]})+'\n');
  fs.mkdirSync(path.dirname(path.join(repo,registryPath)),{recursive:true});fs.writeFileSync(path.join(repo,registryPath),body);git('add','.');git('commit','-qm','registration');git('update-ref','refs/remotes/origin/main',sourceCommit);
  const pin={path:registryPath,mode:'100644',blob:git('rev-parse','HEAD:'+registryPath),bytes:body.length,sha256:createHash('sha256').update(body).digest('hex')};
  const rule={registry_path:registryPath,cases_path:sourceName,outcomes_path:sourceName,cohort_ids:['component'],inputs:[{commit:sourceCommit,...source}]};
  assert.equal(readRegisteredAdministrativeHandoff(repo,rule,{pin,body}).registrationMain,sourceCommit);
  assert.throws(()=>readRegisteredAdministrativeHandoff(repo,rule,{pin,body:Buffer.from('{}')}),/executing-HEAD/);
  assert.throws(()=>readRegisteredAdministrativeHandoff(repo,rule,{pin:{...pin,blob:'f'.repeat(40)},body}),/executing-HEAD/);
  git('update-ref','refs/remotes/origin/main',initial);assert.throws(()=>readRegisteredAdministrativeHandoff(repo,rule,{pin,body}));
 }finally{fs.rmSync(repo,{recursive:true,force:true});}
});

test('registered physical inverse uses independent whole restored products and complete row counts',()=>{
 const product={path:'components-030.jsonl.gz',bytes:1196109,sha256:'22363c332379d6dc16354b6079bf59766abf4cb9e7b20b111c7528e7c757fde8',hash_kind:'file-bytes',uncompressed_bytes:8376604,uncompressed_sha256:'05a242b39ebd98bd0f4a7b49515f50376e48c012e9e4561d22b455f5c04d6ae8'};
 const restoration={path:product.path,whole_original_bytes:product.bytes,whole_original_sha256:product.sha256,decoded_bytes:product.uncompressed_bytes,decoded_sha256:product.uncompressed_sha256,rows:1326};
 const scope={physical_restoration:{restorations:[restoration]}};assert.equal(registeredOriginalPhysicalProduct(scope,product,1326),true);
 for(const key of ['path','bytes','sha256','uncompressed_bytes','uncompressed_sha256','hash_kind'])assert.equal(registeredOriginalPhysicalProduct(scope,{...product,[key]:typeof product[key]==='number'?product[key]+1:'changed'},1326),false);
 for(const rows of [1325,1327,0])assert.equal(registeredOriginalPhysicalProduct(scope,product,rows),false);
 assert.equal(registeredOriginalPhysicalProduct({physical_restoration:{restorations:[]}},product,1326),false);
 assert.equal(registeredOriginalPhysicalProduct({physical_restoration:{restorations:[restoration,restoration]}},product,1326),false);
 assert.equal(registeredOriginalPhysicalProduct(scope,{...product,unexpected:true},1326),false);
});
