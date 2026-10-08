import test from 'node:test';
import assert from 'node:assert/strict';
import {publicationPlan,readPublicationState,referencedIssues,validateDelivery,publicationEnvironment,publicationTask} from '../scripts/publication-plan.mjs';
const root='/repos/ChengshuLi/WorldAtlas',base='a'.repeat(40),target='b'.repeat(40),other='c'.repeat(40);
const delivery=()=>({version:1,primary_commit:base,source_commit:other,site:{project_id:'appgprj_6abdf87277c08191bce4a22b8dfb25db',version:24,deployment_id:'appgdep_fixture'},release_id:'fixture-release',hierarchy_sha256:'d'.repeat(64),footprint_sha256:'e'.repeat(64),assets_sha256:'f'.repeat(64),evidence_urls:['https://github.com/ChengshuLi/WorldAtlas/issues/6#issuecomment-1']});
const issue=n=>({number:n,title:'Fixture '+n,state:n===3?'closed':'open',html_url:'https://github.com/ChengshuLi/WorldAtlas/issues/'+n,labels:n===51?['publisher-needed','status:blocked']:[]});
function fixture(){
 const calls=[],routes=new Map([
  [root+'/commits/main',{sha:target}],
  [root+'/deployments?per_page=100&page=1',[]],
  [root+'/issues?state=open&labels=publisher-needed&per_page=100&page=1',[issue(51)]],
  [root+'/compare/'+base+'...'+target+'?per_page=100&page=1',{status:'ahead',merge_base_commit:{sha:base},total_commits:1,commits:[{sha:target,commit:{message:'merged'}}]}],
  [root+'/commits/'+target+'/pulls?per_page=100&page=1',[{number:7,html_url:'pr7',body:'Refs #2, #3',merged_at:'2026-10-04',merge_commit_sha:target,base:{ref:'main',repo:{full_name:'ChengshuLi/WorldAtlas'}}}]],
  [root+'/issues/2',issue(2)],[root+'/issues/3',issue(3)]
 ]);
 const api=async route=>{calls.push(route);assert.ok(routes.has(route),'Unexpected route '+route);return structuredClone(routes.get(route));};
 return {routes,calls,api};
}
test('pins main once, discovers merged and closed original issues plus label-only blocked operation',async()=>{
 const f=fixture(),p=await publicationPlan(f.api,{bootstrap:delivery()});
 assert.equal(f.calls[0],root+'/commits/main');assert.equal(f.calls.filter(r=>r===root+'/commits/main').length,1);
 assert.equal(p.target_commit,target);assert.deepEqual(p.issues.map(i=>i.number),[2,3,51]);assert.equal(p.issues[1].state,'closed');assert.equal(p.issues[2].eligibility,'unreviewed');assert.deepEqual(p.blockers,[]);
});
test('missing boundary returns labeled backlog without assuming main deployed',async()=>{
 const f=fixture(),p=await publicationPlan(f.api);assert.equal(p.last_delivery,null);assert.equal(p.commits.length,0);assert.match(p.blockers[0],/No verified/);assert.equal(p.issues[0].number,51);
});
test('explicit references only, preserves multiple original issues',()=>assert.deepEqual(referencedIssues('Closes #3\nRefs https://github.com/ChengshuLi/WorldAtlas/issues/2, #51\nSee #77'),[2,3,51]));
test('all delivery identities required',()=>{for(const key of ['primary_commit','source_commit','site','release_id','hierarchy_sha256','footprint_sha256','assets_sha256','evidence_urls']){const d=delivery();delete d[key];assert.throws(()=>validateDelivery(d));}});
test('unlinked commits and PRs remain visible',async()=>{
 const f=fixture();f.routes.set(root+'/commits/'+target+'/pulls?per_page=100&page=1',[]);
 const p=await publicationPlan(f.api,{bootstrap:delivery()});assert.deepEqual(p.unlinked_commits,[target]);
 f.routes.set(root+'/commits/'+target+'/pulls?per_page=100&page=1',[{number:8,body:'No issue',merged_at:'date',merge_commit_sha:target,base:{ref:'main',repo:{full_name:'ChengshuLi/WorldAtlas'}}}]);
 assert.equal((await publicationPlan(f.api,{bootstrap:delivery()})).pull_requests[0].needs_manual_issue_mapping,true);
});
for(const [label,change] of [
 ['mirror boundary',x=>x.merge_base_commit.sha=other],['divergent ancestry',x=>x.status='diverged'],['missing pages',x=>x.total_commits=2],['duplicate commits',x=>{x.total_commits=2;x.commits.push(x.commits[0]);}]
])test('rejects '+label,async()=>{const f=fixture(),route=root+'/compare/'+base+'...'+target+'?per_page=100&page=1';change(f.routes.get(route));await assert.rejects(()=>publicationPlan(f.api,{bootstrap:delivery()}));});
test('paginates immutable commit and issue inventories beyond 100 without moving main',async()=>{
 const f=fixture(),commits=Array.from({length:101},(_,i)=>({sha:(i+1).toString(16).padStart(40,'0'),commit:{message:'fixture'}}));
 for(let page=1;page<=2;page++)f.routes.set(root+'/compare/'+base+'...'+target+'?per_page=100&page='+page,{status:'ahead',merge_base_commit:{sha:base},total_commits:101,commits:commits.slice((page-1)*100,page*100)});
 for(const c of commits)f.routes.set(root+'/commits/'+c.sha+'/pulls?per_page=100&page=1',[]);
 f.routes.set(root+'/issues?state=open&labels=publisher-needed&per_page=100&page=1',Array.from({length:100},(_,i)=>issue(i+100)));
 f.routes.set(root+'/issues?state=open&labels=publisher-needed&per_page=100&page=2',[issue(51)]);
 const p=await publicationPlan(f.api,{bootstrap:delivery()});assert.equal(p.commits.length,101);assert.equal(p.issues.length,101);assert.equal(p.target_commit,target);
});
function deployedFixture(){
 const f=fixture(),op={version:1,operation_id:'fixture-op',publisher_worker_id:'publisher',kind:'site',primary_commit:base,issues:[2],started_at:'2026-10-04T00:00:00Z',expires_at:'2026-10-04T00:30:00Z',rollback_url:'https://github.com/ChengshuLi/WorldAtlas/issues/6'};
 const deployment={id:1,sha:base,environment:publicationEnvironment,task:publicationTask,payload:{worldatlas_publication:op}};
 const result={version:1,deployment_id:1,operation_id:op.operation_id,publisher_worker_id:op.publisher_worker_id,primary_commit:base,state:'verified',cleanup_confirmed:true,delivery:delivery(),issue_checks:[{issue:2,outcome:'failed',evidence_urls:['https://github.com/ChengshuLi/WorldAtlas/issues/2#issuecomment-5']}]};
 const url='https://github.com/ChengshuLi/WorldAtlas/issues/2#issuecomment-5';
 const comment=()=>({html_url:url,user:{type:'User'},author_association:'OWNER',body:'<!-- worldatlas-publication-result:v1\n'+JSON.stringify(result)+'\n-->'});
 f.routes.set(root+'/deployments?per_page=100&page=1',[deployment]);
 f.routes.set(root+'/deployments/1/statuses?per_page=100&page=1',[{id:2,state:'success',log_url:url}]);
 f.routes.set(root+'/issues/comments/5',comment());
 return {...f,op,deployment,result,refresh:()=>f.routes.set(root+'/issues/comments/5',comment())};
}
test('failed production acceptance survives successful delivery even without a label or new commits',async()=>{
 const f=deployedFixture();f.routes.set(root+'/compare/'+base+'...'+target+'?per_page=100&page=1',{status:'identical',merge_base_commit:{sha:base},total_commits:0,commits:[]});
 const p=await publicationPlan(f.api);assert.equal(p.last_delivery.primary_commit,base);assert.equal(p.commits.length,0);assert.deepEqual(p.issues.find(i=>i.number===2).discovery,['outstanding-acceptance']);assert.equal(p.issues.find(i=>i.number===2).last_check.outcome,'failed');
});
test('failed settled deployment never advances delivery',async()=>{
 const f=deployedFixture();f.result.state='failed-settled';f.result.delivery=null;f.refresh();f.routes.get(root+'/deployments/1/statuses?per_page=100&page=1')[0].state='failure';
 const state=await readPublicationState(f.api);assert.equal(state.delivery,null);assert.equal(state.unsettled.length,0);
});
test('expired operation without explicit cleanup blocks next operation',async()=>{
 const f=deployedFixture();f.routes.set(root+'/deployments/1/statuses?per_page=100&page=1',[]);
 const p=await publicationPlan(f.api,{bootstrap:delivery()});assert.equal(p.unsettled_operations.length,1);assert.match(p.blockers[0],/unsettled/);
});
for(const [label,change] of [
 ['wrong source commit',f=>f.result.delivery.primary_commit=other],['failed deployment marked delivered',f=>f.result.state='failed-settled'],['unsettled cleanup',f=>f.result.cleanup_confirmed=false],['missing issue result',f=>f.result.issue_checks=[]],['missing delivery field',f=>delete f.result.delivery],['wrong worker',f=>f.result.publisher_worker_id='other']
])test('rejects incoherent '+label,async()=>{const f=deployedFixture();change(f);f.refresh();await assert.rejects(()=>readPublicationState(f.api));});
test('unauthorized receipt fails closed',async()=>{const f=deployedFixture();f.routes.get(root+'/issues/comments/5').author_association='NONE';await assert.rejects(()=>readPublicationState(f.api));});

