// Research adapter for a trusted same-origin host. The host supplies an
// authenticated, read-only Neon release lookup and independently trusted pins.
// This module provisions no database credentials and starts no server.
import {createHash} from 'node:crypto';
const HEX=/^[0-9a-f]{64}$/;
const MAX_BYTES=2*1024*1024;
const hash=s=>createHash('sha256').update(s,'utf8').digest('hex');
function canonical(x){
 if(x===null||typeof x==='boolean'||typeof x==='string')return JSON.stringify(x);
 if(typeof x==='number'){if(!Number.isSafeInteger(x))throw Error('unsafe number');return JSON.stringify(x)}
 if(Array.isArray(x))return '['+x.map(canonical).join(',')+']';
 if(typeof x==='object'&&Object.getPrototypeOf(x)===Object.prototype){const keys=Object.keys(x).sort();if(keys.some(k=>!/^[\x20-\x7e]*$/.test(k)))throw Error('non-ASCII key');return '{'+keys.map(k=>JSON.stringify(k)+':'+canonical(x[k])).join(',')+'}'}
 throw Error('unsupported value');
}
export function createPresentationHandler({fetchRelease,expectedManifestSha256,expectedReleaseId}){
 if(typeof fetchRelease!=='function'||!HEX.test(expectedManifestSha256||'')||typeof expectedReleaseId!=='string'||!expectedReleaseId)throw Error('invalid trusted presentation configuration');
 return async function(request){
  if(request.method!=='GET')return new Response('Method not allowed',{status:405,headers:{Allow:'GET'}});
  try{
   const row=await fetchRelease(expectedReleaseId);
   if(!row||row.release_id!==expectedReleaseId||row.release_kind!=='historical_review_presentation'||row.manifest_sha256!==expectedManifestSha256||row.manifest?.release_id!==expectedReleaseId||row.manifest?.schema!=='worldatlas-presentation-parity-manifest-v2')throw Error('release mismatch');
   const manifestText=canonical(row.manifest)+'\n',recordsText=canonical(row.records)+'\n';
   if(Buffer.byteLength(manifestText)>MAX_BYTES||Buffer.byteLength(recordsText)>MAX_BYTES||hash(manifestText)!==expectedManifestSha256||!HEX.test(row.manifest.assets?.records||'')||hash(recordsText)!==row.manifest.assets.records||hash(recordsText)!==row.records_sha256)throw Error('release content mismatch');
   const body=canonical({schema:'worldatlas-presentation-transport-v1',manifest:row.manifest,records:row.records})+'\n';
   if(Buffer.byteLength(body)>MAX_BYTES)throw Error('release too large');
   return new Response(body,{status:200,headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store','x-content-type-options':'nosniff'}});
  }catch{return new Response('Presentation unavailable',{status:503,headers:{'cache-control':'no-store'}})}
 };
}
