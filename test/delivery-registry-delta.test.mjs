import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {jsonBytes, digest, finalizeDelivery, packageProjection} from '../scripts/prepare-delivery-handoff.mjs';

// Small immutable metadata only. No authority qualification, native scans or GIS.
const BASE = '1'.repeat(40), SOURCE = '2'.repeat(40), NEXT = '3'.repeat(40);
const OWNED = 'coordination/engineering/joint-delta/';
function fixture({count = 7, generated = true, cumulative = true} = {}) {
  const records = new Map(), charges = [], reads = [], parsed = [];
  const reader = {
    budget: {add(item) { assert.ok(Number.isSafeInteger(item.bytes) && item.bytes >= 0); charges.push(item.bytes); }},
    add(name, value, commit = NEXT) {
      const raw = Buffer.isBuffer(value) ? value : jsonBytes(value);
      const pin = {commit, path: name, mode: '100644', bytes: raw.length, sha256: digest(raw),
        git_blob_oid: createHash('sha1').update('blob ' + raw.length + '\0').update(raw).digest('hex')};
      records.set(commit + ':' + name, {pin, raw}); return pin;
    },
    pin(commit, name) { const entry = records.get(commit + ':' + name); assert.ok(entry, 'Missing exact snapshot: ' + name); return entry.pin; },
    read(pin) {
      const actual = records.get(pin.commit + ':' + pin.path); assert.ok(actual, 'Missing original body');
      const {roles, ...identity} = pin; // Projection annotations are not part of immutable identity.
      assert.deepEqual(identity, actual.pin, 'Changed whole original pin'); reads.push(pin.path); return actual.raw;
    },
    json(pin) { parsed.push(pin.path); return JSON.parse(reader.read(pin)); },
    hasPath(commit, name) { return records.has(commit + ':' + name); },
    git(...args) { assert.deepEqual(args, ['rev-parse', 'HEAD']); return Buffer.from(NEXT); }
  };
  const common = {};
  for (const role of ['catalogue', 'physical_input', 'physical_reproduction', 'physical_evidence', 'native_latitudes', 'owner_roster'])
    common[role] = reader.add('coordination/engineering/original-common/' + role + '.json', {retained: role}, BASE);
  const family = reader.add('coordination/engineering/original-common/family.json', {type: 'FeatureCollection', features: []}, BASE);
  const originals = [], restorations = [];
  const makeAuthority = (ordinal, stem, commit) => {
    const evidence = reader.add(stem + 'source-evidence.json', {version: 1, kind: 'source-target-native-evidence-v1',
      ...common, targets: [{id: 'original:' + ordinal}], families: [{source_id: 'original', parts: [family]}]}, commit);
    const native = reader.add(stem + 'native-patch.json', {rows: [{y: ordinal, runs: [[ordinal, ordinal + 1, 1]]}]}, commit);
    const binding = {version: 1, kind: 'source-target-native-custody-v1', source_evidence: evidence, native_patch: native};
    const source_authority = reader.add(stem + 'authority-binding.json', binding, commit);
    const rule_preimage = reader.add(stem + 'original-rule-preimage.json', {...binding, kind: 'source-target-native-rule-v1'}, commit);
    const body = {policy_id: 'retained-source-literal-additions', policy_version: 1,
      rule_preimage, rule_sha256: rule_preimage.sha256, source_authority};
    const entry = {authority_sha256: digest(jsonBytes(body)), ...body};
    const geometry = {type: 'Polygon', coordinates: [[[0, 0], [1, 0], [0, 1], [0, 0]]]};
    const row = {representation: 'native-cells', component_id: 'source-target:' + ordinal, target_id: 'target:' + ordinal,
      pixelIndex: 1, disposition: 'assigned', base_geometry: geometry, base_geometry_sha256: digest(jsonBytes(geometry)),
      native_rows: [{y: ordinal, runs: [[ordinal, ordinal + 1, 1]]}], native_bounds: [0, 0, 1, 1], native_cells: 1,
      source_receipt_sha256: common.physical_evidence.sha256, authority_sha256: entry.authority_sha256, rule_sha256: entry.rule_sha256};
    const pins = [evidence, native, source_authority, rule_preimage]; originals.push(...pins);
    if (commit === SOURCE) for (const pin of pins) {
      reader.add(pin.path, reader.read(pin), NEXT); restorations.push(pin.path);
    }
    return {entry, row};
  };
  // An inherited authority deliberately lies inside new_prefix; path selection
  // would incorrectly count it as new and omit all seven original-prefix groups.
  const old = makeAuthority(0, OWNED + 'inherited/', BASE);
  const additions = Array.from({length: count}, (_, i) => makeAuthority(i + 1,
    'coordination/engineering/original-country-' + i + '/authority/', SOURCE));
  const accepted = {version: 1, kind: 'retained-rule-authority-registry-v1', entries: [old.entry]};
  const priorRegistry = reader.add(OWNED + 'accepted-registry.json', accepted, BASE);
  const owner = common.owner_roster;
  const reference = {id: 'geography:base', footprints_sha256: 'a'.repeat(64), hierarchy_sha256: 'b'.repeat(64)};
  const manifest = reader.add('coordination/engineering/original-common/manifest.json', {
    geographic_release: reference.id, footprints_sha256: reference.footprints_sha256, hierarchy_sha256: reference.hierarchy_sha256,
    original_assets: {bounds: {sha256: owner.sha256}}}, BASE);
  const base = {version: 1, release_id: reference.id, sha256: manifest.sha256, selected_geography: {z: 1, a: 2}};
  const priorLedger = reader.add(OWNED + 'accepted-ledger.json', {version: 2, kind: 'native-additive-repair-ledger-v2',
    authority_registry_sha256: priorRegistry.sha256, scope_ids: [old.row.component_id], rows: [old.row]}, BASE);
  const priorPatch = reader.add(OWNED + 'accepted-patch.json', {rows: old.row.native_rows}, BASE);
  const priorEnvelope = reader.add(OWNED + 'accepted-envelope.json', {base_reference: reference}, BASE);
  const priorSidecar = reader.add(OWNED + 'accepted-sidecar.json', {version: 2, kind: 'retained-native-additive-selection-v2',
    base_selection: base, authority_registry: priorRegistry, runtime_envelope: priorEnvelope,
    logical_asset_map: {base_manifest: manifest, owner_roster: owner, ledger: priorLedger, patch: priorPatch}}, BASE);
  const selector = reader.add('data/ownership-selection.json', {...base, ...(cumulative ? {
    additive_release: {path: priorSidecar.path, bytes: priorSidecar.bytes, sha256: priorSidecar.sha256}} : {})}, BASE);
  const stub = reader.add('coordination/engineering/original-common/custody.json', {}, BASE);
  const operating = reader.add('coordination/engineering/original-common/operating.json', {execution_custody: {terminal: stub}}, BASE);
  const rebind = reader.add('coordination/engineering/original-common/rebind.json', {
    request: stub, facts: stub, publication: stub, result: stub, operating}, BASE);
  const package_inputs = reader.add('.github/package-inputs.json', {version: 1,
    inputs: ['public/', '.github/package-inputs.json'], optional_inputs: ['public/'], verification_paths: [], generated_outputs: []}, BASE);
  const config = {version: 1, new_prefix: OWNED, selector, package_inputs, rebind};
  if (restorations.length) config.restored_read_roles = {commit: NEXT, paths: restorations};
  const setRegistry = entries => {
    const registry = {version: 1, kind: accepted.kind, entries: [...entries].sort((a, b) => a.authority_sha256.localeCompare(b.authority_sha256))};
    config.registry = reader.add(OWNED + 'registry.json', registry);
    const rows = [old, ...additions].filter(value => entries.some(entry => entry.authority_sha256 === value.entry.authority_sha256))
      .map(value => value.row).sort((a, b) => a.component_id.localeCompare(b.component_id));
    config.ledger = config.selected_ledger = reader.add(OWNED + 'selected-ledger.json', {version: 2, kind: 'native-additive-repair-ledger-v2',
      authority_registry_sha256: config.registry.sha256, scope_ids: rows.map(row => row.component_id), rows,
      current_rebind: rebind, current_targets: [{target_id: 'original'}]});
    config.patch = reader.add(OWNED + 'patch.json', {authority_registry_sha256: config.registry.sha256,
      ledger_sha256: config.ledger.sha256, base_reference: reference, effective_reference: {...reference, id: 'geography:next'}});
    const assets = {base_manifest: manifest, ledger: config.ledger, owner_roster: owner, patch: config.patch};
    config.runtime_envelope = reader.add(OWNED + 'envelope.json', {base_reference: reference,
      effective_reference: {...reference, id: 'geography:next'}, ...Object.fromEntries(Object.entries(assets).map(([role, pin]) =>
        [role, {bytes: pin.bytes, sha256: pin.sha256}]))});
    if (generated) config.sidecar_output = OWNED + 'new-sidecar.json';
    else config.sidecar = reader.add(OWNED + 'new-sidecar.json', {version: 2, kind: 'retained-native-additive-selection-v2',
      base_selection: base, authority_registry: config.registry, logical_asset_map: assets, runtime_envelope: config.runtime_envelope});
  };
  setRegistry([old.entry, ...additions.map(value => value.entry)]);
  return {reader, config, old, additions, originals, priorRegistry, priorSidecar, accepted, setRegistry, charges, reads, parsed, base};
}

