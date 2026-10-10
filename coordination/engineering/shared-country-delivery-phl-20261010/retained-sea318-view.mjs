import {createHash} from 'node:crypto';
import {isDeepStrictEqual as equal} from 'node:util';
import accepted from './accepted-handoff.json' with {type:'json'};

export const RETAINED_ADMINISTRATIVE_318_HANDOFF=Object.freeze(accepted.map(row=>Object.freeze({...row})));
export const SEA318_BATCH='gap-operational-batch:0393f64c9f8549bcfca1ace9';
const hash=body=>createHash('sha256').update(body).digest('hex');
const demand=(condition,message)=>{if(!condition)throw Error(message);};
const unique=(rows,key,count)=>{
  demand(Array.isArray(rows)&&rows.length===count&&rows.every(row=>typeof row[key]==='string')
    &&new Set(rows.map(row=>row[key])).size===count,'Incomplete/duplicate SEA318 roster');
  return new Map(rows.map(row=>[row[key],row]));
};

// This pure adapter authenticates retained records and checks their literal
// projection into the existing administrative caller. It performs no spatial
// operator, source admission, native selection, output write or closure decision.
// The existing caller still authenticates original physical report products,
// current targets/parents, catalogue, complete source product and all predicates.
export function retainedAdministrative318Views({scope,geometryScope,operands}) {
  demand(geometryScope==='full-component','SEA318 PHL scope is full-component only');
  const decoded=new Map();
  for(const pin of RETAINED_ADMINISTRATIVE_318_HANDOFF){
    const matches=operands.filter(value=>value.pin?.path===pin.path);
    demand(matches.length===1,'Missing/duplicate accepted SEA318 product');
    const value=matches[0];
    demand(['path','mode','blob','bytes','sha256'].every(key=>value.pin[key]===pin[key])
      &&Buffer.isBuffer(value.body)&&value.body.length===pin.bytes&&hash(value.body)===pin.sha256,
      'Changed accepted SEA318 whole-product custody');
    decoded.set(pin.role,JSON.parse(value.body));
  }
  const source=decoded.get('simplified_comparison_path'),state=decoded.get('outcomes_path'),families=decoded.get('families_path');
  const cases=unique(source.cases,'component_id',30),states=unique(state.rows,'component_id',318);
  const familyMap=unique(families.families,'family_id',122);
  demand([source,state,families].every(value=>value.batch_id===SEA318_BATCH)
    &&state.component_count===318&&state.family_count===122&&families.component_count===318&&families.family_count===122
    &&equal(state.family_rows,families.families),'Changed SEA318 original denominators/families');
  const familyMembers=families.families.flatMap(row=>row.component_ids);
  demand(familyMembers.length===318&&new Set(familyMembers).size===318
    &&equal([...familyMembers].sort(),[...states.keys()].sort()),'SEA318 family membership differs');
  for(const row of source.cases)demand(states.has(row.component_id)
    &&familyMap.get(row.family_id)?.component_ids.includes(row.component_id),'Foreign SEA318 source family');
  const selected=source.cases.filter(row=>row.source_product.product_id==='gb:PHL:ADM3');
  const ids=selected.map(row=>row.component_id);
  demand(ids.length===9&&new Set(selected.map(row=>row.family_id)).size===9
    &&scope.original_operational_batch===SEA318_BATCH&&scope.original_denominator===318
    &&scope.whole_gap_completion===false&&equal(scope.whole_original_outcomes,state.rows)
    &&equal(scope.whole_original_families,families.families)
    &&equal(scope.scopeIds,ids)&&equal(scope.candidate_source_native_bindings.map(row=>row.component_id),ids)
    &&equal(scope.original_physical_comparison_bindings.map(row=>row.component_id),ids),
    'Foreign/omitted SEA318 nine-case product scope or original states');
  const other=state.rows.filter(row=>!ids.includes(row.component_id));
  demand(other.length===309&&equal(scope.unprocessed_original_outcomes,other),'Changed other309 SEA318 states');
  const projections=[],operations=[],payloads=[];
  for(const supplied of scope.candidate_source_native_bindings){
    const row=cases.get(supplied.component_id),id=row.component_id;
    const candidate=row.current_component_candidate.feature,op=row.original_administrative_comparison.record;
    // Preserve every original intersection. Only this exact single-relation PHL
    // product cohort is admitted to the adapter; the other21 are not projected.
    const hits=op.feature_intersections;
    demand(equal(row.country_codes,['PHL'])&&hits.length===1&&hits[0].binding.recorded_stable_subjects.length===1
      &&hits[0].source_feature_covers_entire_component===true,'Foreign/nonunique SEA318 PHL relation');
    const hit=hits[0],subject=hit.binding.recorded_stable_subjects[0];
    demand(equal(subject,row.compatible_recorded_subject.record)
      &&subject.reference_year==='2020'&&hit.binding.source_id==='gb:PHL:ADM3'
      &&equal(op.component_minus_source_union,row.original_administrative_comparison.component_minus_source_union),
      'Changed SEA318 subject/year/source/residual join');
    const projection={component_id:id,candidate_feature:candidate,
      whole_candidate_coverage_status:'complete-in-retained-comparison',
      whole_candidate_source_coverage:{remainder:op.component_minus_source_union},
      original_outcome_record:states.get(id)};
    const operation={component_id:id,source_comparison_record:op,
      positive_area_recorded_source_subject_ids:[subject.id],
      positive_area_source_feature_intersections:[{feature_sha256:hit.binding.feature_sha256,
        geometry_sha256:hit.binding.geometry_sha256,source_id:hit.binding.source_id,
        recorded_stable_subjects:hit.binding.recorded_stable_subjects,intersection_geometry:hit.intersection.geometry}]};
    const payload=supplied.retained_payload,target=payload?.target_current_feature;
    demand(equal(supplied.original_candidate_feature,candidate)&&equal(supplied.whole_original_case,projection)
      &&equal(supplied.retained_source_operation_row,operation)&&equal(supplied.original_source_rule_fit_record,row)
      &&supplied.geometry_scope==='full-component'&&supplied.whole_gap_completion===false,
      'Changed SEA318 literal source projection');
    demand(payload?.component_id===id&&equal(payload.candidate_feature,candidate)
      &&payload.candidate_feature_sha256===row.current_component_candidate.feature_sha256
      &&payload.candidate_geometry_sha256===row.current_component_candidate.geometry_sha256
      &&payload.candidate_feature_sha256===op.full_component_feature_sha256
      &&payload.candidate_geometry_sha256===op.component_geometry_sha256
      &&payload.target_stable_location_id===subject.id&&target?.feature_sha256===subject.original_feature_sha256
      &&target.parent_id===subject.original_parent_id&&/^[a-f0-9]{64}$/.test(target.geometry_sha256)
      &&payload.unsupported_candidate_remainder_included===false
      &&equal(payload.source_supported_intersection_fragments,[{source_feature_sha256:hit.binding.feature_sha256,
        source_geometry_sha256:hit.binding.geometry_sha256,intersection_geometry:hit.intersection.geometry}]),
      'Changed SEA318 candidate/target/parent/intersection binding');
    const physical=scope.original_physical_comparison_bindings.find(binding=>binding.component_id===id);
    demand(equal(physical.original_component_feature,candidate),'Changed SEA318 original physical candidate');
    const {candidate_feature_sha256,candidate_geometry_sha256,original_context,...packed}=physical.physical_comparison.row;
    demand(candidate_feature_sha256===payload.candidate_feature_sha256&&candidate_geometry_sha256===payload.candidate_geometry_sha256
      &&equal({...packed,complete_current_record_metadata_alias:'v1'},
        row.original_physical_query_custody.complete_original_packed_comparison_row.record),
      'Changed SEA318 complete original physical inverse');
    projections.push(projection);operations.push(operation);payloads.push(payload);
  }
  return {cohort:source.cases.map(row=>({component_id:row.component_id})),payloads,outcomes:projections,gb:operations,ncl:[],
    remainderRows:[],original_outcome_count:318};
}
