// Explicit local synthetic fixture. Never connects to a provider or uses secrets.
import fs from 'node:fs';
import {execFileSync,spawn} from 'node:child_process';
import {randomUUID,createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {recoveryImage,readRecoveryInventory,assertRestoredInventory,isolatedRestoreSQL,isolatedOriginalChecks,isolatedRecoveryBootstrapSQL,isolatedDatabaseACLList,isolatedDatabaseACLSQL} from './current-postgres-recovery.mjs';
import {storageExportV2Contract} from '../hosted/storage-export-v2-contract.js';
const sha=x=>createHash('sha256').update(x).digest('hex');
const native=(args,input)=>execFileSync('docker',args,{input,timeout:180000,maxBuffer:16*1024*1024,stdio:['pipe','pipe','pipe']});
let name;const receipt={version:1,fixture_only:true,production_access:false,image:recoveryImage,status:'failed'};
const cleanup=()=>{if(name){native(['rm','-fv',name]);assert.equal(native(['ps','-a','--filter','name=^/'+name+'$','--format','{{.ID}}']).toString().trim(),'');name=null;}};
async function start(){name='atlas-sql-fixture-'+randomUUID();native(['run','-d','--name',name,'--network','none','--read-only','--tmpfs','/var/lib/postgresql:rw,size=256m','--tmpfs','/var/run/postgresql:rw,size=16m','--memory','1g','-e','POSTGRES_HOST_AUTH_METHOD=trust',recoveryImage]);for(let i=0;i<30;i++){try{native(['exec',name,'pg_isready','-U','postgres']);return;}catch{await new Promise(r=>setTimeout(r,1000));}}throw Error('fixture not ready');}
const command=(args,input)=>native(['exec','-i',name,...args],input);
const sql=value=>command(['psql','-X','-Atq','-U','postgres','-d','neondb','-v','ON_ERROR_STOP=1'],value);
const query=async value=>JSON.parse(sql('SET ROLE neondb_owner; SELECT coalesce(json_agg(row_to_json(q)),\'[]\'::json) FROM ('+value+') q;').toString());
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
 // Demonstrate real session-lock loss and database-level release detection.
 const locker=spawn('docker',['exec','-i',name,'psql','-X','-Atq','-U','postgres','-d','neondb','-v','ON_ERROR_STOP=1'],{stdio:['pipe','pipe','pipe']});
 locker.stdin.on('error',()=>{});locker.stderr.on('data',()=>{});
 const locked=await new Promise((resolve,reject)=>{let text='';const timer=setTimeout(()=>reject(Error('fixture lock timeout')),10000);locker.once('error',reject);locker.stdout.on('data',chunk=>{text+=chunk;if(text.includes('\n')){clearTimeout(timer);try{resolve(JSON.parse(text.trim()));}catch(error){reject(error);}}});locker.stdin.write("SELECT json_build_object('locked',pg_try_advisory_lock(807245315,1),'pid',pg_backend_pid());\n");});
 assert.equal(locked.locked,true);assert.equal((await query(`SELECT exists(SELECT 1 FROM pg_locks WHERE pid=${locked.pid} AND locktype='advisory' AND classid=807245315 AND objid=1 AND granted) held`))[0].held,true);
 sql(`SELECT pg_terminate_backend(${locked.pid});`);locker.stdin.destroy();assert.equal((await query(`SELECT exists(SELECT 1 FROM pg_locks WHERE pid=${locked.pid} AND locktype='advisory' AND classid=807245315 AND objid=1 AND granted) held`))[0].held,false);receipt.session_lock_loss_and_release_detected=true;
 const before=await readRecoveryInventory(query);assert.equal(before.catalog_sha256,storageExportV2Contract.postgres_catalog_sha256);
 const dump=command(['pg_dump','-U','postgres','-d','neondb','--format=custom','--schema=public']);assert.equal(dump.subarray(0,5).toString(),'PGDMP');
 const acl=()=>sql("SELECT datacl::text FROM pg_database WHERE datname='neondb'; SELECT defaclrole::regrole::text,defaclobjtype,defaclacl::text FROM pg_default_acl ORDER BY 1,2;").toString();const originalACL=acl();
 assert.throws(()=>isolatedDatabaseACLList(command(['pg_restore','--list'],dump).toString()),/unexpected-native-database-acl-toc/);
 const databaseACLList=isolatedDatabaseACLList(command(['pg_restore','--create','--list'],dump).toString());
 receipt.database_acl_requires_create_listing=true;
 const after=await readRecoveryInventory(query);
 // A killed native CLI is not evidence that its named container was removed.
 const slow='atlas-sql-timeout-fixture-'+randomUUID();try{cleanup();native(['create','--name',slow,'--network','none','--read-only',recoveryImage,'sleep','30']);assert.throws(()=>execFileSync('docker',['start','-ai',slow],{timeout:250,stdio:'pipe'}));}finally{try{native(['rm','-fv',slow]);}catch{}assert.equal(native(['ps','-a','--filter','name=^/'+slow+'$','--format','{{.ID}}']).toString().trim(),'');}receipt.timed_out_named_client_absence_confirmed=true;
cleanup();await start();command(['psql','-X','-U','postgres','-d','postgres','-v','ON_ERROR_STOP=1'],isolatedRecoveryBootstrapSQL);sql('DROP SCHEMA public;');
 const restoreSQL=isolatedRestoreSQL(command(['pg_restore','--file=-'],dump));command(['psql','-X','-U','postgres','-d','neondb','--single-transaction','-v','ON_ERROR_STOP=1'],restoreSQL);
 command(['sh','-c','cat > /var/lib/postgresql/database-acl.list'],databaseACLList);const databaseACL=command(['pg_restore','--create','--use-list=/var/lib/postgresql/database-acl.list','--file=-'],dump);assert.match(databaseACL.toString(),/CREATE DATABASE neondb/);const aclSQL=isolatedDatabaseACLSQL(databaseACL);assert.doesNotMatch(aclSQL.toString(),/\b(?:CREATE|DROP|ALTER) DATABASE\b|\\connect/);sql(aclSQL);
 sql(isolatedOriginalChecks(fs.readFileSync('postgres/schema.sql')));const restored=await readRecoveryInventory(query);assertRestoredInventory(before,restored,after);assert.equal(acl(),originalACL);receipt.database_and_provider_default_acls_preserved=true;
 assert.equal((await query('SELECT metadata FROM atlas_attribute_records'))[0].metadata,'{ "original" : "claim" }');assert.equal((await query('SELECT metadata FROM atlas_names'))[0].metadata,'{ "original" : "name" }');assert.equal((await query('SELECT counts FROM atlas_ingestions'))[0].counts,'{ "original" : 1 }');
 sql('SET ROLE neondb_owner; REVOKE SELECT ON atlas_ingestions FROM worldatlas_app;');const corrupted=await readRecoveryInventory(query);assert.throws(()=>assertRestoredInventory(before,corrupted,after));
 // A fresh target must reject a truncated native archive, not certify a partial restore.
 cleanup();await start();command(['psql','-X','-U','postgres','-d','postgres','-v','ON_ERROR_STOP=1'],isolatedRecoveryBootstrapSQL);sql('DROP SCHEMA public;');assert.throws(()=>command(['pg_restore','-U','postgres','-d','neondb','--single-transaction','--exit-on-error'],dump.subarray(0,Math.floor(dump.length/2))));
 Object.assign(receipt,{status:'passed',catalog_sha256:before.catalog_sha256,dump:{bytes:dump.length,sha256:sha(dump)},collections:before.collections,owner_registry_sha256:before.owner_registry_sha256,raw_text_preserved:true,table_acl_corruption_rejected:true,truncated_archive_rejected:true});
}finally{cleanup();receipt.isolated_targets_removed=true;console.log(JSON.stringify(receipt,null,2));}
