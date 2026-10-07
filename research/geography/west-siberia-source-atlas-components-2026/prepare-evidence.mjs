import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {readFileSync, writeFileSync} from 'node:fs';

const BASE = '42937b066c28eab0c5a53f94c0f5aee7b3d5aae3';
const OWNED = 'research/geography/west-siberia-source-atlas-components-2026';
const PRIOR = 'data/regional-review/regional-review-626fdf640aab94e2';
const FOLLOWUP = 'data/regional-review/west-siberia-roles-followup-20261006';
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const read = path => readFileSync(`${OWNED}/${path}`);
const git = path => execFileSync('git', ['show', `${BASE}:${path}`], {maxBuffer: 32 * 1024 * 1024});
const writeNew = (path, value) => writeFileSync(`${OWNED}/${path}`, JSON.stringify(value, null, 2) + '\n', {flag: 'wx'});

const run = JSON.parse(read('findings/run-one.json').toString('utf8'));
const runTwo = read('findings/run-two.json');
if (sha(runTwo) !== sha(read('findings/run-one.json')) || run.counts.source_atlas_differences !== 8) {
  throw new Error('Final dual-run reproduction is not identical or has unexpected counts');
}
const issue = JSON.parse(read('sources/issue-1315-api.json').toString('utf8'));
const match = issue.body.match(/<!-- worldatlas-work:v1\s*(\{[\s\S]*?\})\s*-->/);
if (!match || issue.number !== 1315 || issue.state !== 'open') throw new Error('Missing issue 1315 scope snapshot');
const contract = JSON.parse(match[1]);
const subjects = contract.evidence_quality.subject_ids.slice().sort();
const pinMap = {
  prior_scoped_source_features: `${PRIOR}/sources/geoboundaries-rus-adm2-2017-scoped-original-features.geojson`,
  prior_atlas_features: `${PRIOR}/sources/current-scoped-features.geojson`,
  prior_assessments: `${PRIOR}/findings/member-assessments.json`,
  prior_lineage: `${PRIOR}/findings/current-lineage.json`,
};
const expectedPins = {
  prior_scoped_source_features: '7eb4cba61f0d17bfacb634c08aff3ec4873ece62734d518b51614bf061a5a129',
  prior_atlas_features: '44aa8bed8c6d3f6b7f4c553007efbaa82d39ff384790e95c06d1e3615ad4f070',
  prior_assessments: '55e20fc63247dd81a3d23dac405811c34e7dee79dc7b7a72712febbe813d913f',
  prior_lineage: '0781ff358d8e1e574eaecf1deea1b7fb1931a890105b17468ffecbe20d6f4874',
};
if (subjects.length !== 199 || new Set(subjects).size !== 199 ||
    sha(Buffer.from(JSON.stringify(subjects))) !== run.issue_scope.subject_ids_sha256) {
  throw new Error('Captured issue subject roster differs from final reproduction');
}

const positive = {
  method_id: 'source-atlas-component-crosswalk', kind: 'positive-control', outcome: 'passed',
  evidence: 'A known positive detects the original-source MultiPolygon:3 versus Atlas MultiPolygon:2 discrepancy for gb:RUS:ADM2:50074027B1024572337800.',
};
const negative = {
  method_id: 'source-atlas-component-crosswalk', kind: 'negative-control', outcome: 'passed',
  cases: [
    'Removing one subject was rejected by the exact-199 roster and contract digest check.',
    'Duplicating one subject was rejected by the unique-ID check.',
    'Increasing a matching Atlas count by one changes the discrepancy count from eight to nine and fails the expected result check.',
    'Re-running against the existing run-one output path exited with EEXIST; post-attempt SHA-256 remained 4e6b16e4c66715536376ebab4a8a50e971797b39b5ca45a63cdbdbf1823b9bd8.',
  ],
};
const reproducibility = {
  method_id: 'source-atlas-component-crosswalk', kind: 'reproducibility', outcome: 'passed',
  run_one_sha256: sha(read('findings/run-one.json')), run_two_sha256: sha(runTwo),
  equal_bytes: read('findings/run-one.json').equals(runTwo), output_bytes: read('findings/run-one.json').length,
};
writeNew('findings/positive-control.json', positive);
writeNew('findings/negative-control.json', negative);
writeNew('findings/reproducibility.json', reproducibility);

