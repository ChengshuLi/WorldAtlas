import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import {importBatch,registerMedia,entityProfile} from '../hosted/records.js';
import {catalogPage,entityRelationshipsPage,entityMediaPage,capacityReport} from '../hosted/research-catalog.js';

class D1 {
 constructor(){this.sqlite=new DatabaseSync(':memory:');this.sqlite.exec('PRAGMA foreign_keys=ON');for(const file of fs.readdirSync(new URL('../drizzle/',import.meta.url)).filter(f=>f.endsWith('.sql')).sort())this.sqlite.exec(fs.readFileSync(new URL(`../drizzle/${file}`,import.meta.url),'utf8'));}
 prepare(sql){const sqlite=this.sqlite;let args=[];return {bind(...values){args=values;return this;},async all(){return {results:sqlite.prepare(sql).all(...args)};},async first(){return sqlite.prepare(sql).get(...args)??null;},run(){return {meta:{changes:Number(sqlite.prepare(sql).run(...args).changes)}};}};}
 async batch(statements){this.sqlite.exec('BEGIN IMMEDIATE');try{const rows=statements.map(s=>s.run());this.sqlite.exec('COMMIT');return rows;}catch(error){this.sqlite.exec('ROLLBACK');throw error;}}
}
const source=(id='history',extra={})=>({id,name:'Historical source',url:'https://example.org/source',license:'CC0',vintage:'2026',supported_from:-3000,supported_to:2027,status:'historical',metadata:{sha256:'f'.repeat(64),method:'published census'},...extra});
async function importMany(db,key,rows){for(let offset=0;offset<rows.length;offset+=200)await importBatch(db,{[key]:rows.slice(offset,offset+200)});}
async function fixture(){
 const db=new D1();await importBatch(db,JSON.parse(fs.readFileSync(new URL('../data/hosted-type-catalog.json',import.meta.url))));
 const tiers=['continent','subcontinent','region','area','province','location'];
 await importBatch(db,{sources:[source(),source('example',{status:'example'})],entities:[...tiers.map((kind,i)=>({id:kind,kind,name:`Reference ${kind}`,parent_id:i?tiers[i-1]:null})),{id:'person',kind:'person',name:'Person'},{id:'person:archived',kind:'person',name:'Archived person',active:0},{id:'person:example',kind:'person',name:'Example person',is_example:1}],categories:[{id:'owner:one',kind:'owner',name:'Owner One',source_id:'history'},{id:'culture:one',kind:'culture',name:'Culture One',source_id:'history'},{id:'owner:example',kind:'owner',name:'Example owner',source_id:'example'}]});
 return db;
}
async function exhaustive(loader){const rows=[];let cursor='';do{const p=await loader(cursor);assert.ok(p.records.length<=250);rows.push(...p.records);cursor=p.next_cursor;}while(cursor);assert.equal(new Set(rows.map(r=>r.id)).size,rows.length);return rows;}

test('discovery preserves identity/source metadata and pages every result with bounded filters',async()=>{
 const db=await fixture();try{
  await importMany(db,'sources',Array.from({length:271},(_,i)=>source(`source:${String(i).padStart(3,'0')}`,{name:`Research 100% source ${i}`})));
  const first=await catalogPage(db,'sources',{q:'100%',limit:1000});assert.equal(first.records.length,250);assert.ok(first.next_cursor);assert.equal(first.records[0].metadata.sha256,'f'.repeat(64));assert.match(first.identity_context,/Undated/);
  const all=await exhaustive(cursor=>catalogPage(db,'sources',{q:'100%',cursor,limit:250}));assert.equal(all.length,271);assert.equal(all.at(-1).id,'source:270');
  assert.equal((await catalogPage(db,'sources',{q:"%' OR 1=1 --"})).records.length,0,'search punctuation is literal bound data');
  assert.equal((await catalogPage(db,'sources',{kind:'example'})).records.length,0);assert.equal((await catalogPage(db,'sources',{kind:'example',examples:true})).records[0].id,'example');
  assert.deepEqual((await catalogPage(db,'categories',{kind:'owner'})).records.map(r=>r.id),['owner:one']);assert.equal((await catalogPage(db,'categories',{kind:'owner',examples:true})).records.length,2);
  assert.deepEqual((await catalogPage(db,'entities',{kind:'person',active:true})).records.map(r=>r.id),['person']);assert.equal((await catalogPage(db,'entities',{kind:'person'})).records.length,2,'archived identities remain discoverable');assert.equal((await catalogPage(db,'entities',{kind:'person',examples:true})).records.length,3);
  await importMany(db,'categories',Array.from({length:271},(_,i)=>({id:`owner:additional:${String(i).padStart(3,'0')}`,kind:'owner',name:`Additional owner ${i}`,source_id:'history'})));
  for(const collection of ['categories','entities'])assert.equal((await exhaustive(cursor=>catalogPage(db,collection,{q:'ADDITIONAL OWNER',cursor,limit:137}))).length,271);
  await assert.rejects(catalogPage(db,'entities',{limit:0}),/limit/);await assert.rejects(catalogPage(db,'sources',{active:true}),/Active/);await assert.rejects(catalogPage(db,'sources',{q:'x'.repeat(257)}),/256/);await assert.rejects(catalogPage(db,'unknown'),/collection/);
 }finally{db.sqlite.close();}
});

