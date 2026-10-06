import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const packet = 'data/regional-review/regional-review-029dcbc646de003d';
const scopePath = path.join(packet, 'scope.json');
const sourceDir = path.join(packet, 'sources');
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const canonName = value => String(value).normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('en').replace(/[^a-z0-9]/g, '');
const indent = depth => ' '.repeat(depth * 2);
function stableJSON(value, depth = 0) {
  if (Array.isArray(value)) {
    if (!value.length) return '[]';
    if (value.every(item => item === null || ['string', 'number', 'boolean'].includes(typeof item))) return `[${value.map(item => JSON.stringify(item)).join(', ')}]`;
    return `[\n${value.map(item => `${indent(depth + 1)}${JSON.stringify(item)}`).join(',\n')}\n${indent(depth)}]`;
  }
  if (value && typeof value === 'object') {
    const entries = Object.entries(value);
    if (!entries.length) return '{}';
    return `{\n${entries.map(([key, item]) => `${indent(depth + 1)}${JSON.stringify(key)}: ${stableJSON(item, depth + 1)}`).join(',\n')}\n${indent(depth)}}`;
  }
  return JSON.stringify(value);
}

let savedScope;
if (fs.existsSync(scopePath)) {
  savedScope = JSON.parse(fs.readFileSync(scopePath, 'utf8'));
} else {
  const issue = JSON.parse(execFileSync('gh', ['api', 'repos/ChengshuLi/WorldAtlas/issues/411'], {encoding: 'utf8'}));
  const block = [...issue.body.matchAll(/```json\n([\s\S]*?)\n```/g)].map(m => JSON.parse(m[1])).find(x => x.batch_id === 'regional-review:029dcbc646de003d');
  if (!block) throw new Error('Could not find the issue-pinned machine-readable scope');
  savedScope = {
    issue: 411,
    title: issue.title,
    url: issue.html_url,
    retrieved_at: new Date().toISOString(),
    issue_created_at: issue.created_at,
    issue_body_sha256: sha(Buffer.from(issue.body, 'utf8')),
    member_location_ids_sha256_declared: block.member_location_ids_sha256,
    scope: block
  };
  fs.writeFileSync(scopePath, JSON.stringify(savedScope, null, 2) + '\n', {flag: 'wx'});
}

const scope = savedScope.scope;
const ids = scope.member_location_ids;
if (ids.length !== scope.location_count || new Set(ids).size !== ids.length) throw new Error('Issue scope count or uniqueness failure');
const jsonArrayDigest = sha(Buffer.from(JSON.stringify(ids), 'utf8'));
const declaredDigest = sha(Buffer.from([...ids].sort().join('\n'), 'utf8'));
if (declaredDigest !== scope.member_location_ids_sha256) {
  throw new Error(`Issue member digest mismatch: declared ${scope.member_location_ids_sha256}; sorted newline SHA-256 ${declaredDigest}`);
}

const baselineCommit = savedScope.baseline_commit ?? execFileSync('git', ['rev-parse', 'HEAD'], {encoding: 'utf8'}).trim();
const sourceByISO = {AGO: 'geoBoundaries-AGO-ADM2-2018.geojson', MOZ: 'geoBoundaries-MOZ-ADM2-2019.geojson', MWI: 'geoBoundaries-MWI-ADM2-2020.geojson'};
const sources = {};
for (const [iso, filename] of Object.entries(sourceByISO)) {
  const bytes = fs.readFileSync(path.join(sourceDir, filename));
  const geo = JSON.parse(bytes);
  if (geo.type !== 'FeatureCollection' || !Array.isArray(geo.features)) throw new Error(`Invalid source GeoJSON ${filename}`);
  sources[iso] = {filename, sha256: sha(bytes), bytes: bytes.length, features: geo.features};
}

const baselineFeatures = [];
for (const part of ['data/geography/part-16.json', 'data/geography/part-29.json']) {
  const bytes = fs.readFileSync(part);
  const geo = JSON.parse(bytes);
  baselineFeatures.push(...geo.features.map(feature => ({...feature, _part: part, _part_sha256: sha(bytes)})));
}
const atlasByID = new Map();
for (const feature of baselineFeatures) {
  const id = feature.properties?.id ?? feature.id;
  if (atlasByID.has(id)) throw new Error(`Duplicate baseline identity ${id}`);
  atlasByID.set(id, feature);
}

const sourceByID = new Map();
for (const [iso, source] of Object.entries(sources)) {
  for (const feature of source.features) {
    const p = feature.properties ?? {};
    const id = `gb:${iso}:${p.shapeType}:${p.shapeID}`;
    if (sourceByID.has(id)) throw new Error(`Duplicate native source identity ${id}`);
    sourceByID.set(id, {iso, feature, source});
  }
}

