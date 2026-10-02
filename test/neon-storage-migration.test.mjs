import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash,generateKeyPairSync} from 'node:crypto';
import {deflateRawSync} from 'node:zlib';
import {DatabaseSync} from 'node:sqlite';
import {PGlite} from '@electric-sql/pglite';
import {createPostgresDatabase} from '../hosted/postgres-adapter.js';
import {importBatch,registerMedia} from '../hosted/records.js';
import {storageExportCollections,exportStorageMarker,exportStoragePage} from '../hosted/storage-export.js';
import {stageGeographicRelease,finalizeGeographicRelease,geographicMembershipHash,geographicLocationIdsHash,geographicChangesHash} from '../hosted/geographic-releases.js';
import {exportHostedStorage} from '../scripts/export-hosted-storage.mjs';
import {packStorageCheckpoint} from '../scripts/storage-checkpoint.mjs';
import {readVerifiedStorageSnapshot} from '../scripts/restore-postgres-storage.mjs';
import {runNeonStorageMigration,validateMigrationOperation,rehearsalReceiptFromZIP,encryptedCredentialLogPayload,migrationWorkflowPath,migrationRepository} from '../scripts/neon-storage-migration.mjs';
import {expectedNeonProjectId} from '../scripts/verify-neon-project.mjs';
import {productionBranchId} from '../scripts/verify-neon-sql.mjs';
import {postgresSchemaURL} from '../scripts/verify-postgres-schema.mjs';
import {credentialRecipientFingerprint,decryptCredentialEnvelope} from '../scripts/credential-envelope.mjs';

const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const neonSecret='private-test-neon-key',githubSecret='private-test-actions-key',ownerPassword='private-test-owner-password';
const childId='br-full-storage-fixture',childHost='ep-storage-fixture.aws.neon.tech',productionHost='ep-production-fixture.aws.neon.tech';
const baseEnv={NEON_PROJECT_ID:expectedNeonProjectId,NEON_API_KEY:neonSecret,GITHUB_TOKEN:githubSecret,GITHUB_REPOSITORY:migrationRepository,GITHUB_RUN_ID:'111000',GITHUB_RUN_ATTEMPT:'1',GITHUB_SHA:'a'.repeat(40),GITHUB_WORKFLOW_REF:`${migrationRepository}/${migrationWorkflowPath}@refs/heads/work`};
const {publicKey,privateKey}=generateKeyPairSync('rsa',{modulusLength:3072,publicKeyEncoding:{type:'spki',format:'pem'},privateKeyEncoding:{type:'pkcs8',format:'pem'}});

