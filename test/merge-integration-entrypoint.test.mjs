import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

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
