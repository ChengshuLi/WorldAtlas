import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createLocalPostgres} from '../scripts/verify-postgres-schema.mjs';
import {importBatch} from '../hosted/records.js';
import {stageGeographicRelease,finalizeGeographicRelease,geographicMembershipPage,geographicMembershipHash,geographicLocationIdsHash,geographicChangesHash} from '../hosted/geographic-releases.js';
import {rehearseCompactMembershipStorage,rehearseCompactMembershipRollback} from '../scripts/compact-membership-storage.mjs';
import {compactMembershipCatalog} from '../hosted/membership-storage-profile.js';
import {createPostgresDatabase} from '../hosted/postgres-adapter.js';
import {exportStorageMarkerV4,exportStoragePageV4} from '../hosted/storage-export-v4.js';
import {storageCatalogV2} from '../hosted/storage-export-v2.js';
import {storageCatalogV3} from '../hosted/storage-export-v3.js';
import {storageExportV2Definitions} from '../hosted/storage-export-v2-contract.js';
import {storageExportV3Definitions} from '../hosted/storage-export-v3-contract.js';
import {provisionPostgresRuntimeRole} from '../scripts/provision-postgres-runtime-role.mjs';
import {verifyCompactMembershipRuntime} from '../scripts/verify-compact-membership-runtime.mjs';
import {forwardMigrationDefinitions} from '../scripts/neon-forward-migrations.mjs';
import {typedCapabilities} from '../hosted/typed-observations.js';
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

async function forward(f,version){
 const driver={query:(sql,args)=>f.engine.query(sql,args),runTransaction:fn=>f.engine.transaction(fn)};
 await provisionPostgresRuntimeRole({driver,password:'isolated-profile-only-password-0123456789'});
 const definitions=forwardMigrationDefinitions.slice(0,version);
 for(const item of definitions){
  await f.engine.exec(fs.readFileSync(new URL('../'+item.file,import.meta.url),'utf8'));
  for(const table of item.tables)await f.engine.query('GRANT SELECT'+(item.readOnlyTables.includes(table)?'':',INSERT')+' ON '+table+' TO worldatlas_app');
 }
 return {driver,definitions};
}
for(const version of [2,3])test('compact V4 preserves every raw collection and restricted runtime over frozen V'+version,async()=>{
 const f=await fixture();try{
  const {driver,definitions}=await forward(f,version),tables=version===2?storageExportV2Definitions:storageExportV3Definitions;
  const before={};for(const [collection,d]of Object.entries(tables))before[collection]=(await f.db.prepare('SELECT '+d.columns.map(x=>'\"'+x+'\"').join(',')+' FROM '+d.table+' ORDER BY '+d.keys.join(',')).all()).results;
  await rehearseCompactMembershipStorage(f.engine);
  await assert.rejects(version===2?storageCatalogV2(f.db):storageCatalogV3(f.db),/reviewed migration pins/);
  const proof=await verifyCompactMembershipRuntime(driver,definitions);assert.equal(proof.status,'verified');
  await f.engine.exec('SET ROLE worldatlas_app');
  try{
   const marker=await exportStorageMarkerV4(f.db);assert.equal(marker.version,4);assert.equal(marker.contract.base_contract.version,version);
   for(const [collection,expected]of Object.entries(before)){
    let cursor='',result=[];do{const page=await exportStoragePageV4(f.db,collection,{cursor,limit:7});result.push(...page.records);cursor=page.next_cursor;}while(cursor);
    assert.deepEqual(result,expected,collection);assert.equal(marker.counts[collection],expected.length);
   }
   assert.equal((await typedCapabilities(f.db)).storage_export,version===3?4:0);
   await assert.rejects(f.engine.query('SELECT * FROM worldatlas_membership_evidence'),/permission denied/);
  }finally{await f.engine.exec('RESET ROLE');}
  await f.engine.exec('DROP TABLE worldatlas_memberships_original_v1');
  assert.equal((await compactMembershipCatalog(f.db)).profile,'compact-only');
  assert.equal((await verifyCompactMembershipRuntime(driver,definitions)).status,'verified');
 }finally{await f.close();}
});

