import fs from 'node:fs';
import path from 'node:path';
import {execFileSync,spawn} from 'node:child_process';
import {createHash,randomUUID} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {storageExportV2Contract,storageExportV2Definitions,storageExportV2Collections,v2MarkerIdentity} from '../hosted/storage-export-v2-contract.js';
import {storageCatalogV2} from '../hosted/storage-export-v2.js';
import {storageRowsHashV2Ordered} from './restore-postgres-storage-v2.mjs';
import {readClaim,workSpec,githubPages,githubAPI} from './issue-claim-contract.mjs';
import {expectedNeonProjectId,verifyNeonProject} from './verify-neon-project.mjs';
import {backupRecipientFingerprint,sealRecoveryBackup} from './recovery-backup-envelope.mjs';

export const recoveryImage='postgres@sha256:77f585114c32fbca283dc835b0596f4e52b51b4c6662d7810b2f4084f60a1873';
export const recoveryWorkflow='.github/workflows/current-postgres-recovery.yml';
const branchId='br-summer-butterfly-ar8qikk5',repo='ChengshuLi/WorldAtlas';
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const need=(condition,code)=>{if(!condition)throw new Error(code);};
const ident=name=>'"'+name.replaceAll('"','""')+'"';
const maxJSON=128*1024*1024,maxDump=256*1024*1024;
const native=(args,input,timeout=180000,maxBuffer=maxJSON)=>execFileSync('docker',args,{input,timeout,maxBuffer,stdio:['pipe','pipe','pipe']});

