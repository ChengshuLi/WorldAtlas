import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {gunzipSync} from 'node:zlib';
import {admitPhase, authenticateAdmittedBody, readAdmittedBody} from './phase-admission.mjs';
import {footprintContinuation} from './footprint-continuation.mjs';
const sha = body => createHash('sha256').update(body).digest('hex');
const MAX = 32 * 1024 * 1024;
const ORIGINAL = 'c67345546a24479e29ff9e2872098c78b256209a';
const BASE = 'data/canonical-grid/eastern-v8/';

export function produceFootprints(plan, outputValue) {
  const root = process.cwd();
  assert(typeof outputValue === 'string' && !outputValue.split(path.sep).includes('..'));
  const output = path.resolve(outputValue);
  assert(output.startsWith(path.join(root, '.cache') + path.sep));
  assert(!fs.existsSync(output));
  for (let ancestor = output; ; ancestor = path.dirname(ancestor)) {
    try { const stat = fs.lstatSync(ancestor); assert(!stat.isSymbolicLink()); if (ancestor !== output) assert(stat.isDirectory()); }
    catch (error) { if (error.code !== 'ENOENT') throw error; }
    if (ancestor === path.dirname(ancestor)) break;
  }
  assert.equal(plan.kind, 'complete-original-current-native-footprint-continuation');
  assert.equal(plan.original_commit, ORIGINAL);
  assert.equal(process.version, 'v24.19.0'); assert.equal(process.execArgv.length, 0);
  assert(!process.env.NODE_OPTIONS && !process.env.NODE_PATH);
  assert.equal(plan.runtime.path, process.execPath);
  assert.equal(plan.parts.length, 34);
  const parts = plan.parts;
  assert.equal(new Set(parts.map(pin => pin.path)).size, 34);
  let sourceReserve = 0, nextOwner = 1;
  for (const pin of parts) {
    assert(/^context\/part-\d+\.json\.gz$/.test(pin.path));
    assert(/^[a-f0-9]{40}$/.test(pin.oid) && /^[a-f0-9]{64}$/.test(pin.sha256));
    assert(Number.isSafeInteger(pin.bytes) && pin.bytes >= 0 && pin.bytes <= MAX);
    assert(Number.isSafeInteger(pin.decoded_bytes) && pin.decoded_bytes >= 0 && pin.decoded_bytes <= MAX);
    assert.equal(pin.first_owner, nextOwner); nextOwner += pin.owners;
    sourceReserve += pin.bytes + pin.decoded_bytes;
  }
  assert.equal(nextOwner, 49626); assert.equal(sourceReserve, 131943258);
  const admission = admitPhase({inputs: plan.inputs, runtime: plan.runtime,
    reservedInputBytes: sourceReserve, outputReserve: plan.output_reserve,
    metadataBytes: plan.metadata_bytes});
  assert(admission.descriptors + parts.length <= 512, 'Complete source/runtime/code descriptor cap');
  // Launcher independently authenticates these modules and this plan before import.
  for (const pin of admission.snapshots) authenticateAdmittedBody(admission, pin.pin.path);
  const callablePins = [admitPhase, authenticateAdmittedBody, readAdmittedBody, footprintContinuation,
    produceFootprints, execFileSync, gunzipSync].map(fn => fn.toString());
  const verify = () => {
    assert.deepEqual([admitPhase, authenticateAdmittedBody, readAdmittedBody, footprintContinuation,
      produceFootprints, execFileSync, gunzipSync].map(fn => fn.toString()), callablePins);
    for (const pin of admission.snapshots) authenticateAdmittedBody(admission, pin.pin.path);
  };
  const git = args => execFileSync(plan.git.path, ['-C', root, ...args], {maxBuffer: MAX + 1,
    env: process.env});
  assert.equal(git(['rev-parse', 'HEAD']).toString().trim(), plan.source_head);
  assert.equal(path.resolve(git(['rev-parse', '--show-toplevel']).toString().trim()), root);
  for (const pin of plan.code) {
    const line = git(['ls-tree', '-z', plan.source_head, '--', pin.relative]).toString();
    assert.equal(line, `100644 blob ${pin.oid}\t${pin.relative}\0`);
  }
  const index = JSON.parse(readAdmittedBody(admission, plan.index.path));
  assert.deepEqual(index.parts, parts.map(({oid, ...pin}) => pin), 'Complete immutable original context index');
  const changed = JSON.parse(readAdmittedBody(admission, plan.changed.path));
  const continuation = footprintContinuation(49625, changed);
  const actual = [];
  for (const pin of parts) {
    const relative = BASE + pin.path;
    const line = git(['ls-tree', '-z', ORIGINAL, '--', relative]).toString();
    assert.equal(line, `100644 blob ${pin.oid}\t${relative}\0`);
    const encoded = git(['cat-file', 'blob', pin.oid]);
    assert.equal(encoded.length, pin.bytes); assert.equal(sha(encoded), pin.sha256);
    const decoded = gunzipSync(encoded, {maxOutputLength: pin.decoded_bytes});
    assert.equal(decoded.length, pin.decoded_bytes); assert.equal(sha(decoded), pin.decoded_sha256);
    continuation.add(JSON.parse(decoded), pin.first_owner, pin.owners);
    actual.push({commit: ORIGINAL, path: relative, mode: '100644', oid: pin.oid,
      bytes: pin.bytes, sha256: pin.sha256, decoded_bytes: pin.decoded_bytes, decoded_sha256: pin.decoded_sha256});
  }
  const result = continuation.finish();
  assert.equal(result.original_footprints_sha256, plan.original_footprints_sha256);
  verify();
  const report = {...result, version: 1, kind: plan.kind, source_head: plan.source_head,
    original_commit: ORIGINAL, actual_source_bodies: actual, complete_phase_bytes: admission.bytes,
    descriptors: admission.descriptors + actual.length, original_encoded_decoded_bytes: sourceReserve,
    installed_runtime_bytes: plan.runtime.bytes, activation: false};
  assert(report.descriptors <= 512);
  const body = Buffer.from(JSON.stringify(report, null, 2) + '\n');
  assert(body.length <= plan.output_reserve && body.length <= MAX);
  fs.mkdirSync(output, {recursive: true}); fs.writeFileSync(path.join(output, 'footprints.json'), body, {flag: 'wx'});
  return report;
}
