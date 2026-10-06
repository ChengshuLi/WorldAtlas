import {validateCoverageManifest} from '../src/coverage-classification.js';
import {ownershipMetadata} from '../src/ownership-method.js';

// Classification assets depend on physical references and the grid coordinate
// domain, not on location ownership. Rebind only that association, retaining
// every original class/source/blocked-tile limit and all encoded asset digests.
export function rebindCoverageManifest(manifest, {originalGrid, originalGridSha256,
  selectedGrid, selectedGridSha256, release}) {
  const expected = {...release, release_id: release.id, canonical_grid_sha256: originalGridSha256,
    size: originalGrid.size, coordinateBits: originalGrid.coordinateBits};
  validateCoverageManifest(manifest, expected);
  ownershipMetadata(selectedGrid, {requireNative: true, expectedReference: release});
  for (const key of ['size', 'coordinateBits', 'footprints_sha256', 'hierarchy_sha256'])
    if (selectedGrid[key] !== originalGrid[key]) throw Error('Physical classification coordinate/source context changed: ' + key);
  if (!/^[a-f0-9]{64}$/.test(selectedGridSha256 ?? '')) throw Error('Missing selected grid digest');
  const rebound = {...structuredClone(manifest), canonical_grid_sha256: selectedGridSha256,
    ownership_binding: {
      original_canonical_grid_sha256: originalGridSha256,
      selected_canonical_grid_sha256: selectedGridSha256,
      selected_method: selectedGrid.method,
      scope: 'Unchanged physical class assets and coordinate grid; location ownership association only. Original source/water uncertainty and blocked tiles remain.'
    }};
  validateCoverageManifest(rebound, {...expected, canonical_grid_sha256: selectedGridSha256});
  return rebound;
}
