import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';

test('worldwide inventory rejects mutable pins, changed bytes/order and lost membership', () => {
  const result = spawnSync(process.env.PYTHON || 'python3', ['-B', 'test/worldwide-gap-inventory.py'], {
    encoding: 'utf8', env: process.env, timeout: 120000
  });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
  assert.match(result.stderr, /Ran 5 tests/);
});