test('relationship pages exhaust both directions beyond profile truncation with date/example/withdrawal filtering',async()=>{
 const db=await fixture();try{
  const rows=Array.from({length:271},(_,i)=>({id:`link:${String(i).padStart(3,'0')}`,source_entity_id:i%2?'person':'location',target_entity_id:i%2?'location':'person',relationship_type:'associated_with',source_id:'history'}));
  await importMany(db,'relationships',rows);
  await importBatch(db,{relationships:[{id:'link:dated',source_entity_id:'location',target_entity_id:'person',relationship_type:'visited',source_id:'history',valid_from:1000,valid_to:1100},{id:'link:example',source_entity_id:'location',target_entity_id:'person:example',relationship_type:'example',source_id:'example',is_example:1}],retirements:[{id:'retire:relationship',collection:'relationships',target_id:'link:100',source_id:'history',reason:'Source corrected this association'}]});
  const profile=await entityProfile(db,'location',1000);assert.equal(profile.relationships_truncated,true);
  const normal=await exhaustive(cursor=>entityRelationshipsPage(db,'location',1000,{cursor,limit:67}));assert.equal(normal.length,271);assert.ok(normal.every(r=>r.id!=='link:100'&&r.id!=='link:example'));assert.equal(normal.find(r=>r.id==='link:dated').date_status,'dated');assert.equal(normal[0].date_status,'unknown');assert.equal(normal[0].source_metadata.sha256,'f'.repeat(64));
  assert.equal((await exhaustive(cursor=>entityRelationshipsPage(db,'location',1100,{cursor}))).length,270,'exclusive upper date boundary');assert.equal((await exhaustive(cursor=>entityRelationshipsPage(db,'location',1000,{cursor,examples:true}))).length,272);
  assert.equal(await entityRelationshipsPage(db,'missing',1000),null);assert.equal(await entityRelationshipsPage(db,'person:example',1000),null);assert.equal((await entityRelationshipsPage(db,'person:example',1000,{examples:true})).records[0].id,'link:example');await assert.rejects(entityRelationshipsPage(db,'location',0),/year/);
 }finally{db.sqlite.close();}
});

test('media link pages preserve every active link and omit withdrawn, pending and unsupported-year links',async()=>{
 const db=await fixture();try{
  const sha='a'.repeat(64);await registerMedia(db,{id:'image',object_key:`media/${sha}`,sha256:sha,bytes:13,mime:'image/png',name:'Source image',license:'CC0',attribution:'Archive',source_id:'history'});
  const rows=Array.from({length:271},(_,i)=>({id:`media-link:${String(i).padStart(3,'0')}`,media_id:'image',entity_id:'location',role:'image',source_id:'history'}));await importMany(db,'media_links',rows);
  const pending='b'.repeat(64);db.sqlite.prepare('INSERT INTO atlas_media (id,object_key,sha256,bytes,mime,name,license,attribution,source_id,status) VALUES (?,?,?,?,?,?,?,?,?,?)').run('pending',`media/${pending}`,pending,21,'audio/wav','Pending object','CC0','Archive','history','pending');
  await importBatch(db,{media_links:[{id:'media-link:dated',media_id:'image',entity_id:'location',role:'historical map',source_id:'history',valid_from:1000,valid_to:1100},{id:'media-link:example',media_id:'image',entity_id:'location',role:'example',source_id:'example',is_example:1},{id:'media-link:pending',media_id:'pending',entity_id:'location',role:'audio',source_id:'history'}],retirements:[{id:'retire:media',collection:'media_links',target_id:'media-link:100',source_id:'history',reason:'Incorrect source association'}]});
  assert.equal((await entityProfile(db,'location',1000)).media_truncated,true);
  const normal=await exhaustive(cursor=>entityMediaPage(db,'location',1000,{cursor,limit:91}));assert.equal(normal.length,271);assert.ok(normal.every(r=>!['media-link:100','media-link:pending','media-link:example'].includes(r.id)));assert.equal(normal[0].bytes,13);assert.equal(normal[0].sha256,sha);assert.equal(normal[0].source_metadata.method,'published census');assert.equal(normal.find(r=>r.id==='media-link:dated').date_status,'dated');
  assert.equal((await exhaustive(cursor=>entityMediaPage(db,'location',1100,{cursor}))).length,270);assert.equal((await exhaustive(cursor=>entityMediaPage(db,'location',1000,{cursor,examples:true}))).length,272);assert.equal(await entityMediaPage(db,'missing'),null);assert.equal(await entityMediaPage(db,'person:example'),null);
 }finally{db.sqlite.close();}
});

