import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {integrationProof, PROOF_PATHS, WORKFLOW_PATH, successfulGeographyJob} from '../scripts/integration-proof.mjs';
import {integrationProfile, COORDINATION_PATHS} from '../scripts/integration-profile.mjs';

function fixture(profile = 'full') {
  const workflow='ref: ${{ github.event.pull_request.head.sha }}\nname: Complete regression shard\nname: Build hosted assets';
  const workflowRaw=Buffer.from(workflow), workflowOID=createHash('sha1').update(`blob ${workflowRaw.length}\0`).update(workflowRaw).digest('hex');
  const entries = new Map(PROOF_PATHS.map(path=>[path,{sha:path===WORKFLOW_PATH?workflowOID:path,mode:'100644',type:'blob'}]));
  const tree = {object:{tree:{sha:'exact-complete-tree'}}, entries};
  const run = {id:12,run_attempt:1,head_sha:'head',event:'pull_request',path:WORKFLOW_PATH,
    repository:{full_name:'owner/repo'},head_repository:{full_name:'owner/repo'},
    status:'completed',conclusion:'success',pull_requests:[{number:2,head:{sha:'head'}}]};
  const jobs = [{name:'profile',status:'completed',conclusion:'success'},
    ...(profile === 'full' ? [0,1,2] : [0]).map(shard=>({name:`regression (${shard})`,status:'completed',conclusion:'success',
      steps:['Checkout reviewed head','Install browser dependencies only for tests that use Playwright','Complete regression shard',
        ...(profile==='full'?['Install Node dependencies','Install Python dependencies',...(shard===0?['Build hosted assets','Verify full-regression package controls','Read back qualified native build outputs when selected','Verify full-regression package receipt','Retain full-regression package receipt']:[])]:[])].map(name=>({name,status:'completed',conclusion:'success'}))})),
    ...(profile === 'full' ? [{name:'package',status:'completed',conclusion:'success',steps:[{name:'Use full-regression package verification',status:'completed',conclusion:'success'}]}] : [])];
  const f = {run,jobs,workflow};
  f.options = {repo:'owner/repo',number:2,head:'head',profile,baseline:tree,authored:structuredClone(tree),candidate:structuredClone(tree),api:async route=>{
    if(route.includes('/git/blobs/')) return {sha:workflowOID,size:Buffer.byteLength(f.workflow),encoding:'base64',content:Buffer.from(f.workflow).toString('base64')};
    if(route.includes('/jobs')) return {jobs:f.jobs};
    if(route.includes('/actions/runs/12')) return f.run;
    if(route.includes('/actions/workflows/')) return {workflow_runs:[f.run]};
    throw Error(route);
  }};
  return f;
}
test('successful full and focused workflows prove exact tree and pinned current attempt', async()=>{
  for(const profile of ['full','evidence']) {
    const f=fixture(profile);
    const proof=await integrationProof(f.options);
    assert.deepEqual(proof,{run_id:12,run_attempt:1,tree:'exact-complete-tree',profile});
    assert.deepEqual(await integrationProof({...f.options,runId:12,runAttempt:1}),proof);
  }
});
test('geography reuse requires one actual successful producer and every trusted step', async () => {
  const geography = {id: 44, name: 'geography', status: 'completed', conclusion: 'success', steps: [
    'Checkout trusted geographic checker', 'Install trusted geographic dependencies',
    'Check proposed geography with trusted baseline code',
    'Run actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02'
  ].map(name => ({name, status: 'completed', conclusion: 'success'}))};
  const f = fixture(); f.jobs.push(geography);
  assert.equal((await integrationProof(f.options)).geography_job_id, 44);
  for (const mutate of [job => {job.id = 0;}, job => {job.status = 'in_progress';},
    job => {job.conclusion = 'failure';}, job => {job.steps.pop();},
    job => {job.steps[2].conclusion = 'skipped';}, job => {job.steps.push({...job.steps[2]});}]) {
    const job = structuredClone(geography); mutate(job); assert.equal(successfulGeographyJob([job]), null);
  }
  assert.equal(successfulGeographyJob([geography, structuredClone(geography)]), null);
  f.jobs.push(structuredClone(geography));
  assert.equal((await integrationProof(f.options)).geography_job_id, undefined,
    'unusable geography must not discard valid application proof; a fresh geography job remains required');
});
function failOnlyEvidence(f) {
  f.run.conclusion = 'failure';
  f.jobs.push({name:'evidence',status:'completed',conclusion:'failure'},
    ...['scope','geography','package'].filter(name=>!f.jobs.some(job=>job.name===name)).map(name=>({name,status:'completed',conclusion:'success'})));
  return f;
}
test('evidence-only failure reuses successful exact-tree code jobs for both profiles and pinned final reads', async()=>{
  for (const profile of ['full','evidence']) {
    const f=failOnlyEvidence(fixture(profile));
    const proof=await integrationProof(f.options);
    assert.deepEqual(proof,{run_id:12,run_attempt:1,tree:'exact-complete-tree',profile});
    assert.deepEqual(await integrationProof({...f.options,runId:12,runAttempt:1}),proof);
  }
});
test('later metadata-only runs do not hide an earlier completed code proof', async()=>{
  const f=failOnlyEvidence(fixture()), api=f.options.api, calls=[];
  const metadata={...f.run,id:13,conclusion:'success'};
  f.options.api=async route=>{
    calls.push(route);
    if (route.includes('/actions/workflows/')) return {workflow_runs:[metadata,f.run]};
    if (route.includes('/actions/runs/13/')) return {jobs:[{name:'profile',status:'completed',conclusion:'success'},
      {name:'regression',status:'completed',conclusion:'skipped'}]};
    return api(route);
  };
  assert.equal((await integrationProof(f.options)).run_id,12);
  assert.ok(calls.some(route=>route.includes('/runs/12/attempts/1/jobs')));
});
test('evidence-only exception refuses failed, skipped, missing or incomplete code and science', async()=>{
  for (const name of ['profile','scope','geography','package','regression (0)','regression (1)','regression (2)']) {
    for (const outcome of ['failure','cancelled','skipped','neutral','missing','in_progress']) {
      const f=failOnlyEvidence(fixture());
      if (outcome==='missing') f.jobs=f.jobs.filter(job=>job.name!==name);
      else if (outcome==='in_progress') f.jobs.find(job=>job.name===name).status=outcome;
      else f.jobs.find(job=>job.name===name).conclusion=outcome;
      assert.equal(await integrationProof(f.options),null,`${name}: ${outcome}`);
    }
  }
  for (const mutate of [
    f=>f.jobs.find(job=>job.name==='regression (0)').steps.pop(),
    f=>f.jobs.find(job=>job.name==='regression (1)').steps[0].conclusion='skipped',
    f=>f.jobs.find(job=>job.name==='evidence').status='in_progress',
    f=>f.jobs.find(job=>job.name==='evidence').conclusion='success',
    f=>f.jobs.push({name:'other-science',status:'completed',conclusion:'failure'}),
    f=>f.jobs.push({name:'evidence',status:'completed',conclusion:'failure'})
  ]) {
    const f=failOnlyEvidence(fixture());mutate(f);assert.equal(await integrationProof(f.options),null);
  }
});
test('evidence-only failure cannot relax tested tree, workflow identity or pinned attempt', async()=>{
  for (const mutate of [
    f=>f.options.candidate.object.tree.sha='changed-tree',
    f=>f.options.authored.entries.get(WORKFLOW_PATH).sha='changed-workflow',
    f=>f.run.run_attempt=2,
    f=>f.run.status='in_progress',
    f=>f.run.conclusion='cancelled'
  ]) {
    const f=failOnlyEvidence(fixture());mutate(f);
    assert.equal(await integrationProof({...f.options,runId:12,runAttempt:1}),null);
  }
});
test('head metadata without explicit reviewed-head checkout never proves tested tree', async()=>{
  const f=fixture();f.workflow='name: Complete regression shard\nname: Build hosted assets';
  assert.equal(await integrationProof(f.options),null);
});
test('different complete tree or modified approved workflow/runner always falls back', async()=>{
  for(const path of PROOF_PATHS) {
    const f=fixture();f.options.authored.entries.get(path).sha='author-modification';
    assert.equal(await integrationProof(f.options),null);
  }
  const f=fixture();f.options.candidate.object.tree.sha='different-main-tree';
  assert.equal(await integrationProof(f.options),null);
});
test('wrong head/event/repository/PR/path and incomplete or failed run cannot prove coverage', async()=>{
  for(const delta of [{head_sha:'stale'},{event:'push'},{path:'.github/workflows/other.yml'},
    {repository:{full_name:'other/repo'}},{head_repository:{full_name:'fork/repo'}},
    {pull_requests:[]},{status:'in_progress'},{conclusion:'cancelled'},{conclusion:'failure'}]) {
    const f=fixture();Object.assign(f.run,delta);assert.equal(await integrationProof(f.options),null);
  }
});
test('missing/extra shard and skipped or incomplete required steps never count as successful coverage', async()=>{
  for(const mutate of [f=>f.jobs.pop(), f=>f.jobs.push({...f.jobs[1],name:'regression (3)'}),
    f=>f.jobs[1].conclusion='skipped', f=>f.jobs[1].steps.pop(),
    f=>f.jobs[1].steps.at(-1).conclusion='skipped',
    f=>f.jobs[1].steps.find(step=>step.name.includes('browser')).conclusion='skipped', f=>f.jobs[2].steps.at(-1).status='in_progress',
    f=>f.jobs[0].conclusion='failure']) {
    const f=fixture();mutate(f);assert.equal(await integrationProof(f.options),null);
  }
});
test('final pinned run reread rejects revoked proof', async()=>{
  const f=fixture();assert.ok(await integrationProof(f.options));f.run.conclusion='cancelled';
  assert.equal(await integrationProof({...f.options,runId:12,runAttempt:1}),null);
});
test('explicit coordination allowlist defaults full for unknown/application/data/schema/import/deploy/rename impact',()=>{
  for(const filename of COORDINATION_PATHS) assert.equal(integrationProfile('engineering/job',[{filename}]),'evidence',filename);
  for(const filename of ['src/attributes.js','hosted/a.mjs','drizzle/0001.sql','data/hierarchy.json',
    'scripts/import.mjs','scripts/build-hosted.mjs','docs/unknown.json',
    '.github/workflows/deploy.yml','test/application.test.mjs']) {
    assert.equal(integrationProfile('engineering/job',[{filename}]),'full',filename);
    assert.equal(integrationProfile('engineering/job',[{filename:'docs/WORKER_COORDINATION.md',previous_filename:filename}]),'full',filename);
  }
  assert.equal(integrationProfile('engineering/job',[{filename:'docs/prompts/reviewer.md'}]),'evidence');
  assert.equal(integrationProfile('engineering/job',[]),'full');
});

