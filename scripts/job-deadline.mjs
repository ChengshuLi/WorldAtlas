import {performance} from 'node:perf_hooks';

// Reserve time for the refusal/accounting output and runner cleanup. Setup is
// already charged against the authenticated job start, not estimated here.
export const JOB_FINALIZATION_MS = 30_000;
export const HTTP_ATTEMPT_MS = 20_000;
const need = (ok, message) => {if (!ok) throw Error(message);};

export function workflowJobMinutes(workflow, phase) {
  need(/^[a-z][a-z0-9_-]*$/.test(phase ?? ''), 'Invalid workflow phase');
  const roots = [...workflow.matchAll(/^jobs:[ \t]*\r?\n/gm)];
  need(roots.length === 1, 'Cannot establish unique workflow jobs');
  const jobs = workflow.slice(roots[0].index + roots[0][0].length);
  const blocks = [...jobs.matchAll(/^  ([a-z][a-z0-9_-]*):[ \t]*\n([\s\S]*?)(?=^  [a-z][a-z0-9_-]*:[ \t]*$|^\S|(?![\s\S]))/gm)]
    .filter(match => match[1] === phase);
  need(blocks.length === 1, 'Cannot establish unique workflow phase');
  const timeouts = [...blocks[0][2].matchAll(/^    timeout-minutes: ([1-9]\d*)\s*$/gm)];
  need(timeouts.length === 1, 'Workflow phase needs a literal finite timeout');
  const minutes = Number(timeouts[0][1]);
  need(Number.isSafeInteger(minutes) && minutes <= 360, 'Invalid workflow phase timeout');
  // These jobs use their ID as the displayed name. A future named/matrix job
  // must deliberately update the binding rather than guessing a matching row.
  need(!/^    (?:name|strategy):/m.test(blocks[0][2]), 'Unsupported scheduler job naming');
  return minutes;
}

const START_FORMAT = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?Z$/;
const PENDING = ['queued', 'requested', 'waiting', 'pending'];
const safeField = (value, valid) => value === undefined ? 'missing' : value === null ? null : valid(value) ? value : 'invalid';
const positive = value => Number.isSafeInteger(value) && value > 0;

