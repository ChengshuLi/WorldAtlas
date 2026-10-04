import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
import {createLocalPostgres} from '../scripts/verify-postgres-schema.mjs';
import {importBatch} from '../hosted/records.js';
import {stageGeographicRelease,finalizeGeographicRelease,geographicMembershipHash,geographicLocationIdsHash,geographicChangesHash} from '../hosted/geographic-releases.js';
import {rehearseCompactMembershipStorage} from '../scripts/compact-membership-storage.mjs';
import {originalMembershipAPIPlan,verifyApplicationMembershipAPI} from '../scripts/verify-live-membership-api-functions.mjs';
const tiers=['continent','subcontinent','region','area','province','location'];
async function fixture(){
 const value=await createLocalPostgres();
 try{
  await importBatch(value.db,JSON.parse(fs.readFileSync(new URL('../data/hosted-type-catalog.json',import.meta.url))));
  await importBatch(value.db,{sources:[{id:'ref',name:'Isolated reference',url:'https://example.org/test-only',license:'CC0',vintage:'2026',status:'reference',supported_from:2026,supported_to:2027}],
   entities:Array.from({length:6},(_,c)=>[...tiers.map((kind,i)=>({id:`${c}:${kind}`,kind,name:kind,parent_id:i?`${c}:${tiers[i-1]}`:null})),...Array.from({length:30},(_,j)=>({id:`${c}:extra:${j}`,kind:'location',name:'Synthetic extra',parent_id:`${c}:province`}))]).flat()});
  const members=Array.from({length:6},(_,c)=>[...tiers.map((kind,i)=>({entity_id:`${c}:${kind}`,kind,parent_id:i?`${c}:${tiers[i-1]}`:null,active:1,source_id:'ref',evidence:{test_only:true}})),...Array.from({length:30},(_,j)=>({entity_id:`${c}:extra:${j}`,kind:'location',parent_id:`${c}:province`,active:1,source_id:'ref',evidence:{test_only:true}}))]).flat();
  const release=async(id,version)=>({id,version,source_id:'ref',reference_date:'2026-10-04',hierarchy_sha256:'a'.repeat(64),footprints_sha256:'b'.repeat(64),membership_sha256:await geographicMembershipHash(members),location_ids_sha256:await geographicLocationIdsHash(members),changes_sha256:await geographicChangesHash([]),expected_counts:Object.fromEntries(tiers.map(kind=>[kind,kind==='location'?186:6]))});
  const first=await release('first',1);await stageGeographicRelease(value.db,{release:first,memberships:members});await finalizeGeographicRelease(value.db,first.id);
  return {...value,members,release,first};
 }catch(error){await value.close();throw error;}
}

test('live function proof covers original cursor/parent/archived/profile responses and rejects changed output or privileges',async()=>{
 const f=await fixture();try{
  await f.engine.exec('CREATE ROLE worldatlas_app NOLOGIN; GRANT USAGE ON SCHEMA public TO worldatlas_app; GRANT SELECT ON ALL TABLES IN SCHEMA public TO worldatlas_app;');
  await rehearseCompactMembershipStorage(f.engine);
  const query=(sql,args)=>f.engine.query(sql,args),plan=await originalMembershipAPIPlan(query);
  assert.equal(plan.length,8);assert.ok(plan.some(p=>p.request.cursor));
  // PGlite has one embedded owner connection; inject its synthetic login identity
  // while real SET LOCAL ROLE and privileges execute. Production uses a separate LOGIN.
  const run=async p=>{await f.engine.exec('BEGIN READ ONLY; SET LOCAL ROLE worldatlas_app;');try{return await verifyApplicationMembershipAPI(async(sql,args)=>{const result=await query(sql,args);if(sql.includes('session_user login')){assert.equal(result.rows[0].role,'worldatlas_app');result.rows[0].login='worldatlas_app';}return result;},p);}finally{await f.engine.exec('ROLLBACK;');}};
  const before=await run(plan);assert.equal(before.served_http_verified,false);assert.equal(before.application_login,true);
  await assert.rejects(run(plan.map((p,i)=>i? p:{...p,sha256:'a'.repeat(64)})),/response-changed/);
  await f.engine.query('DROP TABLE worldatlas_memberships_original_v1');assert.deepEqual(await run(plan),before);
  await assert.rejects(verifyApplicationMembershipAPI(query,plan),/readonly-application-login/);
  await f.engine.query('REVOKE SELECT ON atlas_geographic_memberships FROM worldatlas_app');await assert.rejects(run(plan),/temporarily unavailable|rejected/);
 }finally{await f.close();}
});
