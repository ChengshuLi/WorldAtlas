import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import worker from '../hosted/worker.js';
import {importBatch} from '../hosted/records.js';
import {createLocalPostgres} from '../scripts/verify-postgres-schema.mjs';
import {stageGeographicRelease,finalizeGeographicRelease,geographicMembershipHash,geographicLocationIdsHash,geographicChangesHash} from '../hosted/geographic-releases.js';

class SQLiteBinding {
 constructor(){this.sqlite=new DatabaseSync(':memory:');this.sqlite.exec('PRAGMA foreign_keys=ON');for(const file of fs.readdirSync(new URL('../drizzle/',import.meta.url)).filter(file=>file.endsWith('.sql')).sort())this.sqlite.exec(fs.readFileSync(new URL(`../drizzle/${file}`,import.meta.url),'utf8'));}
 prepare(sql){const statement=this.sqlite.prepare(sql);let values=[];return {bind(...args){values=args;return this;},async first(){return statement.get(...values)??null;},async all(){return {results:statement.all(...values)};},run(){return {meta:{changes:Number(statement.run(...values).changes)}};}};}
 async batch(statements){this.sqlite.exec('BEGIN IMMEDIATE');try{const result=statements.map(statement=>statement.run());this.sqlite.exec('COMMIT');return result;}catch(error){this.sqlite.exec('ROLLBACK');throw error;}}
}
const origin='https://worker-test.example',tiers=['continent','subcontinent','region','area','province','location'];
const pin={release_id:'worker-reference',hierarchy_sha256:'a'.repeat(64),footprints_sha256:'b'.repeat(64)};
const source=(id,status)=>({id,name:`Isolated worker ${id}`,url:'https://example.org/worker-fixture',license:'CC0',vintage:'2026',supported_from:status==='reference'?2026:-3000,supported_to:2027,status,metadata:{synthetic:true}});
const membership=(id,entity_id='location-0',parent_id='province-1',extra={})=>({id,entity_id,parent_id,valid_from:1000,valid_to:1100,source_id:'worker-history',...extra});
async function fixture(backend){
 const pg=backend==='postgres'?await createLocalPostgres():null,DB=pg?.db??new SQLiteBinding();
 try{
  if(pg)await pg.engine.exec(fs.readFileSync(new URL('../postgres/migrations/0001_temporal_geography.sql',import.meta.url),'utf8'));
  await importBatch(DB,JSON.parse(fs.readFileSync(new URL('../data/hosted-type-catalog.json',import.meta.url))));
  const entities=Array.from({length:6},(_,n)=>tiers.map((kind,index)=>({id:`${kind}-${n}`,kind,name:`Worker ${kind} ${n}`,parent_id:index?`${tiers[index-1]}-${n}`:null}))).flat();
  await importBatch(DB,{sources:[source('worker-history','historical'),source('worker-reference-source','reference'),source('worker-example','example')],entities,records:[{id:'worker-population',location_id:'location-0',attribute:'population',value:42,valid_from:1000,valid_to:1100,source_id:'worker-history'}]});
  const memberships=entities.map(row=>({entity_id:row.id,kind:row.kind,parent_id:row.parent_id,reference_name:row.name,active:1,source_id:'worker-reference-source',evidence:{synthetic:true}}));
  await stageGeographicRelease(DB,{release:{id:pin.release_id,source_id:'worker-reference-source',version:1,reference_date:'2026-10-02',hierarchy_sha256:pin.hierarchy_sha256,footprints_sha256:pin.footprints_sha256,membership_sha256:await geographicMembershipHash(memberships),location_ids_sha256:await geographicLocationIdsHash(memberships),changes_sha256:await geographicChangesHash([]),expected_counts:Object.fromEntries(tiers.map(kind=>[kind,6]))},memberships});
  await finalizeGeographicRelease(DB,pin.release_id);
  const objects=new Map();const env={DB,ASSETS:{fetch:()=>new Response('static fixture')},BUCKET:{async head(key){return objects.has(key)?{}:null;},async put(key,bytes){objects.set(key,bytes);},async get(key){const bytes=objects.get(key);return bytes?{body:bytes,size:bytes.byteLength}:null;}}};
  const request=(path,{method='GET',headers={},body,...options}={},selected=env)=>worker.fetch(new Request(origin+path,{method,headers,...(body===undefined?{}:{body:typeof body==='string'||body instanceof Uint8Array?body:JSON.stringify(body)}),...options}),selected,{});
  const post=(body,selected=env)=>request('/api/geography/temporal/import',{method:'POST',headers:{Origin:origin,'Content-Type':'application/json'},body:{expected_geography:pin,...body}},selected);
  return {DB,env,request,post,close:()=>pg?pg.close():DB.sqlite.close()};
 }catch(error){await (pg?pg.close():Promise.resolve(DB.sqlite.close()));throw error;}
}

