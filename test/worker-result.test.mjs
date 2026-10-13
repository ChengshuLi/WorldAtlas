import test from 'node:test';
import assert from 'node:assert/strict';
import {renderWorkerResult,readWorkerResult} from '../scripts/worker-result.mjs';

const request={request_id:'request-unique-a',issue_number:26,worker_id:'worker-a',claim_id:'claim-unique-a',branch:'engineering/a',action:'renew'};
const bot=(body,id=1)=>({id,user:{login:'github-actions[bot]'},body});
const result=(extra={})=>({...request,accepted:true,...extra});

test('results are bound to the bot, request and issue, including denial',()=>{
 const comment=bot(renderWorkerResult('claim',result({accepted:false,reason:'Already held'})));
 assert.equal(readWorkerResult([comment],'claim',request.request_id,26).accepted,false);
 assert.equal(readWorkerResult([{...comment,user:{login:'human'}}],'claim',request.request_id,26),null);
 assert.equal(readWorkerResult([comment],'claim','another-request',26),null);
 assert.equal(readWorkerResult([comment],'claim',request.request_id,27),null);
});
test('latest matching response wins, unrelated or malformed comments cannot confer ownership',()=>{
 const early=bot(renderWorkerResult('claim',result()),2);
 const late=bot(renderWorkerResult('claim',result({accepted:false})),3);
 assert.equal(readWorkerResult([late,early],'claim',request.request_id,26).accepted,false);
 assert.equal(readWorkerResult([bot('**Reservation result:** malformed')],'claim',request.request_id,26),null);
});
test('merge responses retain exact PR binding and embedded HTML cannot break the marker',()=>{
 const value={request_id:'merge-a',pr_number:31,accepted:false,reason:'contains <!-- and -->'};
 const body=renderWorkerResult('merge',value);
 assert.equal(readWorkerResult([bot(body)],'merge','merge-a',31).reason,value.reason);
 assert.equal(readWorkerResult([bot(body)],'merge','merge-a',32),null);
 assert.equal(body.includes('contains <!--'),false);
});
