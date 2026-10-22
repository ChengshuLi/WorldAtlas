import {collectGeographicApproval, bindingHash} from './geographic-adjudication-api.mjs';
import {COORDINATION_PATHS, integrationProfile, inertEvidenceAdditions, selectedDataCandidate, selectedDataSelection, candidateGeographyCode} from './integration-profile.mjs';
import {focusedIntegrationTest, PACKAGED_ASSET_TESTS} from './run-integration-tests.mjs';
import {EXECUTION_CODE, REBIND_CODE} from './check-unchanged-selected-geography.mjs';
import {loadPackageInputs, packagePathRequired, readPackageInputs, safePackagePath, containsPackagePath, selectedDataCheckoutPatterns, fullCheckoutPatterns, focusedCheckoutPatterns} from './package-inputs.mjs';
import {githubPages} from './issue-claim-contract.mjs';
import {memoizeImmutableGitBlobs} from './immutable-git-blobs.mjs';
import {checkGeographicReport, geographicReportProducts, preparedQueueSource} from './geographic-report-artifact.mjs';
import {QUEUE_WORKFLOW_PATH} from './integration-proof.mjs';

const need = (condition, message) => { if (!condition) throw Error(message); };
const root = repo => `/repos/${repo}`;

// Reuse the existing control/test inventories, excluding actual scientific
// method and package roles. Docs, workflows and packets can be source/producer
// pins; those ambiguous inputs retain geography. No scientific data is scanned.
export function geographyRequired(branch, files, reservation = {}, authoredEntries) {
  if (integrationProfile(branch, files, reservation, authoredEntries) !== 'evidence') return true;
  let definition;
  try { definition = loadPackageInputs(); } catch { return true; }
  const methods = new Set([...EXECUTION_CODE, ...REBIND_CODE]);
  return files.some(file => [file.filename, ...(file.previous_filename ? [file.previous_filename] : [])].some(name =>
    !(COORDINATION_PATHS.has(name) && name.startsWith('scripts/') || focusedIntegrationTest(name)) ||
    methods.has(name) || packagePathRequired(name, definition)));
}

