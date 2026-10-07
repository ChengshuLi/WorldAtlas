import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const packet = 'data/regional-review/southern-africa-411-crosswalk-validation-1047-erratum';
const original = 'data/regional-review/regional-review-029dcbc646de003d';
const manifestPath = `${packet}/evidence-quality.json`;
const baselineCommit = '762d7b5a568ca845d85a98a4d188678c126a5d58';
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const readJSON = filename => JSON.parse(fs.readFileSync(path.join(root, filename), 'utf8'));
const gitBytes = name => execFileSync('git', ['show', `${baselineCommit}:${name}`], {maxBuffer: 32 * 1024 * 1024});
const issueSnapshot = readJSON(`${packet}/issue-scope-snapshot.json`);
const blocks = [...issueSnapshot.body.matchAll(/<!-- worldatlas-work:v1\s*\n([\s\S]*?)\n-->/g)];
if (blocks.length !== 1) throw new Error('Current issue snapshot must contain one work contract');
const contract = JSON.parse(blocks[0][1]);
if (issueSnapshot.number !== 1279 || issueSnapshot.state !== 'OPEN' || contract.mode !== 'geography' ||
    contract.owned_paths?.length !== 1 || contract.owned_paths[0] !== `${packet}/`) {
  throw new Error('Issue snapshot no longer matches the claimed packet scope');
}
const quality = contract.evidence_quality;
if (quality?.version !== 1 || quality.review_kind !== 'source' || quality.subject_ids.length !== 223) {
  throw new Error('Issue evidence declaration differs from this packet');
}
const reproduction = JSON.parse(gitBytes(`${original}/scope-reproduction.json`).toString('utf8'));
const issue411 = JSON.parse(gitBytes(`${original}/scope.json`).toString('utf8'));
const sourceReview = JSON.parse(gitBytes(`${original}/source-review.json`).toString('utf8'));
const runOne = `${packet}/runs/2026-10-07/run-1`;
const runTwo = `${packet}/runs/2026-10-07/run-2`;
const validated = readJSON(`${runOne}/validation.json`);
const subjectSet = values => JSON.stringify([...values].sort());
const subjectIdsSha256 = sha(Buffer.from(subjectSet(quality.subject_ids)));
if (subjectSet(quality.subject_ids) !== subjectSet(issue411.scope.member_location_ids) ||
    subjectSet(quality.subject_ids) !== subjectSet(reproduction.rows.map(row => row.id))) {
  throw new Error('Issue, original and reproduced subject rosters differ');
}

const pinnedNames = {
  ...Object.fromEntries(Object.keys(quality.pins).map(key => [key, `${original}/${key.slice('original:'.length)}`])),
  ...Object.fromEntries(reproduction.baseline_files.map(file => [`baseline:${file.path}`, file.path])),
  ...Object.fromEntries(sourceReview.sources.filter(source => source.artifact_path)
    .map(source => [`source:${source.id}`, `${original}/${source.artifact_path}`]))
};
const baselineFiles = [];
const pins = {};
const pinFiles = {};
for (const [key, filename] of Object.entries(pinnedNames)) {
  const bytes = gitBytes(filename);
  const descriptor = {path: filename, bytes: bytes.length, sha256: sha(bytes), hash_kind: 'file-bytes', role: 'original-source'};
  const expected = quality.pins[key] ?? (key.startsWith('baseline:')
    ? reproduction.baseline_files.find(file => file.path === filename)?.sha256
    : sourceReview.sources.find(source => `source:${source.id}` === key)?.sha256);
  if (expected && descriptor.sha256 !== expected) throw new Error(`Issue/source pin mismatch at #1047 merge: ${key}`);
  baselineFiles.push(descriptor);
  pins[key] = descriptor.sha256;
  pinFiles[key] = filename;
}
if (baselineFiles.length > 512) throw new Error('Baseline descriptor count exceeds policy');

