import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {verifyRetainedObjectRecovery} from '../scripts/verify-retained-object-recovery.mjs';
import {storageExportV2Collections,storageExportV2Contract,v2MarkerIdentity} from '../hosted/storage-export-v2-contract.js';
const sha=x=>createHash('sha256').update(x).digest('hex');
function fixture(t,change={}){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-object-recovery-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 const bytes=Buffer.from('original compressed archive bytes\0\xff'),row={id:'media:original',object_key:'immutable/'+sha(bytes),sha256:sha(bytes),bytes:bytes.length,source_id:'source:retained',status:'archived'};
 const m={version:2,backend:'postgres',revision:3,read_only:false,counts:Object.fromEntries(storageExportV2Collections.map(k=>[k,k==='media'?1:0])),geographic_releases_sha256:sha('release'),footprint_versions_sha256:sha('footprints'),catalog_sha256:storageExportV2Contract.postgres_catalog_sha256,contract:storageExportV2Contract};
 m.fingerprint=sha(JSON.stringify(v2MarkerIdentity(m)));let markerReads=0;
 const json=x=>new Response(JSON.stringify(x),{headers:{'content-type':'application/json'}});
 const fetcher=async(url,options)=>{
  assert.equal(options.method,'GET');assert.equal(options.redirect,'error');assert.equal(options.headers['OAI-Sites-Authorization'],'Bearer fixture-private-input');assert.equal(new URL(url).origin,'https://confirmed.example');
  const route=new URL(url).pathname;
  if(route.endsWith('export-marker')){markerReads++;return json(change.marker?.(structuredClone(m),markerReads)??m);}
  if(route.endsWith('export/media'))return json(change.page?.({collection:'media',records:[row],snapshot_marker:m,next_cursor:null})??{collection:'media',records:[row],snapshot_marker:m,next_cursor:null});
  assert.equal(route,'/api/media/media%3Aoriginal');return change.object?.(bytes,options)??new Response(bytes);
 };
 return {root,bytes,row,m,options:{origin:'https://confirmed.example/',token:'fixture-private-input',directory:path.join(root,'isolated'),fetcher},markerReads:()=>markerReads};
}
test('full original hash, copied bytes, local readback and unchanged source marker; no maintenance or range claims',async t=>{
 const f=fixture(t),r=await verifyRetainedObjectRecovery(f.options);assert.equal(r.status,'verified');assert.equal(r.registered_objects,1);assert.equal(r.recovered_bytes,f.bytes.length);assert.equal(f.markerReads(),2);
 assert.deepEqual(fs.readFileSync(path.join(f.options.directory,r.objects[0].path)),f.bytes);assert.equal(r.objects[0].full_sha256_verified,true);assert.equal(r.objects[0].local_readback_verified,true);
 assert.ok(!fs.readFileSync(path.join(f.options.directory,'receipt.json'),'utf8').includes('fixture-private-input'));assert.equal(r.before_marker.read_only,false);
});
for(const [name,change]of [
 ['corrupted full bytes',{object:b=>new Response(Buffer.alloc(b.length))}],
 ['truncated body',{object:b=>new Response(b.subarray(1))}],
 ['oversized body',{object:b=>new Response(Buffer.concat([b,Buffer.from('x')]))}],
 ['range response',{object:b=>new Response(b,{status:206,headers:{'content-range':'bytes 0-1/32'}})}],
 ['misleading full content-range',{object:b=>new Response(b,{headers:{'content-range':'bytes 0-1/32'}})}],
 ['wrong content-length',{object:b=>new Response(b,{headers:{'content-length':'1'}})}],
 ['duplicate media identity',{page:p=>({...p,records:[p.records[0],p.records[0]]})}],
 ['negative byte count',{page:p=>({...p,records:[{...p.records[0],bytes:-1}]})}],
 ['unknown extra factual table',{marker:m=>({...m,counts:{...m.counts,hidden:1}})}],
 ['incomplete V2 legacy projection',{marker:m=>({...m,legacy_projection:{complete:false}})}],
 ['uncovered footprint object references',{marker:m=>{m.counts.footprint_version_objects=1;m.fingerprint=sha(JSON.stringify(v2MarkerIdentity(m)));return m;}}],
 ['changed final source',{marker:(m,n)=>{if(n>1){m.revision++;m.fingerprint=sha(JSON.stringify(v2MarkerIdentity(m)));}return m;}}],
 ['unsafe credential-bearing origin',{}]
])test('reject '+name+' with preserved sanitized partial receipt',async t=>{
 const f=fixture(t,change);if(name==='unsafe credential-bearing origin')f.options.origin='https://user:password@confirmed.example/';
 await assert.rejects(verifyRetainedObjectRecovery(f.options));if(fs.existsSync(f.options.directory)){const raw=fs.readFileSync(path.join(f.options.directory,'receipt.json'),'utf8');assert.equal(JSON.parse(raw).status,'failed');assert.ok(!raw.includes(f.options.token));}
});
test('refuse existing target and preserve original artifact',async t=>{const f=fixture(t);fs.mkdirSync(f.options.directory);fs.writeFileSync(path.join(f.options.directory,'original'),'retained');await assert.rejects(verifyRetainedObjectRecovery(f.options),/Preserve existing/);assert.equal(fs.readFileSync(path.join(f.options.directory,'original'),'utf8'),'retained');});
test('deadline covers stalled response body and retains partial bytes',async t=>{const f=fixture(t,{object:()=>new Response(new ReadableStream({pull:()=>new Promise(()=>{})}))});f.options.requestTimeoutMs=25;const start=performance.now();await assert.rejects(verifyRetainedObjectRecovery(f.options));assert.ok(performance.now()-start<1000);assert.equal(JSON.parse(fs.readFileSync(path.join(f.options.directory,'receipt.json'))).phase,'full-object-copy');});
test('late fetch cannot create object files after deadline rejection',async t=>{const f=fixture(t);f.options.requestTimeoutMs=20;const original=f.options.fetcher;f.options.fetcher=async(u,o)=>{if(u.includes('/api/media/'))await new Promise(r=>setTimeout(r,60));return original(u,o);};await assert.rejects(verifyRetainedObjectRecovery(f.options));await new Promise(r=>setTimeout(r,80));assert.deepEqual(fs.readdirSync(path.join(f.options.directory,'objects')),[]);});
test('abort propagates and does not disclose credential',async t=>{const f=fixture(t);const c=new AbortController();c.abort();f.options.signal=c.signal;await assert.rejects(verifyRetainedObjectRecovery(f.options));assert.ok(!JSON.stringify(JSON.parse(fs.readFileSync(path.join(f.options.directory,'receipt.json')))).includes(f.options.token));});
