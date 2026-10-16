import {execFileSync} from 'node:child_process';
import {gitBlobTransport} from '../scripts/git-blob-transport.mjs';
import {memoizeImmutableGitBlobs} from '../scripts/immutable-git-blobs.mjs';
import {sha256, subjectsHash} from '../scripts/evidence-quality.mjs';
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import os from 'node:os';
import path from 'node:path';
import {FOCUSED_INTEGRATION_TESTS, integrationTestFiles, integrationNeedsBrowser, prepareIntegrationTests} from '../scripts/run-integration-tests.mjs';
import {renderClaim, githubAPI} from '../scripts/issue-claim-contract.mjs';
import {prepareIntegration, completeIntegration, checkCurrentChecks, integrationProfile, geographyRequired, createCandidate, cleanupCandidate, cleanupMergedHead} from '../scripts/merge-integration.mjs';

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
  const f = {repo, pr, issue, head, base, candidate, claim, writes: [], mainReads: 0, calls: [], refs: new Map(),
    checks: [{id:1, name:'scope',app:{id:1},status:'completed',conclusion:'success'}],
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
    if (p==='/pulls/2') return structuredClone(f.pr);
    if (p==='/issues/1') return structuredClone(f.issue);
    if (p==='/issues/1/comments') return [{id:1,user:{login:'github-actions[bot]'},body:renderClaim(f.claim)}];
    if (p==='/issues/1/timeline') return [];
    if (p==='/pulls/2/files') return [{filename:'src/a.js',status:'modified'}];
    if (p==='/commits/'+head+'/check-runs') return {check_runs:structuredClone(f.checks)};
    if (p==='/commits/'+head+'/status') {f.statusReads=(f.statusReads??0)+1;return f.failStatusOnRead===f.statusReads ? {statuses:[{}],state:'failure'} : {statuses:[]};}
    if (p==='/git/ref/heads/main') {f.mainReads++;return {object:{sha:f.advanceOnRead===f.mainReads?sha('d'):f.base}};}
    if (p==='/git/commits/'+head) return {tree:{sha:'authored'}};
    if (p==='/git/commits/'+candidate) return {sha:candidate,tree:{sha:'integrated'},parents:[{sha:f.parentBase??f.base},{sha:head}]};
    if (p==='/git/trees/authored') return {truncated:false,tree:f.authored};
    if (p==='/git/trees/integrated') return {truncated:f.truncated??false,tree:f.integrated};
    throw Error('Unexpected API '+method+' '+route);
  };
  f.options = () => ({api:f.api,repo,number:2,expectedHead:head,policy:{version:1,mode:'enforce-new',activation_time:'2100-01-01T00:00:00Z'},
    integrationRequestId:'owned-candidate-test-request',
    evidenceCheck:async()=>{f.evidenceReads=(f.evidenceReads??0)+1;if(f.staleReview)throw Error('Missing independent exact-head review');return {status:'legacy'};}});
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
  const a=fixture();a.parentBase=sha('e');await assert.rejects(prepareIntegration(a.options()),/exact current main/);
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
test('the final queue validates its real candidate without redundant author checks', async () => {
  const f=fixture();f.checks=[];
  const prepared=await prepareIntegration(f.options());
  assert.equal(prepared.candidate,f.candidate);
  const result=await f.complete();
  assert.equal(result.accepted,true);assert.equal(f.writes.length,1);
  assert(f.evidenceReads>=3,'actual queue evidence checks still execute');
});
test('missing author checks cannot hide failed current checks or current evidence', async () => {
  for(const failure of ['checks','evidence']) {
    const f=fixture();f.checks=[];
    if(failure==='checks')f.checks=[{id:1,name:'external-validation',app:{id:2},status:'in_progress',conclusion:null}];
    else f.staleReview=true;
    await assert.rejects(prepareIntegration(f.options()),failure==='checks'?/pending or failed/:/exact-head review/);
    await assert.rejects(f.complete(),failure==='checks'?/pending or failed/:/exact-head review/);
    assert.equal(f.writes.length,0);
  }
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
  assert.doesNotMatch(integration,/Read back qualified native build outputs|native-normal-built-output\.json|--built-output-readback/);
  const selectedSmoke=steps.find(step=>step.includes('name: Retain selected delivery smoke\n'));
  assert.match(selectedSmoke,/name: selected-delivery-smoke-/);
  assert.match(selectedSmoke,/path: \.cache\/selected-delivery-smoke\.json/);
  assert.doesNotMatch(integration,/WORLDATLAS_CHECKOUT_TOKEN:|Authenticate trusted full-checkout bootstrap|Acquire full checkout with authenticated bounded helper/);
  const checkout=steps.filter(step=>/name: Checkout exact candidate for application regression\n/.test(step));
  assert.equal(checkout.length,1);
  assert.match(checkout[0],/uses: actions\/checkout@d23441a48e516b6c34aea4fa41551a30e30af803/);
  assert.match(checkout[0],/ref: \$\{\{ needs\.prepare\.outputs\.candidate \}\}/);
  assert.match(checkout[0],/sparse-checkout: \$\{\{ needs\.prepare\.outputs\.checkout_patterns \}\}/);
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
   for(const scientific of ['scripts/native-ownership/native-preparation-guards.mjs','scripts/native-ownership/validate-build-context-stage.mjs','scripts/native-ownership/chained-build-context.mjs','src/native-grid.js','coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs']) {
     assert.equal(integrationProfile('engineering/example',[{filename:helper},{filename:scientific}],{}),'full');
     assert.equal(integrationProfile('engineering/example',[{filename:helper,previous_filename:scientific}],{}),'full');
   }
 }
 assert.equal(integrationProfile('engineering/example',[{filename:'docs/WORKER_COORDINATION.md'},{filename:'coordination/engineering/example/receipt.json'}],{}),'evidence');
 for(const filename of ['src/attributes.js','data/hierarchy.json','drizzle/0001.sql','scripts/build-hosted.mjs','scripts/run-integration-tests.mjs'])
   assert.equal(integrationProfile('engineering/example',[{filename}],{}),'full');
 assert.equal(integrationProfile('engineering/example',[{filename:'docs/a.md',previous_filename:'src/attributes.js'}],{}),'full');
 assert.equal(integrationProfile('engineering/example',[{filename:'coordination/engineering/other/receipt.json'}],{}),'full');
});

