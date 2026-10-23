import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {DatabaseSync} from 'node:sqlite';
import {createLocalPostgres} from '../scripts/verify-postgres-schema.mjs';
import {compileResearchInput,prepareResearchBundle,researchHash,researchJSON,settlementEstimateSource,typedResearchEndpoint} from '../scripts/prepare-research-bundle.mjs';
import {readResearchBundle,importResearchBundle} from '../scripts/import-research-bundle.mjs';
import {importBatch} from '../hosted/records.js';
import {importTypedBatch,typedSnapshotPage,typedSourcePins} from '../hosted/typed-observations.js';
import {observationContract} from '../src/observation-modules.js';
import {normalizeTypedEvidence,resolveTypedSnapshot,decodeTypedRow} from '../src/typed-snapshot.js';
import {typedRequiresGeography,validateTypedGeography} from '../src/typed-derivations.js';
const inputURL=new URL('../data/settlement-estimates.json',import.meta.url),original=fs.readFileSync(inputURL),input=JSON.parse(original);
const compiled=compileResearchInput(input),observations=compiled.batches.flatMap(batch=>batch.payload.observations??[]);
const context={sources:[settlementEstimateSource],entities:input.entities};

test('all 9301 original facts retain exact identity/date/value/source with no geography, examples, interpolation or extra subject',async()=>{
 assert.equal(researchHash(original),'8c7cb39cfce591b87eedeb0eddfbd21e0cabdce6a53d39023409e633e617ce0d');
 assert.deepEqual(compiled.counts,{sources:1,observations:9301,settlement_subjects:582});assert.equal(compiled.geography,null);assert.equal(compiled.batches.length,48);
 assert.ok(compiled.batches.every(batch=>batch.rows<=200&&batch.bytes.length<=1048576));
 const byId=new Map(observations.map(row=>[row.id,row]));assert.equal(byId.size,input.entity_history.length);
 for(const original of input.entity_history){const row=byId.get(original.id);assert.equal(row.subject_id,original.entity_id);assert.equal(row.subject_kind,'settlement');assert.equal(row.field_id,'settlement.population');assert.equal(row.value,original.value.population);assert.equal(row.valid_from,original.valid_from);assert.equal(row.valid_to,original.valid_to);assert.equal(row.method,'estimate');assert.equal(row.status,'estimate');assert.equal(row.is_example,0);assert.equal(row.source_id,settlementEstimateSource.id);assert.deepEqual(row.metadata.original_record,original);assert.equal(row.metadata.language,'und');assert.equal(row.metadata.name_role,'preferred');assert.equal(row.metadata.un_edition,null);assert.equal(row.metadata.estimate_projection_cutoff,null);assert.equal(row.metadata.estimate_or_projection,'not_disambiguated_by_retained_source');}
 const contract=await observationContract(),snapshot={version:1,registry_sha256:contract.registry_sha256,...context,observations,feature_links:[],retirements:[]};
 assert.ok(contract.registries.cc6aae6c18099d3e776c73ee4144556422ac87b911aa30aa95bef831ca18d2d2);
 assert.equal((await resolveTypedSnapshot(snapshot,1950)).observations.length,581);assert.equal((await resolveTypedSnapshot(snapshot,1951)).observations.length,0);assert.equal((await resolveTypedSnapshot(snapshot,2025)).observations.length,582);assert.equal((await resolveTypedSnapshot(snapshot,2026)).observations.length,0);
});

test('changed or missing original IDs, dates, source, values and examples cannot use the identity-only compiler',()=>{
 for(const mutate of [x=>x.entity_history.pop(),x=>x.entities.pop(),x=>x.entity_history[0].value.population++,x=>x.entity_history[0].valid_to++,x=>x.entity_history[0].source='latest UN census',x=>x.entity_history[0].entity_id=x.entities[1].id,x=>x.entity_history.push(x.entity_history[0]),x=>x.entities[0].kind='location',x=>x.entities[0].is_example=1]){const changed=structuredClone(input);mutate(changed);assert.throws(()=>compileResearchInput(changed),/retained/);}
 assert.throws(()=>compileResearchInput({sources:[settlementEstimateSource]}),/published geographic/);
});

