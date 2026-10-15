import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {sourceCohort} from '../scripts/prepare-delivery-handoff.mjs';
import {candidateBudget} from '../scripts/native-ownership/native-preparation-guards.mjs';

test('source admits declared parent output before runtime or child execution', async t => {
  const root=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'source-parent-admission-')));
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  const python={path:path.join(root,'must-never-execute'),bytes:1,sha256:'a'.repeat(64)};
  const config={version:1,processing_allowance:{phaseBytes:1048576,rssBytes:1048576},
    runtime_inventory:{python,files:[python]},source:{version:1,resources:{output_bytes:131072}}};
  const budget=candidateBudget([],{reserveBytes:0,reserveDescriptors:0,
    allowance:{phaseBytes:65536,rssBytes:536870912}});
  await assert.rejects(sourceCohort(config,{budget},root,'.cache/delivery-handoff/result','source'),
    /Source output reserve exceeds parent preparation budget/);
  assert.deepEqual(fs.readdirSync(root),[],'refusal precedes runtime lookup and all child staging');
});

test('source never silently replaces an invalid explicit parent limit', async () => {
  for (const preparation_allowance of [null, 0, {}, {phaseBytes:0,rssBytes:1}, {phaseBytes:1,rssBytes:-1}]) {
    const config={version:1,preparation_allowance,processing_allowance:{phaseBytes:1,rssBytes:1},
      runtime_inventory:{},source:{version:1}};
    await assert.rejects(sourceCohort(config,{},'/unused','.cache/delivery-handoff/result','source'),
      /Explicit parent preparation allowance/);
  }
});

test('physical aggregate reserve is not mistaken for one ordinary file', async t => {
  const root=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'physical-aggregate-admission-')));
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  const python={path:path.join(root,'absent-runtime-after-admission'),bytes:1,sha256:'a'.repeat(64)};
  const config={version:1,processing_allowance:{phaseBytes:67108864,rssBytes:67108864},
    runtime_inventory:{python,files:[python]},physical:{version:1,resources:{output_bytes:50331648}}};
  const budget=candidateBudget([],{reserveBytes:0,reserveDescriptors:0,
    allowance:{phaseBytes:134217728,rssBytes:536870912}});
  await assert.rejects(sourceCohort(config,{budget},root,'.cache/delivery-handoff/result','physical'),
    error => error.code === 'ENOENT');
  assert.equal(budget.snapshot().accounted_bytes,0, 'preflight does not double charge later publication');
  assert.deepEqual(fs.readdirSync(root),[]);
});
