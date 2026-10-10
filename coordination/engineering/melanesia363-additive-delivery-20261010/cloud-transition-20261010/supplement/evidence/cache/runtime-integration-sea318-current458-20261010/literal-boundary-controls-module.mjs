import {createHash} from 'node:crypto';
function require(value, message) { if (!value) throw Error(message); }
function exactKeys(value, keys, name) {
  require(value && typeof value === 'object' && !Array.isArray(value), name + ' must be an object');
  require(Object.keys(value).sort().join('\0') === [...keys].sort().join('\0'), name + ' has missing/foreign fields');
}
export function canonicalValue(value) {
  if (Array.isArray(value)) return value.map(canonicalValue);
  if (value && typeof value === 'object') {
    const out = Object.create(null);
    for (const key of Object.keys(value).sort()) out[key] = canonicalValue(value[key]);
    return out;
  }
  require(value !== undefined && (typeof value !== 'number' || Number.isFinite(value)), 'Nonfinite or missing footprint value');
  return value;
}
export function polygonParts(geometry) {
  require(geometry && ['Polygon', 'MultiPolygon'].includes(geometry.type), 'Unsupported original native geometry / footprint primitive');
  exactKeys(geometry, ['type', 'coordinates'], 'Primitive geometry');
  const polygons = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates;
  require(Array.isArray(polygons) && polygons.length > 0, 'Missing footprint polygons');
  for (const polygon of polygons) {
    require(Array.isArray(polygon) && polygon.length > 0, 'Missing footprint rings');
    for (const ring of polygon) {
      require(Array.isArray(ring) && ring.length >= 4, 'Incomplete footprint ring');
      for (const point of ring) require(Array.isArray(point) && point.length === 2 && point.every(Number.isFinite)
        && Math.abs(point[0]) <= 180 && Math.abs(point[1]) <= 90, 'Invalid native footprint coordinate');
      require(ring[0][0] === ring.at(-1)[0] && ring[0][1] === ring.at(-1)[1], 'Unclosed footprint ring');
    }
  }
  return polygons;
}
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const canonical=value=>Buffer.from(JSON.stringify(canonicalValue(value))+'\n');
const hex=value=>typeof value==='string'&&/^[a-f0-9]{64}$/.test(value);
function demand(value,message){if(!value)throw Error(message);}
export function wholePrimitivePointsetEqual(a,b) {
  const normalize=g=>polygonParts(g).map(polygon=>polygon.map(ring=>{
    const points=ring.slice(0,-1),strings=points.map(point=>JSON.stringify(point));
    let first=0;for(let i=1;i<strings.length;i++)if(strings[i]<strings[first])first=i;
    return JSON.stringify([...points.slice(first),...points.slice(0,first)]);
  })).map(rings=>JSON.stringify([rings[0],...rings.slice(1).sort()])).sort();
  return JSON.stringify(normalize(a))===JSON.stringify(normalize(b));
}
function completeEmptyGeometry(geometry) {
  return geometry===null || geometry?.type==='GeometryCollection'&&Array.isArray(geometry.geometries)&&geometry.geometries.length===0
    || ['Polygon','MultiPolygon'].includes(geometry?.type)&&Array.isArray(geometry.coordinates)&&geometry.coordinates.length===0;
}
export function originalAdministrativeTargetHash({sourceScope,target,kind,expected}) {
  if(!['feature','geometry'].includes(kind)||!hex(expected))return false;
  const value=kind==='feature'?target:target.geometry;
  if(sha(canonical(value))===expected)return true;
  const matches=sourceScope.original_target_canonical_bindings?.filter(row=>row.target_id===target.id);
  if(matches?.length!==1)return false;
  const binding=matches[0],encoded=binding[kind+'_bytes_base64'];
  if(binding[kind+'_sha256']!==expected||typeof encoded!=='string')return false;
  const bytes=Buffer.from(encoded,'base64');
  if(bytes.length===0||bytes.length>32*1024*1024||sha(bytes)!==expected)return false;
  try{return JSON.stringify(canonicalValue(JSON.parse(bytes)))===JSON.stringify(canonicalValue(value));}
  catch{return false;}
}

