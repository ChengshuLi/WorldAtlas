// Optional predecessor computation admission. This executes only trusted code;
// current ownership/evidence/review and current-head controls remain fresh.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {githubAPI, githubPages} from './issue-claim-contract.mjs';
import {readGeographyReuseTree, reusePRGeography} from './reuse-pr-geography.mjs';
import {prepareGeographyProof} from './geographic-report-artifact.mjs';
import {METADATA_PROGRAMS, matchMetadataRegressionProgram} from './metadata-regression-program.mjs';
import {originalFullRegressionJobs} from './regression-proof-jobs.mjs';
import {inspectUnchangedSelectedGeography} from './check-unchanged-selected-geography.mjs';
import {createRoutingMetadataAcquisition} from './geography-routing-metadata.mjs';
const need = (value, reason) => {if (!value) throw Error(reason);};

export async function readMetadataRegressionCatalogue({api, repo, trusted}) {
  const entry = trusted.entries.get(METADATA_PROGRAMS);
  need(entry?.type === 'blob' && entry.mode === '100644' && Number.isSafeInteger(entry.size) &&
    entry.size > 0 && entry.size <= 64 * 1024, 'regression-program-catalogue-unavailable');
  const value = await api(`/repos/${repo}/git/blobs/${entry.sha}`);
  need(value?.sha === entry.sha && value.encoding === 'base64' && value.size === entry.size &&
    typeof value.content === 'string', 'regression-program-catalogue-body-unavailable');
  const raw = Buffer.from(value.content, 'base64');
  need(raw.length === entry.size && createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex') === entry.sha,
    'regression-program-catalogue-integrity');
  return JSON.parse(raw);
}

export async function reusePRRegression({event, repo, api, token, directory = process.cwd(),
  reuseGeography = reusePRGeography, loadGeography = prepareGeographyProof, inspect}) {
  const head = event?.pull_request?.head?.sha, base = event?.pull_request?.base?.sha;
  const current = await readGeographyReuseTree({api, repo, commit: head});
  need(current.object.parents.length === 1, 'unsupported-parent-count');
  const parent = current.object.parents[0].sha;
  const [source, trusted] = await Promise.all([readGeographyReuseTree({api, repo, commit: parent}),
    readGeographyReuseTree({api, repo, commit: base})]);
  const catalogue = await readMetadataRegressionCatalogue({api, repo, trusted});
  const program = matchMetadataRegressionProgram({source, current, trusted,
    branch: event.pull_request.head.ref, catalogue});
  let original;
  const result = await reuseGeography({event, repo, api, token, directory, ...(inspect ? {inspect} : {}),
    loadProof: async options => {
      const proof = options.proof;
      const jobs = await githubPages(async route => (await api(route)).jobs,
        `/repos/${repo}/actions/runs/${proof.run_id}/attempts/${proof.run_attempt}/jobs`);
      const selected = originalFullRegressionJobs(jobs, {run: proof.run_id, attempt: proof.run_attempt, head: parent});
      if (!selected) return null;
      const loaded = await loadGeography(options);
      if (loaded) original = {head: parent, tree: source.object.tree.sha, run_id: proof.run_id,
        run_attempt: proof.run_attempt, jobs: selected};
      return loaded;
    }});
  need(result?.status === 'reused-original' && original && result.reviewed_head === head &&
    result.trusted_baseline === base && result.candidate_tree === current.object.tree.sha &&
    result.source?.run_id === original.run_id &&
    (result.source.current_run_attempt ?? result.source.run_attempt) === original.run_attempt,
    'regression-original-binding-unavailable');
  return {...result, program, original_computation: original, regression_reexecuted: false,
    package_rebuilt: false, fresh_tests: program.fresh_tests};
}

// Both queue phases invoke the same admission again against the actual current
// main/head. No current run is relabelled as the original computation producer.
export async function loadMetadataRegressionProof({api, repo, number, head, baseline, token, directory, inspect}) {
  const pr = await api(`/repos/${repo}/pulls/${number}`);
  need(pr.number === number && pr.head?.sha === head && pr.base?.sha === baseline && pr.state === 'open', 'current-pr-changed');
  return reusePRRegression({api, repo, token, directory, inspect,
    event: {repository: {full_name: repo}, pull_request: pr}});
}

// One queue process may inspect the same immutable operands during capacity
// planning and final validation. Cache only that immutable collector result;
// PR/issue/run/job/artifact authority and program admission are always reread.
export function createMetadataRegressionProofLoader({token, directory = process.cwd(),
  inspect = inspectUnchangedSelectedGeography, load = loadMetadataRegressionProof,
  acquire = createRoutingMetadataAcquisition}) {
  let saved;
  const immutableInspect = async (options, authority) => {
    const key = JSON.stringify([options.baseline, options.candidate, options.trusted, options.metadataPaths]);
    if (saved?.key === key) return structuredClone(saved.value);
    need(typeof authority.api === 'function', 'metadata-proof-api-unavailable');
    const acquisition = acquire({repo: directory, baseline: options.baseline, token,
      ...(options.limits ? {limits: options.limits} : {}),
      loadTree: (root, recursive = true) => authority.api(`/repos/${authority.repo}/git/trees/${root}${recursive ? '?recursive=1' : ''}`)});
    const value = await inspect({...options, acquisition});
    if (value?.status === 'unchanged-selected-inputs' && value.baseline_commit === options.baseline &&
      value.candidate_commit === options.candidate && value.trusted_reader_policy_commit === options.trusted &&
      value.candidate_code_executed === false && value.science_reexecuted === false &&
      Buffer.byteLength(JSON.stringify(value)) <= 32 * 1024 * 1024) saved = {key, value: structuredClone(value)};
    return value;
  };
  return options => load({...options, token, directory, inspect: input => immutableInspect(input, options)});
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  let result;
  try {
    const gates = JSON.parse(fs.readFileSync('pr-gates.json', 'utf8'));
    need(gates.status === 'checked' && gates.profile === 'full' && (gates.test_selection ?? 'complete') === 'complete',
      'complete-full-profile-required');
    const event = JSON.parse(fs.readFileSync(process.env.GITHUB_EVENT_PATH, 'utf8'));
    result = await reusePRRegression({event, repo: process.env.GITHUB_REPOSITORY,
      token: process.env.GH_TOKEN, api: githubAPI(process.env.GH_TOKEN)});
  } catch (error) {
    result = {version: 1, status: 'fresh-check-required', reason: /^[a-z][a-z0-9-]{1,80}$/.test(error?.message ?? '')
      ? error.message : 'predecessor-regression-proof-unavailable'};
  }
  fs.writeFileSync('regression-reuse.json', JSON.stringify(result, null, 2) + '\n');
  const reused = result.status === 'reused-original';
  fs.appendFileSync(process.env.GITHUB_OUTPUT, `reused=${reused}\n` + (reused ?
    `source_run=${result.original_computation.run_id}\nsource_attempt=${result.original_computation.run_attempt}\nsource_head=${result.original_computation.head}\n` : ''));
  console.log(JSON.stringify({status: result.status, reason: result.reason, original: result.original_computation,
    program: result.program, regression_reexecuted: result.regression_reexecuted, package_rebuilt: result.package_rebuilt}));
}
