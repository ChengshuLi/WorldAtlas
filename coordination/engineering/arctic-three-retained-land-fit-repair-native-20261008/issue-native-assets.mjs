// Finished byte-copy stage. Ownership words are not decoded or recomputed.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {admitPhase, authenticateAdmittedBody, readAdmittedBody} from './phase-admission.mjs';

const sha = raw => createHash('sha256').update(raw).digest('hex');
export function issueNativeAssets(plan, destination) {
  assert.equal(plan.kind, 'complete-56-native-v9-compressed-asset-copy');
  assert(path.isAbsolute(destination) && !destination.split(path.sep).includes('..'));
  assert(destination.startsWith(plan.root + '/.cache/'));
  let exists = true;
  try { fs.lstatSync(destination); } catch (error) {
    if (error.code !== 'ENOENT') throw error;
    exists = false;
  }
  assert(!exists, 'Fresh ordinary destination required');
  for (let current = path.dirname(destination); ; current = path.dirname(current)) {
    assert(!fs.lstatSync(current).isSymbolicLink());
    if (current === path.dirname(current)) break;
  }
  assert.equal(plan.assets.length, 56);
  assert.equal(new Set(plan.assets.map(pin => pin.logical)).size, 56);
  for (const pin of plan.assets) {
    assert(/^native-v1\/ownership\/(runs-\d+|rows-0)\.bin\.gz$/.test(pin.logical));
    assert.equal(pin.mode, 0o644);
    assert.equal(pin.decoded_bytes ?? 0, 0, 'This phase consumes compressed bodies only');
  }
  const outputBytes = plan.assets.reduce((sum, pin) => sum + pin.bytes, 0);
  assert.equal(outputBytes, 47604645);
  const inputs = [...plan.assets, plan.originalCustody, plan.repackCustody, ...plan.code];
  const admission = admitPhase({inputs, runtime: plan.runtime,
    outputReserve: outputBytes + 1048576, metadataBytes: 1048576});
  for (const pin of [...inputs, plan.runtime]) authenticateAdmittedBody(admission, pin.path);
  const original = JSON.parse(readAdmittedBody(admission, plan.originalCustody.path));
  assert.equal(original.kind, 'complete-54-native-original-whole-body-alias-custody');
  assert.equal(original.all_actual_git_and_retained_bodies_equal, true);
  assert.equal(original.rows.length, 54);
  for (const row of original.rows) {
    const pin = plan.assets.find(pin => pin.logical === row.logical_current_v9_path);
    assert(pin);
    assert.equal(pin.path, row.retained_source);
    assert.equal(pin.bytes, row.bytes);
    assert.equal(pin.sha256, row.sha256);
  }
  const replacements = plan.assets.filter(pin => !original.rows.some(row => row.logical_current_v9_path === pin.logical));
  const repack = JSON.parse(readAdmittedBody(admission, plan.repackCustody.path));
  assert.equal(repack.qualified_processes, 4);
  assert.equal(repack.full_rows, 262166);
  assert.equal(repack.global_run_words_unchanged, 57617774);
  assert.deepEqual(replacements.map(pin => pin.sha256).sort(), [
    'fceeec44661182bb9344083dd8aefee195d521b982619602f55a4c4e21f84ce7',
    '51a2e4a95b922856870e644fcf1c2ec6685fc36d49a1ad684708d6df8e42b47b'].sort());
  const receipt = {issue: 1520, kind: plan.kind, source_head: plan.head,
    complete_phase_bytes: admission.bytes, descriptors: admission.descriptors,
    compressed_files: 56, compressed_bytes: outputBytes, unchanged_original_files: 54,
    changed_files: 2, source_custody_sha256: plan.originalCustody.sha256,
    repack_custody_sha256: plan.repackCustody.sha256, decoded_native_payload_consumed: false,
    activated: false, files: plan.assets.map(({logical, bytes, sha256, mode}) => ({path: logical, bytes, sha256, mode})),
    limit: 'Complete compressed asset custody only; transport inverse, selected manifest and normal caller remain pending.'};
  const receiptBytes = Buffer.from(JSON.stringify(receipt) + '\n');
  assert(outputBytes + receiptBytes.length <= admission.outputReserve);
  fs.mkdirSync(destination);
  for (const pin of plan.assets) {
    const raw = readAdmittedBody(admission, pin.path);
    const file = path.join(destination, 'assets', pin.logical);
    fs.mkdirSync(path.dirname(file), {recursive: true});
    fs.writeFileSync(file, raw, {flag: 'wx', mode: 0o644});
    assert.equal(sha(fs.readFileSync(file)), pin.sha256);
  }
  for (const pin of [...inputs, plan.runtime]) authenticateAdmittedBody(admission, pin.path);
  fs.writeFileSync(path.join(destination, 'asset-copy-receipt.json'), receiptBytes, {flag: 'wx', mode: 0o644});
  return receipt;
}
