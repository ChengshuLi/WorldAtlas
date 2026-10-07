// Run with Node24 from an owned exact-head review checkout, with no real credentials.
// Native loopback HTTP validates AbortSignal through headers and body consumption.
// Scale the timer to500ms while asserting the production caller requests20000ms.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';
import assert from 'node:assert/strict';
const {runScheduler}=await import(pathToFileURL(path.resolve('scripts/run-merge-scheduler.mjs')));
const workflow=fs.readFileSync('.github/workflows/merge-scheduler.yml','utf8');
const head=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
const epoch=Date.parse('2026-10-07T04:00:00Z');
const request={pr_number:42,expected_head:'c'.repeat(40),request_id:'independent-native-abort-ticket'};
const nativeFetch=globalThis.fetch,nativeTimeout=AbortSignal.timeout;
let mode='headers',calls=[],durable=[],writes=0;
const timers=[];
const delay=(fn,ms)=>timers.push(setTimeout(fn,ms));
const jobs={total_count:1,jobs:[{id:99,name:'register',run_id:777,run_attempt:2,status:'in_progress',started_at:new Date(epoch).toISOString()}]};
const server=http.createServer((req,res)=>{
 if(req.method==='POST'){
  let body='';req.on('data',b=>body+=b);req.on('end',()=>{
   writes++;durable.push({id:1,user:{login:'github-actions[bot]'},body:JSON.parse(body).body});
   res.writeHead(201,{'content-type':'application/json'});res.write('{"id":');
   delay(()=>{if(!res.destroyed)res.end('1}');},2000);
  });return;
 }
 if(mode==='headers'){
  delay(()=>{if(!res.destroyed){res.writeHead(200,{'content-type':'application/json'});res.end('{}');}},2000);return;
 }
 const isJobs=req.url.includes('/jobs?');
 if(mode==='metadata-body'||mode==='pull-body'&&!isJobs){
  res.writeHead(200,{'content-type':'application/json'});res.write('{"slow":');
  delay(()=>{if(!res.destroyed)res.end('true}');},2000);return;
 }
 const payload=isJobs?jobs:req.url.includes('/pulls/42')?{number:42,state:'open',head:{sha:request.expected_head}}:req.url.includes('/comments?')?durable:undefined;
 assert.notEqual(payload,undefined,'Unexpected local route');
 res.writeHead(200,{'content-type':'application/json'});res.end(JSON.stringify(payload));
});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const origin=`http://127.0.0.1:${server.address().port}`;
try{
 AbortSignal.timeout=ms=>{assert.equal(ms,20000);return nativeTimeout(500);};
 globalThis.fetch=(url,opt)=>{
  const u=new URL(url);assert.equal(u.origin,'https://api.github.com');
  assert.equal(opt.headers.Authorization,'Bearer synthetic-native-review');
  calls.push({method:opt.method,path:u.pathname});
  return nativeFetch(origin+u.pathname+u.search,{method:opt.method,body:opt.body,signal:opt.signal});
 };
 const options={event:{inputs:request},workflow,env:{GH_TOKEN:'synthetic-native-review',GITHUB_REF:'refs/heads/main',GITHUB_REPOSITORY:'review/fixture',GITHUB_RUN_ID:'777',GITHUB_RUN_ATTEMPT:'2',GITHUB_JOB:'register',QUEUE_PHASE:'register',GITHUB_WORKFLOW_SHA:head,GITHUB_WORKFLOW_REF:'review/fixture/.github/workflows/merge-scheduler.yml@refs/heads/main'},wallNow:()=>epoch+10000,monotonicNow:()=>10000};
 for(mode of['headers','metadata-body','pull-body']){
  calls=[];const execution=await runScheduler(options);
  assert.equal(execution.failed,true);assert.equal(execution.result.retryable,false);
  assert.equal(calls.filter(c=>c.method==='POST').length,0);
  assert.equal(execution.request_accounting.actual_http_attempts,calls.length);
  assert.equal(calls.length,mode==='pull-body'?2:1);
  console.log({native_http_boundary:mode,refused:true,attempts:calls.length});
 }
 // The server really persists the POST before aborting its successful201 body.
 mode='persisted-write';calls=[];
 const first=await runScheduler(options);
 assert.equal(first.failed,true);assert.equal(first.result.retryable,false);
 assert.equal(first.request_accounting.actual_http_attempts,4);
 assert.equal(writes,1);assert.equal(durable.length,1);
 assert.equal(first.result.request_id,request.request_id);
 const replay=await runScheduler(options);
 assert.equal(replay.failed,false);assert.equal(replay.result.request_id,request.request_id);
 assert.equal(replay.request_accounting.actual_http_attempts,3);
 assert.equal(writes,1);assert.equal(calls.length,7);
 assert.equal(replay.job_deadline.workflow_commit,head);
 console.log({persisted_POST201_aborted_body:true,same_ticket_replay:true,posts:writes,http_attempts:calls.length,controls:5,head});
}finally{
 globalThis.fetch=nativeFetch;AbortSignal.timeout=nativeTimeout;
 for(const timer of timers)clearTimeout(timer);
 server.closeAllConnections();await new Promise(r=>server.close(r));
}