test('ordinary modified focused tests compose with coordination while unknown setup stays full', () => {
  const files=integrationTestFiles('evidence',0).map(filename=>({filename,status:'modified'}));
  const tree=new Map(files.map(file=>[file.filename,{type:'blob',mode:'100644',sha:'1'.repeat(40)}]));
  assert.equal(integrationProfile('engineering/tests',files,{},tree),'evidence');
  for(const file of files) {
    assert.equal(integrationProfile('engineering/tests',[file],{},tree),'evidence');
    for(const status of [undefined,'added','removed','renamed','copied'])
      assert.equal(integrationProfile('engineering/tests',[{...file,status}],{},tree),'full');
    for(const previous_filename of [file.filename,'src/native-grid.js','test/unknown.test.mjs'])
      assert.equal(integrationProfile('engineering/tests',[{...file,previous_filename}],{},tree),'full');
    for(const entry of [undefined,{type:'blob',mode:'120000'},{type:'blob',mode:'100755'},{type:'tree',mode:'040000'},{type:'blob',mode:'100644'},{type:'blob',mode:'100644',sha:'unknown'}]) {
      const changed=new Map(tree);entry ? changed.set(file.filename,entry) : changed.delete(file.filename);
      assert.equal(integrationProfile('engineering/tests',[file],{},changed),'full');
    }
    assert.equal(integrationProfile('engineering/tests',[file]),'full');
    for(const filename of ['scripts/prepare-delivery-handoff.mjs','docs/LOCAL_WORKSPACES.md',
      'coordination/engineering/tests/receipt.json'])
      assert.equal(integrationProfile('engineering/tests',[file,{filename,status:'modified'}],{},tree),'evidence');
    for(const filename of ['scripts/native-ownership/native-preparation-guards.mjs',
      'scripts/native-ownership/chained-build-context.mjs','src/native-grid.js','src/main.js','hosted/app.mjs',
      'scripts/run-integration-tests.mjs','scripts/build-cloudflare.mjs','vite.config.js','package.json',
      'package-lock.json','requirements.txt','.github/package-inputs.json','data/hierarchy.json','test/unknown.test.mjs'])
      assert.equal(integrationProfile('engineering/tests',[file,{filename,status:'modified'}],{},tree),'full');
  }
  // These package-contract, asset-dependent and Python-helper tests are not
  // executed by the exact focused Node roster, even with ordinary tree proof.
  for(const filename of ['test/deployment-budget-scope.test.mjs','test/package-inputs.test.mjs',
    'test/package-build.test.mjs','test/deployment-budget.test.mjs','test/pr-gates.test.mjs',
    'test/canonical-compact-repack.test.mjs','test/source-cohort.test.py','test/physical-source-retention.test.py']) {
    assert.ok(!files.some(file=>file.filename===filename));
    const ordinary=new Map([[filename,{type:'blob',mode:'100644',sha:'1'.repeat(40)}]]);
    assert.equal(integrationProfile('engineering/tests',[{filename,status:'modified'}],{},ordinary),'full');
  }
  assert.equal(integrationProfile('engineering/tests',[],{},tree),'full');
});

