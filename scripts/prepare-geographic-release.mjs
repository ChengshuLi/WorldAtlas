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

const canonical=value=>Array.isArray(value)?value.map(canonical):value&&typeof value==='object'?Object.fromEntries(Object.keys(value).sort().map(k=>[k,canonical(value[k])])):value;
const contentHash=value=>sha(json(canonical(value)));
export function metadataRelationshipEvidence(pair){
 const evidence={receipt_sha256:pair.receipt_sha256,relationship:pair.relationship};
 if(Buffer.byteLength(json(pair.source_evidence))<=4096)evidence.source_evidence=pair.source_evidence;
 else evidence.source_evidence_ref={receipt_sha256:pair.receipt_sha256,json_pointer:'/source_evidence',content_sha256:contentHash(pair.source_evidence),records:pair.source_evidence.length};
 return evidence;
}
const uniqueIds=(rows,label)=>{if(!Array.isArray(rows)||rows.some(v=>typeof v!=='string'||!v)||new Set(rows).size!==rows.length)throw Error(`Invalid or duplicate ${label}`);return new Set(rows);};
const equalIds=(a,b)=>a.size===b.size&&[...a].every(v=>b.has(v));
const geometryId=f=>{if(!f?.id||f.id!==f.properties?.id||!f.geometry)throw Error('Geometry identity must match properties.id');return f.id;};
const safeProofFile=(base,relative)=>{const file=path.resolve(base,relative);if(!file.startsWith(path.resolve(base)+path.sep))throw Error('Proof archive path escapes evidence directory');return file;};

