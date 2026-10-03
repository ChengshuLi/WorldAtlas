import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import {createLocalPostgres} from '/workspace/worldatlas-observation-integration-20261003-7e91/scripts/verify-postgres-schema.mjs';
import {importBatch} from '/workspace/worldatlas-observation-integration-20261003-7e91/hosted/records.js';
import {stageGeographicRelease,finalizeGeographicRelease,geographicMembershipHash,geographicLocationIdsHash,geographicChangesHash} from '/workspace/worldatlas-observation-integration-20261003-7e91/hosted/geographic-releases.js';
import {typedCapabilities,typedSourcePins,importTypedBatch} from '/workspace/worldatlas-observation-integration-20261003-7e91/hosted/typed-observations.js';
import {observationContract} from '/workspace/worldatlas-observation-integration-20261003-7e91/src/observation-modules.js';
import {decodeTypedRow,resolveTypedSnapshot} from '/workspace/worldatlas-observation-integration-20261003-7e91/src/typed-snapshot.js';
import {exportStorageMarkerV3} from '/workspace/worldatlas-observation-integration-20261003-7e91/hosted/storage-export-v3.js';

class D1{
 constructor({forward=true}={}){this.sqlite=new DatabaseSync(':memory:');for(const file of fs.readdirSync(new URL('/workspace/worldatlas-observation-integration-20261003-7e91/drizzle/',import.meta.url)).filter(file=>file.endsWith('.sql')&&(forward||/^000[0-7]_/.test(file))).sort())this.sqlite.exec(fs.readFileSync(new URL('/workspace/worldatlas-observation-integration-20261003-7e91/drizzle/'+file,import.meta.url),'utf8'));}
 prepare(sql){const sqlite=this.sqlite;let args=[];return {bind(...values){args=values;return this;},async first(){return sqlite.prepare(sql).get(...args)??null;},async all(){return {results:sqlite.prepare(sql).all(...args)};},run(){return {meta:{changes:Number(sqlite.prepare(sql).run(...args).changes)}};}};}
 async batch(statements){this.sqlite.exec('BEGIN IMMEDIATE');try{const result=statements.map(statement=>statement.run());this.sqlite.exec('COMMIT');return result;}catch(error){this.sqlite.exec('ROLLBACK');throw error;}}
}
const kinds=['continent','subcontinent','region','area','province','location'];
const pins={release_id:'synthetic-typed-release',hierarchy_sha256:'a'.repeat(64),footprints_sha256:'b'.repeat(64)};
async function fixture(backend){
 const pg=backend==='postgres'?await createLocalPostgres():null,db=pg?.db??new D1();
 if(pg)for(const file of fs.readdirSync(new URL('/workspace/worldatlas-observation-integration-20261003-7e91/postgres/migrations/',import.meta.url)).sort())await pg.engine.exec(fs.readFileSync(new URL('/workspace/worldatlas-observation-integration-20261003-7e91/postgres/migrations/'+file,import.meta.url),'utf8'));
 try{
  await importBatch(db,JSON.parse(fs.readFileSync(new URL('/workspace/worldatlas-observation-integration-20261003-7e91/data/hosted-type-catalog.json',import.meta.url))));
  await importBatch(db,JSON.parse(fs.readFileSync(new URL('/workspace/worldatlas-observation-integration-20261003-7e91/data/typed-entity-types-v1.json',import.meta.url))));
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



const f=await fixture('sqlite');
try{
 const results=[];
 const p=await f.envelope({observations:[observation('cycle-a',{method:'derived',metadata:{derivation_input_ids:['cycle-b']}}),observation('cycle-b',{subject_id:'location-1',method:'derived',metadata:{derivation_input_ids:['cycle-a']}})]});
 try{results.push({probe:'same-batch-two-node-cycle',accepted:true,result:await importTypedBatch(f.db,p)});}catch(e){results.push({probe:'same-batch-two-node-cycle',accepted:false,error:e.message});}
 await importTypedBatch(f.db,await f.envelope({observations:[observation('example-original',{subject_id:'location-2'})]}));
 const derived=await f.envelope({observations:[observation('example-derived',{subject_id:'location-3',method:'derived',metadata:{derivation_input_ids:['example-original']}})]});
 try{results.push({probe:'retained-example-to-example-without-factual-certificate',accepted:true,result:await importTypedBatch(f.db,derived)});}catch(e){results.push({probe:'retained-example-to-example-without-factual-certificate',accepted:false,error:e.message});}
 console.log(JSON.stringify({scope:'isolated SQLite synthetic fixtures only',results},null,2));
}finally{await f.close();}
