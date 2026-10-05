import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';

test('native monthly water diagnostics retain missing observations and spatial uncertainty', () => {
  const r = spawnSync(process.env.PYTHON || 'python3', ['-I', '-B', 'test/geographic-water.py'], {
    encoding: 'utf8', env: process.env, timeout: 120000
  });
  assert.equal(r.status, 0, `${r.stdout}\n${r.stderr}`);
  assert.match(r.stderr, /Ran 17 tests/);
});
