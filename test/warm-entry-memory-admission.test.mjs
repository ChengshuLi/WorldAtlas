import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {processingAllowance} from '../scripts/check-effective-geographic-regression.mjs';
import {preparationAllowance} from '../scripts/native-ownership/native-preparation-guards.mjs';
import {jointExecutionAllowance, JOINT_CODE} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-joint-entry.mjs';
import {trustedFixture} from './helpers/selected-joint-fixture.mjs';

const MiB = 1024 ** 2;
const idleSupply = [1818279936, 1737015296, 1760100352, 1590296576];

function currentObservations(t, state) {
  const args = [...process.execArgv], usage = process.memoryUsage();
  const saved = Object.fromEntries(['NODE_OPTIONS', 'NODE_PATH', 'WORLDATLAS_CONCURRENT_RESERVED_BYTES']
    .map(key => [key, process.env[key]]));
  t.after(() => {
    process.execArgv.splice(0, process.execArgv.length, ...args);
    for (const [key, value] of Object.entries(saved)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
  });
  process.execArgv.splice(0, process.execArgv.length, '--expose-gc');
  delete process.env.NODE_OPTIONS;
  delete process.env.NODE_PATH;
  delete process.env.WORLDATLAS_CONCURRENT_RESERVED_BYTES;
  t.mock.method(process, 'availableMemory', () => state.availableBytes);
  t.mock.method(process, 'memoryUsage', () => ({...usage, rss: state.currentRssBytes}));
}

test('pre-import joint allowance matches native/preparation admission at idle and loaded observations', () => {
  for (const availableBytes of idleSupply) {
    for (const concurrentReservedBytes of [0, 128 * MiB]) {
      const options = {availableBytes, concurrentReservedBytes, currentRssBytes: 51658752};
      const expected = {phaseBytes: options.currentRssBytes + Math.floor((availableBytes - concurrentReservedBytes) / 2),
        rssBytes: options.currentRssBytes + Math.floor((availableBytes - concurrentReservedBytes) / 2)};
      const allowance = jointExecutionAllowance(options);
      assert.deepEqual(allowance, expected);
      assert(Object.isFrozen(allowance));
      assert.deepEqual(processingAllowance(options), allowance);
      assert.deepEqual(preparationAllowance(options), allowance);
      const loaded = {...options, availableBytes: availableBytes - 400 * MiB,
        currentRssBytes: options.currentRssBytes + 400 * MiB};
      assert.deepEqual(jointExecutionAllowance(loaded), processingAllowance(loaded));
      assert(jointExecutionAllowance(loaded).phaseBytes >= allowance.phaseBytes);
      assert(jointExecutionAllowance(loaded).rssBytes - loaded.currentRssBytes <=
        Math.floor((loaded.availableBytes - concurrentReservedBytes) / 2));
    }
  }
});

test('joint admission refuses unknown/exhausted supply and unsafe measured sums', () => {
  const observation = {availableBytes: 1000, concurrentReservedBytes: 200, currentRssBytes: 100};
  assert.deepEqual(jointExecutionAllowance(observation), {phaseBytes: 500, rssBytes: 500});
  for (const key of Object.keys(observation)) for (const value of [-1, NaN, Infinity, .5, Number.MAX_SAFE_INTEGER + 1])
    assert.throws(() => jointExecutionAllowance({...observation, [key]: value}), /observations/);
  for (const availableBytes of [0, 1, 200, 201])
    assert.throws(() => jointExecutionAllowance({...observation, availableBytes}), /Insufficient/);
  assert.throws(() => jointExecutionAllowance({...observation, currentRssBytes: Number.MAX_SAFE_INTEGER}), /observations/);
  assert.deepEqual(jointExecutionAllowance({...observation, availableBytes: 202}), {phaseBytes: 101, rssBytes: 101});
});

test('actual qualified warm entry completes native validation at all reported idle observations', async t => {
  const f = await trustedFixture(t, {nativeOnly: true});
  const state = {availableBytes: idleSupply[0], currentRssBytes: 51658752};
  currentObservations(t, state);
  process.env.WORLDATLAS_CONCURRENT_RESERVED_BYTES = String(128 * MiB);
  const trusted = f.git('rev-parse', 'HEAD').toString().trim();
  for (const [index, availableBytes] of idleSupply.entries()) {
    state.availableBytes = availableBytes;
    const destination = path.join(f.root, 'idle-' + index);
    const result = await f.joint.selectedJointStage(f.root, trusted, f.selected, f.selected, destination);
    assert.equal(result.mode, 'authenticated-checkpoint-append-v1');
    assert.equal(result.native.status, 'no-new-native-loss');
    assert.equal(result.native.lost_or_reassigned_cells, 0);
    assert.equal(result.candidate_code_executed, false);
    assert.equal(result.continuous, undefined);
    assert.deepEqual(fs.readdirSync(destination).sort(), [
      'checkpoint-routes.json', 'derived-certificate.json.gz', 'derived-facts.json', 'derived-publication.json'
    ]);
  }
  assert(process.availableMemory.mock.callCount() >= 2 * idleSupply.length);
});

test('actual warm entry rejects invalid/reserved/exhausted supply before opening project bodies', async t => {
  const f = await trustedFixture(t);
  const state = {availableBytes: idleSupply.at(-1), currentRssBytes: 51658752};
  currentObservations(t, state);
  const trusted = f.git('rev-parse', 'HEAD').toString().trim();
  const open = t.mock.method(fs, 'readFileSync', () => assert.fail('Project body opened before admission'));
  for (const reservation of ['-1', 'NaN', 'Infinity', '0.5', '9007199254740992', String(state.availableBytes - 1), String(state.availableBytes)]) {
    process.env.WORLDATLAS_CONCURRENT_RESERVED_BYTES = reservation;
    const destination = path.join(f.root, 'refused');
    await assert.rejects(() => f.joint.selectedJointStage(f.root, trusted, f.selected, f.selected, destination),
      /observations|Insufficient/);
    assert.equal(fs.existsSync(destination), false);
  }
  assert.equal(open.mock.callCount(), 0);
});

test('actual joint code/runtime accounting retains its strict one-byte boundary before body opens', async t => {
  const f = await trustedFixture(t);
  const completeBytes = JOINT_CODE.reduce((sum, name) => sum + 2 * fs.statSync(path.join(f.root, name)).size, 0)
    + fs.statSync(process.execPath).size + 8 * MiB + 32 * MiB;
  const state = {availableBytes: 2 * (completeBytes - 51658752), currentRssBytes: 51658752};
  currentObservations(t, state);
  const trusted = f.git('rev-parse', 'HEAD').toString().trim();
  const destination = path.join(f.root, 'boundary');
  const originalRead = fs.readFileSync;
  let opened = 0;
  t.mock.method(fs, 'readFileSync', (...args) => { opened++; return originalRead(...args); });
  await assert.rejects(() => f.joint.selectedJointStage(f.root, trusted, f.selected, f.selected, destination),
    /Joint code\/runtime exceeds current allowance before body opens/);
  assert.equal(opened, 0);
  assert.equal(fs.existsSync(destination), false);
  // One additional admitted byte passes the code gate. Later complete reader
  // accounting still refuses this intentionally tiny grant without output.
  state.availableBytes += 2;
  await assert.rejects(() => f.joint.selectedJointStage(f.root, trusted, f.selected, f.selected, destination),
    error => /phase|allowance|cap/.test(error.message) &&
      !/Joint code\/runtime exceeds current allowance before body opens/.test(error.message));
  assert(opened > 0);
  assert.equal(fs.existsSync(destination), false);
});

test('idle warm admission still authenticates every consumer before importing it', async t => {
  const f = await trustedFixture(t);
  const state = {availableBytes: idleSupply.at(-1), currentRssBytes: 51658752};
  currentObservations(t, state);
  const trusted = f.git('rev-parse', 'HEAD').toString().trim();
  fs.appendFileSync(path.join(f.root, 'scripts/selected-checkpoint-native.mjs'),
    '\nthrow Error("unauthenticated idle consumer executed");\n');
  const destination = path.join(f.root, 'unauthenticated');
  await assert.rejects(() => f.joint.selectedJointStage(f.root, trusted, f.selected, f.selected, destination),
    /Joint code size differs/);
  assert.equal(fs.existsSync(destination), false);
});

test('actual warm entry propagates explicit headroom through authenticated consumers',async t=>{
 const f=await trustedFixture(t,{nativeOnly:true});
 const state={availableBytes:1401257984,currentRssBytes:52576256};
 currentObservations(t,state);
 const previous=process.env.WORLDATLAS_MEMORY_HEADROOM_BYTES;
 t.after(()=>{if(previous===undefined)delete process.env.WORLDATLAS_MEMORY_HEADROOM_BYTES;else process.env.WORLDATLAS_MEMORY_HEADROOM_BYTES=previous;});
 process.env.WORLDATLAS_MEMORY_HEADROOM_BYTES='572882944';
 const expected={phaseBytes:880951296,rssBytes:880951296};
 assert.deepEqual(jointExecutionAllowance(),expected);
 assert.deepEqual(processingAllowance(),expected);
 assert.deepEqual(preparationAllowance(),expected);
 const trusted=f.git('rev-parse','HEAD').toString().trim();
 const result=await f.joint.selectedJointStage(f.root,trusted,f.selected,f.selected,path.join(f.root,'explicit-headroom'));
 assert.equal(result.native.status,'no-new-native-loss');
 assert.equal(result.native.lost_or_reassigned_cells,0);
 assert.equal(result.candidate_code_executed,false);
});
