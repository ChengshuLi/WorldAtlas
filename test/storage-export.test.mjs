import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {DatabaseSync} from 'node:sqlite';
import {importBatch,registerMedia} from '../hosted/records.js';
import {stageGeographicRelease,finalizeGeographicRelease,geographicMembershipHash,geographicLocationIdsHash,geographicChangesHash} from '../hosted/geographic-releases.js';
import {exportStoragePage,exportStorageMarker,storageExportCollections} from '../hosted/storage-export.js';
import {exportHostedStorage} from '../scripts/export-hosted-storage.mjs';

class D1 {
 constructor(){this.sqlite=new DatabaseSync(':memory:');this.sqlite.exec('PRAGMA foreign_keys=ON');for(const file of fs.readdirSync(new URL('../drizzle/',import.meta.url)).filter(f=>f.endsWith('.sql')).sort())this.sqlite.exec(fs.readFileSync(new URL(`../drizzle/${file}`,import.meta.url),'utf8'));}
 prepare(sql){const sqlite=this.sqlite;let args=[];return {bind(...values){args=values;return this;},async all(){return {results:sqlite.prepare(sql).all(...args)};},async first(){return sqlite.prepare(sql).get(...args)??null;},run(){return {meta:{changes:Number(sqlite.prepare(sql).run(...args).changes)}};}};}
 async batch(statements){this.sqlite.exec('BEGIN IMMEDIATE');try{const result=statements.map(s=>s.run());this.sqlite.exec('COMMIT');return result;}catch(error){this.sqlite.exec('ROLLBACK');throw error;}}
}
const tableFor=collection=>({records:'atlas_attribute_records',retirements:'atlas_evidence_retirements'}[collection]??`atlas_${collection}`);
const source=(id,status='historical')=>({id,name:id,url:'https://example.org/source',license:'CC0',vintage:'2026',supported_from:status==='reference'?2026:-3000,supported_to:2027,status});
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
test('complete export marker works under managed D1 compound-SELECT limits',async()=>{
 const {db}=await fixture();const prepare=db.prepare.bind(db);
 db.prepare=sql=>{if((sql.match(/\bUNION\b/gi)||[]).length>=5)throw Error('D1_ERROR: too many terms in compound SELECT');return prepare(sql);};
 try{const marker=await exportStorageMarker(db);assert.equal(Object.keys(marker.counts).length,14);for(const collection of storageExportCollections)assert.equal(marker.counts[collection],db.sqlite.prepare(`SELECT count(*) n FROM ${tableFor(collection)}`).get().n);assert.equal((await exportStoragePage(db,'entities')).snapshot_marker.fingerprint,marker.fingerprint);}
 finally{db.sqlite.close();}
});
async function fixture(){
 const db=new D1();await importBatch(db,JSON.parse(fs.readFileSync(new URL('../data/hosted-type-catalog.json',import.meta.url))));
 const kinds=['continent','subcontinent','region','area','province','location'],entities=[];for(let c=0;c<6;c++)for(let i=0;i<6;i++)entities.push({id:`${kinds[i]}-${c}`,kind:kinds[i],name:`Reference ${kinds[i]} ${c}`,parent_id:i?`${kinds[i-1]}-${c}`:null});
 await importBatch(db,{sources:[source('history'),source('reference','reference'),source('example','example')],entities:[...entities,{id:'archived-place',kind:'place',name:'Archived',active:0},{id:'example-person',kind:'person',name:'Example',is_example:1}],categories:[{id:'owner:one',kind:'owner',name:'Owner One',source_id:'history'}]});
 db.sqlite.prepare('INSERT INTO atlas_attribute_records(id,location_id,attribute,value,valid_from,valid_to,method,status,source_id,metadata) VALUES(?,?,?,?,?,?,?,?,?,?)').run('original-population','location-0','population',' 42 ',1000,1001,'direct','sourced','history','{ "precision" : "census", "original" : "verbatim" }');
 await importBatch(db,{names:[{id:'original-name',entity_id:'location-0',name:'Historical name',language:'en',valid_from:1000,valid_to:1001,source_id:'history'}],relationships:[{id:'example-association',source_entity_id:'location-0',target_entity_id:'example-person',relationship_type:'associated_with',source_id:'example',is_example:1}]});
 const digest='a'.repeat(64);await registerMedia(db,{id:'original-media',object_key:`media/${digest}`,sha256:digest,bytes:42,mime:'audio/wav',name:'Sourced audio',license:'CC0',attribution:'Archive',source_id:'history'});
 await importBatch(db,{media_links:[{id:'original-media-link',media_id:'original-media',entity_id:'location-0',role:'music',source_id:'history'}],retirements:[{id:'original-withdrawal',collection:'records',target_id:'original-population',source_id:'history',reason:'Sourced correction'}]});
 const memberships=entities.map(e=>({entity_id:e.id,kind:e.kind,parent_id:e.parent_id,reference_name:e.name,active:1,source_id:'reference',evidence:{original:true}}));
 async function stage(id,version,publish=true){const changes=[{id:`${id}:retained`,old_entity_id:'location-0',new_entity_id:'location-0',change_type:'retain',source_id:'reference',evidence:{source:'Original footprint'}}];const release={id,version,source_id:'reference',reference_date:'2026-10-01',hierarchy_sha256:'b'.repeat(64),footprints_sha256:'c'.repeat(64),membership_sha256:await geographicMembershipHash(memberships),location_ids_sha256:await geographicLocationIdsHash(memberships),changes_sha256:await geographicChangesHash(changes),expected_counts:Object.fromEntries(kinds.map(kind=>[kind,6])),metadata:{reference_only:true}};await stageGeographicRelease(db,{release,memberships,changes});if(publish)await finalizeGeographicRelease(db,id);}
 await stage('release:A',1);await stage('release:B',2,false);return {db,stage};
}
async function collect(db,collection,limit=3){const pages=[],records=[];let cursor='';do{const page=await exportStoragePage(db,collection,{cursor,limit});pages.push(page);records.push(...page.records);cursor=page.next_cursor??'';}while(cursor);return {pages,records};}
function service(db,{readOnly=true,intercept}={}){return async(url,options)=>{assert.equal(options.headers['OAI-Sites-Authorization'],'Bearer TEST_ONLY_CREDENTIAL');const parsed=new URL(url);if(intercept){const intercepted=await intercept(parsed);if(intercepted)return intercepted;}try{if(parsed.pathname==='/api/storage/export-marker')return Response.json({...await exportStorageMarker(db),read_only:readOnly});const collection=parsed.pathname.split('/').at(-1);return Response.json(await exportStoragePage(db,collection,{cursor:parsed.searchParams.get('cursor')??'',limit:Number(parsed.searchParams.get('limit')??200)}));}catch(error){return Response.json({error:error.message,retryable:error.retryable,suggested_limit:error.suggested_limit},{status:error.status??503});}};}

