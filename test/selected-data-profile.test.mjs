import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {selectIntegrationProfile} from '../scripts/check-integration-profile.mjs';
import {prepareIntegration, completeIntegration} from '../scripts/merge-integration.mjs';
import {PROOF_PATHS, WORKFLOW_PATH} from '../scripts/integration-proof.mjs';
import {checkPRGates} from '../scripts/check-pr-gates.mjs';
import {selectedDataSelection, selectedDataCandidate, validateSelectedExpectations, SELECTED_SMOKE} from '../scripts/integration-profile.mjs';
const prefix = 'coordination/engineering/fixture-delivery/';
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
function fixture({mutate = () => {}} = {}) {
  const blobs = new Map(), baseline = {entries:new Map()}, authored = {entries:new Map()}, reads=[];
  const put = (name, value, old=false) => {
    const bytes = Buffer.from(typeof value === 'string' ? value : JSON.stringify(value));
    const sha = createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex');
    blobs.set(sha,bytes); const row={path:name,type:'blob',mode:'100644',size:bytes.length,sha};
    authored.entries.set(name,row); if(old)baseline.entries.set(name,row);
    return {path:name,bytes:bytes.length,sha256:digest(bytes),mode:'100644',git_blob_oid:sha,commit:'a'.repeat(40)};
  };
  const leaf = (name, old=false) => put((old?'coordination/engineering/prior/':prefix)+name,{opaque:true},old);
  put(SELECTED_SMOKE,'// Accepted generic helper',true);
  const authority = leaf('authority.json',true), rule = leaf('rule.json',true);
  const entry={authority_sha256:'a'.repeat(64),policy_id:'retained-source-literal-additions',policy_version:1,
    rule_preimage:rule,rule_sha256:rule.sha256,source_authority:authority};
  const registryBody={version:1,kind:'registry',entries:[entry]};
  const oldRegistry=put('coordination/engineering/prior/registry.json',registryBody,true);
  const base={version:1,method:'native-linear-evenodd-first-owner-v1',artifact_consumption:{certificate:{},review:{}},manifest_path:'unchanged.json',sha256:'a'.repeat(64)};
  const oldSidecar=put('coordination/engineering/prior/sidecar.json',{authority_registry:oldRegistry},true);
  const hook=pin=>({path:pin.path,bytes:pin.bytes,sha256:pin.sha256});
  put('data/ownership-selection.json',{...base,additive_release:hook(oldSidecar)},true);
  const registry=put(prefix+'registry.json',registryBody);
  const original=leaf('composed-original-ledger.json');
  const plan=put(prefix+'issued-plan.json',{original_inputs:[{...registry,commit:'b'.repeat(40)},original]});
  const custody=Object.fromEntries(['code_source','terminal','stderr','stdout'].map(name=>[name,leaf(name+'.json')]));
  custody.issued_plan=plan;
  const operating=put(prefix+'operating.json',{execution_custody:custody});
  const certificateBody={version:1,kind:'qualified-native-additive-current-bank-rebind-v1',operating,
    ...Object.fromEntries(['request','facts','publication','result'].map(name=>[name,leaf(name+'.json')]))};
  const certificate=put(prefix+'certificate.json',certificateBody);
  const rows=[{component_id:'old',target_id:'target-old',disposition:'assigned',geometry_sha256:'1'.repeat(64),native_cells:2},
    {component_id:'new',target_id:'target-new',disposition:'zero-cell',geometry_sha256:'2'.repeat(64),native_cells:0}];
  const ledgerBody={version:2,kind:'native-additive-repair-ledger-v2',rows,current_rebind:certificate};
  const ledger=put(prefix+'ledger.json',ledgerBody);
  const sidecarBody={version:2,kind:'retained-native-additive-selection-v2',base_selection:base,
    authority_registry:registry,runtime_envelope:leaf('envelope.json'),
    logical_asset_map:{ledger,patch:leaf('patch.json'),owner_roster:leaf('owners.json',true),base_manifest:leaf('manifest.json',true)}};
  const sidecar=put(prefix+'selection-sidecar.json',sidecarBody);
  put('data/ownership-selection.json',{...base,additive_release:hook(sidecar)});
  const expected={version:1,selected_ledger_sha256:ledger.sha256,cumulative_native_cells:2,
    cohorts:[{original_batch_id:'complete-original',component_ids:['old','new'],members:rows.map(({native_cells,...member})=>member)}]};
  put(prefix+'selected-delivery-expectations.json',expected);
  const policy={version:1,inputs:['.github/package-inputs.json','data/ownership-selection.json'],optional_inputs:[],verification_paths:[],generated_outputs:[]};
  put('.github/package-inputs.json',policy,true);
  const definition={...policy,inputs:[...policy.inputs,...[...authored.entries.keys()].filter(name=>name.startsWith(prefix)&&!name.endsWith('selected-delivery-expectations.json'))]};
  put('.github/package-inputs.json',definition);
  const f={put,leaf,blobs,baseline,authored,reads,base,rows,expected,definition,policy,sidecarBody,ledgerBody,certificateBody,registryBody,plan,registry,operating};
  mutate(f);
  f.files=[...authored.entries].filter(([name,row])=>baseline.entries.get(name)?.sha!==row.sha).map(([filename])=>({filename,status:baseline.entries.has(filename)?'modified':'added'}));
  f.api=async route=>{const oid=route.split('/').at(-1),bytes=blobs.get(oid);assert(bytes,route);reads.push(oid);return {sha:oid,size:bytes.length,encoding:'base64',content:bytes.toString('base64')};};
  f.run=()=>selectedDataSelection({api:f.api,repo:'owner/repo',branch:'engineering/fixture-delivery',files:f.files,baseline,authored});
  return f;
}
function refreshPins(f, {planMutate = () => {}} = {}) {
  const registry=f.put(prefix+'registry.json',f.registryBody);
  const planBody={original_inputs:[{...registry,commit:'b'.repeat(40)},f.leaf('composed-original-ledger.json')]};planMutate(planBody);
  const plan=f.put(prefix+'issued-plan.json',planBody);
  const oldOperating=JSON.parse(f.blobs.get(f.operating.git_blob_oid));oldOperating.execution_custody.issued_plan=plan;
  const operating=f.put(prefix+'operating.json',oldOperating);
  const certificate=f.put(prefix+'certificate.json',{...f.certificateBody,operating});
  const ledger=f.put(prefix+'ledger.json',{...f.ledgerBody,current_rebind:certificate});
  const side=f.put(prefix+'selection-sidecar.json',{...f.sidecarBody,authority_registry:registry,logical_asset_map:{...f.sidecarBody.logical_asset_map,ledger}});
  f.put('data/ownership-selection.json',{...f.base,additive_release:{path:side.path,bytes:side.bytes,sha256:side.sha256}});
  f.put(prefix+'selected-delivery-expectations.json',{...f.expected,selected_ledger_sha256:ledger.sha256});
  f.definition.inputs=[...f.policy.inputs,...[...f.authored.entries.keys()].filter(name=>name.startsWith(prefix)&&!name.endsWith('selected-delivery-expectations.json'))];
  f.put('.github/package-inputs.json',f.definition);
}
test('selected-data uses full setup with one narrow selection, exact package appends and complete reviewed roster',async()=>{
  const f=fixture();assert.equal(selectedDataCandidate('engineering/fixture-delivery',f.files),true);
  assert.deepEqual(await f.run(),{test_selection:'selected-data',expectations_path:prefix+'selected-delivery-expectations.json',shards:[0]});
  for(const name of ['request.json','facts.json','result.json','patch.json'])assert(!f.reads.includes(f.authored.entries.get(prefix+name).sha),'opaque role was unnecessarily read');
  assert(!f.reads.includes(f.authored.entries.get('coordination/engineering/prior/authority.json').sha),'unchanged authority was reread');
});
test('inert evidence is not a license to append unreachable package data',async()=>{
  const f=fixture({mutate:f=>f.put(prefix+'assembly-receipt.json',{complete:true})});assert.ok(await f.run());
  f.definition.inputs.push(prefix+'assembly-receipt.json');f.put('.github/package-inputs.json',f.definition);assert.equal(await f.run(),null);
});
for(const [name,mutate] of Object.entries({
  'missing accepted smoke':f=>f.baseline.entries.delete(SELECTED_SMOKE),
  'candidate helper substitution':f=>f.put(SELECTED_SMOKE,'// candidate replacement'),
  'missing expectations':f=>f.authored.entries.delete(prefix+'selected-delivery-expectations.json'),
  'ambiguous expectations':f=>f.put(prefix+'other/selected-delivery-expectations.json',f.expected),
  'incomplete expected roster':f=>{f.expected.cohorts[0].members.pop();f.expected.cohorts[0].component_ids.pop();f.put(prefix+'selected-delivery-expectations.json',f.expected);},
  'wrong expected target':f=>{f.expected.cohorts[0].members[0].target_id='wrong';f.put(prefix+'selected-delivery-expectations.json',f.expected);},
  'wrong expected cells':f=>{f.expected.cumulative_native_cells=1;f.put(prefix+'selected-delivery-expectations.json',f.expected);},
  'wrong ledger expectation':f=>{f.expected.selected_ledger_sha256='f'.repeat(64);f.put(prefix+'selected-delivery-expectations.json',f.expected);},
  'package removal':f=>{f.definition.inputs.shift();f.put('.github/package-inputs.json',f.definition);},
  'package reordering':f=>{f.definition.inputs.reverse();f.put('.github/package-inputs.json',f.definition);},
  'package policy rewrite':f=>{f.definition.verification_paths.push('src/');f.put('.github/package-inputs.json',f.definition);},
  'directory package append':f=>{f.definition.inputs.push(prefix+'extra/');f.put('.github/package-inputs.json',f.definition);},
  'code disguised as package data':f=>f.put(prefix+'package.json',{scripts:{postinstall:'do something'}}),
  'new executable':f=>f.put(prefix+'helper.mjs','throw Error()'),
  'foreign data':f=>f.put('coordination/engineering/other/result.json',{}),
  'malformed supporting JSON':f=>f.put(prefix+'receipt.json','console.log("not data")'),
  'symlink role':f=>f.authored.entries.get(prefix+'patch.json').mode='120000',
  'executable role':f=>f.authored.entries.get(prefix+'patch.json').mode='100755',
  'tree size drift':f=>f.authored.entries.get(prefix+'patch.json').size++,
  'method change':f=>{f.base.method='new-method';f.put('data/ownership-selection.json',f.base);},
}))test('selected-data falls back to full for '+name,async()=>assert.equal(await fixture({mutate}).run(),null));
test('rename/copy/removal origins never use selected routing',async()=>{
  for(const delta of [{previous_filename:'src/code.js'},{status:'removed'},{status:'renamed'}]){const f=fixture();Object.assign(f.files.find(row=>row.filename.endsWith('patch.json')),delta);assert.equal(await f.run(),null);}
});
test('whole-ledger expectation check rejects duplicate batches/members and foreign fields',()=>{
  for(const mutate of [e=>e.cohorts.push(structuredClone(e.cohorts[0])),e=>e.foreign=true,e=>e.cohorts[0].members[0].foreign=true]){
    const f=fixture();mutate(f.expected);assert.throws(()=>validateSelectedExpectations(f.expected,f.ledgerBody,f.expected.selected_ledger_sha256));
  }
});

