import fs from 'node:fs';import assert from 'node:assert/strict';
import {ImmutableReader,loadBaseSelection,loadNativeRowTable,acquireNativeRows} from '../../../../scripts/check-effective-geographic-regression.mjs';
const baseline='ab0d2088bc66e0d9847b273eb8519a92c0f109b1',prefix='coordination/engineering/fiji-current-cell-20261016/';
const requested=JSON.parse(fs.readFileSync(prefix+'original-native-patch.json'));
const reader=new ImmutableReader(process.cwd(),baseline),snapshot=loadBaseSelection(reader);
console.log('authenticated selected base');
const table=loadNativeRowTable(snapshot),rows=requested.rows.map(r=>r.y);
const native=acquireNativeRows(snapshot,table,rows);let checked=0;
for(let k=0;k<requested.rows.length;k++)for(const [a,z]of requested.rows[k].runs){
 for(let i=native.offsets[k];i<native.offsets[k+1];i+=3)assert.ok(native.words[i+1]<=a||native.words[i]>=z,'Claim touches original occupied native interval');
 checked+=z-a;
}
const side=reader.json(snapshot.selection.additive_release.path,{expected:snapshot.selection.additive_release.sha256});
const p=side.logical_asset_map.patch,patch=reader.json(p.path,{version:p.commit,expected:p.sha256});const byRow=new Map(patch.rows.map(r=>[r.y,r.runs]));
for(const row of requested.rows)for(const [a,z]of row.runs)for(const [p,q]of byRow.get(row.y)??[])assert.ok(q<=a||p>=z,'Claim touches current additive interval');
assert.equal(checked,3963);
const report={version:1,baseline,original_native_cells_checked:checked,native_rows_checked:rows.length,
 native_base_manifest_sha256:snapshot.selection.sha256,original_base_overlap_cells:0,current_additive_overlap_cells:0,
 whole_native_parts:native.custody.whole_parts.map(p=>({path:p.path,bytes:p.bytes,sha256:p.sha256,decoded_sha256:p.decoded_sha256})),
 limitations:['Bounded actual selected base and cumulative-patch owner-zero proof; hosted final consumer and smoke remain required.']};
fs.writeFileSync(prefix+'bounded-current-owner-zero.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({checked,rows:rows.length,parts:report.whole_native_parts.length}));
