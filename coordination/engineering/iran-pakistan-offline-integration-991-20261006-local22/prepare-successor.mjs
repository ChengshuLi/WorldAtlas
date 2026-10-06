// Append a geometry-only modern reference release to the verified predecessor.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gzipSync,gunzipSync} from 'node:zlib';
import {isDeepStrictEqual} from 'node:util';
import {readGeographicReleaseManifest,decodeGeographicReleaseBatch} from '../../../scripts/read-geographic-release-manifest.mjs';
import {geographicMembershipHash,geographicLocationIdsHash,geographicChangesHash} from '../../../hosted/geographic-releases.js';
import {committedPreparationFiles,requirePlainExecution} from '../../../scripts/native-ownership/native-preparation-guards.mjs';

requirePlainExecution();
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..'),prefix='coordination/engineering/iran-pakistan-offline-integration-991-20261006-local22';
const [migrationName,outName]=process.argv.slice(2),out=path.resolve(root,outName??'');
if(!migrationName?.startsWith(prefix+'/')||!out.startsWith(path.join(root,prefix)+path.sep)||fs.existsSync(out))throw Error('Committed migration and fresh owned output required');
const head=execFileSync('git',['-C',root,'rev-parse','HEAD'],{encoding:'utf8'}).trim(),digest=raw=>createHash('sha256').update(raw).digest('hex');
const producer=committedPreparationFiles(root,head,['package.json',prefix+'/prepare-successor.mjs','scripts/read-geographic-release-manifest.mjs',
  'hosted/geographic-releases.js','hosted/store.js','scripts/native-ownership/native-preparation-guards.mjs']);
const migrationRaw=execFileSync('git',['-C',root,'show',head+':'+migrationName],{maxBuffer:32*1024*1024});
if(!migrationRaw.equals(fs.readFileSync(path.join(root,migrationName))))throw Error('Commit migration evidence before preparing release');
const migration=JSON.parse(migrationRaw),validationName=path.posix.dirname(migrationName)+'/validation.json';
const validationRaw=execFileSync('git',['-C',root,'show',head+':'+validationName],{maxBuffer:32*1024*1024}),validation=JSON.parse(validationRaw);
if(!validation.exact_staged_original_archive_checked||validation.complete_staged_partitions_semantically_checked?.length!==2||
  migration.historical_claims_transferred!==false||migration.changed_ids.length!==2||migration.added_ids.length||migration.removed_ids.length||
  migration.before_footprints_sha256!==validation.before_footprints_sha256||migration.after_footprints_sha256!==validation.after_footprints_sha256)throw Error('Complete last-step migration validation required');
const baseline=validation.inputs.find(f=>f.path==='data/geographic-releases/current-manifest.json');
if(!baseline)throw Error('Predecessor pointer pin required');
const sourceCommit='d0cc67eac85038159f88a673acbc39b77ab7461d',inputs=[];
let budget=producer.reduce((n,p)=>n+p.bytes,0)+migrationRaw.length+validationRaw.length;
function read(name){
  const raw=execFileSync('git',['-C',root,'show',sourceCommit+':'+name],{maxBuffer:32*1024*1024});
  if(raw.length>32*1024*1024)throw Error('Oversized predecessor input');budget+=raw.length;if(budget>256*1024*1024)throw Error('Bounded source/output budget exceeded');
  inputs.push({commit:sourceCommit,path:name,bytes:raw.length,sha256:digest(raw)});return raw;
}
const pointerRaw=read('data/geographic-releases/current-manifest.json'),pointer=JSON.parse(pointerRaw);
if(digest(pointerRaw)!==baseline.sha256)throw Error('Predecessor pointer differs');
const extensionRaw=read('data/geographic-releases/'+pointer.path),indexRaw=read('data/geographic-releases/index.json');
if(digest(extensionRaw)!==pointer.sha256||digest(indexRaw)!==pointer.predecessor_index_sha256)throw Error('Predecessor extension differs');
const predecessor=JSON.parse(gunzipSync(extensionRaw)),previous=predecessor.releases.at(-1),members=[],oldChanges=[];
if(previous.version!==6||previous.id!==validation.predecessor_release_id||previous.footprints_sha256!==migration.before_footprints_sha256)throw Error('Migration does not extend actual version six');
for(const part of predecessor.batches.filter(p=>/^6-(memberships|changes)-/.test(p.path))){
  const payload=JSON.parse(decodeGeographicReleaseBatch(read('data/geographic-releases/'+part.path),part));
  if(payload.release_id!==previous.id)throw Error('Predecessor batch release differs');
  if(payload.memberships)members.push(...payload.memberships);if(payload.changes)oldChanges.push(...payload.changes);
}
if(await geographicMembershipHash(members)!==previous.membership_sha256||await geographicLocationIdsHash(members)!==previous.location_ids_sha256||
  await geographicChangesHash(oldChanges)!==previous.changes_sha256||new Set(members.map(m=>m.entity_id)).size!==members.length)throw Error('Complete predecessor membership/change hashes differ');
