import test from 'node:test';

import assert from 'node:assert/strict';

import fs from 'node:fs';

import os from 'node:os';

import path from 'node:path';

import {fileURLToPath} from 'node:url';

import childProcess, {execFileSync} from 'node:child_process';

import zlib, {gzipSync} from 'node:zlib';

import crypto from 'node:crypto';

import {syncBuiltinESMExports} from 'node:module';

import {jsonBytes, digest, pinReader, publish, admitPublication, prepareRequests, retainProducts, nativeRequests, rebindCustody, requestProfile} from '../scripts/prepare-delivery-handoff.mjs';

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

test('immutable Git input reader rejects whole-body drift, missing objects and nonordinary pins', t => {
  const root = directory(t); const git = (...args) => execFileSync('git', args, {cwd: root, stdio: ['pipe', 'pipe', 'pipe']}).toString().trim();
  git('init'); git('config', 'user.name', 'Fixture'); git('config', 'user.email', 'fixture@example.invalid'); write(root, 'input.json', jsonBytes({value: 1}));
  git('add', 'input.json'); git('commit', '-m', 'Fixture'); const r = pinReader(root), pin = r.pin(git('rev-parse', 'HEAD'), 'input.json');
  assert.equal(r.json(pin).value, 1); assert.throws(() => r.read({...pin, path: 'missing.json'}), /Missing ordinary/); assert.throws(() => r.read({...pin, sha256: '0'.repeat(64)}), /hash differs/);
  assert.throws(() => r.read({...pin, mode: '120000'}), /identity/); assert.throws(() => r.read({...pin, path: '../input.json'}), /safe/);
});

function immutableReaderFixture(t) {
  const root = directory(t);
  const git = (...args) => execFileSync('git', args, {cwd: root, stdio: ['pipe', 'pipe', 'pipe']}).toString().trim();
  git('init'); git('config', 'user.name', 'Fixture'); git('config', 'user.email', 'fixture@example.invalid');
  write(root, 'input.json', jsonBytes({value: 1}));
  write(root, 'alias.json', jsonBytes({value: 1}));
  git('add', '.'); git('commit', '-m', 'Fixture');
  return {root, git, head: git('rev-parse', 'HEAD')};
}

test('immutable Git input reader reuses exact descriptor queries without trusting returned copies or requested hashes', t => {
  const {root, head} = immutableReaderFixture(t), r = pinReader(root);
  const execute = childProcess.execFileSync, calls = [];
  childProcess.execFileSync = (command, args, options) => {
    if (command === 'git' && options?.cwd === root) calls.push(args);
    return execute(command, args, options);
  }; syncBuiltinESMExports();
  try {
    const pin = r.pin(head, 'input.json'), descriptor = r.descriptor(head, 'input.json');
    descriptor.bytes++; descriptor.git_blob_oid = '0'.repeat(40);
    assert.equal(r.descriptor(head, 'input.json').bytes, pin.bytes);
    assert.equal(r.descriptor(head, 'input.json').git_blob_oid, pin.git_blob_oid);
    assert.equal(r.json(pin).value, 1);
    assert.deepEqual(r.pin(head, 'input.json'), pin);
    for (const changed of [{...pin, bytes: pin.bytes + 1}, {...pin, mode: '100755'},
      {...pin, git_blob_oid: '0'.repeat(40)}]) assert.throws(() => r.read(changed), /identity differs/);
    assert.throws(() => r.read({...pin, sha256: '0'.repeat(64)}), /hash differs/);
    const exposed = r.read(pin); exposed[0] ^= 1;
    assert.throws(() => r.read(pin), /hash differs/);
    assert.equal(calls.filter(args => args[0] === 'ls-tree').length, 1);
    // One descriptor size query and the existing bounded body-read size query.
    assert.equal(calls.filter(args => args[0] === 'cat-file' && args[1] === '-s').length, 2);
    assert.equal(calls.filter(args => args[0] === 'cat-file' && args[1] === 'blob').length, 1);
  } finally { childProcess.execFileSync = execute; syncBuiltinESMExports(); }
});

test('immutable Git input reader separates exact paths, vintages and fresh readers', t => {
  const {root, git, head} = immutableReaderFixture(t), r = pinReader(root);
  const first = r.pin(head, 'input.json'), alias = r.pin(head, 'alias.json');
  assert.equal(first.git_blob_oid, alias.git_blob_oid); assert.notEqual(first.path, alias.path);
  write(root, 'input.json', jsonBytes({value: 2})); git('add', '.'); git('commit', '-m', 'Changed');
  const next = r.pin(git('rev-parse', 'HEAD'), 'input.json');
  assert.equal(r.json(next).value, 2); assert.equal(r.json(first).value, 1);
  assert.throws(() => r.read({...first, path: 'alias.json', bytes: first.bytes + 1}), /identity differs/);
  const exposed = r.read(first); exposed[0] ^= 1;
  assert.throws(() => r.read(first), /hash differs/);
  assert.equal(pinReader(root).json(first).value, 1);
});

test('immutable Git input reader validates before lookup and never caches missing or invalid metadata', t => {
  const {root, git, head} = immutableReaderFixture(t), r = pinReader(root);
  r.descriptor(head, 'input.json');
  const execute = childProcess.execFileSync, calls = [];
  let failSize = true;
  childProcess.execFileSync = (command, args, options) => {
    if (command === 'git' && options?.cwd === root) {
      calls.push(args);
      if (failSize && args[0] === 'cat-file' && args[1] === '-s') { failSize = false; return Buffer.from('NaN'); }
    }
    return execute(command, args, options);
  }; syncBuiltinESMExports();
  try {
    for (const [version, name] of [['main', 'input.json'], [head, '../input.json']])
      assert.throws(() => r.descriptor(version, name), /Exact commit and safe/);
    assert.equal(calls.length, 0);
    for (let i = 0; i < 2; i++) assert.throws(() => r.descriptor(head, 'missing.json'), /Missing ordinary/);
    assert.throws(() => r.descriptor(head, 'alias.json'), /Invalid whole body size/);
    assert.equal(r.descriptor(head, 'alias.json').path, 'alias.json');
    assert.equal(calls.filter(args => args[0] === 'ls-tree').length, 4);
  } finally { childProcess.execFileSync = execute; syncBuiltinESMExports(); }
  fs.symlinkSync('input.json', path.join(root, 'link.json'));
  git('add', '.'); git('update-index', '--chmod=+x', 'input.json'); git('commit', '-m', 'Nonordinary');
  const changed = git('rev-parse', 'HEAD');
  for (const name of ['input.json', 'link.json']) assert.throws(() => r.descriptor(changed, name), /Missing ordinary/);
});

test('immutable Git input reader ignores mutable replacement objects for exact commit and blob identities', t => {
  const {root, git, head} = immutableReaderFixture(t), r = pinReader(root), first = r.pin(head, 'input.json');
  write(root, 'input.json', jsonBytes({value: 2})); git('add', '.'); git('commit', '-m', 'Replacement');
  const replacement = git('rev-parse', 'HEAD'), changed = r.pin(replacement, 'input.json');
  git('replace', head, replacement);
  git('replace', first.git_blob_oid, changed.git_blob_oid);
  assert.equal(pinReader(root).json(first).value, 1);
  assert.equal(pinReader(root).pin(head, 'input.json').sha256, first.sha256);
  assert.equal(r.json(first).value, 1);
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
