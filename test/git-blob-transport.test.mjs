import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {gitBlobTransport} from '../scripts/git-blob-transport.mjs';
const binding=bytes=>({sha:createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex'),size:bytes.length});
function fixture({corrupt=false,fail=false,incomplete=false,count=2}={}){
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'quota-transport-test-'));let rest=0,fetches=0,bodyReads=0;
 const bytes=Array.from({length:count},(_,i)=>Buffer.from('source evidence '+i));const rows=bytes.map(binding);
 const transport=gitBlobTransport(async()=>{rest++;return {mutable:rest};},{repo:'a/b',token:'private-test-token',directory,execute:(cmd,args,options)=>{
  if(args.includes('fetch')){
   fetches++;
   assert(args.includes('--stdin'));assert.equal(options.input,rows.filter(row=>options.input.includes(row.sha)).map(row=>row.sha).join('\n')+'\n');assert(!args.some(arg=>/^[a-f0-9]{40}$/.test(arg)));
   assert.equal(options.env.GIT_TERMINAL_PROMPT,'0');assert.equal(options.env.GIT_CONFIG_VALUE_1,'');assert(!args.some(x=>x.includes('private-test-token')));
   if(fail)throw Error('sensitive private-test-token');
   for(const raw of incomplete?bytes.slice(0,-1):bytes)execFileSync('git',[args[0],'hash-object','-w','--stdin'],{input:raw,env:options.env});
   return Buffer.alloc(0);
  }
  if(args.includes('blob')){
   bodyReads++;
   if(corrupt){
    const raw=bytes[rows.findIndex(row=>row.sha===args.at(-1))];
    if(corrupt==='same-size')return Buffer.alloc(raw.length,0);
    if(corrupt==='oversized')return Buffer.concat([raw,Buffer.from('x')]);
    return raw.subarray(0,raw.length-1);
   }
  }
  return execFileSync(cmd,args,options);
 }});
 return {transport,rows,bytes,get rest(){return rest;},get fetches(){return fetches;},get bodyReads(){return bodyReads;},directory,close(){transport.close();assert.equal(fs.readdirSync(directory).length,0);fs.rmdirSync(directory);}};
}
test('one exact-OID batch replaces blob REST reads while mutable authority remains fresh',async()=>{
 const f=fixture();try{
  await f.transport.api.prefetchGitBlobs('a/b',f.rows);assert.equal(f.bodyReads,0,'acquisition must not walk bodies before actual consumption');
  for(let pass=0;pass<2;pass++)for(let i=0;i<f.rows.length;i++){
   const value=await f.transport.api('/repos/a/b/git/blobs/'+f.rows[i].sha);assert.equal(value.size,f.bytes[i].length);assert.deepEqual(Buffer.from(value.content,'base64'),f.bytes[i]);
  }
  assert.equal(f.bodyReads,4);assert.equal(f.rest,0);assert.equal(f.fetches,1);await f.transport.api('/repos/a/b/pulls/1');await f.transport.api('/repos/a/b/pulls/1');assert.equal(f.rest,2);
  await f.transport.api.prefetchGitBlobs('a/b',f.rows);assert.equal(f.fetches,1);
  const stores=fs.readdirSync(f.directory);assert.equal(stores.length,1);assert(!fs.existsSync(path.join(f.directory,stores[0],'index')));
 }finally{f.close();}
});
test('malformed inventory, wrong repository, unsafe sizes and conflicting sizes are rejected before fetch',async()=>{
 const f=fixture();try{
  for(const [repo,rows] of [['other/repo',f.rows],['a/b',[{sha:'bad',size:1}]],['a/b',[{sha:f.rows[0].sha,size:Number.MAX_SAFE_INTEGER+1}]],['a/b',[f.rows[0],{...f.rows[0],size:99}]]])
   await assert.rejects(f.transport.api.prefetchGitBlobs(repo,rows));
  assert.equal(f.fetches,0);
 }finally{f.close();}
});
for(const corrupt of ['truncated','same-size','oversized'])test(`${corrupt} object bytes fail at actual consumption`,async()=>{
 const f=fixture({corrupt});try{
  await f.transport.api.prefetchGitBlobs('a/b',f.rows);assert.equal(f.bodyReads,0);
  await assert.rejects(f.transport.api('/repos/a/b/git/blobs/'+f.rows[0].sha),/object changed/);assert.equal(f.rest,0);
 }finally{f.close();}
});
test('failed fetch publishes no cache entry and never exposes credentials',async()=>{
 const f=fixture({fail:true});try{await assert.rejects(f.transport.api.prefetchGitBlobs('a/b',f.rows),error=>!error.message.includes('private-test-token'));await f.transport.api('/repos/a/b/git/blobs/'+f.rows[0].sha);assert.equal(f.rest,1);}finally{f.close();}
});
test('missing object in a partial batch fails at consumption without REST fallback',async()=>{
 const f=fixture({incomplete:true});try{
  await f.transport.api.prefetchGitBlobs('a/b',f.rows);
  await assert.rejects(f.transport.api('/repos/a/b/git/blobs/'+f.rows.at(-1).sha),/Exact immutable Git transport failed/);assert.equal(f.rest,0);
 }finally{f.close();}
});

