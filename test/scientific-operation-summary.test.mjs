import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {scientificOperationSummary} from '../scripts/native-ownership/scientific-operation-summary.mjs';

const hash = value => createHash('sha256').update(value).digest('hex');
const bytes = value => Buffer.from(JSON.stringify(value) + '\n');
const canonical = value => Array.isArray(value) ? value.map(canonical)
  : value && typeof value === 'object'
    ? Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])])) : value;
const recordHash = value => hash(JSON.stringify(canonical(value)) + '\n');

function fixture(phase = 'physical') {
  // Actual sourceCohort/run_physical receipt and stdout shapes. Synthetic paths
  // stand in for installed local files; no scientific operation is executed.
  const files = Array.from({length: 388}, (_, i) => ({path: `/Users/fixture/runtime/module-${i}.py`, bytes: i + 1,
    sha256: hash(String(i))}));
  const binding = {phase, config_sha256: 'a'.repeat(64), program_sha256: 'b'.repeat(64), entry_sha256: 'c'.repeat(64)};
  const destination = '.cache/delivery-handoff/fixture';
  const admission = {version: 1, observed_unix_seconds: 1792020000,
    allowance: {phaseBytes: 536870912, rssBytes: 536870912}, runtime_inventory_bytes: 75466,
    execution_reserve_bytes: 33721054, program_sha256: binding.program_sha256, config_sha256: 'd'.repeat(64), runtime_files: files};
  const execution = {version: 1, complete: true, program: {path: 'scripts/qualify-source-cohort.py', sha256: binding.program_sha256},
    outputs: [{path: `${destination}/whole-target-support.json`, bytes: 3, sha256: hash('{}\n')}], inputs: [],
    fresh_admission: admission, peak_rss_bytes: 301000000, elapsed_seconds: 2.5,
    limits: ['Physical source-relative evidence only; no selected acceptance.', 'RSS checks occur at boundaries.']};
  const products = {'whole-target-support.json': Buffer.from('{}\n'), 'execution-receipt.json': bytes(execution)};
  const preparation = bytes({version: 1, binding, outputs: Object.fromEntries(Object.entries(products)
    .map(([name, raw]) => [name, {bytes: raw.length, sha256: hash(raw)}]))});
  const publication = {destination, resumed: false, binding, observation: {elapsed_seconds: 2.7,
    allowance: admission.allowance, runtime_inventory: files.map(pin => ({...pin, resolved: pin.path})),
    limits: ['Scientific checks are cooperative boundaries, not process-tree enforcement.']}};
  return {publication, products, preparation, execution, admission};
}

test('actual physical shapes retain binding, exact receipt/output refs and observed operating quantities compactly', () => {
  const f = fixture(), originals = {publication: JSON.stringify(f.publication), preparation: Buffer.from(f.preparation),
    receipt: Buffer.from(f.products['execution-receipt.json'])};
  const s = scientificOperationSummary(f.publication, f), raw = JSON.stringify(s);
  assert.equal(s.kind, 'derived-scientific-operation-summary');
  assert.deepEqual(s.binding, f.publication.binding);
  assert.equal(s.artifacts.preparation.sha256, hash(f.preparation));
  assert.equal(s.artifacts.execution_receipt.sha256, hash(f.products['execution-receipt.json']));
  assert.equal(s.artifacts.execution_receipt.path, f.publication.destination + '/execution-receipt.json');
  assert.equal(s.outputs.length, 2);
  assert.equal(s.outputs[0].bytes, 3);
  assert.equal(s.observed.elapsed_seconds, 2.7);
  assert.equal(s.observed.execution.elapsed_seconds, 2.5);
  assert.equal(s.observed.execution.peak_rss_bytes, 301000000);
  assert.equal(s.observed.receipt_complete, true);
  assert.deepEqual(s.admission.allowance, f.admission.allowance);
  assert.equal(s.admission.config_sha256, 'd'.repeat(64)); // Phase config differs from outer binding.
  assert.equal(s.runtime_inventory.records, 388);
  assert.equal(s.runtime_inventory.complete_records_sha256, recordHash(f.publication.observation.runtime_inventory));
  assert.equal(s.admission.runtime_inventory.complete_records_sha256, recordHash(f.admission.runtime_files));
  assert(raw.length < 5000 && raw.length < JSON.stringify(f.publication).length / 10);
  assert(!raw.includes('/Users/') && !raw.includes('module-'));
  assert.equal(JSON.stringify(f.publication), originals.publication);
  assert(f.preparation.equals(originals.preparation));
  assert(f.products['execution-receipt.json'].equals(originals.receipt));
  assert(!('exit_code' in s.observed) && !('success' in s) && !('qualified_cells' in s));
});

