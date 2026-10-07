import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import {gunzipSync} from 'node:zlib';

const root = process.cwd();
const originalPacket = 'data/regional-review/regional-review-029dcbc646de003d';
const packet = 'data/regional-review/southern-africa-411-crosswalk-validation-1047-erratum';
const args = process.argv.slice(2);
function option(name, fallback) {
  const at = args.indexOf(`--${name}`);
  if (at < 0) return fallback;
  if (!args[at + 1]) throw new Error(`--${name} requires a path`);
  return path.resolve(args[at + 1]);
}
const crosswalkPath = option('crosswalk', path.join(root, originalPacket, 'scope-reproduction.json'));
const assessmentPath = option('assessments', path.join(root, originalPacket, 'row-assessments.json'));
const outputPath = option('output');
if (!outputPath) throw new Error('--output is required');
if (!path.relative(root, outputPath) || path.relative(root, outputPath).startsWith('..')) {
  throw new Error('Output must remain inside the repository');
}
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const readJSON = filename => JSON.parse(fs.readFileSync(filename, 'utf8'));
const fail = message => { throw new Error(message); };
const check = (condition, message) => { if (!condition) fail(message); };
const gitBytes = (commit, filename) => execFileSync('git', ['show', `${commit}:${filename}`], {maxBuffer: 64 * 1024 * 1024});
const canonicalName = value => String(value).normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('en').replace(/[^a-z0-9]/g, '');
const equal = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const originalEvidenceCommit = '762d7b5a568ca845d85a98a4d188678c126a5d58';
const scopeSnapshot = JSON.parse(gitBytes(originalEvidenceCommit, `${originalPacket}/scope.json`).toString('utf8'));
const reproduction = readJSON(crosswalkPath);
const assessments = readJSON(assessmentPath);
const sourceReview = JSON.parse(gitBytes(originalEvidenceCommit, `${originalPacket}/source-review.json`).toString('utf8'));
const ids = scopeSnapshot.scope?.member_location_ids;
check(scopeSnapshot.issue === 411 && Array.isArray(ids), 'missing frozen #411 scope');
check(ids.length === 223 && new Set(ids).size === ids.length, 'frozen #411 scope must contain exactly 223 unique IDs');
check(scopeSnapshot.scope.location_count === ids.length, 'frozen issue count differs from raw ID list');
check(sha(Buffer.from([...ids].sort().join('\n'))) === scopeSnapshot.scope.member_location_ids_sha256,
  'frozen scope ID digest mismatch');
check(scopeSnapshot.issue_body_sha256 === reproduction.issue_body_sha256, 'crosswalk issue body digest differs from frozen scope');
check(scopeSnapshot.scope.member_location_ids_sha256 === reproduction.issue_member_location_ids_sha256,
  'crosswalk frozen member digest differs from scope');
check(scopeSnapshot.baseline_commit === reproduction.baseline_commit, 'crosswalk is bound to a different baseline commit');
check(reproduction.version === 1 && reproduction.issue === 411, 'crosswalk version or issue mismatch');
check(reproduction.issue_scope_count === ids.length, 'declared crosswalk scope count mismatch');
check(Array.isArray(reproduction.rows) && reproduction.rows.length === ids.length, 'actual crosswalk row count differs from frozen scope');
check(reproduction.matched_scope_count === reproduction.rows.length, 'self-reported matched count differs from actual rows');
check(reproduction.unique_scope_ids === new Set(reproduction.rows.map(row => row.id)).size,
  'self-reported unique count differs from actual crosswalk rows');

const idSet = new Set(ids);
const crosswalkIds = reproduction.rows.map(row => row.id);
check(crosswalkIds.every(id => typeof id === 'string') && new Set(crosswalkIds).size === crosswalkIds.length,
  'crosswalk rows contain duplicate or invalid IDs');
