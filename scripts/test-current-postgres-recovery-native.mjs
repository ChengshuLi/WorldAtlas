// Explicit local synthetic fixture. Never connects to a provider or uses secrets.
import fs from 'node:fs';
import {execFileSync,spawn} from 'node:child_process';
import {randomUUID,randomBytes,createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {recoveryImage,readRecoveryInventory,assertRestoredInventory,isolatedRestoreSQL,isolatedOriginalChecks,isolatedRecoveryBootstrapSQL,isolatedDatabaseACLList,isolatedDatabaseACLSQL,restoreIsolatedDatabaseACL} from './current-postgres-recovery.mjs';
import {storageExportV2Contract} from '../hosted/storage-export-v2-contract.js';
import {compactRecoveryProfile,recoveryForwardContract} from './compact-recovery-profile.mjs';
import {rehearseCompactMembershipStorage} from './compact-membership-storage.mjs';
const sha=x=>createHash('sha256').update(x).digest('hex');
const native=(args,input)=>execFileSync('docker',args,{input,timeout:180000,maxBuffer:64*1024*1024,stdio:['pipe','pipe','pipe']});
let name;const receipt={version:1,fixture_only:true,production_access:false,image:recoveryImage,status:'failed'};
const cleanup=()=>{if(name){native(['rm','-fv',name]);assert.equal(native(['ps','-a','--filter','name=^/'+name+'$','--format','{{.ID}}']).toString().trim(),'');name=null;}};
async function start(){name='atlas-sql-fixture-'+randomUUID();native(['run','-d','--name',name,'--network','none','--read-only','--tmpfs','/var/lib/postgresql:rw,size=256m','--tmpfs','/var/run/postgresql:rw,size=16m','--memory','1g','-e','POSTGRES_HOST_AUTH_METHOD=trust',recoveryImage]);for(let i=0;i<30;i++){try{native(['exec',name,'pg_isready','-h','127.0.0.1','-U','postgres']);return;}catch{await new Promise(r=>setTimeout(r,1000));}}throw Error('fixture not ready');}
const command=(args,input)=>native(['exec','-i',name,...args],input);
const sql=value=>command(['psql','-X','-Atq','-U','postgres','-d','neondb','-v','ON_ERROR_STOP=1'],value);
const query=async value=>JSON.parse(sql('SET ROLE neondb_owner; SELECT coalesce(json_agg(row_to_json(q)),\'[]\'::json) FROM ('+value+') q;').toString());
// One real native session owns the rehearsal transaction and advisory lock.
// Independent CLI round trips would not preserve that transaction.
async function compactFixture(){
 const child=spawn('docker',['exec','-i',name,'psql','-X','-Atq','-U','postgres','-d','neondb','-v','ON_ERROR_STOP=1'],{stdio:['pipe','pipe','pipe']});
 child.stdin.on('error',()=>{});let sessionError='';child.stderr.on('data',chunk=>{sessionError=(sessionError+chunk).slice(-4096);});
 let pending,buffer='';
 const rejectPending=()=>{if(pending){clearTimeout(pending.timer);pending.reject(Error('fixture native session failed: '+sessionError));pending=null;}};
 child.on('error',rejectPending);child.on('close',rejectPending);
 child.stdout.on('data',chunk=>{buffer+=chunk;const at=pending?buffer.indexOf(pending.marker+'\n'):-1;if(at>=0){const value=buffer.slice(0,at).trim(),row=pending;buffer=buffer.slice(at+row.marker.length+1);pending=null;clearTimeout(row.timer);row.resolve(value);}});
 const exec=value=>new Promise((resolve,reject)=>{assert.ok(!pending);const marker='end_'+randomUUID().replaceAll('-','');pending={marker,resolve,reject,timer:setTimeout(()=>{child.kill();rejectPending();},180000)};child.stdin.write(value+';\n\\echo '+marker+'\n');});
 const tx={exec,query:async(value,params=[])=>{assert.deepEqual(params,[]);if(!/^\s*(SELECT|WITH)\b/i.test(value)){await exec(value);return {rows:[]};}return {rows:JSON.parse(await exec("SELECT coalesce(json_agg(row_to_json(q)),'[]'::json) FROM ("+value+') q'))};}};
 try{await exec('SET ROLE neondb_owner');await rehearseCompactMembershipStorage({transaction:async callback=>{await exec('BEGIN');try{const result=await callback(tx);await exec('COMMIT');return result;}catch(error){await exec('ROLLBACK');throw error;}}},{copyOnServer:true});}
 finally{child.stdin.end('\\q\n');await new Promise(resolve=>{if(child.exitCode!==null)resolve();else child.once('close',resolve);});}
}
try{
 await start();command(['psql','-X','-U','postgres','-d','postgres','-v','ON_ERROR_STOP=1'],isolatedRecoveryBootstrapSQL);
 sql('GRANT ALL ON DATABASE neondb TO neon_superuser; ALTER DEFAULT PRIVILEGES FOR ROLE cloud_admin IN SCHEMA public GRANT ALL ON TABLES TO neon_superuser WITH GRANT OPTION; ALTER DEFAULT PRIVILEGES FOR ROLE cloud_admin IN SCHEMA public GRANT ALL ON SEQUENCES TO neon_superuser WITH GRANT OPTION;');
 for(const file of ['postgres/schema.sql','postgres/migrations/0001_temporal_geography.sql','postgres/migrations/0002_footprint_versions.sql'])sql('SET ROLE neondb_owner; '+fs.readFileSync(file,'utf8'));
 const registryModule=fs.readFileSync('scripts/neon-forward-migrations.mjs','utf8'),registry=registryModule.match(/const registrySQL=`([\s\S]*?)`;/)[1];sql('SET ROLE neondb_owner; '+registry);
 sql(`SET ROLE neondb_owner; INSERT INTO worldatlas_schema_migrations VALUES('synthetic-fixture',repeat('a',64),repeat('b',64),repeat('c',64),repeat('d',64),repeat('e',64),123456789);
 INSERT INTO atlas_ingestions(id,fingerprint,counts,created_at) VALUES('synthetic-fixture',repeat('f',64),'{ "original" : 1 }',987654321);
 GRANT USAGE ON SCHEMA public TO worldatlas_app; GRANT SELECT ON atlas_ingestions TO worldatlas_app;`);

 sql(`SET ROLE neondb_owner; INSERT INTO atlas_sources(id,name,license,vintage,supported_from,supported_to,status,metadata) VALUES('fixture-source','Synthetic fixture only','test-only','synthetic',1,20,'example','{ "original" : "source" }');`);
 const tiers=['continent','subcontinent','region','area','province','location'];for(let i=0;i<tiers.length;i++)sql(`SET ROLE neondb_owner; INSERT INTO atlas_entity_types(id,name,geographic_level) VALUES('${tiers[i]}','Synthetic ${tiers[i]}',${5-i}); INSERT INTO atlas_entities(id,kind,name,parent_id,valid_from,valid_to,source_id,is_example,metadata) VALUES('fixture-${tiers[i]}','${tiers[i]}','Synthetic ${tiers[i]}',${i?"'fixture-"+tiers[i-1]+"'":'NULL'},1,10,'fixture-source',1,'{ "original" : "identity" }');`);
 sql(`SET ROLE neondb_owner; INSERT INTO atlas_attribute_records(id,location_id,attribute,value,valid_from,valid_to,method,status,source_id,is_example,metadata) VALUES('fixture-record','fixture-location','population','10',1,10,'estimate','example','fixture-source',1,'{ "original" : "claim" }'); INSERT INTO atlas_names(id,entity_id,name,valid_from,valid_to,source_id,is_example,metadata) VALUES('fixture-name','fixture-location','Synthetic original name',1,10,'fixture-source',1,'{ "original" : "name" }');`);
 // Match the actual archive size with incompressible synthetic source metadata.
 // Never include real data or credentials; COPY consumes the complete stdin.
 const noise=Array.from({length:5200},(_,i)=>['transport-fixture:'+String(i).padStart(5,'0'),'Synthetic transport source','test-only','synthetic',1,20,'example',JSON.stringify({test_only:true,noise:randomBytes(4500).toString('base64')})].join('\t')).join('\n');
 sql('SET ROLE neondb_owner; COPY atlas_sources(id,name,license,vintage,supported_from,supported_to,status,metadata) FROM STDIN;\n'+noise+'\n\\.\n');
 // Demonstrate real session-lock loss and database-level release detection.
 const locker=spawn('docker',['exec','-i',name,'psql','-X','-Atq','-U','postgres','-d','neondb','-v','ON_ERROR_STOP=1'],{stdio:['pipe','pipe','pipe']});
 locker.stdin.on('error',()=>{});locker.stderr.on('data',()=>{});
 const locked=await new Promise((resolve,reject)=>{let text='';const timer=setTimeout(()=>reject(Error('fixture lock timeout')),10000);locker.once('error',reject);locker.stdout.on('data',chunk=>{text+=chunk;if(text.includes('\n')){clearTimeout(timer);try{resolve(JSON.parse(text.trim()));}catch(error){reject(error);}}});locker.stdin.write("SELECT json_build_object('locked',pg_try_advisory_lock(807245315,1),'pid',pg_backend_pid());\n");});
 assert.equal(locked.locked,true);assert.equal((await query(`SELECT exists(SELECT 1 FROM pg_locks WHERE pid=${locked.pid} AND locktype='advisory' AND classid=807245315 AND objid=1 AND granted) held`))[0].held,true);
 sql(`SELECT pg_terminate_backend(${locked.pid});`);locker.stdin.destroy();assert.equal((await query(`SELECT exists(SELECT 1 FROM pg_locks WHERE pid=${locked.pid} AND locktype='advisory' AND classid=807245315 AND objid=1 AND granted) held`))[0].held,false);receipt.session_lock_loss_and_release_detected=true;
 const before=await readRecoveryInventory(query);assert.equal(before.catalog_sha256,storageExportV2Contract.postgres_catalog_sha256);
 const dump=command(['pg_dump','-U','postgres','-d','neondb','--format=custom','--schema=public']);assert.equal(dump.subarray(0,5).toString(),'PGDMP');assert.ok(dump.length>=22*1024**2);receipt.production_sized_archive_transport=true;
 try{command(['pg_restore','--create','--list'],dump);receipt.large_toc_stdin_probe={status:'completed'};}catch(error){receipt.large_toc_stdin_probe={status:'failed',code:['EPIPE','ENOBUFS'].includes(error.code)?error.code:'native-command-failed',exit_status:Number.isInteger(error.status)?error.status:null};}
 const acl=()=>sql("SELECT datacl::text FROM pg_database WHERE datname='neondb'; SELECT defaclrole::regrole::text,defaclobjtype,defaclacl::text FROM pg_default_acl ORDER BY 1,2;").toString();const originalACL=acl();
 command(['sh','-c','cat > /var/lib/postgresql/fixture-original.dump'],dump);
 assert.throws(()=>isolatedDatabaseACLList(command(['pg_restore','--list','/var/lib/postgresql/fixture-original.dump']).toString()),/unexpected-native-database-acl-toc/);
 const databaseACLList=isolatedDatabaseACLList(command(['pg_restore','--create','--list','/var/lib/postgresql/fixture-original.dump']).toString());
 receipt.database_acl_requires_create_listing=true;
 const after=await readRecoveryInventory(query);
 // A killed native CLI is not evidence that its named container was removed.
 const slow='atlas-sql-timeout-fixture-'+randomUUID();try{cleanup();native(['create','--name',slow,'--network','none','--read-only',recoveryImage,'sleep','30']);assert.throws(()=>execFileSync('docker',['start','-ai',slow],{timeout:250,stdio:'pipe'}));}finally{try{native(['rm','-fv',slow]);}catch{}assert.equal(native(['ps','-a','--filter','name=^/'+slow+'$','--format','{{.ID}}']).toString().trim(),'');}receipt.timed_out_named_client_absence_confirmed=true;
cleanup();await start();command(['psql','-X','-U','postgres','-d','postgres','-v','ON_ERROR_STOP=1'],isolatedRecoveryBootstrapSQL);sql('DROP SCHEMA public;');
 const restoreSQL=isolatedRestoreSQL(command(['pg_restore','--file=-'],dump));command(['psql','-X','-U','postgres','-d','neondb','--single-transaction','-v','ON_ERROR_STOP=1'],restoreSQL);
 const aclDirectory=fs.mkdtempSync('/tmp/atlas-acl-fixture-');try{receipt.database_acl_recovery=restoreIsolatedDatabaseACL(name,dump,aclDirectory);assert.equal(receipt.database_acl_recovery.archive_sha256,sha(dump));}finally{fs.rmSync(aclDirectory,{recursive:true});}
 sql(isolatedOriginalChecks(fs.readFileSync('postgres/schema.sql')));const restored=await readRecoveryInventory(query);assertRestoredInventory(before,restored,after);assert.equal(acl(),originalACL);receipt.database_and_provider_default_acls_preserved=true;
 assert.equal((await query('SELECT metadata FROM atlas_attribute_records'))[0].metadata,'{ "original" : "claim" }');assert.equal((await query('SELECT metadata FROM atlas_names'))[0].metadata,'{ "original" : "name" }');assert.equal((await query('SELECT counts FROM atlas_ingestions'))[0].counts,'{ "original" : 1 }');
 // Current compact profile: synthetic rows only, not a geographic certificate.
 // Disable only isolated fixture USER guards while installing raw test data;
 // constraints/FKs remain active, and all guards are re-enabled before capture.
 sql(`SET ROLE neondb_owner;
 ALTER TABLE atlas_entities DISABLE TRIGGER USER; ALTER TABLE atlas_geographic_releases DISABLE TRIGGER USER; ALTER TABLE atlas_geographic_memberships DISABLE TRIGGER USER;
 INSERT INTO atlas_entities(id,kind,name,source_id,is_example) VALUES('fixture-root','continent','Fixture root','fixture-source',1),('fixture-leaf','location','Fixture leaf','fixture-source',1);
 INSERT INTO atlas_geographic_releases(id,source_id,version,reference_date,hierarchy_sha256,footprints_sha256,membership_sha256,location_ids_sha256,changes_sha256,expected_counts) VALUES('fixture-release','fixture-source',1,'synthetic',repeat('a',64),repeat('b',64),repeat('c',64),repeat('d',64),repeat('e',64),'{}');
 INSERT INTO atlas_geographic_memberships(release_id,entity_id,parent_id,reference_name,active,source_id,evidence) VALUES('fixture-release','fixture-root',NULL,'Root',1,'fixture-source','{ "raw" : 1 }'),('fixture-release','fixture-leaf','fixture-root',NULL,0,'fixture-source','{"raw":1}');
 ALTER TABLE atlas_entities ENABLE TRIGGER USER; ALTER TABLE atlas_geographic_releases ENABLE TRIGGER USER; ALTER TABLE atlas_geographic_memberships ENABLE TRIGGER USER;
 ALTER TABLE worldatlas_schema_migrations DISABLE TRIGGER USER; TRUNCATE worldatlas_schema_migrations; ALTER TABLE worldatlas_schema_migrations ENABLE TRIGGER USER;`);
 for(const pin of storageExportV2Contract.postgres_migrations.slice(1)){
  const id=pin.path.split('/').at(-1).replace('.sql',''),contract=await recoveryForwardContract(query,id);
  sql(`SET ROLE neondb_owner; INSERT INTO worldatlas_schema_migrations VALUES('${id}','${pin.sha256}','${storageExportV2Contract.postgres_migrations[0].sha256}',repeat('c',64),repeat('d',64),'${contract}',123456789);`);
 }
 await compactFixture();
 await assert.rejects(()=>readRecoveryInventory(query,{profile:compactRecoveryProfile}),/incomplete-owner-and-factual-inventory/);
 sql('SET ROLE neondb_owner; DROP TABLE worldatlas_memberships_original_v1;');
 const compactBefore=await readRecoveryInventory(query,{profile:compactRecoveryProfile});
 assert.equal(compactBefore.collections.geographic_memberships.count,2);
 assert.equal(compactBefore.compact_storage.physical.worldatlas_membership_evidence.count,2);
 const compactDump=command(['pg_dump','-U','postgres','-d','neondb','--format=custom','--schema=public']);
 const compactAfter=await readRecoveryInventory(query,{profile:compactRecoveryProfile});
 cleanup();await start();command(['psql','-X','-U','postgres','-d','postgres','-v','ON_ERROR_STOP=1'],isolatedRecoveryBootstrapSQL);sql('DROP SCHEMA public;');
 command(['psql','-X','-U','postgres','-d','neondb','--single-transaction','-v','ON_ERROR_STOP=1'],isolatedRestoreSQL(command(['pg_restore','--file=-'],compactDump)));
 const compactACLDirectory=fs.mkdtempSync('/tmp/atlas-compact-acl-fixture-');try{restoreIsolatedDatabaseACL(name,compactDump,compactACLDirectory);}finally{fs.rmSync(compactACLDirectory,{recursive:true});}
 sql(isolatedOriginalChecks(fs.readFileSync('postgres/schema.sql')));
 const compactRestored=await readRecoveryInventory(query,{profile:compactRecoveryProfile});
 // Bounded fixture-only diagnostics contain hashes/state, never real source data.
 for(const key of Object.keys(compactBefore))if(key!=='identity'&&JSON.stringify(compactBefore[key])!==JSON.stringify(compactRestored[key])){
  const summarize=value=>key==='compact_storage'?{catalog_sha256:sha(JSON.stringify(value.catalog)),physical:value.physical,sequences:value.sequences}:value;
  console.log('compact fixture parity difference '+key+' '+JSON.stringify({before:summarize(compactBefore[key]),restored:summarize(compactRestored[key])}).slice(0,12000));
 }
 assertRestoredInventory(compactBefore,compactRestored,compactAfter);
 assert.deepEqual((await query('SELECT evidence FROM atlas_geographic_memberships ORDER BY entity_id')).map(row=>row.evidence),['{"raw":1}','{ "raw" : 1 }']);
 const badSequence=structuredClone(compactRestored);badSequence.compact_storage.sequences.worldatlas_membership_evidence_key_seq.last_value++;
 assert.throws(()=>assertRestoredInventory(compactBefore,badSequence,compactAfter));
 sql('SET ROLE neondb_owner; GRANT SELECT ON worldatlas_membership_evidence TO worldatlas_app;');
 await assert.rejects(()=>readRecoveryInventory(query,{profile:compactRecoveryProfile}),/Compact private storage privileges are exposed/);
 sql('SET ROLE neondb_owner; REVOKE SELECT ON worldatlas_membership_evidence FROM worldatlas_app;');
 receipt.compact={status:'passed',profile:compactRecoveryProfile,dump:{bytes:compactDump.length,sha256:sha(compactDump)},catalog_sha256:compactBefore.catalog_sha256,logical_memberships:compactBefore.collections.geographic_memberships,physical:compactBefore.compact_storage.physical,sequences:compactBefore.compact_storage.sequences,raw_spelling_preserved:true,retained_original_rejected:true,private_acl_corruption_rejected:true,sequence_corruption_rejected:true};
 sql('SET ROLE neondb_owner; REVOKE SELECT ON atlas_ingestions FROM worldatlas_app;');const corrupted=await readRecoveryInventory(query,{profile:compactRecoveryProfile});assert.throws(()=>assertRestoredInventory(compactBefore,corrupted,compactAfter));
 // A fresh target must reject a truncated native archive, not certify a partial restore.
 cleanup();await start();command(['psql','-X','-U','postgres','-d','postgres','-v','ON_ERROR_STOP=1'],isolatedRecoveryBootstrapSQL);sql('DROP SCHEMA public;');assert.throws(()=>command(['pg_restore','-U','postgres','-d','neondb','--single-transaction','--exit-on-error'],dump.subarray(0,Math.floor(dump.length/2))));
 Object.assign(receipt,{status:'passed',catalog_sha256:before.catalog_sha256,dump:{bytes:dump.length,sha256:sha(dump)},collections:before.collections,owner_registry_sha256:before.owner_registry_sha256,raw_text_preserved:true,table_acl_corruption_rejected:true,truncated_archive_rejected:true});
}finally{cleanup();receipt.isolated_targets_removed=true;console.log(JSON.stringify(receipt,null,2));}
