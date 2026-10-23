import {execFileSync, spawnSync} from 'node:child_process';
import {candidateGeographyCode, inertEvidenceAdditions} from '../scripts/integration-profile.mjs';
import {memoizeImmutableGitBlobs} from '../scripts/immutable-git-blobs.mjs';
import {fullCheckoutPatterns,focusedCheckoutPatterns,loadPackageInputs,packagePathRequired} from '../scripts/package-inputs.mjs';
import {sha256, subjectsHash} from '../scripts/evidence-quality.mjs';
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import os from 'node:os';
import path from 'node:path';
import {focusedIntegrationTest, integrationTestFiles, integrationNeedsBrowser, prepareIntegrationTests} from '../scripts/run-integration-tests.mjs';
import {renderClaim, githubAPI} from '../scripts/issue-claim-contract.mjs';
import {reviewedTestPlan, prepareIntegration, completeIntegration, checkCurrentChecks, integrationProfile, integrationChanges, geographyRequired, createCandidate, cleanupCandidate, cleanupMergedHead} from '../scripts/merge-integration.mjs';

import {EXECUTION_CODE, REBIND_CODE} from '../scripts/check-unchanged-selected-geography.mjs';
import {staticModuleClosure} from './helpers/static-module-closure.mjs';
const sha = letter => letter.repeat(40);
const FOCUSED_INTEGRATION_TESTS = integrationTestFiles('evidence', 0);

test('actual sparse preparation imports method inventories without scientific coordination files', () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'atlas-sparse-prepare-'));
  try {
    // Exactly the namespaces selected by worker-merge.yml prepare, plus its
    // ordinary root package metadata. No coordination files or dependencies.
    for (const name of ['scripts', 'src', '.github']) fs.cpSync(name, path.join(temporary, name), {recursive: true});
    fs.copyFileSync('package.json', path.join(temporary, 'package.json'));
    assert.equal(fs.existsSync(path.join(temporary, 'coordination')), false);
    const output = execFileSync(process.execPath, ['--input-type=module', '-e',
      "await import('./scripts/merge-integration.mjs'); console.log('sparse-prepare-import-passed');"],
      {cwd: temporary, encoding: 'utf8'});
    assert.equal(output.trim(), 'sparse-prepare-import-passed');
  } finally { fs.rmSync(temporary, {recursive: true, force: true}); }
});

test('only staging-test shards prepare the immutable migration derivative', () => {
  const cwd=process.cwd(), temporary=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-integration-prerequisite-'));
  fs.cpSync('drizzle',path.join(temporary,'drizzle'),{recursive:true});
  const original=fs.readFileSync(path.join(temporary,'drizzle/0002_geographic_reference_releases.sql'));
  try {
    process.chdir(temporary);
    assert.throws(()=>prepareIntegrationTests(['test/compact-ownership.test.mjs']),/requires the actual hosted build/);
    assert.throws(()=>prepareIntegrationTests(['test/prepared-parity.test.mjs']),/requires the actual hosted build/);
    prepareIntegrationTests(['test/merge-integration.test.mjs']);
    assert.equal(fs.existsSync('dist'),false);
    prepareIntegrationTests(['test/stage-site-migrations.test.mjs']);
    const receipt=JSON.parse(fs.readFileSync('dist/drizzle/transport-receipt.json'));
    assert.equal(receipt.source_sql_rewritten,false);
    assert.equal(receipt.migrations.length,fs.readdirSync('drizzle').filter(name=>name.endsWith('.sql')).length);
    assert.deepEqual(fs.readFileSync('drizzle/0002_geographic_reference_releases.sql'),original);
  } finally { process.chdir(cwd); fs.rmSync(temporary,{recursive:true,force:true}); }
});
test('new native dispatch refuses absent or blank intent before API setup without changing queued legacy inputs', () => {
  const workflow=fs.readFileSync('.github/workflows/worker-merge.yml','utf8');
  const field=workflow.match(/      reviewed_tests:\n([\s\S]*?)(?=      request_id:)/)[1];
  assert.match(field,/required: true/);assert.doesNotMatch(field,/default:/);
  assert.match(workflow,/REVIEWED_TESTS_REQUIRED: 'true'/);
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-dispatch-intent-'));
  try {
    for(const name of staticModuleClosure(process.cwd(),['scripts/run-worker-merge.mjs'])){
      const target=path.join(directory,name);fs.mkdirSync(path.dirname(target),{recursive:true});fs.copyFileSync(name,target);
    }
    fs.copyFileSync('package.json',path.join(directory,'package.json'));
    const event=path.join(directory,'event.json'),output=path.join(directory,'output');
    const invoke=(reviewed_tests,required=true)=>{
      fs.writeFileSync(event,JSON.stringify({inputs:{pr_number:'2',expected_head:sha('a'),request_id:'dispatch-intent-test',reviewed_tests}}));
      const env={...process.env,GH_TOKEN:'',GITHUB_TOKEN:'',NODE_OPTIONS:'',NODE_PATH:'',
        GITHUB_EVENT_PATH:event,GITHUB_REPOSITORY:'owner/repo',GITHUB_REF:'refs/heads/main',
        MERGE_PHASE:'prepare',GITHUB_OUTPUT:output};
      if(required)env.REVIEWED_TESTS_REQUIRED='true';else delete env.REVIEWED_TESTS_REQUIRED;
      return spawnSync(process.execPath,['scripts/run-worker-merge.mjs'],{cwd:directory,env,encoding:'utf8',timeout:10000});
    };
    for(const missing of [undefined,null,'','  ',{}]){
      const result=invoke(missing);assert.notEqual(result.status,0);
      assert.match(result.stderr,/Required reviewed_tests/);
      assert.doesNotMatch(result.stderr,/Read\/write GitHub token required/,'Intent rejects before constructing an API client');
      assert.equal(fs.existsSync(output),false);assert.equal(fs.existsSync(path.join(directory,'merge-result.json')),false);
    }
    // No credentials are supplied: reaching this existing boundary proves that
    // valid intent and already-queued old definitions survive the new check.
    for(const intent of ['auto','complete',JSON.stringify({base:sha('b'),head:sha('a'),files:['test/example.test.mjs']})])
      assert.match(invoke(intent).stderr,/Read\/write GitHub token required/);
    assert.match(invoke(undefined,false).stderr,/Read\/write GitHub token required/);
  } finally {fs.rmSync(directory,{recursive:true,force:true});}
});