test('final proof pins attempt and refuses a later successful rerun or missing/invalid attempt', async()=>{
  const f=fixture();const proof=await integrationProof(f.options);assert.equal(proof.run_attempt,1);
  f.run.run_attempt=2;
  assert.equal(await integrationProof({...f.options,runId:12,runAttempt:proof.run_attempt}),null);
  for(const runAttempt of [undefined,0,-1,1.5,'1',NaN])
    assert.equal(await integrationProof({...fixture().options,runId:12,runAttempt}),null);
});

test('focused proof accepts complete controls without installing Node dependencies', async()=>{
  const f=fixture('evidence');
  assert.ok(!f.jobs[1].steps.some(step=>step.name==='Install Node dependencies'));
  assert.ok(await integrationProof(f.options));
  f.jobs[1].steps.push({name:'Install Node dependencies',status:'completed',conclusion:'skipped'});
  assert.ok(await integrationProof(f.options));
});
test('full proof refuses missing, failed, cancelled or skipped Node installation in any shard', async()=>{
  for(const shard of [0,1,2]) for(const conclusion of ['missing','failure','cancelled','skipped']) {
    const f=fixture();const job=f.jobs.find(job=>job.name===`regression (${shard})`);
    if(conclusion==='missing') job.steps=job.steps.filter(step=>step.name!=='Install Node dependencies');
    else job.steps.find(step=>step.name==='Install Node dependencies').conclusion=conclusion;
    assert.equal(await integrationProof(f.options),null);
  }
});