check(equal([...crosswalkIds].sort(), [...idSet].sort()), 'crosswalk IDs do not exactly equal the frozen 223-member scope');
const assessedIds = assessments.rows?.map(row => row.id) ?? [];
check(assessedIds.length === ids.length && new Set(assessedIds).size === assessedIds.length,
  'actual assessment rows must contain exactly 223 unique IDs');
check(equal([...assessedIds].sort(), [...idSet].sort()), 'assessment IDs do not exactly equal the frozen scope');
check(assessments.issue === 411, 'assessment issue mismatch');
check(assessments.scope_reproduction_sha256 === sha(fs.readFileSync(crosswalkPath)),
  'assessment does not bind the complete consumed crosswalk bytes');

const baselineFiles = reproduction.baseline_files;
check(Array.isArray(baselineFiles) && baselineFiles.length === 6, 'baseline file roster must retain all six original pins');
const baselineByPath = new Map();
for (const descriptor of baselineFiles) {
  check(/^data\/[A-Za-z0-9_./-]+$/.test(descriptor.path) && !descriptor.path.split('/').includes('..'),
    `unsafe baseline path: ${descriptor.path}`);
  const bytes = gitBytes(scopeSnapshot.baseline_commit, descriptor.path);
  check(bytes.length === descriptor.bytes && sha(bytes) === descriptor.sha256, `original baseline pin mismatch: ${descriptor.path}`);
  baselineByPath.set(descriptor.path, {bytes, sha256: sha(bytes)});
}
for (const pathName of ['data/world-index.json', 'data/geography/part-16.json', 'data/geography/part-29.json',
  'data/hierarchy.json', 'data/macro-foundation/regional-handoffs.json.gz',
  'data/macro-foundation/current-membership-inventory.json.gz']) {
  check(baselineByPath.has(pathName), `required original baseline path missing: ${pathName}`);
}

const atlasById = new Map();
for (const part of ['data/geography/part-16.json', 'data/geography/part-29.json']) {
  const bytes = baselineByPath.get(part).bytes;
  const geo = JSON.parse(bytes.toString('utf8'));
  check(geo.type === 'FeatureCollection' && Array.isArray(geo.features), `invalid baseline feature collection: ${part}`);
  for (const feature of geo.features) {
    const id = feature.properties?.id ?? feature.id;
    if (!id) continue;
    check(!atlasById.has(id), `duplicate baseline Atlas subject: ${id}`);
    atlasById.set(id, {feature, part, partSha: baselineByPath.get(part).sha256});
  }
}
for (const id of ids) check(atlasById.has(id), `frozen subject absent from its pinned Atlas part: ${id}`);
const hierarchy = JSON.parse(baselineByPath.get('data/hierarchy.json').bytes.toString('utf8'));
const hierarchyById = new Map(hierarchy.map(node => [node.id, node]));

const retainedSourceByPath = new Map();
for (const source of sourceReview.sources) {
  if (!source.artifact_path) continue;
  const relative = `${originalPacket}/${source.artifact_path}`;
  const bytes = gitBytes(originalEvidenceCommit, relative);
  check(bytes.length === source.bytes && sha(bytes) === source.sha256, `retained source pin mismatch: ${source.id}`);
  if (source.raw_sha256 !== undefined) {
    const raw = gunzipSync(bytes);
    check(raw.length === source.raw_bytes && sha(raw) === source.raw_sha256, `restored attribution pin mismatch: ${source.id}`);
  }
  if (/\.geojson$/i.test(source.artifact_path)) {
    const geo = JSON.parse(bytes.toString('utf8'));
    check(geo.type === 'FeatureCollection' && Array.isArray(geo.features), `invalid retained source collection: ${source.id}`);
    retainedSourceByPath.set(source.artifact_path, {source, bytes, features: geo.features});
  }
}
check(retainedSourceByPath.size === 3, 'expected all three original source GeoJSON collections');
const sourceById = new Map();
for (const {source, features} of retainedSourceByPath.values()) {
  for (const feature of features) {
    const p = feature.properties ?? {};
    const id = `gb:${p.shapeGroup}:${p.shapeType}:${p.shapeID}`;
    check(p.shapeID && p.shapeGroup && p.shapeType, `source feature lacks native identity in ${source.id}`);
    check(!sourceById.has(id), `duplicate native source identity: ${id}`);
    sourceById.set(id, {feature, source});
  }
}

