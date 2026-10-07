// #1295 only: field-preserving successor of the authentic complete v7 ledger.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {geographicMembershipHash,geographicLocationIdsHash,geographicChangesHash} from '../../../hosted/geographic-releases.js';
import {appendRelease} from '../../../scripts/install-macro-reference.mjs';
import {footprintHash} from '../../../scripts/check-prepared.mjs';
import {BEFORE,AFTER,TARGETS} from './native-producer.mjs';
const json=x=>Buffer.from(JSON.stringify(x)+'\n'),sha=b=>createHash('sha256').update(b).digest('hex');
const clone=x=>JSON.parse(JSON.stringify(x));
const tiers=['location','province','area','region','subcontinent','continent'];
export async function validatePredecessor({registry,memberships,changes,hierarchySha,originalCatalogSha}){
 assert.equal(registry.releases.length,7,'Complete v1–v7 prefix required');
 for(let i=0;i<7;i++)assert.equal(registry.releases[i].version,i+1,'Skipped predecessor release');
 assert.equal(registry.original_catalog_sha256,originalCatalogSha,'Immutable original catalog changed');
 const old=registry.releases.at(-1);assert.equal(old.version,7);assert.equal(old.footprints_sha256,BEFORE);assert.equal(old.hierarchy_sha256,hierarchySha);
 assert.equal(new Set(memberships.map(m=>m.entity_id)).size,memberships.length,'Duplicate current member');
 assert.equal(await geographicMembershipHash(memberships),old.membership_sha256,'Complete predecessor member/evidence/source fields differ');
 assert.equal(await geographicLocationIdsHash(memberships),old.location_ids_sha256,'Predecessor location roster differs');
 assert.equal(await geographicChangesHash(changes),old.changes_sha256,'Complete predecessor historical changes differ');
 const counts=Object.fromEntries(tiers.map(t=>[t,memberships.filter(m=>m.kind===t&&m.active===1).length]));assert.deepEqual(counts,old.expected_counts);
 const byId=new Map(memberships.map(m=>[m.entity_id,m]));
 for(const m of memberships.filter(m=>m.active===1)){
  assert(tiers.includes(m.kind)&&typeof m.source_id==='string'&&m.source_id&&m.evidence&&typeof m.evidence==='object'&&!Array.isArray(m.evidence),'Missing original member source/evidence');
  const level=tiers.indexOf(m.kind);if(level===5)assert.equal(m.parent_id,null);else assert.equal(byId.get(m.parent_id)?.kind,tiers[level+1]);
  if(level!==5)assert.equal(byId.get(m.parent_id).active,1);
 }
 return old;
}
export async function successorRelease({registry,memberships,changes,world,hierarchySha,originalCatalogSha,relationships,receiptSha,proposalCommit,releaseId,sourceId,referenceDate='2026-10-07'}){
 const old=await validatePredecessor({registry,memberships,changes,hierarchySha,originalCatalogSha});
 assert.equal(world.length,49625);const activeLocations=new Map(memberships.filter(m=>m.kind==='location'&&m.active===1).map(m=>[m.entity_id,m]));
 assert.equal(footprintHash(world),AFTER,'Complete serialized successor geometry differs from approved footprint');
 assert.equal(activeLocations.size,world.length);assert.equal(new Set(world.map(f=>f.id)).size,world.length);
 for(const f of world){const m=activeLocations.get(f.id);assert(m,'Current selected location absent from original current members');assert.equal(m.parent_id,f.properties.parent_id,'Current selected parent changed');}
 assert.equal(relationships.length,2);assert.deepEqual(relationships.map(p=>p.old_entity_id).sort(),[...TARGETS].sort());
 for(const pair of relationships){assert.equal(pair.old_entity_id,pair.new_entity_id);assert.equal(pair.change_type,'retain');assert.equal(pair.history_transfer,'none');assert(activeLocations.has(pair.old_entity_id));}
 assert.match(receiptSha,/^[a-f0-9]{64}$/);assert.match(proposalCommit,/^[a-f0-9]{40}$/);assert.match(releaseId,/^geography:review:[a-f0-9]{64}$/);assert.match(sourceId,/^source:atlas:geographic-review:[a-f0-9]{64}$/);
 assert(!registry.releases.some(r=>r.id===releaseId),'Successor ID already exists');
 // Original membership and immutable source/evidence fields are retained exactly.
 // The new two relationships live in the new release change ledger, not rewrites.
 const nextMembers=clone(memberships),key=releaseId.split(':').at(-1);
 const nextChanges=relationships.map((pair,i)=>({id:`${key}:geometry:${i}:${pair.old_entity_id}`,old_entity_id:pair.old_entity_id,new_entity_id:pair.new_entity_id,change_type:'retain',source_id:sourceId,
  evidence:{reference_only:true,history_transfer:'none',geometry_migration:pair,migration_sha256:receiptSha}}));
 const release={...clone(old),id:releaseId,version:8,source_id:sourceId,reference_date:referenceDate,footprints_sha256:AFTER,
  membership_sha256:await geographicMembershipHash(nextMembers),location_ids_sha256:await geographicLocationIdsHash(nextMembers),changes_sha256:await geographicChangesHash(nextChanges),
  metadata:{...clone(old.metadata),predecessor_release_id:old.id,predecessor_manifest_sha256:sha(json(registry)),
   geometry_migration:{commit:proposalCommit,path:'data/reference-migrations/eastern-two-gap-repair-20261006/migration-receipt.json.gz',sha256:receiptSha,before_footprints_sha256:BEFORE,after_footprints_sha256:AFTER,history_transfer:'none'},
   physical_reference_correction:{issue:1295,subjects:TARGETS,source_role:'Main-approved physical-reference envelope only',legal_administrative_authority:false,water_classification:false,historical_cause_approval:false}}};
 assert.equal(release.membership_sha256,old.membership_sha256);assert.equal(release.location_ids_sha256,old.location_ids_sha256);
 assert.deepEqual(nextMembers,memberships);assert.deepEqual(release.expected_counts,old.expected_counts);
 const source={id:sourceId,name:'Two reviewed eastern Canada physical-reference corrections',url:null,license:'Original AAFC/source notices retained unchanged in the reviewed source evidence',vintage:referenceDate,status:'reference',supported_from:2026,supported_to:2027,
  metadata:{reference_only:true,historical_membership_not_asserted:true,issue:1295,proposal_commit:proposalCommit,migration_sha256:receiptSha,source_role:'Physical-reference correction, not administrative/legal authority'}};
 return {release,source,memberships:nextMembers,changes:nextChanges,old};
}
export function appendSuccessor(registry,result,{rowsPerBatch=200}={}){
 assert(Number.isInteger(rowsPerBatch)&&rowsPerBatch>=1&&rowsPerBatch<=250,'Existing atomic input cap must be preserved');
 const files=new Map(),batches=[];
 function add(name,payload,route){const raw=json(payload);assert(raw.length<=1048576,'Actual staged payload exceeds existing cap');assert((payload.memberships?.length??0)+(payload.changes?.length??0)+Number(Boolean(payload.release))<=250);files.set(name,raw);batches.push({path:name,route,sha256:sha(raw)});}
 add('sources.json',{sources:[result.source],ingestion_id:result.release.id+':sources'},'/api/records/import');
 add('release-8.json',{release:result.release,ingestion_id:result.release.id+':header'},'/api/geography/stage');
 for(const [kind,rows] of [['memberships',result.memberships],['changes',result.changes]])for(let at=0;at<rows.length;at+=rowsPerBatch)add(`8-${kind}-${at}.json`,{release_id:result.release.id,[kind]:rows.slice(at,at+rowsPerBatch),ingestion_id:`${result.release.id}:${kind}:${at}`},'/api/geography/stage');
 const next={...registry,releases:[result.release],batches,new_entities:0,total_memberships:result.memberships.length,changes:result.changes.length};
 const appended=appendRelease(registry,next,name=>files.get(name),{compressed:true});
 assert.deepEqual(appended.index.releases.slice(0,7),registry.releases,'Whole original release prefix changed');
 assert.deepEqual(appended.index.batches.slice(0,registry.batches.length),registry.batches,'Whole original batch prefix changed');
 assert.equal(appended.index.original_catalog_sha256,registry.original_catalog_sha256);
 assert.deepEqual(appended.index.sources_batches.slice(0,registry.sources_batches.length),registry.sources_batches);
 const raw=json(appended.index),encoded=gzipSync(raw,{level:9});assert(raw.length<=32*1024*1024&&encoded.length<=32*1024*1024);
 return {...appended,manifest_raw:raw,manifest_encoded:encoded};
}
