import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {gzipSync} from 'node:zlib';
import {candidateBudget} from '../scripts/native-ownership/native-preparation-guards.mjs';
import {renderClaim} from '../scripts/issue-claim-contract.mjs';
import {subjectsHash} from '../scripts/evidence-quality.mjs';
import {jsonBytes, digest, pinReader, publish, prepareRequests, retainProducts, nativeRequests,
  composeAuthorities, packageProjection, rebindCustody, requestProfile, finalizedSelection, finalizedPackageInputs, finalizeDelivery, prepareEvidence, freezeReview} from '../scripts/prepare-delivery-handoff.mjs';

const commit = 'a'.repeat(40), prefix = 'coordination/engineering/control/';
function memoryReader({admit = true} = {}) {
  const bodies = new Map(), pins = new Map(); let ordinal = 0;
  const reader = {budget: admit ? candidateBudget([], {reserveBytes: 0, reserveDescriptors: 0}) : null,
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

test('combined read/output budget fails before creating destination', t => {
  const root = directory(t), budget = candidateBudget([], {reserveBytes: 0, reserveDescriptors: 0,
    allowance: {phaseBytes: 256 * 1048576, rssBytes: 1024 * 1048576}});
  let remaining = budget.snapshot().limit_bytes;
  while (remaining) { const bytes = Math.min(32 * 1048576, remaining); budget.add({bytes}); remaining -= bytes; }
  assert.throws(() => publish(root, '.cache/delivery-handoff/overflow', {'x.json': jsonBytes({})}, {}, false, budget), /Aggregate/);
  assert.equal(fs.existsSync(path.join(root, '.cache')), false);
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

function reviewFixture({packetPrefix = prefix, ownedPaths} = {}) {
  const head = 'b'.repeat(40), manifestPath = packetPrefix + 'evidence-quality.json';
  const spec = {mode: 'engineering', max_prs: 1, depends_on: [], scope: 'Bounded fixture', ...(ownedPaths ? {owned_paths:ownedPaths} : {}), evidence_quality: {version: 1,
    manifest_path: manifestPath, subject_ids: [], pins: {}, review_kind: 'code'}};
  const issue = {number: 42, state: 'open', labels: ['type:engineering', 'kind:work-item', 'status:ready'], created_at: '2026-10-10T00:00:00Z', body: 'Original acceptance\n<!-- worldatlas-work:v1\n' + JSON.stringify(spec) + '\n-->'};
  const files = [{filename: 'scripts/renamed.mjs', previous_filename: 'scripts/identity-old.mjs', status: 'renamed'}, {filename: manifestPath, status: 'added'}];
  const pr = {number: 43, state: 'open', body: 'Refs #42\n', head: {sha: head, ref: 'engineering/control'}, base: {sha: commit}, changed_files: files.length};
  const claim = {version: 1, active: true, worker_id: 'author', claim_id: 'fixture-claim', request_id: 'fixture-request', issue_number: 42, mode: 'engineering', max_prs: 1, live_work: false, branch: pr.head.ref, expires_at: '2099-01-01T00:00:00Z'};
  const manifest = {version: 1, issue: 42, lane: 'engineering', worker_id: 'author', subject_ids: [], subject_ids_sha256: subjectsHash([]),
    baseline: {commit, files: [{path: 'baseline.txt', bytes: 9, sha256: digest(Buffer.from('baseline\n')), hash_kind: 'file-bytes'}], pins: {}}, sources: [], outputs: [], methods: [{id: 'code', kind: 'code', description: 'Metadata', software: 'Node 24', units: 'none'}],
    metrics: [], summaries: [], conclusions: [], stages: {research: 'complete', implementation: 'implemented', geographic_approval: 'not-requested'}, commands: []};
  const r = memoryReader(), pin = r.add(manifestPath, manifest), raw = r.read(pin); r.pin = () => pin;
  const api = async url => {
    if (url.endsWith('/pulls/43')) return structuredClone(pr);
    if (url.endsWith('/issues/42')) return structuredClone(issue);
    if (url.includes('/issues/42/comments')) return [{id: 1, user: {login: 'github-actions[bot]', type: 'Bot'}, body: renderClaim(claim)}];
    if (url.includes('/pulls/43/files')) return files;
    if (url.includes('/git/commits/')) return {tree: {sha: 'tree'}};
    if (url.includes('/git/trees/')) return {truncated: false, tree: [{path: manifestPath, type: 'blob', mode: '100644', sha: pin.blob, size: raw.length}, {path: 'baseline.txt', type: 'blob', mode: '100644', sha: 'baseblob', size: 9}]};
    if (url.includes('/git/blobs/')) return {encoding: 'base64', content: (url.endsWith('/baseblob') ? Buffer.from('baseline\n') : raw).toString('base64')};
    if (url.includes('/compare/')) return {status: 'ahead'};
    throw Error('Unexpected API: ' + url);
  };
  return {pr, issue, claim, spec, files, api, reader: r, repo: 'fixture/repo', number: 43, expectedHead: head};
}

test('review handoff includes current bindings/complete rename scope and no approval; stale head/body/scope fail', async () => {
  const f = reviewFixture(), packet = JSON.parse((await freezeReview(f))['review-packet.json']);
  assert.equal(packet.kind, 'review-preparation-only'); assert.ok(packet.inspected_files.includes('scripts/identity-old.mjs'));
  assert.equal(packet.outcome, undefined); assert.equal(packet.reviewer_worker_id, undefined); assert.match(packet.pr_body_sha256, /^[a-f0-9]{64}$/);
  for (const field of ['head', 'body', 'changed_files']) {
    const g = reviewFixture(), original = g.api; let reads = 0;
    g.api = async url => { const value = await original(url); if (url.endsWith('/pulls/43') && ++reads === 2) {
      if (field === 'head') value.head.sha = 'c'.repeat(40); else if (field === 'body') value.body += 'Changed disposition'; else value.changed_files++;
    } return value; };
    await assert.rejects(freezeReview(g), /changed while freezing/);
  }
  const missing = reviewFixture(); missing.files.pop(); await assert.rejects(freezeReview(missing), /Incomplete/);
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

test('new request issuance requires explicit finite v2 profiles and actual HEAD support/code pins', () => {
  const reader = memoryReader(), code = reader.add('scripts/operator.mjs', Buffer.from('code'));
  const support = ['scripts/local-workspace.mjs', 'scripts/worker-identity.mjs'].map(p => reader.add(p, Buffer.from('support')));
  const template = {operating_profile: 'source-native-v2', output_reserve: 131072, executed_code: [code], operating_runtime: {supervisor: code, support_code: support}};
  reader.git = () => Buffer.from(commit); reader.pin = (c, p) => [code, ...support].find(x => x.path === p);
  const requested_resources = {processing_allowance: {phaseBytes: 600000000, rssBytes: 700000000}, operating_limits:
    {rss_bytes: 800000000, wall_seconds: 1400, output_bytes: 2000000, retained_bytes: 3000000, log_bytes: 100000, monitor_bytes: 100000, receipt_bytes: 10000}};
  const issued = requestProfile(template, {}, {requested_resources}, reader);
  assert.deepEqual(issued.processing_allowance, requested_resources.processing_allowance); assert.equal(issued.operating_limits.wall_seconds, 1400);
  assert.throws(() => requestProfile({...template, operating_profile: undefined}, {}, {}, reader), /v2/);
  assert.throws(() => requestProfile(template, {}, {}, reader), /Explicit/);
  for (const mutate of [x => x.operating_limits.rss_bytes = Infinity, x => x.operating_limits.wall_seconds = 0,
    x => x.processing_allowance.phaseBytes = 900000000, x => x.processing_allowance.phaseBytes = 131071, x => x.operating_limits.output_bytes = 1,
    x => x.operating_limits.retained_bytes = 1, x => x.operating_limits.log_bytes = 900000000,
    x => x.operating_limits.monitor_bytes = 900000000, x => x.operating_limits.receipt_bytes = 900000000]) {
    const bad = structuredClone(requested_resources); mutate(bad); assert.throws(() => requestProfile(template, {}, {requested_resources: bad}, reader));
  }
  for (const output_reserve of [1000, Number.MAX_SAFE_INTEGER]) {
    assert.throws(() => requestProfile({...template, output_reserve}, {}, {requested_resources}, reader), /finite bounds/);
  }
  const drift = structuredClone(template); drift.operating_runtime.support_code[0].sha256 = '0'.repeat(64);
  assert.throws(() => requestProfile(drift, {}, {requested_resources}, reader), /actual HEAD/);
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


test('finalization appends authenticated inherited read roles without widening output ownership', () => {
  const {reader, config} = finalizationFixture({historical: true});
  const original = reader.json(config.package_inputs), result = finalizeDelivery(config, reader);
  const actual = JSON.parse(result['package-inputs.json']);
  assert.deepEqual(actual.inputs.slice(0, original.inputs.length), original.inputs);
  assert.ok(actual.inputs.includes('coordination/engineering/accepted-original/custody.json'));
  assert.ok(actual.inputs.includes('coordination/engineering/accepted-original/operating.json'));
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
  assert.ok(JSON.parse(finalizeDelivery(restored.config,restored.reader)['package-inputs.json']).inputs.includes(name));
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
  for (const name of f.config.restored_read_roles.paths) assert.ok(inputs.includes(name));
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
  assert.throws(()=>finalizeDelivery(h.config,h.reader), error => h.reader &&
    error.message.includes('accepted-original/custody.json') && error.message.includes('accepted-original/operating.json'));
});

test('finalization refuses a new identity at an accepted package path', () => {
  const {reader,config} = finalizationFixture();
  const first = finalizeDelivery(config, reader);
  const package_inputs = reader.add(config.package_inputs.path, first['package-inputs.json']);
  const originalPin = reader.pin;
  reader.pin = (c,p) => p === config.selected_ledger.path ? {...originalPin(c,p), sha256: '0'.repeat(64)} : originalPin(c,p);
  assert.throws(() => finalizeDelivery({...config,package_inputs},reader), /conflicts with accepted path identity/);
});

test('review freeze binds refreshed PR state before reading evidence and detects target/readiness drift', async () => {
  const prepare = () => {
    const f = reviewFixture(); f.pr.draft = false;
    f.pr.head.repo = {full_name: f.repo}; f.pr.base.ref = 'main'; f.pr.base.repo = {full_name: f.repo};
    return f;
  };
  for (const drift of [p => { p.draft = true; }, p => { p.base.ref = 'other'; },
    p => { p.head.ref = 'engineering/other'; }, p => { p.base.repo.full_name = 'foreign/repo'; },
    p => { p.head.repo.full_name = 'foreign/repo'; }, p => { p.body += 'Changed'; }]) {
    const f = prepare(); f.expectedPR = structuredClone(f.pr); drift(f.pr);
    await assert.rejects(freezeReview(f), /state changed after review preparation/);
    const g = prepare(), original = g.api; let reads = 0;
    g.api = async route => { const result = await original(route); if (route.endsWith('/pulls/43') && ++reads === 2) drift(result); return result; };
    await assert.rejects(freezeReview(g), /changed while freezing/);
  }
  const draft = prepare(); draft.pr.draft = true; draft.expectedPR = structuredClone(draft.pr);
  const packet = JSON.parse((await freezeReview(draft))['review-packet.json']);
  assert.equal(packet.pr.draft, true); assert.equal(packet.kind, 'review-preparation-only');
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

test('review freeze authenticates current issue scope for an owned nested manifest', async () => {
  const options={packetPrefix:'coordination/engineering/retained/new-delivery/',ownedPaths:['coordination/engineering/retained/','scripts/renamed.mjs','scripts/identity-old.mjs']};
  const f=reviewFixture(options), packet=JSON.parse((await freezeReview(f))['review-packet.json']);
  assert.equal(packet.manifest.path,options.packetPrefix+'evidence-quality.json');
  for(const mutate of [f=>delete f.spec.owned_paths,f=>f.spec.owned_paths=['coordination/engineering/foreign/'],
    f=>f.issue.number=41,f=>f.issue.state='closed']) {
    const g=reviewFixture(options);mutate(g);g.issue.body='Original acceptance\n<!-- worldatlas-work:v1\n'+JSON.stringify(g.spec)+'\n-->';
    await assert.rejects(freezeReview(g));
  }
});

test('review freeze rechecks current issue state and owned scope after reading evidence', async () => {
  for(const mutation of [issue=>issue.state='closed',
    issue=>issue.body=issue.body.replace('coordination/engineering/retained/','coordination/engineering/foreign/')]) {
    const f=reviewFixture({packetPrefix:'coordination/engineering/retained/nested/',ownedPaths:['coordination/engineering/retained/']}), original=f.api;let reads=0;
    f.api=async url=>{const value=await original(url);if(url.endsWith('/issues/42')&&++reads===2)mutation(value);return value;};
    await assert.rejects(freezeReview(f));
  }
});
