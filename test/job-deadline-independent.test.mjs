import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

// Fixtures were independently derived in exact-head review. Run each in a
// separate credential-free process, using real Git authentication and entrypoints.
const root = path.resolve(import.meta.dirname, '..');
for (const [fixture, proof] of [
  ['independent-boundaries.mjs', /independent_entrypoint_controls: 20/],
  ['independent-native-http.mjs', /persisted_POST201_aborted_body: true/]
]) {
  test(`retained independent scheduler control: ${fixture}`, () => {
    const child = spawnSync(process.execPath, [path.join(root, 'test/fixtures/deadline', fixture)],
      {cwd: root, env: {PATH: process.env.PATH}, encoding: 'utf8', timeout: 30_000});
    assert.equal(child.error, undefined);
    assert.equal(child.status, 0, child.stderr + child.stdout);
    assert.match(child.stdout, proof);
  });
}
