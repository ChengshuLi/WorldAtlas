// Read-only cell-center eligibility against the committed canonical rasterizer.
import fs from 'node:fs';
import path from 'node:path';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {createGridIndex, rasterize, GRID_ZOOM, GRID_WIDTH} from '../../../src/pixel-grid.js';

const directory=path.resolve(process.argv[2]);
const here=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(here,'../../..');
const raw=fs.readFileSync(path.join(directory,'source-dry-land.geojson.gz'));
const sources=JSON.parse(gunzipSync(raw)).features;
const rows=sources.map(feature=>{
 const index=createGridIndex([{id:feature.id,geometry:feature.geometry}]);
 const b=index[0].bounds,x=Math.floor(b[0]),y=Math.floor(b[1]);
 const width=Math.ceil(b[2])-x+1,height=Math.ceil(b[3])-y+1;
 const pixels=rasterize(index,{x,y,width,height});
 let count=0;const examples=[];
 for(let i=0;i<pixels.length;i++)if(pixels[i]){
  count++;if(examples.length<8)examples.push([x+i%width,y+Math.floor(i/width)]);
 }
 return {name:feature.id,whole_dry_land_cell_centers:count,examples,
  status:count?'represented':'unrepresented; never move a nearby water cell',
  canonical_grid_width:GRID_WIDTH,canonical_grid_zoom:GRID_ZOOM};
});
if(rows.some(row=>['Palmerston','Manihiki'].includes(row.name)&&!row.whole_dry_land_cell_centers))throw Error('Approved correction has no canonical-grid representation');
const sha=p=>createHash('sha256').update(fs.readFileSync(p)).digest('hex');
fs.writeFileSync(path.join(directory,'grid-check.json'),JSON.stringify({rows,
 method:'Exact committed canonical cell-center rasterizer; source dry land and explicit water masks; no current ownership generation or uploads',
 source_sha256:sha(path.join(directory,'source-dry-land.geojson.gz')),
 implementation_sha256:sha(path.join(root,'src/pixel-grid.js')),
 installed_assets_changed:false,ownership_recompiled:false}));
