// Metadata preparation and explicit body acquisition. Existing
// operators, source authority and independent review remain authoritative.
import fs from 'node:fs';
import {performance} from 'node:perf_hooks';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {gunzipSync} from 'node:zlib';
import {locate} from './delivery-handoff-advance.mjs';
import {validatePackageInputs} from './package-inputs.mjs';
import {baselineFiles, validateEvidence} from './evidence-quality.mjs';
import {composeRetainedLedgers} from '../coordination/engineering/additive-native-gap-batch-20261008/composition-v2/compose-retained.mjs';
import {normaliseRetainedRepairLedger, compareVersionedRepairLedgers, verifyCurrentRebindExecution, CURRENT_REBIND_CODE} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';

const need = (ok, message) => { if (!ok) throw Error(message); };
const hex = (value, size) => typeof value === 'string' && new RegExp(`^[a-f0-9]{${size}}$`).test(value);
const canonical = value => Array.isArray(value) ? value.map(canonical) : value && typeof value === 'object'
  ? Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])])) : value;
export const jsonBytes = value => Buffer.from(JSON.stringify(canonical(value)) + '\n');
export const digest = raw => createHash('sha256').update(raw).digest('hex');
const same = (a, b) => jsonBytes(a).equals(jsonBytes(b));
const safe = name => typeof name === 'string' && /^[a-zA-Z0-9_./-]+$/.test(name) && !path.isAbsolute(name)
  && name.split('/').every(part => part && part !== '.' && part !== '..');
const unique = values => Array.isArray(values) && values.length > 0 && values.every(v => typeof v === 'string' && v) && new Set(values).size === values.length;
const environment = () => ({...process.env, GIT_NO_LAZY_FETCH: '1', GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: '/dev/null', GIT_TERMINAL_PROMPT: '0'});

export function pinReader(root) {
  const cache = new Map();
  const git = (...args) => {
    const options={cwd:root,env:environment(),maxBuffer:Infinity};
    if(args[0]==='cat-file'&&args[1]==='blob') options.maxBuffer=Number(git('cat-file','-s',args[2]))+1;
    return execFileSync('git',args,options);
  };
  function descriptor(commit, name) {
    need(hex(commit, 40) && safe(name), 'Exact commit and safe whole-file path required');
    const line = git('ls-tree', '-z', commit, '--', name).toString();
    const match = /^100644 blob ([a-f0-9]{40})\t([^\0]+)\0$/.exec(line);
    need(match && match[2] === name, 'Missing ordinary exact Git body: ' + name);
    const size = Number(git('cat-file', '-s', match[1]).toString());
    need(Number.isSafeInteger(size) && size >= 0, 'Invalid whole body size: ' + name);
    return {path: name, commit, mode: '100644', git_blob_oid: match[1], bytes: size};
  }
  function read(pin) {
    const actual = descriptor(pin.commit, pin.path);
    need(pin.mode === actual.mode && (pin.git_blob_oid ?? pin.blob) === actual.git_blob_oid
      && pin.bytes === actual.bytes && hex(pin.sha256, 64), 'Whole pin identity differs: ' + pin.path);
    if (!cache.has(actual.git_blob_oid)) {
      const raw = git('cat-file', 'blob', actual.git_blob_oid);
      need(raw.length === actual.bytes, 'Whole body length changed');
      cache.set(actual.git_blob_oid, raw);
    }
    const raw = cache.get(actual.git_blob_oid);
    need(digest(raw) === pin.sha256, 'Whole body hash differs: ' + pin.path);
    return raw;
  }
  return {git, read, descriptor, json: pin => JSON.parse(read(pin)),
    hasPath(commit, name) {
      need(hex(commit, 40) && safe(name), 'Exact commit and safe whole-file path required');
      return git('ls-tree', '-z', commit, '--', name).length > 0;
    },
    pin(commit, name) { const p = descriptor(commit, name);
      if (!cache.has(p.git_blob_oid)) { cache.set(p.git_blob_oid, git('cat-file', 'blob', p.git_blob_oid)); }
      return {...p, sha256: digest(cache.get(p.git_blob_oid))}; }};
}

function ordinary(root, relative) {
  need(safe(relative), 'Unsafe input path');
  const filename = path.join(root, relative);
  const stat = fs.lstatSync(filename);
  need(stat.isFile() && fs.realpathSync(filename) === filename, 'Require ordinary input: ' + relative);
  return fs.readFileSync(filename);
}

