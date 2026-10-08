import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {admitPhase, readAdmittedBody} from './phase-admission.mjs';
const root = fs.mkdtempSync(path.join(process.cwd(), '.cache-phase-control-'));
const body = Buffer.from('complete original fixture\n');
const file = path.join(root, 'input'); fs.writeFileSync(file, body, {mode: 0o600});
const runtime = path.join(root, 'runtime-fixture'); fs.writeFileSync(runtime, body, {mode: 0o600});
const pin = file => ({path: file, bytes: body.length, mode: 0o600,
  sha256: createHash('sha256').update(body).digest('hex')});
let opens = 0;
const open = fs.openSync;
fs.openSync = (...args) => { opens++; return open(...args); };
try {
  const admitted = admitPhase({inputs: [pin(file)], runtime: pin(runtime), outputReserve: 1024});
  assert.equal(opens, 0); assert.deepEqual(readAdmittedBody(admitted, file), body);
  opens = 0;
  assert.throws(() => admitPhase({inputs: [pin(file)], runtime: pin(runtime), outputReserve: 256 * 1024 * 1024}));
  assert.equal(opens, 0);
  assert.throws(() => admitPhase({inputs: Array.from({length: 513}, () => pin(file)), runtime: pin(runtime), outputReserve: 0}));
  assert.equal(opens, 0);
  assert.throws(() => admitPhase({inputs: [pin(file), pin(file)], runtime: pin(runtime), outputReserve: 0}));
  const link = path.join(root, 'symlink'); fs.symlinkSync(file, link);
  assert.throws(() => admitPhase({inputs: [pin(link)], runtime: pin(runtime), outputReserve: 0}));
  assert.equal(opens, 0);
  assert.throws(() => readAdmittedBody(admitted, path.join(root, 'foreign')));
  fs.writeFileSync(file, Buffer.alloc(body.length, 0));
  assert.throws(() => readAdmittedBody(admitted, file));
  console.log(JSON.stringify({positive: 1, negative: 6, overbound_body_opens: 0,
    fixture_runtime_only: true, actual_installed_runtime_qualification: false}));
} finally {
  fs.openSync = open;
  fs.rmSync(root, {recursive: true});
}
