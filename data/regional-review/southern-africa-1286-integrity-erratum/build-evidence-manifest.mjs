import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const packet = 'data/regional-review/southern-africa-1286-integrity-erratum';
const issueContractPath = `${packet}/github-issue-contract.json`;
const templatePath = 'data/regional-review/southern-africa-411-crosswalk-validation-1047-erratum/evidence-quality.json';
const manifestPath = `${packet}/evidence-quality.json`;
const baselineHead = '088ab05aeb16ddfa8f0c43e596533f3f11d5fcec';
const originalCommit = '762d7b5a568ca845d85a98a4d188678c126a5d58';
const predecessorCommit = '9be99dfefb5871237ac464c6ef8a23e82be501f6';
const originalPacket = 'data/regional-review/regional-review-029dcbc646de003d';
const oldErratum = 'data/regional-review/southern-africa-411-crosswalk-validation-1047-erratum';
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const jsonBytes = value => Buffer.from(`${JSON.stringify(value, null, 2)}\n`);
const readJSON = name => JSON.parse(fs.readFileSync(path.join(root, name), 'utf8'));
const gitBytes = (commit, name) => execFileSync('git', ['show', `${commit}:${name}`], {maxBuffer: 32 * 1024 * 1024});
const descriptor = (name, bytes, extra = {}) => ({path: name, bytes: bytes.length, sha256: sha(bytes), hash_kind: 'file-bytes', ...extra});
const timestamp = new Date().toISOString();
const issue = readJSON(issueContractPath);
const work = JSON.parse(issue.body.match(/<!-- worldatlas-work:v1\s*\n([\s\S]*?)\n-->/)?.[1] ?? 'null');
if (issue.number !== 1459 || issue.state !== 'open' || !work || work.mode !== 'geography' ||
    JSON.stringify(work.owned_paths) !== JSON.stringify([`${packet}/`])) throw new Error('Live issue snapshot no longer matches the reviewed scope');
const expectedSubjects = work.evidence_quality.subject_ids;
if (expectedSubjects.length !== 223 || new Set(expectedSubjects).size !== 223) throw new Error('Issue contract does not contain 223 unique subjects');
const expectedPins = work.evidence_quality.pins;
if (Object.keys(expectedPins).length !== 27) throw new Error('Issue contract pin inventory changed');
const commitFor = name => name.startsWith(`${oldErratum}/`) ? predecessorCommit : originalCommit;
const baselineFiles = [];
const pins = {};
const pinFiles = {};
for (const [name, expectedSha] of Object.entries(expectedPins)) {
  const commit = commitFor(name);
  const raw = gitBytes(commit, name);
  if (sha(raw) !== expectedSha) throw new Error(`Immutable issue pin mismatch: ${name}`);
  baselineFiles.push(descriptor(name, raw, {role: 'original-source', commit}));
  pins[name] = expectedSha;
  pinFiles[name] = {path: name, commit};
}
const baselineTemplate = readJSON(templatePath).baseline;
const sourceByPath = new Map();
const sourceSpecs = readJSON(`${originalPacket}/source-review.json`).sources;
for (const source of sourceSpecs) if (source.artifact_path?.endsWith('.geojson')) {
  const file = `${originalPacket}/${source.artifact_path}`;
  const spec = baselineFiles.find(entry => entry.path === file);
  if (!spec || spec.sha256 !== source.sha256 || spec.bytes !== source.bytes) throw new Error(`Source pin mismatch: ${source.id}`);
  sourceByPath.set(source.id, {...source, file});
}
if (sourceByPath.size !== 3) throw new Error('Expected the three retained country source collections');

