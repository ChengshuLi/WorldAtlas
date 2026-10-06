import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';

test('before-water audit retains gaps, unknown water, tiny shapes and all residues', () => {
  const result = spawnSync(process.env.PYTHON || 'python3', ['-B', 'test/physical-gap-audit.py'], {
    encoding: 'utf8', env: process.env, timeout: 120000
  });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
  assert.match(result.stderr, /Ran 9 tests/);
});
