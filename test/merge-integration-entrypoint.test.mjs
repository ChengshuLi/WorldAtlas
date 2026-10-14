import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {renderClaim} from '../scripts/issue-claim-contract.mjs';

const root=path.resolve(import.meta.dirname,'..');
// Mock the real authenticated core-response boundary even when these child
// entry points inherit the hosted Actions environment. Keep denied mutations
// denied; missing capacity must not silently disable production admission.
const capacityShim=`const coreHeaders={'x-ratelimit-resource':'core','x-ratelimit-limit':'5000','x-ratelimit-remaining':'4900','x-ratelimit-reset':String(Math.floor(Date.now()/1000)+3600)};
const NativeResponse=globalThis.Response;
globalThis.Response=class extends NativeResponse {
 constructor(body,options={}){const headers=new Headers(options.headers);for(const [key,value] of Object.entries(coreHeaders))headers.set(key,value);super(body,{...options,headers});}
 static json(body,options={}){return new this(JSON.stringify(body),{...options,headers:{'Content-Type':'application/json',...options.headers}});}
};
`;

function run({readFails=false,commentFails=false,phase='prepare',merged=true,head='a'.repeat(40),integration='skipped',geography='skipped',mergeOnReconcile=false,mergeCommit='b'.repeat(40)}={}) {
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-merge-entry-'));
  fs.mkdirSync(path.join(directory,'.github'));
  fs.copyFileSync(path.join(root,'.github/evidence-policy.json'),path.join(directory,'.github/evidence-policy.json'));
  fs.writeFileSync(path.join(directory,'event.json'),JSON.stringify({inputs:{pr_number:'2',expected_head:'a'.repeat(40),request_id:'entrypoint-test-request'}}));
  fs.writeFileSync(path.join(directory,'mock.mjs'),capacityShim+`let reads=0;globalThis.fetch=async(url,options)=> {
    if(options.method==='PUT')throw Error('Unexpected new merge');
    const posting=options.method==='POST';
    if(new URL(url).pathname.endsWith('/pulls/2'))reads++;
    return new Response(JSON.stringify(posting?{}:{merged:${merged}||(${mergeOnReconcile}&&reads>1),head:{sha:'${head}'},merge_commit_sha:${JSON.stringify(mergeCommit)}}),
      {status:posting?${commentFails?403:201}:${readFails?418:200},headers:{'Content-Type':'application/json'}});
  };`);
  const result=spawnSync(process.execPath,['--import',path.join(directory,'mock.mjs'),path.join(root,'scripts/run-worker-merge.mjs')],{
    cwd:directory,encoding:'utf8',env:{...process.env,GITHUB_ACTIONS:'false',GH_TOKEN:'synthetic-test-token',GITHUB_REPOSITORY:'owner/repo',GITHUB_REF:'refs/heads/main',
      GITHUB_EVENT_PATH:path.join(directory,'event.json'),GITHUB_OUTPUT:path.join(directory,'outputs'),GITHUB_STEP_SUMMARY:path.join(directory,'summary'),MERGE_PHASE:phase,INTEGRATION_RESULT:integration,GEOGRAPHY_RESULT:geography}});
  const receipt=JSON.parse(fs.readFileSync(path.join(directory,'merge-result.json'))),summary=fs.readFileSync(path.join(directory,'summary'),'utf8');
  fs.rmSync(directory,{recursive:true,force:true});return {result,receipt,summary};
}
test('actual trusted entry point preserves the original rejection before a denied comment',()=>{
  const {result,receipt,summary}=run({readFails:true,commentFails:true});
  assert.notEqual(result.status,0);assert.match(result.stderr,/POST.*HTTP 403/);
  assert.equal(receipt.accepted,false);assert.equal(receipt.status,'not-merged');
  assert.match(receipt.reason,/GET.*HTTP 418/);assert.match(summary,/GET.*HTTP 418/);
  assert.equal(receipt.api_error.http_status,418);assert.equal(receipt.notification_api_error.http_status,403);
});
test('actual trusted entry point retains its preparation receipt before successful notification',()=>{
  const {result,receipt}=run();assert.equal(result.status,0,result.stderr);
  assert.equal(receipt.status,'already-merged');assert.equal(receipt.accepted,true);
});
test('trusted preparation has PR comment permission while candidate tests remain read-only',()=>{
  const yaml=fs.readFileSync(path.join(root,'.github/workflows/worker-merge.yml'),'utf8');
  assert.match(yaml.split('  prepare:\n')[1].split('  integration:\n')[0],/pull-requests: write/);
  const candidate=yaml.split('  integration:\n')[1].split('  merge:\n')[0];
  // Exact read-token bootstrap scope is exercised in merge-integration.test.mjs.
  const forbidden=/contents: write|pull-requests: write|issues: write|secrets\./;
  assert.match(candidate,/permissions:\n      contents: read/);assert.doesNotMatch(candidate,forbidden);
  for(const unsafe of ['contents: write','pull-requests: write','issues: write','secrets.TOKEN'])
    assert.match(unsafe,forbidden);
});

