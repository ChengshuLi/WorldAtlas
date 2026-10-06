import {test} from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {assertAuthorWorkerIdentity} from '../scripts/worker-identity.mjs';

const scripts = fileURLToPath(new URL('../scripts/', import.meta.url));
test('author identity accepts its chat, rejects copied identity, and documents unavailable identity', () => {
  assert.doesNotThrow(() => assertAuthorWorkerIdentity('chat-one', 'chat-one'));
  assert.throws(() => assertAuthorWorkerIdentity('chat-two', 'chat-one'), /identity mismatch/);
  assert.doesNotThrow(() => assertAuthorWorkerIdentity('persistent-outside-codex', ''));
});

test('claim/recover and default/explicit author allocation reject before GitHub or Git side effects', t => {
  const cwd = fs.mkdtempSync(path.join(os.tmpdir(), 'atlas-identity-'));
  t.after(() => fs.rmSync(cwd, {recursive: true, force: true}));
  const calls = [
    ['issue-lease.mjs', 'claim', '--issue', '1', '--worker', 'copied-id', '--branch', 'engineering/test'],
    ['issue-lease.mjs', 'recover', '--issue', '1', '--worker', 'copied-id', '--branch', 'engineering/test'],
    ['local-workspace.mjs', 'allocate', '--worker', 'copied-id', '--branch', 'engineering/test'],
    ['local-workspace.mjs', 'allocate', '--worker', 'copied-id', '--slot', 'work', '--branch', 'engineering/test'],
  ];
  for (const [script, ...args] of calls) {
    const run = spawnSync(process.execPath, [path.join(scripts, script), ...args], {
      cwd, env: {...process.env, CODEX_THREAD_ID: 'actual-chat', PATH: ''}, encoding: 'utf8',
    });
    assert.notEqual(run.status, 0);
    assert.match(run.stderr, /Worker identity mismatch/);
    assert.deepEqual(fs.readdirSync(cwd), []);
  }
});

test('legacy renew/release, inspect and independent review are not mistaken for new author work', t => {
  const cwd = fs.mkdtempSync(path.join(os.tmpdir(), 'atlas-identity-legacy-'));
  t.after(() => fs.rmSync(cwd, {recursive: true, force: true}));
  const calls = [
    ...['renew', 'release'].map(action => ['issue-lease.mjs', action, '--issue', '1', '--worker', 'legacy-id', '--branch', 'engineering/test', '--claim-id', 'held-claim']),
    ['issue-lease.mjs', 'inspect', '--issue', '1'],
    ['local-workspace.mjs', 'allocate', '--worker', 'distinct-review-agent', '--slot', 'review', '--commit', 'a'.repeat(40)],
    ['local-workspace.mjs', 'report'],
    ['local-workspace.mjs', 'release', '--worker', 'legacy-id', '--token', 'held-token'],
  ];
  for (const [script, ...args] of calls) {
    const run = spawnSync(process.execPath, [path.join(scripts, script), ...args], {
      cwd, env: {...process.env, CODEX_THREAD_ID: 'actual-chat', PATH: ''}, encoding: 'utf8',
    });
    // No Git/gh in this fixture: reaching that boundary proves the new identity
    // guard did not block legacy maintenance, inspection or distinct review.
    assert.notEqual(run.status, 0);
    assert.doesNotMatch(run.stderr, /Worker identity mismatch/);
    assert.match(run.stderr, /ENOENT/);
  }
});
