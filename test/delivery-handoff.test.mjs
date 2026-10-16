import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync, spawnSync} from 'node:child_process';
import {gzipSync} from 'node:zlib';
import {renderClaim} from '../scripts/issue-claim-contract.mjs';
import {subjectsHash} from '../scripts/evidence-quality.mjs';
import {jsonBytes, digest, pinReader, publish, admitPublication, prepareRequests, retainProducts, nativeRequests,
  composeAuthorities, packageProjection, rebindCustody, requestProfile, finalizedSelection, finalizedPackageInputs, finalizeDelivery, prepareEvidence} from '../scripts/prepare-delivery-handoff.mjs';

const commit = 'a'.repeat(40), prefix = 'coordination/engineering/control/';
function memoryReader() {
  const bodies = new Map(), pins = new Map(); let ordinal = 0;
  const reader = {
    add(name, value) { const raw = Buffer.isBuffer(value) ? value : jsonBytes(value); const pin = {path: name, commit,
      mode: '100644', blob: (++ordinal).toString(16).padStart(40, '0'), bytes: raw.length, sha256: digest(raw)};
      bodies.set(pin.sha256, raw); pins.set(name, pin); return pin; },
    pin(c, name) { assert.equal(c, commit); const pin = pins.get(name); assert.ok(pin, "missing fixture path"); return pin; },
    read(pin) { const raw = bodies.get(pin.sha256); assert.ok(raw, 'missing fixture pin'); assert.equal(raw.length, pin.bytes); return raw; },
    json(pin) { return JSON.parse(reader.read(pin)); }};
  return reader;
}
function requestsFixture() {
  const reader = memoryReader(), ids = ['case-z', 'case-a', 'case-m'];
  const handoff = reader.add('research/geography/control/source.json', {scopeIds: ids,
    candidate_source_native_bindings: ids.map(component_id => ({component_id, retained_payload: {target_stable_location_id: 'target'}}))});
  const {commit: accepted_source_commit, ...source} = handoff;
  const registry = reader.add(prefix + 'registry.json', {version: 1, kind: 'accepted-administrative-handoffs-v1',
    entries: [{id: 'whole', cohort_ids: ids, target_ids: ['target'], accepted_source_commit, source}]});
  const request = {operation: 'retained-land-source-premises-v1', baseline: {pins: []}, destination: '.cache/native-grid-candidates/original',
    output_reserve: 1000, operating_runtime: {version: 1}, executed_code: [], installed_modules: [], parent: {components: 3}, report: reader.add('report.json', {}), source_rule: {profile: 'retained-consumed-administrative-source',
      inputs: [handoff], cases_path: handoff.path, outcomes_path: handoff.path, registry_path: registry.path,
      cohort_ids: ids, expected_ids: ids, geometry_scope: 'full-component', administrative_products: [], target_banks: ['bank']}};
  const template = reader.add(prefix + 'request.json', request);
  const config = {version: 1, compatibility: 'literal-historical-v1', registry, component_ids: ids,
    groups: [{id: 'actual-method', handoff_id: 'whole', template, component_ids: [...ids].reverse(), destination: '.cache/native-grid-candidates/prepared'}]};
  return {reader, config, request};
}

test('SOURCE preparation preserves handoff order, methods/resources and complete whole handoff pin', () => {
  const {reader, config, request} = requestsFixture(); const outputs = prepareRequests(config, reader);
  const actual = JSON.parse(outputs['actual-method-source-request.json']);
  assert.deepEqual(actual.source_rule.expected_ids, ['case-z', 'case-a', 'case-m']);
  assert.deepEqual({...actual, destination: request.destination}, request);
  assert.deepEqual(prepareRequests(config, reader), outputs);
  for (const mutate of [c => c.groups[0].component_ids.push('foreign'), c => c.groups.push({...c.groups[0], id: 'duplicate-scope'}),
    c => c.groups[0].handoff_id = 'unaccepted', c => c.component_ids.pop(), c => c.groups[0].destination = '../outside']) {
    const copy = structuredClone(config); mutate(copy); assert.throws(() => prepareRequests(copy, reader));
  }
});

test('accepted whole handoff target/order drift fails even when its new pin is coherent', () => {
  for (const change of [h => h.candidate_source_native_bindings.reverse(), h => h.candidate_source_native_bindings[0].retained_payload.target_stable_location_id = 'wrong']) {
    const {reader, config} = requestsFixture(), registry = reader.json(config.registry), entry = registry.entries[0];
    const handoff = reader.json({...entry.source, commit: entry.accepted_source_commit}); change(handoff);
    const pin = reader.add(entry.source.path, handoff); const {commit: c, ...source} = pin; entry.source = source;
    config.registry = reader.add(config.registry.path, registry);
    assert.throws(() => prepareRequests(config, reader), /order|join/);
  }
});

function directory(t) { const root = fs.mkdtempSync(path.join(os.tmpdir(), 'delivery-prep-')); t.after(() => fs.rmSync(root, {recursive: true, force: true})); return root; }
function write(root, name, raw) { fs.mkdirSync(path.dirname(path.join(root, name)), {recursive: true}); fs.writeFileSync(path.join(root, name), raw); }

test('writer resumes only exact complete bytes and rejects collisions, dangling symlinks and changed bindings', t => {
  const root = directory(t), dest = '.cache/delivery-handoff/run', products = {'small.json': jsonBytes({value: 1})};
  assert.equal(publish(root, dest, products, {phase: 'test'}).resumed, false);
  assert.equal(publish(root, dest, products, {phase: 'test'}, true).resumed, true);
  assert.throws(() => publish(root, dest, products, {phase: 'test'}), /Occupied/);
  assert.throws(() => publish(root, dest, products, {phase: 'changed'}, true), /changed/);
  const saved = fs.readFileSync(path.join(root, dest, 'small.json'));
  fs.unlinkSync(path.join(root, dest, 'preparation.json'));
  assert.throws(() => publish(root, dest, products, {phase: 'test'}, true), /Incomplete/);
  assert.deepEqual(fs.readFileSync(path.join(root, dest, 'small.json')), saved);
  fs.symlinkSync('/missing-destination', path.join(root, '.cache/delivery-handoff/link'));
  assert.throws(() => publish(root, '.cache/delivery-handoff/link', products, {}), /Nonordinary/);
  assert.throws(() => publish(root, '.cache/delivery-handoff/link/child', products, {}), /Nonordinary/);
  assert.throws(() => publish(root, '.cache/delivery-handoff/../escape', products, {}), /fresh owned/);
});


function terminalFixture(root) {
  const {reader, request} = requestsFixture(); const requestPin = reader.add(prefix + 'source-request.json', request);
  const facts = {execution_commit: commit, request: requestPin, source_rule: request.source_rule, components: 3, source_compatible: 3, assigned_cells: 0,
    executed_code: request.executed_code, installed_modules: request.installed_modules, baseline: request.baseline, parent: request.parent,
    input_descriptors: [request.report, ...request.source_rule.inputs, ...request.baseline.pins], operation: request.operation, runtime: {bytes: 100, sha256: 'b'.repeat(64)}};
  const handoffPin = request.source_rule.inputs[0], cases = reader.json(handoffPin).candidate_source_native_bindings;
  const factRaw = jsonBytes(facts), decoded = Buffer.concat(request.source_rule.expected_ids.map((component_id, ordinal) => jsonBytes({component_id, target_id: 'target', source_compatible: true,
    source_case: {source: handoffPin, ordinal, row_sha256: digest(jsonBytes(cases[ordinal]))}}))), inventory = gzipSync(decoded);
  const publication = {version: 1, complete: true, facts: {bytes: factRaw.length, sha256: digest(factRaw)}, inventory: {bytes: inventory.length, sha256: digest(inventory), uncompressed_bytes: decoded.length, uncompressed_sha256: digest(decoded)}};
  const terminal = {qualified: true, exit: {code: 0, signal: null}, refusal: null, execution_commit: commit,
    request_sha256: requestPin.sha256, destination: request.destination, owned_processes_remaining: [], termination_events: []};
  const config = {version: 1, request: requestPin, output: 'run', terminal: 'operating/receipt.json'};
  for (const [name, raw] of Object.entries({'run/facts.json': factRaw, 'run/inventory.jsonl.gz': inventory, 'run/publication.json': jsonBytes(publication), 'operating/receipt.json': jsonBytes(terminal)})) write(root, name, raw);
  return {reader, config, request, facts, terminal, publication, inventory};
}

test('retention joins genuine terminal, request, facts and every published output; no completion from partial files', t => {
  const root = directory(t), f = terminalFixture(root);
  assert.deepEqual(Object.keys(retainProducts(f.config, root, f.reader)).sort(), ['facts.json', 'inventory.jsonl.gz', 'publication.json', 'request.json', 'terminal.json']);
  for (const change of [v => v.exit.code = 1, v => v.qualified = false, v => v.refusal = 'guard', v => v.termination_events.push('killed'), v => v.owned_processes_remaining.push(99), v => v.request_sha256 = '0'.repeat(64)]) {
    const terminal = structuredClone(f.terminal); change(terminal); write(root, f.config.terminal, jsonBytes(terminal)); assert.throws(() => retainProducts(f.config, root, f.reader));
  }
  write(root, f.config.terminal, jsonBytes(f.terminal)); fs.unlinkSync(path.join(root, 'run/inventory.jsonl.gz'));
  assert.throws(() => retainProducts(f.config, root, f.reader), /ENOENT/);
  write(root, 'run/inventory.jsonl.gz', Buffer.from('changed')); assert.throws(() => retainProducts(f.config, root, f.reader), /Incomplete/);
});

test('native preparation requires committed genuine SOURCE products and preserves immutable runtime/resource fields', t => {
  const root = directory(t), f = terminalFixture(root), r = f.reader;
  const source = {request: f.config.request, facts: r.add(prefix + 'facts.json', f.facts), operating: r.add(prefix + 'operating.json', f.terminal),
    publication: r.add(prefix + 'publication.json', f.publication), inventory: r.add(prefix + 'inventory.jsonl.gz', f.inventory)};
  const additive = {source_profile: f.request.source_rule.profile, scope_ids: f.request.source_rule.expected_ids, inputs: Object.values(source)};
  for (const [key, value] of Object.entries({source_request_path: 'request', operating_path: 'operating', publication_path: 'publication', facts_path: 'facts', inventory_path: 'inventory'})) additive[key] = source[value].path;
  const template = r.add(prefix + 'native-template.json', {operation: 'unactivated-additive-native-batch-v1', baseline: f.request.baseline,
    destination: '.cache/native-grid-candidates/native-old', output_reserve: 123, additive});
  const config = {compatibility: 'literal-historical-v1', groups: [{id: 'native', template, source, destination: '.cache/native-grid-candidates/native-new'}]};
  const actual = JSON.parse(nativeRequests(config, r)['native-native-request.json']);
  assert.equal(actual.output_reserve, 123); assert.deepEqual(actual.additive.scope_ids, f.request.source_rule.expected_ids);
  assert.equal(actual.additive.source_execution_commit, commit); assert.deepEqual(actual.additive.source_runtime, f.facts.runtime);
  assert.deepEqual(actual.additive.inputs.find(p => p.path === actual.additive.source_request_path), f.facts.request);
  const inventoryPin = actual.additive.inputs.find(p => p.path === actual.additive.inventory_path);
  assert.equal(inventoryPin.uncompressed_bytes, f.publication.inventory.uncompressed_bytes);
  assert.equal(inventoryPin.uncompressed_sha256, f.publication.inventory.uncompressed_sha256);
  source.operating = r.add(prefix + 'failed.json', {...f.terminal, qualified: false}); assert.throws(() => nativeRequests(config, r), /successful terminal/);
});

function authorityFixture() {
  const reader = memoryReader(), rule = reader.add(prefix + 'rule.json', {}), source = reader.add(prefix + 'binding.json', {});
  const entry = {policy_id: 'retained-source-literal-additions', policy_version: 1, rule_sha256: rule.sha256,
    rule_preimage: {...rule, git_blob_oid: rule.blob}, source_authority: {...source, git_blob_oid: source.blob}};
  for (const p of [entry.rule_preimage, entry.source_authority]) delete p.blob;
  entry.authority_sha256 = digest(jsonBytes(entry));
  const registry = {version: 1, kind: 'retained-rule-authority-registry-v1', entries: [entry]};
  const geometry = {type: 'Polygon', coordinates: [[[0, 0], [1, 0], [0, 1], [0, 0]]]};
  const row = {component_id: 'component:a', target_id: 'target', pixelIndex: 1, base_geometry_sha256: 'b'.repeat(64), geometry_sha256: digest(jsonBytes(geometry)),
    source_receipt_sha256: 'c'.repeat(64), geometry, native_cells: 2, disposition: 'assigned'};
  const ledger = {version: 1, kind: 'native-additive-repair-ledger-v1', rule_sha256: rule.sha256, parent_inventory: {total: 1}, scope_ids: [row.component_id], rows: [row]};
  return {reader, registry, ledger};
}

