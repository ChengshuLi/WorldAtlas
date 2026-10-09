import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {gunzipSync, gzipSync} from 'node:zlib';
import {admitPhase, authenticateAdmittedBody, readAdmittedBody} from './phase-admission.mjs';
import {continueContextPart} from './context-part-continuation.mjs';
const sha = body => createHash('sha256').update(body).digest('hex');
const MAX = 32 * 1024 * 1024;
const ORIGINAL = 'c67345546a24479e29ff9e2872098c78b256209a';
const BASE = 'data/canonical-grid/eastern-v8/';

export function produceContextPart(plan, outputValue) {
  const root = process.cwd();
  assert(typeof outputValue === 'string' && !outputValue.split(path.sep).includes('..'));
  const output = path.resolve(outputValue);
  assert(output.startsWith(path.join(root, '.cache') + path.sep)); assert(!fs.existsSync(output));
  for (let ancestor = output; ; ancestor = path.dirname(ancestor)) {
    try { const stat = fs.lstatSync(ancestor); assert(!stat.isSymbolicLink()); if (ancestor !== output) assert(stat.isDirectory()); }
    catch (error) { if (error.code !== 'ENOENT') throw error; }
    if (ancestor === path.dirname(ancestor)) break;
  }
  assert.equal(plan.kind, 'complete-two-target-native-context-part-continuation');
  assert.equal(plan.original_commit, ORIGINAL); assert.equal(process.version, 'v24.19.0');
  assert.equal(process.execArgv.length, 0); assert(!process.env.NODE_OPTIONS && !process.env.NODE_PATH);
  assert.equal(plan.runtime.path, process.execPath);
  const pin = plan.part;
  assert.equal(pin.path, 'context/part-6000.json.gz'); assert.equal(pin.first_owner, 6001); assert.equal(pin.owners, 1500);
  assert(/^[a-f0-9]{40}$/.test(pin.oid));
  assert(Number.isSafeInteger(pin.bytes) && pin.bytes <= MAX);
  assert(Number.isSafeInteger(pin.decoded_bytes) && pin.decoded_bytes <= MAX);
  const admission = admitPhase({inputs: plan.inputs, runtime: plan.runtime,
    reservedInputBytes: pin.bytes + pin.decoded_bytes, outputReserve: plan.output_reserve,
    metadataBytes: plan.metadata_bytes});
  assert(admission.descriptors + 1 <= 512);
  for (const snapshot of admission.snapshots) authenticateAdmittedBody(admission, snapshot.pin.path);
  const callables = [produceContextPart, continueContextPart, admitPhase, authenticateAdmittedBody,
    readAdmittedBody, execFileSync, gunzipSync, gzipSync];
  const fingerprints = callables.map(fn => fn.toString());
  const git = args => execFileSync(plan.git.path, ['-C', root, ...args], {maxBuffer: MAX + 1, env: process.env});
  assert.equal(git(['rev-parse', 'HEAD']).toString().trim(), plan.source_head);
  assert.equal(path.resolve(git(['rev-parse', '--show-toplevel']).toString().trim()), root);
  for (const source of plan.code) assert.equal(git(['ls-tree', '-z', plan.source_head, '--', source.relative]).toString(),
    `100644 blob ${source.oid}\t${source.relative}\0`);
  const index = JSON.parse(readAdmittedBody(admission, plan.index.path));
  assert.equal(index.parts.length, 34);
  assert.deepEqual(index.parts[4], (({oid, ...rest}) => rest)(pin));
  const footprintRaw = readAdmittedBody(admission, plan.footprints.path), footprints = JSON.parse(footprintRaw);
  assert.equal(footprints.original_footprints_sha256, 'b9a3c8bf375217dba3a50d1a022ec7e4ac6c6f1cdedff22845da953c805b7433');
  assert.equal(footprints.current_footprints_sha256, '2deeff1457ff9238cb3dbe599e9a858dcce29d8ba88e2a66abe2785ddec0aed9');
  assert.equal(footprints.owners, 49625); assert.equal(footprints.unchanged_owners, 49623);
  const changed = JSON.parse(readAdmittedBody(admission, plan.changed.path));
  const relative = BASE + pin.path;
  assert.equal(git(['ls-tree', '-z', ORIGINAL, '--', relative]).toString(), `100644 blob ${pin.oid}\t${relative}\0`);
  const encoded = git(['cat-file', 'blob', pin.oid]); assert.equal(encoded.length, pin.bytes); assert.equal(sha(encoded), pin.sha256);
  const decoded = gunzipSync(encoded, {maxOutputLength: pin.decoded_bytes});
  assert.equal(decoded.length, pin.decoded_bytes); assert.equal(sha(decoded), pin.decoded_sha256);
  const before = JSON.parse(decoded), continuation = continueContextPart(before, changed, pin);
  const currentDecoded = Buffer.from(JSON.stringify(continuation.after) + '\n');
  assert(currentDecoded.length <= MAX);
  const currentEncoded = gzipSync(currentDecoded, {level: 9, mtime: 0});
  assert(currentEncoded.length + currentDecoded.length + 131072 <= plan.output_reserve);
  const current = {...index.parts[4], bytes: currentEncoded.length, sha256: sha(currentEncoded),
    decoded_bytes: currentDecoded.length, decoded_sha256: sha(currentDecoded)};
  const currentIndex = {...index, parts: index.parts.map((part, ordinal) => ordinal === 4 ? current : part)};
  assert.deepEqual(currentIndex.parts.filter((_, ordinal) => ordinal !== 4), index.parts.filter((_, ordinal) => ordinal !== 4));
  const report = {version: 1, kind: plan.kind, source_head: plan.source_head, original_commit: ORIGINAL,
    original_part: pin, current_part: current, complete_owner_order_preserved: true, original_owners: 1500,
    unchanged_full_rows: 1498, changed_ids: continuation.changed_ids, footprints_sha256: footprints.current_footprints_sha256,
    complete_phase_bytes: admission.bytes, descriptors: admission.descriptors + 1, activation: false};
  assert.deepEqual(callables.map(fn => fn.toString()), fingerprints);
  for (const snapshot of admission.snapshots) authenticateAdmittedBody(admission, snapshot.pin.path);
  fs.mkdirSync(output, {recursive: true});
  for (const [name, body] of [['part-6000.json.gz', currentEncoded], ['context-index.json', Buffer.from(JSON.stringify(currentIndex) + '\n')],
    ['context-proof.json', Buffer.from(JSON.stringify(report, null, 2) + '\n')]]) {
    assert(body.length <= MAX); fs.writeFileSync(path.join(output, name), body, {flag: 'wx'});
  }
  return report;
}
