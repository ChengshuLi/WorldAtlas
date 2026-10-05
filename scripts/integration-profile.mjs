// Only these coordination controls have an audited focused test inventory.
// Unknown docs/scripts/workflows retain full regression, including rename origins.
export const COORDINATION_PATHS = new Set([
  'docs/WORKER_COORDINATION.md', 'docs/PREMERGE_EVIDENCE_REVIEW.md',
  'scripts/issue-claim-contract.mjs', 'scripts/issue-lease.mjs', 'scripts/run-issue-claim.mjs',
  'scripts/worker-result.mjs', 'scripts/check-handoff-scope.mjs', 'scripts/check-linked-github-issue.mjs',
  'scripts/evidence-quality.mjs', 'scripts/evidence-policy.mjs', 'scripts/premerge-evidence.mjs',
  'scripts/check-pr-evidence.mjs', 'scripts/merge-integration.mjs', 'scripts/integration-proof.mjs',
  'scripts/integration-profile.mjs', 'scripts/check-integration-profile.mjs',
  'scripts/classify-deployment-budget.mjs', 'scripts/package-research-inputs.mjs',
  '.github/workflows/deployment-budget.yml', 'test/deployment-budget-scope.test.mjs',
  // Test-runner changes require full regression to validate the real inventory.
  'scripts/run-worker-merge.mjs', 'scripts/queue-pr-merge.mjs',
  '.github/workflows/handoff-scope.yml',
  '.github/workflows/merge-integration-checks.yml', '.github/workflows/worker-merge.yml',
  '.github/evidence-policy.json',
  ...['handoff-scope','issue-claims','worker-result','regional-research-gate','geography-worker-lane',
    'evidence-quality','premerge-evidence','trusted-workflow-checkouts','merge-integration',
    'merge-integration-client','merge-integration-entrypoint','integration-proof'].map(name=>`test/${name}.test.mjs`)
]);
export function integrationProfile(branch, files, reservation = {}) {
  const names = files.flatMap(file => [file.filename, ...(file.previous_filename ? [file.previous_filename] : [])]);
  if (!names.length) return 'full';
  if (branch.startsWith('geography/') && Array.isArray(reservation.owned_paths) &&
      names.every(name => reservation.owned_paths.some(prefix => name.startsWith(prefix)))) return 'evidence';
  const job = branch.split('/').slice(1).join('/');
  if (branch.startsWith('research/') && names.every(name => name.startsWith(`research/campaigns/${job}/`))) return 'evidence';
  if (branch.startsWith('engineering/') && names.every(name => COORDINATION_PATHS.has(name) || (name.startsWith('docs/') && /\.(md|txt)$/.test(name)) ||
      name.startsWith(`coordination/engineering/${job}/`) || name === `coordination/engineering/${job}.json`)) return 'evidence';
  return 'full';
}
