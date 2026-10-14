// Optional read-only reuse of a successful predecessor's scientific execution.
// Current ownership, scope, evidence and review remain separate fresh gates.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {githubAPI, githubPages, workSpec} from './issue-claim-contract.mjs';
import {validateIssuePRBody} from './check-handoff-scope.mjs';
import {WORKFLOW_PATH, successfulGeographyJob} from './integration-proof.mjs';
import {prepareGeographyProof, validateGeographyProof} from './geographic-report-artifact.mjs';
import {inspectExecutingSelectedGeography} from './check-unchanged-selected-geography.mjs';
import {validatePackageInputs, packagePathRequired, PACKAGE_INPUT_FILE} from './package-inputs.mjs';

const oid = value => typeof value === 'string' && /^[a-f0-9]{40}$/.test(value);
const positive = value => Number.isSafeInteger(value) && value > 0;
const need = (value, reason) => {if (!value) throw Error(reason);};
const ordinary = row => row?.type === 'blob' && row.mode === '100644' && oid(row.sha) &&
  Number.isSafeInteger(row.size) && row.size > 0;
const same = (left, right) => left?.type === right?.type && left?.mode === right?.mode && left?.sha === right?.sha;
const MAX_METADATA = 1024 * 1024;

export async function readGeographyReuseTree({api, repo, commit}) {
  need(oid(commit), 'invalid-commit');
  const object = await api(`/repos/${repo}/git/commits/${commit}`);
  need(object?.sha === commit && oid(object.tree?.sha) && Array.isArray(object.parents), 'invalid-commit-object');
  const value = await api(`/repos/${repo}/git/trees/${object.tree.sha}?recursive=1`);
  need(value?.sha === object.tree.sha && value.truncated === false && Array.isArray(value.tree) &&
    value.tree.length > 0 && value.tree.length <= 100000, 'incomplete-tree');
  const entries = new Map();
  for (const row of value.tree) {
    need(typeof row.path === 'string' && row.path.length > 0 && !row.path.includes('\\') &&
      row.path.split('/').every(part => part && part !== '.' && part !== '..') &&
      !entries.has(row.path) && oid(row.sha) &&
      ['040000:tree', '100644:blob', '100755:blob', '120000:blob', '160000:commit'].includes(`${row.mode}:${row.type}`), 'invalid-tree-entry');
    entries.set(row.path, row);
  }
  return {object, entries};
}

async function blob({api, repo, entry, maximum = MAX_METADATA}) {
  need(ordinary(entry) && entry.size <= maximum, 'nonordinary-or-oversized-metadata');
  const value = await api(`/repos/${repo}/git/blobs/${entry.sha}`);
  need(value?.sha === entry.sha && value.encoding === 'base64' && value.size === entry.size &&
    typeof value.content === 'string' && value.content.length <= maximum * 2, 'invalid-metadata-transport');
  const raw = Buffer.from(value.content, 'base64');
  need(raw.length === entry.size && createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex') === entry.sha,
    'metadata-blob-identity');
  need(!raw.includes(0) && Buffer.from(raw.toString('utf8')).equals(raw), 'nontext-metadata');
  return raw;
}

// Filename admission does NOT prove scientific non-consumption. The complete
// audited route collector below must also establish unchanged actual inputs.
export async function receivingMetadataDelta({api, repo, source, current, trusted, branch, manifestPath}) {
  need(/^engineering\/[A-Za-z0-9_-]+$/.test(branch ?? ''), 'unsupported-receiving-branch');
  const prefix = `coordination/engineering/${branch.slice('engineering/'.length)}/`;
  need(manifestPath === prefix + 'evidence-quality.json', 'foreign-receiving-manifest');
  need(current.object.parents.length === 1 && current.object.parents[0].sha === source.object.sha,
    'not-direct-metadata-successor');
  const names = new Set([...source.entries.keys(), ...current.entries.keys()]);
  const changed = [...names].filter(name => {
    const before = source.entries.get(name), after = current.entries.get(name);
    return !(before?.type === 'tree' && after?.type === 'tree') && !same(before, after);
  }).sort();
  need(changed.length > 0 && changed.length <= 2 && changed.every(name =>
    name === manifestPath || name === prefix + 'README.md'), 'nonmetadata-tree-delta');
  for (const name of changed) {
    for (const tree of [source, current]) {
      const raw = await blob({api, repo, entry: tree.entries.get(name), maximum: name.endsWith('.md') ? 128 * 1024 : MAX_METADATA});
      if (name.endsWith('.json')) need(JSON.parse(raw)?.version === 1, 'unsupported-receiving-manifest');
    }
  }
  // The executing workflow is approved current-base code. A candidate workflow
  // cannot mint its own successful job shape or select different checkouts.
  need(ordinary(trusted.entries.get(WORKFLOW_PATH)) &&
    same(trusted.entries.get(WORKFLOW_PATH), source.entries.get(WORKFLOW_PATH)) &&
    same(trusted.entries.get(WORKFLOW_PATH), current.entries.get(WORKFLOW_PATH)), 'untrusted-producer-workflow');
  const definition = validatePackageInputs(JSON.parse(await blob({api, repo, entry: current.entries.get(PACKAGE_INPUT_FILE)})));
  need(changed.every(name => !packagePathRequired(name, definition)), 'metadata-is-package-input');
  return changed;
}

