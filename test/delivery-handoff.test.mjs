import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync, spawnSync} from 'node:child_process';
import zlib, {gzipSync} from 'node:zlib';
import crypto from 'node:crypto';
import {syncBuiltinESMExports} from 'node:module';
import {jsonBytes, digest, pinReader, publish, admitPublication, prepareRequests, retainProducts, nativeRequests,
  composeAuthorities, packageProjection, rebindCustody, requestProfile, finalizedSelection, finalizedPackageInputs, finalizeDelivery} from '../scripts/prepare-delivery-handoff.mjs';

import {admitPackageInputTransition, PACKAGE_PRODUCER_KIND} from '../scripts/package-inputs.mjs';
import {committedPackageInputs} from '../scripts/package-output-artifact.mjs';

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

test('retention decodes and hashes the inventory once per invocation without changing products', t => {
  const root = directory(t), f = terminalFixture(root), decoded = zlib.gunzipSync(f.inventory);
  const gunzip = zlib.gunzipSync, hash = crypto.createHash; let decodes = 0, hashes = 0;
  zlib.gunzipSync = (raw, ...args) => {
    if (Buffer.isBuffer(raw) && raw.equals(f.inventory)) decodes++;
    return gunzip(raw, ...args);
  };
  crypto.createHash = (algorithm, ...args) => {
    const result = hash(algorithm, ...args), update = result.update;
    result.update = function(raw, ...rest) {
      if (algorithm === 'sha256' && Buffer.isBuffer(raw) && raw.equals(decoded)) hashes++;
      return update.call(this, raw, ...rest);
    }; return result;
  }; syncBuiltinESMExports();
  try {
    const first = retainProducts(f.config, root, f.reader);
    assert.equal(decodes, 1); assert.equal(hashes, 1);
    assert.deepEqual(first['inventory.jsonl.gz'], f.inventory);
    assert.deepEqual(retainProducts(f.config, root, f.reader), first);
    assert.equal(decodes, 2); assert.equal(hashes, 2);
  } finally { zlib.gunzipSync = gunzip; crypto.createHash = hash; syncBuiltinESMExports(); }
});

test('retention still rejects missing, invalid and changed decoded inventory identities', t => {
  const root = directory(t), f = terminalFixture(root);
  for (const mutate of [p => delete p.uncompressed_bytes, p => p.uncompressed_bytes = 0,
    p => p.uncompressed_bytes = -1, p => p.uncompressed_bytes = 1.5,
    p => p.uncompressed_bytes--, p => p.uncompressed_bytes++,
    p => delete p.uncompressed_sha256, p => p.uncompressed_sha256 = '0'.repeat(64)]) {
    const publication = structuredClone(f.publication); mutate(publication.inventory);
    write(root, 'run/publication.json', jsonBytes(publication));
    assert.throws(() => retainProducts(f.config, root, f.reader), /inventory|outputLength|larger than/);
  }
});

