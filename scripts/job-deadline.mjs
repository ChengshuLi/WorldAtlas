import {performance} from 'node:perf_hooks';

// Reserve time for the refusal/accounting output and runner cleanup. Setup is
// already charged against the authenticated job start, not estimated here.
export const JOB_FINALIZATION_MS = 30_000;
export const HTTP_ATTEMPT_MS = 20_000;
const need = (ok, message) => {if (!ok) throw Error(message);};

export function schedulerJobMinutes(workflow, phase) {
  need(['register', 'schedule'].includes(phase), 'Invalid scheduler phase');
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

export async function loadSchedulerDeadline({api, repo, phase, workflow, env = process.env,
  wallNow = Date.now, monotonicNow = () => performance.now()}) {
  need(/^[-\w.]+\/[-\w.]+$/.test(repo ?? ''), 'Invalid deadline repository');
  need(env.GITHUB_JOB === phase && /^[1-9]\d*$/.test(env.GITHUB_RUN_ID ?? '') &&
    /^[1-9]\d*$/.test(env.GITHUB_RUN_ATTEMPT ?? ''), 'Missing current job/run/attempt authority');
  const run = Number(env.GITHUB_RUN_ID), attempt = Number(env.GITHUB_RUN_ATTEMPT);
  need(Number.isSafeInteger(run) && Number.isSafeInteger(attempt), 'Invalid job/run/attempt authority');
  const minutes = schedulerJobMinutes(workflow, phase);
  const wallStarted = wallNow(), monotonicStarted = monotonicNow();
  // The bootstrap API has no quota retry. An unavailable/ambiguous inventory
  // refuses before queue writes; do not spend an eight-minute wait finding it.
  const response = await api(`/repos/${repo}/actions/runs/${run}/attempts/${attempt}/jobs?per_page=100&page=1`);
  need(Number.isSafeInteger(response?.total_count) && response.total_count > 0 && response.total_count <= 100 &&
    Array.isArray(response.jobs) && response.jobs.length === response.total_count,
  'Incomplete current job inventory');
  need(response.jobs.every(row => Number.isSafeInteger(row.id) && row.id > 0) &&
    new Set(response.jobs.map(row => row.id)).size === response.jobs.length, 'Invalid current job inventory');
  const matches = response.jobs.filter(row => row.name === phase);
  need(matches.length === 1, 'Ambiguous current phase job');
  const job = matches[0];
  need(job.run_id === run && job.run_attempt === attempt && job.status === 'in_progress' &&
    /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?Z$/.test(job.started_at ?? ''),
  'Job metadata does not bind the executing phase');
  const started = Date.parse(job.started_at);
  const canonicalStart = job.started_at.includes('.') ? job.started_at.replace(/\.(\d{1,3})Z$/, (_, fraction) => '.' + fraction.padEnd(3, '0') + 'Z') : job.started_at.replace(/Z$/, '.000Z');
  need(Number.isFinite(started) && started <= wallStarted && new Date(started).toISOString() === canonicalStart,
    'Invalid current job start');
  const expires = started + minutes * 60_000;
  const remaining = () => {
    const elapsed = monotonicNow() - monotonicStarted;
    need(Number.isFinite(elapsed) && elapsed >= 0, 'Invalid elapsed job clock');
    return expires - wallStarted - elapsed - JOB_FINALIZATION_MS;
  };
  need(remaining() > HTTP_ATTEMPT_MS, 'Job deadline exhausted during metadata admission');
  return {remaining, job_id: job.id, run_id: run, run_attempt: attempt,
    phase, started_at: job.started_at, timeout_minutes: minutes, finalization_ms: JOB_FINALIZATION_MS};
}
