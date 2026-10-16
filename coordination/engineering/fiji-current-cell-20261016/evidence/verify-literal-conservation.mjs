import fs from 'node:fs';import assert from 'node:assert/strict';import path from 'node:path';import {fileURLToPath} from 'node:url';
import {pinReader} from '../../../../scripts/prepare-delivery-handoff.mjs';
export function verifyLiteralConservation(base='ab0d2088bc66e0d9847b273eb8519a92c0f109b1',composition='composition-001'){
const r=pinReader(process.cwd()),prefix='coordination/engineering/fiji-current-cell-20261016/';
const sel=r.json(r.pin(base,'data/ownership-selection.json')),side=r.json(r.pin(base,sel.additive_release.path));
const old=r.json(side.logical_asset_map.ledger),oldPatch=r.json(side.logical_asset_map.patch),oldReg=r.json(side.authority_registry);
const read=name=>JSON.parse(fs.readFileSync(prefix+name));
const ledger=read(composition+'/selected-ledger.json'),patch=read(composition+'/patch.json'),reg=read(composition+'/authority-registry.json');
const ctor=read('native-001/constructor-result.json'),native=read('original-native-patch.json');
const constructorPin=r.pin('0dc80808373b6437877933e808572792ab61bc6b',prefix+'native-001/constructor-result.json');
assert.deepEqual(fs.readFileSync(prefix+'native-001/constructor-result.json'),r.read(constructorPin),'Original constructor bytes differ');
for(const row of old.rows)assert.deepEqual(ledger.rows.find(n=>n.component_id===row.component_id&&n.authority_sha256===row.authority_sha256),row);
for(const entry of oldReg.entries)assert.deepEqual(reg.entries.find(n=>n.authority_sha256===entry.authority_sha256),entry);
const oldIds=new Set(old.rows.map(row=>row.authority_sha256+':'+row.component_id)),added=ledger.rows.filter(row=>!oldIds.has(row.authority_sha256+':'+row.component_id));
assert.equal(added.length,15);assert.equal(ctor.ledger_rows.length,15);
for(const row of ctor.ledger_rows){const selected=added.find(n=>n.component_id===row.component_id);const {authority_sha256,rule_sha256,...original}=selected;assert.deepEqual(original,row);}
const canonical=rows=>rows.map(({y,runs})=>({y,runs:runs.map(r=>r.slice())}));
const union=rows=>{const map=new Map();for(const row of rows){const runs=map.get(row.y)??[];runs.push(...row.runs);map.set(row.y,runs);}return [...map].sort((a,b)=>a[0]-b[0]).map(([y,runs])=>{const merged=[];for(const run of runs.sort((a,b)=>a[0]-b[0])){const prior=merged.at(-1);assert.ok(!prior||prior[1]<=run[0]);if(prior&&prior[1]===run[0]&&prior[2]===run[2])prior[1]=run[1];else merged.push([...run]);}return {y,runs:merged};});};
assert.deepEqual(union([...canonical(oldPatch.rows),...canonical(native.rows)]),canonical(patch.rows));
const count=rows=>rows.reduce((n,row)=>n+row.runs.reduce((n,r)=>n+r[1]-r[0],0),0);
assert.equal(count(patch.rows)-count(oldPatch.rows),3963);
assert.deepEqual(JSON.parse(fs.readFileSync('data/ownership-selection.json')).reference_projection,sel.reference_projection);
const report={version:1,baseline:base,source_constructor_commit:constructorPin.commit,
 inherited_ledger_rows:old.rows.length,added_ledger_rows:added.length,inherited_authorities:oldReg.entries.length,added_authorities:reg.entries.length-oldReg.entries.length,
 inherited_literal_rows_unchanged:true,inherited_authorities_unchanged:true,exact_patch_union:true,prior_native_cells:count(oldPatch.rows),added_native_cells:count(native.rows),final_native_cells:count(patch.rows),metadata_projection_unchanged:true,
 limitations:['Literal composition and source qualification; hosted selected consumer and emitted smoke remain required.']};
return report;
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const report=verifyLiteralConservation(process.argv[2],process.argv[3]);
 const retained=process.argv[4]??'coordination/engineering/fiji-current-cell-20261016/literal-conservation.json';
 assert.deepEqual(JSON.parse(fs.readFileSync(retained)),report,'Retained whole report differs');console.log(report);
}
