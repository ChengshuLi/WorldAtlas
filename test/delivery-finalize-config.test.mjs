import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync, spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {digest, jsonBytes, pinReader, resolveFinalizeConfig, finalizeDelivery} from '../scripts/prepare-delivery-handoff.mjs';

const entry = fileURLToPath(new URL('../scripts/prepare-delivery-handoff.mjs', import.meta.url));
const PREFIX = 'coordination/engineering/finalize-config/';
const locator = ({commit, path}) => ({commit, path});
function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'delivery-finalize-config-'));
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  const env = {...process.env, GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: '/dev/null', GIT_NO_LAZY_FETCH: '1', NODE_OPTIONS: '', NODE_PATH: ''};
  const git = (...args) => execFileSync('git', args, {cwd: root, env, encoding: 'utf8'}).trim();
  git('init', '-q'); git('config', 'user.name', 'Fixture'); git('config', 'user.email', 'fixture@example.invalid');
  const write = (name, value) => {
    fs.mkdirSync(path.dirname(path.join(root, name)), {recursive: true});
    fs.writeFileSync(path.join(root, name), jsonBytes(value));
  };
  const commit = () => { git('add', '.'); git('commit', '-qm', 'Immutable fixture'); return git('rev-parse', 'HEAD'); };
  const reader = () => pinReader(root, {allowance: {phaseBytes: 134217728, rssBytes: 536870912}});
  const pin = (commit, name) => reader().pin(commit, name);
  const common = PREFIX + 'original/';
  write(common + 'body.json', {retained: true});
  const body = pin(commit(), common + 'body.json');
  const authority = {policy_id: 'retained-source-literal-additions', policy_version: 1,
    rule_preimage: body, rule_sha256: body.sha256, source_authority: body};
  const authorityEntry = {authority_sha256: digest(jsonBytes(authority)), ...authority};
  const registry = {version: 1, kind: 'retained-rule-authority-registry-v1', entries: [authorityEntry]};
  const reference = {id: 'geography:base', footprints_sha256: 'a'.repeat(64), hierarchy_sha256: 'b'.repeat(64)};
  write(common + 'registry.json', registry);
  write(common + 'manifest.json', {geographic_release: reference.id, footprints_sha256: reference.footprints_sha256,
    hierarchy_sha256: reference.hierarchy_sha256, original_assets: {bounds: {sha256: body.sha256}}});
  write(common + 'operating.json', {execution_custody: {terminal: body}});
  const originals = commit(), priorRegistry = pin(originals, common + 'registry.json'), manifest = pin(originals, common + 'manifest.json');
  write(common + 'rebind.json', {request: body, facts: body, publication: body, result: body,
    operating: pin(originals, common + 'operating.json')});
  const base = {version: 1, release_id: reference.id, sha256: manifest.sha256, selected_geography: {z: 1, a: 2}};
  const sidecar = {version: 2, kind: 'retained-native-additive-selection-v2', base_selection: base,
    authority_registry: priorRegistry, runtime_envelope: body,
    logical_asset_map: {base_manifest: manifest, owner_roster: body, ledger: body, patch: body}};
  write(common + 'sidecar.json', sidecar);
  const inherited = commit(), rebind = pin(inherited, common + 'rebind.json'), priorSidecar = pin(inherited, common + 'sidecar.json');
  write('data/ownership-selection.json', {...base, additive_release: {path: priorSidecar.path, bytes: priorSidecar.bytes, sha256: priorSidecar.sha256}});
  write('.github/package-inputs.json', {version: 1, inputs: ['public/', '.github/package-inputs.json'],
    optional_inputs: ['public/'], verification_paths: [], generated_outputs: []});
  const baseline = commit(), selector = pin(baseline, 'data/ownership-selection.json'), package_inputs = pin(baseline, '.github/package-inputs.json');
  const geometry = {type: 'Polygon', coordinates: [[[0, 0], [1, 0], [0, 1], [0, 0]]]};
  const row = {representation: 'native-cells', component_id: 'source-target:original', target_id: 'target:original', pixelIndex: 1,
    disposition: 'assigned', base_geometry: geometry, base_geometry_sha256: digest(jsonBytes(geometry)),
    native_rows: [{y: 0, runs: [[0, 1, 1]]}], native_bounds: [0, 0, 1, 1], native_cells: 1,
    source_receipt_sha256: body.sha256, authority_sha256: authorityEntry.authority_sha256, rule_sha256: authority.rule_sha256};
  const ledger = {version: 2, kind: 'native-additive-repair-ledger-v2', authority_registry_sha256: digest(jsonBytes(registry)),
    scope_ids: [row.component_id], rows: [row], current_rebind: rebind, current_targets: [{target_id: row.target_id}]};
  const effective = {...reference, id: 'geography:next'};
  const patch = {authority_registry_sha256: digest(jsonBytes(registry)), ledger_sha256: digest(jsonBytes(ledger)),
    base_reference: reference, effective_reference: effective, rows: row.native_rows};
  const descriptor = value => ({bytes: jsonBytes(value).length, sha256: digest(jsonBytes(value))});
  const envelope = {base_reference: reference, effective_reference: effective, base_manifest: {bytes: manifest.bytes, sha256: manifest.sha256},
    owner_roster: {bytes: body.bytes, sha256: body.sha256}, ledger: descriptor(ledger), patch: descriptor(patch)};
  const products = {'authority-registry.json': registry, 'selected-ledger.json': ledger, 'patch.json': patch, 'runtime-envelope.json': envelope};
  for (const [name, value] of Object.entries(products)) write(PREFIX + 'compose/' + name, value);
  const composed = commit();
  const full = {version: 1, selector, package_inputs, rebind, new_prefix: PREFIX, sidecar_output: PREFIX + 'sidecar.json',
    preparation_allowance: {phaseBytes: 134217728, rssBytes: 536870912},
    registry: pin(composed, PREFIX + 'compose/authority-registry.json'), ledger: pin(composed, PREFIX + 'compose/selected-ledger.json'),
    selected_ledger: pin(composed, PREFIX + 'compose/selected-ledger.json'), patch: pin(composed, PREFIX + 'compose/patch.json'),
    runtime_envelope: pin(composed, PREFIX + 'compose/runtime-envelope.json')};
  const compact = {version: full.version, selector: locator(selector), package_inputs: locator(package_inputs), rebind: locator(rebind),
    new_prefix: full.new_prefix, sidecar_output: full.sidecar_output, preparation_allowance: full.preparation_allowance,
    composition: locator(full.selected_ledger)};
  const run = (config, destination, ...flags) => {
    write('config.json', config);
    return spawnSync(process.execPath, [entry, 'finalize', 'config.json', destination, ...flags], {cwd: root, env, encoding: 'utf8'});
  };
  return {root, reader, full, compact, write, commit, baseline, products, run};
}

