import test from 'node:test';
import assert from 'node:assert/strict';
import {currentRebindResult,valueSha} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
test('current rebind recomputes owner and original polygon preservation after generation guard removal',()=>{
 const polygon=x=>({type:'Polygon',coordinates:[[[x,0],[x+1,0],[x+1,1],[x,0]]]}),base=polygon(0),primitive=polygon(2);
 const input={baseSelection:{version:1},registry:{version:1},size:16,
  originalRows:[{component_id:'new',target_id:'A',pixelIndex:1,disposition:'assigned',base_geometry:base,base_geometry_sha256:valueSha(base),geometry:primitive,geometry_sha256:valueSha(primitive)}],
  originalPatches:[{version:1,kind:'unassigned-native-cells-v1',rows:[{y:3,runs:[[4,5,1]]}]}],
  currentTargets:[{target_id:'A',pixelIndex:1,geometry:base,geometry_sha256:valueSha(base)}],currentRows:[{y:3,runs:[[0,2,2]]}]};
 const result=currentRebindResult(input);assert.equal(result.native.assigned_cells,1);
 assert.deepEqual(result.native.effective_rows,[{y:3,runs:[[0,2,2],[4,5,1]]}]);
 const occupied=structuredClone(input);occupied.currentRows[0].runs.push([4,5,2]);assert.throws(()=>currentRebindResult(occupied),/already owned/);
 const rebound=structuredClone(input);rebound.currentTargets[0].pixelIndex=2;assert.throws(()=>currentRebindResult(rebound),/identity differs/);
 const missing=structuredClone(input);missing.currentRows=[];assert.throws(()=>currentRebindResult(missing),/Missing complete current native row/);
 const altered=structuredClone(input);altered.currentTargets[0].geometry=polygon(8);altered.currentTargets[0].geometry_sha256=valueSha(altered.currentTargets[0].geometry);
 assert.throws(()=>currentRebindResult(altered),/loses\/rebuilds an original full polygon group/);
});
