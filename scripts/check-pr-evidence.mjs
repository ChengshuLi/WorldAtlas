import fs from 'node:fs';
import {githubAPI, githubPages, workSpec, readClaim} from './issue-claim-contract.mjs';
import {validateIssuePRBody} from './check-handoff-scope.mjs';
import {checkPremergeEvidence} from './premerge-evidence.mjs';

const event = JSON.parse(fs.readFileSync(process.env.GITHUB_EVENT_PATH, 'utf8'));
const repo = event.repository.full_name, api = githubAPI(process.env.GH_TOKEN);
const pr = await api(`/repos/${repo}/pulls/${event.pull_request.number}`);
if (pr.head.sha !== event.pull_request.head.sha) throw Error('PR head changed since this check was scheduled');
const {github_issue} = validateIssuePRBody(pr.body ?? '');
const [issue, comments, files] = await Promise.all([
  api(`/repos/${repo}/issues/${github_issue}`), githubPages(api, `/repos/${repo}/issues/${github_issue}/comments`),
  githubPages(api, `/repos/${repo}/pulls/${pr.number}/files`)
]);
const claim = readClaim(comments);
if (!claim?.active) throw Error('Evidence check requires a canonical active reservation');
const spec = workSpec(issue.body);
let report;
try {
  report = await checkPremergeEvidence({api, repo, pr, issue, files,
    reservation: {...claim, owned_paths: spec.owned_paths}});
} catch (error) {
  report = {status: 'incomplete-or-invalid', head_sha: pr.head.sha, reason: error.message,
    limits: ['Evidence was not fully verified; merge must wait']};
  process.exitCode = 1;
}
fs.writeFileSync('evidence-check.json', JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report));