test('registry identity scope cannot be selected by row metadata or applied to territorial fields, links, old digests or wrong subjects',async()=>{
 const contract=await observationContract(),row=observations[0];assert.equal(typedRequiresGeography(row,contract.registries),false);validateTypedGeography([row],null,contract.registries);
 for(const changed of [{...row,registry_sha256:'a'.repeat(64)},{...row,registry_sha256:'cc6aae6c18099d3e776c73ee4144556422ac87b911aa30aa95bef831ca18d2d2'},{...row,field_id:'atlas.marine-contact',subject_kind:'location'},{...row,subject_kind:'location'},{...row,relationship_type:'atlas.port-location'},{...row,location_id:'location'}]){assert.equal(typedRequiresGeography(changed,contract.registries),true);assert.throws(()=>validateTypedGeography([changed],null,contract.registries),/geography pins/);}
 await assert.rejects(normalizeTypedEvidence('observations',{...row,subject_id:'absent'},context),/subject/);
 await assert.rejects(normalizeTypedEvidence('observations',{...row,subject_kind:'location'},context),/subject kind/);
 await assert.rejects(normalizeTypedEvidence('observations',{...row,valid_from:1949},context),/source interval/);
});

class D1{
 constructor(){this.sqlite=new DatabaseSync(':memory:');for(const file of fs.readdirSync(new URL('../drizzle/',import.meta.url)).filter(file=>file.endsWith('.sql')).sort())this.sqlite.exec(fs.readFileSync(new URL('../drizzle/'+file,import.meta.url),'utf8'));}
 prepare(sql){const sqlite=this.sqlite;let args=[];return {bind(...values){args=values;return this;},async first(){return sqlite.prepare(sql).get(...args)??null;},async all(){return {results:sqlite.prepare(sql).all(...args)};},run(){return {meta:{changes:Number(sqlite.prepare(sql).run(...args).changes)}};}};}
 async batch(statements){this.sqlite.exec('BEGIN IMMEDIATE');try{const result=statements.map(statement=>statement.run());this.sqlite.exec('COMMIT');return result;}catch(error){this.sqlite.exec('ROLLBACK');throw error;}}
}
async function fixture(backend){
 const pg=backend==='postgres'?await createLocalPostgres():null,db=pg?.db??new D1();
 if(pg)for(const file of fs.readdirSync(new URL('../postgres/migrations/',import.meta.url)).sort())await pg.engine.exec(fs.readFileSync(new URL('../postgres/migrations/'+file,import.meta.url),'utf8'));
 await importBatch(db,JSON.parse(fs.readFileSync(new URL('../data/hosted-type-catalog.json',import.meta.url))));
 // Test-only catalog with the original settlement IDs. No geographic release or
 // regional approval is created, and no factual parent membership is imported.
 await importBatch(db,{entities:input.entities.slice(0,2).map(row=>({id:row.id,kind:row.kind,name:row.name})),sources:[settlementEstimateSource,{id:'synthetic:historical',name:'Test only',license:'CC0',vintage:'1950',status:'historical',supported_from:1950,supported_to:2026}]});
 const contract=await observationContract(),row={...observations[0],id:'synthetic:population'},rawSources=(await db.prepare('SELECT * FROM atlas_sources ORDER BY id').all()).results;
 const envelope=async(claims,extra={})=>({version:1,registry_sha256:contract.registry_sha256,source_pins:await typedSourcePins(rawSources.filter(source=>new Set(Object.values(claims).flat().map(row=>row.source_id)).has(source.id))),...claims,...extra});
 return {db,contract,row,envelope,close:()=>pg?pg.close():db.sqlite.close()};
}

