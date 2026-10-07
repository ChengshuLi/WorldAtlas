import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {closeSync, mkdirSync, openSync, readFileSync, writeFileSync} from 'node:fs';
import {dirname, resolve} from 'node:path';

const BASE = '42937b066c28eab0c5a53f94c0f5aee7b3d5aae3';
const ROOT = 'data/regional-review/regional-review-626fdf640aab94e2';
const FOLLOWUP = 'data/regional-review/west-siberia-roles-followup-20261006';
const OWNED = 'research/geography/west-siberia-source-atlas-components-2026';
const ISSUE_SNAPSHOT = `${OWNED}/sources/issue-1315-api.json`;
const OUT = resolve(process.argv[2] ?? `${OWNED}/findings/component-comparison.json`);
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
function git(path) {
  return execFileSync('git', ['show', `${BASE}:${path}`], {maxBuffer: 32 * 1024 * 1024});
}
function json(bytes, label) {
  try { return JSON.parse(bytes.toString('utf8')); }
  catch { throw new Error(`Invalid JSON input: ${label}`); }
}
function geometrySummary(geometry) {
  if (!geometry || !['Polygon', 'MultiPolygon'].includes(geometry.type) || !Array.isArray(geometry.coordinates)) {
    throw new Error('Expected nonempty Polygon/MultiPolygon coordinate arrays');
  }
  return {type: geometry.type, components: geometry.type === 'MultiPolygon' ? geometry.coordinates.length : 1};
}
function exactRoster(ids, expected) {
  if (!Array.isArray(ids) || ids.length !== 199 || new Set(ids).size !== 199 ||
      sha(Buffer.from(JSON.stringify([...ids].sort()))) !== sha(Buffer.from(JSON.stringify([...expected].sort())))) {
    throw new Error('Roster is missing, duplicated, or differs from the issue contract');
  }
}
function assert(condition, message) { if (!condition) throw new Error(message); }

const issueBytes = readFileSync(ISSUE_SNAPSHOT);
const originalPointerBytes = readFileSync(`${OWNED}/sources/geoboundaries-rus-adm2-2017-lfs-pointer.txt`);
const originalPointerText = originalPointerBytes.toString('utf8');
assert(originalPointerText === 'version https://git-lfs.github.com/spec/v1\noid sha256:74012237384e53061aa63b6e20b9be24f94facfe615b52bbe72e62a81fa68ff0\nsize 120489189\n',
  'Original-source LFS pointer differs from the official pinned commit response');
const issue = json(issueBytes, ISSUE_SNAPSHOT);
assert(issue.number === 1315 && issue.state === 'open', 'Unexpected current issue snapshot');
const contractMatch = issue.body.match(/<!-- worldatlas-work:v1\s*(\{[\s\S]*?\})\s*-->/);
assert(contractMatch, 'Issue work contract was not found');
const contract = JSON.parse(contractMatch[1]);
const expectedIds = contract.evidence_quality.subject_ids;
assert(expectedIds.length === 199 && new Set(expectedIds).size === 199, 'Issue contract is not exact-199');

const read = {
  source: git(`${ROOT}/sources/geoboundaries-rus-adm2-2017-scoped-original-features.geojson`),
  atlasExtract: git(`${ROOT}/sources/current-scoped-features.geojson`),
  assessments: git(`${ROOT}/findings/member-assessments.json`),
  lineage: git(`${ROOT}/findings/current-lineage.json`),
  followup: git(`${FOLLOWUP}/findings/followup-assessments.json`),
  sourceMetadata: git(`${ROOT}/sources/geoboundaries-rus-adm2-2017-metadata.json`),
  sourceCommit: git(`${ROOT}/sources/geoboundaries-commit-9469f09.json`),
  issue395Scope: git(`${ROOT}/baseline/issue-scope.json`),
  producerAssess: git(`${ROOT}/assess-members.mjs`),
  producerLineage: git(`${ROOT}/reproduce-current-lineage.mjs`),
  producerFollowup: git(`${FOLLOWUP}/reproduce-followup.py`),
  producerExtract: git(`${ROOT}/extract-pinned-source.mjs`),
};
const source = json(read.source, 'original source extract');
const atlasExtract = json(read.atlasExtract, 'Atlas scoped extract');
const assessments = json(read.assessments, 'prior member assessments');
const lineage = json(read.lineage, 'prior current lineage');
const followup = json(read.followup, 'current-law follow-up');
const sourceMetadata = json(read.sourceMetadata, 'geoBoundaries metadata');
const sourceCommit = json(read.sourceCommit, 'geoBoundaries immutable commit response');
const scope395 = json(read.issue395Scope, 'prior exact scope');

