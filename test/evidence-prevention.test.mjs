import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';

test('shared evidence execution/admission regressions run without provider credentials or large datasets', () => {
  const env = {...process.env, PYTHONDONTWRITEBYTECODE: '1'};
  for (const key of ['GH_TOKEN', 'GITHUB_TOKEN', 'DATABASE_URL', 'NEON_DATABASE_URL']) delete env[key];
  const result = spawnSync(process.env.WORLDATLAS_TEST_PYTHON ?? 'python3', ['-B', 'test/evidence-prevention.py'], {
    encoding: 'utf8', env, timeout: 30000, maxBuffer: 1024 * 1024
  });
  assert.equal(result.error, undefined);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.match(result.stderr, /Ran 7 tests/);
  assert.doesNotMatch(result.stderr, /skipped/);
});

test('scientific helper and real preparation CLI regressions reject native CRS assumptions and unsafe destinations', () => {
  const env = {...process.env, PYTHONDONTWRITEBYTECODE: '1'};
  for (const key of ['GH_TOKEN', 'GITHUB_TOKEN', 'DATABASE_URL', 'NEON_DATABASE_URL']) delete env[key];
  const result = spawnSync(process.env.WORLDATLAS_TEST_PYTHON ?? 'python3', ['-B', 'test/evidence-geography.py'], {
    encoding: 'utf8', env, timeout: 60000, maxBuffer: 1024 * 1024
  });
  assert.equal(result.error, undefined);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.match(result.stderr, /Ran 10 tests/);
  assert.doesNotMatch(result.stderr, /skipped/);
});
