import {resolveTypedSnapshot,canonicalTypedJSON,retainedTypedJSON} from './typed-snapshot.js';
import {observationContract,observationDigest} from './observation-modules.js';

const maxBytes=64*1024*1024;
function abortable(promise,signal){
 if(signal.aborted)return Promise.reject(signal.reason);
 return new Promise((resolve,reject)=>{
  const abort=()=>reject(signal.reason);signal.addEventListener('abort',abort,{once:true});
  Promise.resolve(promise).then(resolve,reject).finally(()=>signal.removeEventListener('abort',abort));
 });
}
async function boundedLoad({signal,timeoutMs=60000},callback){
 if(!Number.isSafeInteger(timeoutMs)||timeoutMs<1||timeoutMs>120000)throw Error('Invalid typed load deadline');
 const controller=new AbortController(),abort=()=>controller.abort(signal.reason);
 if(signal?.aborted)abort();else signal?.addEventListener('abort',abort,{once:true});
 const timer=setTimeout(()=>controller.abort(new DOMException('Typed evidence load deadline exceeded','TimeoutError')),timeoutMs);
 try{controller.signal.throwIfAborted();return await abortable(callback(controller.signal),controller.signal);}finally{clearTimeout(timer);signal?.removeEventListener('abort',abort);}
}
async function readBytes(response,limit,signal){
 if(!response.ok)throw Object.assign(Error('Typed evidence request failed'),{status:response.status});
 const reader=response.body.getReader(),chunks=[];let length=0;
 try{for(;;){const {value,done}=await abortable(reader.read(),signal);if(done)break;length+=value.length;if(length>limit)throw Error('Typed evidence response exceeds its byte budget');chunks.push(value);}}
 finally{void reader.cancel().catch(()=>{});reader.releaseLock();}
 const bytes=new Uint8Array(length);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length;}return bytes;
}
export async function loadPreparedTypedEvidence(options){
 return boundedLoad(options,signal=>loadPreparedCore({...options,signal}));
}
async function loadPreparedCore({url,sha256,year,examples=false,fetcher=fetch,signal}){
 if(!/^[a-f0-9]{64}$/.test(sha256??''))throw Error('Prepared typed evidence requires an exact byte hash');
 const bytes=await readBytes(await abortable(fetcher(url,{credentials:'same-origin',signal}),signal),maxBytes,signal);
 const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),byte=>byte.toString(16).padStart(2,'0')).join('');
 if(digest!==sha256)throw Error('Prepared typed evidence bytes differ from the descriptor');
 return resolveTypedSnapshot(JSON.parse(new TextDecoder().decode(bytes)),year,{examples});
}

/** Opt-in domain seam. A changed marker rejects the entire load; callers may
 * start a fresh bounded load, never concatenate snapshots from two revisions. */
export async function loadHostedTypedEvidence(options){
 return boundedLoad(options,signal=>loadHostedCore({...options,signal}));
}
async function loadHostedCore({origin,year,examples=false,limit=100,fetcher=fetch,signal}){
 const contract=await observationContract(),collections={observations:[],feature_links:[],retirements:[]};
 const catalogs={sources:new Map(),entities:new Map(),derivation_inputs:new Map()},sourcePins=new Map();
 let fingerprint=null,revision=null,geographyPins=null,bytes=0,pages=0;
 const merge=(map,key,value)=>{const prior=map.get(key);if(prior&&canonicalTypedJSON(prior)!==canonicalTypedJSON(value))throw Error('Typed context changed across pages');map.set(key,value);if(map.size>100000)throw Error('Typed context exceeds its identity budget');};
 for(const stream of Object.keys(collections)){
  let cursor='',total=null;const cursors=new Set(),identities=new Set();
  do{
   if(++pages>3000)throw Error('Typed snapshot exceeds its page budget');
   const url=new URL('/api/typed/v1/snapshot',origin);for(const [key,value]of Object.entries({year,examples:Number(examples),stream,limit,cursor}))url.searchParams.set(key,value);
   const raw=await readBytes(await abortable(fetcher(url,{credentials:'same-origin',signal}),signal),8*1024*1024,signal);bytes+=raw.length;if(bytes>maxBytes)throw Error('Typed snapshot exceeds its aggregate byte budget');
   const page=JSON.parse(new TextDecoder().decode(raw));
   if(page.version!==1||page.year!==year||page.stream!==stream||page.examples!==Number(examples)||page.registry_sha256!==contract.registry_sha256||!Array.isArray(page.rows)||!Number.isSafeInteger(page.total)||page.total<0||page.total>100000)throw Error('Invalid typed snapshot page');
   if(fingerprint===null){fingerprint=page.fingerprint;revision=page.revision;geographyPins=page.geography_pins;}
   if(typeof fingerprint!=='string'||!/^[a-f0-9]{64}$/.test(fingerprint)||page.fingerprint!==fingerprint||page.revision!==revision)throw Error('Typed snapshot changed; restart all streams');
   if(canonicalTypedJSON(page.geography_pins)!==canonicalTypedJSON(geographyPins))throw Error('Typed territory changed across pages');
   if(total===null)total=page.total;if(page.total!==total)throw Error('Typed stream total changed');
   for(const row of page.rows){if(identities.has(row.id))throw Error('Repeated typed snapshot identity');identities.add(row.id);collections[stream].push(row);}
   for(const key of ['sources','entities']){if(!Array.isArray(page[key]))throw Error('Missing typed context');for(const row of page[key])merge(catalogs[key],row.id,row);}
   for(const entry of page.derivation_inputs??[])merge(catalogs.derivation_inputs,JSON.stringify([entry.kind,entry.row.id]),entry);
   for(const pin of page.source_pins??[])merge(sourcePins,pin.id,pin);
   cursor=page.next_cursor;if(cursor!==null&&(typeof cursor!=='string'||!cursor||cursors.has(cursor)||!page.rows.length))throw Error('Invalid or circular typed page cursor');cursors.add(cursor);
  }while(cursor!==null);
  if(collections[stream].length!==total)throw Error('Incomplete typed snapshot stream');
 }
 const sources=[...catalogs.sources.values()];
 const columns=['id','name','url','license','vintage','supported_from','supported_to','status','metadata'];
 if(sourcePins.size!==sources.length)throw Error('Incomplete original source pins');
 for(const source of sources){if(typeof source.original_metadata_json!=='string')throw Error('Missing original source bytes');retainedTypedJSON(source.metadata,source.original_metadata_json,'source metadata',{objectRequired:true});const raw={...source,metadata:source.original_metadata_json};if(await observationDigest(columns.map(key=>raw[key]))!==sourcePins.get(source.id)?.sha256)throw Error('Typed source bytes differ from their pin');}
 const resolved=await resolveTypedSnapshot({version:1,registry_sha256:contract.registry_sha256,geography_pins:geographyPins,...collections,sources,entities:[...catalogs.entities.values()],derivation_inputs:[...catalogs.derivation_inputs.values()]},year,{examples});
 return {...resolved,fingerprint,revision};
}
