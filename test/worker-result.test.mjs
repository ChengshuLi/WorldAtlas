import test from 'node:test';
import assert from 'node:assert/strict';
import {renderClaim} from '../scripts/issue-claim-contract.mjs';
import {renderWorkerResult,readWorkerResult,confirmReservation} from '../scripts/worker-result.mjs';

const request={request_id:'request-unique-a',issue_number:26,worker_id:'worker-a',claim_id:'claim-unique-a',branch:'engineering/a',action:'renew'};
const claim={...request,version:1,active:true,expires_at:'2026-10-03T12:00:00Z'};
const now=Date.parse('2026-10-02T12:00:00Z');
const bot=(body,id=1)=>({id,user:{login:'github-actions[bot]'},body});
const canonical=value=>bot(renderClaim(value));
const result=(extra={})=>({...request,accepted:true,...extra});

test('results are bound to the bot, request and issue, including denial',()=>{
 const comment=bot(renderWorkerResult('claim',result({accepted:false,reason:'Already held'})));
 assert.equal(readWorkerResult([comment],'claim',request.request_id,26).accepted,false);
 assert.equal(readWorkerResult([{...comment,user:{login:'human'}}],'claim',request.request_id,26),null);
 assert.equal(readWorkerResult([comment],'claim','another-request',26),null);
 assert.equal(readWorkerResult([comment],'claim',request.request_id,27),null);
 assert.equal(confirmReservation([comment],request,now).reason,'Already held');
});
test('latest matching response wins, unrelated or malformed comments cannot confer ownership',()=>{
 const early=bot(renderWorkerResult('claim',result()),2);
 const late=bot(renderWorkerResult('claim',result({accepted:false})),3);
 assert.equal(readWorkerResult([late,early],'claim',request.request_id,26).accepted,false);
 assert.equal(readWorkerResult([bot('**Reservation result:** malformed')],'claim',request.request_id,26),null);
});
test('positive confirmations require current exact canonical ownership, not stale success',()=>{
 const comment=bot(renderWorkerResult('claim',result()),2);
 assert.equal(confirmReservation([canonical(claim),comment],request,now).result_source,'github-comment');
 for(const changes of [{request_id:'new-request'},{active:false},{branch:'engineering/b'},{worker_id:'worker-b'},{claim_id:'another-claim'},{expires_at:'2026-10-01T12:00:00Z'}])assert.throws(()=>confirmReservation([canonical({...claim,...changes}),comment],request,now),/not confirmed/);
});
test('bootstrap fallback requires exact request and releases require inactive state',()=>{
 assert.equal(confirmReservation([canonical(claim)],request,now).result_source,'canonical-comment');
 assert.throws(()=>confirmReservation([canonical({...claim,request_id:'older-request'})],request,now),/not confirmed/);
 assert.throws(()=>confirmReservation([],request,now),/not confirmed/);
 assert.equal(confirmReservation([canonical({...claim,active:false})],{...request,action:'release'},now).claim.active,false);
 assert.throws(()=>confirmReservation([canonical(claim)],{...request,action:'release'},now),/not confirmed/);
});
test('merge responses retain exact PR binding and embedded HTML cannot break the marker',()=>{
 const value={request_id:'merge-a',pr_number:31,accepted:false,reason:'contains <!-- and -->'};
 const body=renderWorkerResult('merge',value);
 assert.equal(readWorkerResult([bot(body)],'merge','merge-a',31).reason,value.reason);
 assert.equal(readWorkerResult([bot(body)],'merge','merge-a',32),null);
 assert.equal(body.includes('contains <!--'),false);
});