export async function loadJobDeadline({api, repo, phase, workflow, env = process.env,
  wallNow = Date.now, monotonicNow = () => performance.now(), metadataRemaining,
  sleep = ms => new Promise(resolve => setTimeout(resolve, ms))}) {
  need(/^[-\w.]+\/[-\w.]+$/.test(repo ?? ''), 'Invalid deadline repository');
  need(env.GITHUB_JOB === phase && /^[1-9]\d*$/.test(env.GITHUB_RUN_ID ?? '') &&
    /^[1-9]\d*$/.test(env.GITHUB_RUN_ATTEMPT ?? ''), 'Missing current job/run/attempt authority');
  const run = Number(env.GITHUB_RUN_ID), attempt = Number(env.GITHUB_RUN_ATTEMPT);
  need(Number.isSafeInteger(run) && Number.isSafeInteger(attempt), 'Invalid job/run/attempt authority');
  const minutes = workflowJobMinutes(workflow, phase);
  const wallStarted = wallNow(), monotonicStarted = monotonicNow(), observations = [];
  let reads = 0, waited = 0, pinnedID, pinnedStart, job, started;
  const elapsed = () => {
    const value = monotonicNow() - monotonicStarted;
    need(Number.isFinite(value) && value >= 0, 'Invalid elapsed job clock');
    return value;
  };
  const snapshot = (mismatches, row, counts = {}) => ({mismatches,
    expected: {phase, run_id: run, run_attempt: attempt}, ...counts,
    ...(row ? {observed: {
      job_id: safeField(row.id, positive), run_id: safeField(row.run_id, positive),
      run_attempt: safeField(row.run_attempt, positive),
      status: safeField(row.status, value => [...PENDING, 'in_progress', 'completed'].includes(value)),
      started_at: safeField(row.started_at, value => typeof value === 'string' && START_FORMAT.test(value))
    }} : {})});
  const fail = (message, binding, extras = {}) => {
    throw Object.assign(Error(message), {deadlineBinding: {...binding, metadata_reads: reads,
      metadata_wait_ms: waited, metadata_observations: observations}, ...extras});
  };
  // Only the PR caller opts into rereading successful but pending metadata.
  // Its existing startup deadline includes workflow lookup, every read and wait.
  // HTTP/quota/permission/transport failures are never retried here.
  for (;;) {
    reads++;
    let response;
    try { response = await api(`/repos/${repo}/actions/runs/${run}/attempts/${attempt}/jobs?per_page=100&page=1`); }
    catch (error) {
      if (observations.length) error.deadlineBinding = {...observations.at(-1), metadata_reads: reads,
        metadata_wait_ms: waited, metadata_observations: observations};
      throw error;
    }
    elapsed();
    const count = response?.total_count;
    if (!Number.isSafeInteger(count) || count < 0 || count > 100 || !Array.isArray(response.jobs) || response.jobs.length !== count)
      fail('Incomplete current job inventory', snapshot(['inventory'], null));
    if (!response.jobs.every(row => row && positive(row.id)) || new Set(response.jobs.map(row => row.id)).size !== count)
      fail('Invalid current job inventory', snapshot(['job_id'], null, {total_count: count}));
    const matches = response.jobs.filter(row => row.name === phase);
    if (matches.length > 1) fail('Ambiguous current phase job', snapshot(['phase'], null, {match_count: matches.length, total_count: count}));
    job = matches[0];
    const mismatches = [];
    let pending = true;
    if (!job) mismatches.push('phase');
    else {
      if (pinnedID !== undefined && job.id !== pinnedID) {mismatches.push('job_id');pending = false;}
      pinnedID ??= job.id;
      for (const [field, expected] of [['run_id', run], ['run_attempt', attempt]]) {
        if (job[field] !== expected) {mismatches.push(field);if (job[field] != null) pending = false;}
      }
      if (job.status !== 'in_progress') {
        mismatches.push('status');if (job.status != null && !PENDING.includes(job.status)) pending = false;
      }
      if (job.started_at == null) mismatches.push('started_at');
      else {
        started = typeof job.started_at === 'string' ? Date.parse(job.started_at) : NaN;
        const canonical = typeof job.started_at === 'string' && START_FORMAT.test(job.started_at)
          ? job.started_at.includes('.') ? job.started_at.replace(/\.(\d{1,3})Z$/, (_, fraction) => '.' + fraction.padEnd(3, '0') + 'Z')
            : job.started_at.replace(/Z$/, '.000Z') : null;
        if (!canonical || !Number.isFinite(started) || started > wallStarted || new Date(started).toISOString() !== canonical ||
          pinnedStart !== undefined && started !== pinnedStart) {mismatches.push('started_at');pending = false;}
        else pinnedStart ??= started;
      }
    }
    if (!mismatches.length) break;
    const binding = snapshot(mismatches, job, {match_count: matches.length, total_count: count});
    observations.push(binding);
    const message = 'Job metadata does not bind the executing phase: ' + mismatches.join(', ');
    const pause = [250, 750][reads - 1];
    if (!pending || typeof metadataRemaining !== 'function' || pause === undefined) fail(message, binding);
    const canRead = wait => {
      const budget = metadataRemaining();
      if (!Number.isFinite(budget) || budget <= wait + HTTP_ATTEMPT_MS)
        fail('Startup deadline exhausted during metadata admission', binding, {jobDeadline: true});
    };
    canRead(pause);
    const before = elapsed();
    await sleep(pause);
    const after = elapsed();
    need(after >= before, 'Invalid elapsed job clock');
    waited += after - before;
    canRead(0);
  }
  const expires = started + minutes * 60_000;
  const remaining = () => expires - wallStarted - elapsed() - JOB_FINALIZATION_MS;
  need(remaining() > HTTP_ATTEMPT_MS, 'Job deadline exhausted during metadata admission');
  return {remaining, job_id: job.id, run_id: run, run_attempt: attempt,
    phase, started_at: job.started_at, timeout_minutes: minutes, finalization_ms: JOB_FINALIZATION_MS,
    metadata_reads: reads, metadata_wait_ms: waited, metadata_observations: observations};
}

// Preserve the existing scheduler interface and its deliberately bounded phases.
export function schedulerJobMinutes(workflow, phase) {
  need(['register', 'schedule'].includes(phase), 'Invalid scheduler phase');
  return workflowJobMinutes(workflow, phase);
}
export function loadSchedulerDeadline(options) {
  need(['register', 'schedule'].includes(options.phase), 'Invalid scheduler phase');
  return loadJobDeadline(options);
}
