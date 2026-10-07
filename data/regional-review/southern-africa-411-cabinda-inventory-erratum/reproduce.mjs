import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';

const issue = 1284;
const method = 'cabinda-inventory-reproduction';
const baselineCommit = 'c9f2ce1f4fe6434a42a8fbe4886dcfcaa73169e8';
const historicalCommit = '762d7b5a568ca845d85a98a4d188678c126a5d58';
const packet = 'data/regional-review/regional-review-029dcbc646de003d';
const ids = [
  'gb:AGO:ADM2:16411231B22766430211667',
  'gb:AGO:ADM2:16411231B679187258105',
  'gb:AGO:ADM2:16411231B42954517222252',
  'gb:AGO:ADM2:16411231B63355352791940'
];
const expected = {
  readme1047: {commit: historicalCommit, path: `${packet}/README.md`, bytes: 8350, sha256: '44005dd5b85ecf2eed4e05d9b1d5c649e1dc4172f609a471f0f13308ac343155'},
  readme1057: {commit: baselineCommit, path: `${packet}/README.md`, bytes: 9697, sha256: '89cfade5ddbb9e5208772bee3ba8431d690a9461bdff0c3b6aa62e6ae54499e2'},
  scope: {commit: baselineCommit, path: `${packet}/scope.json`, bytes: 20734, sha256: '20b2cc1aae272ba862059a11779fa14d2569d1a0c3e5cf59ffa034ce764347ee'},
  atlasPart29: {commit: baselineCommit, path: 'data/geography/part-29.json', bytes: 12932167, sha256: '077e3bdfb18a42318e27bad840bba823a5049ced449407584fb4b9be2ef67c7a'},
  sourceReview: {commit: baselineCommit, path: `${packet}/source-review.json`, bytes: 22077, sha256: '87201ce5d44caee0adb742aa823fce5f7687e5ff9b05b65e587139a3c78d9356'},
  geoBoundaries2018: {commit: baselineCommit, path: `${packet}/sources/geoBoundaries-AGO-ADM2-2018.geojson`, bytes: 3146775, sha256: '44e58b2a8c2fefb9369294a32e2adde3e3637b9e02e8f1e2c53b400bec04f404'},
  geoBoundaries2018Metadata: {commit: baselineCommit, path: `${packet}/sources/geoBoundaries-metadata/geoBoundaries-AGO-ADM2-metaData.json`, bytes: 927, sha256: '0f45ab188f1e12b2f4068ecddeb62b2fb73d4ee7d1a71e29a8a8992d4b7ad302'}
};
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
function pinned(name) {
  const descriptor = expected[name];
  const bytes = execFileSync('git', ['show', `${descriptor.commit}:${descriptor.path}`], {maxBuffer: 32 * 1024 * 1024});
  if (bytes.length !== descriptor.bytes || sha256(bytes) !== descriptor.sha256) {
    throw new Error(`Pinned bytes mismatch for ${name}: ${bytes.length} bytes, ${sha256(bytes)}`);
  }
  return bytes;
}

