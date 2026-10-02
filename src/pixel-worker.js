import {compileOwnership,sampleOwnership,samplePackedOwnership} from './pixel-ownership.js';
let packed=null,locations=null,political=null,compilations=0,compileMs=0;
self.onmessage=({data})=>{
  if(data.type==='precompiled'){packed=data.grid;return;}
  if(data.type==='locations'||data.type==='political'){
    const started=performance.now();
    const grid=data.index.length?compileOwnership(data.index):null;
    if(grid)compilations++;
    compileMs+=performance.now()-started;
    if(data.type==='locations')locations=grid;else political=grid;
    return;
  }
  const {request,frame}=data;
  const ids=packed?samplePackedOwnership(packed,frame):sampleOwnership(locations,frame),claims=political?sampleOwnership(political,frame):null;
  self.postMessage({request,ids,political:claims,compilations,compileMs},[ids.buffer,...(claims?[claims.buffer]:[])]);
};