test('all fourteen raw tables export exhaustively with original text, rowids and archived evidence',async()=>{
 const {db}=await fixture();try{
  const tables=db.sqlite.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'atlas_%' ORDER BY name").all().map(r=>r.name);assert.deepEqual(storageExportCollections.map(tableFor).sort(),tables);
  const marker=await exportStorageMarker(db);assert.equal(Object.keys(marker.counts).length,14);
  for(const collection of storageExportCollections){
   assert.ok(marker.counts[collection]>0,`${collection} fixture must contain real data`);const {pages,records}=await collect(db,collection);assert.equal(records.length,marker.counts[collection]);assert.ok(pages.every(p=>p.records.length<=3&&p.snapshot_marker.fingerprint===marker.fingerprint));
   const table=tableFor(collection),columns=db.sqlite.prepare(`PRAGMA table_info(${table})`).all().map(r=>r.name);if(collection==='ingestions')columns.unshift('rowid');assert.deepEqual(pages[0].columns,columns);
   const order=collection==='ingestions'?'rowid':collection==='geographic_memberships'?'release_id,entity_id':collection==='geographic_changes'?'release_id,id':'id';const original=db.sqlite.prepare(`SELECT ${columns.join(',')} FROM ${table} ORDER BY ${order}`).all();assert.equal(JSON.stringify(records),JSON.stringify(original),`${collection} must preserve every raw column exactly`);
  }
  const records=(await collect(db,'records')).records;assert.equal(records[0].value,' 42 ');assert.equal(records[0].metadata,'{ "precision" : "census", "original" : "verbatim" }');assert.equal((await collect(db,'entities')).records.find(r=>r.id==='archived-place').active,0);assert.equal((await collect(db,'relationships')).records[0].is_example,1);assert.equal((await collect(db,'retirements')).records[0].target_id,'original-population');assert.ok((await collect(db,'ingestions')).records.every(r=>Number.isSafeInteger(r.rowid)&&r.rowid>0));
 }finally{db.sqlite.close();}
});

