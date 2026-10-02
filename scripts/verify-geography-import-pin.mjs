import {randomUUID} from 'node:crypto';
import fs from 'node:fs';
import {createPostgresDatabase} from '../hosted/postgres-adapter.js';
import {importBatch} from '../hosted/records.js';
import {stageGeographicRelease,finalizeGeographicRelease,geographicMembershipHash,geographicLocationIdsHash,geographicChangesHash} from '../hosted/geographic-releases.js';

const lock='SELECT pg_advisory_xact_lock(807245315,1)';
const tiers=['continent','subcontinent','region','area','province','location'];
const pause=milliseconds=>new Promise(resolve=>setTimeout(resolve,milliseconds));
const result=value=>({...value,rowCount:value.rowCount??value.affectedRows??value.rows.length});
const deferred=()=>{let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});return {promise,resolve,reject};};
const samePin=(left,right)=>['release_id','hierarchy_sha256','footprints_sha256'].every(key=>left?.[key]===right?.[key]);
async function within(promise,milliseconds){let timer;try{return await Promise.race([promise,new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('Pinned import never entered its transaction')),milliseconds);})]);}finally{clearTimeout(timer);}}
function database(driver,{onLock=()=>{}}={}){
 return createPostgresDatabase({query:async(sql,params)=>(result(await driver.query(sql,params))),transaction:async(statements,options)=>driver.runTransaction(async tx=>{
  // The real interactive driver's BEGIN precedes this; the adapter chooses
  // isolation, and this command must precede every query inside the transaction.
  if(!['ReadCommitted','Serializable'].includes(options.isolationLevel))throw Error('Unexpected verification transaction isolation');
  await tx.query(`SET TRANSACTION ISOLATION LEVEL ${options.isolationLevel==='ReadCommitted'?'READ COMMITTED':'SERIALIZABLE'}`);
  const rows=[];for(const statement of statements){if(statement.query===lock)onLock();rows.push(result(await tx.query(statement.query,statement.params)));}return rows;
 })},{timeoutMs:30000});
}
function transactionDatabase(tx){
 return createPostgresDatabase({query:async(sql,params)=>result(await tx.query(sql,params)),transaction:async statements=>{
  const rows=[];for(const statement of statements)rows.push(result(await tx.query(statement.query,statement.params)));return rows;
 }},{timeoutMs:30000});
}
async function blocked(tx,pid,timeoutMs){
 const deadline=Date.now()+timeoutMs;
 while(Date.now()<deadline){const row=(await tx.query("SELECT EXISTS(SELECT 1 FROM pg_locks WHERE pid=$1 AND locktype='advisory' AND NOT granted) AS blocked",[pid])).rows[0];if(row?.blocked===true)return;await pause(50);}
 throw Error('Import did not observably wait on the publication advisory lock');
}

/** Destructive fixture writes are permitted ONLY in a caller-created disposable
 * provider branch. Requires two independent interactive PostgreSQL sessions;
 * PGlite and HTTP transaction simulations cannot establish this proof.
 * Caller owns branch creation/deletion and secret connection configuration.
 */
