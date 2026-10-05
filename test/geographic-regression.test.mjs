import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';

test('differential geography checks preserve neighbor, water, dateline and immutable-input controls', () => {
  const result = spawnSync(process.env.PYTHON || 'python3', ['test/geographic-regression.py'], {
    encoding: 'utf8', env: process.env, timeout: 120000
  });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
  assert.match(result.stderr, /Ran 16 tests/);
});
