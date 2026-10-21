import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {deflateRawSync} from 'node:zlib';
import {rehearsalReceiptFromZIP} from '../scripts/neon-storage-migration.mjs';
import {spawnSync} from 'node:child_process';
import {createLocalPostgres} from '../scripts/verify-postgres-schema.mjs';
import {PGlite} from '@electric-sql/pglite';
import {importTypedBatch,typedSourcePins} from '../hosted/typed-observations.js';
import {observationContract} from '../src/observation-modules.js';
import {createPostgresDatabase} from '../hosted/postgres-adapter.js';
import {rehearseCompactMembershipStorage} from '../scripts/compact-membership-storage.mjs';
import {exportStorageMarkerV4} from '../hosted/storage-export-v4.js';
import {readRecoveryInventory,assertCurrentInventory,assertRestoredInventory} from '../scripts/current-postgres-recovery.mjs';
import {compactRecoveryProfile,compactRecoveryProfileV3} from '../scripts/compact-recovery-profile.mjs';
import {stageGeographicRelease,finalizeGeographicRelease,geographicMembershipHash,geographicLocationIdsHash,geographicChangesHash} from '../hosted/geographic-releases.js';
import {importBatch} from '../hosted/records.js';
import {exportStorageMarker,exportStoragePage,storageExportCollections,storageExportColumns} from '../hosted/storage-export.js';
import {restorePostgresStorage} from '../scripts/restore-postgres-storage.mjs';
import {provisionPostgresRuntimeRole} from '../scripts/provision-postgres-runtime-role.mjs';
import {applyPostgresForwardMigrations,forwardMigrationDefinitions,validateForwardOperation,validateForwardMaintenance,runNeonForwardMigrations,verifyForwardRuntimeRole,readForwardCurrentSource,assertForwardCurrentPreserved} from '../scripts/neon-forward-migrations.mjs';
const root=path.resolve(new URL('..',import.meta.url).pathname),hash=value=>createHash('sha256').update(value).digest('hex');
const migration={...forwardMigrationDefinitions[0],sha256:hash(fs.readFileSync(new URL('../postgres/migrations/0001_temporal_geography.sql',import.meta.url)))};
async function fixture({currentOwner=false}={}){
 let pg;if(currentOwner){const seed=new PGlite();await seed.exec('CREATE ROLE neondb_owner SUPERUSER LOGIN');await seed.exec('CREATE DATABASE neondb OWNER neondb_owner');const loadDataDir=await seed.dumpDataDir();await seed.close();const engine=new PGlite({loadDataDir,username:'neondb_owner',database:'neondb'});await engine.exec(fs.readFileSync(path.join(root,'postgres/schema.sql'),'utf8'));const driver={async query(sql,args=[]){const r=await engine.query(sql,args);return {...r,rowCount:r.affectedRows??r.rows.length};},async transaction(statements){return engine.transaction(async tx=>{const results=[];for(const statement of statements){const r=await tx.query(statement.query,statement.params??[]);results.push({...r,rowCount:r.affectedRows??r.rows.length});}return results;});}};pg={engine,db:createPostgresDatabase(driver),close:()=>engine.close()};}else pg=await createLocalPostgres();
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-forward-test-')),owner={query:(query,params=[])=>pg.engine.query(query,params),runTransaction:callback=>pg.engine.transaction(tx=>callback({query:(query,params=[])=>tx.query(query,params)}))};try{
 await importBatch(pg.db,{sources:[{id:'retained-source',name:'Isolated forward fixture',url:'https://example.org/forward-test',license:'CC0',vintage:'2026',supported_from:-3000,supported_to:2027,status:'historical',metadata:{only:'synthetic testing'}}]});await provisionPostgresRuntimeRole({driver:owner,password:'isolated-fixture-password-for-test-only'});
 const marker={...await exportStorageMarker(pg.db),read_only:true},collections={};for(const collection of storageExportCollections){fs.mkdirSync(path.join(directory,collection));const page=await exportStoragePage(pg.db,collection),bytes=Buffer.from(JSON.stringify(page,null,2)+'\n'),file=`${collection}/part-000001.json`;fs.writeFileSync(path.join(directory,file),bytes);collections[collection]={count:page.records.length,columns:storageExportColumns[collection],parts:[{path:file,sha256:hash(bytes),bytes:bytes.length,rows:page.records.length,start_cursor:'',end_cursor:null}]};}
 fs.writeFileSync(path.join(directory,'index.json'),JSON.stringify({version:1,status:'complete',read_only:true,snapshot_consistent:true,source_backend:'postgres',snapshot_marker:marker,format:{json_text_preserved:true,ingestion_rowid_preserved:true,includes_archived_examples_withdrawals:true},collections}));
 const revision=marker.revision;await owner.runTransaction(tx=>tx.query(`ALTER SEQUENCE atlas_ingestions_rowid_seq RESTART WITH ${revision+1}`));const baseline=await restorePostgresStorage({directory,driver:owner,verifyOnly:true,receiptFile:null});return {pg,directory,owner,baseline,close:async()=>{await pg.close();fs.rmSync(directory,{recursive:true,force:true});}};
 }catch(error){await pg.close();fs.rmSync(directory,{recursive:true,force:true});throw error;}}