test('a newer success cannot hide an older active operation and all status pages are read',async()=>{
 const f=deployedFixture(),old=structuredClone(f.deployment);
 old.payload.worldatlas_publication.operation_id='older-operation';f.deployment.id=2;f.result.deployment_id=2;f.refresh();
 f.routes.set(root+'/deployments/2/statuses?per_page=100&page=1',f.routes.get(root+'/deployments/1/statuses?per_page=100&page=1'));
 f.routes.set(root+'/deployments?per_page=100&page=1',[f.deployment,old]);
 f.routes.set(root+'/deployments/1/statuses?per_page=100&page=1',Array.from({length:100},(_,i)=>({id:i+10,state:'in_progress'})));
 f.routes.set(root+'/deployments/1/statuses?per_page=100&page=2',[]);
 const s=await readPublicationState(f.api);assert.equal(s.delivery.primary_commit,base);assert.equal(s.unsettled.length,1);assert.ok(f.calls.includes(root+'/deployments/1/statuses?per_page=100&page=2'));
});
test('verified Site operation without delivery identity is incoherent',async()=>{const f=deployedFixture();f.result.delivery=null;f.refresh();await assert.rejects(()=>readPublicationState(f.api));});
test('concurrent main advance does not change pinned plan',async()=>{
 const f=fixture();let reads=0;const api=route=>route===root+'/commits/main'?Promise.resolve({sha:reads++?other:target}):f.api(route);
 const p=await publicationPlan(api,{bootstrap:delivery()});assert.equal(reads,1);assert.equal(p.target_commit,target);
});
test('rejects backwards delivery history instead of losing already delivered changes',async()=>{
 const f=deployedFixture();const bootstrap={...delivery(),primary_commit:other};
 f.routes.set(root+'/compare/'+other+'...'+base+'?per_page=1',{status:'behind',merge_base_commit:{sha:base}});
 await assert.rejects(()=>publicationPlan(f.api,{bootstrap}),/Non-monotone/);
});