test('compact profile rejects changed lookup/guard/index/ACL contracts and extra private tables',async()=>{
 const f=await fixture();try{
  await forward(f,2);await rehearseCompactMembershipStorage(f.engine);
  await f.engine.exec('CREATE ROLE extra_reader NOLOGIN; GRANT USAGE ON SCHEMA public TO extra_reader');
  for(const mutation of ['ALTER TABLE worldatlas_membership_rows DISABLE TRIGGER worldatlas_membership_immutable',
   'GRANT SELECT ON worldatlas_membership_evidence TO worldatlas_app',
   'GRANT SELECT(raw) ON worldatlas_membership_evidence TO worldatlas_app',
   'GRANT SELECT(raw) ON worldatlas_membership_evidence TO extra_reader',
   'ALTER FUNCTION worldatlas_membership_insert() OWNER TO extra_reader',
   'ALTER SEQUENCE worldatlas_membership_evidence_key_seq OWNER TO extra_reader',
   'GRANT USAGE ON SEQUENCE worldatlas_membership_evidence_key_seq TO worldatlas_app',
   'GRANT EXECUTE ON FUNCTION worldatlas_membership_copy_batch(json) TO PUBLIC',
   'CREATE TABLE worldatlas_membership_unreviewed(id text)',
   'CREATE OR REPLACE VIEW atlas_geographic_memberships AS SELECT * FROM worldatlas_membership_projection WHERE false',
   'DROP INDEX worldatlas_membership_parent']){
   await assert.rejects(f.engine.transaction(async tx=>{await tx.query(mutation);await compactMembershipCatalog({...f.db,prepare(sql){let args=[];return {bind(...p){args=p;return this;},async all(){return {results:(await tx.query(sql,args)).rows};},async first(){return (await tx.query(sql,args)).rows[0]??null;}};}});}));
   assert.equal((await compactMembershipCatalog(f.db)).profile,'retained-original');
  }
  const internal=(await f.engine.query("SELECT tgname FROM pg_trigger WHERE tgrelid='worldatlas_membership_rows'::regclass AND tgisinternal LIMIT 1")).rows[0].tgname;
  await assert.rejects(f.engine.transaction(async tx=>{await tx.query('ALTER TABLE worldatlas_membership_rows DISABLE TRIGGER \"'+internal+'\"');await compactMembershipCatalog({...f.db,prepare(sql){return {async all(){return {results:(await tx.query(sql)).rows};}};}});}));
 }finally{await f.close();}
});

test('bulk owner copy preserves duplicate JSON keys and rolls back missing keys/duplicate identities',async()=>{
 const f=await fixture();try{
  await forward(f,2);await rehearseCompactMembershipStorage(f.engine);
  const before=(await f.engine.query('SELECT count(*)::int n FROM worldatlas_membership_rows')).rows[0].n;
  await assert.rejects(f.engine.query('SELECT worldatlas_membership_copy_batch($1::json)',[JSON.stringify([{release_id:'missing',entity_id:'0:continent',parent_id:null,reference_name:null,active:1,source_id:'ref',evidence:'{"a":0,"a":1}'}])]),/foreign key/);
  assert.equal((await f.engine.query('SELECT count(*)::int n FROM worldatlas_membership_rows')).rows[0].n,before);
  await assert.rejects(f.engine.query('SELECT worldatlas_membership_copy_batch($1::json)',[JSON.stringify((await f.engine.query('SELECT * FROM atlas_geographic_memberships LIMIT 1')).rows)]),/duplicate key/);
  await rehearseCompactMembershipRollback(f.engine);assert.equal((await f.engine.query('SELECT count(*)::int n FROM atlas_geographic_memberships')).rows[0].n,36);
 }finally{await f.close();}
});

test('V4 bounded export and logical restore retain exact original fields in an independent empty base target',async()=>{
 const {exportHostedStorageV4}=await import('../scripts/export-hosted-storage-v4.mjs');
 const {restorePostgresStorageV4}=await import('../scripts/restore-postgres-storage-v4.mjs');
 const os=await import('node:os'),path=await import('node:path');
 const output=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-v4-export-'));
 const f=await fixture(),target=await createLocalPostgres();try{
  await forward(f,2);await rehearseCompactMembershipStorage(f.engine);
  for(const name of ['0001_temporal_geography','0002_footprint_versions'])await target.engine.exec(fs.readFileSync(new URL('../postgres/migrations/'+name+'.sql',import.meta.url),'utf8'));
  const fetcher=async url=>{const u=new URL(url);return Response.json(u.pathname.endsWith('export-marker')?{...await exportStorageMarkerV4(f.db),read_only:true}:await exportStoragePageV4(f.db,u.pathname.split('/').at(-1),{cursor:u.searchParams.get('cursor')??'',limit:Number(u.searchParams.get('limit')??200)}));};
  const manifest=await exportHostedStorageV4({origin:'https://example.org/',output,token:'isolated-secret-never-log',fetcher});
  assert.equal(manifest.version,4);assert.equal(manifest.collections.geographic_memberships.count,36);
  const driver={query:(sql,args)=>target.engine.query(sql,args),runTransaction:fn=>target.engine.transaction(fn)};
  const receipt=await restorePostgresStorageV4({directory:output,driver,acknowledgeOwnerRestore:true});
  assert.equal(receipt.status,'restored');assert.equal(receipt.native_owner_metadata_restored,false);
  assert.deepEqual((await target.engine.query('SELECT * FROM atlas_geographic_memberships ORDER BY release_id,entity_id')).rows,(await f.engine.query('SELECT * FROM atlas_geographic_memberships ORDER BY release_id,entity_id')).rows);
  const part=manifest.collections.geographic_memberships.parts[0];fs.appendFileSync(path.join(output,part.path),' ');
  await assert.rejects(restorePostgresStorageV4({directory:output,dryRun:true}),/bytes changed/);
 }finally{await f.close();await target.close();fs.rmSync(output,{recursive:true});}
});