const readme1047 = pinned('readme1047').toString('utf8');
const readme1057 = pinned('readme1057').toString('utf8');
const quotedClaim = 'They are absent from all pinned atlas partitions';
if (!readme1047.includes(quotedClaim) || !readme1057.includes(quotedClaim)) {
  throw new Error('The historical claim was not found in both pinned README vintages');
}
const sourceReview = JSON.parse(pinned('sourceReview').toString('utf8'));
const sourceReviewAGO = sourceReview.sources?.find(source => source.id === 'GB-AGO-2018');
const geoBoundaries = JSON.parse(pinned('geoBoundaries2018').toString('utf8'));
const sourceMetadata = JSON.parse(pinned('geoBoundaries2018Metadata').toString('utf8'));
if (geoBoundaries.type !== 'FeatureCollection' || !Array.isArray(geoBoundaries.features) || geoBoundaries.features.length !== 161 ||
  String(sourceMetadata.boundaryYear) !== '2018' || sourceMetadata.boundaryType !== 'ADM2' ||
  String(sourceMetadata.admUnitCount) !== '161' || sourceMetadata.boundaryLicense !== 'Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO)' ||
  !sourceReviewAGO || sourceReviewAGO.sha256 !== expected.geoBoundaries2018.sha256 ||
  sourceReviewAGO.metadata_sha256 !== expected.geoBoundaries2018Metadata.sha256 ||
  sourceReviewAGO.retrieved_at_utc !== '2026-10-06T00:15:21Z' || sourceReviewAGO.source_vintage !== '2018' ||
  sourceReviewAGO.geoBoundaries_reported_unit_count !== 161 || sourceReviewAGO.geoBoundaries_source_data_updated !== '2023-01-19' ||
  sourceReviewAGO.geoBoundaries_build !== '2023-12-12' ||
  sourceMetadata.sourceDataUpdateDate !== 'Thu Jan 19 07:31:04 2023' || sourceMetadata.buildDate !== 'Dec 12, 2023') {
  throw new Error('Pinned geoBoundaries 2018 source metadata, count, license or retrieval receipt mismatch');
}
const scopeFile = JSON.parse(pinned('scope').toString('utf8'));
const scope = scopeFile.scope;
const memberIds = scope?.member_location_ids;
if (!Array.isArray(memberIds) || memberIds.length !== 223 || new Set(memberIds).size !== 223) {
  throw new Error('Frozen #411 scope must contain exactly 223 unique member IDs');
}
const atlas = JSON.parse(pinned('atlasPart29').toString('utf8'));
if (atlas.type !== 'FeatureCollection' || !Array.isArray(atlas.features) || atlas.features.length !== 1500) {
  throw new Error('Pinned complete part 29 must be a 1,500-feature FeatureCollection');
}
const scopeSet = new Set(memberIds);
const sourceRows = ids.map(id => {
  const matches = geoBoundaries.features.filter(feature => {
    const p = feature.properties ?? {};
    return `gb:${p.shapeGroup}:${p.shapeType}:${p.shapeID}` === id;
  });
  if (matches.length !== 1) throw new Error(`Expected exactly one original geoBoundaries 2018 source match for ${id}, found ${matches.length}`);
  const properties = matches[0].properties ?? {};
  return {id, source_name: properties.shapeName, source_shape_group: properties.shapeGroup, source_shape_type: properties.shapeType, source_occurrences: matches.length};
});
const featureRows = ids.map(id => {
  const matches = atlas.features.filter(feature => (feature.properties?.id ?? feature.id) === id);
  if (matches.length !== 1) throw new Error(`Expected exactly one Atlas match for ${id}, found ${matches.length}`);
  const properties = matches[0].properties ?? {};
  const original = sourceRows.find(row => row.id === id);
  return {id, name: properties.name, source_name: original.source_name, source_name_matches_atlas: properties.name === original.source_name,
    source_occurrences: original.source_occurrences, parent_id: properties.parent_id, atlas_occurrences: matches.length, in_frozen_scope: scopeSet.has(id)};
});
const fabricatedId = 'gb:AGO:ADM2:NOT_A_REAL_CABINDA_FEATURE_1284';
const fabricatedAtlasMatches = atlas.features.filter(feature => (feature.properties?.id ?? feature.id) === fabricatedId).length;
const fabricatedScopeMatches = memberIds.filter(id => id === fabricatedId).length;
const allFourInScope = ids.every(id => scopeSet.has(id));
if (fabricatedAtlasMatches !== 0 || fabricatedScopeMatches !== 0 || allFourInScope) {
  throw new Error('A negative control unexpectedly passed the incorrect assertion');
}
if (featureRows.some(row => row.in_frozen_scope || row.parent_id !== 'framework:province:cabinda:fb67d098df5d' || !row.source_name_matches_atlas)) {
  throw new Error('Unexpected scope inclusion or stored parent');
}

