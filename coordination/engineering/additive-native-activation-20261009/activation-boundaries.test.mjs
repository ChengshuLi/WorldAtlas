import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {prepareSupportedRebindPlan} from './prepare-supported-rebind-plan.mjs';
import {prepareChoiseulNativeInputs} from './prepare-choiseul-native-inputs.mjs';
import {assembleSupportedActivation} from './assemble-supported-activation.mjs';
import {nativeBaseSelection,requirePriorAdditiveConservation,normaliseRetainedRepairLedger} from '../selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';

test('native base extraction removes only the additive hook and preserves all selected artifact fields',()=>{
  const base={version:1,manifest_path:'x/manifest.json',method:'native-linear-evenodd-first-owner-v1',
    sha256:'1'.repeat(64),release_id:'geography:review:x',selected_geography:{path:'x/source.json'},
    artifact_consumption:{path:'x/certificate.json'}};
  const selected={...base,additive_release:{path:'x/hook.json',bytes:1,sha256:'2'.repeat(64)}};
  assert.deepEqual(nativeBaseSelection(selected),base);assert.ok(selected.additive_release);
  assert.deepEqual(nativeBaseSelection(base),base);assert.throws(()=>nativeBaseSelection(null));
});
test('prior conservation rejects a forged view even if its ledger and registry look complete',()=>{
  assert.throws(()=>requirePriorAdditiveConservation({selection:{additive_release:{}},
    additive:{ledger:{rows:[]},registry:{entries:[]}}},{entries:[]},{rows:[]}),/privately consumed/);
});

test('no public preparation or publication entry accepts an invented selected identity',()=>{
  const snapshot={manifest:{size:262166},owners:[]};
  assert.throws(()=>prepareSupportedRebindPlan({reader:{},snapshot}),/actual selected immutable reader/i);
  assert.throws(()=>prepareChoiseulNativeInputs(snapshot),/authenticated selected snapshot/);
  assert.throws(()=>assembleSupportedActivation({snapshot,baseAssets:{base_manifest:{},owner_roster:{}},
    logicalPaths:{ledger:'additive-repairs/ledger.json',patch:'additive-repairs/patch.json'}}),/authenticated selected snapshot/);
});
test('publication rejects foreign logical asset paths before selected acquisition',()=>{
  for(const path of ['../ledger.json','x\\ledger.json','/absolute.json','x//ledger.json'])
    assert.throws(()=>assembleSupportedActivation({snapshot:{},baseAssets:{base_manifest:{},owner_roster:{}},
      logicalPaths:{ledger:path,patch:'additive-repairs/patch.json'}}),/safe new logical paths/);
});
test('retained complete metadata binds twelve supported components, seven targets and all eight exceptions',()=>{
  const description=JSON.parse(fs.readFileSync(new URL('./retained-activation-inputs.json',import.meta.url)));
  const bindings=JSON.parse(fs.readFileSync(new URL('./original-target-source-bindings.json',import.meta.url)));
  const git=process.platform==='darwin'?'/Library/Developer/CommandLineTools/usr/bin/git':'/usr/bin/git';
  const values=description.original_inputs.map(pin=>{
    const line=execFileSync(git,['ls-tree',pin.commit,'--',pin.path],{encoding:'utf8'}).trim();
    assert.equal(line,`${pin.mode} blob ${pin.git_blob_oid}\t${pin.path}`);
    assert.equal(Number(execFileSync(git,['cat-file','-s',pin.git_blob_oid])),pin.bytes);
    assert.ok(pin.bytes<=33554432);
    const bytes=execFileSync(git,['show',pin.commit+':'+pin.path],{maxBuffer:33554432});
    assert.equal(bytes.length,pin.bytes);assert.equal(createHash('sha256').update(bytes).digest('hex'),pin.sha256);
    return JSON.parse(bytes);
  });
  const [registry,ledger]=values,rows=[...normaliseRetainedRepairLedger(ledger,registry).rows.values()];
  assert.deepEqual(ledger.scope_ids,description.original_scope_ids);
  assert.deepEqual(rows.map(r=>r.component_id),description.supported_scope_ids);
  assert.equal(ledger.rows.length,20);assert.equal(rows.length,12);
  assert.equal(ledger.rows.filter(r=>!['assigned','zero-cell'].includes(r.disposition)).length,8);
  assert.equal(new Set(rows.map(r=>r.target_id)).size,7);
  assert.deepEqual(new Set(bindings.source_bindings.map(p=>p.target_id)),new Set(rows.map(r=>r.target_id)));
  assert.equal(rows.reduce((n,r)=>n+r.native_cells,0),141);
});
