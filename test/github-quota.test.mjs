import test from 'node:test';
import assert from 'node:assert/strict';
import {githubAPI} from '../scripts/issue-claim-contract.mjs';
import {quotaDelay,requestAccounting} from '../scripts/github-quota.mjs';
import {waitForFinalCapacity} from '../scripts/final-capacity.mjs';
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
test('capacity wait honors secondary retry-after before the next actual observation',async()=>{
 let time=0,calls=0;const error=Object.assign(Error('secondary'),{github:{http_status:403,retry_after:'2'}});
 const api=Object.assign(async()=>assert.fail('generic capacity must not be read'),{readRepositoryCapacity:async()=>{if(++calls===1)throw error;return {remaining:500,limit:1000,reset:100};}});
 const row=await waitForFinalCapacity({api,repo:'a/b',required:100,now:()=>time,wallNow:()=>time,sleep:async ms=>{time+=ms;},deadlineMs:10000});assert.equal(time,3000);assert.equal(row.remaining,500);
});
test('quota classifier rejects malformed or irrelevant error metadata',()=>{
 assert.equal(quotaDelay({github:{http_status:404,rate_remaining:'0',rate_reset:'100'}}),null);
 assert.equal(quotaDelay({github:{http_status:403,retry_after:'bogus'}}),null);
});
test('scheduler with real zero capacity neither inventories the queue nor spends a dispatch attempt',async()=>{
 const {scheduleNext}=await import('../scripts/merge-scheduler.mjs');
 const api=Object.assign(async()=>assert.fail('no queue read or write without capacity'),{readRepositoryCapacity:async()=>({remaining:0,limit:1000,reset:100})});
 const result=await scheduleNext({api,repo:'a/b',now:99000});assert.equal(result.status,'waiting-quota');assert.equal(Date.parse(result.retry_at),101000);
});
test('final paid-call allowance covers actual HTTP retries and preserves recovery capacity',async()=>{
 const {finalRequestBudget}=await import('../scripts/final-capacity.mjs');let calls=0,time=99000;
 await mocked(async()=>{calls++;return response(calls===1?403:200,calls===1?'0':'999');},async()=>{
  const raw=githubAPI('private',{readWaitMs:10000,now:()=>time,sleep:async ms=>{time+=ms;}});
  const budget=finalRequestBudget(raw);budget.setLimit(1);
  await assert.rejects(budget.api('/repos/a/b/pulls/1'),error=>error.requestBudget===true&&error.quotaCause?.github?.rate_remaining==='0');
  assert.equal(calls,1);budget.dispose();await raw('/repos/a/b/issues/1/comments','POST',{body:'recovery'});assert.equal(calls,2);
 });
});
test('final deadline is checked before a retry actually sends HTTP',async()=>{
 const {finalRequestBudget}=await import('../scripts/final-capacity.mjs');let calls=0,time=99000;
 await mocked(async()=>{calls++;return response(403);},async()=>{
  const raw=githubAPI('private',{readWaitMs:10000,now:()=>time,sleep:async ms=>{time+=ms;}});
  const budget=finalRequestBudget(raw);budget.setLimit(3);budget.setDeadline(()=>100000-time);
  await assert.rejects(budget.api('/repos/a/b/pulls/1'),/deadline/);assert.equal(calls,1);budget.dispose();
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