test('actual PostgreSQL forward DDL preserves every baseline byte and sequence, grants minimum runtime access, and retries idempotently',async()=>{const f=await fixture();try{const options={driver:f.owner,sourceDirectory:f.directory,migrations:[migration,{...forwardMigrationDefinitions[1],sha256:hash(fs.readFileSync(new URL('../postgres/migrations/0002_footprint_versions.sql',import.meta.url)))}],baselineTriggerHash:f.baseline.trigger_inventory_sha256,root},first=await applyPostgresForwardMigrations(options);assert.equal(first.status,'verified');assert.equal(first.atlas_fact_tables,23);assert.deepEqual(first.original_collections,f.baseline.collections);assert.equal(first.original_sequence_preserved,true);assert.equal(first.runtime.registry_access,false);const retry=await applyPostgresForwardMigrations(options);assert.equal(retry.migrations[0].status,'already-applied');const verified=await applyPostgresForwardMigrations({...options,verifyOnly:true});assert.equal(verified.read_only,true);
 await f.owner.query('SET ROLE worldatlas_app');try{await f.owner.query('SELECT * FROM atlas_temporal_geography_validations');for(const query of ['SELECT * FROM worldatlas_schema_migrations','UPDATE atlas_geographic_membership_records SET metadata=metadata','DELETE FROM atlas_geographic_existence_records','TRUNCATE atlas_temporal_geography_retirements','ALTER TABLE atlas_geographic_membership_records DISABLE TRIGGER ALL'])await assert.rejects(f.owner.query(query));}finally{await f.owner.query('RESET ROLE');}
 await assert.rejects(f.owner.query('DELETE FROM worldatlas_schema_migrations'));await assert.rejects(f.owner.query('TRUNCATE worldatlas_schema_migrations'));
 }finally{await f.close();}});

test('original collection scans occur only before and after DDL inside the advisory-locked transaction',async t=>{
 const f=await fixture(),scans=[];let locked=false,applied=false;
 const observe=(query,inTransaction)=>{
  const table=/^SELECT .* FROM (atlas_\w+) ORDER BY .* LIMIT 200$/.exec(query)?.[1];
  if(table)scans.push({table,inTransaction,locked,applied});
 };
 const driver={query:async(query,params)=>{observe(query,false);return f.owner.query(query,params);},
  runTransaction:callback=>f.owner.runTransaction(tx=>callback({query:async(query,params)=>{
   observe(query,true);const result=await tx.query(query,params);
   if(query==='SELECT pg_advisory_xact_lock(807245315,1)')locked=true;
   if(query.startsWith('INSERT INTO worldatlas_schema_migrations'))applied=true;
   return result;
  }}))};
 try{
  const result=await applyPostgresForwardMigrations({driver,sourceDirectory:f.directory,migrations:[migration],baselineTriggerHash:f.baseline.trigger_inventory_sha256,root});
  assert.deepEqual(result.original_collections,f.baseline.collections);assert.equal(result.original_sequence_preserved,true);
  t.diagnostic(JSON.stringify({collection_queries:scans.length,unlocked:scans.filter(row=>!row.inTransaction||!row.locked).length,
   locked_before:scans.filter(row=>row.inTransaction&&row.locked&&!row.applied).length,locked_after:scans.filter(row=>row.inTransaction&&row.locked&&row.applied).length}));
  assert.equal(scans.length,storageExportCollections.length*2);
  assert(scans.every(row=>row.inTransaction&&row.locked));
  const before=scans.filter(row=>!row.applied).map(row=>row.table).sort(),after=scans.filter(row=>row.applied).map(row=>row.table).sort();
  assert.equal(new Set(before).size,storageExportCollections.length);assert.deepEqual(after,before);
 }finally{await f.close();}
});

