// Extract the supported complement without changing or narrowing original scope.
// Whole-source science remains in the stock diagnostic and authority constructor.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {gunzipSync} from 'node:zlib';
import {pinReader, jsonBytes, digest, admitPublication} from '../../../../scripts/prepare-delivery-handoff.mjs';
const [configPath, destination] = process.argv.slice(2);
assert(configPath && destination && process.argv.length === 4, 'Use CONFIG FRESH_DESTINATION');
const root = fs.realpathSync(process.cwd());
assert(/^coordination\/engineering\/angola-repair-delivery-20261017\/[a-zA-Z0-9_/-]+$/.test(destination));
assert(destination.split('/').every(part => part && part !== '.' && part !== '..'));
// Admit the entire fresh destination before reading or computing the partition.
let current = root;
for (const part of destination.split('/')) {
  current = path.join(current, part);
  const stat = fs.lstatSync(current, {throwIfNoEntry: false});
  if (stat) assert(stat.isDirectory() && fs.realpathSync(current) === current, 'Nonordinary destination');
}
assert(!fs.lstatSync(current, {throwIfNoEntry: false}), 'Occupied destination');
const configRaw = fs.readFileSync(configPath), config = JSON.parse(configRaw);
const reader = pinReader(root), inputs = {};
for (const [role, locator] of Object.entries(config.inputs)) {
  const pin = reader.pin(locator.commit, locator.path);
  assert(pin.bytes <= 16 * 1024 * 1024, 'Bounded whole input required');
  inputs[role] = pin;
}
assert.equal(Object.values(inputs).reduce((n, p) => n + p.bytes, 0) < 32 * 1024 * 1024, true);
const diagnostic = reader.json(inputs.diagnostic), original = reader.json(inputs.original_patch);
const source = reader.json(inputs.source_evidence);
const foreignBytes = gunzipSync(reader.read(inputs.foreign_overlap), {maxOutputLength: 16 * 1024 * 1024});
const foreign = JSON.parse(foreignBytes);
assert.deepEqual(diagnostic.original_pins.native_patch, inputs.original_patch);
assert.deepEqual(diagnostic.original_pins.source_evidence, inputs.source_evidence);
assert.deepEqual(diagnostic.requested_rows, original.rows);
function cells(rows) {
  const found = new Map();
  for (const {y, runs} of rows) for (const [start, end, owner] of runs) {
    assert(Number.isSafeInteger(y) && Number.isSafeInteger(start) && Number.isSafeInteger(end)
      && Number.isSafeInteger(owner) && end > start);
    for (let x = start; x < end; x++) {
      const key = `${y}:${x}`;
      assert(!found.has(key), 'Duplicate native cell'); found.set(key, owner);
    }
  }
  return found;
}
const requested = cells(original.rows), supported = cells(diagnostic.supported_rows), held = cells(diagnostic.held_rows);
assert.equal(requested.size, 170526); assert.equal(supported.size, 141263); assert.equal(held.size, 29263);
assert.equal(requested.size, supported.size + held.size);
for (const [key, owner] of requested) {
  assert.notEqual(supported.has(key), held.has(key), 'Partition must cover exactly once');
  assert.equal(supported.get(key) ?? held.get(key), owner);
}
const independent = new Map();
for (const row of foreign.rows) {
  const key = `${row.y}:${row.x}`;
  assert(!independent.has(key), 'Duplicate independent centre'); independent.set(key, row.owner);
}
assert.deepEqual(independent, held, 'Every held cell must equal the independent foreign-source union');
const owners = new Map(source.targets.map(t => [t.pixelIndex, t]));
assert.equal(owners.size, source.targets.length); assert.equal(owners.size, 47);
const count = (map, owner) => [...map.values()].filter(value => value === owner).length;
const targets = [...owners].map(([owner, target]) => ({target_id: target.id, pixelIndex: owner,
  requested_cells: count(requested, owner), supported_cells: count(supported, owner), held_cells: count(held, owner)}));
for (const target of targets) assert.equal(target.requested_cells, target.supported_cells + target.held_cells);
const accounting = {version: 1, kind: 'original-angola-conservative-disposition-v1', inputs,
  requested_cells: requested.size, supported_cells: supported.size, held_cells: held.size,
  original_owners: owners.size, supported_owners: new Set(supported.values()).size,
  held_owners: new Set(held.values()).size, targets,
  limitations: ['Original diagnostic requested rows and original native patch remain unchanged.',
    'Held centres exactly equal the independent whole foreign ADM1 overlap union. No held centre receives repair credit.',
    'This supported-patch extraction is not source qualification, current-owner-zero or selected/emitted-output acceptance.',
    'All full original geometries, source uncertainty, JRC contrary-water observations and separate packages remain retained.']};
const products = {'native-patch.json': jsonBytes({rows: diagnostic.supported_rows}),
  'held-native-rows.json': jsonBytes({rows: diagnostic.held_rows}),
  'original-scope-disposition.json': jsonBytes(accounting)};
const result = admitPublication(root, destination, products,
  {phase: 'angola-conservative-extraction', config_sha256: digest(configRaw), inputs}, false)();
console.log(JSON.stringify({...result, requested_cells: requested.size, supported_cells: supported.size, held_cells: held.size}));
