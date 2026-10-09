import test from 'node:test';
import assert from 'node:assert/strict';
import {githubAPI} from '../scripts/issue-claim-contract.mjs';
import {quotaDelay,requestAccounting} from '../scripts/github-quota.mjs';
async function mocked(fn,run){const previous=globalThis.fetch;globalThis.fetch=fn;try{await run();}finally{globalThis.fetch=previous;}}
const headers=(remaining,reset=3600)=>({'x-ratelimit-limit':'1000','x-ratelimit-remaining':String(remaining),'x-ratelimit-reset':String(reset),'x-ratelimit-resource':'core'});
const response=(remaining,reset=3600)=>new Response('{}',{headers:headers(remaining,reset)});
function clock(){let time=0;return {now:()=>time,sleep:async ms=>{time+=ms;},advance:ms=>{time+=ms;}};}

test('a burst of launched reads drains without consuming the recovery floor',async()=>{
 const timing=clock(),accounting=requestAccounting('burst');let remaining=32,calls=0,active=0,maximum=0;
 await mocked(async()=>{calls++;active++;maximum=Math.max(maximum,active);await Promise.resolve();active--;return response(--remaining);},async()=>{
  const api=githubAPI('private',{...timing,minimumRemaining:16,onRequest:accounting.observe});
  const results=await Promise.allSettled(Array.from({length:50},(_,i)=>api('/repos/a/b/issues/'+i)));
  assert.equal(results.filter(x=>x.status==='fulfilled').length,16);
  assert(results.filter(x=>x.status==='rejected').every(x=>x.reason.quotaAdmission&&x.reason.github===undefined));
 });
 assert.equal(remaining,16);assert.equal(calls,16);assert(maximum>1, 'Independent admitted reads must stay parallel');assert(maximum<=16);assert.equal(accounting.receipt().actual_http_attempts,16);
});
test('higher stale counters and an early different reset cannot mint capacity',async()=>{
 const timing=clock();let calls=0;
 await mocked(async()=>response(++calls===1?20:999,calls===1?3600:7200),async()=>{
  const api=githubAPI('private',{...timing,minimumRemaining:16});
  await api('/repos/a/b/issues/1');
  for(let i=0;i<4;i++)await api('/repos/a/b/issues/1');
  await assert.rejects(api('/repos/a/b/issues/1'),error=>error.quotaAdmission.remaining===16&&error.quotaAdmission.reset===3600);
});assert.equal(calls,5);
});
test('later reset headers cannot perpetually postpone the first authenticated recovery window',async()=>{
 const timing=clock();let calls=0;
 await mocked(async()=>response(++calls===1?18:900,calls===1?3600:7200),async()=>{
  const api=githubAPI('private',{...timing,minimumRemaining:16});
  await api('/repos/a/b/issues/1');
  await api('/repos/a/b/issues/2');
  await api('/repos/a/b/issues/3');
  await assert.rejects(api('/repos/a/b/issues/4'),error=>error.quotaAdmission.reset===3600);
  timing.advance(3600000);
  await api('/repos/a/b/issues/4');
 });assert.equal(calls,5); // A fresh repository observation precedes resumed work.
});
test('an authenticated unchanged response refunds the conservative possible paid attempt',async()=>{
 const timing=clock();let calls=0;
 await mocked(async(url,options)=>++calls===1?new Response('{"body":"contract"}',{headers:{...headers(17),etag:'"one"'}}):
  new Response(null,{status:304,headers:{...headers(17),etag:'"one"'}}),async()=>{
   const api=githubAPI('private',{...timing,minimumRemaining:16});
   for(let i=0;i<30;i++)assert.equal((await api('/repos/a/b/issues/1')).body,'contract');
 });assert.equal(calls,30);
});
test('a reset timestamp never grants unobserved capacity and a fresh positive probe is required',async()=>{
 const timing=clock(),routes=[];let resetGranted=false;
 await mocked(async url=>{routes.push(url);return response(resetGranted?500:16,resetGranted?7200:3600);},async()=>{
  const api=githubAPI('private',{...timing,minimumRemaining:16});
  await api('/repos/a/b/issues/1');
  await assert.rejects(api.readRepositoryCapacity('a/b'),e=>quotaDelay(e,timing.now())!==null);
  assert.equal(routes.length,1);timing.advance(3600000);
  await assert.rejects(api('/repos/a/b/issues/2'),e=>e.quotaAdmission.remaining===16);
  assert(routes.at(-1).endsWith('/repos/a/b'));assert.equal(routes.length,2);
  resetGranted=true;await api('/repos/a/b/issues/2');
  assert(routes.at(-2).endsWith('/repos/a/b'));assert(routes.at(-1).endsWith('/issues/2'));
 });
});
test('a first mutation requires positive actual capacity, never retries and preserves ambiguity',async()=>{
 const timing=clock(),methods=[];
 await mocked(async(url,options)=>{methods.push(options.method);if(options.method==='GET')return response(500);throw Error('lost response');},async()=>{
  const api=githubAPI('private',{...timing,minimumRemaining:16});
  await assert.rejects(api('/repos/a/b/issues/1/comments','POST',{body:'progress'}),/lost response/);
 });assert.deepEqual(methods,['GET','POST']);
 await mocked(async()=>response(16),async()=>{
  await assert.rejects(githubAPI('private',{...clock(),minimumRemaining:16})('/repos/a/b/issues/1/comments','POST',{body:'progress'}),e=>!!e.quotaAdmission);
 });
});
test('missing core headers cannot support further authenticated work',async()=>{
 await mocked(async()=>new Response('{}'),async()=>{
  await assert.rejects(githubAPI('private',{...clock(),minimumRemaining:16})('/repos/a/b/issues/1'),/Missing actual core capacity/);
 });
});
test('available capacity imposes no artificial sleeps and actual remaining deadline still binds reads/writes',async()=>{
 const timing=clock(),starts=[];let sleeps=0;
 await mocked(async(url,options)=>{starts.push({time:timing.now(),method:options.method});return response(900);},async()=>{
  const api=githubAPI('private',{...timing,sleep:async()=>{sleeps++;throw Error('Artificial pacing is forbidden');},minimumRemaining:16});
  await Promise.all([api('/repos/a/b/issues/1'),api('/repos/a/b/issues/2'),api('/repos/a/b/issues/1/comments','POST',{}),api('/repos/a/b/issues/1/comments','POST',{})]);
 });
 assert.equal(sleeps,0);assert(starts.every(row=>row.time===0));
 let calls=0;
 await mocked(async()=>{calls++;timing.advance(100);return response(900);},async()=>{
  const api=githubAPI('private',{...timing,minimumRemaining:16,deadlineRemaining:()=>20050-timing.now()});
  await assert.rejects(api('/repos/a/b/issues/1/comments','POST',{}),e=>e.jobDeadline===true);
 });assert.equal(calls,1); // Initial capacity read consumed actual deadline margin.
});