for (const generated of [true, false]) test('cumulative finalizer discovers seven original-prefix authorities, preserving original custody (' + generated + ')', () => {
  const f = fixture({generated}), before = f.originals.map(pin => Buffer.from(f.reader.read(pin)));
  const output = finalizeDelivery(f.config, f.reader), roles = JSON.parse(output['package-roles.json']);
  assert.equal(roles.new_authorities, 7);
  for (const {entry} of f.additions) for (const pin of [entry.rule_preimage, entry.source_authority])
    assert.ok(roles.paths.some(path => path.path === pin.path && path.sha256 === pin.sha256 && path.commit === pin.commit));
  assert.ok(!roles.paths.some(path => path.path === f.old.entry.source_authority.path));
  f.originals.forEach((pin, i) => assert.deepEqual(f.reader.read(pin), before[i]));
  assert.equal(JSON.parse(output['selected-delivery-expectations.json']).cumulative_native_cells, 8);
  assert.deepEqual(JSON.parse(output['package-inputs.json']).inputs.slice(0, 2), ['public/', '.github/package-inputs.json']);
  assert.equal(f.charges.filter(bytes => bytes === f.priorRegistry.bytes).length, 12);
  const again = finalizeDelivery(f.config, f.reader);
  for (const name of Object.keys(output)) assert.deepEqual(again[name], output[name]);
});

