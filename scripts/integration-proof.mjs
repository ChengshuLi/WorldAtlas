// Original geographic artifact readers still authenticate historical PR and
// current queue producers. Ordinary regression is only run on the final queue.
export const WORKFLOW_PATH = '.github/workflows/merge-integration-checks.yml';
export const QUEUE_WORKFLOW_PATH = '.github/workflows/worker-merge.yml';

export function successfulGeographyJob(jobs, workflow = WORKFLOW_PATH) {
  if (![WORKFLOW_PATH, QUEUE_WORKFLOW_PATH].includes(workflow)) return null;
  const matches = jobs.filter(job => job.name === 'geography');
  if (matches.length !== 1) return null;
  const job = matches[0];
  // Step projections can remain pending or disappear after job completion.
  // Callers authenticate this successful producer's run and immutable receipt.
  if (!Number.isSafeInteger(job.id) || job.id < 1 || job.status !== 'completed' || job.conclusion !== 'success') return null;
  return job;
}
