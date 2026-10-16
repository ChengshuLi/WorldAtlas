import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';

test('compact component controls reject identity, uncertainty and relationship omissions', async () => {
  const child = spawn(process.env.PYTHON || 'python3', ['-B', 'test/physical-component-evidence-controls.py'],
    {timeout: 600000, stdio: ['ignore', 'pipe', 'pipe']});
  child.stdout.pipe(process.stdout, {end: false});
  child.stderr.pipe(process.stderr, {end: false});
  let failure;
  const result = await new Promise(resolve => {
    child.once('error', error => { failure = error; });
    child.once('close', (status, signal) => resolve({status, signal}));
  });
  if (failure) throw failure;
  assert.equal(result.status, 0, `Component controls failed${result.signal ? ': '+result.signal : ''}`);
});
