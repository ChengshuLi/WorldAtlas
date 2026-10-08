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

/** Baseline v2 authenticates explicit file vintages; the enclosing manifest stays v1. */
export const MAX_BASELINE_COMMITS = 16;
export function baselineFiles(manifest) {
  const baseline = manifest.baseline;
  require(/^[a-f0-9]{40}$/.test(baseline?.commit ?? '') &&
    Array.isArray(baseline.files) && baseline.files.length > 0, 'Missing immutable baseline');
  const version = baseline.version ?? 1;
  require([1, 2].includes(version), 'Unsupported baseline version');
  const seen = new Set();
  const files = baseline.files.map(file => {
    fileDescriptor(file);
    require(version === 2 || !Object.hasOwn(file, 'commit'), 'Per-file commit requires baseline version 2');
    const commit = version === 2 ? file.commit : baseline.commit;
    require(/^[a-f0-9]{40}$/.test(commit ?? ''), 'Historical file requires an immutable commit');
    const key = `${commit}:${file.path}`;
    require(!seen.has(key), 'Duplicate historical file descriptor'); seen.add(key);
    return {...file, commit};
  });
  require(new Set([baseline.commit, ...files.map(file => file.commit)]).size <= MAX_BASELINE_COMMITS,
    'Historical commit inventory exceeds bounded review budget');
  return files;
}

/** A path-only reference is permitted only when it names one exact file vintage. */
export function baselineFile(manifest, reference) {
  const name = typeof reference === 'string' ? reference : reference?.path;
  safeEvidencePath(name);
  const commit = typeof reference === 'string' ? undefined : reference.commit;
  if (typeof reference !== 'string') require(commit !== undefined, 'Versioned reference needs an explicit commit');
  if (commit !== undefined) {
    require(manifest.baseline.version === 2, 'Versioned reference requires baseline version 2');
    require(/^[a-f0-9]{40}$/.test(commit), 'Invalid historical reference commit');
  }
  const matches = baselineFiles(manifest).filter(file => file.path === name &&
    (commit === undefined || file.commit === commit));
  require(matches.length === 1, matches.length ? 'Ambiguous historical file reference' : 'Reference names unpinned file');
  return matches[0];
}

export function metricInput(manifest, metric) {
  const matches = [...baselineFiles(manifest), ...manifest.sources.filter(source => manifest.baseline.version !== 2 || source.retention === 'retained').flatMap(source => source.files ?? [])
    .concat(manifest.outputs).map(file => ({...file, commit: 'candidate'}))]
    .filter(file => file.sha256 === metric.input_sha256);
  if (metric.input_file !== undefined) {
    require(manifest.baseline.version === 2, 'Explicit metric input requires baseline version 2');
    const ref = metric.input_file;
    safeEvidencePath(ref?.path);
    require(ref.commit === 'candidate' || /^[a-f0-9]{40}$/.test(ref.commit ?? ''), 'Invalid metric input commit');
    require(matches.filter(file => file.path === ref.path && file.commit === ref.commit).length === 1,
      'Metric input does not resolve to exact authenticated file');
  } else if (manifest.baseline.version === 2) {
    require(matches.length === 1, 'Ambiguous or missing metric input; declare input_file path and commit');
  }
  require(matches.length > 0, 'Metric references unlisted input');
}

// Subject JSON uses the same declared gzip transport as whole-file inspection.
// Legacy .gz files remain supported; arbitrary binary files are never sniffed.
function subjectJSON(file, name, vintage, readFile, maxFileBytes) {
  const raw = readFile(name, vintage);
  const compressed = file.uncompressed_sha256 !== undefined || name.endsWith('.gz');
  return JSON.parse(compressed ? gunzipSync(raw, {maxOutputLength: maxFileBytes}) : raw);
}

