import {compileOwnership,packOwnership} from './pixel-ownership.js';
let compilations=0,compileMs=0;
self.onmessage=({data})=>{
  const started=performance.now(),grid=packOwnership(compileOwnership(data.index));
  compilations++;compileMs+=performance.now()-started;
  self.postMessage({type:data.type,revision:data.revision,grid,compilations,compileMs},[grid.rows.buffer,grid.runs.buffer]);
};
