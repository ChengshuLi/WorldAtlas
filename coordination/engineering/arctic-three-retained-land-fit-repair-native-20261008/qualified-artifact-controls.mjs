// Actual imported application API controls. These do not execute scientific
// producers or claim a successful normal build; hosted full callers do that.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {validateOriginalQualificationInvocation, requireConsumedArcticArtifacts,
  consumeQualifiedArcticArtifacts, validateRetainedRegistryPrefixes} from './qualified-artifact-consumer.mjs';
const directory=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(directory,'../../..');
const inventory=JSON.parse(gunzipSync(fs.readFileSync(path.join(directory,'qualified-artifacts/inventory.json.gz'))));
let originalInvocations=0, planless=0, rejected=0;
for(const phase of inventory.complete_phase_inventory) for(const run of phase.runs) {
  validateOriginalQualificationInvocation(phase.phase,run,run.original_invocation.code_source?.original_whole_code_source);
  originalInvocations++;if(!run.complete_original_plans.length)planless++;
}
assert.equal(originalInvocations,171);assert.equal(planless,70);
const certificate=JSON.parse(fs.readFileSync(path.join(directory,'qualified-artifacts/consumption-certificate.json')));
const registryBody=pin=>{
  const raw=fs.readFileSync(path.join(root,pin.path));
  assert.equal(raw.length,pin.bytes);assert.equal(createHash('sha256').update(raw).digest('hex'),pin.sha256);
  const decoded=gunzipSync(raw);assert.equal(decoded.length,pin.decoded_bytes);
  assert.equal(createHash('sha256').update(decoded).digest('hex'),pin.decoded_sha256);
  return JSON.parse(decoded);
};
const registry=registryBody(certificate.registry),originalRegistry=registryBody(certificate.predecessor_registry);
validateRetainedRegistryPrefixes(registry,originalRegistry);
let registryRejections=0;
for(const change of [r=>r.memberships_batches=[],r=>delete r.sources_batches,r=>r.batches.shift(),
  r=>r.releases.shift(),r=>r.releases[0].id='foreign',r=>r.sources_batches[0]='foreign',
  r=>r.batches[0].sha256='0'.repeat(64),r=>r.sources_batches=null]){
  const changed=structuredClone(registry);change(changed);
  assert.throws(()=>validateRetainedRegistryPrefixes(changed,originalRegistry));registryRejections++;
}
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
  actual_complete_registry_positive:1,registry_mutation_rejections:registryRejections,
  actual_private_identity_and_entry_rejections:rejected,invalid_entry_body_opens:opens,
  scientific_producers_invoked:false,actual_complete_normal_caller_executed:false}));
