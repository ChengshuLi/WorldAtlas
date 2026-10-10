import {createHash} from 'node:crypto';
import {nativeRuntimeIndex} from '../../../src/native-runtime.js';
import {nativePolygonIntervals} from '../../../src/native-grid.js';
import {combineNativeBatch} from '../../../scripts/additive-gap-repair.mjs';
import {SelectedGeometrySources,validateNativeRowCarry} from '../../../scripts/check-effective-geographic-regression.mjs';

const demand=(value,message)=>{if(!value)throw Error(message);};
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const LATITUDE_SHA='66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23';
const preparedFrames=new WeakMap();

// The actual entry must use this route. Synthetic fixture grids remain confined
// to prepareNativeCandidateFrames and cannot stand in for a selected bank.
export function prepareSelectedNativeCandidateFrames(snapshot,input) {
  new SelectedGeometrySources(snapshot); // requires the checker-owned snapshot identity
  demand(snapshot.manifest.size===262166&&input.size===snapshot.manifest.size,
    'Actual complete canonical selected grid required');
  demand(input.sourceRows.every(row=>Number.isSafeInteger(row.pixelIndex)
    &&snapshot.owners[row.pixelIndex-1]?.id===row.target_id),
    'Selected complete owner identity differs from candidate source target');
  return prepareNativeCandidateFrames(input);
}

// Reuse the checker-owned acquisition and private full-row projection. The
// caller prospectively reserves the returned ordinary row serialization while
// the compact projection remains live; this function opens no native bodies.
export function selectedOwnerRowsFromProjection(snapshot,product,rowIds) {
  validateNativeRowCarry(product,snapshot,rowIds);
  return rowIds.map((y,k)=>{const runs=[];
    for(let i=product.offsets[k];i<product.offsets[k+1];i+=3){
      const run=[product.words[i],product.words[i+1],product.words[i+2]];
      demand(snapshot.owners[run[2]-1],'Foreign native projected owner');runs.push(run);
    }
    return {y,complete_owner_intervals:runs};
  });
}

// These results are grid evaluations, not source approvals or release permits.
// The caller must authenticate each complete original source/geometry and the
// selected snapshot before acquiring the complete requested owner rows.
export function prepareNativeCandidateFrames({scopeIds,sourceRows,candidates,latitudes,size}) {
  demand(Array.isArray(scopeIds)&&scopeIds.length>0&&new Set(scopeIds).size===scopeIds.length,
    'Complete unique candidate scope required');
  demand(Array.isArray(sourceRows)&&sourceRows.length===scopeIds.length
    &&sourceRows.every((row,i)=>row.component_id===scopeIds[i]&&typeof row.source_compatible==='boolean'),
    'Complete ordered source decisions required');
  demand(Number.isSafeInteger(size)&&size>=2&&size<=262166
    &&latitudes instanceof Float64Array&&latitudes.length===size,'Complete native latitude table required');
  for(let y=0;y<size;y++)demand(Number.isFinite(latitudes[y])&&Math.abs(latitudes[y])<90
    &&(!y||latitudes[y]<latitudes[y-1]),'Invalid ordered native latitude table');
  if(size===262166){
    const bytes=Buffer.alloc(size*8);latitudes.forEach((v,i)=>bytes.writeDoubleLE(v,i*8));
    demand(sha(bytes)===LATITUDE_SHA,'Changed literal canonical latitude rule');
  }
  demand(Array.isArray(candidates),'Missing complete candidate geometry roster');
  const byId=new Map();
  for(const candidate of candidates){
    const source=sourceRows.find(row=>row.component_id===candidate.component_id);
    demand(source?.source_compatible===true&&!byId.has(candidate.component_id)
      &&candidate.target_id===source.target_id&&candidate.pixelIndex===source.pixelIndex,
      'Foreign, duplicate or unqualified candidate target');
    const index=nativeRuntimeIndex([{id:candidate.target_id,pixelIndex:candidate.pixelIndex,geometry:candidate.geometry}]);
    const polygons=candidate.geometry.type==='Polygon'?[candidate.geometry.coordinates]:candidate.geometry.coordinates;
    let minimum=90,maximum=-90;
    for(const polygon of polygons)for(const ring of polygon)for(const point of ring){minimum=Math.min(minimum,point[1]);maximum=Math.max(maximum,point[1]);}
    const atOrBelow=latitudes.findIndex(value=>value<=maximum),below=latitudes.findIndex(value=>value<minimum);
    const start=atOrBelow<0?size-1:Math.max(0,atOrBelow-1),end=below<0?size:Math.min(size,below+1);
    demand(end>start&&end-start<=4096,'Candidate needs another bounded complete native window');
    const actual=nativePolygonIntervals(index,{size,latitudes,rowStart:start,rowEnd:end});
    byId.set(candidate.component_id,{component_id:candidate.component_id,target_id:candidate.target_id,
      pixelIndex:candidate.pixelIndex,row_start:start,row_end:end,
      rows:Array.from({length:end-start},(_,i)=>({y:start+i,
        runs:(actual.rows.get(start+i)??[]).map(run=>[run.start,run.end,candidate.pixelIndex])})),
      native_ties:actual.ties});
  }
  demand(sourceRows.every(row=>!row.source_compatible||byId.has(row.component_id)),
    'Eligible candidate geometry omitted');
  const ordered=scopeIds.filter(id=>byId.has(id)).map(id=>byId.get(id));
  const frame={kind:'complete-native-candidate-frames-v1',grid_size:size,
    qualification:size===262166?'canonical-latitude-candidate-calculation':'synthetic-grid-control',
    candidates:ordered,row_ids:[...new Set(ordered.flatMap(candidate=>candidate.rows.map(row=>row.y)))].sort((a,b)=>a-b)};
  preparedFrames.set(frame,{scope:JSON.stringify(scopeIds),source:JSON.stringify(sourceRows),frame:JSON.stringify(frame)});
  return frame;
}

export function evaluatePreparedNativeCandidates({scopeIds,sourceRows,frames,ownerRows,continuousConflicts}) {
  const original=preparedFrames.get(frames);
  demand(original&&original.scope===JSON.stringify(scopeIds)&&original.source===JSON.stringify(sourceRows)
    &&original.frame===JSON.stringify(frames),'Require unchanged actually computed native frames and source decisions');
  demand(frames?.kind==='complete-native-candidate-frames-v1'&&Array.isArray(ownerRows)
    &&ownerRows.length===frames.row_ids.length&&ownerRows.every((row,i)=>row.y===frames.row_ids[i]),
    'Missing, foreign or reordered complete selected owner rows');
  const result=combineNativeBatch({scopeIds,sourceRows,candidates:frames.candidates,ownerRows,
    continuousConflicts,size:frames.grid_size});
  return {version:1,kind:'selected-native-gap-evaluation-v1',grid_size:frames.grid_size,
    qualification:frames.qualification,scope_ids:scopeIds,result,
    limits:['Native grid evaluation only; source authority and selected input custody require separate authentication.',
      'Zero new native cells is not water, physical truth or a completed repair.',
      'This result cannot authorize a selection, transfer a private certificate or activate an unmerged bank.']};
}