for(const phase of ['before DDL','after DDL'])for(const changed of ['original row','sequence'])
 test('locked '+phase+' verification refuses changed '+changed+' and rolls back migration',async()=>{
  const f=await fixture();let injected=false,locked=false;
  const mutate=async tx=>{
   if(changed==='sequence')await tx.query(`ALTER SEQUENCE atlas_ingestions_rowid_seq RESTART WITH ${f.baseline.sequence.next_rowid+1}`);
   else{
    await tx.query('ALTER TABLE atlas_sources DISABLE TRIGGER USER');
    await tx.query("UPDATE atlas_sources SET name='changed isolated original' WHERE id='retained-source'");
    await tx.query('ALTER TABLE atlas_sources ENABLE TRIGGER USER');
   }
   injected=true;
  };
  const driver={...f.owner,runTransaction:callback=>f.owner.runTransaction(tx=>callback({query:async(query,params)=>{
   const result=await tx.query(query,params);
   if(query==='SELECT pg_advisory_xact_lock(807245315,1)')locked=true;
   if(!injected&&(phase==='before DDL'&&query==='SELECT pg_advisory_xact_lock(807245315,1)'||
      phase==='after DDL'&&query.startsWith('INSERT INTO worldatlas_schema_migrations'))){assert(locked);await mutate(tx);}
   return result;
  }}))};
  try{
   await assert.rejects(applyPostgresForwardMigrations({driver,sourceDirectory:f.directory,migrations:[migration],baselineTriggerHash:f.baseline.trigger_inventory_sha256,root}),
    error=>error.code==='forward-transaction-failed'&&error.commit_status==='rolled-back-or-not-started');
   assert(injected&&locked,'The actual locked boundary must observe the changed original state');
   assert.equal((await f.owner.query("SELECT to_regclass('public.worldatlas_schema_migrations') IS NULL absent")).rows[0].absent,true);
   assert.equal((await f.owner.query("SELECT to_regclass('public.atlas_geographic_existence_records') IS NULL absent")).rows[0].absent,true);
   const restored=await restorePostgresStorage({directory:f.directory,driver:f.owner,verifyOnly:true,receiptFile:null});
   assert.deepEqual(restored.collections,f.baseline.collections);assert.deepEqual(restored.sequence,f.baseline.sequence);
  }finally{await f.close();}
 });

test('forward failure rolls back DDL, registry and grants without changing original bytes',async()=>{const f=await fixture();try{const driver={...f.owner,runTransaction:callback=>f.owner.runTransaction(tx=>callback({query:async(query,params)=>{if(query.startsWith('GRANT SELECT,INSERT ON TABLE public.atlas_geographic_existence_records'))throw Object.assign(Error('Synthetic private driver detail must not escape'),{code:'40001'});return tx.query(query,params);}}))};await assert.rejects(applyPostgresForwardMigrations({driver,sourceDirectory:f.directory,migrations:[migration],baselineTriggerHash:f.baseline.trigger_inventory_sha256,root}),error=>error.code==='forward-transaction-failed'&&error.sqlstate==='40001'&&!error.message.includes('private driver detail'));assert.equal((await f.owner.query("SELECT to_regclass('public.worldatlas_schema_migrations') IS NULL absent")).rows[0].absent,true);assert.equal((await f.owner.query("SELECT to_regclass('public.atlas_geographic_existence_records') IS NULL absent")).rows[0].absent,true);const after=await restorePostgresStorage({directory:f.directory,driver:f.owner,verifyOnly:true,receiptFile:null});assert.deepEqual(after.collections,f.baseline.collections);
 }finally{await f.close();}});

test('registered catalog tampering and unreviewed hashes reject instead of silently repairing a database',async()=>{const f=await fixture();try{const options={driver:f.owner,sourceDirectory:f.directory,migrations:[migration],baselineTriggerHash:f.baseline.trigger_inventory_sha256,root};await assert.rejects(applyPostgresForwardMigrations({...options,migrations:[{...migration,sha256:'f'.repeat(64)}]}),/hash/);await applyPostgresForwardMigrations(options);await f.owner.query('ALTER TABLE atlas_geographic_membership_records DISABLE TRIGGER atlas_10_temporal_contract');await assert.rejects(applyPostgresForwardMigrations(options),/guard-disabled/);await f.owner.query('ALTER TABLE atlas_geographic_membership_records ENABLE TRIGGER atlas_10_temporal_contract');await f.owner.query('GRANT SELECT ON worldatlas_schema_migrations TO worldatlas_app');await assert.rejects(verifyForwardRuntimeRole(f.owner,[forwardMigrationDefinitions[0]]),/unrelated/);
 }finally{await f.close();}});

