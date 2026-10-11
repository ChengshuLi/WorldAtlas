// Actual emitted selected-delivery check. Expectations are caller-reviewed
// rosters, not a new source-authority or scientific approval mechanism.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {gunzipSync} from 'node:zlib';
import {repositoryReader, sha256} from './evidence-quality.mjs';
import {loadOwnershipAssets} from '../src/ownership-assets.js';
import {loadAdditiveNativePatch, effectivePrimitiveGeometries, footprintValueSha256,
  verifyAdditiveLedgerSelection} from '../src/effective-footprint.js';
import {pickOwnership, samplePackedOwnership} from '../src/pixel-ownership.js';

const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const text = value => typeof value === 'string' && value.trim().length > 0;
function exactKeys(value, keys, label) {
  assert(value && typeof value === 'object' && !Array.isArray(value), `${label} must be an object`);
  assert.deepEqual(Object.keys(value).sort(), [...keys].sort(), `${label} has missing/foreign fields`);
}
function uniqueStrings(values, label) {
  assert(Array.isArray(values) && values.length > 0 && values.every(text), `${label} must be nonempty`);
  assert.equal(new Set(values).size, values.length, `Duplicate ${label}`);
}

export function validateDeliveryExpectations(value) {
  exactKeys(value, ['version', 'selected_ledger_sha256', 'cumulative_native_cells', 'cohorts'], 'Expectations');
  assert.equal(value.version, 1, 'Unsupported expectations version');
  assert(hash(value.selected_ledger_sha256), 'Missing selected ledger hash');
  assert(Number.isSafeInteger(value.cumulative_native_cells) && value.cumulative_native_cells >= 0,
    'Invalid expected cumulative native cells');
  assert(Array.isArray(value.cohorts) && value.cohorts.length > 0, 'Missing expected cohorts');
  const batches = new Set(), components = new Set();
  for (const cohort of value.cohorts) {
    exactKeys(cohort, ['original_batch_id', 'component_ids', 'members'], 'Expected cohort');
    assert(text(cohort.original_batch_id) && !batches.has(cohort.original_batch_id), 'Missing/duplicate original batch ID');
    batches.add(cohort.original_batch_id);
    uniqueStrings(cohort.component_ids, 'expected component roster');
    assert(Array.isArray(cohort.members), 'Missing expected members');
    for (const member of cohort.members) {
      exactKeys(member, ['component_id', 'target_id', 'disposition', 'geometry_sha256'], 'Expected member');
      assert(text(member.component_id) && !components.has(member.component_id), 'Missing/duplicate expected member');
      components.add(member.component_id);
      assert(text(member.target_id) && ['assigned', 'zero-cell'].includes(member.disposition)
        && hash(member.geometry_sha256), 'Invalid expected target/disposition/geometry');
    }
    assert.deepEqual(cohort.members.map(member => member.component_id).sort(), [...cohort.component_ids].sort(),
      'Expected members must cover the complete component roster exactly');
  }
  return value;
}