test('composition invokes existing conservation logic and rejects duplicate original scope', () => {
  const f = authorityFixture(), reg = f.reader.add(prefix + 'registry.json', f.registry), led = f.reader.add(prefix + 'ledger.json', f.ledger);
  const config = {registries: [reg], ledgers: [led]}, output = composeAuthorities(config, f.reader);
  const ledger = JSON.parse(output['composed-original-ledger.json']);
  assert.equal(ledger.rows[0].native_cells, 2); assert.deepEqual(ledger.scope_ids, ['component:a']);
  assert.throws(() => composeAuthorities({...config, ledgers: [led, led]}, f.reader), /Duplicate/);
  const unordered = {...f.ledger, scope_ids: ['component:z', 'component:a'], rows: [{...f.ledger.rows[0], component_id: 'component:z'}, f.ledger.rows[0]]};
  const ordered = JSON.parse(composeAuthorities({...config, ledgers: [f.reader.add(prefix + 'unordered.json', unordered)]}, f.reader)['composed-original-ledger.json']);
  assert.deepEqual(ordered.scope_ids, ['component:a', 'component:z']);
  unordered.scope_ids.reverse(); assert.throws(() => composeAuthorities({...config, ledgers: [f.reader.add(prefix + 'wrong-roster.json', unordered)]}, f.reader), /roster mismatch/);
  const projection = packageProjection({registry: f.reader.add(prefix + 'composed-reg.json', JSON.parse(output['authority-registry.json'])),
    ledger: f.reader.add(prefix + 'composed-led.json', ledger), new_prefix: 'coordination/engineering/new/'}, f.reader);
  const smoke = JSON.parse(projection['selected-delivery-expectations.json']); assert.equal(smoke.cumulative_native_cells, 2); assert.equal(smoke.selected_ledger_sha256, null);
});

test('immutable Git input reader rejects whole-body drift, missing objects and nonordinary pins', t => {
  const root = directory(t); const git = (...args) => execFileSync('git', args, {cwd: root, stdio: ['pipe', 'pipe', 'pipe']}).toString().trim();
  git('init'); git('config', 'user.name', 'Fixture'); git('config', 'user.email', 'fixture@example.invalid'); write(root, 'input.json', jsonBytes({value: 1}));
  git('add', 'input.json'); git('commit', '-m', 'Fixture'); const r = pinReader(root), pin = r.pin(git('rev-parse', 'HEAD'), 'input.json');
  assert.equal(r.json(pin).value, 1); assert.throws(() => r.read({...pin, path: 'missing.json'}), /Missing ordinary/); assert.throws(() => r.read({...pin, sha256: '0'.repeat(64)}), /hash differs/);
  assert.throws(() => r.read({...pin, mode: '120000'}), /identity/); assert.throws(() => r.read({...pin, path: '../input.json'}), /safe/);
});

test('rebind commit phases require complete custody and publication-matching result pins', () => {
  const r = memoryReader(), request = r.add(prefix + 'request.json', {execution_commit: commit, base_selection: {}, authority_registry_sha256: 'a'.repeat(64)});
  const facts = r.add(prefix + 'facts.json', {}), result = r.add(prefix + 'result.json', {});
  const publication = r.add(prefix + 'publication.json', {execution_commit: commit, request_sha256: request.sha256,
    outputs: {facts: {path: 'facts.json', bytes: facts.bytes, sha256: facts.sha256}, result: {path: 'result.json', bytes: result.bytes, sha256: result.sha256}}});
  const terminal = r.add(prefix + 'terminal.json', {execution_commit: commit, exit_code: 0, signal: null, guard_reason: null,
    owned_processes_remaining: [], termination_events: [], request_sha256: request.sha256, publication_sha256: publication.sha256, lifetime_rss_bytes: 100, elapsed_seconds: 1});
  const execution_custody = {terminal, ...Object.fromEntries(['code_source', 'stderr', 'stdout', 'issued_plan'].map(k => [k, r.add(prefix + k + '.json', {})]))};
  const config = {request, publication, terminal, facts, result, execution_custody};
  assert.throws(() => rebindCustody(config, r), /historical rebind code roster/);
  assert.throws(() => rebindCustody({...config, execution_custody: {terminal}}, r), /Complete external/);
  assert.throws(() => rebindCustody({...config, result: r.add(prefix + 'wrong-result.json', {wrong: true})}, r), /output pin differs/);
});

test('new request issuance authenticates v2 actual HEAD support/code pins', () => {
  const reader = memoryReader(), code = reader.add('scripts/operator.mjs', Buffer.from('code'));
  const support = ['scripts/local-workspace.mjs', 'scripts/worker-identity.mjs'].map(p => reader.add(p, Buffer.from('support')));
  const template = {operating_profile: 'source-native-v2', output_reserve: 131072, executed_code: [code], operating_runtime: {supervisor: code, support_code: support}};
  reader.git = () => Buffer.from(commit); reader.pin = (c, p) => [code, ...support].find(x => x.path === p);
  const issued = requestProfile(template, {}, {}, reader);
  assert.equal(issued.operating_profile, 'source-native-v2');
  assert.equal(Object.hasOwn(issued,'output_reserve'),false);
  assert.throws(() => requestProfile({...template, operating_profile: undefined}, {}, {}, reader), /v2/);
  const drift = structuredClone(template); drift.operating_runtime.support_code[0].sha256 = '0'.repeat(64);
  assert.throws(() => requestProfile(drift, {}, {}, reader), /actual HEAD/);
});

test('coherent SOURCE inventory changes and native preparation facts omissions are rejected against pinned scope/targets', t => {
  const root = directory(t), f = terminalFixture(root);
  const handoffPin = f.request.source_rule.inputs[0], cases = f.reader.json(handoffPin).candidate_source_native_bindings;
  const originalRows = f.request.source_rule.expected_ids.map((component_id, ordinal) => ({component_id, target_id: 'target', source_compatible: true, source_case: {source: handoffPin, ordinal, row_sha256: digest(jsonBytes(cases[ordinal]))}}));
  for (const rows of [[], originalRows.slice(1), [originalRows[0], originalRows[0], originalRows[2]],
    [{...originalRows[0], component_id: 'foreign'}, ...originalRows.slice(1)], [{...originalRows[0], target_id: 'wrong'}, ...originalRows.slice(1)],
    [{...originalRows[0], source_case: {...originalRows[0].source_case, ordinal: 2}}, ...originalRows.slice(1)]]) {
    const decoded = Buffer.concat(rows.map(jsonBytes)), encoded = gzipSync(decoded), publication = structuredClone(f.publication);
    publication.inventory = {bytes: encoded.length, sha256: digest(encoded), uncompressed_bytes: decoded.length, uncompressed_sha256: digest(decoded)};
    write(root, 'run/inventory.jsonl.gz', encoded); write(root, 'run/publication.json', jsonBytes(publication));
    assert.throws(() => retainProducts(f.config, root, f.reader), /inventory|Inventory|identity|SOURCE/);
  }
  const r = f.reader, corruptFacts = {...f.facts, components: 0, source_compatible: 0}, facts = r.add(prefix + 'coherent-facts.json', corruptFacts);
  const publication = r.add(prefix + 'coherent-publication.json', {...f.publication, facts: {bytes: facts.bytes, sha256: facts.sha256}});
  const source = {request: f.config.request, facts, publication, operating: r.add(prefix + 'operating.json', f.terminal), inventory: r.add(prefix + 'inventory.jsonl.gz', f.inventory)};
  assert.throws(() => nativeRequests({groups: [{id: 'bad-source', source}]}, r), /scope\/order\/count/);
});

test('native retention rejects a publication that omits the required ledger asset', t => {
  const root = directory(t), f = terminalFixture(root), r = f.reader;
  const request = {...f.request, operation: 'unactivated-additive-native-batch-v1', additive: {scope_ids: f.request.source_rule.expected_ids, source_request_path: f.config.request.path, inputs: [...f.request.source_rule.inputs, f.config.request]}};
  const pin = r.add(prefix + 'native-request.json', request), facts = {...f.facts, request: pin, operation: request.operation, source_predecessor: request.additive, input_descriptors: [request.report, ...request.additive.inputs, ...request.baseline.pins]};
  const decoded = Buffer.concat(request.additive.scope_ids.map(component_id => jsonBytes({component_id, native_cells: 0, disposition: 'rejected'}))), encoded = gzipSync(decoded);
  facts.assigned_cells = 0;
  const factRaw = jsonBytes(facts), publication = {...f.publication, facts: {bytes: factRaw.length, sha256: digest(factRaw)},
    inventory: {bytes: encoded.length, sha256: digest(encoded), uncompressed_bytes: decoded.length, uncompressed_sha256: digest(decoded)}, assets: []};
  write(root, 'run/inventory.jsonl.gz', encoded);
  write(root, 'run/facts.json', factRaw); write(root, 'run/publication.json', jsonBytes(publication));
  write(root, f.config.terminal, jsonBytes({...f.terminal, request_sha256: pin.sha256}));
  assert.throws(() => retainProducts({...f.config, request: pin}, root, r), /fixed native publication asset roster/);
});

test('native self-consistent target substitutions fail the independent immutable SOURCE join', t => {
  const root = directory(t), f = terminalFixture(root), r = f.reader;
  const request = {...f.request, operation: 'unactivated-additive-native-batch-v1', additive: {
    scope_ids: f.request.source_rule.expected_ids, source_request_path: f.config.request.path, inputs: [...f.request.source_rule.inputs, f.config.request]}};
  const pin = r.add(prefix + 'native-request.json', request);
  function candidate(target) {
    const rows = request.additive.scope_ids.map(component_id => ({component_id, target_id: target, disposition: 'assigned', native_cells: 1}));
    const inventoryRaw = Buffer.concat(rows.map(jsonBytes)), inventory = gzipSync(inventoryRaw);
    const ledger = {scope_ids: request.additive.scope_ids, rows: rows.map(row => ({...row, pixelIndex: 1})), assigned_cells: 3};
    const products = {'base-native-manifest.json': jsonBytes({}), 'ledger-batch.json': jsonBytes(ledger),
      'owners-batch.json.gz': gzipSync(Buffer.from('{}')), 'features.json': jsonBytes([]), 'owner-window.json': jsonBytes([]), 'virtual-owner-window.json': jsonBytes([])};
    products['patch-batch.json'] = jsonBytes({ledger_sha256: digest(products['ledger-batch.json']), rows: [{y: 1, runs: [[0, 3, 1]]}]});
    products['release-envelope.json'] = jsonBytes({additiveRelease: Object.fromEntries(Object.entries({base_manifest: 'base-native-manifest.json',
      ledger: 'ledger-batch.json', patch: 'patch-batch.json', owner_roster: 'owners-batch.json.gz'}).map(([role, name]) => [role, {bytes: products[name].length, sha256: digest(products[name])}]))});
    const facts = jsonBytes({...f.facts, request: pin, operation: request.operation, source_predecessor: request.additive, assigned_cells: 3,
      input_descriptors: [request.report, ...request.additive.inputs, ...request.baseline.pins]});
    const publication = {version: 1, complete: true, facts: {bytes: facts.length, sha256: digest(facts)},
      inventory: {bytes: inventory.length, sha256: digest(inventory), uncompressed_bytes: inventoryRaw.length, uncompressed_sha256: digest(inventoryRaw)},
      assets: Object.entries(products).map(([path, raw]) => ({path, bytes: raw.length, sha256: digest(raw)}))};
    for (const [name, raw] of Object.entries({...products, 'facts.json': facts, 'inventory.jsonl.gz': inventory, 'publication.json': jsonBytes(publication)})) write(root, 'run/' + name, raw);
    write(root, f.config.terminal, jsonBytes({...f.terminal, request_sha256: pin.sha256}));
  }
  candidate('target'); assert.ok(retainProducts({...f.config, request: pin}, root, r)['ledger-batch.json']);
  candidate('foreign-native-target');
  assert.throws(() => retainProducts({...f.config, request: pin}, root, r), /immutable SOURCE handoff/);
});


