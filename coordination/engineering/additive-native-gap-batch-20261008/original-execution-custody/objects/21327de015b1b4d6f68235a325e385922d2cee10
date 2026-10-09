import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync, gzipSync} from 'node:zlib';
import {validateNativeSelectionReceipt} from './native-ownership/require-verified-selection.mjs';
import verifiedCandidates from './native-ownership/verified-candidates.json' with {type:'json'};
import {canonicalValue, footprintValueSha256, polygonParts, additiveReleaseFootprintDigest} from '../src/effective-footprint.js';
import {candidateBudget, committedPreparationFiles, createNativeCandidateOutput, requirePlainExecution} from './native-ownership/native-preparation-guards.mjs';

import {nativePolygonIntervals} from '../src/native-grid.js';
import {nativeRuntimeIndex} from '../src/native-runtime.js';
import {unshuffleOwnershipBytes} from '../src/ownership-codec.js';
export const ADDITIVE_PROPOSAL_VERSION='unactivated-additive-native-release-v1';
export const ADDITIVE_BATCH_PROPOSAL_VERSION='unactivated-additive-native-batch-v1';
export const SOURCE_PREMISES_VERSION='retained-land-source-premises-v1';
export const INVENTORY_VERSION = 'complete-source-relative-gap-inventory-v1';
export const DISPOSITIONS = ['eligible', 'assigned', 'zero-cell', 'already-resolved', 'rejected', 'awaiting-evidence'];
const categories = new Set(['mapped-land-support', 'mapped-inland-water-support', 'mixed-source-support', 'outside-mapped-L1-context', 'unknown']);
const sha = raw => createHash('sha256').update(raw).digest('hex');
const canonical = value => Buffer.from(JSON.stringify(canonicalValue(value)) + '\n');
const hex = value => /^[a-f0-9]{64}$/.test(value ?? '');
function demand(value, message) { if (!value) throw Error(message); }

// Input intervals are produced by the literal native operator, never accepted
// from a source approval flag. The cold entry authenticates that operator and
// complete containing owner assets before calling this shared combination.
export function combineNativeBatch({scopeIds,sourceRows,candidates,ownerRows,continuousConflicts=[],size=262166}) {
  demand(Array.isArray(scopeIds)&&scopeIds.length>0&&new Set(scopeIds).size===scopeIds.length
    &&scopeIds.every(id=>typeof id==='string'&&id),'Invalid complete batch scope');
  demand(Number.isInteger(size)&&size>0&&size<=262166,'Invalid native batch grid');
  const original=new Map(),native=new Map(),old=new Map();
  for(const row of sourceRows){demand(scopeIds.includes(row.component_id)&&!original.has(row.component_id)
    &&typeof row.source_compatible==='boolean','Foreign/duplicate/incomplete source decision');original.set(row.component_id,row);}
  demand(original.size===scopeIds.length,'Source batch omitted a candidate');
  const validRun=run=>Array.isArray(run)&&run.length===3&&run.every(Number.isInteger)
    &&run[0]>=0&&run[1]>run[0]&&run[1]<=size&&run[2]>0&&run[2]<=49625;
  for(const row of ownerRows){
    demand(Number.isInteger(row.y)&&row.y>=0&&row.y<size&&!old.has(row.y)
      &&Array.isArray(row.complete_owner_intervals),'Foreign/duplicate complete owner row');
    let end=0;for(const run of row.complete_owner_intervals){demand(validRun(run)&&run[0]>=end,'Corrupt complete owner interval');end=run[1];}
    old.set(row.y,row.complete_owner_intervals.map(run=>[...run]));
  }
  for(const candidate of candidates){
    const source=original.get(candidate.component_id);
    demand(source?.source_compatible===true&&!native.has(candidate.component_id)
      &&candidate.target_id===source.target_id&&candidate.pixelIndex===source.pixelIndex
      &&Number.isInteger(candidate.pixelIndex)&&candidate.pixelIndex>0&&candidate.pixelIndex<=49625
      &&Number.isInteger(candidate.row_start)&&Number.isInteger(candidate.row_end)&&candidate.row_start>=0
      &&candidate.row_end>candidate.row_start&&candidate.row_end<=size
      &&Array.isArray(candidate.rows)&&candidate.rows.length===candidate.row_end-candidate.row_start,'Foreign/duplicate candidate or target/window join');
    const seen=new Set();for(const row of candidate.rows){
      demand(Number.isInteger(row.y)&&row.y>=candidate.row_start&&row.y<candidate.row_end
        &&!seen.has(row.y)&&old.has(row.y)&&Array.isArray(row.runs),'Missing full owner row or duplicate candidate row');seen.add(row.y);
      let end=0;for(const run of row.runs){demand(validRun(run)&&run[2]===candidate.pixelIndex&&run[0]>=end,'Invalid native candidate interval');end=run[1];}
    }
    native.set(candidate.component_id,candidate);
  }
  demand([...original.values()].every(row=>row.source_compatible!==true||native.has(row.component_id)),'Eligible candidate has no actual native result');
  const conflicts=new Map();const conflict=(id,reason)=>{if(!conflicts.has(id))conflicts.set(id,new Set());conflicts.get(id).add(reason);};
  demand(Array.isArray(continuousConflicts),'Missing continuous batch conflict roster');
  const seenPairs=new Set();
  for(const pair of continuousConflicts){demand(Array.isArray(pair)&&pair.length===2&&pair[0]!==pair[1]
    &&native.has(pair[0])&&native.has(pair[1]),'Foreign continuous batch conflict');
    const key=[...pair].sort().join('\n');demand(!seenPairs.has(key),'Duplicate continuous conflict');seenPairs.add(key);
    if(original.get(pair[0]).target_id!==original.get(pair[1]).target_id){conflict(pair[0],'continuous-batch-owner-conflict');conflict(pair[1],'continuous-batch-owner-conflict');}}
  const byRow=new Map();
  for(const candidate of native.values())for(const row of candidate.rows)for(const run of row.runs){
    for(const previous of old.get(row.y))if(previous[2]!==run[2]&&Math.max(previous[0],run[0])<Math.min(previous[1],run[1]))conflict(candidate.component_id,'existing-foreign-owner');
    if(!byRow.has(row.y))byRow.set(row.y,[]);byRow.get(row.y).push({id:candidate.component_id,run});
  }
  // Symmetric refusal: ordering must never choose the first competing owner.
  for(const values of byRow.values())for(let a=0;a<values.length;a++)for(let b=a+1;b<values.length;b++){
    const one=values[a],two=values[b];if(one.run[2]!==two.run[2]&&Math.max(one.run[0],two.run[0])<Math.min(one.run[1],two.run[1])){
      conflict(one.id,'competing-batch-owner');conflict(two.id,'competing-batch-owner');
    }
  }
  const subtract=(run,prior)=>{
    let spans=[[run[0],run[1],run[2]]];
    for(const previous of prior){const next=[];for(const span of spans){
      if(Math.max(span[0],previous[0])>=Math.min(span[1],previous[1]))next.push(span);
      else {demand(previous[2]===span[2],'Unrefused foreign owner');if(span[0]<previous[0])next.push([span[0],previous[0],span[2]]);if(previous[1]<span[1])next.push([previous[1],span[1],span[2]]);}
    }spans=next;}return spans;
  };
  const merge=runs=>{
    const sorted=runs.map(run=>[...run]).sort((a,b)=>a[0]-b[0]||a[1]-b[1]||a[2]-b[2]),result=[];
    for(const run of sorted){const previous=result.at(-1);if(previous&&previous[2]===run[2]&&run[0]<=previous[1])previous[1]=Math.max(previous[1],run[1]);
      else {demand(!previous||run[0]>=previous[1],'Combined owner overlap');result.push(run);}}
    return result;
  };
  const patch=new Map(),decisions=[];let candidateCells=0;
  for(const id of scopeIds){
    const source=original.get(id),candidate=native.get(id);
    if(source.source_compatible!==true){decisions.push({...source,disposition:'rejected',reason_kind:'source-exception',native_cells:0});continue;}
    if(conflicts.has(id)){decisions.push({...source,disposition:'rejected',reason_kind:'native-conflict',native_conflicts:[...conflicts.get(id)].sort(),native_cells:0});continue;}
    let cells=0;for(const row of candidate.rows)for(const run of row.runs)for(const span of subtract(run,old.get(row.y))){
      if(!patch.has(row.y))patch.set(row.y,[]);patch.get(row.y).push(span);cells+=span[1]-span[0];
    }
    candidateCells+=cells;decisions.push({...source,disposition:cells?'assigned':'zero-cell',reason_kind:cells?'new-unowned-native-cells':'positive-geometry-no-new-native-cells',native_cells:cells});
  }
  const rows=[...patch].sort((a,b)=>a[0]-b[0]).map(([y,runs])=>({y,runs:merge(runs)}));
  const virtual=rows.map(row=>({y:row.y,complete_owner_intervals:merge([...old.get(row.y),...row.runs])}));
  const assignedCells=rows.reduce((sum,row)=>sum+row.runs.reduce((n,run)=>n+run[1]-run[0],0),0);
  // Shared same-owner candidate cells count once globally. Per-candidate counts
  // describe support/contribution and are deliberately not summed as repairs.
  return {decisions,rows,virtual_owner_rows:virtual,assigned_cells:assignedCells,
    candidate_cell_contributions:candidateCells,shared_same_owner_cells:candidateCells-assignedCells,
    removed_cells:0,reassigned_cells:0,source_exceptions:decisions.filter(row=>row.reason_kind==='source-exception').length,
    native_conflicts:decisions.filter(row=>row.reason_kind==='native-conflict').length,
    assigned_components:decisions.filter(row=>row.disposition==='assigned').length,
    zero_cell_components:decisions.filter(row=>row.disposition==='zero-cell').length};
}
function safe(name) { return typeof name === 'string' && /^[a-zA-Z0-9_.\/-]+$/.test(name) && name.split('/').every(p => p && p !== '.' && p !== '..'); }

// These predicates consume full authenticated predecessor operation products.
// Their result alone is not a custody/source-authority brand or release permit.
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
export function retainedLandSourcePremises({record,candidate,sourceCase,sourceScope,target}) {
  demand(record?.component_id===sourceCase?.component_id&&typeof record.component_id==='string','Source evidence component join differs');
  polygonParts(candidate);polygonParts(target.geometry);
  const support=record.complete_support;
  demand(support&&support.hierarchy_disagreements,'Incomplete original support operation roster');
  const emptyKeys=['mapped_inland_water_support','outside_mapped_L1_context','contradictory_land_water_support','missing_reconstruction','extra_reconstruction'];
  const empty=operation=>operation?.kind==='empty'&&operation.area_m2===0&&operation.planar_area===0&&completeEmptyGeometry(operation.geometry);
  const failures=[];const premise=(name,value)=>{if(!value)failures.push(name);};
  premise('original-candidate-valid',sourceCase.candidate_valid===true);
  premise('retained-whole-land-pointset',record.status==='mapped-land-support'&&support.mapped_land_support?.kind==='whole-operation-pointset'
    &&wholePrimitivePointsetEqual(candidate,support.mapped_land_support.geometry));
  for(const key of emptyKeys)premise(key,empty(support[key]));
  for(const key of ['L2-outside-L1','L3-outside-L2','L4-outside-L3'])premise(key,empty(support.hierarchy_disagreements[key]));
  premise('complete-original-source-context',sourceScope?.active_feature_count===49625&&sourceScope.active_part_count===36
    &&sourceScope.retired_location_count===19050&&sourceScope.native_feature_count===218&&sourceScope.native_unique_ecoregion_id_count===194);
  premise('full-candidate-source-join',wholePrimitivePointsetEqual(candidate,sourceCase.candidate_geometry));
  premise('retained-target-context',target.id===sourceCase.atlas_target_id&&target.properties?.parent_id===sourceCase.atlas_target_parent_id
    &&target.properties?.name===sourceCase.atlas_target_name);
  const native=sourceCase.native_covering_named_envelopes,v22=sourceCase.v22_covering_named_envelopes;
  premise('unique-original-named-envelopes',native?.length===1&&v22?.length===1&&native[0].id===sourceCase.source_ecoregion_id
    &&v22[0].id===native[0].id&&native[0].name===target.properties.name&&v22[0].name===target.properties.name
    &&sourceCase.native_source_properties?.ECOREGION_ID===native[0].id&&sourceCase.v22_source_properties?.ECOREGION_ID===native[0].id);
  premise('both-original-source-predicates',sourceCase.native_source_covers_candidate===true&&sourceCase.v22_source_covers_candidate===true);
  const parents=sourceCase.source_parent_coverage_records;
  premise('complete-source-parent-context',Array.isArray(parents)&&parents.length>0&&parents.some(row=>row.covers===true&&row.name===sourceCase.source_parent)
    &&sourceCase.atlas_parent_hierarchy_record?.id===target.properties.parent_id&&sourceCase.atlas_parent_hierarchy_record?.name===sourceCase.source_parent);
  const retired=sourceCase.retired_administrative_reference_context,ids=sourceCase.atlas_target_source_member_ids;
  premise('full-retired-member-context',Array.isArray(retired)&&Array.isArray(ids)&&ids.length>0&&new Set(ids).size===ids.length
    &&retired.length===ids.length&&JSON.stringify(retired.map(row=>row.id).sort())===JSON.stringify([...ids].sort())
    &&retired.every(row=>Array.isArray(row.parent_chain)&&row.parent_chain.length===5));
  premise('complete-other-owner-exclusion',Array.isArray(sourceCase.active_feature_hits)&&sourceCase.active_feature_hits.every(hit=>hit.id===target.id)
    &&Array.isArray(sourceCase.new_neighbor_intersections)&&sourceCase.new_neighbor_intersections.length===0);
  premise('literal-old-loss-and-full-gain',sourceCase.union_loss_area_deg2===0&&completeEmptyGeometry(sourceCase.loss_geometry)
    &&sourceCase.gain_candidate_symmetric_difference_area_deg2===0&&completeEmptyGeometry(sourceCase.gain_candidate_symmetric_difference_geometry)
    &&sourceCase.candidate_not_added_area_deg2===0&&completeEmptyGeometry(sourceCase.candidate_not_added_geometry)
    &&wholePrimitivePointsetEqual(candidate,sourceCase.gain_geometry));
  return {component_id:record.component_id,source_compatible:failures.length===0,failed_premises:failures,
    representation:'retained-base-plus-additions',authority:record.physical_authority,status:record.physical_status,limits:record.physical_limits};
}