const subjectFiles = Object.fromEntries(reproduction.rows.map(row => [row.id, row.atlas_part]));
if (Object.keys(subjectFiles).length !== quality.subject_ids.length) throw new Error('Incomplete containing-file map');
for (const id of quality.subject_ids) if (!subjectFiles[id]) throw new Error(`No baseline containing file for ${id}`);
const outputFiles = [];
function collect(directory) {
  for (const entry of fs.readdirSync(path.join(root, directory), {withFileTypes: true}).sort((a, b) => a.name.localeCompare(b.name))) {
    const filename = `${directory}/${entry.name}`;
    const absolute = path.join(root, filename);
    const stat = fs.lstatSync(absolute);
    if (stat.isSymbolicLink()) throw new Error(`Packet output cannot be a symlink: ${filename}`);
    if (entry.isDirectory()) collect(filename);
    else if (entry.isFile() && filename !== manifestPath) {
      const bytes = fs.readFileSync(absolute);
      outputFiles.push({path: filename, bytes: bytes.length, sha256: sha(bytes), hash_kind: 'file-bytes'});
    } else if (!entry.isFile()) throw new Error(`Unsupported packet output type: ${filename}`);
  }
}
collect(packet);
if (!outputFiles.length || outputFiles.some(file => !file.path.startsWith(`${packet}/`))) throw new Error('Packet output inventory is empty or out of scope');
const outputByPath = new Map(outputFiles.map(file => [file.path, file]));
const sourceRecords = sourceReview.sources.filter(source => /\.geojson$/i.test(source.artifact_path ?? '')).map(source => {
  const filename = `${original}/${source.artifact_path}`;
  const descriptor = baselineFiles.find(file => file.path === filename);
  if (!descriptor || descriptor.sha256 !== source.sha256) throw new Error(`Retained source inventory mismatch: ${source.id}`);
  return {
    id: source.id,
    url: source.url,
    role: 'Historical administrative level-2 native feature and boundary reference collection; not a current-boundary authority',
    vintage: source.source_vintage,
    retrieved_at: source.retrieved_at_utc,
    license: {status: 'redistributable', terms: source.license},
    retention: 'retained',
    verification: 'verified',
    files: [{path: filename, bytes: descriptor.bytes, sha256: descriptor.sha256, hash_kind: 'file-bytes'}],
    temporal_status: 'reference',
    description: `${source.title}. The retained packet's source-review entry records its complete source hash and explicit factual limits.`
  };
});
sourceRecords.push({
  id: 'issue-411-frozen-scope',
  url: issue411.url,
  role: 'Frozen work-scope roster for the exact #411 review subjects; identity scope only',
  vintage: `issue snapshot created ${issue411.issue_created_at}`,
  retrieved_at: issueSnapshot.retrieved_at_utc,
  license: {status: 'unknown', terms: 'No geographic-data reuse license is inferred from a GitHub issue; the exact scope snapshot is retained as work-contract evidence.'},
  retention: 'restoration-only',
  verification: 'verified',
  restoration: `Restore the frozen scope from ${issue411.url} and verify it against the retained ${original}/scope.json snapshot and issue-body SHA-256.`,
  limit: 'The issue defines exact research subjects; it does not establish current territorial meaning, legal boundaries, completeness or source reuse rights.',
  temporal_status: 'unknown'
});

const metricPath = `${runOne}/validation.json`;
const baselineDigest = filename => baselineFiles.find(file => file.path === filename)?.sha256;
const metricDefinitions = [
  ['frozen-subjects', validated.frozen_subject_count, 'subjects', `${original}/scope.json`, '/frozen_subject_count'],
  ['crosswalk-rows', validated.crosswalk.rows, 'rows', `${original}/scope-reproduction.json`, '/crosswalk/rows'],
  ['unique-crosswalk-identities', validated.crosswalk.unique_ids, 'identities', `${original}/scope-reproduction.json`, '/crosswalk/unique_ids'],
  ['assessment-rows', validated.assessments.rows, 'rows', `${original}/row-assessments.json`, '/assessments/rows'],
  ['justified-dispositions', validated.assessment_classifications.justified, 'rows', `${original}/row-assessments.json`, '/assessment_classifications/justified'],
  ['correction-needed-dispositions', validated.assessment_classifications['correction-needed'], 'rows', `${original}/row-assessments.json`, '/assessment_classifications/correction-needed'],
  ['insufficient-evidence-dispositions', validated.assessment_classifications['insufficient-evidence'], 'rows', `${original}/row-assessments.json`, '/assessment_classifications/insufficient-evidence']
];
const metrics = metricDefinitions.map(([id, value, unit, input, pointer]) => ({id, value, unit, vintage: 'baseline',
  input_sha256: baselineDigest(input), evaluation_commit: baselineCommit}));
