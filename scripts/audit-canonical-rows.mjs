// Immutable, bounded-row execution of the worldwide representation audit.
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync,gzipSync} from 'node:zlib';
import {performance} from 'node:perf_hooks';
import {createGridIndex,GRID_WIDTH} from '../src/pixel-grid.js';
import {loadOwnershipAssets} from '../src/ownership-assets.js';
import {ownershipRun} from '../src/pixel-ownership.js';
import {polygonIntervals,compareRow} from './audit-grid-intervals.mjs';
const options={};
for(let n=2;n<process.argv.length;n+=2){
  const key=process.argv[n];
  if(!['--commit','--row-start','--row-end','--out'].includes(key)||!process.argv[n+1]||options[key])
    throw Error('Require explicit immutable commit, bounded rows and fresh output');
  options[key]=process.argv[n+1];
}
const commit=options['--commit'],rowStart=Number(options['--row-start']),rowEnd=Number(options['--row-end']);
if(!/^[a-f0-9]{40}$/.test(commit??'')||!Number.isInteger(rowStart)||!Number.isInteger(rowEnd)||
   rowStart<0||rowEnd>GRID_WIDTH||rowEnd<=rowStart||rowEnd-rowStart>4096||
   !options['--out']||fs.existsSync(options['--out']))throw Error('Invalid immutable audit domain or existing output');
const hash=raw=>createHash('sha256').update(raw).digest('hex');
const files=new Map(),started=performance.now();
const auditHead=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
for(const name of ['scripts/audit-grid-intervals.mjs','scripts/audit-canonical-rows.mjs'])
  if(hash(execFileSync('git',['show',auditHead+':'+name]))!==hash(fs.readFileSync(name)))
    throw Error('Commit the exact audit implementation before generation');
function read(name){
  if(!/^(data|src)\/[a-zA-Z0-9_./-]+$/.test(name)||name.includes('..'))throw Error('Unsafe immutable path');
  const raw=execFileSync('git',['show',commit+':'+name],{maxBuffer:32*1024*1024});
  files.set(name,{path:name,bytes:raw.length,sha256:hash(raw)});return raw;
}
const decode=raw=>JSON.parse(raw[0]===31&&raw[1]===139?gunzipSync(raw,{maxOutputLength:32*1024*1024}):raw);
for(const name of ['src/pixel-grid.js','src/pixel-ownership.js','src/ownership-assets.js','src/ownership-codec.js'])
  if(hash(read(name))!==hash(fs.readFileSync(name)))throw Error('Executed application code differs from immutable input');
const manifest=decode(read('data/canonical-grid/manifest.json'));
if(manifest.size!==GRID_WIDTH||manifest.coordinateBits!==19)throw Error('Original grid convention differs');
const boundsRaw=read('data/canonical-grid/'+manifest.bounds.path);
if(hash(boundsRaw)!==manifest.bounds.sha256)throw Error('Original bounds pin differs');
const bounds=decode(boundsRaw),owners=new Map(bounds.map(r=>[r.id,r]));
if(owners.size!==bounds.length||bounds.some((r,n)=>r.index!==n+1))throw Error('Original owner registry incomplete');
const hierarchy=read('data/hierarchy.json');
if(hash(hierarchy)!==manifest.hierarchy_sha256)throw Error('Original hierarchy pin differs');
const pointer=decode(read('data/geographic-releases/current-manifest.json'));
const releaseRaw=read('data/geographic-releases/'+pointer.path);
if(hash(releaseRaw)!==pointer.sha256)throw Error('Original release pointer differs');
const release=decode(releaseRaw).releases.at(-1);
if(release.footprints_sha256!==manifest.footprints_sha256||release.hierarchy_sha256!==manifest.hierarchy_sha256||
   release.expected_counts.location!==bounds.length)throw Error('Release and ownership scope differ');