const candidatePaths = [
  'README.md', 'reproduce-components.mjs', 'prepare-evidence.mjs',
  'sources/issue-1315-api.json', 'sources/geoboundaries-rus-adm2-2017-lfs-pointer.txt',
  'findings/run-one.json', 'findings/run-two.json',
  'findings/positive-control.json', 'findings/negative-control.json', 'findings/reproducibility.json',
];
const outputs = candidatePaths.map(path => {
  const bytes = read(path);
  return {path: `${OWNED}/${path}`, bytes: bytes.length, sha256: sha(bytes), hash_kind: 'file-bytes'};
});
const evidenceRunFiles = run.input_files.filter(file => file.path.startsWith('data/'));
const baselinePaths = [...new Set([...evidenceRunFiles.map(file => file.path), `${PRIOR}/README.md`])].sort();
const baselineFiles = baselinePaths.map(path => {
  const bytes = git(path);
  return {path, bytes: bytes.length, sha256: sha(bytes), hash_kind: 'file-bytes'};
});
for (const [name, path] of Object.entries(pinMap)) {
  const file = baselineFiles.find(item => item.path === path);
  if (!file || file.sha256 !== expectedPins[name]) throw new Error(`Pinned baseline mismatch: ${name}`);
}
const partFiles = run.input_files.filter(file => file.role === 'atlas-geography-part');
const partData = new Map(partFiles.map(file => [file.path, JSON.parse(git(file.path).toString('utf8'))]));
const subjectFiles = Object.fromEntries(run.rows.map(row => [row.subject_id,
  partFiles.find(file => partData.get(file.path).features.some(feature => feature.properties?.id === row.subject_id))?.path]));
if (Object.values(subjectFiles).some(path => !path)) throw new Error('Could not bind all exact subjects to geography part files');

const resultFile = outputs.find(file => file.path.endsWith('/findings/run-one.json'));
const metrics = [
  ['native_subjects', 'exact native Atlas/source subjects', 'native_subjects'],
  ['source_atlas_matches', 'matching source/Atlas geometry-type and component-count pairs', 'source_atlas_matches'],
  ['source_atlas_differences', 'different source/Atlas geometry-type or component-count pairs', 'source_atlas_differences'],
  ['followup_native_subjects', 'native subjects among related 45-row follow-up', 'followup_native_subjects'],
  ['followup_native_matches', 'matching native source/Atlas pairs among related follow-up', 'followup_native_matches'],
  ['followup_native_differences', 'different native source/Atlas pairs among related follow-up', 'followup_native_differences'],
  ['followup_non_native_ecoregion_fragments_excluded', 'non-native ecoregion fragments excluded from native comparison', 'followup_non_native_ecoregion_fragments_excluded'],
  ['differences_outside_followup_45', 'differences outside related 45-row follow-up', 'differences_outside_followup_45'],
].map(([id, description, key]) => ({id, description, value: run.counts[key], unit: 'subjects', vintage: 'baseline',
  input_sha256: resultFile.sha256, evaluation_commit: BASE}));
const summaries = metrics.map(metric => ({metric_id: metric.id, value: metric.value, unit: metric.unit}));
const metricBindings = metrics.map(metric => ({metric_id: metric.id,
  path: resultFile.path, json_pointer: `/counts/${metric.id}`}));
