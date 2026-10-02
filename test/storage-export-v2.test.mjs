import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {DatabaseSync} from 'node:sqlite';
import {importBatch,registerMedia} from '../hosted/records.js';
import {stageGeographicRelease,finalizeGeographicRelease,geographicMembershipHash,geographicLocationIdsHash,geographicChangesHash} from '../hosted/geographic-releases.js';
import {importTemporalGeography,temporalGeographySnapshot} from '../hosted/temporal-geography.js';
import {importFootprintSelections,footprintSelectionAt} from '../hosted/footprint-versions.js';
import {exportStorageMarker,exportStoragePage} from '../hosted/storage-export.js';
import {exportHostedStorage} from '../scripts/export-hosted-storage.mjs';
import {readVerifiedStorageSnapshot,restorePostgresStorage} from '../scripts/restore-postgres-storage.mjs';
import {exportStorageMarkerV2,exportStoragePageV2} from '../hosted/storage-export-v2.js';
import {storageExportV2Contract,storageExportV2Definitions,storageExportV2Collections,storageExportV2Columns,v2MarkerIdentity} from '../hosted/storage-export-v2-contract.js';
import {exportHostedStorageV2} from '../scripts/export-hosted-storage-v2.mjs';
import {readVerifiedStorageSnapshotV2,restorePostgresStorageV2,storageRowsHashV2Ordered} from '../scripts/restore-postgres-storage-v2.mjs';
import {createLocalPostgres} from '../scripts/verify-postgres-schema.mjs';
const sha=value=>createHash('sha256').update(value).digest('hex');
const url=file=>new URL('../'+file,import.meta.url);
class D1{
 constructor({forward=true}={}){this.sqlite=new DatabaseSync(':memory:');this.sqlite.exec('PRAGMA foreign_keys=ON');for(const pin of storageExportV2Contract.d1_migrations.filter(pin=>forward||/^drizzle\/000[0-7]_/.test(pin.path)))this.sqlite.exec(fs.readFileSync(url(pin.path),'utf8'));}
 prepare(sql){const sqlite=this.sqlite;let args=[];return {bind(...values){args=values;return this;},async all(){return {results:sqlite.prepare(sql).all(...args)};},async first(){return sqlite.prepare(sql).get(...args)??null;},run(){return {meta:{changes:Number(sqlite.prepare(sql).run(...args).changes)}};}};}
 async batch(statements){this.sqlite.exec('BEGIN IMMEDIATE');try{const result=statements.map(s=>s.run());this.sqlite.exec('COMMIT');return result;}catch(error){this.sqlite.exec('ROLLBACK');throw error;}}
}
const api=(db,v2=true)=>async input=>{const parsed=new URL(input),prefix=v2?'/api/storage/v2':'/api/storage',marker=v2?exportStorageMarkerV2:exportStorageMarker,page=v2?exportStoragePageV2:exportStoragePage;if(parsed.pathname===prefix+'/export-marker')return Response.json({...await marker(db),read_only:true});assert.ok(parsed.pathname.startsWith(prefix+'/export/'));return Response.json(await page(db,parsed.pathname.split('/').at(-1),{cursor:parsed.searchParams.get('cursor')??'',limit:Number(parsed.searchParams.get('limit')??200)}));};
const capture=(db,directory,v2=true,extra={})=>(v2?exportHostedStorageV2:exportHostedStorage)({origin:'https://example.org/',output:directory,token:'isolated-secret-must-not-be-logged',fetcher:api(db,v2),...extra});
const tiers=['continent','subcontinent','region','area','province','location'];
const source=(id,status)=>({id,name:'Synthetic '+id,url:'https://example.org/test-only',license:'CC0',vintage:'2026',supported_from:status==='reference'?2026:-3000,supported_to:2027,status});
async function seed(db,{forward=true,paged=false}={}){
 await importBatch(db,JSON.parse(fs.readFileSync(url('data/hosted-type-catalog.json'))));
 const entities=Array.from({length:6},(_,c)=>tiers.map((kind,i)=>({id:`${kind}-${c}`,kind,name:`Synthetic ${kind} ${c}`,parent_id:i?`${tiers[i-1]}-${c}`:null}))).flat();
 await importBatch(db,{sources:[source('history','historical'),source('reference','reference')],entities:[...entities,{id:'archived-location',kind:'location',name:'Archived',parent_id:'province-0',active:0},{id:'person',kind:'person',name:'Synthetic person'}],categories:[{id:'owner',kind:'owner',name:'Synthetic owner',source_id:'history'}],records:[{id:'old-pop',location_id:'location-0',attribute:'population',value:1,source_id:'history',valid_from:1000,valid_to:1100}],names:[{id:'name',entity_id:'location-0',name:'Recorded synthetic name',source_id:'history',valid_from:1000,valid_to:1100}],relationships:[{id:'link',source_entity_id:'person',target_entity_id:'location-0',relationship_type:'associated_with',source_id:'history',valid_from:1000,valid_to:1100}]});
 await importBatch(db,{records:[{id:'new-pop',location_id:'location-0',attribute:'population',value:2,source_id:'history',valid_from:1000,valid_to:1100}],retirements:[{id:'old-pop-retirement',collection:'records',target_id:'old-pop',replacement_id:'new-pop',source_id:'history',reason:'Isolated correction'}]});
 if(paged)for(let offset=0;offset<205;offset+=200)await importBatch(db,{entities:Array.from({length:Math.min(200,205-offset)},(_,i)=>({id:`person-${String(offset+i).padStart(4,'0')}`,kind:'person',name:'Synthetic pagination identity'}))});
 const members=entities.map(row=>({entity_id:row.id,kind:row.kind,parent_id:row.parent_id,reference_name:row.name,active:1,source_id:'reference',evidence:{test_only:true}}));
 const pins={release_id:'release-2',hierarchy_sha256:'a'.repeat(64),footprints_sha256:'b'.repeat(64)};
 for(let version=1;version<=2;version++){
  const changes=version===1?[]:[{id:'rename',old_entity_id:'location-0',new_entity_id:'location-0',change_type:'rename',source_id:'reference',evidence:{test_only:true}}];
  const membership=version===1?members:members.map(row=>row.entity_id==='location-0'?{...row,reference_name:'Reviewed synthetic label'}:row);
  await stageGeographicRelease(db,{release:{id:`release-${version}`,source_id:'reference',version,reference_date:'2026-10-02',hierarchy_sha256:pins.hierarchy_sha256,footprints_sha256:pins.footprints_sha256,membership_sha256:await geographicMembershipHash(membership),location_ids_sha256:await geographicLocationIdsHash(membership),changes_sha256:await geographicChangesHash(changes),expected_counts:Object.fromEntries(tiers.map(kind=>[kind,6]))},memberships:membership,changes});await finalizeGeographicRelease(db,`release-${version}`);
 }
 const media=[];for(let i=0;i<7;i++){const digest=String(i+1).repeat(64),row={id:`media-${i}`,object_key:`media/${digest}`,sha256:digest,bytes:42,mime:'application/octet-stream',name:'Synthetic object metadata',license:'CC0',attribution:'Isolated test',source_id:'history'};media.push(row);await registerMedia(db,row);}
 await importBatch(db,{media_links:[{id:'media-link',media_id:'media-0',entity_id:'location-0',source_id:'history',role:'image'}]});
 if(!forward)return;
 await importTemporalGeography(db,{expected_geography:pins,memberships:[{id:'parent-old',entity_id:'location-0',parent_id:'province-1',valid_from:1000,valid_to:1100,source_id:'history',metadata:' { "original": 1, "duplicate":1,"duplicate":2 } '}],existence:[{id:'existence',entity_id:'location-1',value:'unknown',valid_from:-1,valid_to:1,source_id:'history'}]});
 await importTemporalGeography(db,{expected_geography:pins,memberships:[{id:'parent-new',entity_id:'location-0',parent_id:'province-2',valid_from:1000,valid_to:1100,source_id:'history'}],retirements:[{id:'parent-retirement',collection:'memberships',target_id:'parent-old',replacement_id:'parent-new',source_id:'history',reason:'Isolated retained correction'}]});
 // This fixture proves catalog/raw restoration, not geometry preparation or
 // object storage. Maintainer-only SQL creates synthetic published metadata;
 // no media byte transfer or producer-signature verification is claimed here.
 const version={id:'footprint-version',release_id:pins.release_id,source_id:'history',supported_from:1000,supported_to:1100,manifest_media_id:'media-5',receipt_media_id:'media-6',footprints_sha256:'c'.repeat(64),location_ids_sha256:await geographicLocationIdsHash(members),dictionary_sha256:'d'.repeat(64),grid_sha256:'e'.repeat(64),footprint_hash_algorithm:'sha256-canonical-json-location-geometry-sha256-v1',grid_size:256,location_count:6,object_count:5,producer_key_id:'isolated-producer',status:'staged',verified_receipt_sha256:null,published_at:null,metadata:' { "catalog": "original source bytes" } '};
 const insert=(collection,row)=>{const d=storageExportV2Definitions[collection];db.sqlite.prepare(`INSERT INTO ${d.table} (${d.columns.map(c=>'"'+c+'"').join(',')}) VALUES(${d.columns.map(()=>'?').join(',')})`).run(...d.columns.map(c=>row[c]??null));};
 insert('footprint_versions',version);
 for(const [i,role]of ['source_archive','reconciled_geometry','coverage_mask','rows','runs'].entries())insert('footprint_version_objects',{version_id:version.id,media_id:media[i].id,role,sha256:media[i].sha256,bytes:42,...(['rows','runs'].includes(role)?{offset:0,words:1,encoding:'gzip-u32le',decoded_sha256:'f'.repeat(64),decoded_bytes:4}:{})});
 db.sqlite.prepare("UPDATE atlas_footprint_versions SET status='published',verified_receipt_sha256=?,published_at=42 WHERE id=?").run(media[6].sha256,version.id);
 await importFootprintSelections(db,{expected_geography:pins,footprints:[{id:'footprint-old',version_id:version.id,valid_from:1000,valid_to:1100,source_id:'history',metadata:' { "original" : "dated footprint" } '}]});
 await importFootprintSelections(db,{expected_geography:pins,footprints:[{id:'footprint-unknown',version_id:null,valid_from:1000,valid_to:1100,source_id:'history'}],retirements:[{id:'footprint-retirement',target_id:'footprint-old',replacement_id:'footprint-unknown',source_id:'history',reason:'Isolated explicit uncertainty'}]});
 db.sqlite.prepare("INSERT INTO atlas_ingestions(rowid,id,fingerprint,counts,created_at) VALUES(99,'preserved-journal',?,'{ \"raw\" : 1 }',123456789)").run('f'.repeat(64));
}
async function fixture({paged=false}={}){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-forward-restore-')),directory=path.join(root,'snapshot'),db=new D1();let pg;
 try{await seed(db,{paged});await capture(db,directory);pg=await createLocalPostgres();for(const pin of storageExportV2Contract.postgres_migrations.slice(1))await pg.engine.exec(fs.readFileSync(url(pin.path),'utf8'));const driver={query:(sql,params)=>pg.engine.query(sql,params),runTransaction:callback=>pg.engine.transaction(tx=>callback({query:(sql,params)=>tx.query(sql,params)}))};return {root,directory,db,pg,driver,close:async()=>{db.sqlite.close();await pg.close();fs.rmSync(root,{recursive:true,force:true});}};}catch(error){db.sqlite.close();await pg?.close();fs.rmSync(root,{recursive:true,force:true});throw error;}
}

