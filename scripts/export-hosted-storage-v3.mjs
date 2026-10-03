import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {storageExportV3Collections as storageExportCollections,storageExportV3Columns as storageExportColumns,storageExportV3Contract,v3MarkerIdentity} from '../hosted/storage-export-v3-contract.js';
import {storageRowsHashV3Ordered} from './restore-postgres-storage-v3.mjs';

const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const stable=value=>Array.isArray(value)?value.map(stable):value&&typeof value==='object'?Object.fromEntries(Object.keys(value).sort().map(key=>[key,stable(value[key])])):value;
const equivalent=(a,b)=>JSON.stringify(stable(a))===JSON.stringify(stable(b));
function atomicJSON(file,value){fs.mkdirSync(path.dirname(file),{recursive:true});const temporary=file+'.tmp',bytes=Buffer.from(JSON.stringify(value,null,2)+'\n'),fd=fs.openSync(temporary,'w',0o600);try{fs.writeFileSync(fd,bytes);fs.fsyncSync(fd);}finally{fs.closeSync(fd);}fs.renameSync(temporary,file);return bytes;}
function confirmedOrigin(input){const url=new URL(input);if(url.protocol!=='https:'||url.username||url.password||url.pathname!=='/'||url.search||url.hash)throw Error('Supply the confirmed HTTPS Site origin');return url.origin;}
function checkMarker(marker){
 if(!marker||marker.version!==3||!Number.isSafeInteger(marker.revision)||marker.revision<0||!/^[a-f0-9]{64}$/.test(marker.fingerprint??'')||!/^[a-f0-9]{64}$/.test(marker.geographic_releases_sha256??'')||!marker.counts||!equivalent(Object.keys(marker.counts).sort(),[...storageExportCollections].sort())||storageExportCollections.some(key=>!Number.isSafeInteger(marker.counts[key])||marker.counts[key]<0))throw Error('Invalid raw-storage snapshot marker');
 if(!equivalent(marker.contract,storageExportV3Contract)||!/^[a-f0-9]{64}$/.test(marker.footprint_versions_sha256??'')||!/^[a-f0-9]{64}$/.test(marker.catalog_sha256??''))throw Error('Forward storage marker requires the complete reviewed schema and migration pins');
 const expected=v3MarkerIdentity(marker);if(hash(JSON.stringify(expected))!==marker.fingerprint)throw Error('Storage snapshot marker hash does not match its counters');
 return marker;
}
function checkPage(page,collection,marker){
 if(!page||page.collection!==collection||!Array.isArray(page.records)||page.records.length>200||!equivalent(page.columns,storageExportColumns[collection])||page.revision!==marker.revision||page.next_cursor!==null&&(typeof page.next_cursor!=='string'||!page.next_cursor))throw Error('Invalid raw-storage export page');
 if(checkMarker(page.snapshot_marker).fingerprint!==marker.fingerprint)throw Error('Source storage changed; a mixed snapshot cannot be resumed');
 for(const row of page.records)if(!row||Array.isArray(row)||!equivalent(Object.keys(row).sort(),[...page.columns].sort())||Object.values(row).some(value=>value!==null&&typeof value!=='string'&&!(typeof value==='number'&&Number.isSafeInteger(value))))throw Error('Raw-storage export row columns do not match the contract');
}
function snapshotChanged(){throw Error('Source storage changed; preserve this partial export and start a new directory after maintenance is stable');}
class StorageTransportError extends Error{}
class StorageJSONError extends Error{}
const bodyTransportFailure=error=>['ECONNRESET','ETIMEDOUT','EPIPE','UND_ERR_SOCKET','UND_ERR_CONNECT_TIMEOUT','UND_ERR_HEADERS_TIMEOUT','UND_ERR_BODY_TIMEOUT'].includes(error?.code)||error?.name==='TimeoutError'||error?.cause&&bodyTransportFailure(error.cause);
function retryPause(milliseconds,signal){
 signal?.throwIfAborted();
 return new Promise((resolve,reject)=>{
  const abort=()=>{clearTimeout(timer);signal?.removeEventListener('abort',abort);reject(signal.reason);};
  const timer=setTimeout(()=>{signal?.removeEventListener('abort',abort);resolve();},milliseconds);
  signal?.addEventListener('abort',abort,{once:true});if(signal?.aborted)abort();
 });
}

