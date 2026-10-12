import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';

test('actual trusted-base bootstrap and inline workflow resist execution and resolution substitution',()=>{
  const result=execFileSync('python3',['-I','-B','test/selected-package-bootstrap-controls.py','scripts/selected-package-bootstrap.py'],
    {encoding:'utf8',maxBuffer:4*1024*1024,timeout:60000,stdio:['ignore','pipe','pipe']});
  assert.equal(typeof result,'string');
});
