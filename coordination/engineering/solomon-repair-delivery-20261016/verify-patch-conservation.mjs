import fs from 'node:fs';
import assert from 'node:assert/strict';
import {pinReader,jsonBytes} from '../../../scripts/prepare-delivery-handoff.mjs';
const r=pinReader(process.cwd()),base='a5f0214a899db981c5e5c0a6974aa8d3a76e1b41',head=process.argv[2]??'f747d6de3c43ff1253fdf2e7c6f7a5915c7ee0c4',p='coordination/engineering/solomon-repair-delivery-20261016';
function state(c){const selector=r.pin(c,'data/ownership-selection.json'),s=r.json(selector),sidecar=r.json(r.pin(c,s.additive_release.path));return {selector,sidecar,patch:r.json(sidecar.logical_asset_map.patch),ledger:r.json(sidecar.logical_asset_map.ledger),registry:r.json(sidecar.authority_registry)};}
const before=state(base),after=state(head),request=r.json(r.pin(head,p+'/source-stage/native-patch.json'));
function cells(patch){const m=new Map();for(const row of patch.rows)for(const [a,z,o]of row.runs)for(let x=a;x<z;x++){const k=row.y+':'+x;assert(!m.has(k));m.set(k,o);}return m;}
const old=cells(before.patch),next=cells(after.patch),delta=cells(request);for(const [k,o]of old)assert.equal(next.get(k),o);
for(const [k,o]of delta){assert(!old.has(k));assert.equal(next.get(k),o);}
assert.equal(next.size,old.size+delta.size);assert.equal(delta.size,3925);
const literal=val=>jsonBytes(val).toString();for(const row of before.ledger.rows)assert(after.ledger.rows.some(x=>literal(x)===literal(row)));
for(const entry of before.registry.entries)assert(after.registry.entries.some(x=>literal(x)===literal(entry)));
const result={version:1,baseline_commit:base,evaluation_commit:head,request:r.pin(head,p+'/source-stage/native-patch.json'),baseline_selector:before.selector,candidate_selector:after.selector,
requested_cells:delta.size,prior_cells:old.size,proposed_cumulative_cells:next.size,assigned_cells:delta.size,removed_cells:0,reassigned_cells:0,overlap_with_prior_cells:0,
prior_ledger_rows:before.ledger.rows.length,proposed_ledger_rows:after.ledger.rows.length,added_ledger_rows:after.ledger.rows.length-before.ledger.rows.length,
prior_authorities:before.registry.entries.length,proposed_authorities:after.registry.entries.length,added_authorities:after.registry.entries.length-before.registry.entries.length,
per_owner:[...new Set(delta.values())].sort((a,b)=>a-b).map(owner=>({owner,cells:[...delta.values()].filter(o=>o===owner).length})),
limits:['Exact immutable patch/ledger conservation only. Actual current owner zero is established separately by selected-native verification. Counts are proposed until verified repository merge; publication remains separate.']};
console.log(JSON.stringify(result));