test('missing reviewed rehearsal operation performs no management requests or database mutation',async()=>{const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-forward-skip-'));try{let requested=false;const receipt=await runNeonForwardMigrations({root:directory,fetchImpl:async()=>{requested=true;throw Error('must not call');}});assert.equal(receipt.status,'skipped');assert.equal(requested,false);assert.equal(receipt.credentials_logged,false);}finally{fs.rmSync(directory,{recursive:true,force:true});}});

test('reviewed forward operation requires an actual production baseline and exact ordered files',()=>{const operation={version:1};assert.throws(()=>validateForwardOperation(operation,{root,mode:'production'}),/reviewed-forward/);const workflow=fs.readFileSync(new URL('../.github/workflows/neon-forward-migrations.yml',import.meta.url),'utf8');assert.ok(!workflow.includes('| rg'));assert.ok(workflow.includes('[ \"$EVENT_NAME\" = workflow_dispatch ] || exit 1'));assert.ok(!/^  push:/m.test(workflow));assert.ok(workflow.includes('cancel-in-progress: false'));});

test('fresh hash-pinned private Site maintenance attestation rejects stale, writable and mismatched context',()=>{const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-maintenance-test-')),now=Date.now(),operation={site_origin:'https://example.org',site_backend:'d1',source_revision:1321,source_snapshot_fingerprint:'a'.repeat(64)};try{const receipt={version:1,verification_method:'root-private-site-authenticated-read',site_origin:operation.site_origin,backend:'d1',source_revision:1321,source_snapshot_fingerprint:operation.source_snapshot_fingerprint,read_only:true,verified_at_utc:new Date(now).toISOString(),deployment_id:'isolated-test-deployment',environment_revision:1},write=value=>{const bytes=Buffer.from(JSON.stringify(value));fs.writeFileSync(path.join(directory,'maintenance.json'),bytes);operation.maintenance={receipt_file:'maintenance.json',receipt_sha256:hash(bytes)};};write(receipt);assert.equal(validateForwardMaintenance(operation,{root:directory,now}).runner_observed_site,false);for(const change of [{read_only:false},{backend:'postgres'},{source_revision:1322},{verified_at_utc:new Date(now-3600001).toISOString()},{verified_at_utc:new Date(now+30001).toISOString()}]){write({...receipt,...change});assert.throws(()=>validateForwardMaintenance(operation,{root:directory,now}),/maintenance/);}write(receipt);fs.appendFileSync(path.join(directory,'maintenance.json'),' ');assert.throws(()=>validateForwardMaintenance(operation,{root:directory,now}),/bytes/);}finally{fs.rmSync(directory,{recursive:true,force:true});}});

test('forward management workflow requires explicit manual dispatch and rejects push selection',()=>{
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-manual-selector-'));
 try{
  const workflow=fs.readFileSync(new URL('../.github/workflows/neon-forward-migrations.yml',import.meta.url),'utf8'),body=workflow.match(/run: \|\n([\s\S]*?)\n      - name: Set up Node/)[1].split('\n').map(line=>line.replace(/^          /,'')).join('\n');
  assert.ok(!/^  push:/m.test(workflow));
  for(const [event,mode] of [['workflow_dispatch','production'],['workflow_dispatch','rehearsal'],['workflow_dispatch','verify-only'],['push','production'],['workflow_dispatch','invalid']]){
   const output=path.join(directory,'output');fs.writeFileSync(output,'');const result=spawnSync('bash',['-c',body],{env:{PATH:'/usr/bin:/bin',GITHUB_OUTPUT:output,EVENT_NAME:event,REQUESTED_MODE:mode},encoding:'utf8'});
   if(event==='push'||mode==='invalid'){assert.notEqual(result.status,0);assert.equal(fs.readFileSync(output,'utf8'),'');}
   else{assert.equal(result.status,0,result.stderr);assert.ok(fs.readFileSync(output,'utf8').includes('mode='+mode+'\n'));}
  }
 }finally{fs.rmSync(directory,{recursive:true,force:true});}
});


test('third reviewed forward migration installs typed runtime privileges without changing retained core contracts or replay identity',async()=>{
 const f=await fixture();
 try{
  const options={driver:f.owner,sourceDirectory:f.directory,migrations:forwardMigrationDefinitions.map(definition=>({...definition,sha256:hash(fs.readFileSync(path.join(root,definition.file)))})),baselineTriggerHash:f.baseline.trigger_inventory_sha256,root};
  const first=await applyPostgresForwardMigrations(options);assert.equal(first.atlas_fact_tables,26);assert.equal(first.storage_export_version,3);assert.equal(first.runtime.tables,26);assert.deepEqual(first.original_collections,f.baseline.collections);
  assert.equal(Number((await f.owner.query("SELECT count(*) n FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname LIKE 'atlas_typed_%' AND has_function_privilege('worldatlas_app',p.oid,'EXECUTE')")).rows[0].n),0);
  const retry=await applyPostgresForwardMigrations(options);assert.deepEqual(retry.migrations.map(row=>row.status),['already-applied','already-applied','already-applied']);assert.equal((await applyPostgresForwardMigrations({...options,verifyOnly:true})).read_only,true);
  await f.owner.query('SET ROLE worldatlas_app');
  try{
   for(const table of forwardMigrationDefinitions[2].tables){await f.owner.query('SELECT * FROM '+table);for(const query of ['UPDATE '+table+' SET metadata=metadata','DELETE FROM '+table,'TRUNCATE '+table,'ALTER TABLE '+table+' DISABLE TRIGGER ALL'])await assert.rejects(f.owner.query(query));}
   await assert.rejects(f.owner.query('SELECT * FROM worldatlas_schema_migrations'));await assert.rejects(f.owner.query('SELECT atlas_typed_observations_guard()'));
  }finally{await f.owner.query('RESET ROLE');}
  for(const grantee of ['worldatlas_app','PUBLIC']){
   await f.owner.query('GRANT EXECUTE ON FUNCTION atlas_typed_observations_guard() TO '+grantee);
   await assert.rejects(applyPostgresForwardMigrations({...options,verifyOnly:true}),/unexpected-typed-function-privileges/);
   await f.owner.query('REVOKE EXECUTE ON FUNCTION atlas_typed_observations_guard() FROM '+grantee);
   assert.equal((await applyPostgresForwardMigrations({...options,verifyOnly:true})).status,'verified');
  }
  await f.owner.query('ALTER TABLE atlas_typed_retirements DISABLE TRIGGER atlas_typed_retirements_immutable');
  await assert.rejects(applyPostgresForwardMigrations(options),/registered-forward-contract|guard-disabled/);
 }finally{await f.close();}
});

function receiptZIP(raw){
 const name=Buffer.from('receipt.json'),compressed=deflateRawSync(raw),local=Buffer.alloc(30),central=Buffer.alloc(46),end=Buffer.alloc(22);
 local.writeUInt32LE(0x04034b50);local.writeUInt16LE(20,4);local.writeUInt16LE(8,8);local.writeUInt32LE(compressed.length,18);local.writeUInt32LE(raw.length,22);local.writeUInt16LE(name.length,26);
 central.writeUInt32LE(0x02014b50);central.writeUInt16LE(20,4);central.writeUInt16LE(20,6);central.writeUInt16LE(8,10);central.writeUInt32LE(compressed.length,20);central.writeUInt32LE(raw.length,24);central.writeUInt16LE(name.length,28);
 end.writeUInt32LE(0x06054b50);end.writeUInt16LE(1,8);end.writeUInt16LE(1,10);end.writeUInt32LE(central.length+name.length,12);end.writeUInt32LE(local.length+name.length+compressed.length,16);
 return Buffer.concat([local,name,compressed,central,name,end]);
}

test('artifact reader accepts one bounded receipt without extracting paths and rejects malformed archive bytes',()=>{
 const raw=Buffer.from('{"status":"fixture"}'),archive=receiptZIP(raw);assert.deepEqual(rehearsalReceiptFromZIP(archive),raw);
 for(const invalid of [Buffer.alloc(0),archive.subarray(0,-1),Buffer.concat([archive,Buffer.from('extra')]),Buffer.alloc(2*1024*1024+1)])assert.throws(()=>rehearsalReceiptFromZIP(invalid));
 const traversal=Buffer.from(archive);const original=Buffer.from('receipt.json');for(let at=0;(at=traversal.indexOf(original,at))>=0;at+=original.length)traversal.write('../evil.json',at,'utf8');assert.throws(()=>rehearsalReceiptFromZIP(traversal));
});

async function grownCompactFixture(){
 const f=await fixture({currentOwner:true});
 try{
  const migrations=forwardMigrationDefinitions.map(definition=>({...definition,sha256:hash(fs.readFileSync(path.join(root,definition.file)))}));
  const options={driver:f.owner,sourceDirectory:f.directory,migrations,root,baselineTriggerHash:f.baseline.trigger_inventory_sha256};
  await applyPostgresForwardMigrations({...options,migrations:migrations.slice(0,2)});
  await importBatch(f.pg.db,JSON.parse(fs.readFileSync(path.join(root,'data/hosted-type-catalog.json'))));
  const tiers=['continent','subcontinent','region','area','province','location'];
  await importBatch(f.pg.db,{sources:[{id:'grown-source',name:'Current source is not original baseline',url:'https://example.org/current-only',license:'CC0',vintage:'undated',status:'reference',supported_from:2026,supported_to:2027,metadata:{raw:'retain me',nested:[1,null,'é']}}],entities:Array.from({length:6},(_,c)=>tiers.map((kind,i)=>({id:`grown:${c}:${kind}`,kind,name:kind,parent_id:i?`grown:${c}:${tiers[i-1]}`:null}))).flat()});
  const members=Array.from({length:6},(_,c)=>tiers.map((kind,i)=>({entity_id:`grown:${c}:${kind}`,kind,parent_id:i?`grown:${c}:${tiers[i-1]}`:null,active:1,source_id:'grown-source',evidence:{raw:'preserve exact compact bytes'}}))).flat();
  const release={id:'grown-release',version:1,source_id:'grown-source',reference_date:'2026-10-21',hierarchy_sha256:'a'.repeat(64),footprints_sha256:'b'.repeat(64),membership_sha256:await geographicMembershipHash(members),location_ids_sha256:await geographicLocationIdsHash(members),changes_sha256:await geographicChangesHash([]),expected_counts:Object.fromEntries(tiers.map(kind=>[kind,6]))};
  await stageGeographicRelease(f.pg.db,{release,memberships:members});await finalizeGeographicRelease(f.pg.db,release.id);
  await rehearseCompactMembershipStorage(f.pg.engine);await f.pg.engine.exec('DROP TABLE worldatlas_memberships_original_v1');
  const query=async sql=>(await f.owner.query(sql)).rows;
  const inventory=await readRecoveryInventory(query,{profile:compactRecoveryProfile}),marker={...await exportStorageMarkerV4(f.pg.db),read_only:true};
  assertCurrentInventory(inventory,marker);assert(marker.revision>f.baseline.source_revision);assert.equal(inventory.compact_storage.physical.worldatlas_membership_rows.count,36);
  return {...f,query,options,currentSource:{inventory,marker,profile:compactRecoveryProfile,baseline_fingerprint:f.baseline.source_snapshot_fingerprint,inventory_sha256:hash(JSON.stringify(inventory)),receipt_sha256:'a'.repeat(64)}};
 }catch(error){await f.close();throw error;}
}

test('actual PostgreSQL grown compact base2 advances only empty V3, preserving all old rows, keys, sequences, registry and access on replay',async t=>{
 const f=await grownCompactFixture();try{
  // Mock only the prior native-capture receipt envelope; all inventory and
  // forward SQL below executes against the real isolated PostgreSQL engine.
  const before=f.currentSource.inventory,raw=Buffer.from(JSON.stringify(before)),receipt={version:1,status:'verified',source_read_only:true,production_writes:0,source_marker:f.currentSource.marker,project:{branch:{id:'br-summer-butterfly-ar8qikk5'},project:{configured_postgres_major:18}},owner_registry_private:true,owner_registry_sha256:before.owner_registry_sha256,catalog_sha256:before.catalog_sha256,collections:before.collections,compact_storage:{physical:before.compact_storage.physical,sequences:before.compact_storage.sequences},dump:{sha256:'d'.repeat(64),local_readback_verified:true},encrypted_backup:{in_memory_aead_roundtrip_verified:true,ciphertext_disk_readback_verified:true,ciphertext_sha256:'e'.repeat(64)},isolated_target_cleanup:'removed-and-absence-confirmed',source_lock_cleanup:'database-lock-absence-and-reader-removal-confirmed'};
  const receiptRaw=Buffer.from(JSON.stringify(receipt));fs.writeFileSync(path.join(f.directory,'current.json'),raw);fs.writeFileSync(path.join(f.directory,'recovery.json'),receiptRaw);
  const operation={source_snapshot_fingerprint:f.baseline.source_snapshot_fingerprint,current_source:{inventory_file:'current.json',inventory_sha256:hash(raw),receipt_file:'recovery.json',receipt_sha256:hash(receiptRaw)}};
  const currentSource=readForwardCurrentSource(operation,{root:f.directory});assert.deepEqual(currentSource.inventory,before);
  assert.throws(()=>readForwardCurrentSource({...operation,current_source:{...operation.current_source,inventory_sha256:'f'.repeat(64)}},{root:f.directory}),/bytes-mismatch/);
  for(const mutate of [r=>r.fixture_only=true,r=>r.production_writes=1,r=>r.status='failed',r=>r.dump.local_readback_verified=false,r=>r.encrypted_backup.ciphertext_disk_readback_verified=false,r=>r.source_lock_cleanup='unconfirmed',r=>r.owner_registry_sha256='f'.repeat(64)]){
   const changed=structuredClone(receipt);mutate(changed);const bytes=Buffer.from(JSON.stringify(changed));fs.writeFileSync(path.join(f.directory,'recovery.json'),bytes);assert.throws(()=>readForwardCurrentSource({...operation,current_source:{...operation.current_source,receipt_sha256:hash(bytes)}},{root:f.directory}),/verified-current-native-recovery/);
  }
  fs.writeFileSync(path.join(f.directory,'recovery.json'),receiptRaw);
  const site={version:1,verification_method:'root-private-site-authenticated-read',site_origin:'https://example.org',backend:'postgres',source_revision:currentSource.marker.revision,source_snapshot_fingerprint:currentSource.marker.fingerprint,read_only:true,verified_at_utc:new Date().toISOString(),deployment_id:'isolated',environment_revision:1};
  const siteBytes=Buffer.from(JSON.stringify(site));fs.writeFileSync(path.join(f.directory,'site.json'),siteBytes);const maintained={...operation,source_revision:f.baseline.source_revision,site_origin:site.site_origin,site_backend:site.backend,maintenance:{receipt_file:'site.json',receipt_sha256:hash(siteBytes)}};
  assert.equal(validateForwardMaintenance(maintained,{root:f.directory}).source_revision,currentSource.marker.revision);
  const stale=Buffer.from(JSON.stringify({...site,source_revision:f.baseline.source_revision,source_snapshot_fingerprint:f.baseline.source_snapshot_fingerprint}));fs.writeFileSync(path.join(f.directory,'site.json'),stale);assert.throws(()=>validateForwardMaintenance({...maintained,maintenance:{...maintained.maintenance,receipt_sha256:hash(stale)}},{root:f.directory}),/fresh-pinned/);
  const result=await applyPostgresForwardMigrations({...f.options,sourceDirectory:path.join(f.directory,'missing-original-snapshot'),currentSource});
  assert.equal(result.current_source_preserved,true);assert.equal(result.migrations[2].status,'applied');assert.equal(result.source_revision,f.currentSource.marker.revision);
  const after=await readRecoveryInventory(f.query,{profile:compactRecoveryProfileV3});assertForwardCurrentPreserved(before,after);
  assert.deepEqual(after.owner_registry.slice(0,2),before.owner_registry);assert.deepEqual(after.compact_storage.physical,before.compact_storage.physical);assert.deepEqual(after.compact_storage.sequences,before.compact_storage.sequences);
  for(const name of Object.keys(before.collections))assert.deepEqual(after.collections[name],before.collections[name],name);
  assert.equal(after.owner_registry[2].source_snapshot_fingerprint,f.currentSource.marker.fingerprint);
  const retry=await applyPostgresForwardMigrations({...f.options,currentSource:f.currentSource});assert(retry.migrations.every(row=>row.status==='already-applied'));assert.deepEqual(await readRecoveryInventory(f.query,{profile:compactRecoveryProfileV3}),after);
  const marker={...await exportStorageMarkerV4(f.pg.db),read_only:true};assertCurrentInventory(after,marker);assertRestoredInventory(after,structuredClone(after),after);
  const currentBase3Source={...f.currentSource,profile:compactRecoveryProfileV3,marker,inventory:after};
  assert.equal((await applyPostgresForwardMigrations({...f.options,currentSource:currentBase3Source,verifyOnly:true})).read_only,true);
  await f.owner.query('SET ROLE worldatlas_app');try{await f.owner.query('SELECT * FROM atlas_typed_observations');for(const sql of ['SELECT * FROM worldatlas_schema_migrations','SELECT * FROM worldatlas_membership_rows','UPDATE atlas_typed_observations SET value=value','DELETE FROM atlas_typed_observations','TRUNCATE atlas_typed_feature_links'])await assert.rejects(f.owner.query(sql));}finally{await f.owner.query('SET ROLE neondb_owner');}
  // Base3 recovery also preserves populated raw typed rows and withdrawals,
  // not merely the three empty tables created by the DDL operation.
  await importBatch(f.pg.db,{sources:[{id:'isolated:estimate',name:'Synthetic estimate',license:'CC0',vintage:'1950',status:'estimate',supported_from:1950,supported_to:1951,metadata:{original_text:'test-only',sha256:'a'.repeat(64)}}],entities:[{id:'isolated:settlement',kind:'settlement',name:'Synthetic settlement'}]});
  const contract=await observationContract(),sourcePins=await typedSourcePins((await f.pg.db.prepare("SELECT * FROM atlas_sources WHERE id='isolated:estimate'").all()).results);
  const claim={id:'isolated:population',subject_id:'isolated:settlement',subject_kind:'settlement',field_id:'settlement.population',value:42,valid_from:1950,valid_to:1951,method:'estimate',status:'estimate',source_id:'isolated:estimate',metadata:{measurement:{unit:'persons',definition:'Synthetic settlement count',period:{from:1950,to:1951}}},original_json:{value:'42.00',metadata:JSON.stringify({measurement:{unit:'persons',definition:'Synthetic settlement count',period:{from:1950,to:1951}}},null,2)}};
  await importTypedBatch(f.pg.db,{version:1,registry_sha256:contract.registry_sha256,source_pins:sourcePins,observations:[claim]});
  await importTypedBatch(f.pg.db,{version:1,registry_sha256:contract.registry_sha256,source_pins:sourcePins,retirements:[{id:'isolated:withdrawal',collection:'observations',target_id:claim.id,source_id:claim.source_id,reason:'Test-only withdrawal'}]});
  const grown=await readRecoveryInventory(f.query,{profile:compactRecoveryProfileV3}),grownMarker={...await exportStorageMarkerV4(f.pg.db),read_only:true};assert.equal(grown.collections.typed_observations.count,1);assert.equal(grown.collections.typed_retirements.count,1);assertCurrentInventory(grown,grownMarker);
  await applyPostgresForwardMigrations({...f.options,currentSource:{...currentBase3Source,inventory:grown,marker:grownMarker,inventory_sha256:hash(JSON.stringify(grown))},verifyOnly:true});assert.deepEqual(await readRecoveryInventory(f.query,{profile:compactRecoveryProfileV3}),grown);
  assert.equal((await f.pg.db.prepare('SELECT value FROM atlas_typed_observations WHERE id=?').bind(claim.id).first()).value,'42.00');
  t.diagnostic(JSON.stringify({engine:(await f.owner.query('SELECT version() version')).rows[0].version,original_revision:f.baseline.source_revision,current_revision:marker.revision,logical_collections:Object.keys(after.collections).length,private_tables:Object.keys(after.compact_storage.physical).length,unchanged_registry_rows:2,new_empty_typed_tables:3}));
 }finally{await f.close();}
});

for(const phase of ['before DDL','after DDL'])test('grown compact '+phase+' current-state drift rolls back without resetting any source or old registry row',async()=>{
 const f=await grownCompactFixture();try{
  let mutated=false;const driver={...f.owner,runTransaction:fn=>f.owner.runTransaction(tx=>fn({query:async(sql,args)=>{const result=await tx.query(sql,args);if(!mutated&&(phase==='before DDL'&&sql==='SELECT pg_advisory_xact_lock(807245315,1)'||phase==='after DDL'&&sql.startsWith('INSERT INTO worldatlas_schema_migrations'))){mutated=true;await tx.query('ALTER TABLE atlas_sources DISABLE TRIGGER USER');await tx.query("UPDATE atlas_sources SET name='wrong current bytes' WHERE id='grown-source'");await tx.query('ALTER TABLE atlas_sources ENABLE TRIGGER USER');}return result;}}))};
  await assert.rejects(applyPostgresForwardMigrations({...f.options,driver,currentSource:f.currentSource}),e=>e.commit_status==='rolled-back-or-not-started');assert(mutated);
  assert.equal((await f.owner.query("SELECT to_regclass('public.atlas_typed_observations') IS NULL absent")).rows[0].absent,true);assert.deepEqual(await readRecoveryInventory(f.query,{profile:compactRecoveryProfile}),f.currentSource.inventory);
 }finally{await f.close();}
});

test('grown compact rejects changed fingerprint, private ACL, raw physical evidence, sequence and immutable registry pins',async()=>{
 const f=await grownCompactFixture();try{
  const bad=structuredClone(f.currentSource);bad.marker.fingerprint='f'.repeat(64);await assert.rejects(applyPostgresForwardMigrations({...f.options,currentSource:bad}));
  for(const mutation of ["GRANT SELECT ON worldatlas_membership_evidence TO worldatlas_app","ALTER SEQUENCE worldatlas_membership_evidence_key_seq RESTART WITH 100","ALTER TABLE worldatlas_membership_evidence DISABLE TRIGGER USER; UPDATE worldatlas_membership_evidence SET raw='{}'; ALTER TABLE worldatlas_membership_evidence ENABLE TRIGGER USER","ALTER TABLE worldatlas_schema_migrations DISABLE TRIGGER USER; UPDATE worldatlas_schema_migrations SET applied_at=applied_at+1; ALTER TABLE worldatlas_schema_migrations ENABLE TRIGGER USER"]){
   let observed=false;const driver={...f.owner,runTransaction:fn=>f.owner.runTransaction(tx=>fn({query:async(sql,args)=>{const result=await tx.query(sql,args);if(sql==='SELECT pg_advisory_xact_lock(807245315,1)'){observed=true;for(const command of mutation.split(';').map(s=>s.trim()).filter(Boolean))await tx.query(command);}return result;}}))};
   await assert.rejects(applyPostgresForwardMigrations({...f.options,driver,currentSource:f.currentSource}),e=>e.commit_status==='rolled-back-or-not-started');assert(observed);assert.deepEqual(await readRecoveryInventory(f.query,{profile:compactRecoveryProfile}),f.currentSource.inventory);
  }
 }finally{await f.close();}
});

test('grown compact refuses post-DDL foreign table, column or function ACL additions and rolls them back',async()=>{
 const f=await grownCompactFixture();try{
  await f.owner.query('CREATE ROLE isolated_other_reader NOLOGIN');
  for(const mutation of ['GRANT SELECT ON atlas_typed_observations TO isolated_other_reader','GRANT SELECT(id) ON atlas_typed_observations TO isolated_other_reader','GRANT EXECUTE ON FUNCTION atlas_typed_ingestion_complete_guard() TO isolated_other_reader']){
   let applied=false;const driver={...f.owner,runTransaction:fn=>f.owner.runTransaction(tx=>fn({query:async(sql,args)=>{const result=await tx.query(sql,args);if(sql.startsWith('INSERT INTO worldatlas_schema_migrations')){applied=true;await tx.query(mutation);}return result;}}))};
   await assert.rejects(applyPostgresForwardMigrations({...f.options,driver,currentSource:f.currentSource}),e=>e.commit_status==='rolled-back-or-not-started');assert(applied);assert.deepEqual(await readRecoveryInventory(f.query,{profile:compactRecoveryProfile}),f.currentSource.inventory);
  }
 }finally{await f.close();}
});
