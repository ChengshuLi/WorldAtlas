import fs from 'node:fs';
import path from 'node:path';
import {createHash,randomUUID} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {researchOrigin} from './import-research-bundle.mjs';
import {researchJSON} from './prepare-research-bundle.mjs';

export const mediaUploadLimit=20*1024*1024;
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const object=value=>value!==null&&typeof value==='object'&&!Array.isArray(value);
const digest=value=>typeof value==='string'&&/^[a-f0-9]{64}$/.test(value);
function fail(code){throw Object.assign(Error(code),{code});}
function keys(value,allowed,required=allowed){if(!object(value)||Object.keys(value).some(key=>!allowed.includes(key))||required.some(key=>!Object.hasOwn(value,key)))fail('media-invalid-manifest-fields');}
function text(value,limit=500){if(typeof value!=='string'||!value.trim()||value.length>limit||/[\x00-\x1f]/.test(value))fail('media-invalid-text');}
function sourceURL(value){let url;try{url=new URL(value);}catch{fail('media-invalid-source-url');}if(!['https:','http:'].includes(url.protocol)||url.username||url.password)fail('media-invalid-source-url');}
function localFile(directory,relative,maxBytes){
 if(typeof relative!=='string'||!relative||path.isAbsolute(relative)||relative.includes('\\')||relative.split('/').some(part=>!part||part==='.'||part==='..'))fail('media-unsafe-file-path');
 const target=path.resolve(directory,relative),root=fs.realpathSync(directory);let stat,real;
 try{stat=fs.statSync(target);real=fs.realpathSync(target);}catch{fail('media-file-unavailable');}
 if(!real.startsWith(root+path.sep)||!stat.isFile()||stat.size>maxBytes)fail('media-file-size-or-path-invalid');return target;
}
function provenance(value){
 keys(value,['source_url','retrieved_at','reference','source_archive'],['source_url','retrieved_at','reference']);sourceURL(value.source_url);text(value.reference,1500);text(value.retrieved_at,30);
 const date=new Date(value.retrieved_at);if(!/^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z)?$/.test(value.retrieved_at)||!Number.isFinite(date.getTime())||date.toISOString().slice(0,10)!==value.retrieved_at.slice(0,10))fail('media-invalid-retrieval-date');
 if(value.source_archive){keys(value.source_archive,['url','sha256','media_id'],['url','sha256']);sourceURL(value.source_archive.url);if(!digest(value.source_archive.sha256))fail('media-invalid-source-archive-digest');if(value.source_archive.media_id!=null)text(value.source_archive.media_id);}
 if(Buffer.byteLength(researchJSON(value))>4096)fail('media-provenance-over-4096-bytes');
}
export function readResearchMedia(manifestFile){
 const directory=fs.realpathSync(path.dirname(path.resolve(manifestFile)));let raw;try{const stat=fs.statSync(manifestFile);if(!stat.isFile()||stat.size>1024*1024)fail('media-manifest-over-1-mib');raw=fs.readFileSync(manifestFile);}catch(error){if(error.code?.startsWith('media-'))throw error;fail('media-manifest-unavailable');}
 let manifest;try{manifest=JSON.parse(raw);}catch{fail('media-invalid-manifest-json');}
 keys(manifest,['version','kind','campaign_id','sources','objects']);if(manifest.version!==1||manifest.kind!=='research-media')fail('media-invalid-manifest-version');text(manifest.campaign_id);
 if(!Array.isArray(manifest.sources)||!manifest.sources.length||manifest.sources.length>1000||!Array.isArray(manifest.objects)||!manifest.objects.length||manifest.objects.length>1000)fail('media-invalid-campaign-size');
 const sources=new Map();for(const source of manifest.sources){keys(source,['id','name','url','license','vintage','status']);text(source.id,256);for(const key of ['name','license','vintage'])text(source[key]);if(source.url!==null)sourceURL(source.url);if(!['historical','reference','estimate','example'].includes(source.status)||sources.has(source.id))fail('media-invalid-source-identity');sources.set(source.id,source);}
 const ids=new Set(),digests=new Set(),objects=[];
 for(const row of manifest.objects){
  keys(row,['id','path','sha256','bytes','mime','name','license','attribution','source_id','redistribution_permitted','provenance']);for(const key of ['id','name','license','attribution','source_id'])text(row[key]);
  if(!sources.has(row.source_id)||ids.has(row.id)||!digest(row.sha256)||digests.has(row.sha256))fail('media-invalid-or-repeated-identity');ids.add(row.id);digests.add(row.sha256);
  if(!Number.isSafeInteger(row.bytes)||row.bytes<1||row.bytes>mediaUploadLimit||typeof row.mime!=='string'||!/^[-\w.+]+\/[-\w.+]+$/.test(row.mime)||row.redistribution_permitted!==true)fail('media-size-mime-or-redistribution-invalid');provenance(row.provenance);
  const file=localFile(directory,row.path,mediaUploadLimit),bytes=fs.readFileSync(file);if(bytes.length!==row.bytes||hash(bytes)!==row.sha256)fail('media-original-bytes-changed');
  const expected={id:row.id,object_key:`media/${row.sha256}`,sha256:row.sha256,bytes:row.bytes,mime:row.mime,name:row.name,license:row.license,attribution:row.attribution,source_id:row.source_id,metadata:JSON.parse(researchJSON(row.provenance))};
  objects.push({row,file,expected,proof_sha256:hash(researchJSON(expected))});
 }
 return {directory,manifest,manifest_sha256:hash(raw),objects};
}
function durableLedger(file,value){
 const directory=path.dirname(file);fs.mkdirSync(directory,{recursive:true});if(fs.existsSync(file)&&(!fs.lstatSync(file).isFile()||fs.lstatSync(file).isSymbolicLink()))fail('media-unsafe-receipt-path');
 const temporary=`${file}.tmp-${process.pid}-${randomUUID()}`;let fd;
 try{fd=fs.openSync(temporary,'wx',0o600);fs.writeFileSync(fd,researchJSON(value)+'\n');fs.fsyncSync(fd);fs.closeSync(fd);fd=null;fs.renameSync(temporary,file);const directoryFd=fs.openSync(directory,'r');try{fs.fsyncSync(directoryFd);}finally{fs.closeSync(directoryFd);}}
 finally{if(fd!=null)fs.closeSync(fd);if(fs.existsSync(temporary))fs.unlinkSync(temporary);}
}
function receiptProof(entry){return hash(researchJSON(Object.fromEntries(Object.entries(entry).filter(([key])=>key!=='receipt_sha256'))));}
function checkedLedger(bundle,origin,file){
 let ledger;if(fs.existsSync(file)){try{ledger=JSON.parse(fs.readFileSync(localFile(bundle.directory,path.relative(bundle.directory,file).split(path.sep).join('/'),2*1024*1024)));}catch(error){if(error.code?.startsWith('media-'))throw error;fail('media-invalid-receipt-json');}}
 else return {version:1,kind:'research-media-upload',origin,campaign_id:bundle.manifest.campaign_id,manifest_sha256:bundle.manifest_sha256,objects:[],complete:false};
 keys(ledger,['version','kind','origin','campaign_id','manifest_sha256','objects','complete','last_error_code'],['version','kind','origin','campaign_id','manifest_sha256','objects','complete']);
 if(ledger.version!==1||ledger.kind!=='research-media-upload'||ledger.origin!==origin||ledger.campaign_id!==bundle.manifest.campaign_id||ledger.manifest_sha256!==bundle.manifest_sha256||!Array.isArray(ledger.objects)||typeof ledger.complete!=='boolean'||ledger.last_error_code!=null&&!/^media-[a-z0-9-]+$/.test(ledger.last_error_code))fail('media-receipt-campaign-mismatch');
 const expected=new Map(bundle.objects.map(row=>[row.row.id,row])),seen=new Set();
 for(const entry of ledger.objects){keys(entry,['id','object_key','sha256','bytes','mime','name','license','attribution','source_id','metadata','proof_sha256','verified_at','verification','receipt_sha256']);const row=expected.get(entry.id);
  if(!row||seen.has(entry.id)||entry.proof_sha256!==row.proof_sha256||entry.receipt_sha256!==receiptProof(entry)||entry.verification!=='metadata-and-full-bytes'||!Number.isFinite(Date.parse(entry.verified_at))||Object.keys(row.expected).some(key=>researchJSON(entry[key])!==researchJSON(row.expected[key])))fail('media-receipt-proof-invalid');seen.add(entry.id);
 }
 if(ledger.complete&&ledger.objects.length!==bundle.objects.length)fail('media-incomplete-completion-receipt');return ledger;
}
async function boundedJSON(response,maxBytes=1024*1024){
 const reader=response.body?.getReader();if(!reader)fail('media-empty-api-response');const chunks=[];let bytes=0;
 try{for(;;){const {done,value}=await reader.read();if(done)break;bytes+=value.byteLength;if(bytes>maxBytes){await reader.cancel();fail('media-api-response-too-large');}chunks.push(Buffer.from(value));}}finally{reader.releaseLock();}
 try{return JSON.parse(Buffer.concat(chunks).toString('utf8'));}catch{fail('media-invalid-api-json');}
}
function metadataMatches(remote,expected){
 if(!object(remote)||!['ready','published'].includes(remote.status)||Object.keys(expected).some(key=>researchJSON(remote[key])!==researchJSON(expected[key])))fail('media-remote-immutable-metadata-mismatch');
}
async function verifyBytes(response,expected){
 if(!response.ok)fail(`media-readback-http-${response.status}`);if(response.headers.get('Content-Type')?.split(';')[0]!==expected.mime)fail('media-readback-mime-mismatch');
 const reader=response.body?.getReader();if(!reader)fail('media-readback-missing-body');const checksum=createHash('sha256');let bytes=0;
 try{for(;;){const {done,value}=await reader.read();if(done)break;bytes+=value.byteLength;if(bytes>expected.bytes){await reader.cancel();fail('media-readback-size-mismatch');}checksum.update(value);}}finally{reader.releaseLock();}
 if(bytes!==expected.bytes||checksum.digest('hex')!==expected.sha256)fail('media-readback-digest-mismatch');
}
export async function uploadResearchMedia({manifestFile,origin,token,request=fetch,wait=ms=>new Promise(resolve=>setTimeout(resolve,ms)),onProgress=()=>{},dryRun=false,receiptFile}={}){
 origin=researchOrigin(origin);const bundle=readResearchMedia(manifestFile);receiptFile=path.resolve(receiptFile||path.join(bundle.directory,'media-upload-receipts.json'));
 if(receiptFile===path.resolve(manifestFile)||bundle.objects.some(row=>row.file===receiptFile)||path.dirname(receiptFile)!==bundle.directory)fail('media-unsafe-receipt-path');
 const ledger=checkedLedger(bundle,origin,receiptFile);
 const uploads=bundle.objects.map(row=>{const params=new URLSearchParams(Object.fromEntries(['id','name','license','attribution','source_id'].map(key=>[key,row.expected[key]])));params.set('metadata',researchJSON(row.expected.metadata));const url=origin+'/api/media/upload?'+params;if(Buffer.byteLength(url)>16*1024)fail('media-upload-url-over-16-kib');return {row,url};});
 if(dryRun)return {dry_run:true,campaign_id:bundle.manifest.campaign_id,manifest_sha256:bundle.manifest_sha256,objects:uploads.length,bytes:uploads.reduce((sum,{row})=>sum+row.expected.bytes,0),network_requests:0};
 if(typeof token!=='string'||!token||token.length>8192||/[\r\n]/.test(token))fail('media-missing-site-service-credential');
 // Manifest text and receipts cannot accidentally retain the runtime credential.
 if(fs.readFileSync(manifestFile,'utf8').includes(token)||researchJSON(bundle.manifest).includes(token)||researchJSON(ledger).includes(token))fail('media-credential-in-input');
 const headers={'OAI-Sites-Authorization':`Bearer ${token}`};
 async function call(url,init={}){
  if(new URL(url).origin!==origin)fail('media-cross-origin-request');
  for(let attempt=0;attempt<4;attempt++){
   let response;try{response=await request(url,{...init,headers:{...headers,...init.headers},redirect:'manual',signal:AbortSignal.timeout(60000)});}catch{if(attempt===3)fail('media-network-unconfirmed');}
   if(response){if(response.status>=300&&response.status<400||response.url&&new URL(response.url).origin!==origin)fail('media-redirect-refused');if(![429,502,503,504].includes(response.status))return response;if(attempt===3)fail(`media-service-http-${response.status}`);}
   if(attempt<3)await wait(Math.min(4000,500*2**attempt));
  }
 }
 async function registered(expected){const response=await call(origin+`/api/media/${encodeURIComponent(expected.id)}?metadata=1`);if(response.headers.get('X-Atlas-Media-Metadata-Version')!=='1')fail('media-provenance-api-not-supported');if(response.status===404)return null;if(!response.ok)fail(`media-metadata-http-${response.status}`);const remote=await boundedJSON(response,32768);metadataMatches(remote,expected);return remote;}
 try{
  // Dependencies come from the generic source campaign; this command never invents sources.
  for(const [sourceIndex,source]of bundle.manifest.sources.entries()){onProgress({stage:'checking-sources',completed:sourceIndex,total:bundle.manifest.sources.length});let cursor='',found=false;const seen=new Set();for(let pages=0;pages<100;pages++){
   const params=new URLSearchParams({q:source.id,limit:'50',examples:'1',cursor}),response=await call(origin+'/api/catalog/sources?'+params);if(!response.ok)fail(`media-source-http-${response.status}`);const page=await boundedJSON(response);
   if(page.collection!=='sources'||!Array.isArray(page.records)||page.records.length>50)fail('media-invalid-source-catalog');const remote=page.records.find(row=>row.id===source.id);
   if(remote){if(Object.keys(source).some(key=>remote[key]!==source[key]))fail('media-source-identity-mismatch');found=true;break;}
   if(!page.next_cursor)break;if(typeof page.next_cursor!=='string'||seen.has(page.next_cursor))fail('media-invalid-source-cursor');seen.add(page.next_cursor);cursor=page.next_cursor;
  }if(!found)fail('media-source-dependency-missing');onProgress({stage:'checked-sources',completed:sourceIndex+1,total:bundle.manifest.sources.length});}
  for(const {row}of uploads){const archive=row.expected.metadata.source_archive;if(!archive?.media_id)continue;
   const response=await call(origin+`/api/media/${encodeURIComponent(archive.media_id)}?metadata=1`);if(response.headers.get('X-Atlas-Media-Metadata-Version')!=='1')fail('media-provenance-api-not-supported');if(!response.ok)fail('media-source-archive-dependency-missing');const remote=await boundedJSON(response,32768);
   if(remote?.id!==archive.media_id||remote.sha256!==archive.sha256||remote.object_key!==`media/${archive.sha256}`||!['ready','published'].includes(remote.status))fail('media-source-archive-identity-mismatch');
  }
  durableLedger(receiptFile,ledger);
  for(const {row,url}of uploads){
   onProgress({stage:'verifying',id:row.expected.id,completed:ledger.objects.length,total:uploads.length});let remote=await registered(row.expected);
   if(!remote){
    const bytes=fs.readFileSync(row.file);if(bytes.length!==row.expected.bytes||hash(bytes)!==row.expected.sha256)fail('media-original-bytes-changed');
    // Each retry first rereads the immutable identity, including a lost POST response.
    for(let attempt=0;attempt<4&&!remote;attempt++){
     let response;try{response=await request(url,{method:'POST',headers:{...headers,'Content-Type':row.expected.mime,Origin:origin},body:bytes,redirect:'manual',signal:AbortSignal.timeout(60000)});}catch{}
     if(response){if(response.status>=300&&response.status<400||response.url&&new URL(response.url).origin!==origin)fail('media-redirect-refused');if(response.ok){try{metadataMatches(await boundedJSON(response,32768),row.expected);}catch(error){if(error.code==='media-remote-immutable-metadata-mismatch'||error.code==='media-api-response-too-large')throw error;/* A truncated response is ambiguous; reread the immutable identity below. */}}else if(![429,502,503,504].includes(response.status))fail(`media-upload-http-${response.status}`);}
     remote=await registered(row.expected);if(!remote&&attempt===3)fail('media-upload-outcome-unconfirmed');if(!remote)await wait(Math.min(4000,500*2**attempt));
    }
   }
   await verifyBytes(await call(origin+`/api/media/${encodeURIComponent(row.expected.id)}`),row.expected);
   const existing=ledger.objects.find(entry=>entry.id===row.expected.id);if(!existing){const entry={...row.expected,proof_sha256:row.proof_sha256,verified_at:new Date().toISOString(),verification:'metadata-and-full-bytes'};entry.receipt_sha256=receiptProof(entry);ledger.objects.push(entry);}
   delete ledger.last_error_code;ledger.complete=false;durableLedger(receiptFile,ledger);onProgress({stage:'verified',id:row.expected.id,completed:ledger.objects.length,total:uploads.length});
  }
  ledger.complete=true;delete ledger.last_error_code;durableLedger(receiptFile,ledger);return {complete:true,campaign_id:ledger.campaign_id,manifest_sha256:ledger.manifest_sha256,verified_objects:ledger.objects.length,receipt:receiptFile};
 }catch(error){ledger.complete=false;ledger.last_error_code=typeof error.code==='string'&&/^media-[a-z0-9-]+$/.test(error.code)?error.code:'media-operation-unconfirmed';durableLedger(receiptFile,ledger);fail(ledger.last_error_code);}
}
async function hiddenCredential(){
 if(!process.stdin.isTTY)fail('media-credential-needs-hidden-terminal');process.stdin.setRawMode(true);process.stdout.write('Ready for private Site service credential JSON on hidden stdin.\n');
 return new Promise((resolve,reject)=>{let value='';const finish=()=>{process.stdin.pause();process.stdin.setRawMode(false);process.stdin.removeListener('data',receive);};const receive=chunk=>{if(chunk.includes(3)){finish();reject(Object.assign(Error('media-credential-entry-cancelled'),{code:'media-credential-entry-cancelled'}));return;}value+=chunk.toString();if(value.length>16384){finish();reject(Object.assign(Error('media-credential-entry-invalid'),{code:'media-credential-entry-invalid'}));return;}if(!/[\r\n]/.test(value))return;finish();try{const credential=JSON.parse(value.trim());if(typeof credential.token!=='string'||!credential.token)throw Error();resolve(credential.token);}catch{reject(Object.assign(Error('media-credential-entry-invalid'),{code:'media-credential-entry-invalid'}));}};process.stdin.on('data',receive);});
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{const args=process.argv.slice(2),dryRun=args.includes('--dry-run'),positional=args.filter(arg=>arg!=='--dry-run');if(positional.length!==2)fail('media-usage-origin-manifest-optional-dry-run');const [origin,manifestFile]=positional;
  // Complete preflight before prompting for a credential or making any request.
  const preview=await uploadResearchMedia({origin,manifestFile,dryRun:true});if(dryRun)console.log(JSON.stringify(preview));else{const token=await hiddenCredential();console.log(JSON.stringify(await uploadResearchMedia({origin,manifestFile,token,onProgress:progress=>console.log(progress.stage.includes('sources')?`Media source dependencies: ${progress.completed}/${progress.total} checked.`:`Media ${progress.stage}: ${progress.completed}/${progress.total} verified objects.`)})));}
 }catch(error){console.error(typeof error.code==='string'&&/^media-[a-z0-9-]+$/.test(error.code)?error.code:'media-workflow-validation-failed');process.exitCode=1;}
}