export function retainedAdministrativeSourcePremises({record,candidate,sourceCase,sourceScope,target}) {
  demand(record?.component_id===sourceCase?.component_id,'Administrative component join differs');
  polygonParts(candidate);polygonParts(target.geometry);
  const failures=[],premise=(name,value)=>{if(!value)failures.push(name);};
  const digest=value=>sha(canonical(value));
  const same=(a,b)=>JSON.stringify(canonicalValue(a))===JSON.stringify(canonicalValue(b));
  const support=record.complete_support;
  demand(support?.hierarchy_disagreements,'Incomplete original administrative land operations');
  const empty=operation=>operation?.kind==='empty'&&operation.area_m2===0
    &&operation.planar_area===0&&completeEmptyGeometry(operation.geometry);
  premise('original-full-candidate-binding',record.candidate_feature_sha256===digest(sourceCase.original_candidate_feature)
    &&record.candidate_geometry_sha256===digest(candidate)
    &&wholePrimitivePointsetEqual(candidate,sourceCase.original_candidate_feature.geometry));
  premise('retained-whole-land-pointset',record.status==='mapped-land-support'
    &&support.mapped_land_support?.kind==='whole-operation-pointset'
    &&wholePrimitivePointsetEqual(candidate,support.mapped_land_support.geometry));
  for(const key of ['mapped_inland_water_support','outside_mapped_L1_context','contradictory_land_water_support','missing_reconstruction','extra_reconstruction'])premise(key,empty(support[key]));
  for(const key of ['L2-outside-L1','L3-outside-L2','L4-outside-L3'])premise(key,empty(support.hierarchy_disagreements[key]));
  const original=sourceScope.original_physical_comparison_bindings?.filter(x=>x.component_id===record.component_id);
  premise('complete-original-query-and-source-metadata',original?.length===1
    &&same(record,original[0].physical_comparison.row)
    &&Array.isArray(record.query_relations)&&record.query_relations.length>0
    &&original[0].original_queried_source_metadata.length===record.query_relations.length
    &&record.query_relations.every((query,i)=>{
      const native=original[0].original_queried_source_metadata[i].original_source_record_metadata;
      return native.id===query.source_id&&native.level===query.source_level
        &&native.record_sha256===query.source_record_sha256
        &&native.decoded_pointset_binary64_sha256===query.source_pointset_sha256
        &&query.status==='checked'&&Array.isArray(query.container_chain_issues)&&query.container_chain_issues.length===0;
    })
    &&record.query_relations.some(q=>q.source_level===1&&q.source_covers_candidate===true&&q.intersects===true&&q.disjoint===false));
  const payload=sourceCase.retained_payload,operation=sourceCase.retained_source_operation_row;
  premise('whole-administrative-candidate-and-target',payload?.component_id===record.component_id
    &&payload.candidate_feature_sha256===record.candidate_feature_sha256
    &&payload.candidate_geometry_sha256===record.candidate_geometry_sha256
    &&payload.target_stable_location_id===target.id
    &&payload.unsupported_candidate_remainder_included===false
    &&payload.source_supported_intersection_fragments?.length===1
    &&wholePrimitivePointsetEqual(candidate,payload.source_supported_intersection_fragments[0].intersection_geometry)
    &&originalAdministrativeTargetHash({sourceScope,target,kind:'feature',expected:payload.target_current_feature.feature_sha256})
    &&originalAdministrativeTargetHash({sourceScope,target,kind:'geometry',expected:payload.target_current_feature.geometry_sha256})
    &&payload.target_current_feature.parent_id===target.properties?.parent_id);
  const admin=operation?.source_comparison_record;
  if(admin){
    const hits=operation.positive_area_source_feature_intersections,subject=admin.uniquely_covering_compatible_recorded_subject;
    premise('retained-simplified-unique-source-subject',admin.component===record.component_id
      &&admin.component_geometry_sha256===record.candidate_geometry_sha256
      &&admin.full_component_feature_sha256===record.candidate_feature_sha256
      &&admin.current_component_relation==='retained-full-original-feature-pointset'
      &&admin.status==='one-compatible-recorded-subject-uniquely-covers-component'
      &&admin.component_minus_source_union?.is_empty===true
      &&completeEmptyGeometry(admin.component_minus_source_union.geometry)
      &&admin.component_minus_source_union.planar_area_coordinate_units_squared===0
      &&admin.component_minus_source_union.planar_length_coordinate_units===0
      &&admin.component_minus_source_union.is_valid===true
      &&admin.component_minus_source_union.geometry_type===admin.component_minus_source_union.geometry?.type
      &&admin.component_minus_source_union.geometry_sha256===digest(admin.component_minus_source_union.geometry)
      &&operation.positive_area_recorded_source_subject_ids?.length===1
      &&operation.positive_area_recorded_source_subject_ids[0]===target.id
      &&hits?.length===1&&hits[0].recorded_stable_subjects?.length===1
      &&same(hits[0].recorded_stable_subjects[0],subject)
      &&subject.id===target.id&&originalAdministrativeTargetHash({sourceScope,target,kind:'feature',expected:subject.original_feature_sha256})
      &&subject.original_parent_id===target.properties.parent_id
      &&typeof subject.reference_year==='string'&&subject.reference_year.length>0
      &&admin.feature_intersections.some(hit=>hit.binding.feature_sha256===hits[0].feature_sha256
        &&hit.binding.geometry_sha256===hits[0].geometry_sha256&&hit.binding.valid_polygon===true
        &&hit.source_feature_covers_entire_component===true
        &&wholePrimitivePointsetEqual(candidate,hit.intersection.geometry)));
  }else{
    const hits=operation?.province_intersections?.filter(hit=>hit.intersection_dimension==='area');
    const coverage=sourceCase.whole_original_case?.whole_candidate_source_coverage;
    premise('retained-generalized-NCL-unique-source-subject',operation?.component_id===record.component_id
      &&operation.candidate_feature_sha256===record.candidate_feature_sha256
      &&operation.candidate_geometry_sha256===record.candidate_geometry_sha256
      &&operation.disposition==='unique-positive-area-georep-province-match'
      &&operation.positive_area_target_stable_location_ids?.length===1
      &&operation.positive_area_target_stable_location_ids[0]===target.id
      &&hits?.length===1&&hits[0].target_stable_location_id===target.id
      &&coverage?.status==='complete-exact-candidate-minus-source-empty'
      &&coverage.target_stable_location_id===target.id
      &&coverage.candidate_minus_retained_source_feature?.is_empty===true
      &&completeEmptyGeometry(coverage.candidate_minus_retained_source_feature.geometry)
      &&coverage.candidate_minus_retained_source_feature.area_degree2===0
      &&['Polygon','MultiPolygon'].includes(coverage.candidate_minus_retained_source_feature.geometry_type)
      &&(coverage.candidate_minus_retained_source_feature.geometry===null
        ||coverage.candidate_minus_retained_source_feature.geometry_type===coverage.candidate_minus_retained_source_feature.geometry.type)
      &&wholePrimitivePointsetEqual(candidate,hits[0].intersection_geometry)
      &&sourceScope.source_policy_facts.generalized_ncl_profile.source_product.features.some(feature=>
        feature.target_stable_location_id===target.id&&feature.source_path===hits[0].source_path
        &&feature.source_file_sha256===hits[0].source_file_sha256
        &&feature.source_feature_sha256===hits[0].source_feature_sha256
        &&feature.source_geometry_sha256===hits[0].source_geometry_sha256));
  }
  return {component_id:record.component_id,target_id:target.id,source_compatible:failures.length===0,
    failed_premises:failures,representation:'retained-base-plus-additions',
    authority:record.physical_authority,status:record.physical_status,limits:record.physical_limits,
    source_vintage:record.source_vintage,
    source_profile:admin?'retained-consumed-simplified-administrative-source':'retained-generalized-NCL-2024-province-source'};
}

