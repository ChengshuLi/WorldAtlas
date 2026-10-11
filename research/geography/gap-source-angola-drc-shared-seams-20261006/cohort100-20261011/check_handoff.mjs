// Actual registered v2 view and existing scientific-premise entry points only.
// These controls do not issue an accepted SOURCE result or rerun geographic GIS.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {canonicalValue} from '../../../../src/effective-footprint.js';
import {retainedAdministrativeSourcePremises, registeredAdministrativeViews} from '../../../../scripts/additive-gap-repair.mjs';

const scope=JSON.parse(fs.readFileSync(new URL('../vintages/cohort100-source-handoff-003/source-handoff.json',import.meta.url)));
const clone=()=>structuredClone(scope);
const targetFor=(s,index=0)=>s.current_neighbor_binding.rows.find(r=>r.component_id===s.scopeIds[index]).candidate_neighbors.find(r=>r.feature.id===s.candidate_source_native_bindings[index].retained_payload.target_stable_location_id).feature;
function premise(s,index=0,target=targetFor(s,index)){
  const sourceCase=s.candidate_source_native_bindings[index];
  const record=s.original_physical_comparison_bindings[index].physical_comparison.row;
  return retainedAdministrativeSourcePremises({record,candidate:sourceCase.original_candidate_feature.geometry,sourceCase,sourceScope:s,target});
}
const entry={format:'source-native-execution-cohort-v2',id:scope.execution_cohort_id,cohort_ids:scope.scopeIds,target_ids:scope.scopeIds.map((_,i)=>targetFor(scope,i).id)};
let count=0;
function test(name,fn){fn();count++;console.log('ok '+count+' - '+name);}
for(let i=0;i<scope.scopeIds.length;i++)test('actual complete case '+i+' retains source-relative support and unapproved truth',()=>{
  const result=premise(scope,i);assert.equal(result.source_compatible,true);assert.deepEqual(result.failed_premises,[]);
  assert.equal(result.authority,'unapproved');assert.equal(result.status,'unknown-source-fitness-and-observation-date');
});
test('actual v2 has three scientific cases and unchanged full100 passive accounting',()=>{
  assert.equal(registeredAdministrativeViews(scope,entry).cohort.length,3);
  assert.equal(scope.original_gap_membership.members.length,3);
  assert.equal(scope.original_membership_evidence.wave_components,100);
});
test('changed complete candidate is refused',()=>{const s=clone();s.candidate_source_native_bindings[0].original_candidate_feature.geometry.coordinates[0][1][0]+=0.01;assert.equal(premise(s).source_compatible,false);});
test('missing mapped-land pointset is refused',()=>{const s=clone();s.original_physical_comparison_bindings[0].physical_comparison.row.complete_support.mapped_land_support.geometry={type:'Polygon',coordinates:[]};assert.throws(()=>premise(s),/Missing footprint rings/);});
test('positive mapped-water support is refused',()=>{const s=clone();const r=s.original_physical_comparison_bindings[0].physical_comparison.row;r.complete_support.mapped_inland_water_support=structuredClone(r.complete_support.mapped_land_support);assert.equal(premise(s).source_compatible,false);});
test('wrong original native record hash is refused',()=>{const s=clone();s.original_physical_comparison_bindings[0].original_queried_source_metadata[0].original_source_record_metadata.record_sha256='0'.repeat(64);assert.equal(premise(s).source_compatible,false);});
test('missing full query is refused',()=>{const s=clone();s.original_physical_comparison_bindings[0].physical_comparison.row.query_relations=[];assert.equal(premise(s).source_compatible,false);});
test('coherently changed target parent still fails original source relation',()=>{const s=clone();const t=structuredClone(targetFor(s));t.properties.parent_id='framework:province:foreign';s.candidate_source_native_bindings[0].retained_payload.target_current_feature.parent_id=t.properties.parent_id;assert.equal(premise(s,0,t).source_compatible,false);});
test('wrong unique source subject is refused',()=>{const s=clone();s.candidate_source_native_bindings[0].retained_source_operation_row.source_comparison_record.uniquely_covering_compatible_recorded_subject.id='gb:AGO:ADM2:foreign';assert.equal(premise(s).source_compatible,false);});
test('missing admitted scientific case is refused',()=>{const s=clone();s.candidate_source_native_bindings.pop();assert.throws(()=>registeredAdministrativeViews(s,entry));});
test('duplicate admitted scientific case is refused',()=>{const s=clone();s.candidate_source_native_bindings[1]=structuredClone(s.candidate_source_native_bindings[0]);assert.throws(()=>registeredAdministrativeViews(s,entry));});
test('missing passive member is refused',()=>{const s=clone();s.original_gap_membership.members.pop();assert.throws(()=>registeredAdministrativeViews(s,entry));});
test('extra fabricated passive member is refused',()=>{const s=clone();s.original_gap_membership.members.push({...s.original_gap_membership.members[0],component_id:'physical-component:foreign'});assert.throws(()=>registeredAdministrativeViews(s,entry));});
// Match the earlier full-product boundary of the actual SOURCE stage as well
// as its later pure premise predicate. Preserve its JavaScript hash semantics.
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const products=scope.consumed_source_bindings.map(binding=>{
  const country=binding.source_id.split(':')[1];
  const body=fs.readFileSync(new URL('../sources/administrative/gb-'+country+'-ADM2-ADM2-consumed-simplified.geojson',import.meta.url));
  assert.equal(body.length,binding.whole_bytes);assert.equal(sha(body),binding.whole_sha256);
  const collection=JSON.parse(body);assert.equal(collection.features.length,binding.feature_count);
  return collection.features.map(feature=>({feature_sha256:sha(JSON.stringify(canonicalValue(feature))+'\n'),geometry_sha256:sha(JSON.stringify(canonicalValue(feature.geometry))+'\n')}));
}).flat();
const fullSourceHit=hit=>{
  const matches=products.filter(feature=>feature.feature_sha256===hit.feature_sha256||feature.feature_sha256===hit.source_feature_sha256);
  return matches.length===1&&matches[0].geometry_sha256===(hit.geometry_sha256??hit.source_geometry_sha256);
};
for(const row of scope.candidate_source_native_bindings)test('actual whole SOURCE feature/geometry join '+row.component_id,()=>{
  assert(row.retained_source_operation_row.positive_area_source_feature_intersections.every(fullSourceHit));
});
test('changed source geometry hash is refused before pure premises',()=>{
  const hit=structuredClone(scope.candidate_source_native_bindings[0].retained_source_operation_row.positive_area_source_feature_intersections[0]);hit.geometry_sha256='0'.repeat(64);assert.equal(fullSourceHit(hit),false);
});
test('retained ab011 original serialization remains refused and excluded',()=>{
  const prior=JSON.parse(fs.readFileSync(new URL('../vintages/cohort100-source-handoff-002/source-handoff.json',import.meta.url)));
  const held=prior.candidate_source_native_bindings.find(row=>row.component_id.startsWith('physical-component:ab0110c9'));
  assert(held);assert(!scope.scopeIds.includes(held.component_id));assert.equal(fullSourceHit(held.retained_source_operation_row.positive_area_source_feature_intersections[0]),false);
});
console.log('1..'+count);