test('composite keyset cursors page across releases and reject foreign, malformed or injected cursors',async()=>{
 const {db}=await fixture();try{
  const {pages,records}=await collect(db,'geographic_memberships',5);assert.equal(records.length,72);assert.equal(new Set(records.map(r=>`${r.release_id}/${r.entity_id}`)).size,72);assert.ok(pages.some(p=>p.records.some(r=>r.release_id==='release:A')&&p.records.some(r=>r.release_id==='release:B')),'a page must safely span release boundaries');
  const valid=pages[0].next_cursor;assert.match(valid,/^[A-Za-z0-9_-]+$/);await assert.rejects(exportStoragePage(db,'sources',{cursor:valid}),/cursor/);
  for(const cursor of ['x; DROP TABLE atlas_sources','e30','====','not canonical$'])await assert.rejects(exportStoragePage(db,'sources',{cursor}),/cursor/);
  const injection=btoa(JSON.stringify({version:1,collection:'sources',key:["' OR 1=1 --"]})).replaceAll('+','-').replaceAll('/','_').replace(/=+$/,'');const safe=await exportStoragePage(db,'sources',{cursor:injection});assert.ok(safe.records.length<=3);assert.equal(db.sqlite.prepare('SELECT count(*) n FROM atlas_sources').get().n,3,'valid string keys remain bound data');
  await assert.rejects(exportStoragePage(db,'__proto__'),/collection/);await assert.rejects(exportStoragePage(db,'sources',{limit:0}),/limit/);assert.equal((await exportStoragePage(db,'sources',{limit:2000})).records.length,3);
 }finally{db.sqlite.close();}
});

test('markers detect publication and media writes outside ingestion revisions and reject raced pages',async()=>{
 const {db}=await fixture();try{
  const before=await exportStorageMarker(db);await finalizeGeographicRelease(db,'release:B');const published=await exportStorageMarker(db);assert.equal(published.revision,before.revision);assert.deepEqual(published.counts,before.counts);assert.notEqual(published.fingerprint,before.fingerprint,'publication changes must participate in snapshot identity');
  const digest='d'.repeat(64);await registerMedia(db,{id:'more-media',object_key:`media/${digest}`,sha256:digest,bytes:1,mime:'image/png',name:'Image',license:'CC0',attribution:'Archive',source_id:'history'});const media=await exportStorageMarker(db);assert.equal(media.revision,before.revision);assert.equal(media.counts.media,before.counts.media+1);assert.notEqual(media.fingerprint,published.fingerprint);
  const prepare=db.prepare.bind(db);let changed=false;db.prepare=sql=>{const statement=prepare(sql);if(sql.startsWith('SELECT id,name,url,license,vintage,supported_from')&&!changed){const all=statement.all;statement.all=async()=>{const result=await all();changed=true;await importBatch(db,{sources:[source('new-source')]});return result;};}return statement;};
  await assert.rejects(exportStoragePage(db,'sources'),error=>error.status===409&&error.retryable===true);
 }finally{db.sqlite.close();}
});

test('oversized retained evidence is reduced through explicit 413 rather than truncated',async()=>{
 const {db}=await fixture();try{
  const insert=db.sqlite.prepare('INSERT INTO atlas_sources(id,name,url,license,vintage,supported_from,supported_to,status,metadata) VALUES(?,?,?,?,?,?,?,?,?)'),metadata=JSON.stringify({original:'x'.repeat(60000)});for(let i=0;i<200;i++)insert.run(`large:${String(i).padStart(3,'0')}`,'Large retained source','https://example.org/large','CC0','2026',2026,2027,'reference',metadata);
  await assert.rejects(exportStoragePage(db,'sources'),error=>error.status===413&&error.retryable===true&&error.suggested_limit===100);const smaller=await exportStoragePage(db,'sources',{limit:100});assert.ok(smaller.records.some(r=>r.metadata===metadata));assert.equal(smaller.records.length,100);assert.ok(smaller.next_cursor);
 }finally{db.sqlite.close();}
});