const sources = [
  {
    id: 'geoboundaries-rus-adm2-2017',
    url: 'https://github.com/wmgeolab/geoBoundaries/tree/9469f09592ced973a3448cf66b6100b741b64c0d',
    role: 'Original-source reference for the RUS ADM2 shapes joined to the exact 199 native subjects',
    vintage: 'Boundary year 2017; source data update 2023-03-03; build date 2023-12-12',
    retrieved_at: '2026-10-05',
    license: {status: 'redistributable', terms: 'Source metadata states Open Data Commons Open Database License 1.0 and OpenStreetMap/Wambacher attribution; preserve required attribution.'},
    retention: 'restoration-only', verification: 'verified', temporal_status: 'reference',
    restoration: 'Fetch https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/RUS/ADM2/geoBoundaries-RUS-ADM2.geojson and verify SHA-256 74012237384e53061aa63b6e20b9be24f94facfe615b52bbe72e62a81fa68ff0 and 120489189 bytes. The exact Git LFS pointer is retained at research/geography/west-siberia-source-atlas-components-2026/sources/geoboundaries-rus-adm2-2017-lfs-pointer.txt.',
    limit: 'The full national object is not retained here; only the exact 203-feature prior scoped extract is pinned. Prior research records 2327 raw features while metadata declares 2328; this campaign does not restore the full archive to repeat that count. A 2017 reference dataset does not establish current law, authoritative boundaries, national completeness, or island completeness.',
  },
  {
    id: 'atlas-geography-at-base',
    url: `https://github.com/ChengshuLi/WorldAtlas/tree/${BASE}/data/geography`,
    role: 'Atlas representation used to compare each exact native subject at the immutable evaluation commit',
    vintage: `WorldAtlas geography at commit ${BASE}`,
    retrieved_at: '2026-10-06',
    license: {status: 'unknown', terms: 'Repository source reuse terms were not independently reviewed as part of this source-count erratum.'},
    retention: 'restoration-only', verification: 'verified', temporal_status: 'reference',
    restoration: `Read the issue subjects from the captured work contract, then fetch each recorded Atlas part from commit ${BASE} using git show; the exact two containing parts and their SHA-256 values are listed in findings/run-one.json.`,
    limit: 'This is Atlas representation at a fixed repository commit, not an independent or legally current territorial authority.',
  },
  {
    id: 'predecessor-source-crosswalk-and-followup',
    url: `https://github.com/ChengshuLi/WorldAtlas/tree/${BASE}/data/regional-review`,
    role: 'Pinned predecessor source extract, assessment/lineage, and #1092 follow-up used to reproduce the count-provenance defect and selection handoff',
    vintage: 'Earlier #1089 and #1098 research results preserved on the immutable baseline',
    retrieved_at: '2026-10-06',
    license: {status: 'unknown', terms: 'These are prior research artifacts; no separate license determination is asserted for the predecessor evidence.'},
    retention: 'restoration-only', verification: 'verified', temporal_status: 'reference',
    restoration: `Use git show at ${BASE} for every path and whole-file digest recorded in findings/run-one.json and the evidence manifest.`,
    limit: 'Prior assessment labels and current/legal boundary interpretation remain subject to their original documented limits; this packet does not overwrite or certify those conclusions.',
  },
  {
    id: 'github-issue-1315-contract',
    url: 'https://api.github.com/repos/ChengshuLi/WorldAtlas/issues/1315',
    role: 'Exact issue acceptance and subject roster snapshot for this 199-subject research scope',
    vintage: 'Issue API snapshot retrieved 2026-10-06 America/Los_Angeles',
    retrieved_at: '2026-10-06',
    license: {status: 'unknown', terms: 'GitHub issue content terms were not separately assessed; a restorable API snapshot is retained solely to bind the scope reviewed.'},
    retention: 'restoration-only', verification: 'verified', temporal_status: 'reference',
    restoration: 'Retrieve https://api.github.com/repos/ChengshuLi/WorldAtlas/issues/1315 and compare state, worldatlas-work:v1 contract, exact subject IDs, and body with the retained API response at research/geography/west-siberia-source-atlas-components-2026/sources/issue-1315-api.json.',
    limit: 'Issue content may change; the retained API response is a dated scope snapshot, not a source for territorial facts.',
  },
];