test('selector finalization preserves insertion order and repeat bytes, including unsorted nested geography', () => {
  const original = {version: 1, selected_geography: {version: 1, kind: 'bank', path: 'bank.json', bytes: 9, sha256: 'a'.repeat(64)},
    policy: {z: 1, a: 2}, additive_release: {path: 'old.json', bytes: 2, sha256: 'b'.repeat(64)}};
  const base = {...original}; delete base.additive_release;
  const sidecar = {version: 2, kind: 'retained-native-additive-selection-v2', base_selection: JSON.parse(jsonBytes(base))};
  const pin = {path: prefix + 'sidecar.json', bytes: 200, sha256: 'c'.repeat(64)};
  const output = finalizedSelection(Buffer.from(JSON.stringify(original, null, 2) + '\n'), sidecar, pin);
  const actual = JSON.parse(output), after = {...actual}; delete after.additive_release;
  assert.equal(JSON.stringify(after), JSON.stringify(base));
  assert.notEqual(JSON.stringify(actual.selected_geography), JSON.stringify(JSON.parse(jsonBytes(base)).selected_geography));
  assert.equal(finalizedSelection(output, sidecar, pin), output);
  const compact = Buffer.from(JSON.stringify(actual) + '\n');
  assert.equal(finalizedSelection(compact, sidecar, pin), compact);
  const changed = structuredClone(sidecar); changed.base_selection.policy.a = 3;
  assert.throws(() => finalizedSelection(output, changed, pin), /complete original base/);
});

test('final package appends preserve the entire accepted prefix and validate duplicates/overlaps', () => {
  const original = {version: 1, description: 'untouched', inputs: ['.github/package-inputs.json', 'z.json', prefix + 'obsolete.json', 'a.json'],
    optional_inputs: ['a.json'], verification_paths: ['test/check.mjs'], generated_outputs: ['dist/'], extra: {z: 1, a: 2}};
  const paths = [prefix + 'new-z.json', prefix + 'new-a.json'];
  const actual = finalizedPackageInputs(original, prefix, paths);
  assert.deepEqual(actual.inputs, [...original.inputs, ...paths.toSorted()]);
  assert.throws(() => finalizedPackageInputs(original, prefix, [paths[0], paths[0]]), /owned package/);
  assert.deepEqual(original.inputs, ['.github/package-inputs.json', 'z.json', prefix + 'obsolete.json', 'a.json']);
  assert.equal(JSON.stringify({...actual, inputs: []}), JSON.stringify({...original, inputs: []}));
  assert.equal(JSON.stringify(finalizedPackageInputs(actual, prefix, paths)), JSON.stringify(actual));
  assert.throws(() => finalizedPackageInputs(original, prefix, [prefix + '../bad']), /owned package/);
  assert.throws(() => finalizedPackageInputs({...original, inputs: [...original.inputs, 'coordination/engineering/']}, prefix, paths), /Overlapping/);
  assert.deepEqual(finalizedPackageInputs({...original, optional_inputs: [prefix + 'obsolete.json']}, prefix, paths).optional_inputs, [prefix + 'obsolete.json']);
});

function finalizationFixture({historical = false, custodyPin = null} = {}) {
  const f = authorityFixture(), r = f.reader, owned = 'coordination/engineering/finalize/';
  const composed = composeAuthorities({registries: [r.add(prefix + 'original-registry.json', f.registry)], ledgers: [r.add(prefix + 'original-ledger.json', f.ledger)]}, r);
  const registry = r.add(owned + 'registry.json', composed['authority-registry.json']);
  const ledger = r.add(owned + 'ledger.json', composed['composed-original-ledger.json']);
  const retained = historical ? 'coordination/engineering/accepted-original/' : owned;
  const stub = {...r.add(retained + 'custody.json', {}), ...(custodyPin ?? {})}, operating = r.add(retained + 'operating.json', {execution_custody: {terminal: stub}});
  const rebind = r.add(owned + 'certificate.json', {request: stub, facts: stub, publication: stub, result: stub, operating});
  const selected_ledger = r.add(owned + 'selected.json', {...r.json(ledger), current_rebind: rebind, current_targets: {target: true}});
  const baseReference = {id: 'base', footprints_sha256: 'b'.repeat(64), hierarchy_sha256: 'c'.repeat(64)};
  const patch = r.add(owned + 'patch.json', {ledger_sha256: selected_ledger.sha256, authority_registry_sha256: registry.sha256, base_reference: baseReference, effective_reference: {id: 'effective'}});
  const owner_roster = r.add(owned + 'owner-roster.json', {});
  const base_manifest = r.add(owned + 'base-manifest.json', {original_assets: {bounds: {sha256: owner_roster.sha256}}, geographic_release: 'base', footprints_sha256: baseReference.footprints_sha256, hierarchy_sha256: baseReference.hierarchy_sha256});
  const assets = {base_manifest, ledger: selected_ledger, owner_roster, patch};
  const runtime_envelope = r.add(owned + 'envelope.json', {...Object.fromEntries(Object.entries(assets).map(([key,pin]) => [key, {bytes: pin.bytes, sha256: pin.sha256}])), base_reference: baseReference, effective_reference: {id: 'effective'}});
  const base = {version: 1, release_id: 'base', sha256: base_manifest.sha256, selected_geography: {version: 1, path: 'bank.json', sha256: 'a'.repeat(64)}};
  const selector = r.add('data/ownership-selection.json', Buffer.from(JSON.stringify(base, null, 2) + '\n'));
  const sidecar = r.add(owned + 'sidecar.json', {version: 2, kind: 'retained-native-additive-selection-v2', base_selection: base, authority_registry: registry, logical_asset_map: assets, runtime_envelope});
  const package_inputs = r.add('.github/package-inputs.json', {version: 1, inputs: ['.github/package-inputs.json', owned + 'obsolete.json', 'public/'], optional_inputs: ['public/'], verification_paths: [], generated_outputs: []});
  return {reader: r, config: {version: 1, registry, ledger, rebind, selected_ledger, selector, sidecar, package_inputs, new_prefix: owned}};
}

test('finalization joins genuine release metadata, stages fresh files, and repeats without changes', t => {
  const {reader,config} = finalizationFixture(), root = directory(t), reads = [], originalRead = reader.read;
  reader.read = pin => { reads.push(pin.path); return originalRead(pin); };
  const output = finalizeDelivery(config, reader);
  assert.ok(reads.includes(reader.json(config.sidecar).logical_asset_map.owner_roster.path), 'retained owner whole pin was authenticated');
  assert.equal(JSON.parse(output['selected-delivery-expectations.json']).selected_ledger_sha256, config.selected_ledger.sha256);
  const again = finalizeDelivery({...config, selector: reader.add(config.selector.path, output['ownership-selection.json']),
    package_inputs: reader.add(config.package_inputs.path, output['package-inputs.json'])}, reader);
  for (const key of Object.keys(output)) assert.deepEqual(again[key], output[key]);
  const destination = '.cache/delivery-handoff/finalized';
  publish(root, destination, output, {phase: 'finalize'});
  assert.equal(publish(root, destination, output, {phase: 'finalize'}, true).resumed, true);
  assert.equal(fs.existsSync(path.join(root, 'data')), false);
  assert.throws(() => publish(root, destination, output, {phase: 'changed'}, true), /changed/);
});

test('finalization rejects coherent foreign sidecar/base/ledger/envelope bindings before publication', t => {
  for (const mutate of [
    (f,s) => s.base_selection.selected_geography.sha256 = '0'.repeat(64),
    (f,s) => s.authority_registry = f.config.ledger,
    (f,s) => { const p=f.reader.add(s.logical_asset_map.base_manifest.path,{foreign:'manifest'}); s.logical_asset_map.base_manifest=p; const e=f.reader.json(s.runtime_envelope); e.base_manifest={bytes:p.bytes,sha256:p.sha256}; s.runtime_envelope=f.reader.add(s.runtime_envelope.path,e); },
    (f,s) => { const p=f.reader.add(s.logical_asset_map.owner_roster.path,{foreign:'roster'}); s.logical_asset_map.owner_roster=p; const e=f.reader.json(s.runtime_envelope); e.owner_roster={bytes:p.bytes,sha256:p.sha256}; s.runtime_envelope=f.reader.add(s.runtime_envelope.path,e); },
    (f,s) => { const e=f.reader.json(s.runtime_envelope); e.owner_roster.decoded_bytes=10; s.runtime_envelope=f.reader.add(s.runtime_envelope.path,e); },
    ...['id', 'footprints_sha256', 'hierarchy_sha256'].map(key => (f,s) => { const p=f.reader.json(s.logical_asset_map.patch), e=f.reader.json(s.runtime_envelope); p.base_reference[key]='foreign'; e.base_reference[key]='foreign'; s.logical_asset_map.patch=f.reader.add(s.logical_asset_map.patch.path,p); e.patch={bytes:s.logical_asset_map.patch.bytes,sha256:s.logical_asset_map.patch.sha256}; s.runtime_envelope=f.reader.add(s.runtime_envelope.path,e); }),
    (f,s) => s.logical_asset_map.ledger = f.config.ledger,
    (f,s) => { const e=f.reader.json(s.runtime_envelope); e.patch.sha256='0'.repeat(64); s.runtime_envelope=f.reader.add(s.runtime_envelope.path,e); },
    (f,s) => { const p=f.reader.json(s.logical_asset_map.patch); p.ledger_sha256='0'.repeat(64); s.logical_asset_map.patch=f.reader.add(s.logical_asset_map.patch.path,p); const e=f.reader.json(s.runtime_envelope); e.patch={bytes:s.logical_asset_map.patch.bytes,sha256:s.logical_asset_map.patch.sha256}; s.runtime_envelope=f.reader.add(s.runtime_envelope.path,e); },
    (f,s) => { const l=f.reader.json(f.config.selected_ledger); l.current_rebind=f.config.ledger; f.config.selected_ledger=f.reader.add(f.config.selected_ledger.path,l); s.logical_asset_map.ledger=f.config.selected_ledger; }
  ]) {
    const f=finalizationFixture(), root=directory(t), sidecar=f.reader.json(f.config.sidecar); mutate(f,sidecar);
    f.config.sidecar=f.reader.add(f.config.sidecar.path,sidecar);
    assert.throws(() => publish(root, '.cache/delivery-handoff/refused', finalizeDelivery(f.config,f.reader), {}), /differs|differ|preserve/);
    assert.equal(fs.existsSync(path.join(root,'.cache')),false);
  }
});


test('finalization retains historical custody but packages only the six current consumer bodies', () => {
  const {reader, config} = finalizationFixture({historical: true});
  const original = reader.json(config.package_inputs), result = finalizeDelivery(config, reader);
  const actual = JSON.parse(result['package-inputs.json']);
  assert.deepEqual(actual.inputs.slice(0, original.inputs.length), original.inputs);
  const sidecar = reader.json(config.sidecar);
  const current = [config.sidecar, sidecar.runtime_envelope, ...Object.values(sidecar.logical_asset_map)].map(p => p.path).sort();
  assert.deepEqual(actual.inputs.slice(original.inputs.length), current);
  const retained = JSON.parse(result['package-roles.json']).paths.map(p => p.path);
  for (const name of ['custody.json', 'operating.json'].map(n => 'coordination/engineering/accepted-original/' + n)) {
    assert.ok(retained.includes(name));
    assert.ok(!actual.inputs.includes(name));
  }
  assert.ok(Object.keys(result).every(name => !name.includes('/')));
  const foreign = reader.add('coordination/engineering/unbound/existing.json', {});
  assert.throws(() => finalizeDelivery({...config, outer_roles: [foreign]}, reader), /derived outer roles/);
  assert.throws(() => finalizedPackageInputs(original, config.new_prefix, [foreign.path]), /owned package/);
});

test('finalization refuses changed, absent or nonordinary inherited read identities', () => {
  for (const change of [p => ({...p, sha256: '0'.repeat(64)}), p => ({...p, bytes: p.bytes + 1}),
    p => ({...p, blob: '0'.repeat(40)}), p => ({...p, mode: '100755'}),
    () => { throw new Error('missing accepted inherited path'); }]) {
    const {reader, config} = finalizationFixture({historical: true}), originalPin = reader.pin;
    reader.pin = (c, name) => name === 'coordination/engineering/accepted-original/custody.json'
      ? change(originalPin(c, name)) : originalPin(c, name);
    assert.throws(() => finalizeDelivery(config, reader), /accepted path identity|missing accepted inherited path/);
  }
});