test('capacity reports measured bytes and declared budgets without claiming a managed quota or prepared assets',async()=>{
 const db=await fixture();try{
  await importBatch(db,{records:[{id:'population',location_id:'location',attribute:'population',value:42,valid_from:1000,valid_to:1001,source_id:'history'}]});
  const sha='c'.repeat(64);await registerMedia(db,{id:'audio',object_key:`media/${sha}`,sha256:sha,bytes:42,mime:'audio/wav',name:'Sourced sound',license:'CC0',attribution:'Archive',source_id:'history'});
  const report=await capacityReport(db);assert.equal(report.counts.sources,2);assert.equal(report.counts.geographic_releases,0);assert.equal(report.database.bytes,db.sqlite.prepare('PRAGMA page_count').get().page_count*db.sqlite.prepare('PRAGMA page_size').get().page_size);assert.equal(report.database.quota_verified,false);assert.equal(report.database.configured_budget_bytes,null);assert.equal(report.database.budget_status,'unknown');assert.equal(report.backend.partitioning_deployed,false);assert.match(report.storage_scope,/prepared/);assert.equal(report.media.upload_limit_bytes,20*1024*1024);
  assert.equal(report.counts.records,1);assert.equal(report.media.registered_objects,1);assert.equal(report.media.registered_bytes,42);
  const atBudget=await capacityReport(db,{databaseBudgetBytes:report.database.bytes});assert.equal(atBudget.database.budget_status,'at-or-above-budget');assert.equal(atBudget.database.budget_is_provider_quota,false);
  const near=await capacityReport(db,{databaseBudgetBytes:Math.ceil(report.database.bytes/0.9)});assert.equal(near.database.budget_status,'approaching-budget');
  const unsupported={prepare(sql){if(sql.startsWith('PRAGMA '))return {async first(){throw Error('D1 does not allow this PRAGMA');}};return db.prepare(sql);}};
  const unknown=await capacityReport(unsupported,{databaseBudgetBytes:1e9});assert.equal(unknown.database.bytes,null);assert.equal(unknown.database.measurement,'unavailable');assert.equal(unknown.database.budget_status,'unknown');assert.equal(unknown.counts.entities,report.counts.entities);
  const nativeMetadata={prepare(sql){const statement=db.prepare(sql);if(sql.startsWith('PRAGMA '))throw Error('Metadata measurement must avoid unsupported PRAGMA');return {...statement,async all(){return {...await statement.all(),meta:{size_after:123456}};}};}};
  const metadata=await capacityReport(nativeMetadata);assert.equal(metadata.database.bytes,123456);assert.equal(metadata.database.measurement,'d1-query-size-after');assert.equal(metadata.database.quota_verified,false);
  await assert.rejects(capacityReport(db,{databaseBudgetBytes:-1}),/budget/);await assert.rejects(capacityReport(db,{warningFraction:1}),/fraction/);
 }finally{db.sqlite.close();}
});

test('catalog and graph reads reject revision changes instead of publishing inconsistent pages',async()=>{
 const db=await fixture();try{
  const drifting=()=>{let reads=0;return {prepare(sql){const statement=db.prepare(sql);if(!sql.includes('coalesce(max(rowid),0) revision'))return statement;return {async first(){const row=await statement.first();return {...row,revision:row.revision+Number(++reads>1)};}};}};};
  for(const request of [d=>catalogPage(d,'sources'),d=>entityRelationshipsPage(d,'location'),d=>entityMediaPage(d,'location'),d=>capacityReport(d)])await assert.rejects(request(drifting()),error=>error.status===409&&error.retryable===true);
 }finally{db.sqlite.close();}
});
