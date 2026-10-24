import test from 'node:test';

import assert from 'node:assert/strict';

import {createHash} from 'node:crypto';

import {prepareIntegration, completeIntegration} from '../scripts/merge-integration.mjs';

import {selectedDataSelection, selectedDataCandidate, candidateGeographyCode, SELECTED_SMOKE} from '../scripts/integration-profile.mjs';

const prefix = 'coordination/engineering/fixture-delivery/';

const digest = bytes => createHash('sha256').update(bytes).digest('hex');

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
  const part=put('data/base-native/rows.bin.gz','immutable native body',true), bounds=put('data/base-native/bounds.json.gz','immutable bounds',true);
  const native=put('data/base-native/manifest.json',{version:2,method:base.method,parts:[{kind:'rows',path:'rows.bin.gz'}],
    bounds:{path:'bounds.json.gz'},original_assets:{bounds:{path:bounds.path}}},true);
  const consumer=put('coordination/engineering/prior/application-code.json',{version:1,kind:'qualified-artifact-application-code-closure-v1',
    critical_files:[{path:SELECTED_SMOKE,bytes:1,sha256:'a'.repeat(64)}]},true), qualification=leaf('qualification.json',true);
  const baseCertificate=put('coordination/engineering/prior/base-consumption.json',{version:1,kind:'qualified-arctic-immutable-product-certificate-v1',
    application_consumer_code:consumer,qualification_inventory:qualification,application_inputs:[consumer,qualification]},true);
  const comparison=leaf('native-comparison.json',true);
  put('scripts/native-ownership/verified-candidates.json',{version:1,candidates:{[native.sha256]:{role:'reviewed-exhaustive-native-rule-comparison',path:comparison.path}}},true);
  base.manifest_path=native.path;base.sha256=native.sha256;base.artifact_consumption.certificate=baseCertificate;
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
    if(route===root+'/git/commits/'+candidate)return {sha:candidate,tree:{sha:f.integrated?'integrated-tree':'head-tree'},parents:[{sha:f.base},{sha:f.head}]};
    if(route===root+'/git/trees/integrated-tree?recursive=1')return {tree:[...f.integrated.entries.values()],truncated:false};
    if(route===root+'/contents/.github/package-inputs.json?ref='+candidate){
      const row=(f.integrated??f.authored).entries.get('.github/package-inputs.json'),bytes=f.blobs.get(row.sha);
      assert(bytes,'Candidate definition must come from its actual integrated tree');
      return {type:'file',path:row.path,sha:row.sha,size:row.size,encoding:'base64',content:bytes.toString('base64')};
    }
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

test('final checker choice skips selected-data classification when no candidate code path exists', async () => {
  const f = mergeFixture(), diagnostics = {};
  assert.equal(selectedDataCandidate(f.pr.head.ref, f.files), true);
  assert.equal(candidateGeographyCode('full', f.files), false);
  const result = await f.complete({metadataDiagnostics: diagnostics});
  assert.equal(result.accepted, true);
  assert.equal(result.geography.trusted_code_commit, f.base);
  assert.deepEqual(diagnostics, {}, 'eligible classifier was never entered');
  assert.equal(f.reads.length, 0, 'no classifier metadata or supporting bodies were read');
  assert.equal(f.mergeReads.filter(route=>route==='/repos/owner/repo/git/commits/'+f.base).length,1, 'one baseline tree for actual execution routing');
  assert.equal(f.mergeReads.filter(route=>route==='/repos/owner/repo/git/trees/base-tree?recursive=1').length,1);
  assert.equal(f.writes.length, 1);
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

const administrativePath = 'coordination/engineering/melanesia363-additive-delivery-20261010/accepted-administrative-handoffs.json';

function ownedFixture({mutate = () => {}} = {}) {
  const packetPrefix = 'coordination/engineering/retained-delivery/new-packet/';
  const f = fixture({packetPrefix, mutate});
  f.branch = 'engineering/rotated-delivery'; f.ownedPaths = ['coordination/engineering/retained-delivery/'];
  f.reservation = {mode:'engineering', owned_paths:f.ownedPaths}; f.packetPrefix = packetPrefix;
  f.run = (options = {}) => selectedDataSelection({api:f.api, repo:'owner/repo', branch:f.branch, files:f.files,
    baseline:f.baseline, authored:f.authored, reservation:f.reservation, ...options});
  return f;
}

function scientificManifestFixture() {
  const f=ownedFixture(), name='coordination/engineering/retained-delivery/evidence-quality.json';
  f.put(name,{version:1,issue:10,outputs:[]},true);
  f.put(name,{version:1,issue:10,outputs:[{path:f.packetPrefix+'ledger.json'}]});
  f.files.push({filename:name,status:'modified'});
  f.reservation.evidence_manifest=name;
  f.evidenceQuality={version:1,manifest_path:name,subject_ids:[],pins:{},review_kind:'code'};
  f.manifestPath=name;return f;
}

function retainedEvidenceFixture(name = 'execution/retained-helper.mjs', body = 'throw Error("must never execute");\n') {
  const f = scientificManifestFixture(), member = f.packetPrefix + name;
  const pin = f.put(member, body);
  f.files.push({filename: member, status: 'added'});
  return Object.assign(f, {retainedName: member, retainedPin: pin});
}

test('final checker choice fails closed when candidate-code classification is unavailable', async () => {
  for (const failure of ['baseline tree', 'consumed ledger']) {
    const f = mergeFixture({selectedFixture: retainedEvidenceFixture()}), original = f.options.api;
    if (failure === 'consumed ledger') f.blobs.delete(f.authored.entries.get(f.sidecarBody.logical_asset_map.ledger.path).sha);
    else f.options.api = async (route, ...args) => {
      if (route === '/repos/owner/repo/git/commits/' + f.base) throw Error('Unavailable baseline tree');
      return original(route, ...args);
    };
    assert.equal(candidateGeographyCode('full', f.files), true);
    await assert.rejects(f.complete(), failure==='baseline tree'?/Unavailable baseline tree/:/exact trusted combined check/);
    assert.equal(f.writes.length, 0, failure);
    const candidateReport = {geographyReportLoader: async () => ({
      version: 1, method_id: 'worldatlas-trusted-geography-check-v1', baseline_commit: f.base,
      trusted_code_commit: f.pr.merge_commit_sha, candidate_commit: f.pr.merge_commit_sha,
      trusted_code_inventory_sha256: 'd'.repeat(64), candidate_code_executed: true,
      published: false, source_approval: false, gate_status: 'passed', status: 'not-applicable'
    })};
    if(failure==='baseline tree'){
      await assert.rejects(f.complete(candidateReport),/Unavailable baseline tree/);
      assert.equal(f.writes.length,0,'Neither report can replace unavailable routing identities');
      continue;
    }
    const result=await f.complete(candidateReport);
    assert.equal(result.accepted, true, failure);
    assert.equal(result.geography.trusted_code_commit, f.pr.merge_commit_sha);
    assert.equal(f.writes.length, 1);
  }
});
