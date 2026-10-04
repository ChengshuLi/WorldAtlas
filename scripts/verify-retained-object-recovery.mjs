import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {storageExportV2Collections,storageExportV2Columns,storageExportV2Contract,v2MarkerIdentity} from '../hosted/storage-export-v2-contract.js';
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const requireValue=(ok,message)=>{if(!ok)throw Error(message);};
const equivalent=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const positive=value=>Number.isSafeInteger(value)&&value>0;
function exactBytes(value){
 requireValue(typeof value==='number'&&Number.isSafeInteger(value)&&value>=0||typeof value==='string'&&/^(0|[1-9][0-9]*)$/.test(value),'Invalid object byte count');
 const n=BigInt(value);requireValue(n<=BigInt(Number.MAX_SAFE_INTEGER),'Unsafe object byte count');return Number(n);
}
function marker(value){
 requireValue(value?.version===2&&value.backend==='postgres'&&Number.isSafeInteger(value.revision)&&value.revision>=0,'Expected current PostgreSQL V2 marker');
 requireValue(!value.legacy_projection&&equivalent(value.contract,storageExportV2Contract),'Complete known V2 contract required');
 requireValue(value.catalog_sha256===storageExportV2Contract.postgres_catalog_sha256&&/^[a-f0-9]{64}$/.test(value.geographic_releases_sha256??'')&&/^[a-f0-9]{64}$/.test(value.footprint_versions_sha256??''),'Original PostgreSQL catalog and release pins required');
 requireValue(equivalent(Object.keys(value.counts??{}).sort(),[...storageExportV2Collections].sort())&&storageExportV2Collections.every(k=>Number.isSafeInteger(value.counts[k])&&value.counts[k]>=0),'Complete counts required');
 requireValue(/^[a-f0-9]{64}$/.test(value.fingerprint??'')&&hash(JSON.stringify(v2MarkerIdentity(value)))===value.fingerprint,'Marker fingerprint mismatch');
 return value;
}
/** Full registered immutable object verification into a new isolated local directory.
 * This is not a SQL snapshot or a provider-managed backup. No production writes.
 */
