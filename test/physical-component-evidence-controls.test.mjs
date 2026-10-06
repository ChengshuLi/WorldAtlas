import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';

test('complete world component evidence rejects rehashed identity, uncertainty and relationship omissions', () => {
  const run = spawnSync(process.env.PYTHON || 'python3', ['-B', 'test/physical-component-evidence-controls.py'],
    {encoding: 'utf8', timeout: 600000, maxBuffer: 4 * 1024 * 1024});
  assert.equal(run.status, 0, `${run.stdout}\n${run.stderr}`);
  assert.match(run.stderr, /Ran 7 tests/);
});
