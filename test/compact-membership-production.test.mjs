import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import os from 'node:os';import path from 'node:path';import {createHash} from 'node:crypto';
import {createLocalPostgres} from '../scripts/verify-postgres-schema.mjs';
import {nativeMembershipDigestSQL,patchNativeRestoreFile} from '../scripts/current-postgres-recovery.mjs';
import {validateCompactProductionWindow,runCompactMembershipProduction,checkOriginalMembershipIndexes,restoreOriginalMembershipIndexes,commitMembershipRetirement} from '../scripts/run-compact-membership-production.mjs';
const sha=b=>createHash('sha256').update(b).digest('hex');
const now=Date.parse('2026-10-04T23:00:00Z'),head='a'.repeat(40),toolSHA='b'.repeat(64),spec={mode:'engineering',depends_on:[],max_prs:1,scope:'Bounded authorized compact production operation',production_operation:{source_issue:783,publisher_worker_id:'engineering-neon-storage-publisher-20261004-local01'}};
const issue={number:900,state:'open',body:'<!-- worldatlas-work:v1\n'+JSON.stringify(spec)+'\n-->'};
const claim={active:true,live_work:true,issue_number:900,claim_id:'fixture',mode:'engineering',worker_id:spec.production_operation.publisher_worker_id,branch:'engineering/fixture',expires_at:new Date(now+3600000).toISOString()};
function window(){return {version:1,source_issue:783,phase:'apply',reservation_issue:900,claim_id:claim.claim_id,operator_worker_id:claim.worker_id,claim_branch:claim.branch,primary_main_commit:head,tool_sha256:toolSHA,reservation_scope_sha256:sha(JSON.stringify(spec)),observed_at_utc:new Date(now).toISOString(),expires_at_utc:new Date(now+3600000).toISOString(),read_only:true,drain_verified:true,site:{project_id:'appgprj_6abdf87277c08191bce4a22b8dfb25db',version:24,deployment_id:'appgdep_fixture'},backup:{run_id:1,dump_sha256:'c'.repeat(64),source_fingerprint:'d'.repeat(64),private_recipient_decryption_verified:true},registry_deployment_id:1,operation_id:'synthetic-operation-123'};}
const validate=(w,c=claim,i=issue)=>validateCompactProductionWindow(w,c,i,{head,toolSHA,now});
test('bounded publisher maintenance accepts only complete current main/claim/scope/recipient window',()=>{assert.equal(validate(window()).phase,'apply');for(const [field,value]of [['primary_main_commit','e'.repeat(40)],['tool_sha256','e'.repeat(64)],['read_only',false],['drain_verified',false],['registry_deployment_id',0],['expires_at_utc',new Date(now).toISOString()]]){const w=window();w[field]=value;assert.throws(()=>validate(w));}assert.throws(()=>validate(window(),{...claim,live_work:false}));assert.throws(()=>validate(window(),claim,{...issue,body:issue.body.replace('Bounded','Changed')}));const w=window();w.backup.private_recipient_decryption_verified=false;assert.throws(()=>validate(w));});
test('retirement additionally requires native backup preservation and live API parity',()=>{const w=window();w.phase='retire';assert.throws(()=>validate(w));w.native_backup_preserved=true;assert.throws(()=>validate(w));w.public_api_parity_verified=true;assert.equal(validate(w).phase,'retire');});
test('database-only retirement needs matching scoped authorization and cannot claim served parity',()=>{const w=window();w.phase='retire';w.native_backup_preserved=true;w.database_only=true;w.site_deployment_postponed=true;assert.throws(()=>validate(w));const scoped={...issue,body:'<!-- worldatlas-work:v1\n'+JSON.stringify({...spec,production_operation:{...spec.production_operation,database_only:true}})+'\n-->'};w.reservation_scope_sha256=sha(JSON.stringify({...spec,production_operation:{...spec.production_operation,database_only:true}}));assert.equal(validate(w,claim,scoped).phase,'retire');w.public_api_parity_verified=true;assert.throws(()=>validate(w,claim,scoped));delete w.public_api_parity_verified;w.site_deployment_postponed=false;assert.throws(()=>validate(w,claim,scoped));});
test('untrusted production maintenance makes no provider calls and preserves sanitized failure receipt',async()=>{const output=fs.mkdtempSync(path.join(os.tmpdir(),'compact-owner-test-'))+'/receipt';let calls=0;try{const r=await runCompactMembershipProduction({env:{NEON_API_KEY:'secret-fixture'},fetcher:()=>{calls++;throw Error('unexpected');},output});assert.equal(r.status,'failed');assert.equal(calls,0);assert.equal(fs.readFileSync(output+'/receipt.json','utf8').includes('secret-fixture'),false);}finally{fs.rmSync(path.dirname(output),{recursive:true});}});
test('bounded native membership digest preserves raw JSON TEXT spelling and is independent of insertion order',async()=>{const f=await createLocalPostgres();try{await f.engine.exec('DROP TABLE atlas_geographic_memberships; CREATE TABLE atlas_geographic_memberships(release_id text,entity_id text,parent_id text,reference_name text,active integer,source_id text,evidence text)');const row=['r','x',null,null,1,'s',' {"a":1,"a":2} '];await f.engine.query('INSERT INTO atlas_geographic_memberships VALUES($1,$2,$3,$4,$5,$6,$7)',row);const before=(await f.engine.query(nativeMembershipDigestSQL())).rows[0];assert.equal(Number(before.rows),1);assert.match(before.ordered_rows_sha256,/^[a-f0-9]{64}$/);await f.engine.query("UPDATE atlas_geographic_memberships SET evidence=$1",['{"a":2}']);assert.notEqual((await f.engine.query(nativeMembershipDigestSQL())).rows[0].ordered_rows_sha256,before.ordered_rows_sha256);}finally{await f.close();}});
test('stream restore header patch retains COPY bytes beyond first bounded header buffer',()=>{const dir=fs.mkdtempSync(path.join(os.tmpdir(),'native-header-')),file=path.join(dir,'restore.sql'),head="-- dump\nSELECT pg_catalog.set_config('search_path', '', false);\n-- Name: test; Type: TABLE DATA\n",tail='COPY test FROM stdin;\n'+'original raw bytes\n'.repeat(2000)+'\\.\n';try{fs.writeFileSync(file,head+tail,{mode:0o600});patchNativeRestoreFile(file);const bytes=fs.readFileSync(file,'utf8');assert.equal(bytes.slice(bytes.indexOf('\n-- Name: ')),(head+tail).slice((head+tail).indexOf('\n-- Name: ')));assert.ok(bytes.includes('public,pg_catalog'));}finally{fs.rmSync(dir,{recursive:true});}});