test('native failed-job retries retain original receipts without artifact-name collisions',()=>{
  const yaml=fs.readFileSync(path.join(root,'.github/workflows/worker-merge.yml'),'utf8');
  for(const name of ['native-built-output','merge'])
    assert(yaml.includes(`name: ${name}-\${{ inputs.request_id }}-\${{ github.run_attempt }}`),name);
  assert.doesNotMatch(yaml,/overwrite: true/);
  const client=fs.readFileSync(path.join(root,'docs/MERGE_QUEUE_CLIENT.md'),'utf8');
  assert.match(client,/gh run rerun RUN-ID --repo ChengshuLi\/WorldAtlas --failed/);
  assert.match(client,/still the tested base/);
  assert.match(client,/execution predates attempt-qualified uploads/);
});

test('actual entry point saves stale/head/conflict/base diagnostics even when notification fails',()=>{
 for(const kind of ['stale','head','conflict','base']) {
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-merge-diagnostics-'));
  const sha=c=>c.repeat(40),head=sha('a'),base=sha('b'),candidate=sha('c');
  fs.mkdirSync(path.join(directory,'.github'));
  fs.copyFileSync(path.join(root,'.github/evidence-policy.json'),path.join(directory,'.github/evidence-policy.json'));
  fs.writeFileSync(path.join(directory,'event.json'),JSON.stringify({inputs:{pr_number:'2',expected_head:head,request_id:'diagnostics-test-request'}}));
  const issue={number:1,state:'open',created_at:'2020-01-01T00:00:00Z',labels:['type:engineering','kind:work-item','status:ready'],
    body:'<!-- worldatlas-work:v1\n'+JSON.stringify({mode:'engineering',max_prs:2,depends_on:[],scope:'code'})+'\n-->'};
  const pr={number:2,state:'open',draft:false,body:'Closes #1',title:'Repair',changed_files:1,
    head:{sha:head,ref:'engineering/test',repo:{full_name:'owner/repo'}},base:{ref:'main',sha:base},mergeable:true,merge_commit_sha:candidate};
  const routes={
    '/pulls/2':pr,'/issues/1':issue,'/issues/1/timeline':[],
    '/issues/1/comments':[{id:1,user:{login:'github-actions[bot]'},body:renderClaim({version:1,active:true,worker_id:'worker',claim_id:'nonce',branch:'engineering/test',expires_at:new Date(Date.now()+3600000).toISOString()})}],
    '/pulls/2/files':[{filename:'src/a.js',status:'modified'}],
    ['/commits/'+head+'/check-runs']:{check_runs:[{id:1,name:'scope',app:{id:1},status:'completed',conclusion:'success'}]},
    ['/commits/'+head+'/status']:{statuses:[]},'/git/ref/heads/main':{object:{sha:base}},
    ['/git/commits/'+candidate]:{sha:candidate,parents:[{sha:sha('e')},{sha:head}]}
  };
  fs.writeFileSync(path.join(directory,'mock.mjs'),capacityShim+`const routes=${JSON.stringify(routes)};
    const realSetTimeout=globalThis.setTimeout;globalThis.setTimeout=(fn,ms,...args)=>realSetTimeout(fn,ms===2000?0:ms,...args);
    let prReads=0,baseReads=0;
    globalThis.fetch=async(url,options)=>{
      const route=new URL(url).pathname.replace('/repos/owner/repo','');
      if(route==='/pulls/2'&&++prReads===2) {
        if('${kind}'==='head')routes[route].head.sha='d'.repeat(40);
        if('${kind}'==='conflict')routes[route].mergeable=false;
      }
      if(route==='/git/ref/heads/main'&&++baseReads===2&&'${kind}'==='base')routes[route].object.sha='d'.repeat(40);
      return new Response(JSON.stringify(options.method==='POST'?{}:routes[route]??{}),{status:options.method==='POST'?403:200,headers:{'Content-Type':'application/json'}});
    };`);
  try {
    const result=spawnSync(process.execPath,['--import',path.join(directory,'mock.mjs'),path.join(root,'scripts/run-worker-merge.mjs')],{
      cwd:directory,encoding:'utf8',env:{...process.env,GITHUB_ACTIONS:'false',GH_TOKEN:'synthetic-token',GITHUB_REPOSITORY:'owner/repo',GITHUB_REF:'refs/heads/main',
        GITHUB_EVENT_PATH:path.join(directory,'event.json'),GITHUB_OUTPUT:path.join(directory,'outputs'),GITHUB_STEP_SUMMARY:path.join(directory,'summary'),MERGE_PHASE:'prepare'}});
    const receipt=JSON.parse(fs.readFileSync(path.join(directory,'merge-result.json')));
    assert.notEqual(result.status,0);assert.match(result.stderr,/HTTP 403/);
    assert.equal(receipt.retryable,kind==='stale'||kind==='base');
    assert.equal(receipt.candidate_diagnostics.attempt,kind==='stale'?6:1);
    assert.equal(receipt.candidate_diagnostics.expected_base,kind==='base'?sha('d'):base);
    assert.equal(receipt.candidate_diagnostics.expected_head,head);
    assert.equal(receipt.candidate_diagnostics.candidate,candidate);
    assert.equal(receipt.candidate_diagnostics.reason,{stale:'stale-candidate',head:'head-changed',conflict:'conflict',base:'base-advanced'}[kind]);
    assert.ok(receipt.candidate_diagnostics.observed_at);
    if(kind==='stale')assert.deepEqual(receipt.candidate_diagnostics.actual_parents,[sha('e'),head]);
    assert.match(fs.readFileSync(path.join(directory,'summary'),'utf8'),/stale|head changed|conflict|base advanced/);
  } finally {fs.rmSync(directory,{recursive:true,force:true});}
 }
});

