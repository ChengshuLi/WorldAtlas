import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createPresentationHandler} from './presentation-service.mjs';
const canon=x=>x===null||typeof x!=='object'?JSON.stringify(x):Array.isArray(x)?'['+x.map(canon).join(',')+']':'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canon(x[k])).join(',')+'}';
const hash=s=>createHash('sha256').update(s).digest('hex');
const records={groups:[],leaves:[],schema:'fictional',source:{id:'fictional'}};
const rh=hash(canon(records)+'\n');
const manifest={schema:'worldatlas-presentation-parity-manifest-v2',release_id:'fictional',assets:{records:rh}};
const mh=hash(canon(manifest)+'\n');
let row={release_id:'fictional',release_kind:'historical_review_presentation',manifest_sha256:mh,records_sha256:rh,manifest,records};
const handler=createPresentationHandler({fetchRelease:async id=>id==='fictional'?row:null,expectedManifestSha256:mh,expectedReleaseId:'fictional'});
const request=new Request('http://localhost/presentation');
let response=await handler(request);assert.equal(response.status,200);assert.equal(response.headers.get('cache-control'),'no-store');assert.deepEqual(JSON.parse(await response.text()).records,records);
assert.equal((await handler(new Request('http://localhost/presentation',{method:'POST'}))).status,405);
for(const change of [r=>r.release_id='other',r=>r.manifest.release_id='other',r=>r.records.groups.push({id:'changed'}),r=>r.manifest_sha256='0'.repeat(64),r=>r.records_sha256='0'.repeat(64)]){row=structuredClone({release_id:'fictional',release_kind:'historical_review_presentation',manifest_sha256:mh,records_sha256:rh,manifest,records});change(row);assert.equal((await handler(request)).status,503)}
row=null;assert.equal((await handler(request)).status,503);
assert.throws(()=>createPresentationHandler({fetchRelease:async()=>null,expectedManifestSha256:'bad',expectedReleaseId:'fictional'}));
console.log('presentation service synthetic tests passed');
