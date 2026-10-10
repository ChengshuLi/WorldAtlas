import test from 'node:test';
import assert from 'node:assert/strict';
import {nativeRowLatitudes} from '../../../src/native-grid.js';
import {prepareNativeCandidateFrames,prepareSelectedNativeCandidateFrames,selectedOwnerRowsFromProjection,evaluatePreparedNativeCandidates} from './evaluate-native-candidates.mjs';

const rectangle=(a,b,c,d)=>({type:'Polygon',coordinates:[[[a,b],[c,b],[c,d],[a,d],[a,b]]]});
const inputs=(geometry=rectangle(-25,-15,25,15))=>({scopeIds:['component:a'],
  sourceRows:[{component_id:'component:a',target_id:'target:a',pixelIndex:7,source_compatible:true}],
  candidates:[{component_id:'component:a',target_id:'target:a',pixelIndex:7,geometry}],
  latitudes:nativeRowLatitudes(16),size:16});
const execute=(input,owner=[])=>{const frames=prepareNativeCandidateFrames(input);
  return {frames,output:evaluatePreparedNativeCandidates({...input,frames,
    ownerRows:frames.row_ids.map(y=>({y,complete_owner_intervals:owner})),continuousConflicts:[]})};};

test('actual literal operator finds positive cells; output states synthetic grid limits',()=>{
  const {output}=execute(inputs());assert.ok(output.result.assigned_cells>0);
  assert.equal(output.qualification,'synthetic-grid-control');
  assert.equal(output.result.removed_cells,0);assert.equal(output.result.reassigned_cells,0);
});
test('zero cells from a subcell primitive and an already owned target stay distinct from water',()=>{
  const a=execute(inputs(rectangle(-.001,-.001,.001,.001))).output;
  const b=execute(inputs(),[[0,16,7]]).output;
  for(const output of [a,b]){assert.equal(output.result.assigned_cells,0);
    assert.equal(output.result.decisions[0].disposition,'zero-cell');
    assert.equal(output.result.decisions[0].reason_kind,'positive-geometry-no-new-native-cells');
    assert.ok(output.limits.some(line=>line.includes('not water')));}
});
test('actual foreign owner produces a refused candidate, with no reassignment',()=>{
  const {output}=execute(inputs(),[[0,16,9]]);
  assert.equal(output.result.decisions[0].reason_kind,'native-conflict');
  assert.equal(output.result.assigned_cells,0);assert.equal(output.result.reassigned_cells,0);
});
test('overlapping same-owner components aggregate native cells once',()=>{
  const a=inputs(),one=execute(a).output;
  const b={...a,scopeIds:['component:a','component:b'],sourceRows:[...a.sourceRows,
    {...a.sourceRows[0],component_id:'component:b'}],candidates:[...a.candidates,
    {...a.candidates[0],component_id:'component:b'}]};
  const two=execute(b).output;
  assert.equal(two.result.assigned_cells,one.result.assigned_cells);
  assert.equal(two.result.candidate_cell_contributions,2*one.result.assigned_cells);
});
test('consequential input and private frame mutations refuse actual entry',()=>{
  const mutations=[
    a=>{a.scopeIds.push('component:a');},
    a=>{a.sourceRows=[];},
    a=>{a.sourceRows[0].source_compatible=false;},
    a=>{a.candidates[0].target_id='foreign';},
    a=>{a.candidates.push(structuredClone(a.candidates[0]));},
    a=>{a.candidates=[];},
    a=>{a.candidates[0].geometry.coordinates[0].pop();},
    a=>{a.latitudes[1]=a.latitudes[0];}
  ];
  for(const mutate of mutations){const a=inputs();mutate(a);assert.throws(()=>prepareNativeCandidateFrames(a));}
  const a=inputs(),frames=prepareNativeCandidateFrames(a),ownerRows=frames.row_ids.map(y=>({y,complete_owner_intervals:[]}));
  const call=changes=>evaluatePreparedNativeCandidates({...a,frames,ownerRows,continuousConflicts:[],...changes});
  assert.throws(()=>call({frames:structuredClone(frames)}),/actually computed/);
  assert.throws(()=>call({ownerRows:ownerRows.slice(1)}),/complete selected owner rows/);
  assert.throws(()=>call({continuousConflicts:[['component:a','foreign']]}),/Foreign continuous/);
  a.sourceRows[0].pixelIndex=8;assert.throws(()=>call({}),/actually computed/);a.sourceRows[0].pixelIndex=7;
  frames.candidates[0].rows[0].runs.push([0,1,7]);assert.throws(()=>call({}),/actually computed/);
});
test('selected entry refuses invented snapshots and unbranded native projections',()=>{
  const a=inputs();
  assert.throws(()=>prepareSelectedNativeCandidateFrames({manifest:{size:262166},owners:[{id:'target:a'}]},a),
    /authenticated selected snapshot/);
  assert.throws(()=>selectedOwnerRowsFromProjection({owners:[{id:'target:a'}]},
    {rows:new Uint32Array([0]),offsets:new Uint32Array([0,3]),words:new Uint32Array([0,1,1])},[0]));
});
