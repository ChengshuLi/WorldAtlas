// Actual imported application API controls. These do not execute scientific
// producers or claim a successful normal build; hosted full callers do that.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {gunzipSync} from 'node:zlib';
import {validateOriginalQualificationInvocation, requireConsumedArcticArtifacts,
  consumeQualifiedArcticArtifacts} from './qualified-artifact-consumer.mjs';
const directory=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(directory,'../../..');
const inventory=JSON.parse(gunzipSync(fs.readFileSync(path.join(directory,'qualified-artifacts/inventory.json.gz'))));
let originalInvocations=0, planless=0, rejected=0;
for(const phase of inventory.complete_phase_inventory) for(const run of phase.runs) {
  validateOriginalQualificationInvocation(phase.phase,run,run.original_invocation.code_source?.original_whole_code_source);
  originalInvocations++;if(!run.complete_original_plans.length)planless++;
}
assert.equal(originalInvocations,171);assert.equal(planless,70);
for(const forged of [{},{kind:'authenticated-qualified-artifact-consumption-v1'},
  {kind:'authenticated-qualified-artifact-consumption-v1',issue:1520,steps:[{receipt:{geometry_stage_validated:true}}]}]) {
  assert.throws(()=>requireConsumedArcticArtifacts(forged));rejected++;
}
const source=fs.mkdtempSync(path.join(root,'.cache/qualified-artifact-source-control-'));
const previous={stage:process.env.WORLDATLAS_PACKAGE_STAGE,source:process.env.WORLDATLAS_PACKAGE_SOURCE_ROOT};
process.env.WORLDATLAS_PACKAGE_STAGE=root;process.env.WORLDATLAS_PACKAGE_SOURCE_ROOT=source;
const open=fs.openSync;let opens=0;
fs.openSync=(...args)=>{opens++;return open(...args);};
try {
  for(const stage of [{version:3},{version:4,kind:'foreign'},
    {version:4,kind:'arctic-qualified-artifact-application-consumption-v1',issue:999}]) {
    await assert.rejects(()=>consumeQualifiedArcticArtifacts({root,stage,selection:{},restoredReceipt:{},currentExecution:{}}));rejected++;
  }
  assert.equal(opens,0,'Invalid route must reject before artifact body reads');
} finally {
  fs.openSync=open;
  for(const [name,value] of [['WORLDATLAS_PACKAGE_STAGE',previous.stage],['WORLDATLAS_PACKAGE_SOURCE_ROOT',previous.source]]) {
    if(value===undefined)delete process.env[name];else process.env[name]=value;
  }
  fs.rmdirSync(source);
}
console.log(JSON.stringify({actual_imported_invocations:originalInvocations,planless_originals:planless,
  actual_private_identity_and_entry_rejections:rejected,invalid_entry_body_opens:opens,
  scientific_producers_invoked:false,actual_complete_normal_caller_executed:false}));
