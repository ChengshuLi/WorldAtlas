import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {gzipSync,gunzipSync} from 'node:zlib';
import {loadOwnershipAssets} from '../src/ownership-assets.js';
import {rasterColorNeighbors} from './map-color-neighbors.mjs';
const directory=process.argv[2];
if(!directory||!/^data\/engineering\/[a-z0-9][a-z0-9-]{0,63}$/.test(directory))throw Error('Owned evidence directory required');
const bytes=fs.readFileSync('data/canonical-grid/manifest.json'),manifest=JSON.parse(bytes),sha=b=>createHash('sha256').update(b).digest('hex');
const grid=await loadOwnershipAssets(manifest,async file=>new Response(fs.readFileSync(path.join('data/canonical-grid',file))));
const gap=Math.floor(8*grid.size/1024),neighbors=rasterColorNeighbors(grid,{maxHorizontalGap:gap});
const destination=path.join(directory,'raster-neighbors.json.gz');
if(process.argv.includes('--check')){
  const saved=JSON.parse(gunzipSync(fs.readFileSync(destination)));
  if(saved.manifest_sha256!==sha(bytes)||saved.max_horizontal_gap_cells!==gap||JSON.stringify(saved.adjacent)!==JSON.stringify(neighbors.adjacent)||JSON.stringify(saved.nearby)!==JSON.stringify(neighbors.nearby))throw Error('Exact raster graph differs from retained receipt');
}else{
  const result={version:1,baseline_commit:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),manifest_sha256:sha(bytes),footprints_sha256:manifest.footprints_sha256,hierarchy_sha256:manifest.hierarchy_sha256,grid_size:grid.size,max_horizontal_gap_cells:gap,nearby_definition:'Nearest nonzero land runs separated horizontally by at most 8 pixels on a 1024-pixel world-width map, including date-line wrap; screen proximity, not geographic distance. Vertical proximity gaps are not covered.',...neighbors};
  fs.mkdirSync(directory,{recursive:true});fs.writeFileSync(destination,gzipSync(JSON.stringify(result)),{flag:'wx'});
}
console.log(JSON.stringify({adjacent:neighbors.adjacent.length,nearby:neighbors.nearby.length,max_horizontal_gap_cells:gap,mode:process.argv.includes('--check')?'check':'prepare'}));
