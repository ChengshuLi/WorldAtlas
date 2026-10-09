// One finished whole-byte transport join; no ownership calculation.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {admitPhase, authenticateAdmittedBody, readAdmittedBody} from './phase-admission.mjs';
const sha = raw => createHash('sha256').update(raw).digest('hex');
export function joinNativeAssetIndexes(plan, destination) {
  assert.equal(plan.kind, 'finished-two-group-native-v9-index-join');
  assert(path.isAbsolute(destination) && !destination.split(path.sep).includes('..'));
  assert(destination.startsWith(plan.root + '/.cache/'));
  for (const output of [destination, destination + '.receipt.json']) {
  let exists = true;
  try { fs.lstatSync(output); } catch (error) {
    if (error.code !== 'ENOENT') throw error;
    exists = false;
  }
  assert(!exists);
  }
  for (let current = path.dirname(destination); ; current = path.dirname(current)) {
    assert(!fs.lstatSync(current).isSymbolicLink());
    if (current === path.dirname(current)) break;
  }
  assert.equal(plan.groups.length, 2);
  assert.equal(plan.original_compressed_bytes, 47604645);
  for(const group of plan.groups) { assert.equal(group.parts.length, 2); for(const part of group.parts) assert(part.decoded_bytes > 0 && part.decoded_bytes <= 16 * 1024 * 1024); }
  const inputs = [plan.copyReceipt, ...plan.code,
    ...plan.groups.flatMap(group => [group.index, group.report, group.terminal, ...group.parts])];
  const admission = admitPhase({inputs, runtime: plan.runtime,
    outputReserve: 1048576, metadataBytes: 1048576});
  for (const pin of [...inputs, plan.runtime]) authenticateAdmittedBody(admission, pin.path);
  const copied = JSON.parse(readAdmittedBody(admission, plan.copyReceipt.path));
  assert.equal(copied.kind, 'complete-56-native-v9-compressed-asset-copy');
  assert.equal(copied.compressed_files, 56);
  assert.equal(copied.compressed_bytes, 47604645);
  const expected = [...copied.files].sort((a, b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0);
  assert.equal(new Set(expected.map(pin => pin.path)).size, 56);
  const index = {version: 1, issue: 1295, kind: 'ordered-exact-original-byte-fragments', files: [], parts: []};
  const whole = createHash('sha256');
  let base = 0;
  for (let ordinal = 0; ordinal < 2; ordinal++) {
    const group = plan.groups[ordinal];
    const source = JSON.parse(readAdmittedBody(admission, group.index.path));
    const report = JSON.parse(readAdmittedBody(admission, group.report.path));
    const terminal = JSON.parse(readAdmittedBody(admission, group.terminal.path));
    assert.equal(report.group, ordinal);
    assert.equal(report.source_head, plan.group_head);
    assert.equal(report.index_sha256, group.index.sha256);
    assert.equal(report.whole_bytes, source.whole_bytes);
    assert.equal(report.whole_sha256, source.whole_sha256);
    assert.equal(report.files, 28);
    assert.equal(terminal.head, plan.group_head);
    assert.equal(terminal.qualified, true);
    assert.equal(terminal.exit_code, 0);
    assert.equal(terminal.guard_reason, null);
    assert.deepEqual(terminal.owned_group_survivors, []);
    assert(terminal.time_l_lifetime_max_rss_bytes <= 512 * 1024 * 1024);
    assert.equal(source.version, 1);
    assert.equal(source.issue, 1295);
    assert.equal(source.kind, 'ordered-exact-original-byte-fragments');
    assert.equal(source.files.length, 28);
    assert.equal(source.parts.length, group.parts.length);
    const chunks = [], groupHash = createHash('sha256');
    let offset = 0;
    for (let partOrdinal = 0; partOrdinal < source.parts.length; partOrdinal++) {
      const pin = source.parts[partOrdinal], body = group.parts[partOrdinal];
      assert.equal(pin.offset, offset);
      assert(/^part-\d{3}\.bin\.gz$/.test(pin.path));
      for (const key of ['bytes', 'sha256', 'decoded_bytes', 'decoded_sha256']) assert.equal(pin[key], body[key]);
      const wire = readAdmittedBody(admission, body.path);
      const raw = gunzipSync(wire, {maxOutputLength: 16 * 1024 * 1024});
      assert.equal(raw.length, pin.decoded_bytes);
      assert.equal(sha(raw), pin.decoded_sha256);
      groupHash.update(raw);
      whole.update(raw);
      chunks.push(raw);
      index.parts.push({...pin, path: `run-1/chunk-${String(ordinal).padStart(2, '0')}/${pin.path}`, offset: base + offset});
      offset += raw.length;
    }
    assert.equal(offset, source.whole_bytes);
    assert.equal(groupHash.digest('hex'), source.whole_sha256);
    const bytes = Buffer.concat(chunks);
    offset = 0;
    for (let fileOrdinal = 0; fileOrdinal < 28; fileOrdinal++) {
      const pin = source.files[fileOrdinal], original = expected[ordinal * 28 + fileOrdinal];
      assert.equal(pin.offset, offset);
      assert.equal(pin.path, original.path);
      assert.equal(pin.bytes, original.bytes);
      assert.equal(pin.sha256, original.sha256);
      assert.equal(pin.mode, '100644');
      assert.equal(sha(bytes.subarray(offset, offset + pin.bytes)), pin.sha256);
      index.files.push({...pin, offset: base + offset});
      offset += pin.bytes;
    }
    assert.equal(offset, bytes.length);
    base += bytes.length;
  }
  assert.equal(base, 47604645);
  assert.equal(index.files.length, 56);
  index.whole_bytes = base;
  index.whole_sha256 = whole.digest('hex');
  const raw = Buffer.from(JSON.stringify(index) + '\n');
  const receipt = Buffer.from(JSON.stringify({issue: 1520, source_head: plan.head,
    kind: plan.kind, complete_phase_bytes: admission.bytes, descriptors: admission.descriptors,
    index_sha256: sha(raw), files: 56, whole_bytes: base, whole_sha256: index.whole_sha256,
    all_original_compressed_file_inverses: true, scientific_reexecution: false, activated: false}) + '\n');
  assert(raw.length + receipt.length <= admission.outputReserve);
  for (const pin of [...inputs, plan.runtime]) authenticateAdmittedBody(admission, pin.path);
  fs.writeFileSync(destination, raw, {flag: 'wx', mode: 0o644});
  fs.writeFileSync(destination + '.receipt.json', receipt, {flag: 'wx', mode: 0o644});
  return JSON.parse(receipt);
}
