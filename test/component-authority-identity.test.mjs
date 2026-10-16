import test from 'node:test';
import assert from 'node:assert/strict';
import {repairComponentKey, compareRepairComponents} from '../src/native-grid.js';
import {valueSha, normaliseRetainedRepairLedger, compareVersionedRepairLedgers} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
import {deriveCoordinateDelta} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint.mjs';
import {newVisibleRepairCandidates, repairVisibilityWitnesses} from '../scripts/check-effective-geographic-regression.mjs';
import {bindAdditiveLedgerFeatures, verifyAdditiveLedgerSelection, additiveReleaseFootprintDigest, effectiveNativeAdditionRows} from '../src/effective-footprint.js';
import {fixtures} from './fixtures/selected-checkpoint.mjs';

function fixture() {
  const {features, certificate} = fixtures(), geometry = features[0].geometry;
  const pin = name => ({commit:'1'.repeat(40),path:name,mode:'100644',git_blob_oid:'2'.repeat(40),bytes:1,sha256:'3'.repeat(64)});
  const entry = name => {
    const body = {policy_id:'retained-source-literal-additions',policy_version:1,rule_preimage:pin(name+'/rule.json'),
      rule_sha256:'3'.repeat(64),source_authority:pin(name+'/binding.json')};
    return {authority_sha256:valueSha(body),...body};
  };
  const entries = [entry('first'),entry('second')].sort((a,b)=>a.authority_sha256.localeCompare(b.authority_sha256));
  const rows = entries.map((entry,i)=>({representation:'native-cells',component_id:'source-target:unchanged-original-label',
    target_id:'A',pixelIndex:1,disposition:'assigned',base_geometry:geometry,base_geometry_sha256:valueSha(geometry),
    native_rows:[{y:i+1,runs:[[i+2,i+3,1]]}],native_bounds:[10+i,20,10+i,20],native_cells:1,
    source_receipt_sha256:'4'.repeat(64),authority_sha256:entry.authority_sha256,rule_sha256:entry.rule_sha256}));
  const registry = {version:1,kind:'retained-rule-authority-registry-v1',entries};
  const ledger = {version:2,kind:'native-additive-repair-ledger-v2',authority_registry_sha256:valueSha(registry),
    parent_inventory:{components:0,report_sha256:'5'.repeat(64),roster_sha256:'6'.repeat(64)},
    scope_ids:rows.map(row=>row.component_id),rows};
  return {features,certificate,entries,rows,registry,ledger};
}

test('versioned identity retains equal original labels and conserves exact authority-scoped rows',()=>{
  const f=fixture(), oldRegistry={...f.registry,entries:f.entries.slice(0,1)};
  const old={...f.ledger,authority_registry_sha256:valueSha(oldRegistry),rows:f.rows.slice(0,1),scope_ids:f.ledger.scope_ids.slice(0,1)};
  const normalized=normaliseRetainedRepairLedger(f.ledger,f.registry);
  assert.equal(normalized.rows.size,2);
  for(const row of f.rows) assert.deepEqual(normalized.rows.get(repairComponentKey(row)),row);
  assert.equal(compareVersionedRepairLedgers(old,f.ledger,{beforeRegistry:oldRegistry,afterRegistry:f.registry}).preserved_components,1);
  const {authority_sha256,rule_sha256,...original}=f.rows[0];
  const legacy={version:1,kind:'native-additive-repair-ledger-v1',rule_sha256,scope_ids:[original.component_id],rows:[original]};
  assert.equal(compareVersionedRepairLedgers(legacy,f.ledger,{beforeRegistry:oldRegistry,afterRegistry:f.registry}).preserved_components,1);
  const repeatedLegacy={...legacy,scope_ids:[original.component_id,original.component_id],rows:[{...original,authority_sha256:'a'.repeat(64)},{...original,authority_sha256:'b'.repeat(64)}]};
  assert.throws(()=>normaliseRetainedRepairLedger(repeatedLegacy,oldRegistry),/duplicate/);
  const duplicate={...f.ledger,rows:[f.rows[0],f.rows[0]]};
  assert.throws(()=>normaliseRetainedRepairLedger(duplicate,f.registry),/duplicate/);
  const changed=structuredClone(f.ledger);changed.rows[0].native_rows[0].runs[0]=[10,11,1];
  assert.throws(()=>compareVersionedRepairLedgers(old,changed,{beforeRegistry:oldRegistry,afterRegistry:f.registry}),/lost\/rebound/);
  const before=deriveCoordinateDelta({certificate:f.certificate,oldAdditions:[],additions:[f.rows[0]],selection:{}}).certificate;
  const delta=deriveCoordinateDelta({certificate:before,oldAdditions:[f.rows[0]],additions:f.rows,selection:{next:true}});
  assert.deepEqual(delta.changedIds,['A']);
  assert.equal(delta.certificate.entries[0][8],valueSha({base_geometry_sha256:f.rows[0].base_geometry_sha256,additions:f.rows}));
});

test('browser ledger binding and release digest preserve both same-label native interval sets',()=>{
  const f=fixture(), base={id:'geography:base',footprints_sha256:'7'.repeat(64),hierarchy_sha256:'8'.repeat(64)};
  const ledgerSha=valueSha(f.ledger), release={ledger:{sha256:ledgerSha}};
  const features=bindAdditiveLedgerFeatures(f.features.map((feature,i)=>({...feature,pixelIndex:i+1})),f.ledger,release,base);
  assert.deepEqual(effectiveNativeAdditionRows(features[0]),f.rows.flatMap(row=>row.native_rows));
  const patch={version:2,authority_registry_sha256:f.ledger.authority_registry_sha256,ledger_sha256:ledgerSha,
    base_reference:base,rows:f.rows.flatMap(row=>row.native_rows)};
  assert.deepEqual(verifyAdditiveLedgerSelection(f.ledger,features,patch),{selected_components:2,assigned_cells:2});
  assert.match(additiveReleaseFootprintDigest(base,features),/^[a-f0-9]{64}$/);
  const missing={...patch,rows:patch.rows.slice(0,1)};
  assert.throws(()=>verifyAdditiveLedgerSelection(f.ledger,features,missing),/intervals omitted/);
  const duplicate=structuredClone(features);duplicate[0].additiveFootprint.components=[f.rows[0],f.rows[0]];
  assert.throws(()=>additiveReleaseFootprintDigest(base,duplicate),/unordered/);
});

test('each same-label authority still needs its own actual changed-cell witness',()=>{
  const {rows}=fixture(), beforeRows=rows.map(row=>({y:row.native_rows[0].y,runs:[]}));
  const afterRows=rows.flatMap(row=>row.native_rows);
  assert.deepEqual(newVisibleRepairCandidates([rows[0]],rows),[rows[1]]);
  const inspect=after=>repairVisibilityWitnesses({candidates:rows,size:8,latitudes:new Float64Array(8),beforeRows,afterRows:after});
  const witnesses=inspect(afterRows);
  assert.deepEqual(witnesses.map(repairComponentKey),rows.map(repairComponentKey));
  assert.equal(inspect([afterRows[0],{y:afterRows[1].y,runs:[]}])[1],null);
  assert.throws(()=>newVisibleRepairCandidates([],[rows[0],rows[0]]),/Duplicate/);
  assert.deepEqual([...rows].reverse().sort(compareRepairComponents),rows);
});
