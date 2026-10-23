import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import test from 'node:test';

// Part of the normal test/*.test.mjs inventory. Unlike a deliberately limited
// standalone pure-Python check, CI must execute the real Git/GEOS controls.
test('source-cohort identity, scientific predicates and immutable outputs', () => {
  const result = spawnSync(process.env.WORLDATLAS_TEST_PYTHON ?? process.env.PYTHON ?? 'python3',
    ['-I', '-B', 'test/source-cohort.test.py'], {
      cwd: new URL('..', import.meta.url), encoding: 'utf8', timeout: 60000, maxBuffer: 2 * 1024 * 1024,
      env: {...process.env, WORLDATLAS_REQUIRE_SOURCE_SCIENCE: '1', PYTHONDONTWRITEBYTECODE: '1'}
    });
  assert.ifError(result.error);
  assert.equal(result.status, 0, result.stdout + '\n' + result.stderr);
  assert.match(result.stderr, /Ran \d+ tests/);
  assert.doesNotMatch(result.stderr, /skipped=/);
});
