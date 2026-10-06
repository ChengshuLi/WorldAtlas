import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';

test('worldwide gap priorities preserve source uncertainty and exhaustive accounting', () => {
  const run = spawnSync(process.env.PYTHON || 'python3', ['-B', 'test/physical-gap-priority-controls.py'],
    {encoding: 'utf8', timeout: 600000, maxBuffer: 4 * 1024 * 1024});
  assert.equal(run.status, 0, `${run.stdout}\n${run.stderr}`);
  assert.match(run.stderr, /Ran 27 tests/);
});
