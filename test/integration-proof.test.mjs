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
      steps:['Checkout reviewed head','Install Node dependencies','Install browser dependencies only for tests that use Playwright','Complete regression shard',
        ...(profile==='full'?['Install Python dependencies',...(shard===0?['Build hosted assets']:[])]:[])].map(name=>({name,status:'completed',conclusion:'success'}))}))];
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
