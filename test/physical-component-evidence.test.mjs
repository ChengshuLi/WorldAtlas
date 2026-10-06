import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';

test('whole-world physical components retain every original shape, relationship and unknown', () => {
  const result = spawnSync(process.env.PYTHON || 'python3', ['-B', 'scripts/validate-physical-component-evidence.py'],
    {encoding: 'utf8', env: process.env, timeout: 600000, maxBuffer: 4 * 1024 * 1024});
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
  const report = JSON.parse(result.stdout);
  assert.equal(report.new_components, 95174);
  assert.equal(report.fragment_pairs, 108035);
  assert.equal(report.source_contact_components, 95174);
  assert.equal(report.source_contact_unknowns, 0);
});
