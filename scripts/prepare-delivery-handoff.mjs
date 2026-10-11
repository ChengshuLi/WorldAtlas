// Metadata-only preparation. Existing operators, source authority, review and
// queue admission remain authoritative. No operator or GitHub write is invoked.
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {gunzipSync} from 'node:zlib';
import {candidateBudget} from './native-ownership/native-preparation-guards.mjs';
import {reviewContractBinding, reviewInventoryCommitment, checkPremergeEvidence} from './premerge-evidence.mjs';
import {githubAPI, githubPages, readClaim, workSpec} from './issue-claim-contract.mjs';
import {composeRetainedLedgers} from '../coordination/engineering/additive-native-gap-batch-20261008/composition-v2/compose-retained.mjs';
import {normaliseRetainedRepairLedger} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';

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
  const budget = candidateBudget([], {reserveBytes: 0, reserveDescriptors: 0}), cache = new Map();
  const git = (...args) => execFileSync('git', args, {cwd: root, env: environment(), maxBuffer: 33554433});
  function descriptor(commit, name) {
    need(hex(commit, 40) && safe(name), 'Exact commit and safe whole-file path required');
    const line = git('ls-tree', '-z', commit, '--', name).toString();
    const match = /^100644 blob ([a-f0-9]{40})\t([^\0]+)\0$/.exec(line);
    need(match && match[2] === name, 'Missing ordinary exact Git body: ' + name);
    const size = Number(git('cat-file', '-s', match[1]).toString());
    need(Number.isSafeInteger(size) && size >= 0 && size <= 33554432, 'Whole body cap: ' + name);
    return {path: name, commit, mode: '100644', git_blob_oid: match[1], bytes: size};
  }
  function read(pin) {
    const actual = descriptor(pin.commit, pin.path);
    need(pin.mode === actual.mode && (pin.git_blob_oid ?? pin.blob) === actual.git_blob_oid
      && pin.bytes === actual.bytes && hex(pin.sha256, 64), 'Whole pin identity differs: ' + pin.path);
    if (!cache.has(actual.git_blob_oid)) {
      budget.add(actual);
      const raw = git('cat-file', 'blob', actual.git_blob_oid);
      need(raw.length === actual.bytes, 'Whole body length changed');
      cache.set(actual.git_blob_oid, raw);
    }
    const raw = cache.get(actual.git_blob_oid);
    need(digest(raw) === pin.sha256, 'Whole body hash differs: ' + pin.path);
    return raw;
  }
  return {git, read, json: pin => JSON.parse(read(pin)), budget,
    pin(commit, name) { const p = descriptor(commit, name);
      if (!cache.has(p.git_blob_oid)) { budget.add(p); cache.set(p.git_blob_oid, git('cat-file', 'blob', p.git_blob_oid)); }
      return {...p, sha256: digest(cache.get(p.git_blob_oid))}; }};
}

function ordinary(root, relative) {
  need(safe(relative), 'Unsafe input path');
  const filename = path.join(root, relative);
  const stat = fs.lstatSync(filename);
  need(stat.isFile() && fs.realpathSync(filename) === filename && stat.size <= 33554432, 'Require bounded ordinary input: ' + relative);
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
export function publish(root, destination, products, binding, resume = false, sharedBudget = null) {
  const target = admitDestination(root, destination, resume);
  const budget = sharedBudget ?? candidateBudget([], {reserveBytes: 0, reserveDescriptors: 0});
  for (const [name, raw] of Object.entries(products)) {
    need(safe(name) && !name.includes('/') && name !== 'preparation.json' && Buffer.isBuffer(raw), 'Plain unique product filenames required');
    budget.add({bytes: raw.length});
  }
  need(Object.keys(products).length > 0, 'No empty completion');
  const outputs = Object.fromEntries(Object.entries(products).map(([name, raw]) => [name, {bytes: raw.length, sha256: digest(raw)}]));
  const receipt = jsonBytes({version: 1, binding, outputs});
  need(receipt.length <= 4096, 'Preparation receipt cap'); budget.add({bytes: receipt.length});
  if (fs.existsSync(target)) {
    need(resume, 'Occupied destination; use explicit --resume to verify an identical completed phase');
    need(same(fs.readdirSync(target).sort(), [...Object.keys(products), 'preparation.json'].sort()), 'Incomplete or foreign resumed output inventory');
    for (const [name, raw] of Object.entries({...products, 'preparation.json': receipt}))
      need(ordinary(root, destination + '/' + name).equals(raw), 'Resumed bytes/binding changed: ' + name);
    return {destination, resumed: true, binding};
  }
  fs.mkdirSync(path.dirname(target), {recursive: true});
  fs.mkdirSync(target);
  for (const [name, raw] of Object.entries({...products, 'preparation.json': receipt})) fs.writeFileSync(path.join(target, name), raw, {flag: 'wx'});
  return {destination, resumed: false, binding};
}

export function prepareRequests(config, reader) {
  const registry = reader.json(config.registry), outputs = {}, index = [], seen = new Set();
  need(registry.version === 1 && registry.kind === 'accepted-administrative-handoffs-v1', 'Existing accepted handoff registry required');
  need(Array.isArray(config.groups) && config.groups.length, 'Explicit finite method/resource groups required');
  for (const group of config.groups) {
    need(/^[a-z0-9-]+$/.test(group.id) && !seen.has(group.id) && unique(group.component_ids), 'Invalid/duplicate request group');
    seen.add(group.id);
    const template = reader.json(group.template), rule = template.source_rule;
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
        output_reserve: template.output_reserve, operating_runtime: template.operating_runtime})),
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

