import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {copyAPIFeatures} from './github-quota.mjs';
import {addBytes} from './evidence-quality.mjs';

const MAX_ENTRIES=512;
const oid=value=>/^[a-f0-9]{40}$/.test(value??'');
// Fetch exact tree-bound blob OIDs into a disposable bare object store. No
// candidate checkout, hooks, persistent credential or executable candidate code.
export function gitBlobTransport(api,{repo,token,directory,onFetch=()=>{},execute=execFileSync}){
 if(!/^[-\w.]+\/[-\w.]+$/.test(repo??'')||!token||!path.isAbsolute(directory))throw Error('Invalid immutable transport configuration');
 const store=fs.mkdtempSync(path.join(directory,'quota-blobs-')),known=new Map();
 const env=Object.fromEntries(Object.entries(process.env).filter(([key])=>!key.startsWith('GIT_')));
 Object.assign(env,{GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_GLOBAL:'/dev/null',GIT_TERMINAL_PROMPT:'0',
   GIT_CONFIG_COUNT:'3',GIT_CONFIG_KEY_0:'http.extraHeader',GIT_CONFIG_VALUE_0:'AUTHORIZATION: basic '+Buffer.from('x-access-token:'+token).toString('base64'),
   GIT_CONFIG_KEY_1:'credential.helper',GIT_CONFIG_VALUE_1:'',GIT_CONFIG_KEY_2:'core.hooksPath',GIT_CONFIG_VALUE_2:'/dev/null'});
 const git=(args,maxBuffer=1024*1024)=>{
  try{return execute('git',['--git-dir='+store,...args],{env,maxBuffer,timeout:60000,stdio:['ignore','pipe','pipe']});}
  catch{throw Error('Exact immutable Git transport failed; no partial bytes accepted');}
 };
 try{git(['init','--bare',store]);}catch(error){fs.rmSync(store,{recursive:true,force:true});throw error;}
 const prefetch=async(targetRepo,rows)=>{
  if(targetRepo!==repo||!Array.isArray(rows)||rows.length>MAX_ENTRIES)throw Error('Invalid immutable transport inventory');
  const pending=new Map();
  for(const row of rows){
   if(!oid(row.sha)||!Number.isSafeInteger(row.size)||row.size<0)throw Error('Invalid tree-bound immutable blob');
   const prior=known.get(row.sha)??pending.get(row.sha);
   if(prior!==undefined&&prior!==row.size)throw Error('Conflicting immutable tree sizes');
   if(!known.has(row.sha))pending.set(row.sha,row.size);
  }
  if(!pending.size)return;
  const extra=[...pending.values()].reduce((a,b)=>addBytes(a,b),0);
  if(known.size+pending.size>MAX_ENTRIES)return; // Exact REST fallback retains validation.
  // Git streams the admitted inventory to disk; aggregate bytes are not resident memory.
  git(['-c','fetch.unpackLimit=1','fetch','--no-tags','--no-write-fetch-head','--recurse-submodules=no','--filter=blob:none',
    'https://github.com/'+repo+'.git',...[...pending.keys()]]);
  // Verify every object before publishing any success from this batch.
  for(const [sha,size] of pending){
   if(git(['cat-file','-t',sha]).toString().trim()!=='blob')throw Error('Immutable object is not a blob');
   const content=git(['cat-file','blob',sha],Math.max(1,addBytes(size,1)));
   if(content.length!==size||createHash('sha1').update(`blob ${content.length}\0`).update(content).digest('hex')!==sha)throw Error('Immutable object bytes differ from tree binding');
  }
  for(const [sha,size] of pending)known.set(sha,size);
  onFetch({blob_count:pending.size,decoded_bytes:extra});
 };
 const wrapped=async(route,method='GET',body,options)=>{
  const match=/^\/repos\/([-\w.]+\/[-\w.]+)\/git\/blobs\/([a-f0-9]{40})$/.exec(route);
  if(method!=='GET'||body!==undefined||!match||match[1]!==repo||!known.has(match[2]))return api(route,method,body,options);
  const size=known.get(match[2]);
  if(options?.expectedImmutableBytes!==undefined&&options.expectedImmutableBytes!==size)throw Error('Immutable transport tree size differs');
  const bytes=git(['cat-file','blob',match[2]],Math.max(1,addBytes(size,1)));
  if(bytes.length!==known.get(match[2])||createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex')!==match[2])throw Error('Immutable transport object changed');
  return {sha:match[2],size:bytes.length,encoding:'base64',content:bytes.toString('base64')};
 };
 copyAPIFeatures(wrapped,api);wrapped.prefetchGitBlobs=prefetch;
 wrapped.hasGitBlobs=(targetRepo,rows)=>targetRepo===repo&&Array.isArray(rows)&&rows.every(row=>known.has(row.sha)&&known.get(row.sha)===row.size);
 return {api:wrapped,close(){fs.rmSync(store,{recursive:true,force:true});}};
}