test('actual final entry point cleans only its owned ref and retains successful merge on cleanup failure',()=>{
  for(const kind of ['deleted','denied','unowned']) {
    const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-owned-cleanup-'));
    fs.mkdirSync(path.join(directory,'.github'));
    fs.copyFileSync(path.join(root,'.github/evidence-policy.json'),path.join(directory,'.github/evidence-policy.json'));
    const request='cleanup-entrypoint-request',reference=`worldatlas-integration/pr-2-${request}-1234`;
    fs.writeFileSync(path.join(directory,'event.json'),JSON.stringify({inputs:{pr_number:'2',expected_head:'a'.repeat(40),request_id:request}}));
    fs.writeFileSync(path.join(directory,'mock.mjs'),capacityShim+`globalThis.fetch=async(url,options)=>{
      const route=new URL(url).pathname;
      if(options.method==='PUT')throw Error('Unexpected new merge');
      if(options.method==='DELETE') {
        if(route!=='/repos/owner/repo/git/refs/heads/${reference}')throw Error('Unowned deletion');
        return '${kind}'==='denied'?new Response('{}',{status:403}):new Response(null,{status:204});
      }
      return new Response(JSON.stringify(route.endsWith('/pulls/2')?{merged:true,head:{sha:'a'.repeat(40)},merge_commit_sha:'b'.repeat(40)}:
        route.includes('/git/ref/heads/')?{object:{sha:'b'.repeat(40)}}:{}),{status:200,headers:{'Content-Type':'application/json'}});
    };`);
    try {
      const result=spawnSync(process.execPath,['--import',path.join(directory,'mock.mjs'),path.join(root,'scripts/run-worker-merge.mjs')],{
        cwd:directory,encoding:'utf8',env:{...process.env,GITHUB_ACTIONS:'false',GH_TOKEN:'synthetic-token',GITHUB_REPOSITORY:'owner/repo',GITHUB_REF:'refs/heads/main',
          GITHUB_RUN_ID:'1234',GITHUB_EVENT_PATH:path.join(directory,'event.json'),GITHUB_OUTPUT:path.join(directory,'outputs'),GITHUB_STEP_SUMMARY:path.join(directory,'summary'),
          MERGE_PHASE:'merge',INTEGRATION_RESULT:'success',TESTED_CANDIDATE:'b'.repeat(40),CANDIDATE_REF:kind==='unowned'?'main':reference}});
      const receipt=JSON.parse(fs.readFileSync(path.join(directory,'merge-result.json')));
      assert.equal(result.status,0,result.stderr);assert.equal(receipt.accepted,true);assert.equal(receipt.status,'merged');
      assert.equal(receipt.candidate_cleanup.status,kind==='deleted'?'deleted':'pending');
      if(kind==='unowned')assert.match(receipt.candidate_cleanup.reason,/unowned/);
    } finally {fs.rmSync(directory,{recursive:true,force:true});}
  }
});