function fixture({head=sha('a'),base=sha('b'),candidate=sha('c')}={}) {
  const repo = 'owner/repo';
  const issue = {number: 1, state: 'open', created_at: '2026-10-03T00:00:00Z', labels: ['type:engineering','kind:work-item','status:ready'],
    body: '<!-- worldatlas-work:v1\n'+JSON.stringify({mode:'engineering',max_prs:3,depends_on:[],scope:'code'})+'\n-->'};
  const pr = {number: 2, state: 'open', draft: false, body: 'Closes #1', title: 'Repair code', changed_files: 1,
    head: {sha: head, ref: 'engineering/test', repo: {full_name: repo}}, base: {ref:'main',sha:base},
    mergeable: true, merge_commit_sha: candidate};
  const claim = {version: 1, active: true, worker_id: 'worker', claim_id: 'nonce', branch:pr.head.ref,
    expires_at: new Date(Date.now()+3600000).toISOString()};
  const f = {repo, pr, issue, head, base, candidate, claim,
    packageInputs: {version:1, inputs:['.github/package-inputs.json'], optional_inputs:[], verification_paths:[], generated_outputs:[]}, writes: [], mainReads: 0, calls: [], refs: new Map(),
    checks: [{id:1, name:'scope',app:{id:1},status:'completed',conclusion:'success'}],
    baseline: [{path:'src/a.js',sha:'blob-before',mode:'100644',type:'blob'}],
    authored: [{path:'src/a.js',sha:'blob-a',mode:'100644',type:'blob'}],
    integrated: [{path:'src/a.js',sha:'blob-a',mode:'100644',type:'blob'}]};
  f.api = async (route, method='GET', body) => {
    const p=route.split('?')[0].replace('/repos/'+repo, '');
    f.calls.push({route,method,body});
    if(p==='/git/refs'&&method==='POST'){f.refs.set(body.ref.replace('refs/heads/',''),body.sha);return {ref:body.ref};}
    if(p==='/merges'&&method==='POST'){
      assert.notEqual(body.base,'main');assert.notEqual(body.base,f.pr.head.ref);assert.equal(body.head,head);
      if(f.pr.mergeable===false)throw Error('GitHub POST failed (HTTP 409)');
      f.refs.set(body.base,candidate);return {sha:candidate};
    }
    if(/\/git\/refs?\/heads\/worldatlas-integration\//.test(p)){
      const ref=p.split(/\/git\/refs?\/heads\//)[1];
      if(method==='DELETE'){f.refs.delete(ref);return null;}return {object:{sha:f.refs.get(ref)}};
    }
    if (method==='PUT') {f.writes.push(body);return {merged:true,sha:sha('f')};}
    if (p==='/contents/.github/package-inputs.json') {
      assert.equal(new URL('https://fixture.invalid'+route).searchParams.get('ref'), f.synthetic ?? candidate);
      const raw=Buffer.from(JSON.stringify(f.packageInputs));
      return {type:'file',path:'.github/package-inputs.json',encoding:'base64',size:raw.length,
        sha:createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex'),content:raw.toString('base64')};
    }
    if (p==='/pulls/2') return structuredClone(f.pr);
    if (p==='/issues/1') return structuredClone(f.issue);
    if (p==='/issues/1/comments') return [{id:1,user:{login:'github-actions[bot]'},body:renderClaim(f.claim)}];
    if (p==='/issues/1/timeline') return [];
    if (p==='/pulls/2/files') return [{filename:'src/a.js',status:'modified'}];
    if (p==='/commits/'+head+'/check-runs') return {check_runs:structuredClone(f.checks)};
    if (p==='/commits/'+head+'/status') {f.statusReads=(f.statusReads??0)+1;return f.failStatusOnRead===f.statusReads ? {statuses:[{}],state:'failure'} : {statuses:[]};}
    if (p==='/git/ref/heads/main') {f.mainReads++;return {object:{sha:f.advanceOnRead===f.mainReads?sha('d'):f.base}};}
    if (p==='/git/commits/'+f.base) return {tree:{sha:'baseline'}};
    if (p==='/git/trees/baseline') return {truncated:f.baselineTruncated??false,tree:f.baseline};
    if (p==='/git/commits/'+head) return {tree:{sha:'authored'}};
    if (p==='/git/commits/'+candidate) return {sha:candidate,tree:{sha:'integrated'},parents:[{sha:f.parentBase??f.base},{sha:head}]};
    if (p==='/git/trees/authored') return {truncated:false,tree:f.authored};
    if (p==='/git/trees/integrated') return {truncated:f.truncated??false,tree:f.integrated};
    throw Error('Unexpected API '+method+' '+route);
  };
  f.options = () => ({api:f.api,repo,number:2,expectedHead:head,policy:{version:1,mode:'enforce-new',activation_time:'2100-01-01T00:00:00Z'},
    integrationRequestId:'owned-candidate-test-request',
    evidenceCheck:async()=>{throw Error('Ordinary queue must not run the removed generic evidence traversal');}});
  f.complete = extra => completeIntegration({...f.options(),integrationResult:'success',geographyResult:'success',testedBase:base,testedCandidate:candidate,
    geographyReportLoader:async()=>({version:1,method_id:'worldatlas-trusted-geography-check-v1',
      baseline_commit:f.base,trusted_code_commit:f.base,candidate_commit:extra?.testedCandidate??candidate,candidate_code_executed:false,
      published:false,source_approval:false,gate_status:'passed',status:'not-applicable'}),...extra});
  return f;
}

test('final queue rejects incomplete or duplicate current PR inventory before computation or merge',async()=>{
 for(const duplicate of [false,true]){
  const f=fixture(), original=f.api;
  f.pr.changed_files=duplicate?2:1;
  f.api=async(route,...args)=>route.includes('/pulls/2/files')?(duplicate?[{filename:'src/a.js'},{filename:'src/a.js'}]:[]):original(route,...args);
  await assert.rejects(prepareIntegration(f.options()),/Incomplete PR file inventory/);
  await assert.rejects(f.complete(),/Incomplete PR file inventory/);assert.equal(f.writes.length,0);
 }
});

test('actual full preparation emits archive patterns from the authenticated candidate package roles',async()=>{
  const f=fixture();
  f.packageInputs.verification_paths=['research/geography/shared-seam-prt-esp-20261006/required.json'];
  const prepared=await prepareIntegration(f.options());
  assert.equal(prepared.profile,'full');assert.equal(prepared.candidate,f.candidate);
  assert.equal(prepared.candidate_tree,'integrated');
  assert.deepEqual(prepared.checkout_patterns,fullCheckoutPatterns(f.packageInputs));
  assert(prepared.checkout_patterns.includes('/research/geography/shared-seam-prt-esp-20261006/required.json'));
  assert(prepared.checkout_patterns.includes('!/coordination/engineering/reference-source-custody-20261007/'));
  assert.equal(f.calls.filter(row=>row.route.includes('/contents/.github/package-inputs.json')).length,1);
});

test('explicit auto refuses unsupported scope and cleans its candidate while complete deliberately selects every shard',async()=>{
  for(const make of [fixture,packetFixture]){
    const f=make();
    if(make===fixture){
      await assert.rejects(prepareIntegration({...f.options(),reviewedTests:'auto'}),/Automatic test scope is unavailable/);
      assert.equal(f.refs.size,0);assert.equal(f.writes.length,0);
      assert.equal(f.calls.filter(row=>row.method==='DELETE'&&row.route.includes('/git/refs/heads/worldatlas-integration/')).length,1);
    }
    const prepared=await prepareIntegration({...f.options(),reviewedTests:'complete'});
    assert.equal(prepared.profile,'full');assert.equal(prepared.test_selection,'complete');
    assert.deepEqual(prepared.shards,[0,1,2]);assert.equal(prepared.test_files,undefined);
    assert.deepEqual(prepared.checkout_patterns,fullCheckoutPatterns(f.packageInputs));
    assert.equal(prepared.geography_required,true);
    assert.equal(prepared.geography_software,false);
  }
  const legacy=fixture(),prepared=await prepareIntegration(legacy.options());
  assert.equal(prepared.profile,'full');assert.equal(prepared.test_selection,undefined,'Already-queued omitted input keeps its old route');
  const final=fixture();
  assert.equal((await final.complete({reviewedTests:'complete'})).accepted,true,'Explicit complete retains final admission');
});


const PACKET_TESTS = ['test/evidence-quality.test.mjs','test/premerge-evidence.test.mjs','test/engineering-owned-scope-routing.test.mjs'];
function packetFixture(format = 'json') {
  const f=fixture(),old=f.api,prefix='coordination/engineering/colombia-held-residual-830-20261019/';
  const names=['README.md','current-owner-observation-79c7802.json','full-package-crosswalk-current-owner-79c7802.json','partition-a.json','partition-b.json','per-key-unresolved-request.json'].map(n=>prefix+n.replace(/\.json$/, '.'+format));
  const blob=path=>({path,sha:sha('e'),mode:'100644',type:'blob',size:1});
  const parents=rows=>{
    const all=new Map(rows.map(row=>[row.path,row]));
    for(const row of rows)for(let at=row.path.indexOf('/');at>=0;at=row.path.indexOf('/',at+1)){
      const parent=row.path.slice(0,at);if(!all.has(parent))all.set(parent,{path:parent,sha:sha('d'),mode:'040000',type:'tree'});
    }
    return [...all.values()];
  };
  f.baseline=parents([...new Set([...EXECUTION_CODE,...PACKET_TESTS,'test/fixtures/contract/input.json'])].map(blob));
  f.integrated=parents([...structuredClone(f.baseline),...names.map(blob)]);f.authored=structuredClone(f.integrated);
  f.files=names.map(filename=>({filename,status:'added'}));f.pr.changed_files=f.files.length;f.packageInputs=loadPackageInputs();
  f.api=(route,...args)=>route.split('?')[0].endsWith('/pulls/2/files')?structuredClone(f.files):old(route,...args);
  f.packetNames=names;return f;
}

test('default actual preparation derives the inert packet consumers without an operator roster',async()=>{
  for(const format of ['json','jsonl','json.gz','jsonl.gz'])for(const reviewedTests of [undefined,null,'','auto']){
    const f=packetFixture(format),prepared=await prepareIntegration({...f.options(),reviewedTests});
    assert.equal(prepared.profile,'evidence');assert.equal(prepared.test_selection,'reviewed');
    assert.deepEqual(prepared.test_files,PACKET_TESTS);assert.deepEqual(prepared.shards,[0]);
    assert.deepEqual(prepared.checkout_patterns,focusedCheckoutPatterns(f.packageInputs,EXECUTION_CODE));
    assert.equal(prepared.geography_required,true);assert.equal(prepared.geography_software,false);
    assert.equal(prepared.base,f.base);assert.equal(prepared.pr.head.sha,f.head);assert.equal(prepared.candidate,f.candidate);
    assert.equal(f.calls.filter(row=>row.route.includes('/contents/.github/package-inputs.json')).length,1);
    await assert.rejects(f.complete({geographyResult:'skipped'}),/Trusted combined geography/);
  }
  const f=packetFixture();
  const reviewedTests=JSON.stringify({base:f.base,head:f.head,files:PACKET_TESTS});
  const explicit=await prepareIntegration({...f.options(),reviewedTests});
  assert.equal(explicit.profile,'evidence');assert.equal(explicit.test_selection,'reviewed');
  assert.deepEqual(explicit.test_files,PACKET_TESTS);
  // The existing dispatch input distinguishes this identical manual roster.
  await assert.rejects(prepareIntegration({...f.options(),reviewedTests:{base:sha('0'),head:f.head,files:PACKET_TESTS}}),/stale/);
});

test('actual automatic packet roster runs without installed dependencies or external executables',async()=>{
  const f=packetFixture('json.gz'),prepared=await prepareIntegration(f.options());
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-packet-runtime-'));
  try {
    const sources=staticModuleClosure(process.cwd(),['scripts/run-integration-tests.mjs',...prepared.test_files]);
    for(const name of [...sources,'.github/evidence-policy.json','scripts/native-ownership/validate-context-input-stage.mjs']){
      const target=path.join(directory,name);fs.mkdirSync(path.dirname(target),{recursive:true});fs.copyFileSync(name,target);
    }
    const empty=path.join(directory,'empty-path');fs.mkdirSync(empty);
    const env={...process.env,PATH:empty,NODE_PATH:'',NODE_OPTIONS:'',INTEGRATION_PROFILE:prepared.profile,INTEGRATION_SHARD:String(prepared.shards[0]),
      INTEGRATION_TEST_SELECTION:prepared.test_selection,INTEGRATION_TEST_FILES_BASE64:Buffer.from(JSON.stringify(prepared.test_files)).toString('base64')};
    delete env.NODE_TEST_CONTEXT; // Exercise the real nested Node test runner.
    const result=spawnSync(process.execPath,['scripts/run-integration-tests.mjs'],{cwd:directory,encoding:'utf8',timeout:20000,
      env});
    assert.equal(result.status,0,result.stdout+result.stderr);assert.match(result.stdout,/# skipped 0/);
    assert.match(result.stdout,/# fail 0/);assert.match(result.stdout,/"git_command_attempts":0/);
    assert.match(result.stdout,/"native_inputs":\{"applicable":true,"fetched":\[\]\}/);
    assert.equal(fs.existsSync(path.join(directory,'node_modules')),false);
  } finally {fs.rmSync(directory,{recursive:true,force:true});}
});

test('automatic packet boundary reuses inert names and refuses executable, redirected or declared roles',()=>{
 for(const format of ['json','jsonl','json.gz','jsonl.gz']){
  const f=packetFixture(format),entries=new Map(f.integrated.map(row=>[row.path,row]));
  assert(inertEvidenceAdditions(f.files,entries,f.packageInputs));
  for(const file of [f.files[0],f.files[1]]){
  for(const delta of [{status:'modified'},{status:'removed'},{status:'renamed',previous_filename:'src/old.js'},{previous_filename:'old.json'}])
    assert.equal(inertEvidenceAdditions([{...file,...delta}],entries,f.packageInputs),false);
  for(const delta of [{mode:'100755'},{mode:'120000'},{type:'commit',mode:'160000'},{sha:'not-an-oid'},{size:undefined}]){
    const changed=new Map(entries);changed.set(file.filename,{...changed.get(file.filename),...delta});
    assert.equal(inertEvidenceAdditions([file],changed,f.packageInputs),false);
  }
  const redirected=new Map(entries);redirected.set('coordination/engineering',{type:'blob',mode:'120000',sha:sha('f'),size:1});
  assert.equal(inertEvidenceAdditions(f.files,redirected,f.packageInputs),false);
  for(const category of ['inputs','verification_paths'])for(const role of [file.filename,'coordination/engineering/colombia-held-residual-830-20261019/'])
    assert.equal(inertEvidenceAdditions(f.files,entries,{...f.packageInputs,[category]:[...f.packageInputs[category],role]}),false);
  }
  for(const filename of ['package.json','package-lock.json','npm-shrinkwrap.json','import-map.json','requirements.txt','replay.mjs','replay.py',
    'replay.mjs.gz','replay.py.gz','payload.gz','report.json.gz.mjs','report.json.gz.gz']){
    for(const root of ['coordination/engineering/packet/','research/geography/packet/']){
      const name=root+filename,changed=new Map(entries);changed.set(name,{path:name,type:'blob',mode:'100644',sha:sha('f'),size:1});
      for(let at=name.indexOf('/');at>=0;at=name.indexOf('/',at+1))changed.set(name.slice(0,at),{type:'tree',mode:'040000',sha:sha('d')});
      assert.equal(inertEvidenceAdditions([{filename:name,status:'added'}],changed,f.packageInputs),false,name);
    }
  }
  assert.equal(inertEvidenceAdditions([],entries,f.packageInputs),false);
 }
});

test('default mixed changes retain broad routing and missing packet consumers cannot be silently omitted',async()=>{
 for(const format of ['json','json.gz']){
  for(const filename of ['scripts/merge-integration.mjs','test/evidence-quality.test.mjs','.github/package-inputs.json','src/effective-footprint.js','data/ownership-selection.json']){
    const f=packetFixture(format),row=f.integrated.find(row=>row.path===filename);
    if(row)row.sha=sha('f');else f.integrated.push({path:filename,sha:sha('f'),type:'blob',mode:'100644',size:1});
    const prepared=await prepareIntegration(f.options());assert.notEqual(prepared.test_selection,'reviewed',filename);
  }
  for(const filename of [...PACKET_TESTS,EXECUTION_CODE[0],'test/fixtures/contract/input.json']){
    const f=packetFixture(format);for(const key of ['baseline','authored','integrated'])f[key]=f[key].filter(row=>row.path!==filename);
    await assert.rejects(prepareIntegration(f.options()),/ordinary|unavailable|fixture boundary/,filename);
  }
 }
});

test('reviewed tests bind both trusted phases without changing actual geography obligations', async () => {
  const f=controlFixture({withContractBoundary:true}), files=['test/example.test.mjs'];
  const context={base:f.base,head:f.head,entries:new Map(f.integrated.map(row=>[row.path,row])),files:[],definition:f.packageInputs};
  const request=reviewedTestPlan({base:f.base,head:f.head,files},context).request;
  const serialized=JSON.stringify(request);
  assert.deepEqual(reviewedTestPlan(serialized,context).request,request);
  const prepared=await prepareIntegration({...f.options(),reviewedTests:serialized});
  assert.equal(prepared.profile,'evidence');assert.equal(prepared.test_selection,'reviewed');
  assert.deepEqual(prepared.test_files,files);assert.deepEqual(prepared.shards,[0]);
  assert.equal(prepared.geography_required,false);
  assert.deepEqual(prepared.checkout_patterns,focusedCheckoutPatterns(f.packageInputs,[...EXECUTION_CODE]));
  assert.equal((await f.complete({reviewedTests:serialized,geographyResult:'skipped'})).accepted,true);
  for(const changed of [{base:sha('0')},{head:sha('0')},{head:undefined}]) {
    const stale={...request,...changed};
    await assert.rejects(prepareIntegration({...f.options(),reviewedTests:stale}),/stale|binding/);
    await assert.rejects(f.complete({reviewedTests:stale,geographyResult:'skipped'}),/stale|binding/);
  }
  f.integrated.push({path:'scripts/unknown-checker.py',sha:sha('f'),type:'blob',mode:'100644'});
  const unknown=await prepareIntegration({...f.options(),reviewedTests:request});
  assert.equal(unknown.geography_required,true);assert.equal(unknown.geography_software,true);
  await assert.rejects(f.complete({reviewedTests:request,geographyResult:'skipped'}),/Trusted combined geography/);
});

test('reviewed tests derive the complete fixture and executing-policy boundary without manual operands', () => {
  const row=(mode='100644',type='blob')=>({sha:sha('e'),mode,type});
  const entries=new Map([...EXECUTION_CODE.map(name=>[name,row()]),['test',row('040000','tree')],
    ['test/example.test.mjs',row()],['test/fixtures/contract/input.json',row()]]);
  const plan={base:sha('a'),head:sha('b'),files:['test/example.test.mjs'],inputs:[]};
  const context={base:plan.base,head:plan.head,entries,files:[],definition:loadPackageInputs()};
  const result=reviewedTestPlan(plan,context);
  assert.deepEqual(result.files,plan.files);assert.deepEqual(result.inputs,[...EXECUTION_CODE]);assert.equal(result.build,false);
  assert.deepEqual(result.request,{base:plan.base,head:plan.head,files:plan.files});
  assert.deepEqual(reviewedTestPlan(JSON.stringify(result.request),context),result);
  assert.deepEqual(reviewedTestPlan({...plan,files:[...plan.files,...plan.files]},context).request,result.request,'Request uses the normalized reviewed roster');
  assert.throws(()=>reviewedTestPlan(JSON.stringify(result.files),context),/stale|binding/,'A bare suite list is not a bound dispatch argument');
  for(const changed of [{base:sha('c')},{head:sha('c')}])
    assert.throws(()=>reviewedTestPlan(JSON.stringify(result.request),{...context,...changed}),/stale|binding/);
  assert.deepEqual(reviewedTestPlan({...plan,inputs:undefined},context),result);
  assert.deepEqual(reviewedTestPlan({...plan,inputs:result.inputs},context),result,'Derived compatibility envelope works unchanged');
  for(const files of [[],['test/missing.test.mjs'],['../escape.test.mjs'],['test/../escape.test.mjs'],[null]])
    assert.throws(()=>reviewedTestPlan({...plan,files},context),/roster|ordinary/);
  for(const inputs of [['../escape'],['/etc/passwd'],['data/fixture.json'],[null]])
    assert.throws(()=>reviewedTestPlan({...plan,inputs},context),/manual inputs/);
  for(const [name,mode,type] of [['test/example.test.mjs','120000','blob'],['test','120000','blob'],
    ['test/fixtures/contract/input.json','120000','blob'],['test/fixtures/contract','120000','blob'],
    [EXECUTION_CODE[0],'160000','commit']]) {
    const changed=new Map(entries);changed.set(name,row(mode,type));
    assert.throws(()=>reviewedTestPlan(plan,{...context,entries:changed}),/ordinary|unavailable/);
  }
  const omitted=new Map(entries);omitted.delete(EXECUTION_CODE[0]);
  assert.throws(()=>reviewedTestPlan(plan,{...context,entries:omitted}),/unavailable/);
  const noFixtures=new Map(entries);noFixtures.delete('test/fixtures/contract/input.json');
  assert.throws(()=>reviewedTestPlan(plan,{...context,entries:noFixtures}),/fixture boundary/);
  for(const absent of [undefined,null,'']) assert.equal(reviewedTestPlan(absent,context),null);
});


for (const [label, consumer, operand] of [
  ...['test/final-bank-finalizer.test.mjs','test/selected-delivery-smoke.test.mjs','test/final-bank-checkpoint.test.mjs','test/selected-owner-observation.test.mjs',
    'test/accepted-checkpoint-qualification.test.mjs'].map(consumer =>
    [consumer,consumer,'coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz']),
  ['rebind custody', 'test/current-rebind-product-custody.test.mjs', 'coordination/engineering/additive-native-composition-20261009/execution-code-paths.json'],
  ['workspace bootstrap', 'test/local-workspace.test.mjs', 'docs/LOCAL_WORKSPACES.md'],
  ['quota observation guide', 'test/github-quota.test.mjs', 'docs/MERGE_QUEUE_CLIENT.md'],
  ['regional research gate', 'test/regional-research-gate.test.mjs', 'data/research-geography-gate.json'],
  ...['test/publication-plan.test.mjs','test/package-current-additive.test.mjs'].map(consumer =>
    [consumer,consumer,'coordination/publication/cloudflare-history.json'])
]) test(`reviewed ${label} retains current declared policy and refuses missing or redirected operands`, () => {
  const row=(mode='100644',type='blob')=>({sha:sha('e'),mode,type});
  const entries=new Map([...EXECUTION_CODE.map(name=>[name,row()]),[operand,row()],
    [consumer,row()],['test/example.test.mjs',row()],['test/fixtures/contract/input.json',row()]]);
  const request={base:sha('a'),head:sha('b'),files:[consumer]};
  const context={base:request.base,head:request.head,entries,files:[],definition:loadPackageInputs()};
  const plan=reviewedTestPlan(request,context);
  assert.deepEqual(plan.inputs,[...EXECUTION_CODE,operand]);
  assert(plan.checkout_patterns.includes('/'+operand));assert.equal(plan.build,false);
  assert(!reviewedTestPlan({...request,files:['test/example.test.mjs']},context).inputs.includes(operand));
  const absent=new Map(entries);absent.delete(operand);
  assert.throws(()=>reviewedTestPlan(request,{...context,entries:absent}),/unavailable/);
  for(const name of [operand,operand.slice(0,operand.lastIndexOf('/'))]) {
    const redirected=new Map(entries);redirected.set(name,row('120000'));
    assert.throws(()=>reviewedTestPlan(request,{...context,entries:redirected}),/unavailable/);
  }
  const definition={...context.definition,verification_paths:context.definition.verification_paths.filter(name=>name!==operand)};
  assert.throws(()=>reviewedTestPlan(request,{...context,definition}),/verification declaration/);
  assert.throws(()=>reviewedTestPlan({...request,inputs:[...plan.inputs,'data/arbitrary.json']},context),/manual inputs/);
  const changed=new Map(entries);changed.set(operand,{...row(),sha:sha('f')});
  assert.deepEqual(reviewedTestPlan(request,{...context,entries:changed}),plan,'Select the current body, not a historical fixture copy');
});

test('reviewed quota consumer reads its current guide through actual sparse checkout', () => {
  const consumer='test/github-quota.test.mjs',operand='docs/MERGE_QUEUE_CLIENT.md';
  const row={sha:sha('e'),mode:'100644',type:'blob'};
  const entries=new Map([...EXECUTION_CODE,operand,consumer,'test/fixtures/contract/input.json'].map(name=>[name,row]));
  const request={base:sha('a'),head:sha('b'),files:[consumer]};
  const plan=reviewedTestPlan(request,{...request,entries,files:[],definition:loadPackageInputs()});
  assert.equal(plan.build,false);
  const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'reviewed-quota-guide-'));
  try {
    const git=(args,options={})=>execFileSync('git',args,{cwd:temporary,encoding:'utf8',...options});
    git(['init','-q']);
    for(const name of [...staticModuleClosure(process.cwd(),[consumer]),operand,'package.json']) {
      fs.mkdirSync(path.dirname(path.join(temporary,name)),{recursive:true});
      fs.copyFileSync(name,path.join(temporary,name));
    }
    const excluded='docs/unrelated-guide.md';fs.writeFileSync(path.join(temporary,excluded),'not a reviewed operand');
    git(['add','.']);git(['-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','current quota guide inputs']);
    git(['sparse-checkout','set','--no-cone','--stdin'],{input:plan.checkout_patterns.join('\n')+'\n'});
    assert.deepEqual(fs.readFileSync(path.join(temporary,operand)),fs.readFileSync(operand));
    assert.equal(fs.existsSync(path.join(temporary,excluded)),false);
    const args=['--test','--test-reporter=tap','--test-name-pattern=canonical native observation',consumer];
    const env={...process.env};delete env.NODE_TEST_CONTEXT;
    const result=spawnSync(process.execPath,args,{cwd:temporary,encoding:'utf8',env});
    assert.equal(result.status,0,result.stdout+result.stderr);
    assert.match(result.stdout,/canonical native observation examples/);
    fs.unlinkSync(path.join(temporary,operand));
    const absent=spawnSync(process.execPath,args,{cwd:temporary,encoding:'utf8',env});
    assert.notEqual(absent.status,0,'The actual consumer must reject a missing current guide');
    assert.match(absent.stdout+absent.stderr,/ENOENT/);
  } finally { fs.rmSync(temporary,{recursive:true,force:true}); }
});

for (const consumer of ['test/final-bank-finalizer.test.mjs','test/selected-delivery-smoke.test.mjs','test/final-bank-checkpoint.test.mjs','test/selected-owner-observation.test.mjs',
    'test/accepted-checkpoint-qualification.test.mjs'])
test(`reviewed ${consumer} materializes its normative latitude operand through actual sparse checkout`, () => {
  const operand='coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz';
  const row={sha:sha('e'),mode:'100644',type:'blob'};
  const entries=new Map([...EXECUTION_CODE,operand,consumer,'test/fixtures/contract/input.json'].map(name=>[name,row]));
  const request={base:sha('a'),head:sha('b'),files:[consumer]};
  const plan=reviewedTestPlan(request,{...request,entries,files:[],definition:loadPackageInputs()});
  assert.equal(plan.build,false);
  const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'reviewed-final-bank-inputs-'));
  try {
    const git=(args,options={})=>execFileSync('git',args,{cwd:temporary,encoding:'utf8',...options});
    git(['init','-q']);
    fs.mkdirSync(path.dirname(path.join(temporary,operand)),{recursive:true});
    // This control tests opaque current-body materialization, not scientific decoding.
    const body=Buffer.from('Synthetic current latitude operand\n');
    fs.writeFileSync(path.join(temporary,operand),body);
    const excluded='data/unrelated-retained-input.json';
    fs.mkdirSync(path.join(temporary,'data'));fs.writeFileSync(path.join(temporary,excluded),'not a reviewed operand');
    git(['add','.']);git(['-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','current final-bank fixture inputs']);
    const head=git(['rev-parse','HEAD']),tree=git(['rev-parse','HEAD^{tree}']);
    git(['sparse-checkout','set','--no-cone','--stdin'],{input:plan.checkout_patterns.join('\n')+'\n'});
    assert.deepEqual(fs.readFileSync(path.join(temporary,operand)),body);
    assert.equal(fs.existsSync(path.join(temporary,excluded)),false);
    assert.equal(git(['rev-parse','HEAD']),head);assert.equal(git(['rev-parse','HEAD^{tree}']),tree);
    assert.equal(git(['status','--porcelain']), '');
  } finally { fs.rmSync(temporary,{recursive:true,force:true}); }
});

