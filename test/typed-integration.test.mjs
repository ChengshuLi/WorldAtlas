import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import {createLocalPostgres} from '../scripts/verify-postgres-schema.mjs';
import {importBatch} from '../hosted/records.js';
import {stageGeographicRelease,finalizeGeographicRelease,geographicMembershipHash,geographicLocationIdsHash,geographicChangesHash} from '../hosted/geographic-releases.js';
import {typedCapabilities,typedSourcePins,importTypedBatch} from '../hosted/typed-observations.js';
import {observationContract} from '../src/observation-modules.js';
import {decodeTypedRow,resolveTypedSnapshot} from '../src/typed-snapshot.js';
import {exportStorageMarkerV3} from '../hosted/storage-export-v3.js';

class D1{
 constructor({forward=true}={}){this.sqlite=new DatabaseSync(':memory:');for(const file of fs.readdirSync(new URL('../drizzle/',import.meta.url)).filter(file=>file.endsWith('.sql')&&(forward||/^000[0-7]_/.test(file))).sort())this.sqlite.exec(fs.readFileSync(new URL('../drizzle/'+file,import.meta.url),'utf8'));}
 prepare(sql){const sqlite=this.sqlite;let args=[];return {bind(...values){args=values;return this;},async first(){return sqlite.prepare(sql).get(...args)??null;},async all(){return {results:sqlite.prepare(sql).all(...args)};},run(){return {meta:{changes:Number(sqlite.prepare(sql).run(...args).changes)}};}};}
 async batch(statements){this.sqlite.exec('BEGIN IMMEDIATE');try{const result=statements.map(statement=>statement.run());this.sqlite.exec('COMMIT');return result;}catch(error){this.sqlite.exec('ROLLBACK');throw error;}}
}
const kinds=['continent','subcontinent','region','area','province','location'];
const pins={release_id:'synthetic-typed-release',hierarchy_sha256:'a'.repeat(64),footprints_sha256:'b'.repeat(64)};
async function fixture(backend){
 const pg=backend==='postgres'?await createLocalPostgres():null,db=pg?.db??new D1();
 if(pg)for(const file of fs.readdirSync(new URL('../postgres/migrations/',import.meta.url)).sort())await pg.engine.exec(fs.readFileSync(new URL('../postgres/migrations/'+file,import.meta.url),'utf8'));
 try{
  await importBatch(db,JSON.parse(fs.readFileSync(new URL('../data/hosted-type-catalog.json',import.meta.url))));
  await importBatch(db,JSON.parse(fs.readFileSync(new URL('../data/typed-entity-types-v1.json',import.meta.url))));
  const entities=Array.from({length:6},(_,c)=>kinds.map((kind,i)=>({id:`${kind}-${c}`,kind,name:'Synthetic '+kind,parent_id:i?`${kinds[i-1]}-${c}`:null}))).flat();
  await importBatch(db,{sources:['example','historical','reference'].map(status=>({id:status,name:'Synthetic '+status,url:'https://example.org/isolated-typed-fixture',license:'CC0 test-only',vintage:'2026',supported_from:status==='reference'?2026:-3000,supported_to:2027,status,metadata:{original_archive_sha256:'d'.repeat(64),scope:'synthetic controls only; no factual approval'}})),entities:[...entities,{id:'port',kind:'port',name:'Synthetic port',source_id:'example',valid_from:-100,valid_to:2027,is_example:1}]});
  const memberships=entities.map(row=>({entity_id:row.id,kind:row.kind,parent_id:row.parent_id,reference_name:row.name,active:1,source_id:'reference',evidence:{synthetic:true}}));
  await stageGeographicRelease(db,{release:{id:pins.release_id,source_id:'reference',version:1,reference_date:'2026-10-03',hierarchy_sha256:pins.hierarchy_sha256,footprints_sha256:pins.footprints_sha256,membership_sha256:await geographicMembershipHash(memberships),location_ids_sha256:await geographicLocationIdsHash(memberships),changes_sha256:await geographicChangesHash([]),expected_counts:Object.fromEntries(kinds.map(kind=>[kind,6]))},memberships});await finalizeGeographicRelease(db,pins.release_id);
  const rawSources=(await db.prepare('SELECT * FROM atlas_sources ORDER BY id').all()).results,contract=await observationContract();
  const envelope=async(rows,extra={})=>({version:1,registry_sha256:contract.registry_sha256,expected_geography:pins,source_pins:await typedSourcePins(rawSources.filter(source=>new Set(Object.values(rows).flat().map(row=>row.source_id)).has(source.id))),examples:true,...rows,...extra});
  return {db,pg,envelope,contract,close:()=>pg?pg.close():db.sqlite.close()};
 }catch(error){await (pg?pg.close():Promise.resolve(db.sqlite.close()));throw error;}
}
async function both(callback){for(const backend of ['sqlite','postgres']){const f=await fixture(backend);try{await callback(f,backend);}finally{await f.close();}}}
const observation=(id,extra={})=>({id,subject_id:'location-0',subject_kind:'location',field_id:'atlas.marine-contact',value:false,valid_from:-100,valid_to:-99,source_id:'example',is_example:1,...extra});
const rejection=error=>[400,409].includes(error.status);

