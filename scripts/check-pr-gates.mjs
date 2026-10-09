import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {performance} from 'node:perf_hooks';
import {githubAPI, githubPages, linkedPulls, verifyClaimForPR} from './issue-claim-contract.mjs';
import {validateIssuePRBody} from './check-handoff-scope.mjs';
import {reviewContractBinding} from './premerge-evidence.mjs';
import {checkPREvidence} from './check-pr-evidence.mjs';
import {checkLinkedIssue} from './check-linked-github-issue.mjs';
import {selectIntegrationProfile} from './check-integration-profile.mjs';
import {deploymentBudgetProfile} from './classify-deployment-budget.mjs';
import {gitBlobTransport} from './git-blob-transport.mjs';
import {completeReads, copyAPIFeatures, quotaDelay, requestAccounting} from './github-quota.mjs';
import {loadJobDeadline, HTTP_ATTEMPT_MS} from './job-deadline.mjs';

export async function readPRGateWorkflow({api, event, env}) {
  const repo = env.GITHUB_REPOSITORY, workflowPath = '.github/workflows/merge-integration-checks.yml';
  if (env.GITHUB_WORKFLOW_REF !== `${repo}/${workflowPath}@refs/pull/${event.pull_request?.number}/merge` ||
      !/^[a-f0-9]{40}$/.test(env.GITHUB_WORKFLOW_SHA ?? '')) throw Error('Missing executing PR workflow authority');
  const file = await api(`/repos/${repo}/contents/${workflowPath}?ref=${env.GITHUB_WORKFLOW_SHA}`);
  if (file?.type !== 'file' || file.path !== workflowPath || file.encoding !== 'base64' ||
      !/^[a-f0-9]{40}$/.test(file.sha ?? '') || !Number.isSafeInteger(file.size) ||
      file.size <= 0 || file.size > 128 * 1024 || typeof file.content !== 'string') throw Error('Executing PR workflow unavailable');
  const bytes = Buffer.from(file.content, 'base64');
  if (bytes.length !== file.size || createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex') !== file.sha)
    throw Error('Executing PR workflow bytes changed');
  return bytes.toString('utf8');
}

// Compose the actual trusted gates with one client. No prior successful verdict
// is reused: each phase starts fresh and ends with authenticated rechecks.
export async function checkPRGates({event, repo, token, api, now = Date.now, phase = 'all'}) {
  if (!['all', 'metadata', 'evidence'].includes(phase)) throw Error('Invalid PR gate phase');
  const scheduled = event.pull_request, root = `/repos/${repo}`;
  if (event.repository?.full_name !== repo || !/^[-\w.]+\/[-\w.]+$/.test(repo ?? '') ||
      !Number.isSafeInteger(scheduled?.number) || scheduled.number < 1 ||
      !/^[a-f0-9]{40}$/.test(scheduled.head?.sha ?? '') || !token) throw Error('Invalid trusted PR gate context');
  // One coherent authority pass is shared by the selectors. These are freshly
  // fetched records, not prior verdicts. The final reconciliation below bypasses
  // this pass and reauthenticates every mutable authority against GitHub.
  const captured = new Map(); let captureBytes = 0;
  const read = async route => {
    const eligible = route.startsWith(root + '/pulls/') || route.startsWith(root + '/issues/') ||
      route.startsWith(root + '/contents/.github/package-inputs.json?ref=');
    if (!eligible) return api(route);
    if (captured.has(route)) return JSON.parse(await captured.get(route));
    const pending = api(route).then(value => JSON.stringify(value));
    captured.set(route, pending);
    try {
      const text = await pending, bytes = Buffer.byteLength(text);
      if (captured.size > 64 || captureBytes + bytes > 16 * 1024 * 1024) captured.delete(route);
      else captureBytes += bytes;
      return JSON.parse(text);
    } catch (error) {captured.delete(route); throw error;}
  };
  // Sharing fresh authority records must preserve the authenticated immutable
  // transport and its admission controls across the composed evidence path.
  copyAPIFeatures(read, api);
  const prRoute = `${root}/pulls/${scheduled.number}`;
  const current = await read(prRoute);
  const assertHead = pr => {
    if (pr.number !== scheduled.number || pr.state !== 'open' || pr.head?.sha !== scheduled.head.sha ||
        pr.head?.ref !== scheduled.head.ref || pr.head?.repo?.full_name !== repo ||
        pr.base?.repo?.full_name !== repo || pr.base?.ref !== 'main') throw Error('PR identity changed during trusted gates');
  };
  assertHead(current);
  const {github_issue} = validateIssuePRBody(current.body ?? '');
  const issueRoute = `${root}/issues/${github_issue}`;
  const [issue, comments, prs] = await completeReads([read(issueRoute),
    githubPages(read, `${issueRoute}/comments`), linkedPulls(read, repo, github_issue)]);
  if (issue.number !== github_issue) throw Error('Issue response belongs to another contract');
  const holder = verifyClaimForPR({branch: current.head.ref, issue, comments, prs, now: now()});
  const binding = reviewContractBinding(issue, current);
  // Use the current authoritative body, not a possibly older edited-event body.
  const authoritativeEvent = {...event, pull_request: {...scheduled, body: current.body}};
  const evidence = phase === 'metadata' ? undefined : await checkPREvidence({event: authoritativeEvent, api: read});
  if (evidence && (evidence.head_sha !== scheduled.head.sha || evidence.status === 'incomplete-or-invalid'))
    throw Error('Evidence verification did not bind the scheduled head');
  const linked = phase === 'evidence' ? undefined : await checkLinkedIssue({branch: current.head.ref, event: authoritativeEvent,
    token, api: read, checkClaim: true});
  const regression = phase === 'evidence' ? undefined : await selectIntegrationProfile({event: authoritativeEvent, repo, api: read, now: now()});
  const packageProfile = phase === 'evidence' ? undefined : await deploymentBudgetProfile({event: authoritativeEvent,
    eventName: 'pull_request', repository: repo, api: read});
  if (packageProfile?.blocked) throw Object.assign(Error('Package classification deferred for quota'),
    {blocked: packageProfile, ...(packageProfile.api_error ? {github: packageProfile.api_error} : {})});

  // Reconcile changed contracts/ownership after the byte checks. Renewals and
  // ordinary progress comments are allowed; different holders or scope are not.
  const [settled, finalIssue, finalComments, finalPRs] = await completeReads([
    api(prRoute), api(issueRoute), githubPages(api, `${issueRoute}/comments`), linkedPulls(api, repo, github_issue)]);
  assertHead(settled);
  if (settled.base?.sha !== current.base?.sha || finalIssue.number !== github_issue ||
      JSON.stringify(reviewContractBinding(finalIssue, settled)) !== JSON.stringify(binding))
    throw Error('PR base, acceptance contract or disposition changed during trusted gates');
  const finalHolder = verifyClaimForPR({branch: settled.head.ref, issue: finalIssue,
    comments: finalComments, prs: finalPRs, now: now()});
  if (JSON.stringify(finalHolder) !== JSON.stringify(holder)) throw Error('Canonical ownership changed during trusted gates');
  return {status: 'checked', phase, head_sha: scheduled.head.sha, trusted_base: scheduled.base?.sha,
    github_issue, pr_body: current.body ?? '', issue_binding: binding, evidence, linked,
    ...(regression ? {profile: regression.profile, shards: regression.shards,
      owned_paths: linked.owned_paths ?? [], package: packageProfile} : {})};
}

export async function runPRGates({event, env = process.env, directory = process.cwd(),
  apiFactory = githubAPI, transportFactory = gitBlobTransport, wallNow = Date.now,
  monotonicNow = () => performance.now(), phase = 'all'}) {
  const accounting = requestAccounting('pr-gates'), downloads = [], started = monotonicNow();
  let result, transport, deadline;
  const hosted = env.GITHUB_ACTIONS === 'true';
  // Only finite, no-retry metadata reads can precede authenticated job timing.
  const bootstrapRemaining = () => 2 * HTTP_ATTEMPT_MS + 1000 - (monotonicNow() - started);
  const api = apiFactory(env.GH_TOKEN, {onRequest: accounting.observe,
    deadlineRemaining: () => deadline ? deadline.remaining() : hosted ? bootstrapRemaining() : 8 * 60 * 1000 - (monotonicNow() - started)});
  try {
    if (hosted) {
      const workflow = await readPRGateWorkflow({api, event, env});
      deadline = await loadJobDeadline({api, repo: env.GITHUB_REPOSITORY, phase: phase === 'evidence' ? 'evidence' : 'profile', workflow, env, wallNow, monotonicNow});
    }
    if (phase !== 'metadata') transport = transportFactory(api, {repo: env.GITHUB_REPOSITORY, token: env.GH_TOKEN,
      directory, onFetch: row => downloads.push(row)});
    result = await checkPRGates({event, repo: env.GITHUB_REPOSITORY, token: env.GH_TOKEN, api: transport?.api ?? api, now: wallNow, phase});
  }
  catch (error) {
    const delay = quotaDelay(error, wallNow());
    result = {status: 'incomplete-or-invalid', head_sha: event.pull_request?.head?.sha,
      reason: error.message, ...(error.github ? {api_error: error.github} : {}),
      ...(error.blocked ? {package: error.blocked} : {}), retryable: delay !== null || Boolean(error.blocked),
      ...(delay !== null ? {retry_at: new Date(wallNow() + delay).toISOString()} : {}),
      limits: ['Trusted metadata/evidence gates remain unverified; no success or applicability skip is claimed']};
  } finally { transport?.close(); }
  const {remaining, ...job} = deadline ?? {};
  return {...result, ...(deadline ? {job_deadline: job} : {}), elapsed_ms: Math.floor(monotonicNow() - started),
    request_accounting: accounting.receipt(), immutable_transport: downloads};
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const event = JSON.parse(fs.readFileSync(process.env.GITHUB_EVENT_PATH, 'utf8'));
  const phase = process.env.PR_GATE_PHASE ?? 'metadata';
  const result = await runPRGates({event, phase});
  fs.writeFileSync('pr-gates.json', JSON.stringify(result, null, 2) + '\n');
  console.log(JSON.stringify(result));
  if (result.status !== 'checked') process.exitCode = 1;
  else if (phase !== 'evidence') fs.appendFileSync(process.env.GITHUB_OUTPUT,
    `profile=${result.profile}\nshards=${JSON.stringify(result.shards)}\nowned_paths=${JSON.stringify(result.owned_paths)}\npr_body=${JSON.stringify(result.pr_body)}\nfull=${result.package.full}\nblocked=false\n`);
}
