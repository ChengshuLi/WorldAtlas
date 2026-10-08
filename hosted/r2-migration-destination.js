import {readOnlyR2Export, migrationAuthorized} from './site-r2-export.js';

const MAX = 32 * 1024 * 1024;
const encoder = new TextEncoder();
const json = (body,status)=>new Response(JSON.stringify(body),{status,headers:{'Content-Type':'application/json','Cache-Control':'no-store'}});
// Separately provisioned temporary Worker, never the public atlas Worker.
// This destination binding can only atomically create absent objects. Its GET
// paths share the expiring exporter authentication and full metadata inventory.
const reader = readOnlyR2Export({fetch:()=>json({error:'Not found'},404)});
export default {
  async fetch(request,env,context) {
    const url = new URL(request.url);
    if (request.method !== 'PUT' || url.pathname !== '/api/_migration/r2/object') return reader.fetch(request,env,context);
    if (!await migrationAuthorized(request,env)) return json({error:'Not found'},404);
    const key = url.searchParams.get('key'), size = Number(request.headers.get('Content-Length'));
    if (!key || encoder.encode(key).length>1024 || !request.headers.has('Content-Length') || !Number.isSafeInteger(size) || size<0 || size>MAX) return json({error:'Invalid object bounds'},400);
    const expected = request.headers.get('X-Migration-Sha256');
    if (!/^[a-f0-9]{64}$/.test(expected??'')) return json({error:'Invalid checksum'},400);
    let metadata;
    try {
      const header=request.headers.get('X-Migration-Metadata');
      if (!header || header.length>16384) throw Error();
      metadata=JSON.parse(decodeURIComponent(header));
      if (!metadata.httpMetadata || !metadata.customMetadata || !['Standard','InfrequentAccess'].includes(metadata.storageClass??'Standard')) throw Error();
      if (metadata.httpMetadata.cacheExpiry) {
        metadata.httpMetadata.cacheExpiry=new Date(metadata.httpMetadata.cacheExpiry);
        if (!Number.isFinite(metadata.httpMetadata.cacheExpiry.getTime())) throw Error();
      }
    } catch {return json({error:'Invalid object metadata'},400);}
    try {
      const chunks=[];let bytes=0;
      if (request.body) for await (const chunk of request.body) {
        bytes+=chunk.byteLength;
        if (bytes>size || bytes>MAX) return json({error:'Body too large'},413);
        chunks.push(chunk);
      }
      if (bytes!==size) return json({error:'Incomplete body'},400);
      const body=new Uint8Array(bytes);let offset=0;
      for(const chunk of chunks){body.set(chunk,offset);offset+=chunk.byteLength;}
      const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',body)),byte=>byte.toString(16).padStart(2,'0')).join('');
      if (digest!==expected) return json({error:'Checksum mismatch'},400);
      if (!await migrationAuthorized(request,env)) return json({error:'Migration window expired'},404);
      const result=await env.BUCKET.put(key,body,{onlyIf:{etagDoesNotMatch:'*'},httpMetadata:metadata.httpMetadata,
        customMetadata:metadata.customMetadata,storageClass:metadata.storageClass??'Standard'});
      return result ? json({key,size,sha256:digest},201) : json({error:'Object already exists'},409);
    } catch {return json({error:'Storage unavailable; read back before retry'},503);}
  },
};
