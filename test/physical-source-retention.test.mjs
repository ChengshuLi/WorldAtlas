import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
test('physical metadata closure and single native buffer preserve exact boundaries',()=>{
 const result=spawnSync(process.env.WORLDATLAS_TEST_PYTHON??process.env.PYTHON??'python3',['-I','-B','test/physical-source-retention.test.py'],{encoding:'utf8',timeout:60000});
 assert.ifError(result.error);assert.equal(result.status,0,result.stdout+'\n'+result.stderr);assert.doesNotMatch(result.stderr,/skipped=/);
});