function subjectFileBinding(value, manifest) {
  if (typeof value === 'string') return {path: safeEvidencePath(value), kind: 'direct'};
  if (value && Object.keys(value).sort().join(',') === 'commit,path') {
    const file = baselineFile(manifest, value);
    return {path: file.path, commit: file.commit, kind: 'direct'};
  }
  const keys = Object.keys(value ?? {}).filter(key => key !== 'commit').sort().join(',');
  require(value && typeof value === 'object' && !Array.isArray(value) && value.version === 1 &&
    keys === 'id_template,path,properties,version' &&
    (!Object.hasOwn(value, 'commit') || manifest.baseline.version === 2),
  'Invalid versioned subject-file binding');
  safeEvidencePath(value.path);
  require(Array.isArray(value.properties) && value.properties.length > 0 && value.properties.length <= 8 &&
    value.properties.every(key => typeof key === 'string' && /^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) &&
    new Set(value.properties).size === value.properties.length, 'Invalid subject identity properties');
  require(typeof value.id_template === 'string' && value.id_template.length <= 512 && !/[\r\n]/.test(value.id_template),
    'Invalid subject identity template');
  const tokens = [...value.id_template.matchAll(/\{([^{}]+)\}/g)].map(match => match[1]);
  require(value.id_template.replace(/\{[^{}]+\}/g, '').indexOf('{') === -1 &&
    value.id_template.replace(/\{[^{}]+\}/g, '').indexOf('}') === -1 &&
    tokens.length === value.properties.length && tokens.every((key, index) => key === value.properties[index]),
  'Subject identity template must use each declared property exactly once in order');
  return {path: value.path, ...(Object.hasOwn(value, 'commit') ? {commit: value.commit} : {}), kind: 'composed', properties: value.properties, id_template: value.id_template};
}

function composedSubjectIds(collection, binding) {
  require(collection && collection.type === 'FeatureCollection' && Array.isArray(collection.features),
    'Composed subject source must be a GeoJSON FeatureCollection');
  const ids = new Set();
  for (const feature of collection.features) {
    require(feature?.type === 'Feature' && feature.properties && typeof feature.properties === 'object' &&
      !Array.isArray(feature.properties), 'Composed subject source contains a malformed feature');
    let index = 0;
    const id = binding.id_template.replace(/\{([^{}]+)\}/g, (_token, key) => {
      const value = feature.properties[key];
      require(typeof value === 'string' && value.length > 0 && value === value.trim() && !/[\u0000-\u001f\u007f]/.test(value),
        `Subject feature lacks a canonical string identity property: ${key}`);
      index++;
      return value;
    });
    require(index === binding.properties.length && id.trim().length > 0, 'Invalid composed subject identity');
    require(!ids.has(id), `Duplicate composed subject identity: ${id}`);
    ids.add(id);
  }
  return ids;
}

