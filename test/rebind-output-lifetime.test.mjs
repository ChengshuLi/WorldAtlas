import test from 'node:test';
import assert from 'node:assert/strict';
import {ImmutableReader} from '../scripts/check-effective-geographic-regression.mjs';
import {admitCurrentRebindOutputFrame,withCurrentRebindOutputReserve,retainCurrentRebindPhasePeak} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const MiB=1048576;
test('completed or refused rebind serialization cannot charge the next row-table phase',()=>{
 for(const throws of [false,true]){
  const r=new ImmutableReader('.', 'a'.repeat(40),{runtimeBytes:24,executionBytes:0,metadataBytes:190*MiB,outputBytes:4*MiB,allowance:{phaseBytes:256*MiB,rssBytes:1024*MiB}});
  let peak;
  const frame=()=>withCurrentRebindOutputReserve(r,()=>{
   peak=admitCurrentRebindOutputFrame(r,{output_bytes:8*MiB,complete_phase_bytes:256*MiB});
   retainCurrentRebindPhasePeak(r,1,peak,[]);
   if(throws)throw Error('actual frame refusal');
   return 'completed';
  });
  if(throws)assert.throws(frame,/actual frame refusal/);else assert.equal(frame(),'completed');
  assert.equal(r.outputBytes,4*MiB);assert.equal(r.used,peak);assert.equal(peak,246*MiB+24);
  r.metadataBytes=219*MiB;r.phase();
  r.admit({commit:'a'.repeat(40),path:'next-row-table',bytes:32*MiB});
  assert(r.used<256*MiB,'next frame fits the unchanged historical 256 MiB ceiling');
  // The same next frame with leaked serialization scratch must exceed that ceiling.
  assert(219*MiB+7*8*MiB+24>256*MiB);
 }
});
