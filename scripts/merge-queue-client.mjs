import {githubPages} from './issue-claim-contract.mjs';
import {queueRows} from './merge-scheduler.mjs';
import {readWorkerResult, verifyAcceptedMergeResult} from './worker-result.mjs';
import {execFileSync} from 'node:child_process';
import {conditionalSnapshots} from './github-snapshots.mjs';

const MIN_POLL = 60_000, MAX_POLL = 300_000;
const RECOVERY_RESERVE = 16;
const retryDelay = (value, reference) => {
  if (/^\d+$/.test(value ?? '') && Number.isSafeInteger(Number(value) * 1000)) return Number(value) * 1000;
  const date = Date.parse(value);
  return Number.isFinite(date) ? Math.max(0, date - reference) : 0;
};

// gh retains its existing authentication. Snapshots live only in this process,
// are bounded, and never authorize a result without a fresh conditional GET.
export function mergeQueueAPI({execute = execFileSync, snapshotOptions} = {}) {
  const snapshots = conditionalSnapshots(snapshotOptions);
  return (route, {timeoutMs = 20_000, onResponse = () => {}} = {}) => {
    if (!/^\/repos\/[-\w.]+\/[-\w.]+\//.test(route) || !Number.isFinite(timeoutMs) || timeoutMs <= 0)
      throw Error('Invalid bounded queue read');
    const snapshot = snapshots.get(route), args = ['api', '--include'];
    if (snapshot) args.push('-H', `If-None-Match: ${snapshot.etag}`);
    args.push(route);
    let output, failure;
    try { output = execute('gh', args, {encoding: 'utf8', maxBuffer: 16 * 1024 * 1024,
      timeout: Math.min(20_000, timeoutMs), killSignal: 'SIGKILL', stdio: ['ignore', 'pipe', 'pipe']}); }
    catch (error) { output = String(error.stdout ?? ''); failure = error; }
    const separator = output.search(/\r?\n\r?\n/);
    const headers = output.startsWith('HTTP/') && separator >= 0 ? output.slice(0, separator) : '';
    const field = name => new RegExp(`^${name}:\\s*([^\\r\\n]*)`, 'im').exec(headers)?.[1]?.trim();
    const integer = name => /^\d+$/.test(field(name) ?? '') && Number.isSafeInteger(Number(field(name)))
      ? Number(field(name)) : undefined;
    const status = Number(/^HTTP\/\S+\s+(\d+)/.exec(headers)?.[1]);
    const body = headers ? output.slice(separator).trim() : output;
    // gh reports a complete 304 with exit 1. Timeouts/signals must still fail,
    // even if they happened after writing partial response headers.
    if ((failure && !(status === 304 && failure.status === 1 && !failure.signal)) || ![200, 304].includes(status)) {
      let secondaryLimit = false;
      try { secondaryLimit = /secondary rate limit/i.test(JSON.parse(body).message ?? ''); } catch { /* HTTP status remains authority. */ }
      const error = Error(`GitHub read failed for ${route}; no merge claimed`);
      error.github = {http_status: status, rate_remaining: field('x-ratelimit-remaining'),
        rate_reset: field('x-ratelimit-reset'), retry_after: field('retry-after'), secondary_limit: secondaryLimit,
        server_date_ms: Date.parse(field('date'))};
      throw error;
    }
    const value = status === 304 ? snapshots.revalidated(snapshot, field('etag') ?? null) : JSON.parse(body);
    if (status === 200) {
      snapshots.invalidate(route);
      if (!/\bno-store\b/i.test(field('cache-control') ?? '')) snapshots.retain(route, field('etag'), value);
    }
    const maxAge = /(?:^|,)\s*max-age=(\d+)\s*(?:,|$)/i.exec(field('cache-control') ?? '')?.[1];
    const milliseconds = seconds => Number.isSafeInteger(Number(seconds)) && Number(seconds) >= 0
      && Number.isSafeInteger(Number(seconds) * 1000) ? Number(seconds) * 1000 : 0;
    onResponse({http_status: status, conditional: Boolean(snapshot), cacheable: Boolean(snapshots.get(route)),
      poll_ms: milliseconds(integer('x-poll-interval')), cache_ms: milliseconds(maxAge),
      retry_after: field('retry-after'), server_date_ms: Date.parse(field('date')),
      capacity: {limit: integer('x-ratelimit-limit'), remaining: integer('x-ratelimit-remaining'),
        reset: integer('x-ratelimit-reset'), resource: field('x-ratelimit-resource')}});
    return value;
  };
}

// Observation is read-only. Submission has its own single, non-retried boundary.
// All reads share a deadline and rate-limit pause, including pagination and the
// final authoritative merge check. A missing response never proves completion.
export async function runMergeQueueClient({api, submit, repo, number, head,
  requestId, observeOnly = false, resuming = false, now = () => performance.now(), wallNow = Date.now,
  sleep = ms => new Promise(resolve => setTimeout(resolve, ms)),
  random = Math.random, timeoutMs = 65 * 60_000, progress = () => {}}) {
  const started = now(), deadline = started + timeoutMs, startedAt = new Date(wallNow()).toISOString();
  let readRequests = 0, readMs = 0, sleepMs = 0, capacity, resetAt = 0, commentHints = [];
  let retryAt = 0;
  const pollAt = new Map();
  let receiptAt, reconciledAt;
  const statuses = {};
  const emit = value => progress({request_id: requestId, elapsed_ms: now() - started,
    observed_at: new Date(wallNow()).toISOString(), ...value});
  const wait = async (delay, reason) => {
    const before = now();
    emit({status: 'waiting', reason, scheduled_ms: delay});
    await sleep(delay);
    sleepMs += now() - before;
    emit({status: 'wait-ended', reason, scheduled_ms: delay, duration_ms: now() - before});
  };
  const finish = result => {
    const observation = {started_at: startedAt, completed_at: new Date(wallNow()).toISOString(),
      elapsed_ms: now() - started, read_requests: readRequests, read_ms: readMs, sleep_ms: sleepMs,
      http_status_counts: {...statuses}, duration_clock: 'monotonic',
      ...(receiptAt !== undefined ? {receipt_observed_elapsed_ms: receiptAt} : {}),
      ...(reconciledAt !== undefined ? {merge_reconciled_elapsed_ms: reconciledAt} : {})};
    emit({status: 'observation-ended', ...observation});
    // Automatic delivery retains this bounded summary with its ordinary result.
    return {...result, observation};
  };
  const pending = () => finish({status: 'pending', request_id: requestId,
    reviewed_head: head, reason: 'Observation ended; inspect the same durable request. No merge claimed.'});
  let expired = false;
  let secondaryRetries = 0;
  const read = async route => {
    let serviceRetries = 0;
    for (;;) {
      if (now() >= deadline) { expired = true; return undefined; }
      // Even a successful response can exhaust the shared primary allowance.
      // A cached page might change next time; 304 is not a quota reservation.
      const quotaAt = capacity?.remaining <= RECOVERY_RESERVE ? resetAt : 0;
      const notBefore = Math.max(quotaAt, retryAt, pollAt.get(route) ?? 0);
      if (notBefore > now()) {
        if (notBefore >= deadline) { expired = true; return undefined; }
        await wait(notBefore - now(), notBefore === quotaAt ? 'primary-capacity' : 'provider-guidance');
        if (capacity?.remaining <= RECOVERY_RESERVE && now() >= resetAt) capacity = undefined;
        if (now() >= deadline) { expired = true; return undefined; }
      }
      const readStarted = now();
      let response, accounted = false;
      try {
        readRequests++;
        const value = await api(route, {timeoutMs: Math.max(1, Math.min(20_000, deadline - now())),
          onResponse: detail => { response = detail; }});
        readMs += now() - readStarted;
        const key = response?.http_status ?? 'unreported'; statuses[key] = (statuses[key] ?? 0) + 1;
        accounted = true;
        if (response) {
          const reference = Number.isFinite(response.server_date_ms) ? response.server_date_ms : wallNow();
          retryAt = Math.max(retryAt, now() + retryDelay(response.retry_after, reference));
          if (response.poll_ms > 0) pollAt.set(route, now() + response.poll_ms);
        }
        const c = response?.capacity;
        if (c?.resource === 'core' && ['limit', 'remaining', 'reset'].every(name => Number.isSafeInteger(c[name]))
          && c.limit > 0 && c.remaining >= 0 && c.remaining <= c.limit && c.reset > 0) {
          capacity = c;
          resetAt = now() + Math.max(0, c.reset * 1000 -
            (Number.isFinite(response.server_date_ms) ? response.server_date_ms : wallNow())) + 2000;
        } else if (c?.remaining === 0) throw Error('Exhausted GitHub quota lacks usable reset metadata; inspect the same request later');
        else capacity = undefined;
        if (route.includes(`/issues/${number}/comments?`)) commentHints.push(response);
        emit({status: 'read-observed', resource: route.includes('/comments?') ? 'result-comments' :
          route.includes('/pulls/') ? 'pull-request' : 'registration', duration_ms: now() - readStarted,
          http_status: response?.http_status ?? null, conditional: response?.conditional ?? false});
        if (now() >= deadline) { expired = true; return undefined; }
        return value;
      }
      catch (error) {
        if (!accounted) {
          readMs += now() - readStarted;
          const status = error.github?.http_status || 'failed'; statuses[status] = (statuses[status] ?? 0) + 1;
        }
        if (now() >= deadline) { expired = true; return undefined; }
        const detail = error.github ?? {};
        const limited = detail.http_status === 429 ||
          (detail.http_status === 403 && (Number(detail.rate_remaining) === 0 || detail.retry_after !== undefined || detail.secondary_limit));
        let delay;
        if (limited) {
          const reset = Number(detail.rate_reset) * 1000;
          const retry = retryDelay(detail.retry_after,
            Number.isFinite(detail.server_date_ms) ? detail.server_date_ms : wallNow());
          const primary = Number(detail.rate_remaining) === 0;
          if (!primary && ++secondaryRetries > 3)
            throw Error('Secondary API rate limit persisted after three bounded retries; inspect the same request later. No merge claimed.');
          delay = Math.max(primary ? 60_000 : 60_000 * 2 ** (secondaryRetries - 1),
            primary && Number.isFinite(reset) ? reset -
              (Number.isFinite(detail.server_date_ms) ? detail.server_date_ms : wallNow()) + 2000 : 0,
            retry);
          emit({status: 'rate-limited', retry_at: new Date(wallNow() + delay).toISOString()});
        } else if (detail.http_status >= 500 && detail.http_status <= 599 && serviceRetries++ < 2) {
          delay = Math.max(60_000 * serviceRetries, retryDelay(detail.retry_after,
            Number.isFinite(detail.server_date_ms) ? detail.server_date_ms : wallNow()));
        } else throw error;
        if (now() + delay >= deadline) { expired = true; return undefined; }
        await wait(delay, limited ? 'rate-limit' : 'service-retry');
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
    commentHints = [];
    try { comments = await pages(`/repos/${repo}/issues/${number}/comments`); }
    catch (error) { if (expired) return pending(); throw error; }
    if (expired) return pending();
    const result = readWorkerResult(comments, 'merge', requestId, number);
    if (result && result.status !== 'testing' && (result.accepted || !result.retryable)) {
      receiptAt = now() - started;
      emit({status: 'receipt-observed', accepted: result.accepted});
      if (!result.accepted) return finish(result);
      const merged = await read(`/repos/${repo}/pulls/${number}`);
      if (expired) return pending();
      verifyAcceptedMergeResult(result, merged, head);
      reconciledAt = now() - started;
      emit({status: 'merge-reconciled', merge_commit: result.merge_commit});
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
      if (!registered) emit({status: 'registered', reviewed_head: head});
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
      emit({status: 'submitting', reviewed_head: head});
      // Do not retry an uncertain write. Its printed identity permits inspection.
      await submit({number, head, requestId, timeoutMs: Math.max(1, Math.min(20_000, deadline - now()))});
      emit({status: 'submitted', reviewed_head: head});
    }
    const cacheReady = commentHints.length > 0 && commentHints.every(hint => hint?.cacheable)
      && capacity?.remaining > RECOVERY_RESERVE;
    // Retain the existing one-minute floor. Healthy conditional reads follow
    // GitHub's cache/poll guidance instead of slowing simply because CI is old.
    const providerDelay = Math.max(0, retryAt - now(), ...commentHints.map(hint => Math.max(hint?.poll_ms ?? 0,
      hint?.cache_ms ?? 0)));
    const quotaPace = capacity?.remaining > RECOVERY_RESERVE
      ? Math.max(0, resetAt - now()) * commentHints.length / (capacity.remaining - RECOVERY_RESERVE) : 0;
    const normal = cacheReady ? MIN_POLL : interval;
    const jittered = Math.round(normal * (1 + Math.max(0, Math.min(1, random())) * 0.1));
    const delay = Math.max(providerDelay, Math.ceil(quotaPace), cacheReady ? jittered : Math.min(MAX_POLL, jittered));
    if (now() + delay >= deadline) return pending();
    await wait(delay, cacheReady ? 'conditional-poll' : 'fallback-poll');
    interval = Math.min(MAX_POLL, interval * 2);
  }
  return pending();
}
