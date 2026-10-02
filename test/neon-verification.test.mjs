import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {PGlite} from '@electric-sql/pglite';
import {createPostgresDatabase} from '../hosted/postgres-adapter.js';
import {expectedNeonProjectId,verifyNeonProject,runNeonVerification} from '../scripts/verify-neon-project.mjs';
import {verifyNeonSQL,productionBranchId,schemaTransactionStatements} from '../scripts/verify-neon-sql.mjs';
import {postgresSchemaURL,postgresTables} from '../scripts/verify-postgres-schema.mjs';

const credential='private-test-api-credential';
const password='private-test-database-password';
const temporaryId='br-isolated-verification-fixture';
const nonce='11111111-2222-4333-8444-555555555555';
const branchName='atlas-sql-check-'+nonce;
const endpointHost='ep-isolated-fixture.aws.neon.tech';
const connection=`postgresql://neondb_owner:${password}@ep-isolated-fixture-pooler.aws.neon.tech/neondb?sslmode=require`;
const env={NEON_API_KEY:credential,NEON_PROJECT_ID:expectedNeonProjectId};
const prefix='/api/v2/projects/'+expectedNeonProjectId;

function receiptFile(t){
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-neon-verification-'));
 t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
 return path.join(directory,'receipt.json');
}
function assertSanitized(receipt,filename){
 const text=JSON.stringify(receipt),saved=fs.readFileSync(filename,'utf8');
 for(const bytes of [credential,password,connection,'postgresql://','raw-private-error']){
  assert.equal(text.includes(bytes),false);assert.equal(saved.includes(bytes),false);
 }
 assert.deepEqual(JSON.parse(saved),receipt);
 assert.ok(Buffer.byteLength(saved)<64*1024);
}

/** All requests are intercepted. Fixtures intentionally contain secret fields
 * that official metadata responses may include; receipts must omit them.
 */
