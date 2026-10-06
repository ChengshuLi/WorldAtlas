// Independently read the complete predecessor and prepared delta; never import.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {isDeepStrictEqual} from 'node:util';
import {decodeGeographicReleaseBatch,readGeographicReleaseManifest} from '../../../scripts/read-geographic-release-manifest.mjs';
import {geographicMembershipHash,geographicLocationIdsHash,geographicChangesHash} from '../../../hosted/geographic-releases.js';
import {committedPreparationFiles,requirePlainExecution} from '../../../scripts/native-ownership/native-preparation-guards.mjs';

requirePlainExecution();
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const prefix='coordination/engineering/iran-pakistan-offline-integration-991-20261006-local22';
const [inputName,outName]=process.argv.slice(2),input=path.resolve(root,inputName??''),out=path.resolve(root,outName??'');
if(![input,out].every(p=>p.startsWith(path.join(root,prefix)+path.sep))||fs.existsSync(out))throw Error('Owned input and exclusive new receipt required');
const head=execFileSync('git',['-C',root,'rev-parse','HEAD'],{encoding:'utf8'}).trim();
const executed=committedPreparationFiles(root,head,['package.json',prefix+'/verify-successor.mjs',
  'scripts/read-geographic-release-manifest.mjs','hosted/geographic-releases.js','scripts/native-ownership/native-preparation-guards.mjs']);
const digest=raw=>createHash('sha256').update(raw).digest('hex');
const baseline='d0cc67eac85038159f88a673acbc39b77ab7461d';
const read=name=>execFileSync('git',['-C',root,'show',baseline+':data/geographic-releases/'+name],{maxBuffer:32*1024*1024});
const oldPointer=JSON.parse(read('current-manifest.json')),oldRaw=read(oldPointer.path);
if(digest(oldRaw)!==oldPointer.sha256)throw Error('Predecessor manifest hash differs');
const old=JSON.parse(gunzipSync(oldRaw)),next=readGeographicReleaseManifest(input),previous=old.releases.at(-1),release=next.releases.at(-1);
const prep=JSON.parse(fs.readFileSync(path.join(input,'preparation.json')));
const oldMembers=[],oldChanges=[],members=[],changes=[],sources=[];
for(const part of old.batches.filter(p=>/^6-(memberships|changes)-/.test(p.path))){
  const row=JSON.parse(decodeGeographicReleaseBatch(read(part.path),part));
  if(row.release_id!==previous.id)throw Error('Predecessor release ID differs');
  oldMembers.push(...row.memberships??[]);oldChanges.push(...row.changes??[]);
}
const newParts=next.batches.slice(old.batches.length),products=[];
for(const name of fs.readdirSync(input).sort()){
  const raw=fs.readFileSync(path.join(input,name));products.push({path:name,bytes:raw.length,sha256:digest(raw)});
}
for(const part of newParts){
  const payload=decodeGeographicReleaseBatch(fs.readFileSync(path.join(input,part.path)),part),row=JSON.parse(payload);
  if(payload.length>1048576||(row.memberships?.length??0)+(row.changes?.length??0)+Number(Boolean(row.release))>250)throw Error('Atomic API batch limit exceeded');
  if(row.memberships||row.changes){if(row.release_id!==release.id)throw Error('Successor batch ID differs');}
  if(row.release&&!isDeepStrictEqual(row.release,release))throw Error('Staged release object differs');
  members.push(...row.memberships??[]);changes.push(...row.changes??[]);sources.push(...row.sources??[]);
}
if(!fs.readFileSync(path.join(input,'index.json')).equals(read('index.json'))||
  await geographicMembershipHash(oldMembers)!==previous.membership_sha256||await geographicLocationIdsHash(oldMembers)!==previous.location_ids_sha256||
  await geographicChangesHash(oldChanges)!==previous.changes_sha256)throw Error('Complete predecessor registry differs');
