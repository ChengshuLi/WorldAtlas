import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';

test('component custody preserves whole runs and rejects missing, duplicate and redirected aliases', () => {
  const result = spawnSync(process.env.PYTHON || 'python3', ['-B', 'test/physical-component-custody.py'],
    {encoding: 'utf8', env: process.env, timeout: 120000});
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
  assert.match(result.stderr, /Ran 15 tests/);
});
