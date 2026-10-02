import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {importBatch,attributesAt,namesAt,evidenceHistory} from '../hosted/records.js';
import {createPostgresDatabase,createNeonDatabase} from '../hosted/postgres-adapter.js';

export const postgresSchemaURL=new URL('../postgres/schema.sql',import.meta.url);
export const postgresTables=['atlas_sources','atlas_entity_types','atlas_entities','atlas_categories','atlas_attribute_records','atlas_names','atlas_relationships','atlas_media','atlas_media_links','atlas_evidence_retirements','atlas_ingestions','atlas_geographic_releases','atlas_geographic_memberships','atlas_geographic_changes'];
export async function createLocalPostgres(){
 const {PGlite}=await import('@electric-sql/pglite'),engine=new PGlite();
 try{
  const schema=fs.readFileSync(postgresSchemaURL,'utf8');await engine.exec(schema);
  const driver={
   async query(sql,params=[]){const result=await engine.query(sql,params);return {...result,rowCount:result.affectedRows??result.rows.length};},
   async transaction(statements){return engine.transaction(async transaction=>{const results=[];for(const statement of statements){const result=await transaction.query(statement.query,statement.params??[]);results.push({...result,rowCount:result.affectedRows??result.rows.length});}return results;});},
  };
  return {engine,driver,db:createPostgresDatabase(driver),schema_sha256:createHash('sha256').update(schema).digest('hex'),close:()=>engine.close()};
 }catch(error){await engine.close();throw Error(`Local PostgreSQL schema/application setup failed: ${error.message}${error.code?` (SQLSTATE ${error.code})`:''}${error.position?` at SQL character ${error.position}`:''}`);}
}
export async function postgresSchemaInventory(db){
 const version=await db.prepare('SELECT version() AS postgres_version,current_database() AS database_name,current_schema() AS schema_name').first();
 const tables=await db.prepare("SELECT table_name FROM information_schema.tables WHERE table_schema=current_schema() AND table_type='BASE TABLE' ORDER BY table_name").all();
 const names=tables.results.map(row=>row.table_name),missing=postgresTables.filter(name=>!names.includes(name));
 return {postgres_version:version.postgres_version,schema_name:version.schema_name,tables:names,expected_tables:postgresTables.length,missing_tables:missing,schema_complete:missing.length===0};
}
export async function exercisePostgresSmoke(db){
 const source={id:'pg-verification:source',name:'Isolated verification source',url:'https://example.org/isolation-test-only',license:'CC0',vintage:'2026',supported_from:1000,supported_to:1100,status:'historical',metadata:{test_only:true,original_digest:'a'.repeat(64)}};
 await importBatch(db,JSON.parse(fs.readFileSync(new URL('../data/hosted-type-catalog.json',import.meta.url))));
 const tiers=['continent','subcontinent','region','area','province','location'];
 await importBatch(db,{sources:[source],entities:tiers.map((kind,index)=>({id:`pg-verification:${kind}`,kind,name:`Test-only ${kind}`,parent_id:index?`pg-verification:${tiers[index-1]}`:null})),records:[{id:'pg-verification:old',location_id:'pg-verification:location',attribute:'population',value:42,valid_from:1000,valid_to:1100,source_id:source.id}],names:[{id:'pg-verification:name',entity_id:'pg-verification:location',name:'Isolated dated name',valid_from:1000,valid_to:1100,source_id:source.id}]});
 await importBatch(db,{records:[{id:'pg-verification:new',location_id:'pg-verification:location',attribute:'population',value:43,valid_from:1000,valid_to:1100,source_id:source.id}],retirements:[{id:'pg-verification:withdrawal',collection:'records',target_id:'pg-verification:old',replacement_id:'pg-verification:new',source_id:source.id,reason:'Isolated test-only correction'}]});
 const claims=await attributesAt(db,1000),names=await namesAt(db,1000),old=await evidenceHistory(db,'records','pg-verification:old');
 if(claims.records.find(row=>row.id==='pg-verification:new')?.value!==43||old.claim.value!==42||old.status!=='superseded'||names.records.find(row=>row.id==='pg-verification:name')?.value!=='Isolated dated name')throw Error('Actual hosted service PostgreSQL verification failed');
 if((await attributesAt(db,1100)).records.some(row=>row.id==='pg-verification:new'))throw Error('Exclusive PostgreSQL claim endpoint failed');
 return {actual_hosted_service_checks:['type registry','six-tier entity chain','immutable sources','dated attributes','dated names','atomic sourced correction','original evidence read-back','exclusive interval endpoint'],fixture_scope:'isolated ephemeral PostgreSQL; no production mutation',retained_original_population:old.claim.value,resolved_population:43};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const mode=process.argv[2]??'--local';
 if(mode==='--local'){
  const fixture=await createLocalPostgres();try{const result={mode:'local-pglite-postgresql',...(await postgresSchemaInventory(fixture.db)),schema_sha256:fixture.schema_sha256,...await exercisePostgresSmoke(fixture.db)};if(!result.schema_complete)throw Error('PostgreSQL schema is missing required tables');console.log(JSON.stringify(result));}finally{await fixture.close();}
 }else if(mode==='--remote-read-only'){
  const url=process.env.DATABASE_URL;if(!url)throw Error('DATABASE_URL is required through the authorized secret environment');
  try{const result=await postgresSchemaInventory(createNeonDatabase(url));console.log(JSON.stringify({mode:'remote-read-only-inventory',read_only:true,...result,contract_tested:false,limitations:'Inventory only; this mode does not apply migrations, import fixtures, test writes or prove service capacity.'}));if(!result.schema_complete)process.exitCode=1;}catch(error){console.error(JSON.stringify({mode:'remote-read-only-inventory',error:String(error.message).split(url).join('[redacted]')}));process.exitCode=1;}
 }else throw Error('Usage: node scripts/verify-postgres-schema.mjs [--local | --remote-read-only]. Local runs isolated PostgreSQL contracts; remote mode never writes.');
}
