import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {githubAPI, githubPages, workSpec, readClaim} from './issue-claim-contract.mjs';
import {validateIssuePRBody} from './check-handoff-scope.mjs';
import {checkPremergeEvidence} from './premerge-evidence.mjs';
import {gitBlobTransport} from './git-blob-transport.mjs';
import {requestAccounting, quotaDelay, completeReads} from './github-quota.mjs';

// Only trusted base code executes. Transport supplies tree-bound immutable
// bytes; PR identities, contracts, ownership and trees remain freshly read.
export async function checkPREvidence({event, api, verify = checkPremergeEvidence}) {
  const repo = event.repository?.full_name, scheduled = event.pull_request;
  if (!/^[-\w.]+\/[-\w.]+$/.test(repo ?? '') ||
      !Number.isSafeInteger(scheduled?.number) || scheduled.number < 1 ||
      !/^[a-f0-9]{40}$/.test(scheduled.head?.sha ?? '')) throw Error('Invalid evidence event');
  const pr = await api(`/repos/${repo}/pulls/${scheduled.number}`);
  if (pr.head.sha !== scheduled.head.sha) throw Error('PR head changed since this check was scheduled');
  const {github_issue} = validateIssuePRBody(pr.body ?? '');
  const [issue, comments, files] = await completeReads([
    api(`/repos/${repo}/issues/${github_issue}`), githubPages(api, `/repos/${repo}/issues/${github_issue}/comments`),
    githubPages(api, `/repos/${repo}/pulls/${pr.number}/files`)
  ]);
  const claim = readClaim(comments);
  if (!claim?.active) throw Error('Evidence check requires a canonical active reservation');
  const spec = workSpec(issue.body);
  return verify({api, repo, pr, issue, files, reservation: {...claim, owned_paths: spec.owned_paths}});
}

export async function runPREvidence({event, env = process.env, directory = process.cwd(),
  apiFactory = githubAPI, transportFactory = gitBlobTransport, verify}) {
  const repo = event.repository?.full_name;
  if (env.GITHUB_REPOSITORY !== repo || !/^[-\w.]+\/[-\w.]+$/.test(repo ?? ''))
    throw Error('Evidence event belongs to another repository');
  const accounting = requestAccounting('premerge-evidence'), downloads = [];
  const transport = transportFactory(apiFactory(env.GH_TOKEN, {onRequest: accounting.observe}),
    {repo, token: env.GH_TOKEN, directory, onFetch: row => downloads.push(row)});
  let report;
  try {
    report = await checkPREvidence({event, api: transport.api, verify});
  } catch (error) {
    const delay = quotaDelay(error);
    report = {status: 'incomplete-or-invalid', head_sha: event.pull_request?.head?.sha,
      reason: error.message, ...(error.github ? {api_error: error.github} : {}),
      retryable: delay !== null,
      ...(delay !== null ? {retry_at: new Date(Date.now() + delay).toISOString()} : {}),
      limits: ['Evidence was not fully verified; merge must wait']};
  } finally {
    transport.close();
  }
  return {...report, request_accounting: accounting.receipt(), immutable_transport: downloads};
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const event = JSON.parse(fs.readFileSync(process.env.GITHUB_EVENT_PATH, 'utf8'));
  const report = await runPREvidence({event});
  if (report.status === 'incomplete-or-invalid') process.exitCode = 1;
  fs.writeFileSync('evidence-check.json', JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report));
}