/** Validate exact before/after identity/footprint chains, never infer replacements. */
export function validateGeometryMigrations({features,baselineIds,baselineFootprints,manifestFiles=[]}){
 const proofs=[];let state=new Map(features.map(f=>[geometryId(f),f]));
 if(state.size!==features.length)throw Error('Duplicate current location identities');
 for(const manifestFile of manifestFiles){
  const absolute=path.resolve(manifestFile),base=path.dirname(absolute),manifest=read(absolute),files={};
  for(const [name,pin] of Object.entries(manifest.files??{})){
   const file=safeProofFile(base,pin.archive_path??name),raw=fs.readFileSync(file);
   if(sha(raw)!==pin.sha256)throw Error(`Geometry proof archive hash mismatch: ${name}`);
   if(pin.uncompressed_sha256&&sha(file.endsWith('.gz')?gunzipSync(raw):raw)!==pin.uncompressed_sha256)throw Error(`Geometry proof decompressed hash mismatch: ${name}`);
   files[name]={file,sha256:pin.sha256};
  }
  const pinned=files['migration-receipt.json']??files['migration-receipt.json.gz'];
  if(!pinned)throw Error('Geometry manifest requires a pinned migration-receipt.json');
  const receipt=read(pinned.file);
  if(receipt.geometry_stage_validated!==true||receipt.historical_claims_transferred!==false&&receipt.historical_claims_transferred!==0||manifest.history_transfer!==false)throw Error('Geometry proof requires independent validation and zero historical transfer');
  for(const key of ['before_footprints_sha256','after_footprints_sha256'])if(!/^[a-f0-9]{64}$/.test(receipt[key])||receipt[key]!==manifest[key])throw Error(`Geometry manifest/receipt ${key} mismatch`);
  const changed=uniqueIds(receipt.changed_ids,'changed IDs'),removed=uniqueIds(receipt.removed_ids,'removed IDs'),added=uniqueIds(receipt.added_ids,'added IDs'),reused=uniqueIds(receipt.reused_ids,'reused IDs');
  for(const sets of [[changed,removed],[changed,added],[changed,reused],[removed,added],[removed,reused],[added,reused]])if([...sets[0]].some(v=>sets[1].has(v)))throw Error('Geometry identity dispositions overlap');
  const archives=new Map();
  for(const row of receipt.archives??[]){const f=row.feature;if(row.id!==geometryId(f)||archives.has(row.id))throw Error('Invalid or duplicate original geometry archive identity');archives.set(row.id,f);}
  if(!equalIds(new Set(archives.keys()),new Set([...changed,...removed])))throw Error('Every changed/retired identity requires its exact archived original feature');
  const pairs=[],coveredBefore=new Set(),coveredAfter=new Set();
  for(const relationship of receipt.relationships??[]){
   if(relationship.history_transfer!==false)throw Error('Geometry relationship may not transfer historical evidence');
   const before=uniqueIds(relationship.before_ids,'relationship before IDs'),after=uniqueIds(relationship.after_ids,'relationship after IDs');
   if(!before.size||!after.size||[...before].some(id=>!changed.has(id)&&!removed.has(id))||[...after].some(id=>!changed.has(id)&&!added.has(id)))throw Error('Geometry relationship endpoints must match changed/retired/new dispositions');
   let links=relationship.identity_pairs;
   if(!links){
    if(equalIds(before,after))links=[...before].map(id=>({before_id:id,after_id:id}));
    else if(before.size===1||after.size===1)links=[...before].flatMap(before_id=>[...after].map(after_id=>({before_id,after_id})));
    else throw Error('Many-to-many geography replacement requires precise identity_pairs');
   }
   const localBefore=new Set(),localAfter=new Set(),seen=new Set();
   for(const link of links){
    const old=link.before_id,now=link.after_id,key=json([old,now]);
    if(!before.has(old)||!after.has(now)||seen.has(key))throw Error('Invalid or duplicate precise geometry identity pair');
    seen.add(key);localBefore.add(old);localAfter.add(now);
    pairs.push({old_entity_id:old,new_entity_id:now,change_type:old===now?'retain':after.size===1?'merge':before.size===1?'split':'replace',proposal_id:relationship.proposal_id,kind:relationship.kind,history_transfer:'none',pair_evidence:link.evidence??null});
   }
   if(!equalIds(localBefore,before)||!equalIds(localAfter,after))throw Error('Precise identity pairs must account for every relationship endpoint');
   for(const id of before)coveredBefore.add(id);for(const id of after)coveredAfter.add(id);
  }
  if(!equalIds(coveredBefore,new Set([...changed,...removed]))||!equalIds(coveredAfter,new Set([...changed,...added])))throw Error('Geometry relationships do not exhaustively account for identity changes');
  if(!Array.isArray(receipt.source_evidence)||!receipt.source_evidence.length||receipt.source_evidence.some(e=>!/^https?:\/\//.test(e.url??'')||!/^[a-f0-9]{64}$/.test(e.source_sha256??'')))throw Error('Geometry changes require inspected source URLs and reproducible source hashes');
  proofs.push({manifestFile:absolute,manifest_sha256:sha(fs.readFileSync(absolute)),receipt_sha256:pinned.sha256,manifest,receipt,changed,removed,added,reused,archives,pairs,files});
 }
 // Reconstruct the entire original footprint set, validating every unchanged
 // polygon as well as explicit edits. IDs alone are never evidence of equality.
 for(const proof of [...proofs].reverse()){
  const {receipt,changed,removed,added,reused,archives}=proof;
  if(footprintHash([...state.values()])!==receipt.after_footprints_sha256)throw Error('Current geometry contains an unreceipted footprint mutation or wrong migration order');
  if(!equalIds(new Set(state.keys()),new Set([...changed,...added,...reused])))throw Error('After-geometry identity inventory differs from validated receipt');
  for(const id of added)state.delete(id);for(const [id,feature] of archives)state.set(id,feature);
  if(!equalIds(new Set(state.keys()),new Set([...changed,...removed,...reused]))||footprintHash([...state.values()])!==receipt.before_footprints_sha256)throw Error('Archived originals do not reconstruct the pinned pre-migration footprints');
 }
 if(!equalIds(new Set(state.keys()),new Set(baselineIds)))throw Error('Location migration requires a separately validated footprint/identity crosswalk');
 if(footprintHash([...state.values()])!==baselineFootprints)throw Error('Names/membership-only release changed the pinned pre-migration location footprints');
 return {proofs,baselineFeatures:[...state.values()],pairs:proofs.flatMap(p=>p.pairs.map(row=>({...row,manifest_sha256:p.manifest_sha256,receipt_sha256:p.receipt_sha256,before_footprints_sha256:p.receipt.before_footprints_sha256,after_footprints_sha256:p.receipt.after_footprints_sha256}))),changedIds:new Set(proofs.flatMap(p=>[...p.changed])),retiredIds:new Set(proofs.flatMap(p=>[...p.removed])),addedIds:new Set(proofs.flatMap(p=>[...p.added]))};
}

const identity=row=>({id:row.id,name:row.name,parent_id:row.parent_id,kind:row.level??row.kind});
function descendantInventory(groups,locations){
 const members=new Map([...groups.keys()].map(id=>[id,new Set()]));
 for(const group of groups.values()){
  const tier=tiers.indexOf(group.kind);
  if(tier<0||tier===tiers.length-1||tier===0&&group.parent_id!==null||tier>0&&groups.get(group.parent_id)?.kind!==tiers[tier-1])throw Error('Metadata relationship has incomplete adjacent-tier group chains');
 }
 for(const location of locations.values()){
  if(location.kind!=='location')throw Error('Metadata relationship location identity has the wrong tier');
  let parent=location.parent_id;
  for(let tier=tiers.length-2;tier>=0;tier--){
   const group=groups.get(parent);
   if(group?.kind!==tiers[tier])throw Error('Metadata relationship has incomplete adjacent-tier location chains');
   members.get(parent).add(location.id);parent=group.parent_id;
  }
  if(parent!==null)throw Error('Metadata relationship continent has a parent');
 }
 if([...members.values()].some(ids=>!ids.size))throw Error('Metadata relationship has an empty active geographic group');
 return members;
}

/** Opt-in reference-only same-tier merges/splits, sourced creations and retirements. */
export function validateMetadataRelationships({beforeGroups,beforeLocations,beforeUnitRecords=null,receipt,receiptSha256,registry=null}){
 if(!Object.hasOwn(receipt,'relationships'))return [];
 if(!Array.isArray(receipt.relationships)||receipt.reference_only!==true||receipt.historical_claims_transferred!==false||receipt.summary?.geometry_changes!==0)throw Error('Metadata relationships require explicit reference-only evidence and zero history/geometry transfer');
 if(!/^[a-f0-9]{64}$/.test(receiptSha256??''))throw Error('Metadata relationship receipt hash is invalid');
 if(!Array.isArray(receipt.source_evidence)||!receipt.source_evidence.length||receipt.source_evidence.some(row=>!/^https?:\/\//.test(row.url??'')||!/^[a-f0-9]{64}$/.test(row.source_sha256??'')))throw Error('Metadata relationships require inspected source URLs and hashes');
 if(!Array.isArray(receipt.before_units)||receipt.before_units.some(row=>!row?.id)||new Set(receipt.before_units.map(row=>row.id)).size!==receipt.before_units.length)throw Error('Metadata relationships require the complete original unit archive');
 const archivedBefore=new Map(receipt.before_units.map(row=>[row.id,row]));
 if(!equalIds(new Set(archivedBefore.keys()),new Set(beforeGroups.keys()))||[...archivedBefore].some(([id,row])=>contentHash(identity(row))!==contentHash(identity(beforeGroups.get(id)))))throw Error('Metadata original unit archive differs from actual before identities');
 if(beforeUnitRecords&&(!equalIds(new Set(archivedBefore.keys()),new Set(beforeUnitRecords.keys()))||[...archivedBefore].some(([id,row])=>contentHash(row)!==contentHash(beforeUnitRecords.get(id)))))throw Error('Metadata original unit archive alters the exact retained before records');
 const groups=new Map(beforeGroups),locations=new Map(beforeLocations),deltas=new Map(),retired=new Set(),created=new Set();
 for(const delta of receipt.group_changes??[]){
  if(!delta?.id||deltas.has(delta.id))throw Error('Metadata group delta has an extra identity or altered original archive');
  if(!beforeGroups.has(delta.id)){
   if(delta.before!==null||!delta.after||delta.after.id!==delta.id||!tiers.slice(1,-1).includes(delta.after.level??delta.after.kind))throw Error('New metadata group needs an explicit null before record and same-tier split receipt');
   if(registry?.has(delta.id)&&registry.get(delta.id).kind!==(delta.after.level??delta.after.kind))throw Error('New metadata group changes a registered stable identity tier');
   created.add(delta.id);groups.set(delta.id,identity(delta.after));
  }else{
   if(!delta.before||delta.id!==delta.before.id||contentHash(delta.before)!==contentHash(archivedBefore.get(delta.id)))throw Error('Metadata group delta has an extra identity or altered original archive');
   if(delta.after){if(delta.id!==delta.after.id||(delta.after.level??delta.after.kind)!==beforeGroups.get(delta.id).kind)throw Error('Metadata group delta changes a stable identity tier');groups.set(delta.id,identity(delta.after));}
   else{retired.add(delta.id);groups.delete(delta.id);}
  }
  deltas.set(delta.id,delta);
 }
 const archivedRetired=new Map();
 for(const row of receipt.retired_units??[]){if(!row?.id||archivedRetired.has(row.id))throw Error('Duplicate retired metadata unit archive');archivedRetired.set(row.id,row);}
 if(!equalIds(new Set(archivedRetired.keys()),retired)||[...archivedRetired].some(([id,row])=>contentHash(row)!==contentHash(archivedBefore.get(id))))throw Error('Retired metadata units must retain their complete exact original records');
 const changedLocations=new Set();
 for(const delta of receipt.changed_location_properties??[]){
  const old=beforeLocations.get(delta.location_id),p=delta.after_properties,b=delta.before_properties;
  if(!old||changedLocations.has(delta.location_id)||!p||!b||p.id!==old.id||b.id!==old.id||contentHash(identity({...b,kind:'location'}))!==contentHash(identity(old)))throw Error('Metadata location delta has an extra identity or mismatched original properties');
  changedLocations.add(old.id);locations.set(old.id,identity({...p,kind:'location'}));
 }
 const beforeMembers=descendantInventory(beforeGroups,beforeLocations),afterMembers=descendantInventory(groups,locations),covered=new Set(),targets=new Map(),splits=new Map(),splitTargets=new Set(),createTargets=new Set(),oldTypes=new Map(),pairs=[];
 for(const relationship of receipt.relationships){
  const old=relationship?.old_entity_id,target=relationship?.new_entity_id,oldGroup=beforeGroups.get(old),survivor=groups.get(target),type=relationship?.change_type;
  if(!['merge','split','retire','create'].includes(type)||relationship.reference_only!==true||relationship.history_transfer!=='none')throw Error('Metadata relationship must be an explicit reference-only merge/split/retire/create without history transfer');
  if(type==='create'){
   if(old!==null||!created.has(target)||!survivor||createTargets.has(target)||splitTargets.has(target))throw Error('Metadata creation requires a unique new-group endpoint and explicit null old identity');
   const derived=relationship.derived_from_id;
   if(derived!==undefined&&(!beforeGroups.has(derived)||beforeGroups.get(derived).kind!==survivor.kind||registry&&(!registry.has(derived)||registry.get(derived).kind!==survivor.kind)))throw Error('Metadata creation derived-from identity must be an existing registered same-tier group');
   createTargets.add(target);pairs.push({old_entity_id:null,new_entity_id:target,change_type:type,receipt_sha256:receiptSha256,relationship,source_evidence:receipt.source_evidence});continue;
  }
  if(!retired.has(old)||!oldGroup||old===target||oldTypes.has(old)&&(oldTypes.get(old)!==type||type!=='split'))throw Error('Metadata relationship has extra, duplicate, unretired or missing endpoints');
  if(registry&&(!registry.get(old)||registry.get(old).kind!==oldGroup.kind))throw Error('Metadata relationship endpoints lack registered stable same-tier identities');
  oldTypes.set(old,type);covered.add(old);
  if(type==='retire'){
   if(target!==null||!['province','area'].includes(oldGroup.kind))throw Error('Explicit metadata retirement requires a null successor and a local province/area identity');
   for(const id of beforeMembers.get(old))if(!locations.has(id))throw Error('Metadata retirement cannot drop descendant locations');
  }else if(type==='merge'){
   if(!beforeGroups.has(target)||!survivor)throw Error('Metadata merge has extra, duplicate, unretired or missing endpoints');
   if(oldGroup.kind==='continent'||oldGroup.kind!==survivor.kind||oldGroup.parent_id!==beforeGroups.get(target).parent_id||survivor.parent_id!==beforeGroups.get(target).parent_id)throw Error('Metadata merge requires existing same-tier groups with the same unchanged adjacent-tier parent');
   if(registry&&(!registry.get(target)||registry.get(target).kind!==survivor.kind))throw Error('Metadata merge endpoints lack registered stable same-tier identities');
   if(!targets.has(target))targets.set(target,new Set(beforeMembers.get(target)));
   const union=targets.get(target);for(const id of beforeMembers.get(old)){if(union.has(id))throw Error('Metadata merge original member footprints overlap');union.add(id);}
  }else{
   if(!created.has(target)||!survivor||splitTargets.has(target)||createTargets.has(target))throw Error('Metadata split has extra, duplicate, or unreceipted successor endpoints');
   if(oldGroup.kind==='continent'||oldGroup.kind!==survivor.kind||survivor.parent_id!==oldGroup.parent_id||!groups.has(oldGroup.parent_id)||groups.get(oldGroup.parent_id).parent_id!==beforeGroups.get(oldGroup.parent_id)?.parent_id)throw Error('Metadata split requires same-tier successors under the same unchanged adjacent-tier parent');
   splitTargets.add(target);if(!splits.has(old))splits.set(old,[]);splits.get(old).push(target);
  }
  pairs.push({old_entity_id:old,new_entity_id:target,change_type:type,receipt_sha256:receiptSha256,relationship,source_evidence:receipt.source_evidence});
 }
 if(!equalIds(covered,retired))throw Error('Metadata crosswalk must account for every retired parent exactly once (or every explicit split successor)');
 if(!equalIds(new Set([...splitTargets,...createTargets]),created))throw Error('Every new metadata group requires exactly one explicit split successor or create relationship');
 for(const [target,union] of targets)if(!equalIds(union,afterMembers.get(target)))throw Error('Metadata merge must conserve the exact union of original descendant location footprints');
 for(const [old,successors] of splits){
  if(successors.length<2)throw Error('Metadata split requires at least two unique successors');
  const union=new Set();for(const target of successors)for(const id of afterMembers.get(target)){if(union.has(id))throw Error('Metadata split successor member footprints overlap');union.add(id);}
  if(!equalIds(union,beforeMembers.get(old)))throw Error('Metadata split must conserve the exact disjoint union of original descendant location footprints');
 }
 for(const pair of pairs.filter(pair=>['merge','split'].includes(pair.change_type))){const parent=beforeGroups.get(pair.old_entity_id).parent_id;if(!equalIds(beforeMembers.get(parent),afterMembers.get(parent)))throw Error('Metadata merge/split changes its containing parent footprint');}

 return pairs;
}

function validateReviewedIdentities({original,current,migration,geometryProof,metadataProofs,registry}){
 const expectedGroups=new Map([...original.values()].filter(e=>e.active&&e.kind!=='location').map(e=>[e.id,{id:e.id,name:e.name,parent_id:e.parent_id,kind:e.kind}]));
 const expectedLocations=new Map([...original.values()].filter(e=>e.active&&e.kind==='location').map(e=>[e.id,{id:e.id,name:e.name,parent_id:e.parent_id,kind:'location'}]));
 const expectedUnitRecords=new Map((migration.before_units??[]).map(row=>[row.id,row]));
 const putGroup=row=>{if(row){expectedGroups.set(row.id,{id:row.id,name:row.name,parent_id:row.parent_id,kind:row.level??row.kind});expectedUnitRecords.set(row.id,row);}};
 const removeGroup=id=>{expectedGroups.delete(id);expectedUnitRecords.delete(id);};
 for(const row of migration.group_changes??[]){if(row.after)putGroup(row.after);else removeGroup(row.id);}
 for(const row of migration.changes??[]){const p=row.after_properties;if(p)expectedLocations.set(row.location_id,{id:row.location_id,name:p.name,parent_id:p.parent_id,kind:'location'});}
 for(const proof of geometryProof.proofs){
  const hierarchy=proof.files['after/hierarchy.json']??proof.files['after-hierarchy.json'];
  if(hierarchy){expectedGroups.clear();expectedUnitRecords.clear();for(const row of read(hierarchy.file))putGroup(row);}
  else for(const row of proof.receipt.retired_units??[])removeGroup(row.id);
  for(const id of proof.removed)expectedLocations.delete(id);
  const newRows=new Map((proof.receipt.new_entities??proof.receipt.added_features??[]).map(row=>{const p=row.properties??row;return [p.id,{id:p.id,name:p.name,parent_id:p.parent_id,kind:row.kind??'location'}];}));
  for(const id of proof.added){const row=newRows.get(id);if(!row||row.kind!=='location'||!row.name||!row.parent_id)throw Error('New location requires its precise sourced name/parent definition in the receipt');expectedLocations.set(id,row);}
 }
 const metadataRelationships=new Map(),metadataCreatedRelationships=new Map();
 for(const proof of metadataProofs){
  const proofPairs=validateMetadataRelationships({beforeGroups:expectedGroups,beforeLocations:expectedLocations,beforeUnitRecords:expectedUnitRecords,receipt:proof.receipt,receiptSha256:proof.sha256,registry});
  for(const old of new Set(proofPairs.filter(pair=>pair.old_entity_id!==null).map(pair=>pair.old_entity_id))){
   if(metadataRelationships.has(old))throw Error('Duplicate retired metadata relationship across receipts');
   metadataRelationships.set(old,proofPairs.filter(pair=>pair.old_entity_id===old));
  }
  for(const pair of proofPairs.filter(pair=>pair.old_entity_id===null)){
   if(metadataCreatedRelationships.has(pair.new_entity_id))throw Error('Duplicate created metadata relationship across receipts');
   metadataCreatedRelationships.set(pair.new_entity_id,pair);
  }
  for(const row of proof.receipt.group_changes??[]){if(row.after)putGroup(row.after);else removeGroup(row.id);}
  for(const row of proof.receipt.changed_location_properties??[]){const p=row.after_properties;if(!expectedLocations.has(row.location_id))throw Error('Metadata change targets an unmatched/retired location identity');expectedLocations.set(row.location_id,{id:row.location_id,name:p.name,parent_id:p.parent_id,kind:'location'});}
 }
 const expected=new Map([...expectedGroups,...expectedLocations]);
 if(!equalIds(new Set(expected.keys()),new Set(current.keys())))throw Error('Unreceipted geographic identity creation/retirement');
 for(const [id,now] of current){const wanted=expected.get(id);if(now.kind!==wanted.kind||now.name!==wanted.name||now.parent_id!==wanted.parent_id)throw Error(`Unreceipted geographic name/parent mutation: ${id}`);}
 for(const pair of [...metadataRelationships.values()].flat())if(current.has(pair.old_entity_id)||pair.new_entity_id!==null&&current.get(pair.new_entity_id)?.kind!==registry.get(pair.old_entity_id)?.kind)throw Error('Metadata relationship is inconsistent with the final active geography');
 for(const id of metadataCreatedRelationships.keys())if(!current.has(id))throw Error('Created metadata identity is missing from the final active geography');
 return {retired:metadataRelationships,created:metadataCreatedRelationships};
}

/** Prepare immutable reference membership versions; never overwrite the catalog. */
export async function prepareGeographicRelease({data='data',geographyData=data,output='data/geographic-releases',referenceDate='2026-10-01',geometryManifests=null,metadataMigrations=null,reviewedVersion=2,registryManifests=[]}={}){
 if(!Number.isInteger(reviewedVersion)||reviewedVersion<2)throw Error('Reviewed release version must be an integer greater than baseline version 1');
 if(!/^\d{4}-\d{2}-\d{2}$/.test(referenceDate)||!Number(referenceDate.slice(0,4))||Number.isNaN(Date.parse(referenceDate))||new Date(referenceDate).toISOString().slice(0,10)!==referenceDate)throw Error('Reference date must be a valid ISO calendar date without year zero');
 const referenceYear=Number(referenceDate.slice(0,4));
 const original=new Map(),catalog=read(`${data}/hosted-catalog/index.json`);
 for(const part of catalog.batches.filter(p=>p.kind==='entities')){
  const bytes=fs.readFileSync(`${data}/hosted-catalog/${part.path}`);
  if(sha(bytes)!==part.sha256)throw Error(`Immutable catalog hash mismatch: ${part.path}`);
  for(const entity of JSON.parse(bytes).entities)if(tiers.includes(entity.kind))original.set(entity.id,entity);
 }
 const registry=new Map(original),registryPins={};
 for(const file of registryManifests){const absolute=path.resolve(file),manifest=read(absolute),base=path.dirname(absolute);registryPins[sha(fs.readFileSync(absolute))]=manifest.releases?.at(-1)?.id??null;for(const part of manifest.batches.filter(p=>p.kind==='entities'||p.route==='/api/records/import')){const raw=fs.readFileSync(safeProofFile(base,part.path));if(sha(raw)!==part.sha256)throw Error('Registered identity manifest hash mismatch');for(const e of JSON.parse(raw).entities??[])if(tiers.includes(e.kind)){if(registry.has(e.id)&&json(canonical(registry.get(e.id)))!==json(canonical(e)))throw Error('Immutable registered identity definition changed');registry.set(e.id,e);}}}
 const units=read(`${geographyData}/hierarchy.json`),features=read(`${geographyData}/world-index.json`).parts.flatMap(p=>read(`${geographyData}/${p}`).features);
 const migration=read(`${data}/geographic-decision-migration.json.gz`),current=new Map(units.map(u=>[u.id,{...u,kind:u.level}]));
 for(const f of features)current.set(f.id,{id:f.id,kind:'location',name:f.properties.name,parent_id:f.properties.parent_id,metadata:f.properties.metadata});
 const oldLocationIds=[...original.values()].filter(e=>e.kind==='location'&&e.active===1).map(e=>e.id).sort();
 const footprints=footprintHash(features),pinnedFootprints=read(`${data}/macro-corrections.json`).footprints_sha256_before;
 if(!/^[a-f0-9]{64}$/.test(pinnedFootprints))throw Error('Original baseline footprint pin is missing');
 const manifestFiles=geometryManifests??(footprints!==pinnedFootprints&&fs.existsSync(`${data}/geographic-repair-evidence/index.json`)?[`${data}/geographic-repair-evidence/index.json`]:[]);
 const geometryProof=validateGeometryMigrations({features,baselineIds:oldLocationIds,baselineFootprints:pinnedFootprints,manifestFiles});
 const extraMigrations=metadataMigrations??(geometryProof.proofs.length&&fs.existsSync(`${data}/macro-boundary-migration.json.gz`)?[`${data}/macro-boundary-migration.json.gz`]:[]);
 const metadataProofs=extraMigrations.map(file=>({file,sha256:sha(fs.readFileSync(file)),receipt:read(file)}));
 for(const proof of metadataProofs)if(proof.receipt.historical_claims_transferred!==false||proof.receipt.summary?.geometry_changes!==0)throw Error('Metadata migration may not alter footprints or transfer historical claims');
 for(const [id,now] of current)if(registry.has(id)&&registry.get(id).kind!==now.kind)throw Error(`Immutable geographic identity tier changed: ${id}`);
 const {retired:metadataRelationships,created:metadataCreatedRelationships}=validateReviewedIdentities({original,current,migration,geometryProof,metadataProofs,registry});
 const decisionFiles=fs.readdirSync(`${data}/geographic-decisions`).filter(f=>f.endsWith('.json')).sort();
 if(decisionFiles.length!==6)throw Error('Six continent review files are required');
 const proofs=Object.fromEntries(decisionFiles.map(f=>[f,sha(fs.readFileSync(`${data}/geographic-decisions/${f}`))]));
 const documents=decisionFiles.map(f=>read(`${data}/geographic-decisions/${f}`)),decisions=new Map(documents.flatMap(d=>d.decisions).map(r=>[r.id,r]));
 const migrationHash=sha(fs.readFileSync(`${data}/geographic-decision-migration.json.gz`));
 const proofPins=Object.fromEntries(geometryProof.proofs.map((p,i)=>[`geometry-${i}`,{manifest_sha256:p.manifest_sha256,receipt_sha256:p.receipt_sha256,before_footprints_sha256:p.receipt.before_footprints_sha256,after_footprints_sha256:p.receipt.after_footprints_sha256}]));
 const metadataPins=Object.fromEntries(metadataProofs.map((p,i)=>[`metadata-${i}`,p.sha256]));
 const releaseInputs=geometryProof.proofs.length||metadataProofs.length?[proofs,migrationHash,referenceDate,proofPins,metadataPins,footprints]:[proofs,migrationHash,referenceDate];
 if(reviewedVersion!==2||registryManifests.length)releaseInputs.push({reviewed_version:reviewedVersion,registered_identity_manifest_sha256:registryPins});
 const releaseKey=sha(json(releaseInputs));
 const source={id:`source:atlas:geographic-review:${releaseKey}`,name:'Worldwide inspected reference-geography decisions',url:null,license:'Original source licenses retained in each cited continent decision',vintage:referenceDate,status:'reference',supported_from:referenceYear,supported_to:referenceYear+1,metadata:{reference_only:true,historical_membership_not_asserted:true,decision_sha256:proofs,migration_sha256:migrationHash}};
 if(registryManifests.length)source.metadata.registered_identity_manifest_sha256=registryPins;
 if(geometryProof.proofs.length||metadataProofs.length){source.metadata.geometry_proof_sha256=proofPins;source.metadata.metadata_migration_sha256=metadataPins;}
 const retained={id:`source:atlas:geographic-baseline:${catalog.archive_sha256}`,name:'Retained original atlas reference memberships',url:null,license:'Original source licenses retained in immutable archive',vintage:'Original source vintages retained; modern reference context',status:'reference',supported_from:2026,supported_to:2027,metadata:{reference_only:true,historical_membership_not_asserted:true,archive_sha256:catalog.archive_sha256}};
 const newEntities=[...current.values()].filter(e=>!registry.has(e.id)).map(e=>({id:e.id,kind:e.kind,name:e.name,parent_id:e.parent_id,source_id:source.id,active:1,is_example:0,metadata:{reference_context:true,decision_file:decisions.get(e.id)?.evidence??[],history_transfer:'none'}}));
 if(newEntities.some(e=>e.kind==='location'&&!geometryProof.addedIds.has(e.id)))throw Error('New location identity lacks a validated footprint/identity receipt');
 const commonEvidence={reference_only:true,history_transfer:'none'};
 const baseline=[...original.values()].map(e=>({entity_id:e.id,kind:e.kind,parent_id:e.parent_id,reference_name:e.name,active:e.active,source_id:retained.id,evidence:{...commonEvidence,original_source_id:e.source_id,original_archive_sha256:catalog.archive_sha256}}));
 const memberships=[...registry.values(),...newEntities].map(e=>{
  const now=current.get(e.id),decision=decisions.get(e.id),evidence={...commonEvidence,original_source_id:e.source_id,migration_sha256:migrationHash};
  if(decision)evidence.decision={id:e.id,action:decision.action,evidence:decision.evidence,boundary_status:decision.boundary_status};
  else if(now?.metadata?.semantic_review)evidence.location_review=now.metadata.semantic_review;
  if(geometryProof.changedIds.has(e.id)||geometryProof.retiredIds.has(e.id)||geometryProof.addedIds.has(e.id))evidence.geometry_migration={proof_sha256:proofPins,footprint_changed:geometryProof.changedIds.has(e.id),retired:geometryProof.retiredIds.has(e.id),added:geometryProof.addedIds.has(e.id),history_transfer:'none'};
  if(metadataProofs.length)evidence.metadata_migration_sha256=metadataPins;
  if(Buffer.byteLength(json(evidence))>16384)throw Error(`Membership evidence exceeds bounded size: ${e.id}`);
  return {entity_id:e.id,kind:e.kind,parent_id:now?.parent_id??e.parent_id,reference_name:now?.name??e.name,active:Number(Boolean(now)),source_id:source.id,evidence};
 });
 const activeMembers=new Map(memberships.filter(m=>m.active).map(m=>[m.entity_id,m]));
 for(const m of activeMembers.values()){const tier=tiers.indexOf(m.kind);if(tier===0){if(m.parent_id!==null)throw Error('Continent cannot have a parent');}else if(activeMembers.get(m.parent_id)?.kind!==tiers[tier-1])throw Error(`Incomplete adjacent-tier parent chain: ${m.entity_id}`);}
 const changes=[];
 for(const e of memberships){
  const old=registry.get(e.entity_id),decision=decisions.get(e.entity_id);
  const add=(type,target=e.entity_id)=>changes.push({id:`${releaseKey}:${type}:${e.entity_id}`,old_entity_id:old?e.entity_id:null,new_entity_id:target,change_type:type,source_id:source.id,evidence:{...commonEvidence,migration_sha256:migrationHash,decision:decision?{action:decision.action,rationale:decision.rationale,evidence:decision.evidence}:null,before:old?{name:old.name,parent_id:old.parent_id,active:old.active}:null,after:{name:e.reference_name,parent_id:e.parent_id,active:e.active}}});
  if(!old){add('create');const pair=metadataCreatedRelationships.get(e.entity_id);if(pair)changes.at(-1).evidence.metadata_relationship=metadataRelationshipEvidence(pair);}
  else if((old.active||metadataRelationships.has(e.entity_id))&&e.active===0){const locationPairs=geometryProof.pairs.filter(p=>p.old_entity_id===e.entity_id&&p.old_entity_id!==p.new_entity_id),metadataPairs=metadataRelationships.get(e.entity_id);if(!locationPairs.length){if(metadataPairs){for(const pair of metadataPairs){add(pair.change_type,pair.new_entity_id);if(pair.change_type==='split')changes.at(-1).id+=`:${pair.new_entity_id}`;changes.at(-1).evidence.metadata_relationship=metadataRelationshipEvidence(pair);}}else add(decision?.action==='merge'?'merge':'retire',decision?.action==='merge'?decision.target_id:null);}}
  else if(e.active){if(old.name!==e.reference_name)add('rename');if(old.parent_id!==e.parent_id)add('reparent');}
 }
 for(const [at,pair] of geometryProof.pairs.entries())if(pair.old_entity_id!==pair.new_entity_id||current.has(pair.new_entity_id))changes.push({id:`${releaseKey}:geometry:${at}:${pair.old_entity_id}`,old_entity_id:pair.old_entity_id,new_entity_id:pair.new_entity_id,change_type:pair.change_type,source_id:source.id,evidence:{...commonEvidence,geometry_migration:pair,migration_sha256:migrationHash}});
 // Resolve merge chains so every retired ID points to the surviving identity.
 const byId=new Map(memberships.map(e=>[e.entity_id,e]));
 for(const change of changes.filter(c=>['merge','split','replace'].includes(c.change_type))){
  const visited=new Set();while(!byId.get(change.new_entity_id)?.active){if(visited.has(change.new_entity_id))throw Error('Crosswalk merge cycle');visited.add(change.new_entity_id);const next=decisions.get(change.new_entity_id),geometryNext=geometryProof.pairs.find(p=>p.old_entity_id===change.new_entity_id&&p.old_entity_id!==p.new_entity_id);if(next?.action!=='merge'&&!geometryNext)throw Error('Merge target is not active');change.new_entity_id=next?.target_id??geometryNext.new_entity_id;}
 }
 
 const counts=members=>Object.fromEntries([...tiers].reverse().map(k=>[k,members.filter(e=>e.kind===k&&e.active).length]));
 async function manifest(id,version,rows,delta,sourceId,hierarchyHash,footprintVersion){return {id,version,source_id:sourceId,reference_date:version===1?'2026-10-01':referenceDate,hierarchy_sha256:hierarchyHash,footprints_sha256:footprintVersion,membership_sha256:await geographicMembershipHash(rows),location_ids_sha256:await geographicLocationIdsHash(rows),changes_sha256:await geographicChangesHash(delta),expected_counts:counts(rows),metadata:{reference_only:true,historical_membership_not_asserted:true,original_registry_preserved:true,decision_sha256:proofs,migration_sha256:migrationHash}};}
 const releases=[{release:await manifest(`geography:baseline:${catalog.archive_sha256}`,1,baseline,[],retained.id,sha(json(migration.before_units)),pinnedFootprints),memberships:baseline,changes:[]},{release:await manifest(`geography:review:${releaseKey}`,reviewedVersion,memberships,changes,source.id,sha(fs.readFileSync(`${geographyData}/hierarchy.json`)),footprints),memberships,changes}];
 if(geometryProof.proofs.length||metadataProofs.length){releases[1].release.metadata.geometry_proof_sha256=proofPins;releases[1].release.metadata.metadata_migration_sha256=metadataPins;}
 if(registryManifests.length)releases[1].release.metadata.registered_identity_manifest_sha256=registryPins;
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
 if(registryManifests.length)result.registered_identity_manifest_sha256=registryPins;
 if(geometryProof.proofs.length||metadataProofs.length)result.validated_geometry={baseline_footprints_sha256:pinnedFootprints,current_footprints_sha256:footprints,proof_sha256:proofPins,metadata_migration_sha256:metadataPins,changed_location_ids:[...geometryProof.changedIds].sort(),retired_location_ids:[...geometryProof.retiredIds].sort(),added_location_ids:[...geometryProof.addedIds].sort(),history_transfer:'none'};
 fs.writeFileSync(`${output}/index.json`,JSON.stringify(result,null,2));
 return result;
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const options={};for(let at=2;at<process.argv.length;at++){const key=process.argv[at],value=process.argv[++at];if(!value)throw Error(`Missing value for ${key}`);if(key==='--data')options.data=value;else if(key==='--geography-data')options.geographyData=value;else if(key==='--output')options.output=value;else if(key==='--reference-date')options.referenceDate=value;else if(key==='--reviewed-version')options.reviewedVersion=Number(value);else if(key==='--registry-manifest')(options.registryManifests??=[]).push(value);else if(key==='--geometry-manifest')(options.geometryManifests??=[]).push(value);else if(key==='--metadata-migration')(options.metadataMigrations??=[]).push(value);else throw Error(`Unknown option ${key}`);}
 const result=await prepareGeographicRelease(options);console.log(JSON.stringify({new_entities:result.new_entities,total_memberships:result.total_memberships,changes:result.changes,batches:result.batches.length,releases:result.releases.map(r=>({id:r.id,counts:r.expected_counts,footprints_sha256:r.footprints_sha256}))}));
}
