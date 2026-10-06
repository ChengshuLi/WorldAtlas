import {githubPages} from './issue-claim-contract.mjs';
import {queueRows} from './merge-scheduler.mjs';
import {readWorkerResult} from './worker-result.mjs';

const MIN_POLL = 60_000, MAX_POLL = 300_000;

// Observation is read-only. Submission has its own single, non-retried boundary.
// All reads share a deadline and rate-limit pause, including pagination and the
// final authoritative merge check. A missing response never proves completion.
export async function runMergeQueueClient({api, submit, repo, number, head,
  requestId, observeOnly = false, resuming = false, now = Date.now,
  sleep = ms => new Promise(resolve => setTimeout(resolve, ms)),
  random = Math.random, timeoutMs = 65 * 60_000, progress = () => {}}) {
  const started = now(), deadline = started + timeoutMs;
  let readRequests = 0;
  const finish = result => {
    progress({status: 'observation-ended', request_id: requestId,
      read_requests: readRequests, elapsed_ms: now() - started});
    return result;
  };
  const pending = () => finish({status: 'pending', request_id: requestId,
    reviewed_head: head, reason: 'Observation ended; inspect the same durable request. No merge claimed.'});
  let expired = false;
  let secondaryRetries = 0;
  const read = async route => {
    let serviceRetries = 0;
    for (;;) {
      if (now() >= deadline) { expired = true; return undefined; }
      try {
        readRequests++;
        const value = await api(route, {timeoutMs: Math.max(1, Math.min(20_000, deadline - now()))});
        if (now() >= deadline) { expired = true; return undefined; }
        return value;
      }
      catch (error) {
        if (now() >= deadline) { expired = true; return undefined; }
        const detail = error.github ?? {};
        const limited = detail.http_status === 429 ||
          (detail.http_status === 403 && (Number(detail.rate_remaining) === 0 || detail.retry_after !== undefined || detail.secondary_limit));
        let delay;
        if (limited) {
          const reset = Number(detail.rate_reset) * 1000;
          const retry = Number(detail.retry_after) * 1000;
          const primary = Number(detail.rate_remaining) === 0;
          if (!primary && ++secondaryRetries > 3)
            throw Error('Secondary API rate limit persisted after three bounded retries; inspect the same request later. No merge claimed.');
          delay = Math.max(primary ? 60_000 : 60_000 * 2 ** (secondaryRetries - 1),
            primary && Number.isFinite(reset) ? reset - now() + 2000 : 0,
            Number.isFinite(retry) ? retry : 0);
          progress({status: 'rate-limited', request_id: requestId, retry_at: new Date(now() + delay).toISOString()});
        } else if (detail.http_status >= 500 && detail.http_status <= 599 && serviceRetries++ < 2) {
          delay = 60_000 * serviceRetries;
        } else throw error;
        if (now() + delay >= deadline) { expired = true; return undefined; }
        await sleep(delay);
      }
    }
  };
  const pages = route => githubPages(read, route);
  const title = `queue #${number} ${requestId}`;
  let registration, registrationSettled = false, registered = false;
  let submissionAttempted = observeOnly || resuming, interval = MIN_POLL;
  const actual = await read(`/repos/${repo}/pulls/${number}`);
  if (expired) return pending();
  if (actual.head?.sha !== head) throw Error('Head changed; obtain a fresh review before queueing');

  while (now() < deadline) {
    let comments;
    try { comments = await pages(`/repos/${repo}/issues/${number}/comments`); }
    catch (error) { if (expired) return pending(); throw error; }
    if (expired) return pending();
    const result = readWorkerResult(comments, 'merge', requestId, number);
    if (result && result.status !== 'testing' && (result.accepted || !result.retryable)) {
      if (!result.accepted) return finish(result);
      if (result.status !== 'merged' || !/^[a-f0-9]{40}$/.test(result.merge_commit ?? '') ||
        (result.expected_head !== undefined && result.expected_head !== head) ||
        (result.reviewed_head !== undefined && result.reviewed_head !== head))
        throw Error('Malformed or mismatched accepted merge receipt');
      const merged = await read(`/repos/${repo}/pulls/${number}`);
      if (expired) return pending();
      if (!merged.merged || merged.head?.sha !== head || merged.merge_commit_sha !== result.merge_commit)
        throw Error('Merge receipt differs from actual PR state');
      return finish(result);
    }
    const rows = queueRows(comments);
    if (!resuming && !observeOnly) {
      const other = rows.find(row => {
        if (row.kind !== 'request' || row.request_id === requestId || row.expected_head !== head || row.pr_number !== number) return false;
        const previous = readWorkerResult(comments, 'merge', row.request_id, number);
        return !previous || previous.status === 'testing' || previous.retryable;
      });
      if (other) throw Error(`Existing request ${other.request_id} already owns this reviewed head; observe that identity instead of submitting again`);
    }
    const existing = rows.find(row => row.kind === 'request' && row.request_id === requestId);
    if (existing && (existing.pr_number !== number || existing.expected_head !== head))
      throw Error('Request identity cannot change head or PR');
    if (existing) {
      if (!registered) progress({status: 'registered', request_id: requestId, reviewed_head: head});
      registered = true;
    }
    if (!registered && !registrationSettled) {
      if (registration?.id) registration = await read(`/repos/${repo}/actions/runs/${registration.id}`);
      else if (submissionAttempted || resuming) {
        for (let page = 1; page <= 10; page++) {
          const response = await read(`/repos/${repo}/actions/workflows/merge-scheduler.yml/runs?event=workflow_dispatch&per_page=100&page=${page}`);
          if (expired) return pending();
          if (!Array.isArray(response?.workflow_runs)) throw Error('Invalid registration workflow inventory');
          registration = response.workflow_runs.find(row => row.display_title === title);
          if (registration || response.workflow_runs.length < 100) break;
          if (page === 10) throw Error('Incomplete registration inventory; do not resubmit an uncertain request');
        }
      }
      if (expired) return pending();
      if (registration?.status === 'completed') {
        if (registration.conclusion !== 'success')
          throw Error(`Registration did not complete (${registration.conclusion}); inspect the same request ${requestId}; no automatic resubmission`);
        registrationSettled = true;
      }
    }
    if (!registered && !submissionAttempted && !registration) {
      if (actual.state !== 'open') throw Error('Queue request needs an open PR; no accepted merge receipt found');
      submissionAttempted = true;
      progress({status: 'submitting', request_id: requestId, reviewed_head: head});
      // Do not retry an uncertain write. Its printed identity permits inspection.
      await submit({number, head, requestId, timeoutMs: Math.max(1, Math.min(20_000, deadline - now()))});
      progress({status: 'submitted', request_id: requestId, reviewed_head: head});
    }
    const delay = Math.min(MAX_POLL, Math.round(interval * (1 + Math.max(0, Math.min(1, random())) * 0.1)));
    if (now() + delay >= deadline) return pending();
    await sleep(delay);
    interval = Math.min(MAX_POLL, interval * 2);
  }
  return pending();
}