const SEA318_BATCH='gap-operational-batch:0393f64c9f8549bcfca1ace9';
export function retainedAdministrative318CaseView({fit,physicalCase,querySources,targetBindings,componentId}) {
  demand(fit?.batch_id===SEA318_BATCH&&Array.isArray(fit.cases)&&fit.cases.length===30
    &&new Set(fit.cases.map(row=>row.component_id)).size===30,'Foreign SEA318 priority roster');
  const matches=fit.cases.filter(row=>row.component_id===componentId);
  demand(matches.length===1,'Missing/nonunique SEA318 case');const row=matches[0],q=row.original_physical_query_custody;
  const equal=(a,b)=>JSON.stringify(canonicalValue(a))===JSON.stringify(canonicalValue(b));
  demand(row.source_rule_fit_state==='established'&&row.whole_gap_completion===false
    &&row.current_component_candidate.component_id===componentId&&physicalCase?.batch_id===SEA318_BATCH
    &&physicalCase.case?.component_id===componentId,'Foreign SEA318 fit/candidate/physical case');
  const original=physicalCase.case,feature=row.current_component_candidate.feature;
  demand(equal(original.complete_current_component_candidate.feature,feature)
    &&equal(original.physical_comparison_packed_row,q.complete_original_packed_comparison_row)
    &&equal(original.physical_query_relations,q.complete_original_query_relations)
    &&equal(original.physical_query_source_ids,q.complete_original_query_source_ids)
    &&equal(original.existing_full_admin_comparison.record,row.original_administrative_comparison.record),
    'SEA318 original case inverse differs');
  demand(sha(canonical(feature))===row.current_component_candidate.feature_sha256
    &&sha(canonical(feature.geometry))===row.current_component_candidate.geometry_sha256,
    'SEA318 whole candidate hash differs');
  const packed=q.complete_original_packed_comparison_row.record;
  demand(packed.complete_current_record_metadata_alias==='v1'
    &&packed.component_id===componentId&&equal(packed.query_relations,q.complete_original_query_relations),
    'Foreign SEA318 original physical metadata alias');
  // Restore only the original alias's whole candidate hashes. All other original
  // relation/support/authority fields stay literal, including unknown limits.
  const record={...packed,candidate_feature_sha256:row.current_component_candidate.feature_sha256,
    candidate_geometry_sha256:row.current_component_candidate.geometry_sha256};
  demand(Array.isArray(q.complete_query_source_pointsets)
    &&q.complete_query_source_pointsets.length===record.query_relations.length
    &&Array.isArray(querySources)&&querySources.length===record.query_relations.length
    &&new Set(querySources.map(source=>source.source_id)).size===querySources.length,'Incomplete SEA318 queried sources');
  const queried=record.query_relations.map((relation,index)=>{
    const source=querySources[index],pin=q.complete_query_source_pointsets[index];
    demand(source?.source_id===relation.source_id&&source.native_record_sha256===relation.source_record_sha256
      &&source.decoded_pointset_binary64_sha256===relation.source_pointset_sha256
      &&source.coordinate_bytes_sha256===pin.coordinate_bytes_sha256
      &&source.decoded_pointset_binary64_sha256===pin.binary64_pointset_sha256
      &&source.native_metadata?.id===relation.source_id&&source.native_metadata.level===relation.source_level
      &&source.native_metadata.record_sha256===relation.source_record_sha256
      &&source.native_metadata.decoded_pointset_binary64_sha256===relation.source_pointset_sha256,
      'SEA318 complete query metadata inverse differs');
    return {original_source_record_metadata:source.native_metadata};
  });
  const admin=row.original_administrative_comparison.record;
  demand(equal(admin,row.original_administrative_comparison.record)&&admin.component===componentId
    &&admin.full_component_feature_sha256===record.candidate_feature_sha256
    &&admin.component_geometry_sha256===record.candidate_geometry_sha256,'SEA318 retained comparison differs');
  const hits=admin.feature_intersections.filter(hit=>hit.intersection.planar_area_coordinate_units_squared>0
    &&hit.intersection.is_empty===false).map(hit=>({...hit.binding,intersection_geometry:hit.intersection.geometry}));
  const subject=admin.uniquely_covering_compatible_recorded_subject;
  demand(hits.length===1&&subject&&hits[0].recorded_stable_subjects?.length===1
    &&equal(hits[0].recorded_stable_subjects[0],subject),'SEA318 nonunique positive subject');
  const bindings=targetBindings.filter(binding=>binding.target_id===subject.id);
  demand(bindings.length===1,'Missing SEA318 original target canonical binding');
  const binding=bindings[0];
  const sourceCase={component_id:componentId,original_candidate_feature:feature,
    retained_source_operation_row:{source_comparison_record:admin,positive_area_source_feature_intersections:hits,
      positive_area_recorded_source_subject_ids:[subject.id]},
    retained_payload:{component_id:componentId,candidate_feature_sha256:record.candidate_feature_sha256,
      candidate_geometry_sha256:record.candidate_geometry_sha256,target_stable_location_id:subject.id,
      unsupported_candidate_remainder_included:false,
      source_supported_intersection_fragments:hits,
      target_current_feature:{feature_sha256:binding.feature_sha256,geometry_sha256:binding.geometry_sha256,parent_id:subject.original_parent_id}}};
  const sourceScope={original_physical_comparison_bindings:[{component_id:componentId,
    physical_comparison:{row:record},original_queried_source_metadata:queried}],original_target_canonical_bindings:bindings};
  return {record,sourceCase,sourceScope,original:row,ordinal:fit.cases.indexOf(row)};
}