test('actual fallback prepare cleans its confirmed ref when receipt notification is denied',()=>{
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-prepare-notify-cleanup-'));
  const sha=c=>c.repeat(40),head=sha('a'),base=sha('b'),candidate=sha('c'),owned=sha('e');
  fs.mkdirSync(path.join(directory,'.github'));
  fs.copyFileSync(path.join(root,'.github/evidence-policy.json'),path.join(directory,'.github/evidence-policy.json'));
  fs.writeFileSync(path.join(directory,'event.json'),JSON.stringify({inputs:{pr_number:'2',expected_head:head,request_id:'notification-cleanup-test'}}));
  const issue={number:1,state:'open',created_at:'2020-01-01T00:00:00Z',labels:['type:engineering','kind:work-item','status:ready'],
    body:'<!-- worldatlas-work:v1\n'+JSON.stringify({mode:'engineering',max_prs:2,depends_on:[],scope:'code'})+'\n-->'};
  const pr={number:2,state:'open',draft:false,body:'Closes #1',title:'Repair',changed_files:1,
    head:{sha:head,ref:'engineering/test',repo:{full_name:'owner/repo'}},base:{ref:'main',sha:base},mergeable:true,merge_commit_sha:candidate};
  const routes={
    '/pulls/2':pr,'/issues/1':issue,'/issues/1/timeline':[],
    '/issues/1/comments':[{id:1,user:{login:'github-actions[bot]'},body:renderClaim({version:1,active:true,worker_id:'worker',claim_id:'nonce',branch:'engineering/test',expires_at:new Date(Date.now()+3600000).toISOString()})}],
    '/pulls/2/files':[{filename:'src/a.js',status:'modified'}],
    ['/commits/'+head+'/check-runs']:{check_runs:[{id:1,name:'scope',app:{id:1},status:'completed',conclusion:'success'}]},
    ['/commits/'+head+'/status']:{statuses:[]},'/git/ref/heads/main':{object:{sha:base}},
    ['/git/commits/'+candidate]:{sha:candidate,parents:[{sha:sha('d')},{sha:head}]},
    ['/git/commits/'+owned]:{sha:owned,tree:{sha:'combined'},parents:[{sha:base},{sha:head}]},
    ['/git/commits/'+head]:{tree:{sha:'combined'}},
    '/git/trees/combined':{truncated:false,tree:[{path:'src/a.js',sha:'blob',mode:'100644',type:'blob'}]}
  };
  fs.writeFileSync(path.join(directory,'mock.mjs'),capacityShim+`import fs from 'node:fs';const routes=${JSON.stringify(routes)},refs=new Map();
    const originalSetTimeout=globalThis.setTimeout;globalThis.setTimeout=(fn,ms,...args)=>originalSetTimeout(fn,ms===2000?0:ms,...args);
    globalThis.fetch=async(url,options)=>{
      const route=new URL(url).pathname.replace('/repos/owner/repo',''),body=options.body?JSON.parse(options.body):null;
      if(options.method==='PUT')throw Error('No PR merge authorized');
      if(route==='/git/refs'&&options.method==='POST'){refs.set(body.ref.replace('refs/heads/',''),body.sha);return Response.json({ref:body.ref},{status:201});}
      if(route==='/merges'&&options.method==='POST'){if(body.base==='main'||body.base==='engineering/test')throw Error('Protected branch update');refs.set(body.base,'${owned}');return Response.json({sha:'${owned}'},{status:201});}
      if(route.startsWith('/git/ref/heads/worldatlas-integration/'))return Response.json({object:{sha:refs.get(route.split('/git/ref/heads/')[1])}});
      if(options.method==='DELETE'){refs.delete(route.split('/git/refs/heads/')[1]);fs.writeFileSync('remaining-refs.json',JSON.stringify([...refs]));return new Response(null,{status:204});}
      if(route==='/issues/2/comments'&&options.method==='POST')return Response.json({},{status:403});
      return Response.json(routes[route]??{});
    };`);
  try {
    const result=spawnSync(process.execPath,['--import',path.join(directory,'mock.mjs'),path.join(root,'scripts/run-worker-merge.mjs')],{
      cwd:directory,encoding:'utf8',env:{...process.env,GITHUB_ACTIONS:'false',GH_TOKEN:'synthetic-token',GITHUB_REPOSITORY:'owner/repo',GITHUB_REF:'refs/heads/main',GITHUB_RUN_ID:'1234',
        GITHUB_EVENT_PATH:path.join(directory,'event.json'),GITHUB_OUTPUT:path.join(directory,'outputs'),GITHUB_STEP_SUMMARY:path.join(directory,'summary'),MERGE_PHASE:'prepare',PREPARE_FALLBACK:'true'}});
    const receipt=JSON.parse(fs.readFileSync(path.join(directory,'merge-result.json')));
    assert.notEqual(result.status,0);assert.match(result.stderr,/POST.*HTTP 403/);
    assert.equal(receipt.accepted,false);assert.equal(receipt.status,'testing');assert.equal(receipt.tested_candidate,owned);
    assert.match(receipt.notification_error,/HTTP 403/);assert.equal(receipt.candidate_cleanup.status,'deleted');
    assert.deepEqual(JSON.parse(fs.readFileSync(path.join(directory,'remaining-refs.json'))),[]);
  } finally {fs.rmSync(directory,{recursive:true,force:true});}
});

