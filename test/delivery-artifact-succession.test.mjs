import test from 'node:test';
import assert from 'node:assert/strict';
import {finalizedSelection, digest} from '../scripts/prepare-delivery-handoff.mjs';

const original = {version: 1, method: 'native-linear-evenodd-first-owner-v1',
  manifest_path: 'data/canonical-grid/selected/manifest.json', sha256: 'a'.repeat(64),
  release_id: 'geography:retained', selected_geography: {path: 'data/original.json', sha256: 'b'.repeat(64)}};
const pin = {path: 'coordination/engineering/control/sidecar.json', bytes: 10, sha256: 'c'.repeat(64)};
const sidecar = base => ({version: 2, kind: 'retained-native-additive-selection-v2', base_selection: base});
const hook = suffix => ({certificate: {path: 'certificate-' + suffix + '.json', mode: '100644', bytes: 10, sha256: suffix.repeat(64)},
  review: {path: 'review-' + suffix + '.json', mode: '100644', bytes: 10, sha256: suffix.repeat(64)}});

test('unchanged complete bases keep pure legacy finalization and exact repeat bytes without authority reads', () => {
  const selection = {...original, additive_release: pin}, raw = Buffer.from(JSON.stringify(selection, null, 2) + '\n');
  const unreadable = new Proxy({}, {get() { throw Error('unexpected authority access'); }});
  assert.equal(finalizedSelection(raw, sidecar(original), pin, unreadable), raw);
  const qualified = {...original, artifact_consumption: hook('d')};
  const qualifiedRaw = Buffer.from(JSON.stringify({...qualified, additive_release: pin}) + '\n');
  assert.equal(finalizedSelection(qualifiedRaw, sidecar(qualified), pin, unreadable), qualifiedRaw);
});

test('a changed operational hook cannot use absent, cloned or fabricated current authority', () => {
  const historical = {...original, artifact_consumption: hook('d')};
  const selection = {...original, artifact_consumption: hook('e'), additive_release: pin};
  const raw = Buffer.from(JSON.stringify(selection)), before = digest(raw), old = JSON.stringify(historical);
  for (const snapshot of [undefined, null, {}, {selection, reader: {version: 'f'.repeat(40)}, artifactConsumption: {}},
    {selection, reader: {}, artifactConsumption: {certificate: {}, code_inventory: {}}, approved: true}]) {
    assert.throws(() => finalizedSelection(raw, sidecar(historical), pin, snapshot), /authenticated|authority/);
  }
  assert.equal(digest(raw), before); assert.equal(JSON.stringify(historical), old);
});

test('scientific or missing-hook changes remain refusals on the direct selector API', () => {
  for (const change of [s => s.release_id += '-changed', s => s.manifest_path += '-changed',
    s => s.sha256 = 'f'.repeat(64), s => s.method = 'foreign', s => s.version = 2,
    s => s.selected_geography = {...s.selected_geography, path: 'foreign'}, s => s.future_operand = true,
    s => s.artifact_consumption = hook('d')]) {
    const changed = structuredClone(original); change(changed);
    assert.throws(() => finalizedSelection(Buffer.from(JSON.stringify(original)), sidecar(changed), pin), /complete original base/);
  }
});

test('delivery evidence still rejects a changed complete baseline authority hook before any succession', async () => {
  const {prepareEvidence, jsonBytes} = await import('../scripts/prepare-delivery-handoff.mjs');
  const {candidateBudget} = await import('../scripts/native-ownership/native-preparation-guards.mjs');
  const bodies = new Map(), pins = new Map(), baseline = '1'.repeat(40), candidate = '2'.repeat(40);
  const reader = {budget: candidateBudget([], {reserveBytes: 0, reserveDescriptors: 0}),
    git(...args) { assert.deepEqual(args, ['merge-base', '--is-ancestor', baseline, candidate]); return Buffer.alloc(0); },
    pin(version, name) { const pin = pins.get(version + ':' + name); assert.ok(pin); return pin; },
    read(pin) { const raw = bodies.get(pin.commit + ':' + pin.path); assert.equal(digest(raw), pin.sha256); return raw; },
    json(pin) { return JSON.parse(reader.read(pin)); }};
  const put = (commit, path, value) => { const raw = jsonBytes(value), pin = {commit, path, mode: '100644',
    bytes: raw.length, sha256: digest(raw), git_blob_oid: '3'.repeat(40)};
    pins.set(commit + ':' + path, pin); bodies.set(commit + ':' + path, raw); return pin; };
  for (const [commit, marker] of [[baseline, 'd'], [candidate, 'e']]) {
    const base = {...original, artifact_consumption: hook(marker)};
    const registry = put(commit, 'registry.json', {version: 1, entries: []});
    const ledger = put(commit, 'ledger.json', {version: 2, rows: []});
    const side = put(commit, 'sidecar.json', {...sidecar(base), authority_registry: registry, logical_asset_map: {ledger}});
    put(commit, 'data/ownership-selection.json', {...base, additive_release: {path: side.path, bytes: side.bytes, sha256: side.sha256}});
  }
  const config = {version: 1, delivery: {version: 1, baseline_commit: baseline, candidate_commit: candidate,
    manifest_path: 'coordination/engineering/control/evidence-quality.json', issue: 1963, worker_id: 'bounded-test',
    subject_ids: ['subject'], sources: [], limits: ['Metadata control only'], qualified_constructor_pins: [{}]}};
  assert.throws(() => prepareEvidence(config, reader), /Delivery base\/rows differ/);
});