test('actual SQLite/PostgreSQL accept only identity-only factual observations without global geography and retain source/retirement/derivation guards',async()=>{
 for(const backend of ['sqlite','postgres']){const f=await fixture(backend);try{
 const payload=await f.envelope({observations:[f.row]}),receipt=await importTypedBatch(f.db,payload,{gate:{version:2,ready_for_location_attributes:false,regions:[]}});assert.equal(receipt.expected_geography,null);assert.equal(receipt.counts.observations,1);assert.equal((await importTypedBatch(f.db,payload)).duplicate,true);
 const page=await typedSnapshotPage(f.db,1950);assert.equal(page.geography_pins,null);assert.equal(page.rows[0].value,f.row.value);assert.deepEqual(page.rows[0].metadata.original_record,f.row.metadata.original_record);
 const before=(await f.db.prepare('SELECT count(*) n FROM atlas_typed_observations').first()).n;
 for(const bad of [{...payload,observations:[{...f.row,id:'wrong-kind',subject_kind:'location'}]},{...payload,source_pins:[]},{...payload,observations:[{...f.row,id:'missing-derivation',method:'derived',metadata:{...f.row.metadata,derivation_input_ids:['missing']}}]}])await assert.rejects(importTypedBatch(f.db,bad));
 assert.equal((await f.db.prepare('SELECT count(*) n FROM atlas_typed_observations').first()).n,before);
 // An identity-only row cannot launder an actual territorial typed dependency.
 const territorial={...f.row,id:'synthetic:territorial',field_id:'atlas.marine-contact',subject_id:'synthetic:location',subject_kind:'location',value:false,source_id:'synthetic:historical',method:'direct',status:'sourced',metadata:{}};
 const hierarchy=['continent','subcontinent','region','area','province','location'].map((kind,i,all)=>({id:`synthetic:${kind}`,kind,name:'Test only',parent_id:i?`synthetic:${all[i-1]}`:null}));await importBatch(f.db,{entities:hierarchy});
 const mixed=await f.envelope({observations:[territorial,{...f.row,id:'derived',subject_id:input.entities[1].id,method:'derived',metadata:{...f.row.metadata,derivation_input_ids:[territorial.id]}}]});await assert.rejects(importTypedBatch(f.db,mixed),/geography pins/);
 await assert.rejects(importTypedBatch(f.db,await f.envelope({observations:[{...territorial,metadata:{geography_scope:'identity'}}]})),/geography pins/);
 // Corrections derive scope from retained targets, not retirement labels.
 const replacement={...f.row,id:'replacement',value:f.row.value+1},retirement={id:'withdraw',collection:'observations',target_id:f.row.id,replacement_id:replacement.id,source_id:f.row.source_id,reason:'Test-only correction'};
 await importTypedBatch(f.db,await f.envelope({observations:[replacement],retirements:[retirement]}));
 const retired=await typedSnapshotPage(f.db,1950,{stream:'retirements'});assert.equal(retired.rows[0].target_id,f.row.id);assert.equal((await f.db.prepare('SELECT value FROM atlas_typed_observations WHERE id=?').bind(f.row.id).first()).value,String(f.row.value));
 const snapshot=async()=>{const evidence=await typedSnapshotPage(f.db,1950),withdrawals=await typedSnapshotPage(f.db,1950,{stream:'retirements'});return resolveTypedSnapshot({version:1,registry_sha256:f.contract.registry_sha256,geography_pins:null,sources:evidence.sources,entities:evidence.entities,observations:evidence.rows,feature_links:[],retirements:withdrawals.rows},1950);};
 assert.equal((await snapshot()).observations[0].value,replacement.value);assert.equal((await snapshot()).observations[0].evidence.id,replacement.id);
 assert.equal((await typedSnapshotPage(f.db,1951)).rows.length,0);
 await importTypedBatch(f.db,await f.envelope({retirements:[{id:'withdraw-replacement',collection:'observations',target_id:replacement.id,source_id:f.row.source_id,reason:'Test-only withdrawal with no replacement'}]}));
 assert.equal((await snapshot()).observations.length,0,'Withdrawn values must not return from older claims');

 }finally{await f.close();}}
});

test('existing bundle entrypoints dry-run without network and reject tampering, false receipts and unsupported endpoint substitution',async()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'settlement-bundle-')),directory=path.join(root,'bundle');
 try{
 prepareResearchBundle({input:inputURL,output:directory});const verified=readResearchBundle(directory);assert.equal(verified.manifest.geography,null);
 const dry=await importResearchBundle({directory,origin:'https://example.org',dryRun:true,request:()=>{throw Error('Network must not be used');}});assert.equal(dry.network_requests,0);assert.equal(dry.counts.observations,9301);
 const wrong=async(_url,init)=>{const p=JSON.parse(init.body);return Response.json({ingestion_id:p.ingestion_id,expected_geography:null,counts:{sources:0},revision:1});};
 await assert.rejects(importResearchBundle({directory,origin:'https://example.org',token:'synthetic-only',request:wrong}),/exact source\/observation counts/);
 const indexFile=path.join(directory,'index.json'),index=JSON.parse(fs.readFileSync(indexFile));index.batches[1].endpoint='/api/records/import';fs.writeFileSync(indexFile,JSON.stringify(index));assert.throws(()=>readResearchBundle(directory),/endpoint/);
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});

