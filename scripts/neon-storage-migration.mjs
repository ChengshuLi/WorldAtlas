import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash,randomBytes,randomUUID} from 'node:crypto';
import {inflateRawSync} from 'node:zlib';
import {fileURLToPath} from 'node:url';
import {Client,neonConfig} from '@neondatabase/serverless';
import {createNeonDatabase} from '../hosted/postgres-adapter.js';
import {exportStorageMarker} from '../hosted/storage-export.js';
import {capacityReport,catalogPage} from '../hosted/research-catalog.js';
import {mapSnapshotPage} from '../hosted/map-snapshots.js';
import {hydrateMapSnapshotPage} from '../src/map-snapshot-format.js';
import {unpackStorageCheckpoint} from './storage-checkpoint.mjs';
import {readVerifiedStorageSnapshot,restorePostgresStorage} from './restore-postgres-storage.mjs';
import {postgresSchemaURL,postgresTables} from './verify-postgres-schema.mjs';
import {schemaTransactionStatements,productionBranchId} from './verify-neon-sql.mjs';
import {expectedNeonProjectId,verifyNeonProject} from './verify-neon-project.mjs';
import {runtimeRole,provisionPostgresRuntimeRole,verifyPostgresRuntimeRole} from './provision-postgres-runtime-role.mjs';
import {encryptCredentialEnvelope,credentialRecipientFingerprint} from './credential-envelope.mjs';

export const migrationWorkflowPath='.github/workflows/neon-storage-migration.yml';
export const migrationRepository='ChengshuLi/WorldAtlas';
const schemaSHA='1a43333772e6059d4fa97ce60baad7a27239616693c86708d08eadbc73b97618';
const roleURL=new URL('../postgres/runtime-role.sql',import.meta.url);
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const validHash=value=>typeof value==='string'&&/^[a-f0-9]{64}$/.test(value);
const validId=value=>typeof value==='string'&&/^br-[a-z0-9-]{1,150}$/.test(value);
const object=value=>value!==null&&typeof value==='object'&&!Array.isArray(value);
const validNumber=value=>typeof value==='string'&&/^[1-9][0-9]{0,19}$/.test(value);
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
class MigrationError extends Error{constructor(code){super(code);this.code=code;}}
const fail=code=>{throw new MigrationError(code);};