test('geography omission derives only non-scientific control and validated focused-test changes', () => {
  const ordinary = name => new Map([[name,{type:'blob',mode:'100644',sha:sha('a')}]]);
  const required = (filename, extra = {}) => geographyRequired('engineering/controls',
    [{filename,status:'modified',...extra}],{},ordinary(filename));
  for (const name of ['scripts/merge-integration.mjs','scripts/run-worker-merge.mjs',
    'scripts/integration-profile.mjs','scripts/prepare-delivery-handoff.mjs',...FOCUSED_INTEGRATION_TESTS])
    assert.equal(required(name),false,name);
  // Existing checkpoint/current-method and package roles remain mandatory,
  // including shared helpers that otherwise qualify for focused regression.
  for (const name of ['scripts/check-handoff-scope.mjs','scripts/evidence-policy.mjs',
    'scripts/evidence-quality.mjs','scripts/integration-proof.mjs','scripts/issue-claim-contract.mjs',
    'scripts/worker-result.mjs','scripts/classify-deployment-budget.mjs','scripts/local-workspace.mjs',
    'src/native-grid.js','data/hierarchy.json','data/ownership-selection.json',
    '.github/workflows/worker-merge.yml','.github/workflows/merge-integration-checks.yml',
    '.github/evidence-policy.json','docs/WORKER_COORDINATION.md','docs/unknown.md',
    'coordination/engineering/controls/source.json','test/unknown.test.mjs'])
    assert.equal(required(name),true,name);
  for (const status of ['added','removed','renamed','copied'])
    assert.equal(required('test/merge-integration.test.mjs',{status}),true);
  assert.equal(required('scripts/merge-integration.mjs',{previous_filename:'scripts/evidence-quality.mjs'}),true);
  assert.equal(required('test/merge-integration.test.mjs',{previous_filename:'scripts/merge-integration.mjs'}),true);
  assert.equal(geographyRequired('engineering/controls',[]),true);
  assert.equal(geographyRequired('geography/controls',[{filename:'scripts/merge-integration.mjs'}]),true);
});

function controlFixture() {
  const f=fixture(), original=f.api;
  f.files=['scripts/merge-integration.mjs','test/merge-integration.test.mjs'].map(filename=>({filename,status:'modified'}));
  f.pr.changed_files=f.files.length;
  f.authored=f.files.map(file=>({path:file.filename,sha:sha('e'),mode:'100644',type:'blob'}));
  f.integrated=structuredClone(f.authored);
  f.api=(route,...args)=>route.split('?')[0].endsWith('/pulls/2/files') ? structuredClone(f.files) : original(route,...args);
  return f;
}

test('actual prepare and complete omit unrelated geography without reading or fabricating a report', async () => {
  const f=controlFixture(), prepared=await prepareIntegration(f.options());
  assert.equal(prepared.profile,'evidence');assert.equal(prepared.geography_required,false);
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
  for (const kind of ['scientific','packet','test-mode','test-added','rename-origin']) {
    const f=controlFixture();await prepareIntegration(f.options());
    if(kind==='scientific')f.files[0].filename='scripts/evidence-quality.mjs';
    if(kind==='packet')f.files[0].filename='coordination/engineering/test/source.json';
    if(kind==='test-mode')f.authored[1].mode='120000';
    if(kind==='test-added')f.files[1].status='added';
    if(kind==='rename-origin')f.files[0].previous_filename='data/hierarchy.json';
    await assert.rejects(f.complete({geographyResult:'skipped'}));assert.equal(f.writes.length,0,kind);
  }
});

