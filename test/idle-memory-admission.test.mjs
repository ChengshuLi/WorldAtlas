import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import {processingAllowance, ImmutableReader} from '../scripts/check-effective-geographic-regression.mjs';
import {preparationAllowance, preparationRequestAllowance, candidateBudget} from '../scripts/native-ownership/native-preparation-guards.mjs';

const MiB = 1024 ** 2;
const root = path.resolve(import.meta.dirname, '..');
const guards = [processingAllowance, preparationAllowance];
const observations = [1818279936, 1737015296, 1760100352, 1590296576];

test('idle reported availability admits finite current grants with no physical-RAM floor', () => {
  for (const availableBytes of observations) {
    const currentRssBytes = 51658752;
    const expected = currentRssBytes + Math.floor(availableBytes / 2);
    for (const guard of guards) {
      const allowance = guard({availableBytes, currentRssBytes, concurrentReservedBytes: 0});
      assert.deepEqual(allowance, {phaseBytes: expected, rssBytes: expected});
      assert(Object.isFrozen(allowance));
      assert.deepEqual(Object.keys(allowance).sort(), ['phaseBytes', 'rssBytes']);
      assert(allowance.rssBytes - currentRssBytes <= Math.floor(availableBytes / 2));
    }
  }
});

test('future reservations reduce growth once and explicit grants retain safety headroom', () => {
  for (const guard of guards) {
    const observation = {availableBytes: 1000, currentRssBytes: 100, concurrentReservedBytes: 200};
    assert.deepEqual(guard(observation), {phaseBytes: 500, rssBytes: 500});
    assert.deepEqual(guard({...observation, phaseBytes: 300, rssBytes: 450}), {phaseBytes: 300, rssBytes: 450});
    assert.deepEqual(guard({...observation, phaseBytes: 500, rssBytes: 500}), {phaseBytes: 500, rssBytes: 500});
    for (const parameter of ['phaseBytes', 'rssBytes']) {
      assert.throws(() => guard({...observation, [parameter]: 501}), /admission/);
      for (const value of [-1, 0, NaN, Infinity, Number.MAX_SAFE_INTEGER + 1]) {
        assert.throws(() => guard({...observation, [parameter]: value}), /admission/);
      }
    }
  }
});

test('unknown/exhausted observations and unsafe resident-plus-growth sums fail closed', () => {
  for (const guard of guards) {
    const observation = {availableBytes: 1000, currentRssBytes: 100, concurrentReservedBytes: 0};
    for (const parameter of ['availableBytes', 'currentRssBytes', 'concurrentReservedBytes']) {
      for (const value of [-1, NaN, Infinity, Number.MAX_SAFE_INTEGER + 1]) {
        assert.throws(() => guard({...observation, [parameter]: value}), /observations/);
      }
    }
    for (const options of [{availableBytes: 0}, {availableBytes: 1}, {concurrentReservedBytes: 999}, {concurrentReservedBytes: 1000}, {concurrentReservedBytes: 1001}]) {
      assert.throws(() => guard({...observation, ...options}), /Insufficient/);
    }
    assert.throws(() => guard({...observation, currentRssBytes: Number.MAX_SAFE_INTEGER}), /observations/);
  }
});

test('coordinator environment declares future growth without changing allowance domains', t => {
  t.mock.method(process, 'availableMemory', () => 1000);
  t.mock.method(process, 'memoryUsage', () => ({rss: 100}));
  const previousReservation = process.env.WORLDATLAS_CONCURRENT_RESERVED_BYTES;
  t.after(() => {
    if (previousReservation === undefined) delete process.env.WORLDATLAS_CONCURRENT_RESERVED_BYTES;
    else process.env.WORLDATLAS_CONCURRENT_RESERVED_BYTES = previousReservation;
  });
  process.env.WORLDATLAS_CONCURRENT_RESERVED_BYTES = '200';
  for (const guard of guards) {
    assert.deepEqual(guard(), {phaseBytes: 500, rssBytes: 500});
    assert.deepEqual(guard({concurrentReservedBytes: 0}), {phaseBytes: 600, rssBytes: 600});
  }
  for (const invalid of ['-1', 'NaN', 'Infinity', '0.5', '9007199254740992']) {
    process.env.WORLDATLAS_CONCURRENT_RESERVED_BYTES = invalid;
    for (const guard of guards) assert.throws(() => guard(), /observations/);
  }
  process.env.WORLDATLAS_CONCURRENT_RESERVED_BYTES = '1000';
  for (const guard of guards) assert.throws(() => guard(), /Insufficient/);
});