/** Read-only transfer. Secrets are kept in memory; completed pages/ledger are
 * durable and reusable after interruption with a fresh private credential.
 */
export async function exportHostedStorageV3({origin:input,output,token,fetcher=fetch,onProgress=()=>{},signal,concurrency=2,requestTimeoutMs=60000}={}){
 const origin=confirmedOrigin(input);if(typeof token!=='string'||!token)throw Error('A private read-only service credential is required');if(typeof output!=='string'||!output)throw Error('Supply a durable export directory');output=path.resolve(output);
 if(!Number.isSafeInteger(concurrency)||concurrency<1||concurrency>4)throw Error('Export concurrency must be an integer from one to four');
 if(!Number.isSafeInteger(requestTimeoutMs)||requestTimeoutMs<10||requestTimeoutMs>60000)throw Error('Export request timeout must be an integer from 10 to 60000 milliseconds');
 const headers={'OAI-Sites-Authorization':`Bearer ${token}`};
 async function request(route,attempt){
  signal?.throwIfAborted();
  const deadline=new AbortController(),requestSignal=signal?AbortSignal.any([signal,deadline.signal]):deadline.signal;
  const timer=setTimeout(()=>deadline.abort(new DOMException('Read-only storage export request timed out','TimeoutError')),requestTimeoutMs);
  let response,abort;
  const aborted=new Promise((resolve,reject)=>{abort=()=>reject(requestSignal.reason);requestSignal.addEventListener('abort',abort,{once:true});if(requestSignal.aborted)abort();});
  // Race explicitly as well as forwarding the signal: custom transports and
  // stalled body readers must not hold the durable export journal indefinitely.
  const operation=(async()=>{
   try{response=await fetcher(origin+route,{headers,signal:requestSignal});}catch{if(requestSignal.aborted)throw requestSignal.reason;throw new StorageTransportError('Read-only storage export network request failed');}
   if([429,502,503,504].includes(response.status)&&attempt<3){await response.body?.cancel();return {retry:true};}
   let body;
   try{body=await response.json();}catch(error){if(requestSignal.aborted)throw requestSignal.reason;if(bodyTransportFailure(error))throw new StorageTransportError('Read-only storage export body transfer failed');throw new StorageJSONError('Read-only storage export returned invalid JSON');}
   return {response,body};
  })();
  try{return await Promise.race([operation,aborted]);}
  finally{
   clearTimeout(timer);requestSignal.removeEventListener('abort',abort);
   if(requestSignal.aborted&&!response?.body?.locked){try{Promise.resolve(response?.body?.cancel()).catch(()=>{});}catch{}}
  }
 }
 async function get(route){
  for(let attempt=0;attempt<4;attempt++){
   signal?.throwIfAborted();let result;
   try{result=await request(route,attempt);}catch(error){if(signal?.aborted)throw signal.reason;if(!(error instanceof StorageTransportError)&&!bodyTransportFailure(error))throw error;if(attempt===3)throw Error(error?.name==='TimeoutError'?'Read-only storage export request timed out after four bounded attempts; preserved pages can be resumed':'Read-only storage export network request failed');await retryPause(Math.min(4000,500*2**attempt),signal);continue;}
   if(result.retry){await retryPause(Math.min(4000,500*2**attempt),signal);continue;}
   const {response,body}=result;
   if(!response.ok){if(response.status===413&&body.retryable)return {oversized:true,suggested_limit:body.suggested_limit};throw Error(`Read-only storage export HTTP ${response.status}`);}return body;
  }
 }
 async function marker(){const result=await get('/api/storage/v3/export-marker');if(result.read_only!==true)throw Error('Authoritative export requires the Site maintenance read-only flag');return checkMarker(result);}
 const current=await marker(),ledgerFile=path.join(output,'resume.json');let ledger;
 if(fs.existsSync(ledgerFile)){
  ledger=JSON.parse(fs.readFileSync(ledgerFile));if(ledger.version!==3||ledger.origin!==origin||!equivalent(Object.keys(ledger.collections).sort(),[...storageExportCollections].sort()))throw Error('Invalid storage export resume ledger');
  checkMarker(ledger.snapshot_marker);if(ledger.snapshot_marker.fingerprint!==current.fingerprint)snapshotChanged();
 }else{
  if(fs.existsSync(output)&&fs.readdirSync(output).length)throw Error('Export directory contains files without a resume ledger');
  ledger={version:3,status:'partial',origin,source_backend:current.backend??'unknown',snapshot_marker:current,started_at:new Date().toISOString(),collections:Object.fromEntries(storageExportCollections.map(key=>[key,{count:0,columns:[...storageExportColumns[key]],parts:[],cursor:'',complete:false}]))};atomicJSON(ledgerFile,ledger);
 }
 // Check every preserved part before resuming. A successful HTTP response never
 // authorizes replacing bytes from an earlier completed page silently.
 for(const collection of storageExportCollections){
  const entry=ledger.collections[collection];if(!Array.isArray(entry.parts)||!Number.isSafeInteger(entry.count)||entry.count<0||!equivalent(entry.columns,storageExportColumns[collection]))throw Error('Invalid collection resume state');let count=0,cursor='';
  for(let i=0;i<entry.parts.length;i++){
   const part=entry.parts[i],expectedPath=`${collection}/part-${String(i+1).padStart(6,'0')}.json`;if(part.path!==expectedPath||part.start_cursor!==cursor)throw Error('Invalid resume part path or cursor');
   const raw=fs.readFileSync(path.join(output,part.path));if(raw.length!==part.bytes||hash(raw)!==part.sha256)throw Error('Preserved raw-storage export part failed its hash/size check');const page=JSON.parse(raw);checkPage(page,collection,current);if(page.records.length!==part.rows||page.next_cursor!==part.end_cursor)throw Error('Preserved raw-storage page count/cursor differs from its receipt');count+=part.rows;cursor=page.next_cursor??'';
   if(page.next_cursor===null&&i!==entry.parts.length-1)throw Error('A completed collection cannot have later resume parts');
  }
  if(count!==entry.count||cursor!==entry.cursor||entry.complete!==Boolean(entry.parts.length&&entry.parts.at(-1).end_cursor===null))throw Error('Collection resume counters are inconsistent');
 }
 let lastProgress=0;
 async function captureCollection(collection){
  const entry=ledger.collections[collection];let limit=200;const seen=new Set(entry.parts.map(part=>part.start_cursor));
  while(!entry.complete&&!failure){
   const params=new URLSearchParams({limit:String(limit)});if(entry.cursor)params.set('cursor',entry.cursor);
   const page=await get(`/api/storage/v3/export/${collection}?${params}`);
   if(page.oversized){if(limit<=1)throw Error('A raw-storage row exceeds the bounded export transport');limit=Math.max(1,Math.min(limit-1,Number.isSafeInteger(page.suggested_limit)?page.suggested_limit:Math.floor(limit/2)));continue;}
   checkPage(page,collection,current);if(page.next_cursor!==null&&(page.next_cursor===entry.cursor||seen.has(page.next_cursor)))throw Error('Storage export cursor repeated');
   const relative=`${collection}/part-${String(entry.parts.length+1).padStart(6,'0')}.json`,raw=atomicJSON(path.join(output,relative),page);
   entry.parts.push({path:relative,sha256:hash(raw),bytes:raw.length,rows:page.records.length,start_cursor:entry.cursor,end_cursor:page.next_cursor});seen.add(entry.cursor);entry.cursor=page.next_cursor??'';entry.count+=page.records.length;entry.complete=page.next_cursor===null;
   if(entry.count>current.counts[collection]||entry.complete&&entry.count!==current.counts[collection])throw Error('Raw-storage export count differs from the frozen source marker');
   atomicJSON(ledgerFile,ledger);
   if(Date.now()-lastProgress>=15000){onProgress({collection,rows:entry.count,expected_rows:current.counts[collection],completed_collections:storageExportCollections.filter(key=>ledger.collections[key].complete).length});lastProgress=Date.now();}
  }
 }
 // Independent tables overlap; each table's keyset cursor remains sequential.
 // Drain in-flight workers before returning an error so the durable journal is
 // final and a caller can safely restart with a fresh private credential.
 let nextCollection=0,failure;
 await Promise.all(Array.from({length:concurrency},async()=>{while(!failure&&nextCollection<storageExportCollections.length){const collection=storageExportCollections[nextCollection++];try{await captureCollection(collection);}catch(error){failure??=error;}}}));
 if(failure)throw failure;
 const final=await marker();if(final.fingerprint!==current.fingerprint)snapshotChanged();
 ledger.status='complete';ledger.completed_at=new Date().toISOString();atomicJSON(ledgerFile,ledger);
 const manifest={version:3,status:'complete',read_only:true,snapshot_consistent:true,origin,source_backend:ledger.source_backend,contract:storageExportV3Contract,snapshot_marker:current,started_at:ledger.started_at,completed_at:ledger.completed_at,format:{json_text_preserved:true,includes_archived_examples_withdrawals:true,ingestion_rowid_preserved:true},collections:Object.fromEntries(storageExportCollections.map(key=>[key,{count:ledger.collections[key].count,columns:ledger.collections[key].columns,parts:ledger.collections[key].parts,ordered_rows_sha256:storageRowsHashV3Ordered(key,{*[Symbol.iterator](){for(const part of ledger.collections[key].parts){const raw=fs.readFileSync(path.join(output,part.path));if(raw.length!==part.bytes||hash(raw)!==part.sha256)throw Error('Raw source part changed before final hashing');yield* JSON.parse(raw).records;}}})}]))};
 atomicJSON(path.join(output,'index.json'),manifest);return manifest;
}

