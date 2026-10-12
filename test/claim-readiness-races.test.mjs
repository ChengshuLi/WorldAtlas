import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
const runner=new URL('../scripts/run-issue-claim.mjs',import.meta.url);
const spec={mode:'engineering',scope:'bounded repair',max_prs:1,depends_on:[2]};
let caseNumber=0;
async function runCase(drift){
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'wa-claim-race-'));
 const cwd=process.cwd(),fetchBefore=globalThis.fetch,keys=['GITHUB_REF','GITHUB_REPOSITORY','GITHUB_EVENT_PATH','GITHUB_STEP_SUMMARY','GH_TOKEN'];
 const before=Object.fromEntries(keys.map(k=>[k,process.env[k]]));
 const geography=drift==='ownership';
 const caseSpec=geography?{...spec,mode:'geography',owned_paths:['data/regional-review/packet/']}:spec;
 const value={number:1,state:'open',created_at:'2026-10-01T00:00:00Z',updated_at:'same',labels:[geography?'type:geography':'type:engineering','kind:work-item','status:ready'].map(name=>({name})),body:`<!-- worldatlas-work:v1\n${JSON.stringify(caseSpec)}\n-->`};
 let commentReads=0,depReads=0,timelineReads=0,ownershipReads=0;const writes=[];
 try{
  process.chdir(dir);fs.writeFileSync('event.json',JSON.stringify({inputs:{action:'claim',issue_number:'1',worker_id:'author',claim_id:'claim-aaaaaaaaaaaaaaaa',request_id:'request-aaaaaaaaaaaaaaa',branch:geography?'geography/repair':'engineering/repair'}}));
  Object.assign(process.env,{GITHUB_REF:'refs/heads/main',GITHUB_REPOSITORY:'owner/repo',GITHUB_EVENT_PATH:path.join(dir,'event.json'),GITHUB_STEP_SUMMARY:path.join(dir,'summary'),GH_TOKEN:'synthetic-token'});
  globalThis.fetch=async(raw,options)=>{
   const url=new URL(raw),route=url.pathname,method=options.method;let payload;
   if(method!=='GET'){writes.push({route,body:JSON.parse(options.body??'{}')});payload={id:123};}
   else if(route.endsWith('/issues'))payload=ownershipReads++?[value,{...value,number:3}]:[value];
   else if(route.endsWith('/issues/1'))payload=value;
   else if(route.endsWith('/issues/2'))payload={number:2,state:drift==='dependency'&&depReads++?'open':'closed'};
   else if(route.endsWith('/comments'))payload=drift==='blocker'&&commentReads++?[{id:3,user:{login:'human'},body:'<!-- worldatlas-blocker:v1\n{"id":"input","active":true,"reason":"Missing input"}\n-->'}]:[];
   else if(route.endsWith('/timeline'))payload=drift==='budget'&&timelineReads++?[{source:{issue:{number:3,body:'Refs #1',pull_request:{url:'pr'}}}}]:[];
   else if(route.endsWith('/pulls/3'))payload={number:3,state:'closed',body:'Refs #1',merged_at:'now'};
   else throw Error('Unexpected mock route '+route);
   return new Response(JSON.stringify(payload),{status:200,headers:{'Content-Type':'application/json','x-ratelimit-resource':'core','x-ratelimit-limit':'5000','x-ratelimit-remaining':'4900','x-ratelimit-reset':String(Math.floor(Date.now()/1000)+3600)}});
  };
  const {runIssueClaim}=await import(runner.href+'?race='+caseNumber++);
  const result=await runIssueClaim({event:JSON.parse(fs.readFileSync('event.json'))});
  return {result,writes};
 }finally{
  globalThis.fetch=fetchBefore;process.chdir(cwd);
  for(const k of keys)if(before[k]===undefined)delete process.env[k];else process.env[k]=before[k];
  fs.rmSync(dir,{recursive:true,force:true});
 }
}
test('actual claim runner rejects blocker, dependency, budget and ownership drift without writing a reservation',async()=>{
 for(const drift of ['blocker','dependency','budget','ownership']){
  const {result,writes}=await runCase(drift);assert.equal(result.accepted,false);assert.match(result.reason,/changed during claim/);
  assert(!writes.some(x=>x.body.body?.startsWith('**Worker reservation:**')));
  assert.equal(writes.length,1,'Only durable rejection result is written');
 }
});
test('actual claim runner still writes one accepted canonical reservation for stable eligible inputs',async()=>{
 const {result,writes}=await runCase(null);assert.equal(result.accepted,true);
 assert.equal(writes.filter(x=>x.body.body?.startsWith('**Worker reservation:**')).length,1);
});