const rows = ids.map(id => {
  const atlas = atlasByID.get(id);
  const native = sourceByID.get(id);
  if (!atlas) throw new Error(`Scoped ID missing from pinned containing parts: ${id}`);
  if (!native) throw new Error(`Scoped ID missing from retained original source: ${id}`);
  const p = atlas.properties;
  const s = native.feature.properties ?? {};
  const geometry = native.feature.geometry;
  const type = geometry?.type ?? null;
  const polygons = type === 'Polygon' ? [geometry.coordinates] : type === 'MultiPolygon' ? geometry.coordinates : [];
  const closedRings = polygons.flatMap(poly => poly).every(ring => ring.length > 3 && JSON.stringify(ring[0]) === JSON.stringify(ring.at(-1)));
  const finiteCoordinates = polygons.flatMap(poly => poly.flatMap(ring => ring)).every(pos => pos.length >= 2 && pos.every(Number.isFinite));
  return {
    id,
    iso: native.iso,
    atlas_name: p.name,
    source_name: s.shapeName,
    normalized_name_match: canonName(p.name) === canonName(s.shapeName),
    source_role: p.metadata?.source_role ?? null,
    source_year: p.metadata?.reference_year ?? null,
    assigned_parent_id: p.parent_id ?? null,
    source_id: p.metadata?.source_id ?? null,
    source_url: p.metadata?.source_url ?? null,
    source_license: p.metadata?.license ?? null,
    native_shape_id: s.shapeID ?? null,
    native_shape_group: s.shapeGroup ?? null,
    native_shape_type: s.shapeType ?? null,
    source_geometry_type: type,
    source_polygon_component_count: polygons.length,
    source_ring_count: polygons.reduce((n, poly) => n + poly.length, 0),
    source_rings_closed: closedRings,
    source_coordinates_finite: finiteCoordinates,
    atlas_source_geometry_identical: JSON.stringify(atlas.geometry) === JSON.stringify(geometry),
    atlas_part: atlas._part,
    atlas_part_sha256: atlas._part_sha256
  };
});

const byISO = {};
for (const iso of Object.keys(sourceByISO)) {
  const source = sources[iso];
  const owned = rows.filter(r => r.iso === iso);
  const outsideIDs = source.features.map(f => `gb:${iso}:${f.properties.shapeType}:${f.properties.shapeID}`).filter(id => !ids.includes(id));
  byISO[iso] = {
    owned_scope_count: owned.length,
    native_source_feature_count: source.features.length,
    outside_exact_issue_scope_count: outsideIDs.length,
    outside_exact_issue_scope_native_ids: outsideIDs,
    owned_name_mismatch_count: owned.filter(r => !r.normalized_name_match).length,
    owned_geometry_identity_count: owned.filter(r => r.atlas_source_geometry_identical).length,
    owned_multipolygon_count: owned.filter(r => r.source_polygon_component_count > 1).length,
    owned_bad_ring_count: owned.filter(r => !r.source_rings_closed).length,
    source: {path: `${packet}/sources/${source.filename}`, bytes: source.bytes, sha256: source.sha256}
  };
}

const provinceGroups = new Map();
for (const row of rows) {
  const list = provinceGroups.get(row.assigned_parent_id) ?? [];
  list.push(row.id);
  provinceGroups.set(row.assigned_parent_id, list);
}
const summary = {
  version: 1,
  method: 'Exact scope ID -> native geoBoundaries shapeID crosswalk; source-vs-pinned-atlas name and geometry byte-structure comparison; source polygon/ring diagnostics. No topology validity, boundary accuracy or territorial approval is inferred.',
  issue: savedScope.issue,
  retrieved_at: savedScope.retrieved_at,
  issue_body_sha256: savedScope.issue_body_sha256,
  issue_member_location_ids_sha256: scope.member_location_ids_sha256,
  member_ids_sorted_newline_sha256: declaredDigest,
  member_ids_json_array_sha256: jsonArrayDigest,
  baseline_commit: baselineCommit,
  baseline_files: ['data/world-index.json', 'data/geography/part-16.json', 'data/geography/part-29.json', 'data/hierarchy.json', 'data/macro-foundation/regional-handoffs.json.gz', 'data/macro-foundation/current-membership-inventory.json.gz'].map(p => {
    execFileSync('git', ['diff', '--quiet', 'HEAD', '--', p]);
    const bytes = fs.readFileSync(p);
    return {path: p, bytes: bytes.length, sha256: sha(bytes)};
  }),
  issue_scope_count: ids.length,
  matched_scope_count: rows.length,
  unique_scope_ids: new Set(ids).size,
  country_summary: byISO,
  parent_scope_counts: Object.fromEntries([...provinceGroups].sort(([a], [b]) => a.localeCompare(b)).map(([parent, members]) => [parent, members.length])),
  rows
};
const outputArg = process.argv.indexOf('--output');
const outputName = outputArg >= 0 ? process.argv[outputArg + 1] : `${packet}/scope-reproduction.reproduced.json`;
if (!outputName) throw new Error('--output requires a path');
const outputPath = path.isAbsolute(outputName) ? outputName : path.resolve(root, outputName);
fs.writeFileSync(outputPath, stableJSON(summary) + '\n', {flag: 'wx'});
console.log(`Reproduction written once to ${outputPath}`);
console.log(JSON.stringify({issue_scope_count: summary.issue_scope_count, matched_scope_count: summary.matched_scope_count, country_summary: byISO, parent_scope_counts: summary.parent_scope_counts}, null, 2));
