import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';

test('trusted geography controls reject candidate scripts, import shadows and conflicting integrations',()=>{
 const result=spawnSync(process.env.PYTHON??'python3',['-B','test/trusted-geography-check.py'],{encoding:'utf8',timeout:120000});
 assert.equal(result.status,0,result.stdout+'\n'+result.stderr);
 assert.match(result.stderr,/Ran 13 tests/);
 assert.doesNotMatch(result.stderr,/skipped=/);
});
