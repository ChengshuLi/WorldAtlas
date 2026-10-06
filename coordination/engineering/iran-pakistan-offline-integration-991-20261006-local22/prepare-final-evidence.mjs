// Run only after this producer and every candidate input have been committed.
// This constructs one enforced manifest; it neither reruns geographic measurements
// nor treats archived results as measurements against the new PR base.
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {sha256, subjectsHash, safeEvidencePath, validateEvidence} from '../../../scripts/evidence-quality.mjs';
import {validatePremergeManifest} from '../../../scripts/premerge-evidence.mjs';
import {readGitPRFiles} from '../../../scripts/validate-evidence-partitions.mjs';
import {requirePlainExecution, committedPreparationFiles, candidateBudget} from '../../../scripts/native-ownership/native-preparation-guards.mjs';

const P = 'coordination/engineering/iran-pakistan-offline-integration-991-20261006-local22';
const BASE = 'e4edec12c7238be7a803cd01bf264ee0ac840aea';
const ARCHIVE = 'a6c966993e8e5c48912fa8ac9dc0b720f71130bb';
const JOINT = 'coordination/engineering/iran-pakistan-native-joint-991-20261006-local21/evidence-quality.json';
const MANIFEST = P + '/evidence-quality.json';
const SELF = P + '/prepare-final-evidence.mjs';
const MAX = 32 * 1024 * 1024, TOTAL = 256 * 1024 * 1024;
const need = (ok, message) => { if (!ok) throw Error(message); };
requirePlainExecution();
const repo = fs.realpathSync(path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..'));
const git = args => execFileSync('git', args, {cwd: repo, maxBuffer: MAX});
const gitText = args => git(args).toString('utf8').trim();
const head = gitText(['rev-parse', 'HEAD']);
const branch = gitText(['branch', '--show-current']);
need(branch === 'engineering/iran-pakistan-offline-integration-991-20261006-local22', 'Wrong owned branch');
need([4, 6].includes(process.argv.length) && process.argv[2] === '--worker-id' && process.argv[3]?.trim() &&
  (process.argv.length === 4 || process.argv[4] === '--replace-manifest' && /^[a-f0-9]{64}$/.test(process.argv[5])),
  'Usage: node ' + SELF + ' --worker-id CANONICAL_ROOT_RESERVATION_WORKER_ID [--replace-manifest EXACT_PRIOR_SHA256]');
const worker = process.argv[3];
const priorHash = process.argv.length === 6 ? process.argv[5] : null;
const manifestTarget = path.join(repo, MANIFEST);
git(['merge-base', '--is-ancestor', BASE, head]);
need(gitText(['status', '--porcelain', '--untracked-files=normal']) === '', 'Commit all candidate inputs before manifest preparation');

function blob(name, commit) {
  safeEvidencePath(name);
  need(/^[a-f0-9]{40}$/.test(commit), 'Unsafe immutable commit');
  const row = git(['ls-tree', '-z', commit, '--', name]).toString('utf8');
  need(/^100(?:644|755) blob [a-f0-9]{40}\t/.test(row) && row.endsWith('\t' + name + '\0'), 'Missing/nonordinary immutable file: ' + name);
  const oid = row.split(' ')[2].split('\t')[0];
  const size = Number(gitText(['cat-file', '-s', oid]));
  need(Number.isSafeInteger(size) && size <= MAX, 'Whole-file budget exceeded: ' + name);
  const raw = git(['cat-file', 'blob', oid]);
  need(raw.length === size, 'Incomplete Git bytes: ' + name);
  return raw;
}
let previousManifest = null, previousRaw = null;
function checkedPreviousManifest() {
  const stat = fs.lstatSync(manifestTarget);
  need(stat.isFile() && fs.realpathSync(manifestTarget) === manifestTarget && stat.size <= 1024 * 1024,
    'Prior manifest must be an ordinary bounded file without symlinks');
  const raw = fs.readFileSync(manifestTarget);
  need(raw.length === stat.size && sha256(raw) === priorHash && raw.equals(blob(MANIFEST, head)),
    'Prior manifest must match the declared hash and exact committed HEAD bytes');
  if (previousRaw) need(raw.equals(previousRaw), 'Prior manifest changed during preparation');
  return raw;
}
if (priorHash) {
  previousRaw = checkedPreviousManifest();
  previousManifest = {commit: head, path: MANIFEST, bytes: previousRaw.length, sha256: priorHash};
} else need(!fs.existsSync(manifestTarget), 'Existing manifest requires explicitly reviewed --replace-manifest EXACT_PRIOR_SHA256');
const descriptor = (name, raw, role) => ({path: name, bytes: raw.length, sha256: sha256(raw), hash_kind: 'file-bytes', role});
const baseFiles = new Map(), outputs = new Map();
function baseline(name, role = 'predecessor-context') {
  if (!baseFiles.has(name)) baseFiles.set(name, descriptor(name, blob(name, BASE), role));
  return baseFiles.get(name);
}
function candidate(name, role = 'candidate-whole-file') {
  if (outputs.has(name)) return outputs.get(name);
  const raw = blob(name, head), target = path.join(repo, name);
  need(fs.lstatSync(target).isFile() && fs.realpathSync(target) === target && fs.readFileSync(target).equals(raw),
    'Candidate working bytes differ from committed head: ' + name);
  const pin = descriptor(name, raw, role); outputs.set(name, pin); return pin;
}
function closure(entries, commit) {
  const seen = new Set();
  function visit(name) {
    if (seen.has(name)) return;
    seen.add(name);
    const text = blob(name, commit).toString('utf8');
    // Static import and re-export dependencies; node builtins need no repo file.
    for (const match of text.matchAll(/(?:\bfrom\s*|\bimport\s*)['"](\.[^'"]+)['"]/g))
      visit(path.posix.normalize(path.posix.join(path.posix.dirname(name), match[1])));
  }
  entries.forEach(visit); return [...seen].sort();
}
const trustedEntries = ['scripts/evidence-quality.mjs', 'scripts/premerge-evidence.mjs', 'scripts/validate-evidence-partitions.mjs'];
const trusted = closure(trustedEntries, BASE);
for (const name of trusted) need(blob(name, head).equals(blob(name, BASE)), 'Trusted validator differs from PR base: ' + name);
need(blob('.github/evidence-policy.json', head).equals(blob('.github/evidence-policy.json', BASE)), 'Evidence policy differs from trusted base');
const producerNames = [...new Set([...closure([SELF], head), 'package.json', 'package-lock.json', '.github/evidence-policy.json'])].sort();
const producer = committedPreparationFiles(repo, head, producerNames);
for (const name of producerNames) candidate(name, 'committed-preparation-code-or-configuration');

const joint = JSON.parse(blob(JOINT, BASE));
need(joint.issue === 991 && joint.subject_ids.length === 11 && joint.subject_ids_sha256 ===
  '95fbefa53e01535e0688c88f76e7e6fd081ae1648775eee4e754e953b1cba6ff' &&
  subjectsHash(joint.subject_ids) === joint.subject_ids_sha256, 'Wrong exact reviewed eleven-subject roster');
baseline(JOINT, 'prior-reviewed-subject-roster');
for (const name of ['data/canonical-grid/manifest.json', 'data/hierarchy.json', 'data/geography/part-11.json', 'data/geography/part-17.json',
  'data/attribute-sources.json', 'data/semantic-sources.json']) baseline(name);
for (const [id, name] of Object.entries(joint.baseline.subject_files)) {
  need(joint.subject_ids.includes(id) && ['data/geography/part-11.json', 'data/geography/part-17.json'].includes(name), 'Unexpected subject containing file');
  const packet = JSON.parse(blob(name, BASE));
  need(packet.features.some(feature => (feature.id ?? feature.properties?.id) === id), 'Subject absent from exact predecessor shard: ' + id);
}
const pins = {...joint.baseline.pins};
need(pins.canonical_grid === '73899e8581d74634d6304a9e52aa32849dd174730aba2c6cc48db512a985d1f6' &&
  pins.hierarchy === '568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b', 'Changed normative baseline pins');
for (const [key, name] of Object.entries(joint.baseline.pin_files)) need(baseline(name).sha256 === pins[key], 'Baseline pin lacks actual bytes');
const sources = joint.sources.map(source => {
  const originals = (source.files ?? []).map(file => {
    const pin = baseline(file.path, 'original-source');
    need(pin.bytes === file.bytes && pin.sha256 === file.sha256, 'Original source differs from main joint receipt');
    return pin;
  });
  const {files, ...citation} = source;
  return {...citation, retention: 'restoration-only', verification: 'unverified', original_files: originals,
    restoration: 'Restore the listed immutable original_files using git show ' + BASE + ':PATH; source bytes remain retained on the PR base.',
    limit: 'Original retrieval dates and element timestamps are retained independently. ODbL attribution remains required; this engineering integration does not establish source authority, historical membership, a supported interval, unknown-cell water status, or publication approval.'};
});

// Restorer receipts are read from the immutable prototype, never relabeled as
// fresh-base evaluations. Their metadata describes recovery, not provider truth.
function archivedJSON(name) { return {raw: blob(name, ARCHIVE), value: JSON.parse(blob(name, ARCHIVE))}; }
const terrain = archivedJSON(P + '/terrain-source-restoration-v1.json');
const vegetation = archivedJSON(P + '/vegetation-original-archive-restoration-v1.json');
const providerAttempt = archivedJSON(P + '/vegetation-source-restoration-v1.json');
const semantic = JSON.parse(blob('data/semantic-sources.json', BASE));
const climate = JSON.parse(blob('data/attribute-sources.json', BASE)).sources;
sources.push({id: 'terrain-original-restoration', url: terrain.value.source_url,
  role: 'archived-original-reference-restoration', vintage: 'Original terrain byte vintage; archived recovery execution',
  retrieved_at: 'Not recorded in restoration receipt; no date inferred', license: {status: 'unknown', terms: 'Reuse terms require independent source review; receipt does not establish them.'},
  retention: 'restoration-only', verification: 'unverified', temporal_status: 'reference',
  restoration: 'Inspect ' + ARCHIVE + ':' + P + '/terrain-source-restoration-v1.json; recover exact original SHA ' + terrain.value.sha256 + ' from the recorded URL.',
  limit: 'Source restoration does not establish date alignment, physical truth or approval. HTTP Last-Modified is not a retrieval date.',
  archived_receipt: {commit: ARCHIVE, path: P + '/terrain-source-restoration-v1.json', sha256: sha256(terrain.raw)}, recorded_restoration: terrain.value});
sources.push({id: 'vegetation-original-restoration', url: providerAttempt.value.source_url,
  role: 'archived-original-semantic-archive-restoration', vintage: 'Original semantic archive, not current-provider export',
  retrieved_at: semantic.retrieved, license: {status: 'unknown', terms: 'Original source-specific notices govern reuse; this restoration receipt is not a license approval.'},
  retention: 'restoration-only', verification: 'unverified', temporal_status: 'reference',
  restoration: 'Restore the original semantic archive SHA ' + semantic.archive_sha256 + '; inspect ' + ARCHIVE + ':' + P + '/vegetation-original-archive-restoration-v1.json for raw source SHA and execution.',
  limit: 'The cited URL is the recorded current-provider attempt, not an asserted original-archive download URL. That attempt did not restore the expected original bytes and was not substituted. Original vegetation references do not establish historical date alignment or geographic approval.',
  archived_receipt: {commit: ARCHIVE, path: P + '/vegetation-original-archive-restoration-v1.json', sha256: sha256(vegetation.raw)},
  recorded_restoration: vegetation.value, rejected_provider_attempt: {commit: ARCHIVE, path: P + '/vegetation-source-restoration-v1.json', sha256: sha256(providerAttempt.raw), recorded: providerAttempt.value}});
for (const [index, source] of climate.entries()) sources.push({id: 'climate-original-' + index, url: source.url,
  role: 'baseline-environment-reference-citation', vintage: source.name,
  retrieved_at: 'Not recorded in baseline attribute-sources.json; no date inferred',
  license: {status: 'redistributable', terms: source.license}, retention: 'restoration-only', verification: 'unverified', temporal_status: 'reference',
  restoration: 'Restore exact original archive SHA ' + source.sha256 + ' from its recorded URL; source cache path ' + source.cache_path + '.',
  limit: 'Raw archive exceeds the per-file evidence limit and is not claimed retained in this packet. Climate values remain reference labels; this packet establishes no common source date or historical membership.', original_source: source});

const currentFiles = readGitPRFiles(BASE, head, {cwd: repo});
const existingSelf = currentFiles.find(file => file.filename === MANIFEST);
const files = currentFiles.filter(file => file.filename !== MANIFEST);
need(files.every(file => ['added', 'modified', 'removed', 'renamed'].includes(file.status)), 'Unsupported Git change status');
need(!existingSelf || priorHash && ['added', 'modified'].includes(existingSelf.status), 'Unexpected prior manifest change status');
files.push(existingSelf ?? {filename: MANIFEST, status: 'added'});
const receipts = files.map(file => {
  const row = {path: file.filename, status: file.status};
  if (file.previous_filename) row.previous_path = file.previous_filename;
  if (file.status !== 'added') row.original_sha256 = sha256(blob(file.previous_filename ?? file.filename, BASE));
  if (file.status === 'removed') row.reason = 'Original whole-file bytes remain immutable at PR base ' + BASE + '; prototype preserved at ' + ARCHIVE + '. Candidate context reuse/repacked transport is separately pinned and validated; deletion does not certify geography.';
  else if (file.filename !== MANIFEST) candidate(file.filename);
  return row;
});
const metrics = [], bindings = [];
function archivedMetric(relative, pointer, id, unit, commitKey = 'execution_commit') {
  const name = P + '/' + relative, pin = candidate(name, 'archived-validation-receipt');
  need(blob(name, head).equals(blob(name, ARCHIVE)), 'Archived result changed; do not relabel its measurement vintage: ' + name);
  const document = JSON.parse(blob(name, head));
  const value = pointer.slice(1).split('/').reduce((node, key) => node[key], document);
  const evaluation = document[commitKey];
  need(Number.isFinite(value) && /^[a-f0-9]{40}$/.test(evaluation), 'Missing recorded archived metric/evaluation');
  metrics.push({id, value, unit, vintage: 'archived', input_sha256: pin.sha256, evaluation_commit: evaluation});
  bindings.push({metric_id: id, path: name, json_pointer: pointer});
}
archivedMetric('native-pixel-audit-v3/verification.json', '/checked_rows', 'archived-native-checked-rows', 'rows');
archivedMetric('native-pixel-audit-v3/verification.json', '/checked_runs', 'archived-native-checked-runs', 'runs');
archivedMetric('repack-positive-control-v1.json', '/memberships', 'archived-repack-memberships', 'ordered membership rows');
const validation = [['positive-control', 'repack-positive-control-v1.json'], ['negative-control', 'repack-negative-control-v1.json'],
  ['reproducibility', 'repacked-release-reproducibility-v1.json']].map(([kind, relative]) => {
  const name = P + '/' + relative; candidate(name, 'archived-generator-control');
  need(blob(name, head).equals(blob(name, ARCHIVE)), 'Archived control bytes changed: ' + name);
  const control = JSON.parse(blob(name, head));
  need(control.kind === kind && control.method_id === 'lossless-release-transport-repack' && control.outcome === 'passed', 'Invalid actual typed control');
  return {method_id: control.method_id, kind, outcome: control.outcome, evidence_path: name,
    original_execution_commit: control.execution_commit, archived_at: ARCHIVE};
});

function objectInventory(commit) {
  return new Map(git(['ls-tree', '-r', '-z', commit]).toString('utf8').split('\0').filter(Boolean).map(row => {
    const [metadata, name] = row.split('\t'); return [name, metadata.split(' ')[2]];
  }));
}
const archivedObjects = objectInventory(ARCHIVE), currentObjects = objectInventory(head);
for (const output of outputs.values()) if (archivedObjects.get(output.path) === currentObjects.get(output.path))
  output.byte_lineage = {commit: ARCHIVE, path: output.path, git_blob_sha1: currentObjects.get(output.path),
    scope: 'Exact immutable Git blob equality; retained producer execution, no fresh-base geographic measurement'};

const manifest = {version: 1, issue: 991, lane: 'engineering', worker_id: worker,
  subject_ids: joint.subject_ids, subject_ids_sha256: joint.subject_ids_sha256,
  baseline: {commit: BASE, files: [...baseFiles.values()], pins, pin_files: joint.baseline.pin_files, subject_files: joint.baseline.subject_files},
  sources, outputs: [...outputs.values()].sort((a, b) => a.path.localeCompare(b.path)), change_receipts: receipts,
  methods: [
    {id: 'immutable-copy-lineage', kind: 'code', description: 'Whole-file committed candidate/base inspection and retained archived execution provenance. Installed native, source, reference and history products retain their producer receipts; no new geographic measurement is performed by this manifest producer.', software: 'Plain Node; Git ordinary blob reader; exact committed source closure', units: 'file bytes and SHA-256'},
    {id: 'original-source-restoration', kind: 'source', description: 'Preserve baseline original OSM notices/raw bytes and archived environmental restoration receipts with their actual timestamps, source SHA and limits. No source date, authority, water classification or factual approval follows from byte recovery.', software: 'Git immutable base/prototype receipt inspection', units: 'original file bytes and recorded source references'},
    {id: 'lossless-release-transport-repack', kind: 'generator', helper_version: 'worldatlas-evidence-preparation-v1', description: 'Retained immutable producer experiments preserve the exact ordered release membership objects and predecessor/source/release records while reducing transport fragmentation by JSON payload bytes. Typed control normalization only corrects headers; it does not invent experiments or a new metric vintage.', software: 'Archived committed repacker execution and typed positive/negative/two-run receipts', units: 'ordered membership rows and complete file inventories'}],
  metrics, metric_bindings: bindings, summaries: metrics.map(({id, value, unit}) => ({metric_id: id, value, unit})), validation,
  conclusions: [{status: 'unresolved', source_ids: sources.map(source => source.id), text: 'Geographic authority, historical interval alignment, unknown-cell water status, source reuse approvals and publication approval remain unresolved. Byte verification and archived engineering executions do not establish them.'}],
  stages: {research: 'partial', implementation: 'implemented', geographic_approval: 'unapproved'},
  commands: ['node ' + SELF + ' --worker-id ' + worker + (priorHash ? ' --replace-manifest ' + priorHash : '')],
  preparation: {execution_commit: head, prototype_archive_commit: ARCHIVE, producer,
    ...(previousManifest ? {previous_manifest: previousManifest} : {}),
    runtime: {node: process.version, executable_sha256: sha256(fs.readFileSync(process.execPath))},
    self_hash_excluded: MANIFEST, trusted_validator_baseline: BASE,
    validation_scope: 'Local exact-file fixture using trusted PR-base validators; not a GitHub contract check, independent review, factual approval or deployment'},
};

// Mirror the enforced remoteReader cache keys, including separately admitted
// original change bytes. Baseline BASE and remote vintage "base" are distinct.
const admitted = new Map(); let admittedBytes = 0;
function read(name, vintage) {
  const key = vintage + ':' + name;
  if (admitted.has(key)) return admitted.get(key);
  const raw = blob(name, vintage === 'candidate' ? head : vintage === 'base' ? BASE : vintage);
  admittedBytes += raw.length;
  need(admittedBytes + 131072 <= TOTAL, 'Complete trusted premerge-reader bytes exceed 256 MiB with review reserve (including original change receipts): ' + admittedBytes);
  admitted.set(key, raw); return raw;
}
for (const file of manifest.baseline.files) read(file.path, BASE);
for (const file of manifest.outputs) read(file.path, 'candidate');
for (const file of files.filter(file => file.status !== 'added')) read(file.previous_filename ?? file.filename, 'base');
const budget = candidateBudget([...manifest.baseline.files, ...manifest.outputs]);
manifest.preparation.descriptor_budget = budget.snapshot();
manifest.preparation.trusted_remote_reader_bytes = admittedBytes;
manifest.preparation.original_change_bytes_included = true;
validateEvidence(manifest, {readFile: read, expectedIssue: 991, expectedLane: 'engineering', expectedSubjects: joint.subject_ids, expectedPins: pins});
const result = validatePremergeManifest(manifest, {readFile: read, files, manifestPath: MANIFEST, issue: {number: 991},
  spec: {mode: 'engineering', evidence_quality: {subject_ids: joint.subject_ids, pins}},
  reservation: {worker_id: worker, owned_paths: [P + '/']}, branch,
  pr: {base: {sha: BASE}, head: {sha: head, ref: branch}}});
manifest.preparation.local_selfcheck = {status: result.status, changed_files_checked: result.change_files_checked,
  metric_bindings_checked: result.metric_bindings_checked, limits: result.limits};
const raw = Buffer.from(JSON.stringify(manifest, null, 2) + '\n');
need(raw.length <= 1024 * 1024, 'Enforced manifest fetch exceeds 1 MiB');
// The initial manifest fetch has its own remoteReader; report this independently.
manifest.preparation.manifest_fetch_budget_is_separate = true;
const final = Buffer.from(JSON.stringify(manifest, null, 2) + '\n');
need(final.length <= 1024 * 1024, 'Enforced manifest fetch exceeds 1 MiB');
need(gitText(['rev-parse', 'HEAD']) === head && gitText(['status', '--porcelain', '--untracked-files=normal']) === '',
  'Candidate HEAD or inputs changed during validation');
// Complete the new file before touching the old path. An interrupted preparation
// never truncates the committed prior receipt. The temporary file is ours only.
const temporary = manifestTarget + '.prepare-' + process.pid + '.tmp';
let temporaryOwned = false;
try {
  const fd = fs.openSync(temporary, 'wx', 0o644); temporaryOwned = true;
  try { fs.writeFileSync(fd, final); fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
  need(fs.readFileSync(temporary).equals(final), 'Temporary manifest readback mismatch');
  need(gitText(['rev-parse', 'HEAD']) === head, 'Candidate HEAD changed before manifest installation');
  if (priorHash) {
    checkedPreviousManifest();
    fs.renameSync(temporary, manifestTarget);
    temporaryOwned = false;
  } else {
    // A hard link admits the new path exclusively, without an overwrite race.
    fs.linkSync(temporary, manifestTarget);
    fs.unlinkSync(temporary); temporaryOwned = false;
  }
} finally { if (temporaryOwned) fs.unlinkSync(temporary); }
need(fs.readFileSync(manifestTarget).equals(final), 'Manifest readback mismatch');
console.log(JSON.stringify({path: MANIFEST, bytes: final.length, sha256: sha256(final), changed_files: files.length,
  descriptors: manifest.baseline.files.length + manifest.outputs.length, trusted_remote_reader_bytes: admittedBytes,
  status: result.status, metric_vintage: 'archived', approval: 'unapproved'}));
