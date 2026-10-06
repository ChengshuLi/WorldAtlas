// Versioned offline candidate contract; no default selection or asset mutation.
import {NATIVE_GRID_METHOD} from '../../src/native-grid.js';

export const NATIVE_CANONICAL_LATITUDE_SHA256 = '66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23';
const hash = value => /^[a-f0-9]{64}$/.test(value ?? '');
const commit = value => /^[a-f0-9]{40}$/.test(value ?? '');
const requireValue = (ok, message) => { if (!ok) throw Error(message); };

export function nativeCandidateManifest({original, originalSha256, baselineCommit,
  evaluationCommit, releaseId, rosterSha256, ownerCount, latitude, compiled}) {
  requireValue(original?.version === 2 && original.size === 262166 && original.coordinateBits === 19,
    'Original canonical convention differs');
  requireValue(hash(originalSha256) && hash(rosterSha256) && commit(baselineCommit) && commit(evaluationCommit),
    'Missing immutable original/code/roster pins');
  requireValue(hash(original.footprints_sha256) && hash(original.hierarchy_sha256) &&
    typeof releaseId === 'string' && releaseId.startsWith('geography:'), 'Original release pins differ');
  requireValue(Array.isArray(original.provinces) && new Set(original.provinces).size === original.provinces.length &&
    original.provinces.every(id => typeof id === 'string' && id.length), 'Original province inventory differs');
  for (const [descriptor, expected] of [[original.bounds, 'bounds.json.gz'],
    [original.province_membership, 'province-membership.bin.gz']])
    requireValue(descriptor?.path === expected && hash(descriptor.sha256), 'Original identity asset descriptor differs');
  requireValue(latitude?.path === 'coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz' &&
    latitude.root === 'repository' && latitude.role === 'immutable-normative-rule-input' &&
    latitude.commit === evaluationCommit && hash(latitude.sha256) &&
    latitude.decoded_sha256 === NATIVE_CANONICAL_LATITUDE_SHA256 && latitude.decoded_bytes === original.size * 8 &&
    Number.isSafeInteger(latitude.bytes) && latitude.bytes > 0 && latitude.bytes <= 32 * 1024 * 1024,
    'Missing exact normative latitude bytes');
  requireValue(compiled?.method === NATIVE_GRID_METHOD && compiled.version === 2 &&
    compiled.size === original.size && compiled.coordinateBits === original.coordinateBits &&
    compiled.checked_rows === original.size && compiled.checked_cells === original.size ** 2 &&
    compiled.unchecked_cells === 0, 'Candidate method or complete domain differs');
  requireValue(Number.isSafeInteger(compiled.runWords) && compiled.runWords >= 0 && compiled.runWords % 2 === 0 &&
    compiled.runWords / 2 <= 2 ** 32 - 1 && Array.isArray(compiled.parts), 'Invalid compact candidate accounting');
  const seen = new Set();
  for (const kind of ['rows', 'runs']) {
    let offset = 0;
    for (const part of compiled.parts.filter(p => p.kind === kind)) {
      requireValue(part.offset === offset && Number.isInteger(part.words) && part.words > 0 &&
        part.words <= 1048576 && (kind !== 'runs' || part.words % 2 === 0) &&
        part.path === `native-v1/ownership/${kind}-${offset}.bin.gz` && !seen.has(part.path) &&
        part.encoding === 'byte-shuffle' && hash(part.sha256) && hash(part.decoded_sha256) &&
        part.decoded_bytes === part.words * 4 && Number.isInteger(part.bytes) && part.bytes > 0 &&
        part.bytes <= 32 * 1024 * 1024, 'Unsafe or incomplete candidate part proof');
      seen.add(part.path); offset += part.words;
    }
    requireValue(offset === (kind === 'rows' ? original.size * 2 : compiled.runWords), 'Incomplete candidate parts');
  }
  requireValue(seen.size === compiled.parts.length, 'Unknown candidate part kind');
  const owners = compiled.per_owner_cells;
  requireValue(Number.isInteger(ownerCount) && ownerCount > 0 && ownerCount < 2 ** 26 &&
    Array.isArray(owners) && owners.length === ownerCount && owners.every((r, i) => Array.isArray(r) && r.length === 2 &&
    r[0] === i + 1 && Number.isSafeInteger(r[1]) && r[1] >= 0) &&
    owners.reduce((n, r) => n + r[1], 0) === compiled.owned_cells &&
    Number.isSafeInteger(compiled.owned_cells) && compiled.owned_cells >= 0 &&
    compiled.owned_cells <= original.size ** 2, 'Incomplete stable owner accounting');
  // Deliberately do not copy legacy samples, stats or unrecognised method fields.
  // Original bounds/membership are referenced in place, never duplicated/rebuilt.
  return {
    asset_root: 'data/canonical-grid',
    version: 2, coordinateBits: original.coordinateBits, size: original.size,
    method: NATIVE_GRID_METHOD, runWords: compiled.runWords,
    parts: compiled.parts.map(p => ({...p})), native_latitudes: {...latitude},
    footprints_sha256: original.footprints_sha256, hierarchy_sha256: original.hierarchy_sha256,
    geographic_release: releaseId, provinces: [...original.provinces],
    bounds: {...original.bounds}, province_membership: {...original.province_membership},
    original_assets: {
      bounds: {commit: baselineCommit, path: 'data/canonical-grid/' + original.bounds.path,
        sha256: original.bounds.sha256, role: 'original-identity-parent-camera-context'},
      province_membership: {commit: baselineCommit, path: 'data/canonical-grid/' + original.province_membership.path,
        sha256: original.province_membership.sha256, role: 'original-identity-crosswalk'}
    },
    provenance: {baseline_commit: baselineCommit, evaluation_commit: evaluationCommit,
      original_canonical_sha256: originalSha256, owner_roster_sha256: rosterSha256,
      original_source_point_sets_unchanged: true},
    accounting: {checked_rows: compiled.checked_rows, checked_cells: compiled.checked_cells,
      unchecked_cells: 0, owned_cells: compiled.owned_cells, owners: owners.length},
    scientific_approval: false, installation_ready: false
  };
}