test('finalization checks the independent Git package baseline, not the role source commit', t => {
  const root = directory(t), name = 'coordination/engineering/accepted-original/custody.json';
  const git = (...args) => execFileSync('git', args, {cwd: root, stdio: ['pipe','pipe','pipe']}).toString().trim();
  git('init'); git('config','user.name','Fixture'); git('config','user.email','fixture@example.invalid');
  write(root, 'baseline.txt', 'baseline'); git('add','.'); git('commit','-m','Absent baseline');
  const absent = git('rev-parse','HEAD');
  write(root, name, jsonBytes({changed: true})); git('add','.'); git('commit','-m','Different baseline');
  const changed = git('rev-parse','HEAD');
  write(root, name, jsonBytes({})); git('add','.'); git('commit','-m','Original source body');
  const source = git('rev-parse','HEAD'), actual = pinReader(root);
  assert.deepEqual(actual.json(actual.pin(source,name)), {});
  const restored = finalizationFixture({historical: true, custodyPin: actual.pin(source,name)});
  const originalPin = restored.reader.pin;
  restored.config.package_inputs = {...restored.config.package_inputs, commit: absent};
  restored.config.restored_read_roles = {commit: source, paths: [name]};
  restored.reader.hasPath = (c,p) => { assert.equal(c,absent); return actual.hasPath(c,p); };
  restored.reader.pin = (c,p) => p === name ? actual.pin(c,p) : originalPin(commit,p);
  const result = finalizeDelivery(restored.config,restored.reader);
  assert.ok(JSON.parse(result['package-roles.json']).paths.some(pin => pin.path === name));
  assert.ok(!JSON.parse(result['package-inputs.json']).inputs.includes(name));
  restored.config.restored_read_roles.commit = changed;
  assert.throws(()=>finalizeDelivery(restored.config,restored.reader), /Restored snapshot differs/);
  for (const baseline of [absent, changed]) {
    const {reader,config} = finalizationFixture({historical: true}), originalPin = reader.pin, calls = [];
    config.package_inputs = {...config.package_inputs, commit: baseline};
    reader.pin = (c,p) => { calls.push(c); return p === name ? actual.pin(c,p) : originalPin(commit,p); };
    assert.throws(() => finalizeDelivery(config,reader), /Missing ordinary exact Git body|accepted path identity/);
    assert.ok(calls.length && calls.every(c => c === baseline));
    assert.ok(!calls.includes(source));
  }
});

test('finalization admits only an exact committed restoration of absent canonical read roles', () => {
  const setup = () => {
    const f = finalizationFixture({historical: true}), original = f.reader.pin;
    const paths = ['custody.json','operating.json'].map(n => 'coordination/engineering/accepted-original/' + n);
    const snapshot = 'b'.repeat(40);
    f.config.restored_read_roles = {commit: snapshot, paths: [...paths]};
    f.reader.hasPath = (c,p) => { assert.equal(c,commit); return !paths.includes(p); };
    f.reader.pin = (c,p) => {
      if (paths.includes(p)) { assert.equal(c,snapshot); return {...original(commit,p), commit: snapshot}; }
      return original(c,p);
    };
    return f;
  };
  const f = setup(), output = finalizeDelivery(f.config,f.reader);
  const inputs = JSON.parse(output['package-inputs.json']).inputs;
  const retained = JSON.parse(output['package-roles.json']).paths.map(pin => pin.path);
  for (const name of f.config.restored_read_roles.paths) {
    assert.ok(retained.includes(name));
    assert.ok(!inputs.includes(name));
  }
  for (const mutate of [
    f => f.config.restored_read_roles.paths.push(f.config.restored_read_roles.paths[0]),
    f => f.config.restored_read_roles.paths.push('coordination/engineering/unbound/existing.json'),
    f => f.config.restored_read_roles.paths.push(f.config.selected_ledger.path),
    f => f.config.restored_read_roles.paths.pop(),
    f => { const old=f.reader.pin; f.reader.pin=(c,p)=>c==='b'.repeat(40)?{...old(c,p),sha256:'0'.repeat(64)}:old(c,p); },
    f => { const old=f.reader.pin; f.reader.pin=(c,p)=>c==='b'.repeat(40)?{...old(c,p),mode:'120000'}:old(c,p); },
    f => { const old=f.reader.pin; f.reader.pin=(c,p)=>{ if(c==='b'.repeat(40)) throw Error('missing snapshot'); return old(c,p); }; },
    f => { f.reader.hasPath=()=>true; const old=f.reader.pin; f.reader.pin=(c,p)=>old(c===commit?'b'.repeat(40):c,p); }
  ]) { const g=setup(); mutate(g); assert.throws(()=>finalizeDelivery(g.config,g.reader), /inventory|required|accepted path identity/); }
  const g=setup(); g.config.restored_read_roles.paths=[];
  assert.throws(()=>finalizeDelivery(g.config,g.reader), /inventory required/);
  const h=setup(); delete h.config.restored_read_roles;
  assert.throws(() => finalizeDelivery(h.config,h.reader), /accepted path identity/);
});

test('finalization refuses a new identity at an accepted package path', () => {
  const {reader,config} = finalizationFixture();
  const first = finalizeDelivery(config, reader);
  const package_inputs = reader.add(config.package_inputs.path, first['package-inputs.json']);
  const originalPin = reader.pin;
  reader.pin = (c,p) => p === config.selected_ledger.path ? {...originalPin(c,p), sha256: '0'.repeat(64)} : originalPin(c,p);
  assert.throws(() => finalizeDelivery({...config,package_inputs},reader), /conflicts with accepted path identity/);
});