export function validateRecoveryWindow(window,claim,{head,toolSHA,now=Date.now(),phase='start',reservationIssue,sourceClaim,handoffReceipt,dependencies=[]}={}){
 need(window?.version===1&&window.issue===51&&[51,714].includes(window.queue)&&(window.operator_worker_id==='engineering-central-publication-20261003'||(window.reservation_issue!==undefined&&window.reservation_issue!==51&&/^engineering-[a-z0-9-]{1,80}$/.test(window.operator_worker_id??''))),'invalid-publisher-window');
 need(window.primary_main_commit===head&&window.capture_tool_sha256===toolSHA&&window.method==='readonly-native-pg-dump-and-isolated-restore','unreviewed-window-tool');
 need(backupRecipientFingerprint(window.backup_recipient_public_key)===window.backup_recipient_sha256,'unpinned-private-backup-recipient');
 const time=Date.parse(window.observed_at_utc),expiry=Date.parse(window.expires_at_utc);
 need(Number.isFinite(time)&&time<=now&&(phase==='end'||now-time<=10*60000)&&expiry>now&&expiry-time<=30*60000,'stale-publisher-window');
 const reservationNumber=window.reservation_issue===undefined?51:window.reservation_issue;
 need(Number.isSafeInteger(reservationNumber)&&reservationNumber>0,'invalid-operation-reservation-issue');
 need(claim?.active&&claim.live_work===true&&claim.issue_number===reservationNumber&&claim.claim_id===window.claim_id&&claim.worker_id===window.holder_worker_id&&claim.branch===window.claim_branch&&Date.parse(claim.expires_at)>now,'unconfirmed-live-reservation');
 if(reservationNumber!==51){
  // The original worker explicitly releases its implementation reservation;
  // expiry or a false live flag alone is not a completed handoff.
  need(sourceClaim?.issue_number===51&&sourceClaim.active===false&&sourceClaim.live_work===false&&Number.isFinite(Date.parse(sourceClaim.released_at))&&Date.parse(sourceClaim.released_at)<=now,'original-implementation-not-released');
  const labels=(reservationIssue?.labels??[]).map(label=>typeof label==='string'?label:label.name);
  need(reservationIssue?.number===reservationNumber&&reservationIssue.state==='open'&&labels.includes('type:engineering')&&!labels.some(label=>['type:geography','type:history-research','status:blocked','kind:umbrella'].includes(label))&&labels.includes('kind:work-item')&&labels.includes('status:ready'),'unreviewed-operation-issue');
  const spec=workSpec(reservationIssue.body),operation=spec.production_operation;
  need(spec.depends_on.every(number=>dependencies.some(issue=>issue.number===number&&issue.state==='closed')),'operation-dependency-not-complete');
  need(spec.mode==='engineering'&&operation?.source_issue===51&&operation.queue===window.queue&&operation.publisher_worker_id===window.operator_worker_id&&claim.worker_id===window.operator_worker_id&&claim.mode==='engineering','operation-not-publisher-owned');
  need(/^[a-f0-9]{64}$/.test(window.reservation_scope_sha256??'')&&sha(JSON.stringify(spec))===window.reservation_scope_sha256,'changed-operation-scope');
  need(/^https:\/\/github\.com\/ChengshuLi\/WorldAtlas\/issues\/(51|714)#issuecomment-[1-9]\d*$/.test(operation.handoff_receipt_url??'')&&handoffReceipt?.html_url===operation.handoff_receipt_url&&handoffReceipt.user?.type==='User'&&['OWNER','MEMBER','COLLABORATOR'].includes(handoffReceipt.author_association)&&String(handoffReceipt.body??'').trim().length>0,'missing-authorized-implementation-handoff');
 }
 need(window.site?.project_id==='appgprj_6abdf87277c08191bce4a22b8dfb25db'&&Number.isSafeInteger(window.site.version)&&window.site.version>0&&typeof window.site.deployment_id==='string'&&window.site.deployment_id.startsWith('appgdep_'),'unpinned-site-window');
 need(window.read_only===true&&window.drain_verified===true&&window.restore_writes_operator===window.operator_worker_id&&typeof window.rollback_receipt_url==='string'&&window.rollback_receipt_url.startsWith('https://github.com/ChengshuLi/WorldAtlas/'),'unsettled-maintenance-window');
 const marker=window.source_marker;
 need(marker?.version===2&&marker.backend==='postgres'&&marker.read_only===true&&!marker.legacy_projection&&Number.isSafeInteger(marker.revision)&&marker.revision>=0&&same(marker.contract,storageExportV2Contract),'unsupported-source-contract');
 need(['fingerprint','catalog_sha256','geographic_releases_sha256','footprint_versions_sha256'].every(k=>/^[a-f0-9]{64}$/.test(marker[k]??'')),'incomplete-source-hashes');
 need(same(Object.keys(marker.counts??{}).sort(),[...storageExportV2Collections].sort())&&storageExportV2Collections.every(k=>Number.isSafeInteger(marker.counts[k])&&marker.counts[k]>=0),'incomplete-source-counts');
 need(marker.catalog_sha256===storageExportV2Contract.postgres_catalog_sha256&&sha(JSON.stringify(v2MarkerIdentity(marker)))===marker.fingerprint,'invalid-source-marker');
 return window;
}

/** Load fresh canonical reservations and the bounded publisher operation scope.
 * Repeated after capture; no provider/credential access occurs here. */
export async function loadRecoveryReservation(window,api){
 const sourceClaim=readClaim(await githubPages(api,'/repos/'+repo+'/issues/51/comments'));
 if(window.reservation_issue===undefined||window.reservation_issue===51)return {claim:sourceClaim};
 need(Number.isSafeInteger(window.reservation_issue)&&window.reservation_issue>0,'invalid-operation-reservation-issue');
 const reservationIssue=await api('/repos/'+repo+'/issues/'+window.reservation_issue);
 const spec=workSpec(reservationIssue.body),operation=spec.production_operation;
 const dependencies=await Promise.all(spec.depends_on.map(number=>api('/repos/'+repo+'/issues/'+number)));
 const match=/^https:\/\/github\.com\/ChengshuLi\/WorldAtlas\/issues\/(51|714)#issuecomment-([1-9]\d*)$/.exec(operation?.handoff_receipt_url??'');
 need(match,'missing-authorized-implementation-handoff');
 const handoffReceipt=await api('/repos/'+repo+'/issues/comments/'+match[2]);
 const claim=readClaim(await githubPages(api,'/repos/'+repo+'/issues/'+window.reservation_issue+'/comments'));
 return {claim,sourceClaim,reservationIssue,handoffReceipt,dependencies};
}

export function validatedOwnerConnection(value,host){
 let uri;try{uri=new URL(value);}catch{throw Error('invalid-owner-connection');}
 need(['postgres:','postgresql:'].includes(uri.protocol)&&uri.hostname===host&&(!uri.port||uri.port==='5432')&&/^ep-[a-z0-9-]+(?:\.[a-z0-9-]+)+\.neon\.tech$/.test(host),'owner-endpoint-mismatch');
 need(decodeURIComponent(uri.username)==='neondb_owner'&&decodeURIComponent(uri.pathname)==='/neondb'&&uri.searchParams.get('sslmode')==='require'&&!uri.hash,'owner-identity-mismatch');
 const password=decodeURIComponent(uri.password);
 need(password.length>0&&password.length<=8192&&!/[\u0000-\u001f\u007f]/.test(password),'unsafe-owner-secret');
 return {host,password};
}

export function tableReadSQL(collection){
 const definition=storageExportV2Definitions[collection];need(definition,'unknown-factual-table');
 const order=definition.keys.map(k=>ident(k)+(k==='rowid'?'':' COLLATE "C"')).join(',');
 return `SELECT ${definition.columns.map(ident).join(',')} FROM ${ident(definition.table)} ORDER BY ${order}`;
}
const inventorySQL="SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name";
const registrySQL='SELECT migration_id,file_sha256,core_schema_sha256,source_snapshot_fingerprint,base_guards_sha256,installed_contract_sha256,applied_at FROM worldatlas_schema_migrations ORDER BY migration_id COLLATE "C"';
const permissionSQL=`SELECT c.relname object_name,c.relkind object_kind,pg_get_userbyid(c.relowner) owner,
 has_table_privilege('worldatlas_app',c.oid,'SELECT') app_select,has_table_privilege('worldatlas_app',c.oid,'INSERT') app_insert,
 has_table_privilege('worldatlas_app',c.oid,'UPDATE') app_update,has_table_privilege('worldatlas_app',c.oid,'DELETE') app_delete,
 has_table_privilege('worldatlas_app',c.oid,'TRUNCATE') app_truncate,c.relacl::text acl
 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='r' ORDER BY c.relname`;

/** Native PostgreSQL JSON scalar spelling is used only for comparison between
 * the same source and isolated native major. Raw evidence remains TEXT; each
 * complete row is hashed before the bounded ordered digest aggregation. */
export function nativeMembershipDigestSQL(){
 const order='release_id COLLATE \"C\",entity_id COLLATE \"C\"';
 return `SELECT count(*)::bigint rows,encode(sha256(convert_to(coalesce(string_agg(encode(sha256(convert_to(row_to_json(q)::text,'UTF8')),'hex'),'' ORDER BY ${order}),''),'UTF8')),'hex') ordered_rows_sha256 FROM (${tableReadSQL('geographic_memberships')}) q`;
}

export async function readRecoveryInventory(query,{directory}={}){
 const names=await query(inventorySQL),expected=[...storageExportV2Collections.map(k=>storageExportV2Definitions[k].table),'worldatlas_schema_migrations'].sort();
 need(same(names.map(r=>r.table_name),expected),'incomplete-owner-and-factual-inventory');
 const identity=(await query("SELECT current_database() database_name,current_user role_name,current_schema() schema_name,current_setting('server_version_num') version"))[0];
 need(identity?.role_name==='neondb_owner'&&identity.schema_name==='public'&&/^18\d{4}$/.test(String(identity.version)),'unexpected-postgres-owner-or-version');
 const catalog=await storageCatalogV2({dialect:'postgres',prepare:sql=>({all:async()=>({results:await query(sql)})})});
 const proofs={};let revision=0;
 for(const collection of storageExportV2Collections){
  const metrics=(await query(`SELECT count(*) rows,coalesce(sum(octet_length(row_to_json(q)::text)),0) bytes,coalesce(max(octet_length(row_to_json(q)::text)),0) largest FROM (${tableReadSQL(collection)}) q`))[0];
  need(metrics&&['rows','bytes','largest'].every(k=>Number.isSafeInteger(metrics[k])&&metrics[k]>=0)&&metrics.largest<=8*1024*1024,'measured-source-table-exceeds-bound');
  if(collection==='geographic_memberships'){
   need(metrics.rows<=2000000&&metrics.largest<=8*1024*1024,'native-membership-digest-bound');
   const proof=(await query(nativeMembershipDigestSQL()))[0];
   need(proof?.rows===metrics.rows&&/^[a-f0-9]{64}$/.test(proof.ordered_rows_sha256??''),'native-membership-digest-invalid');
   proofs[collection]={count:metrics.rows,ordered_rows_sha256:proof.ordered_rows_sha256,hash_kind:'sha256-pg-json-text-row-digests-c-key-order-v1'};continue;
  }
  need(metrics.bytes+metrics.rows*2+2<=maxJSON,'measured-source-table-exceeds-bound');
  const rows=await query(tableReadSQL(collection));
  need(rows.length===metrics.rows,'measured-source-table-changed');
  need(rows.every(row=>same(Object.keys(row),storageExportV2Definitions[collection].columns)),'changed-raw-factual-columns');
  if(collection==='ingestions')for(const row of rows){need(Number.isSafeInteger(row.rowid)&&row.rowid>0,'unsafe-original-rowid');revision=Math.max(revision,row.rowid);}
  proofs[collection]={count:rows.length,ordered_rows_sha256:storageRowsHashV2Ordered(collection,rows)};
  if(directory)fs.writeFileSync(path.join(directory,collection+'.json'),JSON.stringify(rows)+'\n',{flag:'wx',mode:0o600});
 }
 const registry=await query(registrySQL);need(registry.length>0,'missing-owner-registry-state');
 const permissions=await query(permissionSQL),privateRegistry=permissions.find(r=>r.object_name==='worldatlas_schema_migrations');
 need(privateRegistry?.owner==='neondb_owner'&&!privateRegistry.app_select&&!privateRegistry.app_insert&&!privateRegistry.app_update&&!privateRegistry.app_delete&&!privateRegistry.app_truncate,'owner-registry-exposed');
 const sequence=await query('SELECT last_value,is_called FROM atlas_ingestions_rowid_seq');
 need(sequence.length===1&&Number.isSafeInteger(sequence[0].last_value)&&sequence[0].last_value>=revision,'invalid-ingestion-sequence');
 return {identity,revision,catalog_sha256:sha(JSON.stringify(catalog)),collections:proofs,owner_registry:registry,owner_registry_sha256:sha(JSON.stringify(registry)),permissions,sequence};
}

// pg_restore clears search_path, but frozen PL/pgSQL helpers resolve public
// helper functions at COPY time. Adjust only its generated session header,
// before the first archive object; never search/replace factual COPY bytes.
export function isolatedRestoreSQL(bytes){
 need(Buffer.isBuffer(bytes)&&bytes.length<=maxDump,'restore-sql-size-limit');
 const separator=Buffer.from('\n-- Name: '),offset=bytes.indexOf(separator);
 need(offset>0&&offset<16384,'unsupported-native-restore-header');
 const header=bytes.subarray(0,offset).toString();
 const setting="SELECT pg_catalog.set_config('search_path', '', false);";
 need(header.split(setting).length===2,'ambiguous-native-restore-search-path');
 return Buffer.concat([Buffer.from(header.replace(setting,"SELECT pg_catalog.set_config('search_path', 'public,pg_catalog', false);")),bytes.subarray(offset)]);
}

// Native dump parsing flattens four original AND-expression trees. Reinstall
// those exact frozen reviewed CHECK definitions on the disposable target only,
// revalidating all restored rows; immutable source/catalog pins stay unchanged.

const maxExpandedRestore=1024*1024*1024;
/** Expand bounded native output onto a private file, without a giant JS Buffer. */
export async function nativeRestoreToFile(args,input,file){
 const fd=fs.openSync(file,'wx',0o600);let bytes=0;
 try{await new Promise((resolve,reject)=>{
  const child=spawn('docker',args,{stdio:['pipe','pipe','pipe']}),timer=setTimeout(()=>{child.kill('SIGKILL');reject(Error('native-restore-timeout'));},600000);
  let failure,stderrBytes=0;const fail=code=>{failure??=Error(code);child.kill('SIGKILL');};
  child.on('error',()=>fail('native-restore-client-failed'));
  child.stdout.on('data',chunk=>{bytes+=chunk.length;if(bytes>maxExpandedRestore){fail('expanded-native-restore-size-bound');return;}try{fs.writeSync(fd,chunk);}catch{fail('native-restore-disk-write-failed');}});
  child.stderr.on('data',chunk=>{stderrBytes+=chunk.length;if(stderrBytes>1024*1024)fail('native-restore-stderr-bound');});
  child.stdin.on('error',()=>fail('native-restore-input-failed'));
  child.on('close',code=>{clearTimeout(timer);if(failure||code!==0)reject(failure??Error('native-restore-expansion-failed'));else resolve();});child.stdin.end(input);
 });fs.fsyncSync(fd);need(bytes>0,'empty-native-restore');}finally{fs.closeSync(fd);}
 return {bytes};
}
export function patchNativeRestoreFile(file){
 const fd=fs.openSync(file,'r'),prefix=Buffer.alloc(16384);let count;try{count=fs.readSync(fd,prefix,0,prefix.length,0);}finally{fs.closeSync(fd);}
 const bytes=prefix.subarray(0,count),at=bytes.indexOf(Buffer.from('\n-- Name: '));need(at>0,'unsupported-native-restore-header');
 const patched=isolatedRestoreSQL(bytes),out=file+'.header-patched',target=fs.openSync(out,'wx',0o600),source=fs.openSync(file,'r');
 try{fs.writeSync(target,patched);let offset=count;const chunk=Buffer.alloc(1024*1024);for(;;){const n=fs.readSync(source,chunk,0,chunk.length,offset);if(!n)break;fs.writeSync(target,chunk.subarray(0,n));offset+=n;}fs.fsyncSync(target);}finally{fs.closeSync(source);fs.closeSync(target);}fs.renameSync(out,file);
}
export async function nativeRestoreFromFile(args,file){
 need(fs.statSync(file).size<=maxExpandedRestore+128,'expanded-native-restore-size-bound');
 await new Promise((resolve,reject)=>{
  const child=spawn('docker',args,{stdio:['pipe','pipe','pipe']}),input=fs.createReadStream(file),timer=setTimeout(()=>{child.kill('SIGKILL');reject(Error('native-restore-apply-timeout'));},600000);
  let failure,bytes=0;const fail=code=>{failure??=Error(code);input.destroy();child.kill('SIGKILL');};
  child.on('error',()=>fail('native-restore-client-failed'));input.on('error',()=>fail('native-restore-file-failed'));child.stdin.on('error',()=>fail('native-restore-input-failed'));
  for(const stream of [child.stdout,child.stderr])stream.on('data',chunk=>{bytes+=chunk.length;if(bytes>2*1024*1024)fail('native-restore-output-bound');});
  child.on('close',code=>{clearTimeout(timer);input.destroy();if(failure||code!==0)reject(failure??Error('native-restore-apply-failed'));else resolve();});input.pipe(child.stdin);
 });
}

export function isolatedOriginalChecks(schema){
 need(sha(schema)===storageExportV2Contract.postgres_migrations[0].sha256,'unreviewed-original-constraint-source');
 const pairs=[['atlas_sources','source_dates'],['atlas_entities','entity_dates'],['atlas_attribute_records','attribute_dates'],['atlas_names','name_dates']];
 return 'SET ROLE neondb_owner; BEGIN;\n'+pairs.map(([table,name])=>{
  const line=schema.toString().split('\n').find(line=>line.includes('CONSTRAINT "'+name+'" CHECK('));
  need(line&&line.trim().endsWith(','),'missing-original-check-definition');
  return `ALTER TABLE ${ident(table)} DROP CONSTRAINT ${ident(name)}; ALTER TABLE ${ident(table)} ADD ${line.trim().slice(0,-1)};`;
 }).join('\n')+'\nCOMMIT;';
}

export function assertCurrentInventory(inventory,marker){
 need(inventory.identity.database_name==='neondb'&&inventory.revision===marker.revision&&inventory.catalog_sha256===marker.catalog_sha256,'source-identity-or-catalog-drift');
 need(storageExportV2Collections.every(k=>inventory.collections[k].count===marker.counts[k]),'source-count-drift');
 need(inventory.collections.geographic_releases.ordered_rows_sha256===marker.geographic_releases_sha256&&inventory.collections.footprint_versions.ordered_rows_sha256===marker.footprint_versions_sha256,'source-release-drift');
}
export function assertRestoredInventory(before,target,after){
 need(same({...before,identity:null},{...after,identity:null}),'source-changed-during-capture');
 need(same({...before,identity:null},{...target,identity:null}),'restored-facts-owner-or-permissions-differ');
}

function queryJSON(execute,secrets=[]){return async sql=>{
 const raw=execute(`SELECT coalesce(json_agg(row_to_json(q)),'[]'::json) FROM (${sql}) q;`);
 need(raw.length<=maxJSON&&!secrets.some(s=>s&&raw.includes(Buffer.from(s))),'raw-query-size-or-secret-limit');const rows=JSON.parse(raw.toString());need(Array.isArray(rows),'invalid-native-json');return rows;
};}
function sourceDockerArgs(connection,name){return ['create','--name',name,'-i','--read-only','--network','bridge','--tmpfs','/tmp:rw,size=16m',
  '-e','PGHOST='+connection.host,'-e','PGUSER=neondb_owner','-e','PGDATABASE=neondb','-e','PGSSLMODE=require',
  '-e','PGOPTIONS=-c default_transaction_read_only=on -c statement_timeout=60000 -c lock_timeout=5000',
  '--entrypoint','sh',recoveryImage,'-c','IFS= read -r PGPASSWORD; export PGPASSWORD; exec "$@"','private-native-command'];}
function removeOwnedContainer(name){
 try{native(['rm','-fv',name],undefined,30000,1024*1024);}catch{}
 need(native(['ps','-a','--filter','name=^/'+name+'$','--format','{{.ID}}'],undefined,15000,1024*1024).toString().trim()==='','source-or-target-cleanup-unconfirmed');
}
function sourceClient(connection,readers){
 return (args,input=Buffer.alloc(0),maxBuffer=maxJSON)=>{
  const name='atlas-recovery-reader-'+randomUUID();readers.add(name);
  try{native([...sourceDockerArgs(connection,name),...args],undefined,180000,1024*1024);return native(['start','-ai',name],Buffer.concat([Buffer.from(connection.password+'\n'),Buffer.from(input)]),180000,maxBuffer);}
  finally{removeOwnedContainer(name);readers.delete(name);}
 };
}
async function holdSourceLock(connection,readers){
 const name='atlas-recovery-lock-'+randomUUID();readers.add(name);
 native([...sourceDockerArgs(connection,name),'psql','-X','-Atq','-v','ON_ERROR_STOP=1'],undefined,180000,1024*1024);
 const child=spawn('docker',['start','-ai',name],{stdio:['pipe','pipe','pipe']});
 // A session lock coordinates API/owner writers without an open transaction.
 // The public backend PID is independently rechecked before every source query.
 const observed=await new Promise((resolve,reject)=>{
  let text='';const timeout=setTimeout(()=>reject(Error('source-lock-readiness-timeout')),15000);
  const fail=()=>{clearTimeout(timeout);reject(Error('source-lock-client-exited'));};child.once('error',fail);child.once('exit',fail);child.stdin.on('error',fail);child.stderr.on('data',()=>{});
  child.stdout.on('data',chunk=>{text+=chunk.toString();if(text.length>1024){fail();return;}if(!text.includes('\n'))return;
   try{const value=JSON.parse(text.trim());need(value.locked===true&&Number.isSafeInteger(value.pid)&&value.pid>0,'shared-source-lock-unavailable');clearTimeout(timeout);resolve(value);}catch{fail();}
  });
  child.stdin.write(connection.password+'\nSELECT json_build_object(\'locked\',pg_try_advisory_lock(807245315,1),\'pid\',pg_backend_pid());\n');
 });
 return {pid:observed.pid,alive:()=>child.exitCode===null&&!child.killed,close:()=>{child.stdin.end('\\q\n');removeOwnedContainer(name);readers.delete(name);}};
}
function save(file,value,secrets=[]){
 const raw=JSON.stringify(value,null,2)+'\n';need(!secrets.some(s=>s&&raw.includes(s)),'unsafe-receipt');
 const fd=fs.openSync(file+'.next','w',0o600);try{fs.writeFileSync(fd,raw);fs.fsyncSync(fd);}finally{fs.closeSync(fd);}fs.renameSync(file+'.next',file);
}

export async function boundedOwnerJSON(response){
 need(response.ok&&response.body,'owner-api-read-failed');const chunks=[];let bytes=0;
 try{for await(const chunk of response.body){bytes+=chunk.length;need(bytes<=2*1024*1024,'owner-api-size-limit');chunks.push(chunk);}}
 catch{try{await response.body.cancel();}catch{}throw Error('bounded-owner-response-failed');}
 const result=JSON.parse(Buffer.concat(chunks).toString());need(result&&typeof result==='object'&&!Array.isArray(result),'invalid-owner-api-object');return result;
}

/** Only the publisher's fresh reviewed window plus a live canonical claim can
 * obtain the existing owner connection. Source clients enforce read-only; all
 * restoration and role/schema writes stay on a network-none ephemeral target.
 */
export async function runCurrentPostgresRecovery({env=process.env,fetcher=fetch,output='data/validation/current-postgres-recovery'}={}){
 const started=Date.now(),receipt={version:1,status:'failed',source_read_only:true,production_writes:0,started_at_utc:new Date().toISOString()},secrets=[];
 let target,lock,releaseProbe,stage='authorize';const readers=new Set();
 need(!fs.existsSync(output),'preserve-existing-recovery-target');fs.mkdirSync(output,{recursive:true,mode:0o700});
 const publicOutput=path.join(output,'public-receipts');fs.mkdirSync(publicOutput,{mode:0o700});const receiptFile=path.join(publicOutput,'receipt.json');
 try{
  need(env.GITHUB_EVENT_NAME==='workflow_dispatch'&&env.GITHUB_REPOSITORY===repo&&env.GITHUB_WORKFLOW_REF===repo+'/'+recoveryWorkflow+'@refs/heads/main'&&/^[a-f0-9]{40}$/.test(env.GITHUB_SHA??'')&&/^[1-9]\d*$/.test(env.WINDOW_COMMENT_ID??'')&&env.NEON_PROJECT_ID===expectedNeonProjectId,'trusted-main-manual-context-required');
  secrets.push(env.NEON_API_KEY,env.GITHUB_TOKEN);const api=githubAPI(env.GITHUB_TOKEN);
  const comment=await api('/repos/'+repo+'/issues/comments/'+env.WINDOW_COMMENT_ID);
  need(/^https:\/\/github\.com\/ChengshuLi\/WorldAtlas\/issues\/(51|714)#issuecomment-[1-9]\d*$/.test(comment.html_url??'')&&comment.user?.type==='User'&&['OWNER','MEMBER','COLLABORATOR'].includes(comment.author_association)&&comment.user.login===env.GITHUB_ACTOR,'authorized-publisher-queue-window-required');
  const matches=[...String(comment.body).matchAll(/<!-- worldatlas-recovery-window:v1\n([\s\S]*?)\n-->/g)];need(matches.length===1,'unique-publisher-window-required');
  const toolSHA=sha(fs.readFileSync(fileURLToPath(import.meta.url))),requestedWindow=JSON.parse(matches[0][1]),reservation=await loadRecoveryReservation(requestedWindow,api),{claim}=reservation;
  const window=validateRecoveryWindow(requestedWindow,claim,{head:env.GITHUB_SHA,toolSHA,...reservation});
  need(comment.html_url==='https://github.com/'+repo+'/issues/'+window.queue+'#issuecomment-'+comment.id,'window-tracking-issue-mismatch');
  need(window.operator_github_login===comment.user.login,'publisher-author-binding-required');
  receipt.window_comment_id=comment.id;receipt.claim_id=claim.claim_id;receipt.reservation_issue=claim.issue_number;receipt.source_marker=window.source_marker;receipt.site=window.site;receipt.github={head:env.GITHUB_SHA,run_id:env.GITHUB_RUN_ID,run_attempt:env.GITHUB_RUN_ATTEMPT};save(receiptFile,receipt,secrets);
  stage='verify-production-metadata';receipt.project=await verifyNeonProject({apiKey:env.NEON_API_KEY,projectId:expectedNeonProjectId,fetchImpl:fetcher});
  need(receipt.project.branch.id===branchId&&receipt.project.project.configured_postgres_major===18,'production-branch-or-major-changed');
  const get=async suffix=>boundedOwnerJSON(await fetcher('https://console.neon.tech/api/v2/projects/'+expectedNeonProjectId+suffix,{headers:{Authorization:'Bearer '+env.NEON_API_KEY},redirect:'error',signal:AbortSignal.timeout(15000)}));
  const endpoints=(await get('/endpoints')).endpoints?.filter(e=>e.branch_id===branchId&&e.type==='read_write');need(endpoints?.length===1,'ambiguous-production-endpoint');
  const connection=validatedOwnerConnection((await get('/connection_uri?'+new URLSearchParams({branch_id:branchId,database_name:'neondb',role_name:'neondb_owner',pooled:'false'}))).uri,endpoints[0].host);secrets.push(connection.password);
  stage='native-client';native(['pull',recoveryImage],undefined,180000,4*1024*1024);
  const client=sourceClient(connection,readers),rawSourceQuery=queryJSON(sql=>client(['psql','-X','-Atq','-v','ON_ERROR_STOP=1'],sql),secrets);
  stage='shared-source-lock';lock=await holdSourceLock(connection,readers);releaseProbe=async()=>{const result=(await rawSourceQuery(`SELECT exists(SELECT 1 FROM pg_locks WHERE locktype='advisory' AND pid=${lock.pid} AND classid=807245315 AND objid=1 AND objsubid=2 AND granted) held`))[0];need(result?.held===false,'source-lock-release-unconfirmed');};receipt.source_lock={key:[807245315,1],backend_pid:lock.pid,kind:'session-level; no open transaction'};
  const sourceQuery=async sql=>{need(lock.alive(),'source-lock-session-lost');const held=(await rawSourceQuery(`SELECT exists(SELECT 1 FROM pg_locks WHERE locktype='advisory' AND pid=${lock.pid} AND classid=807245315 AND objid=1 AND objsubid=2 AND granted) held`))[0];need(held?.held===true,'source-lock-lost');const rows=await rawSourceQuery(sql);need(lock.alive(),'source-lock-session-lost');return rows;};
  const capture=path.join(output,'original-rows');fs.mkdirSync(capture,{mode:0o700});
  stage='current-source-inventory';const before=await readRecoveryInventory(sourceQuery,{directory:capture});assertCurrentInventory(before,window.source_marker);save(path.join(output,'source-inventory.json'),before,secrets);
  stage='current-native-dump';await sourceQuery('SELECT 1 lock_checkpoint');const dumpStarted=Date.now(),dump=client(['pg_dump','--format=custom','--schema=public','--no-owner','--lock-wait-timeout=5000'],undefined,maxDump);
  await sourceQuery('SELECT 1 lock_checkpoint');need(dump.length>5&&dump.subarray(0,5).toString()==='PGDMP'&&!secrets.some(s=>s&&dump.includes(Buffer.from(s))),'invalid-or-unsafe-native-dump');
  fs.writeFileSync(path.join(output,'current-public-schema.dump'),dump,{flag:'wx',mode:0o600});receipt.dump={bytes:dump.length,sha256:sha(dump),duration_ms:Date.now()-dumpStarted,owner_registry_included:true,acl_included:true};save(receiptFile,receipt,secrets);
  stage='encrypted-original-backup';const sealed=sealRecoveryBackup({bytes:dump,publicKey:window.backup_recipient_public_key,context:{purpose:'worldatlas-private-sql-backup',repository:repo,primary_main_commit:env.GITHUB_SHA,run_id:env.GITHUB_RUN_ID,run_attempt:env.GITHUB_RUN_ATTEMPT,window_comment_id:String(comment.id),source_fingerprint:window.source_marker.fingerprint,project_id:expectedNeonProjectId,branch_id:branchId}});
  fs.writeFileSync(path.join(publicOutput,'current-public-schema.dump.aesgcm'),sealed.ciphertext,{flag:'wx',mode:0o600});save(path.join(publicOutput,'backup-envelope.json'),sealed.envelope,secrets);
  need(sha(fs.readFileSync(path.join(publicOutput,'current-public-schema.dump.aesgcm')))===sealed.envelope.ciphertext_sha256&&same(JSON.parse(fs.readFileSync(path.join(publicOutput,'backup-envelope.json'),'utf8')),sealed.envelope),'encrypted-backup-disk-readback-failed');
  receipt.encrypted_backup={recipient_sha256:sealed.envelope.recipient_sha256,ciphertext_bytes:sealed.ciphertext.length,ciphertext_sha256:sealed.envelope.ciphertext_sha256,envelope_sha256:sha(fs.readFileSync(path.join(publicOutput,'backup-envelope.json'))),in_memory_aead_roundtrip_verified:true,ciphertext_disk_readback_verified:sha(fs.readFileSync(path.join(publicOutput,'current-public-schema.dump.aesgcm')))===sealed.envelope.ciphertext_sha256,recipient_private_key_recovery_verified:false};save(receiptFile,receipt,secrets);
  stage='isolated-native-target';target='atlas-recovery-'+randomUUID();native(['run','-d','--name',target,'--network','none','--read-only','--tmpfs','/var/lib/postgresql:rw,size=2g','--tmpfs','/var/run/postgresql:rw,size=16m','--memory','4g','-e','POSTGRES_HOST_AUTH_METHOD=trust',recoveryImage],undefined,60000,1024*1024);
  const targetExec=(args,input,maxBuffer=maxJSON)=>native(['exec','-i',target,...args],input,180000,maxBuffer);
  let ready=false;for(let attempt=0;attempt<30;attempt++){try{targetExec(['pg_isready','-U','postgres']);ready=true;break;}catch{await new Promise(resolve=>setTimeout(resolve,1000));}}need(ready,'isolated-target-not-ready');
  targetExec(['psql','-X','-Atq','-U','postgres','-v','ON_ERROR_STOP=1'],"CREATE ROLE neondb_owner NOLOGIN; CREATE ROLE worldatlas_app NOLOGIN; ALTER DATABASE postgres OWNER TO neondb_owner; DROP SCHEMA public;");
  stage='actual-current-native-restore';const restoreStarted=Date.now(),readback=fs.readFileSync(path.join(output,'current-public-schema.dump'));need(readback.length===receipt.dump.bytes&&sha(readback)===receipt.dump.sha256,'retained-dump-readback-failed');const expanded=path.join(output,'isolated-restore.sql');
  await nativeRestoreToFile(['exec','-i',target,'pg_restore','--file=-','--no-owner','--role','neondb_owner'],readback,expanded);
  patchNativeRestoreFile(expanded);
  await nativeRestoreFromFile(['exec','-i',target,'psql','-X','-U','postgres','-d','postgres','--single-transaction','-v','ON_ERROR_STOP=1'],expanded);targetExec(['psql','-X','-U','postgres','-d','postgres','-v','ON_ERROR_STOP=1'],isolatedOriginalChecks(fs.readFileSync('postgres/schema.sql')));receipt.isolated_original_checks_revalidated=true;receipt.restore_duration_ms=Date.now()-restoreStarted;receipt.dump.local_readback_verified=true;
  stage='full-source-and-target-readback';const targetQuery=queryJSON(sql=>targetExec(['psql','-X','-Atq','-U','postgres','-d','postgres','-v','ON_ERROR_STOP=1'],'SET ROLE neondb_owner; '+sql),secrets),restored=await readRecoveryInventory(targetQuery),after=await readRecoveryInventory(sourceQuery);assertCurrentInventory(after,window.source_marker);assertRestoredInventory(before,restored,after);
  const finalReservation=await loadRecoveryReservation(window,api);
  validateRecoveryWindow(window,finalReservation.claim,{head:env.GITHUB_SHA,toolSHA,phase:'end',...finalReservation});
  save(path.join(output,'restored-inventory.json'),restored,secrets);save(path.join(output,'after-inventory.json'),after,secrets);receipt.status='verified';receipt.collections=before.collections;receipt.owner_registry_sha256=before.owner_registry_sha256;receipt.catalog_sha256=before.catalog_sha256;receipt.owner_registry_private=true;
 }catch{receipt.status='failed';receipt.failure_stage=stage;receipt.error_code='bounded-current-recovery-'+stage+'-failed';}
 finally{
  if(lock){try{lock.close();await releaseProbe();receipt.source_lock_cleanup='database-lock-absence-and-reader-removal-confirmed';}catch{receipt.status='failed';receipt.source_lock_cleanup='unconfirmed';}}
  for(const reader of readers){try{removeOwnedContainer(reader);}catch{receipt.status='failed';(receipt.retained_source_readers??=[]).push(reader);}}
  if(target){try{removeOwnedContainer(target);receipt.isolated_target_cleanup='removed-and-absence-confirmed';}catch{receipt.status='failed';receipt.isolated_target_cleanup='failed';receipt.retained_target_name=target;}}
  receipt.duration_ms=Date.now()-started;receipt.completed_at_utc=new Date().toISOString();receipt.limitations=['Logical public-schema recovery; not verified provider-managed backup or server-global recovery.','Source role passwords, managed role memberships, provider secrets and private runtime bindings are excluded; restore through unchanged provider/Sites setup and documented private credential handoff.','Isolated roles are NOLOGIN and target database name differs; table owners/ACLs and effective table privileges are compared. Membership rows use a bounded native ordered row-digest inventory; original raw bytes are retained in the dump, not duplicated as an unbounded client JSON array. Schema/sequence/function/domain/default ACLs are retained in the original dump but not separately compared.','Publisher Site read-only/drain attestation is authenticated by queue author/dispatch actor; Actions does not independently access private Site. Worker IDs are cooperative identities, not separate security principals.','Registered object bytes are the separate414-object proof from PR711; no R2 objects are written.','Publisher must settle maintenance and prove restored writes separately; this tool never changes Site/read-only state.','Artifacts/local copies have limited retention; preserve original dump/rows and receipts before expiry.'];save(receiptFile,receipt,secrets);
 }
 return receipt;
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{const receipt=await runCurrentPostgresRecovery();console.log(JSON.stringify({status:receipt.status,failure_stage:receipt.failure_stage,dump:receipt.dump,collections:receipt.collections,owner_registry_sha256:receipt.owner_registry_sha256,duration_ms:receipt.duration_ms,isolated_target_cleanup:receipt.isolated_target_cleanup}));if(receipt.status!=='verified')process.exitCode=1;}
 catch{console.error('Current recovery unavailable; preserve sanitized receipts and obtain publisher coordination');process.exitCode=1;}
}
