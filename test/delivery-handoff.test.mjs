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
  composeAuthorities, packageProjection, rebindCustody, requestProfile, freezeReview} from '../scripts/prepare-delivery-handoff.mjs';

const commit = 'a'.repeat(40), prefix = 'coordination/engineering/control/';
function memoryReader() {
  const bodies = new Map(); let ordinal = 0;
  const reader = {budget: candidateBudget([], {reserveBytes: 0, reserveDescriptors: 0}),
    add(name, value) { const raw = Buffer.isBuffer(value) ? value : jsonBytes(value); const pin = {path: name, commit,
      mode: '100644', blob: (++ordinal).toString(16).padStart(40, '0'), bytes: raw.length, sha256: digest(raw)};
      bodies.set(pin.sha256, raw); return pin; },
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
  const root = directory(t), budget = candidateBudget([{bytes: 32 * 1048576}, ...Array(7).fill({bytes: 32 * 1048576})], {reserveBytes: 0, reserveDescriptors: 0});
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
  assert.equal(r.json(pin).value, 1); assert.throws(() => r.read({...pin, sha256: '0'.repeat(64)}), /hash differs/);
  assert.throws(() => r.read({...pin, mode: '120000'}), /identity/); assert.throws(() => r.read({...pin, path: '../input.json'}), /safe/);
});

function reviewFixture() {
  const head = 'b'.repeat(40), manifestPath = prefix + 'evidence-quality.json';
  const spec = {mode: 'engineering', max_prs: 1, depends_on: [], scope: 'Bounded fixture', evidence_quality: {version: 1,
    manifest_path: manifestPath, subject_ids: [], pins: {}, review_kind: 'code'}};
  const issue = {number: 42, created_at: '2026-10-10T00:00:00Z', body: 'Original acceptance\n<!-- worldatlas-work:v1\n' + JSON.stringify(spec) + '\n-->'};
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
  return {pr, issue, files, api, reader: r, repo: 'fixture/repo', number: 43, expectedHead: head};
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
  const template = {operating_profile: 'source-native-v2', output_reserve: 1000, executed_code: [code], operating_runtime: {supervisor: code, support_code: support}};
  reader.git = () => Buffer.from(commit); reader.pin = (c, p) => [code, ...support].find(x => x.path === p);
  const requested_resources = {processing_allowance: {phaseBytes: 600000000, rssBytes: 700000000}, operating_limits:
    {rss_bytes: 800000000, wall_seconds: 1400, output_bytes: 2000000, retained_bytes: 3000000, log_bytes: 100000, monitor_bytes: 100000, receipt_bytes: 10000}};
  const issued = requestProfile(template, {}, {requested_resources}, reader);
  assert.deepEqual(issued.processing_allowance, requested_resources.processing_allowance); assert.equal(issued.operating_limits.wall_seconds, 1400);
  assert.throws(() => requestProfile({...template, operating_profile: undefined}, {}, {}, reader), /v2/);
  assert.throws(() => requestProfile(template, {}, {}, reader), /Explicit/);
  for (const mutate of [x => x.operating_limits.rss_bytes = Infinity, x => x.operating_limits.wall_seconds = 0,
    x => x.processing_allowance.phaseBytes = 900000000, x => x.operating_limits.output_bytes = 1,
    x => x.operating_limits.retained_bytes = 1, x => x.operating_limits.log_bytes = 900000000,
    x => x.operating_limits.monitor_bytes = 900000000, x => x.operating_limits.receipt_bytes = 900000000]) {
    const bad = structuredClone(requested_resources); mutate(bad); assert.throws(() => requestProfile(template, {}, {requested_resources: bad}, reader));
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
  const request = {...f.request, operation: 'unactivated-additive-native-batch-v1', additive: {scope_ids: f.request.source_rule.expected_ids, inputs: f.request.source_rule.inputs}};
  const pin = r.add(prefix + 'native-request.json', request), facts = {...f.facts, request: pin, operation: request.operation, source_predecessor: request.additive};
  const decoded = Buffer.concat(request.additive.scope_ids.map(component_id => jsonBytes({component_id, native_cells: 0, disposition: 'rejected'}))), encoded = gzipSync(decoded);
  facts.assigned_cells = 0;
  const factRaw = jsonBytes(facts), publication = {...f.publication, facts: {bytes: factRaw.length, sha256: digest(factRaw)},
    inventory: {bytes: encoded.length, sha256: digest(encoded), uncompressed_bytes: decoded.length, uncompressed_sha256: digest(decoded)}, assets: []};
  write(root, 'run/inventory.jsonl.gz', encoded);
  write(root, 'run/facts.json', factRaw); write(root, 'run/publication.json', jsonBytes(publication));
  write(root, f.config.terminal, jsonBytes({...f.terminal, request_sha256: pin.sha256}));
  assert.throws(() => retainProducts({...f.config, request: pin}, root, r), /fixed native publication asset roster/);
});
