import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readOnlyR2Export} from '../hosted/site-r2-export.js';
const token='fixture-only-strong-random-token-32-characters';
function fixture(){const calls=[];const inner={fetch:()=>new Response('original')};const bucket={
 list:async options=>{calls.push(['list',options]);return {objects:[{key:'unregistered/α.txt',size:3,customMetadata:{provenance:'original'},httpMetadata:{contentType:'text/plain'},checksums:{toJSON:()=>({md5:'fixture'})}}],truncated:true,cursor:'opaque-next'};},
 get:async key=>{calls.push(['get',key]);return {size:3,body:'abc',httpEtag:'"original"'};},
 put:()=>{throw Error('Write forbidden');},delete:()=>{throw Error('Delete forbidden');}};
 return {calls,worker:readOnlyR2Export(inner),env:{BUCKET:bucket,ATLAS_R2_EXPORT_TOKEN:token,ATLAS_R2_EXPORT_EXPIRES_AT:new Date(Date.now()+60000).toISOString()}};}
const request=(path,method='GET',credential=token)=>new Request('https://fixture.test'+path,{method,headers:{Authorization:'Bearer '+credential}});
test('real wrapper rejects missing/wrong/expired auth before any storage call',async()=>{const f=fixture();for(const env of [{...f.env,ATLAS_R2_EXPORT_TOKEN:undefined},{...f.env,ATLAS_R2_EXPORT_EXPIRES_AT:'bad'},{...f.env,ATLAS_R2_EXPORT_EXPIRES_AT:'2020-01-01'}])assert.equal((await f.worker.fetch(request('/api/_migration/r2/inventory'),env)).status,404);assert.equal((await f.worker.fetch(request('/api/_migration/r2/inventory','GET','wrong'),f.env)).status,404);assert.deepEqual(f.calls,[]);});
test('complete enumeration includes unregistered keys and original metadata and cursor',async()=>{const f=fixture();const result=await (await f.worker.fetch(request('/api/_migration/r2/inventory?cursor=opaque-first'),f.env)).json();assert.equal(result.objects[0].key,'unregistered/α.txt');assert.deepEqual(result.objects[0].customMetadata,{provenance:'original'});assert.equal(result.cursor,'opaque-next');assert.equal(f.calls[0][1].cursor,'opaque-first');});
test('opaque key read returns exact bytes and every write method is rejected',async()=>{const f=fixture();for(const method of ['POST','PUT','PATCH','DELETE'])assert.equal((await f.worker.fetch(request('/api/_migration/r2/object?key=x',method),f.env)).status,405);const response=await f.worker.fetch(request('/api/_migration/r2/object?key='+encodeURIComponent('x/../α'), 'GET'),f.env);assert.equal(await response.text(),'abc');assert.deepEqual(f.calls,[['get','x/../α']]);assert.equal(response.headers.get('cache-control'),'no-store');assert.equal(await (await f.worker.fetch(request('/ordinary'),f.env)).text(),'original');});
test('conditional read, missing body, provider failure and adjacent prefix preserve safe behavior',async()=>{
 const f=fixture();let options;f.env.BUCKET.get=async(key,value)=>{options=value;return {size:3,httpEtag:'"new"'};};
 const req=request('/api/_migration/r2/object?key=x');req.headers.set('If-Match','"original"');
 assert.equal((await f.worker.fetch(req,f.env)).status,412);assert.deepEqual(options,{onlyIf:{etagMatches:'original'}});
 f.env.BUCKET.get=async()=>{throw Error('secret-provider-diagnostic');};const failed=await f.worker.fetch(req,f.env);
 assert.equal(failed.status,503);assert.equal((await failed.text()).includes('secret-provider'),false);
 assert.equal(await (await f.worker.fetch(request('/api/_migration/r2-other'),f.env)).text(),'original');
 for(const path of ['/api/_migration/r2/object?key='+encodeURIComponent('α'.repeat(513)),'/api/_migration/r2/inventory?cursor='+'x'.repeat(4097)])assert.equal((await f.worker.fetch(request(path),f.env)).status,400);
});