test('compact typed imports and paged snapshots preserve zero, false, retries and maintenance guards',async()=>{
 const {typedSourcePins}=await import('../hosted/typed-observations.js'),{observationContract}=await import('../src/observation-modules.js'),{default:worker}=await import('../hosted/worker.js');
 const f=await fixture();try{
  await forward(f,3);await rehearseCompactMembershipStorage(f.engine);
  await importBatch(f.db,{sources:[{id:'example',name:'Synthetic example',url:'https://example.org/test-only',license:'CC0',vintage:'2026',supported_from:-3000,supported_to:2027,status:'example'}]});
  const contract=await observationContract(),sources=(await f.db.prepare("SELECT * FROM atlas_sources WHERE id='example'").all()).results;
  const payload={version:1,registry_sha256:contract.registry_sha256,expected_geography:{release_id:f.first.id,hierarchy_sha256:f.first.hierarchy_sha256,footprints_sha256:f.first.footprints_sha256},source_pins:await typedSourcePins(sources),examples:true,observations:[{id:'compact-false',subject_id:'0:location',subject_kind:'location',field_id:'atlas.marine-contact',value:false,valid_from:-100,valid_to:-99,source_id:'example',is_example:1},{id:'compact-zero',subject_id:'1:location',subject_kind:'location',field_id:'atlas.adult-literacy',value:0,valid_from:-100,valid_to:-99,source_id:'example',is_example:1,metadata:{measurement:{unit:'percent',definition:'Synthetic test',cohort:'age-15-plus',period:{from:-100,to:-99}}},original_json:{value:'0.00'}}]};
  const request=(url,options={},env={})=>worker.fetch(new Request('https://example.org'+url,options),{DB:f.db,...env},{});
  const options={method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)};
  const first=await request('/api/typed/v1/import',options);assert.equal(first.status,200,await first.clone().text());
  assert.equal((await (await request('/api/typed/v1/import',options)).json()).duplicate,true);
  assert.equal((await f.db.prepare("SELECT value FROM atlas_typed_observations WHERE id='compact-zero'").first()).value,'0.00');
  const page=await (await request('/api/typed/v1/snapshot?year=-100&examples=1&limit=1')).json();assert.equal(page.total,2);assert.ok(page.next_cursor);
  const next=await (await request('/api/typed/v1/snapshot?year=-100&examples=1&limit=1&cursor='+encodeURIComponent(page.next_cursor))).json();assert.equal(next.fingerprint,page.fingerprint);assert.notEqual(next.rows[0].id,page.rows[0].id);
  assert.equal((await request('/api/typed/v1/import',options,{ATLAS_READ_ONLY:'1'})).status,503);
 }finally{await f.close();}
});

test('V4 export resumes durable pages after interruption and adapts to bounded 413 responses',async()=>{
 const {exportHostedStorageV4}=await import('../scripts/export-hosted-storage-v4.mjs'),os=await import('node:os'),path=await import('node:path');
 const output=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-v4-resume-')),f=await fixture();try{
  await forward(f,2);await rehearseCompactMembershipStorage(f.engine);
  const abort=new AbortController();let oversized=false,pages=0;
  const fetcher=async input=>{const u=new URL(input);if(u.pathname.endsWith('export-marker'))return Response.json({...await exportStorageMarkerV4(f.db),read_only:true});
   if(!oversized&&u.pathname.endsWith('/geographic_memberships')){oversized=true;return Response.json({retryable:true,suggested_limit:7},{status:413});}
   const page=await exportStoragePageV4(f.db,u.pathname.split('/').at(-1),{cursor:u.searchParams.get('cursor')??'',limit:Number(u.searchParams.get('limit')??200)});pages++;return Response.json(page);};
  await assert.rejects(exportHostedStorageV4({origin:'https://example.org',output,token:'isolated-no-log',fetcher,concurrency:1,signal:abort.signal,onProgress:()=>abort.abort(Error('controlled interruption'))}),/controlled interruption/);
  assert.ok(pages>0);let countBefore=pages;
  const manifest=await exportHostedStorageV4({origin:'https://example.org',output,token:'isolated-no-log',fetcher,concurrency:1});assert.equal(manifest.collections.geographic_memberships.count,36);assert.ok(oversized);assert.ok(pages>countBefore);
  assert.ok(manifest.collections.geographic_memberships.parts.length>1);
 }finally{await f.close();fs.rmSync(output,{recursive:true});}
});

