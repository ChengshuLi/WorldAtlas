import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createLocalPostgres} from '../scripts/verify-postgres-schema.mjs';
import {importBatch} from '../hosted/records.js';
import {stageGeographicRelease,finalizeGeographicRelease,geographicMembershipPage,geographicMembershipHash,geographicLocationIdsHash,geographicChangesHash} from '../hosted/geographic-releases.js';
import {rehearseCompactMembershipStorage,rehearseCompactMembershipRollback,compactMembershipParity,compactMembershipObjects} from '../scripts/compact-membership-storage.mjs';

const tiers=['continent','subcontinent','region','area','province','location'];
async function fixture(){
 const value=await createLocalPostgres();
 try{
  await importBatch(value.db,JSON.parse(fs.readFileSync(new URL('../data/hosted-type-catalog.json',import.meta.url))));
  await importBatch(value.db,{sources:[{id:'ref',name:'Isolated reference',url:'https://example.org/test-only',license:'CC0',vintage:'2026',status:'reference',supported_from:2026,supported_to:2027}],
   entities:Array.from({length:6},(_,c)=>tiers.map((kind,i)=>({id:`${c}:${kind}`,kind,name:kind,parent_id:i?`${c}:${tiers[i-1]}`:null}))).flat()});
  const members=Array.from({length:6},(_,c)=>tiers.map((kind,i)=>({entity_id:`${c}:${kind}`,kind,parent_id:i?`${c}:${tiers[i-1]}`:null,active:1,source_id:'ref',evidence:{test_only:true}}))).flat();
  const release=async(id,version)=>({id,version,source_id:'ref',reference_date:'2026-10-04',hierarchy_sha256:'a'.repeat(64),footprints_sha256:'b'.repeat(64),membership_sha256:await geographicMembershipHash(members),location_ids_sha256:await geographicLocationIdsHash(members),changes_sha256:await geographicChangesHash([]),expected_counts:Object.fromEntries(tiers.map(kind=>[kind,6]))});
  const first=await release('first',1);await stageGeographicRelease(value.db,{release:first,memberships:members});await finalizeGeographicRelease(value.db,first.id);
  return {...value,members,release,first};
 }catch(error){await value.close();throw error;}
}
const using=fn=>async()=>{const f=await fixture();try{await fn(f);}finally{await f.close();}};
const rawInsert='INSERT INTO atlas_geographic_memberships(release_id,entity_id,parent_id,reference_name,active,source_id,evidence) VALUES($1,$2,$3,$4,$5,$6,$7)';

test('compact contract preserves original guards, published byte retries and new service publication',using(async f=>{
 const original=(await f.engine.query('SELECT * FROM atlas_geographic_memberships ORDER BY release_id,entity_id')).rows;
 const receipt=await rehearseCompactMembershipStorage(f.engine);assert.equal(receipt.copied,36);assert.equal(receipt.parity.exact,true);
 assert.deepEqual((await f.engine.query('SELECT * FROM atlas_geographic_memberships ORDER BY release_id,entity_id')).rows,original);
 const retry=await f.engine.query(rawInsert,Object.values(original[0]));assert.equal(retry.affectedRows,0);
 await assert.rejects(f.engine.query(rawInsert,Object.values({...original[0],evidence:'{ "test_only": true }'})),/collision/);
 const second=await f.release('second',2);await stageGeographicRelease(f.db,{release:second,memberships:f.members});await finalizeGeographicRelease(f.db,second.id);
 assert.equal((await geographicMembershipPage(f.db,{parentId:'0:province'})).records[0].entity_id,'0:location');
 assert.equal((await f.engine.query('SELECT count(*)::int n FROM worldatlas_membership_evidence')).rows[0].n,1);
 await assert.rejects(rehearseCompactMembershipRollback(f.engine),/parity/);
 assert.equal((await f.engine.query('SELECT count(*)::int n FROM atlas_geographic_memberships')).rows[0].n,72);
}));

test('compact membership rejects invalid parents, source changes, updates and withdrawals',using(async f=>{
 await rehearseCompactMembershipStorage(f.engine);const second=await f.release('second',2);await stageGeographicRelease(f.db,{release:second});
 const valid=['second','0:location','0:province',null,1,'ref','{}'];
 await assert.rejects(f.engine.query(rawInsert,[...valid.slice(0,2),'0:continent',...valid.slice(3)]),/adjacent-tier/);
 await assert.rejects(f.engine.query(rawInsert,[...valid.slice(0,5),'missing','{}']),/reference source/);
 await assert.rejects(f.engine.query(rawInsert,[...valid.slice(0,6),'[]']),/check constraint/);
 await f.engine.query(rawInsert,valid);
 for(const sql of ["UPDATE atlas_geographic_memberships SET active=0 WHERE release_id='second'","DELETE FROM atlas_geographic_memberships WHERE release_id='second'","TRUNCATE worldatlas_membership_rows","UPDATE worldatlas_membership_evidence SET raw='{}'"])
  await assert.rejects(f.engine.query(sql),/append-only/);
 await assert.rejects(f.engine.query('TRUNCATE atlas_geographic_memberships'));
 await assert.rejects(finalizeGeographicRelease(f.db,'second'));
}));

