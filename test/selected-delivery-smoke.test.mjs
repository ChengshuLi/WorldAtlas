import test from 'node:test';

import assert from 'node:assert/strict';

import {execFileSync} from 'node:child_process';

import {fileURLToPath} from 'node:url';

const script = fileURLToPath(new URL('../scripts/selected-delivery-smoke.mjs', import.meta.url));

test('CLI fails on missing required arguments and duplicate/unknown options', () => {
  for (const args of [[], ['--unknown', 'x'], ['--output'], ['--root', 'a', '--root', 'b']])
    assert.throws(() => execFileSync(process.execPath, [script, ...args], {stdio: 'pipe'}));
});

import {validateDeliveryExpectations} from '../scripts/selected-delivery-smoke.mjs';
test('historical cumulative expectations cannot reopen the final-bank consumer',()=>{
 assert.throws(()=>validateDeliveryExpectations({version:1}),/require final-map version 2/);
});