test('revalidation credits already resident bytes for both complete-phase and total RSS limits', t => {
  let availableBytes = 1600 * MiB, residentBytes = 50 * MiB;
  t.mock.method(process, 'availableMemory', () => availableBytes);
  t.mock.method(process, 'memoryUsage', () => ({rss: residentBytes}));
  const previousReservation = process.env.WORLDATLAS_CONCURRENT_RESERVED_BYTES;
  delete process.env.WORLDATLAS_CONCURRENT_RESERVED_BYTES;
  t.after(() => {
    if (previousReservation === undefined) delete process.env.WORLDATLAS_CONCURRENT_RESERVED_BYTES;
    else process.env.WORLDATLAS_CONCURRENT_RESERVED_BYTES = previousReservation;
  });
  const original = preparationAllowance();
  assert.deepEqual(original, {phaseBytes: 850 * MiB, rssBytes: 850 * MiB});
  // The same process has loaded data. Its RSS rose and remaining availability
  // fell by the same bytes; neither the phase nor RSS grant is charged twice.
  residentBytes += 400 * MiB;
  availableBytes -= 400 * MiB;
  assert.deepEqual(preparationRequestAllowance(original), original);
  assert.deepEqual(processingAllowance({...original}), original);
  const budget = candidateBudget([{bytes: 32 * MiB}], {allowance: original});
  assert.equal(budget.snapshot().limit_bytes, original.phaseBytes);
  assert.equal(budget.snapshot().rss_limit_bytes, original.rssBytes);
  // Unrelated growth really consumes remaining capacity and invalidates a
  // request whose future RSS growth no longer leaves finite safety headroom.
  availableBytes = 600 * MiB;
  assert.throws(() => preparationRequestAllowance(original), /admission/);
  assert.throws(() => processingAllowance({...original}), /admission/);
  residentBytes = original.rssBytes;
  assert.throws(() => budget.snapshot(), /RSS/);
});

test('actual reader and preparation budgets retain complete-phase, member and RSS rejection', t => {
  let residentBytes = 50 * MiB;
  t.mock.method(process, 'memoryUsage', () => ({rss: residentBytes}));
  const observation = {availableBytes: 1590296576, concurrentReservedBytes: 0, currentRssBytes: residentBytes};
  const allowance = processingAllowance(observation);
  const reader = new ImmutableReader(root, 'a'.repeat(40), {
    runtimeBytes: 1, executionBytes: 1, metadataBytes: 320 * MiB, outputBytes: 1, allowance
  });
  reader.admit({commit: 'a'.repeat(40), path: 'complete.json', bytes: 20 * MiB});
  assert.equal(reader.used, 340 * MiB + 3);
  assert.throws(() => reader.admit({commit: 'a'.repeat(40), path: 'decoded.json', bytes: 1}, 32 * MiB + 1), /decoded member/);
  assert.throws(() => reader.admit({commit: 'a'.repeat(40), path: 'over-phase.json', bytes: allowance.phaseBytes}), /phase/);
  const budget = candidateBudget([{bytes: 20 * MiB}], {allowance: preparationAllowance(observation)});
  assert.throws(() => budget.add({bytes: 32 * MiB + 1}), /whole-file/);
  residentBytes = allowance.rssBytes;
  assert.throws(() => reader.phase(), /RSS/);
  assert.throws(() => budget.snapshot(), /RSS/);
});