class D1{
 constructor(){this.sqlite=new DatabaseSync(':memory:');this.sqlite.exec('PRAGMA foreign_keys=ON');for(const name of fs.readdirSync(new URL('../drizzle/',import.meta.url)).filter(name=>/^000[0-7]_.*\.sql$/.test(name)).sort())this.sqlite.exec(fs.readFileSync(new URL('../drizzle/'+name,import.meta.url),'utf8'));}
 prepare(sql){const sqlite=this.sqlite;let args=[];return {bind(...values){args=values;return this;},async all(){return {results:sqlite.prepare(sql).all(...args)};},async first(){return sqlite.prepare(sql).get(...args)??null;},run(){return {meta:{changes:Number(sqlite.prepare(sql).run(...args).changes)}};}};}
 async batch(statements){this.sqlite.exec('BEGIN IMMEDIATE');try{const results=statements.map(statement=>statement.run());this.sqlite.exec('COMMIT');return results;}catch(error){this.sqlite.exec('ROLLBACK');throw error;}}
}
async function snapshotFixture(t){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-full-neon-migration-')),source=path.join(root,'original-source'),db=new D1();t.after(()=>{db.sqlite.close();fs.rmSync(root,{recursive:true,force:true});});
 await importBatch(db,JSON.parse(fs.readFileSync(new URL('../data/hosted-type-catalog.json',import.meta.url))));
 const tiers=['continent','subcontinent','region','area','province','location'],entities=Array.from({length:6},(_,continent)=>tiers.map((kind,index)=>({id:`${kind}-${continent}`,kind,name:'Public '+kind,parent_id:index?`${tiers[index-1]}-${continent}`:null}))).flat();
 const sourceRecord=(id,status='historical')=>({id,name:'Public fixture '+id,url:'https://example.org/public-archive',license:'CC0',vintage:'2026',supported_from:status==='reference'?2026:-3000,supported_to:2027,status});
 await importBatch(db,{sources:[sourceRecord('history'),sourceRecord('reference','reference'),sourceRecord('example','example')],entities:[...entities,{id:'archived-place',kind:'place',name:'Archived',active:0},{id:'example-person',kind:'person',name:'Marked example',is_example:1}],categories:[{id:'owner:fixture',kind:'owner',name:'Fixture polity',source_id:'history'}]});
 db.sqlite.prepare("INSERT INTO atlas_attribute_records(id,location_id,attribute,value,valid_from,valid_to,method,status,source_id,metadata) VALUES('original','location-0','population',' \n 42 \t',1000,1100,'direct','sourced','history',?)").run('{ "original" : "retained", "duplicate":1,"duplicate":2 }');
 await importBatch(db,{retirements:[{id:'withdrawal',collection:'records',target_id:'original',replacement_id:'replacement',source_id:'history',reason:'Original correction'}],records:[{id:'replacement',location_id:'location-0',attribute:'population',value:43,valid_from:1000,valid_to:1100,source_id:'history'}],names:[{id:'name',entity_id:'location-0',name:'Dated fixture name',source_id:'history',valid_from:1000,valid_to:1100}],relationships:[{id:'example-link',source_entity_id:'location-0',target_entity_id:'example-person',relationship_type:'associated_with',source_id:'example',is_example:1}]});
 const sha='b'.repeat(64);await registerMedia(db,{id:'media',object_key:'media/'+sha,sha256:sha,bytes:42,mime:'audio/wav',name:'Public metadata',license:'CC0',attribution:'Public fixture',source_id:'history'});await importBatch(db,{media_links:[{id:'audio-link',media_id:'media',entity_id:'location-0',role:'audio',source_id:'history'}]});
 const memberships=entities.map(entity=>({entity_id:entity.id,kind:entity.kind,parent_id:entity.parent_id,reference_name:entity.name,active:1,source_id:'reference',evidence:{original:true}})),changes=[{id:'retain',old_entity_id:'location-0',new_entity_id:'location-0',change_type:'retain',source_id:'reference',evidence:{original:true}}];
 const release={id:'release',version:1,source_id:'reference',reference_date:'2026-10-01',hierarchy_sha256:'a'.repeat(64),footprints_sha256:'b'.repeat(64),membership_sha256:await geographicMembershipHash(memberships),location_ids_sha256:await geographicLocationIdsHash(memberships),changes_sha256:await geographicChangesHash(changes),expected_counts:Object.fromEntries(tiers.map(kind=>[kind,6]))};await stageGeographicRelease(db,{release,memberships,changes});await finalizeGeographicRelease(db,'release');
 db.sqlite.prepare("INSERT INTO atlas_ingestions(rowid,id,fingerprint,counts,created_at) VALUES(99,'original-journal',?,'{ \"records\" : 2 }',123456)").run('c'.repeat(64));
 await exportHostedStorage({origin:'https://example.org/',output:source,token:'private-original-export-token',fetcher:async(input,request)=>{
  assert.equal(request.headers['OAI-Sites-Authorization'],'Bearer private-original-export-token');const url=new URL(input);
  if(url.pathname.endsWith('/export-marker'))return Response.json({...await exportStorageMarker(db),read_only:true});return Response.json(await exportStoragePage(db,url.pathname.split('/').at(-1),{cursor:url.searchParams.get('cursor')??'',limit:Number(url.searchParams.get('limit')??200)}));
 }});
 const checkpointDirectory='data/storage-checkpoints/full-fixture';await packStorageCheckpoint({directory:source,output:path.join(root,checkpointDirectory)});
 const snapshot=readVerifiedStorageSnapshot(source),operation={version:1,project_id:expectedNeonProjectId,production_branch_id:productionBranchId,checkpoint_directory:checkpointDirectory,checkpoint_sha256:hash(fs.readFileSync(path.join(root,checkpointDirectory,'checkpoint.json'))),source_manifest_sha256:snapshot.manifest_sha256,source_snapshot_fingerprint:snapshot.manifest.snapshot_marker.fingerprint,source_revision:snapshot.revision,schema_sha256:hash(fs.readFileSync(postgresSchemaURL)),runtime_role_sql_sha256:hash(fs.readFileSync(new URL('../postgres/runtime-role.sql',import.meta.url))),database_budget_bytes:512*1024*1024};
 fs.mkdirSync(path.join(root,'.github/operations'),{recursive:true});fs.mkdirSync(path.join(root,'data/storage-migration'),{recursive:true});fs.writeFileSync(path.join(root,'data/storage-migration/recipient-public.pem'),publicKey);
 fs.writeFileSync(path.join(root,'.github/operations/neon-storage-rehearsal.json'),JSON.stringify(operation));
 return {root,source,snapshot,operation};
}
async function databaseFixture(t){
 const engine=new PGlite();t.after(()=>engine.close());await engine.query('CREATE ROLE neondb_owner LOGIN CREATEROLE NOINHERIT');const name=(await engine.query('SELECT current_database() AS name')).rows[0].name;assert.match(name,/^[a-z_]+$/);await engine.query(`ALTER DATABASE ${name} OWNER TO neondb_owner`);
 let closed=false,ownerWrites=0,appReads=0;
 const owner={
  async query(sql,params=[]){await engine.query('SET SESSION AUTHORIZATION neondb_owner');if(sql.startsWith('SELECT current_database() AS database_name'))return {rows:[{database_name:'neondb',role_name:'neondb_owner',schema_name:'public',server_version_num:'180003'}]};if(!/^SELECT|^SET LOCAL|^LOCK /i.test(sql.trim()))ownerWrites++;return engine.query(sql,params);},
  async runTransaction(callback){await engine.query('SET SESSION AUTHORIZATION neondb_owner');return engine.transaction(tx=>callback({query:async(sql,params=[])=>{if(!/^SELECT|^SET LOCAL|^LOCK /i.test(sql.trim()))ownerWrites++;return tx.query(sql,params);}}));},
  async close(){await engine.query('SET SESSION AUTHORIZATION postgres');closed=true;},
 };
 const appFactory=async uri=>{
  const url=new URL(uri);assert.equal(url.username,'worldatlas_app');assert.match(url.password,/^[A-Za-z0-9_-]{43}$/);
  return createPostgresDatabase({query:async(sql,params=[])=>{assert.match(sql.trim(),/^SELECT/i);appReads++;await engine.query('SET SESSION AUTHORIZATION worldatlas_app');const result=await engine.query(sql,params);return {...result,rowCount:result.rows.length};},transaction:async()=>{assert.fail('Runtime verification must not mutate the restored snapshot');}});
 };
 return {engine,owner,appFactory,get closed(){return closed;},get ownerWrites(){return ownerWrites;},get appReads(){return appReads;}};
}
function receiptZIP(raw){
 const name=Buffer.from('receipt.json'),compressed=deflateRawSync(raw),local=Buffer.alloc(30),central=Buffer.alloc(46),end=Buffer.alloc(22);
 local.writeUInt32LE(0x04034b50);local.writeUInt16LE(20,4);local.writeUInt16LE(8,8);local.writeUInt32LE(compressed.length,18);local.writeUInt32LE(raw.length,22);local.writeUInt16LE(name.length,26);
 central.writeUInt32LE(0x02014b50);central.writeUInt16LE(20,4);central.writeUInt16LE(20,6);central.writeUInt16LE(8,10);central.writeUInt32LE(compressed.length,20);central.writeUInt32LE(raw.length,24);central.writeUInt16LE(name.length,28);
 end.writeUInt32LE(0x06054b50);end.writeUInt16LE(1,8);end.writeUInt16LE(1,10);end.writeUInt32LE(central.length+name.length,12);end.writeUInt32LE(local.length+name.length+compressed.length,16);
 return Buffer.concat([local,name,compressed,central,name,end]);
}
function managementFixture({database,proof,archive,productionResponse=false,wrongHost=false,cleanupFailure=false,forgedRun=false}={}){
 const calls=[];let childName;
 const fetchImpl=async(input,request={})=>{
  const url=new URL(input),method=request.method??'GET';calls.push({method,path:url.pathname,host:url.hostname});
  if(url.hostname==='storage.blob.core.windows.net'){assert.equal(request.headers?.Authorization,undefined);return new Response(archive);}
  if(url.hostname==='api.github.com'){
   assert.equal(request.headers.Authorization,'Bearer '+githubSecret);
   if(url.pathname.endsWith('/zip'))return new Response(null,{status:302,headers:{location:'https://storage.blob.core.windows.net/private-download?opaque=not-logged'}});
   if(url.pathname.includes('/actions/runs/'))return Response.json({id:Number(proof.run_id),run_attempt:Number(proof.run_attempt),repository:{full_name:migrationRepository},head_branch:'work',head_sha:proof.head_sha,path:migrationWorkflowPath,status:'completed',conclusion:forgedRun?'failure':'success',html_url:proof.run_url});
   return Response.json({id:Number(proof.artifact_id),name:`neon-storage-rehearsal-${proof.run_id}-${proof.run_attempt}`,expired:false,workflow_run:{id:Number(proof.run_id),head_sha:proof.head_sha},digest:'sha256:'+proof.artifact_sha256,size_in_bytes:archive.length});
  }
  assert.equal(url.origin,'https://console.neon.tech');assert.equal(request.headers.Authorization,'Bearer '+neonSecret);assert.equal(url.href.includes(ownerPassword),false);
  if(method==='DELETE'){assert.equal(url.pathname.endsWith('/'+childId),true);assert.equal(database.closed,true);return new Response(null,{status:cleanupFailure?503:204});}
  if(method==='POST'){const payload=JSON.parse(request.body);assert.equal(payload.branch.parent_id,productionBranchId);childName=payload.branch.name;return Response.json({branch:{id:productionResponse?productionBranchId:childId,name:childName,parent_id:productionBranchId},endpoints:[{branch_id:childId,host:childHost,type:'read_write'}]});}
  if(url.pathname.endsWith('/connection_uri')){
   const host=url.searchParams.get('branch_id')===productionBranchId?productionHost:childHost;
   return Response.json({uri:`postgresql://neondb_owner:${ownerPassword}@${wrongHost?'ep-untrusted.aws.neon.tech':host}/neondb?sslmode=require`});
  }
  if(url.pathname.endsWith('/endpoints'))return Response.json({endpoints:[{branch_id:productionBranchId,host:productionHost,type:'read_write'}]});
  if(url.pathname.endsWith('/databases'))return Response.json({databases:[{branch_id:productionBranchId,name:'neondb',owner_name:'neondb_owner'}]});
  if(url.pathname.endsWith('/roles'))return Response.json({roles:[{branch_id:productionBranchId,name:'neondb_owner',password:ownerPassword}]});
  if(url.pathname.endsWith('/branches/'+childId))return Response.json({branch:{id:childId,name:childName,parent_id:productionBranchId,current_state:'ready'}});
  if(url.pathname.endsWith('/branches'))return Response.json({branches:[{id:productionBranchId,name:'production'}]});
  return Response.json({project:{id:expectedNeonProjectId,pg_version:18}});
 };
 return {fetchImpl,calls};
}
function assertSafeReceipt(root,output,receipt){
 const saved=fs.readFileSync(path.join(root,output,'receipt.json'),'utf8');assert.deepEqual(JSON.parse(saved),receipt);
 for(const secret of [neonSecret,githubSecret,ownerPassword,'postgresql://','private-original-export-token','raw-private-error'])assert.equal(saved.includes(secret),false);
 assert.ok(Buffer.byteLength(saved)<128*1024);assert.equal(receipt.production_deleted,false);
}
async function rehearse(t,f,overrides={}){
 const db=await databaseFixture(t),api=managementFixture({database:db,...overrides}),output='data/validation/rehearsal-'+Math.random().toString(36).slice(2);let connections=0;
 const receipt=await runNeonStorageMigration({root:f.root,env:baseEnv,output,fetchImpl:api.fetchImpl,sleepImpl:async()=>{},ownerDriverFactory:async uri=>{connections++;assert.equal(new URL(uri).hostname,childHost);return db.owner;},appDatabaseFactory:db.appFactory});
 assertSafeReceipt(f.root,output,receipt);return {db,api,output,receipt,connections};
}

