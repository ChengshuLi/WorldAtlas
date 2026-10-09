// Versioned retained-identity ledger continuation, not historical membership import.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {geographicLocationIdsHash,geographicChangesHash} from '../../../hosted/geographic-releases.js';
import {PIXEL_TARGETS} from './pixel-audit-continuation.mjs';
import {OLD_FOOTPRINT,NEW_FOOTPRINT} from './native-v9-manifest.mjs';
const OLD_RELEASE='geography:review:896bf79dd6e5661dfbbffba60da96fa987b9971af2b884cf52347189861ebe9e';
const tiers=['location','province','area','region','subcontinent','continent'];
const sha=raw=>createHash('sha256').update(raw).digest('hex');
// Exact stock canonical-array bytes, emitted one full record at a time.
// Preserve SQLite binary code-point ordering and every evidence/source field.
const canonical=value=>Array.isArray(value)?value.map(canonical):value&&typeof value==='object'?Object.fromEntries(Object.keys(value).sort().map(key=>[key,canonical(value[key])])):value;
const binaryCompare=(a,b)=>{const aa=Array.from(a),bb=Array.from(b);for(let i=0;i<Math.min(aa.length,bb.length);i++){const delta=aa[i].codePointAt(0)-bb[i].codePointAt(0);if(delta)return delta;}return aa.length-bb.length;};
export function hashCompleteMemberships(input){
 const hash=createHash('sha256');hash.update('[');let first=true;
 const ordered=input.slice().sort((a,b)=>binaryCompare(a.entity_id??a.id,b.entity_id??b.id));
 for(const row of ordered){const evidence=typeof row.evidence==='string'?JSON.parse(row.evidence):row.evidence??{};assert(evidence&&typeof evidence==='object'&&!Array.isArray(evidence)&&JSON.stringify(evidence).length<=16384);
  const value={entity_id:row.entity_id??row.id,kind:row.kind??row.level,parent_id:row.parent_id??null,reference_name:row.reference_name??null,active:row.active??1,source_id:row.source_id,evidence};
  if(!first)hash.update(',');first=false;hash.update(JSON.stringify(canonical(value)));
 }hash.update(']');return hash.digest('hex');
}