assert(source.type === 'FeatureCollection' && atlasExtract.type === 'FeatureCollection', 'Expected GeoJSON FeatureCollections');
assert(source.features.length === 203 && atlasExtract.features.length === 210, 'Unexpected retained extract cardinality');
assert(sourceMetadata.boundaryYear === '2017' && sourceMetadata.boundaryType === 'ADM2' &&
  sourceMetadata.boundaryLicense === 'Open Data Commons Open Database License 1.0', 'Unexpected source vintage/license metadata');
assert(sourceCommit.sha === '9469f09592ced973a3448cf66b6100b741b64c0d', 'Unexpected upstream source commit');
assert(scope395.member_location_ids.length === 210, 'Unexpected prior native/ecoregion scope');
const native = assessments.rows.filter(row => row.source_kind === 'native-adm2');
const nativeIds = native.map(row => row.atlas_id).sort();
exactRoster(nativeIds, expectedIds);
assert(lineage.rows.length === 210 && followup.assessments.length === 45, 'Unexpected predecessor roster counts');

const sourceById = new Map();
for (const f of source.features) {
  const id = f.properties?.shapeID;
  assert(typeof id === 'string' && !sourceById.has(id), `Missing or duplicate original shapeID ${id}`);
  sourceById.set(id, f);
}
const atlasExtractById = new Map();
for (const f of atlasExtract.features) {
  const id = f.properties?.id;
  assert(typeof id === 'string' && !atlasExtractById.has(id), `Missing or duplicate Atlas ID ${id}`);
  atlasExtractById.set(id, f);
}
const assessmentById = new Map(native.map(row => [row.atlas_id, row]));
const lineageById = new Map(lineage.rows.map(row => [row.id, row]));
const followupById = new Map(followup.assessments.map(row => [row.subject_id, row]));
const selectedPriorIds = assessments.rows.filter(row => row.assessment !== 'justified').map(row => row.atlas_id).sort();
const followupIds = followup.assessments.map(row => row.subject_id).sort();
assert(JSON.stringify(selectedPriorIds) === JSON.stringify(followupIds),
  'The related follow-up roster does not match the prior non-justified selection rule');

