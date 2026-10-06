import test from 'node:test';
import assert from 'node:assert/strict';
import {assertIssueReadiness,transitionClaim,renderClaim} from '../scripts/issue-claim-contract.mjs';
import {reviewIssueReadiness} from '../scripts/review-issue-readiness.mjs';
const spec={mode:'engineering',scope:'bounded repair',max_prs:1,depends_on:[2]};
const issue=s=>({number:1,state:'open',created_at:'2026-10-01T00:00:00Z',updated_at:'before',labels:['type:engineering','kind:work-item','status:ready'],body:`Acceptance: repair safely\n<!-- worldatlas-work:v1\n${JSON.stringify(s??spec)}\n-->`});
const request={action:'claim',worker_id:'author',claim_id:'claim-aaaaaaaaaaaaaaaa',request_id:'request-aaaaaaaaaaaaaaa',branch:'engineering/repair'};
const deps=[{number:2,state:'closed'}];
test('readiness and claiming reject the same invalid contracts, dependencies, budgets and evidence',()=>{
 for(const change of [x=>x.issue.body='malformed',x=>x.dependencies[0].state='open',x=>x.prs=[{merged_at:'now'}],x=>x.issue=issue({...spec,evidence_quality:{version:1,pins:{bad:'not-a-hash'},subject_ids:[],review_kind:'code',manifest_path:'coordination/engineering/{job}/evidence-quality.json'}})]){
  const x={issue:issue(),dependencies:structuredClone(deps),prs:[],comments:[]};change(x);
  let reason;try{assertIssueReadiness({...x,branch:request.branch,requireReady:false});}catch(e){reason=e.message;}
  assert(reason);assert.throws(()=>transitionClaim({...x,request}),e=>e.message===reason);
 }
});
test('geography ownership rejects both readiness and a new claim without taking over existing work',()=>{
 const geo={...spec,mode:'geography',owned_paths:['data/regional-review/packet/'],depends_on:[]};
 const current={...issue(geo),labels:['type:geography','kind:work-item','status:ready']};
 const other={...current,number:3};const x={issue:current,otherIssues:[other],comments:[]};
 assert.throws(()=>assertIssueReadiness({...x,branch:'geography/repair',requireReady:false}),/ownership conflicts/);
 assert.throws(()=>transitionClaim({...x,request:{...request,branch:'geography/repair'}}),/ownership conflicts/);
});
function fixture({mutate=false,fail=false,claim=false,depOpen=false}={}){
 let reads=0;const value=issue();
 return async route=>{
  const url=new URL('https://example.test'+route);
  if(url.pathname.endsWith('/issues/1'))return {...value,updated_at:mutate&&reads++?'changed':'before'};
  if(url.pathname.endsWith('/issues/2'))return {number:2,state:depOpen?'open':'closed'};
  if(url.pathname.endsWith('/timeline'))return [];
  if(url.pathname.endsWith('/comments')){
   if(fail)throw Error('Incomplete HTTP 403 read');
   return claim?[{id:1,user:{login:'github-actions[bot]'},body:renderClaim({version:1,active:true,worker_id:'other',claim_id:'claim-other-aaaaaaaa',branch:'engineering/other',expires_at:'2026-10-01T00:00:00Z'})}]:[];
  }
  throw Error('Unexpected '+route);
 };
}
test('preflight reviews missing ready but never changes labels, and rejects open dependencies',async()=>{
 const ready=await reviewIssueReadiness({api:fixture(),repo:'owner/repo',number:1});assert.equal(ready.eligible,true);assert.equal(ready.coverage,'complete');
 const bad=await reviewIssueReadiness({api:fixture({depOpen:true}),repo:'owner/repo',number:1});assert.equal(bad.eligible,false);assert.match(bad.findings.join(),/dependency/);
});
test('partial reads, changed snapshots and expired ownership cannot permit maintenance or takeover',async()=>{
 for(const option of [{mutate:true},{fail:true},{claim:true}]){
  const result=await reviewIssueReadiness({api:fixture(option),repo:'owner/repo',number:1});assert.equal(result.eligible,false);
  if(!option.claim)assert.equal(result.coverage,'incomplete');else assert.match(result.findings.join(),/expiry alone/);
 }
});
test('an explicit blocker must be resolved for readiness and claiming; ordinary historical prose is not authority',()=>{
 const x={issue:issue(),dependencies:deps,comments:[{id:1,body:'Old HTTP 403; repaired later'}]};assertIssueReadiness({...x,branch:request.branch});
 x.comments.push({id:2,body:'<!-- worldatlas-blocker:v1\n{"id":"input","active":true,"reason":"Waiting for source"}\n-->'});
 assert.throws(()=>assertIssueReadiness({...x,branch:request.branch}),/Explicit unresolved/);assert.throws(()=>transitionClaim({...x,request}),/Explicit unresolved/);
 x.comments.push({id:3,body:'<!-- worldatlas-blocker:v1\n{"id":"input","active":false,"reason":"Retrieved source"}\n-->'});assertIssueReadiness({...x,branch:request.branch});
});