function gateFixture() {
  const f=fixture(), base='b'.repeat(40), head='c'.repeat(40), root='/repos/owner/repo';
  const issue={number:10,state:'open',created_at:'2020-01-01T00:00:00Z',labels:['type:engineering','kind:work-item','status:ready'],
    body:'<!-- worldatlas-work:v1\n'+JSON.stringify({max_prs:2,depends_on:[],mode:'engineering',scope:'Exact unchanged-method selected data'})+'\n-->'};
  const claim={version:1,active:true,issue_number:10,worker_id:'author',claim_id:'selected-claim',branch:'engineering/fixture-delivery',mode:'engineering',expires_at:'2099-01-01T00:00:00Z'};
  const pr={number:20,state:'open',changed_files:f.files.length,body:'Refs #10',head:{sha:head,ref:claim.branch,repo:{full_name:'owner/repo'}},
    base:{sha:base,ref:'main',repo:{full_name:'owner/repo'}}};
  const blobAPI=f.api;
  f.api=async route=>{
    if(route===root+'/pulls/20')return structuredClone(pr);
    if(route===root+'/pulls/20/files?per_page=100&page=1')return f.files;
    if(route===root+'/issues/10')return issue;
    if(route===root+'/issues/10/comments?per_page=100&page=1')return [{id:1,user:{login:'github-actions[bot]'},body:'**Worker reservation:** claimed\n\n<!-- worldatlas-claim:v1\n'+JSON.stringify(claim)+'\n-->'}];
    if(route===root+'/issues/10/timeline?per_page=100&page=1')return [];
    if(route===root+'/git/commits/'+base)return {tree:{sha:'base-tree'}};
    if(route===root+'/git/commits/'+head)return {tree:{sha:'head-tree'}};
    if(route===root+'/git/trees/base-tree?recursive=1')return {tree:[...f.baseline.entries.values()],truncated:false};
    if(route===root+'/git/trees/head-tree?recursive=1')return {tree:[...f.authored.entries.values()],truncated:false};
    if(route===root+'/contents/.github/package-inputs.json?ref='+base){const row=f.baseline.entries.get('.github/package-inputs.json');return {type:'file',path:row.path,sha:row.sha,size:row.size,encoding:'base64',content:f.blobs.get(row.sha).toString('base64')};}
    return blobAPI(route);
  };
  f.event={repository:{full_name:'owner/repo'},pull_request:pr};f.claim=claim;f.pr=pr;f.issue=issue;f.base=base;f.head=head;
  f.select=()=>selectIntegrationProfile({event:f.event,repo:'owner/repo',api:f.api});
  f.gate=()=>checkPRGates({event:f.event,repo:'owner/repo',token:'fixture',api:f.api,phase:'metadata'});
  return f;
}
test('actual trusted metadata entry binds ownership and forwards full setup plus narrowed selection',async()=>{
  const f=gateFixture(), result=await f.gate();
  assert.equal(result.profile,'full');assert.equal(result.test_selection,'selected-data');
  assert.equal(result.expectations_path,prefix+'selected-delivery-expectations.json');assert.deepEqual(result.shards,[0]);assert.equal(result.package.full,true);
  f.claim.active=false;await assert.rejects(f.select());
});
test('actual selector retains all three shards when accepted smoke or complete expectations are unavailable',async()=>{
  for(const mutate of [f=>f.baseline.entries.delete(SELECTED_SMOKE),f=>f.blobs.delete(f.authored.entries.get(prefix+'selected-delivery-expectations.json').sha)]){
    const f=gateFixture();mutate(f);assert.deepEqual(await f.select(),{profile:'full',shards:[0,1,2]});
  }
});

