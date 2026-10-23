import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {validateDeliveryExpectations} from '../../../../scripts/selected-delivery-smoke.mjs';
import {footprintValueSha256} from '../../../../src/effective-footprint.js';
const p='coordination/engineering/sweden-germany-selected-delivery-20261017/';
const bytes=fs.readFileSync(p+'composition-001/selected-ledger.json'), ledger=JSON.parse(bytes);
const e=validateDeliveryExpectations(JSON.parse(fs.readFileSync(p+'selected-delivery-expectations.json')));
assert.equal(createHash('sha256').update(bytes).digest('hex'),e.selected_ledger_sha256);
const rows=ledger.rows.filter(r=>['assigned','zero-cell'].includes(r.disposition)), covered=new Set();
for(const c of e.cohorts) for(const m of c.members){
 const authority=/^retained-authority-scope:([a-f0-9]{64})$/.exec(c.original_batch_id)?.[1];
 const matches=rows.filter(r=>r.component_id===m.component_id&&(!authority||r.authority_sha256===authority));assert.equal(matches.length,1);
 const r=matches[0];assert(!covered.has(r));covered.add(r);
 for(const k of ['target_id','disposition'])assert.equal(r[k],m[k]);
 const native=Object.hasOwn(m,'native_rows_sha256');assert.equal(footprintValueSha256(native?r.native_rows:r.geometry),m[native?'native_rows_sha256':'geometry_sha256']);
}
assert.equal(covered.size,rows.length);assert.equal(e.cumulative_native_cells,6073797);
const result={kind:'actual-expectation-representation-only',selected_ledger_sha256:e.selected_ledger_sha256,cohorts:e.cohorts.length,members:covered.size,cumulative_native_cells:e.cumulative_native_cells,limits:['This validates actual selected ledger representation, not emitted browser consumers or current owner-zero acceptance.']};
fs.writeFileSync(process.argv[2],JSON.stringify(result)+'\n',{flag:'wx'});console.log(result);