// Typed retained-source rule for the original ADM2 county comparison. This
// consumes the complete predecessor observations; it does not turn source
// compatibility into present-day physical authority or a native assignment.
export function retainedCountySourcePremises({record,candidate,sourceCase,sourceScope,target}) {
  demand(record?.component_id===sourceCase?.component_id&&typeof record.component_id==='string','County component join differs');
  polygonParts(candidate);polygonParts(target.geometry);
  const failures=[],premise=(name,value)=>{if(!value)failures.push(name);};
  const support=record.complete_support,empty=operation=>operation?.kind==='empty'&&operation.area_m2===0
    &&operation.planar_area===0&&completeEmptyGeometry(operation.geometry);
  demand(support?.hierarchy_disagreements,'Incomplete county source operations');
  premise('retained-whole-land-pointset',record.status==='mapped-land-support'
    &&support.mapped_land_support?.kind==='whole-operation-pointset'
    &&wholePrimitivePointsetEqual(candidate,support.mapped_land_support.geometry));
  for(const key of ['mapped_inland_water_support','outside_mapped_L1_context','contradictory_land_water_support','missing_reconstruction','extra_reconstruction'])premise(key,empty(support[key]));
  for(const key of ['L2-outside-L1','L3-outside-L2','L4-outside-L3'])premise(key,empty(support.hierarchy_disagreements[key]));
  const county=sourceCase.county_target;
  premise('typed-original-county-vintage',county?.administrative_level==='ADM2'&&county.source_role==='Counties'
    &&county.represented_year_claim==='2018'&&county.atlas_target_id==='gb:USA:ADM2:'+county.shape_id);
  premise('current-target-identity',target.id===county?.atlas_target_id&&target.properties?.name===county?.name
    &&target.properties?.parent_id==='framework:province:alaska:4057e2fddbc5');
  const valid=sourceCase.geometry_validity;
  premise('complete-valid-original-geometries',['candidate','atlas_target','full_county_source','simplified_county_source','alaska_adm1_parent']
    .every(key=>valid?.[key]?.valid===true&&valid[key].empty===false));
  const covered=value=>value?.status==='measured'&&value.candidate_covered_exactly===true
    &&value.candidate_uncovered_area_projected_m2_exact===0&&value.candidate_coverage_ratio===1;
  for(const key of ['candidate_vs_alaska_parent','candidate_vs_full_county','candidate_vs_simplified_county'])
    premise(key,covered(sourceCase.candidate_to_target_intersections_and_uncovered?.[key]));
  premise('original-parent-coverage',covered(sourceCase.source_parent_coverage));
  premise('candidate-source-variants-agree',sourceCase.source_variants_same_for_this_candidate===true);
  // Disjoint contextual native queries are preserved, never mistaken for
  // candidate-covering records. Every original ordered query must match.
  const queries=record.query_relations,native=sourceCase.native_land_relations;
  demand(Array.isArray(queries)&&Array.isArray(native)&&queries.length===native.length,'Incomplete original county queries');
  premise('all-original-query-predicates',queries.every((query,i)=>{
    const row=native[i],original=row?.original_query_relation;
    return row?.component_id===record.component_id&&row.gshhg_native_id===query.source_id
      &&row.gshhg_level===query.source_level&&row.record_sha256===query.source_record_sha256
      &&original?.source_record_sha256===query.source_record_sha256&&original.source_level===query.source_level
      &&original.candidate_covered===query.source_covers_candidate
      &&original.candidate_covers_source===query.candidate_covers_source&&original.disjoint===query.disjoint
      &&original.witness===query.witness&&row.original_predicates_match===true
      &&row.measured?.status==='measured'&&row.measured.intersects===query.intersects
      &&row.measured.candidate_covered_exactly===query.source_covers_candidate;
  }));
  const linked=sourceCase.linked_gshhg_native_ids;
  premise('actual-linked-native-land-support',Array.isArray(linked)&&linked.length>0&&new Set(linked).size===linked.length
    &&linked.every(id=>native.some(row=>row.gshhg_native_id===id&&row.gshhg_level===1&&covered(row.measured))));
  premise('complete-original-contact-scope',sourceScope?.assigned_scope?.component_ids?.includes(record.component_id)
    &&sourceScope.assigned_scope.physical_query_relation_count===25&&sourceScope.assigned_scope.read_only_edge_neighbor_ids?.length===17
    &&sourceCase.original_contacts_match_all_17_actual_atlas_features===true
    &&sourceCase.original_25_relation_predicates_match===true);
  premise('other-atlas-owner-exclusion',Array.isArray(sourceCase.measured_actual_atlas_intersecting_neighbor_ids)
    &&sourceCase.measured_actual_atlas_intersecting_neighbor_ids.length===1
    &&sourceCase.measured_actual_atlas_intersecting_neighbor_ids[0]===target.id);
  return {component_id:record.component_id,source_compatible:failures.length===0,failed_premises:failures,
    source_profile:'retained-USA-ADM2-counties-2018',target_id:target.id,
    authority:record.physical_authority,status:record.physical_status,limits:record.physical_limits,
    representation:'retained-base-plus-additions'};
}

const resolutionBrands = new WeakSet();
// A reconciliation, not permission for a new repair. The caller authenticates
// these complete bodies against its independently frozen selected-bank plan.
// Stale pre-repair geography cannot reset an accepted repair's state.
export function selectedBankResolutions({features, corrections, selectedManifest, selectionReceipt,
  selectedManifestSha256, bankDecodedSha256, expectedBankDecodedSha256}) {
  demand(hex(selectedManifestSha256) && hex(bankDecodedSha256) && bankDecodedSha256===expectedBankDecodedSha256,
    'Stale or foreign installed selected bank');
  demand(selectedManifest?.method==='native-linear-evenodd-first-owner-v1' && selectedManifest.version===2
    && selectedManifest.accounting?.owners===49625 && selectionReceipt?.owners===49625
    && selectionReceipt.method===selectedManifest.method && selectionReceipt.unchecked_cells===0
    && selectionReceipt.products?.find(pin=>pin.path==='manifest.json')?.sha256===selectedManifestSha256,
    'Missing actual selected native-bank registration');
  const migration=selectedManifest.provenance?.source_migration;
  demand(migration?.history_transfer==='none' && migration.after_footprints_sha256===selectedManifest.footprints_sha256
    && Array.isArray(corrections) && corrections.length>0 && Array.isArray(features), 'Missing accepted baseline migration');
  const targets=new Map(features.map(feature=>[feature.id,feature]));
  demand(targets.size===features.length, 'Duplicate selected baseline identity');
  const result=new Map(), changed=new Set(migration.changed_ids);
  demand(changed.size===corrections.length, 'Accepted baseline corrections/selected migration scope differ');
  for(const correction of corrections){
    const feature=targets.get(correction.subject_id);
    demand(feature && changed.has(feature.id) && !result.has(correction.component_id)
      && hex(correction.component_geometry_sha256) && hex(correction.geometry_sha256_after)
      && JSON.stringify(canonicalValue(feature.geometry))===JSON.stringify(canonicalValue(correction.pointsets?.new))
      && (correction.historical_transfer===false || correction.historical_transfer==='none'), 'Actual selected full target differs from accepted after geometry');
    result.set(correction.component_id,{target_id:feature.id,component_geometry_sha256:correction.component_geometry_sha256,
      selected_manifest_sha256:selectedManifestSha256,selected_bank_decoded_sha256:bankDecodedSha256,
      accepted_after_geometry_sha256:correction.geometry_sha256_after});
  }
  resolutionBrands.add(result);return result;
}

// A classification is never an authority to alter ownership. This first stage
// is immediately usable on the retained complete #1261 inventory, including
// every unknown. Repair admission consumes a separate whole source-rule proof.
export function candidateDisposition(row, resolutions) {
  demand(typeof row?.component_id === 'string' && row.component_id && hex(row.candidate_feature_sha256)
    && hex(row.candidate_geometry_sha256) && categories.has(row.status), 'Incomplete original candidate record');
  demand(typeof row.physical_authority === 'string' && typeof row.physical_status === 'string'
    && Array.isArray(row.physical_limits), 'Missing original physical limits');
  if(resolutions!==undefined){
    demand(resolutionBrands.has(resolutions), 'Unverified baseline resolutions');
    const resolved=resolutions.get(row.component_id);
    if(resolved){
      demand(row.candidate_geometry_sha256===resolved.component_geometry_sha256, 'Resolved component original pointset changed');
      return {disposition:'already-resolved',reason:'accepted full after geometry is present in actual selected baseline; no new repair',resolution:resolved};
    }
  }
  return row.status === 'mapped-inland-water-support'
    ? {disposition: 'rejected', reason: 'source-relative-water; retained, not reassigned'}
    : {disposition: 'awaiting-evidence', reason: 'classification does not establish source fitness or target eligibility'};
}

