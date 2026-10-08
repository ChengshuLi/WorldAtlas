import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';

test('control fixture retains actual shared-output custody and refuses unchanged bad descriptors',()=>{
  const run=spawnSync(process.env.PYTHON||'python3',
    ['-B','test/physical-component-evidence-controls.py','FixtureBindingControls'],
    {encoding:'utf8',timeout:120000,maxBuffer:4*1024*1024});
  assert.equal(run.status,0,`${run.stdout}\n${run.stderr}`);
  assert.match(run.stderr,/Ran 2 tests/);
});
