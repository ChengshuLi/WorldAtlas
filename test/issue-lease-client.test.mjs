import test from 'node:test';
import assert from 'node:assert/strict';
import {observeIssueLease} from '../scripts/issue-lease-client.mjs';
import {renderClaim} from '../scripts/issue-claim-contract.mjs';
import {renderWorkerResult} from '../scripts/worker-result.mjs';
const request={action:'renew',issue_number:26,worker_id:'worker-a',branch:'engineering/a',claim_id:'claim-unique-aaaa',request_id:'request-unique-aaaa'};
const origin=Date.parse('2026-10-09T02:00:00Z');
const canonical=(extra={})=>({id:1,user:{login:'github-actions[bot]'},body:renderClaim({...request,version:1,active:true,expires_at:'2026-10-10T02:00:00Z',...extra})});
const receipt=(extra={})=>({id:2,user:{login:'github-actions[bot]'},body:renderWorkerResult('claim',{...request,accepted:true,...extra})});
const run=(status='queued',conclusion=null)=>({id:55,display_title:`renew #26 ${request.request_id}`,status,conclusion});
const clock=()=>{let time=origin;return {now:()=>time,sleep:async ms=>{time+=ms;}};};

test('durable accepted result needs the current exact canonical claim and one bounded observation',async()=>{
 let submitted=0,reads=0;const checkpoints=[];
 const result=await observeIssueLease({repo:'a/b',request,...clock(),submit:async()=>{submitted++;},checkpoint:r=>checkpoints.push(r),api:async()=>{reads++;return [canonical(),receipt()];}});
 assert.equal(result.accepted,true);assert.equal(reads,1);assert.equal(submitted,1);
 assert(checkpoints.some(x=>x.submission_uncertain));assert.equal(checkpoints.at(-1).accepted,true);
});
test('queued execution is discovered beyond the newest hundred and then observed by exact ID',async()=>{
 let comments=0,submitted=0;const routes=[];
 const result=await observeIssueLease({repo:'a/b',request,...clock(),submit:async()=>{submitted++;},api:async route=>{
  routes.push(route);
  if(route.includes('/comments'))return ++comments===1?[]:[canonical(),receipt()];
  if(route.endsWith('page=1'))return {workflow_runs:Array.from({length:100},(_,i)=>({...run(),id:100+i,display_title:'another request'}))};
  if(route.endsWith('page=2'))return {workflow_runs:[run()]};
  if(route.endsWith('/actions/runs/55'))return run('waiting');
  assert.fail(route);
 }});
 assert.equal(result.accepted,true);assert.equal(submitted,1);assert(routes.some(x=>x.endsWith('page=2')));
 assert.equal(routes.filter(x=>x.includes('workflows/issue-claims')).length,2);
});
test('a partial canonical mutation and terminal cancelled execution never authorize work or redispatch',async()=>{
 let submitted=0;
 const result=await observeIssueLease({repo:'a/b',request,...clock(),submit:async()=>{submitted++;},api:async route=>{
  if(route.includes('/comments'))return [canonical()];
  if(route.includes('workflows/issue-claims'))return {workflow_runs:[run()]};
  return run('completed','cancelled');
 }});
 assert.equal(result.accepted,false);assert.equal(result.execution_conclusion,'cancelled');assert.equal(result.submitted,true);assert.equal(submitted,1);
 let repeated=0;
 await observeIssueLease({repo:'a/b',request,...clock(),resuming:true,submit:async()=>{repeated++;},api:async route=>route.includes('/comments')?[canonical()]:route.includes('workflows/')?{workflow_runs:[run()]}:run('completed','cancelled')});
 assert.equal(repeated,0);
});
test('uncertain dispatch response is reconciled through the same durable result without a second write',async()=>{
 let submitted=0;
 const result=await observeIssueLease({repo:'a/b',request,...clock(),submit:async()=>{submitted++;throw Error('lost response');},api:async()=>[canonical(),receipt()]});
 assert.equal(result.accepted,true);assert.equal(submitted,1);
});
test('long queued observation expires with the same request and bounded read count',async()=>{
 const timing=clock();let submitted=0,reads=0;
 const result=await observeIssueLease({repo:'a/b',request,...timing,submit:async()=>{submitted++;},api:async route=>{
  reads++;if(route.includes('/comments'))return [];
  if(route.includes('workflows/'))return {workflow_runs:[run()]};return run('queued');
 }});
 assert.equal(result.status,'pending');assert.equal(result.request_id,request.request_id);assert.equal(submitted,1);assert(reads<=12);assert(timing.now()-origin<=240000);
});
test('server rejection and pre-HTTP quota refusal do not fabricate an accepted or ambiguous dispatch',async()=>{
 for(const error of [Object.assign(Error('not admitted'),{quotaAdmission:{resource:'core',limit:1000,remaining:16,reset:Math.ceil(origin/1000)+3600,minimum_remaining:16}}),Object.assign(Error('permission'),{github:{http_status:403,rate_remaining:'99'}})]){
  const result=await observeIssueLease({repo:'a/b',request,...clock(),submit:async()=>{throw error;},api:async()=>assert.fail('known rejected submission has no execution')});
  assert.equal(result.accepted,false);assert.equal(result.submitted,false);assert.equal(result.submission_uncertain,undefined);
 }
});
test('changed canonical ownership and counterfeit results cannot confirm an old accepted request',async()=>{
 const result=await observeIssueLease({repo:'a/b',request,...clock(),resuming:true,submit:async()=>assert.fail(),api:async()=>[canonical({worker_id:'another-worker'}),receipt()]});
 assert.equal(result.accepted,false);assert.match(result.reason,/not confirmed/);
});
test('a temporary observation failure preserves the checkpoint without declaring execution terminal',async()=>{
 const result=await observeIssueLease({repo:'a/b',request,...clock(),resuming:true,submit:async()=>assert.fail(),api:async()=>{throw Error('service unavailable');}});
 assert.equal(result.status,'pending');assert.equal(result.submitted,true);assert.equal(result.execution_conclusion,undefined);
});
