import test from 'node:test';
import assert from 'node:assert/strict';
import {queueBody, registerRequest, scheduleNext, assertAdmission, executionTitle} from '../scripts/merge-scheduler.mjs';
import {readWorkerResult, renderWorkerResult} from '../scripts/worker-result.mjs';
function fixture() {
  let id = 0;
  const prs = [1,2,3,4].map(number => ({number, state:'open', head:{sha: String(number).repeat(40)}}));
  const comments = new Map(prs.map(pr => [pr.number, []])), runs = [], writes = [];
  const api = async (route, method='GET', body) => {
    writes.push({route, method, body});
    if (route.includes('/actions/workflows/worker-merge.yml/runs')) {
      const status = new URLSearchParams(route.split('?')[1]).get('status');
      return {workflow_runs:status?runs.filter(r=>r.status===status):runs};
    }
    if (route.endsWith('/dispatches')) return null;
    if (route.includes('/pulls?')) return prs.filter(pr=>pr.state==='open');
    const pull = /\/pulls\/(\d+)/.exec(route); if(pull)return prs.find(pr=>pr.number===Number(pull[1]));
    const issue = /\/issues\/(\d+)\/comments/.exec(route);
    if (issue) {
      const rows = comments.get(Number(issue[1]));
      if(method==='POST') {const row={id:++id,created_at:'2026-01-01T00:00:00Z',user:{login:'github-actions[bot]'},body:body.body};rows.push(row);return row;}
      return rows;
    }
    throw Error('Unexpected route '+route);
  };
  const request = n => ({pr_number:n, expected_head:String(n).repeat(40), request_id:`durable-request-${n}`});
  const register = n => registerRequest({api,repo:'o/r',request:request(n)});
  const tick = now => scheduleNext({api,repo:'o/r',now:now??Date.parse('2026-01-01T00:00:00Z')});
  const finish = (n, extra={}) => api(`/repos/o/r/issues/${n}/comments`,'POST',{body:renderWorkerResult('merge',{...request(n),accepted:false,status:'not-merged',retryable:false,...extra})});
  return {api,prs,comments,runs,writes,request,register,tick,finish};
}
test('long request holds main admission amid arbitrarily many short arrivals and FIFO progresses', async()=>{
 const f=fixture();await f.register(1);assert.equal((await f.tick()).request_id,'durable-request-1');
 f.runs.push({id:11,status:'in_progress',display_title:executionTitle(f.request(1),1)});
 for(const n of [2,3,4]) {await f.register(n);assert.equal((await f.tick()).status,'live');}
 assert.equal(f.writes.filter(r=>r.route.endsWith('/dispatches')).length,1);
 f.runs[0].status='completed';await f.finish(1,{accepted:true,status:'merged'});
 assert.equal((await f.tick()).request_id,'durable-request-2');
});
test('coalesced scheduler ticks cannot lose FIFO registrations; duplicate request retains ticket',async()=>{
 const f=fixture();const first=await f.register(1);await f.register(2);const duplicate=await f.register(1);
 assert.equal(duplicate.comment_id,first.id);assert.equal(f.comments.get(1).length,1);
 assert.equal((await f.tick()).request_id,'durable-request-1');
 assert.equal((await f.tick()).status,'awaiting-dispatch');
 assert.equal(f.writes.filter(r=>r.route.endsWith('/dispatches')).length,1);
});
test('pending execution cancellation recovers same request and keeps every attempt receipt',async()=>{
 const f=fixture();await f.register(1);await f.register(2);await f.tick();
 f.runs.push({id:11,status:'completed',conclusion:'cancelled',display_title:executionTitle(f.request(1),1)});
 assert.equal((await f.tick()).attempt,2);
 assert.ok(f.comments.get(1).some(c=>c.body.includes('"conclusion":"cancelled"')));
 assert.equal((await f.tick()).status,'awaiting-dispatch');
});
test('observation timeout does not restart live queued/waiting/old executions',async()=>{
 for(const status of ['queued','in_progress','waiting','pending','requested']) {
  const f=fixture();await f.register(1);f.runs.push({id:42,status});
  assert.equal((await f.tick(Date.parse('2030-01-01'))).status,'live');
  assert.equal(f.writes.filter(r=>r.route.endsWith('/dispatches')).length,0);
 }
});
test('changed head and failed tests settle rejected requests and allow next ticket',async()=>{
 const f=fixture();await f.register(1);await f.register(2);f.prs[0].head.sha='a'.repeat(40);
 assert.equal((await f.tick()).request_id,'durable-request-2');
 assert.match(readWorkerResult(f.comments.get(1),'merge',f.request(1).request_id,1).reason,/Head changed/);
 await f.finish(2,{reason:'failed tests'});await f.register(3);assert.equal((await f.tick()).request_id,'durable-request-3');
});
test('authority rejection settles; main advancement retries original ticket without accepting untested tree',async()=>{
 const f=fixture();await f.register(1);await f.register(2);await f.tick();
 f.runs.push({id:11,status:'completed',conclusion:'success',display_title:executionTitle(f.request(1),1)});
 await f.finish(1,{retryable:true,reason:'main advanced; resubmit unchanged head'});
 assert.equal((await f.tick()).request_id,'durable-request-1');
 await f.finish(1,{reason:'authority changed'});assert.equal((await f.tick()).request_id,'durable-request-2');
});
test('admission rejects bypass, duplicate older attempt, and changed exact head',async()=>{
 const f=fixture();await f.register(1);await f.register(2);await f.tick();
 await assertAdmission({api:f.api,repo:'o/r',request:f.request(1),attempt:1,runId:11});
 for(const [request,attempt] of [[f.request(2),1],[f.request(1),2],[{...f.request(1),expected_head:'f'.repeat(40)},1]]) {
  await assert.rejects(assertAdmission({api:f.api,repo:'o/r',request,attempt,runId:11}),/FIFO admission/);
 }
});
test('absent dispatch recovers only after bounded discovery delay, exhaustion is durable',async()=>{
 const f=fixture();await f.register(1);const start=Date.parse('2026-01-01');await f.tick(start);
 assert.equal((await f.tick(start+119999)).status,'awaiting-dispatch');
 assert.equal((await f.tick(start+120000)).attempt,2);assert.equal((await f.tick(start+240000)).attempt,3);
 assert.equal((await f.tick(start+360000)).status,'empty');
 assert.match(readWorkerResult(f.comments.get(1),'merge',f.request(1).request_id,1).reason,/exhausted/);
 assert.equal((await f.tick(start+480000)).status,'empty');
});