const migrationRaw=fs.readFileSync(path.join(root,prefix,'release-proof-v3/migration-receipt.json')),migration=JSON.parse(migrationRaw),target=new Set(migration.changed_ids);
const validationRaw=fs.readFileSync(path.join(root,prefix,'release-proof-v3/validation.json'));
const expectedProof={commit:prep.evaluation_commit,path:prefix+'/release-proof-v3/migration-receipt.json',sha256:digest(migrationRaw),
  validation_path:prefix+'/release-proof-v3/validation.json',validation_sha256:digest(validationRaw),
  before_footprints_sha256:migration.before_footprints_sha256,after_footprints_sha256:migration.after_footprints_sha256,history_transfer:'none'};
const originalById=new Map(oldMembers.map(row=>[row.entity_id,row]));
const expectedSource={id:release.source_id,name:'Joint Saravan–Panjgur modern reference seam',url:'https://www.openstreetmap.org/copyright',
  license:'ODbL 1.0 for new OSM-derived seam data; retained base source notices preserved',
  vintage:'OSM snapshots retrieved 2026-10-05; no effective boundary date asserted',status:'reference',supported_from:2026,supported_to:2027,
  metadata:{reference_only:true,historical_membership_not_asserted:true,history_transfer:'none',predecessor_release:previous.id,
    predecessor_manifest:{commit:baseline,path:'data/geographic-releases/'+oldPointer.path,sha256:oldPointer.sha256},
    predecessor_proof_chronology:previous.metadata.geometry_proof_sha256,identity_proof_sequence:previous.metadata.identity_proof_sequence,
    geometry_migration:expectedProof,source_policy:migration.source_policy,source_evidence:migration.source_evidence,
    source_offer:'Exact original OSM county/way snapshots and complete joint derivative geography are retained in the primary repository with original notices and hashes.',
    unresolved_source_limits:migration.source_policy.unknown}};
