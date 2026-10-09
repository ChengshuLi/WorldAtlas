import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gunzipSync, gzipSync} from 'node:zlib';
import {fileURLToPath} from 'node:url';
import {admitPhase, authenticateAdmittedBody, readAdmittedBody} from './phase-admission.mjs';
import {serializeQualifiedGeometryChanges, restoreOriginalGeometrySerialization} from './application-geometry-serialization.mjs';

const sha = body => createHash('sha256').update(body).digest('hex');

// A finished application serialization phase. No geometry/scientific operator
// executes here. The original qualified artifact remains in separate custody.
export function issueApplicationGeometry(plan, destination) {
  assert.equal(plan.kind, 'qualified-geometry-application-serialization-plan-v1');
  assert.equal(plan.head, process.env.WORLDATLAS_SELECTED_NATIVE_HEAD);
  assert.equal(plan.runtime.path, process.execPath);
  assert.deepEqual(plan.code.map(pin => pin.path).sort(),
    ['application-geometry-producer.mjs', 'application-geometry-serialization.mjs', 'phase-admission.mjs']
      .map(name => fileURLToPath(new URL(name, import.meta.url))).sort());
  const output = path.resolve(destination);
  assert(!destination.split(path.sep).includes('..'));
  assert(output.startsWith(path.resolve(plan.outputRoot) + path.sep));
  assert(!fs.lstatSync(output, {throwIfNoEntry: false}), 'Fresh output required');
  for (let ancestor = path.dirname(output);; ancestor = path.dirname(ancestor)) {
    const stat = fs.lstatSync(ancestor, {throwIfNoEntry: false});
    if (stat) assert(stat.isDirectory() && !stat.isSymbolicLink());
    if (ancestor === path.dirname(ancestor)) break;
  }
  assert.equal(plan.sources.length, 3);
  assert.deepEqual(plan.sources.map(pin => pin.role), ['original-application-part', 'qualified-scientific-part', 'qualified-changed-records']);
  // Stat-only complete admission precedes all source/runtime body reads. The
  // independently pinned launcher also authenticates code/runtime before import.
  const admission = admitPhase({inputs: [...plan.sources, ...plan.code], runtime: plan.runtime,
    outputReserve: plan.outputReserve, metadataBytes: plan.metadataBytes});
  const read = pin => readAdmittedBody(admission, pin.path);
  for (const pin of [...plan.code, plan.runtime]) authenticateAdmittedBody(admission, pin.path);
  const original = read(plan.sources[0]), encoded = read(plan.sources[1]);
  const qualified = gunzipSync(encoded, {maxOutputLength: plan.sources[1].decoded_bytes});
  assert.equal(qualified.length, plan.sources[1].decoded_bytes);
  assert.equal(sha(qualified), plan.sources[1].decoded_sha256);
  const changedRaw = read(plan.sources[2]), changedRows = JSON.parse(changedRaw);
  const ids = changedRows.map(row => row.id);
  assert.equal(ids.length, plan.changedCount);
  const result = serializeQualifiedGeometryChanges(original, qualified, ids);
  const features = JSON.parse(result.output).features;
  for (const row of changedRows) {
    const matches = features.filter(feature => feature.id === row.id);
    assert.equal(matches.length, 1);
    assert.equal(JSON.stringify(matches[0].geometry), JSON.stringify(row.geometry));
  }
  assert(restoreOriginalGeometrySerialization(result.output, result.inverse).equals(original));
  const compressed = gzipSync(result.output, {level: 9});
  assert(compressed.length <= 8 * 1024 * 1024 && result.output.length <= 32 * 1024 * 1024);
  const inverse = Buffer.from(JSON.stringify({version: 1, kind: 'whole-original-record-byte-inverse',
    original_bytes: original.length, original_sha256: sha(original),
    application_bytes: result.output.length, application_sha256: sha(result.output),
    records: result.inverse}, null, 2) + '\n');
  const receipt = Buffer.from(JSON.stringify({version: 1, kind: 'qualified-geometry-application-serialization',
    source_head: plan.head, sources: plan.sources, code: plan.code, runtime: plan.runtime,
    changed_ids: result.changed_ids, unchanged_literal_full_records: result.unchanged_full_records,
    application: {bytes: compressed.length, sha256: sha(compressed), decoded_bytes: result.output.length, decoded_sha256: sha(result.output)},
    inverse: {bytes: inverse.length, sha256: sha(inverse)},
    full_qualified_record_values_equal: true, exact_qualified_target_geometry_json: true,
    complete_original_byte_inverse: true, scientific_execution: false,
    prospective_phase_bytes: admission.bytes, output_reserve_bytes: plan.outputReserve}, null, 2) + '\n');
  assert(compressed.length + result.output.length + inverse.length + receipt.length <= plan.outputReserve);
  for (const pin of [...plan.code, plan.runtime]) authenticateAdmittedBody(admission, pin.path);
  fs.mkdirSync(output);
  fs.writeFileSync(path.join(output, 'part-29-application.json.gz'), compressed, {flag: 'wx', mode: 0o644});
  fs.writeFileSync(path.join(output, 'application-geometry-inverse.json'), inverse, {flag: 'wx', mode: 0o644});
  fs.writeFileSync(path.join(output, 'application-geometry-receipt.json'), receipt, {flag: 'wx', mode: 0o644});
  return JSON.parse(receipt);
}
