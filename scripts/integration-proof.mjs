import {githubPages} from './issue-claim-contract.mjs';

// Classification selects jobs; proof below verifies the completed inventory itself.
// Its source identity adds no coverage guarantee to an unchanged tested tree.
export const PROOF_PATHS = ['.github/workflows/merge-integration-checks.yml',
  'scripts/run-integration-tests.mjs', 'scripts/check-integration-profile.mjs',
  'scripts/check-pr-gates.mjs'];
export const WORKFLOW_PATH = PROOF_PATHS[0];
export const QUEUE_WORKFLOW_PATH = '.github/workflows/worker-merge.yml';
const prefix = repo => `/repos/${repo}`;

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

const complete = value => value?.status === 'completed' && value.conclusion === 'success';
const positive = value => Number.isSafeInteger(value) && value > 0;

export function successfulMetadataRegressionJobs(jobs, {run, attempt, head}) {
  if (!Array.isArray(jobs)) return null;
  const regression = jobs.filter(job => /^regression(?: \(\d+\))?$/.test(job.name));
  if (regression.length !== 1 || regression[0].name !== 'regression (0)') return null;
  const required = new Map([
    ['profile', ['Validate ownership and focused CI applicability', 'Authenticate predecessor regression inputs']],
    ['regression (0)', ['Install Node dependencies', 'Run current-head regression consumers']],
    ['package', ['Use authenticated predecessor package verification']]
  ]);
  for (const [name, steps] of required) {
    const matches = jobs.filter(job => job.name === name), job = matches[0];
    if (matches.length !== 1 || !positive(job.id) || !complete(job) || job.run_id !== run || job.run_attempt !== attempt || job.head_sha !== head) return null;
    if (!steps.every(name => {const rows = job.steps?.filter(step => step.name === name) ?? [];return rows.length === 1 && complete(rows[0]);})) return null;
  }
  const checkout = regression[0].steps?.filter(step => step.name === 'Checkout reviewed head') ?? [];
  if (checkout.length !== 2 || checkout.filter(complete).length !== 1 ||
    checkout.filter(step => step.status === 'completed' && step.conclusion === 'skipped').length !== 1) return null;
  for (const name of ['Complete regression shard', 'Build hosted assets']) {
    const rows = regression[0].steps?.filter(step => step.name === name) ?? [];
    if (rows.length !== 1 || rows[0].status !== 'completed' || rows[0].conclusion !== 'skipped') return null;
  }
  return {job_id: regression[0].id};
}

