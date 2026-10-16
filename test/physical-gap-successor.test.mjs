import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';

test('physical-source gzip decoding preserves complete encoded and decoded custody', () => {
  const result = spawnSync(process.env.PYTHON || 'python3', ['-B', 'test/physical-gap-successor.py'], {
    encoding: 'utf8', env: process.env, timeout: 120000
  });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
});
