import {GRID_WIDTH} from './pixel-grid.js';

// Compile polygon ownership once, independently of any viewport or zoom. Store
// runs of equal IDs per row instead of a multi-gigabyte dense world bitmap.
export function compileOwnership(index,size=GRID_WIDTH){
  const spans=Array.from({length:size},()=>[]);
  for(const item of index)for(const polygon of item.polygons){
    const edges=[];
    for(const ring of polygon)for(let k=0;k<ring.length-2;k+=2){
      const x1=ring[k],y1=ring[k+1],x2=ring[k+2],y2=ring[k+3];
      if(y1===y2)continue;
      const first=Math.max(0,Math.ceil(Math.min(y1,y2)-.5));
      const end=Math.min(size,Math.ceil(Math.max(y1,y2)-.5));
      if(first<end)edges.push({first,end,x1,y1,x2,y2});
    }
    edges.sort((a,b)=>a.first-b.first);
    let next=0,active=[];
    for(let row=edges[0]?.first??size;row<size&&(next<edges.length||active.length);row++){
      active=active.filter(e=>e.end>row);
      while(next<edges.length&&edges[next].first===row)active.push(edges[next++]);
      const xs=active.map(e=>e.x1+(row+.5-e.y1)*(e.x2-e.x1)/(e.y2-e.y1)).sort((a,b)=>a-b);
      for(let k=0;k+1<xs.length;k+=2){
        const start=Math.max(0,Math.ceil(xs[k]-.5)),end=Math.min(size,Math.ceil(xs[k+1]-.5));
        if(start<end)spans[row].push(start,end,item.index);
      }
    }
  }
  const scratch=new Uint32Array(size),rows=new Array(size);
  for(let y=0;y<size;y++){
    const intervals=spans[y];
    if(!intervals.length){rows[y]=new Uint32Array();continue;}
    scratch.fill(0);let first=size,last=0;
    for(let k=0;k<intervals.length;k+=3){
      const start=intervals[k],end=intervals[k+1],id=intervals[k+2];
      first=Math.min(first,start);last=Math.max(last,end);
      for(let x=start;x<end;x++)if(!scratch[x])scratch[x]=id;
    }
    const runs=[];
    for(let start=first;start<last;){
      const id=scratch[start];let end=start+1;
      while(end<last&&scratch[end]===id)end++;
      if(id)runs.push(start,end,id);
      start=end;
    }
    rows[y]=Uint32Array.from(runs);spans[y]=null;
  }
  return {rows,size};
}

// View changes only sample existing integer IDs. No geometry is consulted.
export function sampleOwnership(grid,{x,y,width,height,stride=1}){
  const ids=new Uint32Array(width*height);
  for(let row=0;row<height;row++){
    const runs=grid.rows[y+row*stride];if(!runs?.length)continue;
    let lo=0,hi=runs.length/3;
    while(lo<hi){const mid=(lo+hi)>>>1;if(runs[mid*3+1]<=x)lo=mid+1;else hi=mid;}
    for(let k=lo*3;k<runs.length&&runs[k]<x+width*stride;k+=3){
      const first=Math.max(0,Math.ceil((runs[k]-x)/stride));
      const end=Math.min(width,Math.ceil((runs[k+1]-x)/stride));
      ids.fill(runs[k+2],row*width+first,row*width+end);
    }
  }
  return ids;
}

