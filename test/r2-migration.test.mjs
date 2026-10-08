import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {inventory,reconcile,readObject} from '../scripts/r2-reconcile.mjs';
import {run} from '../scripts/migrate-site-r2.mjs';
import destinationWorker from '../hosted/r2-migration-destination.js';
import {readOnlyR2Export} from '../hosted/site-r2-export.js';
const token='fixture-only-strong-random-token-32-characters';
const digest=body=>createHash('sha256').update(body).digest('hex');
const row=(key,body)=>({key,size:Buffer.byteLength(body),etag:digest(body),httpEtag:'"'+digest(body)+'"',httpMetadata:{contentType:'application/octet-stream'},customMetadata:{source:'fixture'},storageClass:'Standard'});
function bucket(entries){const stored=new Map(entries.map(([key,body])=>[key,{...row(key,body),body}]));const calls=[];
 return {stored,calls,list:async()=>({objects:[...stored.values()].map(({body,...value})=>value),truncated:false}),
 get:async(key,options)=>{calls.push(['get',key]);const value=stored.get(key);if(!value)return null;if(options?.onlyIf?.etagMatches!==undefined&&options.onlyIf.etagMatches!==value.etag)return {...value,body:undefined};return {...value,body:new Response(value.body).body};},
 put:async(key,body,options)=>{calls.push(['put',key,options]);assert.deepEqual(options.onlyIf,{etagDoesNotMatch:'*'});if(stored.has(key))return null;stored.set(key,{...row(key,body),body,...options});return stored.get(key);},
 delete:()=>{throw Error('Forbidden deletion');}};
}
const env=BUCKET=>({BUCKET,ATLAS_R2_EXPORT_TOKEN:token,ATLAS_R2_EXPORT_EXPIRES_AT:new Date(Date.now()+60000).toISOString()});
function fixtures(){const old=bucket([['unregistered/α.bin',Buffer.from([0,255,7])],['existing.txt','old']]),current=bucket([['existing.txt','old']]);
 const originalWorker=readOnlyR2Export({fetch:()=>new Response('original')});
 const transport=async(url,options)=>{const req=new Request(url,options);return new URL(url).hostname==='source.test'?originalWorker.fetch(req,env(old)):destinationWorker.fetch(req,env(current));};
 return {old,current,transport,source:{url:'https://source.test',token},destination:{url:'https://destination.test',token}};}
