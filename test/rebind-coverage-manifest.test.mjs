import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {rebindCoverageManifest} from '../scripts/rebind-coverage-manifest.mjs';
const originalBytes = await fs.readFile('data/canonical-grid/manifest.json');
const selectedBytes = await fs.readFile('coordination/engineering/native-grid-candidate-1010-20261005-local16/candidate-v1/manifest.json');
const originalGrid = JSON.parse(originalBytes), selectedGrid = JSON.parse(selectedBytes);
const classification = JSON.parse(await fs.readFile('data/coverage-classification/manifest.json'));
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const context = {originalGrid, originalGridSha256: digest(originalBytes), selectedGrid,
  selectedGridSha256: digest(selectedBytes), release: {id: selectedGrid.geographic_release,
    footprints_sha256: selectedGrid.footprints_sha256, hierarchy_sha256: selectedGrid.hierarchy_sha256}};

test('native ownership binding retains all original physical bytes, sources, domain and uncertainties', () => {
  const before = JSON.stringify(classification), rebound = rebindCoverageManifest(classification, context);
  assert.equal(JSON.stringify(classification), before);
  assert.equal(rebound.canonical_grid_sha256, context.selectedGridSha256);
  const {ownership_binding, ...originalFields} = rebound;
  originalFields.canonical_grid_sha256 = classification.canonical_grid_sha256;
  assert.deepEqual(originalFields, classification);
  assert.equal(ownership_binding.original_canonical_grid_sha256, context.originalGridSha256);
  assert.equal(ownership_binding.selected_method, selectedGrid.method);
});

test('changed coordinate grid, sources, release or original ownership binding prohibit reuse', () => {
  for (const key of ['size', 'coordinateBits', 'footprints_sha256', 'hierarchy_sha256']) {
    const changed = {...selectedGrid, [key]: typeof selectedGrid[key] === 'number' ? selectedGrid[key] + 1 : '0'.repeat(64)};
    assert.throws(() => rebindCoverageManifest(classification, {...context, selectedGrid: changed}));
  }
  assert.throws(() => rebindCoverageManifest(classification, {...context, release: {...context.release, id: 'geography:other'}}));
  assert.throws(() => rebindCoverageManifest(classification, {...context, originalGridSha256: '0'.repeat(64)}));
  assert.throws(() => rebindCoverageManifest({...classification, sources: []}, context));
});