for(const backend of ['sqlite','postgres']){
 test(`Worker dated geography routes, revision, evidence and retry work on actual ${backend}`,async()=>{
  const f=await fixture(backend);try{
   const initial=await (await f.request('/api/geography/temporal/snapshot?year=1000')).json();assert.equal(initial.stream,'records');assert.deepEqual(initial.records,[]);assert.equal(initial.capability.datedFootprints,0);assert.equal(initial.release_id,pin.release_id);
   const input={ingestion_id:'worker-ingestion',memberships:[membership('worker:parent/old','location-0',null),membership('worker-example-parent','location-2','province-1',{source_id:'worker-example',is_example:1})],existence:[{id:'worker-absence',entity_id:'location-1',value:'not_exists',valid_from:1000,valid_to:1100,source_id:'worker-history'}]};
   const response=await f.post(input);assert.equal(response.status,200);assert.equal(response.headers.get('Cache-Control'),'no-store');const receipt=await response.json();assert.equal(receipt.duplicate,false);assert.ok(receipt.revision>initial.revision);assert.deepEqual(receipt.expected_geography,pin);
   const first=await (await f.request('/api/geography/temporal/snapshot?year=1000&limit=1')).json();assert.equal(first.records[0].id,'worker:parent/old');assert.equal(first.records[0].effective_parent_id,'province-0');assert.equal(first.records[0].parent_context,'reference');assert.equal(first.records[0].membership_status,'unknown');assert.equal(first.sources[0].id,'worker-history');assert.ok(first.next_cursor);
   const next=await (await f.request('/api/geography/temporal/snapshot?year=1000&limit=1&cursor='+encodeURIComponent(first.next_cursor))).json();assert.equal(next.records[0].value,'not_exists');assert.equal(next.next_cursor,null);assert.equal(next.revision,receipt.revision);
   const examples=await (await f.request('/api/geography/temporal/snapshot?year=1000&examples=1')).json();assert.equal(examples.records.length,3);assert.equal((await (await f.request('/api/geography/temporal/snapshot?year=1100')).json()).records.length,0);
   const replay=await (await f.post(input)).json();assert.equal(replay.duplicate,true);assert.equal(replay.revision,receipt.revision);assert.deepEqual(replay.counts,receipt.counts);
   assert.equal((await f.post({...input,memberships:[membership('worker:parent/old')]})).status,409);
   const correction={ingestion_id:'worker-correction',memberships:[membership('worker-parent-new')],retirements:[{id:'worker-withdrawal',collection:'memberships',target_id:'worker:parent/old',replacement_id:'worker-parent-new',source_id:'worker-history',reason:'Synthetic corrected evidence'}]};assert.equal((await f.post(correction)).status,200);
   const evidence=await f.request('/api/geography/temporal/evidence/memberships/'+encodeURIComponent('worker:parent/old'));assert.equal(evidence.status,200);const retained=await evidence.json();assert.equal(retained.status,'superseded');assert.equal(retained.claim.parent_id,null);assert.equal(retained.withdrawals[0].replacement_id,'worker-parent-new');assert.equal((await f.request('/api/geography/temporal/evidence/memberships/missing')).status,404);
   const withdrawals=await (await f.request('/api/geography/temporal/snapshot?year=-3000&stream=withdrawals')).json();assert.equal(withdrawals.withdrawals[0].target_id,'worker:parent/old');const winners=await (await f.request('/api/geography/temporal/snapshot?year=1000')).json();assert.equal(winners.revision,withdrawals.revision);assert.ok(winners.records.some(row=>row.id==='worker-parent-new'));assert.ok(!winners.records.some(row=>row.id==='worker:parent/old'));
   const scalar=await (await f.request('/api/map/snapshot?year=1000')).json();assert.equal(scalar.revision,winners.revision);assert.ok(scalar.records.some(row=>row.attribute==='population'&&row.value===42));
  }finally{await f.close();}
 });
 test(`Worker dated geography rejects unsafe writes without changing scalar/media routes on actual ${backend}`,async()=>{
  const f=await fixture(backend);try{
   const payload={expected_geography:pin,memberships:[membership('denied')]};
   assert.equal((await f.request('/api/geography/temporal/import',{method:'POST',headers:{Origin:'https://other.example','Content-Type':'application/json'},body:payload})).status,403);
   assert.equal((await f.request('/api/geography/temporal/import',{method:'POST',headers:{'Content-Type':'text/plain'},body:payload})).status,415);
   assert.equal((await f.request('/api/geography/temporal/import',{method:'POST',headers:{'Content-Type':'application/json'},body:'{'})).status,400);
   assert.equal((await f.request('/api/geography/temporal/import',{method:'POST',headers:{'Content-Type':'application/json'},body:' '.repeat(1048577)})).status,413);
   assert.equal((await f.post({memberships:[membership('wrong-pin')],expected_geography:{...pin,footprints_sha256:'f'.repeat(64)}})).status,409);
   for(const query of ['year=0','year=2027','year=-3001','year=1000&stream=unsupported'])assert.equal((await f.request('/api/geography/temporal/snapshot?'+query)).status,400);
   const readOnly={...f.env,ATLAS_READ_ONLY:'1'};const denied=await f.post({memberships:[membership('maintenance-denied')]},readOnly);assert.equal(denied.status,503);assert.equal((await denied.json()).retryable,true);assert.equal((await f.request('/api/geography/temporal/snapshot?year=1000',{},readOnly)).status,200);
   assert.equal((await f.DB.prepare('SELECT count(*) n FROM atlas_geographic_membership_records').first()).n,0);
   const mediaParameters=new URLSearchParams({id:'worker-audio',source_id:'worker-history',name:'Fixture recording',license:'CC0',attribution:'Isolated fixture source',metadata:JSON.stringify({synthetic:true})});const bytes=new Uint8Array([82,73,70,70]);
   assert.equal((await f.request('/api/media/upload?'+mediaParameters,{method:'POST',headers:{Origin:origin,'Content-Type':'audio/wav'},body:bytes},readOnly)).status,503);
   assert.equal((await f.request('/api/media/upload?'+mediaParameters,{method:'POST',headers:{Origin:origin,'Content-Type':'audio/wav'},body:bytes})).status,200);
   const media=await f.request('/api/media/worker-audio?metadata=1');assert.equal(media.status,200);assert.equal((await media.json()).source_id,'worker-history');assert.deepEqual(new Uint8Array(await (await f.request('/api/media/worker-audio')).arrayBuffer()),bytes);
   assert.equal(await (await f.request('/')).text(),'static fixture');assert.equal((await f.request('/api/unknown')).status,404);
  }finally{await f.close();}
 });
}
