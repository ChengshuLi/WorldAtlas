// Immutable original native membership versus stored canonical ownership.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {gzipSync} from 'node:zlib';
import {performance} from 'node:perf_hooks';
import {nativeRowLatitudes,nativePolygonIntervals,NATIVE_GRID_METHOD} from '../src/native-grid.js';
import {ownershipRun} from '../src/pixel-ownership.js';
import {compareRow} from './audit-grid-intervals.mjs';
import {loadNativeAuditInputs,sha256} from './native-grid-inputs.mjs';

const options={};
for(let n=2;n<process.argv.length;n+=2){
  const key=process.argv[n];
  if(!['--repo','--commit','--out','--row-start','--row-end','--partition-rows'].includes(key)||
    !process.argv[n+1]||options[key])throw Error('Use explicit repo, immutable commit, fresh output and row domain');
  options[key]=process.argv[n+1];
}
const repo=options['--repo'],commit=options['--commit'],out=options['--out'];
const rowStart=Number(options['--row-start']),rowEnd=Number(options['--row-end']);
const partitionRows=Number(options['--partition-rows']??4096),size=262166;
const root=fileURLToPath(new URL('..',import.meta.url));
if(!repo||fs.realpathSync(repo)!==fs.realpathSync(root)||!out||fs.existsSync(out)||
  !/^[a-f0-9]{40}$/.test(commit??'')||!Number.isInteger(rowStart)||!Number.isInteger(rowEnd)||
  rowStart<0||rowEnd>size||rowStart>=rowEnd||!Number.isInteger(partitionRows)||partitionRows<1||partitionRows>4096)
  throw Error('Invalid immutable audit domain, executed repository or existing output');
const head=execFileSync('git',['-C',repo,'rev-parse','HEAD'],{encoding:'utf8'}).trim();
const executed=['scripts/audit-native-grid.mjs','scripts/native-grid-inputs.mjs','scripts/audit-grid-intervals.mjs',
  'src/native-grid.js','src/pixel-grid.js','src/pixel-ownership.js','src/ownership-assets.js','src/ownership-codec.js'];
const code=executed.map(name=>{
  const raw=fs.readFileSync(path.join(repo,name));
  if(sha256(raw)!==sha256(execFileSync('git',['-C',repo,'show',head+':'+name])))
    throw Error('Commit exact executed audit implementation before generation');
  return {path:name,bytes:raw.length,sha256:sha256(raw)};
});
for(const name of executed.filter(name=>name.startsWith('src/')&&name!=='src/native-grid.js'))
  if(sha256(fs.readFileSync(path.join(repo,name)))!==sha256(execFileSync('git',['-C',repo,'show',commit+':'+name])))
    throw Error('Executed legacy ownership code differs from immutable original');
const started=performance.now();
fs.mkdirSync(out,{recursive:true});
const progress={phase:'loading',evaluation_commit:head,baseline_commit:commit,completed_rows:0,
  declared_rows:rowEnd-rowStart,completed_partitions:0,observations:[]};
const saveProgress=()=>fs.writeFileSync(path.join(out,'progress.json'),JSON.stringify(progress,null,2)+'\n');
saveProgress();
function write(name,value){
  const raw=Buffer.isBuffer(value)?value:Buffer.from(JSON.stringify(value)+'\n');
  if(raw.length>32*1024*1024)throw Error('Output exceeds existing whole-file decoded budget');
  const encoded=name.endsWith('.gz')?gzipSync(raw,{level:9}):raw;
  fs.writeFileSync(path.join(out,name),encoded,{flag:'wx'});
  return {path:name,bytes:encoded.length,sha256:sha256(encoded),decoded_bytes:raw.length,decoded_sha256:sha256(raw)};
}
const labels={checked_cells:'checked_cells',projected_covered:'native_source_covered_cells',native_owned:'stored_owned_cells',
  raster_only_gap:'projection_empty_cells',native_outside_projected:'projection_overpaint_cells',
  foreign_owner:'projection_foreign_owner_cells',multiple_projected_owners:'native_multiple_owner_cells',
  first_owner_difference:'owner_difference_cells'};
const kinds={raster_only_gap:'projection-empty',native_outside_projected:'projection-overpaint',
  foreign_owner:'projection-foreign-owner',multiple_projected_owners:'native-multiple-owners',
  first_owner_difference:'first-owner-difference'};
