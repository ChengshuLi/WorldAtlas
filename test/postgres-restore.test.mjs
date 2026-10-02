import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {DatabaseSync} from 'node:sqlite';
import {createHash} from 'node:crypto';
import {createLocalPostgres} from '../scripts/verify-postgres-schema.mjs';
import {restorePostgresStorage,readVerifiedStorageSnapshot,storageRowsHash} from '../scripts/restore-postgres-storage.mjs';
import {exportHostedStorage} from '../scripts/export-hosted-storage.mjs';
import {storageExportCollections,exportStorageMarker,exportStoragePage} from '../hosted/storage-export.js';
import {importBatch,attributesAt,evidenceHistory,registerMedia} from '../hosted/records.js';
import {stageGeographicRelease,finalizeGeographicRelease,geographicMembershipHash,geographicLocationIdsHash,geographicChangesHash} from '../hosted/geographic-releases.js';

const hash=bytes=>createHash('sha256').update(bytes).digest('hex'),tiers=['continent','subcontinent','region','area','province','location'];
const source=(id,status='historical')=>({id,name:`Isolated restore test ${id}`,url:'https://example.org/test-only-restore-source',license:'CC0',vintage:'2026',supported_from:status==='reference'?2026:-3000,supported_to:2027,status});
const record=(id,attribute,value,extra={})=>({id,location_id:'location-0',attribute,value,valid_from:1000,valid_to:1100,source_id:'history',...extra});
class D1 {
 constructor(){this.sqlite=new DatabaseSync(':memory:');this.sqlite.exec('PRAGMA foreign_keys=ON');for(const file of fs.readdirSync(new URL('../drizzle/',import.meta.url)).filter(file=>file.endsWith('.sql')).sort())this.sqlite.exec(fs.readFileSync(new URL(`../drizzle/${file}`,import.meta.url),'utf8'));}
 prepare(sql){const sqlite=this.sqlite;let args=[];return {bind(...values){args=values;return this;},async all(){return {results:sqlite.prepare(sql).all(...args)};},async first(){return sqlite.prepare(sql).get(...args)??null;},run(){return {meta:{changes:Number(sqlite.prepare(sql).run(...args).changes)}};}};}
 async batch(statements){this.sqlite.exec('BEGIN IMMEDIATE');try{const result=statements.map(statement=>statement.run());this.sqlite.exec('COMMIT');return result;}catch(error){this.sqlite.exec('ROLLBACK');throw error;}}
}
async function fixture({paged=false}={}){
 const sourceDb=new D1(),root=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-pg-restore-')),directory=path.join(root,'snapshot');
 try{
  await importBatch(sourceDb,JSON.parse(fs.readFileSync(new URL('../data/hosted-type-catalog.json',import.meta.url))));
  const entities=Array.from({length:6},(_,continent)=>tiers.map((kind,index)=>({id:`${kind}-${continent}`,kind,name:`Original ${kind} ${continent}`,parent_id:index?`${tiers[index-1]}-${continent}`:null}))).flat();
  await importBatch(sourceDb,{sources:[source('history'),source('reference','reference'),source('example','example')],entities:[...entities,{id:'archived',kind:'location',name:'Original archived location',parent_id:'province-0',active:0},{id:'person',kind:'person',name:'Research test person'}],categories:[{id:'owner:a',kind:'owner',name:'Owner A',source_id:'history'}],records:[record('old-pop','population',42),record('example-owner','owner','Owner A',{category_id:'owner:a',source_id:'example',is_example:1}),record('archived-pop','population',9,{location_id:'archived'})],names:[{id:'name',entity_id:'location-0',name:'Historic label',valid_from:1000,valid_to:1100,source_id:'history'}],relationships:[{id:'association',source_entity_id:'person',target_entity_id:'location-0',relationship_type:'associated_with',valid_from:1000,valid_to:1100,source_id:'history'}]});
  await importBatch(sourceDb,{retirements:[{id:'retire-old','collection':'records',target_id:'old-pop',replacement_id:'new-pop',source_id:'history',reason:'Isolated correction'}],records:[record('new-pop','population',43)]});
  if(paged)for(let offset=0;offset<205;offset+=200)await importBatch(sourceDb,{entities:Array.from({length:Math.min(200,205-offset)},(_,index)=>({id:`paged-person-${String(offset+index).padStart(4,'0')}`,kind:'person',name:'Isolated pagination identity'}))});
  const digest='c'.repeat(64);await registerMedia(sourceDb,{id:'media',object_key:`media/${digest}`,sha256:digest,bytes:42,mime:'audio/wav',name:'Isolated audio metadata',license:'CC0',attribution:'Test-only archive',source_id:'history'});await importBatch(sourceDb,{media_links:[{id:'audio-link',media_id:'media',entity_id:'location-0',role:'audio',source_id:'history'}]});
  const memberships=entities.map(entity=>({entity_id:entity.id,kind:entity.kind,parent_id:entity.parent_id,reference_name:entity.name,active:1,source_id:'reference',evidence:{method:'pinned-test-reference'}}));
  for(let version=1;version<=2;version++){
   const changes=version===2?[{id:'rename:location',old_entity_id:'location-0',new_entity_id:'location-0',change_type:'rename',source_id:'reference',evidence:{reason:'Isolated reference label review'}}]:[];
   const members=version===2?memberships.map(row=>row.entity_id==='location-0'?{...row,reference_name:'Reviewed modern label'}:row):memberships;
   const release={id:`release-${version}`,source_id:'reference',version,reference_date:'2026-10-01',hierarchy_sha256:'a'.repeat(64),footprints_sha256:'b'.repeat(64),membership_sha256:await geographicMembershipHash(members),location_ids_sha256:await geographicLocationIdsHash(members),changes_sha256:await geographicChangesHash(changes),expected_counts:Object.fromEntries(tiers.map(kind=>[kind,6])),metadata:{test_only:true}};
   await stageGeographicRelease(sourceDb,{release,memberships:members,changes});await finalizeGeographicRelease(sourceDb,release.id);
  }
  // These local-only legacy values were permitted before forward import guards.
  // Preserve their bytes without turning maintenance restoration into new claims.
  const legacyTriggerNames=['atlas_environment_classification','atlas_attribute_unresolved_status'],definitions=legacyTriggerNames.map(name=>sourceDb.sqlite.prepare('SELECT sql FROM sqlite_master WHERE type=\'trigger\' AND name=?').get(name).sql);for(const name of legacyTriggerNames)sourceDb.sqlite.exec(`DROP TRIGGER ${name}`);
  const rawInsert=sourceDb.sqlite.prepare("INSERT INTO atlas_attribute_records(id,location_id,attribute,value,valid_from,valid_to,method,status,source_id,is_example,metadata) VALUES(?,?,?,?,1000,1100,'direct',?,'history',0,?)");
  rawInsert.run('legacy-environment','location-1','vegetation','"Retained legacy source wording"','sourced','{ "original" : "never normalized" }');rawInsert.run('legacy-unresolved','location-2','climate','"climate:Cfb"','unknown','{ "uncertainty": "original bytes" }');rawInsert.run('whitespace-population','location-3','population',' \n 17 \t','sourced','{ "z" : 1, "a" : [2,1], "duplicate":1,"duplicate":2 }');for(const definition of definitions)sourceDb.sqlite.exec(definition);
  sourceDb.sqlite.prepare("INSERT INTO atlas_ingestions(rowid,id,fingerprint,counts,created_at) VALUES(99,'preserved-journal',?,'{ \"source_count\" : 3 }',123456789)").run('d'.repeat(64));
  const fetcher=async url=>{const parsed=new URL(url);if(parsed.pathname==='/api/storage/export-marker')return Response.json({...await exportStorageMarker(sourceDb),read_only:true});const collection=parsed.pathname.split('/').at(-1);return Response.json(await exportStoragePage(sourceDb,collection,{cursor:parsed.searchParams.get('cursor')??'',limit:Number(parsed.searchParams.get('limit')??200)}));};
  await exportHostedStorage({origin:'https://example.org/',output:directory,token:'test-only-secret-never-retained',fetcher});const target=await createLocalPostgres();
  const driver={query:(sql,params)=>target.engine.query(sql,params),runTransaction:callback=>target.engine.transaction(tx=>callback({query:(sql,params)=>tx.query(sql,params)}))};
  return {root,directory,sourceDb,target,driver,close:async()=>{await target.close();sourceDb.sqlite.close();fs.rmSync(root,{recursive:true,force:true});}};
 }catch(error){sourceDb.sqlite.close();fs.rmSync(root,{recursive:true,force:true});throw error;}
}