// GPU and CPU picking share the same compact, immutable row/run tables.
export function packOwnership(grid,{version=2}={}){
  if(!Number.isInteger(grid.size)||grid.size<2||grid.size>2**31||grid.rows.length!==grid.size)throw Error('Invalid ownership grid size');
  if(version!==1&&version!==2)throw Error('Unsupported ownership packing');
  const coordinateBits=Math.ceil(Math.log2(grid.size)),ownerBits=32-coordinateBits;
  const ownerBase=2**ownerBits,maxOwner=Math.min(2**32-1,2**(ownerBits*2)-1);
  const rows=new Uint32Array(grid.size*2);
  const count=grid.rows.reduce((n,row)=>n+row.length/3,0),runs=new Uint32Array(count*(version===2?2:4));
  let offset=0;
  grid.rows.forEach((row,y)=>{
    if(row.length%3)throw Error('Incomplete ownership row');
    rows[y*2]=offset;rows[y*2+1]=row.length/3;
    let previousEnd=0;
    for(let k=0;k<row.length;k+=3){
      const start=row[k],end=row[k+1],id=row[k+2];
      if(!Number.isInteger(start)||!Number.isInteger(end)||start<previousEnd||end<=start||end>grid.size||!Number.isInteger(id)||id<1||id>2**32-1||(version===2&&id>maxOwner))throw Error('Ownership run exceeds integer packing capacity');
      if(version===2){runs[offset*2]=id%ownerBase*2**coordinateBits+start;runs[offset*2+1]=Math.floor(id/ownerBase)*2**coordinateBits+end-1;}
      else runs.set([start,end,id,0],offset*4);
      previousEnd=end;offset++;
    }
  });
  return {version,coordinateBits,size:grid.size,rows,runs};
}
// Public evidence/test readers use the same exact integer decoding as picking.
export function ownershipRun(grid,index){
  if(grid.version!==2)return {start:grid.runs[index*4],end:grid.runs[index*4+1],id:grid.runs[index*4+2]};
  const bits=grid.coordinateBits,mask=2**bits-1,a=grid.runs[index*2],b=grid.runs[index*2+1];
  return {start:a&mask,end:(b&mask)+1,id:(a>>>bits)+(b>>>bits)*2**(32-bits)};
}
export function pickOwnership(grid,x,y){
  x=Math.floor(x);y=Math.floor(y);
  if(!grid||x<0||y<0||x>=grid.size||y>=grid.size)return 0;
  let lo=grid.rows[y*2],hi=lo+grid.rows[y*2+1];const end=hi,compact=grid.version===2,bits=grid.coordinateBits,mask=2**bits-1;
  while(lo<hi){const mid=(lo+hi)>>>1,runEnd=compact?(grid.runs[mid*2+1]&mask)+1:grid.runs[mid*4+1];if(runEnd<=x)lo=mid+1;else hi=mid;}
  if(lo===end)return 0;
  if(!compact)return grid.runs[lo*4]<=x?grid.runs[lo*4+2]:0;
  const a=grid.runs[lo*2],b=grid.runs[lo*2+1];return (a&mask)<=x?(a>>>bits)+(b>>>bits)*2**(32-bits):0;
}

export function samplePackedOwnership(grid,{x,y,width,height,stride=1}){
  const ids=new Uint32Array(width*height);
  const compact=grid.version===2,bits=grid.coordinateBits,mask=2**bits-1;
  for(let row=0;row<height;row++){
    const yy=y+row*stride;if(yy<0||yy>=grid.size)continue;
    let lo=grid.rows[yy*2],hi=lo+grid.rows[yy*2+1];const end=hi;
    while(lo<hi){const mid=(lo+hi)>>>1,runEnd=compact?(grid.runs[mid*2+1]&mask)+1:grid.runs[mid*4+1];if(runEnd<=x)lo=mid+1;else hi=mid;}
    for(let k=lo;k<end;k++){
      const a=grid.runs[k*(compact?2:4)],b=grid.runs[k*(compact?2:4)+1];
      const start=compact?a&mask:a,stop=compact?(b&mask)+1:b;
      if(start>=x+width*stride)break;
      const id=compact?(a>>>bits)+(b>>>bits)*2**(32-bits):grid.runs[k*4+2];
      const first=Math.max(0,Math.ceil((start-x)/stride));
      const last=Math.min(width,Math.ceil((stop-x)/stride));
      ids.fill(id,row*width+first,row*width+last);
    }
  }
  return ids;
}
