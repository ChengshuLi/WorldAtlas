import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';

test('trusted startup, separated proof entry and verification-only mode resist substitution',()=>{
  const result=spawnSync('python3',['-I','-B','test/selected-package-bootstrap-controls.py','scripts/selected-package-bootstrap.py'],
    {encoding:'utf8',maxBuffer:4*1024*1024,timeout:60000,stdio:['ignore','pipe','pipe']});
  assert.equal(result.error,undefined,result.error?.message);
  assert.equal(result.status,0,`${result.stdout}\n${result.stderr}`);
  assert.match(result.stderr,/Ran [1-9][0-9]* tests/,'The Python controls must actually execute');
  assert.match(result.stderr,/\nOK\s*$/,'Every offline bootstrap control must pass');
});
