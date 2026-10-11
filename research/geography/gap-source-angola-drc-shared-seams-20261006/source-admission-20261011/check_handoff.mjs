// Actual registered v2 view and existing scientific-premise entry points only.
// These controls do not issue an accepted SOURCE result or rerun geographic GIS.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {retainedAdministrativeSourcePremises, registeredAdministrativeViews} from '../../../../scripts/additive-gap-repair.mjs';

const scope=JSON.parse(fs.readFileSync(new URL('../vintages/congo-source-handoff-002/source-handoff.json',import.meta.url)));
const clone=()=>structuredClone(scope);
const targetFor=s=>s.current_neighbor_binding.rows[0].candidate_neighbors.find(r=>r.feature.id==='gb:AGO:ADM2:16411231B62076307190429').feature;
function premise(s,index=0,target=targetFor(s)){
  const sourceCase=s.candidate_source_native_bindings[index];
  const record=s.original_physical_comparison_bindings[index].physical_comparison.row;
  return retainedAdministrativeSourcePremises({record,candidate:sourceCase.original_candidate_feature.geometry,sourceCase,sourceScope:s,target});
}
const entry={format:'source-native-execution-cohort-v2',id:scope.execution_cohort_id,cohort_ids:scope.scopeIds,target_ids:[targetFor(scope).id]};
let count=0;
function test(name,fn){fn();count++;console.log('ok '+count+' - '+name);}
for(let i=0;i<2;i++)test('actual complete case '+i+' retains source-relative support and unapproved truth',()=>{
  const result=premise(scope,i);assert.equal(result.source_compatible,true);assert.deepEqual(result.failed_premises,[]);
  assert.equal(result.authority,'unapproved');assert.equal(result.status,'unknown-source-fitness-and-observation-date');
});
test('actual v2 has two scientific cases and unchanged130 passive original accounting',()=>{
  assert.equal(registeredAdministrativeViews(scope,entry).cohort.length,2);
  assert.equal(scope.original_gap_membership.members.length,2);
  assert.equal(scope.original_membership_evidence.batch.component_count,130);
});
test('changed complete candidate is refused',()=>{const s=clone();s.candidate_source_native_bindings[0].original_candidate_feature.geometry.coordinates[0][1][0]+=0.01;assert.equal(premise(s).source_compatible,false);});
test('missing mapped-land pointset is refused',()=>{const s=clone();s.original_physical_comparison_bindings[0].physical_comparison.row.complete_support.mapped_land_support.geometry={type:'Polygon',coordinates:[]};assert.equal(premise(s).source_compatible,false);});
test('positive mapped-water support is refused',()=>{const s=clone();const r=s.original_physical_comparison_bindings[0].physical_comparison.row;r.complete_support.mapped_inland_water_support=structuredClone(r.complete_support.mapped_land_support);assert.equal(premise(s).source_compatible,false);});
test('wrong original native record hash is refused',()=>{const s=clone();s.original_physical_comparison_bindings[0].original_queried_source_metadata[0].original_source_record_metadata.record_sha256='0'.repeat(64);assert.equal(premise(s).source_compatible,false);});
test('missing full query is refused',()=>{const s=clone();s.original_physical_comparison_bindings[0].physical_comparison.row.query_relations=[];assert.equal(premise(s).source_compatible,false);});
test('coherently changed target parent still fails original source relation',()=>{const s=clone();const t=structuredClone(targetFor(s));t.properties.parent_id='framework:province:foreign';s.candidate_source_native_bindings[0].retained_payload.target_current_feature.parent_id=t.properties.parent_id;assert.equal(premise(s,0,t).source_compatible,false);});
test('wrong unique source subject is refused',()=>{const s=clone();s.candidate_source_native_bindings[0].retained_source_operation_row.source_comparison_record.uniquely_covering_compatible_recorded_subject.id='gb:AGO:ADM2:foreign';assert.equal(premise(s).source_compatible,false);});
test('missing admitted scientific case is refused',()=>{const s=clone();s.candidate_source_native_bindings.pop();assert.throws(()=>registeredAdministrativeViews(s,entry));});
test('duplicate admitted scientific case is refused',()=>{const s=clone();s.candidate_source_native_bindings[1]=structuredClone(s.candidate_source_native_bindings[0]);assert.throws(()=>registeredAdministrativeViews(s,entry));});
test('missing passive member is refused',()=>{const s=clone();s.original_gap_membership.members.pop();assert.throws(()=>registeredAdministrativeViews(s,entry));});
test('extra fabricated passive member is refused',()=>{const s=clone();s.original_gap_membership.members.push({...s.original_gap_membership.members[0],component_id:'physical-component:foreign'});assert.throws(()=>registeredAdministrativeViews(s,entry));});
console.log('1..'+count);
