// Stable Web Mercator cells. At zoom 7 one cell is ~1.22 km at the equator.
export const GRID_ZOOM=7;
export const GRID_WIDTH=256*2**GRID_ZOOM;
export function projectCell(lon,lat){
  const s=Math.sin(Math.max(-85.05112878,Math.min(85.05112878,lat))*Math.PI/180);
  return [(lon+180)/360*GRID_WIDTH,(.5-Math.log((1+s)/(1-s))/(4*Math.PI))*GRID_WIDTH];
}
export function createGridIndex(features){
  return [...features].sort((a,b)=>a.pixelIndex&&b.pixelIndex?a.pixelIndex-b.pixelIndex:a.id.localeCompare(b.id)).map((feature,index)=>{
    if(!feature.geometry&&feature.gridBounds)return {feature,index:index+1,polygons:[],bounds:feature.gridBounds};
    let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
    const raw=feature.geometry.type==='Polygon'?[feature.geometry.coordinates]:feature.geometry.coordinates;
    const polygons=raw.map(p=>p.map(r=>{
      const result=new Float64Array(r.length*2);
      r.forEach(([lon,lat],i)=>{const [x,y]=projectCell(lon,lat);result[i*2]=x;result[i*2+1]=y;minX=Math.min(minX,x);maxX=Math.max(maxX,x);minY=Math.min(minY,y);maxY=Math.max(maxY,y);});
      return result;
    }));
    return {feature,index:index+1,polygons,bounds:[minX,minY,maxX,maxY]};
  });
}

// Integer ID buffer, not blended RGB picking. Even-odd scanlines preserve holes.
// A lower-detail view samples a subset of the same canonical cells.
export function rasterize(index,{x,y,width,height,stride=1}){
  const ids=new Uint32Array(width*height);
  for(const item of index){
    const [minX,minY,maxX,maxY]=item.bounds;
    if(maxX<x || minX>x+width*stride || maxY<y || minY>y+height*stride)continue;
    const first=Math.max(0,Math.ceil((minY-y-.5)/stride)),last=Math.min(height-1,Math.floor((maxY-y-.5)/stride));
    for(const polygon of item.polygons)for(let row=first;row<=last;row++){
      const sampleY=y+row*stride+.5,intersections=[];
      for(const ring of polygon)for(let k=0;k<ring.length-2;k+=2){
        const x1=ring[k],y1=ring[k+1],x2=ring[k+2],y2=ring[k+3];
        if((y1<=sampleY && y2>sampleY)||(y2<=sampleY && y1>sampleY))intersections.push(x1+(sampleY-y1)*(x2-x1)/(y2-y1));
      }
      intersections.sort((a,b)=>a-b);
      for(let k=0;k+1<intersections.length;k+=2){
        const start=Math.max(0,Math.ceil((intersections[k]-x-.5)/stride));
        const end=Math.min(width,Math.ceil((intersections[k+1]-x-.5)/stride));
        for(let col=start;col<end;col++){
          const offset=row*width+col;
          // A deterministic tie rule also handles a sample exactly on a shared edge.
          if(ids[offset]===0)ids[offset]=item.index;
        }
      }
    }
  }
  return ids;
}
export function borderKind(a,b,provinceIds){
  if(a===b || (!a && !b))return null;
  if(!a || !b)return 'coast';
  return provinceIds[a]===provinceIds[b]?'location':'province';
}
export function borderStyle(kind,zoom){
  if(kind==='location')return zoom<7?null:{width:.5,alpha:Math.min(.6,(zoom-6)*.12)};
  if(kind==='province')return {width:zoom<7?.8:1.5,alpha:.8};
  return {width:1,alpha:.65};
}

// Canvas fallback samples at screen resolution; never forces four-pixel blocks.
export function viewStride(zoom){return 2**Math.max(0,Math.ceil(GRID_ZOOM-zoom));}
