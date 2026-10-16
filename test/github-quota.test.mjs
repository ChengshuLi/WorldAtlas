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
for(const status of [500,502,503,504])test(`shared GET retries explicit HTTP${status} within its existing attempt and phase allowance`,async()=>{
 let calls=0,time=0;const accounting=requestAccounting('merge'),route='/repos/a/b/git/trees/'+'a'.repeat(40);
 await mocked(async url=>{assert.equal(url,'https://api.github.com'+route);return response(++calls===1?status:200,'999');},async()=>{
  const api=githubAPI('private',{now:()=>time,sleep:async ms=>{time+=ms;},readWaitMs:10000,
    deadlineRemaining:()=>60000-time,onRequest:accounting.observe});
  await api(route);assert.equal(calls,2);assert.equal(time,1000);
  assert.equal(accounting.receipt().actual_http_attempts,2);
  assert.equal(accounting.receipt().counts[`GET:immutable-metadata:${status}`],1);
 });
});
test('exhausted transient reads preserve the actual server failure after only two bounded retries',async()=>{
 let calls=0,time=0;
 await mocked(async()=>{calls++;return response(500,'999');},async()=>{
  const api=githubAPI('private',{now:()=>time,sleep:async ms=>{time+=ms;},readWaitMs:10000,
    deadlineRemaining:()=>60000-time});
  await assert.rejects(api('/repos/a/b/git/trees/'+'a'.repeat(40)),error=>error.github?.http_status===500&&!error.quotaCause);
  assert.equal(calls,3);assert.equal(time,3000);
 });
});
test('quota and transient server responses share one unchanged retry ceiling',async()=>{
 let calls=0,time=99000;
 await mocked(async()=>{calls++;return response(calls===1?403:calls===2?503:200,calls===1?'0':'999');},async()=>{
  const api=githubAPI('private',{now:()=>time,sleep:async ms=>{time+=ms;},readWaitMs:10000,
    deadlineRemaining:()=>160000-time});
  await api('/repos/a/b/pulls/1');assert.equal(calls,3);assert.equal(time,103000);
 });
});
test('transient response cannot add a wait when the caller or next complete HTTP attempt lacks allowance',async()=>{
 for(const options of [{readWaitMs:0},{readWaitMs:10000,deadlineRemaining:()=>21000}]){
  let calls=0;
  await mocked(async()=>{calls++;return response(502,'999');},async()=>{
   const api=githubAPI('private',{...options,sleep:async()=>assert.fail('wait is not admitted')});
   await assert.rejects(api('/repos/a/b/pulls/1'),error=>error.github?.http_status===502);
   assert.equal(calls,1);
  });
 }
});
test('transient retry rechecks deadline after an oversleep before another HTTP send',async()=>{
 let calls=0,time=0;
 await mocked(async()=>{calls++;return response(504,'999');},async()=>{
  const api=githubAPI('private',{now:()=>time,readWaitMs:60000,deadlineRemaining:()=>60000-time,
    sleep:async()=>{time=60000;}});
  await assert.rejects(api('/repos/a/b/pulls/1'),error=>error.jobDeadline===true);
  assert.equal(calls,1);
 });
});
test('server failures never retry writes, body-bearing reads, transport ambiguity or unsupported status',async()=>{
 for(const [method,body,status,ambiguous]of [
  ['POST',{},500,false],['PUT',{},502,false],['PATCH',{},503,false],['DELETE',undefined,504,false],
  ['GET',{},500,false],['GET',undefined,200,true],['GET',undefined,401,false],['GET',undefined,404,false],
  ['GET',undefined,422,false],['GET',undefined,501,false],['GET',undefined,505,false]]){
  let calls=0;
  await mocked(async()=>{calls++;if(ambiguous)throw Error('ambiguous transport');return response(status,'999');},async()=>{
   const api=githubAPI('private',{readWaitMs:60000,sleep:async()=>assert.fail('must not wait')});
   await assert.rejects(api('/repos/a/b/pulls/1',method,body));assert.equal(calls,1);
  });
 }
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
test('each actual HTTP request requires a complete attempt within the caller deadline', async () => {
  let calls = 0, left = 40_000;
  const api = githubAPI('synthetic', {deadlineRemaining: () => left,
    fetchImpl: async () => {calls++;return new Response('{}');}});
  await api('/repos/a/b');assert.equal(calls, 1);
  left = 20_000;await assert.rejects(api('/repos/a/b'), /deadline/);assert.equal(calls, 1);
  left = 40_000;await api('/repos/a/b');assert.equal(calls, 2);
  left = Infinity;await assert.rejects(api('/repos/a/b'), /Invalid job deadline/);assert.equal(calls, 2);
});
