import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {PGlite} from '@electric-sql/pglite';
import {measureNeonStorage,runStorageMeasurement,validateStorageResults,storageQueries,storageTarget,liveStorageDriver} from '../scripts/measure-neon-storage.mjs';

const endpoint={id:'ep-test-storage',host:'ep-test-storage.us-east-2.aws.neon.tech',branch_id:storageTarget.branch,type:'read_write',project_id:storageTarget.project};
const uri='postgresql://neondb_owner:private-test-password@'+endpoint.host+'/neondb?sslmode=require';
const env={NEON_API_KEY:'private-test-api-key',NEON_PROJECT_ID:storageTarget.project};
const fixture=()=>[
  {rows:[{statement_timeout:'5s',lock_timeout:'1s'}]},
  {rows:[{database_name:'neondb',role_name:'neondb_owner',read_only:'on',statement_timeout:'5s',lock_timeout:'1s',endpoint_id:endpoint.id,database_bytes:'163840',observed_at:'2026-10-04T11:00:00Z'}]},
  {rows:[{table_name:'atlas_sources',relation_kind:'r',heap_main_bytes:'8192',toast_total_bytes:'0',table_bytes:'16384',index_bytes:'8192',total_bytes:'24576',estimated_live_rows:'2',estimated_dead_rows:'0',last_analyze:null,last_autoanalyze:null}]},
  {rows:[{table_name:'atlas_sources',index_name:'atlas_sources_pkey',index_bytes:'8192',definition:'CREATE UNIQUE INDEX atlas_sources_pkey ON public.atlas_sources USING btree (id)',valid:true,ready:true}]}
];
const management=overrides=>{
  const calls=[];const fetchImpl=async(url,options)=>{
    calls.push({url:String(url),options});assert.equal(options.method,'GET');assert.equal(options.redirect,'error');assert.equal(options.headers.Authorization,'Bearer '+env.NEON_API_KEY);
    const u=new URL(url);let body;
    if(u.pathname.endsWith('/connection_uri')){assert.equal(u.searchParams.get('branch_id'),storageTarget.branch);assert.equal(u.searchParams.get('pooled'),'false');body={uri};}
    else if(u.pathname.endsWith('/endpoints'))body={endpoints:[endpoint]};
    else if(u.pathname.includes('/branches/'))body={branch:{id:storageTarget.branch,project_id:storageTarget.project,name:'production',logical_size:12345}};
    else body={project:{id:storageTarget.project,branch_logical_size_limit:1024}};
    body=overrides?.(body,u)??body;return new Response(JSON.stringify(body));
  };return {calls,fetchImpl};
};
test('fixed target, GET-only credential acquisition and sanitized separate size metrics',async()=>{
  const api=management();let connected=0;
  const result=await measureNeonStorage({env,fetchImpl:api.fetchImpl,driverFactory:connection=>{assert.equal(connection,uri);connected++;return async()=>fixture();}});
  assert.equal(connected,1);assert.equal(api.calls.length,4);assert.equal(result.status,'measured');assert.equal(result.database_bytes,163840);assert.equal(result.application_relation_bytes,24576);assert.equal(result.other_database_bytes,139264);
  assert.equal(result.provider.branch_logical_size_bytes,12345);assert.equal(result.provider.branch_logical_size_limit_mib,1024);assert.equal(result.provider.billing_usage.status,'unavailable');
  assert.equal(result.tables[0].heap_auxiliary_bytes,8192);assert.equal(result.tables[0].estimated_live_rows,2);
  for(const secret of [env.NEON_API_KEY,uri,'private-test-password'])assert.ok(!JSON.stringify(result).includes(secret));
});
for(const [name,change] of [
  ['wrong project',b=>b.project?{project:{...b.project,id:'other'}}:b],
  ['wrong branch',b=>b.branch?{branch:{...b.branch,id:'br-other'}}:b],
  ['wrong branch name',b=>b.branch?{branch:{...b.branch,name:'staging'}}:b],
  ['wrong endpoint project',b=>b.endpoints?{endpoints:[{...endpoint,project_id:'other'}]}:b],
  ['wrong endpoint branch',b=>b.endpoints?{endpoints:[{...endpoint,branch_id:'br-other'}]}:b],
  ['duplicate endpoint',b=>b.endpoints?{endpoints:[endpoint,endpoint]}:b],
  ['foreign connection host',b=>b.uri?{uri:uri.replace(endpoint.host,'ep-foreign.us-east-2.aws.neon.tech')}:b],
  ['pooled connection',b=>b.uri?{uri:uri.replace('ep-test-storage.','ep-test-storage-pooler.')}:b],
  ['wrong database',b=>b.uri?{uri:uri.replace('/neondb?','/other?')}:b],
  ['wrong role',b=>b.uri?{uri:uri.replace('neondb_owner:','other:')}:b],
  ['TLS removed',b=>b.uri?{uri:uri.replace('require','disable')}:b],
  ['connection options',b=>b.uri?{uri:uri+'&options=-csearch_path=evil'}:b]
])test(name+' fails before SQL',async()=>{
  const api=management(change);let connected=false;
  await assert.rejects(()=>measureNeonStorage({env,fetchImpl:api.fetchImpl,driverFactory:()=>{connected=true;throw Error('must not connect');}}));assert.equal(connected,false);
});
for(const [name,change] of [
  ['read-write transaction',r=>r[1].rows[0].read_only='off'],
  ['wrong SQL role',r=>r[1].rows[0].role_name='other'],
  ['wrong SQL database',r=>r[1].rows[0].database_name='other'],
  ['SQL endpoint mismatch',r=>r[1].rows[0].endpoint_id='ep-other'],
  ['timeouts absent',r=>r[1].rows[0].statement_timeout='0'],
  ['overflow tables',r=>r[2].rows=Array.from({length:513},()=>r[2].rows[0])],
  ['duplicate table',r=>r[2].rows.push({...r[2].rows[0]})],
  ['accounting mismatch',r=>r[2].rows[0].total_bytes='24575'],
  ['unsafe number',r=>r[1].rows[0].database_bytes='9007199254740993'],
  ['negative estimate',r=>r[2].rows[0].estimated_dead_rows='-1'],
  ['unknown index table',r=>r[3].rows[0].table_name='atlas_missing'],
  ['oversized definition',r=>r[3].rows[0].definition='CREATE INDEX '+ 'x'.repeat(8192)]
])test(name+' prevents measured receipt',()=>{const r=fixture();change(r);assert.throws(()=>validateStorageResults(r,{endpointId:endpoint.id}));});
test('driver and API raw exceptions never reach saved failure receipts',async()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'storage738-test-'));try{
    for(const fetchFailure of [false,true]){
      const api=management();const filename=path.join(dir,'receipt.json');
      const receipt=await runStorageMeasurement({env,filename,fetchImpl:fetchFailure?async()=>{throw Error(uri+' '+env.NEON_API_KEY);}:api.fetchImpl,driverFactory:()=>async()=>{throw Error(uri+' '+env.NEON_API_KEY);}});
      assert.equal(receipt.status,'failed');const saved=fs.readFileSync(filename,'utf8');for(const secret of [uri,env.NEON_API_KEY,'private-test-password'])assert.ok(!saved.includes(secret));
    }
  }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