export function inventoryRows(rows, {source, parent, expectedIds, expectedRosterSha256, originalRecordBytes, resolutions}) {
  demand(parent?.version === 1 && Number.isSafeInteger(parent.components) && parent.components > 0
    && hex(parent.roster_sha256) && hex(parent.report_sha256), 'Missing independent complete parent denominator');
  demand(Array.isArray(expectedIds) && expectedIds.length && new Set(expectedIds).size === expectedIds.length
    && expectedIds.every(id => typeof id === 'string' && id), 'Missing exact independently selected IDs');
  const expected = new Set(expectedIds), seen = new Set(), counts = Object.fromEntries(DISPOSITIONS.map(key => [key, 0]));
  const sourceCounts = {}, identities = [], output = [];
  demand(Array.isArray(originalRecordBytes) && originalRecordBytes.length === rows.length
    && originalRecordBytes.every(raw=>Buffer.isBuffer(raw)), 'Complete original record byte boundaries required');
  rows.forEach((row, ordinal) => {
    demand(JSON.stringify(canonicalValue(JSON.parse(originalRecordBytes[ordinal]))) === JSON.stringify(canonicalValue(row)),
      'Original record bytes/value disagree');
    const decision = candidateDisposition(row,resolutions), id = row.component_id;
    demand(expected.has(id) && !seen.has(id), 'Foreign or duplicate candidate identity');
    seen.add(id); counts[decision.disposition]++;
    sourceCounts[row.status] = (sourceCounts[row.status] ?? 0) + 1;
    identities.push({id, feature_sha256: row.candidate_feature_sha256});
    output.push({component_id: id, ...decision, source_relative_category: row.status,
      physical_authority: row.physical_authority, physical_status: row.physical_status,
      physical_limits: row.physical_limits, candidate_feature_sha256: row.candidate_feature_sha256,
      candidate_geometry_sha256: row.candidate_geometry_sha256,
      original: {source, ordinal, whole_record_sha256: sha(originalRecordBytes[ordinal])}});
  });
  demand(seen.size === expected.size, 'Missing candidate identity');
  const roster = footprintValueSha256(identities);
  demand(roster === expectedRosterSha256, 'Original ordered candidate roster changed');
  demand(output.length <= parent.components && Object.values(counts).reduce((a,b) => a+b,0) === output.length,
    'Disposition inventory is incomplete');
  return {rows: output, facts: {version: 1, operation: INVENTORY_VERSION, parent,
    components: output.length, complete_ordered_roster_sha256: roster, counts, source_relative_counts: sourceCounts,
    limits: ['Source-relative categories retained exactly; no physical approval, ownership or geometry change.',
      'Every original whole source body remains required for row restoration; aliases are not replacement geometry.']}};
}

export function joinInventoryFacts(children, parent) {
  demand(Array.isArray(children) && children.length, 'Missing inventory children');
  const ids = new Set(), ordered = [], counts = Object.fromEntries(DISPOSITIONS.map(key => [key,0])), sourceCounts = {};
  for (const child of children) {
    demand(JSON.stringify(canonicalValue(child.facts.parent)) === JSON.stringify(canonicalValue(parent))
      && child.facts.operation === INVENTORY_VERSION && child.rows.length === child.facts.components, 'Foreign inventory parent');
    const actualCounts = Object.fromEntries(DISPOSITIONS.map(key => [key,0]));
    for (const row of child.rows) {
      demand(!ids.has(row.component_id) && DISPOSITIONS.includes(row.disposition), 'Duplicate or invalid disposition');
      ids.add(row.component_id); actualCounts[row.disposition]++; counts[row.disposition]++;
      ordered.push({id: row.component_id, feature_sha256: row.candidate_feature_sha256});
      sourceCounts[row.source_relative_category] = (sourceCounts[row.source_relative_category] ?? 0)+1;
    }
    demand(JSON.stringify(actualCounts) === JSON.stringify(child.facts.counts), 'Child disposition totals changed');
    demand(footprintValueSha256(child.rows.map(row => ({id: row.component_id, feature_sha256: row.candidate_feature_sha256})))
      === child.facts.complete_ordered_roster_sha256, 'Child ordered inventory changed');
  }
  demand(ids.size === parent.components && footprintValueSha256(ordered) === parent.roster_sha256,
    'Incomplete or reordered complete parent inventory');
  return {version: 1, operation: 'complete-gap-inventory-join-v1', parent, components: ids.size, counts,
    source_relative_counts: sourceCounts, repair_authority: 'none; source-rule and selected-release stages remain required'};
}

export const GROUP_JOIN_VERSION = 'whole-gap-inventory-group-v1';
export const COMPLETE_JOIN_VERSION = 'complete-gap-inventory-join-v1';
// Groups retain the exact complete child ledgers as inverse sources. Their
// smaller ordered projection is sufficient for a separate complete-denominator
// join; neither projection replaces original geography or research evidence.
export function inventoryGroup(children, parent, {complete=false}={}) {
  demand(Array.isArray(children) && children.length>0 && children.length<=71, 'Missing bounded inventory children');
  const rows=[], seen=new Set(), counts=Object.fromEntries(DISPOSITIONS.map(key=>[key,0])), sourceCounts={};
  for(const [stage,child] of children.entries()){
    demand(child.facts && JSON.stringify(canonicalValue(child.facts.parent))===JSON.stringify(canonicalValue(parent))
      && child.rows.length===child.facts.components
      && child.facts.operation===(complete?GROUP_JOIN_VERSION:INVENTORY_VERSION), 'Foreign inventory child/parent');
    const actualCounts=Object.fromEntries(DISPOSITIONS.map(key=>[key,0])), actualSource={};
    for(const [ordinal,row] of child.rows.entries()){
      demand(typeof row.component_id==='string' && !seen.has(row.component_id) && hex(row.candidate_feature_sha256)
        && DISPOSITIONS.includes(row.disposition) && categories.has(row.source_relative_category), 'Duplicate or invalid inventory row');
      seen.add(row.component_id);counts[row.disposition]++;actualCounts[row.disposition]++;
      sourceCounts[row.source_relative_category]=(sourceCounts[row.source_relative_category]??0)+1;
      actualSource[row.source_relative_category]=(actualSource[row.source_relative_category]??0)+1;
      rows.push({component_id:row.component_id,candidate_feature_sha256:row.candidate_feature_sha256,
        disposition:row.disposition,source_relative_category:row.source_relative_category,original_ledger:{stage,ordinal}});
    }
    demand(JSON.stringify(canonicalValue(actualCounts))===JSON.stringify(canonicalValue(child.facts.counts))
      && JSON.stringify(canonicalValue(actualSource))===JSON.stringify(canonicalValue(child.facts.source_relative_counts))
      && footprintValueSha256(child.rows.map(row=>({id:row.component_id,feature_sha256:row.candidate_feature_sha256})))
        ===child.facts.complete_ordered_roster_sha256, 'Child inventory counts/ordered roster changed');
  }
  const roster=footprintValueSha256(rows.map(row=>({id:row.component_id,feature_sha256:row.candidate_feature_sha256})));
  demand(rows.length<=parent.components && (!complete || rows.length===parent.components && roster===parent.roster_sha256),
    'Incomplete or reordered complete parent inventory');
  return {rows,facts:{version:1,operation:complete?COMPLETE_JOIN_VERSION:GROUP_JOIN_VERSION,parent,components:rows.length,
    counts,source_relative_counts:sourceCounts,complete_ordered_roster_sha256:roster,
    repair_authority:'none; full source-rule and selected-release gates remain required',
    limits:['Complete child ledger bodies and original research files remain inverse sources; projections do not replace geography.',
      'Counts distinguish prior accepted repairs from new assignments; provisional source categories are not source approval.']}};
}
export function restoreGroupedInventoryRow(row, children) {
  const inverse=row?.original_ledger;
  demand(Number.isSafeInteger(inverse?.stage) && inverse.stage>=0 && Number.isSafeInteger(inverse.ordinal) && inverse.ordinal>=0,
    'Missing complete ledger inverse');
  const original=children[inverse.stage]?.rows?.[inverse.ordinal];
  demand(original && ['component_id','candidate_feature_sha256','disposition','source_relative_category'].every(key=>original[key]===row[key]),
    'Grouped inventory inverse changed');
  return original;
}

function pinCost(pin) {
  if(pin?.kind === 'completed-inventory-body'){
    demand(safe(pin.path) && /^\.cache\/native-grid-candidates\/[A-Za-z0-9_-]+\/(publication\.json|facts\.json|inventory\.jsonl\.gz)$/.test(pin.path)
      && pin.mode==='100644' && hex(pin.sha256), 'Invalid complete inventory body');
  } else if(pin?.kind === 'original-report-product'){
    demand(safe(pin.path) && pin.path.startsWith('.cache/additive-native-gap-repair/') && pin.mode === '100644'
      && hex(pin.report_sha256) && hex(pin.sha256) && Number.isSafeInteger(pin.uncompressed_bytes)
      && hex(pin.uncompressed_sha256) && /^components-[0-9]{3}\.jsonl\.gz$/.test(pin.original_product_path), 'Invalid whole report product binding');
  } else demand(/^[a-f0-9]{40}$/.test(pin?.commit ?? '') && safe(pin.path) && ['100644','100755'].includes(pin.mode)
    && /^[a-f0-9]{40}$/.test(pin.blob ?? '') && hex(pin.sha256), 'Missing whole immutable input descriptor');
  demand(Number.isSafeInteger(pin.bytes) && pin.bytes >= 0 && pin.bytes <= 32*1024*1024, 'Ordinary input exceeds cap');
  if (pin.uncompressed_bytes !== undefined) demand(Number.isSafeInteger(pin.uncompressed_bytes)
    && pin.uncompressed_bytes >= 0 && pin.uncompressed_bytes <= 32*1024*1024 && hex(pin.uncompressed_sha256), 'Decoded whole input exceeds cap');
  return [{bytes: pin.bytes}, ...(pin.uncompressed_bytes === undefined ? [] : [{bytes:pin.uncompressed_bytes}])];
}
function readPin(repo, pin) {
  pinCost(pin);
  if(pin.kind === 'original-report-product' || pin.kind === 'completed-inventory-body'){
    const file=path.join(fs.realpathSync(repo),pin.path);
    let current=fs.realpathSync(repo);
    for(const part of pin.path.split('/')){
      current=path.join(current,part);const stat=fs.lstatSync(current);
      demand(!stat.isSymbolicLink() && (current===file?stat.isFile():stat.isDirectory()) && fs.realpathSync(current)===current, 'Nonordinary original product path');
    }
    const fd=fs.openSync(file,'r');
    try{
      const before=fs.fstatSync(fd);demand(before.size===pin.bytes && (before.mode&0o777)===0o644, 'Original product mode/size drift');
      const raw=fs.readFileSync(fd),after=fs.fstatSync(fd);
      demand(before.ino===after.ino && before.dev===after.dev && before.size===after.size && sha(raw)===pin.sha256, 'Original product whole encoded drift');
      if(pin.uncompressed_bytes===undefined)return raw;
      const decoded=gunzipSync(raw,{maxOutputLength:pin.uncompressed_bytes+1});
      demand(decoded.length===pin.uncompressed_bytes && sha(decoded)===pin.uncompressed_sha256, 'Original product whole decoded drift');
      return decoded;
    }finally{fs.closeSync(fd);}
  }
  const tree = execFileSync('git',['-C',repo,'ls-tree','-z',pin.commit,'--',pin.path],{encoding:'utf8'});
  demand(tree === `${pin.mode} blob ${pin.blob}\t${pin.path}\0`, 'Immutable input mode/blob differs');
  const bytes = Number(execFileSync('git',['-C',repo,'cat-file','-s',pin.blob],{encoding:'utf8'}));
  demand(bytes === pin.bytes, 'Immutable input length differs');
  const raw = execFileSync('git',['-C',repo,'cat-file','blob',pin.blob],{maxBuffer:32*1024*1024});
  demand(sha(raw) === pin.sha256, 'Whole encoded input changed');
  if (pin.uncompressed_bytes === undefined) return raw;
  const decoded = gunzipSync(raw,{maxOutputLength:pin.uncompressed_bytes+1});
  demand(decoded.length === pin.uncompressed_bytes && sha(decoded) === pin.uncompressed_sha256, 'Whole decoded input changed');
  return decoded;
}
// The independent request names immutable current-selection and accepted
// predecessor bodies. Every complete body is admitted and authenticated here;
// no cached reconciliation boolean or raw historical geography is authority.
export function readBaselineResolutions(repo, baseline) {
  demand(baseline.version===1 && Array.isArray(baseline.pins) && baseline.pins.length===12,
    'Missing full selected-bank reconciliation inputs');
  const bodies=new Map();
  for(const pin of baseline.pins){
    demand(pin.kind===undefined && !bodies.has(pin.path),'Foreign/duplicate baseline input');
    bodies.set(pin.path,{pin,raw:readPin(repo,pin)});
  }
  const get=name=>{const body=bodies.get(name);demand(body,'Missing selected baseline body');return body;};
  const value=name=>JSON.parse(get(name).raw);
  const selection=value('data/ownership-selection.json'), manifestBody=get(selection.manifest_path),manifest=JSON.parse(manifestBody.raw);
  demand(selection.sha256===manifestBody.pin.sha256 && selection.method===manifest.method
    && selection.release_id===manifest.geographic_release, 'Current selected bank/manifest binding changed');
  // Pointer bodies must also equal this actual executing checkout's immutable
  // selected state, not merely another branch with a coherent older selection.
  for(const name of ['data/ownership-selection.json',selection.manifest_path,'data/geographic-releases/current-manifest.json',
    'data/geographic-releases/releases-v8.json.gz','data/native-context-migration/manifest.json',
    'data/reference-migrations/eastern-two-gap-repair-20261006/index.json']){
    const pin=get(name).pin, tree=execFileSync('git',['-C',repo,'ls-tree','-z','HEAD','--',name],{encoding:'utf8'});
    demand(tree===`${pin.mode} blob ${pin.blob}\t${name}\0`,'Stale executing selected baseline');
  }
  const registration=verifiedCandidates.candidates[selection.sha256];
  demand(registration?.installation_approval===false && registration.role==='reviewed-exhaustive-native-rule-comparison',
    'Missing independently reviewed native selection');
  const receiptBody=get(registration.path);
  demand(receiptBody.pin.sha256===registration.sha256,'Native selection receipt registration changed');
  validateNativeSelectionReceipt(manifest,selection.sha256,JSON.parse(receiptBody.raw));
  const releasePointer=value('data/geographic-releases/current-manifest.json');
  const releasesBody=get('data/geographic-releases/'+releasePointer.path), releases=JSON.parse(releasesBody.raw);
  const release=releases.releases.find(row=>row.id===selection.release_id), migration=value('data/reference-migrations/eastern-two-gap-repair-20261006/index.json');
  demand(releasesBody.pin.sha256===releasePointer.sha256 && release?.footprints_sha256===manifest.footprints_sha256
    && release.hierarchy_sha256===manifest.hierarchy_sha256 && migration.activated===true && migration.history_transfer===false
    && migration.after_footprints_sha256===manifest.footprints_sha256
    && release.metadata.geometry_migration.history_transfer==='none'
    && release.metadata.physical_reference_correction.issue===1295, 'Selected release is not activated accepted correction');
  const nativeMigration=value('data/native-context-migration/manifest.json');
  demand(nativeMigration.successor_release_id===selection.release_id && nativeMigration.native_manifest.sha256===selection.sha256
    && nativeMigration.geometry_manifest.sha256===get('data/reference-migrations/eastern-two-gap-repair-20261006/index.json').pin.sha256,
    'Current native/source migration lineage differs');
  const index=value(baseline.canonical_index_path), part=get(baseline.canonical_first_part_path);
  const partSpec=index.parts[0];
  demand(partSpec.sha256===part.pin.sha256 && partSpec.bytes===part.pin.bytes && partSpec.offset===0,
    'Whole canonical transport/index binding changed');
  const pathmapSpec=index.files.find(pin=>pin.path==='canonical-path-map.json');
  demand(pathmapSpec?.offset===0 && pathmapSpec.bytes<=part.raw.length, 'Complete canonical path-map not present');
  const pathmapRaw=part.raw.subarray(0,pathmapSpec.bytes);
  demand(sha(pathmapRaw)===pathmapSpec.sha256,'Whole original canonical path-map changed');
  const pathmap=JSON.parse(pathmapRaw);
  demand(pathmap.logical_targets.length===302 && new Set(pathmap.logical_targets.map(pin=>pin.target)).size===302,
    'Incomplete current canonical path-map');
  const target=pathmap.logical_targets.find(pin=>pin.target==='data/geography/part-29.json'), bank=get(baseline.bank_path);
  demand(target?.mode==='100644' && target.bytes===bank.raw.length && target.sha256===sha(bank.raw)
    && target.sha256===baseline.expected_bank_decoded_sha256, 'Historical/foreign bank instead of selected canonical bank');
  const correctionsBody=get(baseline.corrections_path), corrections=JSON.parse(correctionsBody.raw);
  demand(correctionsBody.pin.commit===manifest.provenance.source_migration.proposal_commit,
    'Correction archive not original accepted scientific proposal');
  const features=JSON.parse(bank.raw).features;
  return selectedBankResolutions({features,corrections,selectedManifest:manifest,selectionReceipt:JSON.parse(receiptBody.raw),
    selectedManifestSha256:selection.sha256,bankDecodedSha256:target.sha256,expectedBankDecodedSha256:baseline.expected_bank_decoded_sha256});
}

