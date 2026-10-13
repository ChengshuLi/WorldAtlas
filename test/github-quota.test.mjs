import test from 'node:test';
import assert from 'node:assert/strict';
import {githubAPI} from '../scripts/issue-claim-contract.mjs';
import {quotaDelay,requestAccounting} from '../scripts/github-quota.mjs';
const response=(status,remaining='0',extra={})=>new Response(JSON.stringify({message:status===403?'rate limit exceeded':'ok'}),{status,headers:{'x-ratelimit-limit':'1000','x-ratelimit-remaining':remaining,'x-ratelimit-reset':'100','x-ratelimit-resource':'core',...extra}});
async function mocked(run,fn){const old=globalThis.fetch;globalThis.fetch=run;try{await fn();}finally{globalThis.fetch=old;}}
test('quota retry only retries an explicit read rejection, and accounts every attempt',async()=>{
 let calls=0,time=99000;const accounting=requestAccounting('prepare');
 await mocked(async()=>response(++calls===1?403:200,calls===1?'0':'999'),async()=>{
  const api=githubAPI('private',{now:()=>time,sleep:async ms=>{time+=ms;},readWaitMs:10000,onRequest:accounting.observe});
  await api('/repos/a/b/pulls/1');assert.equal(calls,2);assert.equal(accounting.receipt().actual_http_attempts,2);
 });
});
test('ordinary permission denial, write denial, and ambiguous write never retry',async()=>{
 for(const [method,remaining,ambiguous] of [['GET','99',false],['POST','0',false],['PUT','0',true]]){
  let calls=0;
  await mocked(async()=>{calls++;if(ambiguous)throw Error('network');return response(403,remaining);},async()=>{
   const api=githubAPI('private',{readWaitMs:999999,sleep:async()=>assert.fail('must not wait')});
   await assert.rejects(api('/repos/a/b/pulls/1',method));assert.equal(calls,1);
  });
 }
});
test('read retry respects its finite phase deadline and repeated concurrent exhaustion',async()=>{
 let calls=0,time=99000;
 await mocked(async()=>{calls++;return response(403);},async()=>{
  const api=githubAPI('private',{readWaitMs:2500,now:()=>time,sleep:async ms=>{time+=ms;}});
  await assert.rejects(api('/repos/a/b'),/HTTP 403/);assert(calls<=3);assert(time<101500);
 });
});
test('actual repository capacity overrides unrelated generic capacity',async()=>{
 const routes=[];
 await mocked(async url=>{routes.push(url);return response(403);},async()=>{
  const api=githubAPI('private');const row=await api.readRepositoryCapacity('a/b');
  assert.equal(row.remaining,0);assert.equal(row.limit,1000);assert.equal(routes.length,1);assert(routes[0].endsWith('/repos/a/b'));
 });
});
test('secondary limits cannot masquerade as positive capacity',async()=>{
 await mocked(async()=>response(403,'500',{'retry-after':'2'}),async()=>{
  await assert.rejects(githubAPI('private').readRepositoryCapacity('a/b'),/HTTP 403/);
 });
});
test('invalid capacity headers fail closed and concurrent reads cannot replace probe headers',async()=>{
 await mocked(async url=>url.endsWith('/repos/a/b')?response(200,'12'):response(200,'900'),async()=>{
  const api=githubAPI('private');const [row]=await Promise.all([api.readRepositoryCapacity('a/b'),api('/repos/a/b/pulls/1')]);assert.equal(row.remaining,12);
 });
 await mocked(async()=>new Response('{}'),async()=>{await assert.rejects(githubAPI('private').readRepositoryCapacity('a/b'),/Unavailable/);});
});
test('actual read quota rejection honors secondary retry-after within its finite deadline',async()=>{
 let time=0,calls=0;
 await mocked(async()=>response(++calls===1?403:200,'500',calls===1?{'retry-after':'2'}:{}),async()=>{
  const api=githubAPI('private',{readWaitMs:10000,deadlineRemaining:()=>60000-time,now:()=>time,sleep:async ms=>{time+=ms;}});
  await api('/repos/a/b/pulls/1');assert.equal(time,3000);assert.equal(calls,2);
 });
});
test('quota classifier rejects malformed or irrelevant error metadata',()=>{
 assert.equal(quotaDelay({github:{http_status:404,rate_remaining:'0',rate_reset:'100'}}),null);
 assert.equal(quotaDelay({github:{http_status:403,retry_after:'bogus'}}),null);
});
test('deadline refuses a quota wait that cannot fit one complete HTTP attempt',async()=>{
 let calls=0,time=99000;
 await mocked(async()=>{calls++;return response(403);},async()=>{
  const api=githubAPI('private',{readWaitMs:10000,deadlineRemaining:()=>120000-time,
    now:()=>time,sleep:async()=>assert.fail('deadline cannot admit this wait')});
  await assert.rejects(api('/repos/a/b/pulls/1'),error=>error.jobDeadline===true&&error.github?.rate_remaining==='0');
  assert.equal(calls,1);
 });
});
test('deadline is rechecked after an oversleep before a retry actually sends HTTP',async()=>{
 let calls=0,time=99000;
 await mocked(async()=>{calls++;return response(403);},async()=>{
  const api=githubAPI('private',{readWaitMs:60000,deadlineRemaining:()=>130000-time,
    now:()=>time,sleep:async()=>{time+=15000;}});
  await assert.rejects(api('/repos/a/b/pulls/1'),error=>error.jobDeadline===true&&error.quotaCause?.github?.rate_remaining==='0');
  assert.equal(calls,1);
 });
});

