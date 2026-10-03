import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gzipSync,gunzipSync} from 'node:zlib';
import {footprintHash} from './check-prepared.mjs';
const tiers=['province','area','region','subcontinent','continent'];
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const encode=value=>Buffer.from(JSON.stringify(value)+'\n');
const read=file=>JSON.parse(file.endsWith('.gz')?gunzipSync(fs.readFileSync(file)):fs.readFileSync(file));
const same=(a,b)=>{const left=new Set(a),right=new Set(b);return left.size===a.length&&right.size===b.length&&left.size===right.size&&[...left].every(id=>right.has(id));};
const chain=(parent,groups)=>{const result=[];for(const tier of tiers){const row=groups.get(parent);if(row?.level!==tier)throw Error('Projection requires complete adjacent-tier chains');result.push(parent);parent=row.parent_id;}if(parent!==null)throw Error('Projection continent has a parent');return result;};
function snapshot(value){
 const units=Array.isArray(value.units)?value.units:[...(value.units instanceof Map?value.units:value.groups).values()],groups=new Map(units.map(row=>[row.id,row]));
 if(groups.size!==units.length)throw Error('Projection contains duplicate groups');
 const rows=value.features.map(feature=>{if(feature.id!==feature.properties?.id||!feature.geometry)throw Error('Projection contains invalid location identity');const p=feature.properties,parent_chain=chain(p.parent_id,groups);return {id:feature.id,name:p.name,parent_id:p.parent_id,parent_chain,owner:p.reference_owner,continent:groups.get(parent_chain.at(-1)).name,region_id:parent_chain[2],source_id:p.metadata?.source_id??null,source_year:p.metadata?.reference_year??null,status:'open',semantic_status:'open'};});
 if(new Set(rows.map(row=>row.id)).size!==rows.length)throw Error('Projection contains duplicate locations');
 const members=new Map(units.map(row=>[row.id,[]])),children=new Map(units.map(row=>[row.id,[]]));
 for(const row of units)if(row.parent_id!==null){if(!children.has(row.parent_id))throw Error('Projection has orphan groups');children.get(row.parent_id).push(row.id);}
 for(const row of rows){children.get(row.parent_id).push(row.id);for(const id of row.parent_chain)members.get(id).push(row.id);}
 const projectedGroups=units.map(row=>({...row,children:children.get(row.id).sort(),member_location_ids:members.get(row.id).sort(),descendant_location_count:members.get(row.id).length,status:'open',semantic_status:'pending',branch_semantic_status:'open',checks:{complete_membership:true,boundary_review:'open',child_semantic_review:'pending'}}));
 if(projectedGroups.some(row=>row.descendant_location_count===0))throw Error('Projection has an empty active group');
 return {units,groups,rows,projectedGroups};
}
const HEX=/^[a-f0-9]{64}$/;
const distinct=ids=>Array.isArray(ids)&&ids.every(id=>typeof id==='string'&&id)&&new Set(ids).size===ids.length;
const reference=row=>({id:row.id,name:row.name,parent_id:row.parent_id,owner:row.owner});
/** Read immutable predecessor projections without flattening distinct migrations. */
export function loadProjectionPredecessors({data,projection}){
 const root=path.dirname(path.resolve(data)),result=[],seen=new Set();let current=projection;
 while(current.predecessor_files?.['data/macro-foundation/current-membership-projection.json.gz']){
  const entry=current.predecessor_files['data/macro-foundation/current-membership-projection.json.gz'],file=path.resolve(root,entry.archive_path);
  if(!file.startsWith(root+path.sep)||entry.compression!=='gzip'||seen.has(entry.original_sha256))throw Error('Unsafe or cyclic projection predecessor archive');
  const archive=fs.readFileSync(file);if(sha(archive)!==entry.archive_sha256)throw Error('Projection predecessor archive bytes changed');
  const raw=gunzipSync(archive);if(sha(raw)!==entry.original_sha256)throw Error('Projection predecessor archive bytes changed');
  const prior=JSON.parse(gunzipSync(raw));
  if(['hierarchy_sha256','location_index_sha256','footprints_sha256'].some(key=>current.before_pins?.[key]!==prior.current_pins?.[key]))throw Error('Projection predecessor pins do not join the next migration');
  if(current.geometry_proof?.predecessor_reference_context?.source_projection_sha256&&current.geometry_proof.predecessor_reference_context.source_projection_sha256!==entry.original_sha256)throw Error('Projection predecessor reference archive differs');
  seen.add(entry.original_sha256);result.push(prior);current=prior;
 }
 return result;
}
/** Raw source/footprint checks happen before any open projection is emitted. */
export async function resolveProjectionGeometry({before,after,geometryProofs,sourceReceipt}){
 if(!geometryProofs&&!sourceReceipt)return null;
 if(!geometryProofs||!sourceReceipt)throw Error('Geometry projection requires both pinned proof descriptor and compound source receipt');
 const {verifySourceGeometry}=await import('./install-reviewed-geography.mjs'),prior=snapshot(before),current=snapshot(after),beforeFootprints=footprintHash(before.features),afterFootprints=footprintHash(after.features);
 if(before.proof?.footprints_sha256!==beforeFootprints||after.proof?.footprints_sha256!==afterFootprints)throw Error('Geometry projection footprint pins differ from supplied shapes');
 const receipt=read(sourceReceipt);if(receipt.before_footprints_sha256!==beforeFootprints||receipt.after_footprints_sha256!==afterFootprints||receipt.geometry_stage_validated!==true||![false,0].includes(receipt.historical_claims_transferred))throw Error('Geometry projection compound receipt is stale or transfers history');
 const validated=verifySourceGeometry({geometryProofs:path.resolve(geometryProofs),sourceReceipt:path.resolve(sourceReceipt)},{features:before.features,units:prior.units,ids:new Set(prior.rows.map(row=>row.id)),footprints:beforeFootprints,hierarchy:before.proof.hierarchy_sha256},{features:after.features,units:current.units,ids:new Set(current.rows.map(row=>row.id)),footprints:afterFootprints},receipt),base=path.dirname(path.resolve(geometryProofs));
 const chain=validated.chain,changed=[...chain.changedIds].sort(),removed=[...chain.retiredIds].sort(),added=[...chain.addedIds].sort(),oldRows=new Map(prior.rows.map(row=>[row.id,row])),oldFeatures=new Map(before.features.map(row=>[row.id,row]));
 const manifests=chain.proofs.map(p=>({path:path.relative(base,p.manifestFile),sha256:p.manifest_sha256,receipt_sha256:p.receipt_sha256,before_footprints_sha256:p.receipt.before_footprints_sha256,after_footprints_sha256:p.receipt.after_footprints_sha256,changed_ids:[...p.changed].sort(),removed_ids:[...p.removed].sort(),added_ids:[...p.added].sort(),history_transfer:false}));
 const locations=chain.proofs.flatMap(p=>[...p.changed,...p.added].map(id=>({id,status:'source-assessed-open',semantic_status:'open',kind:p.added.has(id)?'source-backed-create':'source-backed-footprint-replacement',source_manifest_sha256:p.manifest_sha256,source_receipt_sha256:p.receipt_sha256,source_evidence:p.receipt.source_evidence,creation_proof:p.creationProofs.find(row=>row.location_id===id)??null,historical_attributes_assessed:false,regional_interior_approved:false})));
 const newGroups=current.units.filter(row=>!prior.groups.has(row.id));
 const groups=newGroups.map(row=>{const m=row.metadata??{};if(!/^https?:\/\//.test(m.source_url??'')||!(m.basis||m.source))throw Error('New projection group requires its sourced geographic role');return {id:row.id,status:'source-assessed-open',semantic_status:'open',source_url:m.source_url,basis:m.basis??m.source,source_context:m.source??null,source_hierarchy_manifest_sha256:chain.proofs.at(-1).manifest_sha256,regional_interior_approved:false};});
 return {version:1,method:'ordered-source-backed-geographic-migrations',descriptor_sha256:sha(fs.readFileSync(geometryProofs)),source_receipt_sha256:sha(fs.readFileSync(sourceReceipt)),before_footprints_sha256:beforeFootprints,after_footprints_sha256:afterFootprints,changed_ids:changed,removed_ids:removed,added_ids:added,manifests,metadata_receipts:validated.metadataFiles.map(file=>({path:path.relative(base,file),sha256:sha(fs.readFileSync(file)),reference_only:true,history_transfer:false})),created_group_ids:newGroups.map(row=>row.id).sort(),archived_location_references:[...changed,...removed].map(id=>({reference:reference(oldRows.get(id)),parsed_geometry_sha256:sha(Buffer.from(JSON.stringify(oldFeatures.get(id).geometry))),history_transfer:false})),source_assessments:{locations,groups},historical_claims_transferred:false,regional_interiors_approved:false};
}
function validateProjectionGeometry(projection,baselineLocations,locations){
 const proof=projection?.geometry_proof;if(!proof)return null;
 if(proof.version!==1||proof.method!=='ordered-source-backed-geographic-migrations'||proof.historical_claims_transferred!==false||proof.regional_interiors_approved!==false||!HEX.test(proof.descriptor_sha256??'')||!HEX.test(proof.source_receipt_sha256??'')||proof.before_footprints_sha256!==projection.before_pins?.footprints_sha256||proof.after_footprints_sha256!==projection.current_pins?.footprints_sha256||!distinct(proof.changed_ids)||!distinct(proof.removed_ids)||!distinct(proof.added_ids)||!distinct(proof.created_group_ids)||!Array.isArray(proof.manifests)||!proof.manifests.length)throw Error('Invalid projection geometry proof contract');
 const touched=[...proof.changed_ids,...proof.removed_ids,...proof.added_ids];if(!distinct(touched)||projection.geometry_changes!==touched.length)throw Error('Projection geometry dispositions are not exhaustive');
 let previous=proof.before_footprints_sha256;const changed=[],removed=[],added=[];
 for(const manifest of proof.manifests){if(!HEX.test(manifest.sha256??'')||!HEX.test(manifest.receipt_sha256??'')||manifest.history_transfer!==false||manifest.before_footprints_sha256!==previous||!HEX.test(manifest.after_footprints_sha256??'')||!distinct(manifest.changed_ids)||!distinct(manifest.removed_ids)||!distinct(manifest.added_ids))throw Error('Projection geometry manifests are reordered, unpinned or transfer history');previous=manifest.after_footprints_sha256;changed.push(...manifest.changed_ids);removed.push(...manifest.removed_ids);added.push(...manifest.added_ids);}
 if(previous!==proof.after_footprints_sha256||!same([...new Set(changed)],proof.changed_ids)||!same([...new Set(removed)],proof.removed_ids)||!same([...new Set(added)],proof.added_ids))throw Error('Projection geometry lineage does not exhaust exact changes');
 if(baselineLocations){const before=new Map(baselineLocations.map(row=>[row.id,row])),now=new Set(locations.map(row=>row.id));if(!same(locations.map(row=>row.id),[...before.keys()].filter(id=>!proof.removed_ids.includes(id)).concat(proof.added_ids))||proof.changed_ids.some(id=>!before.has(id)||!now.has(id))||proof.added_ids.some(id=>before.has(id))||proof.removed_ids.some(id=>!before.has(id)||now.has(id)))throw Error('Projection geometry crosswalk loses or invents current identities');
  if(!Array.isArray(proof.archived_location_references)||!same(proof.archived_location_references.map(row=>row.reference?.id),proof.changed_ids.concat(proof.removed_ids))||proof.archived_location_references.some(row=>row.history_transfer!==false||!HEX.test(row.parsed_geometry_sha256??'')||JSON.stringify(row.reference)!==JSON.stringify(reference((proof.predecessor_reference_context?.locations??baselineLocations).find(original=>original.id===row.reference.id)))))throw Error('Projection alters original location reference/history context');
 }
 if(proof.predecessor_reference_context){const context=proof.predecessor_reference_context,archive=projection.predecessor_files?.['data/macro-foundation/current-membership-projection.json.gz'];if(!HEX.test(context.source_projection_sha256??'')||archive?.original_sha256!==context.source_projection_sha256||!Array.isArray(context.locations)||!same(context.locations.map(row=>row.id),proof.changed_ids.concat(proof.removed_ids)))throw Error('Projection predecessor reference context is not retained and pinned');}
 const assessments=proof.source_assessments;if(!assessments||!Array.isArray(assessments.locations)||!Array.isArray(assessments.groups)||!same(assessments.locations.map(row=>row.id),proof.changed_ids.concat(proof.added_ids))||!same(assessments.groups.map(row=>row.id),proof.created_group_ids))throw Error('Projection omits supported source assessments');
 for(const row of [...assessments.locations,...assessments.groups]){if(row.status!=='source-assessed-open'||row.semantic_status!=='open'||row.regional_interior_approved!==false)throw Error('Source assessment silently approves geography');if(row.source_evidence?.some(e=>!/^https?:\/\//.test(e.url??'')||!HEX.test(e.source_sha256??''))||row.source_url&&!/^https?:\/\//.test(row.source_url))throw Error('Projection source assessment is untraceable');}
 for(const row of assessments.locations){if(row.historical_attributes_assessed!==false||!row.source_evidence?.length||!proof.manifests.some(m=>m.sha256===row.source_manifest_sha256&&m.receipt_sha256===row.source_receipt_sha256))throw Error('Projection source assessment lacks pinned evidence');if(proof.added_ids.includes(row.id)&&(!row.creation_proof||row.creation_proof.location_id!==row.id||!HEX.test(row.creation_proof.source?.sha256??'')||row.kind!=='source-backed-create'))throw Error('Projection creation assessment lacks exact source proof');}
 for(const row of assessments.groups)if(!/^https?:\/\//.test(row.source_url??'')||!row.basis||!proof.manifests.some(m=>m.sha256===row.source_hierarchy_manifest_sha256))throw Error('New group source assessment lacks supported role evidence');
 if(!Array.isArray(proof.metadata_receipts)||proof.metadata_receipts.some(r=>!HEX.test(r.sha256??'')||r.reference_only!==true||r.history_transfer!==false))throw Error('Projection metadata receipts are not explicit and pinned');
 return proof;
}
/** Retain prior inspection bytes rather than re-labeling them as new reviews. */
export function retainProjectionInputs({data,sourcePaths,files,previousProjection=null,predecessorKey=null}){
 const baselineFiles={...(previousProjection?.baseline_files??{})},predecessorFiles={};
 const original=entry=>{const relative=entry.archive_path.replace(/^data\//,'');if(relative.split('/').includes('..')||path.isAbsolute(relative))throw Error('Unsafe retained inspection path');const bytes=fs.readFileSync(path.join(data,relative));if(sha(bytes)!==entry.archive_sha256||sha(gunzipSync(bytes))!==entry.original_sha256)throw Error('Prior source inspection bytes changed');files.set(relative,bytes);return bytes;};
 for(const entry of Object.values(baselineFiles))original(entry);
 for(const relative of sourcePaths){if(relative.split('/').includes('..')||path.isAbsolute(relative))throw Error('Unsafe retained inspection path');const raw=fs.readFileSync(path.join(data,relative)),key=`data/${relative}`;
  const archive=previousProjection&&predecessorKey?`macro-foundation/predecessor-inspections/${predecessorKey}/${relative}.gz`:baselineFiles[key]?null:`macro-foundation/retained-inspections/${relative}.gz`;
  if(!archive)continue;const bytes=gzipSync(raw,{level:9}),entry={archive_path:`data/${archive}`,archive_sha256:sha(bytes),original_sha256:sha(raw),compression:'gzip'};files.set(archive,bytes);if(previousProjection&&predecessorKey)predecessorFiles[key]=entry;else baselineFiles[key]=entry;
 }
 return {baselineFiles,predecessorFiles};
}
/** Compose retained source assessments; metadata edits do not create inspections. */
export function inheritProjectionAssessments({previous,current,geometryProof=null}){
 const changed=new Set([...(geometryProof?.changed_ids??[]),...(geometryProof?.removed_ids??[])]);
 const oldLocations=new Map((previous?.locations??[]).map(row=>[row.id,row]));
 const oldGroups=new Map((previous?.groups??[]).map(row=>[row.id,row]));
 for(const row of current.rows){const old=oldLocations.get(row.id);if(old?.source_assessment&&!changed.has(row.id)){
  if(old.owner!==row.owner)throw Error('Retained source assessment cannot assign a new owner');
  row.source_assessment=old.source_assessment;
 }}
 for(const row of current.projectedGroups){const old=oldGroups.get(row.id);if(old?.source_assessment)row.source_assessment=old.source_assessment;}
 if(geometryProof){
  const assessments=new Map(geometryProof.source_assessments.locations.map(row=>[row.id,row]));
  for(const row of current.rows)if(assessments.has(row.id))row.source_assessment=assessments.get(row.id);
  const groups=new Map(geometryProof.source_assessments.groups.map(row=>[row.id,row]));
  for(const row of current.projectedGroups)if(groups.has(row.id))row.source_assessment=groups.get(row.id);
 }
}
export function projectAdditionalOwnerProfiles(originalProfiles,rows,previousProfiles=[]){
 const known=new Set(originalProfiles.map(row=>row.owner)),owners=new Map();
 for(const row of rows)if(!known.has(row.owner)){if(!owners.has(row.owner))owners.set(row.owner,[]);owners.get(row.owner).push(row);}
 return [...owners].map(([owner,members])=>{
  const retained=previousProfiles.find(row=>row.owner===owner),assessments=members.map(row=>row.source_assessment).filter(Boolean);
  if((!retained&&assessments.length!==members.length)||assessments.some(row=>row.regional_interior_approved!==false||row.historical_attributes_assessed!==false)||retained&&retained.regional_interiors_approved!==false)throw Error('Additional owner profile lacks retained open source assessments');
  return {...retained,owner,locations:members.length,continent:[...new Set(members.map(row=>row.continent))].sort().join(', '),open_group_ids:[...new Set(members.flatMap(row=>row.parent_chain))],status:'source-assessed-open',source_assessment_context:retained?.source_assessment_context??'Source-backed omitted land; owner remains unknown unless separately evidenced',source_assessment_entries:assessments,regional_interiors_approved:false};
 });
}
/** Explicit current membership projection; preserved inspections are never relabeled. */
export async function prepareMacroReviewProjection({data,before,after,receipts=[],geometryProofs=null,sourceReceipt=null}){
 data=path.resolve(data);const root=path.dirname(data);
 const {validateSemanticFollowup}=await import('./validate-semantic-followup.mjs');
 await validateSemanticFollowup(root);
 const prior=snapshot(before),current=snapshot(after),files=new Map(),geometryProof=await resolveProjectionGeometry({before,after,geometryProofs,sourceReceipt});
 if(!geometryProof&&(!same(prior.rows.map(row=>row.id),current.rows.map(row=>row.id))||footprintHash(before.features)!==footprintHash(after.features)))throw Error('Metadata projection cannot transfer, remove or alter location footprints/history');
 const previousFile=path.join(data,'macro-foundation/current-membership-projection.json.gz'),previous=fs.existsSync(previousFile)?read(previousFile):null;
 const previousDashboard=previous?read(path.join(data,'macro-foundation/world-review-projection.json')):null;
 if(previousDashboard&&['hierarchy_sha256','location_index_sha256','footprints_sha256'].some(key=>previousDashboard.current_pins?.[key]!==before.proof[key]))throw Error('Prior owner profiles differ from the exact predecessor');
 if(previous){if(['hierarchy_sha256','location_index_sha256','footprints_sha256'].some(key=>previous.current_pins?.[key]!==before.proof[key])||!same(previous.locations.map(row=>row.id),prior.rows.map(row=>row.id)))throw Error('Prior projection is not the exact current predecessor');const previousRows=new Map(previous.locations.map(row=>[row.id,row]));if(prior.rows.some(row=>JSON.stringify(reference(row))!==JSON.stringify(reference(previousRows.get(row.id)))))throw Error('Prior projected reference context changed without evidence');if(geometryProof)geometryProof.predecessor_reference_context={source_projection_sha256:sha(fs.readFileSync(previousFile)),locations:geometryProof.archived_location_references.map(row=>reference(previousRows.get(row.reference.id)))};}
 const originalWorld=previous?.baseline_files?.['data/world-review.json']?JSON.parse(gunzipSync(fs.readFileSync(path.join(root,previous.baseline_files['data/world-review.json'].archive_path)))):read(path.join(data,'world-review.json')),closure=read(path.join(data,'global-semantic-closure.json.gz'));
 const sourcePaths=new Set(['hierarchy.json','world-index.json','world-review.json','global-semantic-closure.json.gz','location-policy.json','administrative-sources.json','geographic-decision-migration.json.gz','macro-boundary-migration.json.gz','geographic-repair-evidence/migration-receipt.json.gz']);
 const index=read(path.join(data,'world-index.json'));index.parts.forEach(part=>sourcePaths.add(part));Object.keys(closure.input_sha256).forEach(file=>sourcePaths.add(file));
 const ledgers=[];
 for(const continent of ['africa','asia','europe','north-america','oceania','south-america']){const name=`geographic-semantic-followup/${continent}.json.gz`,report=read(path.join(data,name));ledgers.push({path:`data/${name}`,sha256:sha(fs.readFileSync(path.join(data,name)))});[...Object.keys(report.input_sha256??{}),...Object.keys(report.source_evidence?.diagnostics?.additional_input_sha256??{})].forEach(file=>{if(!file.startsWith('scripts/'))sourcePaths.add(file.replace(/^data\//,''));});}
 if(previous){sourcePaths.add('macro-foundation/current-membership-projection.json.gz');sourcePaths.add('macro-foundation/world-review-projection.json');}
 const {baselineFiles,predecessorFiles}=retainProjectionInputs({data,sourcePaths,files,previousProjection:previous,predecessorKey:previous?sha(fs.readFileSync(previousFile)):null});
 const crosswalks=[...(previous?.crosswalks??[])];for(const file of receipts){const raw=fs.readFileSync(file),receipt=JSON.parse(file.endsWith('.gz')?gunzipSync(raw):raw);if(receipt.reference_only!==true||receipt.historical_claims_transferred!==false||receipt.summary?.geometry_changes!==0)throw Error('Projection requires reference-only immutable-footprint receipts');crosswalks.push({path:path.relative(root,file),sha256:sha(raw),group_changes:receipt.group_changes,relationships:receipt.relationships,retired_units:receipt.retired_units,history_transfer:'none'});}
 const removed=prior.units.filter(row=>!current.groups.has(row.id)),added=current.units.filter(row=>!prior.groups.has(row.id)),retired=new Set(crosswalks.flatMap(row=>row.retired_units??[]).map(row=>row.id)),created=new Set([...crosswalks.flatMap(row=>row.group_changes??[]).filter(row=>row.before===null&&row.after).map(row=>row.id),...(geometryProof?.created_group_ids??[])]);
 if(removed.some(row=>!retired.has(row.id))||added.some(row=>!created.has(row.id)))throw Error('Projection changed group identities lack explicit archive/creation receipts');
 inheritProjectionAssessments({previous,current,geometryProof});
 const projection={version:1,kind:'current-membership-projection',retained_source_assessments:true,scope:geometryProof?'Current membership projection of explicit source-backed migrations; retained source inspections remain unchanged and regional interiors remain open':'Metadata projection of current memberships from retained inspections; not a new source audit or semantic approval',semantic_complete:false,regional_interiors_approved:false,historical_claims_transferred:false,geometry_changes:geometryProof?geometryProof.changed_ids.length+geometryProof.removed_ids.length+geometryProof.added_ids.length:0,...(geometryProof?{geometry_proof:geometryProof}:{}),source_inspections:previous?.source_inspections??{world_review:{path:'data/world-review.json',sha256:sha(fs.readFileSync(path.join(data,'world-review.json')))},closure:{path:'data/global-semantic-closure.json.gz',sha256:sha(fs.readFileSync(path.join(data,'global-semantic-closure.json.gz')))},continent_ledgers:ledgers},baseline_files:baselineFiles,...(previous?{predecessor_files:predecessorFiles}:{}),before_pins:before.proof,current_pins:after.proof,counts:{locations:current.rows.length,groups:current.units.length,...Object.fromEntries(tiers.map(tier=>[tier,current.units.filter(row=>row.level===tier).length]))},locations:current.rows,groups:current.projectedGroups,archived_predecessors:[...(previous?.archived_predecessors??[]),...removed],created_groups:[...(previous?.created_groups??[]),...added],crosswalks};
 files.set('macro-foundation/current-membership-projection.json.gz',gzipSync(encode(projection),{level:9}));
 const ownerGroups=new Map();for(const row of current.rows){if(!ownerGroups.has(row.owner))ownerGroups.set(row.owner,[]);ownerGroups.get(row.owner).push(row);}
 const projectedTerritories=originalWorld.territories.map(row=>{const members=ownerGroups.get(row.owner)??[];return {...row,locations:members.length,continent:[...new Set(members.map(loc=>loc.continent))].sort().join(', '),open_group_ids:[...new Set(members.flatMap(loc=>loc.parent_chain))],status:'source-assessed-open',source_assessment_context:'Retained original inspection; membership counts projected to current geography'};});
 projectedTerritories.push(...projectAdditionalOwnerProfiles(projectedTerritories,current.rows,previousDashboard?.territories));
 const rowById=new Map(current.rows.map(row=>[row.id,row])),originalGroups=new Map(originalWorld.groups.map(row=>[row.id,row]));
 const dashboardGroups=current.projectedGroups.map(row=>{const old=originalGroups.get(row.id);return {id:row.id,name:row.name,level:row.level,parent_id:row.parent_id,status:'open',semantic_status:'pending',checks:row.checks,basis:old?.basis??'Current reference grouping; interior review open',source:old?.source??(geometryProof?row.metadata?.source:null)??null,source_url:old?.source_url??(geometryProof?row.metadata?.source_url:null)??null,...(row.source_assessment?{source_assessment:row.source_assessment}:{}),locations:row.descendant_location_count,children:row.children.length,child_ids:row.children,owners:[...new Set(row.member_location_ids.map(id=>rowById.get(id).owner))],inspection_context:old?'Retained original source inspection; current members may differ':'New reference group; no descendant inspection approval'};});
 const locationParts=[];for(let start=0;start<current.rows.length;start+=1500){const file=`macro-foundation/world-review-locations-${start/1500}.json.gz`;files.set(file,gzipSync(encode(current.rows.slice(start,start+1500)),{level:9}));locationParts.push(file);}
 const partForLocation=new Map(current.rows.map((row,index)=>[row.id,locationParts[Math.floor(index/1500)]])),groupById=new Map(current.projectedGroups.map(row=>[row.id,row]));
 for(const row of dashboardGroups)if(row.level==='province')row.location_parts=[...new Set(groupById.get(row.id).member_location_ids.map(id=>partForLocation.get(id)))];
 const dashboard={...originalWorld,kind:'current-membership-projection',scope:projection.scope,semantic_complete:false,locations:current.rows.length,groups:dashboardGroups,territories:projectedTerritories,root_ids:current.units.filter(row=>row.level==='continent').map(row=>row.id),level_progress:Object.fromEntries(tiers.map(tier=>[tier,{total:current.units.filter(row=>row.level===tier).length,boundary_reviewed:0,pending:current.units.filter(row=>row.level===tier).length}]).concat([['location',{total:current.rows.length,source_assessed:0,semantic_reviewed:0,pending_semantic_review:current.rows.length}]])),location_parts:locationParts,source_inspections:projection.source_inspections,current_pins:after.proof,input_sha256:{'hierarchy.json':after.proof.hierarchy_sha256,'world-index.json':after.proof.location_index_sha256},projection_file:'macro-foundation/current-membership-projection.json.gz',retained_inspection_url:'world-review-source-inspection.json.gz'};
 files.set('macro-foundation/world-review-projection.json',encode(dashboard));return files;
}

export function validateMacroReviewProjection({projection,hierarchy,locations,currentPins,baselineHierarchy=null,baselineLocations=null,predecessorProjections=[]}){
 const predecessor=predecessorProjections[0];
 if(predecessor&&projection.retained_source_assessments===true){
  if(['hierarchy_sha256','location_index_sha256','footprints_sha256'].some(key=>projection.before_pins?.[key]!==predecessor.current_pins?.[key]))throw Error('Projection predecessor does not match exact before pins');
  validateMacroReviewProjection({projection:predecessor,hierarchy:predecessor.groups,locations:predecessor.locations,currentPins:predecessor.current_pins,baselineHierarchy,baselineLocations,predecessorProjections:predecessorProjections.slice(1)});
 }
 const predecessorLocations=predecessor?.locations??baselineLocations,geometryProof=validateProjectionGeometry(projection,predecessorLocations,locations);
 if(predecessor){
  const changed=new Set(geometryProof?.changed_ids??[]),current=new Map(projection.locations.map(row=>[row.id,row]));
  for(const row of predecessor.locations)if(row.source_assessment&&current.has(row.id)&&!changed.has(row.id)){
   if(JSON.stringify(current.get(row.id).source_assessment)!==JSON.stringify(row.source_assessment))throw Error('Projection dropped or rewrote retained source assessment');
  }
 }
 if(projection?.version!==1||projection.kind!=='current-membership-projection'||projection.semantic_complete!==false||projection.regional_interiors_approved!==false||projection.historical_claims_transferred!==false||(!geometryProof&&projection.geometry_changes!==0))throw Error('Invalid current membership projection contract');
 for(const key of ['hierarchy_sha256','location_index_sha256','footprints_sha256'])if(projection.current_pins?.[key]!==currentPins[key])throw Error('Current membership projection has stale geographic pins');
 const groups=new Map(hierarchy.map(row=>[row.id,row])),projected=new Map(projection.groups.map(row=>[row.id,row]));
 if(!same(hierarchy.map(row=>row.id),projection.groups.map(row=>row.id))||!same(locations.map(row=>row.id),projection.locations.map(row=>row.id)))throw Error('Current membership projection does not conserve complete identity inventories');
 if(projection.counts?.locations!==locations.length||projection.counts.groups!==hierarchy.length||tiers.some(tier=>projection.counts[tier]!==hierarchy.filter(row=>row.level===tier).length))throw Error('Current projection counts differ from exact inventories');
 if(!geometryProof&&predecessorLocations&&!same(locations.map(row=>row.id),predecessorLocations.map(row=>row.id)))throw Error('Current projection loses original location identities');
 if(baselineHierarchy){
  const before=new Map(baselineHierarchy.map(row=>[row.id,row])),removed=baselineHierarchy.filter(row=>!groups.has(row.id));
  if(!same(removed.map(row=>row.id),projection.archived_predecessors.map(row=>row.id))||projection.archived_predecessors.some(row=>JSON.stringify(row)!==JSON.stringify(before.get(row.id))))throw Error('Current projection altered archived predecessor identities');
  const retired=new Set(projection.crosswalks.flatMap(row=>row.retired_units??[]).map(row=>row.id)),added=new Set([...projection.crosswalks.flatMap(row=>row.group_changes??[]).filter(row=>row.before===null&&row.after).map(row=>row.id),...(geometryProof?.created_group_ids??[]),...predecessorProjections.flatMap(p=>p.geometry_proof?.created_group_ids??[])]);
  if(removed.some(row=>!retired.has(row.id))||hierarchy.some(row=>!before.has(row.id)&&!added.has(row.id)))throw Error('Current projection group changes lack explicit crosswalks');
 }
 if(geometryProof&&(predecessor?.groups??baselineHierarchy)&&geometryProof.created_group_ids.some(id=>!hierarchy.some(row=>row.id===id)||(predecessor?.groups??baselineHierarchy).some(row=>row.id===id)))throw Error('Projection new group source coverage differs from actual identities');
 const byId=new Map(locations.map(row=>[row.id,row])),members=new Map(hierarchy.map(row=>[row.id,[]]));
 for(const row of projection.locations){const actual=byId.get(row.id),expected=chain(actual.parent_id,groups);if(row.name!==actual.name||row.parent_id!==actual.parent_id||row.owner!==actual.owner||JSON.stringify(row.parent_chain)!==JSON.stringify(expected)||row.status!=='open'||row.semantic_status!=='open')throw Error('Current membership projection contains stale or unapproved location facts');for(const parent of expected)members.get(parent).push(row.id);}
 for(const [id,actual] of groups){const row=projected.get(id);if(row.name!==actual.name||row.parent_id!==actual.parent_id||row.level!==actual.level||row.branch_semantic_status!=='open'||!same(row.member_location_ids,members.get(id)))throw Error('Current membership projection has stale group membership or semantic approval');}
 return {validated:true,counts:projection.counts,semantic_complete:false,baseline_inspections_preserved:true,projection_only:true};
}
