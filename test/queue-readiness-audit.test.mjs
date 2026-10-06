import test from 'node:test';
import assert from 'node:assert/strict';
import {assessIssue,auditQueue,commentBlockers} from '../scripts/queue-readiness-audit.mjs';
import {renderClaim} from '../scripts/issue-claim-contract.mjs';
const spec={max_prs:2,depends_on:[],mode:'engineering',scope:'bounded correction'};
const issue=(number=1,labels=['type:engineering','kind:work-item'],s=spec)=>({number,created_at:'2026-10-01T00:00:00Z',state:'open',labels,body:`<!-- worldatlas-work:v1\n${JSON.stringify(s)}\n-->`});
const codes=r=>r.findings.map(x=>x.code);
test('missing readiness is a review candidate, not permission',()=>{
 assert.deepEqual(codes(assessIssue(issue())),['review-missing-ready']);
 assert(codes(assessIssue(issue(1,['type:engineering','kind:work-item','status:blocked'],{...spec,depends_on:[2]}),{dependencies:[{number:2,state:'closed'}]})).includes('review-blocked'));
 assert(codes(assessIssue(issue(1,['type:engineering','kind:work-item','status:ready'],{...spec,depends_on:[2]}))).includes('ready-blocked'));
});
test('explicit source access blockers survive closed dependencies; prose needs review',()=>{
 const comments=[{id:1,body:'HTTP 403: cannot access original source'}, {id:2,body:'<!-- worldatlas-blocker:v1\n{"id":"source","active":true,"reason":"Original data unavailable"}\n-->'}];
 const result=assessIssue(issue(),{comments});
 assert(codes(result).includes('explicit-blocker'));assert(codes(result).includes('comment-review'));assert(!codes(result).includes('review-missing-ready'));
 assert.equal(commentBlockers([...comments,{id:3,body:'<!-- worldatlas-blocker:v1\n{"id":"source","active":false,"reason":"Recovered and verified"}\n-->'}]).active.length,0);
});
test('unknown lane, invalid prefixes, umbrellas and import approval are separate',()=>{
 assert(codes(assessIssue(issue(1,['type:future','kind:work-item']))).includes('type-label'));
 assert(codes(assessIssue(issue(1,['type:geography','kind:work-item'],{...spec,mode:'geography',owned_paths:['data/core/']}))).includes('invalid-scope'));
 assert.deepEqual(codes(assessIssue(issue(1,['type:engineering','kind:umbrella','status:ready']))),['umbrella-ready']);
 assert(codes(assessIssue(issue(1,['type:history-research','kind:work-item'],{...spec,mode:'content',geographic_release:'r',scope_manifest:'s',territory_match_review:'t'}))).includes('regional-approval-review'));
});
const claim=worker=>({version:1,active:true,worker_id:worker,claim_id:'claim-123456789012',branch:`engineering/${worker}`,expires_at:'2026-10-05T00:00:00Z'});
const comments=worker=>[{id:3,user:{login:'github-actions[bot]'},body:renderClaim(claim(worker))}];
test('same-account workers retain distinct canonical leases and live work constraints',()=>{
 for(const worker of ['worker-a','worker-b']){
  const row=assessIssue(issue(),{comments:comments(worker),now:Date.parse('2026-10-03T00:00:00Z'),prs:[{number:5,state:'open',head:{ref:'engineering/x'}}]});
  assert.equal(row.claim.worker_id,worker);assert(codes(row).includes('active-claim'));assert(codes(row).includes('open-pr'));assert(!codes(row).includes('review-missing-ready'));
 }
 const live=claim('live');live.live_work=true;
 assert(codes(assessIssue(issue(),{comments:[{id:3,user:{login:'github-actions[bot]'},body:renderClaim(live)}],now:Date.parse('2026-10-06T00:00:00Z')})).includes('expired-claim'));
});
function fixture(rows,{fail=false}={}) {
 const calls=[];const api=async(route,method='GET')=>{
  assert.equal(method,'GET'); calls.push(route);
  const url=new URL('https://github.test'+route),page=Number(url.searchParams.get('page')??1);
  if(url.pathname.endsWith('/issues'))return rows.slice((page-1)*100,page*100);
  if(url.pathname.endsWith('/pulls'))return [];
  if(fail && url.pathname.endsWith('/comments'))throw Error('HTTP 403 rate limit');
  if(url.pathname.endsWith('/comments') || url.pathname.endsWith('/timeline'))return [];
  throw Error('Unexpected read '+route);
 };return {api,calls};
}
test('all issue pages and duplicate ownership; checkpoints deduplicate by state',async()=>{
 const rows=Array.from({length:101},(_,i)=>issue(i+1));
 rows[0]=issue(1,['type:geography','kind:work-item'],{...spec,mode:'geography',owned_paths:['data/regional-review/shared/']});rows[100]={...rows[0],number:101};
 const f=fixture(rows),report=await auditQueue({api:f.api,repo:'a/b',now:1000});
 assert.equal(report.status,'complete');assert.equal(report.inspected_issues,101);assert(f.calls.some(x=>x.includes('page=2')));assert(report.findings.some(x=>x.code==='ownership-overlap'));
 const repeat=await auditQueue({api:f.api,repo:'a/b',previous:report,now:2000});assert.equal(repeat.new_findings.length,0);
 rows[1].labels.push('status:ready');const changed=await auditQueue({api:f.api,repo:'a/b',previous:repeat,now:3000});assert.equal(changed.resolved_findings.length,1);
});
test('failed reads preserve checkpoint and never report false resolutions',async()=>{
 const prev={version:1,repository:'a/b',status:'complete',last_successful_coverage:'earlier',findings:[]};
 const f=fixture([issue()],{fail:true}),r=await auditQueue({api:f.api,repo:'a/b',previous:prev});
 assert.equal(r.status,'incomplete');assert.equal(r.last_successful_coverage,'earlier');assert.equal(r.resolved_findings.length,0);
 await assert.rejects(auditQueue({api:f.api,repo:'a/b',previous:{...prev,repository:'wrong/repo'}}),/checkpoint/);
});