test('Git transport verifies an exact Vietnam-sized object with a tree-bound per-body buffer',async()=>{
 const directory=fs.mkdtempSync(path.join(process.cwd(),'.cache-large-git-')),raw=Buffer.alloc(36065990,23),row=binding(raw);let fetches=0;
 const transport=gitBlobTransport(async()=>{throw Error('Unexpected REST fallback');},{repo:'a/b',token:'synthetic-token',directory,execute:(cmd,args,options)=>{
  if(args.includes('fetch')){fetches++;execFileSync('git',[args[0],'hash-object','-w','--stdin'],{input:raw,env:options.env});return Buffer.alloc(0);}
  if(args.includes('blob'))assert.equal(options.maxBuffer,raw.length+1);
  return execFileSync(cmd,args,options);
 }});
 try{
  await transport.api.prefetchGitBlobs('a/b',[row]);assert.equal(fetches,1);
  const options={expectedImmutableBytes:raw.length};assert.equal((await transport.api('/repos/a/b/git/blobs/'+row.sha,'GET',undefined,options)).size,raw.length);
  await assert.rejects(transport.api('/repos/a/b/git/blobs/'+row.sha,'GET',undefined,{expectedImmutableBytes:raw.length-1}),/tree size/);
 }finally{transport.close();fs.rmdirSync(directory);}
});

// PR2082's exact manifest has 360 unique blobs / 327,390,322 bytes. Model its
// admission boundary without copying 327 MB into every unrelated CI run. The
// separate real-manifest replay checks all original bodies and OIDs.
test('PR2082-sized inventories reach Git instead of silently falling off the old aggregate byte cliff',async()=>{
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'quota-transport-inventory-'));let fetches=0,requested;
 const rows=Array.from({length:360},(_,i)=>({sha:(i+1).toString(16).padStart(40,'0'),size:i===0?327390322-359*800000:800000}));
 const transport=gitBlobTransport(async()=>({fallback:true}),{repo:'a/b',token:'synthetic-token',directory,execute:(cmd,args,options)=>{
  if(args.includes('fetch')){fetches++;requested=options.input.trimEnd().split("\n");throw Error('Simulated Git failure');}
  return execFileSync(cmd,args,options);
 }});
 try{
  assert.equal(rows.reduce((sum,row)=>sum+row.size,0),327390322);
  await assert.rejects(transport.api.prefetchGitBlobs('a/b',rows),/Exact immutable Git transport failed/);
  assert.equal(fetches,1);assert.deepEqual(requested,rows.map(row=>row.sha));
  assert.deepEqual(await transport.api('/repos/a/b/git/blobs/'+rows[0].sha),{fallback:true});
 }finally{transport.close();fs.rmdirSync(directory);}
});
test('complete inventories beyond 512 blobs use one stdin fetch and authenticate the last object',async()=>{
 const f=fixture({count:513});try{
  await f.transport.api.prefetchGitBlobs('a/b',f.rows);
  assert.equal(f.fetches,1);
  const last=f.rows.at(-1),result=await f.transport.api('/repos/a/b/git/blobs/'+last.sha);
  assert.deepEqual(Buffer.from(result.content,'base64'),f.bytes.at(-1));assert.equal(f.rest,0);
  await f.transport.api.prefetchGitBlobs('a/b',f.rows);assert.equal(f.fetches,1);
 }finally{f.close();}
});

test('stdin OIDs execute through real Git fetch without an argv inventory',async()=>{
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'quota-real-fetch-')),upstream=path.join(directory,'upstream.git');
 execFileSync('git',['init','--bare','--quiet',upstream]);
 const raw=Buffer.from('real stdin object'),row=binding(raw);
 execFileSync('git',['--git-dir='+upstream,'hash-object','-w','--stdin'],{input:raw});
 const transport=gitBlobTransport(async()=>{throw Error('Unexpected REST fallback');},{repo:'a/b',token:'synthetic-token',directory,
  execute:(cmd,args,options)=>execFileSync(cmd,args.map(arg=>arg==='https://github.com/a/b.git'?upstream:arg),options)});
 try{await transport.api.prefetchGitBlobs('a/b',[row]);const result=await transport.api('/repos/a/b/git/blobs/'+row.sha);
  assert.deepEqual(Buffer.from(result.content,'base64'),raw);
 }finally{transport.close();fs.rmSync(directory,{recursive:true});}
});

for(const kind of ['tree','wrong-size'])test(`fetched ${kind} object cannot satisfy the consumed tree binding`,async()=>{
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'transport-object-binding-'));
 const raw=Buffer.from('ordinary exact body');let row;
 const transport=gitBlobTransport(async()=>assert.fail('No fallback after successful acquisition'),{repo:'a/b',token:'synthetic',directory,execute:(cmd,args,options)=>{
  if(args.includes('fetch'))return Buffer.alloc(0);
  return execFileSync(cmd,args,options);
 }});
 try{
  const store=path.join(directory,fs.readdirSync(directory)[0]);
  const object=kind==='tree'?execFileSync('git',['--git-dir='+store,'mktree'],{input:''}).toString().trim():execFileSync('git',['--git-dir='+store,'hash-object','-w','--stdin'],{input:raw}).toString().trim();
  row={sha:object,size:kind==='tree'?0:raw.length+1};
  await transport.api.prefetchGitBlobs('a/b',[row]);
  await assert.rejects(transport.api('/repos/a/b/git/blobs/'+row.sha),kind==='tree'?/Exact immutable Git transport failed/:/object changed/);
 }finally{transport.close();fs.rmdirSync(directory);}
});
