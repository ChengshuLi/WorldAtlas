import {execFileSync} from 'node:child_process';
import {randomUUID} from 'node:crypto';
import {cleanupCompletedWorkspace} from './local-workspace.mjs';
import {runMergeQueueClient, mergeQueueAPI} from './merge-queue-client.mjs';

const args = process.argv.slice(2), values = {};
for (let i = 0; i < args.length; i++) {
  const key = args[i];
  if (['--observe', '--cleanup'].includes(key) && !values[key]) { values[key] = true; continue; }
  if (!['--pr', '--head', '--request-id'].includes(key) || !args[i + 1] || values[key])
    throw Error('Usage: node scripts/queue-pr-merge.mjs --pr N --head SHA [--request-id ID] [--observe [--cleanup]]');
  values[key] = args[++i];
}
if (!/^[1-9]\d*$/.test(values['--pr'] ?? '') || !/^[a-f0-9]{40}$/.test(values['--head'] ?? ''))
  throw Error('Supply the exact PR number and verified head SHA');
if (values['--observe'] && !values['--request-id']) throw Error('Read-only observation requires the existing request ID');
if (values['--cleanup'] && !values['--observe']) throw Error('Explicit recovery cleanup requires --observe and the existing request ID');
const repo = 'ChengshuLi/WorldAtlas', number = Number(values['--pr']), head = values['--head'];
const requestId = values['--request-id'] ?? randomUUID();
if (!/^[-a-zA-Z0-9]{16,100}$/.test(requestId)) throw Error('Invalid stable request ID');
const gh = (args, timeoutMs = 20_000) => execFileSync('gh', args, {encoding: 'utf8', maxBuffer: 16 * 1024 * 1024,
  timeout: timeoutMs, killSignal: 'SIGKILL'});
const api = mergeQueueAPI();
// Preserve identity before any possible submission, including an uncertain write.
console.log(JSON.stringify({status: 'observing', request_id: requestId, reviewed_head: head}));
const result = await runMergeQueueClient({api, repo, number, head, requestId,
  observeOnly: Boolean(values['--observe']), resuming: Boolean(values['--request-id']),
  progress: value => console.log(JSON.stringify(value)),
  submit: ({number, head, requestId, timeoutMs}) => gh(['workflow', 'run', 'merge-scheduler.yml', '--repo', repo, '--ref', 'main',
    '-f', `pr_number=${number}`, '-f', `expected_head=${head}`, '-f', `request_id=${requestId}`], timeoutMs)});
if (result.accepted) {
  let cleanup;
  if (!values['--observe'] || values['--cleanup']) {
    const started = performance.now();
    console.log(JSON.stringify({status: 'cleanup-started', request_id: requestId, observed_at: new Date().toISOString()}));
    cleanup = cleanupCompletedWorkspace(process.cwd(), head);
    console.log(JSON.stringify({status: 'cleanup-ended', request_id: requestId, duration_ms: performance.now() - started,
      duration_clock: 'monotonic', observed_at: new Date().toISOString()}));
  }
  console.log(JSON.stringify({...result, ...(cleanup ? {local_cleanup: cleanup} : {})}));
}
else {
  console.log(JSON.stringify(result));
  process.exitCode = result.status === 'pending' ? 3 : 2;
}