test('modern compact config resolves exact full pins and preserves legacy objects and canonical outputs', t => {
  const f = fixture(t), before = jsonBytes(f.compact);
  assert.deepEqual(resolveFinalizeConfig(f.compact, f.reader()), f.full);
  assert.strictEqual(resolveFinalizeConfig(f.full, f.reader()), f.full);
  assert.deepEqual(finalizeDelivery(f.compact, f.reader()), finalizeDelivery(f.full, f.reader()));
  assert.deepEqual(jsonBytes(f.compact), before);
});

test('cold CLI emits identical final products and resumes compact configuration exactly', t => {
  const f = fixture(t), destinations = ['full', 'compact'].map(name => '.cache/delivery-handoff/' + name);
  for (const [i, config] of [f.full, f.compact].entries()) {
    const result = f.run(config, destinations[i]); assert.equal(result.status, 0, result.stderr);
  }
  const receipts = destinations.map(dir => JSON.parse(fs.readFileSync(path.join(f.root, dir, 'preparation.json'))));
  assert.deepEqual(receipts[0].outputs, receipts[1].outputs);
  for (const name of Object.keys(receipts[0].outputs))
    assert.deepEqual(fs.readFileSync(path.join(f.root, destinations[0], name)), fs.readFileSync(path.join(f.root, destinations[1], name)));
  assert.notEqual(receipts[0].binding.config_sha256, receipts[1].binding.config_sha256);
  const resumed = f.run(f.compact, destinations[1], '--resume'); assert.equal(resumed.status, 0, resumed.stderr);
  assert.equal(JSON.parse(resumed.stdout).resumed, true);
});

test('compact form refuses mixed full pins, existing sidecar and handwritten locator descriptors', t => {
  const f = fixture(t);
  for (const key of ['registry', 'ledger', 'selected_ledger', 'patch', 'runtime_envelope', 'sidecar', 'unknown'])
    assert.throws(() => finalizeDelivery({...f.compact, [key]: f.full.ledger}, f.reader()), /cannot mix/);
  for (const key of ['selector', 'package_inputs', 'rebind', 'composition'])
    assert.throws(() => finalizeDelivery({...f.compact, [key]: {...f.compact[key], sha256: '0'.repeat(64)}}, f.reader()), /exact commit\/path locator/);
});

test('wrong commit, wrong path, missing product and changed product hash fail before writes', t => {
  const f = fixture(t);
  const cases = [
    {...f.compact, composition: {...f.compact.composition, commit: f.baseline}},
    {...f.compact, composition: {...f.compact.composition, path: PREFIX + 'compose/patch.json'}},
    {...f.compact, composition: {...f.compact.composition, path: '../selected-ledger.json'}},
    {...f.compact, rebind: {...f.compact.rebind, commit: f.full.ledger.commit}},
    {...f.full, patch: {...f.full.patch, sha256: '0'.repeat(64)}}
  ];
  f.write(PREFIX + 'incomplete/selected-ledger.json', f.products['selected-ledger.json']);
  const missing = f.commit(); cases.push({...f.compact, composition: {commit: missing, path: PREFIX + 'incomplete/selected-ledger.json'}});
  f.write(PREFIX + 'compose/patch.json', {...f.products['patch.json'], ledger_sha256: '0'.repeat(64)});
  const changed = f.commit(); cases.push({...f.compact, composition: {...f.compact.composition, commit: changed}});
  fs.chmodSync(path.join(f.root, PREFIX + 'compose/authority-registry.json'), 0o755);
  const executable = f.commit(); cases.push({...f.compact, composition: {...f.compact.composition, commit: executable}});
  cases.push({...f.compact, preparation_allowance: {...f.compact.preparation_allowance, phaseBytes: 1}});
  for (const [i, config] of cases.entries()) {
    const destination = '.cache/delivery-handoff/refused-' + i, result = f.run(config, destination);
    assert.notEqual(result.status, 0, 'Invalid metadata must refuse');
    assert.match(result.stderr, /Missing ordinary exact Git body|committed selected-ledger|safe whole-file path|exact commit\/path locator|metadata joins differ|Whole body hash differs|Aggregate evidence preparation budget exceeded/);
    assert.equal(fs.existsSync(path.join(f.root, destination)), false, 'Refusal cannot create output');
  }
});
