import {integrationProfile} from './integration-profile.mjs';
import {integrationProof} from './integration-proof.mjs';
import {githubPages, linkedPulls, verifyClaimForPR, workSpec} from './issue-claim-contract.mjs';
import {validateIssuePRBody, validateLanePaths} from './check-handoff-scope.mjs';
import {checkPremergeEvidence} from './premerge-evidence.mjs';
import {evidenceRequirement} from './evidence-policy.mjs';

const need = (condition, message) => { if (!condition) throw Error(message); };
const root = repo => `/repos/${repo}`;
export function checkCurrentChecks(checks, {evidenceRequired = false} = {}) {
  const latest = new Map();
  for (const check of checks) {
    const key = `${check.app?.id}:${check.name}`;
    if (!latest.has(key) || latest.get(key).id < check.id) latest.set(key, check);
  }
  for (const name of ['scope', ...(evidenceRequired ? ['evidence'] : [])]) {
    const check = [...latest.values()].filter(row => row.name === name).sort((a,b) => b.id-a.id)[0];
    need(check?.status === 'completed' && check.conclusion === 'success', `Current head must pass trusted ${name} check`);
  }
  need([...latest.values()].every(row => row.status === 'completed' && ['success','skipped','neutral'].includes(row.conclusion)),
    'Current checks are pending or failed; submit only ready PRs');
}

export function checkCandidateParents(commit, base, head) {
  need(commit.parents?.length === 2 && commit.parents[0].sha === base && commit.parents[1].sha === head,
    'Integration candidate is not the exact current main plus reviewed head; resubmit unchanged head');
}
export function checkReviewedTrees(files, authored, integrated) {
  for (const name of new Set(files.flatMap(file => [file.filename, ...(file.previous_filename ? [file.previous_filename] : [])]))) {
    const a = authored.get(name), b = integrated.get(name);
    need((!a && !b) || (a && b && a.sha === b.sha && a.mode === b.mode && a.type === b.type),
      `Integration changes reviewed bytes at ${name}; update and obtain substantive review`);
  }
}
export {integrationProfile} from './integration-profile.mjs';

async function tree(api, repo, commit) {
  const object = await api(`${root(repo)}/git/commits/${commit}`);
  const value = await api(`${root(repo)}/git/trees/${object.tree.sha}?recursive=1`);
  need(!value.truncated && Array.isArray(value.tree), 'Incomplete integration tree; cannot verify reviewed scope');
  return {object, entries: new Map(value.tree.map(row => [row.path, row]))};
}

