import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';

test('exact gap components preserve tiles, dateline, holes and ambiguous contacts', () => {
  const result = spawnSync(process.env.PYTHON || 'python3', ['-I', '-B', 'test/geographic-components.py'], {
    encoding: 'utf8', env: process.env, timeout: 120000
  });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
  assert.match(result.stderr, /Ran 20 tests/);
});
