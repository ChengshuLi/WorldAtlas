import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {spawn,execFileSync} from 'node:child_process';
import {gzipSync,gunzipSync} from 'node:zlib';
import {fileURLToPath} from 'node:url';
import {createGridIndex,GRID_ZOOM} from '../src/pixel-grid.js';
import {ownershipRun,packOwnership} from '../src/pixel-ownership.js';
import {shuffleOwnershipBytes,unshuffleOwnershipBytes,decodeOwnershipVarints} from '../src/ownership-codec.js';
import {footprintHash} from './check-prepared.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
process.chdir(root);
const argument=(key,fallback)=>process.argv.find(x=>x.startsWith(`--${key}=`))?.slice(key.length+3)??fallback;
const zooms=argument('zooms','7,8,9,10').split(',').map(Number);
const cache=path.resolve(argument('cache','.cache/grid-resolution-review'));
const worldIndex=path.resolve(argument('world-index','data/world-index.json'));
const reportFile=path.resolve(argument('report','data/grid-resolution-review.json'));
const stagedInput=worldIndex!==path.join(root,'data/world-index.json');
const readJSON=file=>JSON.parse(file.endsWith('.gz')?gunzipSync(fs.readFileSync(file)):fs.readFileSync(file));
fs.mkdirSync(cache,{recursive:true});
export function loadFeatures(){
  const result=[];
  for(const part of readJSON(worldIndex).parts){
    const parsed=readJSON(path.join(path.dirname(worldIndex),part));
    for(const f of parsed.features)result.push({id:f.id??f.properties.id,geometry:f.geometry,properties:{name:f.properties.name,reference_owner:f.properties.reference_owner}});
  }
  return result;
}
export function indexAt(index,zoom){
  const factor=2**(zoom-GRID_ZOOM);
  if(factor===1)return index;
  return index.map(item=>({...item,bounds:item.bounds.map(x=>x*factor),polygons:item.polygons.map(p=>p.map(r=>Float64Array.from(r,x=>x*factor)))}));
}
const ringArea=ring=>{let sum=0;for(let k=0;k<ring.length-2;k+=2)sum+=ring[k]*ring[k+3]-ring[k+2]*ring[k+1];return Math.abs(sum/2);};
const areaOf=item=>item.polygons.reduce((sum,p)=>sum+ringArea(p[0])-p.slice(1).reduce((n,r)=>n+ringArea(r),0),0);
function minHeapPush(heap,id){let i=heap.length;heap.push(id);while(i){const parent=(i-1)>>1;if(heap[parent]<=id)break;heap[i]=heap[parent];i=parent;}heap[i]=id;}
function minHeapPop(heap){const tail=heap.pop();if(!heap.length)return;let i=0;while(i*2+1<heap.length){let c=i*2+1;if(c+1<heap.length&&heap[c+1]<heap[c])c++;if(heap[c]>=tail)break;heap[i]=heap[c];i=c;}heap[i]=tail;}
// Sparse preparation uses the exact even-odd cell-center intervals and smallest
// location index priority of compileOwnership, without touching every land cell.
export function compileSparse(index,size){
  const wgs84Areas=new Float64Array(index.length+1);
  const A=6378137,flattening=1/298.257223563,E2=flattening*(2-flattening),E=Math.sqrt(E2),C=A*A*(1-E2)/2;
  const strip=u=>C*(u/(1-E2*u*u)+Math.atanh(E*u)/E);
  const cellArea=y=>{const north=Math.atan(Math.sinh(Math.PI*(1-2*y/size))),south=Math.atan(Math.sinh(Math.PI*(1-2*(y+1)/size)));return (strip(Math.sin(north))-strip(Math.sin(south)))*2*Math.PI/size;};
  const spans=Array.from({length:size},()=>[]);let spanCount=0;
  for(const item of index)for(const polygon of item.polygons){
    const edges=[];
    for(const ring of polygon)for(let k=0;k<ring.length-2;k+=2){
      const x1=ring[k],y1=ring[k+1],x2=ring[k+2],y2=ring[k+3];if(y1===y2)continue;
      const first=Math.max(0,Math.ceil(Math.min(y1,y2)-.5)),end=Math.min(size,Math.ceil(Math.max(y1,y2)-.5));
      if(first<end)edges.push({first,end,x1,y1,x2,y2});
    }
    edges.sort((a,b)=>a.first-b.first);let next=0,active=[];
    for(let row=edges[0]?.first??size;row<size&&(next<edges.length||active.length);row++){
      active=active.filter(e=>e.end>row);while(next<edges.length&&edges[next].first===row)active.push(edges[next++]);
      const xs=active.map(e=>e.x1+(row+.5-e.y1)*(e.x2-e.x1)/(e.y2-e.y1)).sort((a,b)=>a-b);
      for(let k=0;k+1<xs.length;k+=2){const start=Math.max(0,Math.ceil(xs[k]-.5)),end=Math.min(size,Math.ceil(xs[k+1]-.5));if(start<end){spans[row].push(start,end,item.index);spanCount++;}}
    }
  }
  console.error(JSON.stringify({phase:'intervals',zoom:Math.log2(size/256),spans:spanCount,rss:process.memoryUsage().rss}));
  const rows=new Array(size),counts=new Float64Array(index.length+1);let runs=0,overlapCells=0;
  for(let y=0;y<size;y++){
    const rowSpans=spans[y],pixelArea=cellArea(y);if(!rowSpans.length){rows[y]=new Uint32Array();spans[y]=null;continue;}
    const events=[];for(let k=0;k<rowSpans.length;k+=3){events.push([rowSpans[k],rowSpans[k+2],1],[rowSpans[k+1],rowSpans[k+2],-1]);}
    events.sort((a,b)=>a[0]-b[0]||a[1]-b[1]||a[2]-b[2]);
    const heap=[],active=new Map(),output=[];let previous=events[0][0],winner=0,totalActive=0;
    for(let k=0;k<events.length;){
      const x=events[k][0];
      if(x>previous&&winner){
        if(output.length&&output.at(-1)===winner&&output.at(-2)===previous)output[output.length-2]=x;else output.push(previous,x,winner);
        counts[winner]+=x-previous;wgs84Areas[winner]+=(x-previous)*pixelArea;
        if(totalActive>1)overlapCells+=x-previous;
      }
      while(k<events.length&&events[k][0]===x){const [,id,delta]=events[k++],next=(active.get(id)??0)+delta;active.set(id,next);totalActive+=delta;if(delta===1)minHeapPush(heap,id);}
      while(heap.length&&!active.get(heap[0]))minHeapPop(heap);
      winner=heap[0]??0;previous=x;
    }
    rows[y]=Uint32Array.from(output);runs+=output.length/3;spans[y]=null;
    if(y%32768===0)console.error(JSON.stringify({phase:'rows',zoom:Math.log2(size/256),row:y,size,rss:process.memoryUsage().rss}));
  }
  return {rows,counts,wgs84Areas,size,runs,spans:spanCount,overlap_cells_including_same_location_components:overlapCells};
}
function packedBytes(grid){
  const packed=packOwnership(grid),rows=packed.rows;let gzip=0,shuffledGzip=0,maxPart=0;const hashes=[];
  for(const kind of ['rows','runs'])for(let offset=0;offset<packed[kind].length;offset+=1048576){
    const words=packed[kind].subarray(offset,offset+1048576),buffer=Buffer.from(words.buffer,words.byteOffset,words.byteLength),compressed=gzipSync(buffer,{level:9}),shuffled=gzipSync(shuffleOwnershipBytes(words),{level:9});
    gzip+=compressed.length;shuffledGzip+=shuffled.length;maxPart=Math.max(maxPart,shuffled.length);hashes.push(createHash('sha256').update(buffer).digest('hex'));
  }
  return {version:2,coordinate_bits:packed.coordinateBits,row_table_bytes:rows.byteLength,run_table_bytes:packed.runs.byteLength,packed_bytes:rows.byteLength+packed.runs.byteLength,gzip_bytes:shuffledGzip,plain_gzip_bytes:gzip,transport:'byte-shuffle',maximum_gzip_part_bytes:maxPart,packed_chunk_sha256:hashes,gpu_texture_width:2048,gpu_rows_texture_height:Math.ceil(grid.size/2048),gpu_runs_texture_height:Math.ceil(grid.runs/2/2048),gpu_padded_bytes:2048*Math.ceil(grid.size/2048)*8+2048*Math.ceil(grid.runs/2/2048)*16};
}

