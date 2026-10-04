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

const commitID = value => /^[a-f0-9]{40}$/.test(value ?? '') ? value : null;
function candidateFailure(message, details) {
  const error = Error(message);
  error.candidateDiagnostics = details;
  return error;
}
function candidateDiagnostics(commit, base, head, extra = {}) {
  return {expected_base: commitID(base), expected_head: commitID(head),
    candidate: commitID(commit?.sha), actual_parents: (commit?.parents ?? []).map(row => commitID(row.sha)), ...extra};
}
export function checkCandidateParents(commit, base, head) {
  if (commit.parents?.length !== 2 || commit.parents[0].sha !== base || commit.parents[1].sha !== head) {
    throw candidateFailure('Integration candidate is not the exact current main plus reviewed head; resubmit unchanged head',
      candidateDiagnostics(commit, base, head));
  }
}
function unchangedPR(fresh, original) {
  need(fresh.head.sha === original.head.sha, 'PR head changed; review the new head');
  need(fresh.state === 'open' && !fresh.draft && fresh.base.ref === 'main' &&
    fresh.head.ref === original.head.ref && fresh.head.repo?.full_name === original.head.repo?.full_name &&
    fresh.body === original.body && fresh.title === original.title && fresh.changed_files === original.changed_files,
    'PR scope/body changed during candidate preparation; revalidate before resubmission');
}
// GitHub generates merge refs asynchronously. Poll only their availability and
// parents, not trees or tests. A real base/evidence vintage change needs a new
// preflight; it must not be silently absorbed into the existing evidence review.
export async function currentCandidate(options, state) {
  const {api, repo, number} = options;
  const sleep = options.candidateSleep ?? (ms => new Promise(resolve => setTimeout(resolve, ms)));
  const now = options.candidateNow ?? Date.now;
  const started = now();
  let diagnostics;
  for (let attempt = 1; attempt <= 6; attempt++) {
    const pr = await api(`${root(repo)}/pulls/${number}`);
    unchangedPR(pr, state.pr);
    const base = (await api(`${root(repo)}/git/ref/heads/main`)).object.sha;
    diagnostics = candidateDiagnostics(null, base, state.pr.head.sha, {
      candidate: commitID(pr.merge_commit_sha), observed_pr_base: commitID(pr.base.sha),
      attempt, observed_at: new Date(now()).toISOString(), elapsed_ms: now() - started});
    if (base !== state.base || pr.base.sha !== state.pr.base.sha) {
      throw candidateFailure('Main or PR evidence base advanced during preparation; resubmit unchanged head',
        {...diagnostics, reason: 'base-advanced', inspected_base: commitID(state.base),
          inspected_pr_base: commitID(state.pr.base.sha)});
    }
    need(pr.mergeable !== false, 'Integration conflict; author intervention required');
    if (commitID(pr.merge_commit_sha)) {
      let object;
      try { object = await api(`${root(repo)}/git/commits/${pr.merge_commit_sha}`); }
      catch (error) {
        // A referenced asynchronous commit may not yet be readable. Never
        // disguise authentication, rate-limit, transport or server failures.
        if (!/\(HTTP 404\)$/.test(error.message)) throw error;
      }
      if (object) {
        diagnostics = candidateDiagnostics(object, base, state.pr.head.sha, {
          ...diagnostics, actual_parents: (object.parents ?? []).map(row => commitID(row.sha)), reason: 'stale-candidate'});
        if (object.parents?.length === 2 && object.parents[0].sha === base && object.parents[1].sha === state.pr.head.sha) {
          return {pr, base, candidate: pr.merge_commit_sha, object, attempts: attempt};
        }
      } else diagnostics.reason = 'candidate-unavailable';
    } else diagnostics.reason = 'candidate-unavailable';
    if (attempt === 6 || now() - started >= 30000) break;
    await sleep(2000);
  }
  throw candidateFailure('Integration candidate remained stale or unavailable after bounded refresh; resubmit unchanged head', diagnostics);
}
export function checkReviewedTrees(files, authored, integrated) {
  for (const name of new Set(files.flatMap(file => [file.filename, ...(file.previous_filename ? [file.previous_filename] : [])]))) {
    const a = authored.get(name), b = integrated.get(name);
    need((!a && !b) || (a && b && a.sha === b.sha && a.mode === b.mode && a.type === b.type),
      `Integration changes reviewed bytes at ${name}; update and obtain substantive review`);
  }
}
export {integrationProfile} from './integration-profile.mjs';

async function tree(api, repo, commit, knownObject) {
  const object = knownObject ?? await api(`${root(repo)}/git/commits/${commit}`);
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
  const fresh = await currentCandidate(options, state);
  if (fresh.attempts > 1) {
    // Waiting must not extend an expired claim or reuse revoked checks/review.
    const revalidated = await inspectMerge(options);
    need(!revalidated.replayed, 'PR merged during candidate refresh; resubmit unchanged head');
    unchangedPR(revalidated.pr, state.pr);
    need(revalidated.issue.body === state.issue.body &&
      revalidated.reservation.claim_id === state.reservation.claim_id,
      'Issue contract or ownership changed during candidate refresh');
    need(revalidated.base === fresh.base && revalidated.pr.base.sha === state.pr.base.sha,
      'Main or PR evidence base advanced during refresh validation; resubmit unchanged head');
    Object.assign(state, revalidated);
  }
  const candidate = fresh.candidate;
  const [authored, integrated] = await Promise.all([
    tree(options.api, options.repo, state.pr.head.sha), tree(options.api, options.repo, candidate, fresh.object)
  ]);
  checkCandidateParents(integrated.object, fresh.base, state.pr.head.sha);
  checkReviewedTrees(state.files, authored.entries, integrated.entries);
  const profile = integrationProfile(state.pr.head.ref, state.files, state.reservation);
  let proof = null;
  try { proof = await integrationProof({...options, head: state.pr.head.sha, profile,
    baseline: await tree(options.api, options.repo, state.base), authored, candidate: integrated}); } catch { /* unavailable proof requires isolated tests */ }
  return {...state, candidate, profile, proof, candidate_refresh_attempts: fresh.attempts};
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
    proof = await integrationProof({...options, runId: options.proofRunId, runAttempt: options.proofRunAttempt, head: state.pr.head.sha,
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
