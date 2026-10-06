import {githubPages} from './issue-claim-contract.mjs';
import {readWorkerResult, renderWorkerResult} from './worker-result.mjs';

const marker = 'worldatlas-merge-queue:v1';
export const MAX_ATTEMPTS = 3;
export function queueBody(row) {
  return `**Merge queue:** ${row.kind}\n\n<!-- ${marker}\n${JSON.stringify(row).replaceAll('<', '\\u003c')}\n-->`;
}
export function queueRows(comments) {
  return comments.filter(c => c.user?.login === 'github-actions[bot]').flatMap(c => {
    const match = new RegExp(`<!-- ${marker}\\n([\\s\\S]*?)\\n-->`).exec(c.body ?? '');
    if (!match) return [];
    let row; try { row = JSON.parse(match[1]); } catch { return []; }
    if (!['request', 'dispatch'].includes(row.kind) || !Number.isSafeInteger(row.pr_number) ||
        !/^[a-f0-9]{40}$/.test(row.expected_head ?? '') || !/^[-a-zA-Z0-9]{16,100}$/.test(row.request_id ?? '')) return [];
    return [{...row, comment_id: c.id, created_at: c.created_at}];
  }).sort((a, b) => a.comment_id - b.comment_id);
}
export async function loadQueue(api, repo) {
  // Open PRs are the only eligible merge targets. All closed PR comments remain
  // durable history; closing a PR withdraws its pending request without merging.
  const prs = await githubPages(api, `/repos/${repo}/pulls?state=open`);
  const queue = [];
  for (const pr of prs) {
    const comments = await githubPages(api, `/repos/${repo}/issues/${pr.number}/comments`);
    const rows = queueRows(comments), seen = new Set();
    for (const request of rows.filter(row => row.kind === 'request')) {
      if (seen.has(request.request_id)) continue;
      seen.add(request.request_id);
      const dispatches = rows.filter(row => row.kind === 'dispatch' && row.request_id === request.request_id);
      const observed = readWorkerResult(comments, 'merge', request.request_id, pr.number);
      const result = observed?.queue_attempt && observed.queue_attempt !== dispatches.at(-1)?.attempt ? null : observed;
      if (result && result.status !== 'testing' && (result.accepted || !result.retryable)) continue;
      queue.push({request, pr, result, dispatches});
    }
  }
  return queue.sort((a, b) => a.request.comment_id - b.request.comment_id);
}
export async function workerRuns(api, repo) {
  const all = [];
  // Complete recent attempts establish cancellation/failure. Live runs of any
  // age are fetched separately so pagination/observation limits cannot restart them.
  for (const status of ['queued', 'in_progress', 'waiting', 'pending', 'requested']) {
    for (let page = 1; page <= 100; page++) {
      const response = await api(`/repos/${repo}/actions/workflows/worker-merge.yml/runs?status=${status}&per_page=100&page=${page}`);
      if (!Array.isArray(response.workflow_runs)) throw Error('Invalid workflow run inventory');
      all.push(...response.workflow_runs);
      if (response.workflow_runs.length < 100) break;
      if (page === 100) throw Error('Incomplete live workflow inventory');
    }
  }
  return [...new Map(all.map(row => [row.id, row])).values()];
}
export async function registerRequest({api, repo, request}) {
  const pr = await api(`/repos/${repo}/pulls/${request.pr_number}`);
  if (pr.state !== 'open' || pr.head.sha !== request.expected_head) throw Error('Queue request needs the current open reviewed head');
  const comments = await githubPages(api, `/repos/${repo}/issues/${pr.number}/comments`);
  const existing = queueRows(comments).find(row => row.kind === 'request' && row.request_id === request.request_id);
  if (existing) {
    if (existing.expected_head !== request.expected_head || existing.pr_number !== request.pr_number) throw Error('Request identity cannot change head or PR');
    return existing;
  }
  return api(`/repos/${repo}/issues/${pr.number}/comments`, 'POST', {body: queueBody({...request, kind: 'request'})});
}
export async function scheduleNext({api, repo, now = Date.now()}) {
  // This routine runs only in the short serialized scheduler job. GitHub may
  // coalesce pending scheduler ticks; requests are separate durable comments.
  const live = await workerRuns(api, repo);
  if (live.length) return {status: 'live', run_ids: live.map(run => run.id)};
  const entry = (await loadQueue(api, repo))[0];
  if (!entry) return {status: 'empty'};
  const {request, pr, dispatches} = entry;
  const finish = async reason => {
    const result = {accepted: false, status: 'not-merged', retryable: false, ...request, reason};
    await api(`/repos/${repo}/issues/${pr.number}/comments`, 'POST', {body: renderWorkerResult('merge', result)});
    return result;
  };
  if (pr.head.sha !== request.expected_head) return finish('Head changed; obtain a fresh review and submit a new request');
  const last = dispatches.at(-1);
  if (last) {
    // The title uniquely binds an execution to the durable attempt. A dispatch
    // that returned an ambiguous failure is given time to appear before recovery.
    const response = await api(`/repos/${repo}/actions/workflows/worker-merge.yml/runs?event=workflow_dispatch&per_page=100`);
    const run = response.workflow_runs?.find(row => row.display_title === executionTitle(request, last.attempt));
    if (run && run.status !== 'completed') return {status: 'live', run_ids: [run.id]};
    if (!run && now - Date.parse(last.dispatched_at) < 120000) return {status: 'awaiting-dispatch', request_id: request.request_id};
    if (run) {
      // Preserve each cancelled/failed attempt even if its final job never ran.
      await api(`/repos/${repo}/issues/${pr.number}/comments`, 'POST', {body: queueBody({...request, kind: 'dispatch',
        attempt: last.attempt, dispatched_at: last.dispatched_at, observed_run_id: run.id, conclusion: run.conclusion})});
    }
  }
  const attempt = (last?.attempt ?? 0) + 1;
  if (attempt > MAX_ATTEMPTS) return finish('Queue recovery exhausted three terminal/absent executions; inspect durable attempt receipts and resubmit unchanged reviewed head');
  await api(`/repos/${repo}/issues/${pr.number}/comments`, 'POST', {body: queueBody({...request, kind: 'dispatch', attempt, dispatched_at: new Date(now).toISOString()})});
  await api(`/repos/${repo}/actions/workflows/worker-merge.yml/dispatches`, 'POST', {ref: 'main', inputs: {
    pr_number: String(pr.number), expected_head: request.expected_head, request_id: request.request_id, queue_attempt: String(attempt)}});
  return {status: 'dispatched', request_id: request.request_id, attempt};
}
export function executionTitle(request, attempt) { return `merge #${request.pr_number} ${request.request_id} attempt ${attempt}`; }
export async function assertAdmission({api, repo, request, attempt, runId}) {
  const queue = await loadQueue(api, repo), first = queue[0];
  if (!first || first.request.request_id !== request.request_id || first.request.pr_number !== request.pr_number ||
      first.request.expected_head !== request.expected_head || first.dispatches.at(-1)?.attempt !== attempt) throw Error('Request lacks current FIFO admission; normal scheduler will recover');
  const live = await workerRuns(api, repo);
  if (live.some(run => run.id !== Number(runId) && run.status !== 'queued' && run.status !== 'pending')) throw Error('Another live integration must settle before preparation');
}