const polygonCoordinates = geometry => geometry?.type === 'Polygon' ? [geometry.coordinates]
  : geometry?.type === 'MultiPolygon' ? geometry.coordinates : [];
const expectedCrosswalkRows = new Map();
const countryCounts = {};
const parentCounts = {};
for (const row of reproduction.rows) {
  const atlasMatch = atlasById.get(row.id);
  const nativeMatch = sourceById.get(row.id);
  check(atlasMatch && nativeMatch, `crosswalk ID lacks a pinned Atlas or native-source match: ${row.id}`);
  const atlas = atlasMatch.feature;
  const ap = atlas.properties ?? {};
  const source = nativeMatch.feature;
  const sp = source.properties ?? {};
  const metadata = ap.metadata ?? {};
  check(hierarchyById.has(ap.parent_id), `assigned parent missing from the pinned hierarchy: ${row.id}`);
  const geometry = source.geometry;
  const polygons = polygonCoordinates(geometry);
  const closed = polygons.flatMap(poly => poly).every(ring => ring.length > 3 && equal(ring[0], ring.at(-1)));
  const finite = polygons.flatMap(poly => poly.flatMap(ring => ring)).every(pos => pos.length >= 2 && pos.every(Number.isFinite));
  const actual = {
    id: `gb:${sp.shapeGroup}:${sp.shapeType}:${sp.shapeID}`,
    iso: sp.shapeGroup,
    atlas_name: ap.name,
    source_name: sp.shapeName,
    normalized_name_match: canonicalName(ap.name) === canonicalName(sp.shapeName),
    source_role: metadata.source_role ?? null,
    source_year: metadata.reference_year ?? null,
    assigned_parent_id: ap.parent_id ?? null,
    source_id: metadata.source_id ?? null,
    source_url: metadata.source_url ?? null,
    source_license: metadata.license ?? null,
    native_shape_id: sp.shapeID ?? null,
    native_shape_group: sp.shapeGroup ?? null,
    native_shape_type: sp.shapeType ?? null,
    source_geometry_type: geometry?.type ?? null,
    source_polygon_component_count: polygons.length,
    source_ring_count: polygons.reduce((count, poly) => count + poly.length, 0),
    source_rings_closed: closed,
    source_coordinates_finite: finite,
    atlas_source_geometry_identical: equal(atlas.geometry, geometry),
    atlas_part: atlasMatch.part,
    atlas_part_sha256: atlasMatch.partSha
  };
  for (const [key, value] of Object.entries(actual)) check(equal(row[key], value), `crosswalk ${key} differs from source/baseline for ${row.id}`);
  expectedCrosswalkRows.set(row.id, actual);
  countryCounts[row.iso] = (countryCounts[row.iso] ?? 0) + 1;
  parentCounts[row.assigned_parent_id] = (parentCounts[row.assigned_parent_id] ?? 0) + 1;
}
check(equal(Object.fromEntries(Object.entries(parentCounts).sort(([a], [b]) => a.localeCompare(b))),
  Object.fromEntries(Object.entries(reproduction.parent_scope_counts ?? {}).sort(([a], [b]) => a.localeCompare(b)))),
'parent scope summary is not derived from the actual crosswalk rows');
check(equal(countryCounts, {AGO: 157, MOZ: 38, MWI: 28}), 'actual crosswalk country totals differ from the frozen workload');