// Actual Git/plain-Node fixture for metadata assembly. The source interpretation
// and native construction controls live in source-member-native-delivery.test;
// this fixture exercises the consumed-role boundary without replaying science.
function modernFinalizationFixture(t, {mixed = false, membership = true, dated = false, territorial = false} = {}) {
  const root = directory(t), owned = 'coordination/engineering/modern-finalize/';
  const git = (...args) => execFileSync('git', args, {cwd: root, stdio: ['pipe', 'pipe', 'pipe']}).toString().trim();
  git('init'); git('config', 'user.name', 'Finalizer fixture'); git('config', 'user.email', 'finalizer@example.invalid');
  const save = (name, value) => write(root, name, Buffer.isBuffer(value) ? value : jsonBytes(value));
  const commitAll = () => { git('add', '.'); git('commit', '--allow-empty', '-qm', 'Immutable finalizer fixture'); return git('rev-parse', 'HEAD'); };
  const r = pinReader(root), pin = name => r.pin(git('rev-parse', 'HEAD'), name);
  const inherited = 'coordination/engineering/accepted-source/';
  const roles = Object.fromEntries(['physical_input', 'physical_reproduction', 'physical_evidence', 'native_latitudes', 'owner_roster']
    .map(role => [role, inherited + role + '.json']));
  roles.catalogue = 'coordination/engineering/original-geography-source-corpus-20261006/catalogue.json';
  for (const name of Object.values(roles)) save(name, {retained: name});
  const familyPart = inherited + 'family-part.json.gz', familyRaw = jsonBytes({type: 'FeatureCollection', features: []});
  save(familyPart, gzipSync(familyRaw));
  const memberPaths = ['data/world-index.json', 'data/semantic-report.json', 'data/geography/part-0.json'];
  for (const name of memberPaths) save(name, {retained: name});
  const incidental = inherited + 'gshhg-never-consumed.json'; save(incidental, {not_a_selected_reader_operand: true});
  const geometry = {type: 'Polygon', coordinates: [[[0, 0], [1, 0], [0, 1], [0, 0]]]};
  const baseReference = {id: 'geography:base', footprints_sha256: 'b'.repeat(64), hierarchy_sha256: 'c'.repeat(64)};
  const ownerPath = inherited + 'owners.json.gz', ownerRaw = jsonBytes([{id: 'target', index: 1}]);
  save(ownerPath, gzipSync(ownerRaw)); commitAll();
  const owner = {...pin(ownerPath), encoding: 'gzip', decoded_bytes: ownerRaw.length, decoded_sha256: digest(ownerRaw)};
  save(inherited + 'base-manifest.json', {geographic_release: baseReference.id, footprints_sha256: baseReference.footprints_sha256,
    hierarchy_sha256: baseReference.hierarchy_sha256, size: 8, coordinateBits: 3, method: 'native-linear-evenodd-first-owner-v1',
    native_latitudes: pin(roles.native_latitudes), original_assets: {bounds: {sha256: owner.sha256}}}); commitAll();
  const baseManifest = pin(inherited + 'base-manifest.json');
  // Deliberately unsorted nested selector keys and accepted declaration ordering.
  const base = {version: 1, release_id: baseReference.id, sha256: baseManifest.sha256,
    selected_geography: {version: 1, path: 'bank.json', z: 3, a: 1, sha256: 'a'.repeat(64)}};
  const originalSelector = Buffer.from(JSON.stringify(base, null, 2) + '\n');
  const originalPackage = {version: 1, inputs: ['public/', '.github/package-inputs.json'], optional_inputs: ['public/'],
    verification_paths: ['test/delivery-handoff.test.mjs'], generated_outputs: ['dist/'], retained_policy: 'unchanged'};
  save('data/ownership-selection.json', originalSelector); save('.github/package-inputs.json', originalPackage); commitAll();
  const selector = pin('data/ownership-selection.json');
  const evidenceBody = {version: 1, kind: 'source-target-native-evidence-v1',
    ...Object.fromEntries(Object.entries(roles).map(([role, name]) => [role, pin(name)])),
    targets: [{id: 'source:A', target_id: 'target'}],
    families: [{source_id: 'source', parts: [{...pin(familyPart), decoded_bytes: familyRaw.length, decoded_sha256: digest(familyRaw)}]}],
    native_contract: {incidental_reproducer_operand: pin(incidental)},
    ...(membership ? {source_membership: {index: pin(memberPaths[0]), lineage: pin(memberPaths[1]), parts: [pin(memberPaths[2])]}} : {})};
  let datedSupport;
  if (dated) {
    const provenance = ['adoption', 'review', 'observation', 'frame'].map(role => {
      const name = inherited + 'dated-' + role + (role === 'frame' ? '.png' : '.json');
      save(name, role === 'frame' ? Buffer.from('encoded frame fixture; never decoded by package projection') : {retained: role});
      return {id: role, role, name};
    });
    commitAll();
    const entries = provenance.map(({id, role, name}) => ({id, role, pin: pin(name)}));
    entries.push({...entries[3], id: 'same-frame-second-reference'});
    const body = {version: 1, kind: 'adopted-dated-native-centre-land-support-v1', provenance: entries, records: []};
    const supportPath = inherited + 'dated-support.json'; save(supportPath, body); commitAll();
    datedSupport = {body, path: supportPath, pin: pin(supportPath)};
    Object.assign(evidenceBody, {version: 2, kind: 'source-target-native-evidence-v2', dated_land_support: datedSupport.pin});
  }
  let territorialSupport;
  if (territorial) {
    const sources = ['adoption','scope','original-source'].map(role => {
      const name = inherited + 'territorial-' + role + '.json';save(name,{retained:role});return {id:role,role,name};
    });commitAll();
    const body = {version:1,kind:'adopted-native-territorial-applicability-v1',
      provenance:sources.map(({id,role,name})=>({id,role,pin:pin(name)})),records:[]};
    const name=inherited+'territorial-applicability.json';save(name,body);commitAll();
    territorialSupport={body,path:name,pin:pin(name)};evidenceBody.territorial_applicability=territorialSupport.pin;
  }
  save(owned + 'source-evidence.json', evidenceBody); save(owned + 'native-patch.json', {rows: [{y: 2, runs: [[2, 4, 1]]}]}); commitAll();
  const authority = binding => {
    const stem = binding.kind === 'source-target-native-custody-v1' ? 'modern' : 'legacy';
    const preimage = stem === 'modern' ? {...binding, kind: 'source-target-native-rule-v1'} : {version: 1, literal: true};
    save(owned + stem + '-binding.json', binding); save(owned + stem + '-rule.json', preimage); commitAll();
    const entry = {policy_id: 'retained-source-literal-additions', policy_version: 1,
      rule_preimage: pin(owned + stem + '-rule.json'), rule_sha256: digest(jsonBytes(preimage)), source_authority: pin(owned + stem + '-binding.json')};
    return {authority_sha256: digest(jsonBytes(entry)), ...entry};
  };
  const modern = authority({version: 1, kind: 'source-target-native-custody-v1',
    source_evidence: pin(owned + 'source-evidence.json'), native_patch: pin(owned + 'native-patch.json')});
  const entries = [modern], nativeRows = [{y: 2, runs: [[2, 4, 1]]}];
  const rows = [{representation: 'native-cells', component_id: 'source-target:fixture', target_id: 'target', pixelIndex: 1,
    disposition: 'assigned', base_geometry: geometry, base_geometry_sha256: digest(jsonBytes(geometry)), native_rows: nativeRows,
    native_bounds: [0, 0, 1, 1], native_cells: 2, source_receipt_sha256: evidenceBody.physical_evidence.sha256,
    authority_sha256: modern.authority_sha256, rule_sha256: modern.rule_sha256}];
  if (mixed) {
    const legacyPrefix = inherited + 'legacy/';
    for (const name of ['source-publication', 'source-inventory', 'source-operating', 'native-publication', 'native-inventory', 'asset', 'stub'])
      save(legacyPrefix + name + '.json', {retained: name}); commitAll();
    const sourcePins = ['publication', 'inventory', 'operating'].map(name => pin(legacyPrefix + 'source-' + name + '.json'));
    save(legacyPrefix + 'native-request.json', {additive: {inputs: sourcePins,
      publication_path: sourcePins[0].path, inventory_path: sourcePins[1].path, operating_path: sourcePins[2].path}}); commitAll();
    const stub = pin(legacyPrefix + 'stub.json');
    const legacy = authority({version: 1, kind: 'original-issued-rule-source-custody-v1',
      original_pins: {source_request: stub, source_facts: stub, native_request: pin(legacyPrefix + 'native-request.json'),
        native_facts: stub, native_manifest: stub, ledger: stub},
      native_proof: {publication: pin(legacyPrefix + 'native-publication.json'), inventory: pin(legacyPrefix + 'native-inventory.json'),
        operating: stub, assets: [pin(legacyPrefix + 'asset.json')]}});
    entries.push(legacy); rows.unshift({component_id: 'legacy:fixture', target_id: 'target', pixelIndex: 1, geometry,
      base_geometry_sha256: digest(jsonBytes(geometry)), geometry_sha256: digest(jsonBytes(geometry)), source_receipt_sha256: 'e'.repeat(64),
      native_cells: 1, disposition: 'assigned', authority_sha256: legacy.authority_sha256, rule_sha256: legacy.rule_sha256});
    rows.unshift({component_id: 'held:fixture', disposition: 'awaiting-evidence', reason: 'literal unresolved evidence',
      authority_sha256: legacy.authority_sha256, rule_sha256: legacy.rule_sha256});
  }
  const package_inputs = pin('.github/package-inputs.json');
  const registry = {version: 1, kind: 'retained-rule-authority-registry-v1', entries: entries.sort((a, b) => a.authority_sha256.localeCompare(b.authority_sha256))};
  save(owned + 'registry.json', registry); save(owned + 'ledger.json', {version: 2, kind: 'native-additive-repair-ledger-v2',
    authority_registry_sha256: digest(jsonBytes(registry)), parent_inventory: {original_denominator: 7}, scope_ids: rows.map(row => row.component_id), rows});
  save(owned + 'custody.json', {retained: true}); commitAll();
  const registryPin = pin(owned + 'registry.json'), ledgerPin = pin(owned + 'ledger.json');
  const stub = pin(owned + 'custody.json'); save(owned + 'operating.json', {execution_custody: {terminal: stub}}); commitAll();
  save(owned + 'rebind.json', {request: stub, facts: stub, publication: stub, result: stub, operating: pin(owned + 'operating.json')}); commitAll();
  const rebind = pin(owned + 'rebind.json');
  save(owned + 'selected-ledger.json', {...r.json(pin(owned + 'ledger.json')), current_rebind: rebind, current_targets: [{target_id: 'target'}]}); commitAll();
  const selected_ledger = pin(owned + 'selected-ledger.json'), effectiveReference = {...baseReference, id: 'geography:effective'};
  save(owned + 'patch.json', {version: 2, kind: 'unassigned-native-cells-v1', authority_registry_sha256: digest(jsonBytes(registry)), ledger_sha256: selected_ledger.sha256,
    base_reference: baseReference, effective_reference: effectiveReference, rows: [...(mixed ? [{y: 1, runs: [[0, 1, 1]]}] : []), ...nativeRows]}); commitAll();
  const assets = {base_manifest: baseManifest, ledger: selected_ledger, owner_roster: owner, patch: pin(owned + 'patch.json')};
  const envelope = {version: 2, kind: 'retained-native-base-plus-delta-v2', base_reference: baseReference, effective_reference: effectiveReference,
    ...Object.fromEntries(Object.entries(assets).map(([role, p]) => [role, {path: 'additive-repairs/' + role + (role === 'owner_roster' ? '.json.gz' : '.json'),
      bytes: p.bytes, sha256: p.sha256, ...(role === 'owner_roster' ? {encoding: 'gzip', decoded_bytes: p.decoded_bytes, decoded_sha256: p.decoded_sha256} : {})}]))};
  save(owned + 'envelope.json', {reference_release: effectiveReference, additiveRelease: envelope}); commitAll();
  save(owned + 'sidecar.json', {version: 2, kind: 'retained-native-additive-selection-v2', base_selection: base,
    authority_registry: registryPin, logical_asset_map: assets, runtime_envelope: pin(owned + 'envelope.json')}); commitAll();
  const config = {version: 1, registry: registryPin, ledger: ledgerPin, rebind, selected_ledger,
    selector, package_inputs, sidecar: pin(owned + 'sidecar.json'), new_prefix: owned};
  const withEvidence = body => {
    save(owned + 'altered-source.json', body); commitAll();
    const binding = {version: 1, kind: 'source-target-native-custody-v1', source_evidence: pin(owned + 'altered-source.json'),
      native_patch: r.json(modern.source_authority).native_patch};
    save(owned + 'altered-binding.json', binding); save(owned + 'altered-rule.json', {...binding, kind: 'source-target-native-rule-v1'}); commitAll();
    const entry = {policy_id: 'retained-source-literal-additions', policy_version: 1, rule_preimage: pin(owned + 'altered-rule.json'),
      rule_sha256: pin(owned + 'altered-rule.json').sha256, source_authority: pin(owned + 'altered-binding.json')};
    const changedRegistry = {version: 1, kind: registry.kind, entries: [{authority_sha256: digest(jsonBytes(entry)), ...entry}]};
    const changedLedger = {...r.json(config.ledger), authority_registry_sha256: digest(jsonBytes(changedRegistry)),
      rows: rows.filter(row => row.representation === 'native-cells').map(row => ({...row,
        authority_sha256: changedRegistry.entries[0].authority_sha256, rule_sha256: entry.rule_sha256}))};
    changedLedger.scope_ids = changedLedger.rows.map(row => row.component_id);
    save(owned + 'altered-registry.json', changedRegistry); save(owned + 'altered-ledger.json', changedLedger); commitAll();
    return {...config, registry: pin(owned + 'altered-registry.json'), ledger: pin(owned + 'altered-ledger.json')};
  };
  const script = new URL('../scripts/prepare-delivery-handoff.mjs', import.meta.url).pathname;
  const run = (phase, destination, flags = [], input = config) => {
    save('config.json', input);
    const env = {...process.env, GIT_NO_LAZY_FETCH: '1'}; delete env.NODE_OPTIONS; delete env.NODE_PATH;
    return spawnSync(process.execPath, [script, phase, 'config.json', destination, ...flags], {cwd: root, env, encoding: 'utf8'});
  };
  return {root, r, config, run, git, save, commitAll, pin, evidenceBody, originalSelector, originalPackage, assets,
    consumed: [...Object.values(roles), familyPart, ...(membership ? memberPaths : [])], incidental, withEvidence, datedSupport, territorialSupport};
}

for (const mixed of [false, true]) test('real finalizer supports ' + (mixed ? 'mixed legacy/modern' : 'modern') + ' roles, flat envelope aliases and exact resume', t => {
  const f = modernFinalizationFixture(t, {mixed}), first = '.cache/delivery-handoff/first', second = '.cache/delivery-handoff/second';
  const packageRun = f.run('package', '.cache/delivery-handoff/projection'); assert.equal(packageRun.status, 0, packageRun.stderr);
  const finalized = f.run('finalize', first); assert.equal(finalized.status, 0, finalized.stderr);
  const products = name => fs.readFileSync(path.join(f.root, first, name));
  const inputs = JSON.parse(products('package-inputs.json'));
  assert.deepEqual(inputs.inputs.slice(0, f.originalPackage.inputs.length), f.originalPackage.inputs);
  for (const key of ['optional_inputs', 'verification_paths', 'generated_outputs', 'retained_policy']) assert.deepEqual(inputs[key], f.originalPackage[key]);
  const custody = JSON.parse(products('package-roles.json')).paths.map(p => p.path);
  for (const name of [...f.consumed, ...Object.values(f.assets).map(p => p.path)]) assert.ok(custody.includes(name), name);
  const sidecar = f.r.json(f.config.sidecar);
  const current = [f.config.sidecar, sidecar.runtime_envelope, ...Object.values(f.assets)].map(p => p.path).sort();
  assert.deepEqual(inputs.inputs.slice(f.originalPackage.inputs.length), current);
  for (const name of f.consumed) assert.ok(!inputs.inputs.includes(name), name);
  assert.ok(!inputs.inputs.includes(f.incidental)); assert.ok(!inputs.inputs.some(name => name.endsWith('selected-delivery-expectations.json')));
  const selected = JSON.parse(products('ownership-selection.json')), original = {...selected}; delete original.additive_release;
  assert.equal(JSON.stringify(original), JSON.stringify(JSON.parse(f.originalSelector)));
  assert.deepEqual(fs.readFileSync(path.join(f.root, 'data/ownership-selection.json')), f.originalSelector);
  const expected = JSON.parse(products('selected-delivery-expectations.json'));
  const members = expected.cohorts.flatMap(cohort => cohort.members);
  assert.equal(members.find(row => row.component_id === 'source-target:fixture').native_rows_sha256, digest(jsonBytes([{y: 2, runs: [[2, 4, 1]]}])));
  assert.equal(expected.cumulative_native_cells, mixed ? 3 : 2);
  if (mixed) assert.ok(members.find(row => row.component_id === 'legacy:fixture').geometry_sha256);
  const resumed = f.run('finalize', first, ['--resume']); assert.equal(resumed.status, 0, resumed.stderr); assert.equal(JSON.parse(resumed.stdout).resumed, true);
  const repeated = f.run('finalize', second); assert.equal(repeated.status, 0, repeated.stderr);
  for (const name of ['ownership-selection.json', 'package-inputs.json', 'package-roles.json', 'selected-delivery-expectations.json'])
    assert.deepEqual(fs.readFileSync(path.join(f.root, second, name)), products(name));
});

test('real v2 package command closes dated support and fixed provenance once without original-role copies', t => {
  const f = modernFinalizationFixture(t, {dated: true}), destination = '.cache/delivery-handoff/dated';
  const run = f.run('package', destination); assert.equal(run.status, 0, run.stderr);
  const projection = JSON.parse(fs.readFileSync(path.join(f.root, destination, 'package-roles.json')));
  const needed = [f.datedSupport.pin, ...f.datedSupport.body.provenance.map(entry => entry.pin)];
  for (const pin of needed) {
    const matches = projection.paths.filter(entry => entry.path === pin.path);
    assert.equal(matches.length, 1, pin.path);
    assert.equal(matches[0].sha256, pin.sha256); assert.equal(matches[0].bytes, pin.bytes);
  }
  for (const role of ['adoption', 'review', 'observation', 'frame']) assert.ok(projection.paths.some(entry =>
    entry.roles.includes('source-target dated ' + role)), role);
  assert.deepEqual(fs.readdirSync(path.join(f.root, destination)).sort(),
    ['package-roles.json', 'preparation.json', 'selected-delivery-expectations.json']);
  assert.ok(!projection.paths.some(pin => pin.path === f.incidental));
});

