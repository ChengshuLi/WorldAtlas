import test from 'node:test';
import assert from 'node:assert/strict';
import {supportedInputs, jsonBytes, digest} from '../scripts/prepare-delivery-handoff.mjs';

function fixture() {
  const files = new Map(), commit = 'a'.repeat(40), puts = [];
  const put = (path, value) => {
    const raw = jsonBytes(value), pin = {commit, path, mode: '100644', git_blob_oid: 'b'.repeat(40), bytes: raw.length, sha256: digest(raw)};
    files.set(path, {raw, pin}); puts.push(pin); return pin;
  };
  const read = pin => { const file = files.get(pin.path); assert.deepEqual(pin, file.pin); return file.raw; };
  const reader = {pin: (c, p) => {assert.equal(c, commit); return files.get(p).pin;}, read, json: p => JSON.parse(read(p))};
  const native_contract = {size: 262166};
  const cover = [{y: 10, runs: [[1, 2, 'mapped_land_support'], [2, 4, 'mapped_inland_water_support']]}];
  const target = (id, pixelIndex) => ({id, pixelIndex, base_geometry: {whole: id}, source_members: ['a', 'b'],
    territorial_exclusions: [{whole_negative: 1}, {source_id: 'foreign', feature_ordinal: 3, geometry_sha256: 'f'.repeat(64)}],
    coverage_rows: pixelIndex === 1 ? cover : [{y: 10, runs: [[6, 8, 'mapped_land_support']]}]});
  const source = {version: 1, kind: 'source-target-native-evidence-v1', native_contract, targets: [target('a', 1), target('b', 1), target('c', 2)],
    families: [{whole: 'original'}], physical_input: {whole: 'all physical members'}, negative_sources: [{whole: 'complete foreign family'}]};
  const pins = {source_evidence: put('source.json', source), native_patch: put('patch.json', {rows: [{y: 10, runs: [[1, 4, 1], [6, 8, 2]]}]})};
  const diagnostic = {version: 1, kind: 'source-target-native-diagnostic-v1', native_contract, original_pins: pins,
    rule_sha256: digest(jsonBytes({version: 1, kind: 'source-target-native-rule-v1', ...pins})),
    requested_rows: [{y: 10, runs: [[1, 4, 1], [6, 8, 2]]}], supported_rows: [{y: 10, runs: [[1, 3, 1]]}],
    held_rows: [{y: 10, runs: [[3, 4, 1], [6, 8, 2]]}],
    decision_rows: [{y: 10, runs: [[1, 3, 1, 'assigned_cells'], [3, 4, 1, 'boundary_cells'], [6, 8, 2, 'territorial_exclusion_cells']]}],
    requested_cells: 5, supported_cells: 2, held_cells: 3};
  put('diagnostic.json', diagnostic);
  const original = {rows: [{y: 10, runs: [[1, 4, 1], [6, 8, 2], [10, 12, 3]]}]}; put('original.json', original);
  const prior = {rows: [{y: 10, runs: [[2, 4, 1, 'prior-fitness'], [10, 12, 3, 'prior-identity']]}],
    assessments: [{original: 'whole retained prior assessment', unresolved: true}]}; put('prior.json', prior);
  const config = {version: 1, diagnostic: {commit, path: 'diagnostic.json'}, original_patch: {commit, path: 'original.json'},
    prior_holds: {commit, path: 'prior.json'}};
  const run = () => Object.fromEntries(Object.entries(supportedInputs(config, reader)).map(([p, raw]) => [p, JSON.parse(raw)]));
  return {put, files, reader, source, pins, diagnostic, original, prior, config, run};
}

test('supported-inputs joins full original, native and prior holds without changing whole operands', () => {
  const f = fixture(), before = structuredClone(f.source), result = f.run();
  assert.deepEqual(result['native-patch.json'], {rows: [{y: 10, runs: [[1, 2, 1]]}]});
  assert.deepEqual(result['held-original.json'], {rows: [{y: 10, runs: [[2, 3, 1, 'prior-fitness'], [3, 4, 1, 'boundary_cells'],
    [6, 8, 2, 'territorial_exclusion_cells'], [10, 12, 3, 'prior-identity']]}]});
  const expected = {...before, targets: before.targets.slice(0, 2).map(t => ({...t, coverage_rows: [{y: 10, runs: [[1, 2, 'mapped_land_support']]}]}))};
  assert.deepEqual(result['source-evidence.json'], expected);
  assert.deepEqual(f.source, before);
  const counts = result['original-scope-partition.json'];
  assert.equal(counts.original_cells, 7); assert.equal(counts.supported_cells, 1); assert.equal(counts.held_cells, 6);
  assert.equal(counts.prior_held_cells, 4); assert.equal(counts.prior_already_native_held_cells, 1);
  assert.deepEqual(counts.owners, [{owner: 1, original_cells: 3, supported_cells: 1, held_cells: 2},
    {owner: 2, original_cells: 2, supported_cells: 0, held_cells: 2}, {owner: 3, original_cells: 2, supported_cells: 0, held_cells: 2}]);
  assert.deepEqual(f.reader.json(counts.prior_holds), f.prior, 'complete prior assessments remain pinned');
  assert.deepEqual(counts.original_inputs, f.pins);
  assert(!Object.keys(result).some(name => /authority|proof|ledger/.test(name)));
});

test('supported-inputs defaults to complete diagnostic scope and preserves class boundaries', () => {
  const f = fixture(); delete f.config.original_patch; delete f.config.prior_holds;
  const result = f.run();
  assert.deepEqual(result['native-patch.json'].rows, f.diagnostic.supported_rows);
  assert.deepEqual(result['source-evidence.json'].targets[0].coverage_rows,
    [{y: 10, runs: [[1, 2, 'mapped_land_support'], [2, 3, 'mapped_inland_water_support']]}]);
  assert.equal(result['source-evidence.json'].targets.length, 2, 'both original member atoms survive');
});

