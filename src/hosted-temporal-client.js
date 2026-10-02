import {validYear} from './model.js';
import {hydrateHostedTemporalGeographyPage,mergeHostedTemporalHistory} from './hosted-temporal-geography.js';

const object=value=>value!==null&&typeof value==='object'&&!Array.isArray(value);
const text=value=>typeof value==='string'&&Boolean(value.trim());
const canonical=value=>Array.isArray(value)?value.map(canonical):object(value)?Object.fromEntries(Object.keys(value).sort().map(key=>[key,canonical(value[key])])):value;
const same=(left,right)=>JSON.stringify(canonical(left))===JSON.stringify(canonical(right));
function failure(code,{retryable=false,status}={}){return Object.assign(Error(code),{code,retryable,...(status?{status}:{})});}
const invalid=code=>{throw failure(`temporal-geography-${code}`);};
const drift=code=>{throw failure(`temporal-geography-${code}`,{retryable:true,status:409});};
function expectedPins(value){
 if(!object(value)||!text(value.release_id??value.id)||!['hierarchy_sha256','footprints_sha256'].every(key=>/^[a-f0-9]{64}$/.test(value[key]??'')))invalid('invalid-expected-pins');
 return {release_id:value.release_id??value.id,hierarchy_sha256:value.hierarchy_sha256,footprints_sha256:value.footprints_sha256};
}
function sourceValid(source){
 if(!object(source)||!text(source.id)||!text(source.name)||!text(source.license)||!text(String(source.vintage??''))||!['historical','reference','estimate','example'].includes(source.status)||!validYear(source.supported_from)||!(validYear(source.supported_to)||source.supported_to===2027)||source.supported_to<=source.supported_from)invalid('invalid-source');
 if(source.url!=null){let url;try{url=new URL(source.url);}catch{invalid('invalid-source-url');}if(!['http:','https:'].includes(url.protocol))invalid('invalid-source-url');}
 let metadata=source.metadata;if(typeof metadata==='string')try{metadata=JSON.parse(metadata);}catch{invalid('invalid-source-metadata');}if(!object(metadata))invalid('invalid-source-metadata');
}
function cancelled(signal){if(signal?.aborted)throw signal.reason??new DOMException('Aborted','AbortError');}
function abortable(operation,signal){
 cancelled(signal);
 return new Promise((resolve,reject)=>{
  const stop=()=>{signal.removeEventListener('abort',stop);reject(signal.reason??new DOMException('Aborted','AbortError'));};signal.addEventListener('abort',stop,{once:true});
  Promise.resolve().then(operation).then(value=>{signal.removeEventListener('abort',stop);resolve(value);},error=>{signal.removeEventListener('abort',stop);reject(error);});
 });
}
function boundedInteger(value,min,max,name){if(!Number.isSafeInteger(value)||value<min||value>max)invalid(`invalid-${name}`);}

/** Read only affected membership/existence rows and permanent withdrawals.
 * apiGet receives a relative API URL plus {signal}; it returns parsed JSON or
 * throws {status,retryable,suggested_limit}. No partial result is authoritative.
 * A scalar-snapshot expectedRevision stays fixed: drift is returned to the
 * caller to reload the entire scalar + geographic snapshot, never repinned.
 */