/** Identity-only projection from retained prior evidence, never a geometry/source certification. */
function verifySubjectInventory(manifest, readFile, maxFileBytes, limits) {
  const inventory = manifest.baseline.subject_inventory;
  require(!manifest.baseline.subject_files, 'Subject inventory cannot replace a containing-file claim');
  require(inventory?.version === 1 && inventory.basis === 'prior-evidence' &&
    text(inventory.id_prefix) && text(inventory.source_property) &&
    text(inventory.json_pointer) && inventory.json_pointer.startsWith('/') &&
    text(inventory.source_id), 'Invalid prior-evidence subject inventory');
  safeEvidencePath(inventory.path); safeEvidencePath(inventory.registry_path);
  const historical = baselineFile(manifest, inventory.commit === undefined ? inventory.path : {path: inventory.path, commit: inventory.commit});
  require(manifest.outputs.some(file => file.path === inventory.registry_path), 'Subject registry must be a declared candidate output');
  require(manifest.sources.some(source => source.id === inventory.source_id), 'Subject inventory references unknown source');
  require(manifest.lane === 'geography' && manifest.stages?.geographic_approval !== 'approved',
    'Prior evidence cannot certify geography');
  limits.push(`Subject inventory uses retained prior evidence (${inventory.path}); original source membership and geometry were not independently validated by this inventory check`);
  if (!readFile) return;
  const decode = (name, vintage) => {
    const files = vintage === 'candidate' ? manifest.outputs : manifest.baseline.files;
    return subjectJSON(files.find(file => file.path === name), name, vintage, readFile, maxFileBytes);
  };
  let values = subjectJSON(historical, historical.path, historical.commit, readFile, maxFileBytes);
  for (const key of inventory.json_pointer.slice(1).split('/').map(key => key.replaceAll('~1', '/').replaceAll('~0', '~'))) {
    require(values && Object.hasOwn(values, key), 'Subject inventory pointer does not resolve');
    values = values[key];
  }
  require(Array.isArray(values) && values.every(text) && new Set(values).size === values.length,
    'Subject inventory needs unique native string IDs');
  // Exact roster, rather than a permissive subset of an unrelated national inventory.
  require(subjectsHash(values.map(value => inventory.id_prefix + value)) === manifest.subject_ids_sha256,
    'Prior evidence subject roster differs from reviewed scope');
  const registry = decode(inventory.registry_path, 'candidate');
  require(registry?.type === 'FeatureCollection' && Array.isArray(registry.features) &&
    registry.features.length === values.length, 'Invalid identity-only subject registry');
  const nativeIds = new Set(values), seen = new Set();
  for (const feature of registry.features) {
    const value = feature?.properties?.source_value, id = inventory.id_prefix + value;
    require(feature?.type === 'Feature' && nativeIds.has(value) && !seen.has(value) &&
      feature.id === id && feature.properties.id === id &&
      feature.properties.source_property === inventory.source_property && feature.geometry === null,
      'Subject registry differs from prior evidence identity-only projection');
    seen.add(value);
  }
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
  const historicalFiles = baselineFiles(manifest);
  if (readFile && manifest.baseline.version === 2) {
    require(typeof readFile.assertAncestor === 'function', 'Historical vintages require ancestry verification');
    for (const commit of new Set([manifest.baseline.commit, ...historicalFiles.map(file => file.commit)])) readFile.assertAncestor(commit);
  }
  const pins = manifest.baseline.pins ?? {};
  for (const [key, value] of Object.entries(pins)) require(hash(value), `Malformed pin: ${key}`);
  for (const [key, value] of Object.entries(expectedPins ?? {})) require(pins[key] === value, `Baseline pin mismatch: ${key}`);
  for (const [key, value] of Object.entries(pins)) {
    const reference = manifest.baseline.pin_files?.[key];
    require(reference !== undefined, `Pin has no actual file binding: ${key}`);
    require(baselineFile(manifest, reference).sha256 === value, `Pin has no actual file binding: ${key}`);
  }
  const sources = manifest.sources;
  require(Array.isArray(sources) && new Set(sources.map(x => x.id)).size === sources.length, 'Duplicate/missing source inventory');
  const limits = [], checked = [], allPaths = new Set(); let total = 0;
  function inspect(file, vintage) {
    fileDescriptor(file);
    require(vintage !== 'candidate' || !Object.hasOwn(file, 'commit'), 'Candidate file cannot declare historical commit');
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
  for (const file of historicalFiles) inspect(file, file.commit);
  require(!manifest.baseline.subject_inventory || manifest.lane === 'geography',
    'Prior-evidence inventory is only supported for geography research');
  if (manifest.lane === 'geography' && !manifest.baseline.subject_inventory) {
    const mappings = manifest.baseline.subject_files;
    require(mappings && subjectsHash(Object.keys(mappings)) === manifest.subject_ids_sha256,
      'Geography needs exact subject-to-containing-file inventory');
    const bindings = new Map(), parsed = new Map(), composedIds = new Map();
    for (const id of ids) {
      const binding = subjectFileBinding(mappings[id], manifest);
      const file = baselineFile(manifest, binding.commit === undefined ? binding.path : {path: binding.path, commit: binding.commit});
      const key = `${file.commit}:${file.path}`;
      if (bindings.has(key)) require(JSON.stringify(bindings.get(key)) === JSON.stringify(binding),
        'Subjects sharing a source file must use one consistent identity binding');
      else bindings.set(key, binding);
      if (readFile) {
        if (!parsed.has(key)) parsed.set(key, subjectJSON(file, file.path, file.commit, readFile, maxFileBytes));
        if (binding.kind === 'direct') {
          require(parsed.get(key).features?.some(f => (f.id ?? f.properties?.id) === id),
            `Subject missing from claimed containing file: ${id}`);
        } else {
          if (!composedIds.has(key)) composedIds.set(key, composedSubjectIds(parsed.get(key), binding));
          require(composedIds.get(key).has(id), `Composed subject missing from claimed containing file: ${id}`);
        }

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
  if (manifest.baseline.subject_inventory) verifySubjectInventory(manifest, readFile, maxFileBytes, limits);
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
    metricInput(manifest, m);
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
  const read = (name, vintage) => {
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
  read.assertAncestor = commit => {
    require(/^[a-f0-9]{40}$/.test(commit ?? ''), 'Unsafe historical commit');
    try { execFileSync('git', ['-C', root, 'merge-base', '--is-ancestor', commit, 'HEAD'], {stdio: 'pipe'}); }
    catch { throw Error('Historical commit is missing or not an ancestor of checkout HEAD'); }
  };
  return read;
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [file, root = process.cwd()] = process.argv.slice(2);
  if (!file) throw Error('Usage: node scripts/evidence-quality.mjs manifest.json [repository-root]');
  console.log(JSON.stringify(validateEvidence(JSON.parse(fs.readFileSync(file, 'utf8')),
    {readFile: repositoryReader(root)}), null, 2));
}