function managementFixture(options={}){
 const calls=[];let branchPages=0;
 const fetchImpl=async(input,request)=>{
  const url=new URL(input),method=request.method;
  assert.equal(url.origin,'https://console.neon.tech');
  assert.equal(request.headers.Authorization,'Bearer '+credential);
  assert.equal(request.redirect,'error');assert.ok(request.signal instanceof AbortSignal);
  assert.equal(url.href.includes(credential),false);
  assert.equal(url.href.includes(password),false);
  calls.push({method,path:url.pathname,query:url.search,body:request.body});
  let result;
  if(method==='DELETE'){
   assert.equal(url.pathname,prefix+'/branches/'+temporaryId);
   options.onDelete?.();
   return new Response(options.cleanupFailure?'raw-private-error '+password:null,{status:options.cleanupFailure?503:204});
  }
  if(method==='POST'){
   assert.equal(url.pathname,prefix+'/branches');
   const payload=JSON.parse(request.body);
   assert.deepEqual(payload,{branch:{name:branchName,parent_id:productionBranchId},endpoints:[{type:'read_write'}]});
   if(options.ambiguousCreation)throw Error('raw-private-error '+credential+' '+connection);
   result={branch:{id:options.productionResponse?productionBranchId:temporaryId,name:branchName,parent_id:productionBranchId,project_id:expectedNeonProjectId},endpoints:[{branch_id:options.wrongEndpointBranch?productionBranchId:temporaryId,host:endpointHost,type:'read_write'}]};
  }else if(url.pathname.endsWith('/connection_uri')){
   assert.equal(url.searchParams.get('branch_id'),temporaryId);
   assert.equal(url.searchParams.get('database_name'),'neondb');
   assert.equal(url.searchParams.get('role_name'),'neondb_owner');
   assert.equal(url.searchParams.get('pooled'),'true');
   result={uri:options.productionHost?connection.replace('ep-isolated-fixture-pooler','ep-production-pooler'):connection};
  }else if(url.pathname.endsWith('/databases')){
   result={databases:[{branch_id:productionBranchId,name:'neondb',owner_name:'neondb_owner',password,connection_uri:connection}]};
  }else if(url.pathname.endsWith('/roles')){
   result={roles:[{branch_id:productionBranchId,name:'neondb_owner',password,secret:credential}]};
  }else if(url.pathname===prefix+'/branches/'+temporaryId){
   result={branch:{id:temporaryId,parent_id:productionBranchId,name:branchName,current_state:'ready'}};
  }else if(url.pathname===prefix+'/branches'){
   branchPages++;
   if(options.pagination&&branchPages===1){
    assert.equal(url.searchParams.has('cursor'),false);
    result={branches:[{id:'br-other-reference',name:'preview'}],pagination:{cursor:'next-page'}};
   }else{
    if(options.pagination)assert.equal(url.searchParams.get('cursor'),'next-page');
    result={branches:[{id:productionBranchId,name:'production',project_id:expectedNeonProjectId}]};
    if(options.repeatedCursor)result.pagination={cursor:'next-page'};
   }
  }else if(url.pathname===prefix){
   if(options.networkFailure)throw Error('raw-private-error '+credential+' '+connection);
   if(options.httpFailure)return new Response('raw-private-error '+password+' '+connection,{status:401});
   result={project:{id:options.wrongProjectResponse?'different-project':expectedNeonProjectId,pg_version:18,default_branch_id:productionBranchId,secret:credential,connection_uri:connection}};
  }else assert.fail('Unexpected management request route');
  return Response.json(result);
 };
 return {calls,fetchImpl};
}
async function sqlFixture(t,options={},driverFactory,ownerDriverFactory){
 const filename=receiptFile(t),api=managementFixture(options);
 let driverCalls=0;
 const receipt=await verifyNeonSQL({env,filename,fetchImpl:api.fetchImpl,uuid:()=>nonce,sleep:async()=>{},driverFactory:uri=>{
  driverCalls++;
  const parsed=new URL(uri);
  if(parsed.username==='neondb_owner')assert.equal(uri,connection);
  else{assert.equal(parsed.username,'worldatlas_app');assert.match(parsed.password,/^[A-Za-z0-9_-]{43}$/);}
  if(driverFactory)return driverFactory(uri);
  throw Error('raw-private-error '+credential+' '+uri);
 },...(ownerDriverFactory?{ownerDriverFactory}:{})});
 assertSanitized(receipt,filename);
 assert.equal(receipt.production_sql_writes,false);
 assert.equal(api.calls.some(call=>call.method==='DELETE'&&call.path.endsWith(productionBranchId)),false);
 return {receipt,filename,api,driverCalls};
}

test('Neon metadata verification authenticates read-only requests, follows pagination, and omits secret response fields',async t=>{
 const filename=receiptFile(t),api=managementFixture({pagination:true});
 const receipt=await runNeonVerification({env,filename,fetchImpl:api.fetchImpl});
 assert.equal(receipt.status,'verified');assert.equal(receipt.read_only,true);
 assert.equal(receipt.project.id,expectedNeonProjectId);assert.equal(receipt.branch.id,productionBranchId);
 assert.deepEqual(receipt.databases,[{name:'neondb',owner_name:'neondb_owner'}]);
 assert.deepEqual(receipt.roles,[{name:'neondb_owner'}]);
 assert.equal(api.calls.length,5);assert.equal(receipt.api_requests,5);
 assert.ok(api.calls.every(call=>call.method==='GET'&&call.body===undefined));
 assert.equal(api.calls.some(call=>call.path.endsWith('/connection_uri')),false);
 assertSanitized(receipt,filename);
});