test('secret-like catalog definition cannot enter sanitized success receipt',async()=>{
  const api=management(),r=fixture();r[3].rows[0].definition+=' /* '+env.NEON_API_KEY+' */';
  await assert.rejects(()=>measureNeonStorage({env,fetchImpl:api.fetchImpl,driverFactory:()=>async()=>r}),/unsafe-or-oversized-receipt/);
});
test('bounded management stream refuses oversized input and never connects',async()=>{
  let connected=false;
  await assert.rejects(()=>measureNeonStorage({env,fetchImpl:async()=>new Response(' '.repeat(2*1024*1024+1)),driverFactory:()=>{connected=true;}}),/management-response-limit/);
  assert.equal(connected,false);
});
test('absent provider logical usage and tuple statistics remain unavailable',async()=>{
  const api=management(b=>b.branch?{branch:{...b.branch,logical_size:null}}:b),r=fixture();r[2].rows[0].estimated_live_rows=null;r[2].rows[0].estimated_dead_rows=null;
  const receipt=await measureNeonStorage({env,fetchImpl:api.fetchImpl,driverFactory:()=>async()=>r});
  assert.equal(receipt.provider.branch_logical_size_bytes,null);assert.equal(receipt.provider.logical_usage_source,'unavailable');assert.equal(receipt.tables[0].estimated_live_rows,null);
});
test('fixed SQL runs against real isolated PostgreSQL catalogs and READ ONLY denies mutation',async()=>{
  const db=new PGlite();try{
    await db.exec('CREATE TABLE atlas_storage_test(id text PRIMARY KEY,value text); CREATE TABLE worldatlas_schema_migrations(id text PRIMARY KEY); CREATE TABLE unrelated_test(id integer); INSERT INTO atlas_storage_test VALUES(\'one\',repeat(\'x\',20000));');
    await db.exec('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY');
    const settings=await db.query(storageQueries[0]);assert.equal(settings.rows[0].statement_timeout,'5s');
    const identity=await db.query(storageQueries[1]);assert.equal(identity.rows[0].read_only,'on');assert.ok(Number(identity.rows[0].database_bytes)>0);
    const tables=await db.query(storageQueries[2]),indexes=await db.query(storageQueries[3]);
    assert.deepEqual(tables.rows.map(r=>r.table_name),['atlas_storage_test','unrelated_test','worldatlas_schema_migrations']);assert.equal(indexes.rows.length,2);assert.equal(indexes.rows[0].index_name,'atlas_storage_test_pkey');
    const t=tables.rows[0];assert.equal(Number(t.table_bytes)+Number(t.index_bytes),Number(t.total_bytes));assert.ok(Number(t.toast_total_bytes)>=0);
    await assert.rejects(()=>db.query('INSERT INTO atlas_storage_test VALUES(\'forbidden\',\'x\')'),e=>e.code==='25006');
    await db.exec('ROLLBACK');assert.equal((await db.query('SELECT count(*)::int AS count FROM atlas_storage_test')).rows[0].count,1);
  }finally{await db.close();}
});
test('complete public catalog includes owner registry and accounts unknown public relations separately',()=>{
  const r=fixture(),table=r[2].rows[0],index=r[3].rows[0];
  r[2].rows.push({...table,table_name:'worldatlas_schema_migrations'},{...table,table_name:'unclassified_public_table'});
  r[3].rows.push({...index,table_name:'worldatlas_schema_migrations',index_name:'worldatlas_schema_migrations_pkey'});
  const result=validateStorageResults(r,{endpointId:endpoint.id});
  assert.equal(result.public_relation_bytes,3*24576);assert.equal(result.application_relation_bytes,2*24576);assert.equal(result.other_public_relation_bytes,24576);
  assert.equal(result.outside_public_relation_bytes,163840-3*24576);assert.equal(result.other_database_bytes,163840-2*24576);
  assert.equal(result.checks.migration_registry_present,true);assert.equal(result.tables[1].known_application_table,true);assert.equal(result.tables[2].known_application_table,false);
  assert.equal(validateStorageResults(fixture(),{endpointId:endpoint.id}).checks.migration_registry_present,false);
});
test('actual driver adapter forces server READ ONLY and only the fixed bounded transaction',async()=>{
  let called=false;
  const driver=liveStorageDriver(uri,(connection,options)=>{
    assert.equal(connection,uri);assert.equal(options.fullResults,true);
    return {transaction:async(callback,txOptions)=>{
      called=true;assert.equal(txOptions.readOnly,true);assert.equal(txOptions.isolationLevel,'RepeatableRead');assert.equal(txOptions.fetchOptions.redirect,'error');assert.ok(txOptions.fetchOptions.signal instanceof AbortSignal);
      const statements=callback({query:(sql,params)=>({sql,params})});assert.deepEqual(statements.map(s=>s.sql),storageQueries);assert.ok(statements.every(s=>s.params.length===0));return fixture();
    }};
  });
  assert.equal((await driver()).length,4);assert.equal(called,true);
});