test('runtime hash covers complete records and canonical keys without exposing their paths', () => {
  const f = fixture(), first = scientificOperationSummary(f.publication, f);
  f.publication.observation.runtime_inventory[0].extra_identity_field = 'retained';
  const second = scientificOperationSummary(f.publication, f);
  assert.notEqual(first.runtime_inventory.complete_records_sha256, second.runtime_inventory.complete_records_sha256);
  f.publication.observation.runtime_inventory = f.publication.observation.runtime_inventory.map(pin =>
    Object.fromEntries(Object.entries(pin).reverse()));
  assert.equal(second.runtime_inventory.complete_records_sha256,
    scientificOperationSummary(f.publication, f).runtime_inventory.complete_records_sha256);
});

test('source shape takes admission and operating facts from original qualification when receipt lacks them', () => {
  const f = fixture('source'); delete f.execution.fresh_admission; delete f.execution.peak_rss_bytes;
  f.products['execution-receipt.json'] = bytes(f.execution);
  f.products['source-qualification.json'] = bytes({fresh_admission: f.admission, elapsed_seconds: 1.2,
    peak_rss_bytes: 299000000, operating_limits: ['Parsed/native expansion remains data-dependent.']});
  const s = scientificOperationSummary(f.publication, {products: f.products});
  assert.equal(s.admission.runtime_inventory.records, 388);
  assert.equal(s.observed.qualification.peak_rss_bytes, 299000000);
  assert(s.limits.includes('Parsed/native expansion remains data-dependent.'));
  assert(s.outputs.every(pin => pin.declared_in === 'provided-product-bytes'));
});

test('failure and partial artifacts never become completion, success, inferred exit0 or credit', () => {
  const partial = Buffer.from('{"complete":');
  const input = {exit_code: 1, signal: 'SIGTERM', qualified_cells: 123, observation: {elapsed_seconds: 0.5,
    error: new Error('failed opening /Users/fixture/private-file.json'), limits: ['Details at /Users/fixture/private.log']}};
  const before = Buffer.from(partial), s = scientificOperationSummary(input, {executionReceipt: partial});
  assert.equal(s.observed.exit_code, 1); assert.equal(s.observed.signal, 'SIGTERM');
  assert.deepEqual(s.unparsed_artifacts, ['execution_receipt']);
  assert.equal(s.artifacts.execution_receipt.sha256, hash(partial));
  assert.equal(s.error.message_sha256, hash(input.observation.error.message));
  assert(!('receipt_complete' in s.observed) && !('success' in s) && !('qualified_cells' in s));
  assert(!JSON.stringify(s).includes('/Users/') && !JSON.stringify(s).includes('private-file'));
  assert(partial.equals(before));
  const incomplete = scientificOperationSummary({}, {executionReceipt: bytes({complete: false, exit_code: 2})});
  assert.equal(incomplete.observed.receipt_complete, false);
  assert.equal(incomplete.observed.execution.exit_code, 2);
  assert(!('exit_code' in scientificOperationSummary().observed));
});

test('failure messages cannot leak URI, punctuation-adjacent or unfamiliar absolute paths', () => {
  for (const message of ['failed:file:///Users/fixture/private.json', 'failed:/Users/fixture/private.json',
    'read /etc/private.conf', 'open /data/private.json', 'detail;/data/private.json', 'detail[/data/private.json', 'failed:C:\\Users\\fixture\\private.json']) {
    const s = scientificOperationSummary({error: message, observation: {limits: [message]}});
    assert.deepEqual(s.error, {message_sha256: hash(message)});
    const raw = JSON.stringify(s);
    assert(!raw.includes('private.') && !raw.includes('/Users/') && !raw.includes('C:\\\\Users'));
    assert.equal(s.limits.length, 1);
  }
});

test('absolute artifact locations are omitted and parsed values cannot invent whole-file hashes', () => {
  const f = fixture(); f.publication.destination = '/Users/fixture/checkout/output';
  const parsedReceipt = JSON.parse(f.preparation);
  const s = scientificOperationSummary(f.publication, {preparation: parsedReceipt, executionReceipt: f.execution});
  assert(!JSON.stringify(s).includes('/Users/'));
  assert(s.omitted_destination_sha256 && !s.destination);
  assert(s.artifacts.preparation.canonical_value_sha256 && !s.artifacts.preparation.sha256);
  assert(s.outputs.every(pin => !pin.path && pin.omitted_path_sha256));
});

test('resume and missing observations do not synthesize a new execution observation', () => {
  const f = fixture(); delete f.publication.observation; f.publication.resumed = true;
  const s = scientificOperationSummary(f.publication, {preparation: f.preparation});
  assert.equal(s.resumed, true); assert.deepEqual(s.observed, {});
  assert(!s.runtime_inventory && !s.admission);
  assert.equal(s.outputs.length, 2);
});