test('full rehearsal restores every original table byte, authenticates restricted read-only services, and deletes only its child',async t=>{
 const f=await snapshotFixture(t),result=await rehearse(t,f),{receipt,db,api}=result;
 assert.equal(receipt.status,'verified',JSON.stringify(receipt));assert.equal(receipt.cleanup_status,'deleted');assert.equal(receipt.source_backup_preserved,true);assert.equal(receipt.raw_snapshot_verified,true);assert.equal(receipt.runtime_read_only_checks,true);
 assert.deepEqual(receipt.restore.collections,f.snapshot.proofs);assert.deepEqual(receipt.readback.collections,f.snapshot.proofs);assert.deepEqual(receipt.runtime.all_fourteen_counts,f.snapshot.manifest.snapshot_marker.counts);assert.equal(receipt.runtime.maps.length,4);assert.ok(db.appReads>0);
 const raw=(await db.engine.query("SELECT value,metadata FROM atlas_attribute_records WHERE id='original'")).rows[0];assert.deepEqual(raw,{value:' \n 42 \t',metadata:'{ "original" : "retained", "duplicate":1,"duplicate":2 }'});
 assert.equal((await db.engine.query("SELECT count(*)::int count FROM atlas_sources WHERE id LIKE 'pg-verification:%'")).rows[0].count,0);
 assert.equal((await db.engine.query('SELECT max(rowid)::int revision FROM atlas_ingestions')).rows[0].revision,99);assert.deepEqual((await db.engine.query('SELECT last_value,is_called FROM atlas_ingestions_rowid_seq')).rows[0],{last_value:100,is_called:false});
 assert.equal(fs.existsSync(path.join(f.root,result.output,'credential-envelope.json')),false);
 assert.deepEqual(api.calls.filter(call=>call.method==='DELETE').map(call=>call.path.split('/').at(-1)),[childId]);
 assert.equal(hash(fs.readFileSync(path.join(f.source,'index.json'))),f.operation.source_manifest_sha256);
});