test('explicit output inventories still authenticate a compressed inventory-named member', t => {
  const root = directory(t), f = terminalFixture(root);
  const publication = {...f.publication, outputs: {
    facts: {path: 'facts.json', ...f.publication.facts},
    inventory: {path: 'inventory.jsonl.gz', ...f.publication.inventory, uncompressed_sha256: '0'.repeat(64)}
  }};
  write(root, 'run/publication.json', jsonBytes(publication));
  assert.throws(() => retainProducts(f.config, root, f.reader), /Decoded output differs/);
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
    return publication;
  }
  const publication = candidate('target');
  assert.ok(retainProducts({...f.config, request: pin}, root, r)['ledger-batch.json']);
  const owners = publication.assets.find(row => row.path === 'owners-batch.json.gz');
  owners.uncompressed_bytes = 2; owners.uncompressed_sha256 = digest(Buffer.from('{}'));
  write(root, 'run/publication.json', jsonBytes(publication));
  assert.ok(retainProducts({...f.config, request: pin}, root, r)['owners-batch.json.gz']);
  owners.uncompressed_sha256 = '0'.repeat(64);
  write(root, 'run/publication.json', jsonBytes(publication));
  assert.throws(() => retainProducts({...f.config, request: pin}, root, r), /Decoded output differs/);
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
function modernFinalizationFixture(t, {completed = false, mixed = false, membership = true, cohort = false, external = false, dated = false, territorial = false, territorialParts = false, provider = false, seam = false, negativeSources = false} = {}) {
  const root = directory(t), owned = 'coordination/engineering/modern-finalize/';
  const git = (...args) => execFileSync('git', args, {cwd: root, stdio: ['pipe', 'pipe', 'pipe']}).toString().trim();
  git('init'); git('config', 'user.name', 'Finalizer fixture'); git('config', 'user.email', 'finalizer@example.invalid');
  git('config', 'gc.auto', '0'); git('config', 'maintenance.auto', 'false');
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
  if (cohort) memberPaths.push('data/macro-foundation/world-review-projection.json', 'data/macro-foundation/world-review-locations-0.json.gz');
  if (external) memberPaths.push('data/sources.json', 'data/retained-natural-earth.json');
  for (const name of memberPaths) save(name, name.endsWith('.gz') ? gzipSync(jsonBytes([{retained:name}])) : {retained: name});
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
    ...(membership ? {source_membership: {index: pin(memberPaths[0]), lineage: pin(memberPaths[1]), parts: [pin(memberPaths[2])],
      ...(cohort ? {cohort_inventory:{index:pin(memberPaths[3]),parts:[pin(memberPaths[4])]}} : {}),
      ...(external ? {negative_natural_earth:{registry:pin('data/sources.json'),source:pin('data/retained-natural-earth.json'),
        atoms:[{source_id:'TST-1',feature_ordinal:0,geometry_sha256:'a'.repeat(64)}]}} : {})}} : {})};
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
    if(territorialParts){
      const raw=jsonBytes({type:'FeatureCollection',features:[]}),cut=Math.floor(raw.length/2);
      const names=[inherited+'negative-part-0.bin.gz',inherited+'negative-part-1.bin.gz'];
      save(names[0],gzipSync(raw.subarray(0,cut)));save(names[1],gzipSync(raw.subarray(cut)));commitAll();
      body.provenance[2]={id:'original-source',role:'original-source',parts:names.map(name=>pin(name))};
    }
    const name=inherited+'territorial-applicability.json';save(name,body);commitAll();
    territorialSupport={body,path:name,pin:pin(name)};evidenceBody.territorial_applicability=territorialSupport.pin;
  }
  let providerAdoption;
  if(provider){
    const name=inherited+'adopted-provider-families.json';
    save(name,{version:1,kind:'adopted-provider-source-families-v1',families:[]});commitAll();
    providerAdoption=pin(name);evidenceBody.adopted_provider_families=providerAdoption;
  }
  let seamViews;
  if(seam){
    save('scripts/majority.py',Buffer.from('# retained canonical method'));commitAll();
    const name=inherited+'canonical-seam-views.json',method=pin('scripts/majority.py');
    save(name,{version:1,kind:'retained-periodic-native-views-v1',method:{pin:method,export:'canonical'},records:[]});commitAll();
    seamViews={pin:pin(name),method};evidenceBody.canonical_seam_views=seamViews.pin;
  }
  if(negativeSources){
    const raw=jsonBytes({type:'FeatureCollection',features:[]});
    const name=inherited+'negative-original.bin.gz';save(name,gzipSync(raw));commitAll();
    evidenceBody.territorial_exclusion_sources=[{source_id:'negative',parts:[{...pin(name),
      decoded_bytes:raw.length,decoded_sha256:digest(raw)}]}];
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
  if (completed) {
    const binding = r.json(modern.source_authority);
    const originalRows = rows.filter(row => row.authority_sha256 === modern.authority_sha256)
      .map(({authority_sha256, rule_sha256, ...row}) => row);
    save(owned + 'constructor-result.json', {version: 1, kind: 'existing-source-target-native-constructor-result',
      inputs: Object.fromEntries(['source_evidence', 'native_patch'].map(role => [role,
        {commit: binding[role].commit, path: binding[role].path}])),
      component_ids: originalRows.map(row => row.component_id), ledger_rows: originalRows,
      rule_sha256: modern.rule_sha256, limitations: ['Metadata fixture; scientific qualification is tested separately.']});
    commitAll(); modern.completed_constructor = pin(owned + 'constructor-result.json');
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
    consumed: [...Object.values(roles), familyPart, ...(membership ? memberPaths : [])], incidental, withEvidence, datedSupport, territorialSupport, providerAdoption, seamViews};
}

// Build a private object universe, not a loose-file deletion simulation. Git's
// pack writer takes this exact OID list (without --revs), so omitted historical
// blobs cannot enter through graph traversal or another object's pack delta.
function omitHistoricalObjects(t, f, omitted, storage) {
  assert.ok(!process.env.GIT_ALTERNATE_OBJECT_DIRECTORIES, 'Fixture has no ambient alternate object database');
  const ids = new Set(omitted), before = f.git('rev-parse', 'HEAD'), tree = f.git('rev-parse', 'HEAD^{tree}');
  const objects = path.resolve(f.root, f.git('rev-parse', '--git-path', 'objects'));
  assert.equal(objects, path.join(f.root, '.git', 'objects'), 'Fixture owns its ordinary object directory');
  assert.equal(fs.existsSync(path.join(objects, 'info', 'alternates')), false);
  assert.equal(f.git('remote'), '', 'Fixture has no network fallback');
  for (const oid of ids) assert.equal(f.git('cat-file', '-t', oid), 'blob');
  if (storage === 'loose') for (const oid of ids)
    assert.equal(fs.existsSync(path.join(objects, oid.slice(0, 2), oid.slice(2))), true);
  if (storage === 'packed') {
    f.git('repack', '-ad');
    assert.ok(fs.readdirSync(path.join(objects, 'pack')).some(name => name.endsWith('.pack')));
    for (const oid of ids) assert.equal(fs.existsSync(path.join(objects, oid.slice(0, 2), oid.slice(2))), false);
  }
  const all = f.git('cat-file', '--batch-all-objects', '--batch-check=%(objectname)').split('\n');
  assert.ok([...ids].every(oid => all.includes(oid)));
  const allowed = all.filter(oid => !ids.has(oid));
  const env = {...process.env, GIT_NO_LAZY_FETCH: '1'};
  const pack = execFileSync('git', ['pack-objects', '--stdout'], {cwd: f.root, env,
    input: allowed.join('\n') + '\n', maxBuffer: 16 * 1024 * 1024});
  const quarantine = fs.mkdtempSync(path.join(os.tmpdir(), 'finalizer-original-objects-'));
  t.after(() => fs.rmSync(quarantine, {recursive: true, force: true}));
  fs.renameSync(objects, path.join(quarantine, 'objects'));
  fs.mkdirSync(path.join(objects, 'pack'), {recursive: true});
  fs.mkdirSync(path.join(objects, 'info'));
  execFileSync('git', ['index-pack', '--stdin'], {cwd: f.root, env, input: pack, stdio: ['pipe', 'pipe', 'pipe']});
  assert.equal(f.git('rev-parse', 'HEAD'), before); assert.equal(f.git('rev-parse', 'HEAD^{tree}'), tree);
  assert.equal(fs.existsSync(path.join(objects, 'info', 'alternates')), false);
  assert.deepEqual(f.git('cat-file', '--batch-all-objects', '--batch-check=%(objectname)').split('\n').sort(), allowed.sort());
  for (const oid of ids) {
    const probe = spawnSync('git', ['cat-file', '-e', oid], {cwd: f.root, env, encoding: 'utf8'});
    assert.notEqual(probe.status, 0, 'Historical body must be genuinely unreadable: ' + oid);
  }
}