// Exact-head review belongs to the submitting operator. Existing checks must
// be settled; check names and issue metadata add no merge authority.
export function checkCurrentChecks(checks) {
  const latest = new Map();
  for (const check of checks) {
    const key = `${check.app?.id}:${check.name}`;
    if (!latest.has(key) || latest.get(key).id < check.id) latest.set(key, check);
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
function preparedBranch({number, integrationRequestId}) {
  need(Number.isSafeInteger(number) && number > 0 && /^[-a-zA-Z0-9]{16,160}$/.test(integrationRequestId ?? ''),
    'Invalid owned integration candidate request');
  return `worldatlas-integration/pr-${number}-${integrationRequestId}`;
}
export async function cleanupCandidate(options, reference, expectedSHA) {
  need(reference === preparedBranch(options) && commitID(expectedSHA), 'Refuse cleanup of unowned integration reference');
  const route = `${root(options.repo)}/git/refs/heads/${reference}`;
  const api = typeof options.api.recovery === 'function' ? options.api.recovery : options.api;
  let current;
  try { current = await api(`${root(options.repo)}/git/ref/heads/${reference}`); }
  catch (error) { if (/\(HTTP 404\)$/.test(error.message)) return {status: 'absent', reference}; throw error; }
  need(current.object?.sha === expectedSHA, 'Integration reference changed; retain for operator inspection');
  await api(route, 'DELETE');
  return {status: 'deleted', reference};
}
// Cleanup is best-effort after an independently confirmed merge. GitHub's
// delete-ref endpoint has no SHA compare-and-swap: workers must never reuse or
// push to merged head branches. Recheck the ref immediately before deletion.
export async function cleanupMergedHead({api: rawAPI, repo, number, expectedHead, cleanupNow = () => performance.now()}) {
  const started = cleanupNow();
  let calls = 0;
  const api = async (...args) => {
    // No abandoned Promise.race: await each bounded GitHub request, then stop.
    // The production adapter limits a single request to 20 seconds. A request
    // already in progress can finish after this 30-second cleanup budget.
    need(calls < 10 && cleanupNow() - started < 30000, 'Head cleanup API/time budget exhausted');
    calls++;
    const result = await rawAPI(...args);
    need(cleanupNow() - started < 30000, 'Head cleanup time budget exhausted');
    return result;
  };
  let reference;
  const retained = reason => ({status: 'retained', ...(reference ? {reference} : {}), reason});
  try {
    need(/^[-\w.]+\/[-\w.]+$/.test(repo ?? '') && Number.isSafeInteger(number) && number > 0 && commitID(expectedHead),
      'Invalid merged-head cleanup request');
    const pr = await api(`${root(repo)}/pulls/${number}`);
    if (pr.merged !== true || pr.state !== 'closed' || !commitID(pr.merge_commit_sha) || pr.head?.sha !== expectedHead)
      return retained('PR is not confirmed merged at the expected head');
    if (pr.head.repo?.full_name !== repo) return retained('Head belongs to another or unavailable repository');
    reference = pr.head.ref;
    if (typeof reference !== 'string' || !/^[a-zA-Z0-9][a-zA-Z0-9._/-]*$/.test(reference) ||
        reference.startsWith('worldatlas-integration/') || reference.includes('..') || reference.includes('//') || reference.endsWith('/') || reference.endsWith('.lock'))
      return retained('Not a safely addressed head branch');
    const metadata = await api(root(repo));
    need(typeof metadata.default_branch === 'string' && metadata.default_branch.length > 0, 'Default branch unavailable');
    if (reference === metadata.default_branch) return retained('Default branch');
    const encoded = encodeURIComponent(reference);
    let branch;
    try { branch = await api(`${root(repo)}/branches/${encoded}`); }
    catch (error) { if (/\(HTTP 404\)$/.test(error.message)) return {status: 'absent', reference}; throw error; }
    if (branch.protected !== false) return retained('Protected or unknown branch protection');
    if (branch.commit?.sha !== expectedHead) return retained('Branch advanced beyond the merged PR head');
    const open = await githubPages(api, `${root(repo)}/pulls?state=open`);
    need(open.every(row => Number.isSafeInteger(row.number) && row.state === 'open' &&
      typeof row.head?.ref === 'string' && typeof row.head.repo?.full_name === 'string' &&
      typeof row.base?.ref === 'string' && typeof row.base.repo?.full_name === 'string'), 'Incomplete open PR identities');
    if (open.some(row => (row.head.repo.full_name === repo && row.head.ref === reference) ||
      (row.base.repo.full_name === repo && row.base.ref === reference)))
      return retained('Another open PR uses this branch as head or base');
    let current;
    try { current = await api(`${root(repo)}/git/ref/heads/${encoded}`); }
    catch (error) { if (/\(HTTP 404\)$/.test(error.message)) return {status: 'absent', reference}; throw error; }
    if (current.object?.sha !== expectedHead) return retained('Head ref changed before deletion');
    await api(`${root(repo)}/git/refs/heads/${encoded}`, 'DELETE');
    return {status: 'deleted', reference, expected_head: expectedHead};
  } catch (error) {
    return {status: 'pending', ...(reference ? {reference} : {}), reason: error.message};
  }
}
export async function createCandidate(options, state) {
  const reference = preparedBranch(options), {api, repo} = options;
  try { await api(`${root(repo)}/git/refs`, 'POST', {ref: `refs/heads/${reference}`, sha: state.base}); }
  catch (error) {
    // A lost response may hide a completed creation. Identify the possible ref,
    // but never delete a collision or a resource whose creation was unconfirmed.
    error.candidateCleanup = {status: 'creation-unconfirmed', reference, reason: error.message};
    throw error;
  }
  let expectedSHA = state.base;
  try {
    // GitHub merges into OUR disposable branch, never main or the worker branch.
    // No repository/candidate executable code runs with this write credential.
    const merged = await api(`${root(repo)}/merges`, 'POST', {base: reference, head: state.pr.head.sha,
      commit_message: `WorldAtlas isolated integration PR${options.number} request ${options.integrationRequestId}`});
    need(commitID(merged?.sha), 'GitHub did not create an isolated integration candidate');
    expectedSHA = merged.sha;
    const object = await api(`${root(repo)}/git/commits/${expectedSHA}`);
    need(object?.sha === expectedSHA && object.tree?.sha, 'Integration candidate identity or tree unavailable');
    checkCandidateParents(object, state.base, state.pr.head.sha);
    return {pr: state.pr, base: state.base, candidate: expectedSHA, object, reference};
  } catch (error) {
    try { await cleanupCandidate(options, reference, expectedSHA); }
    catch (cleanupError) { error.candidateCleanup = {status: 'pending', reference, reason: cleanupError.message}; }
    if (/\(HTTP 409\)$/.test(error.message)) {
      const conflict = candidateFailure('Integration conflict; author intervention required',
        candidateDiagnostics(null, state.base, state.pr.head.sha, {reason: 'conflict', observed_at: new Date().toISOString()}));
      conflict.candidateCleanup = error.candidateCleanup; throw conflict;
    }
    throw error;
  }
}
export {integrationProfile} from './integration-profile.mjs';

async function tree(api, repo, commit, knownObject) {
  const object = knownObject ?? await api(`${root(repo)}/git/commits/${commit}`);
  const value = await api(`${root(repo)}/git/trees/${object.tree.sha}?recursive=1`);
  need(!value.truncated && Array.isArray(value.tree), 'Incomplete integration tree; cannot verify reviewed scope');
  return {object, entries: new Map(value.tree.map(row => [row.path, row]))};
}

// Execution routing follows the authenticated combined tree, not GitHub's PR
// inventory (which can still include changes already accepted on main). The PR
// inventory remains a complete authored diff for review in inspectMerge.
export function integrationChanges(baseline, integrated) {
  const files = [];
  for (const filename of [...new Set([...baseline.keys(), ...integrated.keys()])].sort()) {
    const before = baseline.get(filename), after = integrated.get(filename);
    const old = before?.type === 'tree' ? undefined : before;
    const next = after?.type === 'tree' ? undefined : after;
    if (old?.type === next?.type && old?.mode === next?.mode && old?.sha === next?.sha) continue;
    files.push({filename, status: !old ? 'added' : !next ? 'removed' : 'modified',
      ...(next ? {mode: next.mode} : {})});
  }
  return files;
}

// Both trusted phases bind the reviewed head, current checks and main. Actual
// consumers verify scientific inputs/results; no generic issue-driven byte walk
// is repeated here. Candidate code never receives a write token.
export async function inspectMerge({api, repo, number, expectedHead, candidateContext}) {
  const pr = await api(`${root(repo)}/pulls/${number}`);
  if (pr.head.sha !== expectedHead) throw candidateFailure('PR head changed; review the new head',
    candidateDiagnostics(null, candidateContext?.base ?? pr.base.sha, expectedHead, {
      candidate: commitID(candidateContext?.candidate ?? pr.merge_commit_sha), observed_head: commitID(pr.head.sha), observed_pr_base: commitID(pr.base.sha),
      reason: 'head-changed', observed_at: new Date().toISOString()}));
  if (pr.merged) {
    need(commitID(pr.merge_commit_sha), 'Merged PR has no confirmed merge commit');
    return {replayed: true, pr};
  }
  need(pr.state === 'open' && !pr.draft && pr.base.ref === 'main' && pr.head.repo?.full_name === repo,
    'Only open non-draft repository PRs targeting main may merge');
  const files = await githubPages(api, `${root(repo)}/pulls/${number}/files`);
  need(Number.isSafeInteger(pr.changed_files) && files.length === pr.changed_files &&
    new Set(files.map(file => file.filename)).size === files.length, 'Incomplete PR file inventory');
  checkCurrentChecks(await githubPages(api, `${root(repo)}/commits/${expectedHead}/check-runs`));
  const statuses = await api(`${root(repo)}/commits/${expectedHead}/status`);
  need(!statuses.statuses?.length || statuses.state === 'success', 'Commit status is pending or failed');
  const base = (await api(`${root(repo)}/git/ref/heads/main`)).object.sha;
  return {pr, files, base};
}
// The operator supplies the consumers actually reviewed for
// this immutable pair. This is an execution argument, not source approval or an
// automated proof that an arbitrary roster is sufficient. Unknown impact uses
// the complete suite; package and geography obligations remain independent.
export function reviewedTestPlan(request, {base, head, entries, files, definition}) {
  if (request === undefined || request === null || request === '') return null;
  const plan = typeof request === 'string' ? JSON.parse(request) : request;
  need(plan && !Array.isArray(plan) && commitID(plan.base) && plan.base === base &&
    commitID(plan.head) && plan.head === head, 'Reviewed tests are stale or lack the exact base/head binding');
  need(Array.isArray(plan.files) && plan.files.length > 0, 'Reviewed tests require a nonempty test roster');
  // New requests do not maintain a shadow transitive fixture catalogue.
  const ordinary = (name, row) => row?.type === 'blob' && ['100644','100755'].includes(row.mode) && commitID(row.sha) &&
    name.split('/').slice(0,-1).every((_, index, parts) => {
      const parent = entries.get(parts.slice(0,index+1).join('/'));
      return !parent || parent.type === 'tree' && parent.mode === '040000';
    });
  const tests = [...new Set(plan.files)];
  need(tests.every(name => typeof name === 'string' && /^test\/[A-Za-z0-9_.-]+\.test\.mjs$/.test(name) &&
    ordinary(name, entries.get(name))), 'Reviewed test is missing or not an ordinary candidate test file');
  const packageChanged = files.some(file => [file.filename, file.previous_filename].filter(Boolean)
    .some(name => containsPackagePath(definition.inputs, name)));
  if (packageChanged) for (const name of PACKAGED_ASSET_TESTS) {
    need(ordinary(name, entries.get(name)), 'Required packaged consumer is unavailable');
    if (!tests.includes(name)) tests.push(name);
  }
  const build = tests.some(name => PACKAGED_ASSET_TESTS.includes(name));
  // Contract fixtures are one stable complete source directory. Current policy
  // comes from the existing executing-authority roster, and real package inputs
  // come from the package definition consumed by the builder itself.
  const inputs = [...EXECUTION_CODE];
  // These consumers read current declared policy, not historical fixture copies.
  for (const [consumer, operand] of [
    ...['test/final-bank-finalizer.test.mjs', 'test/selected-delivery-smoke.test.mjs', 'test/final-bank-checkpoint.test.mjs'].map(consumer =>
      [consumer, 'coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz']),
    ['test/current-rebind-product-custody.test.mjs', 'coordination/engineering/additive-native-composition-20261009/execution-code-paths.json'],
    ['test/local-workspace.test.mjs', 'docs/LOCAL_WORKSPACES.md'],
    ['test/regional-research-gate.test.mjs', 'data/research-geography-gate.json'],
    ...['test/current-postgres-recovery.test.mjs', 'test/publication-plan.test.mjs',
      'test/publication-cloudflare.test.mjs', 'test/package-current-additive.test.mjs'].map(consumer =>
      [consumer, 'coordination/publication/cloudflare-history.json']),
    ...['test/publication-cloudflare.test.mjs', 'test/merge-integration.test.mjs'].map(consumer =>
      [consumer, 'coordination/engineering/cloudflare-publication-846-20261007/registry-source.json']),
    ...['test/neon-forward-migrations.test.mjs', 'test/compact-membership-profile.test.mjs', 'test/merge-integration.test.mjs'].flatMap(consumer =>
      ['coordination/publication/cloudflare-history.json', 'data/observation-registry-history/base-v1.json',
        'data/research-geography-gate.json', 'data/hosted-type-catalog.json'].map(operand => [consumer, operand])),
    ...['data/observation-registry-history/base-v1.json', 'data/research-geography-gate.json',
      'data/hosted-type-catalog.json'].map(operand => ['test/settlement-population-import.test.mjs', operand]),
    ...['test/neon-forward-migrations.test.mjs', 'test/settlement-population-import.test.mjs',
      'test/merge-integration.test.mjs'].map(consumer => [consumer, 'data/settlement-estimates.json'])
  ]) if (tests.includes(consumer)) {
    need(definition.verification_paths.includes(operand), 'Current reviewed operand lacks its verification declaration: ' + operand);
    if (!inputs.includes(operand)) inputs.push(operand);
  }
  need(plan.inputs === undefined || Array.isArray(plan.inputs) &&
    (plan.inputs.length===0 || JSON.stringify(plan.inputs)===JSON.stringify(inputs)),
    'Reviewed fixture operands are derived; manual inputs are unsupported');
  for (const name of inputs) need(ordinary(name,entries.get(name)), 'Current executing authority input is unavailable: '+name);
  const fixtures=[...entries].filter(([name,row])=>name.startsWith('test/fixtures/')&&row.type!=='tree');
  need(fixtures.length>0&&fixtures.every(([name,row])=>ordinary(name,row)), 'Self-contained fixture boundary is missing or nonordinary');
  return {files:tests, inputs, build,
    // Full-profile consumers can read historical fixtures outside package roles.
    checkout_patterns:build ? fullCheckoutPatterns(definition) : focusedCheckoutPatterns(definition, inputs)};
}

export async function prepareIntegration(options) {
  options = {...options, api: memoizeImmutableGitBlobs(options.api)};
  const state = await inspectMerge(options);
  if (state.replayed) return state;
  const fresh = await createCandidate(options, state);
  try {
    // Candidate creation cannot grant merge permission: final integration binds
    // the reviewed head, current checks and main again before the squash.
    const candidate = fresh.candidate;
    const [baseline, integrated] = await Promise.all([
      tree(options.api, options.repo, state.base), tree(options.api, options.repo, candidate, fresh.object)
    ]);
    checkCandidateParents(integrated.object, fresh.base, state.pr.head.sha);
    const files = integrationChanges(baseline.entries, integrated.entries);
    const applicability = integrationProfile(state.pr.head.ref, files, {}, integrated.entries);
    let selection = null;
    if (applicability === 'full' && selectedDataCandidate(state.pr.head.ref, files, {})) {
      try {
        // Applicability belongs to the actual combined candidate; older author
        // snapshots need not reproduce accepted-main smoke or package edits.
        selection = await selectedDataSelection({...options, branch: state.pr.head.ref, files, reservation: {}, baseline, authored: integrated});
      } catch { /* Unknown applicability retains the complete suite. */ }
    }
    const geographyRequiredForCandidate = geographyRequired(state.pr.head.ref, files, {}, integrated.entries);
    const software = geographyRequiredForCandidate && candidateGeographyCode(applicability, files, selection?.test_selection);
    const packageInputs = await readPackageInputs({api: options.api, route: root(options.repo), base: candidate, maximumBytes: 8 * 1024 * 1024});
    // Pure new evidence packets need the same reviewed consumer contract by
    // default, not an operator-selected mode or all coordination-code regressions.
    const request = [undefined, null, ''].includes(options.reviewedTests) &&
      inertEvidenceAdditions(files, integrated.entries, packageInputs)
      ? {base:state.base, head:state.pr.head.sha, files:[
        'test/evidence-quality.test.mjs', 'test/premerge-evidence.test.mjs',
        'test/engineering-owned-scope-routing.test.mjs']}
      : options.reviewedTests;
    const reviewed = reviewedTestPlan(request, {base:state.base, head:state.pr.head.sha,
      entries:integrated.entries, files, definition:packageInputs});
    need(!reviewed || !selection, 'Selected-data delivery retains its mandatory native and emitted execution path');
    const profile = reviewed ? (reviewed.build ? 'full' : 'evidence') : applicability;
    const checkoutPatterns = selection?.test_selection === 'selected-data'
      ? selectedDataCheckoutPatterns(packageInputs, integrated.entries, selection.expectations_path)
      : reviewed?.checkout_patterns ?? (profile === 'full' ? fullCheckoutPatterns(packageInputs) : focusedCheckoutPatterns(packageInputs));
    return {...state, candidate, profile, ...selection,
      ...(reviewed ? {test_selection:'reviewed', test_files:reviewed.files, shards:[0]} : {}), geography_software: software,
      geography_required: geographyRequiredForCandidate,
      candidate_tree: integrated.object.tree.sha, checkout_patterns: checkoutPatterns,
      candidate_ref: fresh.reference};
  } catch (error) {
    if (fresh.reference) {
      try { await cleanupCandidate(options, fresh.reference, fresh.candidate); }
      catch (cleanupError) { error.candidateCleanup = {status: 'pending', reference: fresh.reference, reason: cleanupError.message}; }
    }
    throw error;
  }
}
export async function completeIntegration(options) {
  need(options.preparedGeographySoftware === undefined || typeof options.preparedGeographySoftware === 'boolean',
    'Invalid prepared geographic checker choice');
  options = {...options, api: memoizeImmutableGitBlobs(options.api)};
  // Duplicate/canceled executions reconcile the immutable reviewed head before
  // requiring now-inapplicable candidate jobs.
  const initialPR = await options.api(`${root(options.repo)}/pulls/${options.number}`);
  need(initialPR.head?.sha === options.expectedHead, 'PR head changed; obtain fresh exact-head review');
  if (initialPR.merged) {
    need(commitID(initialPR.merge_commit_sha), 'Merged PR has no confirmed merge commit');
    return {accepted: true, replayed: true, merge_commit: initialPR.merge_commit_sha,
      head_cleanup: await cleanupMergedHead(options)};
  }
  need(options.integrationResult === 'success',
    'Integration tests failed, skipped or were cancelled; no merge performed');
  // Rejection-only fast path: known stale base/head cannot benefit from the
  // candidate inventory. Eligible requests still run every actual consumer
  // validation and the later final base guard.
  const current = await options.api(`${root(options.repo)}/git/ref/heads/main`);
  need(current.object?.sha === options.testedBase, 'Main advanced after integration tests; resubmit unchanged head');
  const state = await inspectMerge(options);
  if (state.replayed) return {accepted: true, replayed: true, merge_commit: state.pr.merge_commit_sha,
    head_cleanup: await cleanupMergedHead(options)};
  need(state.base === options.testedBase, 'Main advanced after integration tests; resubmit unchanged head');
  const candidate = await options.api(`${root(options.repo)}/git/commits/${options.testedCandidate}`);
  need(candidate.sha === options.testedCandidate && candidate.tree?.sha,
    'Integration candidate identity or tree unavailable');
  checkCandidateParents(candidate, state.base, state.pr.head.sha);
  // Independently rederive execution applicability from the exact tested pair.
  // Neither preparation output nor a stale authored inventory can waive it.
  const [baseline, integrated] = await Promise.all([
    tree(options.api, options.repo, state.base), tree(options.api, options.repo, options.testedCandidate, candidate)
  ]);
  const files = integrationChanges(baseline.entries, integrated.entries);
  if (options.reviewedTests) reviewedTestPlan(options.reviewedTests, {base:state.base, head:state.pr.head.sha,
    entries:integrated.entries, files,
    definition:await readPackageInputs({api:options.api, route:root(options.repo), base:options.testedCandidate})});
  const omitGeography = options.geographyResult === 'skipped' &&
    !geographyRequired(state.pr.head.ref, files, {}, integrated.entries);
  let geography, geographicSource, waterPass = false;
  // Clean Git composition is verified by the combined candidate checks. Final
  // authority binds its parents and exact tested base/head, not whole-file
  // equality with the isolated author branch.
  if (!omitGeography) {
    need(options.geographyResult === 'success',
      'Trusted combined geography check missing, failed or cancelled; no merge performed');
    need(typeof options.geographyReportLoader === 'function', 'Missing trusted geography report loader');
    geography = await options.geographyReportLoader({api: options.api});
    geographicSource = geographicReportProducts(geography)?.source;
    if (geographicSource) need(geographicSource.tree === candidate.tree.sha &&
      geographicSource.head === state.pr.head.sha && geographicSource.baseline === state.base &&
      (!geographicSource.candidate_commit || geographicSource.candidate_commit === geography.candidate_commit),
      'Geographic source differs from accepted candidate identities');
    const preparedSource = preparedQueueSource(geography);
    if (preparedSource) need(preparedSource.workflow_path === QUEUE_WORKFLOW_PATH &&
      preparedSource.event === 'workflow_dispatch' && preparedSource.candidate_commit === options.testedCandidate &&
      preparedSource.tree === candidate.tree.sha && preparedSource.head === state.pr.head.sha && preparedSource.baseline === state.base,
      'Prepared geographic source differs from accepted queue candidate');
    let software;
    if (preparedSource && options.preparedGeographySoftware !== undefined) {
      // The same trusted prepare output already selected this authenticated
      // queue job's checker. Exact candidate/source bindings above prevent
      // transferring the choice; report text alone supplies no such authority.
      software = options.preparedGeographySoftware;
    } else {
      // Older queued workflows and non-queue callers retain the original
      // derivation. Missing preparation output never implies baseline code.
      const profile = integrationProfile(state.pr.head.ref, files, {}, integrated.entries);
      let selection = null;
      if (candidateGeographyCode(profile, files) && selectedDataCandidate(state.pr.head.ref, files, {})) {
        try {
          selection = await selectedDataSelection({...options, branch: state.pr.head.ref, files,
            reservation: {}, baseline, authored: integrated});
        } catch { /* Unknown applicability retains full software validation. */ }
      }
      software = candidateGeographyCode(profile, files, selection?.test_selection);
    }
    const codeCommit = software ? options.testedCandidate : state.base;
    waterPass = checkGeographicReport(geography, state.base, options.testedCandidate, codeCommit);
  }
  const currentPR = await options.api(`${root(options.repo)}/pulls/${options.number}`);
  need(currentPR.head.sha === state.pr.head.sha && currentPR.head.repo?.full_name === options.repo &&
    currentPR.state === 'open' && !currentPR.draft && currentPR.base.ref === 'main',
    'Reviewed head or PR eligibility changed during integration');
  checkCurrentChecks(await githubPages(options.api, `${root(options.repo)}/commits/${state.pr.head.sha}/check-runs`));
  const freshStatuses = await options.api(`${root(options.repo)}/commits/${state.pr.head.sha}/status`);
  need(!freshStatuses.statuses?.length || freshStatuses.state === 'success', 'Commit statuses changed during final review');
  if (waterPass) {
    const approval = await collectGeographicApproval({api: options.api, repo: options.repo,
      number: options.number, expectedHead: state.pr.head.sha, policy: options.policy});
    need(approval.status === 'reviewed' && approval.authority_sha256 === geography.adjudication.authority_sha256 &&
      bindingHash(approval.review) === bindingHash(geography.adjudication.review) &&
      JSON.stringify(approval.dossiers.flatMap(row => row.decision.finding_sha256s).sort()) ===
        JSON.stringify(geography.adjudication.finding_sha256s),
      'Geographic source decision changed after combined check; rerun unchanged head');
  }
  need((await options.api(`${root(options.repo)}/git/ref/heads/main`)).object.sha === state.base,
    'Main advanced during final review; resubmit unchanged head');
  const merged = await options.api(`${root(options.repo)}/pulls/${options.number}/merge`, 'PUT', {
    sha: state.pr.head.sha, merge_method: 'squash', commit_title: currentPR.title, commit_message: currentPR.body
  });
  need(merged.merged, 'GitHub did not merge the PR');
  return {accepted: true, merge_commit: merged.sha, title: currentPR.title,
    geography: omitGeography ? {status: 'not-applicable', reason: 'non-geographic-controls'} :
      {status: 'passed', trusted_code_commit: geography.trusted_code_commit, candidate_commit: geography.candidate_commit,
      report_sha256: options.geographyReportHash, adjudication: geography.adjudication ?? null,
      ...(geographicSource ? {execution: 'fresh-queue', source: geographicSource} : {})},
    tested_base: state.base, tested_candidate: options.testedCandidate, reviewed_head: state.pr.head.sha,
    head_cleanup: await cleanupMergedHead(options)};
}
