import * as records from './records.js';
import * as geography from './geographic-releases.js';
import {validYear} from '../src/model.js';

const json=(value,status=200)=>Response.json(value,{status,headers:{'Cache-Control':'no-store'}});
function sameOrigin(request){
 const origin=request.headers.get('Origin');
 if(origin&&origin!==new URL(request.url).origin)throw Object.assign(new Error('Cross-origin writes are not permitted'),{status:403});
}
function selectedYear(url){const year=Number(url.searchParams.get('year')??2026);if(!validYear(year))throw Object.assign(new Error('Year must be between 3000 BC and 2026 AD, excluding zero'),{status:400});return year;}
async function boundedBody(request,limit){
 if(!request.body)return new Uint8Array();
 const reader=request.body.getReader(),chunks=[];let length=0;
 try{for(;;){const {done,value}=await reader.read();if(done)break;length+=value.byteLength;if(length>limit){await reader.cancel();throw Object.assign(new Error('Request exceeds the supported upload size'),{status:413});}chunks.push(value);}}
 finally{reader.releaseLock();}
 const bytes=new Uint8Array(length);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength;}return bytes;
}
export default {
 async fetch(request,env,ctx){
  const url=new URL(request.url);
  if(!url.pathname.startsWith('/api/'))return env.ASSETS.fetch(request);
  try{
   if(!env.DB) return json({error:'Historical database is temporarily unavailable'},503);
   if(url.pathname==='/api/storage'&&request.method==='GET')return json(await records.storageOverview(env.DB));
   if(url.pathname==='/api/attributes'&&request.method==='GET')return json(await records.attributesAt(env.DB,selectedYear(url),{examples:url.searchParams.get('examples')==='1',cursor:url.searchParams.get('cursor')??'',limit:Number(url.searchParams.get('limit')||250),locationIds:url.searchParams.has('location_id')?url.searchParams.getAll('location_id'):undefined}));
   if(url.pathname==='/api/names'&&request.method==='GET')return json(await records.namesAt(env.DB,selectedYear(url),{examples:url.searchParams.get('examples')==='1',mapOnly:url.searchParams.get('scope')==='map',cursor:url.searchParams.get('cursor')??'',limit:Number(url.searchParams.get('limit')||250)}));
   if(url.pathname==='/api/retirements'&&request.method==='GET')return json(await records.retirementsAt(env.DB,selectedYear(url),{examples:url.searchParams.get('examples')==='1',mapOnly:url.searchParams.get('scope')==='map',cursor:url.searchParams.get('cursor')??'',limit:Number(url.searchParams.get('limit')||250)}));
   if(url.pathname.startsWith('/api/entities/')&&request.method==='GET')return json(await records.entityProfile(env.DB,decodeURIComponent(url.pathname.slice('/api/entities/'.length)),selectedYear(url),{examples:url.searchParams.get('examples')==='1',releaseId:url.searchParams.get('release_id')}));
   if(url.pathname==='/api/geography/release'&&request.method==='GET')return json(await geography.geographicRelease(env.DB,url.searchParams.get('release_id')));
   if(url.pathname==='/api/geography/memberships'&&request.method==='GET')return json(await geography.geographicMembershipPage(env.DB,{releaseId:url.searchParams.get('release_id'),cursor:url.searchParams.get('cursor')??'',limit:Number(url.searchParams.get('limit')||250),parentId:url.searchParams.get('parent_id'),active:url.searchParams.get('include_archived')==='1'?null:true}));
   if(url.pathname==='/api/geography/changes'&&request.method==='GET')return json(await geography.geographicChangePage(env.DB,{releaseId:url.searchParams.get('release_id'),cursor:url.searchParams.get('cursor')??'',limit:Number(url.searchParams.get('limit')||250)}));
   if(['/api/geography/stage','/api/geography/finalize'].includes(url.pathname)&&request.method==='POST'){
    sameOrigin(request);
    if(!request.headers.get('Content-Type')?.startsWith('application/json'))return json({error:'Geographic release must be JSON'},415);
    const payload=JSON.parse(new TextDecoder().decode(await boundedBody(request,1024*1024)));
    return json(url.pathname.endsWith('/stage')?await geography.stageGeographicRelease(env.DB,payload):await geography.finalizeGeographicRelease(env.DB,payload.release_id));
   }
   if(url.pathname.startsWith('/api/evidence/')&&request.method==='GET'){
    const [collection,...parts]=url.pathname.slice('/api/evidence/'.length).split('/');
    return json(await records.evidenceHistory(env.DB,collection,decodeURIComponent(parts.join('/')),{examples:url.searchParams.get('examples')==='1'}));
   }
   if(url.pathname==='/api/records/import'&&request.method==='POST'){
    sameOrigin(request);
    if(!request.headers.get('Content-Type')?.startsWith('application/json'))return json({error:'Import must be JSON'},415);
    const text=new TextDecoder().decode(await boundedBody(request,1024*1024));
    return json(await records.importBatch(env.DB,JSON.parse(text)));
   }
   if(url.pathname==='/api/media/upload'&&request.method==='POST'){
    sameOrigin(request);if(!env.BUCKET)return json({error:'Media storage is temporarily unavailable'},503);
    const length=Number(request.headers.get('Content-Length'));
    if(length>20*1024*1024)return json({error:'This upload endpoint accepts media files up to 20 MiB'},413);
    const bytes=await boundedBody(request,20*1024*1024);
    const sha256=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(b=>b.toString(16).padStart(2,'0')).join('');
    const object_key=`media/${sha256}`,mime=request.headers.get('Content-Type')||'application/octet-stream';
    const input={id:url.searchParams.get('id')||`media:${sha256}`,object_key,sha256,bytes:bytes.byteLength,mime,source_id:url.searchParams.get('source_id'),name:url.searchParams.get('name')||sha256,license:url.searchParams.get('license'),attribution:url.searchParams.get('attribution')};
    // Validate relational metadata before writing blob bytes. Published objects
    // are content-addressed, so another upload never overwrites earlier media.
    await records.validateMedia(env.DB,input);
    if(!await env.BUCKET.head(object_key))await env.BUCKET.put(object_key,bytes,{httpMetadata:{contentType:mime}});
    return json(await records.registerMedia(env.DB,input));
   }
   if(url.pathname.startsWith('/api/media/')&&request.method==='GET'){
    if(!env.BUCKET)return json({error:'Media storage is temporarily unavailable'},503);
    const media=await records.mediaById(env.DB,decodeURIComponent(url.pathname.slice('/api/media/'.length)));
    if(!media)return json({error:'Media not found'},404);
    if(request.headers.has('Range')){
     const range=/^bytes=(\d*)-(\d*)$/.exec(request.headers.get('Range'));
     const start=range?.[1]?Number(range[1]):null,end=range?.[2]?Number(range[2]):null;
     if(!range||start==null&&!(end>0)||start!=null&&(!Number.isSafeInteger(start)||start>=media.bytes)||end!=null&&!Number.isSafeInteger(end)||start!=null&&end!=null&&end<start)return new Response(null,{status:416,headers:{'Content-Range':`bytes */${media.bytes}`}});
    }
    const object=await env.BUCKET.get(media.object_key,request.headers.has('Range')?{range:request.headers}:undefined);if(!object)return json({error:'Media bytes unavailable'},503);
    const safeInline=/^(image\/(png|jpeg|webp|gif)|audio\/|video\/|application\/pdf)/i.test(media.mime);
    const headers=new Headers({'Content-Type':media.mime,'X-Content-Type-Options':'nosniff','Cache-Control':'private, max-age=3600','Content-Disposition':safeInline?'inline':'attachment','Accept-Ranges':'bytes'});if(object.httpEtag)headers.set('ETag',object.httpEtag);
    const partial=request.headers.has('Range')&&object.range?.length!=null;
    if(partial){const {offset=0,length}=object.range;headers.set('Content-Range',`bytes ${offset}-${offset+length-1}/${object.size}`);headers.set('Content-Length',String(length));}
    return new Response(object.body,{headers,status:partial?206:200});
   }
   return json({error:'Not found'},404);
  }catch(error){
   console.error('Atlas request failed',url.pathname,error.message);
   const status=error.status||(error instanceof SyntaxError?400:503);
   return json({error:status===503?'Atlas storage is temporarily unavailable':error.message,...(error.retryable?{retryable:true}:{})},status);
  }
 }
};
