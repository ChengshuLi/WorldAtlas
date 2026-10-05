import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import '@playwright/test';
test('GPU and Canvas explain and render physical coverage without changing ownership', {timeout:180000},()=>{
 const result=spawnSync(process.execPath,['test/coverage-browser.mjs'],{encoding:'utf8',timeout:170000,maxBuffer:4*1024*1024});
 assert.equal(result.status,0,(result.stdout??'')+(result.stderr??''));
});
