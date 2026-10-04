/** Offline full-size rehearsal of the actual compatibility DDL and copier.
 * Synthetic shared registries support pinned original membership rows; this
 * does not publish or scientifically approve any prepared release. */
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {performance} from 'node:perf_hooks';
import {PGlite} from '@electric-sql/pglite';
import {createPostgresDatabase} from '../hosted/postgres-adapter.js';
import {inspectInputs,preparedBatches,insertOriginal,measureRelations,allocatedBytes,digest,canonicalJSON} from './benchmark-membership-storage.mjs';
import {rehearseCompactMembershipStorage,rehearseCompactMembershipRollback} from './compact-membership-storage.mjs';
import {compactMembershipCatalog} from '../hosted/membership-storage-profile.js';
import {provisionPostgresRuntimeRole} from './provision-postgres-runtime-role.mjs';
import {forwardMigrationDefinitions} from './neon-forward-migrations.mjs';
import {verifyCompactMembershipRuntime} from './verify-compact-membership-runtime.mjs';
const need=(value,message)=>{if(!value)throw Error(message);};
export async function benchmarkCompactMembershipProfile({directory,output,target,onProgress=()=>{}}){
 need(path.isAbsolute(output)&&path.isAbsolute(target)&&!fs.existsSync(output)&&!fs.existsSync(target),'Fresh absolute output and target required');
 const input=inspectInputs(directory),frozenRaw=fs.readFileSync('coordination/engineering/membership-storage-20261004-local01/result.json'),reference=JSON.parse(frozenRaw);
 need(digest(JSON.stringify(input.inventory,null,2)+'\n')===reference.input_inventory_sha256,'Frozen complete input pins differ');
 const receipt={version:1,scope:'isolated-full-size-compatible-membership-storage',complete:false,input_inventory_sha256:reference.input_inventory_sha256,frozen_result_sha256:digest(frozenRaw),
  ddl_sha256:digest(fs.readFileSync('postgres/membership-storage-v1.sql')),copier_sha256:digest(fs.readFileSync('scripts/compact-membership-storage.mjs')),script_sha256:digest(fs.readFileSync(import.meta.filename)),
  node:process.version,limits:['All 508,777 raw prepared memberships over six retained releases; synthetic shared registry descriptions and empty other fact collections, not a production export/backup or served release proof.',
   'Original/final core plus V2 forward schemas, original guards, actual compact DDL, runtime roles and strict new export catalogs are installed. Loading fixture membership rows disables only their USER guards in the isolated target, then restores them before migration.',
   'Actual relation sizes and sampled local allocated bytes; not provider logical billing, guaranteed peak, native remote concurrency or a backup.',
   'Original physical rows remain until byte-exact parity and successful no-new-writes rollback. The final footprint measurement discards only the verified disposable original fixture heap.']};
 fs.mkdirSync(path.dirname(output),{recursive:true});fs.mkdirSync(target);const save=()=>fs.writeFileSync(output,JSON.stringify(receipt,null,2)+'\n',{mode:0o600});save();const engine=new PGlite(target);
 const driver={query:(sql,args)=>engine.query(sql,args),runTransaction:fn=>engine.transaction(fn)},db=createPostgresDatabase({query:(sql,args)=>engine.query(sql,args),transaction:statements=>engine.transaction(async tx=>{const results=[];for(const statement of statements)results.push(await tx.query(statement.query,statement.params??[]));return results;})});
 try{
  await engine.exec(fs.readFileSync('postgres/schema.sql','utf8'));for(const item of forwardMigrationDefinitions.slice(0,2))await engine.exec(fs.readFileSync(item.file,'utf8'));
  await engine.exec('ALTER TABLE atlas_entities DISABLE TRIGGER USER; ALTER TABLE atlas_geographic_memberships DISABLE TRIGGER USER');
  const insert=async(table,fields,types,values)=>{for(let i=0;i<values.length;i+=200)await engine.query(`INSERT INTO ${table} (${fields.join(',')}) SELECT ${fields.join(',')} FROM json_to_recordset($1::json) x(${fields.map((k,n)=>k+' '+types[n]).join(',')})`,[JSON.stringify(values.slice(i,i+200))]);};
  const types=JSON.parse(fs.readFileSync('data/hosted-type-catalog.json')).entity_types;
  await insert('atlas_entity_types',['id','name','geographic_level'],['text','text','integer'],types);
  await insert('atlas_sources',['id','name','license','vintage','supported_from','supported_to','status'],['text','text','text','text','integer','integer','text'],[...input.sources].map(id=>({id,name:'Isolated fixture source',license:'Test-only',vintage:'2026',supported_from:2026,supported_to:2027,status:'reference'})));
  await insert('atlas_entities',['id','kind','name'],['text','text','text'],[...input.entities].map(([id,kind])=>({id,kind,name:'Isolated '+id})));
  const releaseFields=['id','source_id','version','reference_date','hierarchy_sha256','footprints_sha256','membership_sha256','location_ids_sha256','changes_sha256','expected_counts','metadata'];
  await insert('atlas_geographic_releases',releaseFields,releaseFields.map(k=>k==='version'?'integer':'text'),input.manifest.releases.map(r=>({...r,expected_counts:JSON.stringify(r.expected_counts),metadata:JSON.stringify(r.metadata??{})})));
  let count=0;for(const batch of preparedBatches(directory,input.manifest)){await engine.transaction(tx=>insertOriginal(tx,batch.rows));count+=batch.rows.length;if(count%20000===0)onProgress({stage:'seed',rows:count});}
  receipt.rows=count;await engine.exec('ALTER TABLE atlas_entities ENABLE TRIGGER USER; ALTER TABLE atlas_geographic_memberships ENABLE TRIGGER USER; ANALYZE');
  await provisionPostgresRuntimeRole({driver,password:'isolated-rehearsal-only-0123456789-never-live'});
  for(const item of forwardMigrationDefinitions.slice(0,2))for(const table of item.tables)await engine.query('GRANT SELECT'+(item.readOnlyTables.includes(table)?'':',INSERT')+' ON '+table+' TO worldatlas_app');
  receipt.before=await measureRelations(engine);save();
  await engine.exec('DROP INDEX geographic_membership_page; DROP INDEX geographic_membership_parent');
  receipt.after_committed_index_drop=await measureRelations(engine);onProgress({stage:'copy'});
  const start=performance.now();receipt.copy=await rehearseCompactMembershipStorage(engine);receipt.copy_ms=performance.now()-start;
  receipt.retained_original=await measureRelations(engine);receipt.profile=await compactMembershipCatalog(db);receipt.runtime=await verifyCompactMembershipRuntime(driver,forwardMigrationDefinitions.slice(0,2));save();
  // Compare all previously pinned nonempty public lookup results in the actual view.
  const sql={page:'SELECT * FROM atlas_geographic_memberships WHERE release_id=$1 AND active=1 AND entity_id>$2 COLLATE "C" ORDER BY entity_id COLLATE "C" LIMIT 200',
   'midpoint-page':'SELECT * FROM atlas_geographic_memberships WHERE release_id=$1 AND active=1 AND entity_id>$2 COLLATE "C" ORDER BY entity_id COLLATE "C" LIMIT 200',
   parent:'SELECT * FROM atlas_geographic_memberships WHERE release_id=$1 AND active=1 AND parent_id=$2 ORDER BY entity_id COLLATE "C" LIMIT 200',
   'largest-parent':'SELECT * FROM atlas_geographic_memberships WHERE release_id=$1 AND active=1 AND parent_id=$2 ORDER BY entity_id COLLATE "C" LIMIT 200',identity:'SELECT * FROM atlas_geographic_memberships WHERE release_id=$1 AND entity_id=$2'};
  receipt.queries=[];for(const p of reference.targets.original.queries){const start=performance.now(),rows=(await engine.query(sql[p.kind],p.args)).rows;need(rows.length===p.rows&&digest(canonicalJSON(rows))===p.result_sha256,'Pinned public lookup differs');receipt.queries.push({...p,elapsed_ms:[performance.now()-start]});}
  receipt.allocated_before_rollback=allocatedBytes(target);need(receipt.allocated_before_rollback<=6*1024**3,'Owned rehearsal target exceeds 6 GiB bound');
  receipt.rollback=await rehearseCompactMembershipRollback(engine);save();onProgress({stage:'second-copy'});
  receipt.second_copy=await rehearseCompactMembershipStorage(engine);
  await engine.exec('DROP TABLE worldatlas_memberships_original_v1');receipt.final=await measureRelations(engine);receipt.final_profile=await compactMembershipCatalog(db);
  receipt.reduction_bytes=receipt.before.total_relation_bytes-receipt.final.total_relation_bytes;receipt.complete=true;save();return receipt;
 }catch(error){receipt.failure=error.message;save();throw error;}finally{await engine.close();}
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){const [directory,output,target]=process.argv.slice(2);const r=await benchmarkCompactMembershipProfile({directory,output,target,onProgress:p=>console.log(JSON.stringify(p))});console.log(JSON.stringify({complete:r.complete,before:r.before.total_relation_bytes,after:r.final.total_relation_bytes,saved:r.reduction_bytes,rows:r.rows,copy_ms:r.copy_ms}));}