test('realistic new authority source/native roles append exact inert leaves without decoding science',async()=>{
  const f=fixture({mutate:f=>{
    const sourcePublication=f.leaf('source/publication.json'),sourceInventory=f.leaf('source/inventory.jsonl.gz'),sourceOperating=f.leaf('source/operating.json');
    const request=f.put(prefix+'native/request.json',{additive:{inputs:[sourcePublication,sourceInventory,sourceOperating],
      publication_path:sourcePublication.path,inventory_path:sourceInventory.path,operating_path:sourceOperating.path}});
    const original_pins={native_request:request,...Object.fromEntries(['ledger','native_facts','native_manifest','source_facts','source_request'].map(name=>[name,f.leaf('original/'+name+'.json')]))};
    const native_proof={publication:f.leaf('native/publication.json'),inventory:f.leaf('native/inventory.jsonl.gz'),operating:f.leaf('native/operating.json'),
      assets:['base-native-manifest','ledger-batch','patch-batch','features','owners-batch','release-envelope','owner-window','virtual-owner-window'].map(name=>f.leaf('native/'+name+'.json'))};
    const source_authority=f.put(prefix+'authority-binding.json',{version:1,kind:'original-issued-rule-source-custody-v1',original_pins,native_proof});
    const rule_preimage=f.leaf('original-rule.json');f.registryBody.entries.push({authority_sha256:'b'.repeat(64),policy_id:'retained-source-literal-additions',policy_version:1,source_authority,rule_preimage,rule_sha256:rule_preimage.sha256});
    refreshPins(f);
  }});
  assert.ok(await f.run());
  for(const name of ['source/inventory.jsonl.gz','original/native_facts.json','result.json'])
    assert(!f.reads.includes(f.authored.entries.get(prefix+name).sha),'classification decoded opaque role');
});
for(const [name,mutate] of Object.entries({
  'removed previous authority':f=>{f.registryBody.entries=[];refreshPins(f);},
  'rewritten previous authority':f=>{f.registryBody.entries[0].policy_version=2;refreshPins(f);},
  'foreign registry member':f=>{f.registryBody.entries[0].module=f.leaf('module.json');refreshPins(f);},
  'extra original input':f=>refreshPins(f,{planMutate:p=>p.original_inputs.push(f.leaf('foreign.json'))}),
  'reversed original operands':f=>refreshPins(f,{planMutate:p=>p.original_inputs.reverse()}),
  'wrong original registry':f=>refreshPins(f,{planMutate:p=>p.original_inputs[0]=f.leaf('other-registry.json')}),
  'code original operand':f=>refreshPins(f,{planMutate:p=>p.original_inputs[1]=f.put(prefix+'helper.mjs','export default 1')}),
}))test('selected-data rejects '+name,async()=>assert.equal(await fixture({mutate}).run(),null));