test('Neon verifier rejects wrong project configuration and absent credentials without requests',async t=>{
 for(const badEnv of [{NEON_API_KEY:credential,NEON_PROJECT_ID:'different-project'},{NEON_PROJECT_ID:expectedNeonProjectId}]){
  let requests=0;const fetchImpl=async()=>{requests++;throw Error('must not request');};
  const metadataFile=receiptFile(t),metadata=await runNeonVerification({env:badEnv,filename:metadataFile,fetchImpl});
  assert.equal(metadata.status,'failed');assertSanitized(metadata,metadataFile);
  const sqlFile=receiptFile(t),sql=await verifyNeonSQL({env:badEnv,filename:sqlFile,fetchImpl});
  assert.equal(sql.status,'failed');assert.equal(sql.cleanup_status,'not-required');assert.equal(sql.management_requests,0);
  assertSanitized(sql,sqlFile);assert.equal(requests,0);
 }
});

test('Neon metadata failures never retain raw HTTP/network bodies, mismatched projects, or repeated pagination cursors',async t=>{
 for(const [scenario,code] of [
  [{networkFailure:true},'api-request-unavailable'],
  [{httpFailure:true},'neon-api-http-error'],
  [{wrongProjectResponse:true},'project-response-mismatch'],
  [{pagination:true,repeatedCursor:true},'repeated-branch-cursor'],
 ]){
  const filename=receiptFile(t),api=managementFixture(scenario);
  const receipt=await runNeonVerification({env,filename,fetchImpl:api.fetchImpl});
  assert.equal(receipt.status,'failed');assert.equal(receipt.error_code,code);
  assert.ok(api.calls.every(call=>call.method==='GET'));assertSanitized(receipt,filename);
 }
});

test('PostgreSQL schema splitter retains command bytes while respecting nested comments, quoted identifiers, strings and dollar bodies',()=>{
 const command="\nCREATE FUNCTION x() RETURNS text AS $body$ SELECT ';' /*;*/ $body$ LANGUAGE sql;";
 assert.deepEqual(schemaTransactionStatements('BEGIN;'+command+'COMMIT;'),[command]);
 const quoted=" CREATE TABLE x(\"a;b\" text DEFAULT E'\\\';', b text DEFAULT 'it''s;fine');";
 assert.deepEqual(schemaTransactionStatements('--before\nBEGIN;'+quoted+' /* nested /* ; */ ; */ COMMIT;'),[quoted]);
 assert.equal(schemaTransactionStatements('BEGIN; CREATE TABLE x(a text); COMMIT; -- trailing comment').length,1);
 for(const invalid of [
  "BEGIN; SELECT 'unclosed; COMMIT;",
  'BEGIN; SELECT $body$ unclosed; COMMIT;',
  'BEGIN; /* unclosed; COMMIT;',
  'BEGIN; SELECT 1; COMMIT; SELECT 2',
  'SELECT 1;',
  'BEGIN; SELECT 1; COMMIT; COMMIT;',
 ])assert.throws(()=>schemaTransactionStatements(invalid));
});

