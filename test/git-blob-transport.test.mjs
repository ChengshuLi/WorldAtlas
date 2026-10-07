import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {gitBlobTransport} from '../scripts/git-blob-transport.mjs';
const binding=bytes=>({sha:createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex'),size:bytes.length});
function fixture({corrupt=false,fail=false}={}){
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'quota-transport-test-'));let rest=0,fetches=0;
 const bytes=[Buffer.from('source evidence'),Buffer.from('implementation evidence')];const rows=bytes.map(binding);
 const transport=gitBlobTransport(async()=>{rest++;return {mutable:rest};},{repo:'a/b',token:'private-test-token',directory,execute:(cmd,args,options)=>{
  if(args.includes('fetch')){
   fetches++;
   assert.equal(options.env.GIT_TERMINAL_PROMPT,'0');assert.equal(options.env.GIT_CONFIG_VALUE_1,'');assert(!args.some(x=>x.includes('private-test-token')));
   if(fail)throw Error('sensitive private-test-token');
   for(const raw of bytes)execFileSync('git',[args[0],'hash-object','-w','--stdin'],{input:raw,env:options.env});
   return Buffer.alloc(0);
  }
  if(corrupt&&args.includes('blob'))return Buffer.from('changed');
  return execFileSync(cmd,args,options);
 }});
 return {transport,rows,bytes,get rest(){return rest;},get fetches(){return fetches;},directory,close(){transport.close();assert.equal(fs.readdirSync(directory).length,0);fs.rmdirSync(directory);}};
}
test('one exact-OID batch replaces blob REST reads while mutable authority remains fresh',async()=>{
 const f=fixture();try{
  await f.transport.api.prefetchGitBlobs('a/b',f.rows);
  for(let pass=0;pass<2;pass++)for(let i=0;i<f.rows.length;i++){
   const value=await f.transport.api('/repos/a/b/git/blobs/'+f.rows[i].sha);assert.equal(value.size,f.bytes[i].length);assert.deepEqual(Buffer.from(value.content,'base64'),f.bytes[i]);
  }
  assert.equal(f.rest,0);assert.equal(f.fetches,1);await f.transport.api('/repos/a/b/pulls/1');await f.transport.api('/repos/a/b/pulls/1');assert.equal(f.rest,2);
  await f.transport.api.prefetchGitBlobs('a/b',f.rows);assert.equal(f.fetches,1);
  const stores=fs.readdirSync(f.directory);assert.equal(stores.length,1);assert(!fs.existsSync(path.join(f.directory,stores[0],'index')));
 }finally{f.close();}
});
test('malformed inventory, wrong repository, oversized objects and conflicting sizes are rejected before fetch',async()=>{
 const f=fixture();try{
  for(const [repo,rows] of [['other/repo',f.rows],['a/b',[{sha:'bad',size:1}]],['a/b',[{sha:f.rows[0].sha,size:33*1024*1024}]],['a/b',[f.rows[0],{...f.rows[0],size:99}]]])
   await assert.rejects(f.transport.api.prefetchGitBlobs(repo,rows));
  assert.equal(f.fetches,0);
 }finally{f.close();}
});
test('truncated or corrupted object bytes never become successful evidence',async()=>{
 const f=fixture({corrupt:true});try{await assert.rejects(f.transport.api.prefetchGitBlobs('a/b',f.rows),/bytes differ/);assert.equal(f.rest,0);}finally{f.close();}
});
test('failed fetch publishes no cache entry and never exposes credentials',async()=>{
 const f=fixture({fail:true});try{await assert.rejects(f.transport.api.prefetchGitBlobs('a/b',f.rows),error=>!error.message.includes('private-test-token'));await f.transport.api('/repos/a/b/git/blobs/'+f.rows[0].sha);assert.equal(f.rest,1);}finally{f.close();}
});
test('missing object in a partial batch fails without accepting the available prefix',async()=>{
 const f=fixture();try{await assert.rejects(f.transport.api.prefetchGitBlobs('a/b',[...f.rows,{sha:'f'.repeat(40),size:1}]));await f.transport.api('/repos/a/b/git/blobs/'+f.rows[0].sha);assert.equal(f.rest,1);}finally{f.close();}
});
