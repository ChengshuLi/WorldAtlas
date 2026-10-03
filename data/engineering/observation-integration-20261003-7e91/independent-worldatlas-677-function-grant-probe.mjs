import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {createLocalPostgres} from '/workspace/worldatlas-observation-integration-20261003-7e91/scripts/verify-postgres-schema.mjs';
import {importBatch} from '/workspace/worldatlas-observation-integration-20261003-7e91/hosted/records.js';
import {exportStorageMarker,exportStoragePage,storageExportCollections,storageExportColumns} from '/workspace/worldatlas-observation-integration-20261003-7e91/hosted/storage-export.js';
import {restorePostgresStorage} from '/workspace/worldatlas-observation-integration-20261003-7e91/scripts/restore-postgres-storage.mjs';
import {provisionPostgresRuntimeRole} from '/workspace/worldatlas-observation-integration-20261003-7e91/scripts/provision-postgres-runtime-role.mjs';
import {applyPostgresForwardMigrations,forwardMigrationDefinitions,validateForwardOperation,validateForwardMaintenance,runNeonForwardMigrations,verifyForwardRuntimeRole} from '/workspace/worldatlas-observation-integration-20261003-7e91/scripts/neon-forward-migrations.mjs';
const root='/workspace/worldatlas-observation-integration-20261003-7e91',hash=value=>createHash('sha256').update(value).digest('hex');
const migration={...forwardMigrationDefinitions[0],sha256:hash(fs.readFileSync(new URL('/workspace/worldatlas-observation-integration-20261003-7e91/postgres/migrations/0001_temporal_geography.sql',import.meta.url)))};
async function fixture(){const pg=await createLocalPostgres(),directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-forward-test-')),owner={query:(query,params=[])=>pg.engine.query(query,params),runTransaction:callback=>pg.engine.transaction(tx=>callback({query:(query,params=[])=>tx.query(query,params)}))};try{
 await importBatch(pg.db,{sources:[{id:'retained-source',name:'Isolated forward fixture',url:'https://example.org/forward-test',license:'CC0',vintage:'2026',supported_from:-3000,supported_to:2027,status:'historical',metadata:{only:'synthetic testing'}}]});await provisionPostgresRuntimeRole({driver:owner,password:'isolated-fixture-password-for-test-only'});
 const marker={...await exportStorageMarker(pg.db),read_only:true},collections={};for(const collection of storageExportCollections){fs.mkdirSync(path.join(directory,collection));const page=await exportStoragePage(pg.db,collection),bytes=Buffer.from(JSON.stringify(page,null,2)+'\n'),file=`${collection}/part-000001.json`;fs.writeFileSync(path.join(directory,file),bytes);collections[collection]={count:page.records.length,columns:storageExportColumns[collection],parts:[{path:file,sha256:hash(bytes),bytes:bytes.length,rows:page.records.length,start_cursor:'',end_cursor:null}]};}
 fs.writeFileSync(path.join(directory,'index.json'),JSON.stringify({version:1,status:'complete',read_only:true,snapshot_consistent:true,source_backend:'postgres',snapshot_marker:marker,format:{json_text_preserved:true,ingestion_rowid_preserved:true,includes_archived_examples_withdrawals:true},collections}));
 const revision=marker.revision;await owner.runTransaction(tx=>tx.query(`ALTER SEQUENCE atlas_ingestions_rowid_seq RESTART WITH ${revision+1}`));const baseline=await restorePostgresStorage({directory,driver:owner,verifyOnly:true,receiptFile:null});return {pg,directory,owner,baseline,close:async()=>{await pg.close();fs.rmSync(directory,{recursive:true,force:true});}};
 }catch(error){await pg.close();fs.rmSync(directory,{recursive:true,force:true});throw error;}}


const f=await fixture();try{
 const options={driver:f.owner,sourceDirectory:f.directory,migrations:forwardMigrationDefinitions.map(d=>({...d,sha256:hash(fs.readFileSync(path.join(root,d.file)))})),baselineTriggerHash:f.baseline.trigger_inventory_sha256,root};
 await applyPostgresForwardMigrations(options);
 await f.owner.query('GRANT EXECUTE ON FUNCTION atlas_typed_observations_guard() TO worldatlas_app');
 let result;try{result={accepted:true,receipt:await applyPostgresForwardMigrations({...options,verifyOnly:true})};}catch(e){result={accepted:false,error:e.message};}
 const allowed=(await f.owner.query("SELECT has_function_privilege('worldatlas_app','atlas_typed_observations_guard()','EXECUTE') allowed")).rows[0].allowed;
 console.log(JSON.stringify({probe:'verify-only after excessive new typed trigger-function EXECUTE grant',scope:'isolated PGlite owner fixture, no provider',allowed,result},null,2));
}finally{await f.close();}
