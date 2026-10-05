// Diagnostic sparse comparison only. Never changes geography or ownership.
// Inputs are already projected by the pinned application's createGridIndex.
export function polygonIntervals(index,{size,rowStart,rowEnd}){
  if(!Number.isSafeInteger(size)||size<2||size>2**31||
     !Number.isInteger(rowStart)||!Number.isInteger(rowEnd)||
     rowStart<0||rowEnd>size||rowStart>=rowEnd||rowEnd-rowStart>4096)
    throw Error('Require an explicit bounded row domain of at most 4096 rows');
  const rows=new Map(),ties=[];
  const owners=new Set();let previousOwner=0;
  for(const item of index){
    if(!Number.isInteger(item.index)||item.index<1||item.index>2**32-1||owners.has(item.index))
      throw Error('Missing or duplicate original owner index');
    if(item.index<=previousOwner)throw Error('Noncanonical original owner order');
    previousOwner=item.index;owners.add(item.index);
    for(const polygon of item.polygons){
      const edges=[];
      for(const ring of polygon){
        if(ring.length<8||ring.length%2||ring[0]!==ring.at(-2)||ring[1]!==ring.at(-1)||
           !Array.from(ring).every(Number.isFinite))throw Error('Nonfinite or unclosed original projected ring');
        for(let k=0;k<ring.length-2;k+=2){
          const x1=ring[k],y1=ring[k+1],x2=ring[k+2],y2=ring[k+3];
          // Boundary diagnostics include edges/vertices excluded by raster fill.
          // Horizontal centres are retained as half-open integer cell spans.
          if(y1===y2){
            const y=y1-.5;
            if(Number.isInteger(y)&&y>=rowStart&&y<rowEnd){
              const start=Math.max(0,Math.ceil(Math.min(x1,x2)-.5));
              const end=Math.min(size,Math.floor(Math.max(x1,x2)-.5)+1);
              if(start<end)ties.push({y,start,end,owner:item.index,kind:'horizontal-boundary-cell-centres'});
            }
            continue;
          }
          const upperY=Math.max(y1,y2),upperX=y1>y2?x1:x2,y=upperY-.5;
          if(Number.isInteger(y)&&y>=rowStart&&y<rowEnd&&Number.isInteger(upperX-.5)&&upperX>=.5&&upperX<size)
            ties.push({y,x:upperX,owner:item.index,kind:'excluded-upper-vertex-on-cell-centre'});
          const first=Math.max(rowStart,Math.ceil(Math.min(y1,y2)-.5));
          const end=Math.min(rowEnd,Math.ceil(Math.max(y1,y2)-.5));
          if(first<end)edges.push({first,end,x1,y1,x2,y2});
        }
      }
      edges.sort((a,b)=>a.first-b.first);
      let next=0,active=[];
      for(let y=edges[0]?.first??rowEnd;y<rowEnd&&(next<edges.length||active.length);y++){
        active=active.filter(e=>e.end>y);
        while(next<edges.length&&edges[next].first===y)active.push(edges[next++]);
        const xs=active.map(e=>e.x1+(y+.5-e.y1)*(e.x2-e.x1)/(e.y2-e.y1)).sort((a,b)=>a-b);
        if(xs.length%2)throw Error('Unpaired scanline intersection; domain is unmeasured');
        for(const x of xs)if(Number.isInteger(x-.5)&&x>=.5&&x<size)
          ties.push({y,x,owner:item.index,kind:'intersection-on-cell-centre'});
        for(let k=0;k<xs.length;k+=2){
          const start=Math.max(0,Math.ceil(xs[k]-.5)),end=Math.min(size,Math.ceil(xs[k+1]-.5));
          if(start<end){
            if(!rows.has(y))rows.set(y,[]);
            rows.get(y).push({start,end,owner:item.index});
          }
        }
      }
    }
  }
  return {rows,ties,rowStart,rowEnd,size};
}

export function coverageRow(intervals,size){
  const events=new Map([[0,new Map()],[size,new Map()]]);
  for(const {start,end,owner} of intervals){
    if(!Number.isInteger(start)||!Number.isInteger(end)||start<0||end>size||start>=end||
       !Number.isInteger(owner)||owner<1)throw Error('Invalid projected cell interval');
    for(const [x,delta] of [[start,1],[end,-1]]){
      if(!events.has(x))events.set(x,new Map());
      const changes=events.get(x);changes.set(owner,(changes.get(owner)??0)+delta);
    }
  }
  const positions=[...events.keys()].sort((a,b)=>a-b),active=new Map(),result=[];
  for(let n=0;n<positions.length;n++){
    const start=positions[n];
    for(const [owner,delta] of events.get(start)){
      const count=(active.get(owner)??0)+delta;
      if(count<0)throw Error('Negative active polygon membership');
      if(count)active.set(owner,count);else active.delete(owner);
    }
    if(n===positions.length-1)break;
    const end=positions[n+1],owners=[...active.keys()].sort((a,b)=>a-b);
    const previous=result.at(-1);
    if(previous&&previous.end===start&&previous.owners.length===owners.length&&
       previous.owners.every((owner,i)=>owner===owners[i]))previous.end=end;
    else result.push({start,end,owners});
  }
  if(active.size)throw Error('Unclosed projected intervals');
  return result;
}

function nativeSegments(runs,size){
  if(runs.length%3)throw Error('Incomplete native row');
  const result=[];let previous=0;
  for(let n=0;n<runs.length;n+=3){
    const start=runs[n],end=runs[n+1],owner=runs[n+2];
    if(!Number.isInteger(start)||!Number.isInteger(end)||start<previous||start>=end||end>size||
       !Number.isInteger(owner)||owner<1||owner>2**32-1)throw Error('Invalid native row');
    if(previous<start)result.push({start:previous,end:start,owner:0});
    result.push({start,end,owner});previous=end;
  }
  if(previous<size)result.push({start:previous,end:size,owner:0});
  return result;
}

export function compareRow(intervals,nativeRuns,size){
  const projected=coverageRow(intervals,size),native=nativeSegments(nativeRuns,size);
  const counts={checked_cells:0,projected_covered:0,native_owned:0,raster_only_gap:0,
    native_outside_projected:0,foreign_owner:0,multiple_projected_owners:0,
    first_owner_difference:0};
  const findings=[];let p=0,n=0;
  while(p<projected.length&&n<native.length){
    const a=projected[p],b=native[n],start=Math.max(a.start,b.start),end=Math.min(a.end,b.end);
    if(start>=end)throw Error('Incomplete sparse row accounting');
    const length=end-start,owners=a.owners,first=owners[0]??0;
    counts.checked_cells+=length;
    if(owners.length)counts.projected_covered+=length;
    if(b.owner)counts.native_owned+=length;
    const kinds=[];
    if(!b.owner&&owners.length)kinds.push('raster_only_gap');
    if(b.owner&&!owners.length)kinds.push('native_outside_projected');
    if(b.owner&&owners.length&&!owners.includes(b.owner))kinds.push('foreign_owner');
    if(owners.length>1)kinds.push('multiple_projected_owners');
    if(first!==b.owner)kinds.push('first_owner_difference');
    for(const kind of kinds)counts[kind]+=length;
    if(kinds.length)findings.push({start,end,native_owner:b.owner,projected_owners:owners,kinds});
    if(a.end===end)p++;
    if(b.end===end)n++;
  }
  if(p!==projected.length||n!==native.length||counts.checked_cells!==size)
    throw Error('Unchecked cells in declared row');
  return {counts,findings};
}
