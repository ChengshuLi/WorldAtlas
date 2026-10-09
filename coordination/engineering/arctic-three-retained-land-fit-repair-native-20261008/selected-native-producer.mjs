// The external reviewed launcher authenticates every imported code body first.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {admitPhase, authenticateAdmittedBody, readAdmittedBody} from './phase-admission.mjs';
import {loadSelectedNativeInputs} from './selected-native-inputs.mjs';
import {compileSelectedNativeProof} from './selected-native-proof.mjs';
import * as proof from './selected-native-proof.mjs';
import * as inputs from './selected-native-inputs.mjs';
import * as codec from './operand-codec.mjs';
import * as append from './append-scope.mjs';
import {compileRowBlock} from './compile-row-block.mjs';
import {nativePolygonIntervals} from '../../../src/native-grid.js';
import {coverageRow} from '../../../scripts/audit-grid-intervals.mjs';
import {unshuffleOwnershipBytes} from '../../../src/ownership-codec.js';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const sha = body => createHash('sha256').update(body).digest('hex');
export function selectedDestination(value) {
  assert(typeof value === 'string' && path.isAbsolute(value) && !value.split(path.sep).includes('..'));
  assert(value.startsWith(ROOT + '/.cache/'), 'Owned fresh destination required');
  assert(!fs.existsSync(value), 'Destination already exists');
  try { fs.lstatSync(value); assert.fail('Existing or dangling destination'); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  let current = path.dirname(value);
  while (!fs.existsSync(current)) {
    try { fs.lstatSync(current); assert.fail('Dangling destination ancestor'); }
    catch (error) { if (error.code !== 'ENOENT') throw error; }
    current = path.dirname(current);
  }
  for (;; current = path.dirname(current)) {
    const stat = fs.lstatSync(current);
    assert(stat.isDirectory() && !stat.isSymbolicLink(), 'Ordinary destination ancestors required');
    if (current === path.dirname(current)) break;
  }
  return value;
}

export function produceSelectedNative(plan, outputValue) {
  const output = selectedDestination(outputValue);
  assert.equal(plan.kind, 'complete-selected-native-input-plan');
  assert.equal(plan.source_head, process.env.WORLDATLAS_SELECTED_NATIVE_HEAD);
  assert.equal(sha(JSON.stringify(plan)), process.env.WORLDATLAS_SELECTED_NATIVE_PLAN_SHA256);
  assert.equal(process.execPath, plan.runtime.path);
  assert.equal(process.version, plan.runtime.version);
  assert.deepEqual(process.execArgv, []);
  assert(!process.env.NODE_OPTIONS && !process.env.NODE_PATH);
  const admission = admitPhase({inputs: plan.inputs, runtime: plan.runtime,
    outputReserve: plan.output_reserve, metadataBytes: plan.metadata_bytes,
    reservedInputBytes: plan.canonical_unshuffle_bytes});
  assert.equal(plan.canonical_unshuffle_bytes, [plan.installed_rows, ...plan.installed_runs]
    .reduce((sum, pin) => sum + pin.decoded_bytes, 0));
  const code = new Map();
  for (const pin of plan.code) code.set(pin.relative, readAdmittedBody(admission, pin.path).toString());
  const functions = [produceSelectedNative, selectedDestination, admitPhase,
    authenticateAdmittedBody, readAdmittedBody, compileRowBlock, nativePolygonIntervals,
    coverageRow, unshuffleOwnershipBytes, ...Object.values(proof), ...Object.values(inputs),
    ...Object.values(codec), ...Object.values(append)];
  const signatures = functions.map(fn => Function.prototype.toString.call(fn));
  function guard() {
    assert.deepEqual(functions.map(fn => Function.prototype.toString.call(fn)), signatures);
    for (const signature of signatures) assert([...code.values()].some(body => body.includes(signature)),
      'Actual callable absent from admitted whole source');
    for (const pin of plan.code) authenticateAdmittedBody(admission, pin.path);
    authenticateAdmittedBody(admission, plan.runtime.path);
  }
  guard();
  const started = new Date().toISOString();
  const loaded = loadSelectedNativeInputs(admission, plan);
  const scientific = compileSelectedNativeProof(loaded.before, loaded.after, loaded.options);
  // Serialize typed words as explicit complete arrays; no GPU layout changes.
  const body = Buffer.from(JSON.stringify({...scientific, append_proofs: loaded.appendProofs},
    (_key, value) => value instanceof Uint32Array ? [...value] : value) + '\n');
  assert(body.length <= plan.output_reserve - 65536 && body.length <= 32 * 1024 * 1024,
    'Complete selected output exceeds prospective reserve');
  guard();
  const receipt = Buffer.from(JSON.stringify({kind: 'selected-native-execution',
    source_head: plan.source_head, started_at: started, completed_at: new Date().toISOString(),
    phase_bytes: admission.bytes, descriptors: admission.descriptors,
    output: {path: 'selected-native-proof.json', bytes: body.length, sha256: sha(body)},
    checked_rows: 60, full_owner_count: 49625, activated: false}) + '\n');
  assert(body.length + receipt.length <= plan.output_reserve);
  fs.mkdirSync(output, {recursive: true});
  fs.writeFileSync(path.join(output, 'selected-native-proof.json'), body, {flag: 'wx', mode: 0o644});
  fs.writeFileSync(path.join(output, 'execution.json'), receipt, {flag: 'wx', mode: 0o644});
  return JSON.parse(receipt);
}
