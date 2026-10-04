import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {storageCatalogV3} from '../hosted/storage-export-v3.js';
import {storageCatalogV2} from '../hosted/storage-export-v2.js';
import {checkedStorageV4Contract,v4MarkerIdentity} from '../hosted/storage-export-v4-contract.js';
import {storageExportV3Collections as storageExportCollections,storageExportV3Columns as storageExportColumns,storageExportV3Definitions,storageExportV3Contract,v3MarkerIdentity} from '../hosted/storage-export-v3-contract.js';

const hash=value=>createHash('sha256').update(value).digest('hex');
const table=collection=>storageExportV3Definitions[collection].table;
const keys=collection=>storageExportV3Definitions[collection].keys;
const integerColumns=new Set(['contract_version','rowid','created_at','bytes','valid_from','valid_to','supported_from','supported_to','is_example','active','version','published_at','geographic_level','grid_size','offset','words','decoded_bytes','location_count','object_count','reference_year','ordinal','width','height','grid_width','grid_height','row_count','location_index_start','location_index_end']);
const restoreOrder=['sources','entity_types','entities','categories','records','media','names','relationships','media_links','retirements','geographic_releases','geographic_memberships','geographic_changes','temporal_geography_validations','geographic_membership_records','geographic_existence_records','temporal_geography_retirements','footprint_versions','footprint_version_objects','footprint_selection_validations','geographic_footprint_records','footprint_retirements','typed_observations','typed_feature_links','typed_retirements','ingestions'];
const expectedTargetSchema='1a43333772e6059d4fa97ce60baad7a27239616693c86708d08eadbc73b97618';
const identifiers=columns=>columns.map(column=>'"'+column+'"').join(',');
const equal=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
function canonicalRow(row,columns,{postgres=false}={}){
 return Object.fromEntries(columns.map(column=>{let value=row[column];if(postgres&&value!=null&&integerColumns.has(column)){value=Number(value);if(!Number.isSafeInteger(value))throw Error('Unsafe PostgreSQL restored integer');}return [column,value];}));
}
function compareRows(collection,a,b){for(const key of keys(collection)){const order=key==='rowid'?a[key]-b[key]:Buffer.compare(Buffer.from(a[key]),Buffer.from(b[key]));if(order)return order;}return 0;}
export function storageRowsHashV3Ordered(collection,rows){
 const digest=createHash('sha256');digest.update('[');let previous=null,count=0;
 for(const row of rows){if(previous&&compareRows(collection,previous,row)>=0)throw Error('Duplicate or unordered raw source identity');if(count++)digest.update(',');digest.update(JSON.stringify(canonicalRow(row,storageExportColumns[collection])));previous=row;}digest.update(']');return digest.digest('hex');
}
export function storageRowsHashV3(collection,rows){return storageRowsHashV3Ordered(collection,[...rows].sort((a,b)=>compareRows(collection,a,b)));}
function safeFile(directory,name){if(typeof name!=='string'||path.isAbsolute(name)||name.split(/[\\/]/).some(part=>!part||part==='..'))throw Error('Unsafe storage snapshot path');const result=path.resolve(directory,name),root=fs.realpathSync(directory),real=fs.realpathSync(result);if(!real.startsWith(root+path.sep))throw Error('Storage snapshot path escapes its directory');return result;}
const markerIdentity=v4MarkerIdentity;
export function readVerifiedStorageSnapshotV4(directory){
 const raw=fs.readFileSync(path.join(directory,'index.json')),manifest=JSON.parse(raw),marker=manifest.snapshot_marker;
 checkedStorageV4Contract(manifest.contract);const storageExportCollections=Object.keys(manifest.contract.base_contract.definitions);
 if(manifest.version!==4||manifest.status!=='complete'||manifest.read_only!==true||manifest.snapshot_consistent!==true||!['d1','postgres'].includes(manifest.source_backend)||!manifest.format?.json_text_preserved||!manifest.format?.ingestion_rowid_preserved||!manifest.format?.includes_archived_examples_withdrawals)throw Error('Restore requires a completed byte-preserving read-only source snapshot');
 if(!marker||marker.version!==4||marker.read_only!==true||!Number.isSafeInteger(marker.revision)||marker.revision<0||!marker.counts||!equal(Object.keys(manifest.collections??{}).sort(),[...storageExportCollections].sort())||storageExportCollections.some(key=>!Number.isSafeInteger(marker.counts[key])||marker.counts[key]<0)||hash(JSON.stringify(markerIdentity(marker)))!==marker.fingerprint)throw Error('Invalid or unverified source snapshot marker');
 if(!equal(manifest.contract,marker.contract))throw Error('Forward snapshot schema or migration pins changed');
 const collections={},proofs={};let actualRevision=0;
 for(const collection of storageExportCollections){
  const entry=manifest.collections[collection],columns=storageExportColumns[collection];if(!entry||entry.count!==marker.counts[collection]||!equal(entry.columns,columns)||!Array.isArray(entry.parts)||!entry.parts.length)throw Error('Missing raw source table or column proof');
  // Re-open and hash every page when consumed, including during restoration.
  // Historical claims stream in bounded pages; only the identity graph is kept
  // in memory for its dependency ordering. A later file edit cannot bypass proof.
  collections[collection]={[Symbol.iterator]:function*(){
   let cursor='',previous=null,count=0;
   for(const [index,part]of entry.parts.entries()){
    if(part.path!==`${collection}/part-${String(index+1).padStart(6,'0')}.json`||part.start_cursor!==cursor||!Number.isSafeInteger(part.rows)||part.rows<0||part.rows>200||!Number.isSafeInteger(part.bytes)||part.bytes>16*1024*1024||!/^[a-f0-9]{64}$/.test(part.sha256??''))throw Error('Invalid raw source part sequence');
    const bytes=fs.readFileSync(safeFile(directory,part.path));if(bytes.length!==part.bytes||hash(bytes)!==part.sha256)throw Error('Raw source snapshot bytes changed');
    const page=JSON.parse(bytes);if(page.collection!==collection||!equal(page.columns,columns)||!Array.isArray(page.records)||page.records.length!==part.rows||page.next_cursor!==part.end_cursor||page.revision!==marker.revision||page.snapshot_marker?.fingerprint!==marker.fingerprint||hash(JSON.stringify(markerIdentity(page.snapshot_marker)))!==marker.fingerprint)throw Error('Raw source page disagrees with its immutable marker');
    for(const row of page.records){
     if(!row||Array.isArray(row)||!equal(Object.keys(row).sort(),[...columns].sort())||Object.values(row).some(value=>value!==null&&typeof value!=='string'&&!(typeof value==='number'&&Number.isSafeInteger(value))))throw Error('Raw source columns must remain original text or safe integer scalars');
     for(const key of keys(collection))if(key==='rowid'? !Number.isSafeInteger(row[key])||row[key]<1:typeof row[key]!=='string'||!row[key])throw Error('Invalid raw source primary key');
     if(previous&&compareRows(collection,previous,row)>=0)throw Error('Duplicate or unordered raw source identity');previous=row;count++;yield canonicalRow(row,columns);
    }
    if(part.end_cursor===null&&index!==entry.parts.length-1||part.end_cursor!==null&&(typeof part.end_cursor!=='string'||!part.end_cursor))throw Error('Invalid raw source end cursor');cursor=part.end_cursor;
   }
   if(cursor!==null||count!==entry.count)throw Error('Incomplete raw source collection');
  }};
  const ordered_rows_sha256=storageRowsHashV3Ordered(collection,collections[collection]);proofs[collection]={count:entry.count,ordered_rows_sha256};if(entry.ordered_rows_sha256!==ordered_rows_sha256)throw Error('Forward collection raw row hash changed');
 }
 for(const row of collections.ingestions)actualRevision=Math.max(actualRevision,row.rowid);
 if(actualRevision!==marker.revision||proofs.geographic_releases.ordered_rows_sha256!==marker.geographic_releases_sha256||proofs.footprint_versions.ordered_rows_sha256!==marker.footprint_versions_sha256)throw Error('Source revision or geographic releases do not match their marker');
 return {manifest,manifest_sha256:hash(raw),collections,proofs,revision:actualRevision};
}
function topologicalEntities(rows){
 const pending=new Map([...rows].map(row=>[row.id,row])),ordered=[],done=new Set();
 while(pending.size){const ready=[...pending.values()].filter(row=>!row.parent_id||done.has(row.parent_id)).sort((a,b)=>compareRows('entities',a,b));if(!ready.length)throw Error('Raw entity parent is missing or cyclic');for(const row of ready){pending.delete(row.id);done.add(row.id);ordered.push(row);}}
 return ordered;
}
async function resultRows(driver,query,params=[]){const result=await driver.query(query,params);if(!result||!Array.isArray(result.rows))throw Error('Invalid owner PostgreSQL query result');return result.rows;}
async function targetTriggers(driver,storageExportCollections){
 return resultRows(driver,"SELECT c.relname AS table_name,t.tgname AS trigger_name,t.tgenabled AS enabled,pg_get_triggerdef(t.oid) AS definition FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=current_schema() AND NOT t.tgisinternal AND c.relname=ANY($1::text[]) ORDER BY c.relname,t.tgname",[storageExportCollections.map(table)]);
}
async function validateTarget(driver,base){
 const storageExportCollections=Object.keys(base.definitions);
 await (base.version===3?storageCatalogV3:storageCatalogV2)({dialect:'postgres',prepare:query=>({all:async()=>({results:await resultRows(driver,query)})})});
 const allTables=await resultRows(driver,"SELECT table_name FROM information_schema.tables WHERE table_schema=current_schema() AND table_type='BASE TABLE' AND left(table_name,6)='atlas_' ORDER BY table_name");if(!equal(allTables.map(row=>row.table_name),storageExportCollections.map(table).sort()))throw Error('Forward PostgreSQL factual table inventory changed');
 const columns=await resultRows(driver,"SELECT table_name,column_name,data_type FROM information_schema.columns WHERE table_schema=current_schema() AND table_name=ANY($1::text[]) ORDER BY table_name,ordinal_position",[storageExportCollections.map(table)]);
 for(const collection of storageExportCollections){const actual=columns.filter(row=>row.table_name===table(collection));if(!equal(actual.map(row=>row.column_name),storageExportColumns[collection]))throw Error('Target PostgreSQL table inventory does not match the restore contract');for(const name of ['metadata','value','counts','expected_counts','evidence'])if(actual.some(row=>row.column_name===name&&row.data_type!=='text'))throw Error('Target would normalize original JSON evidence bytes');}
 const owned=await resultRows(driver,"SELECT bool_and(c.relowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)) AS owner_ok FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=current_schema() AND c.relname=ANY($1::text[])",[storageExportCollections.map(table)]);if(owned[0]?.owner_ok!==true)throw Error('Restore requires the schema owner, not the runtime application role');
 const triggers=await targetTriggers(driver,storageExportCollections);if(triggers.some(row=>row.enabled!=='O'))throw Error('Target has disabled or nonstandard user triggers');for(const collection of storageExportCollections)for(const expected of [storageExportV3Definitions[collection].guard??'atlas_00_identity','atlas_no_truncate'])if(!triggers.some(row=>row.table_name===table(collection)&&row.trigger_name===expected))throw Error('Target is missing required immutable guards');return triggers;
}
async function verifyCollections(driver,snapshot){
 const storageExportCollections=Object.keys(snapshot.manifest.contract.base_contract.definitions),proofs={};
 for(const collection of storageExportCollections){
  const columns=storageExportColumns[collection],keyColumns=keys(collection),sort=keyColumns.map(key=>key==='rowid'?key:`${key} COLLATE "C"`),digest=createHash('sha256');let cursor=null,count=0,previous=null;digest.update('[');
  while(true){
   const predicate=cursor?` WHERE (${sort.join(',')}) > (${keyColumns.map((_,index)=>`$${index+1}`).join(',')})`:'',rows=(await resultRows(driver,`SELECT ${identifiers(columns)} FROM ${table(collection)}${predicate} ORDER BY ${sort.join(',')} LIMIT 200`,cursor??[])).map(row=>canonicalRow(row,columns,{postgres:true}));
   for(const row of rows){if(previous&&compareRows(collection,previous,row)>=0)throw Error('Restored primary-key pagination is not strictly ordered');if(count)digest.update(',');digest.update(JSON.stringify(row));count++;previous=row;}
   if(rows.length<200)break;cursor=keyColumns.map(key=>rows.at(-1)[key]);
  }
  digest.update(']');const proof={count,ordered_rows_sha256:digest.digest('hex')};if(!equal(proof,snapshot.proofs[collection]))throw Error(`Restored collection does not match original bytes: ${collection}`);proofs[collection]=proof;
 }
 const revision=Number((await resultRows(driver,'SELECT coalesce(max(rowid),0) AS revision FROM atlas_ingestions'))[0].revision);if(revision!==snapshot.revision)throw Error('Restored ingestion revision differs from its source');return proofs;
}
async function verifySequence(driver,revision){const state=(await resultRows(driver,'SELECT last_value,is_called FROM atlas_ingestions_rowid_seq'))[0],last=Number(state.last_value);if(!Number.isSafeInteger(last)||last<1||state.is_called!==false||last!==Math.max(1,revision+1))throw Error('Restored ingestion sequence does not resume after its original revision');return {next_rowid:last,is_called:false,reset_method:'transactional ALTER SEQUENCE RESTART'};}
function writeReceipt(file,value){if(!file)return;fs.mkdirSync(path.dirname(file),{recursive:true});const temporary=`${file}.tmp-${process.pid}`;const fd=fs.openSync(temporary,'w',0o600);try{fs.writeFileSync(fd,JSON.stringify(value,null,2)+'\n');fs.fsyncSync(fd);}finally{fs.closeSync(fd);}fs.renameSync(temporary,file);}
/** Owner-only restoration, never a new-content import. One transaction either
 * restores every original row and all guards, or leaves the target unchanged.
 * Interactive transaction driver keeps large copies out of one HTTP payload.
 */
