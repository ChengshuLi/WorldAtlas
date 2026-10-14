import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {transitionClaim,readClaim,renderClaim,verifyIssueScope,workSpec,githubPages,canonicalIssueNumber} from '../scripts/issue-claim-contract.mjs';
import {assertResearchImportsReady,assertResearchBundleApproved} from '../scripts/research-import-gate.mjs';

const now=Date.parse('2026-10-02T12:00:00Z');
const spec={max_prs:3,depends_on:[],scope:'A bounded code repair',mode:'engineering'};
const issue=(extra={})=>({number:22,created_at:'2026-10-01T00:00:00Z',state:'open',body:`Scope\n<!-- worldatlas-work:v1\n${JSON.stringify(spec)}\n-->`,labels:['type:engineering','kind:work-item','status:ready'],...extra});
const request=(extra={})=>({action:'claim',worker_id:'thread-a',claim_id:'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',request_id:'rrrrrrrr-rrrr-rrrr-rrrr-rrrrrrrrrrrr',branch:'engineering/repair-a',...extra});
const comment=claim=>({id:101,user:{login:'github-actions[bot]'},body:renderClaim(claim)});
const first=()=>transitionClaim({issue:issue(),comments:[],request:request(),now}).claim;
const next=(extra={})=>({issue:issue(),comments:[comment(first())],request:request({action:'renew',request_id:'ssssssss-ssss-ssss-ssss-ssssssssssss'}),now,...extra});