test('reviewed hosted consumers retain their current inputs through actual sparse materialization', () => {
  const operands=['coordination/publication/cloudflare-history.json','data/observation-registry-history/base-v1.json',
    'data/research-geography-gate.json','data/hosted-type-catalog.json','data/settlement-estimates.json',
    'coordination/engineering/cloudflare-publication-846-20261007/registry-source.json','docs/MERGE_QUEUE_CLIENT.md'];
  const consumers=['test/neon-forward-migrations.test.mjs','test/compact-membership-profile.test.mjs','test/current-postgres-recovery.test.mjs',
    'test/merge-integration.test.mjs','test/settlement-population-import.test.mjs','test/publication-cloudflare.test.mjs','test/cloudflare-access.test.mjs'];
  const row={sha:sha('e'),mode:'100644',type:'blob'};
  const entries=new Map([...EXECUTION_CODE,...operands,...consumers,'test/example.test.mjs','test/fixtures/contract/input.json'].map(name=>[name,row]));
  const request={base:sha('a'),head:sha('b'),files:consumers};
  const context={base:request.base,head:request.head,entries,files:[],definition:loadPackageInputs()};
  const plan=reviewedTestPlan(request,context);
  assert.equal(plan.build,false);assert.deepEqual(plan.files,consumers);
  assert.deepEqual(plan.inputs,[...EXECUTION_CODE,operands[6],operands[0],operands[5],...operands.slice(1,5)]);
  assert(plan.checkout_patterns.includes('postgres'),'PostgreSQL DDL is executing source, like drizzle');
  for(const consumer of consumers) {
    const expected=consumer===consumers[6]?operands.slice(1,3):consumer===consumers[5]?[operands[0],operands[5]]:consumer===consumers[3]?[operands[6],operands[5],...operands.slice(0,5)]:consumer===consumers[2]?[operands[0]]:consumer===consumers[1]?operands.slice(0,4):
      consumer===consumers[4]?operands.slice(1,5):operands.slice(0,5);
    const single=reviewedTestPlan({...request,files:[consumer]},context);
    assert.deepEqual(single.inputs,[...EXECUTION_CODE,...expected]);
    for(const operand of expected)assert(single.checkout_patterns.includes('/'+operand));
    for(const operand of expected) {
      const absent=new Map(entries);absent.delete(operand);
      assert.throws(()=>reviewedTestPlan({...request,files:[consumer]},{...context,entries:absent}),/unavailable/);
      for(const name of [operand,path.posix.dirname(operand)]) {
        const redirected=new Map(entries);redirected.set(name,{...row,mode:'120000'});
        assert.throws(()=>reviewedTestPlan({...request,files:[consumer]},{...context,entries:redirected}),/unavailable/);
      }
      const definition={...context.definition,verification_paths:context.definition.verification_paths.filter(name=>name!==operand)};
      assert.throws(()=>reviewedTestPlan({...request,files:[consumer]},{...context,definition}),/verification declaration/);
    }
  }
  assert.deepEqual(reviewedTestPlan({...request,files:['test/example.test.mjs']},context).inputs,[...EXECUTION_CODE]);
  assert.throws(()=>reviewedTestPlan({...request,inputs:[...plan.inputs,'data/arbitrary.json']},context),/manual inputs/);
  const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'reviewed-postgres-inputs-'));
  try {
    const git=(args,options={})=>execFileSync('git',args,{cwd:temporary,encoding:'utf8',...options});
    git(['init','-q']);
    for(const name of [...operands,'postgres/schema.sql','scripts/publication-cloudflare.mjs',
      'src/observation-modules.js','src/observation-registry.js','src/json-contract.js']) {
      fs.mkdirSync(path.dirname(path.join(temporary,name)),{recursive:true});
      fs.copyFileSync(name,path.join(temporary,name));
    }
    fs.writeFileSync(path.join(temporary,'package.json'),JSON.stringify({type:'module'}));
    const excluded='data/unrelated-retained-input.json';fs.writeFileSync(path.join(temporary,excluded),'not a reviewed operand');
    git(['add','.']);git(['-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','current PostgreSQL inputs']);
    git(['sparse-checkout','set','--no-cone','--stdin'],{input:plan.checkout_patterns.join('\n')+'\n'});
    for(const name of [...operands,'postgres/schema.sql'])assert.deepEqual(fs.readFileSync(path.join(temporary,name)),fs.readFileSync(name));
    assert.equal(fs.existsSync(path.join(temporary,excluded)),false);
    const result=spawnSync(process.execPath,['--input-type=module','-e',
      "await import('./src/observation-modules.js'); await import('./scripts/publication-cloudflare.mjs'); "+
      "const assert=(await import('node:assert/strict')).default,fs=await import('node:fs'),source=JSON.parse(fs.readFileSync('data/settlement-estimates.json')); "+
      "assert.equal(source.entities.length,582); assert.equal(source.entity_history.length,9301); assert.ok(JSON.parse(fs.readFileSync('coordination/engineering/cloudflare-publication-846-20261007/registry-source.json')).deployments.length); console.log('actual-sparse-postgres-inputs');"],
      {cwd:temporary,encoding:'utf8'});
    assert.equal(result.status,0,result.stderr);assert.equal(result.stdout.trim(),'actual-sparse-postgres-inputs');
  } finally { fs.rmSync(temporary,{recursive:true,force:true}); }
});

test('reviewed regional gate materializes only its live policy for the actual sparse consumer', () => {
  const consumer='test/regional-research-gate.test.mjs',operand='data/research-geography-gate.json';
  const row={sha:sha('e'),mode:'100644',type:'blob'};
  const entries=new Map([...EXECUTION_CODE.map(name=>[name,row]),[operand,row],
    [consumer,row],['test/fixtures/contract/input.json',row]]);
  const request={base:sha('a'),head:sha('b'),files:[consumer]};
  const context={base:request.base,head:request.head,entries,files:[],definition:loadPackageInputs()};
  const plan=reviewedTestPlan(request,context);
  assert.equal(plan.build,false);assert.deepEqual(plan.files,[consumer]);
  const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'reviewed-live-policy-'));
  try {
    const git=(args,options={})=>execFileSync('git',args,{cwd:temporary,encoding:'utf8',...options});
    git(['init','-q']);
    for(const name of ['scripts/research-import-gate.mjs','src/regional-import-gate.js']) {
      fs.mkdirSync(path.dirname(path.join(temporary,name)),{recursive:true});
      fs.copyFileSync(name,path.join(temporary,name));
    }
    fs.writeFileSync(path.join(temporary,'package.json'),JSON.stringify({type:'module'}));
    fs.mkdirSync(path.join(temporary,'data'));
    const body=JSON.stringify({version:2,ready_for_location_attributes:false,marker:'current-fixture-policy'})+'\n';
    fs.writeFileSync(path.join(temporary,operand),body);
    const excluded='data/unrelated-retained-input.json';
    fs.writeFileSync(path.join(temporary,excluded),'not a required policy operand');
    git(['add','.']);git(['-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','live policy fixture']);
    git(['sparse-checkout','set','--no-cone','--stdin'],{input:plan.checkout_patterns.join('\n')+'\n'});
    assert.equal(fs.readFileSync(path.join(temporary,operand),'utf8'),body);
    assert.equal(fs.existsSync(path.join(temporary,excluded)),false);
    const result=spawnSync(process.execPath,['--input-type=module','-e',
      "import assert from 'node:assert/strict'; import {readResearchImportGate,assertResearchImportsReady} from './scripts/research-import-gate.mjs'; const gate=readResearchImportGate(); assert.equal(gate.version,2); assert.equal(gate.marker,'current-fixture-policy'); assert.throws(()=>assertResearchImportsReady(gate,{regionIds:['region:a']}),/paused/); console.log('actual-sparse-policy-read');"],
      {cwd:temporary,encoding:'utf8'});
    assert.equal(result.status,0,result.stderr);assert.equal(result.stdout.trim(),'actual-sparse-policy-read');
  } finally { fs.rmSync(temporary,{recursive:true,force:true}); }
});

test('reviewed lists cannot omit actual packaged consumers when package source changes or moves', async () => {
  for(const changed of [{filename:'src/a.js'}, {filename:'archive/a.js',previous_filename:'src/a.js'}]) {
    const f=controlFixture({withContractBoundary:true});f.packageInputs.inputs.push('src/');
    const required=['test/compact-ownership.test.mjs','test/prepared-parity.test.mjs'];
    const entries=new Map([...f.integrated,...required.map(path=>({path,sha:sha('e'),type:'blob',mode:'100644'}))].map(row=>[row.path,row]));
    const request={base:f.base,head:f.head,files:['test/example.test.mjs'],inputs:[]};
    const context={base:f.base,head:f.head,entries,files:[changed],definition:f.packageInputs};
    const plan=reviewedTestPlan(request,context);
    assert.equal(plan.build,true);assert.deepEqual(plan.files,[...request.files,...required]);
    assert.deepEqual(plan.request,{base:f.base,head:f.head,files:[...request.files,...required]});
    assert.deepEqual(reviewedTestPlan(JSON.stringify(plan.request),context),plan,'The dispatch argument retains automatically required consumers');
    assert.deepEqual(plan.checkout_patterns,fullCheckoutPatterns(f.packageInputs));
    entries.delete(required[0]);assert.throws(()=>reviewedTestPlan(request,context),/packaged consumer/);
  }
  assert(REBIND_CODE.includes('scripts/worker-identity.mjs'),'Author support custody remains mandatory');
  // Use the actual declaration, not a synthetic allowlist. Author and scientific
  // comparison controls are not builder inputs; runtime and package policy are.
  for (const [source,consumer] of [
    ['scripts/local-workspace.mjs','test/local-workspace.test.mjs'],
    ['scripts/worker-identity.mjs','test/local-workspace.test.mjs'],
    ['scripts/check-effective-geographic-regression.mjs','test/effective-geographic-regression.test.mjs']
  ]) {
    const required=['test/compact-ownership.test.mjs','test/prepared-parity.test.mjs'];
    const row={sha:sha('e'),type:'blob',mode:'100644'};
    const entries=new Map([...EXECUTION_CODE.map(name=>[name,row]),...required.map(name=>[name,row]),
      [consumer,row],['docs/LOCAL_WORKSPACES.md',row],['test/fixtures/contract/input.json',row]]);
    const request={base:sha('a'),head:sha('b'),files:[consumer]};
    const changed={filename:source,status:'modified'};
    const context={base:request.base,head:request.head,entries,files:[changed],definition:loadPackageInputs()};
    const comparison=reviewedTestPlan(request,context);
    assert.deepEqual(comparison.files,[consumer]);assert.equal(comparison.build,false);
    assert(comparison.inputs.includes('scripts/check-effective-geographic-regression.mjs'),'Scientific checker custody remains mandatory');
    assert.equal(geographyRequired('engineering/tooling',[changed]),true);
    assert.equal(candidateGeographyCode('evidence',[changed],'reviewed'),true);
    for(const filename of ['src/effective-footprint.js','.github/package-inputs.json']) {
      const actual=reviewedTestPlan(request,{...context,files:[{filename,status:'modified'}]});
      assert.deepEqual(actual.files,[consumer,...required]);assert.equal(actual.build,true);
    }
  }

});

test('minimal reviewed package consumer derives real inputs without a changed package file',()=>{
 const f=controlFixture({withContractBoundary:true});
 const required='test/prepared-parity.test.mjs';
 const entries=new Map([...f.integrated,{path:required,sha:sha('e'),type:'blob',mode:'100644'}].map(row=>[row.path,row]));
 const context={base:f.base,head:f.head,entries,files:[],definition:f.packageInputs};
 const packagePlan=reviewedTestPlan({base:f.base,head:f.head,files:[required]},context);
 assert.equal(packagePlan.build,true);assert.deepEqual(packagePlan.files,[required]);
 assert.deepEqual(packagePlan.checkout_patterns,fullCheckoutPatterns(f.packageInputs));
 const unitPlan=reviewedTestPlan({base:f.base,head:f.head,files:['test/example.test.mjs']},context);
 assert.equal(unitPlan.build,false);assert.deepEqual(unitPlan.inputs,[...EXECUTION_CODE]);
});

test('reviewed full builds materialize real historical fixture paths without widening tests or accepting manual inputs',async()=>{
  const f=controlFixture({withContractBoundary:true}), kernel='src/effective-footprint.js';
  f.packageInputs.inputs.push('src/','data/package-input.json');
  const latitude='coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz';
  f.packageInputs.verification_paths.push(latitude);
  const files=['test/additive-release.test.mjs','test/selected-delivery-smoke.test.mjs',
    'test/effective-footprint.test.mjs','test/source-target-native-delivery.test.mjs'];
  const expected=[...files,'test/compact-ownership.test.mjs','test/prepared-parity.test.mjs'];
  for(const rows of [f.baseline,f.authored,f.integrated]) {
    for(const name of [...expected,latitude])rows.push({path:name,sha:sha('c'),mode:'100644',type:'blob'});
    const existing=rows.find(row=>row.path===kernel);
    if(existing)existing.sha=rows===f.baseline?sha('d'):sha('e');
    else rows.push({path:kernel,sha:rows===f.baseline?sha('d'):sha('e'),mode:'100644',type:'blob'});
  }
  const request={base:f.base,head:f.head,files};
  const prepared=await prepareIntegration({...f.options(),reviewedTests:request});
  assert.equal(prepared.profile,'full');assert.equal(prepared.test_selection,'reviewed');
  assert.deepEqual(prepared.test_files,expected);assert.deepEqual(prepared.shards,[0]);
  assert.equal(prepared.geography_required,true);assert.equal(prepared.geography_software,true);
  await assert.rejects(f.complete({reviewedTests:request,geographyResult:'skipped'}),/Trusted combined geography/);
  for(const inputs of [['data/arbitrary.json'],[...EXECUTION_CODE,'data/package-input.json']])
    await assert.rejects(prepareIntegration({...f.options(),reviewedTests:{...request,inputs}}),/manual inputs/);
  // These unchanged additive-release consumers concatenate archive prefixes with
  // filenames. Their historical operands are not current package inputs.
  const add031='coordination/engineering/additive-native-gap-repair-20261008/add031-release-proposal-v2/';
  const batch='coordination/engineering/additive-native-gap-batch-20261008/';
  const historical=[...['publication.json','patch-add031.json','feature.json','owner-window.json','owners-add031.json.gz'].map(name=>add031+name),
    ...['publication.json','patch-batch.json','features.json','ledger-batch.json','owners-batch.json.gz'].map(name=>batch+'batch-proposal-v1-run1/'+name),
    batch+'current-v8/complete-owner-rows.json'];
  const required=[...historical,kernel,'data/package-input.json'];
  const excluded=['data/regional-review/unrelated/input.json','research/campaigns/unrelated/source.json',
    'coordination/engineering/reference-source-custody-20261007/unrelated.json'];
  const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'reviewed-full-fixtures-'));
  try {
    const git=(args,options={})=>execFileSync('git',args,{cwd:temporary,encoding:'utf8',...options});
    git(['init','-q']);
    for(const name of [...required,...excluded]) {
      const file=path.join(temporary,name);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,'fixture '+name+'\n');
    }
    git(['add','.']);git(['-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixture']);
    git(['sparse-checkout','set','--no-cone','--stdin'],{input:prepared.checkout_patterns.join('\n')+'\n'});
    for(const name of required)assert.equal(fs.readFileSync(path.join(temporary,name),'utf8'),'fixture '+name+'\n');
    for(const name of excluded)assert.equal(fs.existsSync(path.join(temporary,name)),false,name);
  }finally{fs.rmSync(temporary,{recursive:true,force:true});}
  assert.deepEqual(prepared.checkout_patterns,fullCheckoutPatterns(f.packageInputs));
});

test('full preparation rejects unavailable or malformed package roles and cleans its candidate',async()=>{
  for(const kind of ['missing','malformed','wrong-bytes']){
    const f=fixture(),api=f.api;
    f.api=async(route,...args)=>{
      if(!route.includes('/contents/.github/package-inputs.json'))return api(route,...args);
      if(kind==='missing')throw Error('Package inputs unavailable');
      if(kind==='malformed')f.packageInputs.inputs.push('../escape');
      const result=await api(route,...args);
      return kind==='wrong-bytes'?{...result,sha:'0'.repeat(40)}:result;
    };
    await assert.rejects(prepareIntegration(f.options()),/Package inputs unavailable|Invalid package|bytes changed/);
    assert.equal(f.refs.size,0);assert.equal(f.writes.length,0);
  }
});