// Exercise the actual PR CI caller, not just the pure classifier. Omitting its
// issue-owned scope previously forced every geography PR to full regression.
import {selectIntegrationProfile} from '../scripts/check-integration-profile.mjs';
function geographyProfileFixture() {
  const repo = 'owner/repo', prefix = `/repos/${repo}`;
  const branch = 'geography/regional-review-example', owned = 'data/regional-review/regional-review-example/';
  const spec = {max_prs:2, depends_on:[], mode:'geography', scope:'Inspect exact retained source subjects', owned_paths:[owned]};
  const issue = {number:472,state:'open',labels:['type:geography','kind:work-item','status:ready'],
    body:'<!-- worldatlas-work:v1\n'+JSON.stringify(spec)+'\n-->'};
  const pr = {number:814,state:'open',head:{sha:'a'.repeat(40),ref:branch},base:{repo:{full_name:repo}},body:'Closes #472',changed_files:1};
  const event = {repository:{full_name:repo},pull_request:structuredClone(pr)};
  const files = [{filename:owned+'reproduction/findings.json',status:'added'}], calls = [];
  const f = {repo,prefix,spec,issue,pr,event,files,calls};
  f.api = async route => {
    calls.push(route);
    if (route === prefix+'/pulls/814') return structuredClone(pr);
    if (route === prefix+'/pulls/814/files?per_page=100&page=1') return structuredClone(files);
    if (route === prefix+'/issues/472') return {...structuredClone(issue),body:'<!-- worldatlas-work:v1\n'+JSON.stringify(spec)+'\n-->'};
    throw Error('Unexpected API request '+route);
  };
  return f;
}
const select = f => selectIntegrationProfile({event:f.event,repo:f.repo,api:f.api});
test('actual PR selector passes verified geography ownership and selects one evidence shard', async()=>{
  const f=geographyProfileFixture();assert.deepEqual(await select(f),{profile:'evidence',shards:[0]});
  assert.ok(f.calls.includes(f.prefix+'/issues/472'));
  assert.equal(f.calls.some(route=>/comments|timeline/.test(route)),false);
});
for (const [label,change] of [
  ['wrong issue',f=>f.issue.number=473],
  ['wrong lane',f=>f.issue.labels[0]='type:engineering'],['closed issue',f=>f.issue.state='closed'],
  ['wrong mode',f=>f.spec.mode='engineering'],
  ['unsafe prefixes',f=>f.spec.owned_paths=['data/']],
  ['stale PR head',f=>f.pr.head.sha='b'.repeat(40)],
  ['incomplete file list',f=>f.pr.changed_files=2],
  ['duplicate file inventory',f=>{f.files.push({...f.files[0]});f.pr.changed_files=2;}],
  ['missing issue reference',f=>f.pr.body='No issue']
]) test('actual PR selector rejects '+label,async()=>{const f=geographyProfileFixture();change(f);await assert.rejects(()=>select(f));});
test('ordinary geography profile follows current owned scope without readiness labels',async()=>{
  const f=geographyProfileFixture();f.issue.labels.push('status:blocked');
  assert.deepEqual(await select(f),{profile:'evidence',shards:[0]});
  f.spec.owned_paths=['research/geography/another/'];
  assert.deepEqual(await select(f),{profile:'full',shards:[0,1,2]});
});
test('actual PR selector defaults full for files and rename origins outside geography scope',async()=>{
  for(const file of [{filename:'src/attributes.js'},{filename:'data/regional-review/another/findings.json'},
    {filename:'data/regional-review/regional-review-example/renamed.json',previous_filename:'src/attributes.js'}]){
    const f=geographyProfileFixture();f.files[0]=file;assert.deepEqual(await select(f),{profile:'full',shards:[0,1,2]});
  }
});
test('geography scope read paginates all changed files without canonical comments',async()=>{
  const f=geographyProfileFixture(),api=f.api;
  const rows=Array.from({length:101},(_,i)=>({filename:f.spec.owned_paths[0]+i+'.json'}));f.pr.changed_files=101;
  f.api=async route=>{
    if(route.includes('/files?'))return rows.slice(route.endsWith('page=1')?0:100,route.endsWith('page=1')?100:101);
    return api(route);
  };
  assert.deepEqual(await select(f),{profile:'evidence',shards:[0]});
});
test('non-geography selectors preserve existing profiles without requesting geography ownership',async()=>{
  for(const [branch,filename,profile] of [
    ['engineering/example','docs/WORKER_COORDINATION.md','evidence'],
    ['engineering/example','src/attributes.js','full'],
    ['research/example','research/campaigns/example/sources.json','evidence']
  ]){
    const f=geographyProfileFixture();f.pr.head.ref=branch;f.event.pull_request.head.ref=branch;f.files[0]={filename};
    assert.equal((await select(f)).profile,profile);assert.equal(f.calls.some(route=>route.includes('/issues/')),false);
  }
});

