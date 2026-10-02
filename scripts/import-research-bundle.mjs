import {assertResearchImportsReady,assertResearchBundleApproved,readResearchImportGate} from './research-import-gate.mjs';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {previewImport} from '../src/import-records.js';
import {researchHash,researchJSON,validateResearchGeography,compileResearchInput,previewTemporalResearchBatch,temporalResearchEndpoint} from './prepare-research-bundle.mjs';

const safePath=(directory,name)=>{if(typeof name!=='string'||!name||path.isAbsolute(name)||name.split(/[\\/]/).some(part=>part==='..'||part===''))throw Error('Unsafe research bundle path');const resolved=path.resolve(directory,name),real=fs.realpathSync(resolved);if(real!==path.resolve(directory)&&!real.startsWith(fs.realpathSync(directory)+path.sep))throw Error('Research bundle path escapes directory');return resolved;};
export function readResearchBundle(directory){
 const bytes=fs.readFileSync(path.join(directory,'index.json')),manifest=JSON.parse(bytes),manifest_sha256=researchHash(bytes);
 if(manifest.version!==1||manifest.kind!=='research-content'||!Array.isArray(manifest.batches)||!manifest.batches.length)throw Error('Invalid research bundle manifest');
 validateResearchGeography(manifest.geography);
 const validate=entry=>{if(!entry||!/^[a-f0-9]{64}$/.test(entry.sha256)||!Number.isSafeInteger(entry.bytes)||entry.bytes<0)throw Error('Invalid research file proof');const raw=fs.readFileSync(safePath(directory,entry.path));if(raw.length!==entry.bytes||researchHash(raw)!==entry.sha256)throw Error(`Research file bytes changed: ${entry.path}`);return raw;};
 const prepared=compileResearchInput(JSON.parse(validate(manifest.input)),manifest.geography);
 if(researchJSON(prepared.counts)!==researchJSON(manifest.counts)||prepared.batches.length!==manifest.batches.length)throw Error('Research manifest does not match its preserved input');
 const ids=new Set(),batches=[];
 for(const part of manifest.batches){
  if(part.endpoint!==undefined&&part.endpoint!==temporalResearchEndpoint)throw Error('Unsupported research batch endpoint');
  const raw=validate(part),temporal=part.endpoint===temporalResearchEndpoint,checked=temporal?previewTemporalResearchBatch(JSON.parse(raw),manifest.geography):previewImport(raw.toString()),payload=checked.payload,rows=checked.rows.length;
  if(rows>200||rows!==part.rows||payload.ingestion_id!==part.ingestion_id||payload.ingestion_id!==`${temporal?'temporal-research':'research'}:${researchHash(researchJSON(Object.fromEntries(Object.entries(payload).filter(([key])=>key!=='ingestion_id'))))}`||ids.has(payload.ingestion_id))throw Error('Invalid or repeated research batch identity');
  if(prepared.batches[batches.length].sha256!==part.sha256||prepared.batches[batches.length].endpoint!==part.endpoint)throw Error('Research batches do not match their preserved input or endpoint');
  ids.add(payload.ingestion_id);batches.push({part,raw});
 }
 for(const file of manifest.source_files??[]){if(file.redistribution_permitted!==true||!file.license||!file.source_id)throw Error('Invalid licensed research archive');validate(file);}
 return {manifest,manifest_sha256,batches};
}
export function researchOrigin(input){const url=new URL(input);if(url.protocol!=='https:'||url.username||url.password||url.pathname!=='/'||url.search||url.hash)throw Error('Supply the confirmed HTTPS Site origin');return url.origin;}
function atomicLedger(file,ledger){fs.mkdirSync(path.dirname(file),{recursive:true});const temp=`${file}.tmp-${process.pid}`;fs.writeFileSync(temp,JSON.stringify(ledger,null,2)+'\n');fs.renameSync(temp,file);}
export async function importResearchBundle({directory,origin,token,ledgerFile=path.join(directory,'import-receipts.json'),request=fetch,wait=milliseconds=>new Promise(resolve=>setTimeout(resolve,milliseconds)),onProgress=()=>{},dryRun=false}){
 origin=researchOrigin(origin);const bundle=readResearchBundle(directory);
 const expected_geography={release_id:bundle.manifest.geography.id,hierarchy_sha256:bundle.manifest.geography.hierarchy_sha256,footprints_sha256:bundle.manifest.geography.footprints_sha256};
 const pinHash=researchHash(researchJSON(expected_geography)),wire=new Map(bundle.batches.map(({part,raw})=>{const payload={...JSON.parse(raw),ingestion_id:`${part.ingestion_id}:geo:${pinHash}`,expected_geography},bytes=Buffer.from(researchJSON(payload));if(bytes.length>1048576)throw Error('Pinned research batch exceeds 1 MiB; prepare smaller source collections before importing');return [part.ingestion_id,{id:payload.ingestion_id,bytes}];}));
 if(dryRun)return {dry_run:true,manifest_sha256:bundle.manifest_sha256,geography:bundle.manifest.geography,expected_geography,counts:bundle.manifest.counts,batches:bundle.batches.length,network_requests:0};
 if(typeof token!=='string'||!token)throw Error('Missing private Site service credential');
 let ledger=fs.existsSync(ledgerFile)?JSON.parse(fs.readFileSync(ledgerFile)):{version:1,origin,manifest_sha256:bundle.manifest_sha256,geography:bundle.manifest.geography,batches:[],complete:false};
 if(ledger.version!==1||ledger.origin!==origin||ledger.manifest_sha256!==bundle.manifest_sha256||researchJSON(ledger.geography)!==researchJSON(bundle.manifest.geography)||!Array.isArray(ledger.batches))throw Error('Receipt ledger belongs to another bundle, geography or Site');
 const expected=new Map(bundle.batches.map(({part})=>[part.ingestion_id,part]));
 for(const row of ledger.batches)if(!expected.has(row.ingestion_id)||row.sha256!==expected.get(row.ingestion_id).sha256||row.endpoint!==expected.get(row.ingestion_id).endpoint||row.status!=='committed'||row.expected_geography&&(researchJSON(row.expected_geography)!==researchJSON(expected_geography)||row.request_ingestion_id!==wire.get(row.ingestion_id).id))throw Error('Invalid completed batch receipt');
 if(new Set(ledger.batches.map(row=>row.ingestion_id)).size!==ledger.batches.length)throw Error('Duplicate completed receipt');
 // Legacy receipts remain preserved; only a matching pinned transaction is
 // sufficient to skip this campaign's new guarded import on resume.
 const completed=new Set(ledger.batches.filter(row=>row.expected_geography).map(row=>row.ingestion_id));
 const headers={'OAI-Sites-Authorization':`Bearer ${token}`},redact=value=>String(value).split(token).join('[redacted]').slice(0,1000);
 async function call(route,init={}){
  let error;
  for(let attempt=0;attempt<4;attempt++){
   try{const response=await request(origin+route,{...init,headers:{...headers,...init.headers},signal:AbortSignal.timeout(60000)});if(![429,502,503,504].includes(response.status))return response;error=Error(`Transient HTTP ${response.status}`);}catch(caught){error=caught;}
   if(attempt<3)await wait(Math.min(4000,500*2**attempt));
  }
  throw Error(`Research request failed after bounded retries: ${redact(error?.message)}`);
 }
 try{
  const response=await call('/api/geography/release');if(!response.ok)throw Error(`Cannot verify published geography: HTTP ${response.status}`);
  const current=validateResearchGeography(await response.json());if(researchJSON(current)!==researchJSON(bundle.manifest.geography))throw Error('Live geographic release does not match the pinned research bundle');
  atomicLedger(ledgerFile,ledger);
  for(const {part}of bundle.batches){
   if(completed.has(part.ingestion_id)){onProgress({completed:completed.size,total:bundle.batches.length,resumed:true});continue;}
   const sent=wire.get(part.ingestion_id),response=await call(part.endpoint??'/api/records/import',{method:'POST',headers:{'Content-Type':'application/json',Origin:origin},body:sent.bytes});
   if(!response.ok)throw Error(`Research import HTTP ${response.status}: ${redact(await response.text())}`);
   const countKeys=part.endpoint===temporalResearchEndpoint?['memberships','existence','retirements']:['sources','entity_types','entities','categories','records','names','relationships','media_links','retirements'];
   const receipt=await response.json();if(receipt.ingestion_id!==sent.id||researchJSON(receipt.expected_geography)!==researchJSON(expected_geography)||!Number.isSafeInteger(receipt.revision)||receipt.revision<0||!receipt.counts||typeof receipt.counts!=='object'||Array.isArray(receipt.counts)||Object.entries(receipt.counts).some(([key,value])=>!countKeys.includes(key)||!Number.isSafeInteger(value)||value<0))throw Error('Server returned an invalid or unpinned research import receipt');
   // Retain only documented, nonsensitive receipt fields, never headers/token.
   const index=ledger.batches.findIndex(row=>row.ingestion_id===part.ingestion_id),entry={ingestion_id:part.ingestion_id,request_ingestion_id:sent.id,expected_geography,path:part.path,sha256:part.sha256,rows:part.rows,status:'committed',duplicate:Boolean(receipt.duplicate),counts:receipt.counts,revision:receipt.revision,...(part.endpoint?{endpoint:part.endpoint}:{}),...(index>=0?{previous_unpinned_receipt:ledger.batches[index]}:{})};if(index>=0)ledger.batches[index]=entry;else ledger.batches.push(entry);completed.add(part.ingestion_id);
   delete ledger.last_error;ledger.complete=false;atomicLedger(ledgerFile,ledger);onProgress({completed:completed.size,total:bundle.batches.length,resumed:false});
  }
  ledger.complete=true;delete ledger.last_error;atomicLedger(ledgerFile,ledger);return {complete:true,committed_batches:completed.size,counts:bundle.manifest.counts,manifest_sha256:bundle.manifest_sha256,geography:bundle.manifest.geography,ledger:ledgerFile};
 }catch(error){ledger.complete=false;ledger.last_error=redact(error.message);atomicLedger(ledgerFile,ledger);throw Error(ledger.last_error);}
}
async function hiddenCredential(){
 if(!process.stdin.isTTY)throw Error('Use hidden terminal stdin for the private Site service credential; never pass it in arguments or files');
 process.stdin.setRawMode(true);process.stdout.write('Ready for private service credential on hidden stdin.\n');
 return new Promise((resolve,reject)=>{let value='';const finish=()=>{process.stdin.pause();process.stdin.setRawMode(false);process.stdin.removeListener('data',receive);};const receive=chunk=>{if(chunk.includes(3)){finish();reject(Error('Credential entry cancelled'));return;}value+=chunk.toString();if(!/[\r\n]/.test(value))return;finish();try{const token=JSON.parse(value.trim()).token;if(typeof token!=='string'||!token)throw Error();resolve(token);}catch{reject(Error('Supply the private service credential JSON through hidden stdin'));}};process.stdin.on('data',receive);});
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const args=process.argv.slice(2),dryRun=args.includes('--dry-run'),positional=args.filter(arg=>arg!=='--dry-run'),[origin,directory]=positional;
 if(!origin||!directory)throw Error('Usage: node --use-env-proxy scripts/import-research-bundle.mjs https://confirmed-site/ bundle-directory [--dry-run]');
 if(!dryRun){const gate=readResearchImportGate();assertResearchImportsReady(gate);assertResearchBundleApproved(gate,readResearchBundle(directory).manifest.geography);}
 const token=dryRun?undefined:await hiddenCredential();let last=0;
 const receipt=await importResearchBundle({origin,directory,token,dryRun,onProgress:progress=>{if(Date.now()-last>15000||progress.completed===progress.total){console.log(`Research import: ${progress.completed}/${progress.total} bounded batches committed.`);last=Date.now();}}});console.log(JSON.stringify(receipt));
}