test('serialized contenders on one issue have exactly one holder even under the same GitHub account',()=>{
 const holder=first();assert.equal(holder.worker_id,'thread-a');
 assert.throws(()=>transitionClaim(next({request:request({worker_id:'thread-b',claim_id:'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',request_id:'tttttttt-tttt-tttt-tttt-tttttttttttt'})})),/another worker/);
 assert.equal(readClaim([comment(holder)]).claim_id,holder.claim_id);
});
test('renewal and release require the actual worker plus ownership nonce',()=>{
 for(const changes of [{worker_id:'thread-b'},{claim_id:'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'}])assert.throws(()=>transitionClaim(next({request:request({action:'renew',request_id:'ssssssss-ssss-ssss-ssss-ssssssssssss',...changes})})),/current holder/);
 const released=transitionClaim(next({request:request({action:'release',request_id:'ssssssss-ssss-ssss-ssss-ssssssssssss'})})).claim;
 assert.equal(released.active,false);
 const reassigned=transitionClaim(next({comments:[comment(released)],request:request({worker_id:'thread-b',claim_id:'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',request_id:'tttttttt-tttt-tttt-tttt-tttttttttttt'})})).claim;
 assert.equal(reassigned.worker_id,'thread-b');
});
test('an idempotent lost-response retry retains original ownership',()=>{
 const original=first(),replayed=transitionClaim(next({request:request(),now:now+1000}));
 assert.equal(replayed.replayed,true);assert.equal(replayed.claim.expires_at,original.expires_at);
});
test('renewal, rotation and reassignment retain one canonical comment ID',()=>{
 const renewed=transitionClaim(next()).claim;
 assert.equal(renewed.comment_id,101);
 const rotated=transitionClaim(next({request:request({action:'renew',request_id:'ssssssss-ssss-ssss-ssss-ssssssssssss',branch:'engineering/part2'})})).claim;
 assert.equal(rotated.comment_id,101);
 const released=transitionClaim(next({request:request({action:'release',request_id:'ssssssss-ssss-ssss-ssss-ssssssssssss'})})).claim;
 const reassigned=transitionClaim(next({comments:[comment(released)],request:request({worker_id:'thread-b',claim_id:'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',request_id:'tttttttt-tttt-tttt-tttt-tttttttttttt'})})).claim;
 assert.equal(reassigned.comment_id,101);
 assert.equal(renderClaim(renewed).includes('comment_id'),false);
});
test('umbrella, blocked, malformed and unresolved dependency scopes cannot be claimed',()=>{
 for(const labels of [['type:engineering','kind:umbrella','status:ready'],['type:engineering','kind:work-item','status:ready','status:blocked'],['type:engineering','kind:work-item']])assert.throws(()=>transitionClaim({issue:issue({labels}),comments:[],request:request(),now}));
 for(const max_prs of [0,-1,1.5,"3",null,Number.MAX_SAFE_INTEGER+1])assert.throws(()=>workSpec(`<!-- worldatlas-work:v1\n${JSON.stringify({...spec,max_prs})}\n-->`));
 assert.throws(()=>transitionClaim({issue:issue({body:`<!-- worldatlas-work:v1\n${JSON.stringify({...spec,depends_on:[7]})}\n-->`}),comments:[],request:request(),dependencies:[{number:7,state:'open'}],now}),/dependency/);
});
test('expired reservations cannot silently discard branches or active PR/live operations',()=>{
 const expired={...first(),expires_at:new Date(now-1).toISOString()},other=request({worker_id:'thread-b',claim_id:'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',request_id:'tttttttt-tttt-tttt-tttt-tttttttttttt'});
 assert.throws(()=>transitionClaim(next({comments:[comment(expired)],request:other})),/recovery/);
 const recover={...other,action:'recover',reason:'Explicitly reviewed stale branch and retained all evidence'};
 const approved=issue({labels:[...issue().labels,'coordination:recovery-approved']});
 assert.throws(()=>transitionClaim(next({issue:approved,comments:[comment(expired)],request:recover,prs:[{state:'open',head:{ref:expired.branch}}]})),/Recovery/);
 assert.throws(()=>transitionClaim(next({issue:approved,comments:[comment({...expired,live_work:true})],request:recover})),/Recovery/);
 assert.equal(transitionClaim(next({issue:approved,comments:[comment(expired)],request:recover})).claim.worker_id,'thread-b');
});
test('multiple PRs retain ownership and rotate branches only after previous work completes',()=>{
 const renew=request({action:'renew',request_id:'ssssssss-ssss-ssss-ssss-ssssssssssss',branch:'engineering/repair-a-part2'});
 assert.throws(()=>transitionClaim(next({request:renew,prs:[{state:'open',head:{ref:'engineering/repair-a'}}]})),/previous PR/);
 const rotated=transitionClaim(next({request:renew,prs:[{state:'closed',merged_at:'2026-10-02',head:{ref:'engineering/repair-a'}}]})).claim;
 assert.equal(rotated.branch,'engineering/repair-a-part2');assert.equal(rotated.claim_id,first().claim_id);
 assert.throws(()=>transitionClaim(next({request:request({action:'release',request_id:renew.request_id}),prs:[{state:'open',head:{ref:'engineering/repair-a'}}]})),/active PR/);
});
test('canonical comments cannot be impersonated or ambiguous',()=>{
 const value=comment(first());assert.equal(readClaim([{...value,user:{login:'human'}}]),null);
 assert.throws(()=>readClaim([value,{...value,id:102}]),/Multiple/);
 assert.throws(()=>readClaim([{...value,body:'**Worker reservation:** worldatlas-claim:v1 malformed'}]),/Malformed/);
});
test('ordinary scope no longer requires a lease, but content imports retain their scientific gate',()=>{
 assert.deepEqual(verifyIssueScope({issue:issue(),branch:'engineering/repair-a'}),{mode:'engineering'});
 assert.deepEqual(verifyIssueScope({issue:issue({labels:['type:engineering']}),branch:'engineering/other'}),{mode:'engineering'});
 assert.throws(()=>verifyIssueScope({issue:issue(),branch:'research/repair-a'}),/type:/);
 const researchIssue=mode=>issue({labels:['type:history-research'],body:`<!-- worldatlas-work:v1\n${JSON.stringify({...spec,mode,geographic_release:'release-2',scope_manifest:'inputs.json',territory_match_review:'Pending evidence'})}\n-->`});
 assert.equal(verifyIssueScope({issue:researchIssue('source-only'),branch:'research/source-a'}).mode,'source-only');
 assert.throws(()=>transitionClaim({issue:researchIssue('source-only'),comments:[],request:request({branch:'research/source-a'}),now}),/only for engineering live/);
 assert.throws(()=>assertResearchImportsReady({version:1,ready_for_location_attributes:false}),/paused/);
 assert.throws(()=>execFileSync(process.execPath,['scripts/import-research-bundle.mjs','https://example.com','unused-bundle'],{stdio:'pipe'}),error=>error.stderr.toString().includes('Research imports are paused'));
});
test('in-scope continuation beyond the estimate claims, rotates and merges under the same ownership rules',()=>{
 const prs=Array.from({length:6},(_,i)=>({number:i+100,state:'closed',merged_at:'2026-10-02',head:{ref:'engineering/previous'}}));
 const held=transitionClaim({issue:issue(),comments:[],request:request(),prs,now}).claim;
 const rotated=transitionClaim(next({comments:[comment(held)],prs,request:request({action:'renew',request_id:'ssssssss-ssss-ssss-ssss-ssssssssssss',branch:'engineering/next'})})).claim;
 assert.equal(rotated.claim_id,held.claim_id);
 assert.equal(verifyIssueScope({issue:issue(),branch:rotated.branch}).mode,'engineering');
 assert.throws(()=>transitionClaim(next({comments:[comment(held)],prs:[...prs,{state:'open',head:{ref:held.branch}}],request:request({action:'renew',request_id:'ssssssss-ssss-ssss-ssss-ssssssssssss',branch:'engineering/next'})})),/previous PR/);
 const larger=issue({body:'<!-- worldatlas-work:v1\n'+JSON.stringify({...spec,max_prs:10})+'\n-->'});
 assert.equal(workSpec(larger.body).max_prs,10);
 assert.equal(transitionClaim({issue:larger,comments:[],request:request(),prs,now}).claim.max_prs,10);
});
test('pagination inspects later pages rather than assuming only the first page exists',async()=>{
 let pages=0;const rows=await githubPages(async()=>{pages++;return pages===1?Array.from({length:100},(_,id)=>({id})):[{id:101}];},'/comments');
 assert.equal(pages,2);assert.equal(rows.length,101);
});

