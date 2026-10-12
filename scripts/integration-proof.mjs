import {githubPages} from './issue-claim-contract.mjs';

export const PROOF_PATHS = ['.github/workflows/merge-integration-checks.yml',
  'scripts/run-integration-tests.mjs', 'scripts/integration-profile.mjs', 'scripts/check-integration-profile.mjs',
  'scripts/check-pr-gates.mjs'];
export const WORKFLOW_PATH = PROOF_PATHS[0];
export const QUEUE_WORKFLOW_PATH = '.github/workflows/worker-merge.yml';
const prefix = repo => `/repos/${repo}`;

export function successfulGeographyJob(jobs, workflow = WORKFLOW_PATH) {
  if (![WORKFLOW_PATH, QUEUE_WORKFLOW_PATH].includes(workflow)) return null;
  const matches = jobs.filter(job => job.name === 'geography');
  if (matches.length !== 1) return null;
  const job = matches[0];
  const required = ['Checkout trusted geographic checker', 'Install trusted geographic dependencies',
    workflow === WORKFLOW_PATH ? 'Check proposed geography with trusted baseline code' :
      'Check exact combined geography with trusted baseline code',
    'Run actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02'];
  if (!Number.isSafeInteger(job.id) || job.id < 1 || job.status !== 'completed' || job.conclusion !== 'success' ||
      !required.every(name => {
        const steps = job.steps?.filter(step => step.name === name) ?? [];
        return steps.length === 1 && steps[0].status === 'completed' && steps[0].conclusion === 'success';
      })) return null;
  return job;
}

// The approved workflow explicitly checks out the reviewed head. Matching its
// immutable blobs to main and the entire tested tree to the candidate connects
// GitHub's run metadata to the bytes actually executed, rather than treating a
// PR merge-ref run's head_sha as evidence that it tested the authored head.
export async function integrationProof({api, repo, number, head, profile, testSelection = 'complete', baseline, authored, candidate, runId, runAttempt, onUnavailable = () => {}}) {
  const unavailable = reason => {onUnavailable({reason});return null;};
  let reason = 'no-completed-code-run';
  if (!['complete','selected-data'].includes(testSelection) || (testSelection === 'selected-data' && profile !== 'full')) return unavailable('invalid-test-selection');
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
        job.conclusion !== (job.name === 'evidence' ? 'failure' :
          testSelection === 'selected-data' && /^regression(?: \(\d\))?$/.test(job.name) ? 'skipped' : 'success')))) continue;
    reason = 'required-code-job-or-step';
    const expected = testSelection === 'selected-data' ? [] : profile === 'full' ? [0,1,2] : [0];
    if (testSelection === 'selected-data') {
      const skipped = jobs.filter(job => /^regression(?: \(\d\))?$/.test(job.name));
      if (skipped.length !== 1 || skipped[0].status !== 'completed' || skipped[0].conclusion !== 'skipped') continue;
      const packages = jobs.filter(job => job.name === 'package');
      const required = ['Checkout complete package inputs', 'Install package Node dependencies', 'Install package Python dependencies',
        'Verify package controls', 'Build Cloudflare package without publishing',
        'Read back qualified native build outputs when selected', 'Install selected-data browser dependencies', 'Run selected-data consumer checks'];
      if (packages.length !== 1 || packages[0].status !== 'completed' || packages[0].conclusion !== 'success' ||
          !required.every(name => {
            const steps = packages[0].steps?.filter(step => step.name === name) ?? [];
            return steps.length === 1 && steps[0].status === 'completed' && steps[0].conclusion === 'success';
          })) continue;
    }
    if (profile === 'full' && testSelection === 'complete') {
      const packages = jobs.filter(job => job.name === 'package');
      const steps = packages[0]?.steps?.filter(step => step.name === 'Use full-regression package verification') ?? [];
      if (packages.length !== 1 || packages[0].status !== 'completed' || packages[0].conclusion !== 'success' ||
          steps.length !== 1 || steps[0].status !== 'completed' || steps[0].conclusion !== 'success') continue;
    }
    const regression = jobs.filter(job => /^regression \(\d\)$/.test(job.name) &&
      !(testSelection === 'selected-data' && job.conclusion === 'skipped'));
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
      ...(testSelection === 'selected-data' ? {test_selection: testSelection} : {}),
      ...(geography ? {geography_job_id: geography.id} : {})};
  }
  return unavailable(reason);
}
