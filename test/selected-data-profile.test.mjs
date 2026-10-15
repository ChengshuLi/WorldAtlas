import {readFileSync} from 'node:fs';
import {gzipSync, gunzipSync, crc32} from 'node:zlib';
import {CHECKPOINT_MEMBERS} from '../scripts/geographic-report-artifact.mjs';
import {renderWorkerResult} from '../scripts/worker-result.mjs';
import {memoizeImmutableGitBlobs} from '../scripts/immutable-git-blobs.mjs';
import {isDeepStrictEqual as same} from "node:util";
import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {verifyIssueScope} from '../scripts/issue-claim-contract.mjs';
import {checkPremergeEvidence} from '../scripts/premerge-evidence.mjs';
import {prepareIntegration, completeIntegration} from '../scripts/merge-integration.mjs';
import {integrationProfile, selectedDataSelection, selectedDataCandidate, validateSelectedExpectations, SELECTED_SMOKE} from '../scripts/integration-profile.mjs';
const prefix = 'coordination/engineering/fixture-delivery/';
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
// Real ordinary ZIP records exercise the existing authenticated fixed-member
// parser. These small products establish only structural profile eligibility.
function checkpointZip(members) {
  const locals=[],centrals=[];let offset=0;
  for(const [name,body] of members){
    const n=Buffer.from(name),l=Buffer.alloc(30),c=Buffer.alloc(46),crc=crc32(body);
    l.writeUInt32LE(0x04034b50);l.writeUInt16LE(20,4);l.writeUInt32LE(crc,14);
    l.writeUInt32LE(body.length,18);l.writeUInt32LE(body.length,22);l.writeUInt16LE(n.length,26);
    c.writeUInt32LE(0x02014b50);c.writeUInt16LE(0x0314,4);c.writeUInt16LE(20,6);c.writeUInt32LE(crc,16);
    c.writeUInt32LE(body.length,20);c.writeUInt32LE(body.length,24);c.writeUInt16LE(n.length,28);c.writeUInt32LE(offset,42);
    locals.push(l,n,body);centrals.push(c,n);offset+=l.length+n.length+body.length;
  }
  const central=Buffer.concat(centrals),end=Buffer.alloc(22);end.writeUInt32LE(0x06054b50);
  end.writeUInt16LE(members.length,8);end.writeUInt16LE(members.length,10);
  end.writeUInt32LE(central.length,12);end.writeUInt32LE(offset,16);
  return Buffer.concat([...locals,central,end]);
}
function fixture({mutate = () => {}, packetPrefix = prefix} = {}) {
  const prefix = packetPrefix;
  const blobs = new Map(), baseline = {entries:new Map()}, authored = {entries:new Map()}, reads=[];
  const put = (name, value, old=false) => {
    const bytes = Buffer.isBuffer(value) ? value : Buffer.from(typeof value === 'string' ? value : JSON.stringify(value));
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
  const oldLedger=put('coordination/engineering/prior/ledger.json',{rows:[]},true);
  const oldSidecar=put('coordination/engineering/prior/sidecar.json',{authority_registry:oldRegistry,logical_asset_map:{ledger:oldLedger}},true);
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
  f.run=(options={})=>selectedDataSelection({api:f.api,repo:'owner/repo',branch:'engineering/fixture-delivery',files:f.files,baseline,authored,...options});
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
  'base grid change':f=>{const selection=JSON.parse(f.blobs.get(f.authored.entries.get('data/ownership-selection.json').sha));
    f.put('data/ownership-selection.json',{...selection,sha256:'f'.repeat(64)});},
  'mixed renderer change':f=>f.put('src/pixel-ownership.js','export default "changed renderer";'),
  'mixed prepared content change':f=>f.put('data/ownership-history/index.json',{changed:true}),
  'mixed canonical input change':f=>f.put('data/canonical-grid/manifest.json',{changed:true}),
}))test('selected-data falls back to full for '+name,async()=>assert.equal(await fixture({mutate}).run(),null));
test('rename/copy/removal origins never use selected routing',async()=>{
  for(const delta of [{previous_filename:'src/code.js'},{status:'removed'},{status:'renamed'}]){const f=fixture();Object.assign(f.files.find(row=>row.filename.endsWith('patch.json')),delta);assert.equal(await f.run(),null);}
});
test('whole-ledger expectation check rejects duplicate batches/members and foreign fields',()=>{
  for(const mutate of [e=>e.cohorts.push(structuredClone(e.cohorts[0])),e=>e.foreign=true,e=>e.cohorts[0].members[0].foreign=true]){
    const f=fixture();mutate(f.expected);assert.throws(()=>validateSelectedExpectations(f.expected,f.ledgerBody,f.expected.selected_ledger_sha256));
  }
});

