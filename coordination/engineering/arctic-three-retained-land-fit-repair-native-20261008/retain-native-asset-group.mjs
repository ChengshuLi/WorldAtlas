// Two genuinely finished groups use the existing whole-image byte format.
// Only compressed ownership files are fragmented; no ownership words change.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gzipSync, gunzipSync} from 'node:zlib';
import {admitPhase, authenticateAdmittedBody, readAdmittedBody} from './phase-admission.mjs';
const sha = raw => createHash('sha256').update(raw).digest('hex');
const PART = 16 * 1024 * 1024;
export function retainNativeAssetGroup(plan, destination) {
  assert.equal(plan.kind, 'native-v9-complete-compressed-asset-group');
  assert([0, 1].includes(plan.group));
  assert(path.isAbsolute(destination) && !destination.split(path.sep).includes('..'));
  assert(destination.startsWith(plan.root + '/.cache/'));
  let exists = true;
  try { fs.lstatSync(destination); } catch (error) {
    if (error.code !== 'ENOENT') throw error;
    exists = false;
  }
  assert(!exists);
  for (let current = path.dirname(destination); ; current = path.dirname(current)) {
    assert(!fs.lstatSync(current).isSymbolicLink());
    if (current === path.dirname(current)) break;
  }
  assert.equal(plan.assets.length, 28);
  assert.equal(new Set(plan.assets.map(pin => pin.logical)).size, 28);
  assert.deepEqual(plan.assets.map(pin => pin.logical), plan.assets.map(pin => pin.logical).sort());
  for (const pin of plan.assets) {
    assert(/^native-v1\/ownership\/(runs-\d+|rows-0)\.bin\.gz$/.test(pin.logical));
    assert.equal(pin.mode, 0o644);
    assert.equal(pin.decoded_bytes ?? 0, 0, 'Native ownership payload is not decoded here');
  }
  const total = plan.assets.reduce((sum, pin) => sum + pin.bytes, 0);
  const admission = admitPhase({inputs: [...plan.assets, plan.copyReceipt, ...plan.code],
    runtime: plan.runtime, outputReserve: 2 * total + 262144, metadataBytes: 1048576});
  for (const pin of [...plan.assets, plan.copyReceipt, ...plan.code, plan.runtime]) authenticateAdmittedBody(admission, pin.path);
  const copied = JSON.parse(readAdmittedBody(admission, plan.copyReceipt.path));
  assert.equal(copied.kind, 'complete-56-native-v9-compressed-asset-copy');
  assert.equal(copied.compressed_files, 56);
  assert.equal(copied.compressed_bytes, 47604645);
  assert.equal(copied.files.length, 56);
  assert.equal(new Set(copied.files.map(pin => pin.path)).size, 56);
  assert.equal(copied.files.reduce((sum, pin) => sum + pin.bytes, 0), copied.compressed_bytes);
  const full = [...copied.files].sort((a, b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0);
  assert.deepEqual(plan.assets.map(({logical, bytes, sha256, mode}) => ({path: logical, bytes, sha256, mode})),
    full.slice(plan.group * 28, (plan.group + 1) * 28));
  let pending = Buffer.alloc(0), offset = 0, partOffset = 0;
  const whole = createHash('sha256');
  const index = {version: 1, issue: 1295, kind: 'ordered-exact-original-byte-fragments', files: [], parts: []};
  fs.mkdirSync(destination);
  function flush() {
    if (!pending.length) return;
    const name = `part-${String(index.parts.length).padStart(3, '0')}.bin.gz`;
    const raw = gzipSync(pending, {level: 9});
    assert(raw.length <= 32 * 1024 * 1024 && pending.length <= PART);
    assert.deepEqual(gunzipSync(raw, {maxOutputLength: PART}), pending);
    fs.writeFileSync(path.join(destination, name), raw, {flag: 'wx', mode: 0o644});
    index.parts.push({path: name, offset: partOffset, bytes: raw.length, sha256: sha(raw),
      decoded_bytes: pending.length, decoded_sha256: sha(pending)});
    partOffset += pending.length;
    pending = Buffer.alloc(0);
  }
  for (const pin of plan.assets) {
    assert.equal(pin.mode, 0o644);
    const raw = readAdmittedBody(admission, pin.path);
    whole.update(raw);
    index.files.push({path: pin.logical, offset, bytes: raw.length, sha256: sha(raw), mode: '100644',
      original_binding: {issue: 1520, copy_receipt_sha256: plan.copyReceipt.sha256, original_asset: pin.logical}});
    offset += raw.length;
    for (let first = 0; first < raw.length;) {
      const count = Math.min(PART - pending.length, raw.length - first);
      pending = Buffer.concat([pending, raw.subarray(first, first + count)]);
      first += count;
      if (pending.length === PART) flush();
    }
  }
  flush();
  assert.equal(offset, total);
  assert.equal(partOffset, total);
  index.whole_bytes = total;
  index.whole_sha256 = whole.digest('hex');
  const indexBytes = Buffer.from(JSON.stringify(index) + '\n');
  const report = Buffer.from(JSON.stringify({issue: 1520, group: plan.group, source_head: plan.head,
    complete_phase_bytes: admission.bytes, descriptors: admission.descriptors, files: 28,
    index_sha256: sha(indexBytes), encoded_bytes: index.parts.reduce((sum, pin) => sum + pin.bytes, 0),
    decoded_bytes: total, whole_bytes: total, whole_sha256: index.whole_sha256,
    whole_original_gzip_bytes_retained: true, scientific_reexecution: false, activated: false}) + '\n');
  assert(index.parts.reduce((sum, pin) => sum + pin.bytes + pin.decoded_bytes, 0) + indexBytes.length + report.length <= admission.outputReserve);
  for (const pin of [...plan.assets, plan.copyReceipt, ...plan.code, plan.runtime]) authenticateAdmittedBody(admission, pin.path);
  fs.writeFileSync(path.join(destination, 'index.json'), indexBytes, {flag: 'wx', mode: 0o644});
  fs.writeFileSync(path.join(destination, 'group-retention.json'), report, {flag: 'wx', mode: 0o644});
  return JSON.parse(report);
}