test('real package command retains territorial adoption, exact scope and original sources beside dated land roles', t => {
  const f=modernFinalizationFixture(t,{dated:true,territorial:true}),destination='.cache/delivery-handoff/territorial';
  const run=f.run('package',destination);assert.equal(run.status,0,run.stderr);
  const projection=JSON.parse(fs.readFileSync(path.join(f.root,destination,'package-roles.json')));
  for(const typed of [f.datedSupport,f.territorialSupport])for(const pin of [typed.pin,...typed.body.provenance.map(p=>p.pin)]){
    const matches=projection.paths.filter(p=>p.path===pin.path);assert.equal(matches.length,1,pin.path);
    assert.equal(matches[0].sha256,pin.sha256);assert.equal(matches[0].bytes,pin.bytes);
  }
  for(const role of ['adoption','scope','original-source'])assert.ok(projection.paths.some(p=>
    p.roles.includes('source-target territorial '+role)),role);
  assert.deepEqual(fs.readdirSync(path.join(f.root,destination)).sort(),
    ['package-roles.json','preparation.json','selected-delivery-expectations.json']);
  for(const change of ['typed-pin','source-pin','unknown-role']){
    const evidence=structuredClone(f.evidenceBody),support=structuredClone(f.territorialSupport.body);
    if(change==='typed-pin')evidence.territorial_applicability.sha256='0'.repeat(64);
    else{
      if(change==='source-pin')support.provenance[2].pin.sha256='0'.repeat(64);
      else support.provenance[2].role='arbitrary-tree';
      f.save(f.territorialSupport.path,support);f.commitAll();evidence.territorial_applicability=f.pin(f.territorialSupport.path);
    }
    const output='.cache/delivery-handoff/refused-territorial-'+change;
    const failed=f.run('package',output,[],f.withEvidence(evidence));assert.notEqual(failed.status,0,change);
    assert.match(failed.stderr,/hash differs|Unknown territorial applicability provenance role/);
    assert.equal(fs.existsSync(path.join(f.root,output)),false);
  }
});

test('v2 package refuses altered typed or declared provenance and unknown roles before publication', t => {
  const f = modernFinalizationFixture(t, {dated: true}); let ordinal = 0;
  for (const change of ['typed-pin', 'declared-frame', 'unknown-role', 'missing-pin']) {
    const evidence = structuredClone(f.evidenceBody), support = structuredClone(f.datedSupport.body);
    if (change === 'typed-pin') evidence.dated_land_support.sha256 = '0'.repeat(64);
    else {
      if (change === 'declared-frame') support.provenance[3].pin.sha256 = '0'.repeat(64);
      if (change === 'unknown-role') support.provenance[3].role = 'nested-source-tree';
      if (change === 'missing-pin') delete support.provenance[3].pin;
      f.save(f.datedSupport.path, support); f.commitAll(); evidence.dated_land_support = f.pin(f.datedSupport.path);
    }
    const destination = '.cache/delivery-handoff/refused-dated-' + ordinal++;
    const run = f.run('package', destination, [], f.withEvidence(evidence));
    assert.notEqual(run.status, 0, change);
    assert.match(run.stderr, /hash differs|Unknown dated support provenance role|Missing whole consumed package role/, change);
    assert.equal(fs.existsSync(path.join(f.root, destination)), false);
  }
});

test('real modern package command accepts absent optional membership and refuses omitted or altered consumed dependencies before publication', t => {
  const f = modernFinalizationFixture(t, {membership: false});
  const good = f.run('package', '.cache/delivery-handoff/no-membership'); assert.equal(good.status, 0, good.stderr);
  let ordinal = 0;
  for (const name of f.consumed) {
    const oldRead = f.r.read; f.r.read = p => p.path === name ? oldRead({...p, sha256: '0'.repeat(64)}) : oldRead(p);
    assert.throws(() => packageProjection(f.config, f.r), /hash differs/); f.r.read = oldRead;
  }
  for (const role of ['catalogue', 'physical_input', 'physical_reproduction', 'physical_evidence', 'native_latitudes', 'owner_roster', 'families']) {
    const body = structuredClone(f.evidenceBody); delete body[role];
    const destination = '.cache/delivery-handoff/refused-' + ordinal++;
    const refused = f.run('package', destination, [], f.withEvidence(body));
    assert.notEqual(refused.status, 0, role); assert.match(refused.stderr, /Missing.*(?:role|family)/, role);
    assert.equal(fs.existsSync(path.join(f.root, destination)), false);
  }
});


// Scalar extraction from the reviewed AUS facts/evidence at
// c753c65a72e51718b453883a941fc22e148b5fbb, merged as 94d7016a6e12ec5c5414db24202e95d5dd9e4459:
// coordination/engineering/nor-grc-congo-delivery-20261011/aus13-selected-20261012/
// retained-002/native/facts.json and evidence-quality.json. These small controls
// exercise report transfer, not geographic computation or original byte identity.
const ausNativeScalars = {components: 13, assigned_cells: 20, assigned_components: 7,
  zero_cell_components: 6, native_conflicts: 0, removed_cells: 0, reassigned_cells: 0, source_exceptions: 0,
  candidate_cell_contributions: 20, shared_same_owner_cells: 0};
const ausSourceEvaluation = 'ad32930dc368c1b4b1cb46cc0484649053d44762';
const ausNativeEvaluation = '5d287b5f78c9219b1d9202d20d8824ef2ef7898b';

test('real modern package command rejects changed whole dependency pins and incomplete accepted membership', t => {
  const f = modernFinalizationFixture(t); let ordinal = 0;
  const refused = body => {
    const destination = '.cache/delivery-handoff/changed-' + ordinal++;
    const result = f.run('package', destination, [], f.withEvidence(body));
    assert.notEqual(result.status, 0); assert.match(result.stderr, /hash differs|Missing.*membership|Missing.*family/);
    assert.equal(fs.existsSync(path.join(f.root, destination)), false);
  };
  for (const mutate of [
    ...['catalogue', 'physical_input', 'physical_reproduction', 'physical_evidence', 'native_latitudes', 'owner_roster']
      .map(role => body => { body[role].sha256 = '0'.repeat(64); }),
    body => { body.families[0].parts[0].sha256 = '0'.repeat(64); },
    ...['index', 'lineage'].map(role => body => { body.source_membership[role].sha256 = '0'.repeat(64); }),
    body => { body.source_membership.parts[0].sha256 = '0'.repeat(64); },
    ...['index', 'lineage', 'parts'].map(role => body => { delete body.source_membership[role]; }),
    body => { body.source_membership.parts = []; }, body => { body.families[0].parts = []; }
  ]) { const body = structuredClone(f.evidenceBody); mutate(body); refused(body); }
});

function evidenceFixture(reader = memoryReader({admit: false})) {
  const descriptor = pin => ({path: pin.path, bytes: pin.bytes, sha256: pin.sha256, hash_kind: 'file-bytes'});
  const baseline = reader.add('baseline.json', {retained: true});
  const input = reader.add(prefix + 'native-request.json', {operation: 'unactivated-additive-native-batch-v1'});
  const facts = {...ausNativeScalars, execution_commit: ausNativeEvaluation, request: input};
  const measurement = reader.add(prefix + 'native-facts.json', facts);
  const sourceInput = reader.add(prefix + 'source-request.json', {operation: 'retained-land-source-premises-v1'});
  const sourceFacts = reader.add(prefix + 'source-facts.json', {components: 13, source_compatible: 13,
    execution_commit: ausSourceEvaluation, request: sourceInput});
  const manifest = {version: 1, issue: 1785, lane: 'engineering', worker_id: 'fixture', subject_ids: [], subject_ids_sha256: subjectsHash([]),
    baseline: {version: 2, commit, files: [{...descriptor(baseline), commit}], pins: {}}, sources: [],
    outputs: [input, measurement, sourceInput, sourceFacts].map(descriptor),
    methods: [{id: 'delivery', kind: 'code', description: 'Retained delivery measurements', software: 'Node 24', units: 'components, native cells'}],
    metrics: [], summaries: [], conclusions: [], stages: {research: 'complete', implementation: 'implemented', geographic_approval: 'not-requested'}, commands: []};
  const source = {measurement, input, input_file: {path: input.path, commit: 'candidate'}, evaluation_commit: ausNativeEvaluation,
    vintage: 'archived', fields: Object.keys(ausNativeScalars).map(field => ({id: 'aus-native-' + field, field}))};
  const config = {version: 1, template: reader.add(prefix + 'template.json', manifest), metric_sources: [source,
    {measurement: sourceFacts, input: sourceInput, input_file: {path: sourceInput.path, commit: 'candidate'}, evaluation_commit: ausSourceEvaluation,
      vintage: 'archived', fields: ['components', 'source_compatible'].map(field => ({id: 'aus-source-' + field, field}))}]};
  return {reader, config, manifest, source, facts};
}

test('typed evidence transfers actual AUS counts and explicit request/evaluation vintages', () => {
  const f = evidenceFixture(), manifest = JSON.parse(prepareEvidence(f.config, f.reader)['evidence-quality.json']);
  for (const [field, value] of Object.entries(ausNativeScalars)) {
    const metric = manifest.metrics.find(row => row.id === 'aus-native-' + field);
    assert.equal(metric.value, value);
    assert.equal(metric.unit, ['assigned_cells', 'removed_cells', 'reassigned_cells', 'candidate_cell_contributions', 'shared_same_owner_cells'].includes(field) ? 'native cells' : 'components');
    assert.equal(metric.input_sha256, f.source.input.sha256);
    assert.deepEqual(metric.input_file, f.source.input_file);
    assert.equal(metric.evaluation_commit, ausNativeEvaluation); assert.equal(metric.vintage, 'archived');
    assert.deepEqual(manifest.metric_bindings.find(row => row.metric_id === metric.id),
      {metric_id: metric.id, path: f.source.measurement.path, json_pointer: '/' + field});
  }
  assert.equal(manifest.metrics.find(row => row.id === 'aus-source-source_compatible').value, 13);
  assert.equal(manifest.metrics.find(row => row.id === 'aus-source-components').evaluation_commit, ausSourceEvaluation);
});

test('typed evidence supports the concrete elapsed/bytes/emitted delivery measurements', () => {
  const f = evidenceFixture();
  const values = {elapsed_seconds: 54.003, complete_phase_bytes: 289834589, expected_components_verified: 73,
    cumulative_native_cells_picked_and_sampled: 1123, stable_owner_controls: 347};
  const measurement = f.reader.add(prefix + 'measured.json', values);
  f.manifest.outputs.push({path: measurement.path, bytes: measurement.bytes, sha256: measurement.sha256, hash_kind: 'file-bytes'});
  f.config.template = f.reader.add(prefix + 'template-extra.json', f.manifest);
  f.config.metric_sources.push({...f.source, measurement, fields: Object.keys(values).map(field => ({id: field, field}))});
  const result = JSON.parse(prepareEvidence(f.config, f.reader)['evidence-quality.json']);
  for (const [field, unit] of Object.entries({elapsed_seconds: 'seconds', complete_phase_bytes: 'bytes', expected_components_verified: 'components',
    cumulative_native_cells_picked_and_sampled: 'native cells', stable_owner_controls: 'sampled occupied row controls'})) {
    assert.equal(result.metrics.find(row => row.id === field).unit, unit);
    assert.equal(result.metrics.find(row => row.id === field).value, values[field]);
  }
});

test('typed evidence refuses wrong units/types, missing values and changed consumed/evaluation bindings', () => {
  for (const mutate of [f => f.source.fields[0].field = 'unknown_cells', f => f.source.fields[0].unit = 'native cells',
    f => f.source.fields[0].type = 'number', f => f.source.fields.push({...f.source.fields[0]}),
    f => f.source.evaluation_commit = commit, f => f.source.input_file.path = 'foreign.json',
    f => f.source.input_file.commit = 'b'.repeat(40), f => f.source.vintage = 'current', f => f.source.fields = []]) {
    const f = evidenceFixture(); mutate(f); assert.throws(() => prepareEvidence(f.config, f.reader));
  }
  for (const value of [undefined, null, '6', true, -1, 0.5, Number.MAX_SAFE_INTEGER + 1]) {
    const f = evidenceFixture(), facts = {...f.facts, zero_cell_components: value};
    f.source.measurement = f.reader.add(prefix + 'bad-facts.json', facts);
    f.manifest.outputs.push({path: f.source.measurement.path, bytes: f.source.measurement.bytes,
      sha256: f.source.measurement.sha256, hash_kind: 'file-bytes'});
    f.config.template = f.reader.add(prefix + 'bad-template.json', f.manifest);
    assert.throws(() => prepareEvidence(f.config, f.reader), /Missing\/invalid measured value/);
  }
  const f = evidenceFixture(); f.source.input = f.reader.add(prefix + 'foreign-request.json', {other: true});
  f.source.input_file.path = f.source.input.path;
  assert.throws(() => prepareEvidence(f.config, f.reader), /Consumed input differs/);
  const stale = evidenceFixture(); stale.source.measurement.sha256 = '0'.repeat(64);
  assert.throws(() => prepareEvidence(stale.config, stale.reader), /missing fixture pin/);
});