for (const phase of ['prepare', 'merge']) test(`actual ${phase} replay accepts matching merged head despite missing jobs and denied comment`, () => {
  const {result, receipt} = run({phase, commentFails: true});
  assert.equal(result.status, 0, result.stderr); assert.equal(receipt.accepted, true);
  assert.equal(receipt.merge_commit, 'b'.repeat(40)); assert.match(receipt.notification_error, /403/);
});
for (const integration of ['failure', 'cancelled', 'skipped']) test(`actual final ${integration} run fails when PR is still open`, () => {
  const {result, receipt} = run({phase: 'merge', merged: false, integration});
  assert.notEqual(result.status, 0); assert.equal(receipt.accepted, false);
});
test('actual final replay refuses a different merged head', () => {
  const {result, receipt} = run({phase: 'merge', head: 'c'.repeat(40)});
  assert.notEqual(result.status, 0); assert.equal(receipt.accepted, false); assert.match(receipt.reason, /head changed/);
});
test('native Actions concurrency holds the full existing lifecycle without custom scheduling', () => {
  const yaml = fs.readFileSync(path.join(root, '.github/workflows/worker-merge.yml'), 'utf8');
  assert.match(yaml, /concurrency:\n  group: worldatlas-main-integrate\n  queue: max\n  cancel-in-progress: false\n/);
  assert.doesNotMatch(yaml, /queue_attempt|QUEUE_ADMISSION|  wake:/);
  assert.ok(yaml.indexOf('concurrency:') < yaml.indexOf('jobs:'));
  for (const stage of ['prepare', 'integration', 'geography', 'merge']) assert.match(yaml, new RegExp('  ' + stage + ':\\n'));
});

test('actual final refusal reconciles a concurrent matching-head merge without redispatch', () => {
  const {result, receipt} = run({phase: 'merge', merged: false, integration: 'cancelled', mergeOnReconcile: true, commentFails: true});
  assert.equal(result.status, 0, result.stderr); assert.equal(receipt.accepted, true);
  assert.equal(receipt.status, 'already-merged'); assert.equal(receipt.merge_commit, 'b'.repeat(40));
  assert.match(receipt.reason, /cancelled/); assert.match(receipt.notification_error, /403/);
});
for (const phase of ['prepare', 'merge']) test(`actual ${phase} cannot accept merged state without a merge commit`, () => {
  const {result, receipt} = run({phase, mergeCommit: null});
  assert.notEqual(result.status, 0); assert.equal(receipt.accepted, false); assert.match(receipt.reason, /no confirmed merge commit/);
});