const loaded=[];
const native=await loadOwnershipAssets(manifest,async url=>{
  const name='data/canonical-grid/'+url.replace(/^\.\//,'');loaded.push(name);
  return new Response(read(name),{status:200});
});
if(loaded.length!==manifest.parts.length||new Set(loaded).size!==loaded.length)throw Error('Original partition accounting differs');
let totalNativeRuns=0,totalNativeOwned=0;
for(let y=0;y<native.size;y++){
  let previous=0;
  const offset=native.rows[y*2],count=native.rows[y*2+1];
  for(let n=offset;n<offset+count;n++){
    const r=ownershipRun(native,n);
    if(r.start<previous||r.end<=r.start||r.end>native.size||r.id<1||r.id>bounds.length)
      throw Error('Invalid original native run');
    previous=r.end;totalNativeOwned+=r.end-r.start;
  }
  totalNativeRuns+=count;
}
const index=decode(read('data/world-index.json'));
if(!Array.isArray(index.parts)||new Set(index.parts).size!==index.parts.length)throw Error('Invalid original world inventory');
const seen=new Set(),rows=new Map(),ties=[],partInventory=[],boundsDifferences=[];
for(const part of index.parts){
  const name='data/'+part,collection=decode(read(name));
  if(collection.type!=='FeatureCollection'||!Array.isArray(collection.features))throw Error('Invalid original world part');
  const features=collection.features.map(f=>{
    const record=owners.get(f.id);
    if(!record||seen.has(f.id)||f.properties?.parent_id!==record.province_id)throw Error('Original owner/parent crosswalk differs');
    seen.add(f.id);return {...f,pixelIndex:record.index};
  });
  const projected=createGridIndex(features),selected=[];
  for(const item of projected){
    const owner=owners.get(item.feature.id);item.index=owner.index;
    if(item.bounds.some((v,n)=>v!==owner.bounds[n]))boundsDifferences.push({owner:owner.id,
      stored_bounds:owner.bounds,executed_projection_bounds:item.bounds});
    if(item.bounds[1]<=rowEnd-.5&&item.bounds[3]>=rowStart+.5)selected.push(item);
  }
  const sparse=polygonIntervals(selected,{size:native.size,rowStart,rowEnd});
  for(const [y,spans] of sparse.rows){
    if(!rows.has(y))rows.set(y,[]);
    rows.get(y).push(...spans);
  }
  ties.push(...sparse.ties);
  partInventory.push({path:name,original_locations:features.length,intersecting_locations:selected.length});
}
if(seen.size!==bounds.length||[...owners.keys()].some(id=>!seen.has(id)))throw Error('Incomplete original world roster');
const counts={},findings=[];
for(let y=rowStart;y<rowEnd;y++){
  const original=[],offset=native.rows[y*2],count=native.rows[y*2+1];
  for(let n=offset;n<offset+count;n++){
    const r=ownershipRun(native,n);original.push(r.start,r.end,r.id);
  }
  const result=compareRow(rows.get(y)??[],original,native.size);
  for(const [key,value] of Object.entries(result.counts))counts[key]=(counts[key]??0)+value;
  for(const finding of result.findings)findings.push({y,...finding});
}
const checked=(rowEnd-rowStart)*native.size;
if(counts.checked_cells!==checked)throw Error('Incomplete declared domain');
const result={version:1,method_id:'sparse-canonical-row-comparison',evaluation_commit:auditHead,baseline_commit:commit,
  scientific_approval:false,installation_ready:false,source_files:[...files.values()].sort((a,b)=>a.path.localeCompare(b.path)),
  executed_audit_sources:['scripts/audit-grid-intervals.mjs','scripts/audit-canonical-rows.mjs'].map(name=>
    ({path:name,sha256:hash(fs.readFileSync(name))})),geographic_release:release.id,
  world_locations:seen.size,original_partitions:loaded.length,total_native_runs:totalNativeRuns,total_native_owned_cells:totalNativeOwned,
  domain:{size:native.size,row_start:rowStart,row_end:rowEnd,checked_rows:rowEnd-rowStart,
    unchecked_rows:native.size-(rowEnd-rowStart),checked_cells:checked,unchecked_cells:native.size**2-checked},
  counts,part_inventory:partInventory,findings,boundary_ties:ties,projection_bounds_differences:boundsDifferences,
  execution_runtime:{node:process.version,platform:process.platform,architecture:process.arch},
  limits:['Only the explicitly declared rows are exhaustively compared; every other row remains unchecked.',
    'Actual application projected edges and first-owner cell-centre convention; not native longitude/latitude coverage or physical truth.',
    'Every bitwise stored/executed projected-bound difference is retained without tolerance; actual computed bounds select this audit domain.',
    'No water or administrative affiliation inferred; source/projection-invalid geography and continuous gaps remain separately unresolved.',
    'No source bytes, world footprints, native ownership, release history or live facts are changed.']};
const payload=Buffer.from(JSON.stringify(result)+'\n');
fs.writeFileSync(options['--out'],gzipSync(payload,{mtime:0}));
console.log(JSON.stringify({domain:result.domain,counts,findings:findings.length,boundary_ties:ties.length,
  projected_bound_differences:boundsDifferences.length,original_source_bytes:[...files.values()].reduce((n,f)=>n+f.bytes,0),output_sha256:hash(fs.readFileSync(options['--out'])),
  elapsed_seconds:(performance.now()-started)/1000,node_resource_usage_maxRSS:process.resourceUsage().maxRSS}));