test('production requires authenticated successful rehearsal artifact, restores once, and delivers only encrypted app credential',async t=>{
 const f=await snapshotFixture(t),rehearsal=await rehearse(t,f);assert.equal(rehearsal.receipt.status,'verified');
 const raw=fs.readFileSync(path.join(f.root,rehearsal.output,'receipt.json')),archive=receiptZIP(raw),proof={run_id:baseEnv.GITHUB_RUN_ID,run_attempt:baseEnv.GITHUB_RUN_ATTEMPT,head_sha:baseEnv.GITHUB_SHA,run_url:`https://github.com/${migrationRepository}/actions/runs/${baseEnv.GITHUB_RUN_ID}`,artifact_id:'333000',artifact_sha256:hash(archive),receipt_sha256:hash(raw)};
 const operation={...f.operation,production:{acknowledgement:'install-reviewed-snapshot-into-empty-production',rehearsal:proof,recipient_public_key_file:'data/storage-migration/recipient-public.pem',recipient_sha256:credentialRecipientFingerprint(publicKey)}};
 const operationFile='.github/operations/neon-production-install.json';fs.writeFileSync(path.join(f.root,operationFile),JSON.stringify(operation));
 const db=await databaseFixture(t),api=managementFixture({database:db,proof,archive}),env={...baseEnv,GITHUB_RUN_ID:'222000',GITHUB_SHA:'b'.repeat(40)},output='data/validation/production';let appURI;
 const receipt=await runNeonStorageMigration({mode:'production',operationFile,root:f.root,env,output,fetchImpl:api.fetchImpl,ownerDriverFactory:async uri=>{assert.equal(new URL(uri).hostname,productionHost);return db.owner;},appDatabaseFactory:async uri=>{appURI=uri;return db.appFactory(uri);}});
 assertSafeReceipt(f.root,output,receipt);assert.equal(receipt.status,'verified',JSON.stringify(receipt));assert.equal(receipt.authenticated_rehearsal.status,'authenticated-success');assert.equal(api.calls.some(call=>call.method==='DELETE'||call.method==='POST'),false);
 const envelopeBytes=fs.readFileSync(path.join(f.root,output,'credential-envelope.json'));assert.equal(hash(envelopeBytes),receipt.encrypted_handoff.envelope_sha256);assert.equal(envelopeBytes.includes(Buffer.from(appURI)),false);
 const logPayload=encryptedCredentialLogPayload(receipt,envelopeBytes),stdoutLine=JSON.stringify(logPayload);
 assert.deepEqual(Buffer.from(logPayload.envelope_bytes_base64,'base64'),envelopeBytes);assert.equal(logPayload.filename,'credential-envelope.json');
 for(const secret of [appURI,new URL(appURI).password,ownerPassword,neonSecret,githubSecret])assert.equal(stdoutLine.includes(secret),false);
 assert.throws(()=>encryptedCredentialLogPayload({...receipt,status:'failed'},envelopeBytes));assert.throws(()=>encryptedCredentialLogPayload(receipt,Buffer.concat([envelopeBytes,Buffer.from(' ')])));
 const clear=decryptCredentialEnvelope({envelope:envelopeBytes,privateKey,expectedContext:receipt.encrypted_handoff.context});try{assert.equal(clear.toString('utf8'),appURI);}finally{clear.fill(0);}
 const beforeWrites=db.ownerWrites,retry=await runNeonStorageMigration({mode:'production',operationFile,root:f.root,env,output:'data/validation/retry',fetchImpl:api.fetchImpl,ownerDriverFactory:async()=>db.owner,appDatabaseFactory:db.appFactory});
 assert.equal(retry.status,'failed');assert.equal(retry.error_code,'target-not-empty-use-explicit-verify-only');assert.equal(db.ownerWrites,beforeWrites);
 const verify=await runNeonStorageMigration({mode:'verify-only',operationFile,root:f.root,env,output:'data/validation/verify-only',fetchImpl:api.fetchImpl,ownerDriverFactory:async()=>db.owner,appDatabaseFactory:()=>assert.fail('Explicit read-only verification must not rotate/apply credentials')});
 assert.equal(verify.status,'verified',JSON.stringify(verify));assert.equal(verify.read_only,true);assert.equal(db.ownerWrites,beforeWrites);assert.deepEqual(verify.restore.collections,f.snapshot.proofs);
 const forged=managementFixture({database:db,proof,archive,forgedRun:true});let ownerCalls=0;
 const rejected=await runNeonStorageMigration({mode:'production',operationFile,root:f.root,env,output:'data/validation/forged',fetchImpl:forged.fetchImpl,ownerDriverFactory:async()=>{ownerCalls++;return db.owner;}});
 assert.equal(rejected.status,'failed');assert.equal(rejected.error_code,'successful-authorized-rehearsal-run-required');assert.equal(ownerCalls,0);assert.equal(forged.calls.some(call=>call.host==='console.neon.tech'),false);
});

