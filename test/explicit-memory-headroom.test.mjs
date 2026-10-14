import test from 'node:test';
import assert from 'node:assert/strict';
import {processingAllowance} from '../scripts/check-effective-geographic-regression.mjs';
import {preparationAllowance,preparationRequestAllowance,candidateBudget} from '../scripts/native-ownership/native-preparation-guards.mjs';
import {jointExecutionAllowance} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-joint-entry.mjs';
const guards=[processingAllowance,preparationAllowance,jointExecutionAllowance];
const observation={availableBytes:1401257984,currentRssBytes:52576256,concurrentReservedBytes:0};

test('real Myanmar refusal separates configurable headroom from unmeasured target demand',()=>{
 const historicalChildPeak=995868672;
 assert.equal(observation.currentRssBytes+Math.floor(observation.availableBytes/2),753205248);
 // This is the exact arithmetic boundary, not a recommended operating reserve
 // or a measurement of the new coastal workload. No science is executed here.
 const remaining=observation.availableBytes-historicalChildPeak;
 assert.equal(remaining,405389312);
 for(const guard of guards){
  const sameProcess=guard({...observation,headroomBytes:remaining});
  assert.equal(sameProcess.rssBytes,historicalChildPeak+observation.currentRssBytes);
  // A separate not-yet-launched child has no resident credit from its parent.
  const child=guard({...observation,currentRssBytes:0,headroomBytes:remaining});
  assert.equal(child.rssBytes,historicalChildPeak);
  assert(guard({...observation,currentRssBytes:0,headroomBytes:remaining+1}).rssBytes<historicalChildPeak);
  // Actual nearby observed variation exceeds that residual. Admission cannot
  // claim the historical estimate fits when that variation is reserved.
  assert(guard({...observation,currentRssBytes:0,headroomBytes:572882944}).rssBytes<historicalChildPeak);
 }
});

test('all existing guards deduct explicit headroom and future concurrency exactly once',()=>{
 for(const guard of guards){
  const options={availableBytes:1000,currentRssBytes:100,concurrentReservedBytes:200,headroomBytes:150};
  assert.deepEqual(guard(options),{phaseBytes:750,rssBytes:750});
  assert.deepEqual(guard({...options,availableBytes:800}),{phaseBytes:550,rssBytes:550});
  assert.deepEqual(guard({...options,concurrentReservedBytes:400}),{phaseBytes:550,rssBytes:550});
  // Resident growth reduces availability by the same amount; it is not a new reservation.
  assert.deepEqual(guard({...options,availableBytes:800,currentRssBytes:300}),{phaseBytes:750,rssBytes:750});
  assert(Object.isFrozen(guard(options)));
 }
 for(const guard of [processingAllowance,preparationAllowance]){
  const options={availableBytes:1000,currentRssBytes:100,concurrentReservedBytes:200,headroomBytes:150};
  const prior=guard(options);
  assert.deepEqual(guard({...options,...prior}),prior);
  assert.throws(()=>guard({...options,...prior,availableBytes:999}),/admission/);
  assert.throws(()=>guard({...options,...prior,concurrentReservedBytes:201}),/admission/);
  assert.throws(()=>guard({...options,...prior,headroomBytes:151}),/admission/);
 }
});

test('absent policy preserves automatic sizing; invalid explicit policy never falls back',t=>{
 const old=process.env.WORLDATLAS_MEMORY_HEADROOM_BYTES;
 t.after(()=>{if(old===undefined)delete process.env.WORLDATLAS_MEMORY_HEADROOM_BYTES;else process.env.WORLDATLAS_MEMORY_HEADROOM_BYTES=old;});
 delete process.env.WORLDATLAS_MEMORY_HEADROOM_BYTES;
 for(const guard of guards){
  assert.deepEqual(guard(observation),{phaseBytes:753205248,rssBytes:753205248});
  for(const headroomBytes of [0,-1,NaN,Infinity,.5,Number.MAX_SAFE_INTEGER+1,'1',true])
   assert.throws(()=>guard({...observation,headroomBytes}),/headroomBytes/);
  for(const options of [{availableBytes:1,headroomBytes:1},{availableBytes:100,headroomBytes:50,concurrentReservedBytes:50}])
   assert.throws(()=>guard({...observation,...options}),/Insufficient/);
  assert.throws(()=>guard({...observation,headroomBytes:1,currentRssBytes:Number.MAX_SAFE_INTEGER}),/observations/);
 }
 process.env.WORLDATLAS_MEMORY_HEADROOM_BYTES='405389312';
 for(const guard of guards)assert.equal(guard({...observation,currentRssBytes:0}).rssBytes,995868672);
 for(const invalid of ['', '0','-1','NaN','Infinity','.5','9007199254740992']){
  process.env.WORLDATLAS_MEMORY_HEADROOM_BYTES=invalid;
  for(const guard of guards)assert.throws(()=>guard(observation),/headroomBytes/);
 }
});


test('explicit environment reaches fresh preparation revalidation and enforced budgets',t=>{
 const original=process.env.WORLDATLAS_MEMORY_HEADROOM_BYTES;
 const concurrent=process.env.WORLDATLAS_CONCURRENT_RESERVED_BYTES;
 t.after(()=>{for(const [key,value] of [['WORLDATLAS_MEMORY_HEADROOM_BYTES',original],['WORLDATLAS_CONCURRENT_RESERVED_BYTES',concurrent]]){
  if(value===undefined)delete process.env[key];else process.env[key]=value;
 }});
 process.env.WORLDATLAS_MEMORY_HEADROOM_BYTES='405389312';
 process.env.WORLDATLAS_CONCURRENT_RESERVED_BYTES='0';
 let available=observation.availableBytes;
 t.mock.method(process,'availableMemory',()=>available);
 t.mock.method(process,'memoryUsage',()=>({rss:observation.currentRssBytes}));
 const request={phaseBytes:995868672,rssBytes:995868672};
 assert(request.rssBytes>753205248);
 assert.deepEqual(processingAllowance(request),request);
 assert.deepEqual(preparationRequestAllowance(request),request);
 const budget=candidateBudget([],{allowance:request});
 assert.equal(budget.snapshot().rss_limit_bytes,request.rssBytes);
 available-=observation.currentRssBytes+1;
 assert.throws(()=>processingAllowance(request),/admission/);
 assert.throws(()=>preparationRequestAllowance(request),/admission/);
 process.env.WORLDATLAS_MEMORY_HEADROOM_BYTES='0';
 assert.throws(()=>candidateBudget([],{allowance:request}),/headroomBytes/);
});
