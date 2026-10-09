import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {admitPhase, authenticateAdmittedBody, readAdmittedBody} from './phase-admission.mjs';
import {selectedDestination} from './selected-native-producer.mjs';
import {repackNativePart} from './repack-native-part.mjs';
import * as sparse from './sparse-native-repack.mjs';
import {decodeInstalledWords} from './selected-native-inputs.mjs';
import {shuffleOwnershipBytes, unshuffleOwnershipBytes} from '../../../src/ownership-codec.js';
const sha = body => createHash('sha256').update(body).digest('hex');

export function produceRepackedNativePart(plan, outputValue) {
  const output = selectedDestination(outputValue);
  assert.equal(plan.kind, 'qualified-selected-native-whole-part-repack');
  assert.equal(plan.source_head, process.env.WORLDATLAS_SELECTED_NATIVE_HEAD);
  assert.equal(sha(JSON.stringify(plan)), process.env.WORLDATLAS_SELECTED_NATIVE_PLAN_SHA256);
  assert.equal(process.execPath, plan.runtime.path); assert.equal(process.version, plan.runtime.version);
  assert.deepEqual(process.execArgv, []); assert(!process.env.NODE_OPTIONS && !process.env.NODE_PATH);
  const admission = admitPhase({inputs: plan.inputs, runtime: plan.runtime,
    outputReserve: plan.output_reserve, metadataBytes: plan.metadata_bytes,
    reservedInputBytes: plan.canonical_unshuffle_bytes});
  assert.equal(plan.canonical_unshuffle_bytes, plan.rows.decoded_bytes + plan.part.decoded_bytes);
  const sources = plan.code.map(pin => readAdmittedBody(admission, pin.path).toString());
  const functions = [produceRepackedNativePart, selectedDestination, repackNativePart, decodeInstalledWords,
    admitPhase, authenticateAdmittedBody, readAdmittedBody, shuffleOwnershipBytes, unshuffleOwnershipBytes,
    ...Object.values(sparse)];
  const fingerprints = functions.map(fn => Function.prototype.toString.call(fn));
  function guard() {
    assert.deepEqual(functions.map(fn => Function.prototype.toString.call(fn)), fingerprints);
    for (const fingerprint of fingerprints) assert(sources.some(body => body.includes(fingerprint)));
    for (const pin of plan.code) authenticateAdmittedBody(admission, pin.path);
    authenticateAdmittedBody(admission, plan.runtime.path);
  }
  guard(); const started = new Date().toISOString();
  const {encoded, report} = repackNativePart(admission, plan);
  const reportBody = Buffer.from(JSON.stringify(report) + '\n');
  assert(encoded.length + plan.part.decoded_bytes * 2 + reportBody.length <= plan.output_reserve);
  for (const pin of plan.inputs) authenticateAdmittedBody(admission, pin.path);
  guard();
  const execution = Buffer.from(JSON.stringify({kind: 'whole-native-part-byte-execution', source_head: plan.source_head,
    started_at: started, completed_at: new Date().toISOString(), phase_bytes: admission.bytes,
    descriptors: admission.descriptors, original_part_sha256: plan.part.sha256,
    output: report.current_part, full_original_word_inverse: true, grid_rows_computed: 0, activated: false}) + '\n');
  assert(encoded.length + reportBody.length + execution.length <= plan.output_reserve);
  fs.mkdirSync(output, {recursive: true});
  fs.writeFileSync(path.join(output, 'current-part.bin.gz'), encoded, {flag: 'wx', mode: 0o644});
  fs.writeFileSync(path.join(output, 'inverse-proof.json'), reportBody, {flag: 'wx', mode: 0o644});
  fs.writeFileSync(path.join(output, 'execution.json'), execution, {flag: 'wx', mode: 0o644});
  return JSON.parse(execution);
}