for (const storage of ['loose', 'packed']) test('completed-constructor finalization keeps provenance cold with ' + storage + ' history', t => {
  const f = modernFinalizationFixture(t, {completed: true, cohort: true, external: true, dated: true,
    territorial: true, territorialParts: true, provider: true, seam: true, negativeSources: true});
  const entry = f.r.json(f.config.registry).entries[0], binding = f.r.json(entry.source_authority);
  const originalEvidence = Buffer.from(f.r.read(binding.source_evidence)), leaves = new Map();
  const collect = value => {
    if (!value || typeof value !== 'object') return;
    if (value.path && value.commit && value.git_blob_oid) leaves.set(value.path, value);
    else for (const member of Object.values(value)) collect(member);
  };
  collect(f.evidenceBody); collect(f.datedSupport.body); collect(f.territorialSupport.body); collect(f.seamViews);
  for (const pin of [f.evidenceBody.catalogue, f.evidenceBody.source_membership.index,
    f.datedSupport.pin, f.territorialSupport.pin, f.providerAdoption, f.seamViews.method])
    assert.ok(leaves.has(pin.path), 'Exercise the original role: ' + pin.path);
  f.git('rm', '--', ...leaves.keys()); f.commitAll();
  f.config.package_inputs = f.pin('.github/package-inputs.json');
  omitHistoricalObjects(t, f, [...leaves.values()].map(pin => pin.git_blob_oid), storage);
  const destination = '.cache/delivery-handoff/completed-cold';
  const run = f.run('finalize', destination); assert.equal(run.status, 0, run.stderr);
  const output = name => JSON.parse(fs.readFileSync(path.join(f.root, destination, name)));
  const roles = output('package-roles.json').paths;
  for (const pin of [entry.rule_preimage, entry.source_authority, entry.completed_constructor,
    binding.source_evidence, binding.native_patch])
    assert.ok(roles.some(role => role.path === pin.path && role.sha256 === pin.sha256), pin.path);
  for (const name of leaves.keys()) assert.ok(!roles.some(role => role.path === name), name);
  assert.deepEqual(f.r.read(binding.source_evidence), originalEvidence, 'Original provenance body stays byte-identical');
  assert.equal(output('selected-delivery-expectations.json').cumulative_native_cells, 2);
  assert.ok(!f.config.restored_read_roles, 'No restoration snapshot or bypass flag');
});

for (const storage of ['loose', 'packed']) test('unqualified source-target finalization still requires historical leaf bodies with ' + storage + ' history', t => {
  const f = modernFinalizationFixture(t), leaf = f.evidenceBody.catalogue;
  f.git('rm', '--', leaf.path); f.commitAll();
  f.config.package_inputs = f.pin('.github/package-inputs.json');
  omitHistoricalObjects(t, f, [leaf.git_blob_oid], storage);
  const destination = '.cache/delivery-handoff/unqualified-cold';
  const run = f.run('finalize', destination);
  assert.notEqual(run.status, 0, 'No completed constructor means no cold-corpus route');
  assert.match(run.stderr, /cat-file|bad object|missing/i);
  assert.equal(fs.existsSync(path.join(f.root, destination)), false);
});

test('completed-constructor finalizer retains every direct immutable body check', t => {
  const f = modernFinalizationFixture(t, {completed: true});
  const entry = f.r.json(f.config.registry).entries[0], binding = f.r.json(entry.source_authority);
  for (const pin of [entry.rule_preimage, entry.source_authority, entry.completed_constructor,
    binding.source_evidence, binding.native_patch]) {
    const original = f.r.read;
    f.r.read = p => original(p.path === pin.path ? {...p, sha256: '0'.repeat(64)} : p);
    assert.throws(() => packageProjection(f.config, f.r), /hash differs/, pin.path);
    f.r.read = original;
  }
});

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

