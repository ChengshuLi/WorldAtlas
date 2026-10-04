import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {integrationTestFiles, integrationNeedsBrowser, prepareIntegrationTests} from '../scripts/run-integration-tests.mjs';
import {PROOF_PATHS, WORKFLOW_PATH} from '../scripts/integration-proof.mjs';
import {renderClaim} from '../scripts/issue-claim-contract.mjs';
import {prepareIntegration, completeIntegration, checkCurrentChecks, integrationProfile} from '../scripts/merge-integration.mjs';

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
  f.complete = extra => completeIntegration({...f.options(),integrationResult:'success',testedBase:base,testedCandidate:candidate,...extra});
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
test('stale head or review and expired ownership prohibit integration', async () => {
  const a=fixture();a.pr.head.sha=sha('e');await assert.rejects(a.complete(),/head changed/);
  const b=fixture();b.staleReview=true;await assert.rejects(b.complete(),/exact-head review/);
  const c=fixture();c.claim.expires_at='2000-01-01T00:00:00Z';await assert.rejects(c.complete(),/unexpired claim/);
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
  assert.match(yaml.split('  merge:\n')[1],/concurrency:\n      group: worldatlas-main-integrate/);
  assert.doesNotMatch(integration,/concurrency:/);
  assert.match(integration,/permissions:\n      contents: read/);
  assert.doesNotMatch(integration,/GH_TOKEN|secrets\.|contents: write|issues: write|pull-requests: write/);
  assert.match(integration,/persist-credentials: false/);assert.match(integration,/node scripts\/run-integration-tests.mjs/);assert.match(integration,/run: npm run build:hosted/);
  assert.match(yaml,/needs: \[prepare, integration\]/);
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
 assert.equal([0,1,2].filter(shard=>integrationNeedsBrowser('full',shard)).length,1);
});

function addTrustedProof(f) {
  const original=f.api;
  const entries = [...f.authored, ...PROOF_PATHS.map(path=>({path,sha:path,type:'blob',mode:'100644'}))];
  f.authored=entries;
  const run={id:12,run_attempt:1,head_sha:f.head,event:'pull_request',path:WORKFLOW_PATH,
    repository:{full_name:f.repo},head_repository:{full_name:f.repo},status:'completed',conclusion:'success',
    pull_requests:[{number:2,head:{sha:f.head}}]};
  f.run=run;
  const api=async(route,method,body)=>{
    if(route.endsWith('/git/commits/'+f.head) || route.endsWith('/git/commits/'+f.base)) return {tree:{sha:'authored'}};
    if(route.endsWith('/git/commits/'+f.candidate)) return {tree:{sha:'authored'},parents:[{sha:f.base},{sha:f.head}]};
    if(route.includes('/git/blobs/')) return {content:Buffer.from(fs.readFileSync('.github/workflows/merge-integration-checks.yml')).toString('base64')};
    if(route.includes('/actions/workflows/')) return {workflow_runs:[run]};
    if(route.endsWith('/actions/runs/12')) return run;
    if(route.includes('/jobs')) return {jobs:[{name:'profile',status:'completed',conclusion:'success'},
      ...[0,1,2].map(shard=>({name:`regression (${shard})`,status:'completed',conclusion:'success',
        steps:['Checkout reviewed head','Install Node dependencies','Install browser dependencies only for tests that use Playwright','Install Python dependencies','Complete regression shard',
          ...(shard===0?['Build hosted assets']:[])].map(name=>({name,status:'completed',conclusion:'success'}))}))]};
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
test('claim/check/review and issue authority is rechecked after waiting',async()=>{
  for(const change of ['claim','checks','review','issue']) {
    const f=fixture();sequencePR(f,(f,n)=>{
      f.parentBase=n<3?sha('e'):f.base;
      if(n===4) {
        if(change==='claim')f.claim.expires_at='2000-01-01T00:00:00Z';
        if(change==='checks')f.checks[0].conclusion='failure';
        if(change==='review')f.staleReview=true;
        if(change==='issue')f.issue.body=f.issue.body.replace('code','different');
      }
    });
    await assert.rejects(prepareIntegration(f.options()),/unexpired claim|trusted scope|exact-head review|contract or ownership/);
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
