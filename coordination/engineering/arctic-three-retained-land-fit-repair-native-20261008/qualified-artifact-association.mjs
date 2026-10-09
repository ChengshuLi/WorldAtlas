// Application consumption of an independently qualified immutable migration.
// This is a distinct authority type. It never manufactures a geometry-validator
// brand, invokes a scientific producer, or replaces the original live API.
import assert from 'node:assert/strict';
import {validateCoverageManifest} from '../../../src/coverage-classification.js';
import {ownershipMetadata} from '../../../src/ownership-method.js';
import {requireConsumedArcticArtifacts} from './qualified-artifact-consumer.mjs';

function unique(values, label) {
  assert(Array.isArray(values) && values.every(id => typeof id === 'string' && id));
  assert.equal(new Set(values).size, values.length, label);
  return new Set(values);
}

export function validateRetainedAssociation(step) {
  const {predecessor, release, receipt, manifest, receipt_sha256, manifest_sha256} = step;
  assert(/^[a-f0-9]{64}$/.test(receipt_sha256));
  assert(/^[a-f0-9]{64}$/.test(manifest_sha256));
  assert.equal(receipt.geometry_stage_validated, true);
  assert.equal(receipt.before_footprints_sha256, predecessor.footprints_sha256);
  assert.equal(receipt.after_footprints_sha256, release.footprints_sha256);
  assert.equal(manifest.history_transfer, false);
  // Preserve the literal historical receipt schemas: v6→v7 omits this field,
  // v7→v8 uses false, and the new receipt uses 'none'. The independently pinned
  // manifest and every relationship still explicitly prohibit transfer.
  assert(receipt.history_transfer === undefined || receipt.history_transfer === false || receipt.history_transfer === 'none');
  assert(receipt.historical_claims_transferred === false || receipt.historical_claims_transferred === 0);
  assert.equal(release.metadata.predecessor_release_id, predecessor.id);
  assert.equal(release.metadata.geometry_migration.sha256, receipt_sha256);
  assert.equal(release.metadata.geometry_migration.before_footprints_sha256, predecessor.footprints_sha256);
  assert.equal(release.metadata.geometry_migration.after_footprints_sha256, release.footprints_sha256);
  assert.equal(release.metadata.geometry_migration.history_transfer, 'none');
  assert.equal(release.hierarchy_sha256, predecessor.hierarchy_sha256);
  const changed = unique(receipt.changed_ids, 'Duplicate changed identity');
  const reused = unique(receipt.reused_ids, 'Duplicate retained identity');
  assert(changed.size > 0);
  assert.deepEqual(receipt.removed_ids, []);
  assert.deepEqual(receipt.added_ids, []);
  assert.equal(changed.size + reused.size, 49625);
  assert([...changed].every(id => !reused.has(id)));
  const linked = new Set();
  for (const relationship of receipt.relationships) {
    assert.equal(relationship.history_transfer, false);
    const before = unique(relationship.before_ids, 'Duplicate relationship predecessor');
    const after = unique(relationship.after_ids, 'Duplicate relationship successor');
    assert.deepEqual([...before].sort(), [...after].sort());
    const pairs = relationship.identity_pairs ?? [...before].map(id => ({before_id: id, after_id: id}));
    assert.equal(pairs.length, before.size);
    for (const pair of pairs) {
      assert.equal(pair.before_id, pair.after_id);
      assert(before.has(pair.before_id) && changed.has(pair.before_id) && !linked.has(pair.before_id));
      linked.add(pair.before_id);
    }
  }
  assert.deepEqual([...linked].sort(), [...changed].sort());
  const archives = unique(receipt.archives.map(row => row.id), 'Duplicate original archive');
  assert.deepEqual([...archives].sort(), [...changed].sort());
  for (const row of receipt.archives) assert.equal(row.feature.id, row.id);
  return [...changed].sort();
}

export function associateQualifiedCoverage(manifest, {consumption, originalGrid, originalGridSha256, selectedGrid, selectedGridSha256, release}) {
  requireConsumedArcticArtifacts(consumption);
  const previous = [];
  let result = manifest, grid = originalGrid, gridSha = originalGridSha256;
  for (const step of consumption.steps) {
    const ids = validateRetainedAssociation(step);
    assert.equal(step.original_grid_sha256, gridSha);
    const expected = {...step.predecessor, release_id: step.predecessor.id, canonical_grid_sha256: gridSha,
      size: grid.size, coordinateBits: grid.coordinateBits};
    validateCoverageManifest(result, expected);
    const next = step.selected_grid;
    ownershipMetadata(next, {requireNative: true, expectedReference: step.release});
    for (const key of ['size', 'coordinateBits', 'hierarchy_sha256']) assert.equal(next[key], grid[key]);
    assert.equal(grid.footprints_sha256, step.predecessor.footprints_sha256);
    if (result.ownership_binding) previous.push(structuredClone(result.ownership_binding));
    const rebound = {...structuredClone(result), release_id: step.release.id,
      footprints_sha256: step.release.footprints_sha256, canonical_grid_sha256: step.selected_grid_sha256,
      ownership_binding: {
        original_canonical_grid_sha256: gridSha, selected_canonical_grid_sha256: step.selected_grid_sha256,
        selected_method: next.method,
        scope: 'Unchanged physical class assets and coordinate grid; location ownership association only. Original source/water uncertainty and blocked tiles remain.',
        geometry_migration: {
          predecessor_release_id: step.predecessor.id, predecessor_footprints_sha256: step.predecessor.footprints_sha256,
          successor_release_id: step.release.id, successor_footprints_sha256: step.release.footprints_sha256,
          manifest_sha256: step.manifest_sha256, receipt_sha256: step.receipt_sha256, changed_ids: ids,
          historical_claims_transferred: false,
          scope: 'Physical source classes were not recalculated or reinterpreted. Only the validated ownership association changed.'
        }
      }};
    validateCoverageManifest(rebound, {...expected, ...step.release, release_id: step.release.id,
      canonical_grid_sha256: step.selected_grid_sha256});
    result = rebound; grid = next; gridSha = step.selected_grid_sha256;
  }
  assert.equal(gridSha, selectedGridSha256);
  assert.deepEqual(grid, selectedGrid);
  assert.deepEqual(consumption.steps.at(-1).release, release);
  result.ownership_binding.previous_associations = previous;
  assert.equal(previous.length, 2);
  const retained = structuredClone(result); delete retained.ownership_binding;
  for (const key of ['release_id', 'footprints_sha256', 'canonical_grid_sha256']) retained[key] = manifest[key];
  const original = structuredClone(manifest); delete original.ownership_binding;
  assert.deepEqual(retained, original, 'Original classification/source/assets changed');
  return result;
}