const report = {
  version: 1,
  issue,
  method_id: method,
  baseline_commit: baselineCommit,
  historical_readme_commit: historicalCommit,
  verified_inputs: Object.fromEntries(Object.entries(expected).map(([key, value]) => [key, {...value}])),
  historical_claim_present_in_both_readmes: true,
  original_source: {
    name: 'geoBoundaries gbHumanitarian AGO ADM2',
    upstream_commit: '9469f09592ced973a3448cf66b6100b741b64c0d',
    source_vintage: '2018',
    source_data_updated: '2023-01-19',
    source_build: '2023-12-12',
    source_retrieved_at_utc: sourceReviewAGO.retrieved_at_utc,
    source_feature_count: geoBoundaries.features.length,
    source_level: sourceMetadata.boundaryType,
    source_lineage: sourceReviewAGO.geoBoundaries_source_lineage,
    source_reported_upstream_url: sourceReviewAGO.geoBoundaries_reported_source_url,
    source_reported_upstream_url_malformed: !/^https:\/\//.test(sourceReviewAGO.geoBoundaries_reported_source_url ?? ''),
    metadata_license: sourceMetadata.boundaryLicense,
    metadata_lineage: sourceMetadata.boundarySource,
    metadata_reported_upstream_url: sourceMetadata.boundarySourceURL,
    source_data_updated: sourceReviewAGO.geoBoundaries_source_data_updated,
    source_build: sourceReviewAGO.geoBoundaries_build,
    source_feature_matches: sourceRows.length,
    source_name_matches_atlas_count: featureRows.filter(row => row.source_name_matches_atlas).length,
    limitation: '2018 humanitarian ADM2 source identity/name match only; no current legal boundary, completeness, geometry accuracy or neighboring-granularity conclusion.'
  },
  atlas_partition_feature_count: atlas.features.length,
  frozen_scope_member_count: memberIds.length,
  subject_count: ids.length,
  subject_source_occurrence_count: sourceRows.reduce((sum, row) => sum + row.source_occurrences, 0),
  subject_source_name_match_count: featureRows.filter(row => row.source_name_matches_atlas).length,
  subject_atlas_occurrence_count: featureRows.reduce((sum, row) => sum + row.atlas_occurrences, 0),
  subject_frozen_scope_occurrence_count: featureRows.filter(row => row.in_frozen_scope).length,
  subject_outside_frozen_scope_count: featureRows.filter(row => !row.in_frozen_scope).length,
  subjects: featureRows,
  positive_control_passed: featureRows.length === 4 && featureRows.every(row => row.atlas_occurrences === 1 && row.source_occurrences === 1 && row.source_name_matches_atlas),
  negative_controls_passed: fabricatedAtlasMatches === 0 && fabricatedScopeMatches === 0 && !allFourInScope,
  negative_control: {fabricated_id: fabricatedId, atlas_matches: fabricatedAtlasMatches, frozen_scope_matches: fabricatedScopeMatches, incorrect_all_four_in_scope_assertion: allFourInScope},
  result: 'All four exact IDs are present once in the retained Atlas partition and absent from the frozen 223-member #411 workload.',
  limitations: [
    'This verifies retained Atlas identity/name/parent bytes and workload membership only.',
    'It does not establish territorial meaning, current municipality identity, boundary geometry or accuracy, source authority/completeness, source reuse rights, or neighboring granularity.',
    'The historical 2018 source and current-ten-municipality question remain outside this inventory erratum.'
  ]
};

const control = (kind, detail) => ({method_id: method, kind, outcome: 'passed', ...detail});
const option = process.argv[2];
if (option === '--positive-control') {
  console.log(JSON.stringify(control('positive-control', {four_exact_ids_found_once: report.positive_control_passed, subject_rows: featureRows}), null, 2));
} else if (option === '--negative-control') {
  console.log(JSON.stringify(control('negative-control', {fabricated_id_rejected: fabricatedAtlasMatches === 0 && fabricatedScopeMatches === 0, false_workload_inclusion_assertion_rejected: !allFourInScope, evidence: report.negative_control}), null, 2));
} else if (!option) {
  console.log(JSON.stringify(report, null, 2));
} else {
  throw new Error('Use no argument, --positive-control, or --negative-control');
}