export async function restorePostgresStorageV4({directory,driver,acknowledgeOwnerRestore=false,verifyOnly=false,dryRun=false,receiptFile=path.join(directory,'postgres-restore-receipt.json'),onProgress=()=>{}}){
 const snapshot=readVerifiedStorageSnapshotV4(directory),logicalBase=snapshot.manifest.contract.base_contract,storageExportCollections=Object.keys(logicalBase.definitions),schemaBytes=fs.readFileSync(new URL('../postgres/schema.sql',import.meta.url));if(hash(schemaBytes)!==expectedTargetSchema)throw Error('Reviewed PostgreSQL restore schema changed; review a forward migration');
 for(const pin of logicalBase.postgres_migrations)if(hash(fs.readFileSync(new URL('../'+pin.path,import.meta.url)))!==pin.sha256)throw Error('Reviewed forward PostgreSQL migration changed');
 const base={version:4,contract:snapshot.manifest.contract,target_profile:'original-base-schema',native_owner_metadata_restored:false,source_manifest_sha256:snapshot.manifest_sha256,source_snapshot_fingerprint:snapshot.manifest.snapshot_marker.fingerprint,source_backend:snapshot.manifest.source_backend,source_revision:snapshot.revision,target_schema_sha256:expectedTargetSchema,collections:snapshot.proofs,json_text_preserved:true,archived_examples_withdrawals_preserved:true,media_bytes_moved:false};
 if(dryRun)return {...base,dry_run:true,network_requests:0};
 if(!driver||typeof driver.query!=='function'||typeof driver.runTransaction!=='function')throw Error('An interactive owner PostgreSQL driver is required');
 if(!verifyOnly&&!acknowledgeOwnerRestore)throw Error('Use the explicit empty-target owner-maintenance restore mode');
 let phase='target-validation',collection=null;
 try{
  const before=await validateTarget(driver,logicalBase),beforeHash=hash(JSON.stringify(before));
  if(verifyOnly){const proofs=await verifyCollections(driver,snapshot),sequence=await verifySequence(driver,snapshot.revision);const receipt={...base,collections:proofs,status:'verified',read_only:true,trigger_inventory_sha256:beforeHash,sequence};writeReceipt(receiptFile,receipt);return receipt;}
  const receipt=await driver.runTransaction(async tx=>{
   phase='lock';await tx.query('SET CONSTRAINTS ALL DEFERRED');await tx.query('SET LOCAL lock_timeout = \'30s\'');await tx.query(`LOCK TABLE ${storageExportCollections.map(table).join(',')} IN ACCESS EXCLUSIVE MODE`);
   phase='empty-target';for(const key of storageExportCollections){const rows=await resultRows(tx,`SELECT count(*) AS n FROM ${table(key)}`);if(Number(rows[0].n)!==0)throw Error('Owner restore target must be empty; verify a completed copy instead');}
   phase='disable-user-guards';for(const key of storageExportCollections)await tx.query(`ALTER TABLE ${table(key)} DISABLE TRIGGER USER`);
   for(const key of restoreOrder.filter(key=>storageExportCollections.includes(key))){
    collection=key;phase='insert-original-rows';const columns=storageExportColumns[key],rows=key==='entities'?topologicalEntities(snapshot.collections[key]):snapshot.collections[key];
    let copied=0,part=[];
    const flush=async()=>{if(!part.length)return;const params=part.flatMap(row=>columns.map(column=>row[column])),values=part.map((_,index)=>`(${columns.map((__,column)=>`$${index*columns.length+column+1}`).join(',')})`).join(',');await tx.query(`INSERT INTO ${table(key)} (${identifiers(columns)}) VALUES ${values}`,params);copied+=part.length;part=[];onProgress({collection:key,rows:copied,expected_rows:snapshot.proofs[key].count});};
    for(const row of rows){part.push(row);if(part.length===200)await flush();}await flush();
   }
   collection=null;phase='constraints';await tx.query('SET CONSTRAINTS ALL IMMEDIATE');
   phase='reenable-user-guards';for(const key of storageExportCollections)await tx.query(`ALTER TABLE ${table(key)} ENABLE TRIGGER USER`);
   phase='read-back';const proofs=await verifyCollections(tx,snapshot),after=await targetTriggers(tx,storageExportCollections);if(hash(JSON.stringify(after))!==beforeHash)throw Error('Restoration changed original trigger definitions or enabled states');
   phase='sequence';const next=Math.max(1,snapshot.revision+1);if(!Number.isSafeInteger(next))throw Error('Source revision cannot advance safely');await tx.query(`ALTER SEQUENCE atlas_ingestions_rowid_seq RESTART WITH ${next}`);const sequence=await verifySequence(tx,snapshot.revision);
   phase='commit';return {...base,collections:proofs,status:'restored',atomic:true,trigger_inventory_sha256:beforeHash,sequence};
  });
  phase='committed-receipt';writeReceipt(receiptFile,receipt);return receipt;
 }catch(error){const code=/^[A-Z0-9]{5}$/.test(error.code??'')?error.code:null,status=phase==='commit'?'unknown':phase==='committed-receipt'?'committed':'rolled-back-or-not-started';const receipt={...base,status:'failed',phase,...(collection?{collection}:{}),sqlstate:code,commit_status:status};try{writeReceipt(receiptFile,receipt);}catch{/* Original transaction status must not be hidden by a filesystem error. */}const failure=new Error(`PostgreSQL owner restore failed at ${phase}${code?` (SQLSTATE ${code})`:''}; commit status ${status}. Preserve the receipt and use read-only verification before retrying an ambiguous commit.`);failure.code=code;failure.phase=phase;failure.commit_status=status;throw failure;}
}
async function ownerDriver(url){
 const {Client,neonConfig}=await import('@neondatabase/serverless');neonConfig.webSocketConstructor=globalThis.WebSocket;
 const client=new Client({connectionString:url});await client.connect();
 return {query:(sql,params)=>client.query(sql,params),async runTransaction(callback){await client.query('BEGIN ISOLATION LEVEL SERIALIZABLE');try{const result=await callback({query:(sql,params)=>client.query(sql,params)});await client.query('COMMIT');return result;}catch(error){try{await client.query('ROLLBACK');}catch{/* Lost connection leaves transaction outcome for read-back verification. */}throw error;}},close:()=>client.end()};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const [directory,mode]=process.argv.slice(2);if(!directory||!['--dry-run','--verify-only','--empty-target-owner-restore'].includes(mode))throw Error('Usage: node scripts/restore-postgres-storage-v4.mjs snapshot-directory --dry-run | --verify-only | --empty-target-owner-restore. Secret DATABASE_URL stays in the authorized environment.');
 let driver;try{if(mode!=='--dry-run'){if(!process.env.DATABASE_URL)throw Error('Missing authorized owner PostgreSQL secret');driver=await ownerDriver(process.env.DATABASE_URL);}let last=0;const receipt=await restorePostgresStorageV4({directory,driver,dryRun:mode==='--dry-run',verifyOnly:mode==='--verify-only',acknowledgeOwnerRestore:mode==='--empty-target-owner-restore',onProgress:progress=>{if(Date.now()-last>15000){console.log(`Owner restore: ${progress.collection} ${progress.rows}/${progress.expected_rows} original rows.`);last=Date.now();}}});console.log(JSON.stringify(receipt));}catch(error){console.error(error?.phase?error.message:'Owner PostgreSQL restoration configuration or verified snapshot failed; no secret is logged.');process.exitCode=1;}finally{await driver?.close().catch(()=>{});}
}