const metricBindings = metricDefinitions.map(([id, , , , json_pointer]) => ({metric_id: id, path: metricPath, json_pointer}));
const summaries = metricDefinitions.map(([metric_id, value, unit]) => ({metric_id, value, unit}));
const manifest = {
  version: 1,
  issue: 1279,
  lane: 'geography',
  worker_id: '01a10947-b3d7-7812-8b2f-c5a47e88ccb2',
  subject_ids: quality.subject_ids,
  subject_ids_sha256: subjectIdsSha256,
  baseline: {commit: baselineCommit, files: baselineFiles, pins, pin_files: pinFiles, subject_files: subjectFiles},
  sources: sourceRecords,
  outputs: outputFiles,
  methods: [
    {id: 'southern-africa-frozen-crosswalk-integrity', kind: 'generator', helper_version: 'worldatlas-evidence-preparation-v1',
      description: 'Two complete reproductions of the immutable #411 source-to-Atlas identity crosswalk and per-subject assessment pipeline, followed by byte, subject, source-feature and parent correlation validation. Original source and result bytes are preserved.',
      software: 'Node.js 24.19.0; Git; original retained issue #411 producer and assessment scripts; issue-owned verify-crosswalk.mjs',
      units: 'exact subject IDs, native source features, assessment rows, parent IDs and complete-file SHA-256 bytes'},
    {id: 'retained-source-identity', kind: 'source',
      description: 'Verify each in-scope native ID against exact retained geoBoundaries feature properties and the pinned Atlas feature and hierarchy. This confirms the saved crosswalk only; it does not adjudicate current geography.',
      software: 'Node.js 24.19.0; immutable Git baseline; retained GeoJSON and hierarchy JSON',
      units: 'native feature identities, names, source role/vintage fields and parent IDs'},
    {id: 'source-limit-review', kind: 'source',
      description: 'Preserve source vintages, attribution and the explicit unresolved official-source, legal, completeness and geometry findings from the original #411 source review; no new source claim is made.',
      software: 'Issue #411 source-review.json and retained source metadata',
      units: 'source URLs, whole-file hashes, retrieval dates, reuse terms and stated limits'}
  ],
  metrics,
  summaries,
  metric_bindings: metricBindings,
  validation: [
    {method_id: 'southern-africa-frozen-crosswalk-integrity', kind: 'positive-control', outcome: 'passed', evidence_path: `${packet}/validation/positive-control.json`},
    {method_id: 'southern-africa-frozen-crosswalk-integrity', kind: 'negative-control', outcome: 'passed', evidence_path: `${packet}/validation/negative-control.json`},
    {method_id: 'southern-africa-frozen-crosswalk-integrity', kind: 'reproducibility', outcome: 'passed', evidence_path: `${packet}/validation/reproducibility.json`}
  ],
  conclusions: [
    {text: 'The complete frozen roster contains 223 subjects. Two independent crosswalk and assessment executions reproduce the original whole-file outputs, and the superseding validator derives exact row membership and one-to-one source and parent correlations from actual retained bytes.',
      status: 'supported', source_ids: ['issue-411-frozen-scope', 'GB-AGO-2018', 'GB-MOZ-2019', 'GB-MWI-2020']},
    {text: 'The original packet retains 0 justified, 1 correction-needed and 222 insufficient-evidence dispositions. This erratum preserves those limits; current legal assignments, boundaries, completeness, neighboring granularity and regional approval remain unresolved or out of scope.',
      status: 'unresolved', source_ids: ['issue-411-frozen-scope', 'GB-AGO-2018', 'GB-MOZ-2019', 'GB-MWI-2020']}
  ],
  stages: {research: 'complete', implementation: 'proposed', geographic_approval: 'not-requested'},
  commands: [
    'Run the exact commands listed in RESEARCH.md after scripts/local-workspace.mjs check succeeds.',
    `node scripts/evidence-quality.mjs ${manifestPath}`,
    'node scripts/check-handoff-scope.mjs --branch geography/southern-africa-crosswalk-validator-1279-20261007-r2 --base origin/main --issue-file /path/to/current-issue-1279.json'
  ],
  change_receipts: [
    ...outputFiles.map(file => ({path: file.path, status: 'added'})),
    {path: manifestPath, status: 'added'}
  ]
};
if (metrics.some(metric => !metric.input_sha256) || !outputByPath.has(metricPath)) throw new Error('Metric input/output binding is incomplete');
fs.writeFileSync(path.join(root, manifestPath), `${JSON.stringify(manifest, null, 2)}\n`, {flag: 'wx'});
console.log(JSON.stringify({issue: manifest.issue, subjects: manifest.subject_ids.length, baseline_files: baselineFiles.length,
  outputs: outputFiles.length, sources: sourceRecords.length, metrics: metrics.length, baseline_commit: baselineCommit}, null, 2));