// Exercise the real mutation runner with two complete API read rounds. These
// fixtures distinguish concurrent authority changes from GitHub presentation
// churn; they do not identify which field changed in the original refusal.
async function runRenewal({change=()=>{},geography=false,initialChange=()=>{}}={}){
 const {runIssueClaim}=await import(runner);
 const {renderClaim}=await import('../scripts/issue-claim-contract.mjs');
 const branch=geography?'geography/repair':'engineering/repair';
 const claim={version:1,active:true,worker_id:'author',claim_id:'claim-aaaaaaaaaaaaaaaa',branch,
  request_id:'prior-request-aaaaaaaa',expires_at:'2099-01-01T00:00:00Z',claimed_at:'2026-10-01T00:00:00Z',
  mode:geography?'geography':'engineering',...(geography?{owned_paths:['data/regional-review/packet/']}:{})};
 const contract={...spec,...(geography?{mode:'geography',owned_paths:['data/regional-review/packet/']}:{})};
 const issueBody=value=>`Scope\n<!-- worldatlas-work:v1\n${JSON.stringify(value)}\n-->`;
 const initial={
  issue:{number:1,state:'open',created_at:'2026-10-01T00:00:00Z',updated_at:'old',body:issueBody(contract),
   labels:[geography?'type:geography':'type:engineering','kind:work-item','status:ready','status:claimed'].map(name=>({name}))},
  claim,comments:[{id:8,user:{login:'human'},body:'Ordinary progress'}],
  dependency:{number:2,state:'closed',body:'Previous work',updated_at:'old'},
  prs:[{number:3,state:'open',head:{ref:branch,sha:'a'.repeat(40),repo:{id:12,full_name:'owner/repo'}},
   base:{ref:'main',sha:'b'.repeat(40)},body:'Refs #1',updated_at:'old',mergeable:null}],
  otherIssues:geography?[{number:4,state:'open',labels:[{name:'type:geography'},{name:'kind:work-item'}],
   body:issueBody({...contract,owned_paths:['data/regional-review/elsewhere/']})}]:[]
 };
 initialChange(initial,{renderClaim,issueBody});
 const fresh=structuredClone(initial);change(fresh,{renderClaim,issueBody});
 const reads=new Map(),writes=[];
 const apiFactory=()=>async(route,method='GET',body)=>{
  if(method!=='GET'){writes.push({route,method,body});return {id:42};}
  const count=reads.get(route)??0;reads.set(route,count+1);
  const value=count?fresh:initial;
  if(route==='/repos/owner/repo/issues/1')return structuredClone(value.issue);
  if(route==='/repos/owner/repo/issues/2')return structuredClone(value.dependency);
  if(route.includes('/issues/1/comments'))return [
   ...(value.claim?[{id:9,user:{login:'github-actions[bot]'},body:renderClaim(value.claim)}]:[]),...value.comments];
  if(route.includes('/issues/1/timeline'))return value.prs.map(pr=>({source:{issue:{number:pr.number,body:'Refs #1',pull_request:{url:'pr'}}}}));
  if(route.includes('/pulls/'))return structuredClone(value.prs.find(pr=>route.endsWith('/'+pr.number)));
  if(route.includes('/issues?'))return structuredClone(value.otherIssues);
  throw Error('Unexpected mock route '+route);
 };
 const result=await runIssueClaim({event:{inputs:{action:'renew',issue_number:'1',worker_id:'author',
  claim_id:'claim-aaaaaaaaaaaaaaaa',request_id:'request-aaaaaaaaaaaaaaa',branch}},
  env:{GITHUB_REF:'refs/heads/main',GITHUB_REPOSITORY:'owner/repo',GH_TOKEN:'synthetic'},apiFactory});
 return {result,writes};
}
function noReservation({result,writes}){
 assert.equal(result.accepted,false);assert.equal(result.mutation_attempted,false);
 assert(!writes.some(x=>x.body.body?.startsWith('**Worker reservation:**')));
 assert.equal(writes.length,1,'Only the durable refusal is written');
}
test('actual renewal accepts metadata drift and ordinary comments with canonical authority unchanged',async()=>{
 const {result,writes}=await runRenewal({geography:true,change:(value,{issueBody})=>{
  value.issue.updated_at='new';value.issue.title='Retitled';value.issue.labels.reverse();
  value.issue.labels.push({name:'priority:high'});
  value.comments.push({id:12,user:{login:'github-actions[bot]'},body:'**Reservation result:** routine status'},
   {id:13,user:{login:'human'},body:'Progress continues'});
  value.comments[0].body='Edited ordinary comment';value.comments.reverse();
  value.claim=Object.fromEntries(Object.entries(value.claim).reverse());
  value.prs[0].base.sha='d'.repeat(40); // Main advancing does not change the owned PR head.
  Object.assign(value.prs[0],{updated_at:'new',mergeable:true,mergeable_state:'clean',comments:8,
   review_comments:3,statuses_url:'irrelevant',user:{login:'author',avatar_url:'new'}});
  Object.assign(value.dependency,{body:'New discussion summary',updated_at:'new',labels:[{name:'priority:high'}]});
  value.otherIssues[0].updated_at='new';value.otherIssues[0].title='Cosmetic';
  value.otherIssues[0].body=issueBody({...spec,mode:'geography',scope:'Same nonoverlapping ownership, edited text',owned_paths:['data/regional-review/elsewhere/']});
 }});
 assert.equal(result.accepted,true,result.reason);
 assert.equal(writes.filter(x=>x.body.body?.startsWith('**Worker reservation:**')).length,1);
 assert.equal(result.claim.worker_id,'author');assert.equal(result.claim.branch,'geography/repair');
});
test('actual renewal refuses every decision-relevant concurrent change with its category',async()=>{
 const cases=[
  ['lease owner','claim',v=>v.claim.worker_id='foreign'],
  ['lease nonce','claim',v=>v.claim.claim_id='foreign-claim-aaaaaaaa'],
  ['lease branch','claim',v=>v.claim.branch='engineering/foreign'],
  ['lease expiry','claim',v=>v.claim.expires_at='2098-01-01T00:00:00Z'],
  ['lease revoked','claim',v=>v.claim.active=false],
  ['lease removed','claim',v=>v.claim=null],
  ['lease request','claim',v=>v.claim.request_id='concurrent-request-aaaa'],
  ['live operation','claim',v=>v.claim.live_work=true],
  ['PR head','linked_prs',v=>v.prs[0].head.sha='c'.repeat(40)],
  ['PR branch','linked_prs',v=>v.prs[0].head.ref='engineering/foreign'],
  ['PR state','linked_prs',v=>v.prs[0].state='closed'],
  ['PR base','linked_prs',v=>v.prs[0].base.ref='other-main'],
  ['PR repository','linked_prs',v=>v.prs[0].head.repo.id=99],
  ['readiness','readiness',v=>v.issue.labels=v.issue.labels.filter(x=>x.name!=='status:ready')],
  ['blocked','readiness',v=>v.issue.labels.push({name:'status:blocked'})],
  ['issue state','readiness',v=>v.issue.state='closed'],
  ['issue kind','readiness',v=>v.issue.labels.push({name:'kind:umbrella'})],
  ['issue lane','readiness',v=>v.issue.labels.push({name:'type:geography'})],
  ['issue vs PR','readiness',v=>v.issue.pull_request={url:'foreign'}],
  ['evidence activation','readiness',v=>v.issue.created_at='2026-10-12T00:00:00Z'],
  ['work contract','readiness',(v,{issueBody})=>v.issue.body=issueBody({...spec,scope:'Expanded scope'})],
  ['dependency roster','readiness',(v,{issueBody})=>v.issue.body=issueBody({...spec,depends_on:[2,99]})],
  ['blocker','blockers',v=>v.comments.push({id:20,user:{login:'human'},body:'<!-- worldatlas-blocker:v1\n{"id":"input","active":true,"reason":"Missing input"}\n-->'})],
  ['dependency','dependencies',v=>v.dependency.state='open'],
  ['dependency vs PR','dependencies',v=>v.dependency.pull_request={url:'foreign'}],
  ['foreign ownership','ownership',(v,{issueBody})=>v.otherIssues[0].body=issueBody({...spec,mode:'geography',owned_paths:['data/regional-review/packet/']})],
 ];
 for(const [name,category,change] of cases){
  const outcome=await runRenewal({change,geography:category==='ownership'});
  noReservation(outcome);assert.deepEqual(outcome.result.changed_categories,[category],name);
  assert.match(outcome.result.reason,/changed during claim/);
 }
});
test('concurrent changes retain every changed category in the durable refusal',async()=>{
 const outcome=await runRenewal({change:value=>{value.claim.worker_id='foreign';value.dependency.state='open';value.prs[0].head.sha='f'.repeat(40);}});
 noReservation(outcome);
 assert.deepEqual(outcome.result.changed_categories,['claim','dependencies','linked_prs']);
 assert.match(outcome.writes[0].body.body,/changed_categories/);
});
test('actual renewal preserves malformed and multiple canonical record refusal',async()=>{
 for(const initialChange of [
  v=>v.claim.version=2,
  v=>{v.claim=null;v.comments.push({id:9,user:{login:'github-actions[bot]'},body:'**Worker reservation:** broken'});},
  (v,{renderClaim})=>v.comments.push({id:10,user:{login:'github-actions[bot]'},body:renderClaim(v.claim)}),
  v=>v.comments.push({id:20,user:{login:'human'},body:'<!-- worldatlas-blocker:v1\n{"active":true}\n-->'}),
 ]){
  for(const options of [{initialChange},{change:initialChange}]){
   const outcome=await runRenewal(options);noReservation(outcome);
   assert.match(outcome.result.reason,/Invalid canonical|Malformed canonical|Multiple canonical|Malformed blocker/);
  }
 }
});
test('stable conflicting authority still fails the real transition guards',async()=>{
 for(const initialChange of [v=>v.claim.worker_id='foreign',v=>v.claim.claim_id='foreign-claim-aaaaaaaa',
  v=>v.claim.active=false,v=>v.dependency.state='open',v=>v.issue.labels.push({name:'status:blocked'})]){
  const outcome=await runRenewal({initialChange});noReservation(outcome);
  assert.equal(outcome.result.changed_categories,undefined);
  assert.match(outcome.result.reason,/current holder|dependency|ready work items/);
 }
});
