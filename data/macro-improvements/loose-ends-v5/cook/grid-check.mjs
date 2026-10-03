// Read-only use of the canonical rasterizer at zoom 10 and zoom 11.
import fs from 'node:fs';import path from 'node:path';
import {gunzipSync,gzipSync} from 'node:zlib';import {createHash} from 'node:crypto';
import {createGridIndex,rasterize,GRID_ZOOM} from '../../../../src/pixel-grid.js';
const output=path.resolve(process.argv[2]);
const patch=JSON.parse(gunzipSync(fs.readFileSync(path.join(output,'candidate-patch.json.gz'))));
if(GRID_ZOOM!==10)throw Error('Expected pinned canonical zoom 10 source implementation');
const rows=[];
function countCells(feature,zoom){
 const factor=2**(zoom-GRID_ZOOM),index=createGridIndex([feature]);
 for(const row of index){row.bounds=row.bounds.map(v=>v*factor);
  for(const polygon of row.polygons)for(const ring of polygon)for(let j=0;j<ring.length;j++)ring[j]*=factor;}
 const bounds=index[0].bounds,x=Math.floor(bounds[0]),y=Math.floor(bounds[1]);
 const width=Math.ceil(bounds[2])-x+1,height=Math.ceil(bounds[3])-y+1;
 const pixels=rasterize(index,{x,y,width,height});let count=0;
 for(const value of pixels)if(value)count++;
 return count;
}
for(const feature of patch.existing_location_updates)for(const zoom of [10,11]){
 const count=countCells(feature,zoom);
 if(!count)throw Error('Corrected named atoll has no grid representation');
 const polygons=feature.geometry.type==='Polygon'?[feature.geometry.coordinates]:feature.geometry.coordinates;
 const components=polygons.map((coordinates,index)=>({component:index,
  cell_centers:countCells({...feature,geometry:{type:'Polygon',coordinates}},zoom)}));
 rows.push({id:feature.id,name:feature.properties.name,zoom,width:256*2**zoom,cell_centers:count,
  components,source_components_without_cell_centers:components.filter(c=>!c.cell_centers).length});
}
const source=fs.readFileSync(new URL('../../../../src/pixel-grid.js',import.meta.url));
const report={rows,method:'Exact canonical cell-center rasterizer, with projected coordinates doubled for zoom 11.',
 implementation_sha256:createHash('sha256').update(source).digest('hex'),
 grid_ownership_compiled:false,ownership_uploaded:false,installed_assets_changed:false};
fs.writeFileSync(path.join(output,'grid-check.json.gz'),gzipSync(JSON.stringify(report),{mtime:0}));