test('supported-inputs preserves absent masks and accounts for an entirely held scope', () => {
  const f = fixture(); delete f.config.original_patch;
  for (const t of f.source.targets) delete t.coverage_rows;
  f.pins.source_evidence = f.put('source.json', f.source);
  f.diagnostic.rule_sha256 = digest(jsonBytes({version: 1, kind: 'source-target-native-rule-v1', ...f.pins}));
  f.put('diagnostic.json', f.diagnostic);
  f.put('prior.json', {rows: [{y: 10, runs: [[1, 4, 1, 'prior'], [6, 8, 2, 'prior']]}]});
  const result = f.run(); assert.deepEqual(result['native-patch.json'].rows, []);
  assert.deepEqual(result['source-evidence.json'].targets, []);
  assert.equal(result['original-scope-partition.json'].held_cells, 5);
  delete f.config.prior_holds;
  assert(f.run()['source-evidence.json'].targets.every(t => !('coverage_rows' in t)));
});

const changes = {
  'missing diagnostic row': f => f.diagnostic.decision_rows = [],
  'duplicate diagnostic row': f => f.diagnostic.decision_rows.push(f.diagnostic.decision_rows[0]),
  'overlapping diagnostic spans': f => f.diagnostic.decision_rows[0].runs[1][0] = 2,
  'altered native reason': f => f.diagnostic.decision_rows[0].runs[0][3] = 'foreign',
  'wrong original owner': f => f.original.rows[0].runs[0][2] = 9,
  'omitted original owner': f => f.original.rows[0].runs.pop(),
  'extra unaccounted original key': f => f.original.rows[0].runs.push([15, 16, 4]),
  'prior key outside original': f => f.prior.rows[0].runs.push([15, 16, 4, 'foreign']),
  'prior assignment claim': f => f.prior.rows[0].runs[0][3] = 'assigned_cells',
  'duplicate prior key': f => f.prior.rows[0].runs[1] = f.prior.rows[0].runs[0],
  'false diagnostic count': f => f.diagnostic.supported_cells++,
  'wrong rule binding': f => f.diagnostic.rule_sha256 = '0'.repeat(64),
  'wrong native extent': f => f.diagnostic.native_contract = {size: 262165},
  'wrong requested patch': f => f.diagnostic.requested_rows[0].runs[0][1] = 3,
  'out of grid': f => f.original.rows[0].runs.push([262166, 262167, 1]),
  'negative row': f => f.original.rows[0].y = -1,
};
for (const [name, change] of Object.entries(changes)) test('supported-inputs refuses ' + name, () => {
  const f = fixture(); change(f); f.put('diagnostic.json', f.diagnostic); f.put('original.json', f.original); f.put('prior.json', f.prior);
  assert.throws(f.run);
});

for (const [name, change] of Object.entries({
  'missing member owner': s => s.targets = s.targets.slice(0, 2),
  'duplicate member id': s => s.targets[1].id = s.targets[0].id,
  'conflicting sibling classes': s => s.targets[1].coverage_rows = [{y: 10, runs: [[1, 4, 'mapped_land_support']]}],
  'missing class coverage': s => s.targets[0].coverage_rows[0].runs.pop(),
  'invented class': s => s.targets[0].coverage_rows[0].runs[0][2] = 'invented',
  'extra class cell': s => s.targets[0].coverage_rows[0].runs[0][0] = 0,
})) test('supported-inputs refuses ' + name + ' with refreshed source binding', () => {
  const f = fixture(); change(f.source); f.pins.source_evidence = f.put('source.json', f.source);
  f.diagnostic.rule_sha256 = digest(jsonBytes({version: 1, kind: 'source-target-native-rule-v1', ...f.pins}));
  f.put('diagnostic.json', f.diagnostic); assert.throws(f.run);
});

test('supported-inputs authenticates original source bytes rather than accepting a supplied replacement', () => {
  const f = fixture(); f.put('source.json', {...f.source, families: []}); assert.throws(f.run);
  const other = fixture(); other.config.source_evidence = other.config.diagnostic; assert.throws(other.run);
});

test('supported-inputs operates on full-width intervals without expanding native cells', () => {
  const f=fixture();delete f.config.original_patch;delete f.config.prior_holds;
  const requested=[{y:262165,runs:[[0,262166,1]]}],supported=[{y:262165,runs:[[0,262165,1]]}],held=[{y:262165,runs:[[262165,262166,1]]}];
  f.source.targets=f.source.targets.slice(0,2).map(t=>({...t,coverage_rows:[{y:262165,runs:[[0,262166,'mapped_land_support']]}]}));
  f.pins.source_evidence=f.put('source.json',f.source);f.pins.native_patch=f.put('patch.json',{rows:requested});
  Object.assign(f.diagnostic,{requested_rows:requested,supported_rows:supported,held_rows:held,
    decision_rows:[{y:262165,runs:[[0,262165,1,'assigned_cells'],[262165,262166,1,'boundary_cells']]}],
    requested_cells:262166,supported_cells:262165,held_cells:1,
    rule_sha256:digest(jsonBytes({version:1,kind:'source-target-native-rule-v1',...f.pins}))});
  f.put('diagnostic.json',f.diagnostic);
  const result=f.run();assert.deepEqual(result['native-patch.json'],{rows:supported});
  assert.equal(result['original-scope-partition.json'].original_cells,262166);
  assert.deepEqual(result['source-evidence.json'].targets[1].coverage_rows,[{y:262165,runs:[[0,262165,'mapped_land_support']]}]);
});
