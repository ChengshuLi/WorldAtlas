import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {gunzipSync} from 'node:zlib';
import {fileURLToPath} from 'node:url';

export const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');
export const subjectsHash = ids => sha256(JSON.stringify([...ids].sort()));
const require = (ok, message) => { if (!ok) throw Error(message); };
const text = x => typeof x === 'string' && x.trim().length > 0;
const hash = x => /^[a-f0-9]{64}$/.test(x ?? '');
export function safeEvidencePath(value) {
  require(text(value) && !value.includes('\\') && !value.includes('\0') && !path.isAbsolute(value) &&
    value.split('/').every(x => x && x !== '.' && x !== '..'), 'Unsafe evidence path');
  return value;
}
function fileDescriptor(file) {
  safeEvidencePath(file.path);
  require(hash(file.sha256) && Number.isSafeInteger(file.bytes) && file.bytes >= 0 &&
    file.hash_kind === 'file-bytes', 'Invalid whole-file descriptor');
  if (file.uncompressed_sha256 !== undefined) require(hash(file.uncompressed_sha256) &&
    Number.isSafeInteger(file.uncompressed_bytes) && file.uncompressed_bytes >= 0, 'Invalid uncompressed descriptor');
}

/** Reader returns bytes from an immutable baseline or candidate; never executes packet code. */
export function validateEvidence(manifest, {readFile, expectedIssue, expectedSubjects, expectedPins,
  expectedLane, maxFileBytes = 32 * 1024 * 1024, maxTotalBytes = 256 * 1024 * 1024} = {}) {
  require(manifest?.version === 1, 'Unsupported evidence version');
  require(Number.isSafeInteger(manifest.issue) && manifest.issue > 0 &&
    (!expectedIssue || manifest.issue === expectedIssue), 'Wrong evidence issue');
  require(['geography', 'source-only', 'content', 'engineering'].includes(manifest.lane) &&
    (!expectedLane || manifest.lane === expectedLane), 'Wrong evidence lane');
  require(text(manifest.worker_id), 'Missing worker identity');
  const ids = manifest.subject_ids;
  require(Array.isArray(ids) && ids.every(text) && new Set(ids).size === ids.length &&
    subjectsHash(ids) === manifest.subject_ids_sha256, 'Subject identity/digest mismatch');
  if (expectedSubjects) require(subjectsHash(expectedSubjects) === manifest.subject_ids_sha256,
    'Subjects disagree with reviewed scope');
  require(/^[a-f0-9]{40}$/.test(manifest.baseline?.commit ?? '') &&
    Array.isArray(manifest.baseline.files) && manifest.baseline.files.length > 0, 'Missing immutable baseline');
  const pins = manifest.baseline.pins ?? {};
  for (const [key, value] of Object.entries(pins)) require(hash(value), `Malformed pin: ${key}`);
  for (const [key, value] of Object.entries(expectedPins ?? {})) require(pins[key] === value, `Baseline pin mismatch: ${key}`);
  for (const [key, value] of Object.entries(pins)) require(manifest.baseline.files.some(f =>
    f.path === manifest.baseline.pin_files?.[key] && f.sha256 === value), `Pin has no actual file binding: ${key}`);
  const sources = manifest.sources;
  require(Array.isArray(sources) && new Set(sources.map(x => x.id)).size === sources.length, 'Duplicate/missing source inventory');
  const limits = [], checked = [], allPaths = new Set(); let total = 0;
  function inspect(file, vintage) {
    fileDescriptor(file);
    const key = `${vintage}:${file.path}`;
    require(!allPaths.has(key), 'Duplicate file descriptor'); allPaths.add(key);
    require(file.bytes <= maxFileBytes, 'Evidence file exceeds budget');
    total += file.bytes; require(total <= maxTotalBytes, 'Evidence total exceeds budget');
    if (!readFile) { limits.push(`Bytes not checked: ${key}`); return; }
    const raw = Buffer.from(readFile(file.path, vintage));
    require(raw.length === file.bytes && sha256(raw) === file.sha256, `Input bytes mismatch: ${key}`);
    if (file.uncompressed_sha256 !== undefined) {
      require(file.uncompressed_bytes <= maxFileBytes, 'Uncompressed file exceeds budget');
      const unpacked = gunzipSync(raw, {maxOutputLength: maxFileBytes});
      require(unpacked.length === file.uncompressed_bytes && sha256(unpacked) === file.uncompressed_sha256,
        `Uncompressed bytes mismatch: ${key}`);
    }
    checked.push(key);
  }
  for (const file of manifest.baseline.files) inspect(file, manifest.baseline.commit);
  if (manifest.lane === 'geography') {
    const mappings = manifest.baseline.subject_files;
    require(mappings && subjectsHash(Object.keys(mappings)) === manifest.subject_ids_sha256,
      'Geography needs exact subject-to-containing-file inventory');
    const parsed = new Map();
    for (const id of ids) {
      const name = mappings[id];
      require(manifest.baseline.files.some(f => f.path === name), 'Subject references unpinned file');
      if (readFile) {
        if (!parsed.has(name)) parsed.set(name, JSON.parse(readFile(name, manifest.baseline.commit)));
        require(parsed.get(name).features?.some(f => (f.id ?? f.properties?.id) === id),
          `Subject missing from claimed containing file: ${id}`);
      }
    }
  }
  for (const source of sources) {
    require(text(source.id) && /^https:\/\//.test(source.url ?? '') && text(source.role) &&
      text(source.vintage) && text(source.retrieved_at), 'Incomplete source citation');
    require(['redistributable', 'restricted', 'unknown'].includes(source.license?.status) &&
      text(source.license?.terms), 'Missing source reuse terms/uncertainty');
    require(['retained', 'restoration-only'].includes(source.retention) &&
      ['verified', 'unverified'].includes(source.verification), 'Missing source verification status');
    require(['reference', 'historical', 'modeled', 'unknown'].includes(source.temporal_status), 'Missing temporal evidence status');
    if (source.supported_interval !== undefined) {
      const {from, to} = source.supported_interval;
      require(Number.isSafeInteger(from) && Number.isSafeInteger(to) && from !== 0 && to !== 0 && from < to,
        'Supported interval must be half-open with no year zero');
    }
    if (source.temporal_status === 'historical') require(source.supported_interval !== undefined,
      'Historical evidence needs an explicit supported interval');
    if (source.retention === 'retained') {
      require(source.license.status === 'redistributable' && Array.isArray(source.files) && source.files.length > 0,
        'Retained source needs reusable bytes');
      for (const file of source.files) inspect(file, 'candidate');
    } else {
      require(text(source.restoration) && text(source.limit), 'Restoration-only source needs instructions and limits');
      limits.push(`${source.id}: ${source.limit}`);
    }
    if (source.verification === 'unverified') limits.push(`${source.id}: factual verification incomplete`);
  }
  require(Array.isArray(manifest.outputs), 'Missing output inventory');
  for (const file of manifest.outputs) inspect(file, 'candidate');
  require(Array.isArray(manifest.methods) && manifest.methods.every(x => text(x.id) && text(x.description) &&
    text(x.software) && text(x.units)), 'Missing method/environment');
  for (const method of manifest.methods) if (method.kind === 'geography') {
    require(method.axis_order === 'longitude-latitude' && text(method.crs) &&
      text(method.area_method) && text(method.distance_method), 'Incomplete geographic measurement policy');
  }
  const metrics = new Map();
  require(Array.isArray(manifest.metrics) && Array.isArray(manifest.summaries), 'Missing numeric result ledger');
  for (const m of manifest.metrics) {
    require(text(m.id) && !metrics.has(m.id) && Number.isFinite(m.value) && text(m.unit) &&
      ['baseline', 'current', 'archived'].includes(m.vintage) && hash(m.input_sha256) &&
      /^[a-f0-9]{40}$/.test(m.evaluation_commit ?? ''), 'Invalid metric identity/vintage');
    if (m.vintage !== 'archived') require(m.evaluation_commit === manifest.baseline.commit,
      'Current/baseline result evaluated against a different vintage');
    require([...manifest.baseline.files, ...sources.flatMap(s => s.files ?? []), ...manifest.outputs]
      .some(f => f.sha256 === m.input_sha256), 'Metric references unlisted input');
    if (m.denominator !== undefined) require(Number.isFinite(m.numerator) && Number.isFinite(m.denominator) &&
      m.denominator > 0 && Math.abs(m.value - m.numerator / m.denominator) <= 1e-10, 'Metric denominator mismatch');
    metrics.set(m.id, m);
  }
  for (const s of manifest.summaries) require(metrics.get(s.metric_id)?.value === s.value &&
    metrics.get(s.metric_id)?.unit === s.unit, 'Narrative summary/result mismatch');
  require(Array.isArray(manifest.conclusions) && manifest.conclusions.every(c => text(c.text) &&
    ['supported', 'unresolved'].includes(c.status) && Array.isArray(c.source_ids) &&
    c.source_ids.every(id => sources.some(s => s.id === id)) &&
    (c.status !== 'supported' || c.source_ids.length > 0)), 'Unsupported conclusion/source linkage');
  require(['partial', 'complete'].includes(manifest.stages?.research) &&
    ['not-proposed', 'proposed', 'implemented', 'published'].includes(manifest.stages?.implementation) &&
    ['unapproved', 'approved', 'not-requested'].includes(manifest.stages?.geographic_approval), 'Missing separate progress stages');
  if (['geography', 'source-only'].includes(manifest.lane)) require(
    ['not-proposed', 'proposed'].includes(manifest.stages.implementation) &&
    manifest.stages.geographic_approval !== 'approved', 'Research cannot assert implemented/published/approved geography');
  require(Array.isArray(manifest.commands) && manifest.commands.every(text), 'Missing reproduction commands');
  return {status: limits.length ? 'limited' : 'bytes-verified', checked, limits,
    factual_validation: 'Requires independent source/method review; hashes do not establish truth'};
}