export async function loadHostedTemporalGeography({apiGet,year,examples=false,expectedGeography,expectedRevision,signal,legacyHistory=[],limit=200,maxAttempts=2,maxPages=2000,maxRows=150000,maxBytes=64*1024*1024,onProgress=()=>{}}={}){
 if(typeof apiGet!=='function'||!validYear(year)||typeof examples!=='boolean'||!Array.isArray(legacyHistory)||typeof onProgress!=='function')invalid('invalid-loader-options');
 const pins=expectedPins(expectedGeography);if(expectedRevision!==undefined&&(!Number.isSafeInteger(expectedRevision)||expectedRevision<0))invalid('invalid-expected-revision');
 boundedInteger(limit,1,200,'limit');boundedInteger(maxAttempts,1,3,'attempts');boundedInteger(maxPages,2,100000,'page-budget');boundedInteger(maxRows,0,1000000,'row-budget');boundedInteger(maxBytes,1024,256*1024*1024,'byte-budget');cancelled(signal);
 for(let attempt=0;attempt<maxAttempts;attempt++){
  const controller=new AbortController(),forwardAbort=()=>controller.abort(signal.reason);signal?.addEventListener('abort',forwardAbort,{once:true});
  const sources=new Map(),records=new Map(),withdrawals=new Map();let revision=expectedRevision,pages=0,bytes=0;
  const add=(target,key,value,kind)=>{if(target.has(key)){if(!same(target.get(key),value))invalid(`conflicting-${kind}`);return;}target.set(key,value);};
  async function stream(kind){
   let cursor='',pageLimit=limit;const cursors=new Set();
   for(;;){
    cancelled(controller.signal);if(++pages>maxPages)invalid('page-budget-exceeded');
    const params=new URLSearchParams({year:String(year),examples:String(Number(examples)),stream:kind,cursor,limit:String(pageLimit)});let page;
    try{page=await abortable(()=>apiGet('/api/geography/temporal/snapshot?'+params,{signal:controller.signal}),controller.signal);}
    catch(error){
     cancelled(signal);
     if(error?.status===413&&error.retryable&&pageLimit>1){const suggested=error.suggested_limit;if(suggested!==undefined&&(!Number.isSafeInteger(suggested)||suggested<1||suggested>=pageLimit))invalid('invalid-suggested-limit');pageLimit=suggested??Math.max(1,Math.floor(pageLimit/2));continue;}
     if(error?.status===409)drift('revision-or-publication-changed');throw error;
    }
    cancelled(controller.signal);
    if(!object(page)||page.stream!==kind||page.year!==year||!Number.isSafeInteger(page.revision)||page.revision<0)invalid('invalid-stream-page');
    if(['release_id','hierarchy_sha256','footprints_sha256'].some(key=>page[key]!==pins[key]))drift('pin-mismatch');
    if(revision===undefined)revision=page.revision;else if(page.revision!==revision)drift('revision-mismatch');
    if(!Array.isArray(page.records)||!Array.isArray(page.withdrawals)||!Array.isArray(page.sources)||page.records.length>pageLimit*2||page.withdrawals.length>pageLimit||page.sources.length>page.records.length+page.withdrawals.length||kind==='records'&&page.withdrawals.length||kind==='withdrawals'&&page.records.length)invalid('invalid-stream-bounds');
    if(page.next_cursor!==null&&(!text(page.next_cursor)||page.next_cursor.length>2000))invalid('invalid-next-cursor');
    if(page.next_cursor!==null&&(page.next_cursor===cursor||cursors.has(page.next_cursor)))invalid('repeated-cursor');
    let pageBytes;try{pageBytes=new TextEncoder().encode(JSON.stringify(page)).byteLength;}catch{invalid('invalid-page-json');}if(pageBytes>8*1024*1024)invalid('page-byte-budget-exceeded');bytes+=pageBytes;if(bytes>maxBytes)invalid('byte-budget-exceeded');
    const pageSources=new Map();for(const source of page.sources){sourceValid(source);pageSources.set(source.id,source);}
    for(const row of [...page.records,...page.withdrawals])if(!object(row)||!pageSources.has(row.source_id))invalid('missing-page-source');
    // Each page is validated independently; complete validation below also
    // catches cross-page winning-field conflicts, withdrawals and bad chains.
    hydrateHostedTemporalGeographyPage(page,{year,examples,expectedGeography:pins});
    for(const source of page.sources)add(sources,source.id,source,'source');
    for(const row of page.records)add(records,`${row.collection}/${row.id}`,row,'claim');
    for(const row of page.withdrawals)add(withdrawals,row.id,row,'withdrawal');
    if(records.size+withdrawals.size>maxRows)invalid('row-budget-exceeded');
    onProgress({stream:kind,pages,rows:records.size+withdrawals.size,sources:sources.size,revision});
    if(page.next_cursor===null)return;cursors.add(page.next_cursor);cursor=page.next_cursor;
   }
  }
  try{
   await Promise.all([stream('records'),stream('withdrawals')]);cancelled(signal);
   const compare=(left,right)=>left<right?-1:left>right?1:0,ordered=map=>[...map.values()].sort((left,right)=>compare(left.id,right.id));
   const claims=[...records.values()].sort((left,right)=>compare(left.entity_id,right.entity_id)||compare(left.collection,right.collection)||compare(left.id,right.id));
   // Raw source observations were compared before normalization. Parse legacy
   // JSON metadata once so every hydrated claim can share its source object.
   const sharedSources=ordered(sources).map(source=>typeof source.metadata==='string'?{...source,metadata:JSON.parse(source.metadata)}:source);
   const combinedSnapshot={year,stream:'records',...pins,records:claims,withdrawals:ordered(withdrawals),sources:sharedSources,next_cursor:null,revision,capability:{datedMembership:1,datedExistence:1,datedFootprints:0}};
   hydrateHostedTemporalGeographyPage(combinedSnapshot,{year,examples,expectedGeography:pins,complete:true});cancelled(signal);
   const mergedHistory=mergeHostedTemporalHistory(legacyHistory,combinedSnapshot,{year,examples,expectedGeography:pins,complete:true});
   return {available:true,complete:true,revision,combinedSnapshot,mergedHistory};
  }catch(error){
   controller.abort(error);cancelled(signal);
   if(expectedRevision===undefined&&error?.retryable&&error.status===409&&attempt+1<maxAttempts)continue;
   throw error;
  }finally{signal?.removeEventListener('abort',forwardAbort);}
 }
 throw failure('temporal-geography-retries-exhausted',{retryable:true,status:409});
}