const partBytes = new Map();
const rows = expectedIds.slice().sort().map(id => {
  const prior = assessmentById.get(id), link = lineageById.get(id);
  assert(prior && link && link.part, `Missing prior lineage for ${id}`);
  if (!partBytes.has(link.part)) partBytes.set(link.part, git(link.part));
  const part = json(partBytes.get(link.part), link.part);
  const atlasMatches = part.features.filter(f => f.properties?.id === id);
  assert(atlasMatches.length === 1, `Atlas part must contain exactly one ${id}`);
  const atlas = atlasMatches[0], sourceFeature = sourceById.get(prior.source_unit_id);
  assert(sourceFeature, `No source shapeID for ${id}`);
  const sourceJoinCount = source.features.filter(f => f.properties?.shapeID === prior.source_unit_id).length;
  assert(sourceJoinCount === 1, `Source join is not one-to-one for ${id}`);
  const pinnedAtlas = atlasExtractById.get(id);
  assert(pinnedAtlas && JSON.stringify(pinnedAtlas.geometry) === JSON.stringify(atlas.geometry),
    `Pinned Atlas extract geometry differs from the actual geography part for ${id}`);
  assert(atlas.properties?.metadata?.original_id === prior.source_unit_id,
    `Atlas original_id differs from assessment source ID for ${id}`);
  assert(atlas.properties?.name === prior.atlas_name && sourceFeature.properties?.shapeName === prior.source_unit_name,
    `Names differ from prior identity crosswalk for ${id}`);
  assert(atlas.properties?.name === sourceFeature.properties?.shapeName,
    `Original source and Atlas names differ for ${id}`);
  const srcGeom = geometrySummary(sourceFeature.geometry), atlasGeom = geometrySummary(atlas.geometry);
  assert(prior.geometry_type === atlasGeom.type && prior.component_count === atlasGeom.components,
    `Prior fields are not Atlas-derived geometry for ${id}`);
  const f = followupById.get(id);
  if (f) assert(f.source_geometry_type === prior.geometry_type && f.source_component_count === prior.component_count,
    `Follow-up mislabeled fields do not match the prior Atlas-derived values for ${id}`);
  return {
    subject_id: id,
    atlas_name: atlas.properties.name,
    prior_assessment: prior.assessment,
    original_source_shape_id: sourceFeature.properties.shapeID,
    original_source_name: sourceFeature.properties.shapeName,
    parent_id: prior.parent_id,
    parent_name: prior.province_name,
    original_source_geometry_type: srcGeom.type,
    original_source_component_count: srcGeom.components,
    atlas_geometry_type: atlasGeom.type,
    atlas_component_count: atlasGeom.components,
    prior_assessment_geometry_type: prior.geometry_type,
    prior_assessment_component_count: prior.component_count,
    followup_45_member_subject: Boolean(f),
    followup_prior_field_geometry_type: f?.source_geometry_type ?? null,
    followup_prior_field_component_count: f?.source_component_count ?? null,
    comparison: srcGeom.type === atlasGeom.type && srcGeom.components === atlasGeom.components ? 'match' : 'different',
  };
});

assert(rows.length === 199 && new Set(rows.map(r => r.subject_id)).size === 199, 'Output roster is not unique exact-199');
assert(rows.every(r => r.original_source_name === r.atlas_name), 'Source/Atlas names differ');
const mismatches = rows.filter(r => r.comparison === 'different');
const inFollowup = rows.filter(r => r.followup_45_member_subject);
const followupMismatch = inFollowup.filter(r => r.comparison === 'different');
const outsideMismatch = rows.filter(r => !r.followup_45_member_subject && r.comparison === 'different');
const followupNative = followup.assessments.filter(r => r.source_kind === 'native-adm2');
const followupNonNative = followup.assessments.filter(r => r.source_kind !== 'native-adm2');
assert(inFollowup.length === 34 && followupNative.length === 34 && followupNonNative.length === 11,
  'Follow-up must partition into 34 native subjects and 11 non-native fragments');
assert(mismatches.length === 8 && followupMismatch.length === 6 && outsideMismatch.length === 2,
  'Expected eight total differences: six in the 34 native follow-up rows and two outside its 45 rows');
assert(outsideMismatch.every(row => row.prior_assessment === 'justified') &&
  followupMismatch.every(row => row.prior_assessment !== 'justified'),
  'Two omitted mismatches must be in the prior justified category excluded by the follow-up selection');
assert(rows.filter(r => r.comparison === 'match').length === 191, 'Expected 191 source/Atlas matches');

const expectedDiffs = {
  'gb:RUS:ADM2:50074027B1024572337800': [3, 2],
  'gb:RUS:ADM2:50074027B10379539839705': [32, 12],
  'gb:RUS:ADM2:50074027B19808785107388': [3, 1],
  'gb:RUS:ADM2:50074027B30864735873510': [8, 6],
  'gb:RUS:ADM2:50074027B53792659884597': [5, 3],
  'gb:RUS:ADM2:50074027B56233113775442': [9, 6],
  'gb:RUS:ADM2:50074027B57421544908828': [107, 45],
  'gb:RUS:ADM2:50074027B58811812536316': [2, 1],
};
for (const row of mismatches) {
  assert(JSON.stringify([row.original_source_component_count, row.atlas_component_count]) ===
    JSON.stringify(expectedDiffs[row.subject_id]), `Unexpected component counts for ${row.subject_id}`);
}
assert(Object.keys(expectedDiffs).length === mismatches.length, 'Unexpected discrepancy roster');

