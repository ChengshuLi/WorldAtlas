import test from 'node:test';
import assert from 'node:assert/strict';
import {runIssueClaim} from '../scripts/run-issue-claim.mjs';
import {renderClaim} from '../scripts/issue-claim-contract.mjs';
const env={GITHUB_REPOSITORY:'a/b',GITHUB_REF:'refs/heads/main',GH_TOKEN:'fixture-secret'};
const quota=()=>Object.assign(Error('Shared installation limit'),{github:{http_status:403,rate_remaining:'0',rate_reset:'100'}});
const request={action:'release',issue_number:'22',worker_id:'worker-a',branch:'engineering/fixture',claim_id:'c'.repeat(20),request_id:'r'.repeat(20)};
const event={inputs:request};
function fixture({failure,notification=false}={}){
 const calls=[];
 const claim={version:1,active:true,issue_number:22,worker_id:request.worker_id,branch:request.branch,claim_id:request.claim_id,request_id:'old'.repeat(8),expires_at:'2099-01-01T00:00:00Z'};
 const issue={number:22,state:'open',body:'legacy issue',labels:[{name:'status:claimed'}]};
 const factory=(_,{onRequest})=>async(route,method='GET',body)=>{
  calls.push({route,method,body});onRequest({route,method,status:failure&&method==='PATCH'?403:200});
  if(method==='PATCH'&&failure)throw failure;
  if(method==='POST'&&notification&&body.body.startsWith('**Reservation result:**'))throw quota();
  if(method!=='GET')return {id:44};
  if(route==='/repos/a/b/issues/22')return issue;
  if(route.includes('/issues/22/comments'))return [{id:11,user:{login:'github-actions[bot]'},body:renderClaim(claim)}];
  if(route.includes('/issues/22/timeline'))return [];
  throw Error('Unexpected route '+route);
 };
 return {calls,run:()=>runIssueClaim({event,env,apiFactory:factory,wallNow:()=>99000})};
}
test('quota refusal before mutation persists reset, accounts attempts and avoids another doomed notification',async()=>{
 let calls=0;
 const result=await runIssueClaim({event,env,wallNow:()=>99000,apiFactory:(_,{onRequest})=>async route=>{calls++;onRequest({route,method:'GET',status:403});throw quota();}});
 assert.equal(result.accepted,false);assert.equal(result.mutation_attempted,false);
 assert.equal(result.reconcile_required,false);assert.equal(result.notification_deferred,true);
 assert.equal(result.retry_at,'1970-01-01T00:01:41.000Z');assert.equal(result.api_error.rate_remaining,'0');
 assert.equal(result.request_accounting.actual_http_attempts,calls);assert.equal(calls,3);
});
test('denied canonical write cannot be replayed or mistaken for an accepted claim',async()=>{
 const f=fixture({failure:quota()}),result=await f.run();
 assert.equal(result.accepted,false);assert.equal(result.mutation_attempted,true);assert.equal(result.reconcile_required,true);
 assert.equal(result.notification_deferred,true);assert.equal(f.calls.filter(r=>r.method==='PATCH').length,1);
 assert.equal(f.calls.filter(r=>r.method==='POST').length,0);
});
test('ambiguous write is never retried and remains distinguishable from proven quota exhaustion',async()=>{
 const f=fixture({failure:Error('Connection lost after write')}),result=await f.run();
 assert.equal(result.accepted,false);assert.equal(result.reconcile_required,true);assert.equal(result.retryable,false);
 assert.equal(result.api_error,undefined);assert.equal(f.calls.filter(r=>r.method==='PATCH').length,1);
 assert.equal(f.calls.filter(r=>r.method==='POST').length,1);
});
test('successful canonical mutation is preserved when durable confirmation cannot be delivered',async()=>{
 const f=fixture({notification:true}),result=await f.run();
 assert.equal(result.accepted,true);assert.equal(result.claim.active,false);assert.equal(result.reconcile_required,true);
 assert.equal(result.notification_error.api_error.rate_remaining,'0');assert.equal(result.retryable,true);
 assert.equal(f.calls.filter(r=>r.method==='POST').length,2);
});

test('fast parallel quota refusal drains bounded reads before recording actual HTTP attempts',async()=>{
 const {githubAPI}=await import('../scripts/issue-claim-contract.mjs');
 const old=globalThis.fetch;let started=0,completed=0;
 globalThis.fetch=async url=>{
  started++;
  if(!url.endsWith('/issues/22'))await new Promise(resolve=>setTimeout(resolve,30));
  completed++;
  return new Response(url.endsWith('/issues/22')?'{}':'[]',{status:url.endsWith('/issues/22')?403:200,
   headers:{'x-ratelimit-remaining':'0','x-ratelimit-reset':'100'}});
 };
 try{
  const result=await runIssueClaim({event,env,apiFactory:githubAPI,wallNow:()=>99000});
  assert.equal(started,3);assert.equal(completed,started);
  assert.equal(result.request_accounting.actual_http_attempts,started);
  assert.equal(result.notification_deferred,true);assert.equal(result.mutation_attempted,false);
 }finally{globalThis.fetch=old;}
});