const validatorPath = `${packet}/verify-integrity.mjs`;
const validatorSha = sha(fs.readFileSync(path.join(root, validatorPath)));
const controlFiles = [];
function walk(directory) {
  for (const entry of fs.readdirSync(directory, {withFileTypes: true})) {
    const absolute = path.join(directory, entry.name);
    if (entry.isSymbolicLink()) throw new Error(`Evidence output may not be a symlink: ${absolute}`);
    if (entry.isDirectory()) walk(absolute);
    else if (entry.isFile()) controlFiles.push(path.relative(root, absolute));
  }
}
walk(path.join(root, packet));
const controlResultPaths = controlFiles.filter(name => name.startsWith(`${packet}/controls/`) && name.endsWith('/control-results.json'));
let controlPath;
let controls;
for (const name of controlResultPaths.sort().reverse()) {
  const candidate = readJSON(name);
  if (candidate.validator_sha256 === validatorSha && candidate.controls?.length === 14 &&
      candidate.original_validator_false_acceptances?.length === 2 && candidate.safe_destination_controls?.length === 5) {
    controlPath = name;
    controls = candidate;
    break;
  }
}
if (!controls || controls.controls.some(item => item.outcome !== 'rejected-before-success-receipt' || item.success_receipt_exists) ||
    controls.original_validator_false_acceptances.some(item => item.outcome !== 'accepted-invalid-pair') ||
    controls.safe_destination_controls.some(item => item.outcome !== 'rejected-before-success-receipt' || item.receipt_exists || item.preserved_sentinel === false)) {
  throw new Error('Control evidence does not establish all exact expected relations');
}
const run1Path = `${packet}/vintages/verified-22e8f9d1-run1/validation.json`;
const run2Path = `${packet}/vintages/verified-22e8f9d1-run2/validation.json`;
const run1 = readJSON(run1Path), run2 = readJSON(run2Path);
const run1Bytes = fs.readFileSync(path.join(root, run1Path));
const run2Bytes = fs.readFileSync(path.join(root, run2Path));
if (run1.validator_sha256 !== validatorSha || run2.validator_sha256 !== validatorSha || !run1Bytes.equals(run2Bytes) ||
    run1.frozen_subject_count !== 223 || run1.assessments.rows !== 223 ||
    JSON.stringify(run1.assessment_classifications) !== JSON.stringify({justified: 0, 'correction-needed': 1, 'insufficient-evidence': 222})) {
  throw new Error('Full valid runs are not exact, reproducible outputs from this validator head');
}

const validationTag = timestamp.replace(/[-:.TZ]/g, '').slice(0, 14);
const proofRoot = `${packet}/validation/${validationTag}`;
fs.mkdirSync(path.join(root, packet, 'validation'), {recursive: true});
fs.mkdirSync(path.join(root, proofRoot), {recursive: false});
const sourceDigests = Object.fromEntries(Object.entries(run1.source_artifacts).map(([iso, record]) => [iso, record.sha256]));
const proofRecords = {
  'positive-control.json': {
    version: 1, method_id: 'southern-africa-1286-integrity', kind: 'positive-control', outcome: 'passed',
    verified_at_utc: timestamp,
    runs: [run1Path, run2Path].map(name => ({path: name, bytes: fs.statSync(path.join(root, name)).size, sha256: sha(fs.readFileSync(path.join(root, name)))})),
    source_artifact_sha256_by_country: sourceDigests,
    exact_subject_count: 223,
    assessment_classifications: run1.assessment_classifications
  },
  'negative-control.json': {
    version: 1, method_id: 'southern-africa-1286-integrity', kind: 'negative-control', outcome: 'passed',
    verified_at_utc: timestamp,
    control_results: {path: controlPath, bytes: fs.statSync(path.join(root, controlPath)).size, sha256: sha(fs.readFileSync(path.join(root, controlPath)))},
    retained_directed_mutations_rejected: controls.prior_directed_control_count,
    coherent_adversarial_mutations_rejected: controls.coherent_adversarial_control_count,
    original_false_acceptances_reproduced: controls.original_validator_false_acceptances.length,
    safe_destination_controls: controls.safe_destination_controls.length
  },
  'reproducibility.json': {
    version: 1, method_id: 'southern-africa-1286-integrity', kind: 'reproducibility', outcome: 'passed',
    verified_at_utc: timestamp,
    run_one_sha256: sha(run1Bytes), run_two_sha256: sha(run2Bytes), byte_identical: run1Bytes.equals(run2Bytes),
    input_crosswalk_sha256: run1.crosswalk.sha256, input_assessments_sha256: run1.assessments.sha256,
    validator_sha256: validatorSha
  }
};
for (const [name, value] of Object.entries(proofRecords)) fs.writeFileSync(path.join(root, proofRoot, name), jsonBytes(value), {flag: 'wx'});

