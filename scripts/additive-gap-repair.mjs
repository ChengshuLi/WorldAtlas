import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync, gzipSync} from 'node:zlib';
import {validateNativeSelectionReceipt} from './native-ownership/require-verified-selection.mjs';
import verifiedCandidates from './native-ownership/verified-candidates.json' with {type:'json'};
import {canonicalValue, footprintValueSha256, polygonParts} from '../src/effective-footprint.js';
import {candidateBudget, committedPreparationFiles, createNativeCandidateOutput, requirePlainExecution} from './native-ownership/native-preparation-guards.mjs';

export const SOURCE_PREMISES_VERSION='retained-land-source-premises-v1';
export const INVENTORY_VERSION = 'complete-source-relative-gap-inventory-v1';
export const DISPOSITIONS = ['eligible', 'assigned', 'zero-cell', 'already-resolved', 'rejected', 'awaiting-evidence'];
const categories = new Set(['mapped-land-support', 'mapped-inland-water-support', 'mixed-source-support', 'outside-mapped-L1-context', 'unknown']);
const sha = raw => createHash('sha256').update(raw).digest('hex');
const canonical = value => Buffer.from(JSON.stringify(canonicalValue(value)) + '\n');
const hex = value => /^[a-f0-9]{64}$/.test(value ?? '');
function demand(value, message) { if (!value) throw Error(message); }
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

function sourcePremiseStage(repo,request,report) {
  const rule=request.source_rule;
  demand(rule?.version===1&&Array.isArray(rule.inputs)&&rule.inputs.length===8&&Array.isArray(rule.expected_ids)
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
    'scripts/native-ownership/compile-native-ownership.mjs','src/native-grid.js','scripts/audit-grid-intervals.mjs',
    'scripts/native-ownership/require-verified-selection.mjs','scripts/native-ownership/read-pinned-build-file.mjs',
    'scripts/native-ownership/verified-candidates.json','scripts/evidence-quality.mjs','src/ownership-method.js',
    'node_modules/@noble/hashes/package.json'];
  const projectNames = codeNames.filter(name=>!name.startsWith('node_modules/')).concat('package-lock.json');
  const projectSizes = projectNames.map(name=>({bytes:fs.lstatSync(path.join(sourceRoot,name)).size}));
  candidateBudget([...projectSizes,...pinCost(requestPin)],{reserveBytes:runtimeStat.size+131072});
  const project = committedPreparationFiles(sourceRoot,commit,projectNames);
  const requestBudget = candidateBudget([...project, ...pinCost(requestPin)],{reserveBytes:runtimeStat.size+131072});
  const request = JSON.parse(readPin(sourceRoot,requestPin));
  demand(request.version === 1 && [INVENTORY_VERSION,GROUP_JOIN_VERSION,COMPLETE_JOIN_VERSION,SOURCE_PREMISES_VERSION].includes(request.operation)
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
  const stagePins=request.operation===SOURCE_PREMISES_VERSION?request.source_rule?.inputs:request.operation===INVENTORY_VERSION?[request.source]:request.children?.flatMap(child=>[child.publication,child.facts,child.inventory]);
  demand(Array.isArray(stagePins) && stagePins.length>0 && stagePins.length<=213, 'Missing complete child body roster');
  const baselinePins=[INVENTORY_VERSION,SOURCE_PREMISES_VERSION].includes(request.operation)?(request.baseline?.pins??[]):[];
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
  if(request.operation===SOURCE_PREMISES_VERSION){
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
  demand(body.length <= 32*1024*1024 && encoded.length <= 32*1024*1024 && body.length+encoded.length+facts.length <= outputReserve,
    'Complete outputs exceed prospective reserve');
  demand(runtimeRead() === runtimeSha, 'Installed runtime drift');
  verifyModules();
  committedPreparationFiles(sourceRoot,commit,project.map(pin=>pin.path));
  const output = createNativeCandidateOutput(sourceRoot,destination);
  fs.writeFileSync(path.join(output,'inventory.jsonl.gz'),encoded,{flag:'wx'});
  fs.writeFileSync(path.join(output,'facts.json'),facts,{flag:'wx'});
  const publication = {version:1,complete:true,facts:{bytes:facts.length,sha256:sha(facts)},
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