function readInventoryChildren(repo, request, report, {project,runtimeSha,runtimeBytes}) {
  const complete=request.operation===COMPLETE_JOIN_VERSION, children=[], originalProducts=[];
  for(const [ordinal,expected] of request.children.entries()){
    demand(expected.ordinal===ordinal && expected.publication.kind==='completed-inventory-body'
      && expected.facts.kind==='completed-inventory-body' && expected.inventory.kind==='completed-inventory-body'
      && [expected.publication,expected.facts,expected.inventory].every(pin=>path.dirname(pin.path)===expected.destination),
      'Foreign or reordered child stage binding');
    pinCost(expected.request);
    const publication=JSON.parse(readPin(repo,expected.publication));
    demand(publication.version===1 && publication.complete===true
      && ['bytes','sha256'].every(key=>publication.facts[key]===expected.facts[key])
      && ['bytes','sha256','uncompressed_bytes','uncompressed_sha256'].every(key=>publication.inventory[key]===expected.inventory[key]),
      'Stale or partial inventory publication');
    const facts=JSON.parse(readPin(repo,expected.facts));
    demand(facts.execution_commit===expected.execution_commit && facts.operation===(complete?GROUP_JOIN_VERSION:INVENTORY_VERSION)
      && JSON.stringify(canonicalValue(facts.request))===JSON.stringify(canonicalValue(expected.request))
      && JSON.stringify(canonicalValue(facts.executed_code))===JSON.stringify(canonicalValue(project))
      && facts.runtime.bytes===runtimeBytes && facts.runtime.sha256===runtimeSha
      && JSON.stringify(canonicalValue(facts.installed_modules))===JSON.stringify(canonicalValue(request.installed_modules))
      && JSON.stringify(canonicalValue(facts.baseline))===JSON.stringify(canonicalValue(request.baseline??null))
      && JSON.stringify(canonicalValue(facts.input_descriptors))===JSON.stringify(canonicalValue(expected.input_descriptors)),
      'Child execution/request/runtime/whole input closure differs');
    const decoded=readPin(repo,expected.inventory), lines=decoded.toString('utf8').split('\n');
    demand(lines.pop()==='', 'Truncated complete child ledger');
    const rows=lines.map(line=>JSON.parse(line));children.push({rows,facts});
    const products=complete?facts.original_source_products:[facts.input_descriptors[1]];
    demand(Array.isArray(products) && products.length>0,'Missing original child source custody');
    for(const source of products){
      const original=report.products.find(pin=>pin.path===source.original_product_path);
      demand(source.kind==='original-report-product' && source.report_sha256===request.report.sha256 && original
        && ['bytes','sha256','uncompressed_bytes','uncompressed_sha256'].every(key=>original[key]===source[key]),
        'Foreign original containing source product');
      originalProducts.push(source);
    }
  }
  const productNames=originalProducts.map(pin=>pin.original_product_path);
  demand(new Set(productNames).size===productNames.length && productNames.every((name,i)=>i===0||name>productNames[i-1]),
    'Duplicate or reordered containing source shards');
  if(complete){
    const all=report.products.filter(pin=>/^components-[0-9]{3}\.jsonl\.gz$/.test(pin.path)).map(pin=>pin.path);
    demand(JSON.stringify(productNames)===JSON.stringify(all),'Missing original complete containing shard');
  }
  const result=inventoryGroup(children,request.parent,{complete});
  result.facts.original_source_products=originalProducts;
  result.facts.child_stages=request.children;
  return result;
}

export function restoreInventoryRow(alias, originalRows, originalSource, originalRecordBytes) {
  demand(JSON.stringify(canonicalValue(alias.original?.source)) === JSON.stringify(canonicalValue(originalSource))
    && Number.isSafeInteger(alias.original.ordinal), 'Wrong original row source');
  const original = originalRows[alias.original.ordinal];
  demand(original?.component_id === alias.component_id && Buffer.isBuffer(originalRecordBytes?.[alias.original.ordinal])
    && sha(originalRecordBytes[alias.original.ordinal]) === alias.original.whole_record_sha256
    && JSON.stringify(canonicalValue(JSON.parse(originalRecordBytes[alias.original.ordinal]))) === JSON.stringify(canonicalValue(original)),
    'Original whole record inverse failed');
  return original;
}

export function admitInventoryDestination(repo, destination) {
  const sourceRoot = fs.realpathSync(repo);
  demand(/^\.cache\/native-grid-candidates\/[A-Za-z0-9_-]+$/.test(destination), 'Fresh offline destination required');
  let current = sourceRoot;
  for (const part of destination.split('/')) {
    current = path.join(current,part); const entry = fs.lstatSync(current,{throwIfNoEntry:false});
    if(entry) demand(current !== path.join(sourceRoot,destination) && entry.isDirectory() && !entry.isSymbolicLink()
      && fs.realpathSync(current) === current, 'Output collision or symlink parent');
  }
  return sourceRoot;
}