const assessmentById = new Map(assessments.rows.map(row => [row.id, row]));
for (const [id, crosswalk] of expectedCrosswalkRows) {
  const row = assessmentById.get(id);
  check(row, `assessment row missing for ${id}`);
  const expected = {
    country: crosswalk.iso,
    location_name: crosswalk.atlas_name,
    source_name: crosswalk.source_name,
    source_vintage: crosswalk.source_year,
    source_role: crosswalk.source_role,
    assigned_parent_id: crosswalk.assigned_parent_id,
    assigned_parent_name: hierarchyById.get(crosswalk.assigned_parent_id)?.name ?? null,
    native_source_feature_matched: true,
    source_name_crosswalk_matched: crosswalk.normalized_name_match,
    source_native_id: crosswalk.native_shape_id,
    source_registry_id: crosswalk.source_id,
    source_artifact_sha256: reproduction.country_summary[crosswalk.iso].source.sha256,
    atlas_part_path: crosswalk.atlas_part,
    atlas_part_sha256: crosswalk.atlas_part_sha256
  };
  for (const [key, value] of Object.entries(expected)) check(equal(row[key], value), `assessment ${key} is not joined to its crosswalk/source for ${id}`);
}
const classificationCounts = Object.fromEntries(['justified', 'correction-needed', 'insufficient-evidence']
  .map(key => [key, assessments.rows.filter(row => row.classification === key).length]));
check(equal(classificationCounts, assessments.counts), 'assessment classification counts do not match actual rows');
check(equal(classificationCounts, {justified: 0, 'correction-needed': 1, 'insufficient-evidence': 222}),
  'frozen scientific dispositions changed');
check(reproduction.country_summary.AGO?.owned_scope_count === 157 &&
  reproduction.country_summary.MOZ?.owned_scope_count === 38 && reproduction.country_summary.MWI?.owned_scope_count === 28,
  'crosswalk country summary differs from actual subject rows');

const result = {
  version: 1,
  issue: 1279,
  reviewed_issue: 411,
  baseline_commit: scopeSnapshot.baseline_commit,
  frozen_subject_count: ids.length,
  frozen_subjects_sha256: sha(Buffer.from(JSON.stringify([...ids].sort()))),
  crosswalk: {path: path.relative(root, crosswalkPath), bytes: fs.statSync(crosswalkPath).size, sha256: sha(fs.readFileSync(crosswalkPath)), rows: reproduction.rows.length, unique_ids: new Set(crosswalkIds).size},
  assessments: {path: path.relative(root, assessmentPath), bytes: fs.statSync(assessmentPath).size, sha256: sha(fs.readFileSync(assessmentPath)), rows: assessments.rows.length},
  source_subject_joins: {AGO: countryCounts.AGO, MOZ: countryCounts.MOZ, MWI: countryCounts.MWI},
  assessment_classifications: classificationCounts,
  checked_baseline_files: [...baselineByPath.keys()],
  retained_geoboundaries_source_hashes: [...retainedSourceByPath.entries()].map(([sourcePath, value]) => ({path: `${originalPacket}/${sourcePath}`, bytes: value.bytes.length, sha256: sha(value.bytes)})),
  limitations: [
    'This validates exact crosswalk and assessment membership/correlation against retained source bytes and the pinned Atlas baseline.',
    'It does not establish current administrative legality, geographic accuracy, source completeness, neighboring granularity, topology, or regional approval.',
    'Inherited official-source retrieval and license gaps remain those recorded in the original packet; this erratum makes no new source or territorial claim.'
  ]
};
fs.mkdirSync(path.dirname(outputPath), {recursive: true});
fs.writeFileSync(outputPath, `${JSON.stringify(result, null, 2)}\n`, {flag: 'wx'});
console.log(JSON.stringify({issue: result.issue, reviewed_issue: result.reviewed_issue, rows: result.crosswalk.rows,
  assessments: result.assessments.rows, source_subject_joins: result.source_subject_joins,
  assessment_classifications: result.assessment_classifications}, null, 2));
