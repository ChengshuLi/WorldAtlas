import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
test('actual CI consumer and cold pre-import guard use current allowance',()=>{
 const root=path.resolve(import.meta.dirname,'..');
 const result=spawnSync('bash',[path.join(root,'coordination/engineering/admitted-processing-limits-20261011/current-ci-allowance-controls.sh'),root],{encoding:'utf8',timeout:30000,maxBuffer:1024*1024});
 assert.equal(result.status,0,result.stderr||result.error?.message);
});
