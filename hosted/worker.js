import * as records from './records.js';
import {mapSnapshotPage} from './map-snapshots.js';
import {contentDatabase,storageReadOnly} from './content-backend.js';
import {exportStoragePage,exportStorageMarker} from './storage-export.js';
import {exportStoragePageV2,exportStorageMarkerV2,storageCatalogV2} from './storage-export-v2.js';
import {exportStoragePageV3,exportStorageMarkerV3,storageCatalogV3} from './storage-export-v3.js';
import {catalogPage,entityRelationshipsPage,entityMediaPage,capacityReport} from './research-catalog.js';
import * as geography from './geographic-releases.js';
import {importTemporalGeography,temporalGeographySnapshotPage,temporalGeographyEvidence} from './temporal-geography.js';
import {validYear} from '../src/model.js';
import {environmentClassifications} from '../src/environment-classifications.js';
import {typedCapabilities,typedRegistry,typedSnapshotPage,importTypedBatch} from './typed-observations.js';
import {legacyStorageMarker,legacyStoragePage,legacyStorageCatalog} from './storage-export-compat.js';

const json=(value,status=200,headers={})=>Response.json(value,{status,headers:{'Cache-Control':'no-store',...headers}});
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
   if(url.pathname==='/api/classifications'&&request.method==='GET')return json({version:1,unknown:null,attributes:environmentClassifications});
   if(storageReadOnly(env)&&['POST','PUT','PATCH','DELETE'].includes(request.method))return json({error:'Historical storage is read-only during a verified transfer',retryable:true},503);
   const db=contentDatabase(env);
   if(url.pathname==='/api/storage/export-marker'&&request.method==='GET')return json({...await exportStorageMarker(db),read_only:storageReadOnly(env)});
   if(url.pathname==='/api/storage/v2/export-marker'&&request.method==='GET')return json({...await legacyStorageMarker(db),read_only:storageReadOnly(env)});
   if(url.pathname==='/api/storage/v2/catalog'&&request.method==='GET'){
    const value=await legacyStorageCatalog(db);
    return value.legacy_projection?json(value.catalog,200,{'X-Atlas-Storage-Scope':'legacy-v2-projection','X-Atlas-Complete-Export-Version':'3'}):json(value);
   }
   if(url.pathname==='/api/storage/v3/export-marker'&&request.method==='GET')return json({...await exportStorageMarkerV3(db),read_only:storageReadOnly(env)});
   if(url.pathname==='/api/storage/v3/catalog'&&request.method==='GET')return json(await storageCatalogV3(db));
   const storageExportV3=/^\/api\/storage\/v3\/export\/([^/]+)$/.exec(url.pathname);
   if(storageExportV3&&request.method==='GET')return json(await exportStoragePageV3(db,storageExportV3[1],{cursor:url.searchParams.get('cursor')??'',limit:Number(url.searchParams.get('limit')||200)}));
   const storageExportV2=/^\/api\/storage\/v2\/export\/([^/]+)$/.exec(url.pathname);
   if(storageExportV2&&request.method==='GET')return json(await legacyStoragePage(db,storageExportV2[1],{cursor:url.searchParams.get('cursor')??'',limit:Number(url.searchParams.get('limit')||200)}));
   const storageExport=/^\/api\/storage\/export\/([^/]+)$/.exec(url.pathname);
   if(storageExport&&request.method==='GET')return json(await exportStoragePage(db,storageExport[1],{cursor:url.searchParams.get('cursor')??'',limit:Number(url.searchParams.get('limit')||200)}));
   if(url.pathname==='/api/typed/v1/capabilities'&&request.method==='GET')return json({...await typedCapabilities(db),read_only:storageReadOnly(env)});
   if(url.pathname==='/api/typed/v1/registry'&&request.method==='GET')return json(await typedRegistry(db));
   if(url.pathname==='/api/typed/v1/snapshot'&&request.method==='GET')return json(await typedSnapshotPage(db,selectedYear(url),{stream:url.searchParams.get('stream')??'observations',examples:url.searchParams.get('examples')==='1',cursor:url.searchParams.get('cursor')??'',limit:Number(url.searchParams.get('limit')??100)}));
   if(url.pathname==='/api/typed/v1/import'&&request.method==='POST'){
    sameOrigin(request);
    if(!request.headers.get('Content-Type')?.startsWith('application/json'))return json({error:'Typed import must be JSON'},415);
    return json(await importTypedBatch(db,JSON.parse(new TextDecoder().decode(await boundedBody(request,1024*1024)))));
   }
   if(url.pathname==='/api/storage/capacity'&&request.method==='GET')return json(await capacityReport(db,{databaseBudgetBytes:env.ATLAS_DATABASE_BUDGET_BYTES==null?null:Number(env.ATLAS_DATABASE_BUDGET_BYTES)}));
   if(url.pathname==='/api/map/snapshot'&&request.method==='GET')return json(await mapSnapshotPage(db,selectedYear(url),{examples:url.searchParams.get('examples')==='1',cursor:url.searchParams.get('cursor')??'',limit:Number(url.searchParams.get('limit')||1000),evidenceOnly:url.searchParams.get('evidence_only')==='1',includeTemporal:url.searchParams.get('include_temporal')==='1'}));
   const catalog=/^\/api\/catalog\/(sources|categories|entities)$/.exec(url.pathname);
   if(catalog&&request.method==='GET')return json(await catalogPage(db,catalog[1],{q:url.searchParams.get('q')??'',kind:url.searchParams.get('kind'),cursor:url.searchParams.get('cursor')??'',limit:Number(url.searchParams.get('limit')||250),examples:url.searchParams.get('examples')==='1',active:url.searchParams.has('active')?url.searchParams.get('active')==='1':null}));
   const graph=/^\/api\/entities\/([^/]+)\/(relationships|media)$/.exec(url.pathname);
   if(graph&&request.method==='GET'){const value=await (graph[2]==='relationships'?entityRelationshipsPage:entityMediaPage)(db,decodeURIComponent(graph[1]),selectedYear(url),{examples:url.searchParams.get('examples')==='1',cursor:url.searchParams.get('cursor')??'',limit:Number(url.searchParams.get('limit')||250)});return value?json(value):json({error:'Entity not found'},404);}
   if(url.pathname==='/api/storage'&&request.method==='GET')return json(await records.storageOverview(db));
   if(url.pathname==='/api/attributes'&&request.method==='GET')return json(await records.attributesAt(db,selectedYear(url),{examples:url.searchParams.get('examples')==='1',cursor:url.searchParams.get('cursor')??'',limit:Number(url.searchParams.get('limit')||250),locationIds:url.searchParams.has('location_id')?url.searchParams.getAll('location_id'):undefined}));
   if(url.pathname==='/api/names'&&request.method==='GET')return json(await records.namesAt(db,selectedYear(url),{examples:url.searchParams.get('examples')==='1',mapOnly:url.searchParams.get('scope')==='map',cursor:url.searchParams.get('cursor')??'',limit:Number(url.searchParams.get('limit')||250)}));
   if(url.pathname==='/api/retirements'&&request.method==='GET')return json(await records.retirementsAt(db,selectedYear(url),{examples:url.searchParams.get('examples')==='1',mapOnly:url.searchParams.get('scope')==='map',cursor:url.searchParams.get('cursor')??'',limit:Number(url.searchParams.get('limit')||250)}));
   if(url.pathname.startsWith('/api/entities/')&&request.method==='GET')return json(await records.entityProfile(db,decodeURIComponent(url.pathname.slice('/api/entities/'.length)),selectedYear(url),{examples:url.searchParams.get('examples')==='1',releaseId:url.searchParams.get('release_id')}));
   if(url.pathname==='/api/geography/release'&&request.method==='GET')return json(await geography.geographicRelease(db,url.searchParams.get('release_id')));
   if(url.pathname==='/api/geography/memberships'&&request.method==='GET')return json(await geography.geographicMembershipPage(db,{releaseId:url.searchParams.get('release_id'),cursor:url.searchParams.get('cursor')??'',limit:Number(url.searchParams.get('limit')||250),parentId:url.searchParams.get('parent_id'),active:url.searchParams.get('include_archived')==='1'?null:true}));
   if(url.pathname==='/api/geography/changes'&&request.method==='GET')return json(await geography.geographicChangePage(db,{releaseId:url.searchParams.get('release_id'),cursor:url.searchParams.get('cursor')??'',limit:Number(url.searchParams.get('limit')||250)}));
   if(url.pathname==='/api/geography/temporal/snapshot'&&request.method==='GET')return json(await temporalGeographySnapshotPage(db,selectedYear(url),{releaseId:url.searchParams.get('release_id'),examples:url.searchParams.get('examples')==='1',cursor:url.searchParams.get('cursor')??'',limit:Number(url.searchParams.get('limit')||200),stream:url.searchParams.get('stream')??'records'}));
   const temporalEvidence=/^\/api\/geography\/temporal\/evidence\/(memberships|existence)\/([^/]+)$/.exec(url.pathname);
   if(temporalEvidence&&request.method==='GET'){
    const evidence=await temporalGeographyEvidence(db,temporalEvidence[1],decodeURIComponent(temporalEvidence[2]));
    return evidence?json(evidence):json({error:'Geographic evidence not found'},404);
   }
   if(url.pathname==='/api/geography/temporal/import'&&request.method==='POST'){
    sameOrigin(request);
    if(!request.headers.get('Content-Type')?.startsWith('application/json'))return json({error:'Dated geography import must be JSON'},415);
    return json(await importTemporalGeography(db,JSON.parse(new TextDecoder().decode(await boundedBody(request,1024*1024)))));
   }
   if(['/api/geography/stage','/api/geography/finalize'].includes(url.pathname)&&request.method==='POST'){
    sameOrigin(request);
    if(!request.headers.get('Content-Type')?.startsWith('application/json'))return json({error:'Geographic release must be JSON'},415);
    const payload=JSON.parse(new TextDecoder().decode(await boundedBody(request,1024*1024)));
    return json(url.pathname.endsWith('/stage')?await geography.stageGeographicRelease(db,payload):await geography.finalizeGeographicRelease(db,payload.release_id));
   }
   if(url.pathname.startsWith('/api/evidence/')&&request.method==='GET'){
    const [collection,...parts]=url.pathname.slice('/api/evidence/'.length).split('/');
    return json(await records.evidenceHistory(db,collection,decodeURIComponent(parts.join('/')),{examples:url.searchParams.get('examples')==='1'}));
   }
   if(url.pathname==='/api/records/import'&&request.method==='POST'){
    sameOrigin(request);
    if(!request.headers.get('Content-Type')?.startsWith('application/json'))return json({error:'Import must be JSON'},415);
    const text=new TextDecoder().decode(await boundedBody(request,1024*1024));
    return json(await records.importBatch(db,JSON.parse(text)));
   }
   if(url.pathname==='/api/media/upload'&&request.method==='POST'){
    sameOrigin(request);if(!env.BUCKET)return json({error:'Media storage is temporarily unavailable'},503);
    const metadataText=url.searchParams.get('metadata')??'{}';
    if(new TextEncoder().encode(metadataText).byteLength>4096)return json({error:'Media provenance must be at most 4096 bytes'},413);
    let metadata;try{metadata=JSON.parse(metadataText);}catch{return json({error:'Media provenance must be a JSON object'},400);}
    if(!metadata||typeof metadata!=='object'||Array.isArray(metadata))return json({error:'Media provenance must be a JSON object'},400);
    const length=Number(request.headers.get('Content-Length'));
    if(length>20*1024*1024)return json({error:'This upload endpoint accepts media files up to 20 MiB'},413);
    const bytes=await boundedBody(request,20*1024*1024);
    const sha256=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(b=>b.toString(16).padStart(2,'0')).join('');
    const object_key=`media/${sha256}`,mime=request.headers.get('Content-Type')||'application/octet-stream';
    const input={id:url.searchParams.get('id')||`media:${sha256}`,object_key,sha256,bytes:bytes.byteLength,mime,source_id:url.searchParams.get('source_id'),name:url.searchParams.get('name')||sha256,license:url.searchParams.get('license'),attribution:url.searchParams.get('attribution'),metadata};
    // Validate relational metadata before writing blob bytes. Published objects
    // are content-addressed, so another upload never overwrites earlier media.
    await records.validateMedia(db,input);
    if(!await env.BUCKET.head(object_key))await env.BUCKET.put(object_key,bytes,{httpMetadata:{contentType:mime}});
    return json(await records.registerMedia(db,input));
   }
   if(url.pathname.startsWith('/api/media/')&&request.method==='GET'){
    const metadataOnly=url.searchParams.get('metadata')==='1';
    const mediaHeaders=metadataOnly?{'X-Atlas-Media-Metadata-Version':'1'}:{};
    const media=await records.mediaById(db,decodeURIComponent(url.pathname.slice('/api/media/'.length)));
    if(!media)return json({error:'Media not found'},404,mediaHeaders);
    if(metadataOnly)return json(media,200,mediaHeaders);
    if(!env.BUCKET)return json({error:'Media storage is temporarily unavailable'},503);
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
   return json({error:status===503?'Atlas storage is temporarily unavailable':error.message,...(error.retryable?{retryable:true}:{}),...(['unknown','committed','rolled-back-or-not-started'].includes(error.commit_status)?{commit_status:error.commit_status}:{}),...(Number.isInteger(error.suggested_limit)?{suggested_limit:error.suggested_limit}:{})},status);
  }
 }
};
