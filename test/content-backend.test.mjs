import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {PGlite} from '@electric-sql/pglite';
import {contentDatabase,storageReadOnly} from '../hosted/content-backend.js';
import {createPostgresDatabase} from '../hosted/postgres-adapter.js';
import {capacityReport} from '../hosted/research-catalog.js';
import worker from '../hosted/worker.js';

test('backend cutover is explicit and cannot expose credentials or silently return D1',()=>{
 const oldDb={dialect:'d1'},newDb={dialect:'postgres'},url='postgresql://user:private-password@host/db';let calls=0;
 const factory=value=>{assert.equal(value,url);calls++;return newDb;},env={DB:oldDb,DATABASE_URL:url};
 assert.equal(contentDatabase(env,{createPostgres:factory}),oldDb);assert.equal(calls,0);
 env.ATLAS_CONTENT_BACKEND='postgres';assert.equal(contentDatabase(env,{createPostgres:factory}),newDb);assert.equal(contentDatabase(env,{createPostgres:factory}),newDb);assert.equal(calls,1);
 for(const invalid of [{DB:oldDb,ATLAS_CONTENT_BACKEND:'unknown'},{DB:oldDb,ATLAS_CONTENT_BACKEND:'postgres'},{DB:oldDb,ATLAS_CONTENT_BACKEND:'postgres',DATABASE_URL:url}]){
  assert.throws(()=>contentDatabase(invalid,{createPostgres:()=>{throw Error(url);}}),error=>error.status===503&&!error.message.includes('private-password'));
 }
 assert.equal(storageReadOnly({ATLAS_READ_ONLY:'1'}),true);assert.equal(storageReadOnly({}),false);
});

test('transfer maintenance blocks every API mutation before touching a database or object bucket',async()=>{
 const env={ATLAS_READ_ONLY:'1',get DB(){throw Error('Database must not be touched');},get BUCKET(){throw Error('Bucket must not be touched');}};
 for(const route of ['/api/records/import','/api/media/upload','/api/geography/stage','/api/geography/finalize']){
  const response=await worker.fetch(new Request(`https://atlas.example${route}`,{method:'POST',body:'{}'}),env,{});
  assert.equal(response.status,503);assert.deepEqual(await response.json(),{error:'Historical storage is read-only during a verified transfer',retryable:true});
 }
 assert.equal((await worker.fetch(new Request('https://atlas.example/api/classifications'),env,{})).status,200);
});

test('PostgreSQL diagnostics and raw export routes use the selected backend and retain honest quota status',async()=>{
 const pg=new PGlite();try{
  await pg.exec(fs.readFileSync(new URL('../postgres/schema.sql',import.meta.url),'utf8'));
  const whitespace=await pg.query('SELECT json_type($1) kind,$1::text original',[' \t\n42\r ']);assert.equal(whitespace.rows[0].kind,'integer');assert.equal(whitespace.rows[0].original,' \t\n42\r ');
  const db=createPostgresDatabase({query:(sql,args)=>pg.query(sql,args),transaction:queries=>pg.transaction(async tx=>Promise.all(queries.map(q=>tx.query(q.query,q.params))))});
  const report=await capacityReport(db);assert.equal(report.backend.kind,'postgres-plus-r2');assert.equal(report.database.measurement,'postgres-pg-database-size');assert.ok(report.database.bytes>0);assert.equal(report.database.quota_verified,false);assert.equal(report.counts.records,0);
  // A D1-shaped binding also permits local route tests without exposing a URL.
  const env={DB:db,ATLAS_READ_ONLY:'1'};
  const markerResponse=await worker.fetch(new Request('https://atlas.example/api/storage/export-marker'),env,{});
  assert.equal(markerResponse.status,200);const marker=await markerResponse.json();assert.equal(marker.read_only,true);assert.equal(marker.backend,'postgres');assert.equal(marker.counts.ingestions,0);
  const pageResponse=await worker.fetch(new Request('https://atlas.example/api/storage/export/sources?limit=200'),env,{});
  assert.equal(pageResponse.status,200);const page=await pageResponse.json();assert.deepEqual(page.records,[]);assert.equal(page.snapshot_marker.fingerprint,marker.fingerprint);
 }finally{await pg.close();}
});
