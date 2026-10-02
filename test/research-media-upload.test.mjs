import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {DatabaseSync} from 'node:sqlite';
import {execFileSync} from 'node:child_process';
import worker from '../hosted/worker.js';
import {importBatch,mediaById} from '../hosted/records.js';
import {uploadResearchMedia,readResearchMedia,mediaUploadLimit} from '../scripts/upload-research-media.mjs';
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const token='private-test-credential-never-persisted';
const origin='https://atlas.test';
const source={id:'test-source',name:'Disposable test source',url:'https://example.test/source',license:'Test fixture license',vintage:'2026 test fixture',status:'historical'};
class D1{
 constructor(){this.sqlite=new DatabaseSync(':memory:');this.sqlite.exec('PRAGMA foreign_keys=ON');for(const name of fs.readdirSync(new URL('../drizzle/',import.meta.url)).filter(name=>name.endsWith('.sql')).sort())this.sqlite.exec(fs.readFileSync(new URL('../drizzle/'+name,import.meta.url),'utf8'));}
 prepare(sql){const sqlite=this.sqlite;let args=[];return {bind(...values){args=values;return this;},async all(){return {results:sqlite.prepare(sql).all(...args)};},async first(){return sqlite.prepare(sql).get(...args)??null;},run(){return {meta:{changes:Number(sqlite.prepare(sql).run(...args).changes)}};}};}
 async batch(statements){this.sqlite.exec('BEGIN IMMEDIATE');try{const result=statements.map(statement=>statement.run());this.sqlite.exec('COMMIT');return result;}catch(error){this.sqlite.exec('ROLLBACK');throw error;}}
}
async function fixture(t,{objects=1}={}){
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-media-')),db=new D1();t.after(()=>{db.sqlite.close();fs.rmSync(directory,{recursive:true,force:true});});
 await importBatch(db,{sources:[{...source,supported_from:1000,supported_to:1100}]});
 const blobs=new Map(),puts=[];const env={DB:db,BUCKET:{async head(key){return blobs.has(key)?{size:blobs.get(key).length}:null;},async put(key,bytes){assert.equal(blobs.has(key),false,'Existing original blob must not be overwritten');puts.push(key);blobs.set(key,Buffer.from(bytes));},async get(key){const bytes=blobs.get(key);return bytes?{body:new Uint8Array(bytes),size:bytes.length,httpEtag:'"fixture"'}:null;}}};
 const manifest={version:1,kind:'research-media',campaign_id:'media-fixture',sources:[source],objects:[]};
 for(let index=0;index<objects;index++){const bytes=Buffer.from(`Disposable media fixture ${index}\n`),file=`media-${index}.txt`;fs.writeFileSync(path.join(directory,file),bytes);manifest.objects.push({id:`fixture-media:${index}`,path:file,sha256:hash(bytes),bytes:bytes.length,mime:'text/plain',name:`Disposable media ${index}`,license:'Test fixture license',attribution:'Disposable test author',source_id:source.id,redistribution_permitted:true,provenance:{source_url:'https://example.test/source/media',retrieved_at:'2026-10-02',reference:'Disposable fixture; not historical evidence'}});}
 const manifestFile=path.join(directory,'media.json'),save=()=>fs.writeFileSync(manifestFile,JSON.stringify(manifest));save();const calls=[];
 const request=async(url,init={})=>{calls.push({url,method:init.method??'GET',headers:init.headers,redirect:init.redirect});assert.equal(new URL(url).origin,origin);assert.equal(init.redirect,'manual');return worker.fetch(new Request(url,init),env,{});};
 return {directory,manifest,manifestFile,save,db,env,blobs,puts,calls,request,receiptFile:path.join(directory,'media-upload-receipts.json'),options:{manifestFile,origin,token,request,wait:async()=>{}}};
}

test('media campaign dry run validates original bytes and rights without network or receipts',async t=>{
 const f=await fixture(t);const preview=await uploadResearchMedia({...f.options,dryRun:true,request:()=>assert.fail('Dry run requested network')});assert.equal(preview.network_requests,0);assert.equal(preview.objects,1);assert.equal(preview.bytes,f.manifest.objects[0].bytes);assert.equal(fs.existsSync(f.receiptFile),false);
 const cli=JSON.parse(execFileSync(process.execPath,['scripts/upload-research-media.mjs',origin,f.manifestFile,'--dry-run'],{cwd:new URL('..',import.meta.url)}));assert.deepEqual(cli,preview);
 for(const update of [row=>{row.license='';},row=>{row.redistribution_permitted=false;},row=>{row.provenance.retrieved_at='2026-02-31';},row=>{row.bytes=mediaUploadLimit+1;},row=>{row.path='../outside.txt';},row=>{row.provenance.source_url='https://user:password@example.test/';},row=>{row.unrecognized_claim='must not silently drop';}]){
  const original=structuredClone(f.manifest.objects[0]);update(f.manifest.objects[0]);f.save();assert.throws(()=>readResearchMedia(f.manifestFile));f.manifest.objects[0]=original;
 }f.save();fs.appendFileSync(path.join(f.directory,f.manifest.objects[0].path),'changed');assert.throws(()=>readResearchMedia(f.manifestFile),/original-bytes-changed/);assert.equal(f.calls.length,0);
});

