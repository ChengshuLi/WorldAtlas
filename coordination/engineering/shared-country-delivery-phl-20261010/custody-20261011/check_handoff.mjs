// Genuine v2 view/source-predicate functions; no issued SOURCE result or GIS.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {retainedAdministrativeSourcePremises, registeredAdministrativeViews, originalAdministrativeTargetHash} from '../../../../scripts/additive-gap-repair.mjs';
const scope=JSON.parse(fs.readFileSync(new URL('../vintages/phl-source-handoff-003/source-handoff.json',import.meta.url)));
const clone=()=>structuredClone(scope);
const targetFor=(s,i)=>s.current_neighbor_binding.rows.find(r=>r.component_id===s.scopeIds[i]).candidate_neighbors[0].feature;
function premise(s,i=0,target=targetFor(s,i)){
 const sourceCase=s.candidate_source_native_bindings[i],record=s.original_physical_comparison_bindings[i].physical_comparison.row;
 return retainedAdministrativeSourcePremises({record,candidate:sourceCase.original_candidate_feature.geometry,sourceCase,sourceScope:s,target});
}
const entry={format:'source-native-execution-cohort-v2',id:scope.execution_cohort_id,cohort_ids:scope.scopeIds,target_ids:scope.candidate_source_native_bindings.map(c=>c.retained_payload.target_stable_location_id)};
let count=0;
function test(name,fn){fn();count++;console.log('ok '+count+' - '+name);}
for(let i=0;i<9;i++)test('actual complete PHL case '+i+' retains source-relative support and unapproved truth',()=>{
 const r=premise(scope,i);assert.equal(r.source_compatible,true,JSON.stringify(r));assert.deepEqual(r.failed_premises,[]);assert.equal(r.authority,'unapproved');assert.equal(r.status,'unknown-source-fitness-and-observation-date');
});
test('actual v2 has nine executable cases with passive original318 accounting',()=>{assert.equal(registeredAdministrativeViews(scope,entry).cohort.length,9);assert.equal(scope.original_gap_membership.members.length,9);assert.equal(scope.original_membership_evidence.original_batch_size,318);assert.equal(scope.accepted_ledger_bindings.length,2);});
test('exactly two necessary Python target aliases are retained',()=>{assert.deepEqual(scope.original_target_canonical_bindings.map(r=>r.target_id).sort(),['gb:PHL:ADM3:30758251B13625365204801','gb:PHL:ADM3:30758251B36088332034654'].sort());});
for(const binding of scope.original_target_canonical_bindings){
 const i=scope.candidate_source_native_bindings.findIndex(c=>c.retained_payload.target_stable_location_id===binding.target_id),target=targetFor(scope,i);
 test('alias '+binding.target_id+' succeeds only with authentic complete Python preimage',()=>{assert.equal(originalAdministrativeTargetHash({sourceScope:scope,target,kind:'feature',expected:binding.feature_sha256}),true);assert.equal(originalAdministrativeTargetHash({sourceScope:{},target,kind:'feature',expected:binding.feature_sha256}),false);});
 test('tampered alias '+binding.target_id+' is refused',()=>{const s=clone();s.original_target_canonical_bindings.find(r=>r.target_id===binding.target_id).feature_bytes_base64=Buffer.from('{}\n').toString('base64');assert.equal(premise(s,i).source_compatible,false);});
}
test('changed complete candidate is refused',()=>{const s=clone();s.candidate_source_native_bindings[0].original_candidate_feature.geometry.coordinates[0][1][0]+=0.01;assert.equal(premise(s).source_compatible,false);});
test('positive mapped-water support is refused',()=>{const s=clone();const r=s.original_physical_comparison_bindings[0].physical_comparison.row;r.complete_support.mapped_inland_water_support=structuredClone(r.complete_support.mapped_land_support);assert.equal(premise(s).source_compatible,false);});
test('wrong complete native metadata is refused',()=>{const s=clone();s.original_physical_comparison_bindings[0].original_queried_source_metadata[0].original_source_record_metadata.record_sha256='0'.repeat(64);assert.equal(premise(s).source_compatible,false);});
test('missing original query is refused',()=>{const s=clone();s.original_physical_comparison_bindings[0].physical_comparison.row.query_relations=[];assert.equal(premise(s).source_compatible,false);});
test('changed target parent fails original source relation',()=>{const s=clone(),t=structuredClone(targetFor(s,0));t.properties.parent_id='framework:province:foreign';s.candidate_source_native_bindings[0].retained_payload.target_current_feature.parent_id=t.properties.parent_id;assert.equal(premise(s,0,t).source_compatible,false);});
test('nonempty original source remainder is refused',()=>{const s=clone();s.candidate_source_native_bindings[0].retained_source_operation_row.source_comparison_record.component_minus_source_union.is_empty=false;assert.equal(premise(s).source_compatible,false);});
test('wrong unique source subject is refused',()=>{const s=clone();s.candidate_source_native_bindings[0].retained_source_operation_row.source_comparison_record.uniquely_covering_compatible_recorded_subject.id='gb:PHL:ADM3:foreign';assert.equal(premise(s).source_compatible,false);});
test('missing executable case is refused',()=>{const s=clone();s.candidate_source_native_bindings.pop();assert.throws(()=>registeredAdministrativeViews(s,entry));});
test('duplicate executable case is refused',()=>{const s=clone();s.candidate_source_native_bindings[1]=structuredClone(s.candidate_source_native_bindings[0]);assert.throws(()=>registeredAdministrativeViews(s,entry));});
test('missing passive member is refused',()=>{const s=clone();s.original_gap_membership.members.pop();assert.throws(()=>registeredAdministrativeViews(s,entry));});
test('extra fabricated passive member is refused',()=>{const s=clone();s.original_gap_membership.members.push({...s.original_gap_membership.members[0],component_id:'physical-component:foreign'});assert.throws(()=>registeredAdministrativeViews(s,entry));});
console.log('1..'+count);
