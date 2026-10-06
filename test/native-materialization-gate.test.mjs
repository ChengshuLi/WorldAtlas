import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {requireVerifiedNativeSelection,validateNativeSelectionReceipt} from '../scripts/native-ownership/require-verified-selection.mjs';
const root='coordination/engineering/native-grid-candidate-1010-20261005-local16/';
const bytes=fs.readFileSync(root+'candidate-v1/manifest.json'),manifest=JSON.parse(bytes);
const sha=createHash('sha256').update(bytes).digest('hex');
const receipt=JSON.parse(fs.readFileSync(root+'decoded-native-verification.json'));

test('selected native candidate binds its full-domain, two-run asset proof to immutable reviewed receipt',()=>{
 const proof=requireVerifiedNativeSelection(manifest,sha);
 assert.equal(proof.manifest_sha256,sha);assert.equal(proof.installation_approval,false);
 assert.equal(validateNativeSelectionReceipt(manifest,sha,receipt),true);
});

test('native materialization rejects another candidate, stale source, partial domain and forged product success',()=>{
 assert.throws(()=>requireVerifiedNativeSelection(manifest,'0'.repeat(64)),/registration/);
 for(const delta of [{baseline_commit:'0'.repeat(40)},{preparation_commit:'0'.repeat(40)},
  {checked_rows:manifest.size-1},{unchecked_cells:1},{checked_cells:1},
  {checked_runs:receipt.checked_runs-1},{owners:1},{owned_cells:1},{installation_ready:true}])
  assert.throws(()=>validateNativeSelectionReceipt(manifest,sha,{...receipt,...delta}),/differs/);
 assert.throws(()=>validateNativeSelectionReceipt(manifest,sha,{...receipt,run_two_sha256:'0'.repeat(64)}),/two-run/);
 const missing=structuredClone(receipt);missing.products.pop();
 assert.throws(()=>validateNativeSelectionReceipt(manifest,sha,missing),/two-run/);
 const altered=structuredClone(manifest);altered.parts[0].sha256='0'.repeat(64);
 assert.throws(()=>validateNativeSelectionReceipt(altered,sha,receipt),/assets differ/);
 assert.throws(()=>validateNativeSelectionReceipt(manifest,'0'.repeat(64),receipt),/two-run/);
});


test('rehashed success summaries cannot conceal missing or altered native asset inventory',()=>{
 const rehash=value=>{
  value.two_run_products=value.products.length;
  const digest=createHash('sha256').update(JSON.stringify(value.products)).digest('hex');
  value.run_one_sha256=digest;value.run_two_sha256=digest;return value;
 };
 const omitted=structuredClone(receipt);
 const position=omitted.products.findIndex(p=>p.path.startsWith('native-v1/ownership/'));
 omitted.products.splice(position,1);
 assert.throws(()=>validateNativeSelectionReceipt(manifest,sha,rehash(omitted)),/assets differ/);
 const changed=structuredClone(receipt);
 changed.products[position].sha256='0'.repeat(64);
 assert.throws(()=>validateNativeSelectionReceipt(manifest,sha,rehash(changed)),/assets differ/);
});