test('actual Worker and registerMedia roundtrip retains provenance, immutable R2 bytes and resumable receipt hashes',async t=>{
 const f=await fixture(t,{objects:2}),result=await uploadResearchMedia(f.options);assert.equal(result.complete,true);assert.equal(result.verified_objects,2);assert.equal(f.puts.length,2);
 const row=await mediaById(f.db,'fixture-media:0');assert.equal(row.source_id,source.id);assert.deepEqual(row.metadata,f.manifest.objects[0].provenance);assert.deepEqual(f.blobs.get(row.object_key),fs.readFileSync(path.join(f.directory,'media-0.txt')));
 const receiptBytes=fs.readFileSync(f.receiptFile),receipt=JSON.parse(receiptBytes);assert.equal(receipt.complete,true);assert.equal(receipt.objects[0].verification,'metadata-and-full-bytes');assert.match(receipt.objects[0].receipt_sha256,/^[a-f0-9]{64}$/);assert.doesNotMatch(receiptBytes.toString(),new RegExp(token));assert.equal(fs.readdirSync(f.directory).some(file=>file.includes('.tmp-')),false);
 const posts=f.calls.filter(call=>call.method==='POST').length;await uploadResearchMedia(f.options);assert.equal(f.calls.filter(call=>call.method==='POST').length,posts);assert.equal(f.puts.length,2);assert.deepEqual(fs.readFileSync(f.receiptFile),receiptBytes,'Identical resume retains original successful evidence receipts');
 const before=f.db.sqlite.prepare('SELECT * FROM atlas_media ORDER BY id').all();f.manifest.objects[0].attribution='Changed author';f.save();await assert.rejects(uploadResearchMedia(f.options),/receipt-campaign-mismatch/);assert.deepEqual(f.db.sqlite.prepare('SELECT * FROM atlas_media ORDER BY id').all(),before);
});

test('lost upload response rereads committed identity and full bytes without a second POST',async t=>{
 const f=await fixture(t);let posts=0;const request=async(url,init={})=>{const response=await f.request(url,init);if(init.method==='POST'){posts++;throw Error(`Lost network response with ${token}`);}return response;};
 const result=await uploadResearchMedia({...f.options,request});assert.equal(result.complete,true);assert.equal(posts,1);assert.equal(f.puts.length,1);assert.equal(f.db.sqlite.prepare('SELECT count(*) n FROM atlas_media').get().n,1);assert.doesNotMatch(fs.readFileSync(f.receiptFile,'utf8'),new RegExp(token));
});

test('failed campaign preserves verified objects and safely resumes only missing identities',async t=>{
 const f=await fixture(t,{objects:2});let failSecond=true;const request=async(url,init={})=>{if(init.method==='POST'&&new URL(url).searchParams.get('id')==='fixture-media:1'&&failSecond)return Response.json({error:token},{status:503});return f.request(url,init);};
 await assert.rejects(uploadResearchMedia({...f.options,request}),/upload-outcome-unconfirmed/);let receipt=JSON.parse(fs.readFileSync(f.receiptFile));assert.equal(receipt.complete,false);assert.equal(receipt.objects.length,1);assert.equal(f.puts.length,1);assert.doesNotMatch(JSON.stringify(receipt),new RegExp(token));
 failSecond=false;await uploadResearchMedia({...f.options,request});receipt=JSON.parse(fs.readFileSync(f.receiptFile));assert.equal(receipt.complete,true);assert.equal(receipt.objects.length,2);assert.equal(f.puts.length,2);assert.equal(f.calls.filter(call=>call.method==='POST'&&new URL(call.url).searchParams.get('id')==='fixture-media:0').length,1);
});

test('source mismatches, changed claims and changed local or remote bytes stop before replacing originals',async t=>{
 const f=await fixture(t);f.manifest.sources[0]={...source,license:'Different license'};f.save();await assert.rejects(uploadResearchMedia(f.options),/source-identity-mismatch/);assert.equal(f.puts.length,0);fs.rmSync(f.receiptFile);
 f.manifest.sources[0]=source;f.save();await uploadResearchMedia(f.options);const original=await mediaById(f.db,'fixture-media:0');
 fs.rmSync(f.receiptFile);f.manifest.objects[0].provenance.reference='Changed immutable provenance';f.save();await assert.rejects(uploadResearchMedia(f.options),/remote-immutable-metadata-mismatch/);assert.equal(f.puts.length,1);assert.deepEqual(await mediaById(f.db,'fixture-media:0'),original);
 f.manifest.objects[0].provenance.reference='Disposable fixture; not historical evidence';f.save();fs.rmSync(f.receiptFile);f.blobs.set(original.object_key,Buffer.from('corrupt'));await assert.rejects(uploadResearchMedia(f.options),/readback-digest-mismatch/);assert.equal(f.puts.length,1);
});