export function repositoryReader(root, {maxFileBytes = 32 * 1024 * 1024} = {}) {
  root = fs.realpathSync(root);
  return (name, vintage) => {
    safeEvidencePath(name);
    if (vintage !== 'candidate') {
      require(/^[a-f0-9]{40}$/.test(vintage), 'Unsafe baseline commit');
      const mode = execFileSync('git', ['-C', root, 'ls-tree', vintage, '--', name], {encoding: 'utf8'});
      require(mode.startsWith('100644 ') || mode.startsWith('100755 '), 'Baseline must be an ordinary file');
      return execFileSync('git', ['-C', root, 'show', `${vintage}:${name}`], {maxBuffer: maxFileBytes});
    }
    const target = path.join(root, name);
    require(fs.realpathSync(target) === target && fs.lstatSync(target).isFile(), 'Candidate must be an ordinary file without symlinks');
    require(fs.statSync(target).size <= maxFileBytes, 'Candidate exceeds budget');
    return fs.readFileSync(target);
  };
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [file, root = process.cwd()] = process.argv.slice(2);
  if (!file) throw Error('Usage: node scripts/evidence-quality.mjs manifest.json [repository-root]');
  console.log(JSON.stringify(validateEvidence(JSON.parse(fs.readFileSync(file, 'utf8')),
    {readFile: repositoryReader(root)}), null, 2));
}
