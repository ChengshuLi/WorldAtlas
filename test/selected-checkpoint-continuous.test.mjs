import test from 'node:test';
import assert from 'node:assert/strict';
import {trustedFixture} from './helpers/selected-joint-fixture.mjs';

function qualified(f) {
  const baseline = f.api.qualifyCheckpoint({reader:f.reader, budget:f.budget});
  assert.equal(baseline.available, true);
  const transition = f.api.qualifyTransition({state:baseline.state, reader:f.reader, budget:f.budget});
  assert.equal(transition.available, true);
  return transition;
}

test('real private transition carries complete unchanged primitives and exact vintage bindings', async t => {
  const f = await trustedFixture(t), transition = qualified(f);
  const product = f.continuous.checkpointContinuousOperands({transition, budget:f.budget});
  assert.equal(product.complete_owners, 3);
  assert.deepEqual(product.operands.plan.required_ids, []);
  assert.deepEqual(product.operands.effective_additions.baseline, transition.baseline.additions);
  assert.deepEqual(product.operands.effective_additions.candidate, transition.candidate.additions);
  assert.equal(product.operands.effective_additions.baseline.length, 1);
  assert.strictEqual(product.custody.baseline.state_binding, transition.plan.source_bindings.baseline);
  assert.strictEqual(product.custody.candidate.state_binding, transition.plan.source_bindings.candidate);
  assert.equal(product.custody.source_features_reused, true);
  f.api.releaseCheckpoint(transition.baseline);
});

test('actual whole-feature projections join by identity rather than positional scope order', async t => {
  const f = await trustedFixture(t), transition = qualified(f), ids = ['A', 'B', 'C'];
  const actual = f.api.projectSourceFeatures({state:transition.baseline, ids, budget:f.budget});
  const reversed = {...actual, features:[...actual.features].reverse()};
  const result = f.continuous.completeContinuousFeatures(reversed, ids);
  for (const feature of actual.features) assert.strictEqual(result[feature.id], feature);
  assert.throws(() => f.continuous.completeContinuousFeatures({...actual, features:actual.features.slice(1)}, ids), /missing or duplicate/);
  assert.throws(() => f.continuous.completeContinuousFeatures({...actual, features:[actual.features[0], actual.features[0], actual.features[2]]}, ids), /identity differs/);
  const changed = structuredClone(actual); changed.features[0].geometry.coordinates[0][0][0] = 99;
  assert.throws(() => f.continuous.completeContinuousFeatures(changed, ids), /identity differs/);
  const rebound = {...actual, inverse:actual.inverse.map(row => row.id === 'A' ? {...row, id:'foreign'} : row)};
  assert.throws(() => f.continuous.completeContinuousFeatures(rebound, ids), /identity differs/);
  f.api.releaseCheckpoint(transition.baseline);
});

test('real states cannot authorize forged, omitted-neighbor or reordered transition wrappers', async t => {
  const f = await trustedFixture(t), transition = qualified(f);
  const read = f.native.ImmutableReader.prototype.read; let opens = 0;
  f.native.ImmutableReader.prototype.read = function(...args) { opens++; return read.apply(this, args); };
  try {
    for (const fake of [structuredClone(transition), {...transition},
      {...transition, plan:{...transition.plan, changed_ids:['A'], required_ids:['A'], pairs:[]}}]) {
      assert.throws(() => f.continuous.checkpointContinuousOperands({transition:fake, budget:f.budget}), /private qualified selected transition/);
    }
    assert.equal(opens, 0);
  } finally { f.native.ImmutableReader.prototype.read = read; f.api.releaseCheckpoint(transition.baseline); }
});

test('complete external output carry is admitted before opening source bodies', async t => {
  const f = await trustedFixture(t), transition = qualified(f);
  f.budget.carriedBytes += f.reader.phaseLimit - f.reader.used - 1024;
  const read = f.native.ImmutableReader.prototype.read; let opens = 0;
  f.native.ImmutableReader.prototype.read = function(...args) { opens++; return read.apply(this, args); };
  try {
    assert.throws(() => f.continuous.checkpointContinuousOperands({transition, budget:f.budget}), /carried-state increase exceeds/);
    assert.equal(opens, 0);
  } finally { f.native.ImmutableReader.prototype.read = read; f.api.releaseCheckpoint(transition.baseline); }
});

test('the continuous consumer refuses another budget and an invocation released by its joint owner', async t => {
  const f = await trustedFixture(t), transition = qualified(f);
  assert.throws(() => f.continuous.checkpointContinuousOperands({transition, budget:{...f.budget}}), /independently budgeted/);
  f.api.releaseCheckpoint(transition.baseline);
  assert.throws(() => f.continuous.checkpointContinuousOperands({transition, budget:f.budget}), /private qualified selected transition/);
});