test('verified owner restore copies all fourteen original tables, legacy bytes, archives, examples, releases and rowids',async()=>{
 const f=await fixture({paged:true});try{
  const before=readVerifiedStorageSnapshot(f.directory);assert.ok(storageExportCollections.every(key=>before.proofs[key].count>0));const dry=await restorePostgresStorage({directory:f.directory,dryRun:true});assert.equal(dry.network_requests,0);
  assert.ok(before.proofs.entities.count>200,'Source export and target verification must traverse more than one keyset page');
  const receipt=await restorePostgresStorage({directory:f.directory,driver:f.driver,acknowledgeOwnerRestore:true});assert.equal(receipt.status,'restored');assert.equal(receipt.atomic,true);assert.equal(receipt.source_revision,99);assert.equal(receipt.sequence.next_rowid,100);assert.equal(receipt.media_bytes_moved,false);assert.deepEqual(receipt.collections,before.proofs);
  const readback=await restorePostgresStorage({directory:f.directory,driver:f.driver,verifyOnly:true});assert.equal(readback.read_only,true);assert.equal(readback.status,'verified');assert.deepEqual(readback.collections,before.proofs);
  for(const id of ['legacy-environment','legacy-unresolved','whitespace-population']){const sourceRow=f.sourceDb.sqlite.prepare('SELECT value,metadata FROM atlas_attribute_records WHERE id=?').get(id),targetRow=(await f.target.engine.query('SELECT value,metadata FROM atlas_attribute_records WHERE id=$1',[id])).rows[0];assert.deepEqual(targetRow,{...sourceRow});}
  assert.equal((await f.target.engine.query("SELECT status FROM atlas_geographic_releases WHERE id='release-2'")).rows[0].status,'published');assert.equal((await f.target.engine.query("SELECT active FROM atlas_entities WHERE id='archived'")).rows[0].active,0);assert.equal((await evidenceHistory(f.target.db,'records','old-pop')).claim.value,42);assert.equal((await attributesAt(f.target.db,1000)).records.find(row=>row.id==='new-pop').value,43);
  await assert.rejects(f.target.engine.query("TRUNCATE atlas_sources CASCADE"),/retained|append-only/i);await assert.rejects(f.target.engine.query("UPDATE atlas_attribute_records SET metadata='{}' WHERE id='legacy-environment'"),/immutable|append-only/i);await assert.rejects(f.target.engine.query("INSERT INTO atlas_sources(id,name,license,vintage,supported_from,supported_to,status,metadata) VALUES('fraction','Fraction','CC0','2026',1000.5,1100,'historical','{}')"),/domain|check/i);
  const next=await importBatch(f.target.db,{records:[record('new-after-restore','religion',null)]});assert.equal(next.revision,100,'New ingestion follows the preserved source maximum');
 }finally{await f.close();}
});
test('nonempty target refuses restoration without replacing evidence or disabled guards',async()=>{
 const f=await fixture();try{
  await importBatch(f.target.db,JSON.parse(fs.readFileSync(new URL('../data/hosted-type-catalog.json',import.meta.url))));await assert.rejects(restorePostgresStorage({directory:f.directory,driver:f.driver,acknowledgeOwnerRestore:true}),error=>error.phase==='empty-target');assert.equal((await f.target.engine.query('SELECT count(*)::int n FROM atlas_entity_types')).rows[0].n,16);assert.equal((await f.target.engine.query('SELECT count(*)::int n FROM atlas_sources')).rows[0].n,0);const disabled=(await f.target.engine.query("SELECT count(*)::int n FROM pg_trigger WHERE NOT tgisinternal AND tgenabled!='O'")).rows[0].n;assert.equal(disabled,0);
 }finally{await f.close();}
});
test('insert failure rolls back every copied table and USER-trigger state with no unsafe partial resume',async()=>{
 const f=await fixture();try{
  let failed=false;const driver={query:f.driver.query,runTransaction:callback=>f.target.engine.transaction(tx=>callback({async query(sql,params){if(!failed&&sql.startsWith('INSERT INTO atlas_names')){failed=true;const error=Error('Test-only failure');error.code='23503';throw error;}return tx.query(sql,params);}}))};await assert.rejects(restorePostgresStorage({directory:f.directory,driver,acknowledgeOwnerRestore:true}),error=>error.phase==='insert-original-rows'&&error.code==='23503');
  for(const collection of storageExportCollections){const table=collection==='records'?'atlas_attribute_records':collection==='retirements'?'atlas_evidence_retirements':`atlas_${collection}`;assert.equal((await f.target.engine.query(`SELECT count(*)::int n FROM ${table}`)).rows[0].n,0);}assert.equal((await f.target.engine.query("SELECT count(*)::int n FROM pg_trigger WHERE NOT tgisinternal AND tgenabled!='O'")).rows[0].n,0);
  const receipt=await restorePostgresStorage({directory:f.directory,driver:f.driver,acknowledgeOwnerRestore:true});assert.equal(receipt.status,'restored');assert.equal(receipt.sequence.next_rowid,100);
 }finally{await f.close();}
});
test('read-back verification failure rolls back source rows and prevents sequence advancement',async()=>{
 const f=await fixture();try{
  const driver={query:f.driver.query,runTransaction:callback=>f.target.engine.transaction(tx=>callback({async query(sql,params){const result=await tx.query(sql,params);if(sql.startsWith('SELECT id,location_id,attribute,value,')){return {...result,rows:result.rows.map((row,index)=>index===0?{...row,metadata:'{"tampered":true}'}:row)};}return result;}}))};await assert.rejects(restorePostgresStorage({directory:f.directory,driver,acknowledgeOwnerRestore:true}),error=>error.phase==='read-back');assert.equal((await f.target.engine.query('SELECT count(*)::int n FROM atlas_entities')).rows[0].n,0);const sequence=(await f.target.engine.query('SELECT last_value,is_called FROM atlas_ingestions_rowid_seq')).rows[0];assert.equal(Number(sequence.last_value),1);assert.equal(sequence.is_called,false);
 }finally{await f.close();}
});
test('tampered source parts and unacknowledged owner restore make no target writes',async()=>{
 const f=await fixture();try{
  await assert.rejects(restorePostgresStorage({directory:f.directory,driver:f.driver}),/explicit/);const manifest=JSON.parse(fs.readFileSync(path.join(f.directory,'index.json'))),part=manifest.collections.records.parts[0];fs.appendFileSync(path.join(f.directory,part.path),' ');assert.throws(()=>readVerifiedStorageSnapshot(f.directory),/bytes changed/);await assert.rejects(restorePostgresStorage({directory:f.directory,driver:f.driver,acknowledgeOwnerRestore:true}),/bytes changed/);assert.equal((await f.target.engine.query('SELECT count(*)::int n FROM atlas_sources')).rows[0].n,0);
 }finally{await f.close();}
});
test('sequence-reset failure rolls back transactional RESTART and preserves all original guards',async()=>{
 const f=await fixture();try{
  const driver={query:f.driver.query,runTransaction:callback=>f.target.engine.transaction(tx=>callback({async query(sql,params){const result=await tx.query(sql,params);return sql==='SELECT last_value,is_called FROM atlas_ingestions_rowid_seq'?{...result,rows:[{last_value:101,is_called:true}]}:result;}}))};
  await assert.rejects(restorePostgresStorage({directory:f.directory,driver,acknowledgeOwnerRestore:true}),error=>error.phase==='sequence');const state=(await f.target.engine.query('SELECT last_value,is_called FROM atlas_ingestions_rowid_seq')).rows[0];assert.equal(Number(state.last_value),1);assert.equal(state.is_called,false);assert.equal((await f.target.engine.query('SELECT count(*)::int n FROM atlas_entities')).rows[0].n,0);assert.equal((await f.target.engine.query("SELECT count(*)::int n FROM pg_trigger WHERE NOT tgisinternal AND tgenabled!='O'")).rows[0].n,0);
 }finally{await f.close();}
});
test('lost commit acknowledgement requires read-only verification before any retry',async()=>{
 const f=await fixture();try{
  const driver={query:f.driver.query,async runTransaction(callback){await f.driver.runTransaction(callback);throw Error('Test-only acknowledgement lost after the real commit');}};await assert.rejects(restorePostgresStorage({directory:f.directory,driver,acknowledgeOwnerRestore:true}),error=>error.phase==='commit'&&error.commit_status==='unknown');assert.equal(JSON.parse(fs.readFileSync(path.join(f.directory,'postgres-restore-receipt.json'))).commit_status,'unknown');
  const receipt=await restorePostgresStorage({directory:f.directory,driver:f.driver,verifyOnly:true});assert.equal(receipt.status,'verified');assert.equal(receipt.sequence.next_rowid,100);await assert.rejects(restorePostgresStorage({directory:f.directory,driver:f.driver,acknowledgeOwnerRestore:true}),error=>error.phase==='empty-target');
 }finally{await f.close();}
});
test('raw row digests preserve original text and obey D1 binary key order',()=>{
 const first={id:'a',name:'A',url:null,license:'CC0',vintage:'2026',supported_from:1000,supported_to:1100,status:'historical',metadata:'{ "x":1 }'},second={...first,id:'😀'};assert.equal(storageRowsHash('sources',[second,first]),storageRowsHash('sources',[first,second]));assert.notEqual(storageRowsHash('sources',[first]),storageRowsHash('sources',[{...first,metadata:'{"x":1}'}]));assert.equal(hash('x').length,64);
});