// A concrete positive control and three adversarial negative controls exercise the result gate.
const positive = mismatches.find(row => row.subject_id === 'gb:RUS:ADM2:50074027B1024572337800');
assert(positive && positive.original_source_component_count === 3 && positive.atlas_component_count === 2,
  'Positive control did not detect the known source/Atlas difference');
const controls = [{method_id: 'source-atlas-component-crosswalk', kind: 'positive-control', outcome: 'passed',
  evidence: 'Known Beisk city-okrug native subject reproduces original source MultiPolygon:3 versus Atlas MultiPolygon:2.'}];
for (const [id, mutate, description] of [
  ['negative-missing-subject', list => list.slice(1), 'A one-subject-short roster is rejected.'],
  ['negative-duplicate-subject', list => [...list, list[0]], 'A duplicate-subject roster is rejected.'],
]) {
  let rejected = false;
  try { exactRoster(mutate(nativeIds), expectedIds); } catch { rejected = true; }
  assert(rejected, `${id} unexpectedly passed`);
  controls.push({method_id: 'source-atlas-component-crosswalk', kind: 'negative-control', outcome: 'passed', id, evidence: description});
}
const wrongCount = structuredClone(rows);
const matchingControl = wrongCount.find(r => r.comparison === 'match');
matchingControl.atlas_component_count += 1;
const alteredMismatchCount = wrongCount.filter(r => r.original_source_component_count !== r.atlas_component_count ||
  r.original_source_geometry_type !== r.atlas_geometry_type).length;
assert(alteredMismatchCount === 9 && alteredMismatchCount !== mismatches.length,
  'Wrong-count mutation was not detected');
controls.push({method_id: 'source-atlas-component-crosswalk', kind: 'negative-control', outcome: 'passed',
  id: 'negative-wrong-count', evidence: 'Increasing one Atlas count changes the discrepancy total from eight to nine and fails the expected result.'});

