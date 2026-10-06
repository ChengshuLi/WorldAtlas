import {validateCoverageManifest} from '../src/coverage-classification.js';
import {ownershipMetadata} from '../src/ownership-method.js';
import {requireValidatedGeometryMigrations} from './prepare-geographic-release.mjs';

// Classification assets depend on physical references and the grid coordinate
// domain, not on location ownership. Rebind only that association, retaining
// every original class/source/blocked-tile limit and all encoded asset digests.
export function rebindCoverageManifest(manifest, {originalGrid, originalGridSha256,
  selectedGrid, selectedGridSha256, release, predecessorRelease, geometryValidation}) {
  const migration = predecessorRelease !== undefined || geometryValidation !== undefined;
  const originalRelease = migration ? predecessorRelease : release;
  if (!originalRelease?.id) throw Error('Missing original physical reference release');
  const expected = {...originalRelease, release_id: originalRelease.id, canonical_grid_sha256: originalGridSha256,
    size: originalGrid.size, coordinateBits: originalGrid.coordinateBits};
  validateCoverageManifest(manifest, expected);
  ownershipMetadata(selectedGrid, {requireNative: true, expectedReference: release});
  for (const key of ['size', 'coordinateBits', 'hierarchy_sha256'])
    if (selectedGrid[key] !== originalGrid[key]) throw Error('Physical classification coordinate/source context changed: ' + key);
  if (migration) {
    // The caller must first reconstruct all predecessor geometry with
    // validateGeometryMigrations. A footprint hash alone is insufficient.
    requireValidatedGeometryMigrations(geometryValidation);
    const proof = geometryValidation.proofs;
    if (proof?.length !== 1 || !geometryValidation.changedIds?.size ||
        geometryValidation.retiredIds?.size !== 0 || geometryValidation.addedIds?.size !== 0 ||
        release.metadata?.predecessor_release_id !== originalRelease.id ||
        release.metadata?.geometry_migration?.sha256 !== proof[0].receipt_sha256 ||
        release.metadata.geometry_migration.before_footprints_sha256 !== originalRelease.footprints_sha256 ||
        release.metadata.geometry_migration.after_footprints_sha256 !== release.footprints_sha256 ||
        release.metadata.geometry_migration.history_transfer !== false ||
        release.hierarchy_sha256 !== originalRelease.hierarchy_sha256 ||
        originalGrid.footprints_sha256 !== originalRelease.footprints_sha256 ||
        proof[0].receipt.before_footprints_sha256 !== originalRelease.footprints_sha256 ||
        proof[0].receipt.after_footprints_sha256 !== release.footprints_sha256 ||
        proof[0].receipt.historical_claims_transferred !== false ||
        !/^[a-f0-9]{64}$/.test(proof[0].receipt_sha256 ?? '') ||
        !/^[a-f0-9]{64}$/.test(proof[0].manifest_sha256 ?? '') ||
        geometryValidation.pairs.length !== geometryValidation.changedIds.size ||
        geometryValidation.pairs.some(pair => pair.change_type !== 'retain' ||
          pair.old_entity_id !== pair.new_entity_id || pair.history_transfer !== 'none' ||
          !geometryValidation.changedIds.has(pair.old_entity_id)))
      throw Error('Physical reassociation requires a complete retained-identity geometry migration');
    const ids = new Set(geometryValidation.pairs.map(pair => pair.old_entity_id));
    if (ids.size !== geometryValidation.changedIds.size)
      throw Error('Duplicate or incomplete retained geometry identities');
  } else if (selectedGrid.footprints_sha256 !== originalGrid.footprints_sha256) {
    throw Error('Physical classification coordinate/source context changed: footprints_sha256');
  }
  if (!/^[a-f0-9]{64}$/.test(selectedGridSha256 ?? '')) throw Error('Missing selected grid digest');
  const rebound = {...structuredClone(manifest), canonical_grid_sha256: selectedGridSha256,
    ownership_binding: {
      original_canonical_grid_sha256: originalGridSha256,
      selected_canonical_grid_sha256: selectedGridSha256,
      selected_method: selectedGrid.method,
      scope: 'Unchanged physical class assets and coordinate grid; location ownership association only. Original source/water uncertainty and blocked tiles remain.'
    }};
  if (migration) {
    rebound.footprints_sha256 = release.footprints_sha256;
    rebound.release_id = release.id;
    rebound.ownership_binding.geometry_migration = {
      predecessor_release_id: originalRelease.id,
      predecessor_footprints_sha256: originalRelease.footprints_sha256,
      successor_release_id: release.id,
      successor_footprints_sha256: release.footprints_sha256,
      manifest_sha256: geometryValidation.proofs[0].manifest_sha256,
      receipt_sha256: geometryValidation.proofs[0].receipt_sha256,
      changed_ids: [...geometryValidation.changedIds].sort(),
      historical_claims_transferred: false,
      scope: 'Physical source classes were not recalculated or reinterpreted. Only the validated ownership association changed.'
    };
  }
  validateCoverageManifest(rebound, {...expected, ...release, release_id: release.id,
    canonical_grid_sha256: selectedGridSha256});
  return rebound;
}