test('two reviewed PRs sharing a base integrate serially without changing authored head', async () => {
  const a=fixture();await prepareIntegration(a.options());await a.complete();
  const b=fixture();b.base=sha('d');b.pr.base.sha=b.base;
  b.integrated.push({path:'src/other.js',sha:'merged-first-pr',mode:'100644',type:'blob'});
  const prepared=await prepareIntegration(b.options());
  assert.equal(prepared.pr.head.sha,b.head);
  await b.complete({testedBase:b.base});assert.equal(b.writes[0].sha,b.head);
  assert.equal(b.writes[0].merge_method,'squash');assert.equal(b.writes[0].commit_title,b.pr.title);
});
test('Git conflicts refuse while cleanly composed blobs retain candidate verification', async () => {
  const a=fixture();a.pr.mergeable=false;await assert.rejects(prepareIntegration(a.options()),/conflict/);assert.equal(a.writes.length,0);
  const b=fixture();b.integrated[0].sha='different-reviewed-file';
  const prepared=await prepareIntegration(b.options());
  assert.equal(prepared.candidate,b.candidate);assert.equal(b.writes.length,0);
  assert.equal((await b.complete()).accepted,true);assert.equal(b.writes.length,1);
});
test('real clean disjoint same-file Git composition proceeds and actual conflicts refuse', async t => {
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-clean-composition-'));
  t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
  const git=(...args)=>execFileSync('git',args,{cwd:directory,encoding:'utf8',stdio:['ignore','pipe','pipe']}).trim();
  git('init','-b','main');git('config','user.name','WorldAtlas fixture');git('config','user.email','fixture@example.invalid');
  fs.mkdirSync(path.join(directory,'src'));
  const body=(first,second)=>`export const first = ${first};\n${'// unchanged separation\n'.repeat(8)}export const second = ${second};\n`;
  const write=(first,second)=>fs.writeFileSync(path.join(directory,'src/a.js'),body(first,second));
  const commit=message=>{git('add','src/a.js');git('commit','-m',message);return git('rev-parse','HEAD');};
  write(0,0);const ancestor=commit('initial');
  git('checkout','-b','author');write(1,0);const head=commit('reviewed first change');
  git('checkout','main');write(0,2);const base=commit('independently merged second change');
  git('merge','--no-ff','--no-edit','author');const candidate=git('rev-parse','HEAD');
  assert.equal(git('show',candidate+':src/a.js'),body(1,2).trim());
  assert.equal(git('show','-s','--format=%P',candidate),base+' '+head);
  const row=revision=>({path:'src/a.js',type:'blob',mode:'100644',sha:git('rev-parse',revision+':src/a.js')});
  const f=fixture({head,base,candidate});f.baseline=[row(base)];f.authored=[row(head)];f.integrated=[row(candidate)];
  assert.notEqual(f.authored[0].sha,f.integrated[0].sha,'Composition deliberately changes the whole authored blob');
  const prepared=await prepareIntegration(f.options());assert.equal(prepared.candidate,candidate);
  const verified=execFileSync(process.execPath,['--input-type=module','-e',
    `import {first,second} from ${JSON.stringify('file://'+path.join(directory,'src/a.js'))}; if(first!==1||second!==2)process.exit(1);`],{encoding:'utf8'});
  assert.equal(verified,'');assert.equal((await f.complete()).accepted,true);
  assert.equal(f.writes[0].sha,head,'The final API merge remains SHA-bound to reviewed head');
  const wrong=fixture({head,base,candidate});
  await assert.rejects(wrong.complete({geographyReportLoader:async()=>({version:1,method_id:'worldatlas-trusted-geography-check-v1',
    baseline_commit:base,trusted_code_commit:base,candidate_commit:ancestor,candidate_code_executed:false,
    published:false,source_approval:false,gate_status:'passed',status:'not-applicable'})}),/exact trusted combined check/);
  assert.equal(wrong.writes.length,0);
  git('checkout','-b','conflicting-author',ancestor);write(3,0);commit('competing first change');
  git('checkout','-b','conflicting-main',ancestor);write(4,0);commit('different first change');
  const conflict=spawnSync('git',['merge','--no-ff','--no-edit','conflicting-author'],{cwd:directory,encoding:'utf8'});
  assert.equal(conflict.status,1);assert.match(conflict.stdout,/CONFLICT/);
  const blocked=fixture();blocked.pr.mergeable=false;
  await assert.rejects(prepareIntegration(blocked.options()),/conflict/);assert.equal(blocked.writes.length,0);
});
test('stale merge object and truncated inventories fail closed', async () => {
  const a=fixture();a.parentBase=sha('e');await assert.rejects(prepareIntegration(a.options()),/exact current main/);
  const b=fixture();b.truncated=true;await assert.rejects(prepareIntegration(b.options()),/Incomplete integration tree/);
});
test('changed reviewed head prohibits integration', async () => {
  const f=fixture();f.pr.head.sha=sha('e');await assert.rejects(f.complete(),/head changed/);
  assert.equal(f.writes.length,0);
});
test('ordinary metadata is not a queue gate or another remote evidence traversal', async () => {
  for (const [body,branch] of [['','fix/Map.Errors_2026'],['Refs #1. Context.\nCloses #2\nCloses #3','feature/fixes'],['Unlinked reviewed change','plain-branch']]) {
    const f=fixture();f.pr.body=body;f.pr.head.ref=branch;f.issue.state='closed';f.issue.labels=[];f.issue.body='no machine contract';
    const prepared=await prepareIntegration(f.options());assert.equal(prepared.candidate,f.candidate);
    assert.equal((await f.complete()).accepted,true);assert.equal(f.writes[0].sha,f.head);
    assert.equal(f.calls.filter(row=>/\/issues\/|\/git\/blobs\//.test(row.route)).length,0);
  }
});
test('editing prose during real report validation does not invalidate the reviewed code', async()=>{
  const f=fixture(),loader=f.complete;
  const result=await f.complete({geographyReportLoader:async()=>{
    f.pr.title='Clearer title';f.pr.body='Closes #1, closes #2. Both completed.';
    return {version:1,method_id:'worldatlas-trusted-geography-check-v1',baseline_commit:f.base,trusted_code_commit:f.base,
      candidate_commit:f.candidate,candidate_code_executed:false,published:false,source_approval:false,gate_status:'passed',status:'not-applicable'};
  }});
  assert.equal(result.accepted,true);assert.equal(f.writes[0].commit_title,f.pr.title);assert.equal(f.writes[0].commit_message,f.pr.body);
});
test('failed or skipped candidate tests never merge an open PR', async () => {
  for(const integrationResult of ['failure','cancelled','skipped']) {
    const f=fixture();await assert.rejects(f.complete({integrationResult}),/tests|successful isolated/);assert.equal(f.writes.length,0);
  }
});
test('base advances before or during final validation are retryable without branch updates', async () => {
  const a=fixture();a.base=sha('d');await assert.rejects(a.complete(),/resubmit unchanged head/);
  const b=fixture();b.advanceOnRead=2;await assert.rejects(b.complete(),/resubmit unchanged head/);
  assert.equal(a.writes.length+b.writes.length,0);
});
test('the final queue validates its real candidate without redundant author checks', async () => {
  const f=fixture();f.checks=[];
  const prepared=await prepareIntegration(f.options());
  assert.equal(prepared.candidate,f.candidate);
  const result=await f.complete();
  assert.equal(result.accepted,true);assert.equal(f.writes.length,1);
  assert.equal(f.calls.filter(row=>/\/issues\/|\/git\/blobs\//.test(row.route)).length,0);
});
test('missing author checks cannot hide failed current checks', async () => {
  const f=fixture();f.checks=[{id:1,name:'external-validation',app:{id:2},status:'in_progress',conclusion:null}];
  await assert.rejects(prepareIntegration(f.options()),/pending or failed/);
  await assert.rejects(f.complete(),/pending or failed/);assert.equal(f.writes.length,0);
});
test('latest failed or pending check replaces old success', () => {
  const good={id:1,name:'scope',app:{id:1},status:'completed',conclusion:'success'};
  assert.throws(()=>checkCurrentChecks([good,{...good,id:2,conclusion:'failure'}]),/pending or failed/);
  assert.throws(()=>checkCurrentChecks([good,{...good,id:2,status:'in_progress',conclusion:null}]),/pending or failed/);
});
test('workflow separates untrusted candidate tests from write credentials and serializes the lifecycle', () => {
  const yaml=fs.readFileSync(new URL('../.github/workflows/worker-merge.yml',import.meta.url),'utf8');
  const integration=yaml.split('  integration:\n')[1].split('  merge:\n')[0];
  assert.match(yaml.split('jobs:')[0],/concurrency:\n  group: worldatlas-main-integrate/);
  assert.doesNotMatch(integration,/concurrency:/);
  assert.match(integration,/permissions:\n      contents: read/);
  assert.doesNotMatch(integration,/GITHUB_TOKEN:|secrets\.|contents: write|issues: write|pull-requests: write/);
  const authenticatedSteps=['Materialize exact prepared checkout inputs','Authenticate selected package installer inputs','Assemble unchanged base with current selected output'];
  const tokenSteps=integration.split(/(?=^      - )/m).filter(step=>/^\s+GH_TOKEN:/m.test(step));
  assert.equal(tokenSteps.length,authenticatedSteps.length);
  for(const [index,step] of tokenSteps.entries()){
    assert.ok(step.startsWith('      - name: '+authenticatedSteps[index]+'\n'));
    assert.equal((step.match(/^\s+GH_TOKEN:/gm)||[]).length,1);
    assert.match(step,/GH_TOKEN: \$\{\{ github\.token \}\}/);
    assert.match(step,/python3 -I -S -B/);
    if(index===0){
      assert.match(step,/CI_CHECKOUT_SHA: \$\{\{ needs\.prepare\.outputs\.candidate \}\}/);
      assert.match(step,/os\.environ\.pop\('GH_TOKEN'\)/);
      assert.match(step,/'sparse-checkout', 'set', '--no-cone', '--stdin'/);
      assert.doesNotMatch(step,/importlib|node |npm |git.*config.*--local.*extraheader/);
    }else{
      assert.match(step,/SELECTED_PACKAGE_TRUSTED_BASE: \$\{\{ needs\.prepare\.outputs\.base \}\}/);
      assert.match(step,/needs\.prepare\.outputs\.test_selection == 'selected-data'/);
    }
  }
  const steps=integration.split(/\n(?=      - )/).slice(1);
  assert.doesNotMatch(integration,/Read back qualified native build outputs|native-normal-built-output\.json|--built-output-readback/);
  const selectedSmoke=steps.find(step=>step.includes('name: Retain selected delivery smoke\n'));
  assert.match(selectedSmoke,/name: selected-delivery-smoke-/);
  assert.match(selectedSmoke,/path: \.cache\/selected-delivery-smoke\.json/);
  assert.doesNotMatch(integration,/WORLDATLAS_CHECKOUT_TOKEN:|Authenticate trusted full-checkout bootstrap|Acquire full checkout with authenticated bounded helper/);
  const checkout=steps.filter(step=>/name: Checkout exact candidate for application regression\n/.test(step));
  assert.equal(checkout.length,1);
  assert.match(checkout[0],/uses: actions\/checkout@d23441a48e516b6c34aea4fa41551a30e30af803/);
  assert.match(checkout[0],/ref: \$\{\{ needs\.prepare\.outputs\.candidate \}\}/);
  assert.match(checkout[0],/sparse-checkout: \|\n            \/\*\n            !\/\*\//);
  const verification=steps.filter(step=>/name: Checkout complete candidate for application regression\n/.test(step));
  assert.equal(verification.length,1);assert.match(verification[0],/HEAD\^\{tree\}/);assert.doesNotMatch(verification[0],/uses: actions\/checkout/);
  assert.match(verification[0],/CI_CHECKOUT_TREE: \$\{\{ needs\.prepare\.outputs\.candidate_tree \}\}/);
  assert.match(integration,/persist-credentials: false/);assert.match(integration,/node scripts\/run-integration-tests.mjs/);assert.match(integration,/run: npm run build:cloudflare/);assert.doesNotMatch(integration,/WORLDATLAS_PACKAGE_PROFILE|run: npm run build:hosted/);
  assert.match(yaml,/needs: \[prepare, integration, geography\]/);
});

test('commit status changing during final review prevents the merge', async () => {
  const f=fixture();f.failStatusOnRead=2;await assert.rejects(f.complete(),/statuses changed/);assert.equal(f.writes.length,0);
});

test('trusted profile uses focused invariants only for isolated evidence and docs', () => {
 assert.equal(integrationProfile('geography/example',[{filename:'research/geography/packet/a.json'}],{owned_paths:['research/geography/packet/']}),'evidence');
 assert.equal(integrationProfile('research/example',[{filename:'research/campaigns/example/a.json'}],{}),'evidence');
 assert.equal(integrationProfile('research/example',[{filename:'research/example/a.json'}],{}),'full');
 for(const helper of ['scripts/prepare-delivery-handoff.mjs','scripts/delivery-handoff-advance.mjs']) {
   assert.equal(integrationProfile('engineering/example',[{filename:helper}],{}),'evidence');
   for(const scientific of ['scripts/native-ownership/native-preparation-guards.mjs','scripts/native-ownership/validate-build-context-stage.mjs','scripts/native-ownership/chained-build-context.mjs','src/native-grid.js']) {
     assert.equal(integrationProfile('engineering/example',[{filename:helper},{filename:scientific}],{}),'full');
     assert.equal(integrationProfile('engineering/example',[{filename:helper,previous_filename:scientific}],{}),'full');
   }
 }
 assert.equal(integrationProfile('engineering/example',[{filename:'docs/WORKER_COORDINATION.md'},{filename:'coordination/engineering/example/receipt.json',status:'added'}],{}),'evidence');
 for(const filename of ['src/attributes.js','data/hierarchy.json','drizzle/0001.sql','scripts/build-hosted.mjs'])
   assert.equal(integrationProfile('engineering/example',[{filename}],{}),'full');
 assert.equal(integrationProfile('engineering/example',[{filename:'docs/a.md',previous_filename:'src/attributes.js'}],{}),'full');
 assert.equal(integrationProfile('engineering/example',[{filename:'coordination/engineering/other/receipt.json'}],{}),'full');
});

test('immutable reader and checkpoint routing retains the complete actual consumer roster and geography gate', () => {
  const prefix='coordination/engineering/selected-geography-effective-prevention-20261009/';
  const methods=['scripts/check-effective-geographic-regression.mjs','scripts/selected-checkpoint-native.mjs', 'scripts/run-geographic-check.py',
    prefix+'selected-checkpoint.mjs',prefix+'selected-joint-entry.mjs'];
  const consumers=[
    "test/accepted-checkpoint-qualification.test.mjs",
    "test/accepted-joint-transport.test.mjs",
    "test/additive-gap-repair.test.mjs",
    "test/administrative-original-hashes.test.mjs",
    "test/component-authority-identity.test.mjs",
    "test/current-rebind-product-custody.test.mjs",
    "test/dated-centre-authority.test.mjs",
    "test/delivery-finalize-config.test.mjs",
    "test/delivery-handoff-advance.test.mjs",
    "test/delivery-handoff.test.mjs",
    "test/delivery-registry-delta.test.mjs",
    "test/effective-geographic-regression.test.mjs",
    "test/evidence-byte-bounds.test.mjs",
    "test/fiji-canonical-reproduction.test.mjs",
    "test/geographic-adjudication-api.test.mjs",
    "test/geographic-checkpoint-products.test.mjs",
    "test/geographic-regression.test.mjs",
    "test/geographic-report-artifact.test.mjs",
    "test/geography-prefetch.test.mjs",
    "test/github-admission.test.mjs",
    "test/immutable-reader-read.test.mjs",
    "test/installed-runtime-identity.test.mjs",
    "test/integration-proof.test.mjs",
    "test/local-workspace.test.mjs",
    "test/map-cell-diagnosis.test.mjs",
    "test/merge-integration.test.mjs",
    "test/native-additions-order.test.mjs",
    "test/native-authority-entry.test.mjs",
    "test/native-checkpoint-consumer.test.mjs",
    "test/native-diagnostic-entry.test.mjs",
    "test/native-witness-authority.test.mjs",
    "test/parallel-geography-comparison.test.mjs",
    "test/physical-source-retention.test.mjs",
    "test/qualification-exclusion-prefilter.test.mjs",
    "test/revised-source-native.test.mjs",
    "test/selected-checkpoint.test.mjs",
    "test/selected-data-profile.test.mjs",
    "test/selected-joint-check.test.mjs",
    "test/selected-joint-entry.test.mjs",
    "test/selected-joint-package-boundary.test.mjs",
    "test/selected-metadata-wiring.test.mjs",
    "test/source-completed-staging.test.mjs",
    "test/source-evidence-derivation.test.mjs",
    "test/source-member-native-delivery.test.mjs",
    "test/source-target-native-delivery.test.mjs",
    "test/source-target-native-diagnostic.test.mjs",
    "test/supported-programs.test.mjs",
    "test/trusted-geography-check.test.mjs",
    "test/trusted-workflow-checkouts.test.mjs",
    "test/unchanged-selected-geography.test.mjs",
    "test/visible-gap-eligibility.test.mjs"
];
  const focused=integrationTestFiles('evidence',0), full=[0,1,2].flatMap(shard=>integrationTestFiles('full',shard));
  for(const name of consumers) {
    assert(focused.includes(name), 'Missing actual reader consumer: '+name);
    assert.equal(full.filter(file=>file===name).length,1);
  }
  assert.equal(integrationNeedsBrowser('evidence',0),false);
  const readerTest={filename:'test/immutable-reader-read.test.mjs',status:'modified'};
  const tree=new Map([[readerTest.filename,{type:'blob',mode:'100644',sha:sha('a')}]]);
  for(const filename of methods) {
    const files=[{filename,status:'modified'},readerTest];
    assert.equal(integrationProfile('engineering/reader',files,{},tree),'evidence',filename);
    assert.equal(candidateGeographyCode('evidence',files,'complete'),true,filename);
    assert.equal(geographyRequired('engineering/reader',files,{},tree),true,filename);
    for(const outside of ['src/main.js','src/native-grid.js','src/effective-footprint.js',
      'scripts/build-static-inner.mjs','scripts/native-ownership/native-preparation-guards.mjs',
      'scripts/check-geographic-regression.py','data/ownership-selection.json','test/compact-ownership.test.mjs']) {
      for(const changed of [[...files,{filename:outside,status:'modified'}],
        [{filename,previous_filename:outside,status:'renamed'},readerTest]])
        assert.equal(integrationProfile('engineering/reader',changed,{},tree),'full',outside);
    }
  }
});

test('ordinary focused tests and checkpoint fixture compose while unknown runtime stays full', () => {
  const files=[...integrationTestFiles('evidence',0),'test/fixtures/selected-checkpoint.mjs'].map(filename=>({filename,status:'modified'}));
  const tree=new Map(files.map(file=>[file.filename,{type:'blob',mode:'100644',sha:'1'.repeat(40)}]));
  assert.equal(integrationProfile('engineering/tests',files,{},tree),'evidence');
  for(const file of files) {
    assert.equal(integrationProfile('engineering/tests',[file],{},tree),'evidence');
    for(const status of [undefined,'added','modified','renamed','copied'])
      assert.equal(integrationProfile('engineering/tests',[{...file,status}],{},tree),'evidence');
    const removed=new Map(tree);removed.delete(file.filename);
    assert.equal(integrationProfile('engineering/tests',[{...file,status:'removed'}],{},removed),'evidence');
    assert.equal(integrationProfile('engineering/tests',[{...file,status:'removed'}],{},tree),'full');
    for(const previous_filename of ['src/native-grid.js','test/unknown.test.mjs'])
      assert.equal(integrationProfile('engineering/tests',[{...file,previous_filename}],{},tree),'full');
    for(const entry of [undefined,{type:'blob',mode:'120000'},{type:'blob',mode:'100755'},{type:'tree',mode:'040000'},{type:'blob',mode:'100644'},{type:'blob',mode:'100644',sha:'unknown'}]) {
      const changed=new Map(tree);entry ? changed.set(file.filename,entry) : changed.delete(file.filename);
      assert.equal(integrationProfile('engineering/tests',[file],{},changed),'full');
    }
    assert.equal(integrationProfile('engineering/tests',[file]),'full');
    for(const filename of ['scripts/prepare-delivery-handoff.mjs','docs/LOCAL_WORKSPACES.md',
      'coordination/engineering/tests/evidence-quality.json'])
      assert.equal(integrationProfile('engineering/tests',[file,{filename,status:'modified'}],{},tree),'evidence');
    for(const filename of ['scripts/native-ownership/native-preparation-guards.mjs',
      'scripts/native-ownership/chained-build-context.mjs','src/native-grid.js','src/main.js','hosted/app.mjs',
      'scripts/build-cloudflare.mjs','vite.config.js','package.json',
      'package-lock.json','requirements.txt','data/hierarchy.json','test/unknown.test.mjs'])
      assert.equal(integrationProfile('engineering/tests',[file,{filename,status:'modified'}],{},tree),'full');
  }
  // These package-contract, asset-dependent and Python-helper tests are not
  // executed by the exact focused Node roster, even with ordinary tree proof.
  for(const filename of ['test/deployment-budget.test.mjs','test/pr-gates.test.mjs',
    'test/canonical-compact-repack.test.mjs','test/source-cohort.test.py','test/physical-source-retention.test.py']) {
    assert.ok(!files.some(file=>file.filename===filename));
    const ordinary=new Map([[filename,{type:'blob',mode:'100644',sha:'1'.repeat(40)}]]);
    assert.equal(integrationProfile('engineering/tests',[{filename,status:'modified'}],{},ordinary),'full');
  }
  assert.equal(integrationProfile('engineering/tests',[],{},tree),'full');
});

test('the exact checkpoint fixture retains every actual importer on the existing focused route', () => {
  const fixture='test/fixtures/selected-checkpoint.mjs';
  const consumers=fs.readdirSync('test',{recursive:true}).filter(name=>name.endsWith('.mjs')).filter(name=>
    [...fs.readFileSync(path.join('test',name),'utf8').matchAll(/(?:from\s*|import\s*(?:\(\s*)?)['"]([^'"]+)['"]/g)]
      .some(([,specifier])=>specifier.startsWith('.')&&path.posix.normalize(path.posix.join('test',path.posix.dirname(name),specifier))===fixture)
  ).map(name=>'test/'+name).sort();
  assert(consumers.length>0,'Fixture importer scan must be nonempty');
  assert(consumers.includes('test/selected-checkpoint.test.mjs'),'Scan must find the known direct checkpoint importer');
  const focused=integrationTestFiles('evidence',0),full=[0,1,2].flatMap(shard=>integrationTestFiles('full',shard));
  for(const consumer of [...consumers,'test/selected-joint-entry.test.mjs']) {
    assert(focused.includes(consumer),consumer);
    assert.equal(full.filter(name=>name===consumer).length,1);
  }
  assert(!focused.includes(fixture),'Fixture is imported by tests, never a standalone test');
  const definition=loadPackageInputs();
  assert(focusedCheckoutPatterns(definition).includes('test'),'Canonical checkout retains the fixture namespace');
  assert.equal(packagePathRequired(fixture,definition),false);
  assert(fs.lstatSync(fixture).isFile());
  const changed={filename:fixture,status:'modified'},tree=new Map([[fixture,{type:'blob',mode:'100644',sha:sha('a')}]]);
  assert.equal(integrationProfile('engineering/fixture',[changed],{},tree),'evidence');
  assert.equal(geographyRequired('engineering/fixture',[changed],{},tree),false);
  for(const filename of ['test/fixtures/unknown.mjs','test/fixtures/selected-checkpoint-other.mjs','src/native-grid.js']) {
    assert.equal(integrationProfile('engineering/fixture',[changed,{filename,status:'modified'}],{},tree),'full');
    assert.equal(integrationProfile('engineering/fixture',[{...changed,previous_filename:filename}],{},tree),'full');
  }
  const method={filename:'coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint.mjs',status:'modified'};
  assert.equal(integrationProfile('engineering/fixture',[changed,method],{},tree),'evidence');
  assert.equal(geographyRequired('engineering/fixture',[changed,method],{},tree),true);
  assert.equal(candidateGeographyCode('evidence',[changed,method],'complete'),true);
});

test('classifier repairs run their complete retained-input regression on the focused route', () => {
  const regression = 'test/selected-data-profile.test.mjs';
  const files = ['scripts/integration-profile.mjs', regression].map(filename => ({filename, status:'modified'}));
  const authored = new Map(files.map(file => [file.filename, {type:'blob', mode:'100644', sha:sha('a')}]));
  assert(integrationTestFiles('evidence', 0).includes(regression));
  assert.equal(integrationProfile('engineering/classifier', files, {}, authored), 'evidence');
  assert.equal(geographyRequired('engineering/classifier', files, {}, authored), false);
  for (const filename of ['scripts/native-ownership/native-preparation-guards.mjs', 'src/native-grid.js',
    'scripts/build-static-inner.mjs', 'data/ownership-selection.json']) {
    const changed = [...files, {filename, status:'modified'}];
    const tree = new Map(authored).set(filename, {type:'blob', mode:'100644', sha:sha('b')});
    assert.equal(integrationProfile('engineering/classifier', changed, {}, tree), 'full', filename);
    assert.equal(geographyRequired('engineering/classifier', changed, {}, tree), true, filename);
  }
  const full = [0, 1, 2].flatMap(shard => integrationTestFiles('full', shard));
  assert.equal(full.filter(name => name === regression).length, 1);
});

test('transport orchestration keeps whole-byte regressions without unrelated application or scientific replay', () => {
  const controls = ['scripts/git-blob-transport.mjs','scripts/immutable-git-blobs.mjs'];
  const tests = ['test/git-blob-transport.test.mjs','test/immutable-git-blobs.test.mjs'];
  const files = [...controls,...tests].map(filename => ({filename,status:'modified'}));
  const authored = new Map(files.map(file => [file.filename,{type:'blob',mode:'100644',sha:sha('a')}]));
  for (const name of tests) assert(integrationTestFiles('evidence',0).includes(name));
  assert.equal(integrationNeedsBrowser('evidence',0),false);
  assert.equal(integrationProfile('engineering/transport',files,{},authored),'evidence');
  assert.equal(geographyRequired('engineering/transport',files,{},authored),false);
  for (const filename of ['src/main.js','scripts/build-static-inner.mjs',
    'scripts/native-ownership/native-preparation-guards.mjs','scripts/qualify-source-cohort.py',
    'src/native-grid.js','data/ownership-selection.json']) {
    const tree = new Map(authored).set(filename,{type:'blob',mode:'100644',sha:sha('b')});
    for (const changed of [[...files,{filename,status:'modified'}],
      [{filename:controls[0],previous_filename:filename,status:'renamed'}]]) {
      assert.equal(integrationProfile('engineering/transport',changed,{},tree),'full',filename);
      assert.equal(geographyRequired('engineering/transport',changed,{},tree),true,filename);
    }
  }
});

test('geography omission derives only non-scientific control and validated focused-test changes', () => {
  const ordinary = name => new Map([[name,{type:'blob',mode:'100644',sha:sha('a')}]]);
  const required = (filename, extra = {}) => geographyRequired('engineering/controls',
    [{filename,status:'modified',...extra}],{},ordinary(filename));
  for (const name of ['scripts/merge-integration.mjs','scripts/run-worker-merge.mjs',
    'scripts/integration-profile.mjs','scripts/prepare-delivery-handoff.mjs'])
    assert.equal(required(name),false,name);
  // Existing checkpoint/current-method and package roles remain mandatory,
  // including shared helpers that otherwise qualify for focused regression.
  for (const name of ['scripts/check-handoff-scope.mjs','scripts/evidence-policy.mjs',
    'scripts/evidence-quality.mjs','scripts/integration-proof.mjs','scripts/issue-claim-contract.mjs',
    'scripts/worker-result.mjs','scripts/local-workspace.mjs',
    'src/native-grid.js','data/hierarchy.json','data/ownership-selection.json',
    '.github/workflows/worker-merge.yml','.github/workflows/merge-integration-checks.yml',
    '.github/evidence-policy.json','docs/WORKER_COORDINATION.md','docs/unknown.md',
    'coordination/engineering/controls/source.json','test/unknown.test.mjs'])
    assert.equal(required(name),true,name);
  for (const status of ['added','modified','renamed','copied'])
    assert.equal(required('test/merge-integration.test.mjs',{status}),false);
  assert.equal(required('test/merge-integration.test.mjs',{status:'removed'}),true);
  assert.equal(required('scripts/merge-integration.mjs',{previous_filename:'scripts/evidence-quality.mjs'}),true);
  assert.equal(required('test/merge-integration.test.mjs',{previous_filename:'scripts/merge-integration.mjs'}),false);
  assert.equal(geographyRequired('engineering/controls',[]),true);
  assert.equal(geographyRequired('geography/controls',[{filename:'scripts/merge-integration.mjs'}]),false);
});

function controlFixture({withContractBoundary=false}={}) {
  const f=fixture(), original=f.api;
  f.files=['scripts/merge-integration.mjs','test/merge-integration.test.mjs'].map(filename=>({filename,status:'modified'}));
  f.pr.changed_files=f.files.length;
  f.authored=f.files.map(file=>({path:file.filename,sha:sha('e'),mode:'100644',type:'blob'}));
  f.baseline=f.authored.map(row=>({...row,sha:sha('d')}));
  const stable=(withContractBoundary?[...EXECUTION_CODE,'test/example.test.mjs','test/fixtures/contract/input.json']:[]).filter(name=>!f.authored.some(row=>row.path===name))
    .map(path=>({path,sha:sha('c'),mode:'100644',type:'blob'}));
  f.authored.push(...structuredClone(stable));f.baseline.push(...structuredClone(stable));
  f.integrated=structuredClone(f.authored);
  f.api=(route,...args)=>route.split('?')[0].endsWith('/pulls/2/files') ? structuredClone(f.files) : original(route,...args);
  return f;
}


test('paired-tree changes compare leaf identity, mode and type without directory or rename noise', () => {
  const entry=(path,sha='a',mode='100644',type='blob')=>({path,sha,mode,type});
  const baseline=[entry('unchanged'),entry('directory','old-tree','040000','tree'),
    entry('directory/leaf'),entry('mode'),entry('kind'),entry('old-name'),
    entry('file-to-directory'),entry('directory-to-file','old-tree','040000','tree'),
    entry('directory-to-file/leaf'),entry('submodule','old-commit','160000','commit')];
  const integrated=[entry('unchanged'),entry('directory','new-tree','040000','tree'),
    entry('directory/leaf'),entry('mode','a','100755'),entry('kind','a','160000','commit'),
    entry('new-name'),entry('file-to-directory','new-tree','040000','tree'),
    entry('file-to-directory/leaf'),entry('directory-to-file'),entry('submodule','new-commit','160000','commit')];
  const map=rows=>new Map(rows.map(row=>[row.path,row]));
  assert.deepEqual(integrationChanges(map(baseline),map(integrated)),[
    {filename:'directory-to-file',status:'added',mode:'100644'},
    {filename:'directory-to-file/leaf',status:'removed'},
    {filename:'file-to-directory',status:'removed'},
    {filename:'file-to-directory/leaf',status:'added',mode:'100644'},
    {filename:'kind',status:'modified',mode:'160000'},
    {filename:'mode',status:'modified',mode:'100755'},
    {filename:'new-name',status:'added',mode:'100644'},
    {filename:'old-name',status:'removed'},
    {filename:'submodule',status:'modified',mode:'160000'}
  ]);
  assert.deepEqual(integrationChanges(map(integrated),map(integrated)),[]);
});

test('stale extra PR paths retain authored evidence but cannot select unrelated runtime work', async () => {
  const f=controlFixture();
  const stale=['src/effective-footprint.js','scripts/selected-delivery-smoke.mjs'];
  for(const path of stale){
    f.files.push({filename:path,status:'modified'});
    f.authored.push({path,sha:sha('f'),mode:'100644',type:'blob'});
    const accepted={path,sha:sha('a'),mode:'100644',type:'blob'};
    f.baseline.push(accepted);f.integrated.push({...accepted});
  }
  f.pr.changed_files=f.files.length;
  let inventories=0;const original=f.api;
  f.api=(route,...args)=>{if(route.includes('/pulls/2/files'))inventories++;return original(route,...args);};
  const options=f.options();
  const prepared=await prepareIntegration(options);
  assert.equal(integrationProfile(f.pr.head.ref,f.files,{},new Map(f.authored.map(row=>[row.path,row]))),'full');
  assert.equal(prepared.profile,'evidence');assert.equal(prepared.geography_required,false);
  assert.equal(prepared.geography_software,false);assert.deepEqual(prepared.files,f.files);
  assert.equal((await f.complete({evidenceCheck:options.evidenceCheck,geographyResult:'skipped'})).accepted,true);
  assert.equal(f.calls.filter(row=>/\/issues\/|\/git\/blobs\//.test(row.route)).length,0);
  assert.equal(inventories,2);
  assert.equal(f.calls.filter(row=>row.route.includes('/git/trees/baseline')).length,2);
  assert.equal(f.calls.filter(row=>row.route.includes('/git/trees/integrated')).length,2);
  assert.equal(f.calls.filter(row=>row.route.includes('/git/trees/authored')).length,0);
});

test('missing API paths cannot hide changed native or unknown checker code at either phase', async () => {
  for(const path of ['src/effective-footprint.js','scripts/previously-unknown-checker.py',
    'coordination/engineering/unknown-packet/replay.mjs']) {
    const f=controlFixture();
    f.integrated.push({path,sha:sha('e'),mode:'100644',type:'blob'});
    const prepared=await prepareIntegration(f.options());
    assert.equal(prepared.profile,'full',path);assert.equal(prepared.geography_required,true,path);
    assert.equal(prepared.geography_software,true,path);
    await assert.rejects(f.complete({geographyResult:'skipped'}),/Trusted combined geography check/);
    await assert.rejects(f.complete(),/exact trusted combined check/);
    assert.equal(f.writes.length,0);
    assert.equal((await f.complete({geographyReportLoader:async()=>({version:1,method_id:'worldatlas-trusted-geography-check-v1',
      baseline_commit:f.base,trusted_code_commit:f.candidate,candidate_commit:f.candidate,candidate_code_executed:true,
      trusted_code_inventory_sha256:'d'.repeat(64),published:false,source_approval:false,gate_status:'passed',status:'not-applicable'})})).accepted,true);
  }
});

test('unchanged listed checker identities use baseline execution while mode changes retain candidate execution', async () => {
  for(const changed of [false,true]){
    const f=fixture(), path='scripts/check-geographic-regression.py';
    const accepted={path,sha:sha('e'),mode:'100644',type:'blob'};
    f.baseline.push(accepted);f.integrated.push({...accepted,...(changed?{mode:'100755'}:{})});
    const original=f.api;
    f.api=(route,...args)=>route.split('?')[0].endsWith('/pulls/2/files')?[{filename:path,status:'modified'}]:original(route,...args);
    const prepared=await prepareIntegration(f.options());
    assert.equal(prepared.profile,'full');assert.equal(prepared.geography_software,changed);
    if(changed)await assert.rejects(f.complete(),/exact trusted combined check/);
    else assert.equal((await f.complete()).accepted,true);
  }
});

test('both routing trees must be complete at preparation and final admission', async () => {
  for(const field of ['baselineTruncated','truncated']){
    const f=controlFixture();f[field]=true;
    await assert.rejects(prepareIntegration(f.options()),/Incomplete integration tree/);
    await assert.rejects(f.complete({geographyResult:'skipped'}),/Incomplete integration tree/);
    assert.equal(f.writes.length,0);
  }
});

test('identical candidate and baseline retain the existing conservative no-op route', async () => {
  const f=controlFixture();f.baseline=structuredClone(f.integrated);
  const prepared=await prepareIntegration(f.options());
  assert.equal(prepared.profile,'full');assert.equal(prepared.geography_required,true);
  assert.equal(prepared.geography_software,false);
  await assert.rejects(f.complete({geographyResult:'skipped'}),/Trusted combined geography check/);
  assert.equal((await f.complete()).accepted,true);
});

test('actual prepare and complete omit unrelated geography without reading or fabricating a report', async () => {
  const f=controlFixture(), prepared=await prepareIntegration(f.options());
  assert.equal(prepared.profile,'evidence');assert.equal(prepared.geography_required,false);
  assert.deepEqual(prepared.checkout_patterns,focusedCheckoutPatterns(f.packageInputs));
  assert(f.calls.some(row=>row.route.endsWith('/contents/.github/package-inputs.json?ref='+f.candidate)));
  const result=await f.complete({geographyResult:'skipped',geographyReportLoader:()=>{throw Error('Unrelated geography must not run');}});
  assert.equal(result.accepted,true);assert.equal(f.writes.length,1);
  assert.deepEqual(result.geography,{status:'not-applicable',reason:'non-geographic-controls'});
  assert.equal(result.tested_base,f.base);assert.equal(result.tested_candidate,f.candidate);
  assert.equal(result.reviewed_head,f.head);
});

test('omission never turns failed, cancelled or absent geography into success', async () => {
  for (const geographyResult of [undefined,'failure','cancelled']) {
    const f=controlFixture();await assert.rejects(f.complete({geographyResult}),/Trusted combined geography check/);
    assert.equal(f.writes.length,0);
  }
  const f=controlFixture();await assert.rejects(f.complete({geographyReportLoader:undefined}),/Missing trusted geography report/);
});

test('final omission independently rechecks current method and ordinary focused-test applicability', async () => {
  for (const kind of ['scientific','packet','test-mode','rename-origin']) {
    const f=controlFixture();await prepareIntegration(f.options());
    if(kind==='scientific')f.integrated[0].path='scripts/evidence-quality.mjs';
    if(kind==='packet')f.integrated[0].path='coordination/engineering/test/source.json';
    if(kind==='test-mode')f.integrated[1].mode='120000';
    if(kind==='rename-origin')f.baseline[0].path='data/hierarchy.json';
    await assert.rejects(f.complete({geographyResult:'skipped'}));assert.equal(f.writes.length,0,kind);
  }
});

test('omitted geography retains exact candidate, review, statuses and both main guards', async () => {
  for (const kind of ['head','early-base','late-base','parents','status','integration']) {
    const f=controlFixture(), options={geographyResult:'skipped'};
    if(kind==='head')f.pr.head.sha=sha('d');
    if(kind==='early-base')f.advanceOnRead=1;
    if(kind==='late-base')f.advanceOnRead=3;
    if(kind==='parents')f.parentBase=sha('d');
    if(kind==='status')f.failStatusOnRead=2;
    if(kind==='integration')options.integrationResult='skipped';
    await assert.rejects(f.complete(options));assert.equal(f.writes.length,0,kind);
  }
});

test('actual review-receipt PR 2010 paths use the complete applicable focused inventory', () => {
  const names = ['docs/AUTHOR_PREFLIGHT.md','docs/GEOGRAPHIC_GAP_ADJUDICATION.md',
    'docs/PREMERGE_EVIDENCE_REVIEW.md','docs/prompts/ENGINEERING.txt','docs/prompts/GEOGRAPHY.txt',
    'docs/prompts/LUNA_HISTORY.txt','scripts/geographic-adjudication-api.mjs','scripts/merge-integration.mjs',
    'scripts/premerge-evidence.mjs','test/geographic-adjudication-api.test.mjs',
    'test/merge-integration.test.mjs','test/premerge-evidence.test.mjs'];
  const files = names.map(filename => ({filename, status: 'modified'}));
  const authored = new Map(names.map(name => [name, {type:'blob', mode:'100644', sha:'1'.repeat(40)}]));
  assert.equal(integrationProfile('engineering/remove-duplicate-review-receipts-20261015', files, {}, authored), 'evidence');
  for (const file of files.filter(file => file.filename.startsWith('test/')))
    assert(integrationTestFiles('evidence',0).includes(file.filename), file.filename);
  const yaml = fs.readFileSync('.github/workflows/worker-merge.yml','utf8');
  const focused = yaml.split('      - name: Materialize exact prepared checkout inputs\n')[1].split('      - name:')[0];
  assert.match(focused,/needs\.prepare\.outputs\.profile == 'evidence'/);
  assert.match(focused,/needs\.prepare\.outputs\.checkout_patterns_base64/);
  assert.match(focused,/'sparse-checkout', 'set', '--no-cone', '--stdin'/);
  assert(focusedCheckoutPatterns(loadPackageInputs()).includes('/coordination/engineering/coverage-gaps-907-20261005-local01/sources/natural-earth-lakes.geojson.gz'));
  const unknown = {filename:'test/new-emitted-asset.test.mjs',status:'added'};
  authored.set(unknown.filename,{type:'blob',mode:'100644',sha:'2'.repeat(40)});
  assert.equal(integrationProfile('engineering/example',[...files,unknown],{},authored),'full');
});

test('parallel full-regression shards cover each unit file once and focused profile retains core gates', () => {
 const expected=fs.readdirSync('test').filter(name=>name.endsWith('.test.mjs')).map(name=>`test/${name}`).sort();
 const shards=[0,1,2].flatMap(shard=>integrationTestFiles('full',shard));
 for(const name of ['test/compact-ownership.test.mjs','test/prepared-parity.test.mjs']) {
   assert.ok(integrationTestFiles('full',0).includes(name));
   assert.ok(!integrationTestFiles('full',1).includes(name));
   assert.ok(!integrationTestFiles('full',2).includes(name));
 }
 assert.deepEqual([...shards].sort(),expected);assert.equal(new Set(shards).size,expected.length);
 const focused=integrationTestFiles('evidence',0);
 assert.deepEqual(focused,expected.filter(focusedIntegrationTest));
 assert.equal(new Set(focused).size,focused.length);
 for(const name of ['premerge-evidence','regional-research-gate','handoff-scope','merge-integration'])assert.ok(focused.includes(`test/${name}.test.mjs`));
 assert.throws(()=>integrationTestFiles('evidence',1),/Invalid/);
 assert.equal(integrationNeedsBrowser('evidence',0),false);
 // New test files can move browser tests across modulo-distributed shards.
 // Each shard must request the browser precisely when its actual files need it.
 for(const shard of [0,1,2]){
   const needsBrowser=integrationTestFiles('full',shard).some(name=>
     /['"](?:@playwright\/test|playwright)['"]/.test(fs.readFileSync(name,'utf8')));
   assert.equal(integrationNeedsBrowser('full',shard),needsBrowser);
 }
 assert.ok([0,1,2].some(shard=>integrationNeedsBrowser('full',shard)));
});

test('ordinary selected data uses emitted smoke while software and explicit output proof retain unit/browser qualification', () => {
 assert.throws(()=>integrationTestFiles('full',0,'selected-data'),/Invalid/);
 assert.ok(integrationTestFiles('full',0,'complete').includes('test/compact-ownership.test.mjs'));
 assert.equal(integrationNeedsBrowser('full',0,'complete'),true);
 assert.deepEqual(integrationTestFiles('full',0,'selected-output'),['test/compact-ownership.test.mjs']);
 assert.equal(integrationNeedsBrowser('full',0,'selected-output'),true);
 assert.throws(()=>integrationTestFiles('evidence',0,'selected-data'),/Invalid/);
 assert.throws(()=>integrationTestFiles('full',1,'selected-data'),/Invalid/);
});

test('ordinary prepare never discovers author computation and skipped final work always rejects',async()=>{
  const f=fixture(), original=f.api;
  f.api=async(route,...args)=>{assert(!route.includes('/actions/'),'No author computation discovery');return original(route,...args);};
  const prepared=await prepareIntegration(f.options());
  assert.equal(prepared.profile,'full');assert(!('proof' in prepared));assert(!('geography_proof' in prepared));
  for(const integrationResult of ['skipped','failure','cancelled',undefined]){
    await assert.rejects(f.complete({integrationResult,proofRunId:12,proofRunAttempt:1}),/Integration tests failed, skipped or were cancelled/);
    assert.equal(f.writes.length,0);
  }
});

test('owned preparation checks authority once and ignores the automatic preview',async()=>{
  for(const preview of [null,sha('d'),sha('c')]) {
    const f=fixture();f.pr.merge_commit_sha=preview;
    const result=await prepareIntegration(f.options());
    assert.equal(result.candidate,f.candidate);assert.equal(f.calls.filter(row=>/\/issues\//.test(row.route)).length,0);
    assert.equal(f.calls.filter(row=>row.route.endsWith('/pulls/2')).length,1);
    assert.equal(f.mainReads,1);assert.equal(f.calls.filter(row=>row.method==='POST').length,2);
    assert.equal(f.calls.filter(row=>row.route.endsWith('/git/commits/'+f.candidate)).length,1);
    assert(!f.calls.some(row=>row.route.endsWith('/git/commits/'+sha('d'))));
    assert.equal(f.writes.length,0);assert.equal(f.refs.get(result.candidate_ref),f.candidate);
    assert(!('candidate_refresh_attempts' in result));
  }
  const source=fs.readFileSync(new URL('../scripts/merge-integration.mjs',import.meta.url),'utf8');
  assert.doesNotMatch(source,/currentCandidate|candidateSleep|candidateNow|setTimeout/);
});
test('owned candidate object failures are not retried and clean only the known ref',async()=>{
  for(const status of [404,403]) {
    const f=isolatedFixture(),api=f.api;let reads=0;
    f.api=async(route,...rest)=>{
      if(route.endsWith('/git/commits/'+f.synthetic)){reads++;throw Error(`GitHub GET failed (HTTP ${status})`);}
      return api(route,...rest);
    };
    await assert.rejects(prepareIntegration(f.options()),new RegExp('HTTP '+status));
    assert.equal(reads,1);assert.equal(f.refs.size,0);assert.equal(f.writes.length,0);
  }
});

function isolatedFixture() {
  const f=fixture(),api=f.api;f.operations=[];f.refs=new Map();f.synthetic=sha('e');
  f.api=async(route,method='GET',body)=>{
    f.operations.push({route,method,body});
    if(route===`/repos/${f.repo}/git/refs`&&method==='POST') {
      assert.equal(body.sha,f.base);assert.match(body.ref,/^refs\/heads\/worldatlas-integration\/pr-2-/);
      if(f.createDenied)throw Error('GitHub POST failed (HTTP 403)');
      f.refs.set(body.ref.replace('refs/heads/',''),body.sha);return {ref:body.ref};
    }
    if(route===`/repos/${f.repo}/merges`&&method==='POST') {
      assert.notEqual(body.base,'main');assert.notEqual(body.base,f.pr.head.ref);assert.equal(body.head,f.head);
      if(f.mergeConflict)throw Error('GitHub POST failed (HTTP 409)');
      f.refs.set(body.base,f.synthetic);return {sha:f.synthetic};
    }
    if(/\/git\/refs?\/heads\/worldatlas-integration\//.test(route)) {
      const ref=route.split(/\/git\/refs?\/heads\//)[1];
      if(method==='DELETE') {if(f.deleteDenied)throw Error('GitHub DELETE failed (HTTP 403)');f.refs.delete(ref);return null;}
      return {object:{sha:f.refChanged?sha('f'):f.refs.get(ref)}};
    }
    if(route.endsWith('/git/commits/'+f.synthetic))return {sha:f.wrongSyntheticIdentity?sha('f'):f.synthetic,tree:f.missingSyntheticTree?undefined:{sha:'integrated'},parents:[{sha:f.wrongSyntheticParent?sha('d'):f.base},{sha:f.head}]};
    return api(route,method,body);
  };
  const options=f.options;f.options=()=>({...options(),integrationRequestId:'isolated-candidate-test-request'});
  return f;
}
test('owned preparation ignores stale automatic preview without editing authored branches',async()=>{
  const f=isolatedFixture();f.parentBase=sha('d');
  const result=await prepareIntegration(f.options());
  assert.equal(result.candidate,f.synthetic);assert.equal(f.calls.filter(row=>/\/issues\//.test(row.route)).length,0);
  assert.equal(f.refs.get(result.candidate_ref),f.synthetic);assert.equal(result.pr.head.sha,f.head);
  assert.equal(f.writes.length,0);
  assert.equal((await cleanupCandidate(f.options(),result.candidate_ref,f.synthetic)).status,'deleted');
  assert.equal(f.refs.size,0);
});
test('isolated conflict or wrong parents is rejected and only the owned ref is deleted',async()=>{
  for(const field of ['mergeConflict','wrongSyntheticParent','wrongSyntheticIdentity','missingSyntheticTree']) {
    const f=isolatedFixture();f[field]=true;
    await assert.rejects(createCandidate(f.options(),{pr:f.pr,base:f.base}),/conflict|exact current main|identity or tree unavailable/);
    assert.equal(f.refs.size,0);assert.equal(f.writes.length,0);
  }
});
test('owned preparation retains complete candidate trees and current authority',async()=>{
  const f=isolatedFixture();f.parentBase=sha('d');f.truncated=true;
  await assert.rejects(prepareIntegration(f.options()),/Incomplete integration tree/);
  assert.equal(f.refs.size,0);assert.equal(f.writes.length,0);
  const g=isolatedFixture();g.parentBase=sha('d');g.checks[0].conclusion='failure';
  await assert.rejects(prepareIntegration(g.options()),/pending or failed/);
  assert.equal(g.operations.some(row=>row.method==='POST'),false);
});
test('cleanup refuses another request, main/worker refs and changed owned refs',async()=>{
  const f=isolatedFixture();const created=await createCandidate(f.options(),{pr:f.pr,base:f.base});
  for(const ref of ['main',f.pr.head.ref,created.reference+'-other'])await assert.rejects(cleanupCandidate(f.options(),ref,f.synthetic),/unowned/);
  f.refChanged=true;await assert.rejects(cleanupCandidate(f.options(),created.reference,f.synthetic),/reference changed/);
  assert.equal(f.refs.size,1);assert.equal(f.operations.some(row=>row.method==='DELETE'),false);
});
test('failed cleanup retains its exact resource for inspection without hiding rejection',async()=>{
  const f=isolatedFixture();f.parentBase=sha('d');f.truncated=true;f.deleteDenied=true;
  await assert.rejects(prepareIntegration(f.options()),error=>{
    assert.match(error.message,/Incomplete integration tree/);assert.equal(error.candidateCleanup.status,'pending');
    assert.match(error.candidateCleanup.reference,/^worldatlas-integration\/pr-2-/);return true;
  });assert.equal(f.writes.length,0);
});

test('isolated candidate follows the existing final tests/main/head merge guards',async()=>{
  const f=isolatedFixture();f.parentBase=sha('d');const prepared=await prepareIntegration(f.options());
  await f.complete({testedCandidate:prepared.candidate,testedBase:prepared.base});
  assert.equal(f.writes[0].sha,f.head);assert.equal(f.writes[0].merge_method,'squash');
  await cleanupCandidate(f.options(),prepared.candidate_ref,prepared.candidate);assert.equal(f.refs.size,0);
  const g=isolatedFixture();g.parentBase=sha('d');const gp=await prepareIntegration(g.options());g.base=sha('d');
  await assert.rejects(g.complete({testedCandidate:gp.candidate,testedBase:gp.base}),/Main advanced/);assert.equal(g.writes.length,0);
});

test('same-candidate failed-job retry survives owned ref cleanup and keeps final authority guards',async()=>{
  for(const changed of [null,'base','head','parents','checks','integration','geography']){
    const f=isolatedFixture();f.parentBase=sha('d');
    const prepared=await prepareIntegration(f.options());
    await cleanupCandidate(f.options(),prepared.candidate_ref,prepared.candidate);
    assert.equal(f.refs.size,0);
    const options={testedCandidate:prepared.candidate,testedBase:prepared.base};
    if(changed==='base')f.base=sha('d');
    if(changed==='head')f.pr.head.sha=sha('d');
    if(changed==='parents')f.wrongSyntheticParent=true;
    if(changed==='checks')f.checks[0].conclusion='failure';
    if(changed==='integration')options.integrationResult='failure';
    if(changed==='geography')options.geographyResult='failure';
    if(changed){await assert.rejects(f.complete(options));assert.equal(f.writes.length,0,changed);}
    else{assert.equal((await f.complete(options)).accepted,true);assert.equal(f.writes[0].sha,f.head);}
    assert.equal(f.refs.size,0,'Final validation consumes immutable SHA, not the deleted ref');
  }
});

test('unconfirmed ref creation identifies the resource without deleting a possible collision',async()=>{
  const f=isolatedFixture();f.createDenied=true;
  await assert.rejects(createCandidate(f.options(),{pr:f.pr,base:f.base}),error=>{
    assert.match(error.message,/HTTP 403/);assert.equal(error.candidateCleanup.status,'creation-unconfirmed');
    assert.match(error.candidateCleanup.reference,/^worldatlas-integration\/pr-2-/);return true;
  });assert.equal(f.operations.some(row=>row.method==='DELETE'),false);assert.equal(f.writes.length,0);
});

test('lost owned creation or merge responses retain possible resources without deleting them',async()=>{
  for(const phase of ['create','merge']) {
    const f=isolatedFixture(),api=f.api;
    f.api=async(route,method,...rest)=>{
      const value=await api(route,method,...rest);
      if(method==='POST'&&route.endsWith(phase==='create'?'/git/refs':'/merges'))throw Error('Lost response after remote write');
      return value;
    };
    await assert.rejects(prepareIntegration(f.options()),error=>{
      assert.match(error.message,/Lost response/);
      assert.equal(error.candidateCleanup.status,phase==='create'?'creation-unconfirmed':'pending');
      if(phase==='merge')assert.match(error.candidateCleanup.reason,/reference changed/);
      return true;
    });
    assert.equal(f.refs.size,1);assert.equal([...f.refs.values()][0],phase==='create'?f.base:f.synthetic);
    assert.equal(f.operations.some(row=>row.method==='DELETE'),false);assert.equal(f.writes.length,0);
  }
});

function headCleanupFixture() {
  const f = {repo:'owner/repo', number:2, expectedHead:sha('a'), deletes:[], reads:[]};
  f.pr = {number:2,merged:true,state:'closed',merge_commit_sha:sha('b'),
    head:{sha:f.expectedHead,ref:'engineering/finished',repo:{full_name:f.repo}}};
  f.branch = {protected:false,commit:{sha:f.expectedHead}};
  f.open = []; f.defaultBranch='main';
  f.api = async (route, method='GET') => {
    f.reads.push({route,method});
    if (f.failAt && route.includes(f.failAt)) throw Error('API denied (HTTP 403)');
    if (method==='DELETE') {
      if(f.deleteDenied)throw Error('Deletion denied (HTTP 403)');
      f.deletes.push(route); return null;
    }
    if (route===`/repos/${f.repo}/pulls/2`) return structuredClone(f.pr);
    if (route===`/repos/${f.repo}`) return {default_branch:f.defaultBranch};
    if (route.includes('/branches/')) {
      if(f.absent)throw Error('Branch absent (HTTP 404)');
      return structuredClone(f.branch);
    }
    if (route.includes('/pulls?state=open')) {
      const page=Number(new URL('https://api.github.test'+route).searchParams.get('page'));
      if(f.badInventory)return {};
      return f.pages ? f.pages[page-1]??[] : structuredClone(f.open);
    }
    if(route.includes('/git/ref/heads/')) {
      if(f.refAbsent)throw Error('Ref absent (HTTP 404)');
      return {object:{sha:f.lastSHA??f.expectedHead}};
    }
    throw Error('Unexpected cleanup API '+route);
  };
  return f;
}
test('merged head cleanup deletes only confirmed unchanged same-repository unused worker heads',async()=>{
  const f=headCleanupFixture();const result=await cleanupMergedHead(f);
  assert.equal(result.status,'deleted');assert.equal(result.expected_head,f.expectedHead);
  assert.deepEqual(f.deletes,['/repos/owner/repo/git/refs/heads/engineering%2Ffinished']);
  assert.match(f.reads.at(-2).route,/\/git\/ref\/heads\//);
  for(const setting of ['absent','refAbsent']) {
    const f=headCleanupFixture();f[setting]=true;
    assert.equal((await cleanupMergedHead(f)).status,'absent');assert.equal(f.deletes.length,0);
  }
});
test('unmerged, wrong head, fork, default, protected, advanced and shared heads are retained',async()=>{
  const mutations=[
    f=>{f.pr.merged=false;}, f=>{f.pr.state='open';}, f=>{f.pr.merge_commit_sha=null;},
    f=>{f.pr.head.sha=sha('d');}, f=>{f.pr.head.repo.full_name='fork/repo';},
    f=>{f.pr.head.repo=null;}, f=>{f.pr.head.ref='main';},
    f=>{f.defaultBranch=f.pr.head.ref;}, f=>{f.branch.protected=true;},
    f=>{delete f.branch.protected;}, f=>{f.branch.commit.sha=sha('d');},
    f=>{f.lastSHA=sha('d');}, f=>{f.open=[{number:3,state:'open',base:{ref:'main',repo:{full_name:f.repo}},head:structuredClone(f.pr.head)}];},
    f=>{f.open=[{number:3,state:'open',base:structuredClone(f.pr.head),head:{ref:'engineering/other',repo:{full_name:f.repo}}}];},
    f=>{f.pr.head.ref='engineering/../main';}, f=>{f.pr.head.ref='worldatlas-integration/other';}
  ];
  for(const mutate of mutations) {
    const f=headCleanupFixture();mutate(f);const result=await cleanupMergedHead(f);
    assert.equal(result.status,'retained',result.reason);assert.equal(f.deletes.length,0);
  }
});
test('head cleanup checks paginated open PRs and fails conservatively on unknown identities or API failures',async()=>{
  const f=headCleanupFixture();f.pages=[Array.from({length:100},(_,i)=>({number:i+10,state:'open',base:{ref:'main',repo:{full_name:f.repo}},head:{ref:'engineering/other-'+i,repo:{full_name:f.repo}}})),
    [{number:999,state:'open',base:{ref:'main',repo:{full_name:f.repo}},head:structuredClone(f.pr.head)}]];
  assert.equal((await cleanupMergedHead(f)).status,'retained');assert.equal(f.deletes.length,0);
  assert.ok(f.reads.some(row=>row.route.endsWith('page=2')));
  f.pages[1][0].head.ref='engineering/another';f.pages[1][0].base=structuredClone(f.pr.head);
  assert.equal((await cleanupMergedHead(f)).status,'retained');assert.equal(f.deletes.length,0);
  for(const mutate of [f=>{f.badInventory=true;},f=>{f.open=[{number:3,state:'open'}];},
    f=>{f.failAt='/branches/';},f=>{f.deleteDenied=true;},f=>{f.defaultBranch=null;}]) {
    const f=headCleanupFixture();mutate(f);const result=await cleanupMergedHead(f);
    assert.equal(result.status,'pending');assert.equal(f.deletes.length,0);assert.ok(result.reason);
  }
  const fork=headCleanupFixture();fork.open=[{number:3,state:'open',base:{ref:'main',repo:{full_name:fork.repo}},head:{ref:fork.pr.head.ref,repo:{full_name:'fork/repo'}}}];
  assert.equal((await cleanupMergedHead(fork)).status,'deleted');
});
test('successful integration records cleanup separately, including deletion failure and replay',async()=>{
  for(const deleteDenied of [false,true]) {
    const f=fixture(),cleanup=headCleanupFixture(),normal=f.api;
    cleanup.pr.head.ref=f.pr.head.ref;cleanup.deleteDenied=deleteDenied;
    f.api=async(route,method='GET',body)=>{
      if(method==='PUT') {const result=await normal(route,method,body);f.pr.merged=true;f.pr.state='closed';f.pr.merge_commit_sha=result.sha;return result;}
      if(f.pr.merged && (route.endsWith('/pulls/2')||route==='/repos/owner/repo'||route.includes('/branches/')||route.includes('/pulls?state=open')||route.includes('/git/ref/heads/engineering')||method==='DELETE'))return cleanup.api(route,method,body);
      return normal(route,method,body);
    };
    const result=await f.complete();assert.equal(result.accepted,true);assert.equal(result.merge_commit,sha('f'));
    assert.equal(result.head_cleanup.status,deleteDenied?'pending':'deleted');
    assert.equal(f.writes.length,1);
  }
  const f=fixture(),cleanup=headCleanupFixture();f.pr.merged=true;f.pr.state='closed';f.pr.merge_commit_sha=sha('b');
  f.api=cleanup.api;
  const result=await f.complete();assert.equal(result.accepted,true);assert.equal(result.replayed,true);assert.equal(result.head_cleanup.status,'deleted');
});


test('cleanup stops on time or inventory call budget without starting deletion after pending',async()=>{
  const timed=headCleanupFixture();let elapsed=0;timed.cleanupNow=()=>elapsed;
  const original=timed.api;timed.api=async(...args)=>{const value=await original(...args);elapsed+=16000;return value;};
  assert.equal((await cleanupMergedHead(timed)).status,'pending');assert.equal(timed.deletes.length,0);
  const paged=headCleanupFixture();paged.pages=Array.from({length:20},()=>Array.from({length:100},(_,i)=>({
    number:i+10,state:'open',head:{ref:'engineering/other',repo:{full_name:paged.repo}},base:{ref:'main',repo:{full_name:paged.repo}}})));
  const result=await cleanupMergedHead(paged);assert.equal(result.status,'pending');assert.match(result.reason,/budget/);
  assert.equal(paged.deletes.length,0);assert.equal(paged.reads.length,10);
});


test('fresh queue geography is mandatory even when old author proof options are supplied',async()=>{
 for(const geographyResult of [undefined,'failure','cancelled','skipped']){
  const f=fixture();
  await assert.rejects(f.complete({geographyResult,proofRunId:12,proofRunAttempt:1}),/Trusted combined geography check/);
  assert.equal(f.writes.length,0);
 }
});
test('fresh geography success is recorded against exact combined commits',async()=>{
 const f=fixture();const result=await f.complete();
 assert.deepEqual(result.geography,{status:'passed',trusted_code_commit:f.base,candidate_commit:f.candidate,report_sha256:undefined,adjudication:null});
});


test('green geography job cannot merge without its authenticated exact-combined report', async()=>{
 for (const delta of [{geographyReportLoader:undefined},
   {geographyReportLoader:async()=>({version:1,gate_status:'passed'})},
   {geographyReportLoader:async()=>{throw Error('Report archive bytes differ from trusted geography job digest');}}]) {
  const f=fixture(); await assert.rejects(f.complete(delta)); assert.equal(f.writes.length,0);
 }
});
test('raw unresolved findings cannot be relabeled as a successful geography check',async()=>{
 const f=fixture(); await assert.rejects(f.complete({geographyReportLoader:async()=>({
  version:1,method_id:'worldatlas-trusted-geography-check-v1',baseline_commit:f.base,
  trusted_code_commit:f.base,candidate_commit:f.candidate,candidate_code_executed:false,
  published:false,source_approval:false,gate_status:'passed',status:'regressions-found',regressions:1
 })}),/findings remain unresolved/); assert.equal(f.writes.length,0);
});

test('trusted geography outputs bind attempted artifact digest through the privileged merge job',()=>{
 const workflow=fs.readFileSync('.github/workflows/worker-merge.yml','utf8');
 const geography=workflow.match(/\n  geography:\n([\s\S]*?)(?=\n  integration:)/)[1];
 assert.match(geography,/report_sha256: \$\{\{ steps\.check\.outputs\.report_sha256 \}\}/);
 assert.match(geography,/artifact_name: \$\{\{ steps\.check\.outputs\.artifact_name \}\}/);
 for(const [output,step,field] of [['report_bytes','check','report_bytes'],['artifact_id','upload','artifact-id'],['artifact_digest','upload','artifact-digest']]) {
  assert(geography.includes(`${output}: \${{ steps.${step}.outputs.${field} }}`));
  assert(workflow.includes(`GEOGRAPHY_${output.toUpperCase()}: \${{ needs.geography.outputs.${output} }}`));
 }
 assert.match(geography,/id: upload/);
 assert.match(geography,/id: check/);
 assert.match(geography,/GEOGRAPHY_PR_NUMBER: \$\{\{ inputs\.pr_number \}\}/);
 assert.match(geography,/GEOGRAPHY_REVIEWED_HEAD: \$\{\{ inputs\.expected_head \}\}/);
 assert.match(geography,/GEOGRAPHY_ARTIFACT_NAME: geography-\$\{\{ inputs\.request_id \}\}-\$\{\{ github\.run_attempt \}\}/);
 assert.match(geography,/echo "artifact_name=\$GEOGRAPHY_ARTIFACT_NAME" >> "\$GITHUB_OUTPUT"/);
 assert.match(workflow,/GEOGRAPHY_REPORT_SHA256: \$\{\{ needs\.geography\.outputs\.report_sha256 \}\}/);
 assert.match(workflow,/GEOGRAPHY_ARTIFACT_NAME: \$\{\{ needs\.geography\.outputs\.artifact_name \}\}/);
 const runner=fs.readFileSync('scripts/run-worker-merge.mjs','utf8');
 assert.match(runner,/geographyReportLoader: \(\{api: reportAPI = api\} = \{\}\) => loadGeographicReport\(\{api: reportAPI/);
 assert.match(runner,/runId: process\.env\.GITHUB_RUN_ID/);
 assert.match(runner,/expectedHash: process\.env\.GEOGRAPHY_REPORT_SHA256/);
 assert.match(runner,/artifact_id: Number\(process\.env\.GEOGRAPHY_ARTIFACT_ID\)/);
 assert.match(runner,/artifact_digest: process\.env\.GEOGRAPHY_ARTIFACT_DIGEST/);
 assert.match(runner,/report_bytes: Number\(process\.env\.GEOGRAPHY_REPORT_BYTES\)/);
 assert.doesNotMatch(workflow,/GEOGRAPHY_PROOF:|proof_run:|proof_attempt:/);
 assert.doesNotMatch(workflow,/actions\/download-artifact/,'privileged job must not extract an unverified archive');
});


test('known stale tested base or head rejects before expensive evidence/tree inspection', async()=>{
 const stale=fixture();stale.base=sha('d');
 await assert.rejects(stale.complete(),/resubmit unchanged head/);
 assert.equal(stale.evidenceReads??0,0);assert.equal(stale.writes.length,0);
 const changed=fixture();changed.pr.head.sha=sha('e');
 await assert.rejects(changed.complete(),/head changed/);
 assert.equal(changed.evidenceReads??0,0);assert.equal(changed.mainReads,0);assert.equal(changed.writes.length,0);
 const eligible=fixture();await eligible.complete();assert.equal(eligible.evidenceReads??0,0);assert.equal(eligible.writes.length,1);
});


test('checks or reviewed head changing during candidate creation still refuse final merge',async()=>{
 for(const changed of ['check','head']) {
  const f=isolatedFixture(),origin=f.api;
  f.api=async(route,...rest)=>{
   const value=await origin(route,...rest);
   if(route.endsWith('/git/commits/'+f.synthetic)) {
    if(changed==='check')f.checks[0].conclusion='failure';
    if(changed==='head')f.pr.head.sha=sha('e');
   }
   return value;
  };
  const prepared=await prepareIntegration(f.options());assert.equal(prepared.candidate,f.synthetic);
  await assert.rejects(f.complete({testedCandidate:prepared.candidate,testedBase:prepared.base}),
    changed==='check'?/pending or failed/:/head changed/);
  assert.equal(f.writes.length,0);
  await cleanupCandidate(f.options(),prepared.candidate_ref,prepared.candidate);assert.equal(f.refs.size,0);
 }
});

// Final merge semantics retained from the removed speculative capacity planner.
{
function finalMergeFixture({software = false} = {}) {
  const repo = 'o/r', head = 'b'.repeat(40), base = 'a'.repeat(40), candidate = 'c'.repeat(40), branch = 'engineering/final-fixture';
  const manifestPath = 'coordination/engineering/final-fixture/evidence-quality.json';
  const outputPath = software ? 'scripts/controlled-geography.mjs' : 'coordination/engineering/final-fixture/result.json';
  const baselineRaw = Buffer.from('baseline\n'), outputRaw = Buffer.from('{"controlled":true}\n');
  const desc = (path, raw) => ({path, bytes: raw.length, sha256: sha256(raw), hash_kind: 'file-bytes'});
  const files = [{filename: outputPath, status: 'added'}, {filename: manifestPath, status: 'added'}];
  const quality = {version: 1, manifest_path: 'coordination/engineering/{job}/evidence-quality.json', subject_ids: [], pins: {}, review_kind: 'release'};
  const spec = {mode: 'engineering', max_prs: 1, scope: 'Synthetic final validation controls', depends_on: [], evidence_quality: quality};
  const issue = {number: 1183, state: 'open', created_at: '2026-10-06T00:00:00Z', labels: ['type:engineering', 'kind:work-item', 'status:ready'],
    body: `<!-- worldatlas-work:v1\n${JSON.stringify(spec)}\n-->`};
  const pr = {number: 23, head: {sha: head, ref: branch, repo: {full_name: repo}}, base: {sha: base, ref: 'main'},
    state: 'open', draft: false, merged: false, title: 'Synthetic final validation', body: 'Refs #1183', changed_files: 2};
  const manifest = {version: 1, issue: 1183, lane: 'engineering', worker_id: 'author', subject_ids: [], subject_ids_sha256: subjectsHash([]),
    baseline: {commit: base, files: [desc('README.md', baselineRaw)]}, sources: [], outputs: [desc(outputPath, outputRaw)],
    methods: [{id: 'controlled', kind: 'code', description: 'Synthetic final validation controls', software: 'Node', units: 'pass/fail'}],
    validation: [], metrics: [], metric_bindings: [], summaries: [], conclusions: [], commands: ['node --test'],
    stages: {research: 'complete', implementation: 'implemented', geographic_approval: 'not-requested'},
    change_receipts: files.map(row => ({path: row.filename, status: row.status}))};
  const manifestRaw = Buffer.from(JSON.stringify(manifest));
  const blobs = new Map(), tree = rows => rows.map(([path, raw]) => {
    const sha = createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
    blobs.set(sha, {sha, size: raw.length, encoding: 'base64', content: raw.toString('base64')});
    return {path, sha, size: raw.length, mode: '100644', type: 'blob'};
  });
  const authored = tree([['README.md', baselineRaw], [outputPath, outputRaw], [manifestPath, manifestRaw]]), baseline = tree([['README.md', baselineRaw]]);
  const f = {repo, head, base, candidate, issue, pr, files, manifest, blobs, authored, baseline, calls: [], writes: [], checks: 'success'};
  f.api = async (route, method = 'GET', body) => {
    f.calls.push({route, method}); const name = route.split('?')[0];
    if (method !== 'GET') {f.writes.push({route, method, body}); return {merged: true, sha: 'd'.repeat(40)};}
    if (name === `/repos/${repo}/pulls`) return [structuredClone(f.pr)];
    if (name === `/repos/${repo}/pulls/23`) return structuredClone(f.pr);
    if (name === `/repos/${repo}/issues/1183`) return structuredClone(f.issue);
    if (name.endsWith('/timeline')) return [];
    if (name === `/repos/${repo}/pulls/23/files`) return structuredClone(f.files);
    if (name.endsWith('/check-runs')) return {check_runs: ['scope', 'evidence'].map((name, id) => ({name, id, status: 'completed', conclusion: f.checks}))};
    if (name.endsWith('/status')) return {statuses: []};
    if (name === `/repos/${repo}/git/ref/heads/main`) return {object: {sha: f.base}};
    if (name.includes('/git/commits/')) {
      const commit = name.split('/').at(-1);
      return {sha: commit, tree: {sha: commit === base ? '1'.repeat(40) : '2'.repeat(40)}, parents: [{sha: base}, {sha: head}]};
    }
    if (name.includes('/git/trees/')) return {truncated: f.truncated ?? false, tree: name.endsWith('1'.repeat(40)) ? baseline : authored};
    if (name.includes('/git/blobs/')) return structuredClone(blobs.get(name.split('/').at(-1)));
    if (name.includes('/compare/')) return {status: 'identical'};
    if (name.endsWith('/artifacts')) return {total_count: 1, artifacts: [{id: 1, name: 'geo'}]};
    throw Error(`Unexpected route ${route}`);
  };
  f.options = () => ({api: memoizeImmutableGitBlobs(f.api), repo, number: 23, expectedHead: head,
    policy: {version: 1, mode: 'enforce-new', activation_time: '2026-01-01T00:00:00Z'}, testedBase: base,
});
  f.complete = (extra = {}) => completeIntegration({...f.options(), integrationResult: 'success',
    geographyResult: 'success', testedCandidate: f.candidate,
    geographyReportLoader: async () => ({version: 1, method_id: 'worldatlas-trusted-geography-check-v1', baseline_commit: f.base,
      trusted_code_commit: f.base, candidate_commit: f.candidate, candidate_code_executed: false, published: false,
      source_approval: false, gate_status: 'passed', status: 'not-applicable'}), ...extra});
  return f;
}

// A real single-entry stored ZIP exercises the production report loader through
// prepare and final integration; no GIS is executed.
// Real HTTP failures and ETag revalidation, with only the network replaced.
function quotaCompletionFixture({retry = false, refuse = false, headerless = false} = {}) {
  const f = finalMergeFixture(), original = f.api, attempts = [];
  let remaining = 2000, time = 0, retried = false, prReads = 0;
  const headers = () => headerless ? {etag: '"unchanged"'} : ({'x-ratelimit-limit': '2000', 'x-ratelimit-remaining': String(remaining),
    'x-ratelimit-reset': '3600', 'x-ratelimit-resource': 'core', etag: '"unchanged"'});
  f.api = githubAPI('synthetic-quota-token', {readWaitMs: 60000,
    now: () => time, sleep: async ms => {time += ms;}, deadlineRemaining: () => 100000 - time,
    onRequest: row => attempts.push({route: row.route, status: row.status, remaining: row.capacity.remaining}),
    fetchImpl: async (url, init) => {
      const route = url.slice('https://api.github.com'.length), name = route.split('?')[0];
      if (retry && !retried && name.endsWith('/pulls/23')) {
        retried = true; remaining--;
        return Response.json({message: 'secondary rate limit'}, {status: 403,
          headers: {...headers(), 'retry-after': '1'}});
      }
      if (name.endsWith('/pulls/23') && ++prReads === 3 && refuse)
        return Response.json({message: 'Forbidden'}, {status: 403});
      if (init.headers['If-None-Match']) return new Response(null, {status: 304, headers: headers()});
      remaining--;
      const value = await original(route, init.method, init.body ? JSON.parse(init.body) : undefined);
      return Response.json(value, {headers: headers()});
    }});
  return {f, attempts, complete: () => f.complete(), get remaining() {return remaining;}, get prReads() {return prReads;}};
}
for (const retry of [false, true]) test(`actual final HTTP retains conditional authority and response-driven retry: ${retry}`, async t => {
  const q = quotaCompletionFixture({retry}), result = await q.complete();
  assert.equal(result.accepted, true);
  assert(q.attempts.some(row => row.status === 304), 'Authority was actually conditionally reread');
  assert.equal(q.attempts.filter(row => row.status === 403).length, retry ? 1 : 0);
  assert.equal(q.f.writes.filter(row => row.method === 'PUT').length, 1);
  assert(!q.attempts.some(row => row.route === '/rate_limit' || row.route === '/repos/o/r'));
  t.diagnostic(JSON.stringify({actual_http_attempts: q.attempts.length,
    conditional_revalidations: q.attempts.filter(row => row.status === 304).length,
    retry_rejections: q.attempts.filter(row => row.status === 403).length}));
});
test('actual final authority stops on a real current-PR HTTP refusal', async () => {
  const q = quotaCompletionFixture({refuse: true});
  await assert.rejects(q.complete(), error => error.github?.http_status === 403);
  assert.equal(q.prReads, 3, 'The final current PR reread actually refused');
  assert.equal(q.f.writes.length, 0);
});

test('actual final completion accepts successful responses without forecast headers', async () => {
  const q = quotaCompletionFixture({headerless: true});
  assert.equal((await q.complete()).accepted, true);
  assert.equal(q.f.writes.filter(row => row.method === 'PUT').length, 1);
  assert(q.attempts.some(row => row.status === 304));
});

}

test('changed checker uses fresh candidate science and cannot accept a baseline-only report', async () => {
 const make = () => {
  const f = fixture(), original = f.api;
  const filename = 'scripts/check-geographic-regression.py';
  f.authored[0].path = filename; f.integrated[0].path = filename;
  f.api = async (route, ...args) => route.includes('/pulls/2/files')
    ? [{filename, status: 'modified'}] : original(route, ...args);
  return f;
 };
 const softwareReport = f => ({version: 1, method_id: 'worldatlas-trusted-geography-check-v1',
  baseline_commit: f.base, candidate_commit: f.candidate, trusted_code_commit: f.candidate,
  trusted_code_inventory_sha256: 'd'.repeat(64), candidate_code_executed: true,
  published: false, source_approval: false, gate_status: 'passed', status: 'not-applicable'});
 const f = make();
 assert.equal((await prepareIntegration(f.options())).geography_software, true);
 await assert.rejects(f.complete(), /exact trusted combined check/);
 assert.equal(f.writes.length, 0);
 const result = await f.complete({geographyReportLoader: async () => softwareReport(f)});
 assert.equal(result.geography.trusted_code_commit, f.candidate);
 assert.equal(result.tested_base, f.base);
 assert.equal(f.writes.length, 1);
 const unrelated = fixture();
 await assert.rejects(unrelated.complete({geographyReportLoader: async () => softwareReport(unrelated)}), /exact trusted combined check/);
 assert.equal(unrelated.writes.length, 0);
});

test('actual queue validates simultaneous final-map and checker edits with accepted main code', async () => {
 const f=fixture(),original=f.api;
 const paths=['scripts/check-geographic-regression.py','data/canonical-grid/current-startup/index.json'];
 for(const filename of paths){
  f.baseline.push({path:filename,sha:'before-'+filename,mode:'100644',type:'blob'});
  f.authored.push({path:filename,sha:'after-'+filename,mode:'100644',type:'blob'});
  f.integrated.push({path:filename,sha:'after-'+filename,mode:'100644',type:'blob'});
 }
 f.pr.changed_files=3;
 f.api=async(route,...args)=>route.includes('/pulls/2/files')
  ? ['src/a.js',...paths].map(filename=>({filename,status:'modified'})):original(route,...args);
 const prepared=await prepareIntegration(f.options());
 assert.equal(prepared.geography_required,true);
 assert.equal(prepared.geography_software,false);
 await assert.rejects(f.complete({geographyReportLoader:async()=>({version:1,method_id:'worldatlas-trusted-geography-check-v1',
  baseline_commit:f.base,candidate_commit:f.candidate,trusted_code_commit:f.candidate,
  trusted_code_inventory_sha256:'d'.repeat(64),candidate_code_executed:true,
  published:false,source_approval:false,gate_status:'passed',status:'not-applicable'})}),/exact trusted combined check/);
 assert.equal(f.writes.length,0);
 const result=await f.complete();
 assert.equal(result.geography.trusted_code_commit,f.base);
 assert.equal(result.tested_base,f.base);
 assert.equal(f.writes.length,1);
});

test('workflow candidate geography is selected by trusted profile output without credentials', () => {
 for (const [file, selector, candidate, baseline] of [
  ['worker-merge.yml', 'prepare', 'needs.prepare.outputs.candidate', 'needs.prepare.outputs.base']
 ]) {
  const source = fs.readFileSync('.github/workflows/' + file, 'utf8');
  const job = source.match(/\n  geography:\n([\s\S]*?)(?=\n  [a-z][a-z-]*:|$)/)[1];
  const expression = `\${{ (needs.${selector}.outputs.geography_software == 'true') && ${candidate} || ${baseline} }}`;
  assert.ok(job.includes('ref: ' + expression));
  assert.ok(job.includes('GEOGRAPHY_CODE_COMMIT: ' + expression));
  assert.ok(job.includes(`GH_TOKEN: \${{ !(needs.${selector}.outputs.geography_software == 'true') && github.token || '' }}`));
  assert.match(job, /persist-credentials: false/);
  assert.match(job, /GIT_CONFIG_GLOBAL: \/dev\/null/);
  assert.doesNotMatch(job, /secrets\.|contents: write|issues: write|pull-requests: write|id-token:/);
 }
});


test('focused Python controls follow their actual paired Node wrapper without a separate filename roster',()=>{
 const child='test/source-cohort.test.py',wrapper='test/source-cohort.test.mjs';
 const row={type:'blob',mode:'100644',sha:'a'.repeat(40)},tree=new Map([[child,row],[wrapper,row]]);
 for(const status of ['added','modified'])assert.equal(integrationProfile('engineering/tests',[{filename:child,status}],{},tree),'evidence');
 tree.delete(wrapper);assert.equal(integrationProfile('engineering/tests',[{filename:child,status:'added'}],{},tree),'full');
 tree.delete(child);assert.equal(integrationProfile('engineering/tests',[{filename:child,status:'removed'}],{},tree),'evidence');
});


test('successful original build archive is retained before later tests without relaxing acceptance',()=>{
 const yaml=fs.readFileSync(new URL('../.github/workflows/worker-merge.yml',import.meta.url),'utf8');
 const integration=yaml.split('\n  integration:\n')[1].split('\n  merge:\n')[0];
 const steps=integration.split(/\n(?=      - )/).slice(1);
 const at=name=>steps.findIndex(step=>step.startsWith('      - name: '+name+'\n'));
 const snapshot=at('Snapshot original final-worker package inputs'),
  build=at('Build the combined application once before asset-dependent tests'),
  inventory=at('Inventory original final-worker package output'),
  retain=at('Retain original final-worker package output'),
  browser=at('Install browser dependencies only for tests that use Playwright'),
  tests=at('Test applicable combined-tree invariants without publishing or live imports');
 assert(snapshot>=0);assert.equal(build,snapshot+1);assert.equal(inventory,build+1);
 assert.equal(retain,inventory+1,'Capture the original bytes before browser setup or tests can fail or mutate them');
 assert(retain<browser&&browser<tests);
 const condition="needs.prepare.outputs.profile == 'full' && matrix.shard == 0 && steps.assembly.outputs.assembled != 'true'";
 for(const index of [snapshot,build,inventory]){
  assert(steps[index].includes('\n        if: '+condition+'\n'));
  assert.doesNotMatch(steps[index],/always\(\)|continue-on-error/);
 }
 assert(steps[retain].includes('\n        if: success() && '+condition+'\n'));
 assert.doesNotMatch(steps[retain],/always\(\)|continue-on-error/);
 assert.match(steps[retain],/uses: actions\/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02/);
 assert.match(steps[retain],/if-no-files-found: error/);
 for(const member of ['dist/client/','dist/cloudflare/','.cache/package-output-manifest.json','.cache/package-input-build.json'])
  assert(steps[retain].includes(member));
 assert.match(steps[tests],/node scripts\/run-integration-tests\.mjs/);
 assert.match(yaml,/needs: \[prepare, integration, geography\]/);
 assert.match(yaml,/INTEGRATION_RESULT: \$\{\{ needs\.integration\.result \}\}/);
 assert.match(yaml,/GEOGRAPHY_RESULT: \$\{\{ needs\.geography\.result \}\}/);
});


test('actual preparation completes a truncated candidate tree and refuses incomplete child metadata before scope selection',async()=>{
  for(const incomplete of [false,true]){
    const f=fixture(),original=f.api,root=sha('e'),directory=sha('d'),calls=[];
    f.api=githubAPI('synthetic-tree-token',{fetchImpl:async(url,init)=>{
      const route=new URL(url).pathname+new URL(url).search;calls.push(route);
      let value;
      if(route==='/repos/owner/repo/git/trees/'+root+'?recursive=1')
        value={sha:root,truncated:true,tree:[{path:'ignored-partial',sha:sha('f'),type:'blob',mode:'100644',size:1}]};
      else if(route==='/repos/owner/repo/git/trees/'+root)
        value={sha:root,truncated:false,tree:[{path:'src',sha:directory,type:'tree',mode:'040000'}]};
      else if(route==='/repos/owner/repo/git/trees/'+directory+'?recursive=1')
        value={sha:directory,truncated:false,tree:[{path:incomplete?'missing/a.js':'a.js',sha:sha('a'),type:'blob',mode:'100644',size:7}]};
      else{
        value=await original(route,init.method,init.body?JSON.parse(init.body):undefined);
        if(route==='/repos/owner/repo/git/commits/'+f.candidate)value={...value,tree:{sha:root}};
      }
      return init.method==='DELETE'?new Response(null,{status:204}):Response.json(value);
    }});
    if(incomplete){
      await assert.rejects(prepareIntegration(f.options()),/Incomplete immutable tree parent inventory/);
      assert.equal(f.refs.size,0,'owned candidate is cleaned on incomplete child refusal');
      assert(!calls.some(route=>route.includes('/contents/.github/package-inputs.json')),'no reviewed scope accepted from a partial tree');
    }else{
      const prepared=await prepareIntegration(f.options());
      assert.equal(prepared.candidate_tree,root);assert.equal(prepared.candidate,f.candidate);
      assert.equal(prepared.profile,'full');assert.equal(prepared.base,f.base);
    }
    assert.equal(calls.filter(route=>route==='/repos/owner/repo/git/trees/'+root+'?recursive=1').length,1);
    assert(!calls.some(route=>route.includes('/git/blobs/')));
  }
});
