import fs from 'node:fs';
import {createHash} from 'node:crypto';
import test from 'node:test';
import assert from 'node:assert/strict';
import {combineNativeBatch} from '../scripts/additive-gap-repair.mjs';
import {canonicalValue, footprintValueSha256, effectivePrimitiveGeometries, additiveReleaseFootprintDigest} from '../src/effective-footprint.js';

const handoffPath = 'research/geography/aus19-original-source-20261011/vintages/source-handoff-001/source-handoff.json';
const rawHandoff = fs.readFileSync(new URL('../' + handoffPath, import.meta.url));
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
assert.equal(rawHandoff.length, 1998089);
assert.equal(sha(rawHandoff), 'a86d07773cb98ac2e3b747b700eb07f845fb33da79da45c904927a2fa3b610b0');
const handoff = JSON.parse(rawHandoff);
const producer = fs.readFileSync(new URL('../scripts/additive-gap-repair.mjs', import.meta.url), 'utf8');
const stages = ['countyBatchProposalStage', 'administrativeBatchProposalStage'];
const additionSort = '.sort((a,b)=>a.component_id<b.component_id?-1:a.component_id>b.component_id?1:0)';

// Execute each production construction boundary verbatim. This avoids adding a
// public API or replaying SOURCE/NATIVE acquisition and scientific qualification.
function construct(stage, fixture, {legacy = false} = {}) {
  const start = producer.indexOf('function ' + stage + '(');
  assert(start >= 0);
  const loop = producer.indexOf('  for(const targetId of ', start);
  const end = producer.indexOf('  const effectiveReference=', loop);
  assert(loop > start && end > loop);
  let body = producer.slice(loop, end);
  assert.equal(body.split(additionSort).length, 2, stage + ' must sort only its derived additions');
  if (legacy) body = body.replace(additionSort, '');
  const build = new Function('ledgerRows', 'targets', 'owners', 'baseReference', 'ledgerSha', 'ruleSha', 'receiptSha',
    'footprintValueSha256', 'const features=[];\n' + body + '\nreturn features;');
  return build(fixture.ledger.rows, fixture.targets, fixture.owners, fixture.baseReference,
    footprintValueSha256(fixture.ledger), footprintValueSha256('mechanism-test-rule'), sha(rawHandoff), footprintValueSha256);
}

function fixture() {
  const targets = new Map(), owners = new Map();
  for (const pin of handoff.original_target_canonical_bindings) {
    const bytes = Buffer.from(pin.feature_bytes_base64, 'base64');
    assert.equal(sha(bytes), pin.feature_sha256);
    const feature = JSON.parse(bytes), index = targets.size + 1;
    assert.equal(feature.id, pin.target_id);
    targets.set(feature.id, {...feature, pixelIndex: index});
    owners.set(feature.id, {index});
  }
  const rows = handoff.candidate_source_native_bindings.map(row => ({
    component_id: row.component_id, target_id: row.retained_payload.target_stable_location_id,
    geometry: row.original_candidate_feature.geometry,
    geometry_sha256: footprintValueSha256(row.original_candidate_feature.geometry),
    // Synthetic zero-cell dispositions isolate serialization. These are not new
    // geographic/source decisions or an executed AUS NATIVE result.
    disposition: 'zero-cell', native_cells: 0,
  }));
  assert.deepEqual(rows.map(row => row.component_id), handoff.scopeIds);
  return {targets, owners, baseReference: handoff.current_neighbor_binding.actual_runtime_envelope.base_reference,
    ledger: {scope_ids: [...handoff.scopeIds], rows}};
}