test('real package command retains every complete territorial source part without parsing a JSON chunk', t => {
  const f=modernFinalizationFixture(t,{territorial:true,territorialParts:true}),destination='.cache/delivery-handoff/multipart';
  const run=f.run('package',destination);assert.equal(run.status,0,run.stderr);
  const projection=JSON.parse(fs.readFileSync(path.join(f.root,destination,'package-roles.json')));
  for(const pin of f.territorialSupport.body.provenance[2].parts){
    const paths=projection.paths.filter(p=>p.path===pin.path);assert.equal(paths.length,1);
    assert.equal(paths[0].sha256,pin.sha256);assert.ok(paths[0].roles.includes('source-target territorial original-source'));
  }
  const evidence=structuredClone(f.evidenceBody),support=structuredClone(f.territorialSupport.body);
  support.provenance[2].parts[1].sha256='0'.repeat(64);
  f.save(f.territorialSupport.path,support);f.commitAll();evidence.territorial_applicability=f.pin(f.territorialSupport.path);
  const output='.cache/delivery-handoff/refused-multipart';
  const failed=f.run('package',output,[],f.withEvidence(evidence));assert.notEqual(failed.status,0);
  assert.match(failed.stderr,/hash differs/);assert.equal(fs.existsSync(path.join(f.root,output)),false);
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

test('delivery CLI refuses retired manifest, review-freeze and queue entry points before mutation', () => {
  const script = fileURLToPath(new URL('../scripts/prepare-delivery-handoff.mjs', import.meta.url));
  for (const args of [['evidence', 'absent-config.json', 'absent-destination'],
    ['review', 'absent-config.json', 'absent-destination'],
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
    const constructed = {version:1,kind:'existing-source-target-native-constructor-result',
      inputs:Object.fromEntries(['source_evidence','native_patch'].map(role=>[role,
        {commit:binding[role].commit,path:binding[role].path}])), component_ids: [row.component_id], ledger_rows: [row],
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
    {authority_sha256: digest(jsonBytes(authority)), ...authority, completed_constructor:f.config.ledger}, 'original authority identity plus completed output custody');
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
  const obsolete = [JSON.parse(f.accepted['ownership-selection.json']).additive_release.path, originalSidecar.runtime_envelope.path, originalSidecar.logical_asset_map.ledger.path, originalSidecar.logical_asset_map.patch.path];
  const retained = priorInputs.inputs.filter(name => !obsolete.includes(name));
  assert.deepEqual(inputs.inputs.slice(0, retained.length), retained);
  assert(obsolete.every(name => !inputs.inputs.includes(name)));
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
    [s => { s.native.rows[0].runs[0][2] = 2; }, /source target\/owner\/receipt/],
    [s => { s.row.pixelIndex = 2; s.row.native_rows[0].runs[0][2] = 2; s.native.rows[0].runs[0][2] = 2; }, /source target\/owner\/receipt/],
    [s => { s.native.rows[0].y = 2; s.row.native_rows[0].y = 2; }, /overlap/],
    [s => { s.source.base_reference.id = 'geography:wrong'; }, /baseline\/contract/],
    [s => { s.source.native_contract.method = 'wrong'; }, /baseline\/contract/],
    [s => { s.source.targets.push({...s.source.targets[0], id: 'source:B', source_family: 'foreign'}); }, /target\/family\/receipt/],
    [s => { const correct = {...s.source.targets[0], id: 'source:B'}; s.source.targets[0].source_receipt_sha256 = 'f'.repeat(64);
      s.source.targets.push(correct); }, /target\/family\/receipt/],
    [s => { s.native.rows = []; }, /source target\/owner\/receipt/],
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
  const priorSelector = JSON.parse(f.accepted['ownership-selection.json']), priorSidecar = f.r.json(f.r.pin(f.config.selector.commit, priorSelector.additive_release.path));
  const obsolete = [priorSelector.additive_release.path, priorSidecar.runtime_envelope.path, priorSidecar.logical_asset_map.ledger.path, priorSidecar.logical_asset_map.patch.path];
  const retained = JSON.parse(f.accepted['package-inputs.json']).inputs.filter(name => !obsolete.includes(name));
  assert.deepEqual(finalRead('package-inputs.json').inputs.slice(0, retained.length), retained);
  assert(obsolete.every(name => !finalRead('package-inputs.json').inputs.includes(name)));
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
  const sameLabel = composeAuthorities(modernGroups(f.config, [f.config, sameEvidence]), f.r);
  const repeated = JSON.parse(sameLabel['selected-ledger.json']).rows.filter(row => row.component_id === f.r.json(f.config.ledger).component_ids[0]);
  assert.equal(repeated.length, 2); assert.notEqual(repeated[0].authority_sha256, repeated[1].authority_sha256);
  assert.deepEqual(repeated.map(row => row.native_cells).sort(), [1, 2]);
  for (const [change, pattern] of [
    [s => { s.native.rows = [{y: 3, runs: [[3, 5, 1]]}]; s.row.native_rows = structuredClone(s.native.rows); s.row.native_cells = 2; }, /overlap/],
    [s => { s.source.native_contract.method = 'wrong'; }, /baseline\/contract/],
    [s => { s.source.base_reference.id = 'geography:wrong'; }, /baseline\/contract/],
    [s => { s.row.source_receipt_sha256 = '0'.repeat(64); }, /source target\/owner\/receipt/],
    [s => { s.native.rows[0].runs[0][2] = 2; }, /source target\/owner\/receipt/],
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

test('real package projection retains the provider-adoption leaf and its existing family/member roles',t=>{
 const f=modernFinalizationFixture(t,{provider:true}),destination='.cache/delivery-handoff/provider';
 const run=f.run('package',destination);assert.equal(run.status,0,run.stderr);
 const projection=JSON.parse(fs.readFileSync(path.join(f.root,destination,'package-roles.json')));
 const matches=projection.paths.filter(pin=>pin.path===f.providerAdoption.path);
 assert.equal(matches.length,1);assert.equal(matches[0].sha256,f.providerAdoption.sha256);
 assert.ok(matches[0].roles.includes('source-target adopted provider families'));
 for(const name of f.consumed)assert.ok(projection.paths.some(pin=>pin.path===name),name);
 const evidence=structuredClone(f.evidenceBody);evidence.adopted_provider_families.sha256='0'.repeat(64);
 const failed=f.run('package','.cache/delivery-handoff/provider-refused',[],f.withEvidence(evidence));
 assert.notEqual(failed.status,0);assert.match(failed.stderr,/hash differs/);
 assert.equal(fs.existsSync(path.join(f.root,'.cache/delivery-handoff/provider-refused','preparation.json')),false);
});


test('finalizer authenticates and parses a shared cumulative selected ledger only once per invocation',t=>{
  const f=modernFinalizationFixture(t),reader=f.r;
  f.config.ledger=f.config.selected_ledger;
  const selected=reader.read(f.config.selected_ledger),oid=f.config.selected_ledger.git_blob_oid;
  const read=reader.read,json=reader.json,hash=crypto.createHash,parse=JSON.parse;let reads=0,parses=0,hashes=0;
  reader.read=pin=>{if(pin.git_blob_oid===oid)reads++;return read(pin);};
  reader.json=pin=>JSON.parse(reader.read(pin));
  JSON.parse=(raw,...args)=>{if(Buffer.isBuffer(raw)&&raw.equals(selected))parses++;return parse(raw,...args);};
  crypto.createHash=(algorithm,...args)=>{
    const result=hash(algorithm,...args),update=result.update;
    result.update=function(raw,...rest){
      if(algorithm==='sha256'&&Buffer.isBuffer(raw)&&raw.equals(selected))hashes++;
      return update.call(this,raw,...rest);
    };return result;
  };syncBuiltinESMExports();
  try{
    const products=finalizeDelivery(f.config,reader);
    assert.equal(JSON.parse(products['selected-delivery-expectations.json']).selected_ledger_sha256,f.config.selected_ledger.sha256);
    console.log('ACTUAL_SELECTED_LEDGER_WORK',JSON.stringify({reads,parses,hashes}));
    assert.equal(reads,1);assert.equal(parses,1);assert.equal(hashes,1);
  }finally{reader.read=read;reader.json=json;JSON.parse=parse;crypto.createHash=hash;syncBuiltinESMExports();}
});

test('finalizer reuses only its owned rows for conservation and normalized projections',t=>{
  const f=modernFinalizationFixture(t,{mixed:true});
  f.config.ledger=f.config.selected_ledger;
  const raw=f.r.read(f.config.selected_ledger),ledger=JSON.parse(raw),registry=f.r.json(f.config.registry);
  const rowBytes=jsonBytes(ledger.rows),scopeBytes=jsonBytes(ledger.scope_ids);
  const complete=new Set([rowBytes.toString(),scopeBytes.toString()]);
  const expected=finalizeDelivery(f.config,f.r),parse=JSON.parse,from=Buffer.from;
  let traversals=0,visits=0;const allocations=[];
  JSON.parse=(body,...args)=>{
    const value=parse(body,...args);
    if(Buffer.isBuffer(body)&&body.equals(raw))Object.defineProperty(value.rows,Symbol.iterator,{value:function*(){
      traversals++;for(let i=0;i<this.length;i++){visits++;yield this[i];}
    }});
    return value;
  };
  Buffer.from=function(value,...args){
    if(typeof value==='string'&&complete.has(value))allocations.push(Buffer.byteLength(value));
    return from.call(this,value,...args);
  };
  let actual;
  try{actual=finalizeDelivery(f.config,f.r);}finally{JSON.parse=parse;Buffer.from=from;}
  assert.deepEqual(actual,expected,'Every emitted finalizer byte is unchanged by observation');
  assert.deepEqual(f.r.read(f.config.selected_ledger),raw,'The original selected body is unchanged');
  t.diagnostic(JSON.stringify({authorities:registry.entries.length,rows:ledger.rows.length,traversals,visits,
    completeCanonicalAllocations:allocations,rowsBytes:rowBytes.length,scopeBytes:scopeBytes.length}));
  assert.deepEqual(allocations,[],'No complete rows/scope canonical Buffer is needed to compare the owned snapshot to itself');
  assert.equal(traversals,3,'Two validation traversals plus one normalized collection');
  assert.equal(visits,3*ledger.rows.length);
});

test('public package projection cannot claim the finalizer snapshot or bypass permissive serialization',t=>{
  const f=modernFinalizationFixture(t,{mixed:true}),ledger=f.r.json(f.config.selected_ledger);
  const config={...f.config,ledger:f.config.selected_ledger};
  const reader={...f.r,json(pin){return pin.git_blob_oid===config.selected_ledger.git_blob_oid?ledger:f.r.json(pin);}};
  const held=ledger.rows.find(row=>row.disposition==='awaiting-evidence');
  assert.ok(held);
  const iterate=ledger.rows[Symbol.iterator],authorities=f.r.json(config.registry).entries.length;let traversals=0;
  Object.defineProperty(ledger.rows,Symbol.iterator,{value:function*(){traversals++;yield* iterate.call(this);}});
  const expected=packageProjection(config,reader);
  assert.equal(traversals,authorities+3,'Caller-owned normalized views are still collected at every original boundary');
  traversals=0;
  held.ignored_metadata={nonfinite:Infinity,omitted:undefined};
  assert.deepEqual(packageProjection(config,reader,null,ledger),expected,
    'Ignored metadata keeps JSON.stringify semantics and a public fourth argument grants no capability');
  assert.equal(traversals,authorities+3);
  held.ignored_metadata=1n;
  assert.throws(()=>packageProjection(config,reader,null,ledger),/BigInt/,
    'Even the same public object still undergoes complete serialization');
});

test('public package projection still compares different row and scope views and requires current metadata',t=>{
  const f=modernFinalizationFixture(t),ledger=f.r.json(f.config.selected_ledger);
  const config={...f.config,ledger:f.config.selected_ledger};
  for(const mutate of [value=>{value.rows[0].ignored_metadata='changed';},value=>{value.scope_ids[0]='changed';},
    value=>{delete value.current_rebind;},value=>{delete value.current_targets;}]){
    const selected=structuredClone(ledger);mutate(selected);let reads=0;
    const reader={...f.r,json(pin){return pin.git_blob_oid===config.selected_ledger.git_blob_oid
      ? ++reads===1?ledger:selected:f.r.json(pin);}};
    assert.throws(()=>packageProjection(config,reader,null,ledger),/does not conserve/);
  }
});

test('finalizer retains complete conservation for a distinct caller-owned composed ledger',t=>{
  const f=modernFinalizationFixture(t,{mixed:true}),json=f.r.json;
  f.r.json=pin=>{
    const value=json(pin);
    if(pin.git_blob_oid===f.config.ledger.git_blob_oid)
      value.rows.find(row=>row.disposition==='awaiting-evidence').ignored_metadata='changed';
    return value;
  };
  assert.throws(()=>finalizeDelivery(f.config,f.r),/does not conserve/);
});


test('finalizer selected snapshot isolates mutable reader bytes and authenticates anew on the next call',t=>{
  const f=modernFinalizationFixture(t),reader=f.r;
  f.config.ledger=f.config.selected_ledger;
  const raw=reader.read(f.config.selected_ledger),json=reader.json;let changed=false;
  reader.json=pin=>{
    if(!changed&&pin.path===f.config.registry.path){raw.fill(0);changed=true;}
    return json(pin);
  };
  const result=finalizeDelivery(f.config,reader);
  assert.equal(JSON.parse(result['selected-delivery-expectations.json']).selected_ledger_sha256,f.config.selected_ledger.sha256);
  assert.equal(changed,true);
  assert.throws(()=>finalizeDelivery(f.config,reader),/Whole body hash differs/);
});

test('finalizer snapshot does not hide a changed selected-ledger role descriptor',t=>{
  const f=modernFinalizationFixture(t),reader=f.r;
  f.config.ledger=f.config.selected_ledger;
  const json=reader.json;let changed=false;
  reader.json=pin=>{
    if(!changed&&pin.path===f.config.registry.path){f.config.ledger.sha256='0'.repeat(64);changed=true;}
    return json(pin);
  };
  assert.throws(()=>finalizeDelivery(f.config,reader),/Whole body hash differs/);
  assert.equal(changed,true);
});

test('cumulative snapshot retains coherent changed-row and rebind refusals',t=>{
  for(const kind of ['rows','rebind']){
    const f=modernFinalizationFixture(t),r=f.r,sidecar=r.json(f.config.sidecar);
    const selected=r.json(f.config.selected_ledger),patch=r.json(sidecar.logical_asset_map.patch);
    const wrapped=r.json(sidecar.runtime_envelope),envelope=wrapped.additiveRelease;
    if(kind==='rows')selected.rows[0].native_cells++;
    else selected.current_rebind=f.config.registry;
    f.save(f.config.selected_ledger.path,selected);f.commitAll();
    const next=f.pin(f.config.selected_ledger.path);
    f.config.ledger=next;f.config.selected_ledger=next;
    patch.ledger_sha256=next.sha256;
    f.save(sidecar.logical_asset_map.patch.path,patch);f.commitAll();
    const nextPatch=f.pin(sidecar.logical_asset_map.patch.path);
    Object.assign(envelope.ledger,{bytes:next.bytes,sha256:next.sha256});
    Object.assign(envelope.patch,{bytes:nextPatch.bytes,sha256:nextPatch.sha256});
    f.save(sidecar.runtime_envelope.path,wrapped);f.commitAll();
    sidecar.runtime_envelope=f.pin(sidecar.runtime_envelope.path);
    sidecar.logical_asset_map.ledger=next;sidecar.logical_asset_map.patch=nextPatch;
    f.save(f.config.sidecar.path,sidecar);f.commitAll();f.config.sidecar=f.pin(f.config.sidecar.path);
    assert.throws(()=>finalizeDelivery(f.config,r),kind==='rows'?/Native component cell count differs/:/metadata joins differ/);
  }
});


test('package roles retain the explicit canonical seam table and exact retained method',t=>{
  const f=modernFinalizationFixture(t,{seam:true}),destination='.cache/delivery-handoff/seam';
  const run=f.run('package',destination);assert.equal(run.status,0,run.stderr);
  const projection=JSON.parse(fs.readFileSync(path.join(f.root,destination,'package-roles.json')));
  for(const pin of [f.seamViews.pin,f.seamViews.method]){
    const matches=projection.paths.filter(entry=>entry.path===pin.path);
    assert.equal(matches.length,1);assert.equal(matches[0].sha256,pin.sha256);
  }
  for(const label of ['views','method'])assert.ok(projection.paths.some(entry=>
    entry.roles.includes('source-target canonical seam '+label)));
});

test('real package command preserves complete canonical cohort pins and rejects malformed roles',t=>{
 const f=modernFinalizationFixture(t,{cohort:true});
 const accepted=f.run('package','.cache/delivery-handoff/cohort-complete');
 assert.equal(accepted.status,0,accepted.stderr);
 const output=JSON.parse(fs.readFileSync(path.join(f.root,'.cache/delivery-handoff/cohort-complete/package-roles.json')));
 for(const pin of [f.evidenceBody.source_membership.cohort_inventory.index,...f.evidenceBody.source_membership.cohort_inventory.parts])
  assert(output.paths.some(item=>item.path===pin.path),'Missing cohort consumed path '+pin.path);
 let ordinal=0;
 for(const mutate of [role=>delete role.index,role=>role.parts=[],role=>role.index.sha256='0'.repeat(64),
  role=>role.parts[0].sha256='0'.repeat(64),role=>role.extra=role.index]){
  const body=structuredClone(f.evidenceBody);mutate(body.source_membership.cohort_inventory);
  const result=f.run('package','.cache/delivery-handoff/cohort-rejected-'+ordinal++,[],f.withEvidence(body));
  assert.notEqual(result.status,0);assert.match(result.stderr,/cohort|hash differs/);
 }
});

test('package closes exact complete negative reference sources without broad pin walking',t=>{
 const f=modernFinalizationFixture(t,{negativeSources:true}),destination='.cache/delivery-handoff/negative-complete';
 const accepted=f.run('package',destination);assert.equal(accepted.status,0,accepted.stderr);
 const output=JSON.parse(fs.readFileSync(path.join(f.root,destination,'package-roles.json'))),
   original=f.evidenceBody.territorial_exclusion_sources[0].parts[0];
 assert.ok(output.paths.some(item=>item.path===original.path&&item.sha256===original.sha256
   &&item.roles.includes('source-target territorial source part')));
 let ordinal=0;
 for(const mutate of [sources=>sources[0].parts=[],sources=>sources.push(sources[0]),
   sources=>sources[0].source_id='',sources=>sources[0].parts[0].sha256='0'.repeat(64),
   sources=>sources[0].extra=sources[0].parts[0]]){
  const body=structuredClone(f.evidenceBody);mutate(body.territorial_exclusion_sources);
  const result=f.run('package','.cache/delivery-handoff/negative-rejected-'+ordinal++,[],f.withEvidence(body));
  assert.notEqual(result.status,0);assert.match(result.stderr,/territorial|hash differs/);
 }
});

test('real package command preserves complete external negative source roles and rejects malformed pins',t=>{
 const f=modernFinalizationFixture(t,{external:true,cohort:true});
 const accepted=f.run('package','.cache/delivery-handoff/negative-external-complete');
 assert.equal(accepted.status,0,accepted.stderr);
 const output=JSON.parse(fs.readFileSync(path.join(f.root,'.cache/delivery-handoff/negative-external-complete/package-roles.json')));
 for(const key of ['registry','source'])assert(output.paths.some(item=>item.path===f.evidenceBody.source_membership.negative_natural_earth[key].path));
 let ordinal=0;
 for(const mutate of [role=>delete role.registry,role=>delete role.source,role=>role.atoms=[],
  role=>role.source.sha256='0'.repeat(64),role=>role.registry.sha256='0'.repeat(64),role=>role.extra=role.source]){
  const body=structuredClone(f.evidenceBody);mutate(body.source_membership.negative_natural_earth);
  const result=f.run('package','.cache/delivery-handoff/negative-external-rejected-'+ordinal++,[],f.withEvidence(body));
  assert.notEqual(result.status,0);assert.match(result.stderr,/Natural Earth|hash differs/);
 }
});

test('combined external ancestry and complete negative reference sources retain both package roles',t=>{
 const f=modernFinalizationFixture(t,{external:true,cohort:true,negativeSources:true});
 const destination='.cache/delivery-handoff/combined-negative-roles',accepted=f.run('package',destination);
 assert.equal(accepted.status,0,accepted.stderr);
 const output=JSON.parse(fs.readFileSync(path.join(f.root,destination,'package-roles.json')));
 for(const pin of [f.evidenceBody.territorial_exclusion_sources[0].parts[0],
  ...['registry','source'].map(key=>f.evidenceBody.source_membership.negative_natural_earth[key])])
  assert(output.paths.some(item=>item.path===pin.path&&item.sha256===pin.sha256),'Both complete negative role sets remain consumed');
});


test('successive finalizations replace authenticated cumulative roots and preserve unrelated and shared inputs', t => {
  const f=modernCompositionFixture(t), products=composeAuthorities(f.config,f.r);
  let config=f.finalizeConfig(products);
  const unrelated='coordination/engineering/unrelated/selected-ledger.json';
  const optional='coordination/engineering/unrelated/patch.json';
  f.save(unrelated,{unrelated:true});f.save(optional,{optional:true});
  const original=f.r.json(config.package_inputs);
  original.inputs.push(unrelated,optional);original.optional_inputs.push(optional);
  f.save('.github/package-inputs.json',original);f.commitAll();config={...config,package_inputs:f.pin('.github/package-inputs.json')};
  const source = () => {
    const definition=JSON.parse(fs.readFileSync(path.join(f.root,'.github/package-inputs.json')));
    return {head:f.git('rev-parse','HEAD'),definition,files:committedPackageInputs(f.root,definition),
      producer:{kind:PACKAGE_PRODUCER_KIND,workflows:[]},
      selection:JSON.parse(fs.readFileSync(path.join(f.root,'data/ownership-selection.json')))};
  };
  const initial=source(), priorSidecarRaw=fs.readFileSync(path.join(f.root,initial.selection.additive_release.path));
  let expectedCount;
  for(let round=0;round<3;round++){
    const output=finalizeDelivery(config,f.r),definition=JSON.parse(output['package-inputs.json']),selector=JSON.parse(output['ownership-selection.json']);
    expectedCount??=definition.inputs.length;assert.equal(definition.inputs.length,expectedCount);
    assert(definition.inputs.includes(unrelated));assert(definition.inputs.includes(optional));assert(definition.optional_inputs.includes(optional));
    const sidecar=JSON.parse(output[path.posix.basename(config.sidecar_output)]);
    for(const role of ['base_manifest','owner_roster'])assert(definition.inputs.includes(sidecar.logical_asset_map[role].path));
    const prior=f.r.json(f.r.pin(config.selector.commit,f.r.json(config.selector).additive_release.path));
    for(const pin of [prior.runtime_envelope,prior.logical_asset_map.ledger,prior.logical_asset_map.patch])
      if(!Object.values(sidecar.logical_asset_map).some(p=>p.path===pin.path)&&sidecar.runtime_envelope.path!==pin.path)assert(!definition.inputs.includes(pin.path));
    f.save(config.sidecar_output,output[path.posix.basename(config.sidecar_output)]);
    f.save('data/ownership-selection.json',output['ownership-selection.json']);f.save('.github/package-inputs.json',output['package-inputs.json']);f.commitAll();
    const current=source();
    const admitted=admitPackageInputTransition(initial,current,{priorSidecarRaw});
    assert(admitted.removed_selected_inputs.length>0);
    assert.throws(()=>admitPackageInputTransition(initial,current),/authenticated prior cumulative/);
    const changed=Buffer.from(priorSidecarRaw);changed[0]^=1;
    assert.throws(()=>admitPackageInputTransition(initial,current,{priorSidecarRaw:changed}),/authenticated prior cumulative/);
    const omitted=structuredClone(current);
    omitted.definition.inputs=omitted.definition.inputs.filter(name=>name!==unrelated);
    omitted.files=omitted.files.filter(row=>row.path!==unrelated);
    assert.throws(()=>admitPackageInputTransition(initial,omitted,{priorSidecarRaw}),/not an authenticated prior cumulative role/);
    const drift=structuredClone(initial);
    drift.files.find(row=>admitted.removed_selected_inputs.includes(row.path)).oid='0'.repeat(40);
    assert.throws(()=>admitPackageInputTransition(drift,current,{priorSidecarRaw}),/differs from original source inventory/);
    const next='coordination/engineering/repeated-'+round+'/';
    for(const [name,pin] of [['selected-ledger.json',config.selected_ledger],['patch.json',config.patch],['runtime-envelope.json',config.runtime_envelope]])f.save(next+name,f.r.read(pin));
    f.commitAll();config={...config,selector:f.pin('data/ownership-selection.json'),package_inputs:f.pin('.github/package-inputs.json'),new_prefix:next,sidecar_output:next+'selection-sidecar.json',selected_ledger:f.pin(next+'selected-ledger.json'),patch:f.pin(next+'patch.json'),runtime_envelope:f.pin(next+'runtime-envelope.json')};
  }
});


test('finalization does not narrow an unrelated accepted directory declaration',t=>{
 const f=modernCompositionFixture(t),config=f.finalizeConfig(composeAuthorities(f.config,f.r));
 const definition=f.r.json(config.package_inputs),selector=f.r.json(config.selector),prior=f.r.json(f.r.pin(config.selector.commit,selector.additive_release.path));
 const directory=path.posix.dirname(selector.additive_release.path)+'/';
 definition.inputs=definition.inputs.filter(p=>!p.startsWith(directory));definition.inputs.push(directory);
 f.save('.github/package-inputs.json',definition);f.commitAll();
 const output=finalizeDelivery({...config,package_inputs:f.pin('.github/package-inputs.json')},f.r);
 assert(JSON.parse(output['package-inputs.json']).inputs.includes(directory));
});

test('malformed prior cumulative role cannot authorize package input removal',t=>{
 const f=modernCompositionFixture(t),config=f.finalizeConfig(composeAuthorities(f.config,f.r));
 const selector=f.r.json(config.selector),prior=f.r.json(f.r.pin(config.selector.commit,selector.additive_release.path));
 prior.logical_asset_map.ledger.path='../unrelated.json';f.save(selector.additive_release.path,prior);f.commitAll();
 const pin=f.pin(selector.additive_release.path);selector.additive_release={path:pin.path,bytes:pin.bytes,sha256:pin.sha256};
 f.save('data/ownership-selection.json',selector);f.commitAll();
 assert.throws(()=>finalizeDelivery({...config,selector:f.pin('data/ownership-selection.json')},f.r),/prior cumulative package roles/);
});
