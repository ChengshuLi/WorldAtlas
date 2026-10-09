import assert from 'node:assert/strict';import fs from 'node:fs';import path from 'node:path';import os from 'node:os';
import{gunzipSync,gzipSync}from'node:zlib';import{createHash}from'node:crypto';
import{continueReleaseRegistry,ORIGINAL_REGISTRY_SHA}from'./release-registry-continuation.mjs';
import{readGeographicReleaseManifest}from'../../../scripts/read-geographic-release-manifest.mjs';
const sha=b=>createHash('sha256').update(b).digest('hex');
const source=JSON.parse(fs.readFileSync(process.argv[2]));const oldWire=fs.readFileSync(source.registry.path);assert.equal(sha(oldWire),ORIGINAL_REGISTRY_SHA);
const oldRaw=gunzipSync(oldWire);assert.equal(sha(oldRaw),source.registry.decoded_sha256);const old=JSON.parse(oldRaw);
const header=JSON.parse(fs.readFileSync(process.argv[3]));const proof=JSON.parse(fs.readFileSync(process.argv[4]));assert.equal(proof.complete_343_whole_pairs_equal,true);assert.equal(proof.complete_gzip_inverse_authenticated,true);
const products=proof.products;const args={originalSha:ORIGINAL_REGISTRY_SHA};const next=continueReleaseRegistry(old,header,products,args);
assert.deepEqual(next.releases.slice(0,8),old.releases);assert(next.releases.slice(0,8).every((r,i)=>r===old.releases[i]));
assert.deepEqual(next.batches.slice(0,old.batches.length),old.batches);assert.equal(next.releases.at(-1),header.release);
assert.equal(next.new_entities,old.new_entities);assert.equal(next.total_memberships,old.total_memberships+84833);assert.equal(next.changes,old.changes+2);
for(const [key,value] of Object.entries(old))if(!['releases','batches','sources_batches','total_memberships','changes'].includes(key))assert.deepEqual(next[key],value);
let negative=0;const reject=(o,h,p,a=args)=>{assert.throws(()=>continueReleaseRegistry(o,h,p,a));negative++;};
reject(old,header,products,{originalSha:'0'.repeat(64)});reject({...old,releases:old.releases.slice(0,-1)},header,products);
reject(old,{...header,activated:true},products);reject(old,{...header,membership_count:84832},products);
reject(old,{...header,release:{...header.release,source_id:'foreign'}},products);
reject(old,{...header,release:{...header.release,membership_sha256:'0'.repeat(64)}},products);
reject(old,{...header,release:{...header.release,expected_counts:{...header.release.expected_counts,location:1}}},products);
reject(old,header,products.slice(1));reject(old,header,[...products.slice(1),products[1]]);
reject(old,header,products.map((p,i)=>i? p:{...p,relative:'../foreign'}));
reject(old,header,products.map((p,i)=>i?p:{...p,sha256:'foreign'}));reject(old,header,products.map((p,i)=>i?p:{...p,mode:'100755'}));
// Real unchanged reader against a fresh empty directory. Encoding here is a
// control carrier, not the final serializer's encoded publication body.
const dir=fs.mkdtempSync(path.join(os.tmpdir(),'atlas1520-release-registry-control-'));
try{
 const baseline=Buffer.from(JSON.stringify(old));fs.writeFileSync(path.join(dir,'index.json'),baseline);
 const compressed=gzipSync(Buffer.from(JSON.stringify(next)));fs.writeFileSync(path.join(dir,'releases-v9.json.gz'),compressed);
 fs.writeFileSync(path.join(dir,'current-manifest.json'),JSON.stringify({path:'releases-v9.json.gz',sha256:sha(compressed),predecessor_index_sha256:sha(baseline)}));
 assert.deepEqual(readGeographicReleaseManifest(dir),next);
 fs.writeFileSync(path.join(dir,'current-manifest.json'),JSON.stringify({path:'releases-v9.json.gz',sha256:'0'.repeat(64),predecessor_index_sha256:sha(baseline)}));assert.throws(()=>readGeographicReleaseManifest(dir));negative++;
}finally{fs.rmSync(dir,{recursive:true});}
console.log(JSON.stringify({positive:2,negative,actual_complete_old_registry_and343_qualified_products:true,old8_releases_all3042_descriptors_preserved:true,actual_stock_reader:true,limit:'Control carrier gzip only; final immutable registry serialization, original baseline index pointer and full current caller remain unqualified.'}));
