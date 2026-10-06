import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';

test('complete worldwide priority inventory matches original source ledgers and exhaustive ranks', () => {
  const run=spawnSync(process.env.PYTHON || 'python3',['-B','scripts/validate-physical-gap-priorities.py',
    '--prefix','coordination/engineering/physical-gap-priorities-1005-20261006-local20/priorities-v2'],
    {encoding:'utf8',timeout:600000,maxBuffer:4*1024*1024});
  assert.equal(run.status,0,`${run.stdout}\n${run.stderr}`);
  const report=JSON.parse(run.stdout);
  assert.equal(report.components,95174);
  assert.equal(report.native_contexts,49625);
  assert.equal(report.unmeasured_fragments,5);
  assert.equal(report.status,'diagnostic-only');
});