const outputFiles = [];
for (const name of controlFiles.sort()) {
  if (name === manifestPath) continue;
  const raw = fs.readFileSync(path.join(root, name));
  if (raw.length > 32 * 1024 * 1024) throw new Error(`Candidate evidence exceeds per-file limit: ${name}`);
  outputFiles.push(descriptor(name, raw));
}
for (const name of Object.keys(proofRecords).map(file => `${proofRoot}/${file}`)) outputFiles.push(descriptor(name, fs.readFileSync(path.join(root, name))));
if (!outputFiles.some(file => file.path === validatorPath)) throw new Error('Replacement code is missing from the output inventory');
const descriptorByPath = new Map(outputFiles.map(file => [file.path, file]));
const run1Descriptor = descriptorByPath.get(run1Path), run2Descriptor = descriptorByPath.get(run2Path);
const controlDescriptor = descriptorByPath.get(controlPath);
if (!run1Descriptor || !run2Descriptor || !controlDescriptor) throw new Error('Actual run/control proof is missing from candidate outputs');

const subjectFiles = {};
for (const [id, name] of Object.entries(baselineTemplate.subject_files)) {
  const file = typeof name === 'string' ? name : name.path;
  const descriptor = baselineFiles.find(row => row.path === file);
  if (!descriptor) throw new Error(`No issue-pinned historical containing file for ${id}`);
  subjectFiles[id] = {path: file, commit: descriptor.commit};
}
const oldSources = readJSON(templatePath).sources;
const sources = oldSources.map(source => ({...source}));
const metrics = [];
const summaries = [];
const metricBindings = [];
const addMetric = (id, value, unit, input, pointer) => {
  const file = descriptorByPath.get(input.path);
  if (!file) throw new Error(`Metric input not in actual output inventory: ${input.path}`);
  metrics.push({id, value, unit, vintage: input.commit === 'candidate' ? 'current' : 'archived',
    input_sha256: file.sha256, evaluation_commit: input.commit === 'candidate' ? baselineHead : input.commit,
    input_file: input});
  summaries.push({metric_id: id, value, unit});
  metricBindings.push({metric_id: id, path: input.path, json_pointer: pointer});
};
const candidate = name => ({path: name, commit: 'candidate'});
addMetric('frozen-subjects', run1.frozen_subject_count, 'subjects', candidate(run1Path), '/frozen_subject_count');
addMetric('crosswalk-rows', run1.crosswalk.rows, 'rows', candidate(run1Path), '/crosswalk/rows');
addMetric('assessment-rows', run1.assessments.rows, 'rows', candidate(run1Path), '/assessments/rows');
for (const iso of ['AGO', 'MOZ', 'MWI']) addMetric(`${iso.toLowerCase()}-source-subjects`, run1.source_subject_joins[iso], 'subjects', candidate(run1Path), `/source_subject_joins/${iso}`);
for (const [kind, value] of Object.entries(run1.assessment_classifications)) addMetric(`${kind.replaceAll('-', '_')}-dispositions`, value, 'rows', candidate(run1Path), `/assessment_classifications/${kind}`);
addMetric('prior-directed-controls-rejected', controls.prior_directed_control_count, 'controls', candidate(controlPath), '/prior_directed_control_count');
addMetric('coherent-adversarial-controls-rejected', controls.coherent_adversarial_control_count, 'controls', candidate(controlPath), '/coherent_adversarial_control_count');
addMetric('all-negative-controls-rejected', controls.total_control_count, 'controls', candidate(controlPath), '/total_control_count');
addMetric('safe-output-controls-rejected', controls.safe_destination_control_count, 'controls', candidate(controlPath), '/safe_destination_control_count');

