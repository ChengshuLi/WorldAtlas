import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';

test('lossless audit input envelopes preserve complete originals and reject tampering', () => {
  const result = spawnSync(process.env.PYTHON || 'python3', ['-B', 'test/lossless-audit-inputs.py'], {
    encoding: 'utf8', env: process.env, timeout: 120000
  });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
  assert.match(result.stderr, /Ran 6 tests/);
});
