// Read-only geography checks; --full compiles an isolated candidate in memory.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {createGridIndex,GRID_WIDTH} from '../../../../src/pixel-grid.js';
import {loadFeatures,compileSparse} from '../../../../scripts/audit-grid-resolutions.mjs';
import {footprintHash} from '../../../../scripts/check-prepared.mjs';
const directory='data/macro-improvements/loose-ends-v5/grid';
const read=file=>JSON.parse(fs.readFileSync(file));
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const additions=read(`${directory}/held-islands.geojson`).features;
for(const feature of additions){
  const source=feature.properties.source,bytes=fs.readFileSync(source.path);
  if(hash(bytes)!==source.archive_sha256||hash(gunzipSync(bytes))!==source.sha256)throw Error('Source bytes changed');
  if(feature.geometry.type!=='MultiPolygon'||feature.geometry.coordinates.length!==3)throw Error('Expected three preserved dry-land rings');
}
const scaled=(features,size)=>createGridIndex(features).map(item=>({...item,bounds:item.bounds.map(x=>x*size/GRID_WIDTH),polygons:item.polygons.map(p=>p.map(r=>Float64Array.from(r,x=>x*size/GRID_WIDTH)))}));
function cells(item){
  const found=new Set();
  for(const polygon of item.polygons){
    for(let y=Math.ceil(item.bounds[1]-.5);y<Math.ceil(item.bounds[3]-.5);y++){
      const xs=[];
      for(const ring of polygon)for(let k=0;k<ring.length-2;k+=2){
        const [x1,y1,x2,y2]=ring.subarray(k,k+4);
        if((y1<=y+.5&&y2>y+.5)||(y2<=y+.5&&y1>y+.5))xs.push(x1+(y+.5-y1)*(x2-x1)/(y2-y1));
      }
      xs.sort((a,b)=>a-b);
      for(let k=0;k+1<xs.length;k+=2)for(let x=Math.ceil(xs[k]-.5);x<Math.ceil(xs[k+1]-.5);x++)found.add(`${x},${y}`);
    }
  }
  return [...found].map(x=>x.split(',').map(Number));
}
const sizeArgument=process.argv.find(x=>x.startsWith('--size='));
const size=sizeArgument?Number(sizeArgument.slice(7)):266240;
if(!Number.isInteger(size)||size<262144||size>524288)throw Error('Candidate size outside bounded review');
const checks=[262144,266240,327680,524288].map(size=>({size,locations:scaled(additions,size).map(item=>({id:item.feature.id,name:item.feature.properties.name,source_cells:cells(item)}))}));
fs.writeFileSync(`${directory}/source-cell-check.json`,JSON.stringify({source_feature_sha256:hash(fs.readFileSync(`${directory}/held-islands.geojson`)),method:'Fixed uniform Web Mercator cell centres inside exact even-odd source rings; isolated source check is not whole-world collision proof.',checks})+'\n');
if(process.argv.includes('--full')){
  const original=loadFeatures(),features=[...original,...additions];
  if(new Set(features.map(f=>f.id)).size!==features.length)throw Error('Location ID collision');
  const index=scaled(features,size),began=performance.now(),grid=compileSparse(index,size);
  const missing=index.filter(item=>!grid.counts[item.index]).map(item=>({id:item.feature.id,name:item.feature.properties.name}));
  const held=index.filter(item=>additions.some(f=>f.id===item.feature.id)).map(item=>({id:item.feature.id,cells:grid.counts[item.index]}));
  const result={issue:540,current_footprints_sha256:footprintHash(original),source_feature_sha256:hash(fs.readFileSync(`${directory}/held-islands.geojson`)),size,equivalent_leaflet_zoom:Math.log2(size/256),locations:features.length,missing,held,runs:grid.runs,decoded_ownership_bytes:size*8+grid.runs*8,compile_ms:performance.now()-began,peak_rss_bytes:process.resourceUsage().maxRSS*1024,acceptance:'Conditional preliminary result: root must recompile all final v5 additions/footprint corrections, measure area distortion, compressed build size, device rendering and publication pins before activation.',global_coarsest_resolution_proven:false,installed:false};
  fs.writeFileSync(`${directory}/full-grid-check.json`,JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify(result));
}