const inputs = [
  {role: 'original-source-extract', path: `${ROOT}/sources/geoboundaries-rus-adm2-2017-scoped-original-features.geojson`, bytes: read.source.length, sha256: sha(read.source)},
  {role: 'atlas-scoped-extract', path: `${ROOT}/sources/current-scoped-features.geojson`, bytes: read.atlasExtract.length, sha256: sha(read.atlasExtract)},
  {role: 'prior-assessments', path: `${ROOT}/findings/member-assessments.json`, bytes: read.assessments.length, sha256: sha(read.assessments)},
  {role: 'prior-lineage', path: `${ROOT}/findings/current-lineage.json`, bytes: read.lineage.length, sha256: sha(read.lineage)},
  {role: 'follow-up-assessments', path: `${FOLLOWUP}/findings/followup-assessments.json`, bytes: read.followup.length, sha256: sha(read.followup)},
  {role: 'geoBoundaries-source-metadata', path: `${ROOT}/sources/geoboundaries-rus-adm2-2017-metadata.json`, bytes: read.sourceMetadata.length, sha256: sha(read.sourceMetadata)},
  {role: 'geoBoundaries-upstream-commit-and-lfs-pointer', path: `${ROOT}/sources/geoboundaries-commit-9469f09.json`, bytes: read.sourceCommit.length, sha256: sha(read.sourceCommit)},
  {role: 'prior-exact-scope', path: `${ROOT}/baseline/issue-scope.json`, bytes: read.issue395Scope.length, sha256: sha(read.issue395Scope)},
  {role: 'prior-source-extraction-producer', path: `${ROOT}/extract-pinned-source.mjs`, bytes: read.producerExtract.length, sha256: sha(read.producerExtract)},
  {role: 'prior-atlas-lineage-producer', path: `${ROOT}/reproduce-current-lineage.mjs`, bytes: read.producerLineage.length, sha256: sha(read.producerLineage)},
  {role: 'prior-assessment-producer', path: `${ROOT}/assess-members.mjs`, bytes: read.producerAssess.length, sha256: sha(read.producerAssess)},
  {role: 'followup-producer', path: `${FOLLOWUP}/reproduce-followup.py`, bytes: read.producerFollowup.length, sha256: sha(read.producerFollowup)},
  {role: 'issue-contract-snapshot', path: ISSUE_SNAPSHOT, bytes: issueBytes.length, sha256: sha(issueBytes)},
  {role: 'geoBoundaries-original-source-lfs-pointer', path: `${OWNED}/sources/geoboundaries-rus-adm2-2017-lfs-pointer.txt`, bytes: originalPointerBytes.length, sha256: sha(originalPointerBytes)},
  ...[...partBytes.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([path, bytes]) =>
    ({role: 'atlas-geography-part', path, bytes: bytes.length, sha256: sha(bytes)})),
];
const output = {
  version: 1,
  issue: 1315,
  evaluation_commit: BASE,
  issue_scope: {subject_count: expectedIds.length, subject_ids_sha256: sha(Buffer.from(JSON.stringify([...expectedIds].sort()))),
    contract_review_kind: contract.evidence_quality.review_kind},
  source_definition: 'Polygon component count is 1; MultiPolygon component count is the number of top-level polygon coordinate arrays. It is a GeoJSON representation count, not a count of legally distinct municipalities, islands, or current land areas.',
  input_files: inputs,
  counts: {
    native_subjects: rows.length,
    source_atlas_matches: rows.length - mismatches.length,
    source_atlas_differences: mismatches.length,
    followup_45_total: followup.assessments.length,
    followup_native_subjects: inFollowup.length,
    followup_native_matches: inFollowup.length - followupMismatch.length,
    followup_native_differences: followupMismatch.length,
    followup_non_native_ecoregion_fragments_excluded: followupNonNative.length,
    differences_outside_followup_45: outsideMismatch.length,
  },
  discrepancy_ids: mismatches.map(r => r.subject_id),
  out_of_followup_discrepancy_ids: outsideMismatch.map(r => r.subject_id),
  controls,
  limitations: [
    'The original input is a 203-feature scoped extract preserved by prior work; the full 120,489,189-byte national geoBoundaries LFS object was not restored or retained. Its official LFS pointer and metadata are recorded in the predecessor packet.',
    'The original dataset metadata labels the boundary vintage 2017, ADM2, says source data updated 2023-03-03 and built 2023-12-12, and reports 2,328 administrative units; the historical full raw file actually contains 2,327 features. This packet does not resolve that metadata/feature-count discrepancy.',
    'The comparison verifies retained source and Atlas representations for the exact 199 issue subjects. It does not establish whether either representation is legally current, complete, authoritative, topologically valid, or complete for islands/disconnected land. A differing component count alone proves no omission or required geometry edit.',
    'Eleven ecological fragments in the related 45-row follow-up are not whole native administrative units and are excluded from source-versus-Atlas native-district comparison.',
  ],
  rows,
};
const header = {...output};
delete header.rows;
const prettyHeader = JSON.stringify(header, null, 2);
const bytes = Buffer.from(`${prettyHeader.slice(0, -2)},\n  "rows": [\n${rows.map(row => `    ${JSON.stringify(row)}`).join(',\n')}\n  ]\n}\n`);
mkdirSync(dirname(OUT), {recursive: true});
let fd;
try { fd = openSync(OUT, 'wx'); } catch (error) {
  throw new Error(`Exclusive output-preservation control: refusing to replace existing output ${OUT} (${error.code})`);
}
try { writeFileSync(fd, bytes); } finally { closeSync(fd); }
console.log(JSON.stringify({output: OUT, sha256: sha(bytes), bytes: bytes.length, counts: output.counts,
  controls: controls.length, inputs: inputs.length}));