const manifest = {
  version: 1, issue: 1315, lane: 'geography', worker_id: '01a10948-7d38-75d0-bc01-4cc28ea41f49',
  subject_ids: subjects,
  subject_ids_sha256: run.issue_scope.subject_ids_sha256,
  baseline: {
    commit: BASE,
    files: baselineFiles,
    pins: expectedPins,
    pin_files: pinMap,
    subject_files: subjectFiles,
  },
  sources, outputs, methods: [{
    id: 'source-atlas-component-crosswalk', kind: 'source',
    description: 'Validate the exact issue roster; join each Atlas subject through the pinned predecessor source_unit_id to a unique 2017 source shapeID; inspect the retained original-source Polygon/MultiPolygon geometry and actual Atlas feature geometry from its recorded geography part; report type and top-level component count separately; compare old assessments and the related follow-up roster without modifying geometry.',
    software: `Node.js ${process.version}; Git at immutable commit ${BASE}`,
    units: 'One source or Atlas feature; Polygon counts as one component; MultiPolygon count is top-level polygon coordinate arrays. No CRS transformation, area, or distance calculations.',
  }],
  metrics, summaries,
  conclusions: [
    {text: 'For all 199 exact native issue subjects, unique source shapeID lineage and names match; 191 source/Atlas geometry type and component-count pairs match and eight differ. These are representation-vintage comparisons only.', status: 'supported', source_ids: ['geoboundaries-rus-adm2-2017', 'atlas-geography-at-base', 'predecessor-source-crosswalk-and-followup']},
    {text: 'The 2017-source component count does not represent legally separate units, prove current completeness, or authorize restoration. Which differing source or Atlas pieces are legally required remains unresolved.', status: 'unresolved', source_ids: ['geoboundaries-rus-adm2-2017', 'atlas-geography-at-base']},
    {text: 'The related #1092 follow-up contains 34 native subjects and 11 non-native ecoregion fragments. Its 34 native subjects have six source/Atlas mismatches and 28 matches; two more native mismatches outside that handoff were previously marked justified and therefore excluded by its non-justified selection rule. These are candidates for the #1092 owner to consider within its existing scope, not legal-completeness findings.', status: 'supported', source_ids: ['predecessor-source-crosswalk-and-followup', 'atlas-geography-at-base']},
    {text: 'The full national 120,489,189-byte source object was not restored in this campaign; current statutory or official polygons were not retrieved for all subjects. National source completeness and current legal/island component completeness remain unresolved.', status: 'unresolved', source_ids: ['geoboundaries-rus-adm2-2017', 'atlas-geography-at-base']},
  ],
  stages: {research: 'complete', implementation: 'not-proposed', geographic_approval: 'unapproved'},
  commands: [
    `node ${OWNED}/reproduce-components.mjs ${OWNED}/findings/run-one.json`,
    `node ${OWNED}/reproduce-components.mjs ${OWNED}/findings/run-two.json`,
    `node scripts/evidence-quality.mjs ${OWNED}/evidence-quality.json`,
    'node --test test/evidence-quality.test.mjs',
    'git diff --check',
  ],
  validation: [
    {method_id: 'source-atlas-component-crosswalk', kind: 'positive-control', outcome: 'passed', evidence_path: `${OWNED}/findings/positive-control.json`},
    {method_id: 'source-atlas-component-crosswalk', kind: 'negative-control', outcome: 'passed', evidence_path: `${OWNED}/findings/negative-control.json`},
    {method_id: 'source-atlas-component-crosswalk', kind: 'reproducibility', outcome: 'passed', evidence_path: `${OWNED}/findings/reproducibility.json`},
  ],
  metric_bindings: metricBindings,
  change_receipts: [
    ...candidatePaths.map(path => ({path: `${OWNED}/${path}`, status: 'added'})),
    {path: `${OWNED}/evidence-quality.json`, status: 'added'},
  ],
};
writeNew('evidence-quality.json', manifest);
console.log(JSON.stringify({manifest_sha256: sha(read('evidence-quality.json')), baseline_files: baselineFiles.length,
  output_files: outputs.length, subjects: subjects.length, metrics: metrics.length,
  subject_ids_sha256: manifest.subject_ids_sha256}, null, 2));
