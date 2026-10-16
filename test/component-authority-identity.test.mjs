import test from 'node:test';
import fs from 'node:fs';
import vm from 'node:vm';
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

// Exercise the exact private-boundary functions without adding production test
// exports or constructing an apparent scientific execution. Only their completed
// prior/authority inputs are fixtures; normalization and conservation are real.
const demand=(value,message)=>{if(!value)throw Error(message);};
const same=(a,b)=>valueSha(a)===valueSha(b);
function sourceFunction(file,name,end,context) {
  const source=fs.readFileSync(file,'utf8'),start=source.indexOf('function '+name+'('),stop=source.indexOf(end,start);
  assert.ok(start>=0&&stop>start);
  return vm.runInNewContext('('+source.slice(start,stop).trim()+')',context);
}
test('private prior conservation resolves both v1 generations and retains colliding v2 authorities',()=>{
  const f=fixture(),registry={...f.registry,entries:[f.entries[0]]};
  const {authority_sha256,rule_sha256,...row}=f.rows[0];
  const exception={component_id:'zz-rejected',disposition:'rejected',reason:'original'};
  const ledger={version:1,kind:'native-additive-repair-ledger-v1',rule_sha256,scope_ids:[row.component_id,exception.component_id],rows:[row,exception]};
  const prior={ledger,registry},snapshot={selection:{additive_release:{}},additive:prior},selectedAdditions=new WeakMap([[prior,{snapshot}]]);
  const conserve=sourceFunction('coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs','requirePriorAdditiveConservation','\n// Literal historical',{selectedAdditions,demand,same,repairComponentKey,compareVersionedRepairLedgers});
  assert.equal(conserve(snapshot,registry,ledger).prior_components,1);
  const next={...f.ledger,rows:[...f.rows,{...exception,authority_sha256,rule_sha256}],scope_ids:[...f.ledger.scope_ids,exception.component_id]};
  assert.equal(conserve(snapshot,f.registry,next).prior_components,1);
  for(const after of [ledger,next]){
    const changed=structuredClone(after);changed.rows.at(-1).reason='changed';
    assert.throws(()=>conserve(snapshot,after===ledger?registry:f.registry,changed),/complete row or exception changed/);
  }
  assert.throws(()=>conserve({...snapshot},registry,ledger),/privately consumed/);
  const wrong={...next,rows:next.rows.slice(1),scope_ids:next.scope_ids.slice(1)};
  assert.throws(()=>conserve(snapshot,f.registry,wrong),/lost\/rebound/);
});
test('current rebind original operands preserve authority-scoped equal labels and reject substitutions',()=>{
  const f=fixture(),proofs=f.rows.map(row=>{
    const {authority_sha256,rule_sha256,...original}=row;
    return {authority_sha256,rule_sha256,original_ledger:{rows:[original]},native_proof:{native_patches:[{rows:row.native_rows}]}};
  });
  const originalOperands=sourceFunction('coordination/engineering/additive-native-composition-20261009/capture-current-rebind.mjs','originalOperands','\n// Ephemeral',{normaliseRetainedRepairLedger,repairComponentKey,demand,same,completedOriginalAuthority:(_,entry)=>proofs.find(proof=>proof.authority_sha256===entry.authority_sha256)});
  const result=originalOperands({},f.registry,f.ledger);
  assert.deepEqual(JSON.parse(JSON.stringify(result.rows)),f.rows);assert.equal(result.patches.length,2);
  const changed=structuredClone(f.ledger);changed.rows[1].source_receipt_sha256='0'.repeat(64);
  assert.throws(()=>originalOperands({},f.registry,changed),/changes original/);
  const omitted={...f.ledger,rows:[f.rows[0]],scope_ids:[f.rows[0].component_id]};
  assert.throws(()=>originalOperands({},f.registry,omitted),/changes original/);
});
