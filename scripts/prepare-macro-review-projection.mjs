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
/** Explicit current membership projection; preserved inspections are never relabeled. */
export async function prepareMacroReviewProjection({data,before,after,receipts}){
 data=path.resolve(data);const root=path.dirname(data);
 const {validateSemanticFollowup}=await import('./validate-semantic-followup.mjs');
 await validateSemanticFollowup(root);
 const prior=snapshot(before),current=snapshot(after),files=new Map();
 if(!same(prior.rows.map(row=>row.id),current.rows.map(row=>row.id))||footprintHash(before.features)!==footprintHash(after.features))throw Error('Metadata projection cannot transfer, remove or alter location footprints/history');
 const originalWorld=read(path.join(data,'world-review.json')),closure=read(path.join(data,'global-semantic-closure.json.gz'));
 const sourcePaths=new Set(['hierarchy.json','world-index.json','world-review.json','global-semantic-closure.json.gz','location-policy.json','administrative-sources.json','geographic-decision-migration.json.gz','macro-boundary-migration.json.gz','geographic-repair-evidence/migration-receipt.json.gz']);
 const index=read(path.join(data,'world-index.json'));index.parts.forEach(part=>sourcePaths.add(part));Object.keys(closure.input_sha256).forEach(file=>sourcePaths.add(file));
 const ledgers=[];
 for(const continent of ['africa','asia','europe','north-america','oceania','south-america']){const name=`geographic-semantic-followup/${continent}.json.gz`,report=read(path.join(data,name));ledgers.push({path:`data/${name}`,sha256:sha(fs.readFileSync(path.join(data,name)))});[...Object.keys(report.input_sha256??{}),...Object.keys(report.source_evidence?.diagnostics?.additional_input_sha256??{})].forEach(file=>{if(!file.startsWith('scripts/'))sourcePaths.add(file.replace(/^data\//,''));});}
 const baselineFiles={};
 for(const relative of sourcePaths){if(relative.split('/').includes('..')||path.isAbsolute(relative))throw Error('Unsafe retained inspection path');const original=fs.readFileSync(path.join(data,relative)),archive=`macro-foundation/retained-inspections/${relative}.gz`,bytes=gzipSync(original,{level:9});files.set(archive,bytes);baselineFiles[`data/${relative}`]={archive_path:`data/${archive}`,archive_sha256:sha(bytes),original_sha256:sha(original),compression:'gzip'};}
 const crosswalks=[];for(const file of receipts){const raw=fs.readFileSync(file),receipt=JSON.parse(file.endsWith('.gz')?gunzipSync(raw):raw);if(receipt.reference_only!==true||receipt.historical_claims_transferred!==false||receipt.summary?.geometry_changes!==0)throw Error('Projection requires reference-only immutable-footprint receipts');crosswalks.push({path:path.relative(root,file),sha256:sha(raw),group_changes:receipt.group_changes,relationships:receipt.relationships,retired_units:receipt.retired_units,history_transfer:'none'});}
 const removed=prior.units.filter(row=>!current.groups.has(row.id)),added=current.units.filter(row=>!prior.groups.has(row.id)),retired=new Set(crosswalks.flatMap(row=>row.retired_units??[]).map(row=>row.id)),created=new Set(crosswalks.flatMap(row=>row.group_changes??[]).filter(row=>row.before===null&&row.after).map(row=>row.id));
 if(removed.some(row=>!retired.has(row.id))||added.some(row=>!created.has(row.id)))throw Error('Projection changed group identities lack explicit archive/creation receipts');
 const projection={version:1,kind:'current-membership-projection',scope:'Metadata projection of current memberships from retained inspections; not a new source audit or semantic approval',semantic_complete:false,regional_interiors_approved:false,historical_claims_transferred:false,geometry_changes:0,source_inspections:{world_review:{path:'data/world-review.json',sha256:sha(fs.readFileSync(path.join(data,'world-review.json')))},closure:{path:'data/global-semantic-closure.json.gz',sha256:sha(fs.readFileSync(path.join(data,'global-semantic-closure.json.gz')))},continent_ledgers:ledgers},baseline_files:baselineFiles,before_pins:before.proof,current_pins:after.proof,counts:{locations:current.rows.length,groups:current.units.length,...Object.fromEntries(tiers.map(tier=>[tier,current.units.filter(row=>row.level===tier).length]))},locations:current.rows,groups:current.projectedGroups,archived_predecessors:removed,created_groups:added,crosswalks};
 files.set('macro-foundation/current-membership-projection.json.gz',gzipSync(encode(projection),{level:9}));
 const ownerGroups=new Map();for(const row of current.rows){if(!ownerGroups.has(row.owner))ownerGroups.set(row.owner,[]);ownerGroups.get(row.owner).push(row);}
 const projectedTerritories=originalWorld.territories.map(row=>{const members=ownerGroups.get(row.owner)??[];return {...row,locations:members.length,continent:[...new Set(members.map(loc=>loc.continent))].sort().join(', '),open_group_ids:[...new Set(members.flatMap(loc=>loc.parent_chain))],status:'source-assessed-open',source_assessment_context:'Retained original inspection; membership counts projected to current geography'};});
 const rowById=new Map(current.rows.map(row=>[row.id,row])),originalGroups=new Map(originalWorld.groups.map(row=>[row.id,row]));
 const dashboardGroups=current.projectedGroups.map(row=>{const old=originalGroups.get(row.id);return {id:row.id,name:row.name,level:row.level,parent_id:row.parent_id,status:'open',semantic_status:'pending',checks:row.checks,basis:old?.basis??'Current reference grouping; interior review open',source:old?.source??null,source_url:old?.source_url??null,locations:row.descendant_location_count,children:row.children.length,child_ids:row.children,owners:[...new Set(row.member_location_ids.map(id=>rowById.get(id).owner))],inspection_context:old?'Retained original source inspection; current members may differ':'New reference group; no descendant inspection approval'};});
 const locationParts=[];for(let start=0;start<current.rows.length;start+=1500){const file=`macro-foundation/world-review-locations-${start/1500}.json.gz`;files.set(file,gzipSync(encode(current.rows.slice(start,start+1500)),{level:9}));locationParts.push(file);}
 const partForLocation=new Map(current.rows.map((row,index)=>[row.id,locationParts[Math.floor(index/1500)]])),groupById=new Map(current.projectedGroups.map(row=>[row.id,row]));
 for(const row of dashboardGroups)if(row.level==='province')row.location_parts=[...new Set(groupById.get(row.id).member_location_ids.map(id=>partForLocation.get(id)))];
 const dashboard={...originalWorld,kind:'current-membership-projection',scope:projection.scope,semantic_complete:false,locations:current.rows.length,groups:dashboardGroups,territories:projectedTerritories,root_ids:current.units.filter(row=>row.level==='continent').map(row=>row.id),level_progress:Object.fromEntries(tiers.map(tier=>[tier,{total:current.units.filter(row=>row.level===tier).length,boundary_reviewed:0,pending:current.units.filter(row=>row.level===tier).length}]).concat([['location',{total:current.rows.length,source_assessed:0,semantic_reviewed:0,pending_semantic_review:current.rows.length}]])),location_parts:locationParts,source_inspections:projection.source_inspections,current_pins:after.proof,input_sha256:{'hierarchy.json':after.proof.hierarchy_sha256,'world-index.json':after.proof.location_index_sha256},projection_file:'macro-foundation/current-membership-projection.json.gz',retained_inspection_url:'world-review-source-inspection.json.gz'};
 files.set('macro-foundation/world-review-projection.json',encode(dashboard));return files;
}

export function validateMacroReviewProjection({projection,hierarchy,locations,currentPins,baselineHierarchy=null,baselineLocations=null}){
 if(projection?.version!==1||projection.kind!=='current-membership-projection'||projection.semantic_complete!==false||projection.regional_interiors_approved!==false||projection.historical_claims_transferred!==false||projection.geometry_changes!==0)throw Error('Invalid current membership projection contract');
 for(const key of ['hierarchy_sha256','location_index_sha256','footprints_sha256'])if(projection.current_pins?.[key]!==currentPins[key])throw Error('Current membership projection has stale geographic pins');
 const groups=new Map(hierarchy.map(row=>[row.id,row])),projected=new Map(projection.groups.map(row=>[row.id,row]));
 if(!same(hierarchy.map(row=>row.id),projection.groups.map(row=>row.id))||!same(locations.map(row=>row.id),projection.locations.map(row=>row.id)))throw Error('Current membership projection does not conserve complete identity inventories');
 if(projection.counts?.locations!==locations.length||projection.counts.groups!==hierarchy.length||tiers.some(tier=>projection.counts[tier]!==hierarchy.filter(row=>row.level===tier).length))throw Error('Current projection counts differ from exact inventories');
 if(baselineLocations&&!same(locations.map(row=>row.id),baselineLocations.map(row=>row.id)))throw Error('Current projection loses original location identities');
 if(baselineHierarchy){
  const before=new Map(baselineHierarchy.map(row=>[row.id,row])),removed=baselineHierarchy.filter(row=>!groups.has(row.id));
  if(!same(removed.map(row=>row.id),projection.archived_predecessors.map(row=>row.id))||projection.archived_predecessors.some(row=>JSON.stringify(row)!==JSON.stringify(before.get(row.id))))throw Error('Current projection altered archived predecessor identities');
  const retired=new Set(projection.crosswalks.flatMap(row=>row.retired_units??[]).map(row=>row.id)),added=new Set(projection.crosswalks.flatMap(row=>row.group_changes??[]).filter(row=>row.before===null&&row.after).map(row=>row.id));
  if(removed.some(row=>!retired.has(row.id))||hierarchy.some(row=>!before.has(row.id)&&!added.has(row.id)))throw Error('Current projection group changes lack explicit crosswalks');
 }
 const byId=new Map(locations.map(row=>[row.id,row])),members=new Map(hierarchy.map(row=>[row.id,[]]));
 for(const row of projection.locations){const actual=byId.get(row.id),expected=chain(actual.parent_id,groups);if(row.name!==actual.name||row.parent_id!==actual.parent_id||row.owner!==actual.owner||JSON.stringify(row.parent_chain)!==JSON.stringify(expected)||row.status!=='open'||row.semantic_status!=='open')throw Error('Current membership projection contains stale or unapproved location facts');for(const parent of expected)members.get(parent).push(row.id);}
 for(const [id,actual] of groups){const row=projected.get(id);if(row.name!==actual.name||row.parent_id!==actual.parent_id||row.level!==actual.level||row.branch_semantic_status!=='open'||!same(row.member_location_ids,members.get(id)))throw Error('Current membership projection has stale group membership or semantic approval');}
 return {validated:true,counts:projection.counts,semantic_complete:false,baseline_inspections_preserved:true,projection_only:true};
}
