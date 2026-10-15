import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
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

function run({readFails=false,commentFails=false,phase='prepare',merged=true,head='a'.repeat(40),integration='skipped',geography='skipped',mergeOnReconcile=false,mergeCommit='b'.repeat(40),hosted=false}={}) {
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-merge-entry-'));
  fs.mkdirSync(path.join(directory,'.github'));
  fs.copyFileSync(path.join(root,'.github/evidence-policy.json'),path.join(directory,'.github/evidence-policy.json'));
  fs.writeFileSync(path.join(directory,'event.json'),JSON.stringify({inputs:{pr_number:'2',expected_head:'a'.repeat(40),request_id:'entrypoint-test-request'}}));
  fs.writeFileSync(path.join(directory,'mock.mjs'),capacityShim+`let reads=0;globalThis.fetch=async(url,options)=> {
    if(options.method==='PUT')throw Error('Unexpected new merge');
    if(new URL(url).pathname.includes('/contents/')||new URL(url).pathname.includes('/attempts/'))throw Error('Job-clock metadata must not be fetched');
    const posting=options.method==='POST';
    if(new URL(url).pathname.endsWith('/pulls/2'))reads++;
    return new Response(JSON.stringify(posting?{}:{merged:${merged}||(${mergeOnReconcile}&&reads>1),head:{sha:'${head}'},merge_commit_sha:${JSON.stringify(mergeCommit)}}),
      {status:posting?${commentFails?403:201}:${readFails?418:200},headers:{'Content-Type':'application/json'}});
  };`);
  const result=spawnSync(process.execPath,['--import',path.join(directory,'mock.mjs'),path.join(root,'scripts/run-worker-merge.mjs')],{
    cwd:directory,encoding:'utf8',env:{...process.env,GITHUB_ACTIONS:String(hosted),GH_TOKEN:'synthetic-test-token',GITHUB_REPOSITORY:'owner/repo',GITHUB_REF:'refs/heads/main',
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

test('failed-job retries retain current smoke artifacts without duplicate diagnostic result uploads',()=>{
  const yaml=fs.readFileSync(path.join(root,'.github/workflows/worker-merge.yml'),'utf8');
  assert(yaml.includes('name: selected-delivery-smoke-${{ inputs.request_id }}-${{ github.run_attempt }}'));
  assert.doesNotMatch(yaml,/path: merge-result\.json|name: merge-preflight-/);
  assert.doesNotMatch(yaml,/overwrite: true/);
});

test('actual entry point logs the exact complete result when bot notification fails',()=>{
  for(const accepted of [false,true]){
    const {result,receipt}=run({phase:accepted?'merge':'prepare',merged:accepted,
      readFails:!accepted,commentFails:true});
    const logged=result.stdout.trim().split('\n').map(line=>{
      try{return JSON.parse(line);}catch{return null;}
    }).filter(row=>row?.request_id==='entrypoint-test-request');
    assert(logged.length>=2,'The original decision and notification failure must both be preserved');
    assert.deepEqual(logged.at(-1),receipt,'Every receipt field survives in actual subprocess stdout');
    assert.equal(receipt.accepted,accepted);
    assert.match(receipt.notification_error,/POST.*HTTP 403/);
    assert.equal(result.status,accepted?0:1);
  }
});

test('actual entry point saves owned-parent/head/conflict/base diagnostics when notification fails',()=>{
 for(const kind of ['parents','head','conflict','base']) {
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-merge-diagnostics-'));
  const sha=c=>c.repeat(40),head=sha('a'),base=sha('b'),candidate=sha('c');
  fs.mkdirSync(path.join(directory,'.github'));
  fs.copyFileSync(path.join(root,'.github/evidence-policy.json'),path.join(directory,'.github/evidence-policy.json'));
  fs.writeFileSync(path.join(directory,'event.json'),JSON.stringify({inputs:{pr_number:'2',expected_head:head,request_id:'diagnostics-test-request'}}));
  const issue={number:1,state:'open',created_at:'2020-01-01T00:00:00Z',labels:['type:engineering','kind:work-item','status:ready'],
    body:'<!-- worldatlas-work:v1\n'+JSON.stringify({mode:'engineering',max_prs:2,depends_on:[],scope:'code'})+'\n-->'};
  const pr={number:2,state:'open',draft:false,body:'Closes #1',title:'Repair',changed_files:1,
    head:{sha:head,ref:'engineering/test',repo:{full_name:'owner/repo'}},base:{ref:'main',sha:base},merge_commit_sha:null};
  const routes={
    '/pulls/2':pr,'/issues/1':issue,'/issues/1/timeline':[],
    '/issues/1/comments':[{id:1,user:{login:'github-actions[bot]'},body:renderClaim({version:1,active:true,worker_id:'worker',claim_id:'nonce',branch:'engineering/test',expires_at:new Date(Date.now()+3600000).toISOString()})}],
    '/pulls/2/files':[{filename:'src/a.js',status:'modified'}],
    ['/commits/'+head+'/check-runs']:{check_runs:[{id:1,name:'scope',app:{id:1},status:'completed',conclusion:'success'}]},
    ['/commits/'+head+'/status']:{statuses:[]},'/git/ref/heads/main':{object:{sha:base}},
    ['/git/commits/'+candidate]:{sha:candidate,tree:{sha:sha('f')},parents:[{sha:kind==='parents'?sha('e'):base},{sha:head}]}
  };
  fs.writeFileSync(path.join(directory,'mock.mjs'),capacityShim+`import fs from 'node:fs';const routes=${JSON.stringify(routes)},refs=new Map();
    let prReads=0,baseReads=0;
    globalThis.fetch=async(url,options)=>{
      const route=new URL(url).pathname.replace('/repos/owner/repo',''),body=options.body?JSON.parse(options.body):null;
      if(route==='/git/refs'&&options.method==='POST'){refs.set(body.ref.replace('refs/heads/',''),body.sha);return Response.json({ref:body.ref},{status:201});}
      if(route==='/merges'&&options.method==='POST'){
        if(body.base==='main'||body.base==='engineering/test')throw Error('Protected branch update');
        if('${kind}'==='conflict')return Response.json({},{status:409});
        refs.set(body.base,'${candidate}');return Response.json({sha:'${candidate}'},{status:201});
      }
      if(route.startsWith('/git/ref/heads/worldatlas-integration/'))return Response.json({object:{sha:refs.get(route.split('/git/ref/heads/')[1])}});
      if(options.method==='DELETE'){refs.delete(route.split('/git/refs/heads/')[1]);fs.writeFileSync('remaining-refs.json',JSON.stringify([...refs]));return new Response(null,{status:204});}
      if(route==='/pulls/2'&&++prReads===2&&'${kind}'==='head')routes[route].head.sha='d'.repeat(40);
      if(route==='/git/ref/heads/main'&&++baseReads===2&&'${kind}'==='base')routes[route].object.sha='d'.repeat(40);
      return Response.json(options.method==='POST'?{}:routes[route]??{},{status:options.method==='POST'?403:200});
    };`);
  try {
    const result=spawnSync(process.execPath,['--import',path.join(directory,'mock.mjs'),path.join(root,'scripts/run-worker-merge.mjs')],{
      cwd:directory,encoding:'utf8',env:{...process.env,GITHUB_ACTIONS:'false',GH_TOKEN:'synthetic-token',GITHUB_REPOSITORY:'owner/repo',GITHUB_REF:'refs/heads/main',
        GITHUB_EVENT_PATH:path.join(directory,'event.json'),GITHUB_OUTPUT:path.join(directory,'outputs'),GITHUB_STEP_SUMMARY:path.join(directory,'summary'),MERGE_PHASE:'prepare'}});
    const receipt=JSON.parse(fs.readFileSync(path.join(directory,'merge-result.json')));
    assert.notEqual(result.status,0);assert.match(result.stderr,/HTTP 403/);
    assert.equal(receipt.retryable,kind==='parents'||kind==='base');
    assert.equal(receipt.candidate_diagnostics.expected_base,base);
    assert.equal(receipt.candidate_diagnostics.expected_head,head);
    assert.equal(receipt.candidate_diagnostics.candidate,kind==='conflict'?null:candidate);
    if(kind==='parents')assert.deepEqual(receipt.candidate_diagnostics.actual_parents,[sha('e'),head]);
    else {
      assert.equal(receipt.candidate_diagnostics.reason,{head:'head-changed',conflict:'conflict',base:'base-advanced'}[kind]);
      assert.ok(receipt.candidate_diagnostics.observed_at);
    }
    assert.deepEqual(JSON.parse(fs.readFileSync(path.join(directory,'remaining-refs.json'))),[]);
    assert.match(fs.readFileSync(path.join(directory,'summary'),'utf8'),/exact current main|head changed|conflict|base advanced/);
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

test('actual owned prepare skips preview polling and cleans its ref when notification is denied',()=>{
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
    const originalSetTimeout=globalThis.setTimeout;globalThis.setTimeout=(fn,ms,...args)=>{if(ms===2000)throw Error('Unexpected candidate polling sleep');return originalSetTimeout(fn,ms,...args);};
    globalThis.fetch=async(url,options)=>{
      const route=new URL(url).pathname.replace('/repos/owner/repo',''),body=options.body?JSON.parse(options.body):null;
      if(route==='/git/commits/${candidate}')throw Error('Automatic preview must not be read');
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
        GITHUB_EVENT_PATH:path.join(directory,'event.json'),GITHUB_OUTPUT:path.join(directory,'outputs'),GITHUB_STEP_SUMMARY:path.join(directory,'summary'),MERGE_PHASE:'prepare'}});
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

test('actual queue entry points omit geography only for independently rechecked controls', () => {
  for (const phase of ['prepare','merge']) {
    const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-control-geography-'));
    const sha=c=>c.repeat(40), head=sha('a'),base=sha('b'),candidate=sha('c');
    const files=['scripts/merge-integration.mjs','test/merge-integration.test.mjs'].map(filename=>({filename,status:'modified'}));
    const rows=files.map(file=>({path:file.filename,sha:sha('e'),mode:'100644',type:'blob'}));
    const issue={number:1,state:'open',created_at:'2020-01-01T00:00:00Z',labels:['type:engineering','kind:work-item','status:ready'],
      body:'<!-- worldatlas-work:v1\n'+JSON.stringify({mode:'engineering',max_prs:1,depends_on:[],scope:'queue controls'})+'\n-->'};
    const pr={number:2,state:'open',draft:false,body:'Closes #1',title:'Repair controls',changed_files:files.length,
      head:{sha:head,ref:'engineering/controls',repo:{full_name:'owner/repo'}},base:{ref:'main',sha:base},mergeable:true};
    const routes={
      '/pulls/2':pr,'/issues/1':issue,'/pulls/2/files':files,
      ['/commits/'+head+'/check-runs']:{check_runs:[{id:1,name:'scope',app:{id:1},status:'completed',conclusion:'success'}]},
      ['/commits/'+head+'/status']:{statuses:[]},'/git/ref/heads/main':{object:{sha:base}},
      ['/git/commits/'+head]:{tree:{sha:sha('6')}},['/git/trees/'+sha('6')]:{truncated:false,tree:rows},
      ['/git/commits/'+candidate]:{sha:candidate,tree:{sha:sha('7')},parents:[{sha:base},{sha:head}]},
      ['/git/trees/'+sha('7')]:{truncated:false,tree:rows}
    };
    fs.mkdirSync(path.join(directory,'.github'));
    fs.copyFileSync(path.join(root,'.github/evidence-policy.json'),path.join(directory,'.github/evidence-policy.json'));
    fs.writeFileSync(path.join(directory,'event.json'),JSON.stringify({inputs:{pr_number:'2',expected_head:head,request_id:'control-geography-entrypoint'}}));
    fs.writeFileSync(path.join(directory,'mock.mjs'),capacityShim+`import fs from 'node:fs';const routes=${JSON.stringify(routes)},refs=new Map();
      globalThis.fetch=async(url,options)=>{
        const route=new URL(url).pathname.replace('/repos/owner/repo',''),body=options.body?JSON.parse(options.body):null;
        if(route==='/git/refs'&&options.method==='POST'){refs.set(body.ref.replace('refs/heads/',''),body.sha);return Response.json({ref:body.ref},{status:201});}
        if(route==='/merges'&&options.method==='POST'){refs.set(body.base,'${candidate}');return Response.json({sha:'${candidate}'},{status:201});}
        if(route.startsWith('/git/ref/heads/worldatlas-integration/'))return Response.json({object:{sha:refs.get(route.split('/git/ref/heads/')[1])}});
        if(route==='/pulls/2/merge'&&options.method==='PUT'){fs.writeFileSync('merge-write.json',JSON.stringify(body));return Response.json({merged:true,sha:'${sha('f')}'});}
        if(route==='/issues/2/comments'&&options.method==='POST')return Response.json({},{status:201});
        if(!Object.hasOwn(routes,route))throw Error('Unexpected geography or external request: '+route);
        return Response.json(routes[route]);
      };`);
    try {
      const result=spawnSync(process.execPath,['--import',path.join(directory,'mock.mjs'),path.join(root,'scripts/run-worker-merge.mjs')],{
        cwd:directory,encoding:'utf8',env:{...process.env,GITHUB_ACTIONS:'false',GH_TOKEN:'synthetic-token',
          GITHUB_REPOSITORY:'owner/repo',GITHUB_REF:'refs/heads/main',GITHUB_EVENT_PATH:path.join(directory,'event.json'),
          GITHUB_OUTPUT:path.join(directory,'outputs'),GITHUB_STEP_SUMMARY:path.join(directory,'summary'),MERGE_PHASE:phase,
          INTEGRATION_RESULT:'success',GEOGRAPHY_RESULT:'skipped',TESTED_BASE:base,TESTED_CANDIDATE:candidate,CANDIDATE_REF:''}});
      assert.equal(result.status,0,result.stderr);
      const receipt=JSON.parse(fs.readFileSync(path.join(directory,'merge-result.json')));
      if(phase==='prepare') {
        assert.equal(receipt.geography_required,false);
        assert.match(fs.readFileSync(path.join(directory,'outputs'),'utf8'),/^geography_required=false$/m);
        assert.equal(fs.existsSync(path.join(directory,'merge-write.json')),false);
      } else {
        assert.equal(receipt.accepted,true);
        assert.deepEqual(receipt.geography,{status:'not-applicable',reason:'non-geographic-controls'});
        assert.equal(JSON.parse(fs.readFileSync(path.join(directory,'merge-write.json'))).sha,head);
      }
    } finally {fs.rmSync(directory,{recursive:true,force:true});}
  }
  const yaml=fs.readFileSync(path.join(root,'.github/workflows/worker-merge.yml'),'utf8');
  assert.match(yaml,/geography_required: \$\{\{ steps\.prepare\.outputs\.geography_required \}\}/);
  assert.match(yaml,/if: needs\.prepare\.outputs\.candidate != '' && needs\.prepare\.outputs\.geography_required != 'false'/);
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


for (const phase of ['prepare', 'merge']) {
  test(`hosted ${phase} uses the existing Actions timeout without job-clock metadata admission`, () => {
    const {result, receipt} = run({phase, hosted: true});
    assert.equal(result.status, 0, result.stderr);
    assert.equal(receipt.accepted, true);
    assert.equal(receipt.status, phase === 'prepare' ? 'already-merged' : 'merged');
    assert.equal(receipt.job_deadline, undefined);
    assert.equal(receipt.request_accounting.actual_http_attempts, phase === 'prepare' ? 2 : 3);
  });
  test(`hosted ${phase} retains actual API denial and durable refusal without metadata admission`, () => {
    const {result, receipt} = run({phase, hosted: true, readFails: true, commentFails: true});
    assert.notEqual(result.status, 0);
    assert.equal(receipt.accepted, false);
    assert.equal(receipt.api_error.http_status, 418);
    assert.equal(receipt.notification_api_error.http_status, 403);
    assert.match(receipt.reason, /GET.*HTTP 418/);
  });
}
