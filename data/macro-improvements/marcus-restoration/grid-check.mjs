// Exact canonical cell-center intervals for one named candidate only; never compile the world.
import fs from 'node:fs';import path from 'node:path';import {createHash} from 'node:crypto';import {gunzipSync} from 'node:zlib';import {pathToFileURL} from 'node:url';
const root=path.resolve(process.argv[2]),output=path.resolve(process.argv[3]),sha=b=>createHash('sha256').update(b).digest('hex'),read=p=>JSON.parse(fs.readFileSync(p));
const {createGridIndex,rasterize,GRID_WIDTH,GRID_ZOOM}=await import(pathToFileURL(path.join(root,'src/pixel-grid.js'))),{ownershipRun}=await import(pathToFileURL(path.join(root,'src/pixel-ownership.js'))),{unshuffleOwnershipBytes}=await import(pathToFileURL(path.join(root,'src/ownership-codec.js')));
const features=read(path.join(output,'candidate-patch.json')).added_features,index=createGridIndex(features),base=path.join(root,'data/canonical-grid'),manifestBytes=fs.readFileSync(path.join(base,'manifest.json')),manifest=JSON.parse(manifestBytes);
if(manifest.size!==GRID_WIDTH||manifest.version!==2||manifest.coordinateBits!==18)throw Error('Canonical lattice differs from tested candidate');
const checked=new Map(),chunks=new Map();
function words(part){const compressed=fs.readFileSync(path.join(base,part.path));if(sha(compressed)!==part.sha256)throw Error('Ownership source compressed bytes changed');const decoded=unshuffleOwnershipBytes(gunzipSync(compressed),part.words);if(sha(Buffer.from(decoded.buffer))!==part.decoded_sha256)throw Error('Ownership source decoded bytes changed');checked.set(part.path,{sha256:part.sha256,decoded_sha256:part.decoded_sha256});return decoded;}
const rows=words(manifest.parts.find(p=>p.kind==='rows'));const cache=part=>{if(!chunks.has(part.offset))chunks.set(part.offset,words(part));return chunks.get(part.offset);};
const run=k=>{const offset=k*2,part=manifest.parts.find(p=>p.kind==='runs'&&offset>=p.offset&&offset+1<p.offset+p.words);if(!part)throw Error('Missing baseline run');return ownershipRun({...manifest,runs:cache(part)},(offset-part.offset)/2);};
const result=index.map(item=>({id:item.feature.id,canonical_grid_zoom:GRID_ZOOM,canonical_size:GRID_WIDTH,projected_bounds:item.bounds,cell_center_count:0,grid_wgs84_area_m2:0,existing_owned_cell_conflicts:0,example_cells:[],status:'pending'}));const byIndex=new Map(index.map((item,i)=>[item.index,result[i]]));
const A=6378137,F=1/298.257223563,E2=F*(2-F),E=Math.sqrt(E2),C=A*A*(1-E2)/2,strip=u=>C*(u/(1-E2*u*u)+Math.atanh(E*u)/E);
const cellArea=y=>{const north=Math.atan(Math.sinh(Math.PI*(1-2*y/GRID_WIDTH))),south=Math.atan(Math.sinh(Math.PI*(1-2*(y+1)/GRID_WIDTH)));return (strip(Math.sin(north))-strip(Math.sin(south)))*2*Math.PI/GRID_WIDTH;};
const b=index[0].bounds,minX=Math.floor(b[0]),minY=Math.floor(b[1]),width=Math.ceil(b[2])-minX+1,height=Math.ceil(b[3])-minY+1;
if(width*height>10000)throw Error('Candidate exceeds bounded cell window');
const pixels=rasterize(index,{x:minX,y:minY,width,height});
for(let row=0;row<height;row++){
 const y=minY+row,intervals=[];let start=-1;for(let col=0;col<=width;col++){const id=col<width?pixels[row*width+col]:0;if(id&&start<0)start=col;if(!id&&start>=0){intervals.push(minX+start,minX+col,1);start=-1;}}if(!intervals.length)continue;
 const first=rows[y*2],last=first+rows[y*2+1];let j=first;
 for(let k=0;k<intervals.length;k+=3){const [start,end,id]=intervals.slice(k,k+3),r=byIndex.get(id);r.cell_center_count+=end-start;r.grid_wgs84_area_m2+=(end-start)*cellArea(y);if(r.example_cells.length<16)r.example_cells.push([start,y]);
  while(j<last&&run(j).end<=start)j++;for(let q=j;q<last;q++){const old=run(q);if(old.start>=end)break;r.existing_owned_cell_conflicts+=Math.max(0,Math.min(end,old.end)-Math.max(start,old.start));}
 }
}
for(const r of result){if(!r.cell_center_count||r.existing_owned_cell_conflicts)throw Error('Candidate canonical representation is held: '+r.id);r.status='represented-in-empty-baseline-cells';}
const measurements=new Map(read(path.join(output,'geometry-measurements.json')).map(r=>[r.id,r]));for(const r of result){r.source_wgs84_area_m2=measurements.get(r.id).dry_land_area_m2;r.relative_wgs84_area_error=r.grid_wgs84_area_m2/r.source_wgs84_area_m2-1;}
const report={version:1,scope:'One source-defined island, exact original canonical even-odd cell-center kernel including inland-water holes; existing ownership runs read and hashed only for intersecting rows. Only a bounded candidate window is rasterized; no world grid compiled or mutated.',canonical_manifest_sha256:sha(manifestBytes),checked_ownership_parts:Object.fromEntries(checked),locations:result,ownership_recompilations_global:0,live_apply:false};fs.writeFileSync(path.join(output,'grid-report.json'),JSON.stringify(report));console.log(JSON.stringify(result));
