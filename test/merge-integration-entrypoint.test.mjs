import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {renderClaim} from '../scripts/issue-claim-contract.mjs';

const root=path.resolve(import.meta.dirname,'..');
function run({readFails=false,commentFails=false}={}) {
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-merge-entry-'));
  fs.mkdirSync(path.join(directory,'.github'));
  fs.copyFileSync(path.join(root,'.github/evidence-policy.json'),path.join(directory,'.github/evidence-policy.json'));
  fs.writeFileSync(path.join(directory,'event.json'),JSON.stringify({inputs:{pr_number:'2',expected_head:'a'.repeat(40),request_id:'entrypoint-test-request'}}));
  fs.writeFileSync(path.join(directory,'mock.mjs'),`globalThis.fetch=async(url,options)=> {
    const posting=options.method==='POST';
    return new Response(JSON.stringify(posting?{}:{merged:true,head:{sha:'a'.repeat(40)},merge_commit_sha:'b'.repeat(40)}),
      {status:posting?${commentFails?403:201}:${readFails?418:200},headers:{'Content-Type':'application/json'}});
  };`);
  const result=spawnSync(process.execPath,['--import',path.join(directory,'mock.mjs'),path.join(root,'scripts/run-worker-merge.mjs')],{
    cwd:directory,encoding:'utf8',env:{...process.env,GH_TOKEN:'synthetic-test-token',GITHUB_REPOSITORY:'owner/repo',GITHUB_REF:'refs/heads/main',
      GITHUB_EVENT_PATH:path.join(directory,'event.json'),GITHUB_OUTPUT:path.join(directory,'outputs'),GITHUB_STEP_SUMMARY:path.join(directory,'summary'),MERGE_PHASE:'prepare'}});
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
  assert.equal(receipt.status,'already-merged');assert.equal(receipt.accepted,false);
});
test('trusted preparation has PR comment permission while candidate tests remain read-only',()=>{
  const yaml=fs.readFileSync(path.join(root,'.github/workflows/worker-merge.yml'),'utf8');
  assert.match(yaml.split('  prepare:\n')[1].split('  integration:\n')[0],/pull-requests: write/);
  const candidate=yaml.split('  integration:\n')[1].split('  merge:\n')[0];
  assert.match(candidate,/permissions:\n      contents: read/);assert.doesNotMatch(candidate,/pull-requests: write|issues: write|GH_TOKEN|secrets\./);
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
  fs.writeFileSync(path.join(directory,'mock.mjs'),`const routes=${JSON.stringify(routes)};
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
      cwd:directory,encoding:'utf8',env:{...process.env,GH_TOKEN:'synthetic-token',GITHUB_REPOSITORY:'owner/repo',GITHUB_REF:'refs/heads/main',
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
    fs.writeFileSync(path.join(directory,'mock.mjs'),`globalThis.fetch=async(url,options)=>{
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
        cwd:directory,encoding:'utf8',env:{...process.env,GH_TOKEN:'synthetic-token',GITHUB_REPOSITORY:'owner/repo',GITHUB_REF:'refs/heads/main',
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
  fs.writeFileSync(path.join(directory,'mock.mjs'),`import fs from 'node:fs';const routes=${JSON.stringify(routes)},refs=new Map();
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
      cwd:directory,encoding:'utf8',env:{...process.env,GH_TOKEN:'synthetic-token',GITHUB_REPOSITORY:'owner/repo',GITHUB_REF:'refs/heads/main',GITHUB_RUN_ID:'1234',
        GITHUB_EVENT_PATH:path.join(directory,'event.json'),GITHUB_OUTPUT:path.join(directory,'outputs'),GITHUB_STEP_SUMMARY:path.join(directory,'summary'),MERGE_PHASE:'prepare',PREPARE_FALLBACK:'true'}});
    const receipt=JSON.parse(fs.readFileSync(path.join(directory,'merge-result.json')));
    assert.notEqual(result.status,0);assert.match(result.stderr,/POST.*HTTP 403/);
    assert.equal(receipt.accepted,false);assert.equal(receipt.status,'testing');assert.equal(receipt.tested_candidate,owned);
    assert.match(receipt.notification_error,/HTTP 403/);assert.equal(receipt.candidate_cleanup.status,'deleted');
    assert.deepEqual(JSON.parse(fs.readFileSync(path.join(directory,'remaining-refs.json'))),[]);
  } finally {fs.rmSync(directory,{recursive:true,force:true});}
});