// Package selection is a coordination control. Exercise its focused contracts
// when the runner omits application regression; full discovery runs that file
// separately, so do not register the same tests twice in the full profile.
if (process.env.INTEGRATION_PROFILE === 'evidence') await import('./deployment-budget-scope.test.mjs');

test('package CI coordination paths use focused tests while builders and runners stay full', () => {
  for (const filename of ['scripts/classify-deployment-budget.mjs',
    '.github/workflows/deployment-budget.yml', 'test/deployment-budget-scope.test.mjs']) {
    assert.equal(integrationProfile('engineering/example', [{filename}]), 'evidence', filename);
  }
  for (const filename of ['scripts/build-hosted.mjs', 'scripts/build-static.mjs', 'scripts/deployment-budget.mjs',
    'scripts/package-inputs.mjs', 'scripts/package-build.mjs', '.github/package-inputs.json',
    'scripts/build-cloudflare-inner.mjs', 'test/package-build.test.mjs', 'scripts/run-integration-tests.mjs', 'src/main.js', 'data/hierarchy.json', 'drizzle/0002.sql']) {
    assert.equal(integrationProfile('engineering/example', [{filename}]), 'full', filename);
  }
  assert.equal(integrationProfile('engineering/example', [{filename:'scripts/classify-deployment-budget.mjs', previous_filename:'src/main.js'}]), 'full');
});