test('typed imports preserve raw zero/false/unknown, exact retries and BC/AD shared snapshot semantics on actual SQLite/PostgreSQL',()=>both(async f=>{
 const metadata={measurement:{unit:'percent',definition:'Synthetic adult literacy test',cohort:'age-15-plus',period:{from:-100,to:-99}}},rawMetadata=JSON.stringify(metadata,null,2);
 const payload=await f.envelope({observations:[observation('false'),observation('zero',{field_id:'atlas.adult-literacy',value:0,metadata,original_json:{value:'0.00',metadata:rawMetadata}}),observation('unknown',{subject_id:'location-1',value:null,status:'unresolved'})],feature_links:[{id:'port-link',relationship_type:'atlas.port-location',source_entity_id:'port',target_entity_id:'location-0',source_id:'example',is_example:1,valid_from:-100,valid_to:-99,metadata:{retained:'synthetic link'}}]});
 assert.equal((await typedCapabilities(f.db)).typed_observations,1);
 const result=await importTypedBatch(f.db,payload);assert.equal(result.duplicate,false);assert.equal((await importTypedBatch(f.db,payload)).duplicate,true);
 const zero=await f.db.prepare("SELECT * FROM atlas_typed_observations WHERE id='zero'").first();assert.equal(zero.value,'0.00');assert.equal(zero.metadata,rawMetadata);
 const sources=(await f.db.prepare('SELECT * FROM atlas_sources').all()).results.map(row=>({...row,metadata:JSON.parse(row.metadata)})),entities=(await f.db.prepare('SELECT * FROM atlas_entities').all()).results.map(row=>({...row,metadata:JSON.parse(row.metadata)}));
 const observations=(await f.db.prepare('SELECT * FROM atlas_typed_observations ORDER BY id').all()).results.map(row=>decodeTypedRow('observations',row)),links=(await f.db.prepare('SELECT * FROM atlas_typed_feature_links').all()).results.map(row=>decodeTypedRow('feature_links',row));
 const snapshot={version:1,registry_sha256:f.contract.registry_sha256,sources,entities,observations,feature_links:links,retirements:[]};
 const selected=await resolveTypedSnapshot(snapshot,-100,{examples:true});assert.equal(selected.observations.find(row=>row.field_id==='atlas.adult-literacy').value,0);assert.equal(selected.observations.find(row=>row.evidence.id==='false').value,false);assert.equal(selected.observations.find(row=>row.evidence.id==='unknown').status,'example');assert.equal(selected.feature_links.length,1);
 assert.equal((await resolveTypedSnapshot(snapshot,-100)).observations.length,0);assert.equal((await resolveTypedSnapshot(snapshot,-99,{examples:true})).observations.length,0);assert.equal((await resolveTypedSnapshot(snapshot,1,{examples:true})).feature_links.length,0);await assert.rejects(resolveTypedSnapshot(snapshot,0));
 const before=await exportStorageMarkerV3(f.db);await assert.rejects(importTypedBatch(f.db,{...payload,ingestion_id:result.ingestion_id,observations:[observation('different')]}),rejection);assert.deepEqual(await exportStorageMarkerV3(f.db),before);
}));