test('actual HTTP wrappers and CLI run preserve binary unregistered originals, existing objects and metadata twice',async()=>{
 const scratch=await fs.mkdtemp(path.join(await fs.realpath(os.tmpdir()),'worldatlas-r2-fixture-'));
 try{let prior;for(const name of ['one','two']){const f=fixtures();const result=await run({source:f.source,destination:f.destination,copy:true,output:path.join(scratch,name)},f.transport);
 assert.equal(result.verified_objects,2);assert.equal(result.remaining_objects,0);assert.equal(result.metadata_discrepancies,0);
 const proof=JSON.parse(await fs.readFile(path.join(result.output,'reconciliation.json'),'utf8'));assert.equal(proof.database_access,false);
 assert.equal(f.current.calls.filter(call=>call[0]==='put').length,1);assert.equal(f.old.calls.filter(call=>call[0]==='put').length,0);
 const normalized=JSON.stringify(proof);if(prior)assert.equal(normalized,prior);prior=normalized;}
 }finally{await fs.rm(scratch,{recursive:true});}
});
test('actual CLI refuses conflicting existing bytes before any put and retains failure',async()=>{
 const scratch=await fs.mkdtemp(path.join(await fs.realpath(os.tmpdir()),'worldatlas-r2-fixture-'));try{const f=fixtures();f.current.stored.set('existing.txt',{...row('existing.txt','bad'),body:'bad'});
 await assert.rejects(run({source:f.source,destination:f.destination,copy:true,output:path.join(scratch,'collision')},f.transport),/Conflicting destination bytes/);
 assert.equal(f.current.calls.filter(call=>call[0]==='put').length,0);assert.equal(JSON.parse(await fs.readFile(path.join(scratch,'collision/failure.json'),'utf8')).status,'failed');
 await assert.rejects(run({source:f.source,destination:f.destination,copy:true,output:path.join(scratch,'collision')},f.transport),/EEXIST/);
 }finally{await fs.rm(scratch,{recursive:true});}
});
test('pagination rejects duplicate actual keys, repeated cursors, excessive sizes and incomplete bodies',async()=>{
 const item=row('x','abc');let n=0;
 assert.equal((await inventory(async()=>++n===1?{objects:[item],truncated:true,cursor:'next'}:{objects:[row('y','abc')],truncated:false,cursor:null})).objects.length,2);
 await assert.rejects(inventory(async()=>({objects:[item],truncated:true,cursor:'next'})),/duplicate/);
 await assert.rejects(inventory(async()=>({objects:[],truncated:true,cursor:'next'})),/repeated/);
 await assert.rejects(inventory(async()=>({objects:[{...item,size:33*1024**2}],truncated:false})),/bounds/);
 await assert.rejects(readObject(new Response('ab'),item),/incomplete/);
 await assert.rejects(readObject(new Response('abcd'),item),/exceeds/);
});
test('source drift and conditional destination collision stop the actual transfer boundary',async()=>{
 const sourceRows=[row('x','abc')];let lists=0,puts=0;
 const source={list:async()=>({objects:++lists===2?[row('x','changed')]:sourceRows,truncated:false}),get:async()=>new Response('abc')};
 const destination={list:async()=>({objects:[],truncated:false}),get:async()=>null,createOnly:async()=>puts++};
 await assert.rejects(reconcile({source,destination,copy:true}),/changed/);assert.equal(puts,0);
 const b=bucket([['x','old']]);const request=new Request('https://target.test/api/_migration/r2/object?key=x',{method:'PUT',body:'new',headers:{Authorization:'Bearer '+token,'Content-Length':'3','X-Migration-Sha256':digest('new'),'X-Migration-Metadata':encodeURIComponent(JSON.stringify(row('x','new')))}});
 assert.equal((await destinationWorker.fetch(request,env(b))).status,409);assert.equal(b.stored.get('x').body,'old');
});
test('destination auth, declared length and actual digest controls run before put',async()=>{
 for(const alteration of [{Authorization:'Bearer wrong'},{'X-Migration-Sha256':digest('bad')},{'Content-Length':'2'}]){
 const b=bucket([]);const request=new Request('https://target.test/api/_migration/r2/object?key=x',{method:'PUT',body:'abc',headers:{Authorization:'Bearer '+token,'Content-Length':'3','X-Migration-Sha256':digest('abc'),'X-Migration-Metadata':encodeURIComponent(JSON.stringify(row('x','abc'))),...alteration}});
 assert.ok([404,400,413].includes((await destinationWorker.fetch(request,env(b))).status));assert.equal(b.calls.length,0);
 }
});
test('metadata collisions are rejected while additional destination cache policy is preserved',async()=>{
 const scratch=await fs.mkdtemp(path.join(await fs.realpath(os.tmpdir()),'worldatlas-r2-fixture-'));
 try {const f=fixtures();f.current.stored.get('existing.txt').httpMetadata.contentType='text/html';
 await assert.rejects(run({source:f.source,destination:f.destination,copy:true,output:path.join(scratch,'bad-metadata')},f.transport),/Conflicting destination metadata/);
 assert.equal(f.current.calls.filter(call=>call[0]==='put').length,0);
 const good=fixtures();good.current.stored.get('existing.txt').httpMetadata.cacheControl='immutable';
 const result=await run({source:good.source,destination:good.destination,copy:true,output:path.join(scratch,'extra-metadata')},good.transport);
 assert.equal(result.metadata_discrepancies,1);assert.equal(good.current.stored.get('existing.txt').httpMetadata.cacheControl,'immutable');
 }finally{await fs.rm(scratch,{recursive:true});}
});
