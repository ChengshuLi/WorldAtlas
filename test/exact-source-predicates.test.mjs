import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';

test('exact original source predicates retain closure, uncertainty and export failures', () => {
  const result = spawnSync(process.env.PYTHON || 'python3', ['-B', 'test/exact-source-predicates.py'],
    {encoding: 'utf8', timeout: 120000, maxBuffer: 1024 * 1024});
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
});
