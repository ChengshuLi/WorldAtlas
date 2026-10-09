import test from 'node:test';
import assert from 'node:assert/strict';
import {observeSetupPhase,measuredGitSetup} from '../scripts/ci-setup-observations.mjs';
test('setup observations separate Git command time from unobserved transport waits',async()=>{
 let tick=0;const rows=[],git=measuredGitSetup({clock:()=>++tick,run:()=>({status:0})});
 const result=await observeSetupPhase('immutable-regression-inputs',()=>{
  git.run('git',['cat-file','-e','original^{commit}']);git.run('git',['fetch','--no-tags','origin','original']);return 'complete';
 },{emit:r=>rows.push(r),clock:()=>++tick,counters:git.snapshot});
 assert.equal(result,'complete');assert.equal(rows.length,2);assert.equal(rows[1].status,'success');
 assert.equal(rows[1].counters.git_command_attempts,2);assert.equal(rows[1].counters.git_fetch_attempts,1);
 assert.equal(rows[1].counters.git_command_elapsed_ms,2);assert.equal(rows[1].counters.git_fetch_elapsed_ms,1);
 assert.equal(rows[1].counters.http_observation_ms,null);assert.equal(rows[1].counters.transport_quota_sleep_ms,null);
});
test('failed setup preserves the original error and records failure without claiming zero transport waits',async()=>{
 const rows=[],error=Error('invalid consumed body');await assert.rejects(()=>observeSetupPhase('canonical-checkout',()=>{throw error;},{emit:r=>rows.push(r)}),e=>e===error);
 assert.equal(rows[1].status,'failed');assert.equal(rows[1].counters.http_observation_ms,null);
});
test('Git failures are counted without being retried or converted to quota waits',()=>{
 let calls=0;const error=Error('permission denied'),git=measuredGitSetup({run:()=>{calls++;throw error;}});
 assert.throws(()=>git.run('git',['fetch','origin','original']),e=>e===error);assert.equal(calls,1);assert.equal(git.snapshot().git_fetch_attempts,1);
});
