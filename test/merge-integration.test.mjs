import {crc32} from 'node:zlib';
import {execFileSync} from 'node:child_process';
import {gitBlobTransport} from '../scripts/git-blob-transport.mjs';
import {memoizeImmutableGitBlobs} from '../scripts/immutable-git-blobs.mjs';
import {loadGeographicReport, prepareGeographyProof, reportHash} from '../scripts/geographic-report-artifact.mjs';
import {sha256, subjectsHash} from '../scripts/evidence-quality.mjs';
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import os from 'node:os';
import path from 'node:path';
import {integrationTestFiles, integrationNeedsBrowser, prepareIntegrationTests} from '../scripts/run-integration-tests.mjs';
import {PROOF_PATHS, WORKFLOW_PATH} from '../scripts/integration-proof.mjs';
import {renderClaim, githubAPI} from '../scripts/issue-claim-contract.mjs';
import {prepareIntegration, completeIntegration, checkCurrentChecks, integrationProfile, createCandidate, cleanupCandidate, cleanupMergedHead} from '../scripts/merge-integration.mjs';

const sha = letter => letter.repeat(40);
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
function fixture() {
  const repo = 'owner/repo', head = sha('a'), base = sha('b'), candidate = sha('c');
  const issue = {number: 1, state: 'open', created_at: '2026-10-03T00:00:00Z', labels: ['type:engineering','kind:work-item','status:ready'],
    body: '<!-- worldatlas-work:v1\n'+JSON.stringify({mode:'engineering',max_prs:3,depends_on:[],scope:'code'})+'\n-->'};
  const pr = {number: 2, state: 'open', draft: false, body: 'Closes #1', title: 'Repair code', changed_files: 1,
    head: {sha: head, ref: 'engineering/test', repo: {full_name: repo}}, base: {ref:'main',sha:base},
    mergeable: true, merge_commit_sha: candidate};
  const claim = {version: 1, active: true, worker_id: 'worker', claim_id: 'nonce', branch:pr.head.ref,
    expires_at: new Date(Date.now()+3600000).toISOString()};
  const f = {repo, pr, issue, head, base, candidate, claim, writes: [], mainReads: 0,
    checks: [{id:1, name:'scope',app:{id:1},status:'completed',conclusion:'success'}],
    authored: [{path:'src/a.js',sha:'blob-a',mode:'100644',type:'blob'}],
    integrated: [{path:'src/a.js',sha:'blob-a',mode:'100644',type:'blob'}]};
  f.api = async (route, method='GET', body) => {
    const p=route.split('?')[0].replace('/repos/'+repo, '');
    if (method==='PUT') {f.writes.push(body);return {merged:true,sha:sha('f')};}
    if (p==='/pulls/2') return structuredClone(f.pr);
    if (p==='/issues/1') return structuredClone(f.issue);
    if (p==='/issues/1/comments') return [{id:1,user:{login:'github-actions[bot]'},body:renderClaim(f.claim)}];
    if (p==='/issues/1/timeline') return [];
    if (p==='/pulls/2/files') return [{filename:'src/a.js',status:'modified'}];
    if (p==='/commits/'+head+'/check-runs') return {check_runs:structuredClone(f.checks)};
    if (p==='/commits/'+head+'/status') {f.statusReads=(f.statusReads??0)+1;return f.failStatusOnRead===f.statusReads ? {statuses:[{}],state:'failure'} : {statuses:[]};}
    if (p==='/git/ref/heads/main') {f.mainReads++;return {object:{sha:f.advanceOnRead===f.mainReads?sha('d'):f.base}};}
    if (p==='/git/commits/'+head) return {tree:{sha:'authored'}};
    if (p==='/git/commits/'+candidate) return {tree:{sha:'integrated'},parents:[{sha:f.parentBase??f.base},{sha:head}]};
    if (p==='/git/trees/authored') return {truncated:false,tree:f.authored};
    if (p==='/git/trees/integrated') return {truncated:f.truncated??false,tree:f.integrated};
    throw Error('Unexpected API '+method+' '+route);
  };
  f.options = () => ({api:f.api,repo,number:2,expectedHead:head,policy:{version:1,mode:'enforce-new',activation_time:'2100-01-01T00:00:00Z'},
    candidateSleep:async()=>{},
    evidenceCheck:async()=>{f.evidenceReads=(f.evidenceReads??0)+1;if(f.staleReview)throw Error('Missing independent exact-head review');return {status:'legacy'};}});
  f.complete = extra => completeIntegration({...f.options(),integrationResult:'success',geographyResult:'success',testedBase:base,testedCandidate:candidate,
    geographyReportLoader:async()=>({version:1,method_id:'worldatlas-trusted-geography-check-v1',
      baseline_commit:f.base,trusted_code_commit:f.base,candidate_commit:extra?.testedCandidate??candidate,candidate_code_executed:false,
      published:false,source_approval:false,gate_status:'passed',status:'not-applicable'}),...extra});
  return f;
}