test('compact dictionary preserves distinct raw JSON whitespace, key order and duplicate keys',using(async f=>{
 await rehearseCompactMembershipStorage(f.engine);await stageGeographicRelease(f.db,{release:await f.release('second',2)});
 const payloads=['{"a":1,"b":2}','{ "a": 1, "b": 2 }','{"b":2,"a":1}','{"a":0,"a":1,"b":2}'];
 for(const [i,raw]of payloads.entries())await f.engine.query(rawInsert,['second',`${i}:continent`,null,null,1,'ref',raw]);
 assert.deepEqual((await f.engine.query("SELECT evidence FROM atlas_geographic_memberships WHERE release_id='second' ORDER BY entity_id")).rows.map(x=>x.evidence),payloads);
 assert.equal((await f.engine.query('SELECT count(*)::int n FROM worldatlas_membership_evidence')).rows[0].n,5);
 await assert.rejects(f.engine.query("INSERT INTO worldatlas_membership_evidence(digest,raw) VALUES(sha256(convert_to('{}','UTF8')),'{ }')"),/check constraint/);
}));

test('failed copy rolls back its dictionaries, relation switch and original rows',using(async f=>{
 await assert.rejects(rehearseCompactMembershipStorage(f.engine,{afterCopy:()=>{throw Error('Injected failed copy');}}),/Injected failed/);
 assert.equal((await f.engine.query("SELECT relkind FROM pg_class WHERE oid='atlas_geographic_memberships'::regclass")).rows[0].relkind,'r');
 assert.equal((await f.engine.query("SELECT count(*)::int n FROM pg_class WHERE relname LIKE 'worldatlas_membership_%'")).rows[0].n,0);
 await rehearseCompactMembershipStorage(f.engine);assert.equal((await compactMembershipParity(f.engine)).exact,true);
 await rehearseCompactMembershipRollback(f.engine);
 assert.equal((await f.engine.query('SELECT count(*)::int n FROM atlas_geographic_memberships')).rows[0].n,36);
 assert.equal((await f.engine.query("SELECT relkind FROM pg_class WHERE oid='atlas_geographic_memberships'::regclass")).rows[0].relkind,'r');
}));

test('copy parity rejects an extra row and migration refuses unreviewed dependent views',using(async f=>{
 await importBatch(f.db,{entities:[{id:'extra',kind:'location',name:'Extra test identity',parent_id:'0:province'}]});
 await assert.rejects(rehearseCompactMembershipStorage(f.engine,{afterCopy:tx=>tx.query("SELECT worldatlas_membership_save('first','extra','0:province',NULL,1,'ref','{}')")}),/parity/);
 assert.equal((await f.engine.query('SELECT count(*)::int n FROM atlas_geographic_memberships')).rows[0].n,36);
 await f.engine.exec('CREATE VIEW extra_membership_reader AS SELECT * FROM atlas_geographic_memberships');
 await assert.rejects(rehearseCompactMembershipStorage(f.engine),/dependencies/);
 assert.equal((await f.engine.query("SELECT count(*)::int n FROM pg_class WHERE relname LIKE 'worldatlas_membership_%'")).rows[0].n,0);
}));

test('application role can use guarded membership view but cannot touch private dictionaries',using(async f=>{
 await f.engine.exec("CREATE ROLE worldatlas_app NOLOGIN NOINHERIT; GRANT USAGE ON SCHEMA public TO worldatlas_app; GRANT SELECT ON ALL TABLES IN SCHEMA public TO worldatlas_app; ALTER DEFAULT PRIVILEGES GRANT ALL ON TABLES TO worldatlas_app; ALTER DEFAULT PRIVILEGES GRANT ALL ON SEQUENCES TO worldatlas_app,PUBLIC; ALTER DEFAULT PRIVILEGES GRANT ALL ON FUNCTIONS TO worldatlas_app;");
 await rehearseCompactMembershipStorage(f.engine);
 for(const name of compactMembershipObjects)assert.equal((await f.engine.query('SELECT has_table_privilege(\'worldatlas_app\',$1,\'SELECT,INSERT,UPDATE,DELETE,TRUNCATE\') exposed',[name])).rows[0].exposed,false);
 for(const name of compactMembershipObjects.filter(x=>x!=='worldatlas_membership_rows'))assert.equal((await f.engine.query('SELECT has_sequence_privilege(\'worldatlas_app\',$1,\'USAGE,SELECT,UPDATE\') exposed',[name+'_key_seq'])).rows[0].exposed,false);
 assert.equal((await f.engine.query("SELECT has_table_privilege('worldatlas_app','atlas_geographic_memberships','UPDATE,DELETE,TRUNCATE') exposed")).rows[0].exposed,false);
 await stageGeographicRelease(f.db,{release:await f.release('second',2)});
 await f.engine.exec('SET ROLE worldatlas_app');
 try{
  assert.equal((await f.engine.query('SELECT count(*)::int n FROM atlas_geographic_memberships')).rows[0].n,36);
  const prior=(await f.engine.query('SELECT * FROM atlas_geographic_memberships ORDER BY entity_id LIMIT 1')).rows[0];
  assert.equal((await f.engine.query(rawInsert,Object.values(prior))).affectedRows,0);
  await assert.rejects(f.engine.query('SELECT * FROM worldatlas_memberships_original_v1'),/permission denied/);
  await assert.rejects(f.engine.query("SELECT worldatlas_membership_save('first','0:continent',NULL,NULL,1,'ref','{}')"),/permission denied/);
  await f.engine.query(rawInsert,['second','0:continent',null,null,1,'ref','{}']);
  await assert.rejects(f.engine.query(rawInsert,['second','1:location','1:continent',null,1,'ref','{}']),/adjacent-tier/);
 }finally{await f.engine.exec('RESET ROLE');}
}));