function admitDestination(root, destination, resume) {
  need(safe(destination) && /^(?:\.cache\/delivery-handoff|coordination\/engineering\/[^/]+)\//.test(destination), 'Use a fresh owned preparation destination');
  let current = root;
  for (const part of destination.split('/')) {
    current = path.join(current, part);
    const stat = fs.lstatSync(current, {throwIfNoEntry: false});
    if (stat) need(stat.isDirectory() && fs.realpathSync(current) === current, 'Nonordinary output ancestor or occupied file');
  }
  const target = path.join(root, destination);
  need(resume || !fs.existsSync(target), 'Occupied destination; use explicit --resume to verify an identical completed phase');
  return target;
}

// Equivalent to the shared new-vintage writer for this JS metadata adapter:
// validate whole destination before mutation, exclusive creation, receipt last.
// Resume means checking every immutable byte; partial output is never repaired.
export function admitPublication(root, destination, products, binding, resume = false) {
  const target = admitDestination(root, destination, resume);
  for (const [name, raw] of Object.entries(products)) {
    need(safe(name) && !name.includes('/') && name !== 'preparation.json' && Buffer.isBuffer(raw),
      'Safe flat product filenames required');
  }
  need(Object.keys(products).length > 0, 'No empty completion');
  const outputs = Object.fromEntries(Object.entries(products).map(([name, raw]) => [name, {bytes: raw.length, sha256: digest(raw)}]));
  const receipt = jsonBytes({version: 1, binding, outputs});
  const inspectExisting = () => {
    admitDestination(root, destination, resume);
    if (!fs.existsSync(target)) return false;
    const expected = [...Object.keys(products), 'preparation.json'].sort();
    const found = fs.readdirSync(target).sort();
    need(same(found, expected), 'Incomplete or foreign resumed output inventory');
    for (const [name, raw] of Object.entries({...products, 'preparation.json': receipt}))
      need(ordinary(root, destination + '/' + name).equals(raw), 'Resumed bytes/binding changed: ' + name);
    return true;
  };
  inspectExisting();
  // A caller may do admitted acquisition between preflight and publication.
  // Recheck the destination after that boundary; never adopt a new collision.
  return () => {
    need(same(Object.keys(products).sort(), Object.keys(outputs).sort())
      && Object.entries(products).every(([name, raw]) => raw.length === outputs[name].bytes && digest(raw) === outputs[name].sha256),
      'Admitted products changed before publication');
    if (inspectExisting()) return {destination, resumed: true, binding};
    fs.mkdirSync(path.dirname(target), {recursive: true});
    fs.mkdirSync(target);
    for (const [name, raw] of Object.entries(products))
      fs.writeFileSync(path.join(target, name), raw, {flag: 'wx'});
    fs.writeFileSync(path.join(target, 'preparation.json'), receipt, {flag: 'wx'});
    return {destination, resumed: false, binding};
  };
}

export function publish(root, destination, products, binding, resume = false) {
  return admitPublication(root, destination, products, binding, resume)();
}

// These are producer fields, not guesses from names: additive-gap-repair counts
// rejected/zero-cell components separately from assigned native cells. Keep this
// roster limited to measured delivery outputs; new measurements need a reviewed
// producer contract before this constructor can publish them.
const deliveryMetricFields = Object.freeze({
  components: {type: 'integer', unit: 'components'},
  source_compatible: {type: 'integer', unit: 'components'},
  assigned_components: {type: 'integer', unit: 'components'},
  zero_cell_components: {type: 'integer', unit: 'components'},
  native_conflicts: {type: 'integer', unit: 'components'},
  source_exceptions: {type: 'integer', unit: 'components'},
  assigned_cells: {type: 'integer', unit: 'native cells'},
  removed_cells: {type: 'integer', unit: 'native cells'},
  reassigned_cells: {type: 'integer', unit: 'native cells'},
  candidate_cell_contributions: {type: 'integer', unit: 'native cells'},
  shared_same_owner_cells: {type: 'integer', unit: 'native cells'},
  elapsed_seconds: {type: 'number', unit: 'seconds'},
  complete_phase_bytes: {type: 'integer', unit: 'bytes'},
  expected_components_verified: {type: 'integer', unit: 'components'},
  cumulative_native_cells_picked_and_sampled: {type: 'integer', unit: 'native cells'},
  stable_owner_controls: {type: 'integer', unit: 'sampled occupied row controls'}
});

export function prepareEvidence(config, reader) {
  let manifest;
  if (config.delivery !== undefined) {
    const d = config.delivery;
    need(d && Object.keys(d).every(key => ['version', 'baseline_commit', 'candidate_commit', 'manifest_path', 'issue',
      'worker_id', 'subject_ids', 'sources', 'limits', 'qualified_constructor_pins', 'pins', 'original_authorities',
      'original_country_issues', 'validation'].includes(key)), 'Unknown delivery evidence field');
    need(!config.template && d?.version === 1 && hex(d.baseline_commit, 40) && hex(d.candidate_commit, 40)
      && safe(d.manifest_path) && Number.isSafeInteger(d.issue) && d.issue > 0
      && typeof d.worker_id === 'string' && d.worker_id.trim() && unique(d.subject_ids)
      && Array.isArray(d.sources) && d.sources.every(source => source.retention === 'restoration-only' && source.files === undefined)
      && (d.validation === undefined || Array.isArray(d.validation)) && Array.isArray(d.limits) && d.limits.length
      && d.limits.every(limit => typeof limit === 'string' && limit.trim())
      && Array.isArray(d.qualified_constructor_pins) && d.qualified_constructor_pins.length,
    'Explicit delivery scope, original scientific citations and limits required');
    reader.git('merge-base', '--is-ancestor', d.baseline_commit, d.candidate_commit);
    const descriptor = pin => ({path: pin.path, commit: d.baseline_commit,
      bytes: pin.bytes, sha256: pin.sha256, hash_kind: 'file-bytes'});
    const metadata = pin => {

      return reader.json(pin);
    };
    const selected = commit => {
      const selectorPin = reader.pin(commit, 'data/ownership-selection.json'), selection = metadata(selectorPin);
      const hook = selection.additive_release;
      need(hook && safe(hook.path), 'Existing selected additive delivery required');
      const sidecarPin = reader.pin(commit, hook.path);
      need(sidecarPin.bytes === hook.bytes && sidecarPin.sha256 === hook.sha256, 'Selected sidecar differs');
      const sidecar = metadata(sidecarPin), base = {...selection}; delete base.additive_release;
      need(sidecar.version === 2 && sidecar.kind === 'retained-native-additive-selection-v2'
        && same(sidecar.base_selection, base), 'Selected base binding differs');
      const registry = reader.pin(commit, sidecar.authority_registry.path);
      const ledger = reader.pin(commit, sidecar.logical_asset_map.ledger.path);
      for (const [actual, original] of [[registry, sidecar.authority_registry], [ledger, sidecar.logical_asset_map.ledger]]) {
        reader.read(original);
        need(actual.bytes === original.bytes && actual.sha256 === original.sha256
          && actual.git_blob_oid === (original.git_blob_oid ?? original.blob), 'Selected original role differs');
      }
      return {selector: selectorPin, selection, registry, ledger, rows: metadata(ledger).rows};
    };
    const before = selected(d.baseline_commit), after = selected(d.candidate_commit);
    const oldBase = {...before.selection}, newBase = {...after.selection};
    delete oldBase.additive_release; delete newBase.additive_release;
    need(same(oldBase, newBase) && Array.isArray(before.rows) && Array.isArray(after.rows), 'Delivery base/rows differ');
    const prior = new Map(before.rows.map(row => [row.component_id, row]));
    const current = new Map(after.rows.map(row => [row.component_id, row]));
    need(prior.size === before.rows.length && current.size === after.rows.length
      && [...prior].every(([id, row]) => current.has(id) && same(row, current.get(id))), 'Inherited delivery row changed');
    const targets = [...new Set(after.rows.filter(row => !prior.has(row.component_id)).map(row => row.target_id))].sort();
    need(same(targets, [...d.subject_ids].sort()), 'Delivery subjects differ from actual added rows');
    const baseline = {version: 2, commit: d.baseline_commit, files: [], pins: {}, pin_files: {}};
    const baselineRoles = {...before, package_inputs: reader.pin(d.baseline_commit, '.github/package-inputs.json')};
    for (const [name, role] of Object.entries({baseline_selector: 'selector', baseline_package_inputs: 'package_inputs',
      baseline_selected_ledger: 'ledger', baseline_authority_registry: 'registry'})) {
      const pin = baselineRoles[role]; reader.read(pin);
      baseline.files.push(descriptor(pin)); baseline.pins[name] = pin.sha256;
      baseline.pin_files[name] = {path: pin.path, commit: d.baseline_commit};
    }
    need(d.pins === undefined || same(d.pins, baseline.pins), 'Issue baseline pins differ from actual accepted baseline');
    const names = reader.git('diff', '--name-only', '--diff-filter=ACMRT', '-z', d.baseline_commit, d.candidate_commit, '--')
      .toString().split('\0').filter(name => name && name !== d.manifest_path);
    need(new Set(names).size === names.length, 'Unique delivery outputs required');
    const outputs = names.map(name => {
      const pin = reader.pin(d.candidate_commit, name); reader.read(pin);
      const {commit, ...file} = descriptor(pin); return file;
    });
    const ids = new Set(), boundComponents = new Set();
    for (const original of d.qualified_constructor_pins) {
      need(typeof original.id === 'string' && original.id && !ids.has(original.id), 'Unique original constructor references required');
      ids.add(original.id);
      const constructed = metadata(original.pin);
      need(constructed.version === 1 && unique(constructed.component_ids) && Array.isArray(constructed.ledger_rows)
        && same(constructed.component_ids, constructed.ledger_rows.map(row => row.component_id))
        && hex(constructed.rule_sha256, 64), 'Complete original constructor rows required');
      for (const row of constructed.ledger_rows) {
        const selected = current.get(row.component_id);
        need(selected && !prior.has(row.component_id) && !boundComponents.has(row.component_id), 'Original constructor scope differs');
        const {authority_sha256, rule_sha256, ...literal} = selected;
        need(hex(authority_sha256, 64) && rule_sha256 === constructed.rule_sha256 && same(literal, row),
          'Original constructor row differs from actual added row');
        boundComponents.add(row.component_id);
      }
      const source = d.sources.filter(source => source.id === original.id);
      need(source.length === 1 && source[0].retention === 'restoration-only'
        && same(source[0].original_pin, original.pin), 'Complete original checkpoint citation required');
    }
    need(boundComponents.size === after.rows.length - before.rows.length, 'Incomplete original constructor coverage');
    if (d.original_authorities !== undefined) need(Array.isArray(d.original_authorities)
      && d.original_authorities.length === ids.size && new Set(d.original_authorities.map(row => row.id)).size === ids.size
      && d.original_authorities.every(row => ids.has(row.id) && same(row.original_authority?.ledger,
        d.qualified_constructor_pins.find(original => original.id === row.id).pin)), 'Original authority inventory differs');
    manifest = {version: 1, issue: d.issue, lane: 'engineering', worker_id: d.worker_id,
      subject_ids: d.subject_ids, subject_ids_sha256: digest(Buffer.from(JSON.stringify([...d.subject_ids].sort()))),
      baseline, sources: d.sources, outputs, methods: [{id: 'retained-selected-delivery', kind: 'code',
        description: 'Derive immutable accepted baseline and candidate byte inventory; original qualification is retained, not replayed.',
        software: 'WorldAtlas prepare-delivery-handoff evidence', units: 'whole-file bytes and SHA-256'}],
      metrics: [], metric_bindings: [], summaries: [], conclusions: [{status: 'unresolved',
        text: 'Byte custody does not establish scientific approval, current-owner-zero, integration, acceptance or publication.',
        source_ids: d.sources.map(source => source.id)}],
      stages: {research: 'partial', implementation: 'proposed', geographic_approval: 'unapproved'}, commands: [],
      qualified_constructor_pins: d.qualified_constructor_pins, limits: d.limits,
      ...(d.validation ? {validation: d.validation} : {}),
      ...(d.original_authorities ? {original_authorities: d.original_authorities} : {}),
      ...(d.original_country_issues ? {original_country_issues: d.original_country_issues} : {})};
  } else manifest = reader.json(config.template);
  need(manifest.baseline?.version === 2 && Array.isArray(manifest.metrics) && !manifest.metrics.length
    && (!manifest.metric_bindings || Array.isArray(manifest.metric_bindings) && !manifest.metric_bindings.length),
  'Evidence construction requires a v2-baseline template with empty metrics/bindings');
  need(Array.isArray(config.metric_sources) && (config.delivery !== undefined || config.metric_sources.length), 'Explicit measured delivery sources required');
  manifest.metric_bindings = [];
  const ids = new Set();
  for (const source of config.metric_sources) {
    const measured = reader.json(source.measurement);
    // Authenticate the actual consumed input as well as the measured result.
    reader.read(source.input);
    need(hex(source.evaluation_commit, 40) && ['baseline', 'current', 'archived'].includes(source.vintage),
      'Explicit measured evaluation commit/vintage required');
    need(source.input_file?.path === source.input.path
      && ['candidate', source.input.commit].includes(source.input_file.commit), 'Metric input selector differs from pinned input');
    const inputs = [...baselineFiles(manifest), ...manifest.outputs.map(file => ({...file, commit: 'candidate'})),
      ...manifest.sources.filter(source => source.retention === 'retained').flatMap(source => source.files ?? []).map(file => ({...file, commit: 'candidate'}))]
      .filter(file => file.path === source.input_file.path && file.commit === source.input_file.commit);
    need(inputs.length === 1 && inputs[0].bytes === source.input.bytes && inputs[0].sha256 === source.input.sha256,
      'Consumed input differs from declared metric input');
    const output = manifest.outputs?.filter(file => file.path === source.measurement.path);
    need(output?.length === 1 && output[0].bytes === source.measurement.bytes && output[0].sha256 === source.measurement.sha256,
      'Measured body differs from declared output');
    if (measured.execution_commit !== undefined) need(measured.execution_commit === source.evaluation_commit, 'Measured evaluation commit differs');
    if (measured.request !== undefined) need(measured.request.sha256 === source.input.sha256
      && measured.request.bytes === source.input.bytes, 'Measured request differs from consumed input');
    if (measured.request_sha256 !== undefined) need(measured.request_sha256 === source.input.sha256, 'Measured request hash differs from consumed input');
    need(Array.isArray(source.fields) && source.fields.length, 'Explicit measured fields required');
    const fields = new Set();
    for (const entry of source.fields) {
      need(entry && typeof entry.field === 'string' && Object.hasOwn(deliveryMetricFields, entry.field), 'Unknown delivery metric field');
      const contract = deliveryMetricFields[entry.field];
      need(entry.unit === undefined || entry.unit === contract.unit, 'Delivery metric unit differs: ' + entry.field);
      need(entry.type === undefined || entry.type === contract.type, 'Delivery metric type differs: ' + entry.field);
      need(typeof entry.id === 'string' && entry.id.trim() && !ids.has(entry.id) && !fields.has(entry.field), 'Duplicate/empty delivery metric identity or field');
      const value = measured[entry.field];
      need(Object.hasOwn(measured, entry.field) && Number.isFinite(value) && value >= 0
        && (contract.type !== 'integer' || Number.isSafeInteger(value)), 'Missing/invalid measured value: ' + entry.field);
      ids.add(entry.id); fields.add(entry.field);
      manifest.metrics.push({id: entry.id, value, unit: contract.unit, vintage: source.vintage,
        input_sha256: source.input.sha256, input_file: {...source.input_file}, evaluation_commit: source.evaluation_commit});
      manifest.metric_bindings.push({metric_id: entry.id, path: source.measurement.path, json_pointer: '/' + entry.field});
    }
  }
  // Shared schema validation includes exact input selectors, vintages and any
  // summaries. Full byte/review/claim gates still run at the existing boundary.
  validateEvidence(manifest);
  return {'evidence-quality.json': jsonBytes(manifest)};
}

export function requestProfile(template, group, config, reader) {
  if (config.compatibility === 'literal-historical-v1') {
    need(template.operating_profile === undefined && !group.requested_resources && !config.requested_resources,
      'Historical compatibility preserves literal v1 resource/runtime fields only');
    return template;
  }
  need(config.compatibility === undefined && template.operating_profile === 'source-native-v2',
    'New issuance requires an admitted source-native-v2 template; historical v1 must be explicit compatibility');
  const support = template.operating_runtime?.support_code;
  need(same(support?.map(p => p.path), ['scripts/local-workspace.mjs', 'scripts/worker-identity.mjs']), 'Complete ordered v2 support-code pins required');
  const head = reader.git('rev-parse', 'HEAD').toString().trim();
  need(Array.isArray(template.executed_code) && template.executed_code.length && template.operating_runtime.supervisor, 'Current v2 code/runtime template required');
  for (const pin of [...template.executed_code, template.operating_runtime.supervisor, ...support]) {
    const actual = reader.pin(head, pin.path);
    need(pin.bytes === actual.bytes && pin.sha256 === actual.sha256, 'New v2 template code differs from actual HEAD: ' + pin.path);
  }
  const {processing_allowance,operating_limits,output_reserve,...request}=template;
  return request;
}

export function prepareRequests(config, reader) {
  const registry = reader.json(config.registry), outputs = {}, index = [], seen = new Set();
  need(registry.version === 1 && registry.kind === 'accepted-administrative-handoffs-v1', 'Existing accepted handoff registry required');
  need(Array.isArray(config.groups) && config.groups.length, 'Explicit finite method/resource groups required');
  for (const group of config.groups) {
    need(/^[a-z0-9-]+$/.test(group.id) && !seen.has(group.id) && unique(group.component_ids), 'Invalid/duplicate request group');
    seen.add(group.id);
    const template = requestProfile(reader.json(group.template), group, config, reader), rule = template.source_rule;
    need(template.operation === 'retained-land-source-premises-v1' && rule?.profile === 'retained-consumed-administrative-source', 'Use an existing admitted SOURCE request template');
    const entries = registry.entries.filter(entry => entry.id === group.handoff_id);
    need(entries.length === 1, 'Unknown/ambiguous accepted whole handoff');
    const entry = entries[0], pin = {...entry.source, commit: entry.accepted_source_commit};
    const handoff = reader.json(pin), roster = handoff.candidate_source_native_bindings;
    need(unique(entry.cohort_ids) && same(handoff.scopeIds, entry.cohort_ids)
      && same(roster?.map(row => row.component_id), entry.cohort_ids), 'Accepted whole handoff order/coverage changed');
    need(same([...new Set(roster.map(row => row.retained_payload?.target_stable_location_id))].sort(), [...entry.target_ids].sort()), 'Accepted handoff target join changed');
    const ordered = entry.cohort_ids.filter(id => group.component_ids.includes(id));
    need(ordered.length === group.component_ids.length, 'Group contains unknown/duplicate component');
    const pinnedHandoff = rule.inputs.filter(p => p.path === rule.cases_path);
    need(pinnedHandoff.length === 1 && same(pinnedHandoff[0], pin) && same(rule.cohort_ids, entry.cohort_ids)
      && rule.outcomes_path === pin.path && rule.registry_path === config.registry.path, 'Template is not bound to this accepted whole handoff');
    // Keep actual template method/product/resource boundaries. No automatic
    // arbitrary chunking, inferred resource limits or expanded science scope.
    need(ordered.every(id => rule.expected_ids.includes(id)) && unique(rule.expected_ids), 'Group exceeds its existing method/resource template scope');
    need(safe(group.destination) && group.destination.startsWith('.cache/native-grid-candidates/'), 'Fresh operator candidate destination required');
    const request = {...template, destination: group.destination, source_rule: {...rule, expected_ids: ordered}};
    const name = group.id + '-source-request.json'; outputs[name] = jsonBytes(request);
    index.push({id: group.id, handoff: pin, component_ids: ordered, template: group.template, request: name,
      method_resource_sha256: digest(jsonBytes({profile: rule.profile, geometry_scope: rule.geometry_scope,
        administrative_products: rule.administrative_products, target_banks: rule.target_banks,
        operating_runtime: template.operating_runtime})),
      next: 'Commit the request, run the existing supervisor separately, then retain real terminal products.'});
  }
  const scopes = index.flatMap(row => row.component_ids);
  need(new Set(scopes).size === scopes.length, 'Overlapping phase component scopes');
  need(unique(config.component_ids) && same([...scopes].sort(), [...config.component_ids].sort()), 'Groups do not exactly cover requested delivery scope');
  outputs['requests.json'] = jsonBytes({version: 1, groups: index, limits: ['Preparation is not source acceptance or execution. Existing operators revalidate current inputs, code and resources.']});
  return outputs;
}

function qualifyTerminal(terminal, requestRaw, publicationRaw, request) {
  const native = Object.hasOwn(terminal, 'qualified');
  need(native ? terminal.qualified === true && terminal.exit?.code === 0 && terminal.exit.signal === null && terminal.refusal === null
    : terminal.exit_code === 0 && terminal.signal === null && terminal.guard_reason === null, 'No genuine successful terminal');
  need(Array.isArray(terminal.owned_processes_remaining) && !terminal.owned_processes_remaining.length
    && Array.isArray(terminal.termination_events) && !terminal.termination_events.length, 'Terminal process cleanup incomplete');
  need(hex(terminal.execution_commit, 40) && terminal.request_sha256 === digest(requestRaw), 'Terminal request/execution binding differs');
  if (request.execution_commit !== undefined) need(terminal.execution_commit === request.execution_commit, 'Terminal execution commit differs');
  if (native) need(terminal.destination === request.destination, 'Terminal destination differs');
  else need(terminal.publication_sha256 === digest(publicationRaw), 'Terminal publication binding differs');
}

function readInventory(raw, descriptor, reader) {
  need(Number.isSafeInteger(descriptor.uncompressed_bytes) && descriptor.uncompressed_bytes > 0,
    'Nonempty decoded inventory identity required');
  const decoded = gunzipSync(raw, {maxOutputLength: descriptor.uncompressed_bytes});
  need(decoded.length === descriptor.uncompressed_bytes && digest(decoded) === descriptor.uncompressed_sha256, 'Actual decoded inventory differs');
  const lines = decoded.toString('utf8').split('\n'); need(lines.pop() === '' && lines.length && lines.every(Boolean), 'Incomplete/empty inventory JSONL');
  const rows = lines.map(line => JSON.parse(line)); need(unique(rows.map(row => row.component_id)), 'Duplicate/missing inventory identity'); return rows;
}

function sourceNativeJoin(request, facts, publication, inventoryRaw, reader, products = null) {
  const source = request.operation === 'retained-land-source-premises-v1';
  need(source || request.operation === 'unactivated-additive-native-batch-v1', 'Unsupported retained operator contract');
  const ids = source ? request.source_rule.expected_ids : request.additive.scope_ids;
  const rows = readInventory(inventoryRaw, publication.inventory, reader);
  need(unique(ids) && same(rows.map(row => row.component_id), ids) && facts.components === ids.length,
    'Inventory does not match complete issued scope/order/count');
  need(same(facts.executed_code, request.executed_code) && same(facts.installed_modules, request.installed_modules)
    && same(facts.baseline, request.baseline) && same(facts.parent, request.parent), 'Published facts changed issued code/runtime/baseline/parent');
  const stage = source ? request.source_rule : request.additive;
  need(same(facts.input_descriptors, [request.report, ...stage.inputs, ...request.baseline.pins]), 'Published facts changed complete issued input closure');
  if (source) {
    need(same(facts.source_rule, stage) && facts.source_compatible === rows.filter(row => row.source_compatible === true).length
      && facts.assigned_cells === 0, 'SOURCE facts/scope/compatibility counts differ from actual rows');
    const pins = stage.inputs.filter(p => p.path === stage.cases_path); need(pins.length === 1, 'Complete SOURCE handoff pin required');
    const handoff = reader.json(pins[0]), cases = handoff.candidate_source_native_bindings;
    need(same(handoff.scopeIds, stage.cohort_ids) && same(cases?.map(row => row.component_id), stage.cohort_ids), 'SOURCE whole handoff scope changed');
    const reference = new Map(cases.map(row => [row.component_id, row.retained_payload?.target_stable_location_id]));
    need(rows.every(row => row.target_id === reference.get(row.component_id)), 'SOURCE inventory target differs from accepted handoff');
    for (const row of rows) {
      const ordinal = cases.findIndex(record => record.component_id === row.component_id);
      need(row.source_case?.ordinal === ordinal && row.source_case.row_sha256 === digest(jsonBytes(cases[ordinal]))
        && same(row.source_case.source, pins[0]), 'SOURCE inventory source-case identity differs from whole handoff');
    }
    need(!publication.assets?.length, 'SOURCE publication has foreign native assets');
  } else {
    need(same(facts.source_predecessor, stage), 'Native facts changed source predecessor');
    const sourcePins = stage.inputs.filter(p => p.path === stage.source_request_path);
    need(sourcePins.length === 1, 'Native output needs the immutable issued SOURCE request');
    const issuedSource = reader.json(sourcePins[0]), sourceRule = issuedSource.source_rule;
    need(issuedSource.operation === 'retained-land-source-premises-v1' && same(sourceRule?.expected_ids, ids), 'Native scope differs from immutable SOURCE scope');
    const handoffPins = sourceRule.inputs.filter(p => p.path === sourceRule.cases_path);
    need(handoffPins.length === 1, 'Native output needs the complete original SOURCE handoff');
    const handoff = reader.json(handoffPins[0]), sourceCases = handoff.candidate_source_native_bindings;
    need(same(handoff.scopeIds, sourceRule.cohort_ids) && same(sourceCases?.map(row => row.component_id), sourceRule.cohort_ids), 'Native original SOURCE handoff scope changed');
    const targets = new Map(sourceCases.map(row => [row.component_id, row.retained_payload?.target_stable_location_id]));
    need(rows.every(row => !['assigned', 'zero-cell'].includes(row.disposition) || row.target_id === targets.get(row.component_id)),
      'Native effective target differs from immutable SOURCE handoff');
    need(rows.every(row => Number.isSafeInteger(row.native_cells) && row.native_cells >= 0), 'Native inventory has invalid measured cell count');
    const cells = rows.reduce((sum, row) => sum + row.native_cells, 0);
    need(Number.isSafeInteger(cells) && facts.assigned_cells === cells, 'Native facts assigned count differs from actual inventory');
    const expected = ['base-native-manifest.json', 'ledger-batch.json', 'patch-batch.json', 'features.json', 'owners-batch.json.gz',
      'release-envelope.json', 'owner-window.json', 'virtual-owner-window.json'].sort();
    need(same(publication.assets?.map(p => p.path).sort(), expected), 'Incomplete fixed native publication asset roster');
    if (products) {
      const ledger = JSON.parse(products['ledger-batch.json']), patch = JSON.parse(products['patch-batch.json']), envelope = JSON.parse(products['release-envelope.json']);
      need(same(ledger.scope_ids, ids) && same(ledger.rows?.map(row => row.component_id), ids), 'Native ledger omitted/reordered issued scope');
      for (let i = 0; i < rows.length; i++) {
        const actual = ledger.rows[i], record = rows[i];
        need(actual.disposition === record.disposition && actual.native_cells === record.native_cells
          && (!['assigned', 'zero-cell'].includes(actual.disposition) || actual.target_id === record.target_id), 'Native ledger/actual inventory differs');
      }
      need(ledger.assigned_cells === cells, 'Native ledger assigned count differs from actual inventory');
      const ledgerHash = digest(products['ledger-batch.json']);
      need(patch.ledger_sha256 === ledgerHash, 'Native patch is not bound to actual ledger');
      const owners = new Set(ledger.rows.filter(row => ['assigned', 'zero-cell'].includes(row.disposition)).map(row => row.pixelIndex));
      need(Array.isArray(patch.rows) && patch.rows.every(row => Array.isArray(row.runs) && row.runs.every(run =>
        Array.isArray(run) && run.length === 3 && run.every(Number.isSafeInteger) && run[0] >= 0 && run[1] > run[0] && owners.has(run[2]))),
      'Native patch owner/run differs from effective ledger');
      need(patch.rows.reduce((sum, row) => sum + row.runs.reduce((n, run) => n + run[1] - run[0], 0), 0) === cells,
        'Native patch measured cells differ from inventory/ledger');
      for (const [role, name] of Object.entries({base_manifest: 'base-native-manifest.json', ledger: 'ledger-batch.json', patch: 'patch-batch.json', owner_roster: 'owners-batch.json.gz'})) {
        const descriptor = envelope.additiveRelease?.[role];
        need(descriptor?.bytes === products[name].length && descriptor.sha256 === digest(products[name]), 'Native envelope output join differs: ' + role);
      }
    }
  }
  return rows;
}

function historicalRebindCode(request, reader) {
  need(same(request.executed_code?.map(p => p.path), CURRENT_REBIND_CODE), 'Complete historical rebind code roster required');
  return CURRENT_REBIND_CODE.map(name => {
    const pin = reader.pin(request.execution_commit, name); reader.read(pin);
    return {path: name, bytes: pin.bytes, sha256: pin.sha256};
  });
}

function localRebindJoin(request, terminal, publication, products, reader) {
  const proof = JSON.parse(products['code-source.json']), plan = JSON.parse(products['issued-plan.json']), stdout = JSON.parse(products['stdout.json']);
  need(terminal.code_source_sha256 === digest(products['code-source.json']) && same(proof.command, terminal.command)
    && same(proof.command, request.execution?.command) && same(proof.pre_use, request.execution?.pre_use)
    && same(proof.pre_use, proof.post_use) && proof.execution_commit === request.execution_commit,
  'Rebind terminal/code-source/issued execution contract differs');
  need(proof.pre_use.plan.bytes === products['issued-plan.json'].length && proof.pre_use.plan.sha256 === digest(products['issued-plan.json'])
    && same(proof.pre_use.code, historicalRebindCode(request, reader)) && plan.execution_commit === request.execution_commit,
  'Rebind actual issued plan/code bytes differ');
  need(stdout.request_sha256 === terminal.request_sha256 && stdout.publication_sha256 === terminal.publication_sha256
    && stdout.execution_commit === terminal.execution_commit && stdout.result_sha256 === digest(products['result.json'])
    && publication.outputs.result.sha256 === stdout.result_sha256, 'Rebind actual stdout/product join differs');
  need(Number.isFinite(terminal.elapsed_seconds) && terminal.elapsed_seconds >= 0, 'Invalid rebind elapsed observation');
}

export function retainProducts(config, root, reader, readLocal = ordinary) {
  const requestRaw = reader.read(config.request), request = JSON.parse(requestRaw);
  const terminalRaw = readLocal(root, config.terminal), terminal = JSON.parse(terminalRaw); const publicationRaw = readLocal(root, config.output + '/publication.json'), publication = JSON.parse(publicationRaw); qualifyTerminal(terminal, requestRaw, publicationRaw, request);
  const rows = publication.outputs ? Object.values(publication.outputs) : publication.complete === true
    ? [{path: 'facts.json', ...publication.facts}, {path: 'inventory.jsonl.gz', ...publication.inventory}, ...(publication.assets ?? [])] : [];
  need(rows.length && new Set(rows.map(p => p.path)).size === rows.length, 'Missing/duplicate publication output inventory');
  const outputs = {'request.json': requestRaw, 'terminal.json': terminalRaw, 'publication.json': publicationRaw};
  for (const row of rows) {
    need(safe(row.path) && !row.path.includes('/') && !Object.hasOwn(outputs, row.path), 'Unsafe/duplicate publication path');
    const raw = readLocal(root, config.output + '/' + row.path); need(raw.length === row.bytes && digest(raw) === row.sha256, 'Incomplete actual publication output: ' + row.path);
    if (row.uncompressed_bytes !== undefined) {
      need(Number.isSafeInteger(row.uncompressed_bytes) && row.uncompressed_bytes > 0, 'Invalid decoded output identity');
      const decoded = gunzipSync(raw, {maxOutputLength: row.uncompressed_bytes});
      need(decoded.length === row.uncompressed_bytes && digest(decoded) === row.uncompressed_sha256, 'Decoded output differs');
    }
    outputs[row.path] = raw;
  }
  const facts = JSON.parse(outputs['facts.json']);
  need(facts.execution_commit === terminal.execution_commit, 'Published facts execution differs');
  if (publication.outputs) {
    need(publication.kind === 'native-additive-current-bank-rebind-publication-v1'
      && publication.execution_commit === terminal.execution_commit && publication.request_sha256 === digest(requestRaw)
      && facts.request_sha256 === digest(requestRaw) && facts.result_sha256 === digest(outputs['result.json']),
    'Rebind publication/facts/result are not joined to terminal request');
    const custodyNames = {code_source: 'code-source.json', issued_plan: 'issued-plan.json', stderr: 'stderr.log', stdout: 'stdout.json'};
    need(config.custody && same(Object.keys(config.custody).sort(), Object.keys(custodyNames).sort()), 'Complete real rebind execution custody required');
    for (const [role, name] of Object.entries(custodyNames)) {
      const raw = readLocal(root, config.custody[role]); outputs[name] = raw;
    }
    localRebindJoin(request, terminal, publication, outputs, reader);
  } else need(facts.request?.sha256 === digest(requestRaw) && facts.request.bytes === requestRaw.length
    && facts.operation === request.operation, 'Published facts are not joined to the actual terminal request');
  if (!publication.outputs) sourceNativeJoin(request, facts, publication, outputs['inventory.jsonl.gz'], reader, outputs);
  return outputs;
}

export function nativeRequests(config, reader) {
  const outputs = {}, seen = new Set(), components = new Set();
  need(Array.isArray(config.groups) && config.groups.length, 'Explicit native groups required');
  for (const group of config.groups) {
    need(/^[a-z0-9-]+$/.test(group.id) && !seen.has(group.id), 'Unique native group IDs required'); seen.add(group.id);
    const sourceRaw = reader.read(group.source.request), source = JSON.parse(sourceRaw);
    const publicationRaw = reader.read(group.source.publication), publication = JSON.parse(publicationRaw);
    const terminal = reader.json(group.source.operating), facts = reader.json(group.source.facts);
    qualifyTerminal(terminal, sourceRaw, publicationRaw, source);
    need(source.operation === 'retained-land-source-premises-v1' && publication.complete === true
      && publication.facts.sha256 === group.source.facts.sha256 && publication.facts.bytes === group.source.facts.bytes
      && publication.inventory.sha256 === group.source.inventory.sha256 && publication.inventory.bytes === group.source.inventory.bytes,
    'Native request requires actual committed SOURCE publication products');
    sourceNativeJoin(source, facts, publication, reader.read(group.source.inventory), reader);
    need(facts.execution_commit === terminal.execution_commit && facts.request?.sha256 === digest(sourceRaw)
      && same(facts.source_rule, source.source_rule), 'SOURCE facts/terminal/request mismatch');
    const template = requestProfile(reader.json(group.template), group, config, reader), additive = template.additive;
    need(template.operation === 'unactivated-additive-native-batch-v1' && additive?.source_profile === source.source_rule.profile
      && same(additive.scope_ids, source.source_rule.expected_ids) && same(template.baseline, source.baseline),
    'Native template method/scope/baseline differs from qualified source');
    need(unique(additive.scope_ids) && additive.scope_ids.every(id => !components.has(id)), 'Overlapping/duplicate native scopes');
    additive.scope_ids.forEach(id => components.add(id));
    need(Number.isSafeInteger(facts.runtime?.bytes) && facts.runtime.bytes > 0 && hex(facts.runtime.sha256, 64), 'Actual SOURCE runtime identity required');
    // Native's existing reader compares the literal issued request descriptor,
    // not only an alias with equal bytes at a later retention commit.
    const originalRequest = facts.request; reader.read(originalRequest);
    need(originalRequest.path === group.source.request.path && originalRequest.bytes === sourceRaw.length
      && originalRequest.sha256 === digest(sourceRaw), 'Original SOURCE request descriptor differs');
    const inventoryPin = {...group.source.inventory, uncompressed_bytes: publication.inventory.uncompressed_bytes,
      uncompressed_sha256: publication.inventory.uncompressed_sha256};
    const changes = {source_request_path: originalRequest, operating_path: group.source.operating,
      publication_path: group.source.publication, facts_path: group.source.facts, inventory_path: inventoryPin};
    const replaced = new Set(Object.keys(changes).map(key => additive[key]));
    need(replaced.size === 5 && [...replaced].every(name => additive.inputs.filter(p => p.path === name).length === 1), 'Native template lacks exact source input slots');
    const inputs = additive.inputs.filter(p => !replaced.has(p.path));
    for (const pin of Object.values(changes)) inputs.push({...pin, blob: pin.blob ?? pin.git_blob_oid});
    for (const pin of inputs) delete pin.git_blob_oid;
    need(new Set(inputs.map(p => p.path)).size === inputs.length, 'Replacement source input path collision');
    need(safe(group.destination) && group.destination.startsWith('.cache/native-grid-candidates/'), 'Native candidate destination required');
    outputs[group.id + '-native-request.json'] = jsonBytes({...template, destination: group.destination,
      additive: {...additive, ...Object.fromEntries(Object.entries(changes).map(([key, pin]) => [key, pin.path])),
        source_execution_commit: terminal.execution_commit, source_runtime: facts.runtime, inputs}});
  }
  return outputs;
}

export function rebindCustody(config, reader, certificate = false) {
  const request = reader.json(config.request), terminal = reader.json(config.terminal), publication = reader.json(config.publication);
  qualifyTerminal(terminal, reader.read(config.request), reader.read(config.publication), request);
  need(same(Object.keys(config.execution_custody).sort(), ['code_source', 'issued_plan', 'stderr', 'stdout', 'terminal']), 'Complete external execution custody required');
  need(same(config.execution_custody.terminal, config.terminal), 'Custody terminal differs');
  const expected = {version: 1, kind: 'native-additive-current-bank-rebind-operating-v1',
    execution_commit: terminal.execution_commit, request_sha256: config.request.sha256, publication_sha256: config.publication.sha256,
    exit_code: terminal.exit_code, signal: terminal.signal, owned_processes_remaining: terminal.owned_processes_remaining,
    ...(Object.hasOwn(terminal,'lifetime_rss_bytes')?{lifetime_rss_bytes:terminal.lifetime_rss_bytes}:{}), elapsed_seconds: terminal.elapsed_seconds, execution_custody: config.execution_custody};
  const operating = certificate ? reader.json(config.operating) : expected;
  need(same(operating, expected), 'Operating proof differs from exact genuine terminal/custody');
  need(publication.execution_commit === request.execution_commit && publication.request_sha256 === config.request.sha256,
    'Rebind publication request binding differs');
  for (const role of ['facts', 'result']) {
    reader.read(config[role]); const output = publication.outputs?.[role];
    need(output && output.bytes === config[role].bytes && output.sha256 === config[role].sha256, 'Rebind output pin differs from actual publication');
  }
  const custody = Object.fromEntries(Object.entries(config.execution_custody).map(([role, pin]) => [role, reader.read(pin)]));
  verifyCurrentRebindExecution({request, operating, expectedCode: historicalRebindCode(request, reader), custody: {...custody, result_sha256: config.result.sha256}});
  if (!certificate) return {'operating.json': jsonBytes(operating)};
  return {'certificate.json': jsonBytes({version: 1, kind: 'qualified-native-additive-current-bank-rebind-v1',
    execution_commit: request.execution_commit, base_selection: request.base_selection,
    authority_registry_sha256: request.authority_registry_sha256,
    request: config.request, facts: config.facts, publication: config.publication, result: config.result, operating: config.operating})};
}

export function composeAuthorities(config, reader) {
  if (config.selector) {
    const authorityFields = ['rule_preimage', 'source_authority', 'ledger', 'native_patch'];
    const multiple = Object.hasOwn(config, 'authorities');
    need(!multiple || !authorityFields.some(key => Object.hasOwn(config, key)), 'Do not mix singleton and multiple modern authorities');
    const authorities = multiple ? config.authorities : [Object.fromEntries(authorityFields.map(key => [key, config[key]]))];
    need(Array.isArray(authorities) && authorities.length > 0 && authorities.every(value => value
      && same(Object.keys(value).sort(), [...authorityFields].sort())
      && authorityFields.every(key => value[key] && Number.isSafeInteger(value[key].bytes) && value[key].bytes > 0)),
    'Complete nonempty modern authority pin groups required');
    need(config.selector.path === 'data/ownership-selection.json' && typeof config.effective_release_id === 'string'
      && config.effective_release_id.startsWith('geography:'), 'Original selected baseline and explicit effective release required');
    const selection = reader.json(config.selector), hook = selection.additive_release;
    need(hook && safe(hook.path), 'Existing cumulative selection required');
    const sidecarPin = reader.pin(config.selector.commit, hook.path);
    need(sidecarPin.bytes === hook.bytes && sidecarPin.sha256 === hook.sha256, 'Original selected sidecar differs');
    const sidecar = reader.json(sidecarPin), base = {...selection}; delete base.additive_release;
    need(sidecar.version === 2 && sidecar.kind === 'retained-native-additive-selection-v2'
      && same(sidecar.base_selection, base), 'Original selected base differs');
    const assets = sidecar.logical_asset_map;
    need(assets && same(Object.keys(assets).sort(), ['base_manifest', 'ledger', 'owner_roster', 'patch']), 'Complete prior logical assets required');
    const priorRegistry = reader.json(sidecar.authority_registry), priorLedger = reader.json(assets.ledger);
    const priorPatch = reader.json(assets.patch), wrapped = reader.json(sidecar.runtime_envelope);
    const envelope = wrapped.additiveRelease ?? wrapped;
    need(envelope.version === 2 && envelope.kind === 'retained-native-base-plus-delta-v2', 'Existing v2 runtime envelope required');
    for (const [role, pin] of Object.entries(assets)) {
      const declared = envelope[role];
      need(declared?.bytes === pin.bytes && declared?.sha256 === pin.sha256
        && (declared.decoded_bytes ?? declared.bytes) === (pin.decoded_bytes ?? pin.bytes)
        && (declared.decoded_sha256 ?? declared.sha256) === (pin.decoded_sha256 ?? pin.sha256), 'Prior envelope asset binding differs: ' + role);
    }
    need(priorRegistry.version === 1 && priorRegistry.kind === 'retained-rule-authority-registry-v1' && priorLedger.version === 2,
      'Existing v2 cumulative registry/ledger required');
    const manifest = reader.json(assets.base_manifest);
    const contract = Object.fromEntries(['size', 'coordinateBits', 'method', 'native_latitudes', 'hierarchy_sha256', 'original_assets']
      .map(key => [key, manifest[key]]));
    need(priorPatch.version === 2 && priorPatch.authority_registry_sha256 === sidecar.authority_registry.sha256
      && priorPatch.ledger_sha256 === assets.ledger.sha256 && same(priorPatch.base_reference, envelope.base_reference)
      && same(priorPatch.effective_reference, envelope.effective_reference), 'Prior cumulative patch bindings differ');
    const entries = [...priorRegistry.entries], addedRows = [], candidates = [];
    const authorityIds = new Set(entries.map(entry => entry.authority_sha256));
    const oldIds = new Set(priorLedger.rows.map(row => row.component_id));
    for (const original of authorities) {
      const constructed = reader.json(original.ledger), candidate = reader.json(original.native_patch);
      const binding = reader.json(original.source_authority), preimage = reader.json(original.rule_preimage);
      // Literal metadata contract of constructAuthorityRegistry. Retained constructor
      // results supply qualification; the final selected reader remains authoritative.
      const rule = reader.pin(original.rule_preimage.commit, original.rule_preimage.path);
      const authority = {policy_id: 'retained-source-literal-additions', policy_version: 1, rule_preimage: rule,
        rule_sha256: rule.sha256, source_authority: reader.pin(original.source_authority.commit, original.source_authority.path)};
      const entry = {authority_sha256: digest(jsonBytes(authority)), ...authority};
      need(binding.version === 1 && binding.kind === 'source-target-native-custody-v1'
        && same(Object.keys(binding).sort(), ['kind', 'native_patch', 'source_evidence', 'version'])
        && same(preimage, {...binding, kind: 'source-target-native-rule-v1'}) && same(binding.native_patch, original.native_patch)
        && entry.rule_sha256 === digest(jsonBytes(preimage)) && constructed.rule_sha256 === entry.rule_sha256 && unique(constructed.component_ids)
        && same(constructed.component_ids, constructed.ledger_rows?.map(row => row.component_id)),
      'Committed modern constructor scope/rule/patch differs');

      const evidence = reader.json(binding.source_evidence);
      need(same(evidence.base_reference, envelope.base_reference) && same(evidence.native_contract, contract)
        && assets.base_manifest.sha256 === selection.sha256 && assets.owner_roster.sha256 === manifest.original_assets?.bounds?.sha256,
      'Modern source changes the selected native baseline/contract');
      need(!authorityIds.has(entry.authority_sha256), 'Modern authority is already selected or duplicated');
      authorityIds.add(entry.authority_sha256);
      entries.push(entry);
      need(unique(evidence.targets?.map(target => target.id)), 'Complete original source-target roster required');
      const targets = new Map();
      for (const target of evidence.targets) {
        const id = target.target_id ?? target.id, prior = targets.get(id);
        need(target.source_receipt_sha256 === evidence.physical_evidence?.sha256
          && (!prior || prior.pixelIndex === target.pixelIndex && prior.source_family === target.source_family
            && same(prior.base_geometry, target.base_geometry)), 'Conflicting original source target/family/receipt');
        targets.set(id, target);
      }
      const added = constructed.ledger_rows.map(row => {
        need(row.representation === 'native-cells' && row.component_id === 'source-target:' + digest(jsonBytes({target_id: row.target_id,
          evidence: binding.source_evidence.sha256})) && !oldIds.has(row.component_id)
          && !Object.hasOwn(row, 'authority_sha256') && !Object.hasOwn(row, 'rule_sha256'), 'Foreign or duplicate modern component');
        const target = targets.get(row.target_id);
        need(target?.pixelIndex === row.pixelIndex && same(target.base_geometry, row.base_geometry)
          && target.source_receipt_sha256 === evidence.physical_evidence?.sha256 && row.source_receipt_sha256 === target.source_receipt_sha256,
        'Modern row changes the original source target/owner/receipt');
        oldIds.add(row.component_id);
        return {...row, authority_sha256: entry.authority_sha256, rule_sha256: entry.rule_sha256};
      });
      need(added.length === targets.size, 'Modern constructor omits an original source target');
      addedRows.push(...added);
      candidates.push({candidate, added});
    }
    const registry = {...priorRegistry, entries: entries.sort((a, b) => a.authority_sha256.localeCompare(b.authority_sha256))};
    const rows = [...priorLedger.rows, ...addedRows].sort((a, b) => a.component_id.localeCompare(b.component_id));
    const ledger = {...priorLedger, authority_registry_sha256: digest(jsonBytes(registry)), rows, scope_ids: rows.map(row => row.component_id)};
    compareVersionedRepairLedgers(priorLedger, ledger, {beforeRegistry: priorRegistry, afterRegistry: registry});
    need(priorLedger.rows.every(row => same(row, rows.find(next => next.component_id === row.component_id))), 'Literal inherited row/exception changed');
    const normalized = normaliseRetainedRepairLedger(ledger, registry), ledgerRaw = jsonBytes(ledger);
    const union = patches => {
      const byRow = new Map();
      for (const patch of patches) {
        need(Array.isArray(patch.rows), 'Complete native intervals required'); let previous = -1;
        for (const row of patch.rows) {
          need(Number.isSafeInteger(row.y) && row.y > previous && row.y < manifest.size && Array.isArray(row.runs) && row.runs.length,
            'Invalid complete native row'); previous = row.y; let end = 0;
          for (const run of row.runs) {
            need(Array.isArray(run) && run.length === 3 && run.every(Number.isSafeInteger) && run[0] >= end
              && run[1] > run[0] && run[1] <= manifest.size && run[2] > 0, 'Invalid complete native interval'); end = run[1];
          }
          const runs = byRow.get(row.y) ?? []; runs.push(...row.runs.map(run => [...run])); byRow.set(row.y, runs);
        }
      }
      return [...byRow].sort((a, b) => a[0] - b[0]).map(([y, runs]) => {
        runs.sort((a, b) => a[0] - b[0]); const merged = [];
        for (const run of runs) {
          const last = merged.at(-1); need(!last || run[0] >= last[1], 'Modern cells overlap the accepted cumulative patch or another original authority');
          if (last && last[1] === run[0] && last[2] === run[2]) last[1] = run[1]; else merged.push(run);
        }
        return {y, runs: merged};
      });
    };
    for (const {candidate, added} of candidates)
      need(same(union([candidate]), union(added.map(row => ({rows: row.native_rows})))), 'Modern ledger intervals differ from original patch');
    const patchRows = union([priorPatch, ...candidates.map(value => value.candidate)]);
    const effective = {...envelope.effective_reference, id: config.effective_release_id,
      footprints_sha256: digest(jsonBytes({domain: 'worldatlas-effective-native-footprints:v2', base_reference: envelope.base_reference,
        authority_registry_sha256: ledger.authority_registry_sha256, ledger_sha256: digest(ledgerRaw), components: [...normalized.rows.values()]}))};
    const patch = {...priorPatch, authority_registry_sha256: ledger.authority_registry_sha256, ledger_sha256: digest(ledgerRaw),
      effective_reference: effective, rows: patchRows}, patchRaw = jsonBytes(patch);
    const nextEnvelope = {...envelope, effective_reference: effective,
      ledger: {...envelope.ledger, bytes: ledgerRaw.length, sha256: digest(ledgerRaw)},
      patch: {...envelope.patch, bytes: patchRaw.length, sha256: digest(patchRaw)}};
    const products = {'authority-registry.json': jsonBytes(registry), 'selected-ledger.json': ledgerRaw, 'patch.json': patchRaw,
      'runtime-envelope.json': jsonBytes(wrapped.additiveRelease ? {...wrapped, reference_release: effective, additiveRelease: nextEnvelope} : nextEnvelope)};
    return products;
  }
  const registries = config.registries.map(p => reader.json(p));
  need(registries.length && registries.every(r => r.version === 1 && r.kind === 'retained-rule-authority-registry-v1'), 'Existing retained registries required');
  const entries = new Map();
  for (const registry of registries) for (const entry of registry.entries) {
    need(!entries.has(entry.authority_sha256) || same(entries.get(entry.authority_sha256), entry), 'Conflicting retained authority');
    entries.set(entry.authority_sha256, entry);
  }
  const registry = {version: 1, kind: 'retained-rule-authority-registry-v1', entries: [...entries.values()].sort((a, b) => a.authority_sha256.localeCompare(b.authority_sha256))};
  const members = config.ledgers.map(pin => {
    const original = reader.json(pin);
    need(original.version === 1 && unique(original.scope_ids) && same(original.scope_ids, original.rows?.map(row => row.component_id)),
      'Original complete ledger roster mismatch');
    // Native outputs retain accepted handoff order. The existing composer uses
    // canonical component order. Preserve every raw row and the original pin;
    // only this in-memory view is ordered for its existing validator.
    const rows = [...original.rows].sort((a, b) => a.component_id.localeCompare(b.component_id));
    return {...original, rows, scope_ids: rows.map(row => row.component_id)};
  });
  const ledger = composeRetainedLedgers(members, registry);
  return {'authority-registry.json': jsonBytes(registry), 'composed-original-ledger.json': jsonBytes(ledger)};
}

export function packageProjection(config, reader, acceptedRegistry = null) {
  const registry = reader.json(config.registry), ledger = reader.json(config.ledger);
  const normalized = normaliseRetainedRepairLedger(ledger, registry);
  const roles = new Map();
  function add(pin, role) {
    need(pin && safe(pin.path), 'Missing whole consumed package role: ' + role);
    reader.read(pin); const prior = roles.get(pin.path);
    need(!prior || prior.sha256 === pin.sha256 && prior.bytes === pin.bytes, 'Conflicting package path vintages');
    if (!prior) roles.set(pin.path, {...pin, roles: []});
    if (!roles.get(pin.path).roles.includes(role)) roles.get(pin.path).roles.push(role);
  }
  need(safe(config.new_prefix.slice(0, -1)) && config.new_prefix.endsWith('/'), 'Explicit new authority prefix required');
  // Finalize supplies the registry authenticated through the original selector.
  // Standalone package and initial legacy finalization retain prefix selection.
  let incoming = registry.entries.filter(e => e.source_authority.path.startsWith(config.new_prefix));
  if (acceptedRegistry !== null) {
    need(acceptedRegistry?.version === 1 && acceptedRegistry.kind === 'retained-rule-authority-registry-v1'
      && Array.isArray(acceptedRegistry.entries) && acceptedRegistry.entries.length > 0,
    'Complete accepted authority registry required');
    const inherited = new Set();
    for (const entry of acceptedRegistry.entries) {
      need(hex(entry?.authority_sha256, 64) && !inherited.has(entry.authority_sha256), 'Duplicate or invalid accepted authority identity');
      inherited.add(entry.authority_sha256);
      need(same(normalized.authorities.get(entry.authority_sha256) ?? null, entry), 'Inherited authority removed or changed');
    }
    incoming = registry.entries.filter(entry => !inherited.has(entry.authority_sha256));
  }
  let added = 0;
  for (const entry of incoming) {
    added++; add(entry.rule_preimage, 'authority rule preimage'); add(entry.source_authority, 'authority binding');
    const binding = reader.json(entry.source_authority);
    if (binding.kind === 'source-target-native-custody-v1') {
      const preimage = reader.json(entry.rule_preimage);
      need(binding.version === 1 && same(Object.keys(binding).sort(), ['kind', 'native_patch', 'source_evidence', 'version'])
        && same(preimage, {...binding, kind: 'source-target-native-rule-v1'}), 'Source-target authority inputs differ');
      add(binding.source_evidence, 'original source evidence'); add(binding.native_patch, 'original native patch');
      const evidence = reader.json(binding.source_evidence);
      need((evidence.version === 1 && evidence.kind === 'source-target-native-evidence-v1'
        || evidence.version === 2 && evidence.kind === 'source-target-native-evidence-v2')
        && Array.isArray(evidence.targets) && evidence.targets.length > 0
        && Array.isArray(evidence.families) && evidence.families.length > 0, 'Missing source-target evidence roles');
      // Closed whole-body read roles of qualifySourceTargetNativeAuthority. Its
      // physical reproducer is authenticated, never executed here; nested GIS
      // operands/native contracts are not a recursive package declaration.
      for (const role of ['catalogue', 'physical_input', 'physical_reproduction', 'physical_evidence', 'native_latitudes', 'owner_roster'])
        add(evidence[role], 'source-target ' + role);
      if (evidence.version === 2) {
        const pin = evidence.dated_land_support;
        add(pin, 'source-target dated land support');
        let raw = reader.read(pin);
        if (pin.decoded_bytes !== undefined) {
          need(Number.isSafeInteger(pin.decoded_bytes) && pin.decoded_bytes > 0
            && hex(pin.decoded_sha256, 64), 'Decoded dated support identity required');
          raw = gunzipSync(raw, {maxOutputLength: pin.decoded_bytes});
          need(raw.length === pin.decoded_bytes && digest(raw) === pin.decoded_sha256,
            'Decoded dated support identity differs');
        }
        const support = JSON.parse(raw);
        need(support.version === 1 && support.kind === 'adopted-dated-native-centre-land-support-v1'
          && Array.isArray(support.provenance) && support.provenance.length > 0,
        'Missing dated support provenance roles');
        for (const provenance of support.provenance) {
          need(['adoption', 'review', 'observation', 'frame'].includes(provenance?.role),
            'Unknown dated support provenance role');
          add(provenance.pin, 'source-target dated ' + provenance.role);
        }
      }
      for (const family of evidence.families) {
        need(typeof family.source_id === 'string' && family.source_id && Array.isArray(family.parts)
          && family.parts.length > 0, 'Missing complete source family roles');
        for (const pin of family.parts) add(pin, 'source-target source family part');
      }
      if (evidence.source_membership !== undefined) {
        const membership = evidence.source_membership;
        need(membership && same(Object.keys(membership).sort(), ['index', 'lineage', 'parts'])
          && Array.isArray(membership.parts) && membership.parts.length > 0, 'Missing accepted source membership roles');
        add(membership.index, 'source-target membership index'); add(membership.lineage, 'source-target membership lineage');
        for (const pin of membership.parts) add(pin, 'source-target membership part');
      }
      continue;
    }
    for (const [role, pin] of Object.entries(binding.original_pins)) add(pin, 'original ' + role);
    for (const role of ['publication', 'inventory', 'operating']) add(binding.native_proof[role], 'native ' + role);
    for (const pin of binding.native_proof.assets) add(pin, 'native emitted asset');
    const aliases = new Map((binding.source_output_aliases ?? []).map(a => [a.original.path, a.published]));
    need(aliases.size === (binding.source_output_aliases ?? []).length, 'Duplicate source alias');
    for (const pin of aliases.values()) add(pin, 'source publication alias');
    const native = reader.json(binding.original_pins.native_request).additive;
    for (const key of ['publication_path', 'inventory_path', 'operating_path']) {
      const matches = native.inputs.filter(p => p.path === native[key]); need(matches.length === 1, 'Missing/ambiguous qualified source role');
      add(aliases.get(matches[0].path) ?? matches[0], 'qualified source ' + key);
    }
  }
  add(config.registry, 'composed registry'); add(config.ledger, 'composed ledger');
  if (config.rebind) {
    add(config.rebind, 'current rebind certificate'); const certificate = reader.json(config.rebind);
    for (const role of ['request', 'facts', 'publication', 'result', 'operating']) add(certificate[role], 'current rebind ' + role);
    for (const [role, pin] of Object.entries(reader.json(certificate.operating).execution_custody)) add(pin, 'current external ' + role);
  }
  const cohorts = registry.entries.map(entry => {
    const rows = [...normalized.rows.values()].filter(row => row.authority_sha256 === entry.authority_sha256);
    return {original_batch_id: 'retained-authority-scope:' + entry.authority_sha256, component_ids: rows.map(row => row.component_id),
      members: rows.map(row => ({component_id: row.component_id, target_id: row.target_id, disposition: row.disposition,
        ...(row.representation === 'native-cells' ? {native_rows_sha256: digest(jsonBytes(row.native_rows))}
          : {geometry_sha256: row.geometry_sha256})}))};
  }).filter(c => c.members.length);
  const expectation = {version: 1, selected_ledger_sha256: null,
    cumulative_native_cells: [...normalized.rows.values()].reduce((sum, row) => sum + row.native_cells, 0), cohorts};
  if (config.selected_ledger) {
    const selected = reader.json(config.selected_ledger);
    need(same(selected.rows, ledger.rows) && same(selected.scope_ids, ledger.scope_ids)
      && selected.authority_registry_sha256 === ledger.authority_registry_sha256 && selected.current_rebind && selected.current_targets,
    'Actual selected ledger does not conserve original rows/current rebind');
    expectation.selected_ledger_sha256 = config.selected_ledger.sha256; add(config.selected_ledger, 'actual selected ledger');
  }
  for (const pin of config.outer_roles ?? []) add(pin, 'explicit final reader outer role');
  const projection = {version: 1, kind: 'prospective-fixed-role-package-projection', new_authorities: added,
    paths: [...roles.values()].sort((a, b) => a.path.localeCompare(b.path)),
    pending: ['Compare actual completed selected-reader inventory, preserving prior declarations; run real package/consumer checks.',
      ...(!config.selected_ledger ? ['Actual selected ledger and outer release/custody pins remain pending.'] : [])],
    limits: ['Fixed consumed metadata roles only; no recursive scientific/preparation inputs. This does not certify reader/build success or delivery.']};
  return {'package-roles.json': jsonBytes(projection), 'selected-delivery-expectations.json': jsonBytes(expectation)};
}

const orderedBytes = value => Buffer.from(JSON.stringify(value, null, 2) + '\n');

export function finalizedSelection(originalRaw, sidecar, pin) {
  const selection = JSON.parse(originalRaw), base = {...selection}; delete base.additive_release;
  need(selection.version === 1 && sidecar.version === 2 && sidecar.kind === 'retained-native-additive-selection-v2'
    && same(sidecar.base_selection, base), 'Final sidecar must preserve the complete original base selection');
  const reference = {path: pin.path, bytes: pin.bytes, sha256: pin.sha256};
  // The selected consumer compares some nested metadata with JSON.stringify.
  // Keep original key insertion order, including selected_geography, and leave
  // an already-finalized body's whitespace untouched on repeated preparation.
  if (same(selection.additive_release, reference)) return originalRaw;
  selection.additive_release = reference;
  const after = {...selection}; delete after.additive_release;
  need(JSON.stringify(after) === JSON.stringify(base), 'Unchanged selector insertion order differs');
  return orderedBytes(selection);
}

export function finalizedPackageInputs(original, prefix, paths) {
  validatePackageInputs(original);
  need(safe(prefix.slice(0, -1)) && prefix.endsWith('/') && original.version === 1
    && unique(original.inputs) && unique(paths) && paths.every(p => safe(p) && p.startsWith(prefix)), 'Exact owned package paths required');
  return appendPackageReadPaths(original, paths);
}

function appendPackageReadPaths(original, paths) {
  validatePackageInputs(original);
  need(unique(paths) && paths.every(safe), 'Exact package read paths required');
  // Preserve the complete accepted declaration prefix. Already-covered roles
  // need no redundant narrower declaration beneath an accepted directory.
  const additions = paths.filter(p => !original.inputs.some(old => old === p || old.endsWith('/') && p.startsWith(old))).sort();
  return validatePackageInputs({...original, inputs: [...original.inputs, ...additions]});
}

// The modern composer emits these four flat products at one real commit.
// Resolve their ordinary whole-file identities once; the existing finalizer
// still checks every registry/ledger/rebind/patch/envelope join and package role.
export function resolveFinalizeConfig(config, reader) {
  if (!Object.hasOwn(config, 'composition')) return config;
  const keys = ['version', 'selector', 'package_inputs', 'composition', 'rebind',
    'preparation_allowance', 'new_prefix', 'sidecar_output'];
  need(config.version === 1 && same(Object.keys(config).filter(key => key !== 'restored_read_roles').sort(), keys.sort()),
    'Compact finalization requires exact locators and cannot mix full pins or an existing sidecar');
  need(config.composition?.path && path.posix.basename(config.composition.path) === 'selected-ledger.json',
    'Modern composition requires the committed selected-ledger.json product');
  const selected = locate(reader, config.composition), prefix = path.posix.dirname(selected.path);
  const sibling = name => locate(reader, {commit: selected.commit, path: prefix + '/' + name});
  const {composition, ...original} = config;
  return {...original, selector: locate(reader, config.selector), package_inputs: locate(reader, config.package_inputs),
    rebind: locate(reader, config.rebind), registry: sibling('authority-registry.json'),
    ledger: selected, selected_ledger: selected, patch: sibling('patch.json'), runtime_envelope: sibling('runtime-envelope.json')};
}

export function finalizeDelivery(config, reader) {
  config = resolveFinalizeConfig(config, reader);
  need(typeof config.new_prefix === 'string' && config.new_prefix.endsWith('/')
    && safe(config.new_prefix.slice(0, -1)), 'Exact owned output prefix required');
  const originalSelector = reader.read(config.selector), selection = JSON.parse(originalSelector);
  let generatedSidecar, prior, acceptedRegistry = null;
  if (selection.additive_release !== undefined || config.sidecar_output !== undefined) {
    const hook = selection.additive_release;
    need(hook && safe(hook.path), 'Original cumulative selector hook required');
    const priorPin = reader.pin(config.selector.commit, hook.path);
    need(priorPin.bytes === hook.bytes && priorPin.sha256 === hook.sha256, 'Original selected sidecar differs');
    prior = reader.json(priorPin);
    const base = {...selection}; delete base.additive_release;
    need(prior.version === 2 && prior.kind === 'retained-native-additive-selection-v2' && same(prior.base_selection, base),
      'Original selected base differs');
    const pin = prior.authority_registry;
    need(pin && Number.isSafeInteger(pin.bytes) && pin.bytes > 0 ,
      'Complete accepted registry pin required');
    // Authenticate the complete accepted registry before parsing.

    acceptedRegistry = reader.json(pin);
  }
  if (config.sidecar_output !== undefined) {
    need(!config.sidecar && safe(config.sidecar_output) && path.posix.dirname(config.sidecar_output) + '/' === config.new_prefix
      && !['ownership-selection.json', 'package-inputs.json', 'package-roles.json', 'selected-delivery-expectations.json', 'preparation.json']
        .includes(path.posix.basename(config.sidecar_output)) && config.patch && config.runtime_envelope,
    'Fresh flat owned sidecar output and committed patch/envelope required');
    generatedSidecar = jsonBytes({...prior, authority_registry: config.registry, runtime_envelope: config.runtime_envelope,
      logical_asset_map: {...prior.logical_asset_map, ledger: config.selected_ledger, patch: config.patch}});
    // This is a generated output identity, never a fabricated future input pin.
    const sidecar = {path: config.sidecar_output, mode: '100644', bytes: generatedSidecar.length, sha256: digest(generatedSidecar),
      git_blob_oid: createHash('sha1').update('blob ' + generatedSidecar.length + '\0').update(generatedSidecar).digest('hex')};
    const head = reader.git('rev-parse', 'HEAD').toString().trim();
    if (reader.hasPath(head, sidecar.path)) {
      const existing = reader.pin(head, sidecar.path);
      need(existing.mode === sidecar.mode && existing.git_blob_oid === sidecar.git_blob_oid && existing.bytes === sidecar.bytes
        && existing.sha256 === sidecar.sha256, 'Generated sidecar would replace an existing committed body');
    }
    config = {...config, sidecar};
  }
  need(config.selector?.path === 'data/ownership-selection.json' && config.package_inputs?.path === '.github/package-inputs.json'
    && config.sidecar?.path.startsWith(config.new_prefix) && config.selected_ledger && config.rebind && !config.outer_roles,
  'Finalization requires original selector/package, actual sidecar/ledger/rebind and derived outer roles');
  const sidecar = generatedSidecar ? JSON.parse(generatedSidecar) : reader.json(config.sidecar), assets = sidecar.logical_asset_map;
  need(same(Object.keys(sidecar).sort(), ['authority_registry', 'base_selection', 'kind', 'logical_asset_map', 'runtime_envelope', 'version'])
    && assets && same(Object.keys(assets).sort(), ['base_manifest', 'ledger', 'owner_roster', 'patch'])
    && same(sidecar.authority_registry, config.registry) && same(assets.ledger, config.selected_ledger), 'Final sidecar authority/selected-ledger pins differ');
  need(assets.base_manifest.sha256 === selection.sha256, 'Final base manifest differs from unchanged selector');
  const baseManifest = reader.json(assets.base_manifest);
  need(assets.owner_roster.sha256 === baseManifest.original_assets?.bounds?.sha256, 'Final owner roster differs from original native bounds');
  reader.read(assets.owner_roster); // Authenticate the retained encoded alias; no decoding or graph computation.
  const selected = reader.json(config.selected_ledger), patch = reader.json(assets.patch);
  const wrapped = reader.json(sidecar.runtime_envelope), envelope = wrapped.additiveRelease ?? wrapped;
  need(typeof selection.release_id === 'string' && baseManifest.geographic_release === selection.release_id
    && hex(baseManifest.footprints_sha256, 64) && hex(baseManifest.hierarchy_sha256, 64)
    && same(envelope.base_reference, {id: selection.release_id, footprints_sha256: baseManifest.footprints_sha256,
      hierarchy_sha256: baseManifest.hierarchy_sha256}), 'Final release baseline differs from original selector/native manifest');
  need(same(selected.current_rebind, config.rebind) && patch.ledger_sha256 === config.selected_ledger.sha256
    && patch.authority_registry_sha256 === config.registry.sha256 && same(patch.base_reference, envelope.base_reference)
    && same(patch.effective_reference, envelope.effective_reference), 'Final release metadata joins differ');
  for (const [role, pin] of Object.entries(assets)) {
    const declared = envelope[role];
    need(declared?.bytes === pin.bytes && declared?.sha256 === pin.sha256
      && (declared.decoded_bytes ?? declared.bytes) === (pin.decoded_bytes ?? pin.bytes)
      && (declared.decoded_sha256 ?? declared.sha256) === (pin.decoded_sha256 ?? pin.sha256), 'Final envelope asset descriptor differs: ' + role);
  }
  const selector = finalizedSelection(originalSelector, sidecar, config.sidecar);
  const outputs = packageProjection({...config, outer_roles: [...Object.values(assets), sidecar.runtime_envelope,
    ...(!generatedSidecar ? [config.sidecar] : [])]}, reader, acceptedRegistry);
  const projection = JSON.parse(outputs['package-roles.json']);
  if (generatedSidecar) {
    projection.paths.push({...config.sidecar, roles: ['generated final sidecar']});
    projection.paths.sort((a, b) => a.path.localeCompare(b.path));
    outputs['package-roles.json'] = jsonBytes(projection);
    outputs[path.posix.basename(config.sidecar.path)] = generatedSidecar;
  }
  const paths = projection.paths.map(p => p.path);
  const baselinePackage = reader.json(config.package_inputs);
  validatePackageInputs(baselinePackage);
  const covered = name => baselinePackage.inputs.some(p => p === name || p.endsWith('/') && name.startsWith(p));
  // This is a closed consumed-role traversal, never caller-granted write scope.
  // Absent historical roles require an exact committed restoration snapshot.
  // Finalization never emits a second copy of original role bodies.
  // Ordinary issue/PR guards separately authorize adoption into the repository.
  const restored = config.restored_read_roles;
  if (restored) need(same(Object.keys(restored).sort(), ['commit', 'paths'])
    && hex(restored.commit, 40) && unique(restored.paths) && restored.paths.every(safe)
    && typeof reader.hasPath === 'function', 'Exact committed restored read-role inventory required');
  const requested = new Set(restored?.paths ?? []), matched = new Set(), conflicts = [];
  const identity = (a, b) => a.mode === '100644' && a.mode === b.mode
    && (a.git_blob_oid ?? a.blob) === (b.git_blob_oid ?? b.blob)
    && a.bytes === b.bytes && a.sha256 === b.sha256;
  for (const pin of projection.paths.filter(p => !p.path.startsWith(config.new_prefix) || covered(p.path))) {
    try {
      const missing = typeof reader.hasPath === 'function' && !reader.hasPath(config.package_inputs.commit, pin.path);
      if (missing && requested.has(pin.path)) {
        const snapshot = reader.pin(restored.commit, pin.path);
        need(identity(snapshot, pin), 'Restored snapshot differs from original consumed role');
        matched.add(pin.path);
      } else {
        const original = reader.pin(config.package_inputs.commit, pin.path);
        need(identity(original, pin), 'Original consumed role differs from accepted path');
        need(!requested.has(pin.path), 'Restoration would overwrite an existing accepted path');
      }
    } catch (error) { conflicts.push({path: pin.path, reason: error.message}); }
  }
  for (const name of requested) if (!matched.has(name) && !conflicts.some(row => row.path === name))
    conflicts.push({path: name, reason: 'Unbound or non-restorable role in restoration inventory'});
  need(!conflicts.length, 'Final package role conflicts with accepted path identity: ' + JSON.stringify(conflicts));
  const packageInputs = appendPackageReadPaths(baselinePackage, paths);
  const expectation = JSON.parse(outputs['selected-delivery-expectations.json']);
  // Preserve the established final smoke-expectation presentation as well.
  const expectations = {version: expectation.version, selected_ledger_sha256: expectation.selected_ledger_sha256,
    cumulative_native_cells: expectation.cumulative_native_cells, cohorts: expectation.cohorts.map(c => ({original_batch_id: c.original_batch_id,
      component_ids: c.component_ids, members: c.members.map(m => ({component_id: m.component_id, target_id: m.target_id,
        disposition: m.disposition, ...(Object.hasOwn(m, 'native_rows_sha256')
          ? {native_rows_sha256: m.native_rows_sha256} : {geometry_sha256: m.geometry_sha256})}))}))};
  return {...outputs, 'ownership-selection.json': selector, 'package-inputs.json': orderedBytes(packageInputs),
    'selected-delivery-expectations.json': orderedBytes(expectations)};
}

const physicalProducts = ['whole-target-support.json', 'execution-receipt.json'];
const sourceProducts = ['original-stage-inputs.json', 'cohort-intervals.json', 'cohort-config.json',
  'source-qualification.json', 'execution-receipt.json'];
function sourceBinding(raw, phase = 'source') {
  return {phase, config_sha256: digest(raw),
    program_sha256: digest(fs.readFileSync(fileURLToPath(new URL('./qualify-source-cohort.py', import.meta.url)))),
    entry_sha256: digest(fs.readFileSync(fileURLToPath(import.meta.url)))};
}
// Reuse complete local original output without repeating scientific operators.
// This validates retained custody; it does not create new scientific authority.
export function resumeSource(root, destination, config, binding, reader) {
  const physical = binding.phase === 'physical', phaseConfig = config[physical ? 'physical' : 'source'];
  const names = physical ? physicalProducts : sourceProducts;
  const receipt = JSON.parse(ordinary(root, destination + '/preparation.json'));
  need(receipt.version === 1 && same(receipt.binding, binding) &&
    same(Object.keys(receipt.outputs ?? {}).sort(), [...names].sort()), 'Source resume configuration/code/inventory differs');
  const products = {};
  for (const name of names) {
    const raw = ordinary(root, destination + '/' + name), pin = receipt.outputs[name];
    need(pin.bytes === raw.length && pin.sha256 === digest(raw), 'Source resumed product changed: ' + name);
    products[name] = raw;
  }
  need(Array.isArray(phaseConfig?.inputs) && phaseConfig.inputs.length > 0, 'Source resume needs original input inventory');
  for (const pin of [...phaseConfig.inputs, ...(physical ? [] : [phaseConfig.physical_reproducer])]) reader.read({...pin, mode: '100644'});
  const execution = JSON.parse(products['execution-receipt.json']);
  const qualified = physical ? execution : JSON.parse(products['source-qualification.json']);
  need(execution.complete === true && execution.program?.sha256 === binding.program_sha256 &&
    qualified.fresh_admission?.config_sha256 === digest(jsonBytes(phaseConfig)), 'Source original execution binding differs');
  need(Array.isArray(execution.outputs) && execution.outputs.length === names.length - 1 &&
    same(execution.outputs.map(pin => pin.path).sort(), names.filter(name => name !== 'execution-receipt.json')
      .map(name => destination + '/' + name).sort()), 'Source original output roster differs');
  for (const pin of execution.outputs) {
    const raw = products[pin.path.slice(destination.length + 1)];
    need(raw && raw.length === pin.bytes && digest(raw) === pin.sha256, 'Source original execution product differs');
  }
  return publish(root, destination, products, binding, true);
}

// The source probe has one data-configured scientific implementation. Admission
// and exclusive publication stay in this existing delivery entry point.
export async function sourceCohort(config, reader, root, destination, phase = 'source') {
  need(['source', 'physical'].includes(phase), 'Unknown scientific delivery phase');
  const phaseConfig = config[phase];
  need(same(Object.keys(config).filter(key => !['preparation_allowance','processing_allowance'].includes(key)).sort(),
    ['runtime_inventory', phase, 'version'].sort()) && config.version === 1 && phaseConfig?.version === 1,
    'Explicit source configuration and runtime inventory required');
  const runtime = config.runtime_inventory;
  need(runtime && same(Object.keys(runtime).sort(), ['files', 'python']) && Array.isArray(runtime.files)
    && runtime.files.length > 0 && unique(runtime.files.map(pin => pin.path))
    && runtime.python?.bytes > 0 && runtime.files.some(pin => same(pin, runtime.python)), 'Complete pinned source runtime inventory required');
  for (const pin of runtime.files) {
    need(pin && same(Object.keys(pin).sort(), ['bytes', 'path', 'sha256']) && path.isAbsolute(pin.path)
      && Number.isSafeInteger(pin.bytes) && pin.bytes >= 0 && hex(pin.sha256, 64), 'Ordinary installed runtime pin required');
  }
  const helper = fileURLToPath(new URL('./qualify-source-cohort.py', import.meta.url));
  const helperRaw = fs.readFileSync(helper), sourceRaw = jsonBytes(phaseConfig);
  const runtimeIdentity = pin => {
    const resolved = fs.realpathSync(pin.path), before = fs.statSync(resolved);
    need(before.isFile() && before.size === pin.bytes, 'Installed source runtime size differs');
    const hash = createHash('sha256'), chunk = Buffer.alloc(1048576), fd = fs.openSync(resolved, 'r');
    let bytes = 0;
    try { for (let n; (n = fs.readSync(fd, chunk, 0, chunk.length, null));) { bytes += n; hash.update(chunk.subarray(0, n)); } }
    finally { fs.closeSync(fd); }
    const after = fs.statSync(resolved);
    need(bytes === pin.bytes && hash.digest('hex') === pin.sha256 && fs.realpathSync(pin.path) === resolved
      && ['dev', 'ino', 'size', 'mtimeMs', 'ctimeMs'].every(key => before[key] === after[key]), 'Installed source runtime identity differs');
    return {path: pin.path, resolved, bytes, sha256: pin.sha256};
  };
  const identities = runtime.files.map(runtimeIdentity);
  const stagingParent = '.cache/delivery-handoff';
  admitDestination(root, stagingParent + '/source-staging', false);
  fs.mkdirSync(path.join(root, stagingParent), {recursive: true});
  const staging = fs.mkdtempSync(path.join(root, stagingParent, 'source-'));
  const stagingIdentity = [];
  for (let current = staging;; current = path.dirname(current)) {
    const stat = fs.lstatSync(current);
    need(stat.isDirectory() && fs.realpathSync(current) === current, 'Nonordinary producer staging ancestor');
    stagingIdentity.push({path: current, dev: stat.dev, ino: stat.ino});
    if (current === root) break;
    need(current.startsWith(root + path.sep), 'Producer staging escaped owned root');
  }
  const discardStaging = () => {
    for (const identity of stagingIdentity) {
      const stat = fs.lstatSync(identity.path, {throwIfNoEntry: false});
      need(stat?.isDirectory() && fs.realpathSync(identity.path) === identity.path
        && stat.dev === identity.dev && stat.ino === identity.ino,
      'Producer staging identity changed; cleanup refused at ' + identity.path);
    }
    fs.rmSync(staging, {recursive: true, force: true});
  };
  let completed = false;
  try {
    const sourceFile = path.join(staging, 'source-config.json'), admissionFile = path.join(staging, 'admission.json');
    const admission = {version: 1, program_sha256: digest(helperRaw), config_sha256: digest(sourceRaw), runtime_files: runtime.files};
    fs.writeFileSync(sourceFile, sourceRaw, {flag: 'wx'});
    fs.writeFileSync(admissionFile, jsonBytes(admission), {flag: 'wx'});
    const output = path.join(staging, 'products'), started = performance.now();
    // Python owns cooperative feature/input/time/output checks. This entry does
    // not claim a hard deadline or process-tree supervisor it does not implement.
    execFileSync(runtime.python.path, ['-I', '-B', helper, '--phase', phase, '--repo', root, '--config', sourceFile,
      '--admission', admissionFile, '--output', output, '--publication-prefix', destination], {cwd: root, env: environment(),
      stdio: ['ignore', 'ignore', 'pipe'], maxBuffer: 131072});
    for (const pin of runtime.files) runtimeIdentity(pin);
    need(fs.readFileSync(helper).equals(helperRaw), 'Source helper changed during execution');
    const names = phase === 'source' ? sourceProducts : physicalProducts;
    need(same(fs.readdirSync(output).sort(), [...names].sort()), 'Incomplete or foreign source output inventory');
    const products = Object.fromEntries(names.map(name => [name, ordinary(root, path.relative(root, path.join(output, name)))]));
    completed = true;
    return {products, retained_staging: path.relative(root, staging),
      discard_staging: discardStaging,
      observation: {elapsed_seconds: (performance.now() - started) / 1000,
      runtime_inventory: identities, limits: ['Scientific checks are cooperative boundaries, not hard process-tree enforcement.',
        phase === 'physical' ? 'Original physical source-relative support is not native, owner-zero, factual or selected-output acceptance.'
          : 'Source prerequisites are not physical, native, owner-zero or selected-output acceptance.']}};
  } finally { if (!completed) discardStaging(); }
}

// Completed producer bodies remain available if the existing outer writer refuses.
// This is not a completed outer publication or an automatic replay/resume route.
export function publishCompletedSource(root, destination, result, binding, resume, reader) {
  let publication;
  try { publication = publish(root, destination, result.products, binding, resume); }
  catch (error) {
    throw new Error(error.message + '; completed producer staging retained at ' + result.retained_staging
      + '; outer publication incomplete', {cause: error});
  }
  try { result.discard_staging(); }
  catch (error) {
    throw new Error('Outer publication complete at ' + destination + '; producer staging cleanup failed: ' + error.message, {cause: error});
  }
  return publication;
}

// Fill only the accepted baseline block of ordinary source evidence. Scientific
// claims stay explicit; this metadata preparation does not qualify their support.
// In particular, the normative manifest descriptor is not a Git custody pin.
export async function sourceEvidence(config, reader) {
  need(config.version === 1 && (config.source_evidence?.version === 1
    && config.source_evidence.kind === 'source-target-native-evidence-v1'
    || config.source_evidence?.version === 2 && config.source_evidence.kind === 'source-target-native-evidence-v2'),
  'Explicit ordinary source evidence required');
  if (config.source_evidence.version === 2) reader.read(config.source_evidence.dated_land_support);
  const {locate} = await import('./delivery-handoff-advance.mjs');
  const selectorPin = locate(reader, config.selector);
  need(selectorPin.path === 'data/ownership-selection.json', 'Original accepted selector locator required');
  const selection = reader.json(selectorPin), hook = selection.additive_release;
  need(hook && same(Object.keys(hook).sort(), ['bytes', 'path', 'sha256']), 'Existing cumulative selection required');
  const sidecarPin = reader.pin(selectorPin.commit, hook.path);
  need(sidecarPin.bytes === hook.bytes && sidecarPin.sha256 === hook.sha256, 'Original selected sidecar differs');
  const sidecar = reader.json(sidecarPin), base = {...selection}; delete base.additive_release;
  need(sidecar.version === 2 && sidecar.kind === 'retained-native-additive-selection-v2'
    && same(sidecar.base_selection, base), 'Original selected base differs');
  const assets = sidecar.logical_asset_map;
  need(assets && same(Object.keys(assets).sort(), ['base_manifest', 'ledger', 'owner_roster', 'patch']),
    'Complete prior logical assets required');
  const wrapped = reader.json(sidecar.runtime_envelope), envelope = wrapped.additiveRelease ?? wrapped;
  need(envelope.version === 2 && envelope.kind === 'retained-native-base-plus-delta-v2', 'Existing v2 runtime envelope required');
  for (const [role, pin] of Object.entries(assets)) {
    const declared = envelope[role];
    need(declared?.bytes === pin.bytes && declared?.sha256 === pin.sha256
      && (declared.decoded_bytes ?? declared.bytes) === (pin.decoded_bytes ?? pin.bytes)
      && (declared.decoded_sha256 ?? declared.sha256) === (pin.decoded_sha256 ?? pin.sha256),
    'Prior envelope asset binding differs: ' + role);
  }
  const manifest = reader.json(assets.base_manifest);
  const selectedManifest = reader.pin(selectorPin.commit, selection.manifest_path);
  need(selectedManifest.sha256 === selection.sha256 && assets.base_manifest.sha256 === selection.sha256
    && selectedManifest.bytes === assets.base_manifest.bytes && selection.method === manifest.method,
  'Original selected native manifest/method differs');
  const contractKeys = ['size', 'coordinateBits', 'method', 'native_latitudes', 'hierarchy_sha256', 'original_assets'];
  need(contractKeys.every(key => Object.hasOwn(manifest, key)), 'Complete original native contract required');
  const native_contract = Object.fromEntries(contractKeys.map(key => [key, manifest[key]]));
  need(same(envelope.base_reference, {id: selection.release_id, footprints_sha256: manifest.footprints_sha256,
    hierarchy_sha256: manifest.hierarchy_sha256}) && manifest.geographic_release === selection.release_id
    && hex(manifest.footprints_sha256, 64) && hex(manifest.hierarchy_sha256, 64),
  'Original selected base reference differs');
  need(assets.owner_roster.sha256 === manifest.original_assets?.bounds?.sha256,
    'Original selected owner asset differs');
  const latitude = manifest.native_latitudes;
  const latitudePin = locate(reader, {commit: latitude.commit, path: latitude.path});
  need(latitudePin.bytes === latitude.bytes && latitudePin.sha256 === latitude.sha256,
    'Original native latitude body differs');
  const native_latitudes = {...latitudePin, decoded_bytes: latitude.decoded_bytes, decoded_sha256: latitude.decoded_sha256};
  // Authenticate both encoded and decoded custody without promoting their Git
  // metadata into the literal normative contract or replaying native science.
  for (const [role, pin] of Object.entries({native_latitudes, owner_roster: assets.owner_roster})) {
    const raw = reader.read(pin);
    need(Number.isSafeInteger(pin.decoded_bytes) && pin.decoded_bytes > 0
      && hex(pin.decoded_sha256, 64), 'Bounded decoded baseline identity required: ' + role);
    const decoded = gunzipSync(raw, {maxOutputLength: pin.decoded_bytes});
    need(decoded.length === pin.decoded_bytes && digest(decoded) === pin.decoded_sha256,
      'Decoded baseline identity differs: ' + role);
  }
  const derived = {native_contract, native_latitudes, owner_roster: assets.owner_roster, base_reference: envelope.base_reference};
  for (const [key, value] of Object.entries(derived))
    need(!Object.hasOwn(config.source_evidence, key) || same(config.source_evidence[key], value),
      'Supplied source evidence changes accepted baseline: ' + key);
  return {'source-evidence.json': jsonBytes({...config.source_evidence, ...derived})};
}

// Execute the existing modern constructor or its admitted read-only diagnostic,
// rather than authoring a country wrapper. Only qualification emits authority.
export async function nativeAuthority(config, reader, root, diagnostic = false) {
  need(typeof diagnostic === 'boolean' && same(Object.keys(config).filter(k=>k!=='preparation_allowance').sort(), ['native_patch', 'source_evidence', 'version'])
    && config.version === 1, 'Explicit native-authority inputs required');
  const flow = await import('./delivery-handoff-advance.mjs');
  const inputs = {source_evidence: config.source_evidence, native_patch: config.native_patch};
  const pins = diagnostic
    ? Object.fromEntries(Object.entries(inputs).map(([role, locator]) => [role, flow.locate(reader, locator)])) : null;
  if (!diagnostic) for (const locator of Object.values(inputs))
    reader.descriptor(locator?.commit, locator?.path);
  const authorityReader = flow.deliveryAuthorityReader(root, reader);
  const started = performance.now();
  let result, products;
  if (diagnostic) {
    const {diagnoseSourceTargetNativeAuthority} = await import('../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs');
    const binding = {version: 1, kind: 'source-target-native-custody-v1', ...pins};
    const preimage = {...binding, kind: 'source-target-native-rule-v1'};
    result = diagnoseSourceTargetNativeAuthority(authorityReader, preimage, binding);
    products = {'native-diagnostic.json': jsonBytes(result)};
  } else {
    result = flow.constructOriginalAuthority(authorityReader, inputs);
    need(Array.isArray(result.ledger_rows) && result.ledger_rows.length > 0
      && same(result.component_ids, result.ledger_rows.map(row => row.component_id)), 'Complete modern constructor rows required');
    products = {...result.products, 'constructor-result.json': jsonBytes({version: 1,
      kind: 'existing-source-target-native-constructor-result', inputs,
      component_ids: result.component_ids, rule_sha256: result.rule_sha256, ledger_rows: result.ledger_rows,
      limitations: result.limitations,
      ...(Object.hasOwn(result,'physical_context_hits') ? {physical_context_hits: result.physical_context_hits} : {})})};
  }
  return {products, observation: {elapsed_seconds: (performance.now() - started) / 1000,
    ...(diagnostic ? {requested_cells: result.requested_cells, supported_cells: result.supported_cells, held_cells: result.held_cells}
      : {qualified_cells: result.ledger_rows.reduce((n, row) => n + row.native_cells, 0)}),
    limits: ['Original source/physical producers are not replayed.', diagnostic
      ? 'Diagnostic screening produces no authority, current-owner-zero or selected-output acceptance.'
      : 'Constructor qualification is not actual current-owner-zero or final selected-output acceptance.']}};
}

async function main(args) {
  const [phase, configFile, destination, ...flags] = args;
  if (phase === 'materialize') {
    need(configFile && destination && flags.every(f => f === '--resume') && flags.length <= 1,
      'Use materialize CONFIG DESTINATION [--resume]');
    need(!process.execArgv.length && !process.env.NODE_OPTIONS?.trim() && !process.env.NODE_PATH?.trim(), 'Plain Node launch required');
    const root = fs.realpathSync(process.cwd()), raw = ordinary(root, configFile), config = JSON.parse(raw);
    need(config.version === 1, 'Explicit materialization configuration required');
    const reader = pinReader(root); const flow = await import('./delivery-handoff-advance.mjs');
    const pin = flow.locate(reader, config.recipe_index), index = reader.json(pin), plan = index.acquisition_plan;
    need(index.version === 1 && plan?.products?.length, 'Completed recipe index with acquisition plan required');
    const products = {'materialized-inputs.json': jsonBytes({version: 1, kind: 'authenticated-delivery-inputs',
      recipe_index: pin, identities: [...new Set(plan.products.map(p => p.identity))], status: 'complete'})};
    const publishComplete = admitPublication(root, destination, products, {phase, config_sha256: digest(raw)}, flags.includes('--resume'));
    const started = performance.now();
    const result = await flow.acquireDeliveryInputs(plan, root, {token: '', execute: flow.deliveryAcquisitionExecute()});
    console.log(JSON.stringify({...publishComplete(), acquisition: result, acquisition_ms: performance.now() - started}));
    return;
  }
  need(['source', 'physical', 'source-evidence', 'native-authority', 'native-diagnostic', 'requests', 'native-requests', 'retain', 'rebind-operating', 'rebind-certificate', 'compose', 'package', 'finalize', 'evidence'].includes(phase) && configFile && destination && flags.every(f => f === '--resume') && flags.length <= 1,
    'Use prepare-delivery-handoff.mjs requests|native-requests|retain|rebind-operating|rebind-certificate|compose|package|finalize|evidence|source|physical|source-evidence|native-authority|native-diagnostic CONFIG DESTINATION [--resume]');
  need(!process.execArgv.length && !process.env.NODE_OPTIONS?.trim() && !process.env.NODE_PATH?.trim(), 'Plain Node launch required');
  const root = fs.realpathSync(process.cwd()); admitDestination(root, destination, flags.includes('--resume'));
  const raw = ordinary(root, configFile), config = JSON.parse(raw), reader = pinReader(root);
  need(config.version === 1, 'Versioned preparation config required');
  const binding = ['source','physical'].includes(phase) ? sourceBinding(raw,phase) : {phase, config_sha256: digest(raw)};
  if (['source','physical'].includes(phase) && flags.includes('--resume') && fs.existsSync(path.join(root, destination))) {
    console.log(JSON.stringify(resumeSource(root, destination, config, binding, reader))); return;
  }
  let outputs, observation;
  if (['source','physical'].includes(phase)) {
    const result = await sourceCohort(config, reader, root, destination, phase);
    console.log(JSON.stringify({...publishCompletedSource(root, destination, result, binding, flags.includes('--resume'), reader), observation: result.observation}));
    return;
  }
  if (['native-authority','native-diagnostic'].includes(phase)) { const result = await nativeAuthority(config, reader, root, phase === 'native-diagnostic'); outputs = result.products; observation = result.observation; }
  if (phase === 'source-evidence') outputs = await sourceEvidence(config, reader);
  if (phase === 'requests') outputs = prepareRequests(config, reader);
  if (phase === 'native-requests') outputs = nativeRequests(config, reader);
  if (phase.startsWith('rebind-')) outputs = rebindCustody(config, reader, phase === 'rebind-certificate');
  if (phase === 'retain') outputs = retainProducts(config, root, reader);
  if (phase === 'compose') outputs = composeAuthorities(config, reader);
  if (phase === 'package') outputs = packageProjection(config, reader);
  if (phase === 'finalize') outputs = finalizeDelivery(config, reader);
  if (phase === 'evidence') outputs = prepareEvidence(config, reader);
  console.log(JSON.stringify({...publish(root, destination, outputs, binding, flags.includes('--resume')), ...(observation ? {observation} : {})}));
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main(process.argv.slice(2)).catch(error => { console.error(error.message); process.exitCode = 1; });