export function ordinaryOriginalGeography(report, {baseline, head}) {
  return report?.version === 1 && report.method_id === 'worldatlas-trusted-geography-check-v1' &&
    report.baseline_commit === baseline && report.trusted_code_commit === baseline && report.candidate_commit === head &&
    report.candidate_code_executed === false && report.published === false && report.source_approval === false &&
    report.gate_status === 'passed' && ['not-applicable', 'no-footprint-change', 'no-new-regression', 'no-new-native-loss'].includes(report.status) &&
    !Object.hasOwn(report, 'adjudication');
}

export function acquireGeographyReuseGraphs({directory, repo, head, token, execute = execFileSync}) {
  const env = {...Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.startsWith('GIT_'))),
    GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: '/dev/null', GIT_TERMINAL_PROMPT: '0',
    GIT_CONFIG_COUNT: '1', GIT_CONFIG_KEY_0: 'http.https://github.com/.extraheader',
    GIT_CONFIG_VALUE_0: 'AUTHORIZATION: basic ' + Buffer.from('x-access-token:' + token).toString('base64')};
  // A warm graph needs no fetch or shallow-boundary mutation. Prove both the
  // parent commit and complete tree metadata locally with lazy fetch disabled.
  const common = ['--no-replace-objects', '-c', 'core.hooksPath=/dev/null', '-c', 'credential.helper=', '-C', directory];
  try {
    const local = {env: {...env, GIT_NO_LAZY_FETCH: '1'}, timeout: 10000,
      maxBuffer: 16 * 1024 * 1024, stdio: ['ignore', 'pipe', 'pipe']};
    execute('git', [...common, 'cat-file', '-e', `${head}^`], local);
    execute('git', [...common, 'ls-tree', '-r', head], local);
    execute('git', [...common, 'ls-tree', '-r', `${head}^`], local);
    return;
  } catch { /* Cold workflow checkout acquires the exact immutable graph below. */ }
  // Only immutable commit/tree metadata, never candidate checkout or execution.
  execute('git', ['--no-replace-objects', '-c', 'core.hooksPath=/dev/null', '-c', 'credential.helper=', '-C', directory,
    'fetch', '--quiet', '--no-tags', '--no-write-fetch-head', '--no-recurse-submodules', '--no-auto-maintenance',
    '--filter=blob:none', '--depth=2', `https://github.com/${repo}.git`, head],
  {env, timeout: 30000, maxBuffer: 1024 * 1024, stdio: ['ignore', 'pipe', 'pipe']});
}

