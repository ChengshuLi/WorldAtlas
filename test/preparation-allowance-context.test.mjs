import test from 'node:test';
import assert from 'node:assert/strict';
import {candidateBudget, preparationAllowance, preparationRequestAllowance} from '../scripts/native-ownership/native-preparation-guards.mjs';

function observations(t, {available = 1725153280, rss = 136953856} = {}) {
  const state = {available, rss};
  t.mock.method(process, 'availableMemory', () => state.available);
  t.mock.method(process, 'memoryUsage', () => ({rss: state.rss}));
  const saved = Object.fromEntries(['WORLDATLAS_MEMORY_HEADROOM_BYTES', 'WORLDATLAS_CONCURRENT_RESERVED_BYTES'].map(k => [k, process.env[k]]));
  delete process.env.WORLDATLAS_MEMORY_HEADROOM_BYTES;
  process.env.WORLDATLAS_CONCURRENT_RESERVED_BYTES = '0';
  t.after(() => { for (const [k, v] of Object.entries(saved)) { if (v === undefined) delete process.env[k]; else process.env[k] = v; } });
  return state;
}
const request = {phaseBytes: 1006632960, rssBytes: 1006632960};
const headroomBytes = 572882944;

test('genuine explicit-headroom grant keeps its policy through fresh nested budget admission', t => {
  observations(t);
  const grant = preparationAllowance({...request, headroomBytes, currentRssBytes: 0});
  assert.deepEqual(Object.keys(grant).sort(), ['phaseBytes', 'rssBytes']);
  assert.ok(Object.isFrozen(grant));
  const budget = candidateBudget([], {reserveBytes: 960680078, reserveDescriptors: 16, allowance: grant});
  assert.deepEqual(budget.allowance, request);
  assert.notEqual(budget.allowance, grant);
  assert.equal(budget.snapshot().reserved_review_bytes, 960680078);
  assert.throws(() => budget.add({bytes: 50000000}), /Invalid whole-file admission/);
  budget.add({bytes: 33554432});
  assert.throws(() => budget.add({bytes: 33554432}), /Aggregate evidence preparation budget exceeded/);
});

test('plain and copied requests retain ambient half-free admission rather than importing policy', t => {
  observations(t);
  const grant = preparationAllowance({...request, headroomBytes, currentRssBytes: 0});
  assert.throws(() => preparationRequestAllowance({...grant}), /exceeds current memory admission/);
  assert.throws(() => candidateBudget([], {allowance: request}), /exceeds current memory admission/);
});

test('nested genuine grants reobserve reduced available memory before any inputs', t => {
  const state = observations(t);
  const grant = preparationAllowance({...request, headroomBytes, currentRssBytes: 0});
  state.available = 1200000000;
  assert.throws(() => candidateBudget([], {allowance: grant}), /exceeds current memory admission/);
});

test('new concurrent reservations cannot be hidden by the previous grant', t => {
  observations(t);
  const grant = preparationAllowance({...request, headroomBytes, concurrentReservedBytes: 0, currentRssBytes: 0});
  process.env.WORLDATLAS_CONCURRENT_RESERVED_BYTES = '400000000';
  assert.throws(() => preparationRequestAllowance(grant), /exceeds current memory admission/);

});

test('an explicit prior concurrent reservation remains a floor when environment is looser', t => {
  const state = observations(t, {available: 2000000000});
  const grant = preparationAllowance({...request, headroomBytes, concurrentReservedBytes: 300000000, currentRssBytes: 0});
  state.available = 1600000000;
  assert.throws(() => preparationRequestAllowance(grant), /exceeds current memory admission/);
});

test('fresh process RSS and cumulative checks still apply after policy propagation', t => {
  const state = observations(t);
  const grant = preparationAllowance({...request, headroomBytes, currentRssBytes: 0});
  state.rss = request.rssBytes;
  assert.throws(() => candidateBudget([], {allowance: grant}), /RSS allowance exceeded/);
});

test('explicit headroom precedence is unchanged by a later environmental value', t => {
  observations(t);
  const grant = preparationAllowance({...request, headroomBytes, currentRssBytes: 0});
  for (const value of ['1000000000', '-1', 'NaN']) {
    process.env.WORLDATLAS_MEMORY_HEADROOM_BYTES = value;
    assert.deepEqual(preparationAllowance({...request, headroomBytes}), request);
    assert.deepEqual(preparationRequestAllowance(grant), request);
  }
});

test('invalid fresh concurrent reservation refuses and plain requests still validate environmental headroom', t => {
  observations(t);
  const grant = preparationAllowance({...request, headroomBytes});
  process.env.WORLDATLAS_CONCURRENT_RESERVED_BYTES = '-1';
  assert.throws(() => preparationRequestAllowance(grant), /resource observations/);
  process.env.WORLDATLAS_CONCURRENT_RESERVED_BYTES = '0';
  process.env.WORLDATLAS_MEMORY_HEADROOM_BYTES = 'NaN';
  assert.throws(() => preparationRequestAllowance({...grant}), /positive byte reservation/);
});

test('default policy is still half of fresh available memory and no fixed country minimum exists', t => {
  observations(t, {available: 1600000000, rss: 50000000});
  const grant = preparationAllowance();
  assert.deepEqual(grant, {phaseBytes: 850000000, rssBytes: 850000000});
  assert.deepEqual(preparationRequestAllowance({phaseBytes: 536870912, rssBytes: 536870912}), {phaseBytes: 536870912, rssBytes: 536870912});
});
