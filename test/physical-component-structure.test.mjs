import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';

test('component reconstruction permits representation order and rejects coordinate or identity changes', () => {
  const result = spawnSync(process.env.PYTHON || 'python3', ['-B', 'test/physical-component-structure.py'],
    {encoding: 'utf8', env: process.env, timeout: 30000, maxBuffer: 1024 * 1024});
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
});