test('empty registry delta is valid and does not rediscover inherited authorities under new_prefix', () => {
  const f = fixture({count: 0}), output = finalizeDelivery(f.config, f.reader);
  assert.equal(JSON.parse(output['package-roles.json']).new_authorities, 0);
  assert.equal(JSON.parse(output['selected-delivery-expectations.json']).cumulative_native_cells, 1);
});

test('standalone package and initial no-hook finalization retain prefix selection', () => {
  const f = fixture({generated: false, cumulative: false});
  assert.equal(JSON.parse(packageProjection(f.config, f.reader)['package-roles.json']).new_authorities, 1);
  delete f.config.restored_read_roles;
  assert.equal(JSON.parse(finalizeDelivery(f.config, f.reader)['package-roles.json']).new_authorities, 1);
});

test('removed, rebound or colliding inherited authority identities refuse at actual finalize entry', () => {
  const removed = fixture(); removed.setRegistry(removed.additions.map(value => value.entry));
  assert.throws(() => finalizeDelivery(removed.config, removed.reader), /Inherited authority removed or changed/);
  const rebound = fixture();
  const entry = {...rebound.old.entry, policy_id: 'changed'};
  const {authority_sha256, ...body} = entry; entry.authority_sha256 = digest(jsonBytes(body));
  rebound.setRegistry([entry, ...rebound.additions.map(value => value.entry)]);
  assert.throws(() => finalizeDelivery(rebound.config, rebound.reader), /Inherited authority removed or changed/);
  const collision = fixture();
  collision.setRegistry([collision.old.entry, {...collision.additions[0].entry, authority_sha256: collision.old.entry.authority_sha256}]);
  assert.throws(() => finalizeDelivery(collision.config, collision.reader), /authority entry|authority.*changed/i);
  const changed = fixture(); changed.setRegistry([{...changed.old.entry, policy_version: 2}, ...changed.additions.map(value => value.entry)]);
  assert.throws(() => finalizeDelivery(changed.config, changed.reader), /authority entry changed/i);
});

