// Bounded native ownership compiler. Compilation is not geographic approval.
import {nativePolygonIntervals,NATIVE_GRID_METHOD} from '../../src/native-grid.js';
import {coverageRow} from '../../scripts/audit-grid-intervals.mjs';

export async function compileNativeOwnership(index,{size,latitudes,rowBlock=4096,
  partWords=1048576,writePart,onBlock=()=>{}}){
  if(!Number.isInteger(size)||size<2||size>300000||
    !Number.isInteger(rowBlock)||rowBlock<1||rowBlock>4096||
    !Number.isInteger(partWords)||partWords<2||partWords>1048576||partWords%2||
    typeof writePart!=='function'||typeof onBlock!=='function')
    throw Error('Require bounded canonical rows and even compact word parts');
  const coordinateBits=Math.ceil(Math.log2(size)),factor=2**coordinateBits,
    ownerBase=2**(32-coordinateBits),maxOwner=Math.min(2**32-1,ownerBase**2-1);
  let previousOwner=0;
  const prepared=index.map(item=>{
    if(!Number.isInteger(item.index)||item.index<=previousOwner||item.index>maxOwner)
      throw Error('Invalid stable original owner order/capacity');
    previousOwner=item.index;
    // Derive selection bounds from actual ring bytes; never trust stale bounds.
    let minLat=Infinity,maxLat=-Infinity;
    for(const polygon of item.polygons)for(const ring of polygon)
      for(let k=1;k<ring.length;k+=2){minLat=Math.min(minLat,ring[k]);maxLat=Math.max(maxLat,ring[k]);}
    return {...item,minLat,maxLat};
  });
  const rows=new Uint32Array(size*2),buffer=new Uint32Array(partWords),parts=[],ownerCounts=new Map(prepared.map(item=>[item.index,0]));
  let used=0,wordOffset=0,totalRuns=0,ownedCells=0,multipleOwnerCells=0,tieRecords=0;
  async function flush(){
    if(!used)return;
    const words=buffer.slice(0,used);
    const receipt=await writePart({kind:'runs',offset:wordOffset,words:used},words);
    parts.push(receipt);wordOffset+=used;used=0;
  }
  function append(start,end,id){
    buffer[used++]=id%ownerBase*factor+start;
    buffer[used++]=Math.floor(id/ownerBase)*factor+end-1;
    totalRuns++;
    if(totalRuns>2**32-1)throw Error('Canonical row offsets exceed uint32 capacity');
    const cells=end-start;ownedCells+=cells;
    ownerCounts.set(id,(ownerCounts.get(id)??0)+cells);
  }
  for(let first=0;first<size;first+=rowBlock){
    const end=Math.min(size,first+rowBlock);
    // The first call validates every original ring, including inactive ones,
    // before emitting any part. Later calls select only true native bounds.
    const selected=first===0?prepared:prepared.filter(item=>
      item.minLat<=latitudes[first]&&item.maxLat>=latitudes[end-1]);
    const native=nativePolygonIntervals(selected,{size,rowStart:first,rowEnd:end,latitudes});
    tieRecords+=native.ties.length;
    for(let y=first;y<end;y++){
      rows[y*2]=totalRuns;
      let pending=null;
      for(const segment of coverageRow(native.rows.get(y)??[],size)){
        if(segment.owners.length>1)multipleOwnerCells+=segment.end-segment.start;
        const id=segment.owners[0]??0;
        if(!id){
          if(pending){
            if(used===buffer.length)await flush();
            append(...pending);pending=null;
          }
          continue;
        }
        if(pending&&pending[1]===segment.start&&pending[2]===id)pending[1]=segment.end;
        else{
          if(pending){
            if(used===buffer.length)await flush();
            append(...pending);
          }
          pending=[segment.start,segment.end,id];
        }
      }
      if(pending){
        if(used===buffer.length)await flush();
        append(...pending);
      }
      rows[y*2+1]=totalRuns-rows[y*2];
    }
    await onBlock({row_start:first,row_end:end,completed_rows:end,total_runs:totalRuns,
      owned_cells:ownedCells,multiple_owner_cells:multipleOwnerCells});
  }
  await flush();
  for(let offset=0;offset<rows.length;offset+=partWords){
    const words=rows.slice(offset,Math.min(rows.length,offset+partWords));
    parts.push(await writePart({kind:'rows',offset,words:words.length},words));
  }
  if(wordOffset!==totalRuns*2)throw Error('Incomplete streamed compact run words');
  return {version:2,coordinateBits,size,runWords:wordOffset,parts,method:NATIVE_GRID_METHOD,
    checked_rows:size,checked_cells:size**2,unchecked_cells:0,owned_cells:ownedCells,
    multiple_owner_cells:multipleOwnerCells,boundary_tie_records:tieRecords,
    per_owner_cells:[...ownerCounts].sort((a,b)=>a[0]-b[0]),
    scientific_approval:false,installation_ready:false};
}