async function hiddenCredential(){
 if(!process.stdin.isTTY)throw Error('Use hidden terminal stdin for the private read-only credential');process.stdin.setRawMode(true);process.stdout.write('Ready for private read-only service credential on hidden stdin.\n');
 const token=await new Promise((resolve,reject)=>{let value='';process.stdin.on('data',chunk=>{if(chunk.includes(3)){process.stdin.setRawMode(false);reject(Error('Credential entry cancelled'));return;}value+=chunk.toString();if(!/[\r\n]/.test(value))return;process.stdin.pause();process.stdin.setRawMode(false);try{resolve(JSON.parse(value.trim()).token);}catch{reject(Error('Invalid credential input'));}});});
 if(typeof token!=='string'||!token)throw Error('Missing private service credential');return token;
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{const option=process.argv[4],concurrency=option===undefined?2:option==='--concurrency'?Number(process.argv[5]):option.startsWith('--concurrency=')?Number(option.slice(14)):NaN;if(!Number.isSafeInteger(concurrency)||concurrency<1||concurrency>4||process.argv.length>(option==='--concurrency'?6:5))throw Error('Usage: node scripts/export-hosted-storage-v3.mjs <HTTPS origin> <durable directory> [--concurrency 1..4]');const manifest=await exportHostedStorageV3({origin:process.argv[2],output:process.argv[3],concurrency,token:await hiddenCredential(),onProgress:progress=>console.log(`Read-only export: ${progress.collection} ${progress.rows}/${progress.expected_rows} rows; ${progress.completed_collections}/26 collections complete.`)});console.log(JSON.stringify({read_only:true,snapshot_consistent:true,output:path.resolve(process.argv[3]),fingerprint:manifest.snapshot_marker.fingerprint,revision:manifest.snapshot_marker.revision,counts:manifest.snapshot_marker.counts,manifest_sha256:hash(fs.readFileSync(path.join(process.argv[3],'index.json'))),verification_scope:'Raw API export only; this does not prove a PostgreSQL migration or media byte transfer.'}));}
 catch(error){console.error(error instanceof SyntaxError?'Invalid local storage export checkpoint':error.message);process.exitCode=1;}
}