test('artifact redirect consumes shared admission and preserves fixed-host credentials', async () => {
 const timing=clock(), accounting=requestAccounting('artifact'), calls=[]; let budget=1;
 await mocked(async(url, options)=>{
  calls.push({url,options});
  return new Response(null,{status:302,headers:{...headers(900),location:'https://results.blob.core.windows.net/a?signature=private-secret'}});
 }, async()=>{
  const api=githubAPI('private',{...timing,minimumRemaining:16,onRequest:accounting.observe});
  api.setHTTPAdmission(()=>{if(!budget--)throw Object.assign(Error('budget refused'),{requestBudget:true});});
  const response=await api.artifactRedirect('/repos/a/b/actions/artifacts/12/zip');
  assert.equal(response.status,302);
  assert.equal(calls[0].options.redirect,'manual');
  assert.equal(calls[0].options.headers.Authorization,'Bearer private');
  await assert.rejects(api.artifactRedirect('/repos/a/b/actions/artifacts/12/zip'),e=>e.requestBudget===true);
  assert.equal(calls.length,1);
 });
 assert.equal(accounting.receipt().actual_http_attempts,1);
 assert(!JSON.stringify(accounting.receipt()).includes('private-secret'));
});
test('artifact redirects cannot bypass a known quota floor or fetch another host', async () => {
 const timing=clock();let calls=0;
 await mocked(async()=>{calls++;return response(16);},async()=>{
  const api=githubAPI('private',{...timing,minimumRemaining:16});
  await api('/repos/a/b');
  await assert.rejects(api.artifactRedirect('/repos/a/b/actions/artifacts/12/zip'),e=>!!e.quotaAdmission);
  for(const route of ['https://attacker.example/a','/repos/a/b/actions/artifacts/0/zip','/repos/a/b/actions/artifacts/12/zip?redirect=1'])
   assert.throws(()=>api.artifactRedirect(route),/Invalid artifact redirect route/);
 });assert.equal(calls,1);
});

