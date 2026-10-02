import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {footprintHash} from './check-prepared.mjs';
import {geographicMembershipHash,geographicLocationIdsHash,geographicChangesHash} from '../hosted/geographic-releases.js';

const tiers=['continent','subcontinent','region','area','province','location'];
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const read=file=>JSON.parse(file.endsWith('.gz')?gunzipSync(fs.readFileSync(file)):fs.readFileSync(file,'utf8'));
const json=value=>JSON.stringify(value);

/** Prepare immutable reference membership versions; never overwrite the catalog. */
export async function prepareGeographicRelease({data='data',output='data/geographic-releases',referenceDate='2026-10-01'}={}){
 const original=new Map(),catalog=read(`${data}/hosted-catalog/index.json`);
 for(const part of catalog.batches.filter(p=>p.kind==='entities')){
  const bytes=fs.readFileSync(`${data}/hosted-catalog/${part.path}`);
  if(sha(bytes)!==part.sha256)throw Error(`Immutable catalog hash mismatch: ${part.path}`);
  for(const entity of JSON.parse(bytes).entities)if(tiers.includes(entity.kind))original.set(entity.id,entity);
 }
 const units=read(`${data}/hierarchy.json`),features=read(`${data}/world-index.json`).parts.flatMap(p=>read(`${data}/${p}`).features);
 const migration=read(`${data}/geographic-decision-migration.json.gz`),current=new Map(units.map(u=>[u.id,{...u,kind:u.level}]));
 for(const f of features)current.set(f.id,{id:f.id,kind:'location',name:f.properties.name,parent_id:f.properties.parent_id,metadata:f.properties.metadata});
 // This migration changes names/membership, never land or location identities.
 const oldLocationIds=[...original.values()].filter(e=>e.kind==='location'&&e.active===1).map(e=>e.id).sort();
 if(json(oldLocationIds)!==json(features.map(f=>f.id).sort()))throw Error('Location migration requires a separately validated footprint/identity crosswalk');
 const decisionFiles=fs.readdirSync(`${data}/geographic-decisions`).filter(f=>f.endsWith('.json')).sort();
 if(decisionFiles.length!==6)throw Error('Six continent review files are required');
 const proofs=Object.fromEntries(decisionFiles.map(f=>[f,sha(fs.readFileSync(`${data}/geographic-decisions/${f}`))]));
 const documents=decisionFiles.map(f=>read(`${data}/geographic-decisions/${f}`)),decisions=new Map(documents.flatMap(d=>d.decisions).map(r=>[r.id,r]));
 const migrationHash=sha(fs.readFileSync(`${data}/geographic-decision-migration.json.gz`));
 const releaseKey=sha(json([proofs,migrationHash,referenceDate]));
 const source={id:`source:atlas:geographic-review:${releaseKey}`,name:'Worldwide inspected reference-geography decisions',url:null,license:'Original source licenses retained in each cited continent decision',vintage:referenceDate,status:'reference',supported_from:2026,supported_to:2027,metadata:{reference_only:true,historical_membership_not_asserted:true,decision_sha256:proofs,migration_sha256:migrationHash}};
 const retained={id:`source:atlas:geographic-baseline:${catalog.archive_sha256}`,name:'Retained original atlas reference memberships',url:null,license:'Original source licenses retained in immutable archive',vintage:'Original source vintages retained; modern reference context',status:'reference',supported_from:2026,supported_to:2027,metadata:{reference_only:true,historical_membership_not_asserted:true,archive_sha256:catalog.archive_sha256}};
 const newEntities=[...current.values()].filter(e=>!original.has(e.id)).map(e=>({id:e.id,kind:e.kind,name:e.name,parent_id:e.parent_id,source_id:source.id,active:1,is_example:0,metadata:{reference_context:true,decision_file:decisions.get(e.id)?.evidence??[],history_transfer:'none'}}));
 if(newEntities.some(e=>e.kind==='location'))throw Error('This release cannot create location footprints');
 const commonEvidence={reference_only:true,history_transfer:'none'};
 const baseline=[...original.values()].map(e=>({entity_id:e.id,kind:e.kind,parent_id:e.parent_id,reference_name:e.name,active:e.active,source_id:retained.id,evidence:{...commonEvidence,original_source_id:e.source_id,original_archive_sha256:catalog.archive_sha256}}));
 const memberships=[...original.values(),...newEntities].map(e=>{
  const now=current.get(e.id),decision=decisions.get(e.id),evidence={...commonEvidence,original_source_id:e.source_id,migration_sha256:migrationHash};
  if(decision)evidence.decision={id:e.id,action:decision.action,evidence:decision.evidence,boundary_status:decision.boundary_status};
  else if(now?.metadata?.semantic_review)evidence.location_review=now.metadata.semantic_review;
  if(Buffer.byteLength(json(evidence))>16384)throw Error(`Membership evidence exceeds bounded size: ${e.id}`);
  return {entity_id:e.id,kind:e.kind,parent_id:now?.parent_id??e.parent_id,reference_name:now?.name??e.name,active:Number(Boolean(now)),source_id:source.id,evidence};
 });
 const changes=[];
 for(const e of memberships){
  const old=original.get(e.entity_id),decision=decisions.get(e.entity_id);
  const add=(type,target=e.entity_id)=>changes.push({id:`${releaseKey}:${type}:${e.entity_id}`,old_entity_id:old?e.entity_id:null,new_entity_id:target,change_type:type,source_id:source.id,evidence:{...commonEvidence,migration_sha256:migrationHash,decision:decision?{action:decision.action,rationale:decision.rationale,evidence:decision.evidence}:null,before:old?{name:old.name,parent_id:old.parent_id,active:old.active}:null,after:{name:e.reference_name,parent_id:e.parent_id,active:e.active}}});
  if(!old)add('create');
  else if(old.active&&e.active===0)add(decision?.action==='merge'?'merge':'retire',decision?.action==='merge'?decision.target_id:null);
  else if(e.active){if(old.name!==e.reference_name)add('rename');if(old.parent_id!==e.parent_id)add('reparent');}
 }
 // Resolve merge chains so every retired ID points to the surviving identity.
 const byId=new Map(memberships.map(e=>[e.entity_id,e]));
 for(const change of changes.filter(c=>c.change_type==='merge')){
  const visited=new Set();while(!byId.get(change.new_entity_id)?.active){if(visited.has(change.new_entity_id))throw Error('Crosswalk merge cycle');visited.add(change.new_entity_id);const next=decisions.get(change.new_entity_id);if(next?.action!=='merge')throw Error('Merge target is not active');change.new_entity_id=next.target_id;}
 }
 const footprints=footprintHash(features),pinnedFootprints=read(`${data}/macro-corrections.json`).footprints_sha256_before;
 if(!/^[a-f0-9]{64}$/.test(pinnedFootprints)||footprints!==pinnedFootprints)throw Error('Names/membership-only release changed the pinned pre-migration location footprints');
 const counts=members=>Object.fromEntries([...tiers].reverse().map(k=>[k,members.filter(e=>e.kind===k&&e.active).length]));
 async function manifest(id,version,rows,delta,sourceId,hierarchyHash){return {id,version,source_id:sourceId,reference_date:referenceDate,hierarchy_sha256:hierarchyHash,footprints_sha256:footprints,membership_sha256:await geographicMembershipHash(rows),location_ids_sha256:await geographicLocationIdsHash(rows),changes_sha256:await geographicChangesHash(delta),expected_counts:counts(rows),metadata:{reference_only:true,historical_membership_not_asserted:true,original_registry_preserved:true,decision_sha256:proofs,migration_sha256:migrationHash}};}
 const releases=[{release:await manifest(`geography:baseline:${catalog.archive_sha256}`,1,baseline,[],retained.id,sha(json(migration.before_units))),memberships:baseline,changes:[]},{release:await manifest(`geography:review:${releaseKey}`,2,memberships,changes,source.id,sha(fs.readFileSync(`${data}/hierarchy.json`))),memberships,changes}];
 fs.mkdirSync(output,{recursive:true});
 const batches=[];
 function write(name,payload,route){const bytes=json(payload);if(Buffer.byteLength(bytes)>1048576)throw Error(`Bounded batch too large: ${name}`);fs.writeFileSync(`${output}/${name}`,bytes);batches.push({path:name,route,sha256:sha(bytes)});}
 write('sources.json',{sources:[retained,source],ingestion_id:`geographic-sources:${releaseKey}`},'/api/records/import');
 for(const tier of tiers)for(let at=0,rows=newEntities.filter(e=>e.kind===tier);at<rows.length;at+=200)write(`entities-${tier}-${at}.json`,{entities:rows.slice(at,at+200),ingestion_id:`geographic-new-identities:${releaseKey}:${tier}:${at}`},'/api/records/import');
 for(const {release,memberships,changes} of releases){
  write(`release-${release.version}.json`,{release,ingestion_id:`geographic-release:${release.id}`},'/api/geography/stage');
  for(const [kind,rows] of [['memberships',memberships],['changes',changes]])for(let at=0;at<rows.length;at+=200)write(`${release.version}-${kind}-${at}.json`,{release_id:release.id,[kind]:rows.slice(at,at+200),ingestion_id:`${release.id}:${kind}:${at}`},'/api/geography/stage');
 }
 const result={version:1,original_catalog_sha256:sha(fs.readFileSync(`${data}/hosted-catalog/index.json`)),releases:releases.map(r=>r.release),new_entities:newEntities.length,total_memberships:memberships.length,changes:changes.length,batches};
 fs.writeFileSync(`${output}/index.json`,JSON.stringify(result,null,2));
 return result;
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const result=await prepareGeographicRelease();console.log(JSON.stringify({new_entities:result.new_entities,total_memberships:result.total_memberships,changes:result.changes,batches:result.batches.length,releases:result.releases.map(r=>({id:r.id,counts:r.expected_counts}))}));
}