for (const stage of stages) {
  test(stage + ' canonicalizes genuine same-target additions without reordering issued scope or ledger', () => {
    const input = fixture(), before = JSON.stringify(input.ledger), sourceBefore = JSON.stringify(handoff);
    assert.notDeepEqual(input.ledger.scope_ids, [...input.ledger.scope_ids].sort());
    const legacy = construct(stage, input, {legacy: true});
    assert.throws(() => additiveReleaseFootprintDigest(input.baseReference, legacy), /Duplicate\/unordered addition identity/);
    const features = construct(stage, input);
    assert.match(additiveReleaseFootprintDigest(input.baseReference, features), /^[a-f0-9]{64}$/);
    let additions = 0, nonlexicalTargets = 0;
    for (const feature of features) {
      const issued = input.ledger.rows.filter(row => row.target_id === feature.id);
      const expected = issued.map(row => row.component_id).sort();
      if (JSON.stringify(expected) !== JSON.stringify(issued.map(row => row.component_id))) nonlexicalTargets++;
      assert.deepEqual(feature.additiveFootprint.additions.map(row => row.component_id), expected);
      const geometries = expected.map(id => issued.find(row => row.component_id === id).geometry);
      assert.deepEqual(effectivePrimitiveGeometries(feature), [input.targets.get(feature.id).geometry, ...geometries]);
      for (const addition of feature.additiveFootprint.additions) {
        const original = issued.find(row => row.component_id === addition.component_id);
        assert.equal(addition.geometry, original.geometry);
        assert.equal(addition.geometry_sha256, original.geometry_sha256);
      }
      additions += issued.length;
    }
    assert.equal(additions, 13);
    assert.equal(nonlexicalTargets, 3);
    assert.equal(JSON.stringify(input.ledger), before);
    assert.equal(JSON.stringify(handoff), sourceBefore);
    assert.equal(sha(fs.readFileSync(new URL('../' + handoffPath, import.meta.url))), sha(rawHandoff));
  });

  test(stage + ' preserves already-canonical output and strict duplicate refusal', () => {
    const input = fixture();
    // A separate already-canonical control, never a mutation of the issued input.
    input.ledger.rows.sort((a, b) => a.component_id < b.component_id ? -1 : a.component_id > b.component_id ? 1 : 0);
    input.ledger.scope_ids = input.ledger.rows.map(row => row.component_id);
    assert.deepEqual(construct(stage, input), construct(stage, input, {legacy: true}));
    input.ledger.rows.push({...input.ledger.rows[0]});
    input.ledger.scope_ids.push(input.ledger.rows[0].component_id);
    const duplicate = construct(stage, input);
    assert.throws(() => additiveReleaseFootprintDigest(input.baseReference, duplicate), /Duplicate\/unordered addition identity/);
  });
}

test('native combination retains source order and exact cell accounting before either construction boundary', () => {
  const original = fixture(), sameTarget = original.ledger.rows.filter(row => row.target_id === original.ledger.rows[0].target_id);
  assert.equal(sameTarget.length, 3);
  const ids = sameTarget.map(row => row.component_id), targetId = sameTarget[0].target_id;
  assert.notDeepEqual(ids, [...ids].sort());
  const sourceRows = sameTarget.map(row => ({...row, pixelIndex: 1, source_compatible: true}));
  // Bounded synthetic intervals exercise accounting only; no geographic result.
  const intervals = [[[0, 2, 1]], [[1, 4, 1]], []];
  const candidates = ids.map((component_id, i) => ({component_id, target_id: targetId, pixelIndex: 1,
    row_start: 1, row_end: 2, rows: [{y: 1, runs: intervals[i]}]}));
  const args = {scopeIds: ids, sourceRows, candidates, ownerRows: [{y: 1, complete_owner_intervals: [[6, 8, 2]]}], size: 8};
  const before = JSON.stringify(args), result = combineNativeBatch(args);
  assert.deepEqual(result.decisions.map(row => row.component_id), ids);
  assert.deepEqual(result.decisions.map(row => [row.disposition, row.native_cells]), [['assigned', 2], ['assigned', 3], ['zero-cell', 0]]);
  assert.deepEqual(result.rows, [{y: 1, runs: [[0, 4, 1]]}]);
  assert.deepEqual(result.virtual_owner_rows, [{y: 1, complete_owner_intervals: [[0, 4, 1], [6, 8, 2]]}]);
  assert.equal(result.assigned_cells, 4);
  assert.equal(result.candidate_cell_contributions, 5);
  assert.equal(result.shared_same_owner_cells, 1);
  assert.equal(result.removed_cells, 0);
  assert.equal(result.reassigned_cells, 0);
  assert.equal(JSON.stringify(args), before);
  assert.throws(() => combineNativeBatch({...args, scopeIds: [...ids, ids[0]]}), /Invalid complete batch scope/);
  assert.throws(() => combineNativeBatch({...args, sourceRows: [...sourceRows, sourceRows[0]]}), /Foreign\/duplicate\/incomplete source decision/);
  assert.throws(() => combineNativeBatch({...args, candidates: [...candidates, candidates[0]]}), /Foreign\/duplicate candidate or target\/window join/);
  assert.deepEqual(canonicalValue(handoff.scopeIds), handoff.scopeIds);
});