export async function reusePRGeography({event, repo, api, token, directory = process.cwd(),
  loadProof = prepareGeographyProof, inspect = inspectExecutingSelectedGeography, acquire = acquireGeographyReuseGraphs}) {
  const scheduled = event?.pull_request;
  need(/^[-\w.]+\/[-\w.]+$/.test(repo ?? '') && event.repository?.full_name === repo && positive(scheduled?.number) &&
    oid(scheduled.head?.sha) && oid(scheduled.base?.sha), 'invalid-pr-context');
  const root = `/repos/${repo}`, number = scheduled.number;
  const pr = await api(`${root}/pulls/${number}`);
  const stable = value => value?.number === number && value.state === 'open' && value.head?.sha === scheduled.head.sha &&
    value.head.ref === scheduled.head.ref && value.head.repo?.full_name === repo && value.base?.repo?.full_name === repo &&
    value.base.ref === 'main' && value.base.sha === scheduled.base.sha;
  need(stable(pr), 'current-pr-changed');
  const {github_issue} = validateIssuePRBody(pr.body ?? '');
  const issue = await api(`${root}/issues/${github_issue}`), spec = workSpec(issue.body);
  need(issue.number === github_issue && issue.state === 'open' && spec.mode === 'engineering', 'foreign-issue-contract');
  const current = await readGeographyReuseTree({api, repo, commit: pr.head.sha});
  need(current.object.parents.length === 1 && oid(current.object.parents[0].sha), 'unsupported-parent-count');
  const head = current.object.parents[0].sha, baseline = pr.base.sha;
  const [source, trusted] = await Promise.all([readGeographyReuseTree({api, repo, commit: head}),
    readGeographyReuseTree({api, repo, commit: baseline})]);
  const paths = await receivingMetadataDelta({api, repo, source, current, trusted, branch: pr.head.ref,
    manifestPath: spec.evidence_quality?.manifest_path});
  const inventory = await api(`${root}/actions/workflows/merge-integration-checks.yml/runs?head_sha=${head}&event=pull_request&per_page=100`);
  need(Array.isArray(inventory.workflow_runs) && inventory.workflow_runs.length <= 100, 'run-inventory-unavailable');
  let selected;
  // Bounded discovery, no recursive chain of reused/expired producers.
  for (const run of inventory.workflow_runs.slice(0, 5)) {
    if (!positive(run.id) || !positive(run.run_attempt) || run.head_sha !== head || run.head_branch !== pr.head.ref ||
      run.path !== WORKFLOW_PATH || run.event !== 'pull_request' || run.repository?.full_name !== repo ||
      run.head_repository?.full_name !== repo || run.status !== 'completed' ||
      !['success', 'failure', 'cancelled'].includes(run.conclusion) || !run.pull_requests?.some(row => row.number === number)) continue;
    const jobs = await githubPages(async route => (await api(route)).jobs,
      `${root}/actions/runs/${run.id}/attempts/${run.run_attempt}/jobs`);
    const job = successfulGeographyJob(jobs);
    if (!job || job.run_id !== run.id || job.head_sha !== head || job.run_attempt !== run.run_attempt) continue;
    const proof = {run_id: run.id, run_attempt: run.run_attempt, geography_job_id: job.id, tree: source.object.tree.sha};
    const loaded = await loadProof({api, repo, number, head, baseline, proof, token});
    if (!loaded || !ordinaryOriginalGeography(loaded.report, {baseline, head: loaded.source.candidate_commit ?? head})) continue;
    const origin = validateGeographyProof(loaded.source);
    need(origin.run_id === run.id && (origin.current_run_attempt ?? origin.run_attempt) === run.run_attempt &&
      (origin.current_job_id ?? origin.job_id) === job.id && origin.head === head && origin.baseline === baseline &&
      origin.tree === source.object.tree.sha && origin.artifact_name === `proposed-geography-${number}-${origin.run_attempt}`,
      'original-proof-binding');
    selected = {run, source: loaded.source}; break;
  }
  need(selected, 'no-original-successful-geography');
  acquire({directory, repo, head: pr.head.sha, token});
  const applicability = await inspect({repo: directory, baseline: head, candidate: pr.head.sha, trusted: baseline, metadataPaths: paths});
  need(applicability?.status === 'unchanged-selected-inputs' && applicability.baseline_commit === head &&
    applicability.candidate_commit === pr.head.sha && applicability.trusted_reader_policy_commit === baseline &&
    applicability.candidate_code_executed === false && applicability.science_reexecuted === false,
    'scientific-input-equivalence-unavailable');
  const [settled, finalIssue, finalRun] = await Promise.all([api(`${root}/pulls/${number}`), api(`${root}/issues/${github_issue}`),
    api(`${root}/actions/runs/${selected.run.id}`)]);
  need(stable(settled) && settled.body === pr.body && finalIssue.body === issue.body && finalIssue.state === 'open', 'current-authority-changed');
  need(finalRun.id === selected.run.id && finalRun.run_attempt === selected.run.run_attempt && finalRun.head_sha === head &&
    finalRun.status === 'completed' && finalRun.conclusion === selected.run.conclusion, 'original-run-changed');
  return {version: 1, status: 'reused-original', reviewed_head: pr.head.sha, candidate_tree: current.object.tree.sha,
    trusted_baseline: baseline, metadata_paths: paths, source: selected.source, applicability,
    science_reexecuted: false, transferable_geography_authority: false,
    limits: ['Original successful execution and bytes retained under their original identities.',
      'Current scope, evidence, ownership and exact-head review remain mandatory.',
      'The merge queue still requires its exact-candidate geography report; this is not accepted checkpoint custody.']};
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  let result;
  try {
    const event = JSON.parse(fs.readFileSync(process.env.GITHUB_EVENT_PATH, 'utf8'));
    result = await reusePRGeography({event, repo: process.env.GITHUB_REPOSITORY, token: process.env.GH_TOKEN,
      api: githubAPI(process.env.GH_TOKEN)});
  } catch (error) {
    // Reuse is optional; no failure/absence becomes scientific success. Do not
    // echo transport errors or subprocess environments containing credentials.
    result = {version: 1, status: 'fresh-check-required', reason: /^[a-z][a-z0-9-]{1,80}$/.test(error?.message ?? '')
      ? error.message : 'predecessor-proof-or-input-equivalence-unavailable'};
  }
  fs.writeFileSync('geography-reuse.json', JSON.stringify(result, null, 2) + '\n');
  fs.appendFileSync(process.env.GITHUB_OUTPUT, `reused=${result.status === 'reused-original'}\n`);
  console.log(JSON.stringify({status: result.status, reason: result.reason,
    reviewed_head: result.reviewed_head, original_head: result.source?.head,
    original_run: result.source?.run_id, science_reexecuted: result.science_reexecuted,
    metadata_bodies_read: result.applicability?.metadata_bodies_read}));
}