function countySourcePremiseStage(repo,request) {
  const rule=request.source_rule,bodies=new Map();
  demand(rule?.profile==='retained-USA-ADM2-counties-2018'&&Array.isArray(rule.expected_ids)
    &&rule.expected_ids.length>0&&new Set(rule.expected_ids).size===rule.expected_ids.length,'Incomplete typed county scope');
  for(const pin of rule.inputs){demand(pin.kind===undefined&&!bodies.has(pin.path),'Duplicate county operand');bodies.set(pin.path,{pin,body:readPin(repo,pin)});}
  const get=name=>{const value=bodies.get(name);demand(value,'Missing complete county operand');return value;};
  const json=name=>JSON.parse(get(name).body),equal=(a,b)=>JSON.stringify(canonicalValue(a))===JSON.stringify(canonicalValue(b));
  const measurement=json(rule.cases_path),publication=json(rule.publication_path),operating=json(rule.operating_path);
  demand(publication.status==='complete'&&publication.outputs.some(pin=>pin.path===rule.cases_path
    &&pin.bytes===get(rule.cases_path).pin.bytes&&pin.sha256===get(rule.cases_path).pin.sha256),'County predecessor whole publication mismatch');
  demand(operating.exit_code===0&&operating.natural_terminal===true&&operating.owned_processes_absent_after_run===true
    &&operating.stop_reason===null&&operating.peak_sampled_group_rss_bytes<=operating.rss_cap_bytes,'Unqualified original county predecessor');
  const reported=JSON.parse(operating.stdout);
  demand(reported.published_outputs.some(pin=>pin.path===rule.cases_path&&pin.sha256===get(rule.cases_path).pin.sha256)
    &&reported.component_count===rule.expected_ids.length,'County operating receipt belongs to other output');
  demand(equal(measurement.assigned_scope.component_ids,rule.expected_ids)
    &&equal(measurement.cases.map(row=>row.component_id),rule.expected_ids),'Incomplete/reordered original county cases');
  // All original source files are consumed as whole authenticated bodies.
  for(const pin of measurement.inputs.files){const value=get(pin.path);demand(value.body.length===pin.bytes&&sha(value.body)===pin.sha256,'Original county input differs');}
  const admission=json(rule.admission_path);
  demand(admission.status==='PASS'&&admission.complete_phase_bytes<=admission.cap_bytes,'Original county source admission incomplete');
  demand(equal(rule.original_code,admission.project_code),'Incomplete original county execution-code roster');
  for(const pin of rule.original_code){const value=get(pin.path);demand(value.body.length===pin.bytes&&sha(value.body)===pin.sha256,'Original county code differs');}
  const candidates=json(rule.candidate_path).features,originalTargets=json(rule.original_targets_path).features;
  const raw=get(rule.records_path).body.toString('utf8').split('\n');demand(raw.pop()==='','Truncated original county row body');
  const records=raw.map(JSON.parse),context=[];
  const baselineIndexPin=request.baseline.pins.find(pin=>pin.path===request.baseline.canonical_index_path),baselinePartPin=request.baseline.pins.find(pin=>pin.path===request.baseline.canonical_first_part_path);
  demand(baselineIndexPin&&baselinePartPin,'Missing selected canonical source closure');
  const canonicalIndex=JSON.parse(readPin(repo,baselineIndexPin)),firstPart=readPin(repo,baselinePartPin),pathmap=canonicalIndex.files.find(pin=>pin.path==='canonical-path-map.json');
  demand(pathmap?.offset===0&&sha(firstPart.subarray(0,pathmap.bytes))===pathmap.sha256,'Selected source path-map drift');
  const actualMap=JSON.parse(firstPart.subarray(0,pathmap.bytes)),contextIndex=get(rule.context_index_path),indexBinding=actualMap.logical_targets.find(pin=>pin.target==='data/canonical-grid/eastern-v8/context-index.json');
  demand(indexBinding?.mode==='100644'&&indexBinding.bytes===contextIndex.body.length&&indexBinding.sha256===sha(contextIndex.body),'Context index is not selected canonical source');
  const parts=JSON.parse(contextIndex.body).parts;
  for(const name of rule.target_banks){const value=get(name),part=parts.find(pin=>pin.path==='context/'+name.split('/').at(-1));
    demand(part&&value.pin.bytes===part.bytes&&value.pin.sha256===part.sha256&&value.pin.uncompressed_bytes===part.decoded_bytes
      &&value.pin.uncompressed_sha256===part.decoded_sha256,'Foreign selected containing context');
    const rows=JSON.parse(value.body);demand(Array.isArray(rows)&&rows.length===part.owners
      &&rows.every((row,i)=>row.pixelIndex===part.first_owner+i),'Invalid complete target context');context.push(...rows);}
  const nativeReceipt=json(rule.native_receipt_path),nativeBody=get(rule.native_body_path).body,selected=nativeReceipt.selected_output;
  demand(nativeReceipt.status==='bytes-verified'&&selected.bytes===nativeBody.length&&selected.sha256===sha(nativeBody)
    &&equal(selected.record_order,measurement.assigned_scope.native_gshhg_record_ids),'Whole original native selection differs');
  let offset=0;const nativeHashes=new Map();
  for(const descriptor of selected.records){
    demand(descriptor.output_offset===offset&&descriptor.bytes===44+descriptor.header_int32[1]*8
      &&offset+descriptor.bytes<=nativeBody.length,'Incomplete/overlapping native record boundaries');
    const body=nativeBody.subarray(offset,offset+descriptor.bytes);
    demand(sha(body)===descriptor.sha256&&sha(body.subarray(44))===descriptor.coordinate_bytes_sha256
      &&descriptor.header_int32.every((value,i)=>body.readInt32BE(i*4)===value)
      &&descriptor.id===descriptor.header_int32[0]&&descriptor.level===(descriptor.header_int32[2]&255)
      &&!nativeHashes.has(descriptor.id),'Original whole native record/header changed');
    nativeHashes.set(descriptor.id,descriptor.sha256);offset+=descriptor.bytes;
  }
  demand(offset===nativeBody.length&&nativeHashes.size===measurement.assigned_scope.native_gshhg_record_count,'Native selected record omitted');
  for(const record of records)for(const query of record.query_relations)demand(nativeHashes.get(query.source_id)===query.source_record_sha256
    &&query.periodic_offset===0&&query.container_chain_issues.length===0,'Original native query/body differs');
  const neighbors=json(rule.neighbor_path).features,contact=json(rule.contact_path);
  demand(equal(neighbors.map(row=>row.id).sort(),measurement.assigned_scope.read_only_edge_neighbor_ids.slice().sort())
    &&equal(contact.all_contact_ids.slice().sort(),neighbors.map(row=>row.id).sort())
    &&contact.edge_ids_equal_all_contact_ids_for_this_family===true&&contact.full_family995_ids_unique===true,'Incomplete original contact authority');
  for(const old of neighbors){const rows=context.filter(row=>row.id===old.id);demand(rows.length===1
    &&rows[0].properties.parent_id===old.properties.parent_id&&wholePrimitivePointsetEqual(rows[0].geometry,old.geometry),'Original contact geometry changed in selected bank');}
  demand(candidates.length===rule.expected_ids.length&&records.length===rule.expected_ids.length
    &&new Set(candidates.map(row=>row.id)).size===candidates.length&&new Set(records.map(row=>row.component_id)).size===records.length,'Duplicate/missing county source rows');
  const rows=measurement.cases.map((sourceCase,ordinal)=>{
    const record=records.find(row=>row.component_id===sourceCase.component_id),candidate=candidates.find(row=>row.id===sourceCase.component_id);
    const old=originalTargets.find(row=>row.id===sourceCase.county_target.atlas_target_id),actual=context.filter(row=>row.id===old?.id);
    demand(record&&candidate&&old&&actual.length===1&&actual[0].properties.parent_id===old.properties.parent_id
      &&wholePrimitivePointsetEqual(actual[0].geometry,old.geometry),'Stale/foreign selected county target');
    const target={...old,geometry:actual[0].geometry,pixelIndex:actual[0].pixelIndex};
    const original=measurement.physical_relation_preservation.rows.find(row=>row.component_id===record.component_id);
    demand(original&&original.original_row_sha256===sha(Buffer.from(raw[records.indexOf(record)]+'\n'))
      &&original.relation_count===record.query_relations.length,'Original full county row boundary mismatch');
    const premises=retainedCountySourcePremises({record,candidate:candidate.geometry,sourceCase,sourceScope:measurement,target});
    return {...premises,pixelIndex:target.pixelIndex,disposition:premises.source_compatible?'awaiting-native-exclusion':'awaiting-evidence',
      candidate:candidate.geometry,target_geometry_sha256:footprintValueSha256(target.geometry),
      original_record:{source:get(rule.records_path).pin,ordinal:records.indexOf(record),row_sha256:original.original_row_sha256},
      source_case:{source:get(rule.cases_path).pin,ordinal,row_sha256:sha(canonical(sourceCase))}};
  });
  return {rows,facts:{version:1,operation:SOURCE_PREMISES_VERSION,source_profile:rule.profile,parent:request.parent,
    components:rows.length,source_compatible:rows.filter(row=>row.source_compatible).length,assigned_cells:0,source_rule:rule,
    source_limits:measurement.source_limits,limits:[...Object.entries(measurement.source_limits).map(([key,value])=>key+': '+value),'Retained 2018 ADM2 county and GSHHG source compatibility only; physical authority/date/shoreline remain unapproved.',
      'No cells assigned; complete selected native owner and combined-candidate exclusions remain required.']}};
}

function sourcePremiseStage(repo,request,report) {
  if(request.source_rule?.profile==='retained-USA-ADM2-counties-2018')return countySourcePremiseStage(repo,request);
  const rule=request.source_rule;
  demand(rule?.version===1&&Array.isArray(rule.inputs)&&rule.inputs.length===12&&Array.isArray(rule.expected_ids)
    &&rule.expected_ids.length>0&&new Set(rule.expected_ids).size===rule.expected_ids.length,'Incomplete independently frozen source-rule scope');
  const bodies=new Map();
  for(const pin of rule.inputs){demand(pin.kind===undefined&&!bodies.has(pin.path),'Foreign/duplicate source-rule input');bodies.set(pin.path,{pin,body:readPin(repo,pin)});}
  const get=name=>{const value=bodies.get(name);demand(value,'Missing complete source-rule body');return value;};
  const scope=JSON.parse(get(rule.cases_path).body),pilot=JSON.parse(get(rule.pilot_path).body);
  const review=JSON.parse(get(rule.review_path).body);
  demand(review.id===rule.review_comment_id&&sha(Buffer.from(review.body))===rule.review_body_sha256
    &&review.html_url===`https://github.com/ChengshuLi/WorldAtlas/issues/1520#issuecomment-${rule.review_comment_id}`,'Independent source-rule provenance differs');
  demand(Array.isArray(scope.results)&&scope.results.length===scope.component_count&&scope.results.length===rule.expected_ids.length
    &&JSON.stringify(scope.results.map(row=>row.component_id))===JSON.stringify(rule.expected_ids),'Missing/duplicate/reordered full source cases');
  const original=new Map();
  for(const source of rule.original_products){
    const {pin,body}=get(source.path),product=report.products.find(row=>row.path===source.original_product_path);
    demand(product&&product.bytes===pin.bytes&&product.sha256===pin.sha256&&product.uncompressed_bytes===pin.uncompressed_bytes
      &&product.uncompressed_sha256===pin.uncompressed_sha256,'Source-rule original product differs from independent complete report');
    const lines=body.toString('utf8').split('\n');demand(lines.pop()==='','Truncated whole original source-rule product');
    for(let ordinal=0;ordinal<lines.length;ordinal++){
      const row=JSON.parse(lines[ordinal]);if(!rule.expected_ids.includes(row.component_id))continue;
      demand(!original.has(row.component_id),'Duplicate original source-rule component');
      original.set(row.component_id,{row,alias:{source:pin,ordinal,row_sha256:sha(Buffer.from(lines[ordinal]+'\n'))}});
    }
  }
  demand(original.size===rule.expected_ids.length,'Missing complete original source-rule component');
  const bankPin=request.baseline.pins.find(pin=>pin.path===request.baseline.bank_path);
  demand(bankPin,'Missing selected full target bank');const bank=JSON.parse(readPin(repo,bankPin));
  demand(bank.type==='FeatureCollection'&&Array.isArray(bank.features),'Missing complete installed target bank');
  const targets=new Map();for(const feature of bank.features){demand(!targets.has(feature.id),'Duplicate installed target identity');targets.set(feature.id,feature);}
  const rows=scope.results.map(sourceCase=>{
    const record=original.get(sourceCase.component_id),target=targets.get(sourceCase.atlas_target_id);
    demand(target,'Source-rule target absent from authenticated installed bank');
    if(sourceCase.component_id===pilot.component_id)demand(JSON.stringify(canonicalValue(target))===JSON.stringify(canonicalValue(pilot.before)),
      'Pilot before image is stale against selected bank');
    const premises=retainedLandSourcePremises({record:record.row,candidate:sourceCase.candidate_geometry,sourceCase,sourceScope:scope,target});
    return {...premises,disposition:premises.source_compatible?'awaiting-native-exclusion':'awaiting-evidence',
      candidate:sourceCase.candidate_geometry,candidate_feature_sha256:record.row.candidate_feature_sha256,
      original_candidate_geometry_sha256:record.row.candidate_geometry_sha256,target_id:target.id,target_geometry_sha256:footprintValueSha256(target.geometry),
      original_record:record.alias,source_case:{source:get(rule.cases_path).pin,ordinal:scope.results.indexOf(sourceCase),row_sha256:sha(canonical(sourceCase))}};
  });
  return {rows,facts:{version:1,operation:SOURCE_PREMISES_VERSION,parent:request.parent,components:rows.length,
    source_compatible:rows.filter(row=>row.source_compatible).length,awaiting_native_exclusion:rows.filter(row=>row.source_compatible).length,
    assigned_cells:0,source_rule:rule,limits:['Derived complete authenticated predecessor source premises; no new physical authority approval.',
      'Current full native owner exclusion and explicit effective-release proof remain required. No cell assigned by this stage.']}};
}