test('v2 inventories all twenty-three tables and pins every reviewed D1/PostgreSQL migration',()=>{
 assert.equal(storageExportV2Collections.length,23);assert.equal(storageExportV2Contract.d1_migrations.length,10);assert.equal(storageExportV2Contract.postgres_migrations.length,3);
 for(const pin of [...storageExportV2Contract.d1_migrations,...storageExportV2Contract.postgres_migrations])assert.equal(sha(fs.readFileSync(url(pin.path))),pin.sha256,pin.path);
 // SQLite's implicit ingestion rowid is separately included in exported columns.
 const db=new D1();try{assert.deepEqual(db.sqlite.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name GLOB 'atlas_*' ORDER BY name").all().map(row=>row.name),storageExportV2Collections.map(key=>storageExportV2Definitions[key].table).sort());for(const key of storageExportV2Collections)assert.deepEqual(db.sqlite.prepare(`PRAGMA table_info(${storageExportV2Definitions[key].table})`).all().map(row=>row.name),key==='ingestions'?storageExportV2Columns[key].filter(column=>column!=='rowid'):storageExportV2Columns[key]);}finally{db.sqlite.close();}
});
test('empty forward migrations preserve every v1 marker/page byte and existing fourteen-table restore',async()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-v1-compat-')),db=new D1({forward:false});let pg;try{
  await seed(db,{forward:false});const before=await exportStorageMarker(db),pages=await Promise.all(Object.keys(before.counts).map(key=>exportStoragePage(db,key)));
  for(const pin of storageExportV2Contract.d1_migrations.slice(8))db.sqlite.exec(fs.readFileSync(url(pin.path),'utf8'));
  assert.equal(JSON.stringify(await exportStorageMarker(db)),JSON.stringify(before));assert.deepEqual(await Promise.all(Object.keys(before.counts).map(key=>exportStoragePage(db,key))),pages);
  const directory=path.join(root,'v1');await capture(db,directory,false);assert.equal(readVerifiedStorageSnapshot(directory).manifest.version,1);assert.throws(()=>readVerifiedStorageSnapshotV2(directory),/completed/);
  pg=await createLocalPostgres();const driver={query:(sql,params)=>pg.engine.query(sql,params),runTransaction:callback=>pg.engine.transaction(tx=>callback({query:(sql,params)=>tx.query(sql,params)}))};assert.equal((await restorePostgresStorage({directory,driver,acknowledgeOwnerRestore:true})).status,'restored');
 }finally{db.sqlite.close();await pg?.close();fs.rmSync(root,{recursive:true,force:true});}
});
test('forward owner restoration streams all twenty-three tables, original JSON bytes, deferred receipts and sequence',async()=>{
 const f=await fixture({paged:true});try{
  const snapshot=readVerifiedStorageSnapshotV2(f.directory);assert.ok(storageExportV2Collections.every(key=>snapshot.proofs[key].count>0));assert.ok(snapshot.proofs.entities.count>200);assert.equal((await restorePostgresStorageV2({directory:f.directory,dryRun:true})).network_requests,0);assert.throws(()=>readVerifiedStorageSnapshot(f.directory),/completed/);
  const receipt=await restorePostgresStorageV2({directory:f.directory,driver:f.driver,acknowledgeOwnerRestore:true});assert.equal(receipt.status,'restored');assert.equal(receipt.version,2);assert.equal(receipt.atomic,true);assert.equal(receipt.sequence.next_rowid,100);assert.deepEqual(receipt.collections,snapshot.proofs);assert.equal(receipt.media_bytes_moved,false);
  assert.equal((await restorePostgresStorageV2({directory:f.directory,driver:f.driver,verifyOnly:true})).status,'verified');
  for(const [table,id]of [['atlas_geographic_membership_records','parent-old'],['atlas_footprint_versions','footprint-version'],['atlas_geographic_footprint_records','footprint-old']])assert.deepEqual((await f.pg.engine.query(`SELECT metadata FROM ${table} WHERE id=$1`,[id])).rows[0],{...f.db.sqlite.prepare(`SELECT metadata FROM ${table} WHERE id=?`).get(id)});
  assert.equal((await temporalGeographySnapshot(f.pg.db,1000)).entities.find(row=>row.id==='location-0').parent_id,'province-2');assert.equal((await footprintSelectionAt(f.pg.db,1000)).status,'unknown');
  for(const collection of storageExportV2Collections.slice(14)){const table=storageExportV2Definitions[collection].table;await assert.rejects(f.pg.engine.query(`DELETE FROM ${table}`),/immutable|retained|append-only/i);await assert.rejects(f.pg.engine.query(`TRUNCATE ${table} CASCADE`),/immutable|retained|append-only/i);}
  const next=await importTemporalGeography(f.pg.db,{expected_geography:{release_id:'release-2',hierarchy_sha256:'a'.repeat(64),footprints_sha256:'b'.repeat(64)},existence:[{id:'after-restore',entity_id:'location-3',value:'unknown',valid_from:1000,valid_to:1100,source_id:'history'}]});assert.equal(next.revision,100);
  const exported=await exportStorageMarkerV2(f.pg.db);assert.equal(exported.backend,'postgres');assert.equal(exported.counts.geographic_membership_records,2);
  const objectRows=[];let cursor='',pages=0;do{const page=await exportStoragePageV2(f.pg.db,'footprint_version_objects',{cursor,limit:2});objectRows.push(...page.records);pages++;cursor=page.next_cursor;}while(cursor);assert.equal(pages,3);assert.equal(storageRowsHashV2Ordered('footprint_version_objects',objectRows),snapshot.proofs.footprint_version_objects.ordered_rows_sha256,'PostgreSQL composite paging and quoted offset values preserve the original object catalog');
 }finally{await f.close();}
});
test('v2 detects changing staged publication, missing source guards and unexpected factual tables',async()=>{
 const f=await fixture();try{
  const d=storageExportV2Definitions.footprint_versions;
  const selected=d.columns.map(column=>column==='id'?"'pending-version'":column==='status'?"'staged'":['verified_receipt_sha256','published_at'].includes(column)?'NULL':'"'+column+'"');
  f.db.sqlite.exec(`INSERT INTO atlas_footprint_versions(${d.columns.map(column=>'"'+column+'"').join(',')}) SELECT ${selected.join(',')} FROM atlas_footprint_versions WHERE id='footprint-version'`);
  const objects=storageExportV2Definitions.footprint_version_objects.columns;
  f.db.sqlite.exec(`INSERT INTO atlas_footprint_version_objects(${objects.map(column=>'"'+column+'"').join(',')}) SELECT ${objects.map(column=>column==='version_id'?"'pending-version'":'"'+column+'"').join(',')} FROM atlas_footprint_version_objects WHERE version_id='footprint-version'`);
  const staged=await exportStorageMarkerV2(f.db);
  f.db.sqlite.prepare("UPDATE atlas_footprint_versions SET status='published',verified_receipt_sha256=?,published_at=43 WHERE id='pending-version'").run('7'.repeat(64));
  const before=await exportStorageMarkerV2(f.db);assert.equal(before.revision,staged.revision);assert.deepEqual(before.counts,staged.counts);assert.notEqual(before.footprint_versions_sha256,staged.footprint_versions_sha256);assert.notEqual(before.fingerprint,staged.fingerprint,'Owner publication without new ingestion must still invalidate a capture marker');
  f.db.sqlite.exec('CREATE TABLE atlas_uninventoried(id TEXT)');await assert.rejects(exportStorageMarkerV2(f.db),/inventory/);f.db.sqlite.exec('DROP TABLE atlas_uninventoried');
  f.db.sqlite.exec('DROP TRIGGER atlas_footprint_retirements_no_delete');await assert.rejects(exportStorageMarkerV2(f.db),/guards|schema/);assert.equal(before.counts.footprint_versions,2);
 }finally{await f.close();}
});
test('a missing target guard or source migration/raw-row proof fails before any target writes',async()=>{
 const f=await fixture();try{
  await f.pg.engine.exec('DROP TRIGGER atlas_no_truncate ON atlas_footprint_retirements');await assert.rejects(restorePostgresStorageV2({directory:f.directory,driver:f.driver,acknowledgeOwnerRestore:true}),error=>error.phase==='target-validation');assert.equal((await f.pg.engine.query('SELECT count(*)::int n FROM atlas_sources')).rows[0].n,0);
  const manifest=JSON.parse(fs.readFileSync(path.join(f.directory,'index.json')));manifest.collections.geographic_membership_records.ordered_rows_sha256='0'.repeat(64);fs.writeFileSync(path.join(f.directory,'index.json'),JSON.stringify(manifest));assert.throws(()=>readVerifiedStorageSnapshotV2(f.directory),/raw row hash/);
  manifest.collections.geographic_membership_records.ordered_rows_sha256=storageRowsHashV2Ordered('geographic_membership_records',JSON.parse(fs.readFileSync(path.join(f.directory,manifest.collections.geographic_membership_records.parts[0].path))).records);manifest.contract.postgres_migrations[1].sha256='0'.repeat(64);fs.writeFileSync(path.join(f.directory,'index.json'),JSON.stringify(manifest));assert.throws(()=>readVerifiedStorageSnapshotV2(f.directory),/marker|migration/);
 }finally{await f.close();}
});
test('a deferred cross-table FK failure rolls back all twenty-three tables, guards and sequence',async()=>{
 const f=await fixture();try{
  let changed=false;const driver={query:f.driver.query,runTransaction:callback=>f.pg.engine.transaction(tx=>callback({async query(sql,params){if(!changed&&sql.startsWith('INSERT INTO atlas_temporal_geography_validations')){changed=true;params=[...params];params[1]='missing-ingestion';params[0]='missing-ingestion';}return tx.query(sql,params);}}))};
  await assert.rejects(restorePostgresStorageV2({directory:f.directory,driver,acknowledgeOwnerRestore:true}),error=>error.phase==='constraints'&&error.code==='23503'&&error.commit_status==='rolled-back-or-not-started');
  for(const collection of storageExportV2Collections)assert.equal((await f.pg.engine.query(`SELECT count(*)::int n FROM ${storageExportV2Definitions[collection].table}`)).rows[0].n,0);
  assert.equal((await f.pg.engine.query("SELECT count(*)::int n FROM pg_trigger WHERE NOT tgisinternal AND tgenabled!='O'")).rows[0].n,0);const seq=(await f.pg.engine.query('SELECT last_value,is_called FROM atlas_ingestions_rowid_seq')).rows[0];assert.equal(Number(seq.last_value),1);assert.equal(seq.is_called,false);
 }finally{await f.close();}
});
test('interrupted v2 capture resumes preserved pages and its v2 cursor cannot be sent to v1',async()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-v2-resume-')),directory=path.join(root,'snapshot'),db=new D1();try{
  await seed(db,{paged:true});const normal=api(db);let stopped=false;
  await assert.rejects(capture(db,directory,true,{concurrency:1,fetcher:async input=>{if(!stopped&&new URL(input).pathname.endsWith('/names')){stopped=true;return Response.json({error:'fixture interruption'},{status:409});}return normal(input);}}),/HTTP 409/);
  const ledger=JSON.parse(fs.readFileSync(path.join(directory,'resume.json'))),part=ledger.collections.entities.parts[0],bytes=fs.readFileSync(path.join(directory,part.path));assert.ok(part.end_cursor);await assert.rejects(exportStoragePage(db,'entities',{cursor:part.end_cursor}),/cursor/);
  const manifest=await capture(db,directory);assert.equal(manifest.version,2);assert.equal(manifest.status,'complete');assert.deepEqual(fs.readFileSync(path.join(directory,part.path)),bytes);assert.equal(readVerifiedStorageSnapshotV2(directory).proofs.entities.count,244);
  assert.equal(fs.readFileSync(path.join(directory,'index.json'),'utf8').includes('isolated-secret-must-not-be-logged'),false);
 }finally{db.sqlite.close();fs.rmSync(root,{recursive:true,force:true});}
});