test('omitted geography retains exact candidate, review, statuses and both main guards', async () => {
  for (const kind of ['head','early-base','late-base','parents','tree','truncated','review','status','integration']) {
    const f=controlFixture(), options={geographyResult:'skipped'};
    if(kind==='head')f.pr.head.sha=sha('d');
    if(kind==='early-base')f.advanceOnRead=1;
    if(kind==='late-base')f.advanceOnRead=3;
    if(kind==='parents')f.parentBase=sha('d');
    if(kind==='tree')f.integrated[0].sha=sha('d');
    if(kind==='truncated')f.truncated=true;
    if(kind==='review')f.staleReview=true;
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
  const focused = yaml.split('      - name: Checkout only focused-test inputs for evidence regression\n')[1].split('      - uses:')[0];
  assert.match(focused,/coverage-gaps-907-20261005-local01\/sources\/natural-earth-lakes\.geojson\.gz/);
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
 assert.deepEqual(focused,FOCUSED_INTEGRATION_TESTS);
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

function sequencePR(f, update) {
  const api=f.api; let reads=0;
  f.api=async(route,...rest)=>{
    if(route===`/repos/${f.repo}/pulls/2`) {reads++;update(f,reads);}
    if(route.includes('/git/trees/')) f.treeReads=(f.treeReads??0)+1;
    return api(route,...rest);
  };
}
test('owned preparation never reads an automatic preview or waits and uses two authority passes',async()=>{
  for(const preview of [null,sha('d'),sha('c')]) {
    const f=fixture();f.pr.merge_commit_sha=preview;
    const result=await prepareIntegration(f.options());
    assert.equal(result.candidate,f.candidate);assert.equal(f.evidenceReads,2);
    assert.equal(f.calls.length,18,'Two six-read authority passes, three owned creation calls and three tree reads');
    assert.equal(f.calls.filter(row=>row.route.endsWith('/pulls/2')).length,2);
    assert.equal(f.mainReads,2);assert.equal(f.calls.filter(row=>row.method==='POST').length,2);
    assert.equal(f.calls.filter(row=>row.route.endsWith('/git/commits/'+f.candidate)).length,1);
    assert(!f.calls.some(row=>row.route.endsWith('/git/commits/'+sha('d'))));
    assert.equal(f.writes.length,0);assert.equal(f.refs.get(result.candidate_ref),f.candidate);
    assert(!('candidate_refresh_attempts' in result));
  }
  const source=fs.readFileSync(new URL('../scripts/merge-integration.mjs',import.meta.url),'utf8');
  assert.doesNotMatch(source,/currentCandidate|candidateSleep|candidateNow|setTimeout/);
});
test('owned preparation rechecks every mutable PR and issue authority before trees and cleans rejection',async()=>{
  for(const change of ['head','body','title','ref','repo','inventory','scope','checks','status','review','issue','main','pr-base','merged']) {
    const f=isolatedFixture();sequencePR(f,(f,n)=>{
      if(n!==2)return;
      if(change==='head')f.pr.head.sha=sha('d');
      if(change==='body')f.pr.body='Refs #1';
      if(change==='title')f.pr.title='Changed title';
      if(change==='ref')f.pr.head.ref='engineering/other';
      if(change==='repo')f.pr.head.repo.full_name='other/repo';
      if(change==='inventory')f.pr.changed_files=2;
      if(change==='scope')f.issue.state='closed';
      if(change==='checks')f.checks[0].conclusion='failure';
      if(change==='status')f.failStatusOnRead=2;
      if(change==='review')f.staleReview=true;
      if(change==='issue')f.issue.body=f.issue.body.replace('code','changed');
      if(change==='main')f.base=sha('d');
      if(change==='pr-base')f.pr.base.sha=sha('d');
      if(change==='merged'){f.pr.merged=true;f.pr.merge_commit_sha=sha('f');}
    });
    await assert.rejects(prepareIntegration(f.options()),error=>{
      assert.match(error.message,/head changed|scope\/body changed|repository PRs|inventory|open GitHub issue|pending or failed|status|exact-head review|contract or ownership|base advanced|PR merged/);
      if(change==='main'||change==='pr-base') {
        assert.equal(error.candidateDiagnostics.expected_base,sha('b'));
        assert.equal(error.candidateDiagnostics.reason,'base-advanced');
      }
      if(change==='head') {
        assert.equal(error.candidateDiagnostics.expected_head,f.head);
        assert.equal(error.candidateDiagnostics.observed_head,sha('d'));
        assert.equal(error.candidateDiagnostics.candidate,f.synthetic);
      }
      return true;
    });
    assert.equal(f.treeReads??0,0,change);assert.equal(f.writes.length,0,change);assert.equal(f.refs.size,0,change);
    assert.equal(f.operations.filter(row=>row.method==='DELETE').length,1,change);
  }
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
  assert.equal(result.candidate,f.synthetic);assert.equal(f.evidenceReads,2);
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
test('owned preparation retains reviewed-byte and authority guards and cleans rejected candidates',async()=>{
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

test('same-candidate failed-job retry survives owned ref cleanup and keeps final authority guards',async()=>{
  for(const changed of [null,'base','head','tree','parents','review','checks','integration','geography']){
    const f=isolatedFixture();f.parentBase=sha('d');
    const prepared=await prepareIntegration(f.options());
    await cleanupCandidate(f.options(),prepared.candidate_ref,prepared.candidate);
    assert.equal(f.refs.size,0);
    const options={testedCandidate:prepared.candidate,testedBase:prepared.base};
    if(changed==='base')f.base=sha('d');
    if(changed==='head')f.pr.head.sha=sha('d');
    if(changed==='tree')f.integrated[0].sha='changed-after-tests';
    if(changed==='parents')f.wrongSyntheticParent=true;
    if(changed==='review')f.staleReview=true;
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
 const eligible=fixture();await eligible.complete();assert.ok(eligible.evidenceReads>0);assert.equal(eligible.writes.length,1);
});


test('post-create revalidation rechecks changed authority while caching only immutable evidence',async()=>{
 for(const changed of ['scope','check','review','head']) {
  const f=isolatedFixture(),origin=f.api,raw=Buffer.from('immutable evidence'),oid=createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
  let blobs=0;
  f.api=async(route,...rest)=>{
   if(route.endsWith('/git/blobs/'+oid)){blobs++;return {sha:oid,size:raw.length,encoding:'base64',content:raw.toString('base64')};}
   const value=await origin(route,...rest);
   if(route.endsWith('/git/commits/'+f.synthetic)) {
    if(changed==='scope')f.issue.state='closed';
    if(changed==='check')f.checks[0].conclusion='failure';
    if(changed==='review')f.staleReview=true;
    if(changed==='head')f.pr.head.sha=sha('e');
   }
   return value;
  };
  const options=f.options();options.evidenceCheck=async({api})=>{
   await api('/repos/owner/repo/git/blobs/'+oid);
   if(f.staleReview)throw Error('Missing independent exact-head review');return {status:'legacy'};
  };
  await assert.rejects(prepareIntegration(options),changed==='scope'?/open GitHub issue/:changed==='check'?/pending or failed/:changed==='review'?/exact-head review/:/head changed/);
  assert.equal(blobs,1);assert.equal(f.writes.length,0);assert.equal(f.refs.size,0);
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

test('actual final validation reads full evidence once and rejects changed bytes and authority', async t => {
  const f = finalMergeFixture(); const result = await f.complete();
  assert.equal(result.accepted, true);
  assert.equal(f.calls.filter(row => row.route.includes('/git/blobs/')).length, 3);
  assert.equal(f.calls.filter(row => row.route.includes('/pulls/23/files?')).length, 1);
  assert.equal(f.calls.filter(row => /\/(?:comments|reviews)\?/.test(row.route)).length, 0);
  assert.equal(f.calls.filter(row => row.route.includes('/artifacts?') || row.route === '/rate_limit').length, 0);
  assert.equal(f.writes.filter(row => row.method === 'PUT').length, 1);
  t.diagnostic(JSON.stringify({actual_api_calls: f.calls.length, final_file_passes: 1, duplicate_review_receipt_reads: 0}));
  for (const changed of ['bytes', 'issue', 'main']) {
    const bad = finalMergeFixture(), original = bad.api;
    if (changed === 'bytes') bad.blobs.get(bad.authored.find(row => row.path.endsWith('result.json')).sha).content = Buffer.from('different').toString('base64');
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