export function retainProducts(config, root, reader) {
  const requestRaw = reader.read(config.request), request = JSON.parse(requestRaw);
  const terminalRaw = ordinary(root, config.terminal), terminal = JSON.parse(terminalRaw); reader.budget.add({bytes: terminalRaw.length});
  const publicationRaw = ordinary(root, config.output + '/publication.json'), publication = JSON.parse(publicationRaw); reader.budget.add({bytes: publicationRaw.length});
  qualifyTerminal(terminal, requestRaw, publicationRaw, request);
  const rows = publication.outputs ? Object.values(publication.outputs) : publication.complete === true
    ? [{path: 'facts.json', ...publication.facts}, {path: 'inventory.jsonl.gz', ...publication.inventory}, ...(publication.assets ?? [])] : [];
  need(rows.length && new Set(rows.map(p => p.path)).size === rows.length, 'Missing/duplicate publication output inventory');
  const outputs = {'request.json': requestRaw, 'terminal.json': terminalRaw, 'publication.json': publicationRaw};
  for (const row of rows) {
    need(safe(row.path) && !row.path.includes('/') && !Object.hasOwn(outputs, row.path), 'Unsafe/duplicate publication path');
    const raw = ordinary(root, config.output + '/' + row.path); reader.budget.add({bytes: raw.length});
    need(raw.length === row.bytes && digest(raw) === row.sha256, 'Incomplete actual publication output: ' + row.path);
    if (row.uncompressed_bytes !== undefined) {
      need(Number.isSafeInteger(row.uncompressed_bytes) && row.uncompressed_bytes <= 33554432, 'Decoded output cap');
      reader.budget.add({bytes: row.uncompressed_bytes}); const decoded = gunzipSync(raw, {maxOutputLength: 33554432});
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
      const raw = ordinary(root, config.custody[role]); reader.budget.add({bytes: raw.length}); outputs[name] = raw;
    }
  } else need(facts.request?.sha256 === digest(requestRaw) && facts.request.bytes === requestRaw.length
    && facts.operation === request.operation, 'Published facts are not joined to the actual terminal request');
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
    reader.read(group.source.inventory);
    need(facts.execution_commit === terminal.execution_commit && facts.request?.sha256 === digest(sourceRaw)
      && same(facts.source_rule, source.source_rule), 'SOURCE facts/terminal/request mismatch');
    const template = reader.json(group.template), additive = template.additive;
    need(template.operation === 'unactivated-additive-native-batch-v1' && additive?.source_profile === source.source_rule.profile
      && same(additive.scope_ids, source.source_rule.expected_ids) && same(template.baseline, source.baseline),
    'Native template method/scope/baseline differs from qualified source');
    need(unique(additive.scope_ids) && additive.scope_ids.every(id => !components.has(id)), 'Overlapping/duplicate native scopes');
    additive.scope_ids.forEach(id => components.add(id));
    need(Number.isSafeInteger(facts.runtime?.bytes) && facts.runtime.bytes > 0 && hex(facts.runtime.sha256, 64), 'Actual SOURCE runtime identity required');
    const changes = {source_request_path: group.source.request, operating_path: group.source.operating,
      publication_path: group.source.publication, facts_path: group.source.facts, inventory_path: group.source.inventory};
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
  const request = reader.json(config.request), terminal = reader.json(config.terminal);
  qualifyTerminal(terminal, reader.read(config.request), reader.read(config.publication), request);
  if (certificate) {
    const operating = reader.json(config.operating);
    need(operating.execution_commit === terminal.execution_commit && operating.request_sha256 === config.request.sha256
      && operating.publication_sha256 === config.publication.sha256, 'Operating/product commit binding differs');
    const publication = reader.json(config.publication);
    need(publication.execution_commit === request.execution_commit && publication.request_sha256 === config.request.sha256,
      'Rebind publication request binding differs');
    for (const role of ['facts', 'result']) {
      reader.read(config[role]); const output = publication.outputs?.[role];
      need(output && output.bytes === config[role].bytes && output.sha256 === config[role].sha256, 'Rebind output pin differs from actual publication');
    }
    return {'certificate.json': jsonBytes({version: 1, kind: 'qualified-native-additive-current-bank-rebind-v1',
      execution_commit: request.execution_commit, base_selection: request.base_selection,
      authority_registry_sha256: request.authority_registry_sha256,
      request: config.request, facts: config.facts, publication: config.publication, result: config.result, operating: config.operating})};
  }
  need(same(Object.keys(config.execution_custody).sort(), ['code_source', 'issued_plan', 'stderr', 'stdout', 'terminal']), 'Complete external execution custody required');
  need(same(config.execution_custody.terminal, config.terminal), 'Custody terminal differs');
  for (const pin of Object.values(config.execution_custody)) reader.read(pin);
  return {'operating.json': jsonBytes({version: 1, kind: 'native-additive-current-bank-rebind-operating-v1',
    execution_commit: terminal.execution_commit, request_sha256: config.request.sha256, publication_sha256: config.publication.sha256,
    exit_code: terminal.exit_code, signal: terminal.signal, owned_processes_remaining: terminal.owned_processes_remaining,
    lifetime_rss_bytes: terminal.lifetime_rss_bytes, elapsed_seconds: terminal.elapsed_seconds, execution_custody: config.execution_custody})};
}