test('claim lock keys use canonical issue numbers so aliases cannot acquire independent locks',()=>{
 assert.equal(canonicalIssueNumber('22'),22);
 for(const value of ['022','2.2e1','+22','22 ','0','9007199254740993',null,undefined])assert.throws(()=>canonicalIssueNumber(value));
});

test('approved research is bound to all three geographic pins and ordinary bot audit text is not authority',()=>{
 const gate={version:1,ready_for_location_attributes:true,semantic_complete:true,approval_evidence:'verified-receipt.json',approved_release:{release_id:'release-2',hierarchy_sha256:'h',footprints_sha256:'f'}};
 assertResearchBundleApproved(gate,{id:'release-2',hierarchy_sha256:'h',footprints_sha256:'f'});
 for(const changed of [{id:'release-3'},{hierarchy_sha256:'other'},{footprints_sha256:'other'}])assert.throws(()=>assertResearchBundleApproved(gate,{id:'release-2',hierarchy_sha256:'h',footprints_sha256:'f',...changed}),/does not match/);
 const ordinary={id:102,user:{login:'github-actions[bot]'},body:'Worker coordination: reason mentions worldatlas-claim:v1'};
 assert.equal(readClaim([comment(first()),ordinary]).worker_id,'thread-a');
});

test('production-only child is reserved by its publisher, not an ordinary implementer',()=>{
 const operationIssue=issue({body:'<!-- worldatlas-work:v1\n'+JSON.stringify({...spec,production_operation:{source_issue:51,queue:714,publisher_worker_id:'publisher-worker'}})+'\n-->'});
 assert.throws(()=>transitionClaim({issue:operationIssue,comments:[],request:request(),now}),/designated publisher/);
 const holder=transitionClaim({issue:operationIssue,comments:[],request:request({worker_id:'publisher-worker'}),now}).claim;
 assert.equal(holder.worker_id,'publisher-worker');
 assert.equal(transitionClaim({issue:operationIssue,comments:[comment(holder)],request:request({worker_id:'publisher-worker',action:'renew',request_id:'ssssssss-ssss-ssss-ssss-ssssssssssss',live_work:true}),now}).claim.live_work,true);
});