function verifyBaseline(grid){
  const file='dist/client/atlas-geography.json';if(!fs.existsSync(file))return {verified:false,reason:'Hosted export absent'};
  const map=JSON.parse(fs.readFileSync(file)).pixelMap;if(map.size!==grid.size)return {verified:false,reason:'Hosted canonical size differs'};
  const rows=new Uint32Array(grid.size*2),runs=new Uint32Array(map.runWords);
  for(const part of [...map.parts.filter(p=>p.kind==='rows'),...map.parts.filter(p=>p.kind==='runs')]){
    const b=gunzipSync(fs.readFileSync('dist/client/'+part.path));
    const words=part.encoding==='byte-shuffle'?unshuffleOwnershipBytes(b,part.words):part.encoding==='row-varint'?decodeOwnershipVarints(b,{rows,offset:part.offset,words:part.words,coordinateBits:map.coordinateBits,size:map.size}):new Uint32Array(b.buffer,b.byteOffset,b.byteLength/4);
    (part.kind==='rows'?rows:runs).set(words,part.offset);
  }
  const published={...map,rows,runs};
  for(let y=0;y<grid.size;y++){const row=grid.rows[y],offset=rows[y*2],length=rows[y*2+1];if(row.length!==length*3)throw Error(`Baseline row count differs at${y}`);for(let k=0;k<length;k++){const decoded=ownershipRun(published,offset+k);if(row[k*3]!==decoded.start||row[k*3+1]!==decoded.end||row[k*3+2]!==decoded.id)throw Error(`Baseline ownership differs at${y},${k}`);}}
  return {verified:true,scope:'Every row/run and location-index value equals the shipped zoom7 packed world; hence every canonical cell owner agrees globally',rows:grid.size,runs:grid.runs};
}
const isMain=process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url);
if(isMain&&process.argv.includes('--candidate')){
  const zoom=Number(argument('zoom','7'));if(!Number.isInteger(zoom)||zoom<7||zoom>10)throw Error('Full candidate zoom must be 7..10');
  const started=performance.now(),features=loadFeatures(),hash=footprintHash(features),base=createGridIndex(features),index=indexAt(base,zoom),size=256*2**zoom;
  const grid=compileSparse(index,size),compiled=performance.now(),layout=packedBytes(grid),packed=performance.now();
  const sourceAreas=JSON.parse(fs.readFileSync(path.join(cache,'wgs84-source-areas.json')));if(sourceAreas.footprints_sha256!==hash)throw Error('Source WGS84 areas stale');
  const stats=index.map(item=>{const area=areaOf(item),cells=grid.counts[item.index],error=area?cells/area-1:null;return {id:item.feature.id,name:item.feature.properties.name,owner:item.feature.properties.reference_owner,cells,source_area_cells:Number(area.toFixed(6)),relative_area_error:error===null?null:Number(error.toFixed(6))};});
  const missing=stats.filter(x=>!x.cells),high=stats.filter(x=>x.source_area_cells>=1&&Math.abs(x.relative_area_error)>.25),baseline=zoom===GRID_ZOOM&&!stagedInput?verifyBaseline(grid):{verified:false,reason:'Explicit staged geography; live grid equivalence is intentionally inapplicable.'};
  const result={zoom,size,footprints_sha256:hash,location_ids:stats.map(x=>x.id),cell_counts:stats.map(x=>x.cells),source_area_cells_zoom7:zoom===GRID_ZOOM?stats.map(x=>x.source_area_cells):undefined,source_wgs84_area_m2:zoom===GRID_ZOOM?stats.map(x=>sourceAreas.areas[x.id]):undefined,grid_wgs84_area_m2:stats.map((x,i)=>Number(grid.wgs84Areas[i+1].toFixed(6))),represented:stats.length-missing.length,missing,high_distortion:high,distortion_threshold:'Absolute projected cell-area error>25%, source projected area at least1cell at this candidate',covered_cells:grid.counts.reduce((a,b)=>a+b,0),zero_cells:size**2-grid.counts.reduce((a,b)=>a+b,0),runs:grid.runs,spans:grid.spans,overlap_cells_including_same_location_components:grid.overlap_cells_including_same_location_components,layout,baseline_equivalence:baseline,timings:{load_and_compile_ms:Math.round(compiled-started),packing_and_gzip_ms:Math.round(packed-compiled),total_ms:Math.round(performance.now()-started)},peak_rss_bytes:process.resourceUsage().maxRSS*1024};
  fs.writeFileSync(path.join(cache,`zoom-${zoom}.json`),JSON.stringify(result));console.log(JSON.stringify({zoom,represented:result.represented,missing:missing.length,high_distortion:high.length,runs:grid.runs,gzip_bytes:layout.gzip_bytes,packed_bytes:layout.packed_bytes,peak_rss_bytes:result.peak_rss_bytes,total_ms:result.timings.total_ms}));
}else if(isMain){
  if(!process.argv.includes('--aggregate-only')){
    const features=loadFeatures(),hash=footprintHash(features),areaFile=path.join(cache,'wgs84-source-areas.json');
    if(!fs.existsSync(areaFile)||JSON.parse(fs.readFileSync(areaFile)).footprints_sha256!==hash){
      console.error(JSON.stringify({phase:'wgs84-source-areas',locations:features.length}));
      const python="import sys,json,pathlib;sys.path.insert(0,'scripts');from shapely.geometry import shape;from majority import canonical,area;P=pathlib.Path(sys.argv[1]);D=P.parent;world=json.loads(P.read_text());out={};\nfor part in world['parts']:\n for f in json.loads((D/part).read_text())['features']:out[f.get('id',f['properties']['id'])]=area(canonical(shape(f['geometry'])))\nprint(json.dumps(out))";
      const raw=execFileSync('python3',['-c',python,worldIndex],{maxBuffer:16*1024*1024,env:{...process.env,OPENBLAS_NUM_THREADS:'1'}});
      fs.writeFileSync(areaFile,JSON.stringify({footprints_sha256:hash,algorithms:['scripts/majority.py','scripts/ellipsoidal_area.py'].map(file=>({file,sha256:createHash('sha256').update(fs.readFileSync(file)).digest('hex')})),areas:JSON.parse(raw)}));
    }
  }
  for(const zoom of process.argv.includes('--aggregate-only')?[]:zooms){
    if(!Number.isInteger(zoom)||zoom<7||zoom>10)throw Error('Full candidate zoom must be7..10; higher full worlds need separate resource review');
    await new Promise((resolve,reject)=>{const child=spawn(process.execPath,['--max-old-space-size=4096',fileURLToPath(import.meta.url),'--candidate',`--zoom=${zoom}`,`--world-index=${worldIndex}`,`--cache=${cache}`,`--report=${reportFile}`],{stdio:'inherit'});child.on('error',reject);child.on('exit',code=>code?reject(Error(`Candidate${zoom}failed:${code}`)):resolve());});
  }
  const candidates=zooms.map(zoom=>JSON.parse(fs.readFileSync(path.join(cache,`zoom-${zoom}.json`)))),base=candidates.find(x=>x.zoom===7);
  if(!base)throw Error('Include zoom7 baseline');
  const currentFeatures=loadFeatures(),currentHash=footprintHash(currentFeatures);
  if(candidates.some(c=>c.footprints_sha256!==currentHash||c.cell_counts.length!==base.location_ids.length))throw Error('Cached full candidate grid is stale');
  const featureIndex=createGridIndex(currentFeatures),byId=new Map(featureIndex.map(x=>[x.feature.id,x])),isolated=[];
  const missingUnion=[...new Map(candidates.flatMap(c=>c.missing).map(x=>[x.id,x])).values()];
  for(const missing of missingUnion){
    const item=byId.get(missing.id),checks=[];
    for(let zoom=7;zoom<=Number(argument('isolated-max-zoom','14'));zoom++){
      const scaled=indexAt([item],zoom)[0],size=256*2**zoom;let cells=0;
      // Count intervals only: these are isolated-footprint samples, never claimed
      // collision-resolved world ownership at unevaluated resolutions.
      for(const polygon of scaled.polygons){
        const first=Math.max(0,Math.ceil(scaled.bounds[1]-.5)),last=Math.min(size,Math.ceil(scaled.bounds[3]-.5));
        for(let y=first;y<last;y++){const xs=[];for(const ring of polygon)for(let k=0;k<ring.length-2;k+=2){const x1=ring[k],y1=ring[k+1],x2=ring[k+2],y2=ring[k+3];if((y1<=y+.5&&y2>y+.5)||(y2<=y+.5&&y1>y+.5))xs.push(x1+(y+.5-y1)*(x2-x1)/(y2-y1));}xs.sort((a,b)=>a-b);for(let k=0;k+1<xs.length;k+=2)cells+=Math.max(0,Math.min(size,Math.ceil(xs[k+1]-.5))-Math.max(0,Math.ceil(xs[k]-.5)));}
      }
      checks.push({zoom,isolated_component_cell_hits:cells});
      // These holes are tiny; bound exploration once a robust interior is found.
      if(cells>=64&&zoom>=10)break;
    }
    isolated.push({id:missing.id,name:missing.name,owner:missing.owner,checks,first_isolated_hit_zoom:checks.find(x=>x.isolated_component_cell_hits)?.zoom??null});
  }
  const sourceReview=JSON.parse(fs.readFileSync('data/region-semantic-review.json')).pixel_missing_source_comparison??[],sourceById=new Map(sourceReview.map(x=>[x.id,x]));
  const report={version:1,footprints_sha256:base.footprints_sha256,method:'Fixed Web Mercator grid cell centers, even-odd source polygons including holes, smallest stable location-index tie priority; complete world ownership compiled independently once per candidate. Navigation is never involved.',scope:{locations:base.location_ids.length,all_location_ids:base.location_ids,source_area_cells_zoom7:base.source_area_cells_zoom7,source_wgs84_area_m2:base.source_wgs84_area_m2,locations_semantically_approved:'Global semantic approval remains incomplete; all current footprints evaluated, not falsely marked approved'},candidates:candidates.map(({location_ids,source_area_cells_zoom7,source_wgs84_area_m2,...x})=>x),missing_union_isolated_research:isolated.map(x=>({...x,source_comparison:sourceById.get(x.id)??null})),selection:{status:'pending-source-and-device-review',reason:'Candidate results must meet source correctness, disappearing-unit and distortion requirements together. No arbitrary cell reassignment or polygon inflation is permitted. Finer resolution does not repair bad source geometry/masks.'},constraints:{hosting_artifact_limit_bytes:256*1024*1024,hosting_asset_file_limit_bytes:25*1024*1024,shader_world_size:'uniform; stage activation must update renderer canonical GRID_ZOOM consistently',gpu_texture_width:2048,device_texture_sizes_to_assess:[2048,4096,8192,16384],cpu_fallback:'Packed rows/runs sampling is resolution independent; renderer transforms still import fixed GRID_ZOOM and must change consistently before deployment.'},completion:false};
  const aggregateErrors=(values,source)=>{const errors=values.map((v,i)=>source[i]?v/source[i]-1:null),above=errors.flatMap((error,i)=>error!==null&&Math.abs(error)>.25?[{id:report.scope.all_location_ids[i],relative_area_error:Number(error.toFixed(9))}]:[]);return {absolute_error_above25_count:above.length,maximum_absolute_relative_error:Math.max(...errors.map(e=>Math.abs(e??0))),records_above25:above};};
  const sumFiles=directory=>fs.existsSync(directory)?fs.readdirSync(directory,{withFileTypes:true}).reduce((n,e)=>n+(e.isDirectory()?sumFiles(path.join(directory,e.name)):e.isFile()?fs.statSync(path.join(directory,e.name)).size:0),0):0;
  const artifactBytes=sumFiles('dist/client')+sumFiles('dist/server')+sumFiles('dist/drizzle')+(fs.existsSync('.openai/hosting.json')?fs.statSync('.openai/hosting.json').size:0);
  const oldOwnershipBytes=report.candidates.find(c=>c.zoom===7).layout.gzip_bytes;
  for(const candidate of report.candidates){
    candidate.projected_all_location_distortion=aggregateErrors(candidate.cell_counts,report.scope.source_area_cells_zoom7.map(a=>a*4**(candidate.zoom-7)));
    candidate.wgs84_all_location_distortion=aggregateErrors(candidate.grid_wgs84_area_m2,report.scope.source_wgs84_area_m2);
    candidate.estimated_artifact_bytes_replacing_existing_grid=artifactBytes-oldOwnershipBytes+candidate.layout.gzip_bytes;
    candidate.estimated_artifact_limit_headroom_bytes=report.constraints.hosting_artifact_limit_bytes-candidate.estimated_artifact_bytes_replacing_existing_grid;
    candidate.device_capacity=report.constraints.device_texture_sizes_to_assess.map(max=>({max_texture_size:max,current_single_texture_layout_fits:candidate.layout.gpu_runs_texture_height<=max&&candidate.layout.gpu_rows_texture_height<=max}));
  }
  const adequate=report.candidates.filter(c=>c.missing.length===0&&c.projected_all_location_distortion.absolute_error_above25_count===0&&c.wgs84_all_location_distortion.absolute_error_above25_count===0).sort((a,b)=>a.zoom-b.zoom);
  report.selection={status:adequate.length?'numeric-candidate-selected-deployment-pending':'no-adequate-candidate',coarsest_tested_zoom_for_current_footprints:adequate[0]?.zoom??null,criteria:'Every current location has an actual collision-resolved cell; all-location projected and WGS84 geographic area errors at most 25%. This is a representation criterion, not approval of source semantics.',reason:'Finer resolution does not repair source label/coordinate defects or coastline/political-mask truncation. Activation requires consistent renderer constants, GPU device compatibility and measured mobile memory/loading performance; no source approval or deployment change is implied.'};
  report.constraints.measured_current_artifact_bytes=artifactBytes;
  const gpuProbe=path.join(cache,'gpu-capacity-probe.json');if(fs.existsSync(gpuProbe))report.constraints.observed_gpu_capacity=JSON.parse(fs.readFileSync(gpuProbe));
  report.background_policy='Zero cell ID means water or source coverage gap; it never means unclaimed land. This report exhaustively resolves current polygon ownership, while distinguishing actual missing land from ocean requires a separately approved coastline/water reference (coverage-report.json remains explicitly incomplete).';
  report.scope.wgs84_method='WGS84 ellipsoid latitude-strip integral for original straight longitude/latitude polygon edges with antimeridian-normalized geometry; canonical cell rectangles weighted analytically by their exact latitude strips. No equal-area-per-cell assumption.';
  report.scope.area_algorithms=JSON.parse(fs.readFileSync(path.join(cache,'wgs84-source-areas.json'))).algorithms;
  report.input_snapshot={world_index:worldIndex,world_index_sha256:createHash('sha256').update(fs.readFileSync(worldIndex)).digest('hex'),stage:stagedInput};
  report.source_geometry_issues={unresolved:true,records:report.missing_union_isolated_research.filter(x=>x.source_comparison&&(['Namibia','Somalia','Marshall Islands','Vatican'].includes(x.owner))).map(x=>({id:x.id,name:x.name,owner:x.owner,current_land_km2:x.source_comparison.current_land_km2,raw_source_land_km2:x.source_comparison.raw_source_land_km2,retained_source_land_share:x.source_comparison.retained_source_land_share,raw_source_point:x.source_comparison.raw_source_point,source_url:x.source_comparison.source_url,issue:x.owner==='Somalia'&&x.name==='BORAMA'?'Known country-mask clipping: current 1.24 km² versus original 1,575 km²; finer pixels cannot restore erased land.':x.owner==='Namibia'?'Published 2007 source-role and name/coordinate audit remains open; northern named units with southern coordinates require source repair, not grid closure.':x.owner==='Vatican'?'Original low-resolution reference is only 0.0122 km²; representing its current tiny remnant is not certification of actual territorial coverage.':'Substantial original/current footprint difference; source polygons may include water, so independently validate dry land before replacement.'})),caution:'Original source area can include marine water or mismatched source geometry; a retained-area ratio alone cannot prove which geography is correct. Newly missing candidates are also inventoried, even if absent from the earlier53-source review.'};
  fs.mkdirSync(path.dirname(reportFile),{recursive:true});fs.writeFileSync(reportFile,reportFile.endsWith('.gz')?gzipSync(JSON.stringify(report),{level:9}):JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({report:reportFile,candidates:report.candidates.map(x=>({zoom:x.zoom,missing:x.missing.length,high_distortion:x.high_distortion.length}))}));
}
