import {createHash} from 'node:crypto';

const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const canonical = value => Array.isArray(value) ? value.map(canonical)
  : value && typeof value === 'object'
    ? Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])])) : value;
const valueHash = value => sha(JSON.stringify(canonical(value)) + '\n');
const object = value => value && typeof value === 'object' && !Array.isArray(value);
const localText = value => /\bfile:|\/Users\/|(?:^|[^\w/])\/(?!\/)|[A-Za-z]:[\\/]/.test(value);
const display = value => localText(value) ? `[local-path text omitted; sha256:${sha(value)}]` : value;
const relative = value => typeof value === 'string' && /^[a-zA-Z0-9_./-]+$/.test(value)
  && !value.startsWith('/') && value.split('/').every(part => part && part !== '.' && part !== '..');

function pick(value, keys) {
  const result = {};
  for (const key of keys) {
    const field = value?.[key];
    if (typeof field === 'string') result[key] = display(field);
    else if (typeof field === 'boolean' || typeof field === 'number' && Number.isFinite(field)) result[key] = field;
  }
  return result;
}

function parsed(value) {
  if (Buffer.isBuffer(value) || typeof value === 'string') {
    try { return JSON.parse(value.toString()); } catch { return null; }
  }
  return object(value) ? value : null;
}

function inventory(records) {
  if (!Array.isArray(records)) return undefined;
  const result = {records: records.length, complete_records_sha256: valueHash(records),
    hash_kind: 'canonical-json-record-array-v1'};
  if (records.every(record => Number.isSafeInteger(record?.bytes) && record.bytes >= 0))
    result.file_bytes = records.reduce((sum, record) => sum + record.bytes, 0);
  return result;
}

function reference(name, value, destination) {
  const result = {};
  const path = destination && relative(name) ? `${destination}/${name}` : name;
  if (relative(path)) result.path = path;
  else if (typeof path === 'string') result.omitted_path_sha256 = sha(path);
  if (Buffer.isBuffer(value) || typeof value === 'string') {
    const raw = Buffer.isBuffer(value) ? value : Buffer.from(value);
    result.bytes = raw.length; result.sha256 = sha(raw);
  } else if (value !== undefined) {
    // An already parsed object cannot establish its original whole-file bytes.
    result.canonical_value_sha256 = valueHash(value);
  }
  return result;
}

/** Pure display projection. It reads/writes no files and authenticates no result.
 * Pass original receipt bytes to retain whole-file references. Runtime hashes
 * include every original record field, including omitted installed paths.
 */
export function scientificOperationSummary(publication = {}, options = {}) {
  const observation = publication.observation ?? {};
  const products = options.products ?? {};
  const preparation = parsed(options.preparation);
  const executionRaw = options.executionReceipt ?? products['execution-receipt.json'];
  const execution = parsed(executionRaw);
  const qualification = parsed(options.qualification ?? products['source-qualification.json']);
  const binding = publication.binding ?? preparation?.binding ?? {};
  const result = {version: 1, kind: 'derived-scientific-operation-summary',
    scope: 'Display summary only; unchanged raw artifacts remain the evidence. No qualification or acceptance is established.',
    binding: pick(binding, ['phase', 'config_sha256', 'program_sha256', 'entry_sha256'])};
  if (typeof publication.resumed === 'boolean') result.resumed = publication.resumed;
  const destination = typeof publication.destination === 'string' ? publication.destination : undefined;
  if (destination !== undefined) {
    if (relative(destination)) result.destination = destination;
    else result.omitted_destination_sha256 = sha(destination);
  }
  result.artifacts = {};
  if (options.preparation !== undefined)
    result.artifacts.preparation = reference('preparation.json', options.preparation, destination);
  if (executionRaw !== undefined)
    result.artifacts.execution_receipt = reference('execution-receipt.json', executionRaw, destination);
  const declared = preparation?.outputs;
  if (object(declared)) {
    result.outputs = Object.entries(declared).map(([name, pin]) => ({
      ...reference(name, undefined, destination), ...pick(pin, ['bytes', 'sha256']), declared_in: 'preparation'}));
  } else if (Object.keys(products).length) {
    result.outputs = Object.entries(products).map(([name, raw]) => ({
      ...reference(name, raw, destination), declared_in: 'provided-product-bytes'}));
  } else if (Array.isArray(execution?.outputs)) {
    result.outputs = execution.outputs.map(pin => ({...reference(pin.path, undefined),
      ...pick(pin, ['bytes', 'sha256']), declared_in: 'execution-receipt'}));
  }
  result.observed = {...pick(publication, ['exit_code', 'signal']),
    ...pick(observation, ['elapsed_seconds', 'exit_code', 'signal', 'peak_rss_bytes',
      'normalized_node_lifetime_peak_rss_bytes'])};
  if (typeof execution?.complete === 'boolean') result.observed.receipt_complete = execution.complete;
  const executionFacts = pick(execution, ['elapsed_seconds', 'peak_rss_bytes', 'exit_code', 'signal']);
  if (Object.keys(executionFacts).length) result.observed.execution = executionFacts;
  const qualificationFacts = pick(qualification, ['elapsed_seconds', 'peak_rss_bytes']);
  if (Object.keys(qualificationFacts).length) result.observed.qualification = qualificationFacts;
  if (object(observation.allowance)) result.observed.allowance = pick(observation.allowance, ['phaseBytes', 'rssBytes']);
  const admission = execution?.fresh_admission ?? qualification?.fresh_admission ?? observation.fresh_admission;
  if (object(admission)) {
    result.admission = pick(admission, ['version', 'observed_unix_seconds', 'runtime_inventory_bytes',
      'execution_reserve_bytes', 'program_sha256', 'config_sha256']);
    if (object(admission.allowance)) result.admission.allowance = pick(admission.allowance, ['phaseBytes', 'rssBytes']);
    if (Array.isArray(admission.runtime_files)) result.admission.runtime_inventory = inventory(admission.runtime_files);
  }
  const runtime = observation.runtime_inventory ?? admission?.runtime_files;
  if (Array.isArray(runtime)) result.runtime_inventory = inventory(runtime);
  if (Array.isArray(execution?.inputs)) result.input_inventory = inventory(execution.inputs);
  const limits = [observation.limits, execution?.limits, qualification?.operating_limits]
    .filter(Array.isArray).flat().filter(value => typeof value === 'string');
  if (limits.length) result.limits = [...new Set(limits.map(display))];
  const error = publication.error ?? observation.error;
  if (error !== undefined) {
    result.error = {};
    const message = typeof error === 'string' ? error : error?.message;
    // Failure text can contain arbitrary paths/URIs. Preserve its digest rather
    // than trying to recognize every private path syntax; stderr stays raw.
    if (typeof message === 'string') result.error.message_sha256 = sha(message);
    for (const key of ['name', 'code', 'signal', 'exit_code']) {
      const value = error?.[key];
      if (typeof value === 'number' && Number.isFinite(value)
        || typeof value === 'string' && /^[A-Za-z0-9_-]+$/.test(value)) result.error[key] = value;
    }
  }
  const unparsed = [];
  if (options.preparation !== undefined && !preparation) unparsed.push('preparation');
  if (executionRaw !== undefined && !execution) unparsed.push('execution_receipt');
  if (unparsed.length) result.unparsed_artifacts = unparsed;
  return result;
}