test('typed API rejects missing approval, bad source/registry/raw pins, unsupported labels and missing correction/derivation identities without partial writes',()=>both(async f=>{
 const base=await f.envelope({observations:[observation('candidate')]});
 const bad=[
  {...base,observations:[observation('factual',{source_id:'historical',is_example:0})],source_pins:await typedSourcePins((await f.db.prepare("SELECT * FROM atlas_sources WHERE id='historical'").all()).results)},
  {...base,source_pins:[{id:'example',sha256:'e'.repeat(64)}]},
  {...base,registry_sha256:'f'.repeat(64)},
  {...base,observations:[observation('raw-mismatch',{original_json:{value:'true'}})]},
  {...base,observations:[observation('unresolved-nonnull',{status:'unresolved'})]},
  {...base,observations:[observation('derived-missing',{method:'derived',metadata:{derivation_input_ids:['absent']}})]},
  {...base,observations:[observation('year-zero',{valid_from:0,valid_to:1})]},
  {...base,examples:false},
 ];
 const before=await exportStorageMarkerV3(f.db);for(const payload of bad){await assert.rejects(importTypedBatch(f.db,payload),rejection);assert.deepEqual(await exportStorageMarkerV3(f.db),before);}
 await importTypedBatch(f.db,base);
 const incomplete=await f.envelope({retirements:[{id:'withdrawal',collection:'observations',target_id:'candidate',replacement_id:'absent',source_id:'example',reason:'Rejected missing correction'}]});const installed=await exportStorageMarkerV3(f.db);await assert.rejects(importTypedBatch(f.db,incomplete),rejection);assert.deepEqual(await exportStorageMarkerV3(f.db),installed);
}));

test('legacy or altered installed schemas never advertise typed capabilities',async()=>{
 const legacy=new D1({forward:false}),current=new D1();try{assert.equal((await typedCapabilities(legacy)).typed_observations,0);current.sqlite.exec('DROP TRIGGER atlas_typed_retirements_collision');assert.equal((await typedCapabilities(current)).typed_observations,0);}finally{legacy.sqlite.close();current.sqlite.close();}
});