// JSON transport omits undefined predecessor fields; compare the actual schema.
const expectedSourceDocument=JSON.parse(JSON.stringify(expectedSource));
async function compare(candidate,rows,delta,sourceRows){
  const last=candidate.releases.at(-1);
  if(!isDeepStrictEqual(candidate.releases.slice(0,-1),old.releases)||!isDeepStrictEqual(candidate.batches.slice(0,old.batches.length),old.batches)||
    !isDeepStrictEqual(candidate.sources_batches.slice(0,old.sources_batches.length),old.sources_batches))throw Error('Predecessor history rewritten');
  if(last.version!==7||last.id!==prep.successor_release_id||last.metadata.predecessor_release_id!==previous.id||
    last.metadata.predecessor_manifest_sha256!==oldPointer.sha256||last.hierarchy_sha256!==previous.hierarchy_sha256||
    last.footprints_sha256!==migration.after_footprints_sha256||last.location_ids_sha256!==previous.location_ids_sha256||
    !isDeepStrictEqual(last.expected_counts,previous.expected_counts)||!isDeepStrictEqual(last.metadata.geometry_migration,expectedProof))throw Error('Successor release identity/source pins differ');
  if(rows.length!==oldMembers.length||new Set(rows.map(r=>r.entity_id)).size!==rows.length)throw Error('Complete membership roster differs');
  const byId=new Map(rows.map(r=>[r.entity_id,r]));
  for(const original of oldMembers){
    const row=byId.get(original.entity_id);
    if(!target.has(original.entity_id)){
      if(!isDeepStrictEqual(row,original))throw Error('Non-target original evidence/identity mutated');
    }else{
      for(const key of Object.keys(original).filter(k=>!['source_id','evidence'].includes(k)))
        if(!isDeepStrictEqual(row[key],original[key]))throw Error('Target stable identity/parent/status mutated');
      if(row.source_id!==last.source_id||row.evidence.history_transfer!=='none'||row.evidence.reference_only!==true||
        !isDeepStrictEqual(row.evidence.geometry_migration,expectedProof)||row.evidence.predecessor_release_id!==previous.id||row.evidence.predecessor_membership_sha256!==previous.membership_sha256)throw Error('Target source migration differs');
      for(const [key,value] of Object.entries(original.evidence))if(!isDeepStrictEqual(row.evidence[key],value))throw Error('Original target evidence lost');
    }
    if(Buffer.byteLength(JSON.stringify(row.evidence))>16384)throw Error('Membership evidence exceeds API limit');
  }
  if(await geographicMembershipHash(rows)!==last.membership_sha256||await geographicLocationIdsHash(rows)!==last.location_ids_sha256||
    await geographicChangesHash(delta)!==last.changes_sha256)throw Error('Successor full membership/change hashes differ');
  if(delta.length!==2||new Set(delta.map(r=>r.new_entity_id)).size!==2||delta.some(r=>r.old_entity_id!==r.new_entity_id||!target.has(r.new_entity_id)||
    r.change_type!=='retain'||r.source_id!==last.source_id||r.evidence.history_transfer!=='none'||r.evidence.reference_only!==true||
    !isDeepStrictEqual(r.evidence.geometry_migration,expectedProof)||!isDeepStrictEqual(r.evidence.original_source_evidence,originalById.get(r.old_entity_id)?.evidence)))throw Error('Unsupported identity/history transfer');
  if(sourceRows.length!==1||!isDeepStrictEqual(sourceRows[0],expectedSourceDocument))throw Error('Exact source provenance, terms or limitations changed');
  if(candidate.new_entities!==old.new_entities||candidate.changes!==old.changes+2||candidate.total_memberships!==Math.max(old.total_memberships,rows.length))throw Error('Cumulative counters differ');
  return true;
}
await compare(next,members,changes,sources);
const controls=[];
async function reject(name,mutate){
  const c=structuredClone(next),r=structuredClone(members),d=structuredClone(changes),s=structuredClone(sources);mutate(c,r,d,s);
  let error;try{await compare(c,r,d,s);}catch(e){error=e.message;}
  if(!error)throw Error('Mutation control accepted: '+name);controls.push({name,outcome:'rejected',error});
}
await reject('rewritten predecessor history',c=>{c.releases[0].reference_date='2020-01-01';});
await reject('target parent mutation',(_,r)=>{r.find(x=>target.has(x.entity_id)).parent_id='wrong-parent';});
await reject('non-target evidence mutation',(_,r)=>{r.find(x=>!target.has(x.entity_id)).evidence.unreviewed=true;});
await reject('historical transfer',(_,r,d)=>{d[0].evidence.history_transfer='all';});
await reject('wrong predecessor',c=>{c.releases.at(-1).metadata.predecessor_manifest_sha256='0'.repeat(64);});
await reject('rehashed changed source URL',(_,r,d,s)=>{s[0].url='https://example.org/wrong';});
await reject('rehashed changed source license',(_,r,d,s)=>{s[0].license='Unknown';});
await reject('rehashed changed source vintage',(_,r,d,s)=>{s[0].vintage='1900';});
await reject('rehashed removed source limits',(_,r,d,s)=>{s[0].metadata.unresolved_source_limits=[];});
await reject('rehashed changed source evidence',(_,r,d,s)=>{s[0].metadata.source_evidence=[];});
await reject('rehashed changed source offer',(_,r,d,s)=>{s[0].metadata.source_offer='Not retained';});
await reject('changed target geometry proof',(_,r)=>{r.find(x=>target.has(x.entity_id)).evidence.geometry_migration.sha256='0'.repeat(64);});
await reject('changed retained original change evidence',(_,r,d)=>{d[0].evidence.original_source_evidence={};});
const part=newParts.find(p=>p.path.startsWith('7-memberships-')),damaged=Buffer.from(fs.readFileSync(path.join(input,part.path)));damaged[damaged.length-1]^=1;
let caught=false;try{decodeGeographicReleaseBatch(damaged,part);}catch{caught=true;}if(!caught)throw Error('Changed batch accepted');
controls.push({name:'altered encoded membership batch',outcome:'rejected'});
const receipt={version:1,evaluation_commit:head,executed_sources:executed,products,predecessor_release:previous.id,successor_release:release.id,
  complete_memberships:members.length,non_target_memberships_preserved:members.length-2,retained_target_identities:2,
  predecessor_release_objects_preserved:old.releases.length,predecessor_batches_preserved:old.batches.length,
  historical_claims_transferred:false,counts:release.expected_counts,controls,installed:false,published:false,
  limits:['Offline delta readback and identity/history preservation; no delivery or geographic approval.']};
fs.writeFileSync(out,JSON.stringify(receipt)+'\n',{flag:'wx'});console.log(JSON.stringify({memberships:members.length,controls:controls.length,release:release.id,installed:false}));