function repoFile(root,relative,maxBytes=65536){
 if(typeof relative!=='string'||!relative||path.isAbsolute(relative)||relative.includes('\\')||relative.split('/').some(part=>!part||part==='.'||part==='..'))fail('unsafe-operation-file-path');
 const file=path.join(root,relative);let current=fs.realpathSync(root);
 for(const component of relative.split('/')){current=path.join(current,component);if(fs.lstatSync(current).isSymbolicLink())fail('operation-symlink-refused');}
 const stat=fs.statSync(file);if(!stat.isFile()||stat.size<1||stat.size>maxBytes||!fs.realpathSync(file).startsWith(fs.realpathSync(root)+path.sep))fail('invalid-operation-file');return fs.readFileSync(file);
}
export function validateMigrationOperation(operation,{mode,root=process.cwd()}={}){
 if(!['rehearsal','production','verify-only'].includes(mode)||!object(operation)||operation.version!==1||operation.project_id!==expectedNeonProjectId||operation.production_branch_id!==productionBranchId||!['checkpoint_sha256','source_manifest_sha256','source_snapshot_fingerprint','schema_sha256','runtime_role_sql_sha256'].every(key=>validHash(operation[key]))||operation.schema_sha256!==schemaSHA||!Number.isSafeInteger(operation.source_revision)||operation.source_revision<0||typeof operation.checkpoint_directory!=='string'||!/^data\/storage-checkpoints\/[A-Za-z0-9._/-]+$/.test(operation.checkpoint_directory)||!Number.isSafeInteger(operation.database_budget_bytes)||operation.database_budget_bytes<=0)fail('invalid-reviewed-operation');
 if(hash(fs.readFileSync(postgresSchemaURL))!==operation.schema_sha256||hash(fs.readFileSync(roleURL))!==operation.runtime_role_sql_sha256)fail('reviewed-install-code-hash-mismatch');
 const checkpoint=repoFile(root,operation.checkpoint_directory+'/checkpoint.json',32*1024*1024);
 if(hash(checkpoint)!==operation.checkpoint_sha256)fail('reviewed-checkpoint-hash-mismatch');
 const index=JSON.parse(checkpoint);
 for(const key of ['source_manifest_sha256','source_snapshot_fingerprint','source_revision'])if(index[key]!==operation[key])fail('reviewed-source-identity-mismatch');
 if(mode!=='rehearsal'){
  const approved=operation.production,proof=approved?.rehearsal;
  if(!object(approved)||approved.acknowledgement!=='install-reviewed-snapshot-into-empty-production'||!object(proof)||!validNumber(proof.run_id)||!validNumber(proof.run_attempt)||!validNumber(proof.artifact_id)||typeof proof.head_sha!=='string'||!/^[a-f0-9]{40}$/.test(proof.head_sha)||!validHash(proof.artifact_sha256)||!validHash(proof.receipt_sha256)||proof.run_url!==`https://github.com/${migrationRepository}/actions/runs/${proof.run_id}`)fail('production-rehearsal-approval-required');
  if(mode==='production'){
   if(!validHash(approved.recipient_sha256)||typeof approved.recipient_public_key_file!=='string'||!['.github/operations/','data/storage-migration/'].some(prefix=>approved.recipient_public_key_file.startsWith(prefix)))fail('approved-recipient-required');
   const recipient=repoFile(root,approved.recipient_public_key_file,32768);
   if(credentialRecipientFingerprint(recipient)!==approved.recipient_sha256)fail('approved-recipient-mismatch');
  }
 }
 return operation;
}
function githubContext(env){
 if(env.GITHUB_REPOSITORY!==migrationRepository||!validNumber(env.GITHUB_RUN_ID)||!validNumber(env.GITHUB_RUN_ATTEMPT)||!/^[a-f0-9]{40}$/.test(env.GITHUB_SHA??'')||env.GITHUB_WORKFLOW_REF!==`${migrationRepository}/${migrationWorkflowPath}@refs/heads/work`)fail('authorized-actions-context-required');
 return {repository:migrationRepository,workflow_path:migrationWorkflowPath,head_sha:env.GITHUB_SHA,run_id:env.GITHUB_RUN_ID,run_attempt:env.GITHUB_RUN_ATTEMPT};
}
async function boundedBytes(response,limit){
 const reader=response.body?.getReader();if(!reader)fail('empty-network-response');const chunks=[];let bytes=0;
 try{for(;;){const {value,done}=await reader.read();if(done)break;bytes+=value.byteLength;if(bytes>limit)fail('network-response-byte-limit');chunks.push(value);}}
 finally{try{await reader.cancel();}catch{}}
 return Buffer.concat(chunks,bytes);
}
function writeJSON(file,value){
 const bytes=Buffer.from(JSON.stringify(value,null,2)+'\n');if(bytes.length>128*1024)fail('sanitized-receipt-byte-limit');fs.mkdirSync(path.dirname(file),{recursive:true});const temporary=file+'.tmp-'+randomUUID(),fd=fs.openSync(temporary,'wx',0o600);try{fs.writeFileSync(fd,bytes);fs.fsyncSync(fd);}finally{fs.closeSync(fd);}fs.renameSync(temporary,file);return bytes;
}
/** Ciphertext-only fallback for authenticated Actions logs. Base64 encodes the
 * exact envelope file bytes so the receipt hash verifies artifact and log alike.
 */
export function encryptedCredentialLogPayload(receipt,envelopeBytes){
 if(receipt?.mode!=='production'||receipt.status!=='verified'||!Buffer.isBuffer(envelopeBytes)||envelopeBytes.length<1||envelopeBytes.length>65536||hash(envelopeBytes)!==receipt.encrypted_handoff?.envelope_sha256)fail('verified-encrypted-log-delivery-required');
 const envelope=JSON.parse(envelopeBytes);
 if(envelope?.version!==1||envelope.suite!=='RSA-OAEP-256+A256GCM'||envelope.recipient_sha256!==receipt.encrypted_handoff.recipient_sha256||JSON.stringify(envelope.context)!==JSON.stringify(receipt.encrypted_handoff.context)||typeof envelope.ciphertext!=='string'||typeof envelope.wrapped_key!=='string')fail('encrypted-log-envelope-binding-mismatch');
 const result={type:'worldatlas-encrypted-runtime-credential',version:1,filename:'credential-envelope.json',envelope_sha256:receipt.encrypted_handoff.envelope_sha256,recipient_sha256:envelope.recipient_sha256,github:receipt.github,envelope_bytes_base64:envelopeBytes.toString('base64')};
 if(Buffer.byteLength(JSON.stringify(result))>65536)fail('encrypted-log-line-byte-limit');return result;
}

