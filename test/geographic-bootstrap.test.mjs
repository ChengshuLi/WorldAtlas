import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import {createHash} from 'node:crypto';
import {bootstrapConcurrency,publishGeographicReleases,retainGeographicArchives} from '../scripts/bootstrap-geographic-release.mjs';
import {importBatch} from '../hosted/records.js';
import {stageGeographicRelease,finalizeGeographicRelease,geographicRelease,geographicMembershipHash,geographicLocationIdsHash,geographicChangesHash} from '../hosted/geographic-releases.js';
class D1{
 constructor(){this.sqlite=new DatabaseSync(':memory:');this.sqlite.exec('PRAGMA foreign_keys=ON');for(const f of fs.readdirSync(new URL('../drizzle/',import.meta.url)).filter(f=>f.endsWith('.sql')).sort())this.sqlite.exec(fs.readFileSync(new URL(`../drizzle/${f}`,import.meta.url),'utf8'));}
 prepare(sql){const sqlite=this.sqlite;let args=[];return {bind(...values){args=values;return this;},async all(){return {results:sqlite.prepare(sql).all(...args)};},async first(){return sqlite.prepare(sql).get(...args)??null;},run(){return {meta:{changes:Number(sqlite.prepare(sql).run(...args).changes)}};}};}
 async batch(statements){this.sqlite.exec('BEGIN IMMEDIATE');try{const result=statements.map(s=>s.run());this.sqlite.exec('COMMIT');return result;}catch(error){this.sqlite.exec('ROLLBACK');throw error;}}
}
const tiers=['continent','subcontinent','region','area','province','location'];
async function fixture({visibleStaged=true}={}){
 const db=new D1();await importBatch(db,JSON.parse(fs.readFileSync(new URL('../data/hosted-type-catalog.json',import.meta.url))));
 const entities=Array.from({length:6},(_,n)=>tiers.map((kind,i)=>({id:`${kind}:${n}`,kind,name:`Original ${kind} ${n}`,parent_id:i?`${tiers[i-1]}:${n}`:null}))).flat();
 const members=entities.map(e=>({entity_id:e.id,kind:e.kind,parent_id:e.parent_id,reference_name:e.name,active:1,source_id:'reference',evidence:{source:'test-only'}}));
 const release={id:'test:reference',version:1,source_id:'reference',reference_date:'2026-10-01',membership_sha256:await geographicMembershipHash(members),location_ids_sha256:await geographicLocationIdsHash(members),changes_sha256:await geographicChangesHash([]),hierarchy_sha256:'a'.repeat(64),footprints_sha256:'b'.repeat(64),expected_counts:Object.fromEntries(tiers.map(t=>[t,6]))};
 const payloads=new Map(),parts=[];const part=(name,payload,route='/api/geography/stage')=>{payloads.set(name,payload);parts.push({path:name,route});};
 part('sources.json',{sources:[{id:'reference',name:'QA reference',license:'CC0 test-only',vintage:'2026',supported_from:2026,supported_to:2027,status:'reference'},{id:'history',name:'QA observed history',license:'CC0 test-only',vintage:'1000',supported_from:1000,supported_to:1100,status:'historical'}],ingestion_id:'sources'},'/api/records/import');
 for(const tier of tiers)part(`entities-${tier}-0.json`,{entities:entities.filter(e=>e.kind===tier),ingestion_id:`entities:${tier}`},'/api/records/import');
 part('release-1.json',{release,ingestion_id:'release'});for(let n=0;n<members.length;n+=6)part(`1-memberships-${n}.json`,{release_id:release.id,memberships:members.slice(n,n+6),ingestion_id:`members:${n}`});
 const calls=[];let inFlight=0,maxInFlight=0;
 const batch=async p=>{calls.push(p.path);inFlight++;maxInFlight=Math.max(maxInFlight,inFlight);try{await new Promise(resolve=>setImmediate(resolve));return await(p.route==='/api/records/import'?importBatch(db,payloads.get(p.path)):stageGeographicRelease(db,payloads.get(p.path)));}finally{inFlight--;}};
 const request=async(route,options)=>{const url=new URL(route,'https://example.invalid');if(url.pathname==='/api/geography/release')return Response.json(await geographicRelease(db,url.searchParams.get('release_id'),{includeStaged:visibleStaged}));if(url.pathname==='/api/geography/finalize')return Response.json(await finalizeGeographicRelease(db,JSON.parse(options.body).release_id));throw Error('Unexpected test route');};
 return {db,release,manifest:{batches:parts,releases:[release]},batch,request,calls,maxInFlight:()=>maxInFlight};
}