// Exported kernel uses the actual production effective primitive, picker and
// sampler entry points. The CLI obtains all arguments from authenticated bytes.
export function verifySelectedDelivery({expectations, ledger, ledgerSha256, patch, patchSha256,
  features, base, effective, request, result}) {
  validateDeliveryExpectations(expectations);
  assert.equal(ledgerSha256, expectations.selected_ledger_sha256, 'Wrong selected ledger hash');
  assert.equal(patch.ledger_sha256, ledgerSha256, 'Patch ledger differs');
  verifyAdditiveLedgerSelection(ledger, features, patch);
  const selected = new Map(), loaded = new Map();
  for (const row of ledger.rows) {
    assert(!selected.has(row.component_id), 'Duplicate selected component');
    selected.set(row.component_id, row);
  }
  for (const feature of features) {
    assert(text(feature.id) && !loaded.has(feature.id), 'Duplicate/missing loaded target');
    loaded.set(feature.id, feature);
  }
  const cohorts = expectations.cohorts.map(cohort => ({
    original_batch_id: cohort.original_batch_id,
    members: cohort.members.map(member => {
      const row = selected.get(member.component_id);
      assert(row, `Missing selected member: ${member.component_id}`);
      for (const field of ['target_id', 'disposition', 'geometry_sha256'])
        assert.equal(row[field], member[field], `Selected member ${field} differs: ${member.component_id}`);
      const target = loaded.get(member.target_id);
      assert(target && target.pixelIndex === row.pixelIndex, `Missing/wrong loaded target: ${member.target_id}`);
      const components = target.additiveFootprint?.components;
      assert(Array.isArray(components), 'Expected selected V2 target components');
      const matches = components.filter(component => component.component_id === member.component_id);
      assert.equal(matches.length, 1, 'Expected exactly one loaded component');
      assert.deepEqual(matches[0], row, 'Loaded component differs from selected row');
      assert.equal(footprintValueSha256(row.geometry), member.geometry_sha256, 'Actual selected geometry differs');
      assert(effectivePrimitiveGeometries(target).some(geometry =>
        footprintValueSha256(geometry) === member.geometry_sha256), 'Actual geometry absent from effective primitives');
      return {...member, effective_primitive_verified: true};
    })
  }));
  let added = 0;
  for (const row of patch.rows) for (const [start, end, id] of row.runs) for (let x = start; x < end; x++) {
    assert.equal(pickOwnership(base, x, row.y), 0, 'Patch cell was already occupied');
    assert.equal(pickOwnership(effective, x, row.y), id, 'Patched picker owner differs');
    assert.equal(samplePackedOwnership(effective, {x, y: row.y, width: 1, height: 1})[0], id,
      'Patched sampler owner differs');
    added++;
  }
  assert.equal(added, expectations.cumulative_native_cells, 'Wrong cumulative native cell count');
  assert.equal(added, result?.native?.assigned_cells, 'Rebind result native cell count differs');
  assert.equal(added, effective.additive_added_cells, 'Loaded effective native cell count differs');
  assert(Array.isArray(request?.current_rows) && request.current_rows.length > 0
    && Array.isArray(request?.acquisition?.predecessor_rows) && request.acquisition.predecessor_rows.length > 0,
  'Missing current/predecessor stable-owner controls');
  const observed = new Map();
  for (const row of [...request.current_rows, ...request.acquisition.predecessor_rows]) {
    assert(Number.isInteger(row.y) && row.y >= 0 && row.y < base.size && Array.isArray(row.runs),
      'Invalid stable-owner control row');
    if (observed.has(row.y)) assert.deepEqual(observed.get(row.y), row, 'Conflicting stable-owner control row');
    else observed.set(row.y, row);
  }
  // Retain the original nonvacuous control: one known occupied cell in EVERY
  // unique observed current/predecessor row. This is not a full-grid proof.
  for (const row of observed.values()) {
    const run = row.runs.find(run => Array.isArray(run) && run.length === 3 && run.every(Number.isInteger)
      && run[0] >= 0 && run[0] < run[1] && run[1] <= base.size && run[2] > 0);
    assert(run, 'Stable-owner row has no occupied control');
    const [x, , id] = run;
    assert.equal(pickOwnership(base, x, row.y), id, 'Stable base owner changed');
    assert.equal(pickOwnership(effective, x, row.y), id, 'Stable effective owner changed');
    assert.equal(samplePackedOwnership(effective, {x, y: row.y, width: 1, height: 1})[0], id,
      'Stable sampled owner changed');
  }
  return {version: 1, kind: 'actual-emitted-selected-consumer', passed: true,
    feature_count: features.length, selected_ledger_sha256: ledgerSha256, selected_patch_sha256: patchSha256,
    cumulative_native_cells_picked_and_sampled: added, stable_owner_controls: observed.size,
    expected_components_verified: cohorts.reduce((n, cohort) => n + cohort.members.length, 0), cohorts,
    limitation: 'Production Node-compatible asset loader, effective primitive, picker and renderer-sampler entry points on actual emitted assets. GPU and Canvas execution still require hosted browser testing. Original batch IDs and complete rosters are supplied reviewed expectations, not independent source or whole-batch approval. Zero-cell inclusion is not visible-pixel gain; stable-owner controls sample one occupied cell per retained observed row.'};
}

function admitOutput(filename) {
  assert(text(filename) && !filename.includes('\0'), 'Missing output path');
  const output = path.resolve(filename), parent = path.dirname(output);
  assert.equal(fs.realpathSync(parent), parent, 'Output symlink parent refused');
  assert(fs.lstatSync(parent).isDirectory(), 'Output parent must be an existing directory');
  assert(!fs.lstatSync(output, {throwIfNoEntry: false}), 'Output collision');
  return output;
}

