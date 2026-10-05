import test from 'node:test';
import assert from 'node:assert/strict';
import {integrationProof, PROOF_PATHS, WORKFLOW_PATH} from '../scripts/integration-proof.mjs';
import {integrationProfile, COORDINATION_PATHS} from '../scripts/integration-profile.mjs';

function fixture(profile = 'full') {
  const entries = new Map(PROOF_PATHS.map(path=>[path,{sha:path,mode:'100644',type:'blob'}]));
  const tree = {object:{tree:{sha:'exact-complete-tree'}}, entries};
  const run = {id:12,run_attempt:1,head_sha:'head',event:'pull_request',path:WORKFLOW_PATH,
    repository:{full_name:'owner/repo'},head_repository:{full_name:'owner/repo'},
    status:'completed',conclusion:'success',pull_requests:[{number:2,head:{sha:'head'}}]};
  const jobs = [{name:'profile',status:'completed',conclusion:'success'},
    ...(profile === 'full' ? [0,1,2] : [0]).map(shard=>({name:`regression (${shard})`,status:'completed',conclusion:'success',
      steps:['Checkout reviewed head','Install browser dependencies only for tests that use Playwright','Complete regression shard',
        ...(profile==='full'?['Install Node dependencies','Install Python dependencies',...(shard===0?['Build hosted assets']:[])]:[])].map(name=>({name,status:'completed',conclusion:'success'}))}))];
  const f = {run,jobs,workflow:'ref: ${{ github.event.pull_request.head.sha }}\nname: Complete regression shard\nname: Build hosted assets'};
  f.options = {repo:'owner/repo',number:2,head:'head',profile,baseline:tree,authored:structuredClone(tree),candidate:structuredClone(tree),api:async route=>{
    if(route.includes('/git/blobs/')) return {content:Buffer.from(f.workflow).toString('base64')};
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
// reservation argument previously forced every geography PR to full regression.
import {selectIntegrationProfile} from '../scripts/check-integration-profile.mjs';
function geographyProfileFixture() {
  const repo = 'owner/repo', prefix = `/repos/${repo}`, now = Date.parse('2026-10-04T20:00:00Z');
  const branch = 'geography/regional-review-example', owned = 'data/regional-review/regional-review-example/';
  const claim = {version:1, active:true, issue_number:472, worker_id:'geo-worker',
    claim_id:'unique-claim', branch, mode:'geography', expires_at:new Date(now + 3600000).toISOString(), owned_paths:[owned]};
  const spec = {max_prs:2, depends_on:[], mode:'geography', scope:'Inspect exact retained source subjects', owned_paths:[owned]};
  const issue = {number:472,state:'open',labels:['type:geography','kind:work-item','status:ready'],
    body:'<!-- worldatlas-work:v1\n'+JSON.stringify(spec)+'\n-->'};
  const pr = {number:814,state:'open',head:{sha:'a'.repeat(40),ref:branch},base:{repo:{full_name:repo}},body:'Closes #472',changed_files:1};
  const event = {repository:{full_name:repo},pull_request:structuredClone(pr)};
  const files = [{filename:owned+'reproduction/findings.json',status:'added'}], calls = [];
  const comments = () => [{id:1,user:{login:'github-actions[bot]'},body:'**Worker reservation:** claimed\n\n<!-- worldatlas-claim:v1\n'+JSON.stringify(claim)+'\n-->'}];
  const f = {repo,prefix,now,claim,spec,issue,pr,event,files,calls,comments};
  f.api = async route => {
    calls.push(route);
    if (route === prefix+'/pulls/814') return structuredClone(pr);
    if (route === prefix+'/pulls/814/files?per_page=100&page=1') return structuredClone(files);
    if (route === prefix+'/issues/472') return {...structuredClone(issue),body:'<!-- worldatlas-work:v1\n'+JSON.stringify(spec)+'\n-->'};
    if (route === prefix+'/issues/472/comments?per_page=100&page=1') return f.comments();
    throw Error('Unexpected API request '+route);
  };
  return f;
}
const select = f => selectIntegrationProfile({event:f.event,repo:f.repo,api:f.api,now:f.now});
test('actual PR selector passes verified geography ownership and selects one evidence shard', async()=>{
  const f=geographyProfileFixture();assert.deepEqual(await select(f),{profile:'evidence',shards:[0]});
  assert.ok(f.calls.includes(f.prefix+'/issues/472/comments?per_page=100&page=1'));
});
for (const [label,change] of [
  ['missing claim',f=>f.comments=()=>[]],['released claim',f=>f.claim.active=false],
  ['expired claim',f=>f.claim.expires_at=new Date(f.now).toISOString()],
  ['wrong branch',f=>f.claim.branch='geography/another'],['wrong issue',f=>f.claim.issue_number=473],
  ['wrong lane',f=>f.claim.mode='engineering'],['closed issue',f=>f.issue.state='closed'],
  ['blocked issue',f=>f.issue.labels.push('status:blocked')],
  ['changed owned scope',f=>f.spec.owned_paths=['research/geography/another/']],
  ['unsafe prefixes',f=>{f.spec.owned_paths=['data/'];f.claim.owned_paths=['data/'];}],
  ['stale PR head',f=>f.pr.head.sha='b'.repeat(40)],
  ['incomplete file list',f=>f.pr.changed_files=2],
  ['duplicate file inventory',f=>{f.files.push({...f.files[0]});f.pr.changed_files=2;}],
  ['missing issue reference',f=>f.pr.body='No issue']
]) test('actual PR selector rejects '+label,async()=>{const f=geographyProfileFixture();change(f);await assert.rejects(()=>select(f));});
test('actual PR selector defaults full for files and rename origins outside geography scope',async()=>{
  for(const file of [{filename:'src/attributes.js'},{filename:'data/regional-review/another/findings.json'},
    {filename:'data/regional-review/regional-review-example/renamed.json',previous_filename:'src/attributes.js'}]){
    const f=geographyProfileFixture();f.files[0]=file;assert.deepEqual(await select(f),{profile:'full',shards:[0,1,2]});
  }
});
test('geography ownership read paginates canonical comments and changed files',async()=>{
  const f=geographyProfileFixture(),api=f.api;
  const rows=Array.from({length:101},(_,i)=>({filename:f.claim.owned_paths[0]+i+'.json'}));f.pr.changed_files=101;
  f.api=async route=>{
    if(route.includes('/files?'))return rows.slice(route.endsWith('page=1')?0:100,route.endsWith('page=1')?100:101);
    if(route.includes('/comments?'))return route.endsWith('page=1')?Array.from({length:100},()=>({user:{login:'untrusted'},body:'No canonical ownership'})):f.comments();
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
  for (const filename of ['scripts/classify-deployment-budget.mjs', 'scripts/package-research-inputs.mjs',
    '.github/workflows/deployment-budget.yml', 'test/deployment-budget-scope.test.mjs']) {
    assert.equal(integrationProfile('engineering/example', [{filename}]), 'evidence', filename);
  }
  for (const filename of ['scripts/build-hosted.mjs', 'scripts/build-static.mjs', 'scripts/deployment-budget.mjs',
    'scripts/run-integration-tests.mjs', 'src/main.js', 'data/hierarchy.json', 'drizzle/0002.sql']) {
    assert.equal(integrationProfile('engineering/example', [{filename}]), 'full', filename);
  }
  assert.equal(integrationProfile('engineering/example', [{filename:'scripts/classify-deployment-budget.mjs', previous_filename:'src/main.js'}]), 'full');
});
