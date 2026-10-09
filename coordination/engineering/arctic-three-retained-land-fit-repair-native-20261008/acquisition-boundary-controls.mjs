import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {acquire} from './acquire-operand.mjs';
const root = process.cwd(), cache = path.join(root, '.cache');
const existed = fs.existsSync(cache);
if (!existed) fs.mkdirSync(cache);
const fixture = fs.mkdtempSync(path.join(cache, 'operand-entry-control-'));
const file = path.join(fixture, 'existing'); fs.writeFileSync(file, 'original');
const dangling = path.join(fixture, 'dangling'); fs.symlinkSync(path.join(fixture, 'absent'), dangling);
const open = fs.openSync; let opens = 0;
fs.openSync = (...args) => { opens++; return open(...args); };
try {
  for (const output of [file, path.join(dangling, 'new'), path.join(file, 'new'),
    cache + '/../../outside', path.join(root, 'outside')]) {
    await assert.rejects(acquire('0'.repeat(40), 0, output));
    assert.equal(opens, 0, 'Invalid destination reached runtime/source body open');
  }
  assert.equal(fs.readFileSync(file, 'utf8'), 'original');
  console.log(JSON.stringify({actual_entry_destination_negatives: 5, runtime_or_source_body_opens: 0,
    acquisition_executed: false, runtime_fixture_qualified: false}));
} finally {
  fs.openSync = open;
  fs.rmSync(fixture, {recursive: true});
  if (!existed) fs.rmdirSync(cache);
}