function mergeFixture({capacity = 2000, afterWait} = {}) {
  const f=gateFixture(), candidate='d'.repeat(40), root='/repos/owner/repo';
  Object.assign(f.pr,{draft:false,merged:false,title:'Synthetic selected delivery',mergeable:true,merge_commit_sha:candidate});
  for(const name of PROOF_PATHS)f.put(name,name===WORKFLOW_PATH?'ref: ${{ github.event.pull_request.head.sha }}\nname: Complete regression shard\nname: Build hosted assets':'// accepted '+name,true);
  const steps=['Checkout complete package inputs','Install package Node dependencies','Install package Python dependencies','Verify package controls',
    'Build and enforce archive/file reserves without publishing','Read back qualified native build outputs when selected','Install selected-data browser dependencies','Run selected-data consumer checks'];
  f.runRecord={id:44,run_attempt:1,head_sha:f.head,event:'pull_request',path:WORKFLOW_PATH,repository:{full_name:'owner/repo'},head_repository:{full_name:'owner/repo'},
    status:'completed',conclusion:'success',pull_requests:[{number:20,head:{sha:f.head}}]};
  f.jobs=[{name:'profile',status:'completed',conclusion:'success'},{name:'regression',status:'completed',conclusion:'skipped'},
    {name:'package',status:'completed',conclusion:'success',steps:steps.map(name=>({name,status:'completed',conclusion:'success'}))}];
  const source=f.api;let rateReads=0,remaining=2000;f.afterCalls=0;f.writes=[];
  f.api=async(route,method='GET',body)=>{
    if(route==='/rate_limit') {rateReads++;if(rateReads===2){remaining=capacity;afterWait?.(f);}return {resources:{core:{limit:2000,remaining,reset:999999}}};}
    if(rateReads>=2){f.afterCalls++;remaining--;assert(remaining>=16,'rejection reserve spent');}
    if(method==='PUT'){f.writes.push(body);return {merged:true,sha:'f'.repeat(40)};}
    if(route===root+'/git/ref/heads/main')return {object:{sha:f.base}};
    if(route===root+'/git/commits/'+candidate)return {tree:{sha:'head-tree'},parents:[{sha:f.base},{sha:f.head}]};
    if(route.includes('/check-runs'))return {check_runs:[{id:1,name:'scope',status:'completed',conclusion:'success',app:{id:1}}]};
    if(route===root+'/commits/'+f.head+'/status')return {statuses:[]};
    if(route.includes('/actions/workflows/merge-integration-checks.yml/runs?'))return {workflow_runs:[f.runRecord]};
    if(route===root+'/actions/runs/44')return f.runRecord;
    if(route.includes('/actions/runs/44/attempts/1/jobs'))return {jobs:f.jobs};
    if(route.includes('/actions/runs/99/artifacts'))return {total_count:0,artifacts:[]};
    return source(route);
  };
  f.options={api:f.api,repo:'owner/repo',number:20,expectedHead:f.head,policy:{version:1,mode:'enforce-new',activation_time:'2100-01-01T00:00:00Z'},
    evidenceCheck:async()=>({status:'legacy'}),candidateSleep:async()=>{}};
  f.complete=()=>completeIntegration({...f.options,finalCapacity:true,artifactRunId:99,integrationResult:'skipped',geographyResult:'success',
    proofRunId:44,proofRunAttempt:1,testedBase:f.base,testedCandidate:candidate,
    geographyReportLoader:async()=>({version:1,method_id:'worldatlas-trusted-geography-check-v1',baseline_commit:f.base,trusted_code_commit:f.base,
      candidate_commit:candidate,candidate_code_executed:false,published:false,source_approval:false,gate_status:'passed',status:'not-applicable'})});
  return f;
}
test('real prepare and cold final-capacity consumer measure selected metadata and reuse actual narrowed proof at exact capacity',async()=>{
  const preparedFixture=mergeFixture(), prepared=await prepareIntegration(preparedFixture.options);
  assert.equal(prepared.profile,'full');assert.equal(prepared.test_selection,'selected-data');assert.deepEqual(prepared.shards,[0]);
  assert.equal(prepared.proof.test_selection,'selected-data');
  // A separate final-phase fixture has no cross-job byte cache or evidence overlap.
  const first=mergeFixture(),result=await first.complete();assert.equal(result.accepted,true);assert.equal(first.writes.length,1);
  assert(result.final_capacity.proof_calls>10,'classifier reads missing from actual planning inventory');
  const exact=mergeFixture({capacity:result.final_capacity.required}),accepted=await exact.complete();
  assert.equal(accepted.accepted,true);assert.equal(exact.writes.length,1);
  assert(exact.afterCalls<=accepted.final_capacity.validation_call_bound);
});
test('actual capacity-enabled selected proof rechecks required consumer steps after waiting before any write',async()=>{
  const f=mergeFixture({afterWait:f=>{f.jobs.find(job=>job.name==='package').steps.at(-1).conclusion='failure';}});
  await assert.rejects(f.complete(),/proof is no longer valid/);assert.equal(f.writes.length,0);
});