// Count driver invocations rather than SQL statements: a Neon HTTP transaction
// sends all of its ordered SELECT statements in one external request.
function requestBudgetDatabase(engine,{budget=50,batch=true,afterQuery}={}){
 const counts={requests:0,selects:0,batches:0};
 const request=()=>{if(++counts.requests>budget)throw Error('Isolated external request budget exceeded');};
 const query=async(sql,args=[])=>{assert.match(sql,/^SELECT\b/i);counts.selects++;const result=await engine.query(sql,args);await afterQuery?.(sql);return result;};
 const db=createPostgresDatabase({
  query:async(sql,args)=>{request();return query(sql,args);},
  transaction:async(statements,options)=>{request();counts.batches++;assert.equal(options.isolationLevel,'Serializable');return engine.transaction(async tx=>{
   const results=[];for(const statement of statements){assert.match(statement.query,/^SELECT\b/i);counts.selects++;results.push(await tx.query(statement.query,statement.params));}return results;
  });}
 });
 if(!batch)delete db.batch;
 return {db,counts};
}

test('V4 metadata batching preserves exact pages and checks under a bounded external request budget',async()=>{
 const f=await fixture();try{
  await forward(f,3);await rehearseCompactMembershipStorage(f.engine);await f.engine.exec('DROP TABLE worldatlas_memberships_original_v1');
  const legacy=requestBudgetDatabase(f.engine,{budget:100,batch:false});
  const expected=await exportStoragePageV4(legacy.db,'geographic_memberships',{limit:7});
  const boundedLegacy=requestBudgetDatabase(f.engine,{batch:false});
  await assert.rejects(exportStoragePageV4(boundedLegacy.db,'geographic_memberships',{limit:7}),/temporarily unavailable/);
  assert.equal(boundedLegacy.counts.requests,51);
  const candidate=requestBudgetDatabase(f.engine);
  assert.deepEqual(await exportStoragePageV4(candidate.db,'geographic_memberships',{limit:7}),expected);
  assert.equal(candidate.counts.selects,legacy.counts.selects);
  assert.equal(legacy.counts.requests,52);assert.equal(candidate.counts.requests,34);assert.equal(candidate.counts.batches,4);
  const all=[];let cursor='';do{
   const page=await exportStoragePageV4(requestBudgetDatabase(f.engine).db,'geographic_memberships',{limit:7,cursor});
   all.push(...page.records);cursor=page.next_cursor;
  }while(cursor);
  assert.deepEqual(all,(await f.engine.query('SELECT * FROM atlas_geographic_memberships ORDER BY release_id,entity_id')).rows);
  await assert.rejects(exportStoragePageV4(requestBudgetDatabase(f.engine).db,'geographic_memberships',{cursor:'invalid'}),/cursor/);
 }finally{await f.close();}
});

test('batched V4 catalog remains fail closed for ACL exposure, disabled guards and failed transactions',async()=>{
 const f=await fixture();try{
  await forward(f,3);await rehearseCompactMembershipStorage(f.engine);
  for(const mutation of ['GRANT SELECT(raw) ON worldatlas_membership_evidence TO worldatlas_app','ALTER TABLE worldatlas_membership_rows DISABLE TRIGGER worldatlas_membership_immutable']){
   await assert.rejects(f.engine.transaction(async tx=>{
    await tx.query(mutation);
    const db=createPostgresDatabase({query:(sql,args)=>tx.query(sql,args),transaction:async statements=>{
     const results=[];for(const item of statements)results.push(await tx.query(item.query,item.params));return results;
    }});
    await exportStoragePageV4(db,'geographic_memberships');
   }),/privileges are exposed|Unverified compact owner or guards/);
   assert.equal((await compactMembershipCatalog(f.db)).profile,'retained-original');
  }
  const db={...f.db,batch:async()=>{throw Error('Controlled metadata transaction failure');}};
  await assert.rejects(exportStorageMarkerV4(db),/Controlled metadata transaction failure/);
 }finally{await f.close();}
});

test('V4 batching rechecks private privileges after reading a page',async()=>{
 const f=await fixture();try{
  await forward(f,3);await rehearseCompactMembershipStorage(f.engine);
  let injected=false;
  const {db}=requestBudgetDatabase(f.engine,{afterQuery:async sql=>{
   if(!injected&&sql.startsWith('SELECT "release_id","entity_id"')){
    injected=true;await f.engine.exec('GRANT SELECT(raw) ON worldatlas_membership_evidence TO worldatlas_app');
   }
  }});
  await assert.rejects(exportStoragePageV4(db,'geographic_memberships'),/privileges are exposed/);
  assert.equal(injected,true);
 }finally{await f.close();}
});