// A detached, unactivated release proposal: whole predecessor source receipts
// and whole current owner containers are mandatory. No global recomputation.
function additiveProposalStage(repo,request) {
  const spec=request.additive,inputs=new Map();
  for(const pin of spec.inputs){demand(!inputs.has(pin.path),'Duplicate additive input');inputs.set(pin.path,{pin,body:readPin(repo,pin)});}
  const get=name=>{if(!inputs.has(name)){const pin=request.baseline.pins.find(pin=>pin.path===name);demand(pin,'Missing complete additive operand');inputs.set(name,{pin,body:readPin(repo,pin)});}return inputs.get(name);};
  const json=name=>JSON.parse(get(name).body),pub=json(spec.publication_path),facts=json(spec.facts_path),issued=json(spec.source_request_path),operating=json(spec.operating_path);
  const equal=(a,b)=>JSON.stringify(canonicalValue(a))===JSON.stringify(canonicalValue(b));
  demand(pub.complete===true&&pub.facts.bytes===get(spec.facts_path).pin.bytes&&pub.facts.sha256===get(spec.facts_path).pin.sha256
    &&['bytes','sha256','uncompressed_bytes','uncompressed_sha256'].every(key=>pub.inventory[key]===get(spec.inventory_path).pin[key]),'Incomplete/drifted source predecessor');
  demand(facts.operation===SOURCE_PREMISES_VERSION&&facts.execution_commit===spec.source_execution_commit
    &&equal(facts.request,get(spec.source_request_path).pin)&&equal(facts.executed_code,issued.executed_code)
    &&equal(facts.input_descriptors,[issued.report,...issued.source_rule.inputs,...issued.baseline.pins])
    &&equal(facts.runtime,spec.source_runtime)&&equal(facts.installed_modules,issued.installed_modules)
    &&equal(facts.parent,request.parent)&&equal(issued.baseline,request.baseline),'Wrong source predecessor closure/vintage');
  demand(operating.qualified===true&&operating.execution_commit===facts.execution_commit&&operating.exit?.code===0
    &&operating.exit.signal===null&&operating.owned_processes_remaining?.length===0&&operating.refusal===null
    &&operating.request_sha256===facts.request.sha256&&operating.destination===issued.destination,'Source predecessor lacks qualified operating proof');
  const lines=get(spec.inventory_path).body.toString('utf8').split('\n');demand(lines.pop()==='','Truncated source premise roster');
  const sourceRows=lines.map(line=>JSON.parse(line));
  demand(equal(sourceRows.map(row=>row.component_id),issued.source_rule.expected_ids)&&sourceRows.length===facts.components,'Omitted/foreign source premise');
  const selected=sourceRows.find(row=>row.component_id===spec.component_id);
  demand(selected?.source_compatible===true&&selected.disposition==='awaiting-native-exclusion','Candidate has no complete retained-land premises');
  const casePin=selected.source_case?.source;
  demand(casePin&&spec.inputs.some(pin=>equal(pin,casePin)),'Original complete source-case input omitted');
  const sourceCase=json(casePin.path).results[selected.source_case.ordinal];
  demand(sourceCase?.component_id===selected.component_id&&sha(canonical(sourceCase))===selected.source_case.row_sha256
    &&sourceCase.candidate_valid===true&&wholePrimitivePointsetEqual(sourceCase.candidate_geometry,selected.candidate),'Original candidate validity/whole case drift');
  const manifest=json(spec.manifest_path),bounds=json(spec.bounds_path),bank=json(request.baseline.bank_path);
  const baseReference={id:manifest.geographic_release,footprints_sha256:manifest.footprints_sha256,hierarchy_sha256:manifest.hierarchy_sha256};
  const target=bank.features.find(feature=>feature.id===selected.target_id),owner=bounds.find(row=>row.id===selected.target_id);
  demand(bounds.length===49625&&new Set(bounds.map(row=>row.id)).size===49625&&new Set(bounds.map(row=>row.index)).size===49625
    &&target&&owner&&target.properties.parent_id===owner.province_id&&footprintValueSha256(target.geometry)===selected.target_geometry_sha256,'Stale/foreign target or full owner roster');
  demand(equal(manifest.original_assets.bounds,spec.original_bounds)&&get(spec.bounds_path).pin.sha256===manifest.original_assets.bounds.sha256,'Bounds source is not selected native original roster');
  const latitudeBody=get(spec.latitudes_path).body;
  demand(latitudeBody.length===262166*8&&sha(latitudeBody)==='66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23','Changed literal native latitude rule');
  const latitudes=Float64Array.from({length:262166},(_,y)=>latitudeBody.readDoubleLE(y*8)),size=262166;
  const candidateIndex=nativeRuntimeIndex([{id:target.id,pixelIndex:owner.index,geometry:selected.candidate}]);
  const coordinates=polygonParts(selected.candidate).flat(2),max=Math.max(...coordinates.map(point=>point[1])),min=Math.min(...coordinates.map(point=>point[1]));
  const first=Math.max(0,latitudes.findIndex(value=>value<=max)-1),stop=latitudes.findIndex(value=>value<min),end=stop<0?size:Math.min(size,stop+1);
  demand(first>=0&&end>first&&end-first<=4096,'Candidate requires another bounded whole-row window');
  const native=nativePolygonIntervals(candidateIndex,{size,latitudes,rowStart:first,rowEnd:end}),containers=[];
  for(const body of spec.owner_parts){
    const descriptor=manifest.parts.find(part=>part.path===body.manifest_path),entry=get(body.path);
    demand(descriptor&&equal(descriptor,body.manifest_descriptor)&&descriptor.encoding==='byte-shuffle'
      &&entry.pin.sha256===descriptor.sha256&&entry.pin.bytes===descriptor.bytes,'Foreign current native owner container');
    const words=unshuffleOwnershipBytes(entry.body,descriptor.words);
    demand(words.byteLength===descriptor.decoded_bytes&&sha(Buffer.from(words.buffer))===descriptor.decoded_sha256,'Whole original native words changed');
    containers.push({descriptor,words});
  }
  const rowsContainer=containers.find(value=>value.descriptor.kind==='rows'&&value.descriptor.offset===0);
  demand(rowsContainer&&rowsContainer.words.length===size*2,'Complete current native row table required');
  const rows=[],oldOwnerRows=[];let cells=0;
  for(let y=first;y<end;y++){
    const offset=rowsContainer.words[y*2],count=rowsContainer.words[y*2+1],old=[];
    for(let n=offset;n<offset+count;n++){
      const source=containers.find(value=>value.descriptor.kind==='runs'&&n*2>=value.descriptor.offset&&n*2+1<value.descriptor.offset+value.words.length);
      demand(source,'Missing complete containing run asset');const i=n*2-source.descriptor.offset,a=source.words[i],b=source.words[i+1];
      old.push([a%2**19,b%2**19+1,Math.floor(a/2**19)+Math.floor(b/2**19)*2**13]);
    }
    let previous=0;for(const [start,end,id]of old){demand(start>=previous&&end>start&&end<=size&&id>0,'Corrupt native owner row');previous=end;}
    const runs=[];for(const span of native.rows.get(y)??[]){
      const start=span.start,end=span.end;demand(!old.some(run=>Math.max(start,run[0])<Math.min(end,run[1])),'Candidate native cell already assigned to an owner');
      runs.push([start,end,owner.index]);cells+=end-start;
    }
    if(runs.length)rows.push({y,runs});oldOwnerRows.push({y,complete_owner_intervals:old});
  }
  // Exact source/candidate addition remains meaningful even at zero native cells.
  const ruleSha=sha(canonical({version:2,source_rule_body_sha256:issued.source_rule.review_body_sha256,representation:'literal-base-or-complete-additions',native_method:manifest.method,executed_code:request.executed_code}));
  const ledger={version:1,kind:'native-additive-repair-ledger-v1',rule_sha256:ruleSha,base_reference:baseReference,parent_inventory:request.parent,
    scope_ids:sourceRows.map(row=>row.component_id).sort(),assigned_cells:cells,rows:sourceRows.map(row=>row.component_id===selected.component_id?
      {component_id:row.component_id,disposition:cells?'assigned':'zero-cell',target_id:target.id,pixelIndex:owner.index,
       base_geometry:target.geometry,base_geometry_sha256:footprintValueSha256(target.geometry),geometry:row.candidate,geometry_sha256:footprintValueSha256(row.candidate),
       source_receipt_sha256:get(spec.facts_path).pin.sha256,native_cells:cells}:
      {component_id:row.component_id,disposition:'awaiting-evidence',source_compatible:row.source_compatible,source_limits:row.limits}).sort((a,b)=>a.component_id.localeCompare(b.component_id))};
  const ledgerBody=canonical(ledger),ledgerSha=sha(ledgerBody),feature={...target,pixelIndex:owner.index,additiveFootprint:{version:1,kind:'retained-base-plus-additions',
    baseline_release_sha256:baseReference.footprints_sha256,base_geometry_sha256:footprintValueSha256(target.geometry),ledger_sha256:ledgerSha,rule_sha256:ruleSha,
    additions:[{component_id:selected.component_id,geometry:selected.candidate,geometry_sha256:footprintValueSha256(selected.candidate),source_receipt_sha256:get(spec.facts_path).pin.sha256}]}};
  const effectiveReference={...baseReference,id:'geography:additive:'+ledgerSha,footprints_sha256:additiveReleaseFootprintDigest(baseReference,[feature])};
  const patch={version:1,kind:'unassigned-native-cells-v1',base_reference:baseReference,effective_reference:effectiveReference,ledger_sha256:ledgerSha,rule_sha256:ruleSha,rows};
  const boundsPin=get(spec.bounds_path).pin,encodedBounds=readPin(repo,Object.fromEntries(Object.entries(boundsPin).filter(([key])=>!['uncompressed_bytes','uncompressed_sha256'].includes(key))));
  const patchBody=canonical(patch),asset=(name,body)=>({path:'additive-repairs/'+name,bytes:body.length,sha256:sha(body)});
  const release={reference_release:effectiveReference,additiveRelease:{version:1,kind:'retained-native-base-plus-delta-v1',base_reference:baseReference,effective_reference:effectiveReference,
    base_manifest:asset('base-native-manifest.json',get(spec.manifest_path).body),ledger:asset('ledger-add031.json',ledgerBody),patch:asset('patch-add031.json',patchBody),owner_roster:{...asset('owners-add031.json.gz',encodedBounds),encoding:'gzip',decoded_bytes:boundsPin.uncompressed_bytes,decoded_sha256:boundsPin.uncompressed_sha256}}};
  const assets=[{name:'base-native-manifest.json',body:get(spec.manifest_path).body},{name:'ledger-add031.json',body:ledgerBody},{name:'patch-add031.json',body:patchBody},{name:'feature.json',body:canonical(feature)},
    {name:'owners-add031.json.gz',body:encodedBounds,decoded_bytes:boundsPin.uncompressed_bytes,decoded_sha256:boundsPin.uncompressed_sha256},
    {name:'release-envelope.json',body:canonical(release)},{name:'owner-window.json',body:canonical(oldOwnerRows)}];
  return {rows:[{component_id:selected.component_id,target_id:target.id,native_cells:cells,effective_reference:effectiveReference,
      baseline_reference:baseReference,activation:false,source_authority_approved:false}],assets,
    facts:{version:1,operation:ADDITIVE_PROPOSAL_VERSION,parent:request.parent,component_id:selected.component_id,
      source_predecessor:spec,assigned_cells:cells,removed_cells:0,reassigned_cells:0,complete_owner_window:[first,end],
      retained_base_geometry_sha256:footprintValueSha256(target.geometry),effective_reference:effectiveReference,
      limits:['Unactivated source-supported retained-base-plus-addition proposal; not an OGC dissolved polygon or new physical authority approval.',
        'N2 strict two-repair selection must precede final current-bank rebind and activation.']}};
}