test('evidence CLI authenticates Git inputs and refuses malformed metrics before publication; immutable resume', t => {
  const root = directory(t), git = (...args) => execFileSync('git', args, {cwd: root, stdio: ['pipe', 'pipe', 'pipe']}).toString().trim();
  git('init'); git('config', 'user.name', 'Fixture'); git('config', 'user.email', 'fixture@example.invalid');
  const memory = evidenceFixture();
  for (const pin of [memory.config.template, ...memory.config.metric_sources.flatMap(source => [source.input, source.measurement])])
    write(root, pin.path, memory.reader.read(pin));
  write(root, 'baseline.json', jsonBytes({retained: true})); git('add', '.'); git('commit', '-m', 'Pinned fixture');
  const reader = pinReader(root), head = git('rev-parse', 'HEAD'), config = structuredClone(memory.config);
  const manifest = memory.manifest; manifest.baseline.commit = head; manifest.baseline.files[0].commit = head;
  // Actual fixture request descriptors are frozen in the measured bytes above;
  // the constructor joins their content hashes without relabeling evaluation.
  write(root, memory.config.template.path, jsonBytes(manifest)); git('add', '.'); git('commit', '-m', 'Pinned template');
  config.template = reader.pin(git('rev-parse', 'HEAD'), memory.config.template.path);
  for (const source of config.metric_sources) {
    source.input = reader.pin(head, source.input.path); source.measurement = reader.pin(head, source.measurement.path);
  }
  const script = new URL('../scripts/prepare-delivery-handoff.mjs', import.meta.url).pathname;
  const run = (destination, ...flags) => JSON.parse(execFileSync(process.execPath,
    [script, 'evidence', 'config.json', destination, ...flags], {cwd: root, env: {...process.env, GIT_NO_LAZY_FETCH: '1'}, stdio: ['pipe', 'pipe', 'pipe']}).toString());
  write(root, 'config.json', jsonBytes(config)); const destination = '.cache/delivery-handoff/evidence';
  assert.equal(run(destination).resumed, false);
  const original = fs.readFileSync(path.join(root, destination, 'evidence-quality.json'));
  assert.equal(JSON.parse(original).metrics.find(row => row.id === 'aus-native-zero_cell_components').unit, 'components');
  assert.equal(run(destination, '--resume').resumed, true);
  assert.throws(() => run(destination), /Occupied destination/);
  for (const change of [c => c.metric_sources[0].fields.find(row => row.field === 'zero_cell_components').unit = 'native cells',
    c => c.metric_sources[0].fields.find(row => row.field === 'native_conflicts').unit = 'native cells',
    c => c.metric_sources[0].fields[0].field = 'unrecognized', c => c.metric_sources[0].fields[0].type = 'number',
    c => c.metric_sources[0].measurement.sha256 = '0'.repeat(64)]) {
    const invalid = structuredClone(config); change(invalid); write(root, 'config.json', jsonBytes(invalid));
    assert.throws(() => run('.cache/delivery-handoff/refused'));
    assert.equal(fs.existsSync(path.join(root, '.cache/delivery-handoff/refused')), false);
    assert.deepEqual(fs.readFileSync(path.join(root, destination, 'evidence-quality.json')), original);
  }
});

test('delivery CLI retires review-freeze and queue-submission entry points before any mutation', () => {
  const script = fileURLToPath(new URL('../scripts/prepare-delivery-handoff.mjs', import.meta.url));
  for (const args of [['review', 'absent-config.json', 'absent-destination'],
    ['advance', 'absent-config.json', 'absent-destination', '--submit-queue']]) {
    assert.throws(() => execFileSync(process.execPath, [script, ...args], {
      encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], env: {...process.env, NODE_OPTIONS: '', NODE_PATH: ''}
    }), error => error.status === 1 && /Use advance\|status|Use prepare-delivery-handoff/.test(error.stderr));
  }
});

function modernCompositionFixture(t, {mixed = true} = {}) {
  const f = modernFinalizationFixture(t, {mixed}), owned = 'coordination/engineering/modern-next/';
  const accepted = finalizeDelivery(f.config, f.r);
  f.save('data/ownership-selection.json', accepted['ownership-selection.json']);
  f.save('.github/package-inputs.json', accepted['package-inputs.json']); f.commitAll();
  const selector = f.pin('data/ownership-selection.json'), packageInputs = f.pin('.github/package-inputs.json');
  const priorLedger = f.r.json(f.config.selected_ledger), priorRegistry = f.r.json(f.config.registry);
  const priorPatch = f.r.json(f.assets.patch), manifest = f.r.json(f.assets.base_manifest);
  const evidence = {...f.evidenceBody, base_reference: priorPatch.base_reference,
    targets: [{...f.evidenceBody.targets[0], source_family: 'source', pixelIndex: 1, base_geometry: priorLedger.rows.find(row => row.representation === 'native-cells').base_geometry,
      source_receipt_sha256: f.evidenceBody.physical_evidence.sha256}],
    native_contract: Object.fromEntries(['size', 'coordinateBits', 'method', 'native_latitudes', 'hierarchy_sha256', 'original_assets']
      .map(key => [key, manifest[key]]))};
  const patch = {rows: [{y: 3, runs: [[2, 4, 1]]}]};
  const makeAppend = (change = () => {}, appendPrefix = owned) => {
    const source = structuredClone(evidence), native = structuredClone(patch);
    const template = priorLedger.rows.find(row => row.representation === 'native-cells');
    const {authority_sha256, rule_sha256, ...originalRow} = template;
    const row = {...originalRow, native_rows: structuredClone(patch.rows), native_cells: 2};
    const state = {source, native, row}; change(state);
    f.save(appendPrefix + 'source-evidence.json', source); f.save(appendPrefix + 'native-patch.json', native); f.commitAll();
    row.component_id = state.component_id ?? 'source-target:' + digest(jsonBytes({target_id: row.target_id, evidence: f.pin(appendPrefix + 'source-evidence.json').sha256}));
    const binding = {version: 1, kind: 'source-target-native-custody-v1',
      source_evidence: f.pin(appendPrefix + 'source-evidence.json'), native_patch: f.pin(appendPrefix + 'native-patch.json')};
    f.save(appendPrefix + 'binding.json', binding); f.save(appendPrefix + 'rule.json', {...binding, kind: 'source-target-native-rule-v1'}); f.commitAll();
    const constructed = {products: JSON.parse(JSON.stringify({'original-rule-preimage.json': jsonBytes({...binding, kind: 'source-target-native-rule-v1'}),
      'authority-binding.json': jsonBytes(binding)})), component_ids: [row.component_id], ledger_rows: [row],
      rule_sha256: f.pin(appendPrefix + 'rule.json').sha256, limitations: ['Actual current owner-zero remains separately required.']};
    f.save(appendPrefix + 'constructed-authority.json', constructed); f.commitAll();
    return {version: 1, selector, rule_preimage: f.pin(appendPrefix + 'rule.json'), source_authority: f.pin(appendPrefix + 'binding.json'),
      ledger: f.pin(appendPrefix + 'constructed-authority.json'),
      native_patch: binding.native_patch, effective_release_id: 'geography:modern-next'};
  };
  const config = makeAppend();
  const finalizeConfig = products => {
    for (const [name, raw] of Object.entries(products)) f.save(owned + name, raw);
    f.commitAll();
    const selected_ledger = f.pin(owned + 'selected-ledger.json');
    return {version: 1, new_prefix: owned, selector, package_inputs: packageInputs, registry: f.pin(owned + 'authority-registry.json'),
      ledger: selected_ledger, selected_ledger, rebind: priorLedger.current_rebind, patch: f.pin(owned + 'patch.json'),
      runtime_envelope: f.pin(owned + 'runtime-envelope.json'), sidecar_output: owned + 'selection-sidecar.json'};
  };
  return {...f, owned, config, makeAppend, finalizeConfig, priorLedger, priorRegistry, priorPatch, accepted};
}

for (const mixed of [false, true]) test('late compose and finalize replace modern assembly and the separate sidecar commit' + (mixed ? ' with inherited legacy exceptions' : ''), t => {
  const f = modernCompositionFixture(t, {mixed}), composed = '.cache/delivery-handoff/compose';
  const run = f.run('compose', composed, [], f.config); assert.equal(run.status, 0, run.stderr);
  const names = ['authority-registry.json', 'selected-ledger.json', 'patch.json', 'runtime-envelope.json'];
  const products = Object.fromEntries(names.map(name => [name, fs.readFileSync(path.join(f.root, composed, name))]));
  const registry = JSON.parse(products['authority-registry.json']), ledger = JSON.parse(products['selected-ledger.json']);
  assert.equal(fs.existsSync(path.join(f.root, f.owned + 'registry.json')), false, 'qualification needs no standalone singleton registry');
  const authority = {policy_id: 'retained-source-literal-additions', policy_version: 1, rule_preimage: f.config.rule_preimage,
    rule_sha256: f.config.rule_preimage.sha256, source_authority: f.config.source_authority};
  assert.deepEqual(registry.entries.find(entry => entry.authority_sha256 === digest(jsonBytes(authority))),
    {authority_sha256: digest(jsonBytes(authority)), ...authority}, 'existing authority constructor policy/pin contract');
  for (const entry of f.priorRegistry.entries) assert.deepEqual(registry.entries.find(next => next.authority_sha256 === entry.authority_sha256), entry);
  for (const row of f.priorLedger.rows) assert.deepEqual(ledger.rows.find(next => next.component_id === row.component_id), row);
  for (const name of ['parent_inventory', 'current_rebind', 'current_targets']) assert.deepEqual(ledger[name], f.priorLedger[name]);
  assert.equal(ledger.rows.length, f.priorLedger.rows.length + 1);
  const patch = JSON.parse(products['patch.json']);
  assert.deepEqual(patch.rows, [...f.priorPatch.rows, {y: 3, runs: [[2, 4, 1]]}]);
  const envelope = JSON.parse(products['runtime-envelope.json']).additiveRelease;
  const priorEnvelope = f.r.json(f.r.json(f.r.pin(f.config.selector.commit, JSON.parse(f.accepted['ownership-selection.json']).additive_release.path)).runtime_envelope).additiveRelease;
  for (const role of ['base_manifest', 'owner_roster']) assert.deepEqual(envelope[role], priorEnvelope[role]);
  for (const role of ['ledger', 'patch']) assert.equal(envelope[role].path, priorEnvelope[role].path);
  const composeResume = f.run('compose', composed, ['--resume'], f.config); assert.equal(composeResume.status, 0, composeResume.stderr);
  const finalConfig = f.finalizeConfig(products);
  assert.equal(fs.existsSync(path.join(f.root, finalConfig.sidecar_output)), false);
  const destination = '.cache/delivery-handoff/final', final = f.run('finalize', destination, [], finalConfig);
  assert.equal(final.status, 0, final.stderr);
  const read = name => fs.readFileSync(path.join(f.root, destination, name));
  const sidecarRaw = read('selection-sidecar.json'), selector = JSON.parse(read('ownership-selection.json'));
  assert.deepEqual(selector.additive_release, {path: finalConfig.sidecar_output, bytes: sidecarRaw.length, sha256: digest(sidecarRaw)});
  const base = {...selector}; delete base.additive_release;
  assert.equal(JSON.stringify(base), JSON.stringify(JSON.parse(f.originalSelector)));
  const sidecar = JSON.parse(sidecarRaw), originalSidecar = f.r.json(f.r.pin(f.config.selector.commit, JSON.parse(f.accepted['ownership-selection.json']).additive_release.path));
  for (const role of ['base_manifest', 'owner_roster']) assert.deepEqual(sidecar.logical_asset_map[role], originalSidecar.logical_asset_map[role]);
  const inputs = JSON.parse(read('package-inputs.json')), priorInputs = JSON.parse(f.accepted['package-inputs.json']);
  assert.deepEqual(inputs.inputs.slice(0, priorInputs.inputs.length), priorInputs.inputs);
  assert.ok(inputs.inputs.includes(finalConfig.sidecar_output)); assert.ok(!inputs.inputs.some(name => name.endsWith('selected-delivery-expectations.json')));
  assert.equal(JSON.parse(read('selected-delivery-expectations.json')).cumulative_native_cells, mixed ? 5 : 4);
  const roles = JSON.parse(read('package-roles.json')).paths.find(p => p.path === finalConfig.sidecar_output);
  assert.ok(!Object.hasOwn(roles, 'commit')); assert.deepEqual(roles.roles, ['generated final sidecar']);
  f.save(finalConfig.sidecar_output, sidecarRaw); f.commitAll();
  const resumed = f.run('finalize', destination, ['--resume'], finalConfig); assert.equal(resumed.status, 0, resumed.stderr);
  const repeated = f.run('finalize', '.cache/delivery-handoff/final-again', [], finalConfig); assert.equal(repeated.status, 0, repeated.stderr);
  for (const name of ['selection-sidecar.json', 'ownership-selection.json', 'package-inputs.json', 'package-roles.json', 'selected-delivery-expectations.json'])
    assert.deepEqual(fs.readFileSync(path.join(f.root, '.cache/delivery-handoff/final-again', name)), read(name));
});