function gateFixture(f=fixture()) {
  const base='b'.repeat(40), head='c'.repeat(40), root='/repos/owner/repo';
  const issue={number:10,state:'open',created_at:'2020-01-01T00:00:00Z',labels:['type:engineering','kind:work-item','status:ready'],
    body:'<!-- worldatlas-work:v1\n'+JSON.stringify({max_prs:2,depends_on:[],mode:'engineering',scope:'Exact unchanged-method selected data',...(f.evidenceQuality ? {evidence_quality:f.evidenceQuality} : {}),...(f.ownedPaths || f.sourceState ? {owned_paths:f.ownedPaths ?? [administrativePath]} : {})})+'\n-->'};
  const claim={version:1,active:true,issue_number:10,worker_id:'author',claim_id:'selected-claim',branch:f.branch??'engineering/fixture-delivery',mode:'engineering',expires_at:'2099-01-01T00:00:00Z'};
  const pr={number:20,state:'open',changed_files:f.files.length,body:'Refs #10',head:{sha:head,ref:claim.branch,repo:{full_name:'owner/repo'}},
    base:{sha:base,ref:'main',repo:{full_name:'owner/repo'}}};
  f.baseline.object={sha:base};
  if(f.sourceState)claim.owned_paths=[administrativePath];
  const blobAPI=f.api;
  f.api=async route=>{
    if(route===root+'/pulls/20')return structuredClone(pr);
    if(route.startsWith(root+'/pulls/20/files?per_page=100&page=')){const page=Number(route.split('=').at(-1));return f.files.slice((page-1)*100,page*100);}
    if(route===root+'/issues/10')return issue;
    if(route===root+'/issues/10/comments?per_page=100&page=1')return [{id:1,user:{login:'github-actions[bot]'},body:'**Worker reservation:** claimed\n\n<!-- worldatlas-claim:v1\n'+JSON.stringify(claim)+'\n-->'}];
    if(route===root+'/issues/10/timeline?per_page=100&page=1')return [];
    if(route===root+'/git/commits/'+base)return {sha:base,tree:{sha:'base-tree'}};
    if(route===root+'/git/commits/'+head)return {sha:head,tree:{sha:'head-tree'}};
    if(route===root+'/git/trees/base-tree?recursive=1')return {tree:[...f.baseline.entries.values()],truncated:false};
    if(route===root+'/git/trees/head-tree?recursive=1')return {tree:[...f.authored.entries.values()],truncated:false};
    if(route===root+'/contents/.github/package-inputs.json?ref='+base){const row=f.baseline.entries.get('.github/package-inputs.json');return {type:'file',path:row.path,sha:row.sha,size:row.size,encoding:'base64',content:f.blobs.get(row.sha).toString('base64')};}
    return blobAPI(route);
  };
  f.event={repository:{full_name:'owner/repo'},pull_request:pr};f.claim=claim;f.pr=pr;f.issue=issue;f.base=base;f.head=head;
  f.select=async()=>{
    const prepared=await prepareIntegration(mergeFixture({selectedFixture:f,gateReady:true}).options);
    return {profile:prepared.profile,shards:prepared.shards??(prepared.profile==='full'?[0,1,2]:[0]),
      ...(prepared.test_selection?{test_selection:prepared.test_selection,expectations_path:prepared.expectations_path}:{}),
      geography_software:prepared.geography_software};
  };
  return f;
}
test('actual queue classification validates current issue authority without author jobs',async()=>{
  const f=gateFixture();
  assert.equal((await f.select()).test_selection,'selected-data');
  f.claim.active=false;assert.equal((await f.select()).test_selection,'selected-data');
  f.issue.state='closed';await assert.rejects(f.select());
});
test('actual selector retains all three shards when accepted smoke or complete expectations are unavailable',async()=>{
  for(const mutate of [f=>f.baseline.entries.delete(SELECTED_SMOKE),f=>f.blobs.delete(f.authored.entries.get(prefix+'selected-delivery-expectations.json').sha)]){
    const f=gateFixture();mutate(f);assert.deepEqual(await f.select(),{profile:'full',shards:[0,1,2],geography_software:false});
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

function mergeFixture({selectedFixture,gateReady=false} = {}) {
  const f=gateReady?selectedFixture:gateFixture(selectedFixture), candidate='9'.repeat(40), root='/repos/owner/repo';
  Object.assign(f.pr,{draft:false,merged:false,title:'Synthetic selected delivery',mergeable:true,merge_commit_sha:candidate});
  const source=f.api;f.mergeReads=[];f.writes=[];
  f.api=async(route,method='GET',body)=>{
    f.mergeReads.push(route);
    if(method==='PUT'){f.writes.push(body);return {merged:true,sha:'f'.repeat(40)};}
    if(route===root+'/git/refs'&&method==='POST')return {ref:body.ref};
    if(route===root+'/merges'&&method==='POST'){assert.notEqual(body.base,'main');assert.equal(body.head,f.head);return {sha:candidate};}
    if(route===root+'/git/ref/heads/main')return {object:{sha:f.base}};
    if(route===root+'/git/commits/'+candidate)return {sha:candidate,tree:{sha:'head-tree'},parents:[{sha:f.base},{sha:f.head}]};
    if(route.includes('/check-runs'))return {check_runs:['scope',...(f.evidenceQuality?['evidence']:[])].map((name,id)=>({id:id+1,name,status:'completed',conclusion:'success',app:{id:1}}))};
    if(route===root+'/commits/'+f.head+'/status')return {statuses:[]};
    if(route.includes('/actions/runs/99/artifacts'))return {total_count:0,artifacts:[]};
    return source(route);
  };
  f.options={api:f.api,repo:'owner/repo',number:20,expectedHead:f.head,policy:{version:1,mode:'enforce-new',activation_time:'2100-01-01T00:00:00Z'},
    evidenceCheck:async()=>({status:'legacy'}),integrationRequestId:'selected-candidate-test-request'};
  f.complete=(overrides={})=>completeIntegration({...f.options,integrationResult:'success',geographyResult:'success',
    testedBase:f.base,testedCandidate:candidate,
    geographyReportLoader:async()=>({version:1,method_id:'worldatlas-trusted-geography-check-v1',baseline_commit:f.base,trusted_code_commit:f.base,
      candidate_commit:candidate,candidate_code_executed:false,published:false,source_approval:false,gate_status:'passed',status:'not-applicable'}),...overrides});
  return f;
}
test('real selected prepare has no author proof and final merge accepts the fresh composed candidate',async()=>{
  const preparedFixture=mergeFixture(), prepared=await prepareIntegration(preparedFixture.options);
  assert.equal(prepared.profile,'full');assert.equal(prepared.test_selection,'selected-data');assert.deepEqual(prepared.shards,[0]);
  assert(!('proof' in prepared));assert(!('geography_proof' in prepared));
  // A separate final-phase fixture has no cross-job byte cache or evidence overlap.
  const first=mergeFixture(),result=await first.complete();assert.equal(result.accepted,true);assert.equal(first.writes.length,1);
  assert(!first.mergeReads.some(route=>route.includes('/actions/')), 'No speculative proof or artifact discovery');
});
test('selected-data refuses absent, failed, skipped or stale final candidate checks before any merge',async()=>{
  for(const integrationResult of [undefined,'failure','cancelled','skipped']){
    const f=mergeFixture();await assert.rejects(f.complete({integrationResult}),/Integration tests|successful isolated/);assert.equal(f.writes.length,0);
  }
  for(const geographyResult of [undefined,'failure','cancelled','skipped']){
    const f=mergeFixture();await assert.rejects(f.complete({geographyResult}),/geography check/);assert.equal(f.writes.length,0);
  }
  for(const overrides of [{testedBase:'e'.repeat(40)}, {testedCandidate:'e'.repeat(40)}, {integrationResult:'skipped',proofRunId:44,proofRunAttempt:1}]){
    const f=mergeFixture();await assert.rejects(f.complete(overrides));assert.equal(f.writes.length,0);
  }
});

// Retained real UKR metadata, not an idealized two-row ledger. Only a new hook,
// reviewed expectations and exact package append are synthesized for eligibility;
// no new repair or scientific output is constructed or published.
function retainedUKRFixture() {
  const blobs=new Map(), parsed=new Map(), pins=new Map();
  const readOriginal=name=>{
    if(parsed.has(name))return parsed.get(name);
    const bytes=execFileSync('git',['show','HEAD:'+name],{maxBuffer:4*1024*1024,env:{...process.env,GIT_NO_LAZY_FETCH:'1'}});
    const oid=createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex');blobs.set(oid,bytes);
    pins.set(name,{path:name,bytes:bytes.length,sha256:digest(bytes),git_blob_oid:oid,mode:'100644'});
    const value=JSON.parse(bytes);parsed.set(name,value);return value;
  };
  const stem='coordination/engineering/melanesia363-additive-delivery-20261010/ukraine-original-batch-20261010/';
  const sidecar=readOriginal(stem+'selected-release-001/selection-sidecar.json');
  const ledger=readOriginal(sidecar.logical_asset_map.ledger.path),registry=readOriginal(sidecar.authority_registry.path);
  assert.equal(digest(blobs.get(pins.get(sidecar.logical_asset_map.ledger.path).git_blob_oid)),
    '72f5b366ab03e13274f5f682624c740a183eb09aa9f02d6b056cb7bda3f7bc6e');
  assert.equal(ledger.rows.length,44);
  const certificate=readOriginal(ledger.current_rebind.path);
  const collect=value=>{if(!value||typeof value!=='object')return;
    if(value.path&&value.git_blob_oid&&value.bytes!==undefined)pins.set(value.path,value);
    for(const child of Object.values(value))collect(child);
  };
  for(const value of [sidecar,ledger,registry,certificate])collect(value);
  const names=[...pins.keys()],rows=execFileSync('git',['ls-tree','HEAD','--',...names],{encoding:'utf8',maxBuffer:1024*1024,env:{...process.env,GIT_NO_LAZY_FETCH:'1'}}).trim().split('\n');
  const baseline={entries:new Map()},authored={entries:new Map()};
  for(const line of rows){const m=/^(\d+) (\w+) ([a-f0-9]+)\t(.+)$/.exec(line);assert(m,line);const pin=pins.get(m[4]);
    assert.equal(m[1],pin.mode);assert.equal(m[3],pin.git_blob_oid);baseline.entries.set(m[4],{path:m[4],type:m[2],mode:m[1],sha:m[3],size:pin.bytes});}
  for(const [name,row] of baseline.entries)authored.entries.set(name,{...row});
  const put=(name,value,old=false)=>{const bytes=Buffer.from(typeof value==='string'?value:JSON.stringify(value)),sha=createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex');
    blobs.set(sha,bytes);const row={path:name,mode:'100644',type:'blob',sha,size:bytes.length};authored.entries.set(name,row);if(old)baseline.entries.set(name,row);
    return {path:name,bytes:bytes.length,sha256:digest(bytes)};};
  put(SELECTED_SMOKE,'// fixture: generic helper accepted unchanged on future baseline',true);
  const oldHook=pins.get(stem+'selected-release-001/selection-sidecar.json');
  put('data/ownership-selection.json',{...sidecar.base_selection,additive_release:{path:oldHook.path,bytes:oldHook.bytes,sha256:oldHook.sha256}},true);
  const definition=readOriginal('.github/package-inputs.json');put('.github/package-inputs.json',definition,true);
  const hook=put(prefix+'selection-sidecar.json',sidecar);put('data/ownership-selection.json',{...sidecar.base_selection,additive_release:hook});
  const active=ledger.rows.filter(row=>['assigned','zero-cell'].includes(row.disposition));
  assert.equal(active.length,36);const expected={version:1,selected_ledger_sha256:sidecar.logical_asset_map.ledger.sha256,cumulative_native_cells:353,
    cohorts:[{original_batch_id:'retained-active-roster-fixture',component_ids:active.map(row=>row.component_id),members:active.map(row=>Object.fromEntries(['component_id','target_id','disposition','geometry_sha256'].map(key=>[key,row[key]])))}]};
  put(prefix+'selected-delivery-expectations.json',expected);put('.github/package-inputs.json',{...definition,inputs:[...definition.inputs,hook.path]});
  const files=[...authored.entries].filter(([name,row])=>baseline.entries.get(name)?.sha!==row.sha).map(([filename])=>({filename,status:baseline.entries.has(filename)?'modified':'added'}));
  const api=async route=>{const oid=route.split('/').at(-1),bytes=blobs.get(oid);assert(bytes,'unexpected opaque read '+route);return {sha:oid,size:bytes.length,encoding:'base64',content:bytes.toString('base64')};};
  return {ledger,expected,sidecar,run:()=>selectedDataSelection({api,repo:'owner/repo',branch:'engineering/fixture-delivery',files,baseline,authored})};
}
test('actual retained44-row UKR graph admits36 active rows while preserving6 held and2 rejected rows',async()=>{
  const f=retainedUKRFixture();assert.ok(await f.run());
  assert.doesNotThrow(()=>validateSelectedExpectations(f.expected,f.ledger,f.sidecar.logical_asset_map.ledger.sha256,f.ledger));
  for(const disposition of ['awaiting-evidence','rejected']){
    const candidate=structuredClone(f.ledger);candidate.rows=candidate.rows.filter(row=>row!==candidate.rows.find(row=>row.disposition===disposition));
    assert.throws(()=>validateSelectedExpectations(f.expected,candidate,f.sidecar.logical_asset_map.ledger.sha256,f.ledger),/held\/rejected/);
  }
  const partial=structuredClone(f.expected);partial.cohorts[0].members.pop();partial.cohorts[0].component_ids.pop();
  assert.throws(()=>validateSelectedExpectations(partial,f.ledger,f.sidecar.logical_asset_map.ledger.sha256,f.ledger),/omit selected members/);
});

// Replay actual retained SOURCE request/facts/handoff/catalogue/report and all
// declared inputs inside a synthetic next-selection delta. No scientific result
// is regenerated: only registry history, the new authority locator and package
// declarations model the classifier boundary under test.
const administrativePath = 'coordination/engineering/melanesia363-additive-delivery-20261010/accepted-administrative-handoffs.json';
const corpusPath = 'coordination/engineering/original-geography-source-corpus-20261006/';
let sourceSpecimen;
function actualSourceSpecimen() {
  if (sourceSpecimen) return sourceSpecimen;
  const bodies = new Map(), documents = new Map(), paths = new Set();
  const raw = name => {
    const bytes = execFileSync('git', ['show', 'HEAD:' + name], {maxBuffer:32*1024*1024, env:{...process.env,GIT_NO_LAZY_FETCH:'1'}});
    bodies.set(createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex'), bytes);return bytes;
  };
  const json = name => {const value=JSON.parse(raw(name));documents.set(name,value);paths.add(name);return value;};
  const stem='coordination/engineering/melanesia363-additive-delivery-20261010/ukraine-original-batch-20261010/';
  const authority=json(stem+'selected-authority/authority-binding.json');
  const issued=json(authority.original_pins.source_request.path),facts=json(authority.original_pins.source_facts.path);
  json(authority.original_pins.native_request.path);
  const registry=json(administrativePath),registration=registry.entries.find(row=>row.source.path===issued.source_rule.cases_path);
  assert(registration);const handoff=json(registration.source.path);
  const catalogue=json(issued.source_rule.source_catalogue_path),report=json(issued.report.path);
  assert.equal(authority.original_pins.source_request.sha256,'b43f9d4bf6c5b5b9f8c957bb137e1a2eae06ab66f2fa79a0c501c405775eb768');
  assert.equal(registration.source.sha256,'7fd3d6da63c1fc9890784a6db6e4a3e9fb55755d52bb3c3a45cf0ad8a7f32462');
  const collect=value=>{if(!value||typeof value!=='object')return;
    if(typeof value.path==='string'&&Number.isSafeInteger(value.bytes)&&!value.path.startsWith('.')&&!value.path.startsWith('/'))paths.add(value.path);
    for(const child of Object.values(value))collect(child);
  };
  for(const value of documents.values())collect(value);
  const output=execFileSync('git',['ls-tree','-l','HEAD','--',...paths],{encoding:'utf8',maxBuffer:4*1024*1024,env:{...process.env,GIT_NO_LAZY_FETCH:'1'}});
  const entries=new Map();
  for(const line of output.trim().split('\n')) {
    const match=/^(\d+) (\w+) ([a-f0-9]+)\s+(\d+)\t(.+)$/.exec(line);
    if(match)entries.set(match[5],{path:match[5],mode:match[1],type:match[2],sha:match[3],size:Number(match[4])});
  }
  // The two whole restored bodies are encoded data, never decoded or executed.
  const physical=handoff.consumed_inputs.filter(row=>/\/(?:components|sources)-\d{3}\.jsonl\.gz$/.test(row.path));
  assert.equal(physical.length,2);for(const row of physical)raw(row.path);
  for(const row of issued.source_rule.administrative_products)raw(row.path);
  return sourceSpecimen={bodies,documents,entries,authority,issued,facts,registry,registration,handoff,catalogue,report,physical};
}
function retainedSourceFixture({format='v1',additionalRegistryEntries=[],mutate=()=>{}}={}) {
  const actual=actualSourceSpecimen(),documents=new Map([...actual.documents].map(([name,value])=>[name,structuredClone(value)]));
  const authority=structuredClone(actual.authority),issued=documents.get(authority.original_pins.source_request.path),
    facts=documents.get(authority.original_pins.source_facts.path),registry=documents.get(administrativePath),
    registration=registry.entries.find(row=>row.id===actual.registration.id),handoff=documents.get(registration.source.path);
  // This historical UKR fixture models one registration appended to an empty
  // registry, not the eligibility of every current or future HEAD registration.
  // Keep its retained specimen isolated as unrelated real deliveries accumulate.
  registry.entries.push(...structuredClone(additionalRegistryEntries));
  assert.equal(registry.entries.filter(row=>row.id===registration.id).length,1);
  registry.entries=[registration];
  const f=fixture({mutate:f=>{
    for(const [oid,bytes] of actual.bodies)f.blobs.set(oid,bytes);
    for(const [name,row] of actual.entries)if(!f.baseline.entries.has(name)){f.baseline.entries.set(name,{...row});f.authored.entries.set(name,{...row});}
    f.policy.inputs.push(administrativePath);f.put('.github/package-inputs.json',f.policy,true);
    f.put(administrativePath,{...registry,entries:[]},true);
    // Explicit v2 schema fixture only. Its input is not a genuine accepted v2
    // packet and cannot establish production adoption or scientific acceptance.
    if(format==='v2'){
      registration.format='source-native-execution-cohort-v2';delete registration.original_batch_id;delete registration.original_component_count;
      handoff.execution_cohort_id=registration.id;
      handoff.original_gap_membership={version:1,index:{path:'data/original-gap-index.json',mode:'100644',commit:'a'.repeat(40),blob:'b'.repeat(40),bytes:100,sha256:'c'.repeat(64)},
        members:registration.cohort_ids.map(component_id=>({component_id,original_batch_id:actual.registration.original_batch_id,original_family_id:'retained-family-schema-fixture'}))};
    }
    const packageRoles=[registration.source.path,issued.source_rule.source_catalogue_path,
      ...issued.source_rule.administrative_products.map(row=>row.path),...actual.physical.map(row=>row.path)];
    const state={f,authority,issued,facts,registry,registration,handoff,documents,packageRoles,comparison:'ahead'};
    Object.assign(f,{sourceState:state});
    mutate(state);
    // Refresh only synthetic candidate bindings after deliberate fixture edits;
    // every unaltered document/encoded payload keeps its real original bytes.
    const write=(name,value,old=false)=>{
      const original=actual.documents.get(name);
      if(same(value,original)){
        const row=actual.entries.get(name);f.authored.entries.set(name,{...row});if(old)f.baseline.entries.set(name,{...row});
        return {path:name,mode:row.mode,git_blob_oid:row.sha,bytes:row.size,sha256:digest(actual.bodies.get(row.sha)),commit:registration.accepted_source_commit};
      }
      return f.put(name,value,old);
    };
    const sourcePin=write(registration.source.path,handoff,true);
    // Source acceptance in this fixture is an exact mocked immutable commit,
    // independent of whether the format is retained v1 or schema-only v2.
    Object.assign(registration.source,{blob:sourcePin.git_blob_oid,bytes:sourcePin.bytes,sha256:sourcePin.sha256});
    const sourceInput=issued.source_rule.inputs.find(row=>row.path===registration.source.path);
    Object.assign(sourceInput,{blob:sourcePin.git_blob_oid,bytes:sourcePin.bytes,sha256:sourcePin.sha256});
    const registryPin=write(administrativePath,registry);
    const registryInput=issued.source_rule.inputs.find(row=>row.path===administrativePath);
    Object.assign(registryInput,{blob:registryPin.git_blob_oid,bytes:registryPin.bytes,sha256:registryPin.sha256});
    const requestPin=write(authority.original_pins.source_request.path,issued,true);
    Object.assign(authority.original_pins.source_request,{git_blob_oid:requestPin.git_blob_oid,bytes:requestPin.bytes,sha256:requestPin.sha256});
    Object.assign(facts.request,{blob:requestPin.git_blob_oid,bytes:requestPin.bytes,sha256:requestPin.sha256});
    facts.source_rule=structuredClone(issued.source_rule);
    facts.input_descriptors=structuredClone([issued.report,...issued.source_rule.inputs,...issued.baseline.pins]);
    state.afterFacts?.(facts);
    const factsPin=write(authority.original_pins.source_facts.path,facts,true);
    Object.assign(authority.original_pins.source_facts,{git_blob_oid:factsPin.git_blob_oid,bytes:factsPin.bytes,sha256:factsPin.sha256});
    for(const alias of authority.source_output_aliases??[])if(alias.published.path===factsPin.path){
      Object.assign(alias.published,{git_blob_oid:factsPin.git_blob_oid,bytes:factsPin.bytes,sha256:factsPin.sha256});
      Object.assign(alias.original,{bytes:factsPin.bytes,sha256:factsPin.sha256});
    }
    const source_authority=f.put(prefix+'source-authority.json',authority),rule_preimage=f.leaf('source-rule.json');
    f.registryBody.entries.push({authority_sha256:source_authority.sha256,policy_id:'retained-source-literal-additions',policy_version:1,
      source_authority,rule_preimage,rule_sha256:rule_preimage.sha256});refreshPins(f);
    f.definition.inputs.push(...packageRoles);f.put('.github/package-inputs.json',f.definition);
  }});
  f.baseline.object={sha:'d'.repeat(40)};
  const original=f.api;const state=f.sourceState;
  const sourceTree={truncated:false,tree:[{...f.baseline.entries.get(state.registration.source.path)}]};
  f.api=async route=>{
    if(route===`/repos/owner/repo/compare/${state.registration.accepted_source_commit}...${f.baseline.object.sha}`)return {status:state.comparison};
    if(route===`/repos/owner/repo/git/commits/${state.registration.accepted_source_commit}`)return {sha:state.registration.accepted_source_commit,tree:{sha:'accepted-source-tree'}};
    if(route==='/repos/owner/repo/git/trees/accepted-source-tree?recursive=1')return sourceTree;
    return original(route);
  };
  return {...f,sourceTree};
}

test('retained complete v1 SOURCE graph admits registry append and exact already-on-main package inputs',async()=>{
  const f=retainedSourceFixture();assert.ok(await f.run());
  for(const name of f.sourceState.packageRoles)assert(f.baseline.entries.has(name));
  assert(f.sourceState.handoff.consumed_inputs.some(row=>row.path.endsWith('.py')),'negative executable example is present');
  assert(!f.sourceState.packageRoles.some(name=>name.startsWith('.cache/')||name.endsWith('.py')));
  const bytes=[...new Set(f.reads)].reduce((sum,oid)=>sum+f.blobs.get(oid).length,0);
  assert(bytes<16*1024*1024);assert(f.reads.length<256);
});
test('explicit v2 schema fixture admits preserved original membership without claiming genuine v2 adoption',async()=>{
  assert.ok(await retainedSourceFixture({format:'v2'}).run());
});

for(const format of ['v1','v2'])test('historical SOURCE '+format+' fixture is isolated from unrelated HEAD registry growth',async()=>{
  // An unrelated future schema/location must not silently become part of the
  // UKR fixture. This does not assert fast-route eligibility for that new entry.
  const unrelated={id:'unrelated-future-registration',format:'future-format',
    source:{path:'coordination/engineering/other/handoff.json'}};
  const f=retainedSourceFixture({format,additionalRegistryEntries:[unrelated]});
  assert.deepEqual(f.sourceState.registry.entries,[f.sourceState.registration]);
  const old=JSON.parse(f.blobs.get(f.baseline.entries.get(administrativePath).sha));
  assert.deepEqual(old.entries,[]);
  assert.ok(await f.run());
});

for(const [name,mutate] of Object.entries({
  'foreign registry field':x=>{x.registry.module='unreviewed.mjs';},
  'foreign entry field':x=>{x.registration.module='unreviewed.mjs';},
  'unknown entry format':x=>{x.registration.format='future-unapproved-format';},
  'mixed v1/v2 keys':x=>{x.registration.format='source-native-execution-cohort-v2';},
  'duplicate registration ID':x=>{x.registry.entries.push({...structuredClone(x.registration)});},
  'duplicate registered source':x=>{x.registry.entries.push({...structuredClone(x.registration),id:'other'});},
  'unselected registration append':x=>{x.registry.entries.push({...structuredClone(x.registration),id:'other',original_batch_id:'other',cohort_ids:['other'],source:{...x.registration.source,path:'research/geography/other/unselected.json'}});},
  'wrong accepted source commit':x=>{x.registration.accepted_source_commit='1'.repeat(40);},
  'unaccepted source ancestry':x=>{x.comparison='diverged';},
  'wrong cohort membership':x=>{x.registration.cohort_ids=['foreign'];},
  'wrong target membership':x=>{x.registration.target_ids=['foreign'];},
  'wrong original batch':x=>{x.handoff.original_batch_id='foreign';},
  'incomplete handoff roster':x=>{x.handoff.scopeIds=[];},
  'different SOURCE profile':x=>{x.issued.source_rule.profile='unreviewed';},
  'partial geometry scope':x=>{x.issued.source_rule.geometry_scope='fragment';},
  'wrong registry locator':x=>{x.issued.source_rule.registry_path='coordination/engineering/foreign/registry.json';},
  'wrong outcome locator':x=>{x.issued.source_rule.outcomes_path='research/geography/other/handoff.json';},
  'foreign catalogue locator':x=>{x.issued.source_rule.source_catalogue_path='data/foreign.json';},
  'facts request mismatch':x=>{x.afterFacts=f=>{f.request.sha256='0'.repeat(64);};},
  'facts rule mismatch':x=>{x.afterFacts=f=>{f.source_rule.geometry_scope='fragment';};},
  'facts input omission':x=>{x.afterFacts=f=>{f.input_descriptors.pop();};},
  'facts input injection':x=>{x.afterFacts=f=>{f.input_descriptors.push({path:'scripts/unreviewed.mjs'});};},
  'wrong administrative decoded identity':x=>{x.issued.source_rule.administrative_products[0].uncompressed_sha256='0'.repeat(64);},
  'unreferenced administrative payload':x=>{x.issued.source_rule.administrative_products[0].path=corpusPath+'payloads/unreferenced.bin.gz';},
  'wrong restored encoded identity':x=>{x.handoff.physical_restoration.restorations[0].whole_original_sha256='0'.repeat(64);},
  'wrong restored decoded identity':x=>{x.handoff.physical_restoration.restorations[0].decoded_sha256='0'.repeat(64);},
  'absent restoration':x=>{x.handoff.physical_restoration.restorations.shift();},
  'ambiguous restoration':x=>{x.handoff.physical_restoration.restorations.push({...x.handoff.physical_restoration.restorations[0]});},
  'ambiguous retained physical input':x=>{x.handoff.consumed_inputs.push({...x.handoff.consumed_inputs.find(row=>row.path.endsWith('/components-030.jsonl.gz'))});},
  'foreign retained physical input':x=>{x.handoff.consumed_inputs.find(row=>row.path.endsWith('/components-030.jsonl.gz')).path='research/geography/foreign/components-030.jsonl.gz';},
  'cache declaration':x=>{x.packageRoles.push(x.issued.source_rule.original_products[0].path);},
  'consumed executable declaration':x=>{x.packageRoles.push(x.handoff.consumed_inputs.find(row=>row.path.endsWith('.py')).path);},
  'undeclared same-folder data':x=>{x.packageRoles.push(x.handoff.consumed_inputs.find(row=>row.path.endsWith('/original-component.json')).path);},
  'source directory declaration':x=>{x.packageRoles.push(x.registration.source.path.split('/').slice(0,-1).join('/'));},
}))test('SOURCE data eligibility refuses '+name,async()=>{
  const f=retainedSourceFixture({mutate});assert.equal(await f.run(),null,name);
});
for(const [name,mutate] of Object.entries({
  'wrong execution cohort':x=>{x.handoff.execution_cohort_id='foreign';},
  'membership omission':x=>{x.handoff.original_gap_membership.members=[];},
  'membership component drift':x=>{x.handoff.original_gap_membership.members[0].component_id='foreign';},
  'missing original family':x=>{delete x.handoff.original_gap_membership.members[0].original_family_id;},
  'foreign membership field':x=>{x.handoff.original_gap_membership.module='unreviewed';},
  'nonordinary original index':x=>{x.handoff.original_gap_membership.index.mode='120000';},
}))test('v2 schema-only eligibility refuses '+name,async()=>assert.equal(await retainedSourceFixture({format:'v2',mutate}).run(),null));

test('SOURCE additions refuse changed or newly introduced foreign baseline data and wrong accepted source tree',async()=>{
  for(const change of ['changed','mode','missing','accepted-source']){
    const f=retainedSourceFixture(),name=f.sourceState.packageRoles[0];
    if(change==='changed')f.authored.entries.get(name).sha='0'.repeat(40);
    if(change==='mode')f.authored.entries.get(name).mode='100755';
    if(change==='missing')f.baseline.entries.delete(name);
    if(change==='accepted-source')f.sourceTree.tree[0].sha='0'.repeat(40);
    assert.equal(await f.run(),null,change);
  }
});
test('registry changes preserve every original entry and cannot remove or rewrite earlier authority',async()=>{
  for(const change of ['rewrite','reorder','remove']){
    const f=retainedSourceFixture(),entry=f.sourceState.registration;
    const old={...structuredClone(entry),id:'prior',original_batch_id:'prior',cohort_ids:['prior'],source:{...entry.source,path:'research/geography/prior/handoff.json'}};
    const value={...f.sourceState.registry,entries:[old,entry]};
    const previous=change==='rewrite'?{...value,entries:[{...old,id:'rewritten'}]}:
      change==='reorder'?{...value,entries:[entry,old]}:{...value,entries:[old,entry,{...old,id:'missing',original_batch_id:'missing',cohort_ids:['missing'],source:{...old.source,path:'research/geography/missing/handoff.json'}}]};
    // This is a negative prefix control. A refreshed candidate SOURCE request
    // is unnecessary: either its pin or the original-prefix check must refuse.
    const candidate=f.authored.entries.get(administrativePath);f.put(administrativePath,previous,true);f.authored.entries.set(administrativePath,candidate);
    assert.equal(await f.run(),null,change);
  }
});

test('real SOURCE metadata entry and cold final merge preserve applicability',async()=>{
  const gate=gateFixture(retainedSourceFixture());
  assert.equal((await gate.select()).test_selection,'selected-data');
  const prep=mergeFixture({selectedFixture:retainedSourceFixture()}),prepared=await prepareIntegration(prep.options);
  assert.equal(prepared.test_selection,'selected-data');assert(!('proof' in prepared));assert(!('geography_proof' in prepared));
  const cold=mergeFixture({selectedFixture:retainedSourceFixture()}),result=await cold.complete();
  assert.equal(result.accepted,true);assert(!('proof' in result));
});

// Only mutable global metadata is snapshotted. Original delivery vintages stay
// in their retained repository paths and are checked against actual Git bodies.
const fixedRows=new Map(),fixedBlobs=new Map();
function fixedDeliveryFixture({leanPackage=false,fixtureName='selected-native-role-ci-1726.json'}={}) {
  const fixed=JSON.parse(readFileSync(new URL('./fixtures/'+fixtureName,import.meta.url))),
    files=structuredClone(fixed.files),added=new Set(files.filter(row=>row.status==='added').map(row=>row.filename)),
    blobs=new Map(fixedBlobs),reads=[],root='/repos/owner/repo';
  const git=(...args)=>execFileSync('git',args,{maxBuffer:32*1024*1024,env:{...process.env,GIT_NO_LAZY_FETCH:'1'}});
  const oid=bytes=>createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex');
  for(const snap of fixed.snapshots){const raw=Buffer.from(snap.body);assert.equal(raw.length,snap.bytes);assert.equal(digest(raw),snap.sha256);assert.equal(oid(raw),snap.git_blob_oid);blobs.set(snap.git_blob_oid,raw);}
  const rows=fixedRows;
  const repositoryRow=name=>{
    if(rows.has(name))return rows.get(name);
    const raw=git('ls-tree','HEAD','--',name).toString('utf8').trim(),match=/^(\d+) (\w+) ([a-f0-9]+)\t(.+)$/.exec(raw);
    if(!match)return undefined;
    const row={path:match[4],mode:match[1],type:match[2],sha:match[3],size:fixed.retained_tree_rows?.find(row=>row.path===name&&row.sha===match[3])?.size??Number(git('cat-file','-s',match[3]).toString())};rows.set(name,row);return row;
  };
  class RoleTree extends Map {
    constructor(commit){super();this.commit=commit;}
    get(name){
      if(super.has(name))return super.get(name);
      if(this.commit===fixed.base&&added.has(name))return undefined;
      const snapshot=fixed.snapshots.find(row=>row.commit===this.commit&&row.path===name);
      const row=snapshot?{path:name,mode:snapshot.mode,type:'blob',sha:snapshot.git_blob_oid,size:snapshot.bytes}:repositoryRow(name);
      if(row)super.set(name,{...row});return super.get(name);
    }
    has(name){return Boolean(this.get(name));}
  }
  const baseline={object:{sha:fixed.base},entries:new RoleTree(fixed.base)},authored={object:{sha:fixed.head},entries:new RoleTree(fixed.head)};
  for(const row of files){baseline.entries.get(row.filename);authored.entries.get(row.filename);}
  const api=async route=>{
    if(route.includes('/git/blobs/')){const sha=route.split('/').at(-1);if(!blobs.has(sha)){const raw=git('cat-file','blob',sha);blobs.set(sha,raw);fixedBlobs.set(sha,raw);}const bytes=blobs.get(sha);reads.push(sha);return {sha,size:bytes.length,encoding:'base64',content:bytes.toString('base64')};}
    if(route.startsWith(root+'/compare/'))return {status:'ahead'};
    if(route.startsWith(root+'/git/commits/')){const sha=route.split('/').at(-1);const source=fixed.accepted_sources.find(row=>row.commit===sha);assert(source,route);return {sha,tree:{sha:source.tree}};}
    if(route.startsWith(root+'/git/trees/')){const sha=route.split('/').at(-1).split('?')[0],source=fixed.accepted_sources.find(row=>row.tree===sha);assert(source,route);return {truncated:false,tree:[source.entry]};}
    throw Error('Unexpected fixed delivery API route '+route);
  };
  const put=(name,value,old=false)=>{const bytes=Buffer.from(typeof value==='string'?value:JSON.stringify(value)),sha=oid(bytes);blobs.set(sha,bytes);const row={path:name,mode:'100644',type:'blob',sha,size:bytes.length};authored.entries.set(name,row);if(old)baseline.entries.set(name,row);return {path:name,mode:'100644',git_blob_oid:sha,bytes:bytes.length,sha256:digest(bytes),commit:'a'.repeat(40)};};
  if(leanPackage){
    const policy=JSON.parse(blobs.get(baseline.entries.get('.github/package-inputs.json').sha));
    put('.github/package-inputs.json',{...policy,inputs:[...policy.inputs,...fixed.prospective_lean_package.inputs]});
  }
  const document=name=>{const row=authored.entries.get(name);if(!blobs.has(row.sha)){const raw=git('cat-file','blob',row.sha);blobs.set(row.sha,raw);fixedBlobs.set(row.sha,raw);}return JSON.parse(blobs.get(row.sha));};
  const f={fixed,files,branch:fixed.branch,baseline,authored,blobs,reads,api,put,document,sourceState:{}};
  f.run=(options={})=>selectedDataSelection({api:f.api,repo:'owner/repo',branch:f.branch,files:f.files,baseline,authored,...options});return f;
}
test('fixed complete COD/PHL package preparation declarations correctly retain full CI',async()=>{
  const f=fixedDeliveryFixture();assert.equal(selectedDataCandidate(f.branch,f.files),true);
  assert.equal(await f.run(),null); // Includes unconsumed preparation evidence and scripts/administrative.py.
  const operands=f.files.filter(row=>row.filename.endsWith('.bin.gz'));assert.equal(operands.length,7);
  for(const row of operands)assert(f.reads.includes(f.authored.entries.get(row.filename).sha));
});


test('new unconsumed supporting text is independent of document title',async()=>{
  const f=fixture({mutate:f=>f.put(prefix+'README.md','Retained delivery packet\n')});
  assert.equal((await f.run()).test_selection,'selected-data');
  f.definition.inputs.push(prefix+'README.md');f.put('.github/package-inputs.json',f.definition);
  assert.equal(await f.run(),null,'a packaged README is not inert supporting text');
});
for(const [label,change] of Object.entries({
  'NUL README':f=>f.put(prefix+'README.md','a\0b'),
  'executable README':f=>{f.put(prefix+'README.md','text');f.authored.entries.get(prefix+'README.md').mode='100755';},
  'symlink README':f=>{f.put(prefix+'README.md','text');f.authored.entries.get(prefix+'README.md').mode='120000';},
}))test('packet documentation falls back for '+label,async()=>assert.equal(await fixture({mutate:change}).run(),null));


test('supporting Markdown remains new, ordinary, in scope and outside actual consumer roles',async()=>{
  for(const name of ['notes.md','nested/README.md','review/independent-static-review.md']) {
    assert.equal((await fixture({mutate:f=>f.put(prefix+name,'support only\n')}).run()).test_selection,'selected-data');
  }
  for(const mutate of [
    f=>f.put('coordination/engineering/foreign/review.md','outside declared scope'),
    f=>{f.put(prefix+'review.md','old',true);f.put(prefix+'review.md','modified');},
    f=>{const row=f.put(prefix+'template.md',f.sidecarBody);f.put('data/ownership-selection.json',
      {...f.base,additive_release:{path:row.path,bytes:row.bytes,sha256:row.sha256}});},
    f=>f.put(prefix+'review.md',Buffer.from([0xff])),
    f=>{f.put(prefix+'review.md','text');f.authored.entries.get(prefix+'review.md').mode='100755';},
    f=>{f.put(prefix+'review.md','text');f.authored.entries.get(prefix+'review.md').mode='120000';},
  ]) assert.equal(await fixture({mutate}).run(),null);
  const renamed=fixture({mutate:f=>f.put(prefix+'review.md','text')});
  renamed.files.find(row=>row.filename===prefix+'review.md').previous_filename='src/runtime-template.md';
  assert.equal(await renamed.run(),null);
});

test('unchanged SOURCE opaque leaves retain exact baseline/candidate Git body and mode bindings',async()=>{
  for(const mutation of ['body','both-body','size','mode']){
    const f=retainedSourceFixture(),name=f.sourceState.packageRoles.find(name=>name.endsWith('.bin.gz'));
    assert(name);const row=f.authored.entries.get(name);
    if(mutation==='body'||mutation==='both-body')row.sha='0'.repeat(40);
    if(mutation==='both-body')f.baseline.entries.get(name).sha=row.sha;
    if(mutation==='size')row.size++;
    if(mutation==='mode')row.mode='100755';
    assert.equal(await f.run(),null,mutation);
  }
});
test('supporting records are validated incrementally without retaining cumulative evidence volume',async()=>{
  const plain=fixture(),ordinary={};assert(await plain.run({metadataDiagnostics:ordinary}));
  const f=fixture({mutate:f=>{for(let n=0;n<400;n++)f.put(prefix+'evidence-'+n+'.json',{n,body:'x'.repeat(48*1024)});}}),stats={};
  assert.equal((await f.run({metadataDiagnostics:stats})).test_selection,'selected-data');
  assert(stats.read_bytes>16*1024*1024);assert(stats.read_count>256);
  assert.equal(stats.retained_bytes,ordinary.retained_bytes);assert.equal(stats.retained_count,ordinary.retained_count);assert.equal(stats.transient_read_count,400);
  // A late bad record must still refuse after the other records have been checked.
  f.put(prefix+'evidence-399.json','{"unfinished":');assert.equal(await f.run({}),null);
});
test('inert supporting gzip validates every decoded JSONL record without granting package authority',async()=>{
  const f=fixture({mutate:f=>{
    f.put(prefix+'support.json.gz',gzipSync(JSON.stringify({inert:true})));
    f.put(prefix+'support.jsonl.gz',gzipSync('{"first":1}\n{"last":2}\n'));
  }}),stats={};
  assert.equal((await f.run({metadataDiagnostics:stats})).test_selection,'selected-data');assert(stats.decoded_bytes>0);
  f.definition.inputs.push(prefix+'support.jsonl.gz');f.put('.github/package-inputs.json',f.definition);
  assert.equal(await f.run(),null);
});
for(const [label,bytes] of Object.entries({
  'invalid gzip':Buffer.from('not a gzip body'),
  'malformed last JSONL record':gzipSync('{"first":1}\n{"last":'),
  'empty JSONL':gzipSync(''),
  'code in JSONL':gzipSync('{"first":1}\nprocess.exit()\n'),
  'blank interior record':gzipSync('{}\n\n{}\n'),
}))test('supporting gzip refuses '+label,async()=>{
  assert.equal(await fixture({mutate:f=>f.put(prefix+'support.jsonl.gz',bytes)}).run(),null);
});
test('supporting gzip validates complete concatenated members and rejects truncated tails',async()=>{
  const first=gzipSync('{"first":1}\n'),second=gzipSync('{"last":2}\n');
  const f=fixture({mutate:f=>f.put(prefix+'support.jsonl.gz',Buffer.concat([first,second]))});
  assert.equal((await f.run()).test_selection,'selected-data');
  f.put(prefix+'support.jsonl.gz',Buffer.concat([first,second.subarray(0,second.length-1)]));
  assert.equal(await f.run(),null);
});

test('prospective lean package keeps the actual COD/PHL scientific graph and selects targeted checks',async()=>{
  const f=fixedDeliveryFixture({leanPackage:true});
  assert.deepEqual(await f.run(),{test_selection:'selected-data',expectations_path:'coordination/engineering/congo-ago2018-delivery-20261011/selected-delivery-expectations.json',shards:[0]});
  const proof=f.fixed.prospective_lean_package.outer_reader,report=f.document(proof.path),reportRow=f.authored.entries.get(proof.path);
  assert.equal(reportRow.sha,proof.git_blob_oid);assert.equal(reportRow.size,proof.bytes);assert.equal(digest(f.blobs.get(reportRow.sha)),proof.sha256);
  const declared=f.document('.github/package-inputs.json').inputs,required=new Set(report.inventory.map(row=>row.path));
  for(const locator of f.fixed.authorities){
    const authority=f.document(locator.authority_path);required.add(locator.authority_path);
    Object.values(authority.original_pins).forEach(pin=>required.add(pin.path));
    for(const role of ['publication','inventory','operating'])required.add(authority.native_proof[role].path);
    authority.native_proof.assets.forEach(pin=>required.add(pin.path));
    const native=f.document(locator.native_request).additive,aliases=authority.source_output_aliases??[];
    for(const role of ['publication_path','inventory_path','operating_path']){
      const original=native.inputs.find(pin=>pin.path===native[role]);
      required.add((aliases.find(alias=>alias.original.path===original.path)?.published??original).path);
    }
    aliases.forEach(alias=>required.add(alias.published.path));
  }
  for(const name of required)assert(declared.some(input=>input===name||input.endsWith('/')&&name.startsWith(input)),name);
  assert.equal(f.fixed.prospective_lean_package.inputs.length,97);
  assert(f.fixed.prospective_lean_package.removed_preparation_only_inputs.includes('scripts/administrative.py'));
  const readBytes=[...new Set(f.reads)].reduce((sum,oid)=>sum+f.blobs.get(oid).length,0);
  assert(readBytes<=16*1024*1024);assert(f.reads.length<256);
});


// Synthetic malicious metadata only: rebind every enclosing exact JSON pin so
// the real native-role checks, rather than a stale outer hash, must refuse it.
function rewriteFixedNative(f,mutate,{factsMutate=()=>{}}={}) {
  const locator=f.fixed.authorities[0],authority=f.document(locator.authority_path),
    request=f.document(locator.native_request),facts=f.document(authority.original_pins.native_facts.path);
  mutate(request);
  const requestPin=f.put(locator.native_request,request);
  facts.request={...facts.request,...requestPin,blob:requestPin.git_blob_oid};
  facts.input_descriptors=[request.report,...request.additive.inputs,...request.baseline.pins];
  facts.source_predecessor=request.additive;factsMutate(facts);
  authority.original_pins.native_request=requestPin;
  authority.original_pins.native_facts=f.put(authority.original_pins.native_facts.path,facts);
  const authorityPin=f.put(locator.authority_path,authority),selection=f.document('data/ownership-selection.json'),
    side=f.document(selection.additive_release.path),registry=f.document(side.authority_registry.path);
  const entry=registry.entries.find(row=>row.source_authority.path===locator.authority_path);
  entry.source_authority=authorityPin;entry.authority_sha256=authorityPin.sha256;
  const registryPin=f.put(side.authority_registry.path,registry);
  const ledger=f.document(side.logical_asset_map.ledger.path),certificate=f.document(ledger.current_rebind.path),
    operating=f.document(certificate.operating.path),plan=f.document(operating.execution_custody.issued_plan.path);
  plan.original_inputs[0]=registryPin;
  operating.execution_custody.issued_plan=f.put(operating.execution_custody.issued_plan.path,plan);
  certificate.operating=f.put(certificate.operating.path,operating);certificate.authority_registry_sha256=registryPin.sha256;
  ledger.current_rebind=f.put(ledger.current_rebind.path,certificate);
  side.authority_registry=registryPin;side.logical_asset_map.ledger=f.put(side.logical_asset_map.ledger.path,ledger);
  const hook=f.put(selection.additive_release.path,side);
  selection.additive_release={path:hook.path,bytes:hook.bytes,sha256:hook.sha256};f.put('data/ownership-selection.json',selection);
  const expectedPath=f.files.find(row=>row.filename.endsWith('/selected-delivery-expectations.json')).filename,
    expected=f.document(expectedPath);expected.selected_ledger_sha256=side.logical_asset_map.ledger.sha256;f.put(expectedPath,expected);
}
for(const [label,mutate] of Object.entries({
  'native manifest descriptor':r=>{r.additive.owner_parts.find(p=>p.path.includes('/congo-ago2018-')).manifest_descriptor.sha256='0'.repeat(64);},
  'native inverse range':r=>{r.additive.owner_parts.find(p=>p.path.includes('/congo-ago2018-')).containing_inverse.inverse_ranges[0].start++;},
  'native bank member':r=>{r.additive.owner_parts.find(p=>p.path.includes('/congo-ago2018-')).containing_inverse.bank_member.offset++;},
  'native containing fragment':r=>{r.additive.owner_parts.find(p=>p.path.includes('/congo-ago2018-')).containing_inverse.whole_containing_fragments[0].blob='0'.repeat(40);},
  'native decoded length':r=>{r.additive.inputs.find(p=>p.path.includes('/congo-ago2018-')&&p.path.endsWith('.bin.gz')).uncompressed_bytes++;},
  'native operand encoded hash':r=>{r.additive.inputs.find(p=>p.path.includes('/congo-ago2018-')&&p.path.endsWith('.bin.gz')).sha256='0'.repeat(64);},
  'native input duplicate':r=>{r.additive.inputs.push(structuredClone(r.additive.inputs.find(p=>p.path.includes('/congo-ago2018-')&&p.path.endsWith('.bin.gz'))));},
}))test('fixed native role refuses rebound '+label,async()=>{
  const f=fixedDeliveryFixture({leanPackage:true});rewriteFixedNative(f,mutate);assert.equal(await f.run(),null);
});
test('fixed native role refuses facts input omission after outer pin rebinding',async()=>{
  const f=fixedDeliveryFixture({leanPackage:true});rewriteFixedNative(f,()=>{},{factsMutate:facts=>facts.input_descriptors.pop()});assert.equal(await f.run(),null);
});

test('fixed native mutation harness preserves a valid exact outer pin graph before adverse changes',async()=>{
  const f=fixedDeliveryFixture({leanPackage:true});rewriteFixedNative(f,()=>{});
  assert.equal((await f.run())?.test_selection,'selected-data');
});

async function fixedConsumerFixture(options={}) {
  const f=fixedDeliveryFixture({leanPackage:true});
  // Populate the fake complete Git trees from retained immutable metadata;
  // subsequent consumer calls have fresh API caches and counters.
  assert.equal((await f.run()).test_selection,'selected-data');f.reads.length=0;
  return options.gate?gateFixture(f):mergeFixture({...options,selectedFixture:f});
}
test('fixed COD/PHL lean declarations reach actual queue selection and cold final merge validation',async()=>{
  const gate=await fixedConsumerFixture({gate:true});
  assert.equal((await gate.select()).test_selection,'selected-data');
  const prep=await fixedConsumerFixture(),prepared=await prepareIntegration(prep.options);
  assert.equal(prepared.test_selection,'selected-data');assert(!('proof' in prepared));assert(!('geography_proof' in prepared));
  const cold=await fixedConsumerFixture(),result=await cold.complete();
  assert.equal(result.accepted,true);assert(!('proof' in result));
});

for(const [label,mutate] of Object.entries({
  'orphan operand':f=>{const name='coordination/engineering/congo-ago2018-delivery-20261011/native-operands/runs-999.bin.gz';f.put(name,'orphan');f.files.push({filename:name,status:'added'});},
  'executable operand':f=>{f.authored.entries.get(f.files.find(row=>row.filename.endsWith('.bin.gz')).filename).mode='100755';},
  'substituted encoded body':f=>{const row=f.authored.entries.get(f.files.find(row=>row.filename.endsWith('.bin.gz')).filename);f.blobs.set(row.sha,Buffer.alloc(row.size));},
  'changed original registry prefix':f=>{const body=f.document(administrativePath);body.entries[0].id='changed';f.put(administrativePath,body);},
  'ambiguous registered source':f=>{const body=f.document(administrativePath);body.entries.push(structuredClone(body.entries[0]));f.put(administrativePath,body);},
  'unaccepted source':f=>{const prior=f.api;f.api=route=>route.includes('/compare/')?Promise.resolve({status:'diverged'}):prior(route);},
  'changed native manifest':f=>{const request=f.document(f.fixed.authorities[0].native_request);f.authored.entries.get(request.additive.manifest_path).sha='0'.repeat(40);},
}))test('fixed selected graph refuses '+label,async()=>{
  const f=fixedDeliveryFixture({leanPackage:true});mutate(f);assert.equal(await f.run(),null);
});
test('native physical path cannot escape its exact new operand role',async()=>{
  const f=fixedDeliveryFixture({leanPackage:true});rewriteFixedNative(f,request=>{
    const part=request.additive.owner_parts.find(p=>p.path.includes('/congo-ago2018-'));
    const input=request.additive.inputs.find(p=>p.path===part.path);input.path=part.path=part.path.replace('/native-operands/','/foreign/');
  });assert.equal(await f.run(),null);
});

function reusePhysicalRole(state) {
  const index=state.handoff.consumed_inputs.findIndex(row=>row.path.endsWith('/components-030.jsonl.gz'));
  assert(index>=0);const [row]=state.handoff.consumed_inputs.splice(index,1);
  const entry=state.f.authored.entries.get(row.path);
  // Schema-only alternative on the retained UKR body, not a claimed NOR execution.
  state.handoff.reused_whole_product_inputs=[{...row,commit:state.registration.accepted_source_commit,
    mode:entry.mode,git_blob_oid:entry.sha,whole_body_consumed:false}];
  return state.handoff.reused_whole_product_inputs[0];
}
test('explicit reused physical role preserves non-consumption while exact original SOURCE joins pass',async()=>{
  const f=retainedSourceFixture({mutate:reusePhysicalRole});assert.equal((await f.run()).test_selection,'selected-data');
  assert.equal(f.sourceState.handoff.reused_whole_product_inputs[0].whole_body_consumed,false);
});
for(const [label,mutate] of Object.entries({
  'missing reuse flag':(s,r)=>{delete r.whole_body_consumed;},
  'false consumption claim':(s,r)=>{r.whole_body_consumed=true;},
  'missing full commit':(s,r)=>{delete r.commit;},
  'missing full OID':(s,r)=>{delete r.blob;delete r.git_blob_oid;},
  'changed body OID':(s,r)=>{r.blob='0'.repeat(40);r.git_blob_oid='0'.repeat(40);},
  'changed encoded hash':(s,r)=>{r.sha256='0'.repeat(64);},
  'cross-list duplicate':(s,r)=>{s.handoff.consumed_inputs.push({...r});},
  'same-list duplicate':(s,r)=>{s.handoff.reused_whole_product_inputs.push({...r});},
}))test('explicit reused physical role refuses '+label,async()=>{
  const f=retainedSourceFixture({mutate:s=>mutate(s,reusePhysicalRole(s))});assert.equal(await f.run(),null);
});

const real1753=()=>fixedDeliveryFixture({fixtureName:'../../coordination/engineering/selected-metadata-admission-20261012/pr1753.json'});
test('complete unmodified merged PR1753 takes selected-data with all original evidence and role joins',async()=>{
  const f=real1753(),stats={};
  assert.equal(f.fixed.base,'7eb3293b739631f4e69d7e676c7a77ae7c22c107');
  assert.equal(f.fixed.head,'1d67abb09f5b9d3009da115c06170678aa5cdf3f');
  assert.equal(f.files.length,426);assert.deepEqual(f.files,f.fixed.changed_rows.map(({filename,status})=>({filename,status})));
  for(const row of f.fixed.changed_rows){
    assert.deepEqual(f.authored.entries.get(row.filename),row.after);
    assert.deepEqual(f.baseline.entries.get(row.filename)??null,row.before);
  }
  const result=await f.run({metadataDiagnostics:stats});assert(result,JSON.stringify(stats));assert.equal(result.test_selection,'selected-data');
  assert.equal(stats.read_count,349);assert.equal(stats.read_bytes,38981635);
  assert.equal(stats.retained_count,51);assert.equal(stats.retained_bytes,13352331);
  assert.equal(stats.transient_read_count,298);assert.equal(stats.decoded_bytes,22197550);
});
test('complete PR1753 record walk rejects malformed unconsumed preparation metadata',async()=>{
  const f=real1753();
  // Pick an independently confirmed unconsumed preparation record rather than a
  // pinned selected role, so stale outer pins cannot account for this rejection.
  const supporting=f.fixed.changed_rows.find(row=>row.filename.endsWith('/publication-preflight-001/classification.json')).filename;
  const original=f.document(supporting);assert(original);
  f.put(supporting,'{"unfinished":');assert.equal(await f.run(),null);
});
test('supporting logs retain complete whole-body text identity',async()=>{
  const lines=Array.from({length:400},(_,i)=>JSON.stringify({i,sample:'x'.repeat(400)})).join('\n')+'\n';
  const f=fixture({mutate:f=>f.put(prefix+'samples.log',lines)});
  assert.equal((await f.run()).test_selection,'selected-data');
  for(const body of [lines+'unexpected trailing text',JSON.stringify('x'.repeat(128*1024)),'unstructured '.repeat(13000)]){
    f.put(prefix+'samples.log',body);assert.equal((await f.run()).test_selection,'selected-data');
  }
  f.put(prefix+'samples.log',lines+'\0');assert.equal(await f.run(),null);
  f.put(prefix+'samples.log',lines);
  const row=f.authored.entries.get(prefix+'samples.log');f.blobs.set(row.sha,Buffer.from(lines.replace('sample','tamper')));
  assert.equal(await f.run(),null);
});
test('real PR1753 selection reaches cold queue classification and final validation',async()=>{
  const ready=async()=>{const f=real1753();assert.equal((await f.run()).test_selection,'selected-data');f.reads.length=0;return f;};
  const gate=gateFixture(await ready());
  assert.equal((await gate.select()).test_selection,'selected-data');
  const cold=mergeFixture({selectedFixture:await ready()}),result=await cold.complete();
  assert.equal(result.accepted,true);assert(!('proof' in result));
});
test('real PR1753 required selected roster cannot omit a member or change its identity',async()=>{
  for(const mutate of [expected=>expected.cohorts[0].members.pop(),expected=>{expected.cohorts[0].members[0].target_id='foreign';}]){
    const f=real1753(),name=f.files.find(row=>row.filename.endsWith('/selected-delivery-expectations.json')).filename;
    const expected=f.document(name);mutate(expected);f.put(name,expected);assert.equal(await f.run(),null);
  }
});

for(const [label,invalid] of Object.entries({
  'invalid leading byte':Buffer.from([0xff]),
  'stray continuation':Buffer.from([0x80]),
  'truncated multibyte sequence':Buffer.from([0xe2,0x82]),
  'overlong encoding':Buffer.from([0xc0,0xaf]),
}))test('strict metadata JSON rejects '+label+' in plain and compressed supporting records',async()=>{
  const raw=Buffer.concat([Buffer.from('{"value":"'),invalid,Buffer.from('"}\n')]);
  for(const suffix of ['json','json.gz','jsonl.gz']){
    const f=fixture({mutate:f=>f.put(prefix+'support.'+suffix,suffix.endsWith('.gz')?gzipSync(raw):raw)}),stats={};
    assert.equal(await f.run({metadataDiagnostics:stats}),null,suffix);
    assert.match(stats.failure,/invalid UTF-8 metadata/,suffix);
  }
});
test('strict JSON keeps legitimate Unicode and existing BOM rejection in every supporting representation',async()=>{
  const raw=Buffer.from(JSON.stringify({value:'Ελλάδα 日本 🌍 e\u0301'})+'\n');
  for(const suffix of ['json','json.gz','jsonl.gz']){
    const f=fixture({mutate:f=>f.put(prefix+'support.'+suffix,suffix.endsWith('.gz')?gzipSync(raw):raw)});
    assert.equal((await f.run()).test_selection,'selected-data',suffix);
    const bom=Buffer.concat([Buffer.from([0xef,0xbb,0xbf]),raw]);
    f.put(prefix+'support.'+suffix,suffix.endsWith('.gz')?gzipSync(bom):bom);assert.equal(await f.run(),null,suffix);
  }
});
test('required role JSON uses the same strict UTF-8 boundary before shape or identity validation',async()=>{
  const f=fixture(),name=prefix+'selected-delivery-expectations.json';
  const bytes=Buffer.from(JSON.stringify(f.expected)),marker=Buffer.from('target-old'),at=bytes.indexOf(marker);
  assert(at>=0);const bad=Buffer.concat([bytes.subarray(0,at),Buffer.from([0xff]),bytes.subarray(at+marker.length)]);
  f.put(name,bad);const stats={};assert.equal(await f.run({metadataDiagnostics:stats}),null);
  assert.match(stats.failure,/invalid UTF-8 metadata/);
});

test('actual immutable transport retains required metadata but not cumulative supporting evidence',async()=>{
 const f=fixture({mutate:f=>{for(let n=0;n<400;n++)f.put(prefix+'support-'+n+'.json',{n,body:'x'.repeat(48*1024)});}});
 f.api=memoizeImmutableGitBlobs(f.api);const stats={};
 assert.equal((await f.run({metadataDiagnostics:stats})).test_selection,'selected-data');
 assert(stats.read_bytes>16*1024*1024);
 let before=f.reads.length;
 for(let n=0;n<400;n++)await f.api('/repos/owner/repo/git/blobs/'+f.authored.entries.get(prefix+'support-'+n+'.json').sha,'GET',undefined,{retainImmutableBlob:false});
 assert.equal(f.reads.length-before,400,'transient responses must not survive in the actual consumer cache');
 before=f.reads.length;
 await f.api('/repos/owner/repo/git/blobs/'+f.authored.entries.get(prefix+'registry.json').sha);
 assert.equal(f.reads.length,before,'required-role reuse is preserved');
});


function ownedFixture({mutate = () => {}} = {}) {
  const packetPrefix = 'coordination/engineering/retained-delivery/new-packet/';
  const f = fixture({packetPrefix, mutate});
  f.branch = 'engineering/rotated-delivery'; f.ownedPaths = ['coordination/engineering/retained-delivery/'];
  f.reservation = {mode:'engineering', owned_paths:f.ownedPaths}; f.packetPrefix = packetPrefix;
  f.run = (options = {}) => selectedDataSelection({api:f.api, repo:'owner/repo', branch:f.branch, files:f.files,
    baseline:f.baseline, authored:f.authored, reservation:f.reservation, ...options});
  return f;
}
function exactOwnedFixture() {
  const f=ownedFixture();
  f.ownedPaths=f.files.filter(row=>row.status==='added').map(row=>row.filename);
  f.reservation={mode:'engineering',owned_paths:f.ownedPaths};
  return f;
}
test('exact-file issue ownership reaches selected preparation and final gates without widening packet scope', async()=>{
  const f=exactOwnedFixture();
  assert.equal(selectedDataCandidate(f.branch,f.files,f.reservation),true);
  assert.equal((await f.run()).test_selection,'selected-data');
  assert.equal((await gateFixture(exactOwnedFixture()).select()).test_selection,'selected-data');
  const final=mergeFixture({selectedFixture:exactOwnedFixture()});
  assert.equal((await final.complete()).accepted,true);
  assert.equal(final.writes.length,1);
});
test('exact-file issue ownership excludes prefix lookalikes, children and sibling files',async()=>{
  for(const suffix of ['.extra.json','/child.json']) {
    const f=exactOwnedFixture(), name=f.packetPrefix+'registry.json'+suffix;
    f.put(name,{});f.files.push({filename:name,status:'added'});
    assert.equal(selectedDataCandidate(f.branch,f.files,f.reservation),false);
    assert.equal(await f.run(),null);
    assert.equal(integrationProfile(f.branch,[{filename:name,status:'added'}],f.reservation),'full');
  }
  const f=exactOwnedFixture(), name=f.packetPrefix+'sibling.json';
  f.put(name,{});f.files.push({filename:name,status:'added'});
  assert.equal(await f.run(),null);
  assert.equal(integrationProfile(f.branch,[{filename:name,status:'added'}],f.reservation),'full');
});
test('shared exact-file and directory scope matching preserves directory boundaries',async()=>{
  const f=ownedFixture(), root='coordination/engineering/retained-delivery/new-packet/';
  f.reservation.owned_paths=[root];
  assert.equal((await f.run()).test_selection,'selected-data');
  assert.equal(integrationProfile(f.branch,[{filename:root+'nested/receipt.json',status:'added'}],f.reservation),'evidence');
  for(const name of [root.slice(0,-1)+'-sibling/receipt.json',root.slice(0,-1)+'.json']) {
    assert.equal(selectedDataCandidate(f.branch,[{filename:'data/ownership-selection.json',status:'modified'},{filename:name,status:'added'}],f.reservation),false);
    assert.equal(integrationProfile(f.branch,[{filename:name,status:'added'}],f.reservation),'full');
  }
  const exact=f.packetPrefix+'registry.json';
  assert.equal(integrationProfile(f.branch,[{filename:exact,status:'added'}],{mode:'engineering',owned_paths:[exact]}),'full',
    'exact selected-data ownership does not expand evidence-only routing');
});
test('exact-owned restored opaque role retains immutable identity and package consumer checks',async()=>{
  const name='coordination/engineering/original-packet/exact-patch.json';
  const f=fixture({mutate:f=>{
    const patch=f.put(name,{opaque:true});
    f.sidecarBody.logical_asset_map.patch=patch;
    const side=f.put(prefix+'selection-sidecar.json',f.sidecarBody);
    f.put('data/ownership-selection.json',{...f.base,additive_release:{path:side.path,bytes:side.bytes,sha256:side.sha256}});
    f.definition.inputs=f.definition.inputs.filter(value=>value!==prefix+'patch.json');
    f.definition.inputs.push(name);f.put('.github/package-inputs.json',f.definition);
  }});
  const reservation={mode:'engineering',owned_paths:[name]};
  assert.equal((await f.run({reservation})).test_selection,'selected-data');
  const original=f.authored.entries.get(name);
  f.authored.entries.set(name,{...original,sha:'f'.repeat(40)});
  assert.equal(await f.run({reservation}),null);
  f.authored.entries.set(name,original);
  const unrelated='coordination/engineering/original-packet/unconsumed.md';
  f.put(unrelated,'support only');f.files.push({filename:unrelated,status:'added'});reservation.owned_paths.push(unrelated);
  assert.equal((await f.run({reservation})).test_selection,'selected-data');
  f.definition.inputs.push(unrelated);f.put('.github/package-inputs.json',f.definition);
  assert.equal(await f.run({reservation}),null);
});
test('exact-file grants do not relax malformed, hidden, renamed, modified or executable data refusal',async()=>{
  for(const owned of ['coordination/engineering/','coordination/engineering/retained-delivery/../escape.json','research/geography/foreign/receipt.json']) {
    const f=exactOwnedFixture();f.reservation.owned_paths.push(owned);
    assert.equal(await f.run(),null);
  }
  for(const mutate of [
    (f,name)=>f.authored.entries.get(name).mode='100755',
    (f,name)=>f.authored.entries.get(name).mode='120000',
    (f,name)=>f.files.find(row=>row.filename===name).previous_filename='src/runtime.json',
    (f,name)=>f.files.find(row=>row.filename===name).status='modified',
  ]) {const f=exactOwnedFixture();mutate(f,f.packetPrefix+'registry.json');assert.equal(await f.run(),null);}
  const f=exactOwnedFixture(), name=f.packetPrefix+'.hidden.json';
  f.put(name,{});f.files.push({filename:name,status:'added'});f.reservation.owned_paths.push(name);
  assert.equal(await f.run(),null);
});
test('retained nested delivery needs authenticated current issue scope through PR, prepare and cold final gates', async () => {
  const f = ownedFixture();
  assert.equal(selectedDataCandidate(f.branch, f.files), false);
  assert.equal(selectedDataCandidate(f.branch, f.files, f.reservation), true);
  assert.equal((await f.run()).test_selection, 'selected-data');
  assert.equal((await gateFixture(ownedFixture()).select()).test_selection, 'selected-data');
  const prepared = await prepareIntegration(mergeFixture({selectedFixture:ownedFixture()}).options);
  assert.equal(prepared.test_selection, 'selected-data');
  const final = mergeFixture({selectedFixture:ownedFixture()});
  const result = await final.complete(); assert.equal(result.accepted, true); assert.equal(final.writes.length, 1);
  assert(!('proof' in result));
});
for (const [name, change] of Object.entries({
  'missing current scope':f => f.issue.body = f.issue.body.replace(/,"owned_paths":\[[^\]]*\]/, ''),
  'closed issue':f => f.issue.state = 'closed',
  'wrong issue':f => f.issue.number = 11,
  'wrong mode':f => f.issue.body = f.issue.body.replace('\"mode\":\"engineering\"','\"mode\":\"source-only\"'),
  'wrong lane':f => f.issue.labels[0] = 'type:geography',
})) test('retained selected metadata refuses ' + name, async () => {
  const f = gateFixture(ownedFixture()); change(f);
  await assert.rejects(f.select());
});
for (const owned_paths of [['coordination/engineering/'], ['coordination/engineering/retained-delivery/../'],
  ['coordination/engineering/other/'], ['coordination/engineering/retained-delivery/new-packet/registry.json']]) {
  test('retained selected scope rejects unsafe/foreign/incomplete ownership ' + owned_paths[0], async () => {
    const f=ownedFixture(); assert.equal(await f.run({reservation:{mode:'engineering',owned_paths}}), null);
  });
}
test('retained inert text stays ordinary, unconsumed and outside package inputs', async () => {
  for (const name of ['README.md','CHECKPOINT.md','notes.md','nested/review.md','unresolved-evidence-001/delivery-config-3816/independent-static-review.md','diagnostic.txt','refusals/stderr.txt']) {
    const f=ownedFixture({mutate:f=>f.put('coordination/engineering/retained-delivery/new-packet/'+name,'retained text\n')});
    assert.equal((await f.run()).test_selection,'selected-data');
    f.definition.inputs.push(f.packetPrefix+name); f.put('.github/package-inputs.json',f.definition);
    assert.equal(await f.run(),null);
  }
  for (const [name, raw] of [['CHECKPOINT.md','x\0y'],['diagnostic.txt',Buffer.from([0xff])],
    ['requirements.txt','some-package'],['constraints-dev.txt','some-package'],['code.mjs','export default 1']]) {
    assert.equal(await ownedFixture({mutate:f=>f.put('coordination/engineering/retained-delivery/new-packet/'+name,raw)}).run(),null,name);
  }
});
function templateFixture(change = () => {}, suffix = 'prospective') {
  return ownedFixture({mutate:f=>{
    const root='coordination/engineering/retained-delivery/new-packet/', directory=root+suffix;
    const expected={...f.expected, selected_ledger_sha256:null};
    const config={version:1, registry:f.registry, ledger:f.leaf('composed-original-ledger.json'),
      rebind:f.ledgerBody.current_rebind, new_prefix:root};
    const canonical=value=>Array.isArray(value)?value.map(canonical):value&&typeof value==='object'
      ? Object.fromEntries(Object.keys(value).sort().map(key=>[key,canonical(value[key])])):value;
    const binding={phase:'package',config_sha256:digest(Buffer.from(JSON.stringify(canonical(config))+'\n'))};
    const intent={version:1,stage:'package',binding,config};
    const template=f.put(directory+'/selected-delivery-expectations.json',expected), roles=f.put(directory+'/package-roles.json',{version:1});
    const descriptor=pin=>({bytes:pin.bytes,sha256:pin.sha256});
    const receipt={version:1,binding,outputs:{'package-roles.json':descriptor(roles),'selected-delivery-expectations.json':descriptor(template)}};
    f.put(directory+'.intent.json',intent); f.put(directory+'/preparation.json',receipt);
    change({f,root,directory,expected,config,intent,receipt});
  }});
}
test('one current-bound expectation disambiguates an exact unconsumed package template with preparation custody', async () => {
  const f=templateFixture(), result=await f.run();
  assert.equal(result.expectations_path,f.packetPrefix+'selected-delivery-expectations.json');
  assert.equal((await gateFixture(templateFixture()).select()).test_selection,'selected-data');
});
test('retained package receipt input custody classifies without a runtime journal in Git', async () => {
  let input, directory;
  const f=templateFixture(v=>{input=v.config;directory=v.directory;},'retained-package');
  const legacy=directory+'.intent.json';
  f.authored.entries.delete(legacy);f.files.splice(f.files.findIndex(row=>row.filename===legacy),1);
  // Preserve the historical immutable receipt contract after retiring its
  // automatic producer. The classifier still authenticates its original input.
  const original=JSON.parse(f.blobs.get(f.authored.entries.get(directory+'/preparation.json').sha));
  original.input=input;f.put(directory+'/preparation.json',original);
  assert.equal((await f.run()).test_selection,'selected-data');
  for(const mutate of [r=>delete r.input,r=>r.input.registry.path='coordination/engineering/foreign/registry.json',
    r=>r.binding.config_sha256='0'.repeat(64),r=>r.outputs['package-roles.json'].bytes++,
    r=>r.input.new_prefix='coordination/engineering/foreign/']) {
    const changed=structuredClone(original);mutate(changed);f.put(directory+'/preparation.json',changed);
    assert.equal(await f.run(),null);
  }
  f.put(directory+'/preparation.json',original);
  f.put(legacy,{version:1,stage:'package',binding:original.binding,config:{...input,new_prefix:'coordination/engineering/foreign/'}});
  f.files.push({filename:legacy,status:'added'});assert.equal(await f.run(),null);
});

for (const [name,change] of Object.entries({
  'two authoritative candidates':({f,directory})=>f.put(directory+'/selected-delivery-expectations.json',f.expected),
  'incorrect current ledger binding':({f,root})=>f.put(root+'selected-delivery-expectations.json',{...f.expected,selected_ledger_sha256:'f'.repeat(64)}),
  'no authoritative candidate':({f,root})=>f.authored.entries.delete(root+'selected-delivery-expectations.json'),
  'missing preparation intent':({f,directory})=>f.authored.entries.delete(directory+'.intent.json'),
  'missing whole-file receipt':({f,directory})=>f.authored.entries.delete(directory+'/preparation.json'),
  'template roster omission':({f,directory,expected})=>{expected.cohorts[0].members.pop();expected.cohorts[0].component_ids.pop();f.put(directory+'/selected-delivery-expectations.json',expected);},
  'template authority substitution':({f,directory,intent})=>{intent.config.registry=f.leaf('foreign.json');f.put(directory+'.intent.json',intent);},
  'template publication bytes drift':({f,directory,receipt})=>{receipt.outputs['selected-delivery-expectations.json'].bytes++;f.put(directory+'/preparation.json',receipt);},
  'template becomes a package input':({f,directory})=>{f.definition.inputs.push(directory+'/selected-delivery-expectations.json');f.put('.github/package-inputs.json',f.definition);},
})) test('prospective expectation disambiguation rejects '+name,async()=>assert.equal(await templateFixture(change).run(),null));

function real1770() {
  const fixed=JSON.parse(readFileSync(new URL('../coordination/engineering/selected-owned-scope-20261012/pr1770.json',import.meta.url)));
  const baseline={object:{sha:fixed.base},entries:new Map(fixed.retained_tree_rows.map(row=>[row.path,{...row}]))};
  const authored={object:{sha:fixed.head},entries:new Map(fixed.retained_tree_rows.map(row=>[row.path,{...row}]))};
  for(const row of fixed.changed_rows) {
    if(row.before)baseline.entries.set(row.filename,{...row.before});else baseline.entries.delete(row.filename);
    authored.entries.set(row.filename,{...row.after});
  }
  const blobs=new Map(), reads=[], gitReads=[], files=structuredClone(fixed.files);
  const bytes=sha=>{
    if(!blobs.has(sha)) {gitReads.push(sha);blobs.set(sha,execFileSync('git',['cat-file','blob',sha],{maxBuffer:32*1024*1024,
      env:{...process.env,GIT_NO_LAZY_FETCH:'1',GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_GLOBAL:'/dev/null',GIT_TERMINAL_PROMPT:'0'}}));}
    return blobs.get(sha);
  };
  for(const row of fixed.snapshots) {
    const raw=Buffer.from(row.body);assert.equal(raw.length,row.bytes);assert.equal(digest(raw),row.sha256);
    assert.equal(createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex'),row.git_blob_oid);
    blobs.set(row.git_blob_oid,raw);
  }
  const api=async route=>{
    if(route.includes('/git/blobs/')){const sha=route.split('/').at(-1),raw=bytes(sha);reads.push(sha);return {sha,size:raw.length,encoding:'base64',content:raw.toString('base64')};}
    if(route.includes('/compare/')) {assert(fixed.accepted_sources.some(row=>route.endsWith(row.commit+'...'+baseline.object.sha)));return {status:'ahead'};}
    if(route.includes('/git/commits/')) {const row=fixed.accepted_sources.find(row=>route.endsWith('/'+row.commit));assert(row,route);return {sha:row.commit,tree:{sha:row.tree}};}
    if(route.includes('/git/trees/')) {const row=fixed.accepted_sources.find(row=>route.endsWith('/'+row.tree+'?recursive=1'));assert(row,route);return {truncated:false,tree:[row.entry]};}
    throw Error('Unexpected actual fixture route '+route);
  };
  const put=(name,value,old=false)=>{const raw=Buffer.from(typeof value==='string'?value:JSON.stringify(value)),sha=createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
    blobs.set(sha,raw);const row={path:name,mode:'100644',type:'blob',sha,size:raw.length};authored.entries.set(name,row);if(old)baseline.entries.set(name,row);
    return {path:name,bytes:raw.length,sha256:digest(raw),mode:'100644',git_blob_oid:sha,commit:'a'.repeat(40)};};
  const f={fixed,files,branch:fixed.branch,ownedPaths:fixed.owned_paths,reservation:{mode:'engineering',owned_paths:fixed.owned_paths},
    sourceState:{},baseline,authored,blobs,reads,gitReads,api,put,document:name=>JSON.parse(bytes(authored.entries.get(name).sha))};
  f.run=(options={})=>selectedDataSelection({api:f.api,repo:'owner/repo',branch:f.branch,files:f.files,baseline,authored,reservation:f.reservation,...options});
  return f;
}
test('complete original PR1770 192-path diff selects the uniquely bound finalized expectation without changing data', async () => {
  const f=real1770(),stats={};
  assert.equal(f.fixed.base,'ad300bd5ffa73c226e591f037980d67d40f6acf3');
  assert.equal(f.fixed.head,'367d68214f8c88532949bf9d21539766491991ad');assert.equal(f.files.length,192);
  assert.equal(selectedDataCandidate(f.branch,f.files),false);assert.equal(selectedDataCandidate(f.branch,f.files,f.reservation),true);
  const result=await f.run({metadataDiagnostics:stats});assert(result,JSON.stringify(stats));
  assert.equal(result.expectations_path,'coordination/engineering/nor-grc-congo-delivery-20261011/aus13-selected-20261012/advance-002/finalize/selected-delivery-expectations.json');
  assert.equal(stats.read_count,164);assert.equal(stats.read_bytes,21503703);
  for(const row of f.fixed.changed_rows)assert.deepEqual(f.authored.entries.get(row.filename),row.after);
  const historicalManifest=f.fixed.snapshots.find(row=>row.path.endsWith('/evidence-quality.json'));
  assert(historicalManifest,'final c753 changed the original added metadata blob');
  assert(f.reads.includes(historicalManifest.git_blob_oid),'original manifest is actually validated');
  for(const row of f.fixed.snapshots)assert(!f.gitReads.includes(row.git_blob_oid),'historical mutable metadata must not require shallow Git history');
  const reachable=new Set(execFileSync('git',['ls-tree','-r','HEAD'],{encoding:'utf8',maxBuffer:16*1024*1024,
    env:{...process.env,GIT_NO_LAZY_FETCH:'1',GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_GLOBAL:'/dev/null',GIT_TERMINAL_PROMPT:'0'}})
    .trim().split('\n').map(line=>line.split('\t')[0].split(' ')[2]));
  for(const oid of f.gitReads)assert(reachable.has(oid),'every unsnapshotted original body must be reachable in shallow HEAD: '+oid);
});
test('actual PR1770 reaches authenticated author and cold queue proof with complete metadata planning', async () => {
  assert.equal((await gateFixture(real1770()).select()).test_selection,'selected-data');
  const prep=await prepareIntegration(mergeFixture({selectedFixture:real1770()}).options);assert.equal(prep.test_selection,'selected-data');
  const final=mergeFixture({selectedFixture:real1770()}), result=await final.complete();
  assert.equal(result.accepted,true);assert.equal(final.writes.length,1);assert(!('proof' in result));
});
for(const [label,mutate] of Object.entries({
  'two authoritative expectations':f=>{const names=f.files.filter(row=>row.filename.endsWith('/selected-delivery-expectations.json')).map(row=>row.filename);const final=names.find(name=>f.document(name).selected_ledger_sha256);f.put(names.find(name=>name!==final),f.document(final));},
  'incorrect current binding':f=>{const name=f.files.find(row=>row.filename.endsWith('/finalize/selected-delivery-expectations.json')).filename;f.put(name,{...f.document(name),selected_ledger_sha256:'f'.repeat(64)});},
  'contradictory template roster':f=>{const name=f.files.find(row=>row.filename.endsWith('/package/selected-delivery-expectations.json')).filename,body=f.document(name);body.cohorts[0].members[0].target_id='wrong';f.put(name,body);},
  'forged null-template provenance':f=>{const name=f.files.find(row=>row.filename.endsWith('/package.intent.json')).filename,body=f.document(name);body.config.registry.path='coordination/engineering/foreign/registry.json';f.put(name,body);},
  'foreign ownership':f=>f.reservation.owned_paths=['coordination/engineering/foreign/'],
  'consumed diagnostic text':f=>{const policy=f.document('.github/package-inputs.json');policy.inputs.push(f.files.find(row=>row.filename.endsWith('/stderr.txt')).filename);f.put('.github/package-inputs.json',policy);},
  'native-path alias drift':f=>{const file=f.files.find(row=>row.filename.endsWith('.bin.gz')),old=file.filename,next=old.replace(/runs-\d+/, 'rows-1');const row=f.authored.entries.get(old);f.authored.entries.delete(old);file.filename=next;f.authored.entries.set(next,{...row,path:next});},
  'unknown executable':f=>{const filename='coordination/engineering/nor-grc-congo-delivery-20261011/aus13-selected-20261012/extra.mjs';f.put(filename,'export default 1');f.files.push({filename,status:'added'});},
}))test('actual PR1770 retains full fallback for '+label,async()=>{const f=real1770();mutate(f);assert.equal(await f.run(),null);});

test('coherently rebound prospective custody still cannot substitute consumed roles or original cohort labels', async () => {
  for(const field of ['registry','ledger','rebind','new_prefix','cohort']) {
    const f=templateFixture(({f,directory,expected,intent,receipt})=>{
      if(field==='cohort') {expected.cohorts[0].original_batch_id='foreign batch';const pin=f.put(directory+'/selected-delivery-expectations.json',expected);
        receipt.outputs['selected-delivery-expectations.json']={bytes:pin.bytes,sha256:pin.sha256};}
      else if(field==='new_prefix')intent.config.new_prefix='coordination/';
      else intent.config[field]=f.leaf('foreign-role.json');
      const canonical=value=>Array.isArray(value)?value.map(canonical):value&&typeof value==='object'
        ? Object.fromEntries(Object.keys(value).sort().map(key=>[key,canonical(value[key])])):value;
      intent.binding.config_sha256=digest(Buffer.from(JSON.stringify(canonical(intent.config))+'\n'));
      receipt.binding={...intent.binding};f.put(directory+'.intent.json',intent);f.put(directory+'/preparation.json',receipt);
    });
    assert.equal(await f.run(),null,field);
  }
});
test('retained native basename alias drift fails fixed manifest custody after all outer pins are rebound', async () => {
  const f=fixedDeliveryFixture({leanPackage:true});
  const reservation={mode:'engineering',owned_paths:['coordination/engineering/congo-ago2018-delivery-20261011/']};
  rewriteFixedNative(f,request=>{
    const part=request.additive.owner_parts.find(p=>p.path.includes('/congo-ago2018-'));
    const input=request.additive.inputs.find(p=>p.path===part.path), old=part.path, name=old.replace(/\/(rows|runs)-\d+\.bin\.gz$/, '/runs-1.bin.gz');
    const row=f.authored.entries.get(old);f.authored.entries.set(name,{...row,path:name});
    f.files.push({filename:name,status:'added'});input.path=part.path=name;
  });
  const stats={};assert.equal(await f.run({reservation,metadataDiagnostics:stats}),null);
  assert.equal(stats.failure,'Selected-data: native operand identities differ');
});

function checkpointProfileFixture() {
  const f=fixture(), locatorPath='data/selected-checkpoint.json', archive=prefix+'accepted-predecessor/geography-artifact.zip';
  const head='a'.repeat(40), before='1'.repeat(40), candidate='2'.repeat(40), merged='d'.repeat(40), tree='e'.repeat(40);
  const request='01234567-abcd-4321-aaaa-123456789012', json=value=>Buffer.from(JSON.stringify(value)+'\n');
  const oldSelection=JSON.parse(f.blobs.get(f.baseline.entries.get('data/ownership-selection.json').sha));
  const facts={candidate_commit:candidate,candidate_selection:oldSelection};
  const locator={version:1,kind:'accepted-selected-checkpoint-locator-v1',acceptance:{pr_number:7,request_id:request,head},retained_artifact:{path:archive}};
  const report={version:1,method_id:'worldatlas-trusted-geography-check-v1',baseline_commit:before,candidate_commit:candidate,
    trusted_code_commit:before,candidate_code_executed:false,published:false,source_approval:false,gate_status:'passed',status:'not-applicable'};
  const source={run_id:12,run_attempt:2,job_id:34,tree,head,baseline:before,candidate_commit:candidate,
    workflow_path:'.github/workflows/worker-merge.yml',event:'workflow_dispatch',workflow_head:'f'.repeat(40),
    artifact_id:56,artifact_name:`geography-${request}-2`};
  const receipt={accepted:true,status:'merged',request_id:request,pr_number:7,merge_commit:merged,reviewed_head:head,
    tested_base:before,tested_candidate:candidate,geography:{status:'passed',trusted_code_commit:before,candidate_commit:candidate,source}};
  const pr={number:7,merged:true,head:{sha:head,repo:{full_name:'owner/repo'}},base:{ref:'main',repo:{full_name:'owner/repo'}},merge_commit_sha:merged};
  // Match genuine A's envelope/status and alphabetic product roster, retained
  // at ef1bf2c691b6f554c32885daf5a6dd35a451c9ff:south5-selected-validation-001.
  // Only tiny operand bodies/identities are substituted for this profile control.
  const c=f.checkpoint={locatorPath,archive,locator,report,source,receipt,pr,facts,tree,bot:'github-actions[bot]',calls:[],names:[...CHECKPOINT_MEMBERS].sort()};
  c.rebuild=()=>{
    const members=c.names.map(name=>{const body=json(name==='derived-facts.json'?facts:{member:name});
      return {name,decoded:body,raw:name.endsWith('.gz')?gzipSync(body):body};});
    report.checkpoint={version:1,kind:'selected-checkpoint-products-v1',members:members.map(({name,raw,decoded})=>({name,bytes:raw.length,sha256:digest(raw),
      ...(name.endsWith('.gz')?{decoded_bytes:decoded.length,decoded_sha256:digest(decoded)}:{})}))};
    const root=json(report),zip=checkpointZip([['geography-check.json',root],...members.map(({name,raw})=>[name,raw])]);
    Object.assign(source,{artifact_digest:digest(zip),artifact_bytes:zip.length,report_sha256:digest(root),report_bytes:root.length});
    receipt.geography.report_sha256=source.report_sha256;f.put(archive,zip);f.put(locatorPath,locator);
  };
  c.refresh=()=>{f.files=[...f.authored.entries].filter(([name,row])=>f.baseline.entries.get(name)?.sha!==row.sha)
    .map(([filename])=>({filename,status:f.baseline.entries.has(filename)?'modified':'added'}));};
  c.rebuild();c.refresh();const blobs=f.api;
  f.api=async (...args)=>{
    const [route]=args;c.calls.push(route);
    if(route==='/repos/owner/repo/issues/7/comments?per_page=100&page=1')return [{id:11,user:{login:c.bot},body:renderWorkerResult('merge',receipt)}];
    if(route==='/repos/owner/repo/pulls/7')return pr;
    if(route.includes('/git/commits/'))return {sha:route.split('/').at(-1),tree:{sha:c.tree}};
    return blobs(...args);
  };
  return f;
}

test('actual profile entry keeps a complete accepted predecessor ZIP and locator in selected-data custody',async()=>{
  const f=checkpointProfileFixture(),g=gateFixture(f),result=await g.select();
  assert.equal(result.test_selection,'selected-data');assert.deepEqual(result.shards,[0]);
  assert(f.reads.includes(f.authored.entries.get(f.checkpoint.archive).sha));
  assert(f.checkpoint.calls.some(route=>route.endsWith('/pulls/7')));
  assert(!f.checkpoint.calls.some(route=>route.includes('/actions/')),'classification does not reacquire or mint scientific authority');
  assert.equal(f.checkpoint.source.head,'a'.repeat(40));assert.equal(f.checkpoint.source.workflow_head,'f'.repeat(40));
});
test('a successor may replace the locator while retaining its predecessor archive unchanged',async()=>{
  const f=checkpointProfileFixture(),c=f.checkpoint;
  f.baseline.entries.set(c.locatorPath,{...f.authored.entries.get(c.locatorPath),sha:'9'.repeat(40)});c.refresh();
  assert.equal(f.files.find(p=>p.filename===c.locatorPath).status,'modified');
  assert.equal((await f.run()).test_selection,'selected-data');
});
for(const [name,mutate] of Object.entries({
  'unbound ZIP':(f,c)=>f.authored.entries.delete(c.locatorPath),
  'foreign ZIP':(f,c)=>{c.locator.retained_artifact.path='coordination/engineering/foreign/geography-artifact.zip';f.put(c.locatorPath,c.locator);},
  'extra ZIP':(f,c)=>f.put(prefix+'extra/geography-artifact.zip',f.blobs.get(f.authored.entries.get(c.archive).sha)),
  'missing ZIP':(f,c)=>f.authored.entries.delete(c.archive),
  'symlink ZIP':(f,c)=>f.authored.entries.get(c.archive).mode='120000',
  'rewritten ZIP':(f,c)=>f.baseline.entries.set(c.archive,{...f.authored.entries.get(c.archive),sha:'9'.repeat(40)}),
  'package-consumed custody':(f,c)=>{f.definition.inputs.push(c.archive);f.put('.github/package-inputs.json',f.definition);},
  'forged locator fields':(f,c)=>{c.locator.approved=true;f.put(c.locatorPath,c.locator);},
  'candidate-only digest':(f,c)=>f.put(c.archive,Buffer.from('locally recomputed bytes are not acceptance')),
  'fake receipt author':(f,c)=>{c.bot='attacker';},
  'unaccepted receipt':(f,c)=>{c.receipt.accepted=false;},
  'unmerged PR':(f,c)=>{c.pr.merged=false;},
  'foreign repository':(f,c)=>{c.pr.base.repo.full_name='foreign/repo';},
  'wrong accepted tree':(f,c)=>{c.tree='8'.repeat(40);},
  'wrong report root':(f,c)=>{c.source.report_sha256='9'.repeat(64);c.receipt.geography.report_sha256=c.source.report_sha256;},
  'incomplete product roster':(f,c)=>{c.names.pop();c.rebuild();},
  'failed original gate':(f,c)=>{c.report.gate_status='blocked';c.rebuild();},
  'coherent unrelated baseline':(f,c)=>{c.facts.candidate_selection={unrelated:true};c.rebuild();},
  'coherent wrong producer':(f,c)=>{c.facts.candidate_commit='9'.repeat(40);c.rebuild();},
  'added code':f=>f.put('scripts/new-reader.mjs','throw Error("not inert custody")'),
}))test('checkpoint custody retains full regression for '+name,async()=>{
  const f=checkpointProfileFixture();mutate(f,f.checkpoint);f.checkpoint.refresh();assert.equal(await f.run(),null);
});

// Retained authority may precede the selected delivery of its original operands.
// Keep its exact bytes in both trees while restoring the existing typed inputs.
function retainFixedAuthorities(f) {
  for (const {authority_path} of f.fixed.authorities) {
    f.baseline.entries.set(authority_path,{...f.authored.entries.get(authority_path)});
    f.files=f.files.filter(row=>row.filename!==authority_path);
  }
  return f;
}
test('retained original authority authenticates newly restored native operands',async()=>{
  const f=retainFixedAuthorities(fixedDeliveryFixture({leanPackage:true})),stats={};
  assert.equal((await f.run({metadataDiagnostics:stats}))?.test_selection,'selected-data',stats.failure);
});
for(const [label,mutate] of Object.entries({
  'inverse':r=>r.additive.owner_parts.find(p=>p.path.includes('/congo-ago2018-')).containing_inverse.inverse_ranges[0].start++,
  'encoded hash':r=>{r.additive.inputs.find(p=>p.path.includes('/congo-ago2018-')&&p.path.endsWith('.bin.gz')).sha256='0'.repeat(64);},
  'facts roster':()=>{},
}))test('retained native restoration refuses altered '+label,async()=>{
  const f=fixedDeliveryFixture({leanPackage:true});
  rewriteFixedNative(f,mutate,{factsMutate:facts=>{if(label==='facts roster')facts.input_descriptors.pop();}});
  retainFixedAuthorities(f);assert.equal(await f.run(),null);
});
for(const [label,mutate] of Object.entries({
  'changed authority':f=>{f.baseline.entries.get(f.fixed.authorities[0].authority_path).sha='0'.repeat(40);},
  'changed original manifest':f=>{const r=f.document(f.fixed.authorities[0].native_request);f.baseline.entries.get(r.additive.manifest_path).sha='0'.repeat(40);},
  'unbound opaque operand':f=>{const name='coordination/engineering/congo-ago2018-delivery-20261011/native-operands/runs-999.bin.gz';f.put(name,'unbound');f.files.push({filename:name,status:'added'});},
  'inert evidence package consumption':f=>{const name='coordination/engineering/congo-ago2018-delivery-20261011/inert.json';f.put(name,{});f.files.push({filename:name,status:'added'});const p=f.document('.github/package-inputs.json');p.inputs.push(name);f.put('.github/package-inputs.json',p);},
}))test('retained native restoration refuses '+label,async()=>{
  const f=retainFixedAuthorities(fixedDeliveryFixture({leanPackage:true}));mutate(f);assert.equal(await f.run(),null);
});

test('new package declaration may consume exact unchanged authenticated original proof',async()=>{
  const f=retainFixedAuthorities(fixedDeliveryFixture({leanPackage:true}));
  const authority=f.document(f.fixed.authorities[0].authority_path),name=authority.native_proof.assets[0].path;
  f.baseline.entries.set(name,{...f.authored.entries.get(name)});f.files=f.files.filter(row=>row.filename!==name);
  const stats={};assert.equal((await f.run({metadataDiagnostics:stats}))?.test_selection,'selected-data',stats.failure);
});
for(const changed of [false,true])test('retained package refuses '+(changed?'changed original proof bytes':'unbound existing evidence'),async()=>{
  const f=retainFixedAuthorities(fixedDeliveryFixture({leanPackage:true}));
  if(changed){
    const name=f.document(f.fixed.authorities[0].authority_path).native_proof.assets[0].path;
    f.baseline.entries.set(name,{...f.authored.entries.get(name),sha:'0'.repeat(40)});
    f.files=f.files.filter(row=>row.filename!==name);
  }else{
    const name='coordination/engineering/congo-ago2018-delivery-20261011/old-inert.json';f.put(name,{},true);
    const p=f.document('.github/package-inputs.json');p.inputs.push(name);f.put('.github/package-inputs.json',p);
  }
  assert.equal(await f.run(),null);
});

// Actual already accepted SOURCE000 proof bytes; only the enclosing selection
// and native locator are synthetic. This tests routing, not source/native science.
function legacySourceProofFixture() {
  return fixture({mutate:f=>{
    const stem='coordination/engineering/melanesia363-additive-delivery-20261010/';
    // Retained HEAD blobs also work in the exact-tree CI checkout without
    // fetching history. Their original 36ce805d bytes remain hash-pinned.
    const names=[
      ['source-requests/000-full-component-request.json','6a15237137046e136e198286831d719087a78c2c6320f82235891f2a68097f1d'],
      ['source-qualified/000/facts.json','bead4a53cc83b254fa1e7ef709e762b9ea4117906b9fca8f1c708d357f50c568'],
      ['source-qualified/000/publication.json','909571ab6b590215e311d79f3bac2e8dbb78d545dbcdf22a678e64a7b2f8d80d'],
      ['source-qualified/000/inventory.jsonl.gz','4ad5edfd57eff2e06bbe97881d5f985f15f7871eba6c85e37024d63736505136'],
      ['native-source-operating/source000-derived-operating-view.json','eec862edb5f7dd1e55d1d1446b7dfa47c4be1b3c50cbba6edb86045bdef7a10e']];
    const pins=names.map(([name,originalHash])=>{
      const bytes=execFileSync('git',['show','HEAD:'+stem+name],
        {maxBuffer:32*1024*1024,env:{...process.env,GIT_NO_LAZY_FETCH:'1'}});
      assert.equal(digest(bytes),originalHash);
      return {...f.put(stem+name,bytes,true),commit:'36ce805d29e1cfd1da6f95d1aa0f4d20ab2ab92c'};
    });
    const [source_request,source_facts,publication,inventory,operating]=pins;
    assert.equal(source_request.sha256,'6a15237137046e136e198286831d719087a78c2c6320f82235891f2a68097f1d');
    const issued=JSON.parse(f.blobs.get(source_request.git_blob_oid));
    assert.equal(issued.source_rule.geometry_scope,'full-component');
    assert.equal(issued.source_rule.registry_path,undefined);
    const native_request=f.put(prefix+'native/request.json',{additive:{inputs:[publication,inventory,operating],
      publication_path:publication.path,inventory_path:inventory.path,operating_path:operating.path}});
    const original_pins={native_request,source_request,source_facts,
      ...Object.fromEntries(['ledger','native_facts','native_manifest'].map(name=>[name,f.leaf('original/'+name+'.json')]))};
    const native_proof={publication:f.leaf('native/publication.json'),inventory:f.leaf('native/inventory.jsonl.gz'),
      operating:f.leaf('native/operating.json'),assets:[f.leaf('native/base-native-manifest.json')]};
    const source_authority=f.put(prefix+'authority-binding.json',
      {version:1,kind:'original-issued-rule-source-custody-v1',original_pins,native_proof});
    const rule_preimage=f.leaf('original-rule.json');
    f.registryBody.entries.push({authority_sha256:source_authority.sha256,policy_id:'retained-source-literal-additions',
      policy_version:1,source_authority,rule_preimage,rule_sha256:rule_preimage.sha256});
    refreshPins(f);f.definition.inputs.push(...pins.map(pin=>pin.path));f.put('.github/package-inputs.json',f.definition);
    f.legacyPins=pins;
  }});
}
test('legacy SOURCE000 proof declarations use exact reachable roles without inventing registry custody',async()=>{
  const f=legacySourceProofFixture(),stats={};
  assert.equal((await f.run({metadataDiagnostics:stats}))?.test_selection,'selected-data',stats.failure);
  assert(!f.files.some(row=>row.filename===administrativePath));
  assert(f.legacyPins.every(pin=>f.baseline.entries.has(pin.path)&&f.definition.inputs.includes(pin.path)));
  const gate=gateFixture(legacySourceProofFixture());
  assert.equal((await gate.select()).test_selection,'selected-data');
});
for(const [label,mutate] of Object.entries({
  'changed retained bytes':f=>{f.baseline.entries.get(f.legacyPins[0].path).sha='0'.repeat(40);},
  'changed retained mode':f=>{f.baseline.entries.get(f.legacyPins[0].path).mode='100755';},
  'missing retained role':f=>{f.authored.entries.delete(f.legacyPins[1].path);},
  'unbound retained declaration':f=>{
    const name='coordination/engineering/prior/unbound.json';f.put(name,{},true);
    f.definition.inputs.push(name);f.put('.github/package-inputs.json',f.definition);
  },
  'new administrative registry':f=>{
    f.put(administrativePath,{version:1,kind:'accepted-administrative-handoffs-v1',entries:[]},true);
    f.files.push({filename:administrativePath,status:'modified'});
  },
  'code change':f=>{f.put('src/attributes.js','// changed');f.files.push({filename:'src/attributes.js',status:'modified'});},
}))test('legacy proof declarations retain full fallback for '+label,async()=>{
  const f=legacySourceProofFixture();mutate(f);assert.equal(await f.run(),null);
});

test('unreachable accepted SOURCE declarations still require administrative custody without a registry edit',async()=>{
  for(const invalid of [false,true]) {
    const f=retainedSourceFixture({mutate:x=>{if(invalid)x.issued.source_rule.registry_path='coordination/engineering/foreign/registry.json';}});
    f.baseline.entries.set(administrativePath,{...f.authored.entries.get(administrativePath)});
    f.files.splice(f.files.findIndex(row=>row.filename===administrativePath),1);
    const stats={},result=await f.run({metadataDiagnostics:stats});
    if(invalid)assert.equal(result,null);else assert.equal(result?.test_selection,'selected-data',stats.failure);
  }
});

// Structural role eligibility only; the source/native reader separately
// authenticates whole products and actual map-cell ownership.
function sourceTargetRoleFixture({wrongRule=false,emptyFamily=false,retainedRoles=false,sourceMembership,mutateRoles=()=>{}}={}) {
  return fixture({mutate:f=>{
    const nativeRows=[{y:3,runs:[[4,5,1]]}];
    f.rows[1]={component_id:'new',target_id:'target-new',disposition:'assigned',native_cells:1,
      representation:'native-cells',native_rows:nativeRows};
    f.ledgerBody.rows=f.rows;
    f.expected.cumulative_native_cells=3;
    f.expected.cohorts[0].members[1]={component_id:'new',target_id:'target-new',disposition:'assigned',
      native_rows_sha256:digest(Buffer.from(JSON.stringify([{runs:[[4,5,1]],y:3}])+'\n'))};
    const roles=Object.fromEntries(['catalogue','physical_evidence','physical_input','physical_reproduction','owner_roster','native_latitudes']
      .map(role=>[role,f.leaf('source-target-'+role+'.json')]));
    const parts=[f.leaf('source-family-part.json')];
    if(retainedRoles){
      for(const value of [roles.physical_reproduction,roles.native_latitudes,parts[0]])f.authored.entries.delete(value.path);
      roles.physical_reproduction=f.put('coordination/engineering/prior/physical-reproduction.py','print(1)\n',true);
      roles.native_latitudes=f.put('coordination/engineering/prior/native-row-latitudes.f64le.gz',gzipSync(Buffer.from([0,1,2,3,4,5,6,7])),true);
      parts[0]=f.put('coordination/engineering/prior/source-family-part.bin.gz',gzipSync(Buffer.from('retained source bytes')),true);
    }
    mutateRoles({f,roles,parts});
    const evidence=f.put(prefix+'source-target-evidence.json',{version:1,kind:'source-target-native-evidence-v1',...roles,
      targets:[{id:'target-new'}],families:[{source_id:'source-family',parts:emptyFamily?[]:parts}],
      ...(sourceMembership?{source_membership:sourceMembership(f)}:{})});
    const patch=f.leaf('source-target-native-patch.json');
    const body={version:1,kind:'source-target-native-custody-v1',source_evidence:evidence,native_patch:patch};
    const authority=f.put(prefix+'source-target-authority.json',body);
    const rule=f.put(prefix+'source-target-rule.json',{...body,kind:'source-target-native-rule-v1',
      native_patch:wrongRule?f.leaf('foreign-source-target-patch.json'):patch});
    f.registryBody.entries.push({authority_sha256:'c'.repeat(64),policy_id:'retained-source-literal-additions',policy_version:1,
      rule_preimage:rule,rule_sha256:rule.sha256,source_authority:authority});
    refreshPins(f);
  }});
}
test('source-target native roles and literal native-row expectations use the existing selected-data route',async()=>{
  const diagnostics={};assert.ok(await sourceTargetRoleFixture().run({metadataDiagnostics:diagnostics}),diagnostics.failure);
});
test('source-target native roles reject a rehashed foreign rule join and incomplete family roles',async()=>{
  assert.equal(await sourceTargetRoleFixture({wrongRule:true}).run(),null);
  assert.equal(await sourceTargetRoleFixture({emptyFamily:true}).run(),null);
});

test('fixed source roles admit unchanged accepted reproduction and binary inputs without suffix exceptions',async()=>{
  const f=sourceTargetRoleFixture({retainedRoles:true}),diagnostics={};
  assert.equal((await f.run({metadataDiagnostics:diagnostics}))?.test_selection,'selected-data',diagnostics.failure);
  for(const suffix of ['physical-reproduction.py','native-row-latitudes.f64le.gz','source-family-part.bin.gz']){
    const name='coordination/engineering/prior/'+suffix;
    assert(!f.reads.includes(f.authored.entries.get(name).sha),'unchanged role body was unnecessarily reread');
  }
});
test('unchanged fixed-role admission follows exact identity rather than known filename suffixes',async()=>{
  const f=sourceTargetRoleFixture({retainedRoles:true,mutateRoles:({f,roles,parts})=>{
    roles.physical_reproduction=f.put('coordination/engineering/prior/reproducer.unfamiliar','accepted code',true);
    parts[0]=f.put('coordination/engineering/prior/raw-source-without-extension',Buffer.from([8,7,6]),true);
  }}),diagnostics={};
  assert.equal((await f.run({metadataDiagnostics:diagnostics}))?.test_selection,'selected-data',diagnostics.failure);
});
for(const [label,mutateRoles] of Object.entries({
  'new executable':({f,roles})=>{roles.physical_reproduction=f.put(prefix+'physical-reproduction.py','new code');},
  'changed executable':({f,roles})=>{roles.physical_reproduction=f.put(roles.physical_reproduction.path,'changed code');},
  'changed binary source':({f,parts})=>{parts[0]=f.put(parts[0].path,Buffer.from([1,2,3]));},
  'forged blob pin':({roles})=>{roles.physical_reproduction.git_blob_oid='0'.repeat(40);},
  'forged byte count':({roles})=>{roles.physical_reproduction.bytes++;},
  'missing blob binding':({roles})=>{delete roles.physical_reproduction.git_blob_oid;},
  'missing mode binding':({roles})=>{delete roles.physical_reproduction.mode;},
  'missing hash binding':({roles})=>{delete roles.physical_reproduction.sha256;},
  'missing immutable commit':({roles})=>{delete roles.physical_reproduction.commit;},
  'invalid hash pin':({roles})=>{roles.physical_reproduction.sha256='invalid';},
  'executable mode':({f,roles})=>{const name=roles.physical_reproduction.path;f.authored.entries.set(name,{...f.authored.entries.get(name),mode:'100755'});roles.physical_reproduction.mode='100755';},
  'baseline executable mode':({f,roles})=>{const name=roles.physical_reproduction.path;f.baseline.entries.set(name,{...f.baseline.entries.get(name),mode:'100755'});},
  'symlink mode':({f,roles})=>{const name=roles.physical_reproduction.path;f.authored.entries.set(name,{...f.authored.entries.get(name),mode:'120000'});},
}))test('unchanged fixed source roles reject '+label,async()=>{
  const f=sourceTargetRoleFixture({retainedRoles:true,mutateRoles});
  assert.equal(await f.run(),null);
});

test('accepted source membership fixed roles remain in selected-data closure',async()=>{
  for(const missing of [false,true]){
    const f=sourceTargetRoleFixture({sourceMembership:f=>({index:f.leaf('member-index.json'),
      lineage:f.leaf('member-lineage.json'),parts:missing?[]:[f.leaf('member-geography.json')]})});
    const diagnostics={},result=await f.run({metadataDiagnostics:diagnostics});
    if(missing)assert.equal(result,null);else assert.equal(result?.test_selection,'selected-data',diagnostics.failure);
  }
});

// Scientific receipts remain independently validated. These tiny metadata
// fixtures exercise eligibility and propagation, not scientific correctness.
function scientificManifestFixture() {
  const f=ownedFixture(), name='coordination/engineering/retained-delivery/evidence-quality.json';
  f.put(name,{version:1,issue:10,outputs:[]},true);
  f.put(name,{version:1,issue:10,outputs:[{path:f.packetPrefix+'ledger.json'}]});
  f.files.push({filename:name,status:'modified'});
  f.reservation.evidence_manifest=name;
  f.evidenceQuality={version:1,manifest_path:name,subject_ids:[],pins:{},review_kind:'code'};
  const part=f.put('data/base-native/rows.bin.gz','immutable native body',true), bounds=f.put('data/base-native/bounds.json.gz','immutable bounds',true);
  const native=f.put('data/base-native/manifest.json',{version:2,method:f.base.method,parts:[{kind:'rows',path:'rows.bin.gz'}],
    bounds:{path:'bounds.json.gz'},original_assets:{bounds:{path:bounds.path}}},true);
  const consumer=f.put('coordination/engineering/prior/application-code.json',{version:1,kind:'qualified-artifact-application-code-closure-v1',
    critical_files:[{path:SELECTED_SMOKE,bytes:1,sha256:'a'.repeat(64)}]},true), qualification=f.leaf('qualification.json',true);
  const certificate=f.put('coordination/engineering/prior/base-consumption.json',{version:1,kind:'qualified-arctic-immutable-product-certificate-v1',
    application_consumer_code:consumer,qualification_inventory:qualification,application_inputs:[consumer,qualification]},true);
  const comparison=f.leaf('native-comparison.json',true);
  f.put('scripts/native-ownership/verified-candidates.json',{version:1,candidates:{[native.sha256]:{role:'reviewed-exhaustive-native-rule-comparison',path:comparison.path}}},true);
  f.base.manifest_path=native.path;f.base.sha256=native.sha256;f.base.artifact_consumption.certificate=certificate;
  const old=JSON.parse(f.blobs.get(f.baseline.entries.get('data/ownership-selection.json').sha));
  f.put('data/ownership-selection.json',{...f.base,additive_release:old.additive_release},true);
  const side=f.put(f.packetPrefix+'selection-sidecar.json',{...f.sidecarBody,base_selection:f.base});
  f.put('data/ownership-selection.json',{...f.base,additive_release:{path:side.path,bytes:side.bytes,sha256:side.sha256}});
  f.manifestPath=name;return f;
}
test('only the authenticated unconsumed scientific receipt update enters existing selected checks',async()=>{
  const f=scientificManifestFixture();
  assert.equal(selectedDataCandidate(f.branch,f.files),false);
  assert.equal(selectedDataCandidate(f.branch,f.files,f.reservation),true);
  assert.equal((await f.run()).test_selection,'selected-data');
  assert(f.reads.includes(f.authored.entries.get(f.manifestPath).sha),'modified manifest syntax was actually read');
  assert.equal((await gateFixture(scientificManifestFixture()).select()).test_selection,'selected-data');
  const prepared=await prepareIntegration(mergeFixture({selectedFixture:scientificManifestFixture()}).options);
  assert.equal(prepared.test_selection,'selected-data');
  const final=mergeFixture({selectedFixture:scientificManifestFixture()});
  assert.equal((await final.complete()).accepted,true);assert.equal(final.writes.length,1);
});
for(const [name,change] of Object.entries({
  'undeclared manifest':f=>delete f.reservation.evidence_manifest,
  'foreign manifest declaration':f=>f.reservation.evidence_manifest='coordination/engineering/other/evidence-quality.json',
  'arbitrary other edited JSON':f=>{const name=f.packetPrefix+'notes.json';f.put(name,{},true);f.put(name,{updated:true});f.files.push({filename:name,status:'modified'});},
  'renamed manifest':f=>f.files.find(row=>row.filename===f.manifestPath).previous_filename=f.packetPrefix+'old-evidence-quality.json',
  'removed manifest':f=>f.files.find(row=>row.filename===f.manifestPath).status='removed',
  'new manifest reported modified':f=>f.baseline.entries.delete(f.manifestPath),
  'baseline symlink manifest':f=>f.baseline.entries.get(f.manifestPath).mode='120000',
  'candidate symlink manifest':f=>f.authored.entries.get(f.manifestPath).mode='120000',
  'executable-mode manifest':f=>f.authored.entries.get(f.manifestPath).mode='100755',
  'malformed manifest JSON':f=>f.put(f.manifestPath,'throw new Error("not JSON")'),
  'manifest in package inputs':f=>{f.definition.inputs.push(f.manifestPath);f.put('.github/package-inputs.json',f.definition);},
  'manifest in package verification paths':f=>{f.policy.verification_paths.push(f.manifestPath);f.definition.verification_paths.push(f.manifestPath);f.put('.github/package-inputs.json',f.policy,true);f.put('.github/package-inputs.json',f.definition);},
  'manifest in selected role graph':f=>{const manifest=f.put(f.manifestPath,{version:1});const side=f.put(f.packetPrefix+'selection-sidecar.json',{...f.sidecarBody,logical_asset_map:{...f.sidecarBody.logical_asset_map,patch:manifest}});f.put('data/ownership-selection.json',{...f.base,additive_release:{path:side.path,bytes:side.bytes,sha256:side.sha256}});},
  'mixed software change':f=>{f.put('src/renderer.js','export const changed=true');f.files.push({filename:'src/renderer.js',status:'modified'});},
  'changed base authority':f=>f.put('data/ownership-selection.json',{...f.base,manifest_path:'other-base.json',additive_release:{path:f.packetPrefix+'selection-sidecar.json',bytes:1,sha256:'0'.repeat(64)}}),
}))test('scientific metadata update preserves full fallback for '+name,async()=>{const f=scientificManifestFixture();change(f);assert.equal(await f.run(),null);});
for(const role of ['manifest_path','selected_geography','certificate','review'])test('scientific receipt cannot be an accepted base '+role+' role',async()=>{
  const f=scientificManifestFixture();
  if(role==='manifest_path')f.base.manifest_path=f.manifestPath;
  else if(role==='selected_geography')f.base.selected_geography={path:f.manifestPath};
  else f.base.artifact_consumption[role]={path:f.manifestPath};
  const old=JSON.parse(f.blobs.get(f.baseline.entries.get('data/ownership-selection.json').sha));
  f.put('data/ownership-selection.json',{...f.base,additive_release:old.additive_release},true);
  const side=f.put(f.packetPrefix+'selection-sidecar.json',{...f.sidecarBody,base_selection:f.base});
  f.put('data/ownership-selection.json',{...f.base,additive_release:{path:side.path,bytes:side.bytes,sha256:side.sha256}});
  assert.equal(await f.run(),null);
});
test('author classification requires the current linked issue declaration, never candidate manifest self-claims',async()=>{
  const f=gateFixture(scientificManifestFixture());
  const spec=JSON.parse(/<!-- worldatlas-work:v1\n([\s\S]*?)\n-->/.exec(f.issue.body)[1]);
  delete spec.evidence_quality;f.issue.body='<!-- worldatlas-work:v1\n'+JSON.stringify(spec)+'\n-->';
  assert.deepEqual(await f.select(),{profile:'full',shards:[0,1,2],geography_software:false});
});
test('cold queue scientific validation failure cannot reach merge despite eligible metadata',async()=>{
  const f=mergeFixture({selectedFixture:scientificManifestFixture()});
  await assert.rejects(f.complete({evidenceCheck:async()=>{throw Error('Changed scientific evidence is invalid');}}),/scientific evidence/);
  assert.equal(f.writes.length,0);
});

function realScientificManifest1906() {
  const fixed=JSON.parse(readFileSync(new URL('./fixtures/selected-scientific-manifest-pr1906.json',import.meta.url)));
  const baseline={object:{sha:fixed.base},entries:new Map(fixed.baseline_rows.map(row=>[row.path,{...row}]))},
    authored={object:{sha:fixed.head},entries:new Map(fixed.authored_rows.map(row=>[row.path,{...row}]))};
  const blobs=new Map(),reads=[],files=structuredClone(fixed.files);
  for(const row of fixed.snapshots){
    const raw=gunzipSync(Buffer.from(row.gzip_base64,'base64'),{maxOutputLength:row.bytes});
    assert.equal(raw.length,row.bytes);assert.equal(digest(raw),row.sha256);
    assert.equal(createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex'),row.git_blob_oid);
    blobs.set(row.git_blob_oid,raw);
  }
  const api=async route=>{assert(route.includes('/git/blobs/'),route);const sha=route.split('/').at(-1),raw=blobs.get(sha);assert(raw,sha);
    reads.push(sha);return {sha,size:raw.length,encoding:'base64',content:raw.toString('base64')};};
  const reservation=verifyIssueScope({branch:fixed.branch,issue:fixed.issue});
  const f={fixed,files,branch:fixed.branch,baseline,authored,blobs,reads,api,reservation};
  f.run=(options={})=>selectedDataSelection({api:f.api,repo:'ChengshuLi/WorldAtlas',branch:f.branch,files:f.files,
    baseline,authored,reservation:f.reservation,...options});return f;
}
test('complete immutable PR1906 metadata removes the observed manifest-only early fallback',async()=>{
  const f=realScientificManifest1906(),stats={};
  assert.equal(f.fixed.head,'92131353e8dba4bf109bfec2f6ad46628977b8fb');assert.equal(f.files.length,19);
  const {evidence_manifest,...scope}=f.reservation;
  assert.equal(selectedDataCandidate(f.branch,f.files,scope),false,'original scope-only boundary rejected this exact diff');
  assert.equal(selectedDataCandidate(f.branch,f.files,f.reservation),true);
  assert.deepEqual(await f.run({metadataDiagnostics:stats}),{test_selection:'selected-data',
    expectations_path:'coordination/engineering/vietnam-current-cell-20261014/mapping-followup-001/delivery/selected-delivery-expectations.json',shards:[0]});
  assert.equal(stats.read_count,28);assert.equal(stats.read_bytes,5060083);
  assert(f.reads.includes(f.authored.entries.get(evidence_manifest).sha),'actual changed scientific manifest was parsed');
});
for(const [name,change] of Object.entries({
  'unknown issue manifest':f=>delete f.reservation.evidence_manifest,
  'missing current manifest':f=>f.authored.entries.delete(f.reservation.evidence_manifest),
  'base manifest nonordinary':f=>f.baseline.entries.get(f.reservation.evidence_manifest).mode='120000',
  'changed accepted smoke':f=>f.authored.entries.get(SELECTED_SMOKE).sha='0'.repeat(40),
  'actual renderer modification':f=>f.files.push({filename:'src/app.js',status:'modified'}),
  'other existing packet JSON edit':f=>f.files.push({filename:'coordination/engineering/vietnam-current-cell-20261014/other.json',status:'modified'}),
  'unavailable manifest bytes':f=>f.blobs.delete(f.authored.entries.get(f.reservation.evidence_manifest).sha),
}))test('original PR1906 keeps complete fallback for '+name,async()=>{const f=realScientificManifest1906();change(f);assert.equal(await f.run(),null);});
test('eligible scientific metadata never replaces the actual independent scientific validator',async()=>{
  const f=mergeFixture({selectedFixture:scientificManifestFixture()});
  assert.equal((await selectedDataSelection({...f.options,branch:f.branch,files:f.files,baseline:f.baseline,authored:f.authored,
    reservation:{mode:'engineering',owned_paths:f.ownedPaths,evidence_manifest:f.manifestPath}})).test_selection,'selected-data');
  await assert.rejects(checkPremergeEvidence({...f.options,pr:f.pr,issue:f.issue,
    reservation:{mode:'engineering',owned_paths:f.ownedPaths},files:f.files}),/Invalid or oversized evidence inventory/);
  await assert.rejects(f.complete({evidenceCheck:checkPremergeEvidence}),/Invalid or oversized evidence inventory/);
  assert.equal(f.writes.length,0);
});

function baseRoutingManifestFixture(change) {
  const f=scientificManifestFixture(),document=name=>JSON.parse(f.blobs.get(f.authored.entries.get(name).sha));
  const native=document(f.base.manifest_path),certificate=document(f.base.artifact_consumption.certificate.path),
    code=document(certificate.application_consumer_code.path),oldNativeHash=f.base.sha256;
  const existing=f.baseline.entries.get(f.manifestPath),consumed={path:f.manifestPath,bytes:existing.size,
    mode:existing.mode,sha256:digest(f.blobs.get(existing.sha))};
  let nativePath=f.base.manifest_path;
  const state={f,native,certificate,code,consumed,document,setNativePath:name=>nativePath=name};
  change(state);
  const codePin=f.put(certificate.application_consumer_code.path===f.manifestPath
    ? 'coordination/engineering/prior/application-code.json':certificate.application_consumer_code.path,code,true);
  if(certificate.application_consumer_code.path!==f.manifestPath)certificate.application_consumer_code=codePin;
  const cert=f.put(f.base.artifact_consumption.certificate.path,certificate,true);
  const manifest=f.put(nativePath,native,true);
  const verified=document('scripts/native-ownership/verified-candidates.json'),receipt=verified.candidates[oldNativeHash];
  f.put('scripts/native-ownership/verified-candidates.json',{...verified,candidates:{[manifest.sha256]:receipt}},true);
  f.base.manifest_path=nativePath;f.base.sha256=manifest.sha256;f.base.artifact_consumption.certificate=cert;
  const old=document('data/ownership-selection.json');
  const oldBaseline=JSON.parse(f.blobs.get(f.baseline.entries.get('data/ownership-selection.json').sha));
  f.put('data/ownership-selection.json',{...f.base,additive_release:oldBaseline.additive_release},true);
  const side=f.put(f.packetPrefix+'selection-sidecar.json',{...document(old.additive_release.path),base_selection:f.base});
  f.put('data/ownership-selection.json',{...f.base,additive_release:{path:side.path,bytes:side.bytes,sha256:side.sha256}});
  return f;
}
for(const [name,change] of Object.entries({
  'certificate application-consumer code':s=>s.certificate.application_consumer_code=s.consumed,
  'certificate qualification inventory':s=>s.certificate.qualification_inventory=s.consumed,
  'certificate release catalogue':s=>s.certificate.release_product_catalogue=s.consumed,
  'certificate selected registry':s=>{s.certificate.release_product_catalogue=s.certificate.qualification_inventory;s.certificate.selected_artifact_bindings={registry:s.consumed};},
  'complete certificate application input':s=>s.certificate.application_inputs.push(s.consumed),
  'application critical source':s=>s.code.critical_files.push(s.consumed),
  'application entry critical source':s=>s.code.entry_critical_files={'scripts/build-hosted-inner.mjs':[s.consumed]},
  'native part':s=>{s.setNativePath('coordination/engineering/retained-delivery/base-native-manifest.json');s.native.parts=[{kind:'rows',path:'evidence-quality.json'}];},
  'native bounds alias':s=>{s.setNativePath('coordination/engineering/retained-delivery/base-native-manifest.json');s.native.bounds.path='evidence-quality.json';},
  'original bounds pin':s=>s.native.original_assets.bounds=s.consumed,
  'native transport index':s=>s.native.native_asset_transport={version:1,kind:'ordered-exact-original-byte-fragments',index:s.consumed},
  'native transport fragment':s=>{const index=s.f.put('coordination/engineering/retained-delivery/index.json',
    {version:1,kind:'ordered-exact-original-byte-fragments',parts:[{path:'evidence-quality.json'}]},true);
    s.native.native_asset_transport={version:1,kind:'ordered-exact-original-byte-fragments',index};},
  'selected source bank':s=>s.f.base.selected_geography={...s.consumed,version:1,kind:'complete-world-index-with-exact-encoded-overrides'},
  'selected source world index':s=>{const bank=s.f.put('data/base-source-bank.json',{version:1,kind:'complete-world-index-with-exact-encoded-overrides',
    world_index:s.consumed,unchanged_files:[],overrides:[]},true);s.f.base.selected_geography={...bank,version:1,kind:'complete-world-index-with-exact-encoded-overrides'};},
  'selected unchanged source':s=>{const bank=s.f.put('data/base-source-bank.json',{version:1,kind:'complete-world-index-with-exact-encoded-overrides',
    world_index:s.certificate.qualification_inventory,unchanged_files:[s.consumed],overrides:[]},true);s.f.base.selected_geography={...bank,version:1,kind:'complete-world-index-with-exact-encoded-overrides'};},
  'selected source override':s=>{const bank=s.f.put('data/base-source-bank.json',{version:1,kind:'complete-world-index-with-exact-encoded-overrides',
    world_index:s.certificate.qualification_inventory,unchanged_files:[],overrides:[s.consumed]},true);s.f.base.selected_geography={...bank,version:1,kind:'complete-world-index-with-exact-encoded-overrides'};},
  'selected native comparison receipt':s=>{const name='scripts/native-ownership/verified-candidates.json',verified=s.document(name);
    verified.candidates[s.f.base.sha256].path=s.f.manifestPath;s.f.put(name,verified,true);},
  'unknown consumption certificate':s=>s.certificate.kind='future-unknown-consumption',
  'unknown application source metadata':s=>s.code.kind='future-unknown-code-routing',
  'unknown native transport':s=>s.native.native_asset_transport={version:2,kind:'unknown'},
  'missing native part roster':s=>delete s.native.parts,
}))test('edited scientific receipt retains complete regression for deeper '+name,async()=>{
  const f=baseRoutingManifestFixture(change),stats={};assert.equal(await f.run({metadataDiagnostics:stats}),null,name);
  assert(stats.failure,name);
});
test('deeper base metadata must be ordinary, unchanged, available and authenticated',async()=>{
  for(const mode of ['100755','120000','160000']){
    const f=scientificManifestFixture();f.authored.entries.get(f.base.artifact_consumption.certificate.path).mode=mode;
    assert.equal(await f.run(),null,mode);
  }
  const unavailable=scientificManifestFixture();unavailable.blobs.delete(unavailable.authored.entries.get(unavailable.base.artifact_consumption.certificate.path).sha);
  assert.equal(await unavailable.run(),null);
  const changed=scientificManifestFixture();changed.put(changed.base.artifact_consumption.certificate.path,{version:1});
  assert.equal(await changed.run(),null);
});


function historicalProducerRoleFixture({mutatePin = () => {}, mixedRole = false, unavailableTree = false} = {}) {
  let original, live;
  const f = sourceTargetRoleFixture({retainedRoles: true, mutateRoles: ({f, roles}) => {
    const oldPath = roles.physical_reproduction.path;
    f.authored.entries.delete(oldPath); f.baseline.entries.delete(oldPath);
    live = f.put('scripts/qualify-source-cohort.py', '# current accepted helper\n', true);
    const raw = Buffer.from('# original physical producer\n'), oid = createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
    f.blobs.set(oid, raw);
    original = {path: live.path, commit: '4'.repeat(40), mode: '100644', git_blob_oid: oid, bytes: raw.length, sha256: digest(raw)};
    roles.physical_reproduction = {...original}; mutatePin(roles.physical_reproduction);
    if (mixedRole) roles.physical_input = {...original};
  }});
  const ordinaryAPI = f.api;
  f.api = async route => {
    if (route.endsWith('/git/commits/' + original.commit)) return {sha: original.commit, tree: {sha: 'historical-producer-tree'}};
    if (route.endsWith('/git/trees/historical-producer-tree?recursive=1')) return {truncated: unavailableTree, tree: [
      {path: original.path, mode: original.mode, type: 'blob', sha: original.git_blob_oid, size: original.bytes}]};
    return ordinaryAPI(route);
  };
  return {...f, original, live};
}

test('historical physical reproduction authenticates original Git bytes while current code stays unchanged', async () => {
  const f = historicalProducerRoleFixture(), before = {...f.authored.entries.get(f.live.path)}, diagnostics = {};
  assert.equal((await f.run({metadataDiagnostics: diagnostics}))?.test_selection, 'selected-data', diagnostics.failure);
  assert(f.reads.includes(f.original.git_blob_oid), 'whole original programme bytes must be read');
  assert.deepEqual(f.authored.entries.get(f.live.path), before);
  assert.equal(f.files.some(file => file.filename === f.live.path), false);
});

test('historical physical reproduction cannot bypass original pin, data or current-code guards', async () => {
  for (const mutatePin of [pin => pin.sha256 = 'f'.repeat(64), pin => pin.git_blob_oid = 'f'.repeat(40),
    pin => pin.bytes++, pin => pin.mode = '100755', pin => pin.commit = '5'.repeat(40)])
    assert.equal(await historicalProducerRoleFixture({mutatePin}).run(), null);
  assert.equal(await historicalProducerRoleFixture({mixedRole: true}).run(), null);
  const changed = historicalProducerRoleFixture();
  changed.put(changed.live.path, '# changed current executable\n');
  assert.equal(await changed.run(), null, 'even a silently omitted changed-file entry cannot use historical custody');
  changed.files.push({filename: changed.live.path, status: 'modified'});
  assert.equal(await changed.run(), null, 'an actual current software change retains full routing');
});


test('historical physical reproduction cannot use an unavailable complete original tree', async () => {
  const f = historicalProducerRoleFixture({unavailableTree: true}), diagnostics = {};
  assert.equal(await f.run({metadataDiagnostics: diagnostics}), null);
  assert.match(diagnostics.failure, /incomplete tree inventory/);
  assert.equal(f.reads.includes(f.original.git_blob_oid), false, 'no unbound historical body read');
});
