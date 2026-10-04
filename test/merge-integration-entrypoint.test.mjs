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

test('actual entry point saves candidate diagnostics even when notification fails',()=>{
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
    globalThis.fetch=async(url,options)=>{
      const route=new URL(url).pathname.replace('/repos/owner/repo','');
      return new Response(JSON.stringify(options.method==='POST'?{}:routes[route]??{}),{status:options.method==='POST'?403:200,headers:{'Content-Type':'application/json'}});
    };`);
  try {
    const result=spawnSync(process.execPath,['--import',path.join(directory,'mock.mjs'),path.join(root,'scripts/run-worker-merge.mjs')],{
      cwd:directory,encoding:'utf8',env:{...process.env,GH_TOKEN:'synthetic-token',GITHUB_REPOSITORY:'owner/repo',GITHUB_REF:'refs/heads/main',
        GITHUB_EVENT_PATH:path.join(directory,'event.json'),GITHUB_OUTPUT:path.join(directory,'outputs'),GITHUB_STEP_SUMMARY:path.join(directory,'summary'),MERGE_PHASE:'prepare'}});
    const receipt=JSON.parse(fs.readFileSync(path.join(directory,'merge-result.json')));
    assert.notEqual(result.status,0);assert.match(result.stderr,/HTTP 403/);
    assert.equal(receipt.retryable,true);assert.equal(receipt.candidate_diagnostics.attempt,6);
    assert.equal(receipt.candidate_diagnostics.expected_base,base);
    assert.equal(receipt.candidate_diagnostics.candidate,candidate);
    assert.deepEqual(receipt.candidate_diagnostics.actual_parents,[sha('e'),head]);
    assert.match(fs.readFileSync(path.join(directory,'summary'),'utf8'),/bounded refresh/);
  } finally {fs.rmSync(directory,{recursive:true,force:true});}
});
