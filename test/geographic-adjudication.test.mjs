import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';

test('whole-loss source support retains actual native water and explicit uncertainty controls', () => {
  const result = spawnSync(process.env.PYTHON || 'python3', ['-I', '-B', 'test/geographic-adjudication.py'], {
    encoding: 'utf8', env: process.env, timeout: 120000
  });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
  assert.match(result.stderr, /Ran 14 tests/);
});
