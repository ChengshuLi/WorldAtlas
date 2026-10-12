import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';

test('joint selected launch and actual continuous numerical/readback controls', () => {
  const result = spawnSync(process.env.PYTHON ?? 'python3', ['-B', 'test/selected-joint-check.py'], {encoding:'utf8', timeout:120000});
  assert.equal(result.status, 0, result.stdout + '\n' + result.stderr);
  assert.match(result.stderr, /Ran 12 tests/);
  assert.doesNotMatch(result.stderr, /skipped=/);
});