export async function runSelectedDeliverySmoke({root = process.cwd(), emittedDirectory = path.join(root, 'dist/client'),
  expectationsPath, outputPath}) {
  const output = admitOutput(outputPath), inputs = new Map();
  const readRoot = repositoryReader(root), readEmitted = repositoryReader(emittedDirectory);
  const read = (scope, name, pin, {nativePart = false} = {}) => {
    const bytes = (scope === 'root' ? readRoot : readEmitted)(name, 'candidate');
    const descriptor = {scope, path: name, bytes: bytes.length, sha256: sha256(bytes)};
    if (pin) {
      // packageStartupOwnership omits encoded bytes on its native run
      // descriptors. The encoded hash remains mandatory; production loading
      // separately authenticates decoded words and their complete coverage.
      const omittedNativeBytes = nativePart && !Object.hasOwn(pin, 'bytes')
        && hash(pin.decoded_sha256) && Number.isSafeInteger(pin.words) && pin.words > 0;
      assert(hash(pin.sha256) && (Number.isSafeInteger(pin.bytes) || omittedNativeBytes),
        'Missing whole-file asset pin');
      if (!omittedNativeBytes) assert.equal(descriptor.bytes, pin.bytes, `Whole asset bytes differ: ${name}`);
      assert.equal(descriptor.sha256, pin.sha256, `Whole asset hash differs: ${name}`);
    }
    const key = `${scope}:${name}`;
    if (inputs.has(key)) assert.deepEqual(inputs.get(key), descriptor, `Consumed asset changed: ${name}`);
    else inputs.set(key, descriptor);
    return bytes;
  };
  const whole = (scope, pin) => {
    assert(pin && typeof pin.path === 'string', 'Missing required asset');
    return JSON.parse(read(scope, pin.path, pin));
  };
  assert(text(expectationsPath), 'Missing expectations path');
  const expectationsFile = path.resolve(expectationsPath);
  const expectationsBytes = repositoryReader(path.dirname(expectationsFile))(path.basename(expectationsFile), 'candidate');
  const expectations = validateDeliveryExpectations(JSON.parse(expectationsBytes));
  const selection = JSON.parse(read('root', 'data/ownership-selection.json'));
  const sidecar = whole('root', selection.additive_release);
  const envelope = whole('root', sidecar.runtime_envelope);
  const atlas = JSON.parse(read('emitted', 'atlas-geography.json'));
  assert.deepEqual(atlas.additiveRelease, envelope, 'Actual emitted envelope differs from selected release');
  assert.equal(envelope.ledger.sha256, expectations.selected_ledger_sha256, 'Wrong selected ledger hash');
  const ledger = whole('emitted', envelope.ledger), patch = whole('emitted', envelope.patch);
  const certificate = whole('root', ledger.current_rebind);
  const request = whole('root', certificate.request), result = whole('root', certificate.result);
  const assets = new Map(), nativeParts = new Set(atlas.pixelMap?.method === 'native-linear-evenodd-first-owner-v1'
    ? (atlas.pixelMap.parts ?? []).map(part => part.path) : []);
  for (const descriptor of [...(atlas.pixelMap?.parts ?? []), envelope.ledger, envelope.patch,
    envelope.owner_roster, envelope.base_manifest]) {
    assert(descriptor && !assets.has(descriptor.path), 'Missing/duplicate emitted asset path');
    assets.set(descriptor.path, descriptor);
  }
  const fetcher = async name => {
    assert(typeof name === 'string', 'Invalid asset fetch path');
    const relative = name.startsWith('./') ? name.slice(2) : name;
    const descriptor = assets.get(relative);
    assert(descriptor, `Unlisted emitted asset: ${relative}`);
    const bytes = read('emitted', relative, descriptor, {nativePart: nativeParts.has(relative)});
    return new Response(bytes, {status: 200, headers: {'Content-Length': String(bytes.length)}});
  };
  const base = await loadOwnershipAssets(atlas.pixelMap, fetcher);
  uniqueStrings(atlas.parts, 'emitted feature parts');
  const features = atlas.parts.flatMap(name => {
    const bytes = read('emitted', name);
    const body = name.endsWith('.gz') ? gunzipSync(bytes, {maxOutputLength: 32 * 1024 * 1024}) : bytes;
    const rows = JSON.parse(body);
    assert(Array.isArray(rows) && rows.length > 0, 'Missing emitted feature records');
    return rows;
  });
  const effective = await loadAdditiveNativePatch(atlas, features, base, {fetcher});
  const report = verifySelectedDelivery({expectations, ledger, ledgerSha256: envelope.ledger.sha256,
    patch, patchSha256: envelope.patch.sha256, features, base, effective, request, result});
  report.expectations_sha256 = sha256(expectationsBytes);
  report.inputs = [...inputs.values()].sort((a, b) => `${a.scope}:${a.path}`.localeCompare(`${b.scope}:${b.path}`));
  // Failures before this point create nothing. Exclusive creation rejects both
  // ordinary collisions and dangling symlinks; parent symlinks are refused too.
  admitOutput(output);
  fs.writeFileSync(output, JSON.stringify(report, null, 2) + '\n',
    {flag: fs.constants.O_WRONLY | fs.constants.O_CREAT | fs.constants.O_EXCL | fs.constants.O_NOFOLLOW});
  return report;
}

export async function main(args = process.argv.slice(2)) {
  if (args.length === 1 && args[0] === '--help') {
    console.log('Usage: node scripts/selected-delivery-smoke.mjs --expectations FILE --output NEW_FILE [--root REPO] [--emitted-directory DIR]');
    return;
  }
  const names = new Map([['--root', 'root'], ['--emitted-directory', 'emittedDirectory'],
    ['--expectations', 'expectationsPath'], ['--output', 'outputPath']]), options = {};
  for (let i = 0; i < args.length; i += 2) {
    const name = names.get(args[i]);
    assert(name && !Object.hasOwn(options, name) && text(args[i + 1]) && !args[i + 1].startsWith('--'),
      `Unknown, duplicate or incomplete option: ${args[i]}`);
    options[name] = args[i + 1];
  }
  const report = await runSelectedDeliverySmoke(options);
  console.log(JSON.stringify(report));
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(error => {console.error(error.message); process.exitCode = 1;});
}