test('two reviewed PRs sharing a base integrate serially without changing authored head', async () => {
  const a=fixture();await prepareIntegration(a.options());await a.complete();
  const b=fixture();b.base=sha('d');b.pr.base.sha=b.base;
  b.integrated.push({path:'src/other.js',sha:'merged-first-pr',mode:'100644',type:'blob'});
  const prepared=await prepareIntegration(b.options());
  assert.equal(prepared.pr.head.sha,b.head);
  await b.complete({testedBase:b.base});assert.equal(b.writes[0].sha,b.head);
  assert.equal(b.writes[0].merge_method,'squash');assert.equal(b.writes[0].commit_title,b.pr.title);
});
test('conflicts and non-conflicting changes to reviewed bytes require intervention', async () => {
  const a=fixture();a.pr.mergeable=false;await assert.rejects(prepareIntegration(a.options()),/conflict/);assert.equal(a.writes.length,0);
  const b=fixture();b.integrated[0].sha='different-reviewed-file';
  await assert.rejects(prepareIntegration(b.options()),/changes reviewed bytes/);assert.equal(b.writes.length,0);
});
test('stale merge object and truncated inventories fail closed', async () => {
  const a=fixture();a.parentBase=sha('e');await assert.rejects(prepareIntegration(a.options()),/bounded refresh/);
  const b=fixture();b.truncated=true;await assert.rejects(prepareIntegration(b.options()),/Incomplete integration tree/);
});
test('stale head, review or issue scope prohibit integration', async () => {
  const a=fixture();a.pr.head.sha=sha('e');await assert.rejects(a.complete(),/head changed/);
  const b=fixture();b.staleReview=true;await assert.rejects(b.complete(),/exact-head review/);
  const c=fixture();c.issue.state='closed';await assert.rejects(c.complete(),/open GitHub issue/);
  assert.equal(a.writes.length+b.writes.length+c.writes.length,0);
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
test('latest failed or pending check replaces old success', () => {
  const good={id:1,name:'scope',app:{id:1},status:'completed',conclusion:'success'};
  assert.throws(()=>checkCurrentChecks([good,{...good,id:2,conclusion:'failure'}]),/trusted scope/);
  assert.throws(()=>checkCurrentChecks([good,{...good,id:2,status:'in_progress',conclusion:null}]),/trusted scope/);
});
test('workflow separates untrusted candidate tests from write credentials and serializes the lifecycle', () => {
  const yaml=fs.readFileSync(new URL('../.github/workflows/worker-merge.yml',import.meta.url),'utf8');
  const integration=yaml.split('  integration:\n')[1].split('  merge:\n')[0];
  assert.match(yaml.split('jobs:')[0],/concurrency:\n  group: worldatlas-main-integrate/);
  assert.doesNotMatch(integration,/concurrency:/);
  assert.match(integration,/permissions:\n      contents: read/);
  assert.doesNotMatch(integration,/GITHUB_TOKEN:|secrets\.|contents: write|issues: write|pull-requests: write/);
  const authenticatedSteps=['Authenticate selected package installer inputs','Assemble unchanged base with current selected output'];
  const tokenSteps=integration.split(/(?=^      - )/m).filter(step=>/^\s+GH_TOKEN:/m.test(step));
  assert.equal(tokenSteps.length,authenticatedSteps.length);
  for(const [index,step] of tokenSteps.entries()){
    assert.ok(step.startsWith('      - name: '+authenticatedSteps[index]+'\n'));
    assert.equal((step.match(/^\s+GH_TOKEN:/gm)||[]).length,1);
    assert.match(step,/GH_TOKEN: \$\{\{ github\.token \}\}/);
    assert.match(step,/SELECTED_PACKAGE_TRUSTED_BASE: \$\{\{ needs\.prepare\.outputs\.base \}\}/);
    assert.match(step,/python3 -I -S -B/);
    assert.match(step,/needs\.prepare\.outputs\.test_selection == 'selected-data'/);
  }
  const steps=integration.split(/\n(?=      - )/).slice(1);
  const credentialSteps=steps.filter(step=>/WORLDATLAS_CHECKOUT_TOKEN:/.test(step));
  assert.equal(credentialSteps.length,2,'read-only acquisition credentials have exactly two trusted consumers');
  for(const step of credentialSteps)assert.match(step,/name: (Authenticate trusted full-checkout bootstrap|Acquire full checkout with authenticated bounded helper)/);
  for(const step of steps.filter(step=>!credentialSteps.includes(step)))assert.doesNotMatch(step,/WORLDATLAS_CHECKOUT_TOKEN:/);
  const verification=steps.filter(step=>/name: Checkout complete candidate for application regression\n/.test(step));
  assert.equal(verification.length,1);assert.match(verification[0],/HEAD\^\{tree\}/);assert.doesNotMatch(verification[0],/uses: actions\/checkout/);
  assert.match(credentialSteps[0],/CI_CHECKOUT_BASE: \$\{\{ needs.prepare.outputs.base \}\}/);
  assert.doesNotMatch(credentialSteps[0],/github.workflow_sha/);
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
 assert.equal(integrationProfile('engineering/example',[{filename:'docs/WORKER_COORDINATION.md'},{filename:'coordination/engineering/example/receipt.json'}],{}),'evidence');
 for(const filename of ['src/attributes.js','data/hierarchy.json','drizzle/0001.sql','scripts/build-hosted.mjs'])
   assert.equal(integrationProfile('engineering/example',[{filename}],{}),'full');
 assert.equal(integrationProfile('engineering/example',[{filename:'docs/a.md',previous_filename:'src/attributes.js'}],{}),'full');
 assert.equal(integrationProfile('engineering/example',[{filename:'coordination/engineering/other/receipt.json'}],{}),'full');
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

test('ordinary selected data retains CPU base checks while software and explicit output proof retain browser qualification', () => {
 assert.deepEqual(integrationTestFiles('full',0,'selected-data'),
   ['test/canonical-compact-repack.test.mjs','test/prepared-parity.test.mjs']);
 assert.equal(integrationNeedsBrowser('full',0,'selected-data'),false);
 assert.ok(integrationTestFiles('full',0,'complete').includes('test/compact-ownership.test.mjs'));
 assert.equal(integrationNeedsBrowser('full',0,'complete'),true);
 assert.deepEqual(integrationTestFiles('full',0,'selected-output'),['test/compact-ownership.test.mjs']);
 assert.equal(integrationNeedsBrowser('full',0,'selected-output'),true);
 assert.throws(()=>integrationTestFiles('evidence',0,'selected-data'),/Invalid/);
 assert.throws(()=>integrationTestFiles('full',1,'selected-data'),/Invalid/);
});

function addTrustedProof(f, {evidenceFailed = false} = {}) {
  const original=f.api;
  const workflowRaw=fs.readFileSync('.github/workflows/merge-integration-checks.yml');
  const workflowOID=createHash('sha1').update(`blob ${workflowRaw.length}\0`).update(workflowRaw).digest('hex');
  const entries = [...f.authored, ...PROOF_PATHS.map(path=>({path,sha:path===WORKFLOW_PATH?workflowOID:path,type:'blob',mode:'100644'}))];
  f.authored=entries;
  const run={id:12,run_attempt:1,head_sha:f.head,event:'pull_request',path:WORKFLOW_PATH,
    repository:{full_name:f.repo},head_repository:{full_name:f.repo},status:'completed',conclusion:'success',
    pull_requests:[{number:2,head:{sha:f.head}}]};
  if (evidenceFailed) run.conclusion='failure';
  f.run=run;
  const api=async(route,method,body)=>{
    if(route.endsWith('/git/commits/'+f.head) || route.endsWith('/git/commits/'+f.base)) return {tree:{sha:'authored'}};
    if(route.endsWith('/git/commits/'+f.candidate)) return {tree:{sha:'authored'},parents:[{sha:f.base},{sha:f.head}]};
    if(route.includes('/git/blobs/')) return {sha:workflowOID,size:workflowRaw.length,encoding:'base64',content:workflowRaw.toString('base64')};
    if(route.includes('/actions/workflows/')) return {workflow_runs:[run]};
    if(route.endsWith('/actions/runs/12')) return run;
    if(route.includes('/jobs')) return {jobs:[{name:'profile',status:'completed',conclusion:'success'},
      {name:'package',status:'completed',conclusion:'success',steps:[{name:'Use full-regression package verification',status:'completed',conclusion:'success'}]},
      ...(evidenceFailed ? [{name:'evidence',status:'completed',conclusion:'failure'},
        ...['scope','geography'].map(name=>({name,status:'completed',conclusion:'success'}))] : []),
      ...[0,1,2].map(shard=>({name:`regression (${shard})`,status:'completed',conclusion:'success',
        steps:['Checkout reviewed head','Install Node dependencies','Install browser dependencies only for tests that use Playwright','Install Python dependencies','Complete regression shard',
          ...(shard===0?['Build hosted assets','Verify full-regression package controls','Read back qualified native build outputs when selected','Verify full-regression package receipt','Retain full-regression package receipt']:[])].map(name=>({name,status:'completed',conclusion:'success'}))}))]};
    return original(route,method,body);
  };
  const options=f.options;f.options=()=>({...options(),api});
}
test('prepare pins successful exact-tree run; skipped candidate job merges only after final proof reread',async()=>{
  const f=fixture();addTrustedProof(f);
  const prepared=await prepareIntegration(f.options());assert.equal(prepared.proof.run_id,12);
  const result=await f.complete({integrationResult:'skipped',proofRunId:12,proofRunAttempt:1});
  assert.equal(result.proof.run_id,12);assert.equal(f.writes.length,1);
});
test('evidence-only historical failure reuses code after fresh authority and geography pass',async()=>{
  const f=fixture();addTrustedProof(f,{evidenceFailed:true});
  // Later metadata authority is green; historical code coverage stays separate.
  f.checks.push({id:2,name:'evidence',app:{id:1},status:'completed',conclusion:'success'});
  const prepared=await prepareIntegration(f.options());assert.equal(prepared.proof.run_id,12);
  const result=await f.complete({integrationResult:'skipped',proofRunId:12,proofRunAttempt:1});
  assert.equal(result.proof.run_attempt,1);assert.equal(f.writes.length,1);
  assert.equal(f.evidenceReads,2);
});
test('historical code success never bypasses fresh evidence, review, ownership, checks or geography',async()=>{
  for (const mutate of [
    f=>f.checks.push({id:2,name:'evidence',app:{id:1},status:'completed',conclusion:'failure'}),
    f=>f.staleReview=true,
    f=>f.issue.state='closed',
    f=>f.checks[0].conclusion='failure'
  ]) {
    const f=fixture();addTrustedProof(f,{evidenceFailed:true});
    assert.ok((await prepareIntegration(f.options())).proof);mutate(f);
    await assert.rejects(prepareIntegration(f.options()));
    await assert.rejects(f.complete({integrationResult:'skipped',proofRunId:12,proofRunAttempt:1}));
    assert.equal(f.writes.length,0);
  }
  for (const geographyResult of [undefined,'failure','cancelled','skipped']) {
    const f=fixture();addTrustedProof(f,{evidenceFailed:true});
    assert.ok((await prepareIntegration(f.options())).proof);
    await assert.rejects(f.complete({integrationResult:'skipped',proofRunId:12,proofRunAttempt:1,geographyResult}),/Trusted combined geography check/);
    assert.equal(f.writes.length,0);
  }
});
test('failed proof reread and stale main prevent merge despite prior accepted proof',async()=>{
  const f=fixture();addTrustedProof(f);assert.ok((await prepareIntegration(f.options())).proof);
  f.run.conclusion='cancelled';
  await assert.rejects(f.complete({integrationResult:'skipped',proofRunId:12,proofRunAttempt:1}),/proof is no longer valid/);
  assert.equal(f.writes.length,0);
  const g=fixture();addTrustedProof(g);await prepareIntegration(g.options());g.base=sha('e');
  await assert.rejects(g.complete({integrationResult:'skipped',proofRunId:12,proofRunAttempt:1}),/Main advanced/);assert.equal(g.writes.length,0);
});

test('successful rerun after preparation invalidates the pinned attempt and refuses merge',async()=>{
  const f=fixture();addTrustedProof(f);const prepared=await prepareIntegration(f.options());
  assert.equal(prepared.proof.run_attempt,1);f.run.run_attempt=2;
  await assert.rejects(f.complete({integrationResult:'skipped',proofRunId:12,proofRunAttempt:1}),/proof is no longer valid/);
  assert.equal(f.writes.length,0);
});

// Responses change independently, just as the asynchronously generated GitHub
// merge candidate can lag unchanged reviewed PR metadata.
function sequencePR(f, update) {
  const api=f.api; let reads=0;
  f.api=async(route,...rest)=>{
    if(route===`/repos/${f.repo}/pulls/2`) {reads++;update(f,reads);}
    if(route.includes('/git/trees/')) f.treeReads=(f.treeReads??0)+1;
    return api(route,...rest);
  };
}
test('late candidate fetch replaces initial stale metadata without branch writes',async()=>{
  const f=fixture();sequencePR(f,(f,n)=>{f.pr.merge_commit_sha=n===1?sha('e'):f.candidate;});
  const result=await prepareIntegration(f.options());
  assert.equal(result.candidate,f.candidate);assert.equal(result.candidate_refresh_attempts,1);
  assert.equal(f.writes.length,0);
});
test('stale parents and unavailable candidates converge with revalidated authority',async()=>{
  for(const kind of ['stale','unavailable']) {
    const f=fixture();sequencePR(f,(f,n)=>{
      f.parentBase=n<4?sha('e'):f.base;
      f.pr.merge_commit_sha=kind==='unavailable'&&n<4?null:f.candidate;
    });
    const result=await prepareIntegration(f.options());
    assert.equal(result.candidate_refresh_attempts,3);assert.equal(f.evidenceReads,2);
    assert.equal(f.writes.length,0);
  }
});
test('permanently stale candidates are bounded and retain exact IDs before tree work',async()=>{
  const f=fixture();f.parentBase=sha('e');let prReads=0;
  const api=f.api;f.api=async(route,...rest)=>{if(route.endsWith('/pulls/2'))prReads++;if(route.includes('/git/trees/'))throw Error('Tree fetched before parents passed');return api(route,...rest);};
  await assert.rejects(prepareIntegration(f.options()),error=>{
    assert.match(error.message,/bounded refresh/);
    assert.equal(error.candidateDiagnostics.attempt,6);
    assert.equal(error.candidateDiagnostics.expected_base,f.base);
    assert.equal(error.candidateDiagnostics.expected_head,f.head);
    assert.equal(error.candidateDiagnostics.candidate,f.candidate);
    assert.deepEqual(error.candidateDiagnostics.actual_parents,[sha('e'),f.head]);return true;
  });assert.equal(prReads,7);assert.equal(f.writes.length,0);
});
test('candidate polling stops at its deadline even before exhausting attempts',async()=>{
  const f=fixture();f.pr.merge_commit_sha=null;let clock=0;
  await assert.rejects(prepareIntegration({...f.options(),candidateNow:()=>clock,candidateSleep:async()=>{clock+=30000;}}),error=>{
    assert.equal(error.candidateDiagnostics.attempt,2);assert.equal(error.candidateDiagnostics.reason,'candidate-unavailable');return true;
  });
});
test('head/body changes and conflicts during refresh fail without integration or writes',async()=>{
  for(const field of ['head','body','conflict']) {
    const f=fixture();sequencePR(f,(f,n)=>{
      if(n===1)f.pr.merge_commit_sha=null;
      if(n===3) {if(field==='head')f.pr.head.sha=sha('e');else if(field==='body')f.pr.body='Refs #1';else f.pr.mergeable=false;}
    });
    await assert.rejects(prepareIntegration(f.options()),error=>{
      assert.match(error.message,/head changed|scope\/body changed|conflict/);
      assert.equal(error.candidateDiagnostics.expected_head,f.head);
      assert.equal(error.candidateDiagnostics.observed_head,field==='head'?sha('e'):f.head);
      assert.equal(error.candidateDiagnostics.reason,{head:'head-changed',body:'pr-scope-changed',conflict:'conflict'}[field]);
      assert.equal(error.candidateDiagnostics.attempt,2);assert.ok(error.candidateDiagnostics.observed_at);return true;
    });
    assert.equal(f.treeReads??0,0);assert.equal(f.writes.length,0);
  }
});
test('main and evidence vintage advances are not silently adopted while refreshing',async()=>{
  for(const change of ['main','pr-base']) {
    const f=fixture();sequencePR(f,(f,n)=>{if(n===2){if(change==='main')f.base=sha('e');else f.pr.base.sha=sha('e');}});
    await assert.rejects(prepareIntegration(f.options()),error=>{
      assert.match(error.message,/base advanced/);assert.equal(error.candidateDiagnostics.reason,'base-advanced');return true;
    });assert.equal(f.treeReads??0,0);assert.equal(f.writes.length,0);
  }
});
test('scope/check/review and issue authority is rechecked after waiting',async()=>{
  for(const change of ['scope','checks','review','issue']) {
    const f=fixture();sequencePR(f,(f,n)=>{
      f.parentBase=n<3?sha('e'):f.base;
      if(n===4) {
        if(change==='scope')f.issue.state='closed';
        if(change==='checks')f.checks[0].conclusion='failure';
        if(change==='review')f.staleReview=true;
        if(change==='issue')f.issue.body=f.issue.body.replace('code','different');
      }
    });
    await assert.rejects(prepareIntegration(f.options()),/open GitHub issue|trusted scope|exact-head review|contract or ownership/);
    assert.equal(f.treeReads??0,0);assert.equal(f.writes.length,0);
  }
});

test('only candidate-object 404 is refreshable; access failures stop immediately',async()=>{
  const f=fixture(),api=f.api;let commitReads=0;
  f.api=async(route,...rest)=>{
    if(route.endsWith('/git/commits/'+f.candidate)&&++commitReads===1)throw Error(`GitHub GET ${route} failed (HTTP 404)`);
    return api(route,...rest);
  };
  assert.equal((await prepareIntegration(f.options())).candidate_refresh_attempts,2);
  const g=fixture(),gapi=g.api;
  g.api=async(route,...rest)=>{if(route.endsWith('/git/commits/'+g.candidate))throw Error('GitHub GET failed (HTTP 403)');return gapi(route,...rest);};
  await assert.rejects(prepareIntegration(g.options()),/HTTP 403/);assert.equal(g.writes.length,0);
});

test('post-wait main advance retains old expected and new observed base diagnostics',async()=>{
  const f=fixture();sequencePR(f,(f,n)=>{f.parentBase=n<3?sha('e'):f.base;if(n===4)f.base=sha('d');});
  await assert.rejects(prepareIntegration(f.options()),error=>{
    assert.match(error.message,/base advanced during refresh validation/);
    assert.equal(error.candidateDiagnostics.expected_base,sha('b'));
    assert.equal(error.candidateDiagnostics.observed_base,sha('d'));
    assert.equal(error.candidateDiagnostics.reason,'base-advanced');return true;
  });assert.equal(f.treeReads??0,0);assert.equal(f.writes.length,0);
});

test('post-convergence head change retains the new head in rejection diagnostics',async()=>{
  const f=fixture();sequencePR(f,(f,n)=>{f.parentBase=n<3?sha('e'):f.base;if(n===4)f.pr.head.sha=sha('d');});
  await assert.rejects(prepareIntegration(f.options()),error=>{
    assert.match(error.message,/head changed/);
    assert.equal(error.candidateDiagnostics.expected_head,f.head);
    assert.equal(error.candidateDiagnostics.observed_head,sha('d'));
    assert.equal(error.candidateDiagnostics.expected_base,sha('b'));
    assert.equal(error.candidateDiagnostics.reason,'head-changed');assert.equal(error.candidateDiagnostics.attempt,2);return true;
  });assert.equal(f.treeReads??0,0);assert.equal(f.writes.length,0);
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
    if(route.endsWith('/git/commits/'+f.synthetic))return {sha:f.synthetic,tree:{sha:'integrated'},parents:[{sha:f.wrongSyntheticParent?sha('d'):f.base},{sha:f.head}]};
    return api(route,method,body);
  };
  const options=f.options;f.options=()=>({...options(),prepareFallback:true,integrationRequestId:'isolated-candidate-test-request'});
  return f;
}
test('persistent automatic lag falls back to exact owned candidate without editing authored branches',async()=>{
  const f=isolatedFixture();f.parentBase=sha('d');
  const result=await prepareIntegration(f.options());
  assert.equal(result.candidate,f.synthetic);assert.equal(result.candidate_refresh_attempts,6);
  assert.equal(f.refs.get(result.candidate_ref),f.synthetic);assert.equal(result.pr.head.sha,f.head);
  assert.equal(f.writes.length,0);
  assert.equal((await cleanupCandidate(f.options(),result.candidate_ref,f.synthetic)).status,'deleted');
  assert.equal(f.refs.size,0);
});
test('isolated conflict or wrong parents is rejected and only the owned ref is deleted',async()=>{
  for(const field of ['mergeConflict','wrongSyntheticParent']) {
    const f=isolatedFixture();f[field]=true;
    await assert.rejects(createCandidate(f.options(),{pr:f.pr,base:f.base}),/conflict|exact current main/);
    assert.equal(f.refs.size,0);assert.equal(f.writes.length,0);
  }
});
test('fallback retains reviewed-byte and post-wait authority guards and cleans rejected candidates',async()=>{
  const f=isolatedFixture();f.parentBase=sha('d');f.integrated[0].sha='unreviewed';
  await assert.rejects(prepareIntegration(f.options()),/changes reviewed bytes/);
  assert.equal(f.refs.size,0);assert.equal(f.writes.length,0);
  const g=isolatedFixture();g.parentBase=sha('d');g.staleReview=true;
  await assert.rejects(prepareIntegration(g.options()),/exact-head review/);
  assert.equal(g.operations.some(row=>row.method==='POST'),false);
});
test('cleanup refuses another request, main/worker refs and changed owned refs',async()=>{
  const f=isolatedFixture();const created=await createCandidate(f.options(),{pr:f.pr,base:f.base});
  for(const ref of ['main',f.pr.head.ref,created.reference+'-other'])await assert.rejects(cleanupCandidate(f.options(),ref,f.synthetic),/unowned/);
  f.refChanged=true;await assert.rejects(cleanupCandidate(f.options(),created.reference,f.synthetic),/reference changed/);
  assert.equal(f.refs.size,1);assert.equal(f.operations.some(row=>row.method==='DELETE'),false);
});
test('failed cleanup retains its exact resource for inspection without hiding rejection',async()=>{
  const f=isolatedFixture();f.parentBase=sha('d');f.integrated[0].sha='unreviewed';f.deleteDenied=true;
  await assert.rejects(prepareIntegration(f.options()),error=>{
    assert.match(error.message,/changes reviewed bytes/);assert.equal(error.candidateCleanup.status,'pending');
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

test('unconfirmed ref creation identifies the resource without deleting a possible collision',async()=>{
  const f=isolatedFixture();f.createDenied=true;
  await assert.rejects(createCandidate(f.options(),{pr:f.pr,base:f.base}),error=>{
    assert.match(error.message,/HTTP 403/);assert.equal(error.candidateCleanup.status,'creation-unconfirmed');
    assert.match(error.candidateCleanup.reference,/^worldatlas-integration\/pr-2-/);return true;
  });assert.equal(f.operations.some(row=>row.method==='DELETE'),false);assert.equal(f.writes.length,0);
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


test('fresh geography success is required even when application proof is reusable', async()=>{
 for(const geographyResult of [undefined,'failure','cancelled','skipped']) {
  const f=fixture();addTrustedProof(f);
  assert.ok((await prepareIntegration(f.options())).proof);
  await assert.rejects(f.complete({integrationResult:'skipped',proofRunId:12,proofRunAttempt:1,geographyResult}),/Trusted combined geography check/);
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
 assert.match(geography,/id: check/);
 assert.match(geography,/GEOGRAPHY_PR_NUMBER: \$\{\{ inputs\.pr_number \}\}/);
 assert.match(geography,/GEOGRAPHY_REVIEWED_HEAD: \$\{\{ inputs\.expected_head \}\}/);
 assert.match(geography,/GEOGRAPHY_ARTIFACT_NAME: geography-\$\{\{ inputs\.request_id \}\}-\$\{\{ github\.run_attempt \}\}/);
 assert.match(geography,/echo "artifact_name=\$GEOGRAPHY_ARTIFACT_NAME" >> "\$GITHUB_OUTPUT"/);
 assert.match(workflow,/GEOGRAPHY_REPORT_SHA256: \$\{\{ needs\.geography\.outputs\.report_sha256 \}\}/);
 assert.match(workflow,/GEOGRAPHY_ARTIFACT_NAME: \$\{\{ needs\.geography\.outputs\.artifact_name \}\}/);
 const runner=fs.readFileSync('scripts/run-worker-merge.mjs','utf8');
 assert.match(runner,/geographyReportLoader: \(\{api: reportAPI = api\} = \{\}\) => loadGeographicReport\(\{api: reportAPI/);
 assert.match(runner,/runId: geographyProof\?\.run_id \?\? process\.env\.GITHUB_RUN_ID/);
 assert.match(runner,/expectedHash: geographyProof\?\.report_sha256 \?\? process\.env\.GEOGRAPHY_REPORT_SHA256/);
 assert.match(geography,/needs\.prepare\.outputs\.geography_proof == ''/);
 assert.match(workflow,/GEOGRAPHY_PROOF: \$\{\{ needs\.prepare\.outputs\.geography_proof \}\}/);
 assert.doesNotMatch(workflow,/actions\/download-artifact/,'privileged job must not extract an unverified archive');
});


test('known stale tested base or head rejects before expensive evidence/tree inspection', async()=>{
 const stale=fixture();stale.base=sha('d');
 await assert.rejects(stale.complete(),/resubmit unchanged head/);
 assert.equal(stale.evidenceReads??0,0);assert.equal(stale.writes.length,0);
 const changed=fixture();changed.pr.head.sha=sha('e');
 await assert.rejects(changed.complete(),/head changed/);
 assert.equal(changed.evidenceReads??0,0);assert.equal(changed.mainReads,0);assert.equal(changed.writes.length,0);
 const eligible=fixture();await eligible.complete();assert.ok(eligible.evidenceReads>0);assert.equal(eligible.writes.length,1);
});


test('candidate waiting rechecks changed scope/check/review/head after caching immutable evidence',async()=>{
 for(const changed of ['scope','check','review','head']) {
  const f=fixture(),origin=f.api,raw=Buffer.from('immutable evidence'),oid=createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
  let candidates=0,blobs=0;
  f.api=async(route,...rest)=>{
   if(route.endsWith('/git/blobs/'+oid)){blobs++;return {sha:oid,size:raw.length,encoding:'base64',content:raw.toString('base64')};}
   const value=await origin(route,...rest);
   if(route.endsWith('/git/commits/'+f.candidate)&&++candidates===1)return {...value,parents:[{sha:sha('d')},{sha:f.head}]};
   return value;
  };
  const options=f.options();options.evidenceCheck=async({api})=>{
   await api('/repos/owner/repo/git/blobs/'+oid);
   if(f.staleReview)throw Error('Missing independent exact-head review');return {status:'legacy'};
  };
  options.candidateSleep=async()=>{
   if(changed==='scope')f.issue.state='closed';
   if(changed==='check')f.checks[0].conclusion='failure';
   if(changed==='review')f.staleReview=true;
   if(changed==='head')f.pr.head.sha=sha('e');
  };
  await assert.rejects(prepareIntegration(options),changed==='scope'?/open GitHub issue/:changed==='check'?/trusted scope/:changed==='review'?/exact-head review/:/head changed/);
  assert.equal(blobs,1);assert.equal(f.writes.length,0);
 }
});

function addMetadataProof(f) {
  addTrustedProof(f);
  const prior=f.options,step=(name,conclusion='success')=>({name,status:'completed',conclusion});
  const job=(name,steps,id)=>({id,run_id:12,run_attempt:1,head_sha:f.head,name,status:'completed',conclusion:'success',steps});
  f.metadataJobs=[
    job('profile',['Validate ownership and focused CI applicability','Authenticate predecessor regression inputs'].map(n=>step(n)),1),
    job('regression (0)',[step('Checkout reviewed head'),step('Checkout reviewed head','skipped'),step('Install Node dependencies'),
      step('Run current-head regression consumers'),step('Complete regression shard','skipped'),step('Build hosted assets','skipped')],2),
    job('package',[step('Use authenticated predecessor package verification')],3)
  ];
  f.metadataLoads=0;
  f.options=()=>{const options=prior();return {...options,
    api:async(route,...args)=>{
      if(route.includes('/jobs'))return {jobs:f.metadataJobs};
      const value=await options.api(route,...args);
      if(route.includes('/git/commits/'))return {...value,sha:route.split('/').at(-1)};
      return value;
    },
    metadataProofLoader:async({head,baseline})=>{
      f.metadataLoads++;assert.equal(head,f.head);assert.equal(baseline,f.base);
      if(f.sourceInvalid)throw Error('original producer changed');
      return {status:'reused-original',reviewed_head:f.head,trusted_baseline:f.base,candidate_tree:'authored',
        program:{id:'audited-fixture'},original_computation:{head:sha('d'),tree:'original-tree',run_id:91,run_attempt:1}};
    },
    geographyProofLoader:async({proof})=>{assert.equal(proof.geography_job_id,undefined);return null;}
  };};
}

test('metadata reuse crosses actual queue prepare and final boundaries with current controls and fresh queue geography',async()=>{
  const f=fixture();addMetadataProof(f);
  const prepared=await prepareIntegration(f.options());
  assert.equal(prepared.proof.run_id,12);assert.equal(prepared.proof.metadata_regression.original_computation.run_id,91);
  assert.equal(prepared.geography_proof,null);assert.equal(f.metadataLoads,1);
  const result=await f.complete({integrationResult:'skipped',proofRunId:12,proofRunAttempt:1});
  assert.equal(f.metadataLoads,2);assert.equal(result.proof.run_id,12);assert.equal(f.writes.length,1);
});

test('queue refuses changed predecessor authority or failed fresh geography after metadata prepare',async()=>{
  for(const kind of ['source','geography']){
    const f=fixture();addMetadataProof(f);assert.ok((await prepareIntegration(f.options())).proof);
    if(kind==='source')f.sourceInvalid=true;
    await assert.rejects(f.complete({integrationResult:'skipped',proofRunId:12,proofRunAttempt:1,
      ...(kind==='geography'?{geographyResult:'failure'}:{})}));
    assert.equal(f.writes.length,0);
  }
});

// Final merge semantics retained from the removed speculative capacity planner.
{
function finalMergeFixture() {
  const repo = 'o/r', head = 'b'.repeat(40), base = 'a'.repeat(40), candidate = 'c'.repeat(40), branch = 'engineering/final-fixture';
  const manifestPath = 'coordination/engineering/final-fixture/evidence-quality.json', outputPath = 'coordination/engineering/final-fixture/result.json';
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
  const review = {version: 1, pr_number: 23, head_sha: head, manifest_sha256: sha256(manifestRaw), author_worker_id: 'author',
    reviewer_worker_id: 'reviewer', inspected_files: files.map(row => row.filename), evidence_hashes: [sha256(baselineRaw), sha256(outputRaw)],
    outcome: 'accepted', limits: [], domains: {implementation: {outcome: 'accepted', scope: 'Synthetic controls', limits: []},
      release: {outcome: 'accepted', scope: 'Synthetic preservation', limits: []}}};
  const blobs = new Map(), tree = rows => rows.map(([path, raw]) => {
    const sha = createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
    blobs.set(sha, {sha, size: raw.length, encoding: 'base64', content: raw.toString('base64')});
    return {path, sha, size: raw.length, mode: '100644', type: 'blob'};
  });
  const authored = tree([['README.md', baselineRaw], [outputPath, outputRaw], [manifestPath, manifestRaw]]), baseline = tree([['README.md', baselineRaw]]);
  const f = {repo, head, base, candidate, issue, pr, files, review, manifest, blobs, authored, baseline, calls: [], writes: [], checks: 'success'};
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
    if (name === `/repos/${repo}/issues/23/comments`) return [
      {id: 1, author_association: 'OWNER', body: `<!-- worldatlas-review:v1\n${JSON.stringify(f.review)}\n-->`}];
    if (name.includes('/git/commits/')) {
      const commit = name.split('/').at(-1);
      return {tree: {sha: commit === base ? '1'.repeat(40) : '2'.repeat(40)}, parents: [{sha: base}, {sha: head}]};
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

function evidenceFailedProof(f) {
  const workflow='ref: ${{ github.event.pull_request.head.sha }}\nname: Complete regression shard\nname: Build hosted assets';
  for (const path of PROOF_PATHS) {
    const raw=Buffer.from(path===WORKFLOW_PATH ? workflow : path);
    const sha=createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
    f.blobs.set(sha,{sha,size:raw.length,encoding:'base64',content:raw.toString('base64')});
    const row={path,sha,size:raw.length,mode:'100644',type:'blob'};
    f.baseline.push(row);f.authored.push(row);
  }
  f.proofRun={id:44,run_attempt:1,head_sha:f.head,event:'pull_request',path:WORKFLOW_PATH,
    repository:{full_name:f.repo},head_repository:{full_name:f.repo},status:'completed',conclusion:'failure',
    pull_requests:[{number:23,head:{sha:f.head}}]};
  f.proofJobs=[...['profile','scope','geography','package'].map(name=>({name,status:'completed',conclusion:'success'})),
    {name:'evidence',status:'completed',conclusion:'failure'},
    {name:'regression (0)',status:'completed',conclusion:'success',steps:
      ['Checkout reviewed head','Install browser dependencies only for tests that use Playwright','Complete regression shard']
        .map(name=>({name,status:'completed',conclusion:'success'}))}];
  const original=f.api;f.proofReads=0;
  f.api=async(route,...args)=>{
    if(route.endsWith('/actions/runs/44')) {f.proofReads++;return structuredClone(f.proofRun);}
    if(route.includes('/actions/runs/44/attempts/1/jobs')) return {jobs:structuredClone(f.proofJobs)};
    return original(route,...args);
  };
  const complete=f.complete;
  f.complete=extra=>complete({integrationResult:'skipped',proofRunId:44,proofRunAttempt:1,...extra});
  return f;
}
test('actual final merge accepts evidence-only run failure after full proof revalidation',async()=>{
  const f=evidenceFailedProof(finalMergeFixture());
  const result=await f.complete();
  assert.equal(result.accepted,true);
  assert.equal(result.proof.run_id,44);assert.equal(result.proof.run_attempt,1);
  assert.equal(f.proofReads,1,'Only the actual final proof is read; both planning passes are gone');
  assert.equal(f.writes.filter(row=>row.route.endsWith('/merge')).length,1);
});
test('final merge cannot authorize failed or missing code and science',async()=>{
  for (const mutate of [
    f=>f.proofJobs.find(job=>job.name==='regression (0)').conclusion='failure',
    f=>f.proofJobs.find(job=>job.name==='regression (0)').steps.pop(),
    f=>f.proofJobs.find(job=>job.name==='regression (0)').steps[0].conclusion='skipped',
    f=>f.proofJobs=f.proofJobs.filter(job=>job.name!=='geography'),
    f=>f.proofJobs.find(job=>job.name==='geography').conclusion='failure',
    f=>f.proofJobs.find(job=>job.name==='scope').conclusion='skipped',
    f=>f.proofRun.run_attempt=2,
    f=>f.proofRun.conclusion='cancelled',
    f=>f.proofRun.status='in_progress'
  ]) {
    const f=evidenceFailedProof(finalMergeFixture());mutate(f);
    await assert.rejects(f.complete(),/Trusted (?:integration )?proof/);
    assert.equal(f.writes.length,0);
  }
});
test('final proof is checked against revoked authority before any merge write',async()=>{
  for(const change of ['attempt','code-step']) {
    const f=evidenceFailedProof(finalMergeFixture()), original=f.api;
    f.api=async(route,...args)=>{
      const result=await original(route,...args);
      if(route.endsWith('/actions/runs/44') && f.proofReads===1) {
        if(change==='attempt') {f.proofRun.run_attempt=2;return structuredClone(f.proofRun);}
        f.proofJobs.find(job=>job.name==='regression (0)').steps[0].conclusion='failure';
      }
      return result;
    };
    await assert.rejects(f.complete(),/Trusted (?:integration )?proof/);assert.equal(f.writes.length,0);
  }
});

function geographyReuseFixture() {
  const f = evidenceFailedProof(finalMergeFixture());
  f.pr.mergeable = true; f.pr.merge_commit_sha = f.candidate;
  const job = f.proofJobs.find(job => job.name === 'geography');
  Object.assign(job, {id: 55, steps: ['Checkout trusted geographic checker', 'Install trusted geographic dependencies',
    'Check proposed geography with trusted baseline code',
    'Run actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02']
    .map(name => ({name, status: 'completed', conclusion: 'success'}))});
  f.source = {run_id: 44, run_attempt: 1, job_id: 55, tree: '2'.repeat(40), head: f.head, baseline: f.base,
    artifact_id: 77, artifact_name: 'proposed-geography-23-1', artifact_digest: 'a'.repeat(64), artifact_bytes: 100,
    report_sha256: 'b'.repeat(64), report_bytes: 200};
  f.report = {version: 1, method_id: 'worldatlas-trusted-geography-check-v1', baseline_commit: f.base,
    trusted_code_commit: f.base, candidate_commit: f.head, candidate_code_executed: false,
    published: false, source_approval: false, gate_status: 'passed', status: 'not-applicable'};
  const original = f.api;
  f.api = async (route, ...args) => route.includes('/actions/workflows/merge-integration-checks.yml/runs')
    ? {workflow_runs: [structuredClone(f.proofRun)]} : original(route, ...args);
  f.prepare = extra => prepareIntegration({...f.options(), geographyProofLoader: async () => ({source: f.source, report: f.report}), ...extra});
  const complete = f.complete;
  f.reuse = extra => complete({geographyResult: 'skipped', geographyProof: f.source,
    geographyReportLoader: async () => structuredClone(f.report), ...extra});
  return f;
}

test('prepare to actual final merge reuses original geography with truthful identities', async () => {
  const f = geographyReuseFixture(), prepared = await f.prepare();
  assert.deepEqual(prepared.geography_proof, f.source); assert.equal(prepared.proof.geography_job_id, 55);
  const result = await f.reuse({geographyProof: prepared.geography_proof});
  assert.equal(result.accepted, true);
  assert.equal(result.tested_candidate, f.candidate); assert.equal(result.geography.candidate_commit, f.head);
  assert.equal(result.geography.execution, 'reused-original'); assert.deepEqual(result.geography.source, f.source);
  assert(!f.calls.some(call => call.route.includes('/artifacts?')),
    'No speculative artifact prewalk when the report loader already supplies the report');
  assert.equal(f.writes.filter(row => row.route.endsWith('/merge')).length, 1);
});

test('unusable prepared report falls back to fresh geography without discarding application proof', async () => {
  for (const change of ['missing', 'wrong-report', 'wrong-source', 'download-failed']) {
    const f = geographyReuseFixture();
    const prepared = await f.prepare({geographyProofLoader: async () => {
      if (change === 'missing') return null;
      if (change === 'download-failed') throw Error('bounded original log unavailable');
      return {source: {...f.source, ...(change === 'wrong-source' ? {job_id: 66} : {})},
        report: {...f.report, ...(change === 'wrong-report' ? {candidate_commit: f.candidate} : {})}};
    }});
    assert.equal(prepared.proof.run_id, 44); assert.equal(prepared.geography_proof, null);
    await assert.rejects(f.reuse({geographyProof: null}), /Trusted combined geography check/);
    assert.equal(f.writes.length, 0);
  }
});

test('reused geography never accepts drift, unresolved science or failed current authority', async () => {
  for (const mutate of [
    f => {f.source.job_id++;}, f => {f.source.run_attempt++;}, f => {f.source.tree = '3'.repeat(40);},
    f => {f.source.baseline = 'd'.repeat(40);}, f => {f.source.head = 'd'.repeat(40);},
    f => {f.source.artifact_name = 'proposed-geography-24-1';},
    f => {f.report.candidate_commit = f.candidate;}, f => {f.report.trusted_code_commit = 'd'.repeat(40);},
    f => {f.report.status = 'regressions-found';}, f => {f.report.gate_status = 'blocked';},
    f => {f.proofJobs.find(job => job.name === 'geography').conclusion = 'skipped';},
    f => {f.proofRun.run_attempt++;}, f => {f.checks = 'failure';},
    f => {f.issue.state = 'closed';}
  ]) {
    const f = geographyReuseFixture(); await f.prepare(); mutate(f);
    await assert.rejects(f.reuse()); assert.equal(f.writes.length, 0);
  }
});

test('final geography source is revalidated during final validation before any write', async () => {
  const f = geographyReuseFixture(); await f.prepare(); const original = f.api;
  f.api = async (route, ...args) => {
    const result = await original(route, ...args);
    if (route.endsWith('/actions/runs/44') && f.proofReads === 1)
      f.proofJobs.find(job => job.name === 'geography').id = 0;
    return result;
  };
  await assert.rejects(f.reuse(), /Original geographic proof/); assert.equal(f.writes.length, 0);
});

test('actual final validation reads full evidence once and rejects changed bytes and authority', async t => {
  const f = finalMergeFixture(); const result = await f.complete();
  assert.equal(result.accepted, true);
  assert.equal(f.calls.filter(row => row.route.includes('/git/blobs/')).length, 3);
  assert.equal(f.calls.filter(row => row.route.includes('/pulls/23/files?')).length, 1);
  assert.equal(f.calls.filter(row => row.route.includes('/issues/23/comments?')).length, 1);
  assert.equal(f.calls.filter(row => row.route.includes('/artifacts?') || row.route === '/rate_limit').length, 0);
  assert.equal(f.writes.filter(row => row.method === 'PUT').length, 1);
  t.diagnostic(JSON.stringify({actual_api_calls: f.calls.length, final_file_passes: 1, final_review_passes: 1}));
  for (const changed of ['bytes', 'review', 'issue', 'main']) {
    const bad = finalMergeFixture(), original = bad.api;
    if (changed === 'bytes') bad.blobs.get(bad.authored.find(row => row.path.endsWith('result.json')).sha).content = Buffer.from('different').toString('base64');
    if (changed === 'review') bad.review.outcome = 'changes-requested';
    let reads = 0;
    bad.api = async (route, ...args) => {
      if (changed === 'issue' && route.endsWith('/issues/1183') && ++reads === 2) bad.issue.body += '\nChanged acceptance';
      if (changed === 'main' && route.endsWith('/git/ref/heads/main') && ++reads === 3) return {object: {sha: 'e'.repeat(40)}};
      return original(route, ...args);
    };
    await assert.rejects(bad.complete()); assert.equal(bad.writes.length, 0, changed);
  }
});
function finalTransportFixture(mode = 'complete', f = finalMergeFixture()) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'final-validation-transport-'));
  const origin = f.api, events = []; let admission, fetches = 0;
  const http = async (route, method = 'GET', ...args) => {
    admission?.({route, method}); events.push({kind: 'http', route});
    return origin(route, method, ...args);
  };
  http.setHTTPAdmission = hook => {admission = hook; return () => {admission = null;};};
  const transport = gitBlobTransport(http, {repo: f.repo, token: 'synthetic-transport-token', directory,
    execute: (command, args, options) => {
      if (!args.includes('fetch')) return execFileSync(command, args, options);
      fetches++; events.push({kind: 'fetch'});
      const requested = args.slice(args.indexOf('https://github.com/' + f.repo + '.git') + 1);
      for (const sha of mode === 'incomplete' ? requested.slice(0, -1) : requested) {
        const blob = f.blobs.get(sha); assert.ok(blob, 'fetch must request only the tree-bound inventory');
        execFileSync('git', [args[0], 'hash-object', '-w', '--stdin'],
          {input: Buffer.from(blob.content, 'base64'), env: options.env});
      }
      return Buffer.alloc(0);
    }});
  f.api = (...args) => transport.api(...args);
  for (const name of ['setHTTPAdmission', 'prefetchGitBlobs', 'hasGitBlobs']) {
    if (mode === 'missing' && name !== 'setHTTPAdmission') continue;
    f.api[name] = function (...args) {
      assert.equal(this, f.api, `${name} must preserve its original receiver through every wrapper`);
      if (mode === 'declined' && name === 'prefetchGitBlobs') return;
      if (mode === 'declined' && name === 'hasGitBlobs') return false;
      return transport.api[name](...args);
    };
  }
  return {f, events, get fetches() {return fetches;}, close() {
    transport.close(); assert.deepEqual(fs.readdirSync(directory), []); fs.rmdirSync(directory);
  }};
}

test('actual final completion retains byte transport and safe REST fallback', async () => {
  for (const mode of ['complete', 'missing', 'declined']) {
    const t = finalTransportFixture(mode), {f} = t;
    try {
      const result = await f.complete();
      assert.equal(result.accepted, true);
      assert.equal(t.fetches, mode === 'complete' ? 1 : 0);
      assert.equal(t.events.filter(row => row.kind === 'http' && row.route.includes('/git/blobs/')).length,
        mode === 'complete' ? 1 : f.blobs.size);
      assert.equal(f.writes.filter(row => row.route.endsWith('/merge')).length, 1);
    } finally {t.close();}
  }
});

test('incomplete actual transport and changed mutable authority cannot reach merge after feature forwarding', async () => {
  for (const mode of ['incomplete', 'complete']) {
    const t = finalTransportFixture(mode), {f} = t;
    try {
      await assert.rejects(f.complete({geographyReportLoader: async () => {
        f.issue.body += '\nChanged acceptance';
        return {version: 1, method_id: 'worldatlas-trusted-geography-check-v1', baseline_commit: f.base, trusted_code_commit: f.base, candidate_commit: f.candidate, candidate_code_executed: false, published: false, source_approval: false, gate_status: 'passed', status: 'not-applicable'};
      }}), mode === 'incomplete' ? /Exact immutable Git transport failed/ : /Head\/body or issue contract changed/);
      assert.equal(t.fetches, 1); assert.equal(f.writes.length, 0);
    } finally {t.close();}
  }
});

// A real single-entry stored ZIP exercises the production report loader through
// prepare and final integration; no GIS is executed.
function storedReportArchive(raw) {
  const name = Buffer.from('geography-check.json'), crc = crc32(raw);
  const local = Buffer.alloc(30); local.writeUInt32LE(0x04034b50); local.writeUInt16LE(20, 4);
  local.writeUInt32LE(crc, 14); local.writeUInt32LE(raw.length, 18); local.writeUInt32LE(raw.length, 22);
  local.writeUInt16LE(name.length, 26);
  const central = Buffer.alloc(46); central.writeUInt32LE(0x02014b50); central.writeUInt16LE(20, 6);
  central.writeUInt32LE(crc, 16); central.writeUInt32LE(raw.length, 20); central.writeUInt32LE(raw.length, 24);
  central.writeUInt16LE(name.length, 28);
  const end = Buffer.alloc(22); end.writeUInt32LE(0x06054b50); end.writeUInt16LE(1, 8); end.writeUInt16LE(1, 10);
  end.writeUInt32LE(46 + name.length, 12); end.writeUInt32LE(30 + name.length + raw.length, 16);
  return Buffer.concat([local, name, raw, central, name, end]);
}
function carriedGeographyFixture() {
  const f = geographyReuseFixture();
  f.originRun = {...structuredClone(f.proofRun), conclusion: 'cancelled', pull_requests: []};
  f.originJobs = [structuredClone(f.proofJobs.find(job => job.name === 'geography'))];
  Object.assign(f.originJobs[0], {run_id: 44, run_attempt: 1, head_sha: f.head});
  f.proofRun.run_attempt = 2;
  f.proofJobs.find(job => job.name === 'geography').id = 66;
  f.publishReport = report => {
  const raw = Buffer.from(JSON.stringify(report) + '\n');
  f.zip = storedReportArchive(raw);
  f.artifact = {id: 77, name: 'proposed-geography-23-1', expired: false, size_in_bytes: f.zip.length,
    digest: 'sha256:' + reportHash(f.zip), workflow_run: {id: 44, head_sha: f.head}};
  f.log = Buffer.from([JSON.stringify({report_bytes: raw.length, report_sha256: reportHash(raw)}),
    'SHA256 digest of uploaded artifact zip is ' + reportHash(f.zip),
    `Artifact proposed-geography-23-1 has been successfully uploaded! Final size is ${f.zip.length} bytes. Artifact ID is 77`].join('\n'));
  };
  f.publishReport(f.report);
  const previous = f.api; f.transportCalls = []; let admission;
  f.api = async (route, method = 'GET', body) => {
    admission?.({route, method}); f.transportCalls.push(route);
    if (route.endsWith('/actions/runs/44/attempts/1')) return structuredClone(f.originRun);
    if (route.includes('/actions/runs/44/attempts/1/jobs')) return {jobs: structuredClone(f.originJobs)};
    if (route.includes('/actions/runs/44/attempts/2/jobs')) return {jobs: structuredClone(f.proofJobs)};
    if (route.includes('/actions/runs/44/artifacts?')) return {total_count: 1, artifacts: [structuredClone(f.artifact)]};
    if (route.endsWith('/logs') || route.endsWith('/zip')) return new Response(null, {status: 302, headers: {
      location: `https://results.blob.core.windows.net/${route.endsWith('/zip') ? 'zip' : route.includes('/55/') ? 'origin' : 'carried'}?fixture`
    }});
    return previous(route, method, body);
  };
  f.api.setHTTPAdmission = hook => {admission = hook; return () => {admission = null;};};
  f.api.jobLogRedirect = route => f.api(route);
  f.api.artifactRedirect = route => f.api(route);
  f.fetchImpl = async (url, init) => {
    assert.equal(init.headers, undefined); assert.equal(init.redirect, 'error');
    return new Response(url.includes('/zip?') ? f.zip : url.includes('/origin?') ? f.originLog ?? f.log : f.log);
  };
  f.prepare = () => prepareIntegration({...f.options(), geographyProofLoader: args => prepareGeographyProof({
    ...args, token: 'synthetic', fetchImpl: f.fetchImpl})});
  f.reuse = (prepared, extra = {}) => completeIntegration({...f.options(),
    integrationResult: 'skipped', geographyResult: 'skipped', testedCandidate: f.candidate,
    proofRunId: prepared.proof.run_id, proofRunAttempt: prepared.proof.run_attempt,
    geographyProof: prepared.geography_proof,
    geographyReportLoader: ({api}) => loadGeographicReport({api, repo: f.repo, token: 'synthetic',
      runId: prepared.geography_proof.run_id, artifactName: prepared.geography_proof.artifact_name,
      expectedHash: prepared.geography_proof.report_sha256, source: prepared.geography_proof, fetchImpl: f.fetchImpl}), ...extra});
  return f;
}
test('actual loaders preserve attempt-one geography through attempt-two code and final merge', async () => {
  const f = carriedGeographyFixture(), prepared = await f.prepare();
  assert.equal(prepared.proof.run_attempt, 2); assert.equal(prepared.proof.geography_job_id, 66);
  assert.equal(prepared.geography_proof.run_attempt, 1); assert.equal(prepared.geography_proof.job_id, 55);
  assert.equal(prepared.geography_proof.current_run_attempt, 2); assert.equal(prepared.geography_proof.current_job_id, 66);
  const result = await f.reuse(prepared);
  assert.equal(result.accepted, true); assert.equal(result.proof.run_attempt, 2);
  assert.equal(result.geography.source.run_attempt, 1); assert.equal(result.geography.source.job_id, 55);
  assert.equal(result.geography.candidate_commit, f.head); assert.equal(result.tested_candidate, f.candidate);
  assert.equal(f.transportCalls.filter(route => route.endsWith('/attempts/1')).length, 2,
    'Origin is authenticated at prepare and actual final validation, with no duplicate planning passes');
  assert.equal(f.writes.filter(row => row.route.endsWith('/merge')).length, 1);
});

test('actual carried prepare rejects missing, multiple, future and foreign receipts but keeps valid latest code', async () => {
  for (const mutate of [
    f => {f.log = Buffer.from('missing');},
    f => {f.log = Buffer.concat([f.log, Buffer.from('\n'), f.log]);},
    f => {f.log = Buffer.from(f.log.toString().replace('proposed-geography-23-1', 'proposed-geography-23-3'));},
    f => {f.log = Buffer.from(f.log.toString().replace('proposed-geography-23-1', 'proposed-geography-24-1'));},
    f => {f.originLog = Buffer.from(f.log.toString().replace('Artifact ID is 77', 'Artifact ID is 78'));},
    f => {f.originJobs[0].status = 'in_progress';}, f => {f.originRun.head_sha = 'e'.repeat(40);},
    f => {f.publishReport({...f.report, baseline_commit: 'e'.repeat(40)});},
    f => {f.publishReport({...f.report, trusted_code_commit: 'e'.repeat(40)});},
    f => {f.publishReport({...f.report, candidate_commit: f.candidate});}
  ]) {
    const f = carriedGeographyFixture(); mutate(f); const prepared = await f.prepare();
    assert.equal(prepared.proof.run_attempt, 2); assert.equal(prepared.geography_proof, null);
    assert.equal(f.writes.length, 0);
  }
});

test('actual final carried reuse rejects identity, source, artifact and report substitutions', async () => {
  for (const mutate of [
    (f, p) => {p.geography_proof.tree = 'e'.repeat(40);},
    (f, p) => {p.geography_proof.head = 'e'.repeat(40);},
    (f, p) => {p.geography_proof.baseline = 'e'.repeat(40);},
    (f, p) => {p.geography_proof.current_job_id++;},
    (f, p) => {p.geography_proof.job_id++;},
    f => {f.originJobs[0].id++;}, f => {f.originJobs[0].run_id++;},
    f => {f.originJobs[0].run_attempt++;}, f => {f.originJobs[0].head_sha = 'e'.repeat(40);},
    f => {f.originRun.id++;}, f => {f.originRun.run_attempt++;},
    f => {f.originRun.head_sha = 'e'.repeat(40);},
    f => {f.originJobs[0].conclusion = 'failure';},
    f => {f.proofJobs.find(job => job.name === 'geography').conclusion = 'failure';},
    f => {f.proofRun.run_attempt++;}, f => {f.artifact.expired = true;},
    f => {f.artifact.id++;}, f => {f.artifact.workflow_run.head_sha = 'e'.repeat(40);},
    f => {f.zip = storedReportArchive(Buffer.from('{}'));}
  ]) {
    const f = carriedGeographyFixture(), prepared = await f.prepare(); mutate(f, prepared);
    await assert.rejects(f.reuse(prepared)); assert.equal(f.writes.length, 0);
  }
});

// Real HTTP admission and ETag revalidation, with only the network replaced.
function quotaCompletionFixture({retry = false, deplete = false} = {}) {
  const f = finalMergeFixture(), original = f.api, attempts = [];
  let remaining = 2000, time = 0, retried = false, issueReads = 0;
  const headers = () => ({'x-ratelimit-limit': '2000', 'x-ratelimit-remaining': String(remaining),
    'x-ratelimit-reset': '3600', 'x-ratelimit-resource': 'core', etag: '"unchanged"'});
  f.api = githubAPI('synthetic-quota-token', {minimumRemaining: 16, readWaitMs: 60000,
    now: () => time, sleep: async ms => {time += ms;}, deadlineRemaining: () => 100000 - time,
    onRequest: row => attempts.push({route: row.route, status: row.status, remaining: row.capacity.remaining}),
    fetchImpl: async (url, init) => {
      const route = url.slice('https://api.github.com'.length), name = route.split('?')[0];
      if (retry && !retried && name.endsWith('/pulls/23')) {
        retried = true; remaining--;
        return Response.json({message: 'secondary rate limit'}, {status: 403,
          headers: {...headers(), 'retry-after': '1'}});
      }
      if (name.endsWith('/issues/1183') && ++issueReads === 2 && deplete) remaining = 16;
      if (init.headers['If-None-Match']) return new Response(null, {status: 304, headers: headers()});
      remaining--;
      const value = await original(route, init.method, init.body ? JSON.parse(init.body) : undefined);
      return Response.json(value, {headers: headers()});
    }});
  return {f, attempts, complete: () => f.complete(), get remaining() {return remaining;}, get issueReads() {return issueReads;}};
}
for (const retry of [false, true]) test(`actual final HTTP uses fresh quota and retains 304/retry guards: ${retry}`, async t => {
  const q = quotaCompletionFixture({retry}), result = await q.complete();
  assert.equal(result.accepted, true);
  assert(q.attempts.some(row => row.status === 304), 'Authority was actually conditionally reread');
  assert.equal(q.attempts.filter(row => row.status === 403).length, retry ? 1 : 0);
  assert.equal(q.f.writes.filter(row => row.method === 'PUT').length, 1);
  assert(q.remaining >= 16);
  assert(!q.attempts.some(row => row.route === '/rate_limit' || row.route === '/repos/o/r'));
  t.diagnostic(JSON.stringify({actual_http_attempts: q.attempts.length,
    conditional_revalidations: q.attempts.filter(row => row.status === 304).length,
    retry_rejections: q.attempts.filter(row => row.status === 403).length}));
});
test('actual final authority stops on newly observed concurrent depletion and preserves recovery', async () => {
  const q = quotaCompletionFixture({deplete: true});
  await assert.rejects(q.complete(), error => error.quotaAdmission?.remaining === 16);
  assert.equal(q.issueReads, 2, 'Depletion is observed in the final current issue reread');
  assert.equal(q.f.writes.length, 0);
});

test('original PR merge candidate survives prepare and final acceptance without becoming reviewed head', async () => {
  const f = geographyReuseFixture(), originCandidate = 'e'.repeat(40), original = f.api;
  Object.assign(f.source, {workflow_path: WORKFLOW_PATH, event: 'pull_request', workflow_head: f.head,
    candidate_commit: originCandidate});
  f.report.candidate_commit = originCandidate;
  Object.assign(f.proofJobs.find(job => job.name === 'geography'), {run_id: 44, run_attempt: 1, head_sha: f.head});
  f.api = async (route, ...args) => {
    if (route.endsWith('/actions/runs/44/attempts/1')) return structuredClone(f.proofRun);
    if (route.endsWith(`/git/commits/${originCandidate}`)) return {sha: originCandidate,
      tree: {sha: f.source.tree}, parents: [{sha: f.base}, {sha: f.head}]};
    return original(route, ...args);
  };
  const prepared = await f.prepare();
  assert.equal(prepared.geography_proof.candidate_commit, originCandidate);
  const result = await f.reuse({geographyProof: prepared.geography_proof});
  assert.equal(result.accepted, true);
  assert.equal(result.reviewed_head, f.head);
  assert.equal(result.tested_candidate, f.candidate);
  assert.equal(result.geography.candidate_commit, originCandidate);
  assert.equal(result.geography.source.candidate_commit, originCandidate);
  assert.equal(result.geography.source.head, f.head);
  assert.equal(f.writes.filter(row => row.route.endsWith('/merge')).length, 1);
});

}