test('protected capacity can finish exact owned cleanup and durable notification, but not new work', async () => {
 const timing=clock(), accounting=requestAccounting('recovery');let available=17,calls=0;
 const ref='worldatlas-integration/pr-1-synthetic-unique-request', route='/repos/a/b/git/ref/heads/'+ref;
 await mocked(async(url, options)=>{
  calls++; available--;
  if(options.method==='DELETE') return new Response(null,{status:204,headers:headers(available)});
  return Response.json(new URL(url).pathname.includes('/git/ref/')?{object:{sha:'a'.repeat(40)}}:{},{headers:headers(available)});
 },async()=>{
  const api=githubAPI('private',{...timing,minimumRemaining:16,onRequest:accounting.observe});
  await api('/repos/a/b');
  await assert.rejects(api('/repos/a/b/issues/1'),e=>!!e.quotaAdmission);
  const {cleanupCandidate}=await import('../scripts/merge-integration.mjs');
  const result=await cleanupCandidate({api,repo:'a/b',number:1,integrationRequestId:'synthetic-unique-request'},ref,'a'.repeat(40));
  assert.equal(result.status,'deleted');
  await api.recovery('/repos/a/b/issues/1/comments','POST',{body:'**Merge result:** not accepted\n<!-- worldatlas-merge-result:v1\n{}\n-->'});
  await api.recovery(route);
  await assert.rejects(api.recovery(route),e=>e.recoveryBudget===true);
  for(const [route,method,body] of [
   ['/repos/a/b/issues/1','GET'],['/repos/a/b/git/refs/heads/main','DELETE'],
   ['/repos/a/b/issues/1/comments','POST',{body:'arbitrary new work'}]
  ]) assert.throws(()=>api.recovery(route,method,body),/outside bounded merge recovery/);
 });
 assert.equal(calls,5); assert.equal(available,12); assert.equal(accounting.receipt().actual_http_attempts,5);
});
test('recovery preserves original ref ownership checks and never repeats ambiguous deletes', async () => {
 const timing=clock(), methods=[];
 await mocked(async(url,options)=>{
  methods.push(options.method);
  if(options.method==='DELETE') throw Error('lost deletion response');
  return Response.json({object:{sha:'b'.repeat(40)}},{headers:headers(16)});
 },async()=>{
  const {cleanupCandidate}=await import('../scripts/merge-integration.mjs');
  const api=githubAPI('private',{...timing,minimumRemaining:16});
  await api('/repos/a/b');
  const options={api,repo:'a/b',number:1,integrationRequestId:'synthetic-unique-request'};
  await assert.rejects(cleanupCandidate(options,'main','a'.repeat(40)),/unowned/);
  await assert.rejects(cleanupCandidate(options,'worldatlas-integration/pr-1-synthetic-unique-request','a'.repeat(40)),/reference changed/);
  assert(!methods.includes('DELETE'));
  await assert.rejects(api.recovery('/repos/a/b/git/refs/heads/worldatlas-integration/pr-1-synthetic-unique-request','DELETE'),/lost deletion response/);
  assert.equal(methods.filter(method=>method==='DELETE').length,1);
 });
});

test('concurrent 304 refunds only its own reservation and cannot erase other in-flight paid charges', async () => {
 const timing=clock();let initialized=false,release;const held=new Promise(resolve=>{release=resolve;});
 await mocked(async(url,options)=>{
  if(!initialized){initialized=true;return new Response('{}',{headers:{...headers(20),etag:'"same"'}});}
  if(options.headers['If-None-Match']){
   await held;return new Response(null,{status:304,headers:{...headers(20),etag:'"same"'}});
  }
  return response(20); // Deliberately stale high counters cannot mint credit.
 },async()=>{
  const api=githubAPI('private',{...timing,minimumRemaining:16});
  await api('/repos/a/b/issues/1');
  const unchanged=api('/repos/a/b/issues/1');
  await Promise.all([api('/repos/a/b/issues/2'),api('/repos/a/b/issues/3'),api('/repos/a/b/issues/4')]);
  release();await unchanged;
  await api('/repos/a/b/issues/5');
  await assert.rejects(api('/repos/a/b/issues/6'),e=>e.quotaAdmission.remaining===16);
 });
});