test('duplicate or invalid accepted identities and a forged accepted registry binding refuse', () => {
  for (const mutate of [body => body.entries.push(body.entries[0]), body => body.entries[0].authority_sha256 = 'invalid']) {
    const f = fixture(), body = structuredClone(f.accepted); mutate(body);
    const pin = f.reader.add(f.priorRegistry.path, body, BASE);
    f.reader.add(f.priorSidecar.path, {...f.reader.json(f.priorSidecar), authority_registry: pin}, BASE);
    const side = f.reader.pin(BASE, f.priorSidecar.path), selection = f.reader.json(f.config.selector);
    f.config.selector = f.reader.add(f.config.selector.path, {...selection, additive_release: {path: side.path, bytes: side.bytes, sha256: side.sha256}}, BASE);
    assert.throws(() => finalizeDelivery(f.config, f.reader), /accepted authority identity/);
  }
  const f = fixture(), prior = f.reader.json(f.priorSidecar);
  const side = f.reader.add(f.priorSidecar.path, {...prior, authority_registry: {...prior.authority_registry, sha256: 'f'.repeat(64)}}, BASE);
  f.config.selector = f.reader.add(f.config.selector.path, {...f.reader.json(f.config.selector),
    additive_release: {path: side.path, bytes: side.bytes, sha256: side.sha256}}, BASE);
  assert.throws(() => finalizeDelivery(f.config, f.reader), /Changed whole original pin/);
});

test('wrong selector hook, prior base, prebuilt base and unavailable parse allowance refuse before publication', () => {
  const badHook = fixture(); badHook.config.selector = badHook.reader.add('data/ownership-selection.json',
    {...badHook.reader.json(badHook.config.selector), additive_release: {path: badHook.priorSidecar.path, bytes: 1, sha256: 'f'.repeat(64)}}, BASE);
  assert.throws(() => finalizeDelivery(badHook.config, badHook.reader), /Original selected sidecar differs/);
  const badBase = fixture(), prior = badBase.reader.json(badBase.priorSidecar);
  const side = badBase.reader.add(badBase.priorSidecar.path, {...prior, base_selection: {...prior.base_selection, release_id: 'wrong'}}, BASE);
  badBase.config.selector = badBase.reader.add('data/ownership-selection.json', {...badBase.reader.json(badBase.config.selector),
    additive_release: {path: side.path, bytes: side.bytes, sha256: side.sha256}}, BASE);
  assert.throws(() => finalizeDelivery(badBase.config, badBase.reader), /Original selected base differs/);
  const prebuilt = fixture({generated: false}); prebuilt.config.sidecar = prebuilt.reader.add(prebuilt.config.sidecar.path,
    {...prebuilt.reader.json(prebuilt.config.sidecar), base_selection: {...prebuilt.base, release_id: 'wrong'}});
  assert.throws(() => finalizeDelivery(prebuilt.config, prebuilt.reader), /preserve.*base/);
  const budget = fixture(); budget.reader.budget.add = () => { throw Error('Control: parse allowance unavailable'); };
  assert.throws(() => finalizeDelivery(budget.config, budget.reader), /parse allowance unavailable/);
  assert.ok(!budget.parsed.includes(budget.priorRegistry.path));
});

test('caller config cannot replace the accepted registry or silently restore missing original roles', () => {
  const f = fixture(); f.config.accepted_registry = {version: 1, entries: []}; f.config.new_authorities = [];
  assert.equal(JSON.parse(finalizeDelivery(f.config, f.reader)['package-roles.json']).new_authorities, 7);
  delete f.config.restored_read_roles;
  assert.throws(() => finalizeDelivery(f.config, f.reader), /accepted path identity/);
});
