import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import assert from 'node:assert/strict';
import {inventoryRows,joinInventoryFacts,restoreInventoryRow,candidateDisposition,admitInventoryDestination} from '../scripts/additive-gap-repair.mjs';
import {footprintValueSha256 as hash} from '../src/effective-footprint.js';
const row=(id,status='mapped-land-support')=>({component_id:id,candidate_feature_sha256:hash(id),candidate_geometry_sha256:hash([id]),status,
 physical_authority:'unapproved',physical_status:'unknown-source-fitness-and-observation-date',physical_limits:['original retained source limits'],complete_support:{whole_original_geometry:true}});
const all=[row('one'),row('water','mapped-inland-water-support'),row('mixed','mixed-source-support'),row('unknown','unknown')];
const roster=rows=>hash(rows.map(r=>({id:r.component_id,feature_sha256:r.candidate_feature_sha256})));
const parent={version:1,components:4,report_sha256:'a'.repeat(64),roster_sha256:roster(all)};
const source={commit:'b'.repeat(40),path:'original.gz',sha256:'c'.repeat(64)};
const rawRows=rows=>rows.map(row=>Buffer.from(JSON.stringify(row)+'\n'));
const child=rows=>inventoryRows(rows,{source,parent,expectedIds:rows.map(r=>r.component_id),expectedRosterSha256:roster(rows),originalRecordBytes:rawRows(rows)});
test('all provisional candidates preserved exactly once; land is not repair permission, water rejected',()=>{
 const one=child(all.slice(0,2)),two=child(all.slice(2)); const result=joinInventoryFacts([one,two],parent);
 assert.equal(result.components,4);assert.deepEqual(result.counts,{eligible:0,assigned:0,'zero-cell':0,rejected:1,'awaiting-evidence':3});
 all.forEach((r,i)=>assert.equal(restoreInventoryRow(child(all).rows[i],all,source,rawRows(all)),r));
 assert.equal(candidateDisposition({...all[0],approved:true}).disposition,'awaiting-evidence');
});
test('whole original roster/alias and parent joins reject omission, duplicate, order and coherent field drift',()=>{
 assert.throws(()=>joinInventoryFacts([child(all.slice(0,2))],parent),/Incomplete/);
 assert.throws(()=>joinInventoryFacts([child(all),child(all)],parent),/Duplicate/);
 assert.throws(()=>joinInventoryFacts([child(all.slice(2)),child(all.slice(0,2))],parent),/reordered/);
 assert.throws(()=>inventoryRows([all[0],all[0]],{source,parent,expectedIds:['one','two'],expectedRosterSha256:roster(all),originalRecordBytes:rawRows([all[0],all[0]])}),/duplicate/);
 assert.throws(()=>inventoryRows(all.slice(1),{source,parent,expectedIds:all.map(r=>r.component_id),expectedRosterSha256:roster(all),originalRecordBytes:rawRows(all.slice(1))}),/Missing/);
 const alias=child(all).rows[0],changed=structuredClone(all);changed[0].complete_support.whole_original_geometry=false;
 assert.throws(()=>restoreInventoryRow(alias,changed,source,rawRows(all)),/inverse/);
 assert.throws(()=>restoreInventoryRow(alias,all,{...source,commit:'d'.repeat(40)},rawRows(all)),/source/);
 const wrong=child(all);wrong.facts.counts.assigned=1;assert.throws(()=>joinInventoryFacts([wrong],parent),/totals/);
});


test('output collision, dangling link and foreign parent rejected before acquisition; sentinels preserved',()=>{
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'additive-admission-fixture-'));
 try {
  fs.mkdirSync(path.join(directory,'.cache','native-grid-candidates'),{recursive:true});
  const target=path.join(directory,'.cache','native-grid-candidates','existing');fs.writeFileSync(target,'sentinel');
  assert.throws(()=>admitInventoryDestination(directory,'.cache/native-grid-candidates/existing'),/collision/);
  assert.equal(fs.readFileSync(target,'utf8'),'sentinel');
  fs.symlinkSync('missing',path.join(directory,'.cache','native-grid-candidates','dangling'));
  assert.throws(()=>admitInventoryDestination(directory,'.cache/native-grid-candidates/dangling'),/collision/);
  assert.equal(fs.readlinkSync(path.join(directory,'.cache','native-grid-candidates','dangling')),'missing');
  fs.rmSync(path.join(directory,'.cache','native-grid-candidates'),{recursive:true});
  fs.symlinkSync(os.tmpdir(),path.join(directory,'.cache','native-grid-candidates'));
  assert.throws(()=>admitInventoryDestination(directory,'.cache/native-grid-candidates/new'),/symlink/);
 } finally {fs.rmSync(directory,{recursive:true,force:true});}
});
