import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

// Retain the native HTTP boundary exercised by the former scheduler fixtures.
// The shared API still serves claims, PR gates and merge validation; no scheduler
// registration or replay protocol is required. Run in a credential-free process.
const root = path.resolve(import.meta.dirname, '..');
for (const [fixture, proof] of [
  ['independent-native-http.mjs', /persisted_POST201_aborted_body: true/]
]) {
  test(`retained shared HTTP control: ${fixture}`, () => {
    const child = spawnSync(process.execPath, [path.join(root, 'test/fixtures/deadline', fixture)],
      {cwd: root, env: {PATH: process.env.PATH}, encoding: 'utf8', timeout: 30_000});
    assert.equal(child.error, undefined);
    assert.equal(child.status, 0, child.stderr + child.stdout);
    assert.match(child.stdout, proof);
  });
}
