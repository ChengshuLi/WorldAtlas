import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {gunzipSync} from 'node:zlib';

const owned = 'data/regional-review/regional-review-5cf69eed7fdff0b5';
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const read = file => fs.readFileSync(file);
const json = file => JSON.parse(read(file));
const root = process.cwd();
const snapshotPath = path.join(owned, 'source/issue-393-api-snapshot.json');
const snapshotBytes = read(snapshotPath);
const issue = JSON.parse(snapshotBytes);
if (issue.number !== 393 || issue.state !== 'open') throw Error('Issue snapshot is not the open #393 issue');
const sourceInventory = json(path.join(owned, 'source-inventory.json'));
const baselineCommit = sourceInventory.baseline_commit;
if (!/^[0-9a-f]{40}$/.test(baselineCommit)) throw Error('Source inventory must pin the reviewed baseline commit.');
execFileSync('git', ['cat-file', '-e', `${baselineCommit}^{commit}`]);
execFileSync('git', ['merge-base', '--is-ancestor', baselineCommit, 'HEAD']);
const baselineBlob = file => execFileSync('git', ['show', `${baselineCommit}:${file}`], {maxBuffer: 64 * 1024 * 1024});
const verifyBaselineBytes = (file, bytes) => {
  if (!baselineBlob(file).equals(bytes)) throw Error(`Input ${file} differs from pinned baseline ${baselineCommit}`);
};
const match = issue.body.match(/Machine-readable exact workload scope \(JSON;[^\n]*\):\n\n```json\n([\s\S]*?)\n```/);
if (!match) throw Error('Exact machine scope JSON was not found');
const scope = JSON.parse(match[1]);
const ids = scope.member_location_ids;
if (!Array.isArray(ids) || ids.length !== 207 || new Set(ids).size !== ids.length) throw Error('Issue scope is not the exact 207 unique IDs');
const expectedDigest = sha(Buffer.from(ids.join('\n')));
if (expectedDigest !== scope.member_location_ids_sha256) throw Error('Issue member ID digest mismatch');

const indexBytes = read('data/world-index.json');
verifyBaselineBytes('data/world-index.json', indexBytes);
const index = JSON.parse(indexBytes);
const wanted = new Set(ids);
const features = new Map();
const partBytes = {};
for (const relative of index.parts) {
  const file = path.join('data', relative);
  const bytes = read(file);
  verifyBaselineBytes(file, bytes);
  partBytes[file] = {bytes: bytes.length, sha256: sha(bytes)};
  const collection = JSON.parse(bytes);
  for (const feature of collection.features ?? []) {
    const id = feature.id ?? feature.properties?.id;
    if (!wanted.has(id)) continue;
    if (features.has(id)) throw Error(`Duplicate pinned feature ${id}`);
    features.set(id, {feature, file});
  }
}
if (features.size !== ids.length) throw Error(`Only ${features.size}/${ids.length} exact subjects found in indexed geometry`);

const hierarchyBytes = read('data/hierarchy.json');
verifyBaselineBytes('data/hierarchy.json', hierarchyBytes);
const hierarchy = new Map(JSON.parse(hierarchyBytes).map(record => [record.id, record]));
const counts = new Map();
const parents = new Map();
const rows = ids.map(id => {
  const {feature, file} = features.get(id);
  const p = feature.properties ?? {};
  const m = p.metadata ?? {};
  const parent = hierarchy.get(p.parent_id);
  const key = `${m.source_id ?? 'unknown'}|${m.source_name ?? 'unknown'}|${m.source_role ?? 'unknown'}`;
  counts.set(key, (counts.get(key) ?? 0) + 1);
  const parentKey = `${p.parent_id ?? 'missing'}|${parent?.name ?? 'missing'}`;
  parents.set(parentKey, (parents.get(parentKey) ?? 0) + 1);
  return {
    id,
    current_name: p.name ?? null,
    current_parent_id: p.parent_id ?? null,
    current_parent_name: parent?.name ?? null,
    feature_path: file,
    geometry_type: feature.geometry?.type ?? null,
    source_id: m.source_id ?? null,
    source_name: m.source_name ?? null,
    source_url: m.source_url ?? null,
    source_license: m.license ?? null,
    source_reference_year: m.reference_year ?? null,
    source_role: m.source_role ?? null,
    source_level: m.administrative_level ?? null,
    source_original_id: m.original_id ?? null,
    source_member_ids: m.source_member_ids ?? [],
    location_basis: m.location_basis ?? null,
    selection_reason: m.selection_reason ?? null,
  };
});

const handoffBytes = read('data/macro-foundation/regional-handoffs.json.gz');
verifyBaselineBytes('data/macro-foundation/regional-handoffs.json.gz', handoffBytes);
const handoffs = JSON.parse(gunzipSync(handoffBytes));
const region = handoffs.regions?.find(value => value.region_id === scope.region_id);
if (!region) throw Error(`Pinned macro handoff lacks ${scope.region_id}`);
if (region.envelope?.geometry_sha256 !== scope.frozen_region_geometry_sha256 ||
    region.envelope?.member_location_ids_sha256 !== scope.frozen_region_member_ids_sha256) {
  throw Error('Issue frozen region envelope/member pins differ from current handoff');
}
const sourceDistribution = Object.fromEntries([...counts.entries()].sort(([a], [b]) => a.localeCompare(b)));
const parentDistribution = Object.fromEntries([...parents.entries()].sort(([a], [b]) => a.localeCompare(b)));
process.stdout.write(JSON.stringify({
  version: 1,
  issue: 393,
  baseline_commit: baselineCommit,
  scope: {
    batch_id: scope.batch_id,
    region_id: scope.region_id,
    location_count: ids.length,
    member_location_ids_sha256: scope.member_location_ids_sha256,
    exact_issue_scope_ids_sha256_recomputed: expectedDigest,
    all_ids_unique: true,
    all_ids_found_once_in_indexed_features: true,
    issue_source_ids: scope.source_ids,
    province_scopes: scope.province_scopes,
  },
  frozen_pins: {
    release: scope.release,
    macro_certificate_sha256: scope.macro_certificate_sha256,
    frozen_region_geometry_sha256: scope.frozen_region_geometry_sha256,
    frozen_region_member_ids_sha256: scope.frozen_region_member_ids_sha256,
    current_regional_handoff_sha256: sha(handoffBytes),
    current_regional_handoff: {
      region_id: region.region_id,
      name: region.name,
      envelope: region.envelope,
      own_boundary_approved: region.own_boundary_approved,
      regional_interiors_approved: region.regional_interiors_approved,
      publication_verified: region.publication_verified,
      location_attribute_imports_ready: region.location_attribute_imports_ready,
    },
  },
  source_distribution: sourceDistribution,
  parent_distribution: parentDistribution,
  inputs: {
    issue_api_snapshot: {path: snapshotPath, bytes: snapshotBytes.length, sha256: sha(snapshotBytes)},
    world_index: {path: 'data/world-index.json', bytes: indexBytes.length, sha256: sha(indexBytes)},
    hierarchy: {path: 'data/hierarchy.json', bytes: hierarchyBytes.length, sha256: sha(hierarchyBytes)},
    regional_handoffs: {path: 'data/macro-foundation/regional-handoffs.json.gz', bytes: handoffBytes.length, sha256: sha(handoffBytes)},
    indexed_parts: partBytes,
  },
  subjects: rows,
}, null, 2) + '\n');
