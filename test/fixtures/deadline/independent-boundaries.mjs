// Run with Node24 from an owned exact-head review checkout, in an empty environment.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';
import assert from 'node:assert/strict';
const {runScheduler}=await import(pathToFileURL(path.resolve('scripts/run-merge-scheduler.mjs')));
const {queueBody}=await import(pathToFileURL(path.resolve('scripts/merge-scheduler.mjs')));
const head=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
const epoch=Date.parse('2026-10-07T04:00:00Z');
const workflow=fs.readFileSync('.github/workflows/merge-scheduler.yml','utf8');
const request={pr_number:42,expected_head:'b'.repeat(40),request_id:'independent-deadline-review-ticket'};
const baseEnv={GH_TOKEN:'synthetic-review',GITHUB_REF:'refs/heads/main',GITHUB_REPOSITORY:'review/fixture',GITHUB_RUN_ID:'777',GITHUB_RUN_ATTEMPT:'2',GITHUB_JOB:'register',QUEUE_PHASE:'register',GITHUB_WORKFLOW_SHA:head,GITHUB_WORKFLOW_REF:'review/fixture/.github/workflows/merge-scheduler.yml@refs/heads/main'};
let controls=0;
async function fixture({elapsed=0,metadata=0,envEdit={},jobsEdit=x=>x,readBody=0,quota=null,paged=false,ambiguous=false,replay=false,phase='register',recover=false,workflowBytes=workflow}={}){
 let time=elapsed,first=true;
 const calls=[],waits=[],writes=[],original=globalThis.fetch;
 const env={...baseEnv,GITHUB_JOB:phase,QUEUE_PHASE:phase,...envEdit};
 const job={id:919,name:phase,run_id:777,run_attempt:2,status:'in_progress',started_at:new Date(epoch).toISOString()};
 const durable=()=>({id:12,user:{login:'github-actions[bot]'},body:queueBody({...request,kind:'request'})});
 const json=(payload,status=200,headers={})=>new Response(JSON.stringify(payload),{status,headers});
 globalThis.fetch=async(url,opt)=>{
  const p=new URL(url).pathname;
  calls.push({p,method:opt.method,at:time});
  assert.equal(opt.headers.Authorization,'Bearer synthetic-review');
  if(p.endsWith('/attempts/2/jobs')){time+=metadata;return json(jobsEdit({total_count:1,jobs:[job]}));}
  if(phase==='schedule'&&p==='/repos/review/fixture')return json({},200,{'x-ratelimit-resource':'core','x-ratelimit-limit':'1000','x-ratelimit-remaining':'999','x-ratelimit-reset':String((epoch+600000)/1000)});
  if(opt.method==='POST'){writes.push(JSON.parse(opt.body));if(ambiguous)throw Error('write outcome unknown');return json({id:13},201);}
  if(p==='/repos/review/fixture/pulls/42'){
   if(quota&&first){first=false;const r=json({},403,{'retry-after':String(quota)});const raw=r.json.bind(r);r.json=async()=>{time+=readBody;return raw();};return r;}
   return json({number:42,state:'open',head:{sha:request.expected_head}});
  }
  if(p==='/repos/review/fixture/pulls'){
   if(first&&recover){first=false;return json({},429,{'retry-after':'2'});}
   return json([{number:42,state:'open',head:{sha:request.expected_head}}]);
  }
  if(p.endsWith('/comments')){
   if(paged){time+=11000;return json(Array.from({length:100},(_,i)=>({id:i+1,user:{login:'someone'},body:'ordinary comment'})));}
   const comments=replay||recover?[durable()]:[];
   if(recover)comments.push({id:13,user:{login:'github-actions[bot]'},body:queueBody({...request,kind:'dispatch',attempt:1,dispatched_at:new Date(epoch+elapsed-119000).toISOString()})});
   return json(comments);
  }
  if(p.endsWith('/actions/workflows/worker-merge.yml/runs'))return json({workflow_runs:[]});
  throw Error('Unexpected fixture route '+p);
 };
 try{
  const execution=await runScheduler({event:{inputs:request},workflow:workflowBytes,env,wallNow:()=>epoch+time,monotonicNow:()=>time,sleep:async ms=>{waits.push(ms);time+=ms;}});
  assert.equal(execution.request_accounting.actual_http_attempts,calls.length);
  return{execution,calls,waits,writes,time};
 }finally{globalThis.fetch=original;}
}
for(const envEdit of[{GITHUB_JOB:'schedule'},{GITHUB_RUN_ATTEMPT:'02'},{GITHUB_RUN_ID:'9007199254740992'},{GITHUB_REF:'refs/pull/42/merge'}]){
 const x=await fixture({envEdit});assert.equal(x.execution.failed,true);assert.equal(x.calls.length,0);controls++;
}
for(const jobsEdit of[x=>({...x,jobs:[{...x.jobs[0],run_attempt:1}]}),x=>({total_count:2,jobs:[x.jobs[0],{...x.jobs[0],name:'schedule'}]}),x=>({...x,jobs:[{...x.jobs[0],started_at:'2026-10-07T04:00:00+00:00'}]})]){
 const x=await fixture({jobsEdit});assert.equal(x.execution.failed,true);assert.equal(x.calls.length,1);controls++;
}
const edge=await fixture({elapsed:249999,metadata:1});assert.equal(edge.execution.failed,true);assert.equal(edge.calls.length,1);assert.equal(edge.writes.length,0);controls++;
const pages=await fixture({elapsed:240000,paged:true});assert.equal(pages.execution.failed,true);assert.equal(pages.calls.length,3);assert.equal(pages.writes.length,0);controls++;
const equal=await fixture({elapsed:230000,quota:19});assert.deepEqual(equal.waits,[]);assert.equal(equal.execution.result.job_deadline_exhausted,true);controls++;
const body=await fixture({elapsed:230000,quota:9,readBody:11000});assert.deepEqual(body.waits,[]);assert.equal(body.writes.length,0);controls++;
const short=await fixture({elapsed:230000,quota:18});assert.deepEqual(short.waits,[19000]);assert.equal(short.execution.failed,false);assert.equal(short.time,249000);assert.equal(short.writes.length,1);assert.equal(short.execution.job_deadline.workflow_commit,head);controls++;
const uncertain=await fixture({ambiguous:true});assert.equal(uncertain.writes.length,1);assert.equal(uncertain.execution.failed,true);assert.equal(uncertain.execution.result.retryable,false);assert.equal(uncertain.execution.result.request_id,request.request_id);controls++;
const replay=await fixture({replay:true});assert.equal(replay.execution.failed,false);assert.equal(replay.writes.length,0);controls++;
const recovery=await fixture({phase:'schedule',elapsed:10000,recover:true});assert.deepEqual(recovery.waits,[3000]);assert.equal(recovery.execution.result.attempt,2);assert.equal(recovery.execution.result.status,'dispatched');const row=JSON.parse(recovery.writes[0].body.match(/<!-- worldatlas-merge-queue:v1\n([\s\S]*?)\n-->/)[1]);assert.equal(row.dispatched_at,new Date(epoch+13000).toISOString());assert.equal(row.attempt,2);controls++;
// Retain the original old-workflow/new-checkout scenario; no HTTP may be sent now.
const originalDrift=await fixture({elapsed:10000,envEdit:{GITHUB_WORKFLOW_SHA:'2237a4518d684ad7ec9f3e8a9ccd4209e815e283'},workflowBytes:workflow.replace('timeout-minutes: 5','timeout-minutes: 10'),quota:180});assert.equal(originalDrift.execution.failed,true);assert.equal(originalDrift.calls.length,0);assert.equal(originalDrift.writes.length,0);controls++;
// Matching real checkout plus divergent supplied bytes also refuses, proving byte authentication.
const byteDrift=await fixture({workflowBytes:workflow.replace('timeout-minutes: 5','timeout-minutes: 10')});assert.equal(byteDrift.execution.failed,true);assert.match(byteDrift.execution.result.reason,/bytes differ/);assert.equal(byteDrift.calls.length,0);controls++;
for(const GITHUB_WORKFLOW_REF of['other/fixture/.github/workflows/merge-scheduler.yml@refs/heads/main','review/fixture/.github/workflows/other.yml@refs/heads/main','review/fixture/.github/workflows/merge-scheduler.yml@refs/tags/main']){
 const x=await fixture({envEdit:{GITHUB_WORKFLOW_REF}});assert.equal(x.execution.failed,true);assert.equal(x.calls.length,0);controls++;
}
console.log({independent_entrypoint_controls:controls,head,status:'passed'});