export async function exerciseGeographyImportPin({publisherDriver,importDriver,disposableBranchId,disposableBranch=false,timeoutMs=15000,onProgress=()=>{}}={}){
 if(disposableBranch!==true||typeof disposableBranchId!=='string'||!/^br-[a-z0-9-]+$/.test(disposableBranchId))throw Error('Geographic pin verification requires an explicitly disposable provider branch');
 if(!publisherDriver?.query||!publisherDriver?.runTransaction||!importDriver?.query||!importDriver?.runTransaction||publisherDriver===importDriver)throw Error('Two independent interactive PostgreSQL drivers are required');
 if(!Number.isInteger(timeoutMs)||timeoutMs<1000||timeoutMs>20000)throw Error('Invalid geographic pin verification timeout');
 const publisherPID=(await publisherDriver.query('SELECT pg_backend_pid() AS pid')).rows[0]?.pid,importPID=(await importDriver.query('SELECT pg_backend_pid() AS pid')).rows[0]?.pid;
 if(!Number.isInteger(publisherPID)||!Number.isInteger(importPID)||publisherPID===importPID)throw Error('Geographic pin verification requires separate real PostgreSQL sessions');
 let watchImport=false;const owner=database(publisherDriver),importStarted=deferred(),app=database(importDriver,{onLock:()=>{if(watchImport)importStarted.resolve();}});
 const prefix=`pin-verification:${randomUUID()}`,referenceSource=`${prefix}:reference`,historySource=`${prefix}:history`,location=`${prefix}:0:location`;
 const sources=[{id:referenceSource,name:'Disposable geographic reference',license:'CC0',vintage:'2026',supported_from:2026,supported_to:2027,status:'reference'},{id:historySource,name:'Disposable historical test source',license:'CC0',vintage:'2026',supported_from:1000,supported_to:1100,status:'historical'}];
 const entities=Array.from({length:6},(_,c)=>tiers.map((kind,i)=>({id:`${prefix}:${c}:${kind}`,kind,name:`Disposable ${kind}`,parent_id:i?`${prefix}:${c}:${tiers[i-1]}`:null}))).flat();
 await importBatch(owner,JSON.parse(fs.readFileSync(new URL('../data/hosted-type-catalog.json',import.meta.url))));await importBatch(owner,{sources,entities});
 const memberships=entities.map(row=>({entity_id:row.id,kind:row.kind,parent_id:row.parent_id,reference_name:row.name,active:1,source_id:referenceSource,evidence:{test_only:true}}));
 const latest=(await owner.prepare('SELECT coalesce(max(version),0) version FROM atlas_geographic_releases').first()).version;
 const manifest=async(id,version)=>({id,version,source_id:referenceSource,reference_date:'2026-10-02',hierarchy_sha256:'a'.repeat(64),footprints_sha256:'b'.repeat(64),membership_sha256:await geographicMembershipHash(memberships),location_ids_sha256:await geographicLocationIdsHash(memberships),changes_sha256:await geographicChangesHash([]),expected_counts:Object.fromEntries(tiers.map(tier=>[tier,6]))});
 const first=await manifest(`${prefix}:first`,latest+1),second=await manifest(`${prefix}:second`,latest+2),pin=release=>({release_id:release.id,hierarchy_sha256:release.hierarchy_sha256,footprints_sha256:release.footprints_sha256});
 await stageGeographicRelease(owner,{release:first,memberships});await finalizeGeographicRelease(owner,first.id);
 const original={ingestion_id:`${prefix}:committed`,expected_geography:pin(first),records:[{id:`${prefix}:population`,location_id:location,attribute:'population',value:42,valid_from:1000,valid_to:1100,source_id:historySource}]};
 await importBatch(app,original);const retained=await app.prepare('SELECT * FROM atlas_ingestions WHERE id=?').bind(original.ingestion_id).first();await stageGeographicRelease(owner,{release:second,memberships});
 const held=deferred();let waitingObserved=false;watchImport=true;
 const publishing=publisherDriver.runTransaction(async tx=>{
  await tx.query('SET TRANSACTION ISOLATION LEVEL READ COMMITTED');await tx.query(lock);held.resolve();onProgress('Publication lock held; waiting for the independent pinned import.');
  await within(importStarted.promise,timeoutMs);
  await blocked(tx,importPID,timeoutMs);waitingObserved=true;
  await finalizeGeographicRelease(transactionDatabase(tx),second.id);
 }).then(value=>({status:'fulfilled',value}),error=>{held.reject(error);return {status:'rejected',error};});
 await held.promise;
 const refusedSource=`${prefix}:must-rollback`,refusedClaim=`${prefix}:climate`,stale={ingestion_id:`${prefix}:stale`,expected_geography:pin(first),sources:[{...sources[1],id:refusedSource}],records:[{id:refusedClaim,location_id:location,attribute:'climate',value:'climate:Cfb',valid_from:1000,valid_to:1100,source_id:refusedSource}]};
 const importing=importBatch(app,stale).then(value=>({status:'fulfilled',value}),error=>({status:'rejected',error}));
 const [published,imported]=await Promise.all([publishing,importing]);
 if(published.status!=='fulfilled'||!waitingObserved)throw Error('Disposable publication/lock concurrency proof failed');
 if(imported.status!=='rejected'||imported.error.status!==409||imported.error.retryable!==true||!/no records were committed/.test(imported.error.message))throw Error('Stale geographic import was not rejected with its explicit atomic conflict');
 for(const [table,id]of [['atlas_sources',refusedSource],['atlas_attribute_records',refusedClaim],['atlas_ingestions',stale.ingestion_id]])if(await app.prepare(`SELECT id FROM ${table} WHERE id=?`).bind(id).first())throw Error('Stale pin transaction retained a forbidden partial write');
 const replay=await importBatch(app,original),stored=await app.prepare('SELECT * FROM atlas_ingestions WHERE id=?').bind(original.ingestion_id).first();
 if(!replay.duplicate||!samePin(replay.expected_geography,pin(first))||JSON.stringify(stored)!==JSON.stringify(retained))throw Error('Geographic publication changed an original pinned ingestion receipt');
 const fresh=await importBatch(app,{...stale,ingestion_id:`${prefix}:fresh`,expected_geography:pin(second)});
 if(!samePin(fresh.expected_geography,pin(second)))throw Error('Current geographic pin was not accepted after publication');
 onProgress('Real blocked two-session publication/import proof passed; fixtures remain in the disposable branch only.');
 return {version:1,status:'verified',disposable_branch_id:disposableBranchId,real_independent_sessions:true,advisory_wait_observed:waitingObserved,transaction_isolation:'ReadCommitted after the common publication/import lock',stale_import_status:409,stale_import_atomic_rollback:true,original_pinned_replay_preserved:true,current_pin_import_accepted:true,production_mutation:false,fixture_scope:'Caller-created disposable PostgreSQL provider branch; caller must delete it.',limitations:['This fixture does not establish production migration or record-scale capacity.']};
}