const limits=[
  'Defined native binary-coordinate even-odd model, not independent geographic truth or source authority.',
  'Original native topology requires separate validity accounting; closed finite rings alone do not prove validity.',
  'Latitude table is generated once and pinned in exact little-endian bytes. Reproduction here is not an untested cross-platform inverse-math promise.',
  'Half-open native latitude min-exclusive/max-inclusive and longitude left-inclusive/right-exclusive; boundary incidences with duplicates are retained.',
  'Source gaps and physical land/water, coast, source vintages and political affiliation remain unclassified. Both-model-empty cells do not establish water.',
  'Only declared canonical rows are compared. Original atlas coverage excludes Antarctica; polar/outside-grid geography is not certified.',
  'No source coordinates, native pointsets, stable identities/parents, historical facts, old ownership grids/rules or release history are changed.',
  'Diagnostic only: no candidate installation, geographic approval, live provider/database operation or publication.'
];
try{
  const inputs=await loadNativeAuditInputs(repo,commit);
  const latitudes=nativeRowLatitudes(size),latitudeBytes=Buffer.alloc(size*8);
  for(let y=0;y<size;y++)latitudeBytes.writeDoubleLE(latitudes[y],y*8);
  const latitudeProduct=write('native-row-latitudes.f64le.gz',latitudeBytes);
  // Complete roster is recoverable from the pinned original bounds/world parts.
  // Keep its canonical digest without exporting a duplicate world inventory.
  const rosterDigest=sha256(Buffer.from(JSON.stringify(inputs.roster)+'\n'));
  const inventory={version:1,baseline_commit:commit,evaluation_commit:head,method:NATIVE_GRID_METHOD,
    source_files:inputs.sourceFiles,executed_sources:code,latitude_product:latitudeProduct,
    owner_roster:{count:inputs.roster.length,canonical_json_sha256:rosterDigest,
      restoration:'Original indices/IDs/parents in bounds; original names/containing paths in all pinned world parts.'},
    geographic_release:inputs.release.id,
    footprints_sha256:inputs.manifest.footprints_sha256,hierarchy_sha256:inputs.manifest.hierarchy_sha256,
    original_partitions:inputs.manifest.parts.length,locations:inputs.roster.length,vertices:inputs.vertices,
    original_total_runs:inputs.totalStoredRuns,original_owned_cells:inputs.totalStoredOwned};
  const inventoryProduct=write('inputs.json',inventory),parts=[],totals={};
  let findingsCount=0,boundaryRecords=0,boundaryIncidences=0;
  progress.phase='comparing';saveProgress();
  for(let first=rowStart;first<rowEnd;first+=partitionRows){
    const end=Math.min(rowEnd,first+partitionRows),began=performance.now();
    // Include touching bounds for diagnostics even when half-open fill excludes
    // that edge. Selection must not hide horizontal/lower-vertex incidences.
    const selected=inputs.index.filter(item=>item.minLat<=latitudes[first]&&item.maxLat>=latitudes[end-1]);
    const native=nativePolygonIntervals(selected,{size,rowStart:first,rowEnd:end,latitudes});
    const counts={},findings=[];
    for(let y=first;y<end;y++){
      const stored=[],offset=inputs.stored.rows[y*2],count=inputs.stored.rows[y*2+1];
      for(let n=offset;n<offset+count;n++){const r=ownershipRun(inputs.stored,n);stored.push(r.start,r.end,r.id);}
      const compared=compareRow(native.rows.get(y)??[],stored,size);
      for(const [old,value] of Object.entries(compared.counts))counts[labels[old]]=(counts[labels[old]]??0)+value;
      for(const f of compared.findings)findings.push({y,start:f.start,end:f.end,stored_owner:f.native_owner,
        native_owners:f.projected_owners,kinds:f.kinds.map(kind=>kinds[kind])});
    }
    if(counts.checked_cells!==(end-first)*size)throw Error('Unchecked cells in declared native partition');
    const product=write(`rows-${first}-${end}.json.gz`,{version:1,method:NATIVE_GRID_METHOD,
      evaluation_commit:head,baseline_commit:commit,inputs_sha256:inventoryProduct.sha256,
      latitude_sha256:latitudeProduct.decoded_sha256,
      domain:{size,row_start:first,row_end:end,checked_rows:end-first,unchecked_rows:size-(end-first),
        checked_cells:counts.checked_cells,unchecked_cells:size**2-counts.checked_cells},
      counts,findings,boundary_ties:native.ties,scientific_approval:false,native_topology_verified:false,limits});
    parts.push({...product,row_start:first,row_end:end});
    for(const [key,value] of Object.entries(counts))totals[key]=(totals[key]??0)+value;
    findingsCount+=findings.length;boundaryRecords+=native.ties.length;
    boundaryIncidences+=native.ties.reduce((n,t)=>n+(t.end===undefined?1:t.end-t.start),0);
    progress.completed_rows+=end-first;progress.completed_partitions++;
    progress.observations.push({row_start:first,row_end:end,elapsed_ms:performance.now()-began,maxRSS_raw:process.resourceUsage().maxRSS});
    saveProgress();console.log(JSON.stringify({rows:[first,end],completed:progress.completed_rows,
      checked_cells:counts.checked_cells,different_cells:counts.owner_difference_cells}));
  }
  if(totals.checked_cells!==(rowEnd-rowStart)*size||progress.completed_rows!==rowEnd-rowStart)
    throw Error('Incomplete declared native domain');
  const report={version:1,method:NATIVE_GRID_METHOD,evaluation_commit:head,baseline_commit:commit,
    domain:{size,row_start:rowStart,row_end:rowEnd,checked_rows:rowEnd-rowStart,
      unchecked_rows:size-(rowEnd-rowStart),checked_cells:totals.checked_cells,unchecked_cells:size**2-totals.checked_cells},
    counts:totals,findings_intervals:findingsCount,boundary_diagnostic_records:boundaryRecords,
    boundary_centre_incidences:boundaryIncidences,parts,inputs:inventoryProduct,
    scientific_approval:false,native_topology_verified:false,installation_ready:false,limits};
  write('report.json',report);progress.phase='complete';progress.elapsed_ms=performance.now()-started;
  progress.maxRSS_raw=process.resourceUsage().maxRSS;saveProgress();
}catch(error){progress.phase='failed';progress.error=error.message;progress.elapsed_ms=performance.now()-started;
  saveProgress();throw error;}