// The approved workflow explicitly checks out the reviewed head. Matching its
// immutable blobs to main and the entire tested tree to the candidate connects
// GitHub's run metadata to the bytes actually executed, rather than treating a
// PR merge-ref run's head_sha as evidence that it tested the authored head.
export async function integrationProof({api, repo, number, head, profile, testSelection = 'complete', baseline, authored, candidate, runId, runAttempt, metadataProofLoader, onUnavailable = () => {}}) {
  const unavailable = reason => {onUnavailable({reason});return null;};
  let reason = 'no-completed-code-run';
  // Ordinary data has no author computation to transfer. Always test its final candidate.
  if (testSelection === 'selected-data' && profile === 'full') return unavailable('selected-data-requires-final-candidate');
  if (testSelection !== 'complete') return unavailable('invalid-test-selection');
  if (runId !== undefined && (!Number.isSafeInteger(runId) || runId < 1 ||
      !Number.isSafeInteger(runAttempt) || runAttempt < 1)) return unavailable('invalid-run-pin');
  if (runAttempt !== undefined && runId === undefined) return unavailable('invalid-run-pin');
  if (authored.object.tree.sha !== candidate.object.tree.sha) return unavailable('tested-tree-mismatch');
  for (const path of PROOF_PATHS) {
    const approved = baseline.entries.get(path), tested = authored.entries.get(path);
    if (!approved || approved.type !== 'blob' || approved.mode !== '100644' ||
        approved.sha !== tested?.sha || approved.mode !== tested?.mode) return unavailable('trusted-checker-identity-changed');
  }
  const workflow = await api(`${prefix(repo)}/git/blobs/${baseline.entries.get(WORKFLOW_PATH).sha}`);
  const text = Buffer.from(workflow.content, 'base64').toString('utf8');
  if (!text.includes('ref: ${{ github.event.pull_request.head.sha }}') ||
      !text.includes('name: Complete regression shard') || !text.includes('name: Build hosted assets')) return unavailable('workflow-contract-unavailable');
  const runs = runId ? [await api(`${prefix(repo)}/actions/runs/${runId}`)] :
    (await api(`${prefix(repo)}/actions/workflows/merge-integration-checks.yml/runs?head_sha=${head}&event=pull_request&per_page=100`)).workflow_runs;
  if (!Array.isArray(runs)) return unavailable('run-inventory-unavailable');
  for (const run of runs) {
    reason = 'run-identity-or-state';
    if (!Number.isSafeInteger(run.id) || run.id < 1 || !Number.isSafeInteger(run.run_attempt) || run.run_attempt < 1 ||
        (runId !== undefined && (run.id !== runId || run.run_attempt !== runAttempt)) || run.head_sha !== head || run.event !== 'pull_request' || run.path !== WORKFLOW_PATH ||
        run.repository?.full_name !== repo || run.head_repository?.full_name !== repo ||
        run.status !== 'completed' || !['success', 'failure'].includes(run.conclusion) ||
        !run.pull_requests?.some(pr => pr.number === number && pr.head?.sha === head)) continue;
    const jobs = await githubPages(async route => (await api(route)).jobs, `${prefix(repo)}/actions/runs/${run.id}/attempts/${run.run_attempt}/jobs`);
    const currentMetadata = profile === 'full' &&
      successfulMetadataRegressionJobs(jobs, {run: run.id, attempt: run.run_attempt, head});
    if (currentMetadata) {
      reason = 'metadata-predecessor-proof-unavailable';
      // Only the narrow existing current evidence failure can be disregarded.
      // Scope and all computational/current-control jobs remain successful.
      if (run.conclusion === 'failure' && (jobs.filter(job => job.name === 'evidence').length !== 1 ||
        !jobs.some(job => job.name === 'evidence' && job.conclusion === 'failure') ||
        jobs.some(job => job.status !== 'completed' || job.conclusion !== (job.name === 'evidence' ? 'failure' : 'success')))) continue;
      if (typeof metadataProofLoader !== 'function') continue;
      let admitted;
      try { admitted = await metadataProofLoader({api, repo, number, head, baseline: baseline.object.sha}); }
      catch (error) { if (error?.requestBudget || error?.planningNeeded) throw error; continue; }
      if (admitted?.status !== 'reused-original' || admitted.reviewed_head !== head ||
        admitted.trusted_baseline !== baseline.object.sha || admitted.candidate_tree !== authored.object.tree.sha ||
        !admitted.original_computation || !admitted.program) continue;
      return {run_id: run.id, run_attempt: run.run_attempt, tree: authored.object.tree.sha, profile,
        metadata_regression: {current_controls_job_id: currentMetadata.job_id, program: admitted.program,
          original_computation: admitted.original_computation}};
    }
    reason = 'failure-outside-evidence';
    // A PR-body edit can invalidate this run's evidence job after all code
    // checks finish. Current authority is checked independently by both merge
    // phases. Reuse only that narrow failure; other failed/skipped jobs do not
    // become coverage. Geography is either checked fresh or revalidated from
    // the authenticated original report on this exact tested tree.
    if (run.conclusion === 'failure' && (
      jobs.filter(job => job.name === 'evidence').length !== 1 ||
      !jobs.some(job => job.name === 'evidence' && job.conclusion === 'failure') ||
      !['scope', 'geography', 'package'].every(name => jobs.some(job => job.name === name)) ||
      jobs.some(job => job.status !== 'completed' ||
        job.conclusion !== (job.name === 'evidence' ? 'failure' : 'success')))) continue;
    reason = 'required-code-job-or-step';
    const expected = profile === 'full' ? [0,1,2] : [0];
    if (profile === 'full') {
      const packages = jobs.filter(job => job.name === 'package');
      const steps = packages[0]?.steps?.filter(step => step.name === 'Use full-regression package verification') ?? [];
      if (packages.length !== 1 || packages[0].status !== 'completed' || packages[0].conclusion !== 'success' ||
          steps.length !== 1 || steps[0].status !== 'completed' || steps[0].conclusion !== 'success') continue;
    }
    const regression = jobs.filter(job => /^regression \(\d\)$/.test(job.name));
    if (regression.length !== expected.length) continue;
    if (!expected.every(shard => {
      const job = regression.find(job => job.name === `regression (${shard})`);
      const required = ['Checkout reviewed head', 'Install browser dependencies only for tests that use Playwright', 'Complete regression shard',
        ...(profile === 'full' ? ['Install Node dependencies', 'Install Python dependencies', ...(shard === 0 ? ['Build hosted assets'] : [])] : [])];
      const producerSteps = profile === 'full' && shard === 0 ? ['Verify full-regression package controls',
        'Read back qualified native build outputs when selected', 'Verify full-regression package receipt', 'Retain full-regression package receipt'] : [];
      return producerSteps.every(name => {
        const steps = job?.steps?.filter(step => step.name === name) ?? [];
        return steps.length === 1 && steps[0].status === 'completed' && steps[0].conclusion === 'success';
      }) && job?.status === 'completed' && job.conclusion === 'success' &&
        required.every(name => job.steps?.some(step => step.name === name && step.status === 'completed' && step.conclusion === 'success'));
    })) continue;
    reason = 'profile-job-unavailable';
    const selector = jobs.find(job => job.name === 'profile');
    if (selector?.conclusion !== 'success' || selector.status !== 'completed') continue;
    const geography = successfulGeographyJob(jobs);
    return {run_id: run.id, run_attempt: run.run_attempt, tree: authored.object.tree.sha, profile,
      ...(geography ? {geography_job_id: geography.id} : {})};
  }
  return unavailable(reason);
}
