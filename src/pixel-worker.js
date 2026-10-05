import {compileOwnership,sampleOwnership,samplePackedOwnership} from './pixel-ownership.js';
let coverage=null,packed=null,locations=null,political=null,compilations=0,compileMs=0;
self.onmessage=({data})=>{
  if(data.type==='coverage'){coverage=data.grid;return;}
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
  const physical=coverage?samplePackedOwnership(coverage,frame):null;
  self.postMessage({request,ids,physical,political:claims,compilations,compileMs},[ids.buffer,...(claims?[claims.buffer]:[]),...(physical?[physical.buffer]:[])]);
};
