import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {transitionClaim,readClaim,renderClaim,verifyClaimForPR,workSpec,githubPages,canonicalIssueNumber} from '../scripts/issue-claim-contract.mjs';
import {assertResearchImportsReady,assertResearchBundleApproved} from '../scripts/research-import-gate.mjs';

const now=Date.parse('2026-10-02T12:00:00Z');
const spec={max_prs:3,depends_on:[],scope:'A bounded code repair',mode:'engineering'};
const issue=(extra={})=>({number:22,state:'open',body:`Scope\n<!-- worldatlas-work:v1\n${JSON.stringify(spec)}\n-->`,labels:['type:engineering','kind:work-item','status:ready'],...extra});
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
test('umbrella, blocked, oversized and unresolved dependency scopes cannot be claimed',()=>{
 for(const labels of [['type:engineering','kind:umbrella','status:ready'],['type:engineering','kind:work-item','status:ready','status:blocked'],['type:engineering','kind:work-item']])assert.throws(()=>transitionClaim({issue:issue({labels}),comments:[],request:request(),now}));
 for(const max_prs of [0,4,30])assert.throws(()=>workSpec(`<!-- worldatlas-work:v1\n${JSON.stringify({...spec,max_prs})}\n-->`));
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
test('PR validation uses current exact-branch ownership and rejects expired or blocked claims',()=>{
 verifyClaimForPR({issue:issue(),comments:[comment(first())],branch:'engineering/repair-a',now});
 assert.throws(()=>verifyClaimForPR({issue:issue(),comments:[comment(first())],branch:'engineering/repair-b',now}),/exact branch/);
 assert.throws(()=>verifyClaimForPR({issue:issue(),comments:[comment(first())],branch:'engineering/repair-a',now:now+86400001}),/unexpired/);
 assert.throws(()=>verifyClaimForPR({issue:issue({labels:[...issue().labels,'status:blocked']}),comments:[comment(first())],branch:'engineering/repair-a',now}),/not ready/);
});
test('location-content claims wait for worldwide approval while source-only work can start',()=>{
 const researchIssue=mode=>issue({labels:['type:history-research','kind:work-item','status:ready'],body:`<!-- worldatlas-work:v1\n${JSON.stringify({...spec,mode,geographic_release:'release-2',scope_manifest:'inputs.json',territory_match_review:'Pending evidence'})}\n-->`});
 const researchRequest=request({branch:'research/source-a'});
 assert.equal(transitionClaim({issue:researchIssue('source-only'),comments:[],request:researchRequest,now}).claim.mode,'source-only');
 assert.throws(()=>transitionClaim({issue:researchIssue('content'),comments:[],request:researchRequest,dependencies:[{number:7,state:'closed'}],geographyGate:{ready_for_location_attributes:false},now}),/Worldwide hierarchy approval/);
 assert.throws(()=>assertResearchImportsReady({version:1,ready_for_location_attributes:false}),/paused/);
 assert.throws(()=>execFileSync(process.execPath,['scripts/import-research-bundle.mjs','https://example.com','unused-bundle'],{stdio:'pipe'}),error=>error.stderr.toString().includes('Research imports are paused'));
});
test('the PR budget cannot be bypassed by claiming another part indefinitely',()=>{
 assert.throws(()=>transitionClaim({issue:issue(),comments:[],request:request(),prs:[{merged_at:'a'},{merged_at:'b'},{merged_at:'c'}],now}),/budget exhausted/);
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