const primary={indexname:'atlas_geographic_memberships_pkey',indexdef:'CREATE UNIQUE INDEX atlas_geographic_memberships_pkey ON public.atlas_geographic_memberships USING btree (release_id, entity_id)'};
const parent={indexname:'geographic_membership_parent',indexdef:'CREATE INDEX geographic_membership_parent ON public.atlas_geographic_memberships USING btree (release_id, active, parent_id, entity_id)'};
const page={indexname:'geographic_membership_page',indexdef:'CREATE INDEX geographic_membership_page ON public.atlas_geographic_memberships USING btree (release_id, active, entity_id)'};
test('original index recovery validates exact definitions and is idempotent when no allocation is needed',async()=>{assert.deepEqual(checkOriginalMembershipIndexes([primary,parent,page]),[]);assert.equal(checkOriginalMembershipIndexes([primary]).length,2);assert.throws(()=>checkOriginalMembershipIndexes([primary,{...page,indexdef:page.indexdef.replace('active, ','')} ]));const engine={query:async()=>({rows:[primary,parent,page]}),transaction:async()=>{throw Error('must not allocate existing indexes');}};assert.equal((await restoreOriginalMembershipIndexes(engine,1024**3)).status,'original-indexes-restored');await assert.rejects(restoreOriginalMembershipIndexes({...engine,query:async()=>({rows:[primary]})},1024**3),/headroom/);});

test('server copy and precommit runtime hook keep the original intact on failed verification',async()=>{
 const {rehearseCompactMembershipStorage}=await import('../scripts/compact-membership-storage.mjs');const f=await createLocalPostgres();try{
  await assert.rejects(rehearseCompactMembershipStorage(f.engine,{copyOnServer:true,afterSwitch:()=>{throw Error('incompatible runtime');}}),/incompatible runtime/);
  assert.equal((await f.engine.query("SELECT relkind FROM pg_class WHERE oid='atlas_geographic_memberships'::regclass")).rows[0].relkind,'r');
  assert.equal((await f.engine.query("SELECT to_regclass('worldatlas_membership_rows') value")).rows[0].value,null);
  const r=await rehearseCompactMembershipStorage(f.engine,{copyOnServer:true});assert.equal(r.copied,0);assert.equal(r.parity.exact,true);
 }finally{await f.close();}
});


test('retirement app proof runs after owner commit and retains committed state on later failure',async()=>{
 for(const failure of [null,'prepare','before-drop','drop','before-commit','after']){
  const events=[];let committed=false;
  const fail=point=>{events.push(point);if(failure===point)throw Error(point);};
  const engine={transaction:async fn=>{events.push('begin');try{const value=await fn({query:async sql=>{if(sql.startsWith('DROP'))fail('drop');else events.push('lock');}});events.push('commit');return value;}catch(error){events.push('rollback');throw error;}}};
  const run=()=>commitMembershipRetirement(engine,{
   prepare:async()=>{fail('prepare');events.push('before-api');return {exact:true};},
   authorize:async point=>fail(point),onCommitted:parity=>{assert.deepEqual(parity,{exact:true});committed=true;events.push('committed-receipt');},
   afterCommit:async()=>{assert.equal(events.at(-1),'committed-receipt');assert.equal(committed,true);fail('after');}
  });
  if(failure)await assert.rejects(run(),new RegExp(failure));else assert.deepEqual(await run(),{exact:true});
  assert.equal(committed,failure===null||failure==='after');
  if(committed){assert.ok(events.indexOf('commit')<events.indexOf('after'));assert.ok(!events.includes('rollback'));}
  else{assert.ok(events.includes('rollback'));assert.ok(!events.includes('after'));}
 }
});


test('unconfirmed owner commit never reports committed retirement or starts final application proof',async()=>{
 let notified=false,proved=false;
 const engine={transaction:async fn=>{await fn({query:async()=>{}});throw Error('commit transport unavailable');}};
 await assert.rejects(commitMembershipRetirement(engine,{prepare:async()=>({exact:true}),authorize:async()=>{},onCommitted:()=>{notified=true;},afterCommit:async()=>{proved=true;}}),/commit transport/);
 assert.equal(notified,false);assert.equal(proved,false);
});