test('actual Worker typed routes enforce transport/maintenance and keep atomic corrections, raw source pins and snapshot paging consistent',()=>both(async f=>{
 const {default:worker}=await import('../hosted/worker.js');
 const request=async(path,options={})=>worker.fetch(new Request('https://example.org'+path,options),{DB:f.db,ASSETS:{fetch:()=>new Response('synthetic assets')}},{});
 const post=payload=>request('/api/typed/v1/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
 const original=await f.envelope({observations:[observation('old',{value:true}),observation('second',{subject_id:'location-1'})]});assert.equal((await post(original)).status,200);
 const retirement={id:'retirement',collection:'observations',target_id:'old',replacement_id:'new',source_id:'example',reason:'Synthetic same-subject correction',metadata:{original:'retained withdrawal bytes'},original_json:{metadata:' { "original" : "retained withdrawal bytes" } '}};
 const correction=await f.envelope({observations:[observation('new')],retirements:[retirement]});assert.equal((await post(correction)).status,200);assert.equal((await post(correction)).status,200);
 assert.equal((await f.db.prepare("SELECT value FROM atlas_typed_observations WHERE id='old'").first()).value,'true');assert.equal((await f.db.prepare("SELECT metadata FROM atlas_typed_retirements WHERE id='retirement'").first()).metadata,retirement.original_json.metadata);
 const first=await (await request('/api/typed/v1/snapshot?year=-100&examples=1&limit=1')).json();assert.equal(first.rows.length,1);assert.ok(first.next_cursor);assert.equal(first.total,3);assert.ok(first.sources[0].original_metadata_json);assert.equal(first.source_pins.length,1);
 const next=await (await request('/api/typed/v1/snapshot?year=-100&examples=1&limit=1&cursor='+encodeURIComponent(first.next_cursor))).json();assert.equal(next.fingerprint,first.fingerprint);assert.notEqual(next.rows[0].id,first.rows[0].id);
 const withdrawals=await (await request('/api/typed/v1/snapshot?year=-100&examples=1&stream=retirements')).json();assert.equal(withdrawals.rows[0].target_id,'old');assert.equal(withdrawals.rows[0].original_json.metadata,retirement.original_json.metadata);
 assert.equal((await request('/api/typed/v1/registry')).status,200);
 const before=await exportStorageMarkerV3(f.db);const conflict=await f.envelope({retirements:[{...retirement,id:'conflicting-retirement',reason:'Different provenance'}]});assert.equal((await post(conflict)).status,409);assert.deepEqual(await exportStorageMarkerV3(f.db),before);
 const crossed=await f.envelope({observations:[observation('wrong-subject',{subject_id:'location-2'})],retirements:[{...retirement,id:'cross-subject',target_id:'new',replacement_id:'wrong-subject'}]});assert.equal((await post(crossed)).status,400);assert.deepEqual(await exportStorageMarkerV3(f.db),before);
 const later=await f.envelope({observations:[observation('later',{subject_id:'location-3'})]});assert.equal((await post(later)).status,200);assert.equal((await request('/api/typed/v1/snapshot?year=-100&examples=1&cursor='+encodeURIComponent(first.next_cursor))).status,409);
 const readOnly=await worker.fetch(new Request('https://example.org/api/typed/v1/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(later)}),{DB:f.db,ATLAS_READ_ONLY:'1'},{});assert.equal(readOnly.status,503);
 assert.equal((await request('/api/typed/v1/import',{method:'POST',headers:{'Content-Type':'text/plain'},body:'{}'})).status,415);assert.equal((await request('/api/typed/v1/import',{method:'POST',headers:{'Content-Type':'application/json',Origin:'https://other.example'},body:'{}'})).status,403);
}));

test('legacy23-table projections require the complete known schema and current maintenance clients refuse them as complete backups',()=>both(async f=>{
 const {legacyStorageMarker,legacyStoragePage,legacyStorageCatalog}=await import('../hosted/storage-export-compat.js');
 const {exportStorageMarkerV2}=await import('../hosted/storage-export-v2.js');
 const {exportHostedStorageV2}=await import('../scripts/export-hosted-storage-v2.mjs');
 await assert.rejects(exportStorageMarkerV2(f.db),error=>error.status===503);
 const marker=await legacyStorageMarker(f.db);assert.equal(marker.version,2);assert.equal(Object.keys(marker.counts).length,23);assert.equal(marker.legacy_projection.complete,false);assert.equal(marker.legacy_projection.required_complete_export_version,3);
 const page=await legacyStoragePage(f.db,'sources',{limit:1});assert.equal(page.records.length,1);assert.ok(page.next_cursor);const next=await legacyStoragePage(f.db,'sources',{limit:1,cursor:page.next_cursor});assert.equal(next.records.length,1);assert.notEqual(next.records[0].id,page.records[0].id);assert.equal(page.snapshot_marker.legacy_projection.complete,false);
 const catalog=await legacyStorageCatalog(f.db);assert.equal(catalog.legacy_projection.complete,false);
 const {default:worker}=await import('../hosted/worker.js');const response=await worker.fetch(new Request('https://example.org/api/storage/v2/catalog'),{DB:f.db},{});assert.equal(response.headers.get('X-Atlas-Complete-Export-Version'),'3');assert.equal(await response.text(),JSON.stringify(catalog.catalog));
 const {default:os}=await import('node:os'),{default:path}=await import('node:path');const directory=fs.mkdtempSync(path.join(os.tmpdir(),'typed-legacy-export-'));
 try{await assert.rejects(exportHostedStorageV2({origin:'https://example.org',output:path.join(directory,'capture'),token:'isolated fixture token',fetcher:async()=>Response.json({...marker,read_only:true})}),/labelled legacy projection/);}finally{fs.rmSync(directory,{recursive:true,force:true});}
 if(f.pg)await f.pg.engine.exec('DROP TRIGGER atlas_typed_retirements_immutable ON atlas_typed_retirements');else f.db.sqlite.exec('DROP TRIGGER atlas_typed_retirements_collision');
 await assert.rejects(legacyStorageMarker(f.db),error=>error.status===503);
}));

test('derivation closures reject example promotion, cycles and ambiguous roots while example-only acyclic chains remain available under the paused factual gate',()=>both(async f=>{
 const approved={version:2,ready_for_location_attributes:true,macro_boundaries:{approved:true,approval_issue:1,approval_evidence:'synthetic-only',boundary_sha256:'c'.repeat(64)},regions:[{region_id:'synthetic',semantic_complete:true,approval_issue:1,approval_evidence:'synthetic-only',macro_boundary_sha256:'c'.repeat(64),approved_release:pins,approved_location_ids:['location-0','location-1'],approved_subject_ids:['location-0','location-1']}]};
 // This fixture is not a geographic approval or a production operation.
 await importTypedBatch(f.db,await f.envelope({observations:[observation('retained-example')]}));
 await importBatch(f.db,{expected_geography:pins,records:[{id:'legacy-example',location_id:'location-0',attribute:'population',value:0,source_id:'example',is_example:1,valid_from:-100,valid_to:-99}]});
 const raw=(await f.db.prepare('SELECT * FROM atlas_sources ORDER BY id').all()).results;
 const withSources=async(rows,sourceIds,extra={})=>({...await f.envelope(rows),source_pins:await typedSourcePins(raw.filter(row=>sourceIds.includes(row.id))),...extra});
 const derived=(id,inputs,extra={})=>observation(id,{method:'derived',metadata:{derivation_input_ids:inputs},...extra});
 const factual=(id,inputs)=>derived(id,inputs,{source_id:'historical',is_example:0});
 const rejected=[
  [await withSources({observations:[factual('promoted-typed',['retained-example'])]},['example','historical'],{examples:false,region_ids:['synthetic']}),/cannot consume example/],
  [await withSources({observations:[factual('promoted-legacy',['legacy-example'])]},['example','historical'],{examples:false,region_ids:['synthetic']}),/cannot consume example/],
  [await withSources({observations:[observation('same-batch-example'),factual('promoted-batch',['same-batch-example'])]},['example','historical'],{region_ids:['synthetic']}),/cannot consume example/],
  [await f.envelope({observations:[derived('cycle-a',['cycle-b']),derived('cycle-b',['cycle-a'])]}),/Circular derivation/],
 ];
 const before=await exportStorageMarkerV3(f.db);
 for(const [payload,message] of rejected){await assert.rejects(importTypedBatch(f.db,payload,{gate:approved}),message);assert.deepEqual(await exportStorageMarkerV3(f.db),before);}
 const positive=await withSources({observations:[derived('example-child',['retained-example'],{subject_id:'location-1'}),derived('example-grandchild',['example-child'],{subject_id:'location-2'}),derived('legacy-child',['legacy-example'],{subject_id:'location-3'})]},['example']);
 await assert.rejects(importTypedBatch(f.db,{...positive,examples:false}),/explicit batch opt-in/);assert.deepEqual(await exportStorageMarkerV3(f.db),before);
 assert.equal((await importTypedBatch(f.db,positive)).duplicate,false);
 for(const id of ['example-child','example-grandchild','legacy-child'])assert.equal((await f.db.prepare('SELECT is_example FROM atlas_typed_observations WHERE id=?').bind(id).first()).is_example,1);
 const {default:worker}=await import('../hosted/worker.js');
 const response=await worker.fetch(new Request('https://example.org/api/typed/v1/snapshot?year=-100&examples=1'),{DB:f.db},{});assert.equal(response.status,200);assert.equal((await response.json()).rows.length,4);
 const factualPayload=await withSources({observations:[observation('still-paused',{source_id:'historical',is_example:0})]},['historical']);
 const marker=await exportStorageMarkerV3(f.db);await assert.rejects(importTypedBatch(f.db,factualPayload),/paused/);assert.deepEqual(await exportStorageMarkerV3(f.db),marker);
}));