test('missing or tampered reviewed checkpoints and missing production acknowledgement cause zero network/DB calls',async t=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-missing-migration-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));let requests=0,connections=0;
 const empty=await runNeonStorageMigration({root,env:baseEnv,fetchImpl:async()=>{requests++;},ownerDriverFactory:async()=>{connections++;}});assert.equal(empty.status,'skipped');assert.equal(requests,0);
 const f=await snapshotFixture(t),operation={...f.operation,checkpoint_sha256:'d'.repeat(64)};fs.writeFileSync(path.join(f.root,'.github/operations/neon-storage-rehearsal.json'),JSON.stringify(operation));
 const tampered=await runNeonStorageMigration({root:f.root,env:baseEnv,fetchImpl:async()=>{requests++;},ownerDriverFactory:async()=>{connections++;}});assert.equal(tampered.status,'failed');assert.equal(tampered.error_code,'reviewed-checkpoint-hash-mismatch');
 assert.throws(()=>validateMigrationOperation(f.operation,{mode:'production',root:f.root}),error=>error.code==='production-rehearsal-approval-required');assert.equal(requests,0);assert.equal(connections,0);
});

test('production branch IDs and mismatched endpoint hosts are refused before connection or production deletion',async t=>{
 const f=await snapshotFixture(t);
 for(const options of [{productionResponse:true},{wrongHost:true}]){
  const result=await rehearse(t,f,options);assert.equal(result.receipt.status,'failed');assert.equal(result.connections,0);
  assert.equal(result.api.calls.some(call=>call.method==='DELETE'&&call.path.endsWith(productionBranchId)),false);
  if(options.productionResponse)assert.equal(result.api.calls.some(call=>call.method==='DELETE'),false);
 }
});