test('one tick drains multiple terminal heads in FIFO order and dispatches only the first eligible ticket',async()=>{
 const f=fixture();for(const n of [3,1,2,4])await f.register(n);
 f.prs[2].head.sha='a'.repeat(40);f.prs[0].head.sha='b'.repeat(40);
 assert.equal((await f.tick()).request_id,'durable-request-2');
 const posts=f.writes.filter(r=>r.method==='POST');
 assert.deepEqual(posts.slice(4).map(r=>r.route),[
  '/repos/o/r/issues/3/comments','/repos/o/r/issues/1/comments',
  '/repos/o/r/issues/2/comments','/repos/o/r/actions/workflows/worker-merge.yml/dispatches']);
 assert.equal(f.comments.get(4).length,1);
 assert.equal((await f.tick()).status,'awaiting-dispatch');
 assert.equal(f.writes.filter(r=>r.route.endsWith('/dispatches')).length,1);
});
test('all terminal heads drain to empty without any idle dispatch or repeated terminal receipt',async()=>{
 const f=fixture();for(const n of [1,2]){await f.register(n);f.prs[n-1].head.sha='f'.repeat(40);}
 assert.deepEqual(await f.tick(),{status:'empty'});
 const count=f.writes.filter(r=>r.method==='POST').length;
 assert.deepEqual(await f.tick(),{status:'empty'});
 assert.equal(f.writes.filter(r=>r.method==='POST').length,count);
 assert.equal(f.writes.filter(r=>r.route.endsWith('/dispatches')).length,0);
});
test('exhausted terminal recovery advances the next registered ticket in the same tick',async()=>{
 const f=fixture();await f.register(1);await f.register(2);
 for(let attempt=1;attempt<=3;attempt++){
  assert.equal((await f.tick()).attempt,attempt);
  f.runs.push({id:attempt,status:'completed',conclusion:'cancelled',display_title:executionTitle(f.request(1),attempt)});
 }
 assert.equal((await f.tick()).request_id,'durable-request-2');
 assert.match(readWorkerResult(f.comments.get(1),'merge',f.request(1).request_id,1).reason,/exhausted/);
 assert.equal(f.writes.filter(r=>r.route.endsWith('/dispatches')).length,4);
});
test('a changed head cannot retire a recent ambiguous dispatch and overlap the next ticket',async()=>{
 const f=fixture();await f.register(1);await f.register(2);const start=Date.parse('2026-01-01');await f.tick(start);
 f.prs[0].head.sha='a'.repeat(40);
 assert.equal((await f.tick(start+119999)).status,'awaiting-dispatch');
 assert.equal(readWorkerResult(f.comments.get(1),'merge',f.request(1).request_id,1),null);
 assert.equal(f.writes.filter(r=>r.route.endsWith('/dispatches')).length,1);
 assert.equal((await f.tick(start+120000)).request_id,'durable-request-2');
});
test('every live run state prevents terminal draining as well as a new dispatch',async()=>{
 for(const status of ['queued','in_progress','waiting','pending','requested']){
  const f=fixture();await f.register(1);await f.register(2);f.prs[0].head.sha='a'.repeat(40);
  f.runs.push({id:44,status});const count=f.writes.filter(r=>r.method==='POST').length;
  assert.equal((await f.tick()).status,'live');
  assert.equal(f.writes.filter(r=>r.method==='POST').length,count);
 }
});
test('failed or ambiguous terminal receipt stops the tick before a later dispatch; fresh read reconciles it',async()=>{
 for(const committed of [false,true]){
  const f=fixture();await f.register(1);await f.register(2);f.prs[0].head.sha='a'.repeat(40);let attempts=0;
  const api=async(route,method,body)=>{
   if(method==='POST'){attempts++;if(committed)await f.api(route,method,body);throw Error('uncertain terminal write');}
   return f.api(route,method,body);
  };
  await assert.rejects(scheduleNext({api,repo:'o/r'}),/uncertain terminal write/);
  assert.equal(attempts,1);assert.equal(f.writes.filter(r=>r.route.endsWith('/dispatches')).length,0);
  assert.equal((await f.tick()).request_id,'durable-request-2');
  assert.equal(f.comments.get(1).length,2);
 }
});
test('terminal draining preserves a later durable quota checkpoint without dispatch',async()=>{
 const f=fixture();await f.register(1);await f.register(2);f.prs[0].head.sha='a'.repeat(40);
 await f.finish(2,{retryable:true,quota_retry_at:'2026-01-01T00:05:00.000Z'});
 assert.deepEqual(await f.tick(),{status:'waiting-quota',request_id:'durable-request-2',retry_at:'2026-01-01T00:05:00.000Z'});
 assert.equal(f.writes.filter(r=>r.route.endsWith('/dispatches')).length,0);
});