export async function verifyRetainedObjectRecovery({origin,token,directory,fetcher=fetch,signal,requestTimeoutMs=60000,maxObjects=1000,maxTotalBytes=512*1024*1024,maxObjectBytes=32*1024*1024,onProgress=()=>{}}={}){
 const url=new URL(origin);requireValue(url.protocol==='https:'&&!url.username&&!url.password&&url.pathname==='/'&&!url.search&&!url.hash,'Confirmed HTTPS Site origin required');origin=url.origin;
 requireValue(typeof token==='string'&&token&&!/[\r\n]/.test(token),'Private credential required');
 requireValue(typeof directory==='string'&&directory,'Isolated output directory required');directory=path.resolve(directory);
 requireValue(positive(requestTimeoutMs)&&requestTimeoutMs<=120000&&positive(maxObjects)&&maxObjects<=10000&&positive(maxTotalBytes)&&positive(maxObjectBytes),'Invalid recovery bounds');
 requireValue(!fs.existsSync(directory),'Preserve existing recovery directories');fs.mkdirSync(directory,{recursive:true,mode:0o700});
 const started=performance.now(),receipt={version:1,status:'partial',origin,started_at_utc:new Date().toISOString(),requests:[],objects:[],limits:[
  'Registered media objects only; unregistered provider objects and billable storage are excluded.',
  'No SQL capture, owner registry restore, provider-managed backup, new upload or production mutation.',
  'Recovered bytes are local isolated files; no external disaster-retention guarantee is inferred.',
  'Published footprint object references require separate inventory coverage if present.'
 ]};let phase='marker-before';
 function save(){const raw=JSON.stringify(receipt,null,2)+'\n';requireValue(!raw.includes(token),'Unsafe receipt');const temporary=path.join(directory,'receipt.json.next');const fd=fs.openSync(temporary,'w',0o600);try{fs.writeFileSync(fd,raw);fs.fsyncSync(fd);}finally{fs.closeSync(fd);}fs.renameSync(temporary,path.join(directory,'receipt.json'));}
 async function transfer(route,{expected,output}={}){
  signal?.throwIfAborted();const deadline=new AbortController(),requestSignal=signal?AbortSignal.any([signal,deadline.signal]):deadline.signal;
  const timer=setTimeout(()=>deadline.abort(new DOMException('Recovery request deadline','TimeoutError')),requestTimeoutMs);
  const log={route,status:null,bytes:0};receipt.requests.push(log);let response,reader,fd;const digest=createHash('sha256'),chunks=[];
  const operation=(async()=>{
   response=await fetcher(origin+route,{method:'GET',redirect:'error',signal:requestSignal,headers:{'OAI-Sites-Authorization':'Bearer '+token}});log.status=response.status;requestSignal.throwIfAborted();
   requireValue(response.status===200,'Complete successful response required');
   requireValue(!response.headers.get('content-range'),'Partial objects are not recovery bytes');
   if(expected&&response.headers.get('content-length')!==null)requireValue(exactBytes(response.headers.get('content-length'))===expected.bytes,'Object length header mismatch');
   if(output)fd=fs.openSync(output,'wx',0o600);reader=response.body?.getReader();requireValue(reader,'Response body required');
   for(;;){const {done,value}=await reader.read();if(done)break;requestSignal.throwIfAborted();log.bytes+=value.byteLength;
    requireValue(log.bytes<=(expected?expected.bytes:4*1024*1024),'Response exceeds expected bound');digest.update(value);
    if(fd!==undefined){let offset=0;while(offset<value.byteLength)offset+=fs.writeSync(fd,value,offset,value.byteLength-offset);}else chunks.push(Buffer.from(value));
   }
   log.sha256=digest.digest('hex');
   if(expected){requireValue(log.bytes===expected.bytes&&log.sha256===expected.sha256,'Original object byte/hash mismatch');fs.fsyncSync(fd);return log;}
   return JSON.parse(Buffer.concat(chunks));
  })();
  let abort;const aborted=new Promise((_,reject)=>{abort=()=>reject(requestSignal.reason);requestSignal.addEventListener('abort',abort,{once:true});if(requestSignal.aborted)abort();});
  try{return await Promise.race([operation,aborted]);}
  finally{clearTimeout(timer);requestSignal.removeEventListener('abort',abort);deadline.abort();try{Promise.resolve(reader?.cancel()).catch(()=>{});}catch{}try{reader?.releaseLock();}catch{}if(fd!==undefined)fs.closeSync(fd);}
 }
 try{
  receipt.before_marker=marker(await transfer('/api/storage/v2/export-marker'));
  requireValue(receipt.before_marker.counts.footprint_version_objects===0,'Separate footprint-reference coverage required');
  phase='registered-inventory';const inventory=[],ids=new Set(),keys=new Map(),cursors=new Set();let cursor='';
  for(let pageNumber=0;pageNumber<=maxObjects;pageNumber++){
   const q=new URLSearchParams({limit:'200'});if(cursor)q.set('cursor',cursor);
   const page=await transfer('/api/storage/v2/export/media?'+q);
   requireValue(page?.collection==='media'&&Array.isArray(page.records)&&page.records.length<=200&&equivalent(page.columns,storageExportV2Columns.media)&&page.revision===receipt.before_marker.revision&&marker(page.snapshot_marker).fingerprint===receipt.before_marker.fingerprint,'Mixed media snapshot');
   for(const row of page.records){
    requireValue(typeof row.id==='string'&&row.id&&row.id.length<=512&&!ids.has(row.id),'Invalid or duplicate media identity');ids.add(row.id);
    requireValue(typeof row.object_key==='string'&&row.object_key&&row.object_key.length<=1024&&/^[a-f0-9]{64}$/.test(row.sha256??''),'Invalid immutable object pin');
    const bytes=exactBytes(row.bytes);requireValue(bytes<=maxObjectBytes,'Object exceeds reviewed byte budget');
    const pin={sha256:row.sha256,bytes};if(keys.has(row.object_key))requireValue(equivalent(keys.get(row.object_key),pin),'Conflicting shared object key');else keys.set(row.object_key,pin);
    inventory.push({id:row.id,object_key:row.object_key,...pin,source_id:row.source_id,status:row.status,original_media_record:row});requireValue(inventory.length<=maxObjects,'Object inventory budget exceeded');
   }
   cursor=page.next_cursor;requireValue(cursor===null||typeof cursor==='string'&&cursor&&!cursors.has(cursor),'Invalid or repeated cursor');
   if(cursor===null)break;cursors.add(cursor);
  }
  requireValue(cursor===null&&inventory.length===receipt.before_marker.counts.media,'Incomplete registered object inventory');
  const total=inventory.reduce((sum,row)=>sum+row.bytes,0);requireValue(Number.isSafeInteger(total)&&total<=maxTotalBytes,'Total recovery byte budget exceeded');
  receipt.inventory=inventory;receipt.expected_registered_bytes=total;const capacity=fs.statfsSync(directory,{bigint:true});receipt.available_local_bytes_before_copy=String(capacity.bavail*capacity.bsize);requireValue(capacity.bavail*capacity.bsize>=BigInt(total)+64n*1024n*1024n,'Insufficient isolated recovery disk capacity');save();fs.mkdirSync(path.join(directory,'objects'),{mode:0o700});phase='full-object-copy';
  for(const row of inventory){
   const relative='objects/'+hash(Buffer.from(row.id))+'.bin',file=path.join(directory,relative),item={...row,path:relative,status:'partial'};receipt.objects.push(item);
   const begin=performance.now(),read=await transfer('/api/media/'+encodeURIComponent(row.id),{expected:row,output:file});
   const restored=fs.readFileSync(file);requireValue(restored.length===row.bytes&&hash(restored)===row.sha256,'Isolated local readback differs');
   item.status='verified';item.full_sha256_verified=true;item.local_readback_verified=true;item.bytes=read.bytes;item.duration_ms=Math.round(performance.now()-begin);save();onProgress({completed:receipt.objects.length,total:inventory.length});
  }
  phase='marker-after';receipt.after_marker=marker(await transfer('/api/storage/v2/export-marker'));
  requireValue(receipt.after_marker.fingerprint===receipt.before_marker.fingerprint,'Source changed during recovery');
  receipt.status='verified';receipt.registered_objects=inventory.length;receipt.recovered_bytes=total;receipt.duration_ms=Math.round(performance.now()-started);receipt.finished_at_utc=new Date().toISOString();save();return receipt;
 }catch(error){receipt.status='failed';receipt.phase=phase;receipt.failure_code=['ENOSPC','EACCES','EIO','ENOENT'].includes(error?.code)?error.code:error?.name==='TimeoutError'?'TIMEOUT':'VERIFICATION_OR_TRANSPORT';receipt.failure='Bounded request, immutable pin, inventory or local readback failed; preserve partial bytes and receipts';receipt.duration_ms=Math.round(performance.now()-started);try{save();}catch{/* Preserve the preceding atomic receipt and any failed temporary bytes. */}throw Error('Retained object recovery failed; sanitized receipt and partial bytes preserved');}
}
export function readHiddenPrivateToken(input=process.stdin){
 requireValue(input.isTTY&&typeof input.setRawMode==='function','Use hidden private credential stdin');
 input.setRawMode(true);
 return new Promise((resolve,reject)=>{
  let value='',finished=false;
  const finish=(error,token)=>{if(finished)return;finished=true;input.removeListener('data',data);input.removeListener('end',end);input.removeListener('error',failure);input.pause();input.setRawMode(false);value='';error?reject(error):resolve(token);};
  const end=()=>finish(Error('Hidden input ended before credential'));
  const failure=()=>finish(Error('Hidden input unavailable'));
  const data=chunk=>{
   if(chunk.includes(3)||chunk.includes(4))return finish(Error('Hidden input cancelled'));
   value+=chunk.toString();if(value.length>8192)return finish(Error('Hidden input too large'));
   if(!/[\r\n]/.test(value))return;
   try{const token=JSON.parse(value.trim()).token;requireValue(typeof token==='string'&&token&&!/[\r\n]/.test(token),'Invalid hidden credential');finish(null,token);}catch{finish(Error('Invalid hidden credential'));}
  };
  input.on('data',data);input.once('end',end);input.once('error',failure);
 });
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){
 const [origin,directory]=process.argv.slice(2);
 try{
  console.log('Ready for private recovery credential JSON on hidden stdin.');const token=await readHiddenPrivateToken();
  const r=await verifyRetainedObjectRecovery({origin,token,directory,onProgress:({completed,total})=>{if(completed%25===0)console.log(`Verified ${completed}/${total} retained objects`);}});
  console.log(JSON.stringify({status:r.status,registered_objects:r.registered_objects,recovered_bytes:r.recovered_bytes,duration_ms:r.duration_ms}));
 }catch{console.error('Recovery cancelled or failed; any sanitized receipts are retained');process.exitCode=1;}
 finally{process.exit(process.exitCode??0);}
}
