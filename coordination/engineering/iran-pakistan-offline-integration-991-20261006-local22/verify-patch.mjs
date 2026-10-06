// Independent complete decoded-grid difference audit, with no fake release ID.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {loadOwnershipAssets} from '../../../src/ownership-assets.js';
import {unshuffleOwnershipBytes} from '../../../src/ownership-codec.js';
import {ownershipRun} from '../../../src/pixel-ownership.js';
import {committedPreparationFiles,requirePlainExecution} from '../../../scripts/native-ownership/native-preparation-guards.mjs';

requirePlainExecution();
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..'),prefix='coordination/engineering/iran-pakistan-offline-integration-991-20261006-local22';
const [oneName,twoName,outName]=process.argv.slice(2);
const ownedPath=name=>{const p=path.resolve(root,name??'');if(!p.startsWith(path.join(root,prefix)+path.sep))throw Error('Owned path required');return p;};
const one=ownedPath(oneName),two=ownedPath(twoName),out=ownedPath(outName);
if(one===two||fs.existsSync(out))throw Error('Distinct complete vintages and fresh receipt required');
const head=execFileSync('git',['-C',root,'rev-parse','HEAD'],{encoding:'utf8'}).trim(),digest=raw=>createHash('sha256').update(raw).digest('hex');
const executed=committedPreparationFiles(root,head,['package.json',prefix+'/verify-patch.mjs','src/ownership-assets.js',
  'src/ownership-codec.js','src/ownership-method.js','src/pixel-ownership.js','src/pixel-grid.js','scripts/native-ownership/native-preparation-guards.mjs']);
const inventory=dir=>fs.readdirSync(dir,{withFileTypes:true}).flatMap(item=>{
  const file=path.join(dir,item.name);if(item.isDirectory())return inventory(file).map(row=>({...row,path:item.name+'/'+row.path}));
  if(!item.isFile())throw Error('Ordinary complete products required');const raw=fs.readFileSync(file);return [{path:item.name,bytes:raw.length,sha256:digest(raw)}];
}).sort((a,b)=>a.path.localeCompare(b.path));
const products=inventory(one),other=inventory(two);
if(JSON.stringify(products)!==JSON.stringify(other))throw Error('Complete two-run product bytes differ');
const manifest=JSON.parse(fs.readFileSync(path.join(one,'pending-manifest.json'))),report=JSON.parse(fs.readFileSync(path.join(one,'patch-report.json')));
if(manifest.geographic_release!==null||!manifest.release_pending||manifest.installation_ready!==false||report.changed_cells!==954||report.lost_cells||report.new_overlaps)throw Error('Pending candidate contract differs');
const baselinePin=manifest.provenance.native_baseline_manifest;
const read=(commit,name)=>execFileSync('git',['-C',root,'show',commit+':'+name],{maxBuffer:32*1024*1024});
const baselineRaw=read(baselinePin.commit,baselinePin.path);
if(digest(baselineRaw)!==baselinePin.sha256)throw Error('Original grid manifest differs');
const baselineManifest=JSON.parse(baselineRaw),base=await loadOwnershipAssets(baselineManifest,async url=>
  new Response(read(baselinePin.commit,path.posix.dirname(baselinePin.path)+'/'+url.slice(2))));