// All remote authorities and evidence are re-read in both trusted phases. No
// candidate executable code is imported by this module or given a write token.
export async function inspectMerge({api, repo, number, expectedHead, policy, evidenceCheck = checkPremergeEvidence}) {
  const pr = await api(`${root(repo)}/pulls/${number}`);
  need(pr.head.sha === expectedHead, 'PR head changed; review the new head');
  if (pr.merged) return {replayed: true, pr};
  need(pr.state === 'open' && !pr.draft && pr.base.ref === 'main' && pr.head.repo?.full_name === repo,
    'Only open non-draft repository PRs targeting main may merge');
  const {github_issue} = validateIssuePRBody(pr.body ?? '');
  const issue = await api(`${root(repo)}/issues/${github_issue}`);
  const reservation = verifyClaimForPR({branch: pr.head.ref, issue,
    comments: await githubPages(api, `${root(repo)}/issues/${github_issue}/comments`),
    prs: await linkedPulls(api, repo, github_issue)});
  const files = await githubPages(api, `${root(repo)}/pulls/${number}/files`);
  need(files.length === pr.changed_files, 'Incomplete PR file inventory');
  validateLanePaths(pr.head.ref, files.flatMap(file => [file.filename, ...(file.previous_filename ? [file.previous_filename] : [])]),
    {ownedPaths: reservation.owned_paths});
  const requirement = evidenceRequirement(issue, workSpec(issue.body), policy, pr.head.ref);
  checkCurrentChecks(await githubPages(api, `${root(repo)}/commits/${expectedHead}/check-runs`),
    {evidenceRequired: policy.mode === 'enforce-new' && requirement.required});
  const statuses = await api(`${root(repo)}/commits/${expectedHead}/status`);
  need(!statuses.statuses?.length || statuses.state === 'success', 'Commit status is pending or failed');
  const evidence = await evidenceCheck({api, repo, pr, issue, reservation, files, policy, review: true});
  const base = (await api(`${root(repo)}/git/ref/heads/main`)).object.sha;
  return {pr, issue, reservation, files, evidence, base};
}
export async function prepareIntegration(options) {
  const state = await inspectMerge(options);
  if (state.replayed) return state;
  // GitHub builds the test merge without changing the worker's branch. A stale
  // or unavailable merge object is not interpreted as a successful integration.
  need(state.pr.mergeable !== false, 'Integration conflict; author intervention required');
  const candidate = state.pr.merge_commit_sha;
  need(/^[a-f0-9]{40}$/.test(candidate ?? ''), 'Integration candidate unavailable; resubmit unchanged head');
  const [authored, integrated] = await Promise.all([
    tree(options.api, options.repo, state.pr.head.sha), tree(options.api, options.repo, candidate)
  ]);
  checkCandidateParents(integrated.object, state.base, state.pr.head.sha);
  checkReviewedTrees(state.files, authored.entries, integrated.entries);
  const profile = integrationProfile(state.pr.head.ref, state.files, state.reservation);
  let proof = null;
  try { proof = await integrationProof({...options, head: state.pr.head.sha, profile,
    baseline: await tree(options.api, options.repo, state.base), authored, candidate: integrated}); } catch { /* unavailable proof requires isolated tests */ }
  return {...state, candidate, profile, proof};
}
export async function completeIntegration(options) {
  need(options.integrationResult === 'success' || options.integrationResult === 'skipped',
    'Integration tests failed or were cancelled; no merge performed');
  const state = await inspectMerge(options);
  if (state.replayed) return {accepted: true, replayed: true, merge_commit: state.pr.merge_commit_sha};
  need(options.integrationResult === 'success' || (options.integrationResult === 'skipped' && options.proofRunId),
    'An open PR requires successful isolated integration tests or revalidated trusted proof');
  need(state.base === options.testedBase, 'Main advanced after integration tests; resubmit unchanged head');
  const candidate = await tree(options.api, options.repo, options.testedCandidate);
  checkCandidateParents(candidate.object, state.base, state.pr.head.sha);
  const authored = await tree(options.api, options.repo, state.pr.head.sha);
  checkReviewedTrees(state.files, authored.entries, candidate.entries);
  let proof = null;
  if (options.proofRunId) {
    proof = await integrationProof({...options, runId: options.proofRunId, head: state.pr.head.sha,
      profile: integrationProfile(state.pr.head.ref, state.files, state.reservation),
      baseline: await tree(options.api, options.repo, state.base), authored, candidate});
    need(proof, 'Trusted integration proof is no longer valid; resubmit unchanged head');
  }
  const currentPR = await options.api(`${root(options.repo)}/pulls/${options.number}`);
  const currentIssue = await options.api(`${root(options.repo)}/issues/${state.issue.number}`);
  need(currentPR.head.sha === state.pr.head.sha && currentPR.body === state.pr.body && currentPR.title === state.pr.title &&
    currentPR.state === 'open' && !currentPR.draft && currentPR.base.ref === 'main' && currentIssue.body === state.issue.body,
    'Head/body or issue contract changed during integration review');
  verifyClaimForPR({branch: currentPR.head.ref, issue: currentIssue,
    comments: await githubPages(options.api, `${root(options.repo)}/issues/${state.issue.number}/comments`),
    prs: await linkedPulls(options.api, options.repo, state.issue.number)});
  checkCurrentChecks(await githubPages(options.api, `${root(options.repo)}/commits/${state.pr.head.sha}/check-runs`),
    {evidenceRequired: options.policy.mode === 'enforce-new' && evidenceRequirement(currentIssue, workSpec(currentIssue.body), options.policy, currentPR.head.ref).required});
  const freshStatuses = await options.api(`${root(options.repo)}/commits/${state.pr.head.sha}/status`);
  need(!freshStatuses.statuses?.length || freshStatuses.state === 'success', 'Commit statuses changed during final review');
  need((await options.api(`${root(options.repo)}/git/ref/heads/main`)).object.sha === state.base,
    'Main advanced during final review; resubmit unchanged head');
  const merged = await options.api(`${root(options.repo)}/pulls/${options.number}/merge`, 'PUT', {
    sha: state.pr.head.sha, merge_method: 'squash', commit_title: state.pr.title, commit_message: state.pr.body
  });
  need(merged.merged, 'GitHub did not merge the PR');
  return {accepted: true, merge_commit: merged.sha, title: state.pr.title, github_issue: state.issue.number,
    tested_base: state.base, tested_candidate: options.testedCandidate, reviewed_head: state.pr.head.sha, evidence: state.evidence, proof};
}
