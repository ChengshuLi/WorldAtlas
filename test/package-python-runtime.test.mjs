import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

test('Python runtime identity, cache, marker and serialized-inventory controls', () => {
  const file = fileURLToPath(new URL('./package-python-runtime.test.py', import.meta.url));
  const env = {...process.env};
  for (const key of Object.keys(env)) if (/TOKEN|SECRET|PASSWORD|CREDENTIAL|AUTHORIZATION|COOKIE/i.test(key)) delete env[key];
  assert.doesNotThrow(() => execFileSync('python3', ['-I', '-S', '-B', file],
    {env, stdio: 'pipe', timeout: 120000, maxBuffer: 1048576}));
});
