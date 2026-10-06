// Structural geometry migration for a lossless compact application context.
// Original-source validation and bounded byte inventories remain separate,
// mandatory caller stages; this never grants geographic or factual approval.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {isDeepStrictEqual} from 'node:util';
import {footprintHash} from '../check-prepared.mjs';
import {validateGeometryMigrations} from '../prepare-geographic-release.mjs';

export function validateContextMigration({original, migrated, candidates,
  predecessorRelease, release, migrationManifestFile}) {
  assert(Array.isArray(original) && original.length > 0 && Array.isArray(migrated),
    'Complete compact contexts are required');
  assert.equal(migrated.length, original.length, 'Compact context identity count changed');
  assert(candidates && typeof candidates === 'object' && !Array.isArray(candidates),
    'Exact reviewed native geometry values are required');
  assert.equal(footprintHash(original), predecessorRelease.footprints_sha256,
    'Original compact context differs from predecessor footprints');
  assert.equal(footprintHash(migrated), release.footprints_sha256,
    'Migrated compact context differs from successor footprints');
  assert.equal(release.hierarchy_sha256, predecessorRelease.hierarchy_sha256,
    'A context-only geometry migration cannot change hierarchy');
  assert.equal(release.metadata?.predecessor_release_id, predecessorRelease.id,
    'Wrong context migration predecessor release');
  const ids = new Set(), changed = [];
  for (let i = 0; i < original.length; i++) {
    const before = original[i], after = migrated[i];
    assert(typeof before.id === 'string' && before.id && !ids.has(before.id),
      'Original compact context has duplicate or missing identities');
    ids.add(before.id);
    assert.equal(before.pixelIndex, i + 1, 'Original compact owner order is incomplete');
    assert.equal(after.id, before.id, 'Compact stable identity/order changed');
    assert.equal(after.pixelIndex, before.pixelIndex, 'Compact owner index changed');
    const expected = Object.hasOwn(candidates, before.id)
      ? {...before, geometry: candidates[before.id]} : before;
    assert(isDeepStrictEqual(after, expected),
      'Compact context differs from the exact source proposal or rewrites an unchanged field: ' + before.id);
    if (!isDeepStrictEqual(before.geometry, after.geometry)) changed.push(before.id);
  }
  assert.deepEqual(changed.sort(), Object.keys(candidates).sort(),
    'Proposal roster is incomplete, unchanged or contains an extra subject');
  const geometryValidation = validateGeometryMigrations({
    features: migrated.map(f => ({id:f.id, geometry:f.geometry,
      properties:{id:f.id, parent_id:f.properties.parent_id}})),
    baselineIds: original.map(f => f.id),
    baselineFootprints: predecessorRelease.footprints_sha256,
    manifestFiles: [migrationManifestFile]
  });
  assert.equal(geometryValidation.proofs.length, 1, 'Require one exact final geometry migration');
  assert.equal(geometryValidation.retiredIds.size, 0, 'Compact migration retired identities');
  assert.equal(geometryValidation.addedIds.size, 0, 'Compact migration created identities');
  assert.deepEqual([...geometryValidation.changedIds].sort(), changed,
    'Receipt and actual complete compact geometry changes disagree');
  assert.equal(geometryValidation.pairs.length, changed.length,
    'Compact migration requires exactly one relationship per changed identity');
  for (const pair of geometryValidation.pairs) {
    assert(pair.old_entity_id === pair.new_entity_id && pair.change_type === 'retain' &&
      pair.history_transfer === 'none', 'Compact geometry migration transferred identity/history');
    const archived = geometryValidation.proofs[0].archives.get(pair.old_entity_id);
    const before = original.find(f => f.id === pair.old_entity_id);
    assert.equal(archived.properties.parent_id, before.properties.parent_id,
      'Archived original context parent differs');
    assert(isDeepStrictEqual(archived.geometry, before.geometry),
      'Archived original differs from the full original compact geometry');
  }
  const proof = geometryValidation.proofs[0];
  assert.equal(release.metadata?.geometry_migration?.sha256, proof.receipt_sha256,
    'Release does not bind the actual geometry receipt');
  assert.equal(release.metadata.geometry_migration.history_transfer, 'none',
    'Release geometry proof transferred history');
  const ownerSha = createHash('sha256').update(JSON.stringify(original.map(f => [f.pixelIndex, f.id]))).digest('hex');
  return {status:'verified', locations:original.length, changed_locations:changed.length,
    unchanged_locations:original.length-changed.length, changed_ids:changed,
    predecessor_release_id:predecessorRelease.id, successor_release_id:release.id,
    footprints_sha256:release.footprints_sha256, owner_sha256:ownerSha,
    historical_claims_transferred:false, geographic_approval:false,
    installation_ready:false, geometryValidation};
}
