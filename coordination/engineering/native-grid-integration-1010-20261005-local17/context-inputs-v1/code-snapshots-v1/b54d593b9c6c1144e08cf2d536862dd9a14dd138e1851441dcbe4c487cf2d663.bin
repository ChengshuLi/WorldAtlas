// Versioned offline rule. Existing projected grids keep their original meaning.
export const NATIVE_GRID_METHOD='native-linear-evenodd-first-owner-v1';

export function nativeRowLatitudes(size){
  if(!Number.isSafeInteger(size)||size<2||size>2**31)throw Error('Invalid grid size');
  return Float64Array.from({length:size},(_,y)=>
    Math.atan(Math.sinh(Math.PI*(1-2*(y+.5)/size)))*180/Math.PI);
}

// Exact rational representation of the actual finite IEEE coordinate. No
// epsilon, snapping or approximate intersection determines a column endpoint.
const bits=new DataView(new ArrayBuffer(8));
function binary(value){
  if(!Number.isFinite(value))throw Error('Nonfinite native coordinate');
  if(value===0)return {n:0n,e:0};
  bits.setFloat64(0,value,false);
  const word=bits.getBigUint64(0,false),power=Number(word>>52n&2047n);
  let n=(word&((1n<<52n)-1n))+(power?1n<<52n:0n);
  let e=power?power-1075:-1074;
  if(word>>63n)n=-n;
  while(n%2n===0n){n/=2n;e++;}
  return {n,e};
}
function integers(values){
  const q=Math.max(0,...values.map(v=>-v.e)),scale=1n<<BigInt(q);
  return {values:values.map(v=>v.n<<BigInt(v.e+q)),scale};
}
function ceilDivision(n,d){
  if(d<=0n)throw Error('Invalid rational denominator');
  return n/d+(n%d>0n?1n:0n);
}
function floorDivision(n,d){return n/d-(n%d<0n?1n:0n);}
function columnFraction(longitude,size){
  const {values:[lon],scale}=integers([binary(longitude)]),width=BigInt(size);
  return {n:width*lon+(180n*width-180n)*scale,d:360n*scale};
}
function vertexColumn(longitude,size){
  const {n,d}=columnFraction(longitude,size);
  return n%d===0n?Number(n/d):null;
}
function prepareEdge(edge){
  edge.exact=[edge.x1,edge.y1,edge.x2,edge.y2].map(binary);
}
function crossing(edge,latitude,size){
  const {values:[x1,y1,x2,y2,lat],scale}=integers([...edge.exact,latitude]);
  const dy=y2-y1,dx=x2-x1,width=BigInt(size);
  const numerator=width*(x1*dy+(lat-y1)*dx)+(180n*width-180n)*dy*scale;
  const denominator=360n*dy*scale;
  return {column:Number(ceilDivision(numerator,denominator)),tie:numerator%denominator===0n};
}
// Latitude is decreasing with row number. Binary search schedules edges using
// min-latitude-exclusive/max-latitude-inclusive, equivalent to the legacy
// projected scanline's vertical half-open convention after inversion.
function firstAtOrBelow(latitudes,value,start,end){
  let lo=start,hi=end;
  while(lo<hi){const mid=Math.floor((lo+hi)/2);if(latitudes[mid]>value)lo=mid+1;else hi=mid;}
  return lo;
}