test('selected-data never discovers or accepts author proof, including historical successful runs', async () => {
  for (const pinned of [false, true]) {
    const f = fixture(); let reason;
    assert.equal(await integrationProof({...f.options, testSelection: 'selected-data',
      ...(pinned ? {runId: 12, runAttempt: 1} : {}),
      api: () => assert.fail('Selected-data has no author computation to discover'),
      onUnavailable: value => {reason = value.reason;}}), null);
    assert.equal(reason, 'selected-data-requires-final-candidate');
  }
  assert.equal(await integrationProof({...fixture('evidence').options, testSelection: 'selected-data'}), null);
});

test('proof fallback reports existing allowlisted decisions without extra requests',async()=>{
  for(const [reason,mutate] of [
    ['tested-tree-mismatch',f=>f.options.candidate.object.tree.sha='different'],
    ['trusted-checker-identity-changed',f=>f.options.authored.entries.get(PROOF_PATHS[1]).sha='different'],
    ['run-identity-or-state',f=>f.run.run_attempt=2],
    ['required-code-job-or-step',f=>f.jobs[1].steps.pop()]]){
    const f=fixture();mutate(f);let observed;const calls=[];const api=f.options.api;
    const proof=await integrationProof({...f.options,runId:12,runAttempt:1,api:async route=>{calls.push(route);return api(route);},onUnavailable:value=>{observed=value;}});
    assert.equal(proof,null);assert.deepEqual(observed,{reason});assert(calls.length<=3);
  }
});


test('full package proof binds every producer control, readback, receipt and status consumer', async () => {
  const producer = ['Verify full-regression package controls', 'Read back qualified native build outputs when selected',
    'Verify full-regression package receipt', 'Retain full-regression package receipt'];
  for (const name of [...producer, 'Use full-regression package verification']) for (const outcome of ['failure','cancelled','skipped','missing','duplicate','in_progress']) {
    const f = fixture(), job = f.jobs.find(job => job.name === (producer.includes(name) ? 'regression (0)' : 'package'));
    const step = job.steps.find(step => step.name === name);
    if (outcome === 'missing') job.steps = job.steps.filter(row => row !== step);
    else if (outcome === 'duplicate') job.steps.push({...step});
    else if (outcome === 'in_progress') step.status = outcome;
    else step.conclusion = outcome;
    assert.equal(await integrationProof(f.options), null, name + '/' + outcome);
  }
  for (const outcome of ['failure','cancelled','skipped','missing','duplicate']) {
    const f=fixture(), job=f.jobs.find(job=>job.name==='package');
    if(outcome==='missing')f.jobs=f.jobs.filter(row=>row!==job);
    else if(outcome==='duplicate')f.jobs.push({...job});
    else job.conclusion=outcome;
    assert.equal(await integrationProof(f.options),null,outcome);
  }
});
