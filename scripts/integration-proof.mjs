import {githubPages} from './issue-claim-contract.mjs';

export const PROOF_PATHS = ['.github/workflows/merge-integration-checks.yml',
  'scripts/run-integration-tests.mjs', 'scripts/integration-profile.mjs', 'scripts/check-integration-profile.mjs'];
export const WORKFLOW_PATH = PROOF_PATHS[0];
const prefix = repo => `/repos/${repo}`;

// The approved workflow explicitly checks out the reviewed head. Matching its
// immutable blobs to main and the entire tested tree to the candidate connects
// GitHub's run metadata to the bytes actually executed, rather than treating a
// PR merge-ref run's head_sha as evidence that it tested the authored head.
export async function integrationProof({api, repo, number, head, profile, baseline, authored, candidate, runId, runAttempt}) {
  if (runId !== undefined && (!Number.isSafeInteger(runId) || runId < 1 ||
      !Number.isSafeInteger(runAttempt) || runAttempt < 1)) return null;
  if (runAttempt !== undefined && runId === undefined) return null;
  if (authored.object.tree.sha !== candidate.object.tree.sha) return null;
  for (const path of PROOF_PATHS) {
    const approved = baseline.entries.get(path), tested = authored.entries.get(path);
    if (!approved || approved.type !== 'blob' || approved.mode !== '100644' ||
        approved.sha !== tested?.sha || approved.mode !== tested?.mode) return null;
  }
  const workflow = await api(`${prefix(repo)}/git/blobs/${baseline.entries.get(WORKFLOW_PATH).sha}`);
  const text = Buffer.from(workflow.content, 'base64').toString('utf8');
  if (!text.includes('ref: ${{ github.event.pull_request.head.sha }}') ||
      !text.includes('name: Complete regression shard') || !text.includes('name: Build hosted assets')) return null;
  const runs = runId ? [await api(`${prefix(repo)}/actions/runs/${runId}`)] :
    (await api(`${prefix(repo)}/actions/workflows/merge-integration-checks.yml/runs?head_sha=${head}&event=pull_request&per_page=100`)).workflow_runs;
  if (!Array.isArray(runs)) return null;
  for (const run of runs) {
    if (!Number.isSafeInteger(run.id) || run.id < 1 || !Number.isSafeInteger(run.run_attempt) || run.run_attempt < 1 ||
        (runId !== undefined && (run.id !== runId || run.run_attempt !== runAttempt)) || run.head_sha !== head || run.event !== 'pull_request' || run.path !== WORKFLOW_PATH ||
        run.repository?.full_name !== repo || run.head_repository?.full_name !== repo ||
        run.status !== 'completed' || run.conclusion !== 'success' ||
        !run.pull_requests?.some(pr => pr.number === number && pr.head?.sha === head)) continue;
    const jobs = await githubPages(async route => (await api(route)).jobs, `${prefix(repo)}/actions/runs/${run.id}/attempts/${run.run_attempt}/jobs`);
    const expected = profile === 'full' ? [0,1,2] : [0];
    const regression = jobs.filter(job => /^regression \(\d\)$/.test(job.name));
    if (regression.length !== expected.length) continue;
    if (!expected.every(shard => {
      const job = regression.find(job => job.name === `regression (${shard})`);
      const required = ['Checkout reviewed head', 'Install Node dependencies', 'Install browser dependencies only for tests that use Playwright', 'Complete regression shard',
        ...(profile === 'full' ? ['Install Python dependencies', ...(shard === 0 ? ['Build hosted assets'] : [])] : [])];
      return job?.status === 'completed' && job.conclusion === 'success' &&
        required.every(name => job.steps?.some(step => step.name === name && step.status === 'completed' && step.conclusion === 'success'));
    })) continue;
    const selector = jobs.find(job => job.name === 'profile');
    if (selector?.conclusion !== 'success' || selector.status !== 'completed') continue;
    return {run_id: run.id, run_attempt: run.run_attempt, tree: authored.object.tree.sha, profile};
  }
  return null;
}
