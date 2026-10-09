// Bounded metadata issuance from the complete finished release products.
// The launcher authenticates this module and its imports before execution.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {execFileSync} from 'node:child_process';
import {admitPhase, authenticateAdmittedBody, readAdmittedBody} from './phase-admission.mjs';
import {continueReleaseRegistry, ORIGINAL_REGISTRY_SHA} from './release-registry-continuation.mjs';

const sha = bytes => createHash('sha256').update(bytes).digest('hex');
export function issueReleaseRegistry(plan, destination) {
  assert.equal(plan.kind, 'complete-qualified-release-registry-1520');
  assert(path.isAbsolute(destination) && !destination.split(path.sep).includes('..'));
  assert(destination.startsWith(plan.root + '/.cache/') && !fs.existsSync(destination));
  for (let current = path.dirname(destination); ; current = path.dirname(current)) {
    assert(!fs.lstatSync(current).isSymbolicLink());
    if (current === path.dirname(current)) break;
  }
  const inputs = [plan.git, plan.original, plan.baselineIndex, plan.header, plan.products, ...plan.code];
  const gitBodyBytes = [plan.original, plan.baselineIndex, ...plan.code].reduce((sum, pin) => sum + pin.bytes, 0);
  const admission = admitPhase({inputs, runtime: plan.runtime, outputReserve: 4194304,
    metadataBytes: 262144, reservedInputBytes: gitBodyBytes});
  for (const pin of [...inputs, plan.runtime]) authenticateAdmittedBody(admission, pin.path);
  const git = args => execFileSync(plan.git.path, args, {cwd: plan.root, maxBuffer: 32 * 1024 * 1024});
  assert.equal(git(['rev-parse', 'HEAD']).toString().trim(), plan.head);
  for (const pin of [plan.original, plan.baselineIndex, ...plan.code]) {
    const binding = pin.original_binding;
    assert(binding && /^[a-f0-9]{40}$/.test(binding.commit));
    assert.equal(git(['ls-tree', '-z', binding.commit, '--', binding.path]).toString(),
      `${binding.mode} blob ${binding.oid}\t${binding.path}\0`);
    assert.equal(sha(git(['cat-file', 'blob', binding.oid])), pin.sha256);
  }
  const raw = readAdmittedBody(admission, plan.original.path);
  assert.equal(sha(raw), ORIGINAL_REGISTRY_SHA);
  const decoded = gunzipSync(raw, {maxOutputLength: plan.original.decoded_bytes});
  assert.equal(decoded.length, plan.original.decoded_bytes);
  assert.equal(sha(decoded), plan.original.decoded_sha256);
  const baselineRaw = readAdmittedBody(admission, plan.baselineIndex.path);
  const header = JSON.parse(readAdmittedBody(admission, plan.header.path));
  const products = JSON.parse(readAdmittedBody(admission, plan.products.path));
  assert.equal(products.complete_343_whole_pairs_equal, true);
  assert.equal(products.complete_gzip_inverse_authenticated, true);
  assert.equal(products.qualified_comparison_processes, 7);
  const result = continueReleaseRegistry(JSON.parse(decoded), header, products.products,
    {originalSha: ORIGINAL_REGISTRY_SHA});
  // Authenticate the actual original index, not a synthetic v8 predecessor.
  const baseline = JSON.parse(baselineRaw);
  assert.equal(result.original_catalog_sha256, baseline.original_catalog_sha256);
  assert.deepEqual(result.releases.slice(0, baseline.releases.length), baseline.releases);
  assert.deepEqual(result.batches.slice(0, baseline.batches.length), baseline.batches);
  for (const pin of [...inputs, plan.runtime]) authenticateAdmittedBody(admission, pin.path);
  const output = Buffer.from(JSON.stringify(result) + '\n');
  assert(output.length <= 4194304);
  fs.mkdirSync(destination);
  fs.writeFileSync(path.join(destination, 'releases-v9.json'), output, {flag: 'wx', mode: 0o644});
  const receipt = {issue: 1520, source_head: plan.head, kind: plan.kind,
    complete_phase_bytes: admission.bytes, descriptors: admission.descriptors,
    immutable_git_body_output_bytes: gitBodyBytes,
    output_bytes: output.length, output_sha256: sha(output),
    original_registry_sha256: plan.original.sha256,
    predecessor_index_sha256: sha(baselineRaw),
    qualified_product_receipt_sha256: plan.products.sha256,
    release_id: header.release.id, releases: result.releases.length,
    complete_old_releases_retained: 8, complete_old_batch_descriptors_retained: 3042,
    new_products: 343, membership_records_retained: 84833,
    activated: false, scientific_reexecution: false,
    limit: 'Raw registry metadata only; encoded registry, current pointer and normal caller remain unqualified.'};
  fs.writeFileSync(path.join(destination, 'registry-issuance.json'), JSON.stringify(receipt) + '\n', {flag: 'wx', mode: 0o644});
  return receipt;
}