test('accounting observes real repository headers without an extra capacity poll or retained secrets',async()=>{
 const accounting=requestAccounting('probe');let calls=0;
 await mocked(async()=>{calls++;return response(200,calls===1?'42':'39',{'authorization':'private-secret'});},async()=>{
  const api=githubAPI('private-secret',{onRequest:accounting.observe});
  await api('/repos/a/b/pulls/1');await api('/repos/a/b/issues/2');
 });
 const receipt=accounting.receipt();assert.equal(calls,2);assert.equal(receipt.actual_http_attempts,2);
 assert.deepEqual(receipt.observed_repository_core.first,{limit:1000,remaining:42,reset:100});
 assert.deepEqual(receipt.observed_repository_core.last,{limit:1000,remaining:39,reset:100});
 assert.equal(receipt.observed_repository_core.lowest_remaining.remaining,39);
 assert(!JSON.stringify(receipt).includes('private-secret'));
});
test('unknown or wrong-resource headers cannot manufacture an observed repository quota',()=>{
 const accounting=requestAccounting('probe');
 for(const capacity of [{resource:'core',limit:1000,remaining:undefined,reset:100},{resource:'search',limit:30,remaining:3,reset:100},
  {resource:'core',limit:1000,remaining:1001,reset:100}])accounting.observe({route:'/repos/a/b',method:'GET',status:200,capacity});
 assert.equal(accounting.receipt().observed_repository_core,undefined);assert.equal(accounting.receipt().actual_http_attempts,3);
});

test('deployment classification quota refusal does not authorize a wasteful full-build fallback',async()=>{
 const {deploymentBudgetProfile,githubBudgetAPI}=await import('../scripts/classify-deployment-budget.mjs');
 const event={repository:{full_name:'a/b'},pull_request:{number:1,head:{sha:'a'.repeat(40)},base:{sha:'b'.repeat(40)}}};
 const run=remaining=>deploymentBudgetProfile({event,eventName:'pull_request',repository:'a/b',
  api:route=>githubBudgetAPI(route,{token:'private',fetchImpl:async()=>response(403,remaining)})});
 const quota=await run('0');assert.equal(quota.blocked,true);assert.equal(quota.full,true);assert.equal(quota.api_error.rate_remaining,'0');
 assert.equal(quota.fallback,true);assert(quota.retry_at);
 const ordinary=await run('500');assert.equal(ordinary.blocked,undefined);assert.equal(ordinary.full,true);assert.equal(ordinary.fallback,true);
});

test('deployment transport ambiguity counts its attempt without inventing quota or retrying',async()=>{
 const {githubBudgetAPI}=await import('../scripts/classify-deployment-budget.mjs');
 const accounting=requestAccounting('deployment-classifier');let attempts=0;
 await assert.rejects(githubBudgetAPI('/repos/a/b',{token:'private',onRequest:accounting.observe,
  fetchImpl:async()=>{attempts++;throw Error('transport lost');}}),/transport lost/);
 assert.equal(attempts,1);assert.equal(accounting.receipt().actual_http_attempts,1);
 assert.equal(accounting.receipt().counts['GET:repository-authority:transport-error'],1);
});

test('caller response admission bounds the real JSON stream while preserving request accounting',async()=>{
  const accounting=requestAccounting('bounded-metadata');let cancelled=false,pulls=0;
  const api=githubAPI('fixture',{onRequest:accounting.observe,fetchImpl:async()=>new Response(new ReadableStream({
    pull(controller){pulls++;controller.enqueue(Buffer.alloc(8,32));},cancel(){cancelled=true;}
  }),{headers:{etag:'"bounded"'}})});
  await assert.rejects(api('/repos/a/b/issues/1/comments','GET',undefined,{maxResponseBytes:16}),/caller byte allowance/);
  await new Promise(resolve=>setImmediate(resolve));
  assert(cancelled);assert(pulls<=5);assert.equal(accounting.receipt().actual_http_attempts,1);
});
test('bounded metadata reads cannot use larger ETag snapshots or grant writes an admission bypass',async()=>{
  const seen=[];const api=githubAPI('fixture',{fetchImpl:async(url,init)=>{
    seen.push(init.headers);return new Response(JSON.stringify({value:'x'.repeat(64)}),{headers:{etag:'"large"'}});
  }});
  await api('/repos/a/b/pulls/1');
  await assert.rejects(api('/repos/a/b/pulls/1','GET',undefined,{maxResponseBytes:16}),/caller byte allowance/);
  assert.equal(seen.length,2);assert.equal(seen[1]['If-None-Match'],undefined);
  for(const value of [0,-1,NaN,Infinity,'16'])await assert.rejects(api('/repos/a/b','GET',undefined,{maxResponseBytes:value}),/response-byte admission/);
  await assert.rejects(api('/repos/a/b','POST',{}, {maxResponseBytes:16}),/response-byte admission/);
  assert.equal(seen.length,2);
  assert.deepEqual(await api('/repos/a/b/pulls/1','GET',undefined,{maxResponseBytes:128}),{value:'x'.repeat(64)});
});
test('a capped read keeps its byte allowance through the actual reset-capacity probe',async()=>{
  let now=0;const routes=[];
  const api=githubAPI('fixture',{minimumRemaining:16,now:()=>now,fetchImpl:async url=>{
    routes.push(url);return new Response(routes.length===1?'{}':JSON.stringify({large:'x'.repeat(64)}),{
      headers:{'x-ratelimit-resource':'core','x-ratelimit-limit':'5000','x-ratelimit-remaining':routes.length===1?'0':'5000','x-ratelimit-reset':'1'}});
  }});
  await api('/repos/a/b/pulls/1');now=2000;
  await assert.rejects(api('/repos/a/b/pulls/2','GET',undefined,{maxResponseBytes:16}),/caller byte allowance/);
  assert.deepEqual(routes,['https://api.github.com/repos/a/b/pulls/1','https://api.github.com/repos/a/b']);
});