const tiers=['continent','subcontinent','region','area','province','location'],counts=rows=>Object.fromEntries(tiers.map(t=>[t,rows.filter(r=>r.kind===t&&r.active).length]));
if(!isDeepStrictEqual(counts(members),previous.expected_counts))throw Error('Complete predecessor counts differ');
const changed=new Set(migration.changed_ids),byId=new Map(members.map(m=>[m.entity_id,m]));
if(migration.archives.some(row=>byId.get(row.id)?.active!==1||byId.get(row.id)?.kind!=='location'||byId.get(row.id)?.parent_id!==row.feature.properties.parent_id||
  byId.get(row.id)?.reference_name!==row.feature.properties.name))throw Error('Source pair does not match published reference identity');
const key=digest(Buffer.from(JSON.stringify({predecessor:pointer.sha256,migration:digest(migrationRaw),reference_date:'2026-10-06'}))),sourceId='source:atlas:geographic-review:'+key,id='geography:review:'+key;
const proof={commit:head,path:migrationName,sha256:digest(migrationRaw),validation_path:validationName,validation_sha256:digest(validationRaw),
  before_footprints_sha256:migration.before_footprints_sha256,after_footprints_sha256:migration.after_footprints_sha256,history_transfer:'none'};
const rows=members.map(row=>changed.has(row.entity_id)?{...row,source_id:sourceId,evidence:{...row.evidence,
  predecessor_release_id:previous.id,predecessor_membership_sha256:previous.membership_sha256,geometry_migration:proof,history_transfer:'none',reference_only:true}}:row);
const changes=migration.changed_ids.map(entity=>({id:'geo-change:'+digest(Buffer.from(id+'\n'+entity)),old_entity_id:entity,new_entity_id:entity,
  change_type:'retain',source_id:sourceId,evidence:{reference_only:true,history_transfer:'none',geometry_migration:proof,
    original_source_evidence:byId.get(entity).evidence}}));
const source={id:sourceId,name:'Joint Saravan–Panjgur modern reference seam',url:'https://www.openstreetmap.org/copyright',
  license:'ODbL 1.0 for new OSM-derived seam data; retained base source notices preserved',vintage:'OSM snapshots retrieved 2026-10-05; no effective boundary date asserted',
  status:'reference',supported_from:2026,supported_to:2027,metadata:{reference_only:true,historical_membership_not_asserted:true,history_transfer:'none',
    predecessor_release:previous.id,predecessor_manifest:{commit:sourceCommit,path:'data/geographic-releases/'+pointer.path,sha256:pointer.sha256},
    predecessor_proof_chronology:previous.metadata.geometry_proof_sha256,identity_proof_sequence:previous.metadata.identity_proof_sequence,
    geometry_migration:proof,source_policy:migration.source_policy,source_evidence:migration.source_evidence,
    source_offer:'Exact original OSM county/way snapshots and complete joint derivative geography are retained in the primary repository with original notices and hashes.',
    unresolved_source_limits:migration.source_policy.unknown}};
const release={...previous,id,version:7,source_id:sourceId,reference_date:'2026-10-06',footprints_sha256:migration.after_footprints_sha256,
  membership_sha256:await geographicMembershipHash(rows),location_ids_sha256:await geographicLocationIdsHash(rows),changes_sha256:await geographicChangesHash(changes),
  metadata:{...previous.metadata,predecessor_release_id:previous.id,predecessor_manifest_sha256:pointer.sha256,geometry_migration:proof,
    reference_only:true,historical_membership_not_asserted:true,original_registry_preserved:true}};
