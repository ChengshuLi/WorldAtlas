import {execFileSync} from 'node:child_process';
import {randomUUID} from 'node:crypto';
import {githubPages} from './issue-claim-contract.mjs';
import {readWorkerResult} from './worker-result.mjs';

const args = process.argv.slice(2), values = {};
for (let i = 0; i < args.length; i += 2) {
  if (!['--pr','--head'].includes(args[i]) || !args[i+1] || values[args[i]]) throw Error('Usage: node scripts/queue-pr-merge.mjs --pr N --head SHA');
  values[args[i]] = args[i+1];
}
if (!/^[1-9]\d*$/.test(values['--pr'] ?? '') || !/^[a-f0-9]{40}$/.test(values['--head'] ?? '')) throw Error('Supply the exact PR number and verified head SHA');
const repo = 'ChengshuLi/WorldAtlas', number = Number(values['--pr']), head = values['--head'];
const gh = args => execFileSync('gh', args, {encoding: 'utf8', maxBuffer: 16*1024*1024});
const api = route => JSON.parse(gh(['api', route]));
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
for (let attempt = 1; attempt <= 3; attempt++) {
  const pr = api(`/repos/${repo}/pulls/${number}`);
  if (pr.head.sha !== head) throw Error('Head changed; obtain a fresh review before queueing');
  const request_id = randomUUID(), title = `merge #${number} ${request_id}`;
  gh(['workflow','run','worker-merge.yml','--repo',repo,'--ref','main',
    '-f',`pr_number=${number}`,'-f',`expected_head=${head}`,'-f',`request_id=${request_id}`]);
  console.log(JSON.stringify({queued: true, request_id, attempt, reviewed_head: head}));
  const started = Date.now(); let run;
  while (Date.now() - started < 65*60*1000) {
    if (run?.id) {
      run = api(`/repos/${repo}/actions/runs/${run.id}`);
    } else {
      for (let page = 1; page <= 10; page++) {
        const runs = api(`/repos/${repo}/actions/workflows/worker-merge.yml/runs?event=workflow_dispatch&per_page=100&page=${page}`);
        run = runs.workflow_runs?.find(row => row.display_title === title);
        if (run || (runs.workflow_runs?.length ?? 0) < 100) break;
      }
    }
    if (run?.status === 'completed') break;
    await sleep(5000);
  }
  if (!run || run.status !== 'completed') throw Error(`Queue wait limit reached; inspect request ${request_id}; no merge claimed`);
  if (run.conclusion === 'cancelled' && attempt < 3) { await sleep(2000 + Math.random()*3000); continue; }
  const comments = await githubPages(api, `/repos/${repo}/issues/${number}/comments`);
  const result = readWorkerResult(comments, 'merge', request_id, number);
  if (!result || result.status === 'testing') throw Error(`No final merge confirmation for ${request_id}; inspect ${run.html_url}`);
  if (result.accepted) {
    const actual = api(`/repos/${repo}/pulls/${number}`);
    if (!actual.merged || actual.head.sha !== head || actual.merge_commit_sha !== result.merge_commit) throw Error('Merge receipt differs from actual PR state');
    console.log(JSON.stringify({...result, workflow_url: run.html_url})); break;
  }
  if (result.retryable && attempt < 3) { await sleep(2000 + Math.random()*3000); continue; }
  console.log(JSON.stringify({...result, workflow_url: run.html_url})); process.exitCode = 2; break;
}