const next={version:manifest.version,size:manifest.size,coordinateBits:manifest.coordinateBits,rows:new Uint32Array(manifest.size*2),runs:new Uint32Array(manifest.runWords)};
for(const kind of ['rows','runs']){
  let offset=0;
  for(const part of manifest.parts.filter(p=>p.kind===kind).sort((a,b)=>a.offset-b.offset)){
    if(part.offset!==offset||part.encoding!=='byte-shuffle'||part.words<1||part.words>1048576||!/^native-v1\/ownership\/(rows|runs)-[0-9]+\.bin\.gz$/.test(part.path))throw Error('Invalid native part accounting');
    const encoded=fs.readFileSync(path.join(one,part.path));if(encoded.length!==part.bytes||digest(encoded)!==part.sha256)throw Error('Encoded candidate bytes differ');
    const raw=gunzipSync(encoded,{maxOutputLength:part.words*4}),words=unshuffleOwnershipBytes(raw,part.words);
    if(words.byteLength!==part.decoded_bytes||digest(Buffer.from(words.buffer))!==part.decoded_sha256)throw Error('Decoded candidate words differ');
    next[kind].set(words,offset);offset+=part.words;
  }
  if(offset!==next[kind].length)throw Error('Incomplete candidate word accounting');
}
const expected=new Map();
// Use the independently retained source delta as an explicit per-row contract.
const deltaRaw=read('d0cc67eac85038159f88a673acbc39b77ab7461d','coordination/engineering/iran-pakistan-native-joint-991-20261006-local21/native-v1/native-cells.json');
const delta=JSON.parse(deltaRaw);
for(const edit of delta.changed_runs){if(edit.before.length||edit.after.length!==1||!edit.component)throw Error('Unsupported source delta');if(!expected.has(edit.y))expected.set(edit.y,[]);expected.get(edit.y).push(edit);}
let checkedRuns=0,changedCells=0,owned=0,changedRows=0,rowOffset=0;
const counts=new Map(report.per_owner_cells.map(([id])=>[id,0])),differences=[];
for(let y=0;y<next.size;y++){
  if(next.rows[y*2]!==rowOffset)throw Error('Unaccounted candidate row');rowOffset+=next.rows[y*2+1];
  const before=[],after=[];
  for(let k=base.rows[y*2];k<base.rows[y*2]+base.rows[y*2+1];k++)before.push(ownershipRun(base,k));
  for(let k=next.rows[y*2];k<rowOffset;k++){
    const run=ownershipRun(next,k);
    if(run.end<=run.start||run.start<0||run.end>next.size||!counts.has(run.id)||after.at(-1)?.end>run.start)throw Error('Invalid output run');
    after.push(run);owned+=run.end-run.start;counts.set(run.id,counts.get(run.id)+run.end-run.start);checkedRuns++;
  }
  const edges=[...new Set([0,next.size,...before.flatMap(r=>[r.start,r.end]),...after.flatMap(r=>[r.start,r.end])])].sort((a,b)=>a-b);
  let a=0,b=0,rowChanged=false;
  for(let i=0;i<edges.length-1;i++){
    const start=edges[i],end=edges[i+1];while(a<before.length&&before[a].end<=start)a++;while(b<after.length&&after[b].end<=start)b++;
    const old=before[a]?.start<=start?before[a].id:0,current=after[b]?.start<=start?after[b].id:0;
    if(old===current)continue;
    if(old!==0||!expected.get(y)?.some(e=>e.start<=start&&e.end>=end&&e.after[0]===current))throw Error('Decoded candidate differs outside supported empty-cell additions');
    differences.push({y,start,end,before:old,after:current});changedCells+=end-start;rowChanged=true;
  }
  if(rowChanged)changedRows++;
}
if(rowOffset*2!==next.runs.length||checkedRuns!==manifest.runWords/2||changedCells!==954||owned!==manifest.accounting.owned_cells||
  owned!==baselineManifest.accounting.owned_cells+954||JSON.stringify([...counts])!==JSON.stringify(report.per_owner_cells))throw Error('Exhaustive decoded-grid accounting differs');
const receipt={version:1,evaluation_commit:head,executed_sources:executed,preparation_commit:report.evaluation_commit,
  baseline_manifest:baselinePin,source_delta_sha256:digest(deltaRaw),pending_manifest_sha256:digest(fs.readFileSync(path.join(one,'pending-manifest.json'))),
  products,two_run_products:products.length,run_one_sha256:digest(Buffer.from(JSON.stringify(products))),run_two_sha256:digest(Buffer.from(JSON.stringify(other))),
  checked_rows:next.size,checked_cells:next.size**2,unchecked_cells:0,checked_baseline_runs:base.runs.length/2,checked_candidate_runs:checkedRuns,
  changed_cells:changedCells,changed_rows:changedRows,lost_owned_cells:0,unsupported_changes:0,owned_cells:owned,differences,
  release_pending:true,installed:false,published:false,limits:['Full decoded equality outside exact reviewed additions; no new source authority or final release/build selection.']};
fs.writeFileSync(out,JSON.stringify(receipt)+'\n',{flag:'wx'});console.log(JSON.stringify({checked_rows:next.size,changed_cells:changedCells,changed_rows:changedRows,checked_candidate_runs:checkedRuns,receipt:outName}));