if(release.location_ids_sha256!==previous.location_ids_sha256||rows.some((r,i)=>!changed.has(r.entity_id)&&!isDeepStrictEqual(r,members[i])))throw Error('Unexpected identity/non-target membership mutation');
fs.mkdirSync(out,{recursive:false});const newBatches=[];
function write(name,payload,route){
  const raw=Buffer.from(JSON.stringify(payload)),encoded=gzipSync(raw,{level:9});if(raw.length>1048576)throw Error('Prepared API batch exceeds one MiB');
  budget+=encoded.length;if(budget>256*1024*1024)throw Error('Bounded source/output budget exceeded');fs.writeFileSync(path.join(out,name),encoded,{flag:'wx'});
  const descriptor={path:name,route,encoding:'gzip',sha256:digest(encoded),payload_sha256:digest(raw)};newBatches.push(descriptor);return descriptor;
}
write('sources-7.json.gz',{sources:[source],ingestion_id:'geographic-sources:'+key},'/api/records/import');
write('release-7.json.gz',{release,ingestion_id:'geographic-release:'+id},'/api/geography/stage');
// Size-based partitions retain every membership while bounding actual API bytes.
let batch=[],first=0;
for(const row of rows){
  const trial={release_id:id,memberships:[...batch,row],ingestion_id:id+':memberships:'+first};
  if(Buffer.byteLength(JSON.stringify(trial))>900000){write(`7-memberships-${first}.json.gz`,{release_id:id,memberships:batch,ingestion_id:id+':memberships:'+first},'/api/geography/stage');first+=batch.length;batch=[];}
  batch.push(row);
}
if(batch.length)write(`7-memberships-${first}.json.gz`,{release_id:id,memberships:batch,ingestion_id:id+':memberships:'+first},'/api/geography/stage');
write('7-changes-0.json.gz',{release_id:id,changes,ingestion_id:id+':changes:0'},'/api/geography/stage');
const next={...predecessor,releases:[...predecessor.releases,release],batches:[...predecessor.batches,...newBatches],
  sources_batches:[...predecessor.sources_batches,'sources-7.json.gz'],changes:predecessor.changes+changes.length,
  total_memberships:Math.max(predecessor.total_memberships,rows.length),successor_geometry:{predecessor_id:previous.id,proof,changed_ids:[...changed],history_transfer:'none'}};
const newRaw=Buffer.from(JSON.stringify(next)),encoded=gzipSync(newRaw,{level:9});
fs.writeFileSync(path.join(out,'index.json'),indexRaw,{flag:'wx'});
fs.writeFileSync(path.join(out,'releases-v7-gzip.json.gz'),encoded,{flag:'wx'});
fs.writeFileSync(path.join(out,'current-manifest.json'),JSON.stringify({path:'releases-v7-gzip.json.gz',sha256:digest(encoded),predecessor_index_sha256:digest(indexRaw)})+'\n',{flag:'wx'});
// The normal reader checks the immutable original index and retained release prefix.
if(!isDeepStrictEqual(readGeographicReleaseManifest(out),next))throw Error('Successor extension readback differs');
fs.writeFileSync(path.join(out,'preparation.json'),JSON.stringify({version:1,evaluation_commit:head,producer,inputs,
  predecessor_release_id:previous.id,successor_release_id:id,release_version:7,complete_memberships:rows.length,counts:release.expected_counts,
  preserved_non_target_memberships:rows.length-2,changed_ids:[...changed],new_entities:0,historical_claims_transferred:false,
  new_batches:newBatches,release_manifest_sha256:digest(encoded),original_index_preserved:true,
  scope:'Delta package overlays immutable predecessor release files; only new batches and extension are generated.',installed:false,published:false})+'\n',{flag:'wx'});
console.log(JSON.stringify({release:id,version:7,memberships:rows.length,new_batches:newBatches.length,changed:2,installed:false,published:false}));