test('CLI exporter preserves a partial ledger, resumes hashed pages and proves frozen all-table counts',async()=>{
 const {db}=await fixture(),output=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-raw-export-'));let interrupted=true,sourceRequests=0;
 const fetcher=service(db,{intercept:async parsed=>{if(parsed.pathname.endsWith('/sources')){sourceRequests++;if(interrupted&&parsed.searchParams.has('cursor'))return Response.json({error:'Interrupted'},{status:500});}if(parsed.pathname.endsWith('/sources')&&!parsed.searchParams.has('cursor')&&Number(parsed.searchParams.get('limit'))>1)return Response.json({retryable:true,suggested_limit:1},{status:413});}});
 try{
  await assert.rejects(exportHostedStorage({origin:'https://atlas.example/',output,token:'TEST_ONLY_CREDENTIAL',fetcher}),/HTTP 500/);const partial=JSON.parse(fs.readFileSync(path.join(output,'resume.json')));assert.equal(partial.status,'partial');assert.equal(partial.collections.sources.count,1);const saved=fs.readFileSync(path.join(output,partial.collections.sources.parts[0].path));assert.ok(!fs.readFileSync(path.join(output,'resume.json'),'utf8').includes('TEST_ONLY_CREDENTIAL'));interrupted=false;
  const complete=await exportHostedStorage({origin:'https://atlas.example/',output,token:'TEST_ONLY_CREDENTIAL',fetcher});assert.equal(complete.status,'complete');assert.equal(complete.snapshot_consistent,true);assert.deepEqual(Object.fromEntries(Object.entries(complete.collections).map(([key,value])=>[key,value.count])),complete.snapshot_marker.counts);assert.deepEqual(fs.readFileSync(path.join(output,partial.collections.sources.parts[0].path)),saved,'resuming never rewrites completed source bytes');
  for(const collection of storageExportCollections)for(const part of complete.collections[collection].parts){const raw=fs.readFileSync(path.join(output,part.path));assert.equal(sha(raw),part.sha256);assert.equal(raw.length,part.bytes);assert.equal(JSON.parse(raw).records.length,part.rows);}
  const before=sourceRequests;await exportHostedStorage({origin:'https://atlas.example/',output,token:'TEST_ONLY_CREDENTIAL',fetcher});assert.equal(sourceRequests,before,'a verified completed export needs only marker reads');
 }finally{db.sqlite.close();fs.rmSync(output,{recursive:true,force:true});}
});

test('CLI rejects unfrozen, changed or tampered exports without mixing checkpoints',async()=>{
 const {db}=await fixture(),directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-raw-export-'));
 try{
  const unfrozen=path.join(directory,'unfrozen');await assert.rejects(exportHostedStorage({origin:'https://atlas.example/',output:unfrozen,token:'TEST_ONLY_CREDENTIAL',fetcher:service(db,{readOnly:false})}),/maintenance/);assert.equal(fs.existsSync(unfrozen),false);
  const output=path.join(directory,'capture'),complete=await exportHostedStorage({origin:'https://atlas.example/',output,token:'TEST_ONLY_CREDENTIAL',fetcher:service(db)}),file=path.join(output,complete.collections.records.parts[0].path),original=fs.readFileSync(file);fs.appendFileSync(file,' ');await assert.rejects(exportHostedStorage({origin:'https://atlas.example/',output,token:'TEST_ONLY_CREDENTIAL',fetcher:service(db)}),/hash\/size/);fs.writeFileSync(file,original);
  await importBatch(db,{sources:[source('after-capture')]});await assert.rejects(exportHostedStorage({origin:'https://atlas.example/',output,token:'TEST_ONLY_CREDENTIAL',fetcher:service(db)}),/Source storage changed/);assert.deepEqual(fs.readFileSync(file),original);
 }finally{db.sqlite.close();fs.rmSync(directory,{recursive:true,force:true});}
});

test('CLI overlaps bounded independent collections while preserving serial cursors and journals',async()=>{
 const {db}=await fixture(),output=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-raw-export-'));let active=0,maximum=0;const inFlight=new Set();
 const fetcher=async(url,options)=>{const parsed=new URL(url);assert.equal(options.headers['OAI-Sites-Authorization'],'Bearer TEST_ONLY_CREDENTIAL');if(parsed.pathname.endsWith('export-marker'))return Response.json({...await exportStorageMarker(db),read_only:true});const collection=parsed.pathname.split('/').at(-1);assert.equal(inFlight.has(collection),false,'one collection cannot issue overlapping keyset reads');inFlight.add(collection);active++;maximum=Math.max(maximum,active);try{await new Promise(resolve=>setTimeout(resolve,2));return Response.json(await exportStoragePage(db,collection,{cursor:parsed.searchParams.get('cursor')??'',limit:3}));}finally{active--;inFlight.delete(collection);}};
 try{const result=await exportHostedStorage({origin:'https://atlas.example/',output,token:'TEST_ONLY_CREDENTIAL',fetcher,concurrency:4});assert.ok(maximum>1,'independent collections actually overlap');assert.ok(maximum<=4);assert.equal(active,0);assert.equal(result.status,'complete');assert.deepEqual(Object.fromEntries(Object.entries(result.collections).map(([key,value])=>[key,value.count])),result.snapshot_marker.counts);await assert.rejects(exportHostedStorage({origin:'https://atlas.example/',output,token:'TEST_ONLY_CREDENTIAL',fetcher,concurrency:5}),/concurrency/);}finally{db.sqlite.close();fs.rmSync(output,{recursive:true,force:true});}
});
