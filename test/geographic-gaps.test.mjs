import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';

test('geographic gap audit preserves seam/island/water and tile controls', () => {
  const result = spawnSync(process.env.PYTHON || 'python3', ['test/geographic-gaps.py'], {
    encoding: 'utf8', env: process.env
  });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
  assert.match(result.stderr, /Ran 6 tests/);
});