test('production child accepts only original-issue or legacy tracking and designated publisher',()=>{
 for(const queue of [51,714,22]){
  const operationIssue=issue({body:'<!-- worldatlas-work:v1\n'+JSON.stringify({...spec,production_operation:{source_issue:51,queue,publisher_worker_id:'publisher-worker'}})+'\n-->'});
  const attempt=()=>transitionClaim({issue:operationIssue,comments:[],request:request({worker_id:'publisher-worker'}),now});
  if(queue===22)assert.throws(attempt,/designated publisher/);else assert.equal(attempt().claim.worker_id,'publisher-worker');
  assert.throws(()=>transitionClaim({issue:operationIssue,comments:[],request:request(),now}),/designated publisher/);
 }
});


test('verified engineering scope carries only safe actual work declarations',()=>{
 const owned_paths=['coordination/engineering/batch/','coordination/engineering/prevention/helper.mjs'];
 const scoped=issue({body:`<!-- worldatlas-work:v1\n${JSON.stringify({...spec,owned_paths})}\n-->`});
 const claim=transitionClaim({issue:scoped,comments:[],request:request(),now}).claim;
 const reservation=verifyIssueScope({issue:scoped,comments:[comment(claim)],branch:claim.branch,now});
 assert.deepEqual(reservation.owned_paths,owned_paths);
 // Existing engineering claims have no stored path array: the matched issue remains authority.
 assert.equal(claim.owned_paths,undefined);
 assert.equal(verifyIssueScope({issue:issue(),comments:[comment(claim)],branch:claim.branch,now}).owned_paths,undefined);
 for(const owned_paths of [['coordination/engineering/'],['coordination/engineering/batch/','coordination/engineering/batch/'],['coordination/engineering/batch/../other/'],['research/geography/a/']])assert.throws(()=>verifyIssueScope({issue:issue({body:`<!-- worldatlas-work:v1\n${JSON.stringify({...spec,owned_paths})}\n-->`}),comments:[comment(claim)],branch:claim.branch,now}));
});

test('live reservation refuses active blockers and can settle historical source-author reservations',()=>{
 const blockers=[{id:1,body:'<!-- worldatlas-blocker:v1\n{"id":"live-stop","active":true,"reason":"Unsettled operation"}\n-->'}];
 assert.throws(()=>transitionClaim({issue:issue(),comments:blockers,request:request(),now}),/live-operation blocker/);
 const held={...first(),mode:'source-only',branch:'research/historical'};
 assert.equal(transitionClaim({issue:issue(),comments:[comment(held)],request:request({action:'release',branch:held.branch,request_id:'ssssssss-ssss-ssss-ssss-ssssssssssss'}),now}).claim.active,false);
});

test('engineering scope carries only the existing validated owned scientific manifest',()=>{
 const quality={version:1,manifest_path:'coordination/engineering/batch/evidence-quality.json',subject_ids:[],pins:{},review_kind:'code'};
 const scoped=(q=quality)=>issue({body:'<!-- worldatlas-work:v1\n'+JSON.stringify({...spec,owned_paths:['coordination/engineering/batch/'],evidence_quality:q})+'\n-->'});
 assert.equal(verifyIssueScope({issue:scoped(),branch:'engineering/repair-a'}).evidence_manifest,quality.manifest_path);
 for(const changes of [{version:2},{manifest_path:'coordination/engineering/foreign/evidence-quality.json'},
   {manifest_path:'coordination/engineering/batch/../evidence-quality.json'},
   {manifest_path:'coordination/engineering/batch/other.json'},{review_kind:'unknown'},{subject_ids:['duplicate','duplicate']}])
  assert.throws(()=>verifyIssueScope({issue:scoped({...quality,...changes}),branch:'engineering/repair-a'}));
 const template=scoped({...quality,manifest_path:'coordination/engineering/{job}/evidence-quality.json'});
 assert.equal(verifyIssueScope({issue:template,branch:'engineering/repair-a'}).evidence_manifest,'coordination/engineering/repair-a/evidence-quality.json');
});