test('bounded import concurrency defaults to six and accepts only one through eight',()=>{assert.equal(bootstrapConcurrency('6'),6);assert.equal(bootstrapConcurrency(8),8);assert.equal(bootstrapConcurrency(1),1);for(const value of ['0','9','3.5','06','six','',null])assert.throws(()=>bootstrapConcurrency(value),/integer from 1 to 8/);});

test('stage then finalize publishes atomically without replaying ownership batches',async()=>{
 const f=await fixture({visibleStaged:false});try{
  const staged=await publishGeographicReleases({...f,mode:'stage'});
  assert.equal(staged[0].status,'staged');assert.equal(staged[0].public_readback_verified,false);
  assert.equal(await geographicRelease(f.db,f.release.id),null);
  assert.equal((await geographicRelease(f.db,f.release.id,{includeStaged:true})).status,'staged');
  const count=f.calls.length;
  const published=await publishGeographicReleases({...f,mode:'finalize'});
  assert.equal(published[0].id,f.release.id);assert.equal(f.calls.length,count);
  assert.equal((await geographicRelease(f.db,f.release.id)).status,'published');
  await assert.rejects(publishGeographicReleases({...f,mode:'incorrect'}),/Unknown/);
 }finally{f.db.sqlite.close();}
});

test('append-only source batches import before newly registered geography and retain the original source bytes',async()=>{
 const f=await fixture();try{
  const original=f.manifest.batches.find(p=>p.path==='sources.json'),later={path:'sources-3.json',route:'/api/records/import'};
  const manifest={...f.manifest,sources_batches:['sources.json','sources-3.json'],batches:[...f.manifest.batches,later]};
  let newSourceImported=false;
  await publishGeographicReleases({...f,manifest,batch:async part=>{
   if(part.path===later.path){await importBatch(f.db,{sources:[{id:'later-source',name:'Later inspected reference',license:'CC0 test-only',vintage:'2026',status:'reference',supported_from:2026,supported_to:2027}]});newSourceImported=true;return;}
   if(part.path.startsWith('entities-'))assert.equal(newSourceImported,true);
   return f.batch(part);
  }});
  assert.equal(f.manifest.batches.find(p=>p.path==='sources.json'),original);
  assert.equal(f.db.sqlite.prepare("SELECT count(*) n FROM atlas_sources WHERE id IN ('reference','later-source')").get().n,2);
  await assert.rejects(publishGeographicReleases({...f,manifest:{...manifest,sources_batches:['sources.json','sources.json']}}),/duplicate/);
 }finally{f.db.sqlite.close();}
});

test('interrupted real-D1 staging resumes explicit or hidden staged releases without rewriting history',async()=>{
 for(const visibleStaged of [true,false]){const f=await fixture({visibleStaged});try{
  let interrupted=false;await assert.rejects(publishGeographicReleases({...f,concurrency:1,batch:async p=>{if(p.path==='1-memberships-12.json'&&!interrupted){interrupted=true;throw Error('Interrupted fixture transport');}return f.batch(p);}}),/Interrupted/);
  assert.equal((await geographicRelease(f.db,f.release.id,{includeStaged:true})).status,'staged');assert.equal(f.db.sqlite.prepare('SELECT count(*) n FROM atlas_geographic_memberships').get().n,12);
  await importBatch(f.db,{records:[{id:'kept-history',location_id:'location:0',attribute:'population',value:42,valid_from:1000,valid_to:1100,source_id:'history'}]});
  const snapshot=table=>JSON.stringify(f.db.sqlite.prepare(`SELECT * FROM ${table} ORDER BY id`).all()),records=snapshot('atlas_attribute_records'),entities=snapshot('atlas_entities'),sources=snapshot('atlas_sources');
  const result=await publishGeographicReleases({...f,concurrency:6});assert.equal(result[0].id,f.release.id);assert.equal((await geographicRelease(f.db,f.release.id)).status,'published');assert.equal(f.db.sqlite.prepare('SELECT count(*) n FROM atlas_geographic_memberships').get().n,36);assert.equal(snapshot('atlas_attribute_records'),records);assert.equal(snapshot('atlas_entities'),entities);assert.equal(snapshot('atlas_sources'),sources);assert.equal(f.maxInFlight(),6);assert.deepEqual(f.db.sqlite.prepare('PRAGMA foreign_key_check').all(),[]);
  const before=snapshot('atlas_ingestions'),start=f.calls.length;await publishGeographicReleases({...f,concurrency:6});assert.equal(snapshot('atlas_ingestions'),before);assert.ok(f.calls.slice(start).every(v=>v==='sources.json'||v.startsWith('entities-')),'Published release must skip all staging and finalization work');
 }finally{f.db.sqlite.close();}}
});