export function successorIdentity({receiptSha,proposalCommit,predecessorManifestSha}){
 for(const pin of [receiptSha,predecessorManifestSha])assert(/^[a-f0-9]{64}$/.test(pin));assert(/^[a-f0-9]{40}$/.test(proposalCommit));
 const key=sha(JSON.stringify({issue:1520,predecessor_release_id:OLD_RELEASE,before_footprints_sha256:OLD_FOOTPRINT,after_footprints_sha256:NEW_FOOTPRINT,geometry_receipt_sha256:receiptSha,proposal_commit:proposalCommit,predecessor_manifest_sha256:predecessorManifestSha}));
 return {releaseId:'geography:review:'+key,sourceId:'source:atlas:geographic-review:'+key};
}
export async function continueRelease({registry,memberships,changes,migrationReceipt,receiptSha,proposalCommit,predecessorManifestSha,referenceDate}){
 assert.equal(registry.releases.length,8);for(let i=0;i<8;i++)assert.equal(registry.releases[i].version,i+1);
 const old=registry.releases.at(-1);assert.equal(old.id,OLD_RELEASE);assert.equal(old.footprints_sha256,OLD_FOOTPRINT);
 assert.equal(old.hierarchy_sha256,'568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b');
 assert.equal(memberships.length,84833);assert.equal(new Set(memberships.map(p=>p.entity_id)).size,memberships.length);
 assert.equal(hashCompleteMemberships(memberships),old.membership_sha256);assert.equal(await geographicLocationIdsHash(memberships),old.location_ids_sha256);assert.equal(await geographicChangesHash(changes),old.changes_sha256);
 assert.deepEqual(Object.fromEntries(tiers.map(t=>[t,memberships.filter(m=>m.kind===t&&m.active===1).length])),old.expected_counts);
 const byId=new Map(memberships.map(p=>[p.entity_id,p]));
 for(const m of memberships.filter(p=>p.active===1)){const at=tiers.indexOf(m.kind);assert(at>=0&&m.source_id&&m.evidence);if(at===5)assert.equal(m.parent_id,null);else{assert.equal(byId.get(m.parent_id)?.kind,tiers[at+1]);assert.equal(byId.get(m.parent_id)?.active,1);}}
 assert.equal(migrationReceipt.before_footprints_sha256,OLD_FOOTPRINT);assert.equal(migrationReceipt.after_footprints_sha256,NEW_FOOTPRINT);assert.deepEqual(migrationReceipt.changed_ids,PIXEL_TARGETS);assert.deepEqual(migrationReceipt.removed_ids,[]);assert.deepEqual(migrationReceipt.added_ids,[]);assert.equal(migrationReceipt.historical_claims_transferred,false);assert.equal(migrationReceipt.geometry_stage_validated,true);
 const ids=[...migrationReceipt.changed_ids,...migrationReceipt.reused_ids];assert.equal(ids.length,49625);assert.equal(new Set(ids).size,49625);assert.deepEqual(ids.sort(),memberships.filter(p=>p.kind==='location'&&p.active===1).map(p=>p.entity_id).sort());
 assert.equal(migrationReceipt.archives.length,2);assert.equal(migrationReceipt.relationships.length,2);
 for(const row of migrationReceipt.archives)assert.equal(row.feature.properties.parent_id,byId.get(row.id)?.parent_id);
 assert(/^2026-\d\d-\d\d$/.test(referenceDate));
 const {releaseId,sourceId}=successorIdentity({receiptSha,proposalCommit,predecessorManifestSha}),key=releaseId.split(':').at(-1);
 const nextChanges=migrationReceipt.relationships.map((row,i)=>{assert.equal(row.history_transfer,false);assert.deepEqual(row.before_ids,[PIXEL_TARGETS[i]]);assert.deepEqual(row.after_ids,[PIXEL_TARGETS[i]]);return {id:`${key}:geometry:${i}:${PIXEL_TARGETS[i]}`,old_entity_id:PIXEL_TARGETS[i],new_entity_id:PIXEL_TARGETS[i],change_type:'retain',source_id:sourceId,evidence:{reference_only:true,history_transfer:'none',migration_sha256:receiptSha,geometry_migration:{old_entity_id:PIXEL_TARGETS[i],new_entity_id:PIXEL_TARGETS[i],change_type:'retain',history_transfer:'none',proposal_id:row.proposal_id,kind:row.kind}}};});
 const release={...old,id:releaseId,version:9,source_id:sourceId,reference_date:referenceDate,footprints_sha256:NEW_FOOTPRINT,changes_sha256:await geographicChangesHash(nextChanges),metadata:{...old.metadata,predecessor_release_id:old.id,predecessor_manifest_sha256:predecessorManifestSha,geometry_migration:{commit:proposalCommit,path:'coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/migration-receipt.json',sha256:receiptSha,before_footprints_sha256:OLD_FOOTPRINT,after_footprints_sha256:NEW_FOOTPRINT,history_transfer:'none'},physical_reference_correction:{issue:1520,subjects:[...PIXEL_TARGETS],source_role:'Independently reviewed AAFC named-envelope and retained GSHHG source fit',legal_administrative_authority:false,water_classification:false,historical_cause_approval:false}}};
 assert.equal(release.membership_sha256,old.membership_sha256);assert.equal(release.location_ids_sha256,old.location_ids_sha256);
 const source={id:sourceId,name:'Two source-supported Arctic retained-land additions',url:migrationReceipt.source_evidence[0].url,license:'Original retained source licenses; no new physical authority claim',vintage:referenceDate,status:'reference',supported_from:2026,supported_to:2027,metadata:{reference_only:true,historical_membership_not_asserted:true,issue:1520,proposal_commit:proposalCommit,migration_sha256:receiptSha,source_evidence:migrationReceipt.source_evidence,source_limits:migrationReceipt.limits,water_status:'unverified',physical_authority:'unapproved',failed_components:migrationReceipt.construction_failed_components,unresolved_source_components:migrationReceipt.source_rule_failed_components}};
 return {release,source,memberships,changes:nextChanges,old};
}