function hostedDeadlineRun({phase = 'merge', ageSeconds = 0, expire = false, corrupt = false, foreignJob = false,
  malformedMetadata = false, pending = false, badWorkflow = false, metadataNetworkFailure = false} = {}) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'atlas-merge-deadline-'));
  fs.mkdirSync(path.join(directory, '.github'));
  fs.copyFileSync(path.join(root, '.github/evidence-policy.json'), path.join(directory, '.github/evidence-policy.json'));
  const request = 'deadline-entrypoint-request', reference = `worldatlas-integration/pr-2-${request}-1234`;
  fs.writeFileSync(path.join(directory, 'event.json'), JSON.stringify({inputs: {pr_number: '2', expected_head: 'a'.repeat(40), request_id: request}}));
  const workflow = fs.readFileSync(path.join(root, '.github/workflows/worker-merge.yml'));
  const file = {type: 'file', path: '.github/workflows/worker-merge.yml', encoding: 'base64', size: workflow.length,
    sha: createHash('sha1').update(`blob ${workflow.length}\0`).update(workflow).digest('hex'), content: workflow.toString('base64')};
  if (corrupt) file.content = Buffer.from('changed workflow').toString('base64');
  fs.writeFileSync(path.join(directory, 'calls.json'), '[]');
  fs.writeFileSync(path.join(directory, 'mock.mjs'), capacityShim + `
    import fs from 'node:fs'; import {performance} from 'node:perf_hooks';
    const realNow = performance.now.bind(performance), wall = Date.now(); let elapsed = 0, jobs = 0;
    Object.defineProperty(performance, 'now', {value: () => realNow() + elapsed});
    const calls = []; globalThis.fetch = async (url, options) => {
      const route = new URL(url).pathname; calls.push({route, method: options.method});
      fs.writeFileSync('calls.json', JSON.stringify(calls));
      if (options.method === 'PUT') throw Error('No new merge is allowed');
      if (route.includes('/contents/')) return Response.json(${JSON.stringify(file)});
      if (route.includes('/attempts/1/jobs')) {
        if (${metadataNetworkFailure}) throw Error('Metadata transport failure');
        jobs++; return Response.json(${malformedMetadata} ? {} : {total_count: 1, jobs: [{id: 51, name: '${phase}',
          run_id: 1234, run_attempt: 1, status: ${pending} && jobs === 1 ? 'queued' : 'in_progress',
          started_at: new Date(wall - ${ageSeconds} * 1000).toISOString()}]});
      }
      if (route.endsWith('/pulls/2')) {
        if (${expire}) elapsed += ${phase === 'merge' ? 75 : 10} * 60000 - ${ageSeconds} * 1000 - 27000;
        return Response.json({merged: ${!(corrupt || foreignJob || malformedMetadata || badWorkflow || metadataNetworkFailure || ageSeconds >= (phase === 'merge' ? 75 : 10) * 60 - 40)}, head: {sha: 'a'.repeat(40)}, merge_commit_sha: 'b'.repeat(40)});
      }
      if (options.method === 'DELETE') return new Response(null, {status: 204});
      return Response.json(route.includes('/git/ref/heads/') ? {object: {sha: 'b'.repeat(40)}} : {});
    };
  `);
  try {
    const result = spawnSync(process.execPath, ['--import', path.join(directory, 'mock.mjs'), path.join(root, 'scripts/run-worker-merge.mjs')], {
      cwd: directory, encoding: 'utf8', timeout: 10000, env: {...process.env,
        GH_TOKEN: 'synthetic-deadline-token', GITHUB_ACTIONS: 'true', GITHUB_REPOSITORY: 'owner/repo', GITHUB_REF: 'refs/heads/main',
        GITHUB_RUN_ID: '1234', GITHUB_RUN_ATTEMPT: '1', GITHUB_JOB: foreignJob ? 'geography' : phase,
        GITHUB_WORKFLOW_SHA: 'c'.repeat(40), GITHUB_WORKFLOW_REF: 'owner/repo/.github/workflows/' + (badWorkflow ? 'foreign.yml' : 'worker-merge.yml') + '@refs/heads/main',
        GITHUB_EVENT_PATH: path.join(directory, 'event.json'), GITHUB_OUTPUT: path.join(directory, 'outputs'), GITHUB_STEP_SUMMARY: path.join(directory, 'summary'),
        MERGE_PHASE: phase, INTEGRATION_RESULT: 'success', GEOGRAPHY_RESULT: 'success', TESTED_CANDIDATE: 'b'.repeat(40), CANDIDATE_REF: reference}});
    const receipt = JSON.parse(fs.readFileSync(path.join(directory, 'merge-result.json')));
    const calls = JSON.parse(fs.readFileSync(path.join(directory, 'calls.json')));
    return {result, receipt, calls};
  } finally {fs.rmSync(directory, {recursive: true, force: true});}
}
for (const [phase, minutes] of [['prepare', 10], ['merge', 75]]) {
  test(`actual ${phase} HTTP deadline binds authenticated job start and executing workflow`, () => {
    const {result, receipt, calls} = hostedDeadlineRun({phase, ageSeconds: 30, pending: true});
    assert.equal(result.status, 0, result.stderr); assert.equal(receipt.accepted, true);
    assert.equal(receipt.job_deadline.timeout_minutes, minutes); assert.equal(receipt.job_deadline.finalization_ms, 30000);
    assert.equal(receipt.job_deadline.metadata_reads, 2); assert.equal(receipt.job_deadline.phase, phase);
    assert.equal(calls.filter(row => row.route.includes('/contents/')).length, 1);
    assert(!calls.some(row => row.route === '/rate_limit'));
  });
  for (const remaining of [40, 19, 0, -60]) test(`actual ${phase} startup refuses ${remaining}s remaining without post-refusal HTTP`, () => {
    const {receipt, calls} = hostedDeadlineRun({phase, ageSeconds: minutes * 60 - remaining});
    assert.equal(receipt.accepted, false); assert.match(receipt.reason, /deadline exhausted/);
    assert.equal(receipt.job_deadline_exhausted, true);
    assert.equal(calls.length, 2, 'Only immutable workflow and authenticated job metadata may be fetched');
    assert(calls.every(row => row.method === 'GET' && /\/contents\/|\/attempts\/1\/jobs$/.test(row.route)));
    assert.match(receipt.notification_error, /deadline/);
  });
  test(`actual ${phase} starts with a valid near-ceiling deadline and reserves finalization time`, () => {
    const {result, receipt, calls} = hostedDeadlineRun({phase, ageSeconds: minutes * 60 - 55});
    assert.equal(result.status, 0, result.stderr); assert.equal(receipt.accepted, true);
    assert.equal(receipt.job_deadline.timeout_minutes, minutes);
    assert.equal(receipt.job_deadline.finalization_ms, 30000);
    assert.equal(calls.filter(row => row.method === 'POST').length, 1);
  });
}
test('actual final work expiry leaves the existing reserved time usable for owned cleanup and notification', () => {
  const {result, receipt, calls} = hostedDeadlineRun({expire: true, ageSeconds: 60});
  assert.notEqual(result.status, 0); assert.equal(receipt.accepted, false); assert.equal(receipt.job_deadline_exhausted, true);
  assert.equal(receipt.candidate_cleanup.status, 'deleted'); assert.equal(receipt.notification_error, undefined);
  assert.equal(calls.filter(row => row.method === 'DELETE').length, 1);
  assert.equal(calls.filter(row => row.method === 'POST').length, 1);
  assert.equal(calls.filter(row => row.route.endsWith('/pulls/2')).length, 1, 'Normal reconciliation cannot spend the cleanup reserve');
});
for (const phase of ['prepare', 'merge']) for (const option of ['corrupt', 'foreignJob', 'malformedMetadata', 'badWorkflow', 'metadataNetworkFailure'])
  test(`actual ${phase} deadline rejects ${option} without post-refusal HTTP`, () => {
    const {receipt, calls} = hostedDeadlineRun({phase, [option]: true});
    assert.equal(receipt.accepted, false);
    assert(calls.every(row => row.method === 'GET' && /\/contents\/|\/attempts\/1\/jobs$/.test(row.route)));
    assert.match(receipt.reason, /workflow|job|inventory|metadata|Metadata/);
    assert.match(receipt.notification_error, /deadline/);
  });
