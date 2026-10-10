import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {RETAINED_ADMINISTRATIVE_318_HANDOFF as pins,SEA318_BATCH,retainedAdministrative318Views} from './retained-sea318-view.mjs';

// Actual immutable source records exercise the projection boundary. The zero
// target geometry digest is deliberately only a shape-valid placeholder: this
// adapter is not current-target proof, and the real caller must reject it unless
// originalAdministrativeTargetHash independently authenticates an actual target.
function fixture() {
  const operands=pins.map(pin=>({pin:{...pin},body:fs.readFileSync(pin.path)}));
  const [source,state,families]=operands.map(value=>JSON.parse(value.body));
  const selected=source.cases.filter(row=>row.source_product.product_id==='gb:PHL:ADM3');
  const ids=selected.map(row=>row.component_id);
  const scope={original_operational_batch:SEA318_BATCH,original_denominator:318,whole_gap_completion:false,
    whole_original_outcomes:state.rows,whole_original_families:families.families,scopeIds:ids,
    unprocessed_original_outcomes:state.rows.filter(row=>!ids.includes(row.component_id)),
    candidate_source_native_bindings:[],original_physical_comparison_bindings:[]};
  for(const row of selected){
    const id=row.component_id,candidate=row.current_component_candidate.feature,op=row.original_administrative_comparison.record;
    const hit=op.feature_intersections[0],subject=hit.binding.recorded_stable_subjects[0];
    const original=state.rows.find(value=>value.component_id===id);
    scope.candidate_source_native_bindings.push({component_id:id,geometry_scope:'full-component',whole_gap_completion:false,
      original_candidate_feature:candidate,original_source_rule_fit_record:row,
      whole_original_case:{component_id:id,candidate_feature:candidate,whole_candidate_coverage_status:'complete-in-retained-comparison',
        whole_candidate_source_coverage:{remainder:op.component_minus_source_union},original_outcome_record:original},
      retained_source_operation_row:{component_id:id,source_comparison_record:op,
        positive_area_recorded_source_subject_ids:[subject.id],positive_area_source_feature_intersections:[{
          feature_sha256:hit.binding.feature_sha256,geometry_sha256:hit.binding.geometry_sha256,source_id:hit.binding.source_id,
          recorded_stable_subjects:hit.binding.recorded_stable_subjects,intersection_geometry:hit.intersection.geometry}]},
      retained_payload:{component_id:id,candidate_feature:candidate,candidate_feature_sha256:row.current_component_candidate.feature_sha256,
        candidate_geometry_sha256:row.current_component_candidate.geometry_sha256,target_stable_location_id:subject.id,
        target_current_feature:{feature_sha256:subject.original_feature_sha256,geometry_sha256:'0'.repeat(64),parent_id:subject.original_parent_id},
        unsupported_candidate_remainder_included:false,source_supported_intersection_fragments:[{
          source_feature_sha256:hit.binding.feature_sha256,source_geometry_sha256:hit.binding.geometry_sha256,intersection_geometry:hit.intersection.geometry}]}});
    const {complete_current_record_metadata_alias,...packed}=row.original_physical_query_custody.complete_original_packed_comparison_row.record;
    scope.original_physical_comparison_bindings.push({component_id:id,original_component_feature:candidate,
      physical_comparison:{row:{...packed,candidate_feature_sha256:row.current_component_candidate.feature_sha256,
        candidate_geometry_sha256:row.current_component_candidate.geometry_sha256,original_context:{}}}});
  }
  return {scope,operands,geometryScope:'full-component'};
}

test('actual accepted318 whole records project exact9 and retain full30 cohort/318 denominator',()=>{
  const data=fixture(),before=JSON.stringify(data.scope),result=retainedAdministrative318Views(data);
  assert.equal(result.cohort.length,30);assert.equal(result.payloads.length,9);assert.equal(result.original_outcome_count,318);
  assert.equal(data.scope.unprocessed_original_outcomes.length,309);assert.equal(JSON.stringify(data.scope),before);
  assert.deepEqual(result.payloads.map(row=>row.component_id),data.scope.scopeIds);
  assert.equal(result.ncl.length,0);assert.equal(result.remainderRows.length,0);
});
const adverse=[
 ['missing accepted product',data=>data.operands.pop(),/Missing\/duplicate/],
 ['duplicate accepted product',data=>data.operands.push(data.operands[0]),/Missing\/duplicate/],
 ['changed consumed byte',data=>{data.operands[0].body=Buffer.from(data.operands[0].body);data.operands[0].body[5]^=1;},/whole-product custody/],
 ['rebound whole-product SHA',data=>data.operands[0].pin.sha256='0'.repeat(64),/whole-product custody/],
 ['omitted original state',data=>data.scope.whole_original_outcomes.pop(),/original states/],
 ['omitted unaffected state',data=>data.scope.unprocessed_original_outcomes.pop(),/other309/],
 ['duplicate exact PHL identity',data=>data.scope.scopeIds[1]=data.scope.scopeIds[0],/product scope/],
 ['foreign provisional PHL identity',data=>data.scope.scopeIds.push('physical-component:foreign'),/product scope/],
 ['rebound target parent',data=>data.scope.candidate_source_native_bindings[0].retained_payload.target_current_feature.parent_id='foreign',/target\/parent/],
 ['rebound source year',data=>{data.scope.candidate_source_native_bindings[0].retained_source_operation_row=structuredClone(data.scope.candidate_source_native_bindings[0].retained_source_operation_row);data.scope.candidate_source_native_bindings[0].retained_source_operation_row.positive_area_source_feature_intersections[0].recorded_stable_subjects[0].reference_year='2026';},/literal source projection/],
 ['dropped original residual',data=>data.scope.candidate_source_native_bindings[0].whole_original_case.whole_candidate_source_coverage.remainder=null,/literal source projection/],
 ['changed original physical query',data=>{data.scope.original_physical_comparison_bindings[0].physical_comparison.row=structuredClone(data.scope.original_physical_comparison_bindings[0].physical_comparison.row);data.scope.original_physical_comparison_bindings[0].physical_comparison.row.query_relations.pop();},/physical inverse/],
 ['invented whole-gap closure',data=>data.scope.whole_gap_completion=true,/original states/],
 ['foreign partial geometry route',data=>data.geometryScope='supported-fragment',/full-component only/],
];
for(const [name,alter,pattern] of adverse)test('refuses '+name,()=>{const data=fixture();alter(data);assert.throws(()=>retainedAdministrative318Views(data),pattern);});
