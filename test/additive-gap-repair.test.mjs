import fs from 'node:fs';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import assert from 'node:assert/strict';
import {retainedLandSourcePremises,wholePrimitivePointsetEqual,inventoryRows,joinInventoryFacts,restoreInventoryRow,candidateDisposition,admitInventoryDestination,selectedBankResolutions,inventoryGroup,restoreGroupedInventoryRow} from '../scripts/additive-gap-repair.mjs';
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
 assert.equal(result.components,4);assert.deepEqual(result.counts,{eligible:0,assigned:0,'zero-cell':0,'already-resolved':0,rejected:1,'awaiting-evidence':3});
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


test('selected baseline accepted repairs remain resolved/idempotent; stale target and unverified resolution maps reject',()=>{
 const geometry={type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,0]]]};
 const correction={component_id:'one',subject_id:'target',component_geometry_sha256:all[0].candidate_geometry_sha256,
  geometry_sha256_after:hash(geometry),pointsets:{new:geometry},historical_transfer:'none'};
 const manifest={version:2,method:'native-linear-evenodd-first-owner-v1',accounting:{owners:49625},footprints_sha256:'a'.repeat(64),
  provenance:{source_migration:{history_transfer:'none',after_footprints_sha256:'a'.repeat(64),changed_ids:['target']}}};
 const args={features:[{id:'target',geometry}],corrections:[correction],selectedManifest:manifest,
  selectionReceipt:{method:manifest.method,owners:49625,unchecked_cells:0,products:[{path:'manifest.json',sha256:'b'.repeat(64)}]},
  selectedManifestSha256:'b'.repeat(64),bankDecodedSha256:'c'.repeat(64),expectedBankDecodedSha256:'c'.repeat(64)};
 const resolutions=selectedBankResolutions(args);
 for(let i=0;i<2;i++)assert.equal(candidateDisposition(all[0],resolutions).disposition,'already-resolved');
 assert.throws(()=>candidateDisposition(all[0],new Map()),/Unverified/);
 assert.throws(()=>selectedBankResolutions({...args,bankDecodedSha256:'d'.repeat(64)}),/Stale/);
 const changed=structuredClone(args);changed.features[0].geometry=structuredClone(changed.features[0].geometry);changed.features[0].geometry.coordinates[0][1][0]=2;
 assert.throws(()=>selectedBankResolutions(changed),/full target/);
 assert.throws(()=>candidateDisposition({...all[0],candidate_geometry_sha256:'e'.repeat(64)},resolutions),/pointset/);
});


test('bounded groups join every original identity and preserve two-level complete inverse',()=>{
 const group1=inventoryGroup([child(all.slice(0,2))],parent),group2=inventoryGroup([child(all.slice(2))],parent);
 const final=inventoryGroup([group1,group2],parent,{complete:true});
 assert.equal(final.facts.components,all.length);
 for(const row of final.rows){const grouped=restoreGroupedInventoryRow(row,[group1,group2]);
  const groupIndex=row.original_ledger.stage;
  const original=restoreGroupedInventoryRow(grouped,[child(groupIndex===0?all.slice(0,2):all.slice(2))]);
  assert.equal(original.component_id,row.component_id);
 }
 assert.throws(()=>inventoryGroup([group1],parent,{complete:true}),/Incomplete/);
 assert.throws(()=>inventoryGroup([group1,group1],parent,{complete:true}),/Duplicate/);
 assert.throws(()=>inventoryGroup([group2,group1],parent,{complete:true}),/reordered/);
 const wrong=structuredClone(group1);wrong.rows[0].source_relative_category='unknown';
 assert.throws(()=>inventoryGroup([wrong,group2],parent,{complete:true}),/counts/);
 assert.throws(()=>restoreGroupedInventoryRow({...final.rows[0],disposition:'assigned'},[group1,group2]),/inverse/);
});


test('actual whole source-supported shared-edge pilot derives source premises without producer approval flags',()=>{
 const root='coordination/engineering/additive-native-gap-repair-20261008/source-supported-pilot/';
 const roster=JSON.parse(fs.readFileSync(root+'original-input-roster.json'));
 const read=name=>{const raw=fs.readFileSync(root+name),pin=roster.inputs.find(pin=>pin.retained_copy.endsWith('/'+name));
  assert.ok(pin);assert.equal(raw.length,pin.bytes);assert.equal(createHash('sha256').update(raw).digest('hex'),pin.sha256);
  const decoded=name.endsWith('.gz')?gunzipSync(raw):raw;assert.equal(decoded.length,pin.decoded_bytes);
  assert.equal(createHash('sha256').update(decoded).digest('hex'),pin.decoded_sha256);return decoded;};
 const pilot=JSON.parse(read('add031-construction-failure.json')),scope=JSON.parse(read('source-fit-seven-cases.json'));
 const sourceCase=scope.results.find(row=>row.component_id===pilot.component_id);
 const record=read('original-scientific-products/components-047.jsonl.gz').toString().trimEnd().split('\n').map(JSON.parse).find(row=>row.component_id===pilot.component_id);
 const input={record,candidate:pilot.candidate,sourceCase,sourceScope:scope,target:pilot.before};
 const facts=retainedLandSourcePremises(input);assert.equal(facts.source_compatible,true);assert.equal(facts.authority,'unapproved');assert.equal(facts.status,record.physical_status);
 const originalGeometry=JSON.stringify(pilot.before.geometry);assert.equal(wholePrimitivePointsetEqual(record.complete_support.mapped_land_support.geometry,pilot.candidate),true);
 for(const alter of [x=>x.record.status='mapped-inland-water-support',x=>x.record.complete_support.mapped_inland_water_support.geometry={type:'Polygon',coordinates:pilot.candidate.coordinates},
  x=>x.sourceScope.active_feature_count--,x=>x.sourceCase.native_covering_named_envelopes.push(x.sourceCase.native_covering_named_envelopes[0]),
  x=>x.sourceCase.new_neighbor_intersections=[{id:'foreign',geometry:pilot.candidate}],x=>x.target.properties.parent_id='foreign',
  x=>x.sourceCase.retired_administrative_reference_context.pop(),x=>x.sourceCase.gain_candidate_symmetric_difference_area_deg2=1e-16]){
  const changed=structuredClone(input);alter(changed);assert.equal(retainedLandSourcePremises(changed).source_compatible,false);
 }
 const foreign=structuredClone(input);foreign.record.component_id='foreign';assert.throws(()=>retainedLandSourcePremises(foreign),/component join/);
 assert.equal(JSON.stringify(pilot.before.geometry),originalGeometry);
 // Neither these premises nor the independent source PASS labels release cells:
 assert.equal(candidateDisposition(record).disposition,'awaiting-evidence');
});
