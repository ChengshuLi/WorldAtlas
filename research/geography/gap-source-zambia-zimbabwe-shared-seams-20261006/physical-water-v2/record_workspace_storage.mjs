import {workspaceManager} from '../../../../scripts/local-workspace.mjs';
import {writeFileSync} from 'node:fs';
import {resolve} from 'node:path';

const repo = process.cwd();
const base = resolve(repo, 'research/geography/gap-source-zambia-zimbabwe-shared-seams-20261006/physical-water-v2');
const snapshot = workspaceManager(repo).check();
const current = snapshot.worktrees.find(entry => entry.path === repo);
if (!current) throw new Error('Current managed author checkout is absent from storage report');
const output = {
  version: 1,
  observed_at: new Date().toISOString(),
  free_bytes: snapshot.freeBytes,
  repository_checkout_bytes: snapshot.checkoutBytes,
  checkout_limit_bytes: snapshot.limits.maximumCheckouts,
  minimum_free_bytes: snapshot.limits.minimumFree,
  current_author_worktree_bytes: current.bytes,
  planned_two_run_result_cap_bytes: 134217728,
  planned_temporary_storage_cap_bytes: 67108864,
  projected_checkout_bytes_at_output_cap: snapshot.checkoutBytes + 134217728,
  projected_free_bytes_after_output_cap: snapshot.freeBytes - 134217728,
};
if (output.projected_checkout_bytes_at_output_cap > output.checkout_limit_bytes || output.projected_free_bytes_after_output_cap < output.minimum_free_bytes) {
  throw new Error('Two-run output cap violates shared checkout or free-space admission');
}
writeFileSync(resolve(base, 'workspace-storage-admission.json'), `${JSON.stringify(output, null, 2)}\n`, {flag: 'w'});
process.stdout.write(`${JSON.stringify(output, null, 2)}\n`);