export function nativePolygonIntervals(index,{size,rowStart,rowEnd,latitudes}){
  if(!Number.isSafeInteger(size)||size<2||size>2**31||
     !Number.isInteger(rowStart)||!Number.isInteger(rowEnd)||rowStart<0||rowEnd>size||
     rowStart>=rowEnd||rowEnd-rowStart>4096||latitudes?.length!==size)
    throw Error('Require explicit latitude table and at most4096 native rows');
  for(let y=0;y<size;y++)if(!Number.isFinite(latitudes[y])||Math.abs(latitudes[y])>=90||
    y&&latitudes[y]>=latitudes[y-1])throw Error('Invalid decreasing native latitude table');
  const rows=new Map(),ties=[];let previousOwner=0;
  for(const item of index){
    if(!Number.isInteger(item.index)||item.index<=previousOwner||item.index>2**32-1)
      throw Error('Noncanonical native owner order');
    previousOwner=item.index;
    if(!Array.isArray(item.polygons)||!item.polygons.length)throw Error('Missing native polygons');
    for(const polygon of item.polygons){
      if(!Array.isArray(polygon)||!polygon.length)throw Error('Missing native polygon rings');
      const edges=[];
      for(const ring of polygon){
        if(ring.length<8||ring.length%2||ring[0]!==ring.at(-2)||ring[1]!==ring.at(-1))
          throw Error('Unclosed native ring');
        for(let k=0;k<ring.length;k+=2)if(!Number.isFinite(ring[k])||!Number.isFinite(ring[k+1])||
          Math.abs(ring[k])>180||Math.abs(ring[k+1])>90)throw Error('Invalid native lon/lat coordinate');
        for(let k=0;k<ring.length-2;k+=2){
          let x1=ring[k],y1=ring[k+1],x2=ring[k+2],y2=ring[k+3];
          if(y1>y2){[x1,x2]=[x2,x1];[y1,y2]=[y2,y1];}
          const excluded=firstAtOrBelow(latitudes,y1,rowStart,rowEnd);
          if(excluded<rowEnd&&latitudes[excluded]===y1){
            if(y1===y2){
              const a=columnFraction(Math.min(x1,x2),size),b=columnFraction(Math.max(x1,x2),size);
              const start=Math.max(0,Number(ceilDivision(a.n,a.d)));
              const end=Math.min(size,Number(floorDivision(b.n,b.d))+1);
              if(start<end)ties.push({y:excluded,start,end,owner:item.index,kind:'horizontal-native-boundary-centres'});
            }else{
              const x=vertexColumn(x1,size);
              if(x!==null&&x>=0&&x<size)ties.push({y:excluded,x,owner:item.index,kind:'excluded-native-lower-vertex-centre'});
            }
          }
          if(y1===y2)continue;
          const first=firstAtOrBelow(latitudes,y2,rowStart,rowEnd),end=excluded;
          if(first<end)edges.push({first,end,x1,y1,x2,y2});
        }
      }
      edges.sort((a,b)=>a.first-b.first);
      let next=0,active=[];
      for(let y=edges[0]?.first??rowEnd;y<rowEnd&&(active.length||next<edges.length);y++){
        active=active.filter(edge=>edge.end>y);
        while(next<edges.length&&edges[next].first===y){const edge=edges[next++];prepareEdge(edge);active.push(edge);}
        const latitude=binary(latitudes[y]),columns=[];
        for(const edge of active){
          const hit=crossing(edge,latitude,size);columns.push(hit.column);
          if(hit.tie&&hit.column>=0&&hit.column<size)
            ties.push({y,x:hit.column,owner:item.index,kind:'native-intersection-on-cell-centre'});
        }
        if(columns.length%2)throw Error('Unpaired native intersections; domain unmeasured');
        // Ceil is monotone, so sorting exact integer thresholds gives the same
        // paired cell spans as sorting the underlying rational intersections.
        columns.sort((a,b)=>a-b);
        for(let k=0;k<columns.length;k+=2){
          const start=Math.max(0,columns[k]),end=Math.min(size,columns[k+1]);
          if(start<end){if(!rows.has(y))rows.set(y,[]);rows.get(y).push({start,end,owner:item.index});}
        }
      }
    }
  }
  // Membership under this numerical rule is not source/topology approval.
  return {rows,ties,size,rowStart,rowEnd,method:NATIVE_GRID_METHOD,
    scientific_approval:false,native_topology_verified:false};
}
