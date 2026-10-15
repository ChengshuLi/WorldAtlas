import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';

function wholeFileSha(filename) {
  const hash = createHash('sha256'), buffer = Buffer.alloc(1024 * 1024);
  const fd = fs.openSync(filename, 'r');
  try {
    for (let n; (n = fs.readSync(fd, buffer, 0, buffer.length, null));)
      hash.update(buffer.subarray(0, n));
  } finally { fs.closeSync(fd); }
  return hash.digest('hex');
}

test('installed runtime identity follows the actual absolute Node under a misleading PATH', t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'worldatlas-runtime-identity-'));
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  const marker = path.join(root, 'path-node-was-executed');
  // If anything resolves and executes PATH's node, it leaves an actual sentinel.
  fs.writeFileSync(path.join(root, 'node'), '#!/bin/sh\n: > "$WORLDATLAS_PATH_NODE_SENTINEL"\nexit 91\n', {mode: 0o755});
  const module = new URL('../scripts/check-effective-geographic-regression.mjs', import.meta.url).href;
  const env = {...process.env, PATH: root, WORLDATLAS_PATH_NODE_SENTINEL: marker};
  delete env.NODE_OPTIONS; delete env.NODE_PATH;
  const script = `
    const {runtimeIdentity} = await import(process.argv[1]);
    const implicit = runtimeIdentity(), explicit = runtimeIdentity(process.execPath);
    process.stdout.write(JSON.stringify({implicit, explicit, version: process.version}));
  `;
  const result = spawnSync(process.execPath, ['--input-type=module', '-e', script, module], {
    cwd: root, env, encoding: 'utf8', timeout: 30000, maxBuffer: 16384
  });
  assert.ifError(result.error);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(fs.existsSync(marker), false, 'PATH node must never execute');
  const observed = JSON.parse(result.stdout), executable = fs.realpathSync(process.execPath);
  const stat = fs.statSync(executable);
  assert.deepEqual(observed.implicit, {
    path: executable, bytes: stat.size, mode: stat.mode & 0o777,
    sha256: wholeFileSha(executable), version: process.version
  });
  assert.deepEqual(observed.explicit, observed.implicit);
  assert.equal(observed.version, process.version);
  assert.deepEqual(fs.readdirSync(root), ['node'], 'identity lookup must create no other files');
});