// Shared bounded producer: one source roster, one whole current asset closure,
// one symmetric batch decision and one sparse overlay. The base bank is literal.
function additiveBatchProposalStage(repo,request) {
  const spec=request.additive,inputs=new Map(),equal=(a,b)=>JSON.stringify(canonicalValue(a))===JSON.stringify(canonicalValue(b));
  for(const pin of spec.inputs){demand(!inputs.has(pin.path),'Duplicate batch operand');inputs.set(pin.path,{pin,body:readPin(repo,pin)});}
  const get=name=>{if(!inputs.has(name)){const pin=request.baseline.pins.find(pin=>pin.path===name);demand(pin,'Missing complete batch operand');inputs.set(name,{pin,body:readPin(repo,pin)});}return inputs.get(name);};
  const json=name=>JSON.parse(get(name).body),publication=json(spec.publication_path),facts=json(spec.facts_path),issued=json(spec.source_request_path),operating=json(spec.operating_path);
  demand(publication.complete===true&&publication.facts.bytes===get(spec.facts_path).pin.bytes&&publication.facts.sha256===get(spec.facts_path).pin.sha256
    &&['bytes','sha256','uncompressed_bytes','uncompressed_sha256'].every(key=>publication.inventory[key]===get(spec.inventory_path).pin[key]),'Incomplete batch source predecessor');
  demand(facts.operation===SOURCE_PREMISES_VERSION&&facts.source_profile==='retained-USA-ADM2-counties-2018'
    &&facts.execution_commit===spec.source_execution_commit&&equal(facts.request,get(spec.source_request_path).pin)
    &&equal(facts.executed_code,issued.executed_code)&&equal(facts.input_descriptors,[issued.report,...issued.source_rule.inputs,...issued.baseline.pins])
    &&equal(facts.runtime,spec.source_runtime)&&equal(facts.installed_modules,issued.installed_modules)
    &&equal(facts.parent,request.parent)&&equal(issued.baseline,request.baseline),'Batch predecessor closure/vintage differs');
  demand(operating.qualified===true&&operating.execution_commit===facts.execution_commit&&operating.exit?.code===0
    &&operating.exit.signal===null&&operating.owned_processes_remaining?.length===0&&operating.refusal===null
    &&operating.request_sha256===facts.request.sha256&&operating.destination===issued.destination,'Unqualified batch source execution');
  const lines=get(spec.inventory_path).body.toString('utf8').split('\n');demand(lines.pop()==='','Truncated full batch source roster');
  const sourceRows=lines.map(JSON.parse);
  demand(equal(sourceRows.map(row=>row.component_id),spec.scope_ids)&&equal(spec.scope_ids,issued.source_rule.expected_ids)
    &&sourceRows.length===facts.components,'Batch selection omitted/reordered a source candidate');
  const manifest=json(spec.manifest_path),bounds=json(spec.bounds_path),targets=new Map();
  for(const name of issued.source_rule.target_banks){demand(spec.inputs.some(pin=>equal(pin,issued.source_rule.inputs.find(source=>source.path===name))),'Batch containing context differs from source proof');const rows=json(name);demand(Array.isArray(rows),'Invalid complete selected context');
    for(const target of rows){demand(!targets.has(target.id),'Duplicate selected context identity');targets.set(target.id,target);}}
  demand(bounds.length===49625&&new Set(bounds.map(row=>row.id)).size===49625&&new Set(bounds.map(row=>row.index)).size===49625
    &&equal(manifest.original_assets.bounds,spec.original_bounds)&&get(spec.bounds_path).pin.sha256===manifest.original_assets.bounds.sha256,'Foreign selected native owner roster');
  const owners=new Map(bounds.map(row=>[row.id,row]));
  const latitudeBody=get(spec.latitudes_path).body,size=262166;
  demand(latitudeBody.length===size*8&&sha(latitudeBody)==='66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23','Changed native latitude rule');
  const latitudes=Float64Array.from({length:size},(_,y)=>latitudeBody.readDoubleLE(y*8)),candidates=[],wantedRows=new Set();
  for(const selected of sourceRows){
    const target=targets.get(selected.target_id),owner=owners.get(selected.target_id);
    demand(target&&owner&&target.pixelIndex===owner.index&&selected.pixelIndex===owner.index
      &&target.properties.parent_id===owner.province_id&&footprintValueSha256(target.geometry)===selected.target_geometry_sha256,'Stale batch target/owner join');
    const casePin=selected.source_case?.source;demand(casePin&&spec.inputs.some(pin=>equal(pin,casePin)),'Original full batch case omitted');
    const sourceCase=json(casePin.path).cases[selected.source_case.ordinal];
    demand(sourceCase?.component_id===selected.component_id&&sha(canonical(sourceCase))===selected.source_case.row_sha256,'Original batch case drift');
    if(!selected.source_compatible)continue;
    demand(sourceCase.geometry_validity.candidate.valid===true&&sourceCase.geometry_validity.candidate.empty===false,'Invalid original batch primitive');
    const coordinates=polygonParts(selected.candidate).flat(2),max=Math.max(...coordinates.map(point=>point[1])),min=Math.min(...coordinates.map(point=>point[1]));
    const first=Math.max(0,latitudes.findIndex(value=>value<=max)-1),stop=latitudes.findIndex(value=>value<min),end=stop<0?size:Math.min(size,stop+1);
    demand(first>=0&&end>first&&end-first<=4096,'Batch candidate requires another bounded row phase');
    const index=nativeRuntimeIndex([{id:target.id,pixelIndex:owner.index,geometry:selected.candidate}]);
    const native=nativePolygonIntervals(index,{size,latitudes,rowStart:first,rowEnd:end});
    const rows=[];for(let y=first;y<end;y++){wantedRows.add(y);rows.push({y,runs:(native.rows.get(y)??[]).map(span=>[span.start,span.end,owner.index])});}
    candidates.push({component_id:selected.component_id,target_id:target.id,pixelIndex:owner.index,row_start:first,row_end:end,rows});
  }
  const containers=[];
  for(const body of spec.owner_parts){const descriptor=manifest.parts.find(part=>part.path===body.manifest_path),entry=get(body.path);
    demand(descriptor&&equal(descriptor,body.manifest_descriptor)&&descriptor.encoding==='byte-shuffle'
      &&entry.pin.sha256===descriptor.sha256&&entry.pin.bytes===descriptor.bytes,'Foreign batch owner container');
    const words=unshuffleOwnershipBytes(entry.body,descriptor.words);
    demand(words.byteLength===descriptor.decoded_bytes&&sha(Buffer.from(words.buffer))===descriptor.decoded_sha256,'Whole batch native words changed');containers.push({descriptor,words});}
  const table=containers.find(value=>value.descriptor.kind==='rows'&&value.descriptor.offset===0);
  demand(table&&table.words.length===size*2,'Missing complete batch row table');const ownerRows=[];
  for(const y of [...wantedRows].sort((a,b)=>a-b)){const offset=table.words[y*2],count=table.words[y*2+1],runs=[];
    for(let n=offset;n<offset+count;n++){const source=containers.find(value=>value.descriptor.kind==='runs'&&n*2>=value.descriptor.offset&&n*2+1<value.descriptor.offset+value.words.length);
      demand(source,'Missing whole batch containing native asset');const i=n*2-source.descriptor.offset,a=source.words[i],b=source.words[i+1];
      runs.push([a%2**19,b%2**19+1,Math.floor(a/2**19)+Math.floor(b/2**19)*2**13]);}
    ownerRows.push({y,complete_owner_intervals:runs});}
  const measurement=json(issued.source_rule.cases_path),pairRows=measurement.candidate_pairwise_contacts;
  demand(Array.isArray(pairRows)&&pairRows.length===sourceRows.length*(sourceRows.length-1)/2,'Incomplete original continuous pair matrix');
  const seenPairs=new Set(),continuousConflicts=[],eligible=new Set(candidates.map(row=>row.component_id));
  for(const pair of pairRows){
    demand(spec.scope_ids.includes(pair.left_component_id)&&spec.scope_ids.includes(pair.right_component_id)
      &&pair.left_component_id!==pair.right_component_id&&pair.status==='measured'&&typeof pair.positive_area_overlap==='boolean'
      &&typeof pair.intersection_area_raw_square_degrees_exact==='number'&&pair.intersection_area_raw_square_degrees_exact>=0,
      'Foreign/invalid original continuous pair');
    const key=[pair.left_component_id,pair.right_component_id].sort().join('\n');demand(!seenPairs.has(key),'Duplicate original continuous pair');seenPairs.add(key);
    demand(pair.positive_area_overlap===(pair.intersection_area_raw_square_degrees_exact>0),'Continuous pair predicate/area differs');
    if(pair.positive_area_overlap&&eligible.has(pair.left_component_id)&&eligible.has(pair.right_component_id))continuousConflicts.push([pair.left_component_id,pair.right_component_id]);
  }
  const combined=combineNativeBatch({scopeIds:spec.scope_ids,sourceRows,candidates,ownerRows,continuousConflicts,size});
  const baseReference={id:manifest.geographic_release,footprints_sha256:manifest.footprints_sha256,hierarchy_sha256:manifest.hierarchy_sha256};
  const ruleSha=sha(canonical({version:3,source_profile:issued.source_rule.profile,source_rule:issued.source_rule,
    representation:'literal-base-or-complete-additions',native_method:manifest.method,executed_code:request.executed_code}));
  const receiptSha=get(spec.facts_path).pin.sha256;
  const ledgerRows=combined.decisions.map(row=>{
    if(!['assigned','zero-cell'].includes(row.disposition))return {component_id:row.component_id,disposition:'rejected',reason_kind:row.reason_kind,
      failed_premises:row.failed_premises,native_conflicts:row.native_conflicts??[],source_limits:row.limits,native_cells:0};
    const target=targets.get(row.target_id);return {component_id:row.component_id,disposition:row.disposition,target_id:row.target_id,pixelIndex:row.pixelIndex,
      base_geometry:target.geometry,base_geometry_sha256:footprintValueSha256(target.geometry),geometry:row.candidate,
      geometry_sha256:footprintValueSha256(row.candidate),source_receipt_sha256:receiptSha,native_cells:row.native_cells};});
  const ledger={version:1,kind:'native-additive-repair-ledger-v1',rule_sha256:ruleSha,base_reference:baseReference,parent_inventory:request.parent,
    scope_ids:spec.scope_ids,assigned_cells:combined.assigned_cells,rows:ledgerRows};
  const ledgerBody=canonical(ledger),ledgerSha=sha(ledgerBody),features=[];
  for(const targetId of [...new Set(ledgerRows.filter(row=>['assigned','zero-cell'].includes(row.disposition)).map(row=>row.target_id))].sort()){
    const target=targets.get(targetId),additions=ledgerRows.filter(row=>row.target_id===targetId).map(row=>({component_id:row.component_id,geometry:row.geometry,
      geometry_sha256:row.geometry_sha256,source_receipt_sha256:receiptSha}));
    features.push({...target,additiveFootprint:{version:1,kind:'retained-base-plus-additions',baseline_release_sha256:baseReference.footprints_sha256,
      base_geometry_sha256:footprintValueSha256(target.geometry),ledger_sha256:ledgerSha,rule_sha256:ruleSha,additions}});}
  const effectiveReference={...baseReference,id:'geography:additive:'+ledgerSha,footprints_sha256:additiveReleaseFootprintDigest(baseReference,features)};
  const patch={version:1,kind:'unassigned-native-cells-v1',base_reference:baseReference,effective_reference:effectiveReference,
    ledger_sha256:ledgerSha,rule_sha256:ruleSha,rows:combined.rows};
  const boundsPin=get(spec.bounds_path).pin,encodedBounds=readPin(repo,Object.fromEntries(Object.entries(boundsPin).filter(([key])=>!['uncompressed_bytes','uncompressed_sha256'].includes(key))));
  const asset=(name,body)=>({path:'additive-repairs/'+name,bytes:body.length,sha256:sha(body)}),patchBody=canonical(patch);
  const release={reference_release:effectiveReference,additiveRelease:{version:1,kind:'retained-native-base-plus-delta-v1',base_reference:baseReference,effective_reference:effectiveReference,
    base_manifest:asset('base-native-manifest.json',get(spec.manifest_path).body),ledger:asset('ledger-batch.json',ledgerBody),patch:asset('patch-batch.json',patchBody),
    owner_roster:{...asset('owners-batch.json.gz',encodedBounds),encoding:'gzip',decoded_bytes:boundsPin.uncompressed_bytes,decoded_sha256:boundsPin.uncompressed_sha256}}};
  const assets=[{name:'base-native-manifest.json',body:get(spec.manifest_path).body},{name:'ledger-batch.json',body:ledgerBody},{name:'patch-batch.json',body:patchBody},
    {name:'features.json',body:canonical(features)},{name:'owners-batch.json.gz',body:encodedBounds,decoded_bytes:boundsPin.uncompressed_bytes,decoded_sha256:boundsPin.uncompressed_sha256},
    {name:'release-envelope.json',body:canonical(release)},{name:'owner-window.json',body:canonical(ownerRows)},
    {name:'virtual-owner-window.json',body:canonical(combined.virtual_owner_rows)}];
  return {rows:combined.decisions.map(row=>({component_id:row.component_id,target_id:row.target_id,disposition:row.disposition,
      reason_kind:row.reason_kind,native_cells:row.native_cells,failed_premises:row.failed_premises,native_conflicts:row.native_conflicts??[],activation:false})),assets,
    facts:{version:1,operation:ADDITIVE_BATCH_PROPOSAL_VERSION,parent:request.parent,components:sourceRows.length,
      source_predecessor:spec,assigned_cells:combined.assigned_cells,assigned_components:combined.assigned_components,zero_cell_components:combined.zero_cell_components,
      source_exceptions:combined.source_exceptions,native_conflicts:combined.native_conflicts,
      candidate_cell_contributions:combined.candidate_cell_contributions,shared_same_owner_cells:combined.shared_same_owner_cells,
      removed_cells:0,reassigned_cells:0,complete_owner_rows:ownerRows.length,effective_reference:effectiveReference,
      limits:['Unactivated source-compatible batch; no new physical authority or current shoreline approval.',
        'Literal original native word layout retained; combined virtual intervals conserve all old owners.',
        'N2 selection and actual current-bank rebind required before activation.']}};
}

