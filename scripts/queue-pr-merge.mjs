import {execFileSync} from 'node:child_process';
import {randomUUID} from 'node:crypto';
import {githubPages} from './issue-claim-contract.mjs';
import {readWorkerResult} from './worker-result.mjs';
import {cleanupCompletedWorkspace} from './local-workspace.mjs';

const args = process.argv.slice(2), values = {};
for (let i = 0; i < args.length; i += 2) {
  if (!['--pr','--head','--request-id'].includes(args[i]) || !args[i+1] || values[args[i]]) throw Error('Usage: node scripts/queue-pr-merge.mjs --pr N --head SHA');
  values[args[i]] = args[i+1];
}
if (!/^[1-9]\d*$/.test(values['--pr'] ?? '') || !/^[a-f0-9]{40}$/.test(values['--head'] ?? '')) throw Error('Supply the exact PR number and verified head SHA');
const repo = 'ChengshuLi/WorldAtlas', number = Number(values['--pr']), head = values['--head'];
const gh = args => execFileSync('gh', args, {encoding: 'utf8', maxBuffer: 16*1024*1024});
const api = route => JSON.parse(gh(['api', route]));
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const request_id = values['--request-id'] ?? randomUUID();
if (!/^[-a-zA-Z0-9]{16,100}$/.test(request_id)) throw Error('Invalid stable request ID');
const pr = api(`/repos/${repo}/pulls/${number}`);
if (pr.head.sha !== head) throw Error('Head changed; obtain a fresh review before queueing');
const title = `queue #${number} ${request_id}`;
// Idempotent registration keeps original FIFO position across retries/resumes.
gh(['workflow','run','merge-scheduler.yml','--repo',repo,'--ref','main',
  '-f',`pr_number=${number}`,'-f',`expected_head=${head}`,'-f',`request_id=${request_id}`]);
console.log(JSON.stringify({queued: true, request_id, reviewed_head: head}));
const started = Date.now(); let registration;
while (Date.now() - started < 65*60*1000) {
  const comments = await githubPages(api, `/repos/${repo}/issues/${number}/comments`);
  const result = readWorkerResult(comments, 'merge', request_id, number);
  if (result && result.status !== 'testing' && (result.accepted || !result.retryable)) {
    if (result.accepted) {
      const actual = api(`/repos/${repo}/pulls/${number}`);
      if (!actual.merged || actual.head.sha !== head || actual.merge_commit_sha !== result.merge_commit) throw Error('Merge receipt differs from actual PR state');
      console.log(JSON.stringify({...result, local_cleanup: cleanupCompletedWorkspace(process.cwd(), head)}));
    } else { console.log(JSON.stringify(result)); process.exitCode = 2; }
    break;
  }
  const actual = api(`/repos/${repo}/pulls/${number}`);
  if (actual.head.sha !== head || actual.state === 'closed') throw Error(`PR changed/closed; inspect request ${request_id}; no merge claimed`);
  if (registration?.id) registration = api(`/repos/${repo}/actions/runs/${registration.id}`);
  else {
    for (let page = 1; page <= 10; page++) {
      const response = api(`/repos/${repo}/actions/workflows/merge-scheduler.yml/runs?event=workflow_dispatch&per_page=100&page=${page}`);
      registration = response.workflow_runs?.find(row => row.display_title === title);
      if (registration || (response.workflow_runs?.length ?? 0) < 100) break;
    }
  }
  if (registration?.status === 'completed' && registration.conclusion !== 'success') {
    throw Error(`Registration did not complete (${registration.conclusion}); resume the same request ${request_id}, inspect ${registration.html_url}`);
  }
  await sleep(5000);
}
if (Date.now() - started >= 65*60*1000) throw Error(`Queue observation limit reached; durable request ${request_id} remains queued/live; resume with --request-id ${request_id}; no merge claimed`);