test('rehearsal failed cleanup preserves the exact child ID without claiming validated production handoff',async t=>{
 const f=await snapshotFixture(t),result=await rehearse(t,f,{cleanupFailure:true});
 assert.equal(result.receipt.status,'failed');assert.equal(result.receipt.cleanup_status,'failed');assert.equal(result.receipt.retained_validation_branch_id,childId);assert.equal(result.receipt.raw_snapshot_verified,true);
 assert.equal(fs.existsSync(path.join(f.root,result.output,'credential-envelope.json')),false);
});

test('artifact reader accepts one bounded receipt without extracting paths and rejects malformed archive bytes',()=>{
 const raw=Buffer.from('{"status":"fixture"}'),archive=receiptZIP(raw);assert.deepEqual(rehearsalReceiptFromZIP(archive),raw);
 for(const invalid of [Buffer.alloc(0),archive.subarray(0,-1),Buffer.concat([archive,Buffer.from('extra')]),Buffer.alloc(2*1024*1024+1)])assert.throws(()=>rehearsalReceiptFromZIP(invalid));
 const traversal=Buffer.from(archive);const original=Buffer.from('receipt.json');for(let at=0;(at=traversal.indexOf(original,at))>=0;at+=original.length)traversal.write('../evil.json',at,'utf8');assert.throws(()=>rehearsalReceiptFromZIP(traversal));
});

