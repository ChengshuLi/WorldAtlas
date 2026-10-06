import test from 'node:test';
import assert from 'node:assert/strict';
import {readQueueDisposition,scopeDigest} from '../scripts/queue-disposition.mjs';
import {checkBudgetHandoff} from '../scripts/queue-budget-handoff.mjs';
import {assessIssue} from '../scripts/queue-readiness-audit.mjs';
import {flagOriginalIssues,triageLabel} from '../scripts/queue-triage-flags.mjs';
import {createHash} from 'node:crypto';
import {reconcileQueueEvent} from '../scripts/queue-readiness-event.mjs';

const repo='a/b';
const scope={max_prs:1,depends_on:[],mode:'engineering',scope:'bounded test'};
const issue={number:1,created_at:'2020-01-01T00:00:00Z',state:'open',labels:['kind:work-item','type:engineering'],body:`<!-- worldatlas-work:v1\n${JSON.stringify(scope)}\n-->`};
test('failed release, unmerged PR and flag projection never refresh the queue; merge confirmation is mandatory',async()=>{
 const noAPI=async()=>{throw Error('Unexpected API call');};
 for(const args of [
  {kind:'claim',event:{inputs:{action:'release'}},result:{accepted:false}},
  {kind:'merge',event:{},result:{accepted:false}},
  {kind:'pull_request_target',event:{action:'closed',pull_request:{merged:false}}},
  {kind:'issues',event:{label:{name:triageLabel}}},
  {kind:'issue_comment',event:{issue:{pull_request:{}}}},
 ])assert((await reconcileQueueEvent({api:noAPI,repo,...args})).skipped);
 await assert.rejects(reconcileQueueEvent({api:async()=>({merged_at:'date',merge_commit_sha:'a',head:{sha:'different'}}),repo,kind:'merge',event:{inputs:{expected_head:'expected'}},result:{accepted:true,status:'merged',pr_number:10}}),/not confirmed/);
});
test('attention flags touch only their own label, deduplicate and retain partial coverage',async()=>{
 let current={...issue,updated_at:'2026-10-06T20:00:00Z',labels:[...issue.labels,'status:claimed']};
 const snapshot=()=>({number:1,updated_at:current.updated_at,body_sha256:createHash('sha256').update(JSON.stringify(current.body)).digest('hex'),labels:current.labels.filter(label=>label!==triageLabel).sort(),triage_present:current.labels.includes(triageLabel)});
 const mutations=[];
 const api=async(route,method='GET',body)=>{
  if(method==='POST'){assert.deepEqual(body,{labels:[triageLabel]});current.labels.push(triageLabel);mutations.push(method);}
  else if(method==='DELETE'){assert(route.endsWith(encodeURIComponent(triageLabel)));current.labels=current.labels.filter(label=>label!==triageLabel);mutations.push(method);}
  else assert.equal(method,'GET');
  return current;
 };
 const report={version:1,repository:repo,status:'complete',findings:[{issue:1,code:'invalid-evidence-contract'}],issue_snapshots:[snapshot()]};
 assert.deepEqual((await flagOriginalIssues({api,repo,report})).added,[1]);
 report.issue_snapshots=[snapshot()];await flagOriginalIssues({api,repo,report});assert.equal(mutations.length,1);
 report.findings=[];report.status='incomplete';await flagOriginalIssues({api,repo,report});assert(current.labels.includes(triageLabel));
 report.status='complete';current.body+='changed';assert.deepEqual((await flagOriginalIssues({api,repo,report})).changed_since_audit,[1]);
 report.issue_snapshots=[snapshot()];assert.deepEqual((await flagOriginalIssues({api,repo,report})).removed,[1]);
 assert(current.labels.includes('status:claimed'));
});
test('evidence declaration is audited; symbolic SHA pins remain valid',()=>{
 const quality={version:1,subject_ids:[],pins:{baseline:'a'.repeat(64)},review_kind:'code',manifest_path:'coordination/engineering/{job}/evidence-quality.json'};
 const current={...issue,created_at:'2026-10-06T00:00:00Z',body:`<!-- worldatlas-work:v1\n${JSON.stringify({...scope,evidence_quality:quality})}\n-->`};
 assert(!assessIssue(current).findings.some(row=>row.code==='invalid-evidence-contract'));
 quality.pins.baseline={sha256:'a'.repeat(64)};
 current.body=`<!-- worldatlas-work:v1\n${JSON.stringify({...scope,evidence_quality:quality})}\n-->`;
 assert(assessIssue(current).findings.some(row=>row.code==='invalid-evidence-contract'));
});
const disposition={version:1,issue:1,scope_sha256:scopeDigest(scope),merged_prs:[10],criteria:[{criterion:'Original acceptance',status:'remaining',evidence:['https://github.com/a/b/pull/10'],follow_up_issues:[2]}]};
const marker=value=>`<!-- worldatlas-queue-disposition:v1\n${JSON.stringify(value)}\n-->`;
test('disposition rejects stale scope/PR state, PR follow-ups and newer malformed receipts',()=>{
 const args={issue,scope,prs:[{number:10,merged_at:'date'}],relatedIssues:[{...issue,number:2}]};
 assert(readQueueDisposition([{id:1,body:marker(disposition)}],args).value);
 assert(readQueueDisposition([{id:1,body:marker(disposition)}],{...args,scope:{...scope,scope:'expanded'}}).error);
 assert(readQueueDisposition([{id:1,body:marker(disposition)}],{...args,prs:[]}).error);
 assert(readQueueDisposition([{id:1,body:marker(disposition)}],{...args,relatedIssues:[{number:2,pull_request:{}}]}).error);
 assert(readQueueDisposition([{id:1,body:marker(disposition)},{id:2,body:marker({})}],args).error);
});
test('new last partial PR must retain a real bounded handoff, including resolved children',async()=>{
 const policy={repository:repo,handoff_activation_time:'2026-10-06T00:00:00Z'};
 const current={...issue,created_at:'2026-10-06T01:00:00Z'};
 const pr={number:10,body:'Refs #1\n'};
 const args={api:async()=>({...issue,number:2}),repo,issue:current,pr,prs:[],policy};
 await assert.rejects(checkBudgetHandoff(args),/missing disposition/);
 pr.body+=marker(disposition);
 assert.equal((await checkBudgetHandoff(args)).required,true);
 assert.equal((await checkBudgetHandoff({...args,api:async()=>({number:2,state:'closed'})})).required,true);
 await assert.rejects(checkBudgetHandoff({...args,api:async()=>({...issue,number:2,labels:['kind:umbrella']})}),/bounded children/);
 assert.equal((await checkBudgetHandoff({...args,issue})).required,false);
 pr.body='Closes #1';assert.equal((await checkBudgetHandoff(args)).required,false);
});