test('late modern composition refuses scope, source-contract, patch and occupied-cell changes before publication', t => {
  const f = modernCompositionFixture(t); let ordinal = 0;
  for (const [change, pattern] of [
    [s => { s.component_id = 'held:fixture'; }, /Foreign or duplicate/],
    [s => { s.row.native_cells = 3; }, /Native component cell count/],
    [s => { s.native.rows[0].runs[0][2] = 2; }, /ledger intervals differ/],
    [s => { s.row.pixelIndex = 2; s.row.native_rows[0].runs[0][2] = 2; s.native.rows[0].runs[0][2] = 2; }, /source target\/owner\/receipt/],
    [s => { s.native.rows[0].y = 2; s.row.native_rows[0].y = 2; }, /overlap/],
    [s => { s.source.base_reference.id = 'geography:wrong'; }, /baseline\/contract/],
    [s => { s.source.native_contract.method = 'wrong'; }, /baseline\/contract/],
    [s => { s.source.targets.push({...s.source.targets[0], id: 'source:B', source_family: 'foreign'}); }, /target\/family\/receipt/],
    [s => { const correct = {...s.source.targets[0], id: 'source:B'}; s.source.targets[0].source_receipt_sha256 = 'f'.repeat(64);
      s.source.targets.push(correct); }, /target\/family\/receipt/],
    [s => { s.native.rows = []; }, /ledger intervals differ/],
    [s => { s.row.native_rows[0].runs[0][0] = -1; }, /native-only|native-cell|interval|primitive identity/i],
  ]) {
    const config = f.makeAppend(change), destination = '.cache/delivery-handoff/refused-compose-' + ordinal++;
    const result = f.run('compose', destination, [], config); assert.notEqual(result.status, 0); assert.match(result.stderr, pattern);
    assert.equal(fs.existsSync(path.join(f.root, destination)), false);
  }
  const config = f.makeAppend(), altered = {...config, native_patch: {...config.native_patch, sha256: '0'.repeat(64)}};
  const result = f.run('compose', '.cache/delivery-handoff/refused-pin', [], altered);
  assert.notEqual(result.status, 0); assert.match(result.stderr, /hash differs/);
  assert.equal(fs.existsSync(path.join(f.root, '.cache/delivery-handoff/refused-pin')), false);
  for (const role of ['rule_preimage', 'source_authority']) {
    const changed = {...config, [role]: {...config[role], sha256: '0'.repeat(64)}};
    const destination = '.cache/delivery-handoff/refused-' + role, refused = f.run('compose', destination, [], changed);
    assert.notEqual(refused.status, 0); assert.match(refused.stderr, /hash differs/);
    assert.equal(fs.existsSync(path.join(f.root, destination)), false);
  }
});

test('modern composition accepts compatible mapped members', t => {
  const f = modernCompositionFixture(t);
  const compatible = f.makeAppend(s => s.source.targets.push({...s.source.targets[0], id: 'source:B'}));
  const accepted = f.run('compose', '.cache/delivery-handoff/compatible-members', [], compatible);
  assert.equal(accepted.status, 0, accepted.stderr);

});

test('generated sidecar refuses foreign/colliding outputs and changed release joins before publication', t => {
  const f = modernCompositionFixture(t), occupied = f.owned + 'occupied-output.json', sentinel = Buffer.from('existing-sidecar-path-sentinel\n');
  f.save(occupied, sentinel);
  const config = f.finalizeConfig(composeAuthorities(f.config, f.r)); let ordinal = 0;
  for (const changed of [
    {...config, sidecar_output: 'coordination/engineering/foreign/sidecar.json'},
    {...config, sidecar_output: f.owned + 'preparation.json'},
    {...config, sidecar_output: f.owned + 'package-inputs.json'},
    {...config, sidecar_output: occupied},
    {...config, sidecar: f.r.pin(f.config.selector.commit, JSON.parse(f.accepted['ownership-selection.json']).additive_release.path)},
    {...config, patch: {...config.patch, sha256: '0'.repeat(64)}},
    {...config, runtime_envelope: {...config.runtime_envelope, sha256: '0'.repeat(64)}},
  ]) {
    const destination = '.cache/delivery-handoff/refused-final-' + ordinal++, result = f.run('finalize', destination, [], changed);
    assert.notEqual(result.status, 0); assert.match(result.stderr, /sidecar output|existing committed body|hash differs/);
    assert.equal(fs.existsSync(path.join(f.root, destination)), false);
    assert.deepEqual(fs.readFileSync(path.join(f.root, occupied)), sentinel);
  }
});


function modernGroups(config, originals) {
  const fields = ['rule_preimage', 'source_authority', 'ledger', 'native_patch'];
  const result = {...config, authorities: originals.map(original => Object.fromEntries(fields.map(key => [key, original[key]])))};
  for (const key of fields) delete result[key];
  return result;
}

function secondModernDelta(state) {
  state.source.retained_metadata = 'independently-qualified-second-original';
  state.native.rows = [{y: 3, runs: [[4, 5, 1]]}];
  state.row.native_rows = structuredClone(state.native.rows); state.row.native_cells = 1;
}

for (const mixed of [false, true]) test('multiple modern originals compose once with separate custody and unchanged selected baseline' + (mixed ? ' and legacy rows' : ''), t => {
  const f = modernCompositionFixture(t, {mixed});
  const second = f.makeAppend(secondModernDelta, f.owned + 'second/');
  const config = modernGroups(f.config, [f.config, second]);
  assert.deepEqual(composeAuthorities(modernGroups(f.config, [f.config]), f.r), composeAuthorities(f.config, f.r),
    'singleton array preserves existing products byte for byte');
  const products = composeAuthorities(config, f.r);
  assert.deepEqual(composeAuthorities({...config, authorities: [...config.authorities].reverse()}, f.r), products,
    'independent originals produce order-independent cumulative bytes');
  const destination = '.cache/delivery-handoff/multiple-compose';
  const run = f.run('compose', destination, [], config); assert.equal(run.status, 0, run.stderr);
  for (const [name, raw] of Object.entries(products)) assert.deepEqual(fs.readFileSync(path.join(f.root, destination, name)), raw);
  const registry = JSON.parse(products['authority-registry.json']), ledger = JSON.parse(products['selected-ledger.json']);
  assert.equal(registry.entries.length, f.priorRegistry.entries.length + 2);
  for (const original of [f.config, second]) {
    const entry = registry.entries.find(value => value.source_authority.sha256 === original.source_authority.sha256);
    assert.ok(entry); assert.deepEqual(entry.source_authority, original.source_authority);
    assert.deepEqual(entry.rule_preimage, original.rule_preimage);
    const qualified = f.r.json(original.ledger);
    for (const row of qualified.ledger_rows) assert.deepEqual(ledger.rows.find(value => value.component_id === row.component_id),
      {...row, authority_sha256: entry.authority_sha256, rule_sha256: entry.rule_sha256});
  }
  for (const row of f.priorLedger.rows) assert.deepEqual(ledger.rows.find(value => value.component_id === row.component_id), row);
  for (const key of ['parent_inventory', 'current_rebind', 'current_targets']) assert.deepEqual(ledger[key], f.priorLedger[key]);
  assert.deepEqual(JSON.parse(products['patch.json']).rows, [...f.priorPatch.rows, {y: 3, runs: [[2, 5, 1]]}]);
  const resume = f.run('compose', destination, ['--resume'], config); assert.equal(resume.status, 0, resume.stderr);
  const finalConfig = f.finalizeConfig(products), finalDestination = '.cache/delivery-handoff/multiple-final';
  const final = f.run('finalize', finalDestination, [], finalConfig); assert.equal(final.status, 0, final.stderr);
  const finalRead = name => JSON.parse(fs.readFileSync(path.join(f.root, finalDestination, name)));
  assert.equal(finalRead('selected-delivery-expectations.json').cumulative_native_cells, mixed ? 6 : 5);
  const finalSelector = finalRead('ownership-selection.json'); delete finalSelector.additive_release;
  assert.equal(JSON.stringify(finalSelector), JSON.stringify(JSON.parse(f.originalSelector)));
  assert.deepEqual(finalRead('package-inputs.json').inputs.slice(0, JSON.parse(f.accepted['package-inputs.json']).inputs.length),
    JSON.parse(f.accepted['package-inputs.json']).inputs);
});

test('multiple modern originals reject mixed/empty groups, duplicate authorities/components and cross-original overlaps', t => {
  const f = modernCompositionFixture(t); let ordinal = 0;
  const second = f.makeAppend(secondModernDelta, f.owned + 'second/');
  const config = modernGroups(f.config, [f.config, second]);
  const refusal = (input, pattern) => {
    const destination = '.cache/delivery-handoff/multiple-refused-' + ordinal++;
    const result = f.run('compose', destination, [], input); assert.notEqual(result.status, 0); assert.match(result.stderr, pattern);
    assert.equal(fs.existsSync(path.join(f.root, destination)), false);
  };
  refusal({...config, rule_preimage: f.config.rule_preimage}, /mix singleton/);
  refusal({...config, authorities: []}, /nonempty/);
  refusal({...config, authorities: [{}]}, /pin groups/);
  refusal(modernGroups(f.config, [f.config, f.config]), /already selected or duplicated/);
  const sameEvidence = f.makeAppend(s => {
    s.native.rows = [{y: 3, runs: [[4, 5, 1]]}]; s.row.native_rows = structuredClone(s.native.rows); s.row.native_cells = 1;
  }, f.owned + 'same-source/');
  refusal(modernGroups(f.config, [f.config, sameEvidence]), /Foreign or duplicate modern component/);
  for (const [change, pattern] of [
    [s => { s.native.rows = [{y: 3, runs: [[3, 5, 1]]}]; s.row.native_rows = structuredClone(s.native.rows); s.row.native_cells = 2; }, /overlap/],
    [s => { s.source.native_contract.method = 'wrong'; }, /baseline\/contract/],
    [s => { s.source.base_reference.id = 'geography:wrong'; }, /baseline\/contract/],
    [s => { s.row.source_receipt_sha256 = '0'.repeat(64); }, /source target\/owner\/receipt/],
    [s => { s.native.rows[0].runs[0][2] = 2; }, /ledger intervals differ/],
  ]) {
    const next = f.makeAppend(s => { secondModernDelta(s); change(s); }, f.owned + 'bad-' + ordinal + '/');
    refusal(modernGroups(f.config, [f.config, next]), pattern);
  }
  const badPin = structuredClone(config); badPin.authorities[1].native_patch.sha256 = '0'.repeat(64);
  refusal(badPin, /hash differs/);
});


test('publication refuses nested original-role copies before creating output', t => {
  const root = directory(t), raw = jsonBytes({original: true});
  const destination = '.cache/delivery-handoff/refused-nested';
  assert.throws(() => publish(root, destination, {'package-roles.json': jsonBytes({paths: []}),
    'restored-read-roles/coordination/engineering/original/source.json': raw}, {}), /flat product filenames/);
  assert.equal(fs.existsSync(path.join(root, '.cache')), false);
});

test('flat publication preserves prior completed trees and refuses post-admission mutation', t => {
  const root = directory(t), destination = '.cache/delivery-handoff/historical';
  const oldBody = jsonBytes({original: true}), receipt = jsonBytes({historical: true});
  write(root, destination + '/restored-read-roles/original.json', oldBody);
  write(root, destination + '/preparation.json', receipt);
  assert.throws(() => publish(root, destination, {'flat.json': jsonBytes({new: true})}, {}, true), /foreign resumed output inventory/);
  assert.deepEqual(fs.readFileSync(path.join(root, destination, 'restored-read-roles/original.json')), oldBody);
  assert.deepEqual(fs.readFileSync(path.join(root, destination, 'preparation.json')), receipt);
  const products = {'flat.json': jsonBytes({value: 1})};
  const publishAdmitted = admitPublication(root, '.cache/delivery-handoff/fresh', products, {});
  products['flat.json'].fill(0);
  assert.throws(publishAdmitted, /Admitted products changed/);
  assert.equal(fs.existsSync(path.join(root, '.cache/delivery-handoff/fresh')), false);
});