// Explicit user authorization may skip a disposable rehearsal. It cannot skip
// the empty production guard, original-byte proof or restricted runtime checks.
test('authorized direct production preserves exhaustive verification and refuses a second installation',async t=>{
 const f=await snapshotFixture(t),db=await databaseFixture(t),api=managementFixture({database:db});
 const operation={...f.operation,production:{acknowledgement:'install-reviewed-snapshot-into-empty-production',execution_policy:'direct-production-with-source-readback',authorization:'User explicitly requested proceeding with production without waiting for the disposable rehearsal.',recipient_public_key_file:'data/storage-migration/recipient-public.pem',recipient_sha256:credentialRecipientFingerprint(publicKey)}};
 const operationFile='.github/operations/neon-production-install.json';fs.writeFileSync(path.join(f.root,operationFile),JSON.stringify(operation));
 const options={mode:'production',operationFile,root:f.root,env:baseEnv,fetchImpl:api.fetchImpl,ownerDriverFactory:async()=>db.owner,appDatabaseFactory:db.appFactory};
 const receipt=await runNeonStorageMigration({...options,output:'data/validation/direct'});
 assert.equal(receipt.status,'verified',JSON.stringify(receipt));assert.equal(receipt.raw_snapshot_verified,true);assert.equal(receipt.runtime_read_only_checks,true);assert.equal(receipt.execution_policy.rehearsal_required,false);assert.equal(receipt.target_branch_id,productionBranchId);
 assert.equal(api.calls.some(call=>call.host==='api.github.com'||call.method==='POST'||call.method==='DELETE'),false);assert.deepEqual(receipt.restore.collections,f.snapshot.proofs);
 const before=db.ownerWrites,retry=await runNeonStorageMigration({...options,output:'data/validation/direct-retry'});assert.equal(retry.error_code,'target-not-empty-use-explicit-verify-only');assert.equal(db.ownerWrites,before);
 const invalid={...operation,production:{...operation.production,authorization:'assumed'}};assert.throws(()=>validateMigrationOperation(invalid,{mode:'production',root:f.root}));
});
