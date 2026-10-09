import assert from 'node:assert/strict';
import {sumCompleteOwnerRuns} from './pixel-area-order.mjs';

// Finished predecessor groups contain the complete original-order target runs.
// This join changes no ownership words and performs no geometry operation.
export function joinPixelAccounting(groups, originalPixel) {
 assert.equal(groups.length,28);
 assert.equal(originalPixel.locations,49625);assert.equal(originalPixel.records.length,49625);
 const ids=new Set(originalPixel.records.map(r=>r.id));assert.equal(ids.size,49625);
 const targets=[6666,6757],before=[],after=[];
 for(let ordinal=0;ordinal<groups.length;ordinal++) {
  const group=groups[ordinal];
  for(const side of ['before','after']) {
   const value=group[side];assert.equal(value.ordinal,ordinal);assert.equal(value.side,side);
   assert.equal(value.kind,'complete-native-target-run-accounting-group');
   assert.equal(value.total_groups,28);assert.equal(value.full_run_parts,55);
   assert.equal(value.full_row_count,262166);assert.equal(value.owner_count,49625);
   assert.equal(value.total_run_words,57617774);assert.deepEqual(value.target_owners,targets);
   assert.equal(value.grid_rows_computed,0);assert.equal(value.activated,false);
   (side==='before'?before:after).push(...value.parts);
  }
  assert.deepEqual(group.before.parts.map(p=>[p.offset,p.words]),group.after.parts.map(p=>[p.offset,p.words]));
 }
 assert.equal(before.length,55);assert.equal(after.length,55);
 const options={size:262166,totalRunWords:57617774,targetOwners:targets};
 const old=sumCompleteOwnerRuns(before,options),current=sumCompleteOwnerRuns(after,options);
 const expected={6666:{id:'atlas:physical:CAN-15:NWT',gain:140},6757:{id:'atlas:physical:CAN-25:NUN',gain:1}};
 const records=targets.map(owner=>{
  const installed=originalPixel.records.find(r=>r.id===expected[owner].id);assert(installed);
  assert.equal(installed.id,expected[owner].id);assert.equal(installed.owner,'Canada');
  assert.equal(old[owner].cells,installed.cells,'Original complete target cell count');
  assert.equal(Number(old[owner].grid_wgs84_area_m2.toFixed(6)),installed.grid_wgs84_area_m2,
   'Original complete target area in stock accumulation order');
  assert.equal(current[owner].cells-old[owner].cells,expected[owner].gain);
  return {id:installed.id,owner,original:old[owner],current:current[owner],
   original_stored_area_m2:Number(old[owner].grid_wgs84_area_m2.toFixed(6)),
   current_stored_area_m2:Number(current[owner].grid_wgs84_area_m2.toFixed(6)),
   added_cells:expected[owner].gain};
 });
 return {version:1,kind:'complete-original-order-two-target-pixel-accounting',
  groups:28,run_parts:55,run_words:57617774,rows:262166,owners:49625,
  records,added_cells:141,removed_cells:0,grid_rows_computed:0,activated:false};
}