test('tampered checkpoints, duplicate content identities and missing source dependencies are rejected',async t=>{
 const f=await fixture(t);await uploadResearchMedia(f.options);const receipt=JSON.parse(fs.readFileSync(f.receiptFile));receipt.objects[0].source_id='wrong-source';fs.writeFileSync(f.receiptFile,JSON.stringify(receipt));const before=f.calls.length;await assert.rejects(uploadResearchMedia(f.options),/receipt-proof-invalid/);assert.equal(f.calls.length,before);
 fs.rmSync(f.receiptFile);f.manifest.objects.push({...structuredClone(f.manifest.objects[0]),id:'different-id-same-content'});f.save();assert.throws(()=>readResearchMedia(f.manifestFile),/repeated-identity/);f.manifest.objects.pop();
 f.manifest.sources[0]={...source,id:'unimported-source'};f.manifest.objects[0].source_id='unimported-source';f.save();await assert.rejects(uploadResearchMedia(f.options),/source-dependency-missing/);assert.equal(f.puts.length,1);
});

test('redirects never forward the private credential and untrusted API errors are not persisted',async t=>{
 const f=await fixture(t);let external=0;const request=async(url,init={})=>{if(new URL(url).origin!==origin)external++;if(init.method==='POST')return Response.redirect('https://external.test/credential-collector',307);return f.request(url,init);};
 await assert.rejects(uploadResearchMedia({...f.options,request}),/redirect-refused/);assert.equal(external,0);assert.equal(f.puts.length,0);assert.doesNotMatch(fs.readFileSync(f.receiptFile,'utf8'),new RegExp(token));
 fs.rmSync(f.receiptFile);f.manifest.objects[0].provenance.reference=token;f.save();await assert.rejects(uploadResearchMedia(f.options),/credential-in-input/);assert.equal(fs.existsSync(f.receiptFile),false);
 fs.writeFileSync(f.manifestFile,JSON.stringify(f.manifest).replaceAll('p','\\u0070'));assert.equal(fs.readFileSync(f.manifestFile,'utf8').includes(token),false);await assert.rejects(uploadResearchMedia(f.options),/credential-in-input/);assert.equal(fs.existsSync(f.receiptFile),false);
});

test('encoded URL bounds and escaped local paths are enforced before any upload',async t=>{
 const f=await fixture(t);for(const field of ['name','license','attribution'])f.manifest.objects[0][field]='漢'.repeat(500);f.manifest.objects[0].provenance.reference='漢'.repeat(1000);f.save();await assert.rejects(uploadResearchMedia({...f.options,dryRun:true}),/url-over-16-kib/);assert.equal(f.calls.length,0);
 const outside=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-outside-'));t.after(()=>fs.rmSync(outside,{recursive:true,force:true}));fs.copyFileSync(path.join(f.directory,'media-0.txt'),path.join(outside,'outside.txt'));fs.symlinkSync(path.join(outside,'outside.txt'),path.join(f.directory,'linked.txt'));f.manifest.objects[0].path='linked.txt';f.save();assert.throws(()=>readResearchMedia(f.manifestFile),/size-or-path-invalid/);
});

test('a truncated successful POST receipt is resolved by direct immutable metadata reread',async t=>{
 const f=await fixture(t);let posts=0;const request=async(url,init={})=>{const response=await f.request(url,init);if(init.method==='POST'){posts++;return new Response('{"truncated"',{headers:{'Content-Type':'application/json'}});}return response;};await uploadResearchMedia({...f.options,request});assert.equal(posts,1);assert.equal(f.puts.length,1);assert.equal(JSON.parse(fs.readFileSync(f.receiptFile)).complete,true);
});

test('optional registered source archives are checked by stable ID and digest before linking provenance',async t=>{
 const f=await fixture(t);await uploadResearchMedia(f.options);const original=f.manifest.objects[0],bytes=Buffer.from('Second disposable media object');fs.writeFileSync(path.join(f.directory,'second.txt'),bytes);fs.rmSync(f.receiptFile);
 f.manifest.campaign_id='second-campaign';f.manifest.objects=[{...structuredClone(original),id:'second',path:'second.txt',bytes:bytes.length,sha256:hash(bytes),provenance:{...original.provenance,source_archive:{url:source.url,sha256:original.sha256,media_id:original.id}}}];f.save();await uploadResearchMedia(f.options);assert.equal(f.puts.length,2);assert.equal((await mediaById(f.db,'second')).metadata.source_archive.media_id,original.id);
 fs.rmSync(f.receiptFile);f.manifest.objects[0].provenance.source_archive.sha256='a'.repeat(64);f.save();await assert.rejects(uploadResearchMedia(f.options),/source-archive-identity-mismatch/);assert.equal(f.puts.length,2);
});

test('older services without provenance capability stop before creating immutable incomplete metadata',async t=>{
 const f=await fixture(t);const request=async(url,init={})=>{if(new URL(url).searchParams.get('metadata')==='1')return Response.json({error:'Media not found'},{status:404});return f.request(url,init);};await assert.rejects(uploadResearchMedia({...f.options,request}),/provenance-api-not-supported/);assert.equal(f.puts.length,0);assert.equal(f.calls.some(call=>call.method==='POST'),false);
});
