import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';

test('complete world component evidence rejects rehashed identity, uncertainty and relationship omissions', async () => {
  const child = spawn(process.env.PYTHON || 'python3', ['-B', 'test/physical-component-evidence-controls.py'],
    {timeout: 600000, stdio: ['ignore', 'pipe', 'pipe']});
  let stdout = '', stderr = '', failure;
  for (const [stream, destination, save] of [
    [child.stdout, process.stdout, chunk => stdout += chunk],
    [child.stderr, process.stderr, chunk => stderr += chunk]
  ]) {
    stream.setEncoding('utf8');
    stream.on('data', chunk => {
      save(chunk);
      if (Buffer.byteLength(stdout) > 4 * 1024 * 1024 || Buffer.byteLength(stderr) > 4 * 1024 * 1024) {
        failure = Error('Complete component controls exceeded unchanged output limit');
        child.kill('SIGKILL');
      }
    });
    stream.pipe(destination, {end: false});
  }
  const status = await new Promise(resolve => {
    child.once('error', error => { failure = error; });
    child.once('close', status => resolve(status));
  });
  if (failure) throw failure;
  assert.equal(status, 0, `${stdout}\n${stderr}`);
  assert.match(stderr, /Ran 7 tests/);
});