test('all 48 real bundle transactions preserve 9301 exact rows and every pre-existing identity, with idempotent resume and no location attributes',async()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'settlement-full-parity-')),directory=path.join(root,'bundle'),pg=await createLocalPostgres(),db=pg.db;
 try{
 for(const file of fs.readdirSync(new URL('../postgres/migrations/',import.meta.url)).sort())await pg.engine.exec(fs.readFileSync(new URL('../postgres/migrations/'+file,import.meta.url),'utf8'));
 await importBatch(db,JSON.parse(fs.readFileSync(new URL('../data/hosted-type-catalog.json',import.meta.url))));
 const tiers=['continent','subcontinent','region','area','province'];
 await importBatch(db,{entities:tiers.map((kind,i)=>({id:'test:'+kind,kind,name:'Synthetic parent fixture',parent_id:i?'test:'+tiers[i-1]:null}))});
 const parents=[...new Set(input.entities.map(row=>row.parent_id))].map(id=>({id,kind:'location',name:'Synthetic location fixture',parent_id:'test:province'}));
 const subjects=input.entities.map(({id,kind,name,parent_id})=>({id,kind,name,parent_id}));
 for(const list of [parents,subjects])for(let i=0;i<list.length;i+=200)await importBatch(db,{entities:list.slice(i,i+200)});
 const before=JSON.stringify((await db.prepare('SELECT * FROM atlas_entities ORDER BY id').all()).results);
 const identity=(await pg.engine.query(fs.readFileSync(new URL('../postgres/settlement-identity-parity.sql',import.meta.url),'utf8'),[original.toString()])).rows[0].jsonb_build_object;
 assert.equal(identity.expected_subjects,582);assert.equal(identity.actual_subjects,582);for(const key of ['missing_or_changed','extra_or_changed','wrong_example_or_active','missing_or_wrong_parent_kind'])assert.equal(identity[key],0);

 prepareResearchBundle({input:inputURL,output:directory});let calls=0;
 const request=async(url,init)=>{calls++;assert.equal(init.method,'POST');const payload=JSON.parse(init.body);assert.equal('expected_geography' in payload,false);return Response.json(url.endsWith(typedResearchEndpoint)?await importTypedBatch(db,payload):await importBatch(db,payload));};
 const result=await importResearchBundle({directory,origin:'https://example.org',token:'test-only',request});assert.equal(result.complete,true);assert.equal(calls,48);
 assert.equal((await importResearchBundle({directory,origin:'https://example.org',token:'test-only',request})).complete,true);assert.equal(calls,48,'Complete identical receipts must not repeat requests');
 const stored=(await db.prepare('SELECT * FROM atlas_typed_observations ORDER BY id').all()).results;assert.equal(stored.length,9301);
 const expected=new Map(input.entity_history.map(row=>[row.id,row]));
 for(const raw of stored){const row=decodeTypedRow('observations',raw),original=expected.get(row.id);assert.ok(original);assert.equal(row.subject_id,original.entity_id);assert.equal(row.subject_kind,'settlement');assert.equal(row.value,original.value.population);assert.equal(row.valid_from,original.valid_from);assert.equal(row.valid_to,original.valid_to);assert.equal(row.source_id,settlementEstimateSource.id);assert.deepEqual(row.metadata.original_record,original);expected.delete(row.id);}assert.equal(expected.size,0);
 assert.equal(JSON.stringify((await db.prepare('SELECT * FROM atlas_entities ORDER BY id').all()).results),before);assert.equal((await db.prepare('SELECT count(*) n FROM atlas_attribute_records').first()).n,0);assert.equal((await db.prepare('SELECT count(*) n FROM atlas_geographic_releases').first()).n,0);assert.equal((await db.prepare('SELECT count(*) n FROM atlas_typed_feature_links').first()).n,0);
 const source=await db.prepare('SELECT * FROM atlas_sources WHERE id=?').bind(settlementEstimateSource.id).first();assert.equal(source.status,'estimate');assert.equal(source.metadata,researchJSON(settlementEstimateSource.metadata));
 const parity=(await pg.engine.query(fs.readFileSync(new URL('../postgres/settlement-population-parity.sql',import.meta.url),'utf8'),[original.toString(),settlementEstimateSource.id,observations[0].registry_sha256,JSON.stringify(settlementEstimateSource)])).rows[0].parity;
 assert.deepEqual(parity,{expected_rows:9301,actual_rows:9301,distinct_subjects:582,missing_or_changed:0,extra_or_changed:0,contract_mismatches:0,source_mismatches:0,unexpected_retirements:0});
 const check=async(source,sourceId=settlementEstimateSource.id,registry=observations[0].registry_sha256)=>(await pg.engine.query(fs.readFileSync(new URL('../postgres/settlement-population-parity.sql',import.meta.url),'utf8'),[JSON.stringify(source),sourceId,registry,JSON.stringify(settlementEstimateSource)])).rows[0].parity;
 const changed=structuredClone(input);changed.entity_history[0].value.population++;assert.equal((await check(changed)).missing_or_changed,1);assert.equal((await check(changed)).extra_or_changed,1);
 const missing=structuredClone(input);missing.entity_history.pop();assert.equal((await check(missing)).extra_or_changed,1);
 const extra=structuredClone(input);extra.entity_history.push({...extra.entity_history[0],id:'absent-original'});assert.equal((await check(extra)).missing_or_changed,1);
 assert.equal((await check(input,'wrong-source')).source_mismatches,1);assert.equal((await check(input,settlementEstimateSource.id,'a'.repeat(64))).contract_mismatches,9301);

 }finally{await pg.close();fs.rmSync(root,{recursive:true,force:true});}
});