export function composeAuthorities(config, reader) {
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

export function packageProjection(config, reader) {
  const registry = reader.json(config.registry), ledger = reader.json(config.ledger);
  const normalized = normaliseRetainedRepairLedger(ledger, registry);
  const roles = new Map();
  function add(pin, role) {
    reader.read(pin); const prior = roles.get(pin.path);
    need(!prior || prior.sha256 === pin.sha256 && prior.bytes === pin.bytes, 'Conflicting package path vintages');
    if (!prior) roles.set(pin.path, {...pin, roles: []});
    if (!roles.get(pin.path).roles.includes(role)) roles.get(pin.path).roles.push(role);
  }
  need(safe(config.new_prefix.slice(0, -1)) && config.new_prefix.endsWith('/'), 'Explicit new authority prefix required');
  let added = 0;
  for (const entry of registry.entries.filter(e => e.source_authority.path.startsWith(config.new_prefix))) {
    added++; add(entry.rule_preimage, 'authority rule preimage'); add(entry.source_authority, 'authority binding');
    const binding = reader.json(entry.source_authority);
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
      members: rows.map(row => Object.fromEntries(['component_id', 'target_id', 'disposition', 'geometry_sha256'].map(k => [k, row[k]])))};
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

export async function freezeReview({repo, number, expectedHead, api, reader}) {
  need(/^[\w.-]+\/[\w.-]+$/.test(repo) && Number.isSafeInteger(number) && number > 0 && hex(expectedHead, 40), 'Exact PR/repository/head required');
  const route = `/repos/${repo}`, pr = await api(`${route}/pulls/${number}`);
  need(pr.state === 'open' && pr.head.sha === expectedHead, 'Current PR head/state differs');
  const refs = [...pr.body.matchAll(/^(?:Refs|Closes) #(\d+)\s*$/gm)]; need(refs.length === 1, 'Exactly one original issue linkage required');
  const issue = await api(`${route}/issues/${refs[0][1]}`), spec = workSpec(issue.body);
  const claim = readClaim(await githubPages(api, `${route}/issues/${issue.number}/comments`));
  need(claim?.active && claim.branch === pr.head.ref && Date.parse(claim.expires_at) > Date.now(), 'Current exact-branch author claim required');
  const files = await githubPages(api, `${route}/pulls/${number}/files`);
  need(files.length === pr.changed_files && files.length > 0 && new Set(files.map(f => f.filename)).size === files.length, 'Incomplete/duplicate PR file scope');
  const checked = await checkPremergeEvidence({api, repo, pr, issue, reservation: claim, files, review: false});
  need(['bytes-verified', 'limited'].includes(checked.status), 'Current premerge evidence did not pass');
  const manifestPath = spec.evidence_quality.manifest_path.replace('{job}', pr.head.ref.split('/').slice(1).join('/'));
  const manifestPin = reader.pin(expectedHead, manifestPath), manifest = reader.json(manifestPin);
  need(manifestPin.sha256 === checked.manifest_sha256, 'Local/hosted manifest differs');
  const domains = new Set(['implementation']);
  if (spec.evidence_quality.review_kind !== 'code') domains.add(spec.evidence_quality.review_kind);
  if (manifest.sources.length || ['geography', 'source-only', 'content'].includes(manifest.lane)) domains.add('source');
  if (manifest.methods.some(m => m.kind === 'geography') || files.some(f => /(?:hierarchy|world-index|crosswalk|ellipsoidal|geometry)/.test(f.filename))) domains.add('geometry');
  if (files.some(f => /(?:release|migration|identity|regional-approval)/.test(f.filename))) domains.add('release');
  const currentPr = await api(`${route}/pulls/${number}`), currentIssue = await api(`${route}/issues/${issue.number}`);
  const currentClaim = readClaim(await githubPages(api, `${route}/issues/${issue.number}/comments`));
  need(same(currentClaim, claim), 'Author claim changed while freezing');
  need(same([currentPr.head.sha, currentPr.base.sha, currentPr.body, currentPr.changed_files, currentPr.state],
    [pr.head.sha, pr.base.sha, pr.body, pr.changed_files, pr.state]) && same(reviewContractBinding(issue, pr), reviewContractBinding(currentIssue, currentPr)), 'Review head/base/scope/body changed while freezing');
  const packet = {version: 1, kind: 'review-preparation-only', repo, pr_number: number, head_sha: expectedHead, base_sha: pr.base.sha,
    author_worker_id: claim.worker_id, manifest: manifestPin, ...reviewContractBinding(issue, pr),
    inventory_commitment: reviewInventoryCommitment({files, manifest}), required_domains: [...domains].sort(),
    inspected_files: [...new Set(files.flatMap(f => [f.filename, f.previous_filename].filter(Boolean)))].sort(),
    evidence_limits: checked.limits, issue, pr, files,
    next: ['A distinct reviewer must independently inspect this exact head and post the existing worldatlas-review:v1 receipt.',
      'After that review, use the existing queue; re-freeze if head, acceptance, body or file scope changes.'],
    queue_command: ['node', 'scripts/queue-pr-merge.mjs', '--pr', String(number), '--head', expectedHead],
    resume_command: ['node', 'scripts/queue-pr-merge.mjs', '--pr', String(number), '--head', expectedHead, '--request-id', 'ACTUAL_EXISTING_REQUEST_ID', '--observe']};
  return {'review-packet.json': jsonBytes(packet)};
}

async function main(args) {
  const [phase, configFile, destination, ...flags] = args;
  need(['requests', 'native-requests', 'retain', 'rebind-operating', 'rebind-certificate', 'compose', 'package', 'review'].includes(phase) && configFile && destination && flags.every(f => f === '--resume') && flags.length <= 1,
    'Use prepare-delivery-handoff.mjs requests|native-requests|retain|rebind-operating|rebind-certificate|compose|package|review CONFIG DESTINATION [--resume]');
  need(!process.execArgv.length && !process.env.NODE_OPTIONS?.trim() && !process.env.NODE_PATH?.trim(), 'Plain Node launch required');
  const root = fs.realpathSync(process.cwd()); admitDestination(root, destination, flags.includes('--resume'));
  const raw = ordinary(root, configFile), config = JSON.parse(raw), reader = pinReader(root);
  reader.budget.add({bytes: raw.length}); need(config.version === 1, 'Versioned preparation config required');
  let outputs;
  if (phase === 'requests') outputs = prepareRequests(config, reader);
  if (phase === 'native-requests') outputs = nativeRequests(config, reader);
  if (phase.startsWith('rebind-')) outputs = rebindCustody(config, reader, phase === 'rebind-certificate');
  if (phase === 'retain') outputs = retainProducts(config, root, reader);
  if (phase === 'compose') outputs = composeAuthorities(config, reader);
  if (phase === 'package') outputs = packageProjection(config, reader);
  if (phase === 'review') {
    const token = execFileSync('gh', ['auth', 'token'], {encoding: 'utf8', maxBuffer: 16384}).trim();
    outputs = await freezeReview({repo: config.repo, number: config.pr_number, expectedHead: config.head_sha, api: githubAPI(token), reader});
  }
  console.log(JSON.stringify(publish(root, destination, outputs, {phase, config_sha256: digest(raw)}, flags.includes('--resume'), reader.budget)));
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main(process.argv.slice(2)).catch(error => { console.error(error.message); process.exitCode = 1; });