// One genuine detached whole-shard acquisition per invocation. The parent
// report supplies the complete denominator; an independently frozen scope
// supplies exact selected IDs/ordered feature hashes. No all-world JSON lives
// in this process. Parent joining is a subsequent bounded custody operation.
export function inventoryCommand({repo, commit, requestPin, destination}) {
  requirePlainExecution();
  const sourceRoot = admitInventoryDestination(repo,destination);
  demand(execFileSync('git',['-C',sourceRoot,'rev-parse','HEAD'],{encoding:'utf8'}).trim() === commit,
    'Executing immutable head differs');
  const runtimeStat = fs.lstatSync(process.execPath);
  demand(runtimeStat.isFile() && !runtimeStat.isSymbolicLink(), 'Installed runtime must be an ordinary whole executable');
  const codeNames = ['package.json','scripts/additive-gap-repair.mjs','src/effective-footprint.js',
    'scripts/native-ownership/native-preparation-guards.mjs','src/native-runtime.js',
    'scripts/native-ownership/compile-native-ownership.mjs','src/native-grid.js','src/ownership-codec.js','scripts/audit-grid-intervals.mjs',
    'scripts/native-ownership/require-verified-selection.mjs','scripts/native-ownership/read-pinned-build-file.mjs',
    'scripts/native-ownership/verified-candidates.json','scripts/evidence-quality.mjs','src/ownership-method.js',
    'node_modules/@noble/hashes/package.json'];
  const projectNames = codeNames.filter(name=>!name.startsWith('node_modules/')).concat('package-lock.json');
  const projectSizes = projectNames.map(name=>({bytes:fs.lstatSync(path.join(sourceRoot,name)).size}));
  candidateBudget([...projectSizes,...pinCost(requestPin)],{reserveBytes:runtimeStat.size+131072});
  const project = committedPreparationFiles(sourceRoot,commit,projectNames);
  const requestBudget = candidateBudget([...project, ...pinCost(requestPin)],{reserveBytes:runtimeStat.size+131072});
  const request = JSON.parse(readPin(sourceRoot,requestPin));
  demand(request.version === 1 && [INVENTORY_VERSION,GROUP_JOIN_VERSION,COMPLETE_JOIN_VERSION,SOURCE_PREMISES_VERSION,ADDITIVE_PROPOSAL_VERSION,ADDITIVE_BATCH_PROPOSAL_VERSION].includes(request.operation)
    && JSON.stringify(canonicalValue(request.executed_code)) === JSON.stringify(canonicalValue(project)),
    'Foreign request operation/head');
  demand(typeof destination === 'string' && destination === request.destination
    && (request.operation!==INVENTORY_VERSION || Array.isArray(request.expected_ids) || request.scope === 'whole-original-report-shard'), 'Foreign output/scope');
  const outputReserve = request.output_reserve;
  demand(Number.isSafeInteger(outputReserve) && outputReserve >= 131072 && outputReserve <= 96*1024*1024, 'Explicit output reserve required');
  const dependencyNames = ['package.json','sha2.js','_md.js','_u64.js','utils.js'].map(name=>'node_modules/@noble/hashes/'+name);
  demand(Array.isArray(request.installed_modules) && request.installed_modules.length === dependencyNames.length
    && request.installed_modules.every((pin,i)=>pin.path === dependencyNames[i] && hex(pin.sha256)
      && Number.isSafeInteger(pin.bytes) && pin.bytes <= 32*1024*1024), 'Complete actual installed import closure required');
  const verifyModules = () => request.installed_modules.forEach(pin=>{
    const file = path.join(sourceRoot,pin.path), stat = fs.lstatSync(file);
    demand(stat.isFile() && !stat.isSymbolicLink() && fs.realpathSync(file) === file && stat.size === pin.bytes && sha(fs.readFileSync(file)) === pin.sha256,
      'Actual installed module drift');
  });
  const stagePins=[ADDITIVE_PROPOSAL_VERSION,ADDITIVE_BATCH_PROPOSAL_VERSION].includes(request.operation)?request.additive?.inputs:request.operation===SOURCE_PREMISES_VERSION?request.source_rule?.inputs:request.operation===INVENTORY_VERSION?[request.source]:request.children?.flatMap(child=>[child.publication,child.facts,child.inventory]);
  demand(Array.isArray(stagePins) && stagePins.length>0 && stagePins.length<=213, 'Missing complete child body roster');
  const baselinePins=[INVENTORY_VERSION,SOURCE_PREMISES_VERSION,ADDITIVE_PROPOSAL_VERSION,ADDITIVE_BATCH_PROPOSAL_VERSION].includes(request.operation)?(request.baseline?.pins??[]):[];
  const inputs = [...project,...request.installed_modules,...pinCost(requestPin),...pinCost(request.report),...stagePins.flatMap(pinCost),...baselinePins.flatMap(pinCost)];
  const budget = candidateBudget(inputs,{reserveBytes:runtimeStat.size+outputReserve+131072});
  const runtimeRead=()=>{
    const before=fs.lstatSync(process.execPath);
    demand(before.isFile() && !before.isSymbolicLink() && before.size===runtimeStat.size
      && before.ino===runtimeStat.ino && before.dev===runtimeStat.dev && before.mode===runtimeStat.mode,'Installed runtime descriptor drift');
    const raw=fs.readFileSync(process.execPath),after=fs.lstatSync(process.execPath);
    demand(raw.length===runtimeStat.size && after.size===before.size && after.ino===before.ino
      && after.dev===before.dev && after.mode===before.mode,'Installed runtime whole read drift');
    return sha(raw);
  };
  const runtimeSha=runtimeRead();
  verifyModules();
  demand(requestPin.kind === undefined && request.report.kind === undefined, 'Report/request must be independently immutable Git bodies');
  const report = JSON.parse(readPin(sourceRoot,request.report));
  if(request.operation===INVENTORY_VERSION && request.source.kind === 'original-report-product')demand(request.source.report_sha256 === request.report.sha256
    && request.source.original_product_path === request.original_product_path, 'Foreign report-product source authority');
  demand(request.parent.report_sha256 === request.report.sha256 && request.parent.components === report.component_count
    && request.parent.roster_sha256 === report.complete_roster_sha256, 'Wrong complete original report');
  const resolutions=baselinePins.length?readBaselineResolutions(sourceRoot,request.baseline):undefined;
  let result;
  if(request.operation===ADDITIVE_BATCH_PROPOSAL_VERSION){
    demand(resolutions,'Complete selected-bank reconciliation required');result=additiveBatchProposalStage(sourceRoot,request);
  }else if(request.operation===ADDITIVE_PROPOSAL_VERSION){
    demand(resolutions,'Complete selected-bank reconciliation required');result=additiveProposalStage(sourceRoot,request);
  }else if(request.operation===SOURCE_PREMISES_VERSION){
    demand(resolutions,'Complete selected-bank reconciliation required');
    result=sourcePremiseStage(sourceRoot,request,report);
  }else if(request.operation===INVENTORY_VERSION){
  demand(/^components-[0-9]{3}\.jsonl\.gz$/.test(request.original_product_path), 'Only complete original component shards accepted');
  const product = report.products.find(pin=>pin.path === request.original_product_path);
  demand(product && ['bytes','sha256','uncompressed_bytes','uncompressed_sha256'].every(key=>product[key] === request.source[key]),
    'Containing shard omitted from original report');
  const decoded = readPin(sourceRoot,request.source), lines = decoded.toString('utf8').split('\n');
  demand(lines.at(-1) === '', 'Truncated original JSONL source'); lines.pop();
  const sourceRows = lines.map(line=>JSON.parse(line));
  // The independently immutable report authenticates the entire containing
  // source; this mode cannot select or omit records within that whole source.
  const expectedIds = request.scope === 'whole-original-report-shard' ? sourceRows.map(row=>row.component_id) : request.expected_ids;
  const expectedRoster = request.scope === 'whole-original-report-shard'
    ? footprintValueSha256(sourceRows.map(row=>({id:row.component_id,feature_sha256:row.candidate_feature_sha256})))
    : request.expected_roster_sha256;
  result = inventoryRows(sourceRows,{source:request.source,parent:request.parent,expectedIds,
    expectedRosterSha256:expectedRoster,originalRecordBytes:lines.map(line=>Buffer.from(line+'\n')),resolutions});
  } else {
    result=readInventoryChildren(sourceRoot,request,report,{project,runtimeSha,runtimeBytes:runtimeStat.size});
  }
  const body = Buffer.concat(result.rows.map(canonical)), encoded = gzipSync(body,{mtime:0});
  const facts = canonical({...result.facts,execution_commit:commit,executed_code:project,request:requestPin,
    input_descriptors:[request.report,...stagePins,...baselinePins],baseline:request.baseline??null,runtime:{bytes:runtimeStat.size,sha256:runtimeSha},
    installed_modules:request.installed_modules, admission:budget.snapshot(), request_admission:requestBudget.snapshot()});
  demand(body.length <= 32*1024*1024 && encoded.length <= 32*1024*1024 && body.length+encoded.length+facts.length+(result.assets??[]).reduce((n,asset)=>n+asset.body.length+(asset.decoded_bytes??0),0) <= outputReserve,
    'Complete outputs exceed prospective reserve');
  demand(runtimeRead() === runtimeSha, 'Installed runtime drift');
  verifyModules();
  committedPreparationFiles(sourceRoot,commit,project.map(pin=>pin.path));
  for(const asset of result.assets??[])demand(/^[a-z0-9-]+\.json(?:\.gz)?$/.test(asset.name)&&asset.body.length<=32*1024*1024,'Foreign/oversized release asset');
  const output = createNativeCandidateOutput(sourceRoot,destination);
  fs.writeFileSync(path.join(output,'inventory.jsonl.gz'),encoded,{flag:'wx'});
  fs.writeFileSync(path.join(output,'facts.json'),facts,{flag:'wx'});
  for(const asset of result.assets??[]){demand(/^[a-z0-9-]+\.json(?:\.gz)?$/.test(asset.name)&&asset.body.length<=32*1024*1024,'Foreign/oversized release asset');fs.writeFileSync(path.join(output,asset.name),asset.body,{flag:'wx'});}
  const publication = {version:1,complete:true,...(result.assets?{assets:result.assets.map(asset=>({path:asset.name,bytes:asset.body.length,sha256:sha(asset.body),...(asset.decoded_bytes?{uncompressed_bytes:asset.decoded_bytes,uncompressed_sha256:asset.decoded_sha256}:{})}))}:{}),facts:{bytes:facts.length,sha256:sha(facts)},
    inventory:{bytes:encoded.length,sha256:sha(encoded),uncompressed_bytes:body.length,uncompressed_sha256:sha(body)}};
  fs.writeFileSync(path.join(output,'publication.json'),canonical(publication),{flag:'wx'});
  return publication;
}
if(process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [repo,commit,requestName,requestSha,destination] = process.argv.slice(2);
  demand(repo && /^[a-f0-9]{40}$/.test(commit ?? '') && safe(requestName) && hex(requestSha),
    'Usage: additive-gap-repair.mjs REPO EXECUTION_COMMIT REQUEST_GIT_PATH REQUEST_SHA256 DESTINATION');
  const tree = execFileSync('git',['-C',repo,'ls-tree','-z',commit,'--',requestName],{encoding:'utf8'});
  const match = /^([0-9]{6}) blob ([a-f0-9]{40})\t/.exec(tree);
  demand(match && tree.endsWith(requestName+'\0'), 'Missing immutable request');
  const bytes = Number(execFileSync('git',['-C',repo,'cat-file','-s',match[2]],{encoding:'utf8'}));
  const publication = inventoryCommand({repo,commit,destination,requestPin:{commit,path:requestName,mode:match[1],blob:match[2],bytes,sha256:requestSha}});
  process.stdout.write(JSON.stringify(publication)+'\n');
}