test('a linked PR merging during preflight cannot leave a complete eligible exhausted issue',async()=>{
 let reads=0;const value=issue({...spec,depends_on:[]});
 const api=async route=>{
  const u=new URL('https://example.test'+route);
  if(u.pathname.endsWith('/issues/1'))return value;
  if(u.pathname.endsWith('/comments'))return [];
  if(u.pathname.endsWith('/timeline'))return [{source:{issue:{number:3,body:'Refs #1',pull_request:{url:'pr'}}}}];
  if(u.pathname.endsWith('/pulls/3'))return {number:3,state:'closed',body:'Refs #1',merged_at:reads++?'now':null};
  throw Error('Unexpected '+route);
 };
 const result=await reviewIssueReadiness({api,repo:'owner/repo',number:1});
 assert.equal(result.coverage,'incomplete');assert.equal(result.eligible,false);assert.match(result.findings.join(),/PR budget/);
});
test('a conflicting geography owner added during preflight cannot be reported eligible',async()=>{
 let lists=0;const geo={...spec,depends_on:[],mode:'geography',owned_paths:['data/regional-review/packet/']};
 const value={...issue(geo),labels:['type:geography','kind:work-item']};
 const api=async route=>{
  const u=new URL('https://example.test'+route);
  if(u.pathname.endsWith('/issues/1'))return value;
  if(u.pathname.endsWith('/comments')||u.pathname.endsWith('/timeline'))return [];
  if(u.pathname.endsWith('/issues'))return lists++?[value,{...value,number:3}]:[value];
  throw Error('Unexpected '+route);
 };
 const result=await reviewIssueReadiness({api,repo:'owner/repo',number:1});
 assert.equal(result.coverage,'incomplete');assert.equal(result.eligible,false);assert.match(result.findings.join(),/ownership changed/);
});


test('narrow geography scopes remain disjoint but conflict with enclosing reservations',()=>{
 const geo={...spec,mode:'geography',depends_on:[],owned_paths:['data/regional-review/packet/nukunonu/']};
 const value={...issue(geo),labels:['type:geography','kind:work-item','status:ready']};
 const other={...value,number:3,body:`<!-- worldatlas-work:v1\n${JSON.stringify({...geo,owned_paths:['data/regional-review/packet/bounty/']})}\n-->`};
 const x={issue:value,otherIssues:[other],comments:[],branch:'geography/repair'};
 assertIssueReadiness(x);transitionClaim({...x,request:{...request,branch:x.branch}});
 other.body=`<!-- worldatlas-work:v1\n${JSON.stringify({...geo,owned_paths:['data/regional-review/packet/']})}\n-->`;
 assert.throws(()=>assertIssueReadiness(x),/ownership conflicts/);assert.throws(()=>transitionClaim({...x,request:{...request,branch:x.branch}}),/ownership conflicts/);
});