/** The authenticated artifact archive is small and hash-pinned. Read one exact
 * central-directory entry without extracting any archive path to disk. */
export function rehearsalReceiptFromZIP(bytes){
 if(!Buffer.isBuffer(bytes)||bytes.length<22||bytes.length>2*1024*1024)fail('invalid-rehearsal-artifact-size');
 let end=-1;for(let i=bytes.length-22;i>=Math.max(0,bytes.length-65557);i--)if(bytes.readUInt32LE(i)===0x06054b50){end=i;break;}
 if(end<0||end+22+bytes.readUInt16LE(end+20)!==bytes.length||bytes.readUInt16LE(end+4)||bytes.readUInt16LE(end+6))fail('unsupported-rehearsal-zip');
 const count=bytes.readUInt16LE(end+10),centralSize=bytes.readUInt32LE(end+12),centralOffset=bytes.readUInt32LE(end+16);
 if(count<1||count>10||count!==bytes.readUInt16LE(end+8)||centralOffset+centralSize!==end)fail('invalid-rehearsal-zip-directory');
 let at=centralOffset,result=null;
 for(let entry=0;entry<count;entry++){
  if(at+46>end||bytes.readUInt32LE(at)!==0x02014b50)fail('invalid-rehearsal-zip-entry');
  const flags=bytes.readUInt16LE(at+8),method=bytes.readUInt16LE(at+10),compressed=bytes.readUInt32LE(at+20),raw=bytes.readUInt32LE(at+24),nameLength=bytes.readUInt16LE(at+28),extra=bytes.readUInt16LE(at+30),comment=bytes.readUInt16LE(at+32),local=bytes.readUInt32LE(at+42);
  const next=at+46+nameLength+extra+comment;if(next>end)fail('invalid-rehearsal-zip-entry-size');
  const name=bytes.subarray(at+46,at+46+nameLength).toString('utf8');
  if(!['receipt.json','credential-envelope.json'].includes(name)||flags&1||![0,8].includes(method)||compressed>2*1024*1024||raw>128*1024)fail('unsafe-rehearsal-zip-entry');
  if(name==='receipt.json'){
   if(result||local+30>centralOffset||bytes.readUInt32LE(local)!==0x04034b50||bytes.readUInt16LE(local+8)!==method)fail('invalid-rehearsal-zip-local-header');
   const localName=bytes.readUInt16LE(local+26),localExtra=bytes.readUInt16LE(local+28),start=local+30+localName+localExtra;
   if(bytes.subarray(local+30,local+30+localName).toString('utf8')!==name||start+compressed>centralOffset)fail('invalid-rehearsal-zip-local-name');
   result=method===0?Buffer.from(bytes.subarray(start,start+compressed)):inflateRawSync(bytes.subarray(start,start+compressed),{maxOutputLength:128*1024});
   if(result.length!==raw)fail('invalid-rehearsal-zip-raw-size');
  }
  at=next;
 }
 if(at!==end||!result)fail('missing-rehearsal-receipt');return result;
}
async function authenticateRehearsal({operation,env,fetchImpl}){
 const expected=operation.production.rehearsal,token=env.GITHUB_TOKEN;
 if(typeof token!=='string'||!token||/[\r\n]/.test(token))fail('authenticated-actions-token-required');
 const request=async route=>{
  let response;try{response=await fetchImpl('https://api.github.com/repos/'+migrationRepository+route,{headers:{Authorization:'Bearer '+token,Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'},redirect:'error',signal:AbortSignal.timeout(15000)});}catch{fail('actions-verification-network-failed');}
  if(!response.ok){await response.body?.cancel().catch(()=>{});fail('actions-verification-http-failed');}return JSON.parse((await boundedBytes(response,2*1024*1024)).toString('utf8'));
 };
 const run=await request('/actions/runs/'+expected.run_id);
 if(!Number.isSafeInteger(run.id)||!Number.isSafeInteger(run.run_attempt)||String(run.id)!==expected.run_id||String(run.run_attempt)!==expected.run_attempt||run.repository?.full_name!==migrationRepository||run.head_branch!=='work'||run.head_sha!==expected.head_sha||run.path!==migrationWorkflowPath||run.status!=='completed'||run.conclusion!=='success'||run.html_url!==expected.run_url)fail('successful-authorized-rehearsal-run-required');
 const artifact=await request('/actions/artifacts/'+expected.artifact_id);
 if(!Number.isSafeInteger(artifact.id)||String(artifact.id)!==expected.artifact_id||artifact.name!==`neon-storage-rehearsal-${expected.run_id}-${expected.run_attempt}`||artifact.expired!==false||!Number.isSafeInteger(artifact.workflow_run?.id)||artifact.workflow_run.id!==Number(expected.run_id)||artifact.workflow_run?.head_sha!==expected.head_sha||artifact.digest!=='sha256:'+expected.artifact_sha256||!Number.isSafeInteger(artifact.size_in_bytes)||artifact.size_in_bytes<1||artifact.size_in_bytes>2*1024*1024)fail('authenticated-rehearsal-artifact-required');
 let redirect;try{redirect=await fetchImpl(`https://api.github.com/repos/${migrationRepository}/actions/artifacts/${expected.artifact_id}/zip`,{headers:{Authorization:'Bearer '+token,Accept:'application/vnd.github+json'},redirect:'manual',signal:AbortSignal.timeout(15000)});}catch{fail('artifact-download-unavailable');}
 if(redirect.status!==302)fail('artifact-download-redirect-required');let url;try{url=new URL(redirect.headers.get('location'));}catch{fail('invalid-artifact-download-location');}
 if(url.protocol!=='https:'||url.username||url.password||!['.blob.core.windows.net','.githubusercontent.com','.actions.githubusercontent.com'].some(suffix=>url.hostname.endsWith(suffix)))fail('untrusted-artifact-download-host');
 let downloaded;try{downloaded=await fetchImpl(url,{redirect:'error',signal:AbortSignal.timeout(15000)});}catch{fail('artifact-download-unavailable');}
 if(!downloaded.ok)fail('artifact-download-http-failed');const archive=await boundedBytes(downloaded,2*1024*1024);
 if(hash(archive)!==expected.artifact_sha256)fail('authenticated-artifact-hash-mismatch');
 const raw=rehearsalReceiptFromZIP(archive);if(hash(raw)!==expected.receipt_sha256)fail('authenticated-receipt-hash-mismatch');const receipt=JSON.parse(raw);
 if(receipt.version!==1||receipt.mode!=='rehearsal'||receipt.status!=='verified'||receipt.cleanup_status!=='deleted'||receipt.raw_snapshot_verified!==true||receipt.runtime_read_only_checks!==true||receipt.github?.repository!==migrationRepository||receipt.github?.workflow_path!==migrationWorkflowPath||receipt.github?.head_sha!==expected.head_sha||receipt.github?.run_id!==expected.run_id||receipt.github?.run_attempt!==expected.run_attempt)fail('completed-rehearsal-contract-required');
 for(const key of ['checkpoint_sha256','source_manifest_sha256','source_snapshot_fingerprint','source_revision','schema_sha256','runtime_role_sql_sha256','database_budget_bytes'])if(receipt[key]!==operation[key])fail('rehearsal-input-identity-mismatch');
 return {run_id:expected.run_id,run_attempt:expected.run_attempt,head_sha:expected.head_sha,artifact_id:expected.artifact_id,artifact_sha256:expected.artifact_sha256,receipt_sha256:expected.receipt_sha256,status:'authenticated-success'};
}

async function ownerConnection(uri){
 neonConfig.webSocketConstructor=globalThis.WebSocket;const client=new Client({connectionString:uri,connectionTimeoutMillis:30000,query_timeout:60000});client.on('error',()=>{});
 try{await client.connect();}catch(error){try{await client.end();}catch{}throw error;}
 return {query:(query,params)=>client.query(query,params),async runTransaction(callback){await client.query('BEGIN ISOLATION LEVEL SERIALIZABLE');try{const result=await callback({query:(query,params)=>client.query(query,params)});await client.query('COMMIT');return result;}catch(error){try{await client.query('ROLLBACK');}catch{}throw error;}},close:()=>client.end()};
}
function checkedOwnerURI(value,host){
 let url;try{url=new URL(value);}catch{fail('invalid-owner-connection');}
 if(typeof value!=='string'||value.length>16384||!['postgres:','postgresql:'].includes(url.protocol)||![host,host.replace(/^([^.]+)\./,'$1-pooler.')].includes(url.hostname)||decodeURIComponent(url.username)!=='neondb_owner'||decodeURIComponent(url.pathname)!=='/neondb'||!url.password||url.hash||url.searchParams.getAll('sslmode').length!==1||url.searchParams.get('sslmode')!=='require')fail('owner-connection-branch-mismatch');return value;
}
function endpointHost(endpoints,branchId){
 if(!Array.isArray(endpoints)||endpoints.length>100)fail('invalid-neon-endpoint-inventory');const selected=endpoints.filter(endpoint=>endpoint?.branch_id===branchId&&endpoint.type==='read_write');
 if(selected.length!==1||selected[0].project_id!==undefined&&selected[0].project_id!==expectedNeonProjectId||!/^ep-[a-z0-9-]+(?:\.[a-z0-9-]+)+\.neon\.tech$/.test(selected[0].host??''))fail('verified-branch-endpoint-required');return selected[0].host;
}
async function runtimeReadChecks(db,snapshot,budget){
 const marker=await exportStorageMarker(db);for(const key of ['revision','geographic_releases_sha256'])if(marker[key]!==snapshot.manifest.snapshot_marker[key])fail('runtime-source-marker-mismatch');
 if(JSON.stringify(marker.counts)!==JSON.stringify(snapshot.manifest.snapshot_marker.counts)||marker.fingerprint!==snapshot.manifest.snapshot_marker.fingerprint)fail('runtime-fourteen-count-mismatch');
 const capacity=await capacityReport(db,{databaseBudgetBytes:budget});if(capacity.revision!==snapshot.revision||!Number.isSafeInteger(capacity.database.bytes)||capacity.database.bytes<=0||capacity.database.bytes>Math.floor(budget*0.8))fail('reviewed-capacity-headroom-insufficient');
 const maps=[];
 for(const year of [-3000,1000,1800,2026]){
  let cursor='';const seen=new Set();
  for(let pageNumber=0;pageNumber<2;pageNumber++){
   const started=performance.now();let page,limit=1000;
   for(;;){try{page=await mapSnapshotPage(db,year,{cursor,limit});break;}catch(error){if(error.status!==413||!error.retryable||limit<=1)throw error;limit=Math.max(1,Math.floor(limit/2));}}
   const hydrated=hydrateMapSnapshotPage(page);if(hydrated.revision!==snapshot.revision||hydrated.entities.some(row=>seen.has(row.id)))fail('runtime-map-page-consistency-failed');for(const row of hydrated.entities)seen.add(row.id);
   maps.push({year,page:pageNumber+1,entities:hydrated.entities.length,records:hydrated.records.length,names:hydrated.names.length,retirements:hydrated.retirements.length,bytes:Buffer.byteLength(JSON.stringify(page)),elapsed_ms:Math.round(performance.now()-started),entity_ids_sha256:hash(JSON.stringify(hydrated.entities.map(row=>row.id))),revision:hydrated.revision});
   if(page.next_cursor===null)break;cursor=page.next_cursor;
  }
 }
 const sources=await catalogPage(db,'sources',{limit:1}),entities=await catalogPage(db,'entities',{limit:1});
 if(sources.revision!==snapshot.revision||entities.revision!==snapshot.revision)fail('runtime-catalog-revision-mismatch');
 return {all_fourteen_counts:marker.counts,storage_marker_fingerprint:marker.fingerprint,database:capacity.database,registered_media:capacity.media,maps,catalog_reads_verified:true,scope:'Read-only app storage/catalog and at most two compact map pages per representative year; exhaustive original rows proven separately.'};
}

/** Trusted owner migration only. Source backups stay untouched. Production
 * cannot be deleted, silently retried after nonempty/ambiguous state, or reset.
 */
export async function runNeonStorageMigration({mode='rehearsal',operationFile='.github/operations/neon-storage-rehearsal.json',root=process.cwd(),env=process.env,output='data/validation/neon-storage-migration',fetchImpl=fetch,ownerDriverFactory=ownerConnection,appDatabaseFactory=uri=>createNeonDatabase(uri,{timeoutMs:30000}),sleepImpl=sleep,onProgress=()=>{}}={}){
 root=path.resolve(root);output=path.resolve(root,output);const receiptFile=path.join(output,'receipt.json');
 const receipt={version:1,mode,status:'running',project_id:expectedNeonProjectId,production_branch_id:productionBranchId,production_deleted:false,credentials_logged:false,cleanup_status:'not-required',started_at_utc:new Date().toISOString()};
 let stage='reviewed-inputs',temporary=null,createdId=null,owner=null,operation=null,requests=0;
 const checkpoint=()=>writeJSON(receiptFile,receipt);
 const api=async(method,route,body)=>{
  if(++requests>120)fail('neon-api-request-limit');let response;
  try{response=await fetchImpl('https://console.neon.tech/api/v2/projects/'+expectedNeonProjectId+route,{method,headers:{Authorization:'Bearer '+env.NEON_API_KEY,Accept:'application/json',...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{}),redirect:'error',signal:AbortSignal.timeout(15000)});}catch{fail('neon-management-network-failed');}
  if(method==='DELETE'&&(response.ok||response.status===404)){await response.body?.cancel().catch(()=>{});return null;}
  if(!response.ok){await response.body?.cancel().catch(()=>{});fail('neon-management-http-failed');}return JSON.parse((await boundedBytes(response,2*1024*1024)).toString('utf8'));
 };
 try{
  if(mode==='rehearsal'&&!fs.existsSync(path.join(root,operationFile))){receipt.status='skipped';receipt.error_code='reviewed-checkpoint-operation-not-present';return receipt;}
  operation=validateMigrationOperation(JSON.parse(repoFile(root,operationFile)),{mode,root});
  receipt.github=githubContext(env);for(const key of ['checkpoint_sha256','source_manifest_sha256','source_snapshot_fingerprint','source_revision','schema_sha256','runtime_role_sql_sha256','database_budget_bytes'])receipt[key]=operation[key];
  if(env.NEON_PROJECT_ID!==expectedNeonProjectId||typeof env.NEON_API_KEY!=='string'||!env.NEON_API_KEY.trim()||/[\r\n]/.test(env.NEON_API_KEY))fail('authorized-neon-configuration-required');
  temporary=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-neon-migration-'));const source=path.join(temporary,'source');
  await unpackStorageCheckpoint({directory:path.join(root,operation.checkpoint_directory),output:source});const snapshot=readVerifiedStorageSnapshot(source);
  if(snapshot.manifest_sha256!==operation.source_manifest_sha256||snapshot.revision!==operation.source_revision||snapshot.manifest.snapshot_marker.fingerprint!==operation.source_snapshot_fingerprint)fail('verified-original-source-mismatch');
  receipt.source_collections=snapshot.proofs;receipt.source_backup_preserved=true;checkpoint();
  if(mode!=='rehearsal'){stage='authenticated-rehearsal';receipt.authenticated_rehearsal=await authenticateRehearsal({operation,env,fetchImpl});checkpoint();}
  stage='production-metadata';const parent=await verifyNeonProject({apiKey:env.NEON_API_KEY,projectId:env.NEON_PROJECT_ID,fetchImpl});requests+=parent.api_requests;
  if(parent.branch.id!==productionBranchId||parent.project.configured_postgres_major!==18||!parent.databases.some(row=>row.name==='neondb'&&row.owner_name==='neondb_owner'))fail('verified-neon-parent-mismatch');
  let branchId=productionBranchId,host;
  if(mode==='rehearsal'){
   stage='rehearsal-branch-creation';const name='atlas-storage-rehearsal-'+randomUUID();receipt.validation_branch_name=name;receipt.cleanup_status='creation-unconfirmed';checkpoint();
   const created=await api('POST','/branches',{branch:{name,parent_id:productionBranchId},endpoints:[{type:'read_write'}]});
   if(validId(created.branch?.id)&&created.branch.id!==productionBranchId){createdId=created.branch.id;receipt.validation_branch_id=createdId;receipt.cleanup_status='pending';checkpoint();}
   if(!createdId||created.branch.name!==name||created.branch.parent_id!==productionBranchId||created.branch.project_id!==undefined&&created.branch.project_id!==expectedNeonProjectId)fail('created-rehearsal-branch-mismatch');
   branchId=createdId;host=endpointHost(created.endpoints,branchId);stage='rehearsal-branch-readiness';let ready=false;
   for(let at=0;at<30;at++){const observed=await api('GET','/branches/'+branchId);if(observed.branch?.id!==branchId||observed.branch.name!==name||observed.branch.parent_id!==productionBranchId)fail('rehearsal-branch-response-mismatch');if(observed.branch.current_state==='ready'){ready=true;break;}await sleepImpl(2000);}
   if(!ready)fail('rehearsal-branch-readiness-timeout');
  }else host=endpointHost((await api('GET','/endpoints')).endpoints,branchId);
  stage='private-owner-connection';const params=new URLSearchParams({branch_id:branchId,database_name:'neondb',role_name:'neondb_owner',pooled:'false'}),connection=await api('GET','/connection_uri?'+params),ownerURI=checkedOwnerURI(connection.uri,host);
  owner=await ownerDriverFactory(ownerURI);const identity=(await owner.query("SELECT current_database() AS database_name,current_user AS role_name,current_schema() AS schema_name,current_setting('server_version_num') AS server_version_num")).rows?.[0];
  if(identity?.database_name!=='neondb'||identity.role_name!=='neondb_owner'||identity.schema_name!=='public'||!/^18\d{4}$/.test(String(identity.server_version_num)))fail('verified-owner-database-identity-required');
  receipt.target_branch_id=branchId;receipt.target_endpoint_host=host;
  if(mode==='verify-only'){
   stage='read-only-original-verification';receipt.restore=await restorePostgresStorage({directory:source,driver:owner,verifyOnly:true,receiptFile:path.join(temporary,'restore.json')});receipt.runtime_role=await verifyPostgresRuntimeRole(owner);receipt.raw_snapshot_verified=true;receipt.read_only=true;receipt.status='verified';return receipt;
  }
  stage='empty-target-guard';const tables=(await owner.query("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'")).rows;
  if(!Array.isArray(tables)||tables.length)fail('target-not-empty-use-explicit-verify-only');
  if((await owner.query('SELECT count(*)::int AS count FROM pg_roles WHERE rolname=$1',[runtimeRole])).rows?.[0]?.count!==0)fail('existing-runtime-role-needs-private-maintenance-review');
  stage='schema-install';const commands=schemaTransactionStatements(fs.readFileSync(postgresSchemaURL,'utf8'));
  await owner.runTransaction(async tx=>{for(const command of commands)await tx.query(command);});receipt.schema_installed=true;checkpoint();
  stage='original-owner-restore';receipt.restore=await restorePostgresStorage({directory:source,driver:owner,acknowledgeOwnerRestore:true,receiptFile:path.join(temporary,'restore.json'),onProgress});receipt.raw_snapshot_verified=true;checkpoint();
  stage='runtime-role-provision';const password=randomBytes(32).toString('base64url');await provisionPostgresRuntimeRole({driver:owner,password});
  const appURI=new URL(ownerURI);appURI.username=runtimeRole;appURI.password=password;
  const app=await appDatabaseFactory(appURI.href),login=await app.prepare('SELECT current_user AS current_user,session_user AS session_user').first();
  if(login?.current_user!==runtimeRole||login.session_user!==runtimeRole)fail('restricted-application-authentication-required');
  stage='restricted-runtime-read-checks';receipt.runtime_role=await verifyPostgresRuntimeRole({query:async(sql,params)=>({rows:(await app.prepare(sql).bind(...(params??[])).all()).results})});
  receipt.runtime=await runtimeReadChecks(app,snapshot,operation.database_budget_bytes);receipt.runtime_read_only_checks=true;
  stage='post-runtime-full-byte-verification';receipt.readback=await restorePostgresStorage({directory:source,driver:owner,verifyOnly:true,receiptFile:path.join(temporary,'readback.json')});
  if(mode==='production'){
   stage='encrypted-private-handoff';const now=Date.now(),context={purpose:'worldatlas-runtime-database-url',repository:migrationRepository,workflow_path:migrationWorkflowPath,commit_sha:receipt.github.head_sha,run_id:receipt.github.run_id,run_attempt:receipt.github.run_attempt,project_id:expectedNeonProjectId,branch_id:productionBranchId,endpoint_host:host,database_name:'neondb',role_name:runtimeRole,source_manifest_sha256:operation.source_manifest_sha256,schema_sha256:operation.schema_sha256,runtime_role_sql_sha256:operation.runtime_role_sql_sha256,issued_at_utc:new Date(now).toISOString(),expires_at_utc:new Date(now+60*60*1000).toISOString()};
   const envelope=encryptCredentialEnvelope({credential:appURI.href,publicKey:repoFile(root,operation.production.recipient_public_key_file,32768),context,now});
   if(envelope.recipient_sha256!==operation.production.recipient_sha256)fail('approved-handoff-recipient-changed');
   const bytes=writeJSON(path.join(output,'credential-envelope.json'),envelope);
   receipt.encrypted_handoff={recipient_sha256:envelope.recipient_sha256,envelope_sha256:hash(bytes),context};
  }
  receipt.status='verified';
 }catch(error){
  receipt.status='failed';receipt.failure_stage=stage;receipt.error_code=error instanceof MigrationError?error.code:stage+'-failed';
  const code=error?.sqlstate??error?.code;if(typeof code==='string'&&/^[A-Z0-9]{5}$/.test(code))receipt.sqlstate=code;
  if(error?.phase)receipt.restore_failure={phase:error.phase,commit_status:error.commit_status??'unknown'};
  if(temporary&&fs.existsSync(path.join(temporary,'restore.json')))try{receipt.restore=JSON.parse(fs.readFileSync(path.join(temporary,'restore.json')));}catch{}
 }finally{
  if(owner)try{await owner.close();receipt.owner_connection_closed=true;}catch{receipt.owner_connection_closed=false;receipt.status='failed';receipt.owner_close_error_code='private-owner-close-failed';}
  if(createdId)try{if(createdId===productionBranchId||!validId(createdId))fail('unsafe-rehearsal-cleanup-target');await api('DELETE','/branches/'+createdId);receipt.cleanup_status='deleted';}catch{receipt.status='failed';receipt.cleanup_status='failed';receipt.retained_validation_branch_id=createdId;}
  receipt.management_requests=requests;receipt.completed_at_utc=new Date().toISOString();receipt.limitations=['No private Site runtime binding, Neon Auth or media-object relocation.','Capacity uses a reviewed operational budget, not verified provider quota.','Production partial or ambiguous installation requires explicit read-only verification; no data reset or automatic nonempty retry.'];
  checkpoint();if(temporary)fs.rmSync(temporary,{recursive:true,force:true});
 }
 return receipt;
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{const [mode='rehearsal',operationFile='.github/operations/neon-storage-rehearsal.json',...extra]=process.argv.slice(2);if(extra.length)fail('invalid-command-arguments');const receipt=await runNeonStorageMigration({mode,operationFile,onProgress:progress=>{if(progress.rows===progress.expected_rows)console.log(JSON.stringify({stage:'original-owner-restore',collection:progress.collection,rows:progress.rows}));}});console.log(JSON.stringify(receipt));if(receipt.mode==='production'&&receipt.status==='verified')console.log(JSON.stringify(encryptedCredentialLogPayload(receipt,fs.readFileSync('data/validation/neon-storage-migration/credential-envelope.json'))));if(!['verified','skipped'].includes(receipt.status))process.exitCode=1;}
 catch{console.error(JSON.stringify({status:'failed',error_code:'sanitized-migration-receipt-unavailable',credentials_logged:false}));process.exitCode=1;}
}