test('isolated Neon verifier applies the exact schema atomically on real PostgreSQL and exercises actual hosted services',async t=>{
 const engine=new PGlite();t.after(()=>engine.close());
 // Reproduce Neon owner administration without superuser privileges. PGlite's
 // original superuser authentication only switches independent test sessions.
 await engine.query('CREATE ROLE neondb_owner LOGIN CREATEROLE NOINHERIT');
 const database=(await engine.query('SELECT current_database() AS name')).rows[0].name;
 assert.match(database,/^[a-z_]+$/);await engine.query(`ALTER DATABASE ${database} OWNER TO neondb_owner`);
 await engine.query('SET SESSION AUTHORIZATION neondb_owner');
 const appliedCommands=[];
 const driver={
  async query(query,params=[]){
   // Only management/connection identity is simulated. All schema, evidence,
   // ingestion and hosted service operations execute in actual PostgreSQL.
   if(query.startsWith('SELECT current_database() AS database_name,current_user'))return {rows:[{database_name:'neondb',role_name:'neondb_owner',schema_name:'public',server_version_num:'180003'}],fields:[],rowCount:1};
   const result=await engine.query(query,params);return {...result,rowCount:result.affectedRows??result.rows.length};
  },
  async transaction(items){return engine.transaction(async tx=>{
   const results=[];for(const item of items){const result=await tx.query(item.query,item.params??[]);results.push({...result,rowCount:result.affectedRows??result.rows.length});}return results;
  });},
 };
 const sql={query:(query,params)=>driver.query(query,params),transaction:async(callback,options)=>{
  assert.equal(options.isolationLevel,'Serializable');
  const statements=callback({query:(query,params)=>({query,params})});appliedCommands.push(...statements.map(item=>item.query));
  return driver.transaction(statements);
 }};
 let ownerClosed=false,appPassword;
 const ownerFactory=async uri=>{
  assert.equal(uri,connection);
  return {query:(query,params)=>engine.query(query,params),runTransaction:callback=>engine.transaction(tx=>callback({query:(query,params)=>tx.query(query,params)})),close:async()=>{await engine.query('SET SESSION AUTHORIZATION postgres');ownerClosed=true;}};
 };
 const {receipt,filename,api,driverCalls}=await sqlFixture(t,{onDelete:()=>assert.equal(ownerClosed,true)},uri=>{
  const parsed=new URL(uri);
  if(parsed.username==='neondb_owner')return {sql,db:createPostgresDatabase(driver)};
  appPassword=parsed.password;
  const authenticated=engine.query('SET SESSION AUTHORIZATION worldatlas_app');
  const appDriver={query:async(query,params)=>{await authenticated;return driver.query(query,params);},transaction:async items=>{await authenticated;return driver.transaction(items);}};
  return {sql:{query:appDriver.query},db:createPostgresDatabase(appDriver)};
 },ownerFactory);
 const bytes=fs.readFileSync(postgresSchemaURL),expectedCommands=schemaTransactionStatements(bytes.toString('utf8'));
 assert.equal(expectedCommands.length,56);assert.deepEqual(appliedCommands,expectedCommands);
 assert.equal(receipt.schema_sha256,createHash('sha256').update(bytes).digest('hex'));
 assert.equal(receipt.status,'verified',JSON.stringify(receipt));assert.equal(receipt.cleanup_status,'deleted');assert.equal(driverCalls,2);
 assert.equal(receipt.schema_complete,true);assert.deepEqual(receipt.schema_tables,postgresTables);
 assert.equal(receipt.sql_contracts_passed,true);assert.equal(receipt.retained_original_population,42);assert.equal(receipt.resolved_population,43);
 assert.equal(receipt.runtime_current_user,'worldatlas_app');assert.equal(receipt.runtime_session_user,'worldatlas_app');
 assert.equal(receipt.runtime_role.permissions.length,14);assert.equal(receipt.runtime_role.memberships,0);assert.equal(receipt.runtime_role.public_schema_create,false);
 assert.equal(receipt.idempotent_application_retry,true);assert.equal(receipt.denied_operations.length,13);assert.equal(receipt.owner_connection_closed,true);
 assert.ok(appPassword);assert.equal(fs.readFileSync(filename,'utf8').includes(appPassword),false);
 assert.equal(api.calls.some(call=>call.path.includes('password')||call.path.endsWith('/roles')&&call.query.includes('worldatlas_app')),false);
 const retained=(await engine.query("SELECT id,value FROM atlas_attribute_records WHERE id IN ('pg-verification:old','pg-verification:new') ORDER BY id")).rows;
 assert.deepEqual(retained,[{id:'pg-verification:new',value:'43'},{id:'pg-verification:old',value:'42'}]);
 assert.deepEqual(api.calls.filter(call=>call.method==='DELETE').map(call=>call.path),[prefix+'/branches/'+temporaryId]);
 assert.equal(receipt.management_requests,api.calls.length);
});

