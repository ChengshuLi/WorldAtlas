import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {integrationTestFiles, integrationNeedsBrowser} from '../scripts/run-integration-tests.mjs';
import {renderClaim} from '../scripts/issue-claim-contract.mjs';
import {prepareIntegration, completeIntegration, checkCurrentChecks, integrationProfile} from '../scripts/merge-integration.mjs';

const sha = letter => letter.repeat(40);
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
    evidenceCheck:async()=>{if(f.staleReview)throw Error('Missing independent exact-head review');return {status:'legacy'};}});
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
  const a=fixture();a.parentBase=sha('e');await assert.rejects(prepareIntegration(a.options()),/exact current main/);
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
 for(const filename of ['src/attributes.js','data/hierarchy.json','drizzle/0001.sql','.github/workflows/worker-merge.yml'])
   assert.equal(integrationProfile('engineering/example',[{filename}],{}),'full');
 assert.equal(integrationProfile('engineering/example',[{filename:'docs/a.md',previous_filename:'src/attributes.js'}],{}),'full');
 assert.equal(integrationProfile('engineering/example',[{filename:'coordination/engineering/other/receipt.json'}],{}),'full');
});

test('parallel full-regression shards cover each unit file once and focused profile retains core gates', () => {
 const expected=fs.readdirSync('test').filter(name=>name.endsWith('.test.mjs')).map(name=>`test/${name}`).sort();
 const shards=[0,1,2].flatMap(shard=>integrationTestFiles('full',shard));
 assert.deepEqual([...shards].sort(),expected);assert.equal(new Set(shards).size,expected.length);
 const focused=integrationTestFiles('evidence',0);
 for(const name of ['premerge-evidence','regional-research-gate','handoff-scope','merge-integration'])assert.ok(focused.includes(`test/${name}.test.mjs`));
 assert.throws(()=>integrationTestFiles('evidence',1),/Invalid/);
 assert.equal(integrationNeedsBrowser('evidence',0),false);
 assert.equal([0,1,2].filter(shard=>integrationNeedsBrowser('full',shard)).length,1);
});
