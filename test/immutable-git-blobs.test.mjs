import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {githubAPI} from '../scripts/issue-claim-contract.mjs';
import {memoizeImmutableGitBlobs} from '../scripts/immutable-git-blobs.mjs';
const blob = content => {
 const raw = Buffer.from(content), sha = createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
 return {sha, size:raw.length, encoding:'base64', content:raw.toString('base64')};
};
const route = b => `/repos/o/r/git/blobs/${b.sha}`;
test('root-format 1479 blob requests become 474 verified immutable fetches across three authority passes',async()=>{
 // #1150/head405 retains 474 distinct OIDs totaling235417555 bytes. This
 // synthetic distribution models that actual aggregate without copying data.
 const count=474,total=235417555,largest=14322993,rest=total-largest,size=Math.floor(rest/(count-1)),extra=rest%(count-1);
 const entries=Array.from({length:count},(_,i)=>{
  const raw=Buffer.alloc(i===0?largest:size+(i<=extra?1:0),i%256);raw.writeUInt32LE(i);
  const sha=createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
  return {sha,size:raw.length,index:i};
 });
 const index=new Map(entries.map(e=>[route(e),e]));let calls=0;
 const api=memoizeImmutableGitBlobs(async r=>{
  calls++;const e=index.get(r),raw=Buffer.alloc(e.size,e.index%256);raw.writeUInt32LE(e.index);
  return {...e,encoding:'base64',content:raw.toString('base64')};
 });
 const loads=[...entries,...entries.slice(0,19)];assert.equal(loads.length,493);
 for(let pass=0;pass<3;pass++)for(const entry of loads)assert.equal((await api(route(entry))).sha,entry.sha);
 assert.equal(calls,474);assert.equal(loads.length*3,1479);
});
test('cache keeps fresh changed OIDs, repository identity, trees and authority reads',async()=>{
 const first=blob('first'),changed=blob('changed'),calls=[];
 const api=memoizeImmutableGitBlobs(async r=>{calls.push(r);return r.endsWith(first.sha)?first:r.endsWith(changed.sha)?changed:{mutable:true};});
 await api(route(first));await api(route(first));await api(route(changed));
 await api(`/repos/other/repo/git/blobs/${first.sha}`);
 for(const mutable of ['/pulls/1','/issues/1/comments','/commits/head/check-runs','/commits/head/status','/compare/base...head','/git/trees/tree?recursive=1','/git/ref/heads/main']) {
  await api('/repos/o/r'+mutable);await api('/repos/o/r'+mutable);
  assert.equal(calls.filter(r=>r.endsWith(mutable)).length,2);
 }
 assert.equal(calls.filter(r=>r===route(first)).length,1);assert.equal(calls.filter(r=>r===route(changed)).length,1);
 assert.equal(calls.filter(r=>r.includes('/other/repo/')).length,1);
});
test('failed, malformed, truncated, changed content and mismatched OID responses never populate cache',async()=>{
 const good=blob('verified bytes');
 for(const failure of [Error('HTTP403'),{...good,encoding:'utf-8'},{...good,size:good.size+1},{...good,content:good.content.slice(0,-1)},
  {...good,content:blob('other').content},{...good,sha:'a'.repeat(40)},{...good,size:-1}]) {
  let calls=0;const api=memoizeImmutableGitBlobs(async()=>{calls++;if(calls===1){if(failure instanceof Error)throw failure;return failure;}return good;});
  await assert.rejects(api(route(good)));assert.equal((await api(route(good))).sha,good.sha);await api(route(good));assert.equal(calls,2);
 }
});
test('bounded memory/entry overflow stays uncached without evicting useful initial scan; execution caches are separate',async()=>{
 const a=blob('a'),b=blob('b');let calls=0;const origin=async r=>{calls++;return r.endsWith(a.sha)?a:b;};
 const api=memoizeImmutableGitBlobs(origin,{maxEntries:1,maxBytes:1});
 await api(route(a));await api(route(b));await api(route(a));await api(route(b));assert.equal(calls,3);
 await memoizeImmutableGitBlobs(origin)(route(a));assert.equal(calls,4);
 assert.throws(()=>memoizeImmutableGitBlobs(origin,{maxEntries:-1}),/bounds/);
});


test('actual API rejection preserves only sanitized message/status and allowlisted rate/request headers',async()=>{
 const original=globalThis.fetch;
 globalThis.fetch=async()=>Response.json({message:'denied github_pat_notasecret Bearer synthetic-token',documentation_url:'not retained',unknown:'not retained'},
  {status:403,headers:{'x-ratelimit-remaining':'0','x-ratelimit-reset':'1791306000','retry-after':'60','x-github-request-id':'ABCD:1234',authorization:'Bearer synthetic-token','set-cookie':'secret'}});
 try {
  await assert.rejects(githubAPI('synthetic-token')('/repos/o/r/git/blobs/'+'a'.repeat(40)),e=>{
   assert.match(e.message,/\(HTTP 403\)$/);assert.deepEqual(e.github,{http_status:403,message:'denied [redacted] Bearer [redacted]',rate_remaining:'0',rate_reset:'1791306000',retry_after:'60',request_id:'ABCD:1234'});
   assert.ok(!JSON.stringify(e.github).includes('synthetic-token'));return true;
  });
 } finally {globalThis.fetch=original;}
});


test('callers and origin objects cannot mutate cached bytes or metadata used by later checks',async()=>{
 const origin=blob('unchanged immutable content'),expected={...origin};
 const api=memoizeImmutableGitBlobs(async()=>origin);
 const first=await api(route(expected));assert.ok(Object.isFrozen(first));
 assert.throws(()=>{first.content='mutated';},TypeError);assert.throws(()=>{first.size=0;},TypeError);
 origin.content='changed origin';origin.sha='f'.repeat(40);origin.size=0;
 assert.deepEqual(await api(route(expected)),expected);
});
