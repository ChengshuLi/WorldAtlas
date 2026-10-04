// Run from the repository root before packaging evidence. Restore test bytes on every exit.
import fs from 'node:fs';
import {spawnSync, execFileSync} from 'node:child_process';
import {performance} from 'node:perf_hooks';
import {createHash} from 'node:crypto';

const directory = 'coordination/engineering/queue-test-clock-699';
const test = 'test/merge-integration-client.test.mjs';
const baseline = '66aa35ba8998846abc1f3f5a9b197a85ad9505e5';
const checkpoint = 'c0a89e155ad5386736068b9c6cdaf01c5bf104af';
const current = fs.readFileSync(test);
const production = fs.readFileSync('scripts/queue-pr-merge.mjs');
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const records = [];

function run(id, args, env, codeCommit) {
  const started = performance.now();
  const result = spawnSync(process.execPath, args, {
    encoding: 'utf8', env: {...process.env, ...env}, maxBuffer: 64 * 1024 * 1024
  });
  const elapsed = performance.now() - started;
  const log = result.stdout + result.stderr;
  const logPath = `${directory}/${id}.log`;
  fs.writeFileSync(logPath, log);
  const counts = Object.fromEntries(['tests', 'pass', 'fail', 'skipped'].map(key =>
    [key, Number(log.match(new RegExp(`^# ${key} (\\d+)$`, 'm'))?.[1])]));
  if (result.status !== 0 || counts.skipped !== 0 || counts.fail !== 0 || counts.pass !== counts.tests)
    throw Error(`${id} did not establish complete passing coverage`);
  records.push({id, code_commit: codeCommit, command: ['node', ...args].join(' '), env,
    elapsed_ms: elapsed, status: result.status, ...counts, log_path: logPath,
    test_sha256: hash(fs.readFileSync(test))});
  console.log(JSON.stringify(records.at(-1)));
}

try {
  if (!current.equals(execFileSync('git', ['show', `${checkpoint}:${test}`])))
    throw Error('Candidate bytes differ from declared code checkpoint');
  fs.writeFileSync(test, execFileSync('git', ['show', `${baseline}:${test}`]));
  run('client-baseline', ['--test', '--test-reporter=tap', test], {}, baseline);
  run('focused-baseline', ['scripts/run-integration-tests.mjs'],
    {INTEGRATION_PROFILE: 'evidence', INTEGRATION_SHARD: '0'}, baseline);
  fs.writeFileSync(test, current);
  run('client-clock', ['--test', '--test-reporter=tap', test], {}, checkpoint);
  run('focused-clock', ['scripts/run-integration-tests.mjs'],
    {INTEGRATION_PROFILE: 'evidence', INTEGRATION_SHARD: '0'}, checkpoint);

  const bad = current.toString().replace('assert.deepEqual(state.delays,[5000])',
    'assert.deepEqual(state.delays,[4999])');
  if (bad === current.toString()) throw Error('Negative control not applied');
  fs.writeFileSync(test, bad);
  const negative = spawnSync(process.execPath, ['--test', '--test-reporter=tap', test], {encoding: 'utf8'});
  fs.writeFileSync(`${directory}/negative-control.log`, negative.stdout + negative.stderr);
  if (negative.status !== 1 || !negative.stdout.includes('5000') || !negative.stdout.includes('4999') ||
      !/^# fail 1$/m.test(negative.stdout)) throw Error('Negative control did not fail exactly once');
  fs.writeFileSync(`${directory}/positive-control.json`, JSON.stringify({
    method_id: 'local-wall-clock', kind: 'positive-control', outcome: 'passed',
    scope: 'Both actual spawned-CLI test commands and complete focused runner finished with no failures or skipped tests.',
    records: records.map(({id, pass, fail, skipped}) => ({id, pass, fail, skipped}))
  }, null, 2) + '\n');
  fs.writeFileSync(`${directory}/negative-control.json`, JSON.stringify({
    method_id: 'local-wall-clock', kind: 'negative-control', outcome: 'passed',
    scope: 'Temporarily asserted 4999ms instead of 5000ms; recorded production poll delay caused exactly one test failure. Candidate bytes restored afterward.',
    exit_status: negative.status, failed_tests: 1, evidence_path: `${directory}/negative-control.log`
  }, null, 2) + '\n');
  fs.writeFileSync(`${directory}/benchmark.json`, JSON.stringify({
    node: process.version, platform: process.platform, arch: process.arch,
    baseline_commit: baseline, code_checkpoint: checkpoint, records,
    production_queue_sha256: hash(production),
    excluded_setup_attempt: `${directory}/focused-baseline-incomplete-sparse.log`,
    limits: ['One local run per command/vintage; elapsed wall time includes startup and depends on machine load.',
      'Fake GitHub fixtures measure deterministic test savings; no hosted queue throughput or external latency measured.',
      'An earlier incomplete sparse checkout failed six fixture-access tests; retained separately and excluded from the benchmark.']
  }, null, 2) + '\n');
} finally {
  fs.writeFileSync(test, current);
  if (!fs.readFileSync('scripts/queue-pr-merge.mjs').equals(production)) throw Error('Production queue bytes changed');
}