const manifest = {
  version: 1,
  issue: 1459,
  lane: 'geography',
  worker_id: '01a10948-7d38-75d0-bc01-4cc28ea41f49',
  subject_ids: expectedSubjects,
  subject_ids_sha256: sha(Buffer.from(JSON.stringify([...expectedSubjects].sort()))),
  baseline: {
    version: 2,
    commit: baselineHead,
    files: baselineFiles,
    pins,
    pin_files: pinFiles,
    subject_files: subjectFiles
  },
  sources,
  outputs: outputFiles,
  methods: [
    {id: 'southern-africa-1286-integrity', kind: 'code',
      description: 'Execute the exact validator bytes against the original 223-subject crosswalk and per-ID assessments. Derive country source digests from retained source files and compare every scientific disposition and uncertainty rationale with the frozen original row; publish one fully admitted output receipt.',
      software: 'Node.js 24.19.0, Git, immutable original #411 source and assessment evidence, issue-owned verify-integrity.mjs',
      units: '223 subject IDs, source-feature descriptors, assessment rows, per-ID dispositions, and complete-file SHA-256 bytes'},
    {id: 'southern-africa-source-identity', kind: 'source',
      description: 'Reconcile every subject to its actual retained 2018 Angola, 2019 Mozambique or 2020 Malawi geoBoundaries feature, immutable Atlas feature and pinned hierarchy parent. The check establishes historical identity joins only.',
      software: 'Node.js 24.19.0, Git immutable blobs, pinned geoBoundaries collections and Atlas baseline',
      units: 'native source IDs, feature names, reported roles and source vintages, Atlas IDs and parent IDs'},
    {id: 'southern-africa-prior-evidence-limits', kind: 'source',
      description: 'Preserve source attribution, retrieval dates, historical license evidence and unresolved legal/completeness/neighboring-granularity findings from the original packet. No new territorial conclusion is made.',
      software: 'Pinned original issue #411 source-review.json, source metadata and source attribution statement',
      units: 'source vintages, full-file hashes, licensing and uncertainty limits'}
  ],
  metrics,
  summaries,
  metric_bindings: metricBindings,
  validation: [
    {method_id: 'southern-africa-1286-integrity', kind: 'positive-control', outcome: 'passed', evidence_path: `${proofRoot}/positive-control.json`},
    {method_id: 'southern-africa-1286-integrity', kind: 'negative-control', outcome: 'passed', evidence_path: `${proofRoot}/negative-control.json`},
    {method_id: 'southern-africa-1286-integrity', kind: 'reproducibility', outcome: 'passed', evidence_path: `${proofRoot}/reproducibility.json`}
  ],
  conclusions: [
    {text: 'The replacement validator authenticates each subject source hash against the actual retained native source bytes and preserves all 223 frozen original per-ID scientific dispositions, rationale and uncertainty. Two complete executions of the actual entry point are byte-identical; the 14 directed/adversarial controls reject before a success receipt.',
      status: 'supported', source_ids: ['GB-AGO-2018', 'GB-MOZ-2019', 'GB-MWI-2020', 'issue-411-frozen-scope']},
    {text: 'This validator-integrity work does not establish present-day territorial meaning, legal parentage, boundary accuracy or completeness, neighboring granularity, or geographic approval. The original 0/1/222 decisions and every separate source follow-up remain unchanged.',
      status: 'unresolved', source_ids: ['GB-AGO-2018', 'GB-MOZ-2019', 'GB-MWI-2020', 'issue-411-frozen-scope']}
  ],
  stages: {research: 'complete', implementation: 'proposed', geographic_approval: 'not-requested'},
  commands: [
    'Run the exact Node.js 24 commands recorded in RESEARCH.md; each validator invocation supplies the current validator SHA-256 and a new vintages/<name>/validation.json destination.',
    `node scripts/evidence-quality.mjs ${manifestPath}`,
    'node scripts/premerge-evidence.mjs --issue 1459 --manifest data/regional-review/southern-africa-1286-integrity-erratum/evidence-quality.json',
    'node scripts/check-handoff-scope.mjs --branch geography/southern-africa-1286-integrity-erratum-1459-20261008 --base origin/main --issue-file data/regional-review/southern-africa-1286-integrity-erratum/github-issue-contract.json --pr-body-file data/regional-review/southern-africa-1286-integrity-erratum/pr-body.txt'
  ],
  change_receipts: [...outputFiles.map(file => ({path: file.path, status: 'added'})), {path: manifestPath, status: 'added'}]
};
fs.writeFileSync(path.join(root, manifestPath), jsonBytes(manifest), {flag: 'wx'});
console.log(JSON.stringify({issue: manifest.issue, subjects: manifest.subject_ids.length, baseline_pins: Object.keys(pins).length,
  outputs: outputFiles.length, metrics: metrics.length, controls: controls.controls.length, proof_root: proofRoot}, null, 2));