test('a mismatched existing staged or published manifest blocks all geographic staging before writes',async()=>{
 const f=await fixture();try{
  for(const p of f.manifest.batches.filter(p=>p.path==='sources.json'||p.path.startsWith('entities-')))await f.batch(p);await f.batch(f.manifest.batches.find(p=>p.path==='release-1.json'));
  for(const state of ['staged','published']){if(state==='published')await publishGeographicReleases({...f,concurrency:6});const before=JSON.stringify(f.db.sqlite.prepare('SELECT * FROM atlas_geographic_memberships').all());
  for(const key of ['membership_sha256','footprints_sha256','hierarchy_sha256','location_ids_sha256','changes_sha256']){const altered={...f.manifest,releases:[{...f.release,[key]:'c'.repeat(64)}]},start=f.calls.length;await assert.rejects(publishGeographicReleases({...f,manifest:altered,concurrency:6}),new RegExp(`${key} mismatch`));assert.ok(f.calls.slice(start).every(v=>v==='sources.json'||v.startsWith('entities-')));assert.equal(JSON.stringify(f.db.sqlite.prepare('SELECT * FROM atlas_geographic_memberships').all()),before);}
  }
 }finally{f.db.sqlite.close();}
});

test('identical archive bytes upload once with a stable first-sorted name and preserve every receipt alias across retries',async()=>{
 const contents=new Map([['data/before-boundaries.json.gz',Buffer.from('same compressed source bytes')],['data/after-boundaries.json.gz',Buffer.from('same compressed source bytes')],['data/other.json',Buffer.from('{"test":"distinct evidence"}')]]),stored=new Map();let calls=0;
 const request=async(route,options)=>{if(!route.startsWith('/api/media/upload')){const id=decodeURIComponent(new URL(route,'https://example.invalid').pathname.slice('/api/media/'.length));return stored.has(id)?Response.json(stored.get(id)):new Response(null,{status:404});}calls++;const parameters=new URL(route,'https://example.invalid').searchParams,digest=createHash('sha256').update(options.body).digest('hex'),id=parameters.get('id'),metadata={id,name:parameters.get('name'),source_id:parameters.get('source_id'),mime:options.headers['Content-Type'],sha256:digest,bytes:options.body.length};
  if(stored.has(id))assert.deepEqual(stored.get(id),metadata,'Retries must retain immutable media metadata');else stored.set(id,metadata);
  return Response.json(metadata);
 };
 const options={archiveFiles:new Set(contents.keys()),sourceId:'reference',request,readArchive:file=>contents.get(file)},receipt=await retainGeographicArchives(options);assert.equal(calls,2);assert.equal(receipt.length,3);const a=receipt.find(r=>r.path==='data/after-boundaries.json.gz'),b=receipt.find(r=>r.path==='data/before-boundaries.json.gz');assert.equal(a.id,b.id);assert.equal(a.sha256,b.sha256);assert.equal(a.bytes,b.bytes);assert.equal(a.canonical_path,'data/after-boundaries.json.gz');assert.equal(b.canonical_path,a.canonical_path);assert.equal(stored.get(a.id).name,'after-boundaries.json.gz');assert.deepEqual(new Set(receipt.map(r=>r.path)),new Set(contents.keys()));
 const retry=await retainGeographicArchives({...options,sourceId:'later-reference',archiveFiles:[...contents.keys()].reverse()});assert.deepEqual(retry,receipt);assert.equal(calls,2,'Later releases reuse exact existing objects without rewriting immutable source metadata');
 await assert.rejects(retainGeographicArchives({...options,request:async()=>Response.json({sha256:'incorrect',bytes:1})}),/does not match/);
});