test('private owner connection failures remain sanitized and cleanup still deletes the validation branch',async t=>{
 let closeAttempted=false;
 const {receipt}=await sqlFixture(t,{},()=>({
  sql:{transaction:callback=>Promise.resolve(callback({query:()=>({})}))},
  db:{prepare:query=>({first:async()=>query.startsWith('SELECT current_database()')?{database_name:'neondb',role_name:'neondb_owner',schema_name:'public',server_version_num:'180003'}:{count:0},all:async()=>({results:postgresTables.map(table_name=>({table_name}))})})},
 }),async()=>({
  query:async()=>{throw Error('raw-private-error '+connection);},
  runTransaction:async callback=>callback({query:async()=>{throw Error('raw-private-error '+connection);}}),
  close:async()=>{closeAttempted=true;throw Error('raw-private-error '+password);},
 }));
 assert.equal(receipt.status,'failed');assert.equal(receipt.failure_stage,'restricted-role-provisioning');
 assert.equal(closeAttempted,true);assert.equal(receipt.owner_connection_closed,false);
 assert.equal(receipt.owner_close_error_code,'private-owner-close-failed');assert.equal(receipt.cleanup_status,'deleted');
});

test('isolated SQL verifier refuses production IDs and production hosts before any SQL connection',async t=>{
 for(const scenario of [{productionResponse:true},{productionHost:true},{wrongEndpointBranch:true}]){
  const {receipt,api,driverCalls}=await sqlFixture(t,scenario);
  assert.equal(receipt.status,'failed');assert.equal(driverCalls,0);
  assert.equal(api.calls.some(call=>call.path.endsWith('/connection_uri')),!scenario.productionResponse&&!scenario.wrongEndpointBranch);
  if(scenario.productionResponse){assert.equal(api.calls.some(call=>call.method==='DELETE'),false);assert.equal(receipt.cleanup_status,'creation-unconfirmed');}
  else assert.equal(receipt.cleanup_status,'deleted');
 }
});

test('SQL driver errors are sanitized and clean up only the newly created branch',async t=>{
 const {receipt,api,driverCalls}=await sqlFixture(t);
 assert.equal(driverCalls,1);assert.equal(receipt.status,'failed');assert.equal(receipt.cleanup_status,'deleted');
 assert.equal(receipt.failure_stage,'isolated-connection');
 assert.deepEqual(api.calls.filter(call=>call.method==='DELETE').map(call=>call.path),[prefix+'/branches/'+temporaryId]);
});

test('cleanup failures retain the exact validation branch ID and fail the verification receipt',async t=>{
 const {receipt}=await sqlFixture(t,{cleanupFailure:true});
 assert.equal(receipt.status,'failed');assert.equal(receipt.cleanup_status,'failed');
 assert.equal(receipt.retained_validation_branch_id,temporaryId);
 assert.equal(receipt.cleanup_error_code,'validation-branch-cleanup-failed');
});

test('ambiguous creation persists its unique name without guessing a deletion target or SQL connection',async t=>{
 const {receipt,api,driverCalls}=await sqlFixture(t,{ambiguousCreation:true});
 assert.equal(receipt.status,'failed');assert.equal(receipt.cleanup_status,'creation-unconfirmed');
 assert.equal(receipt.validation_branch_name,branchName);assert.equal(receipt.validation_branch_id,undefined);
 assert.equal(receipt.failure_stage,'branch-creation');assert.equal(driverCalls,0);
 assert.equal(api.calls.some(call=>call.method==='DELETE'||call.path.endsWith('/connection_uri')),false);
});

test('read-only metadata helper does not accept a project mismatch supplied by the API',async()=>{
 const api=managementFixture({wrongProjectResponse:true});
 await assert.rejects(verifyNeonProject({apiKey:credential,projectId:expectedNeonProjectId,fetchImpl:api.fetchImpl}),error=>error.code==='project-response-mismatch');
 assert.equal(api.calls.length,1);
});
