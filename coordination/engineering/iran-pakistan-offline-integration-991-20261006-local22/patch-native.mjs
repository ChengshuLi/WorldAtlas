// Materialize reviewed additions on a verified native grid; never select a build.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gzipSync,gunzipSync} from 'node:zlib';
import {loadOwnershipAssets} from '../../../src/ownership-assets.js';
import {ownershipRun} from '../../../src/pixel-ownership.js';
import {shuffleOwnershipBytes} from '../../../src/ownership-codec.js';
import {check} from '../iran-pakistan-native-joint-991-20261006-local21/native-check.mjs';
import {validateNativeSelectionReceipt} from '../../../scripts/native-ownership/require-verified-selection.mjs';
import {committedPreparationFiles,requirePlainExecution} from '../../../scripts/native-ownership/native-preparation-guards.mjs';

requirePlainExecution();
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const prefix='coordination/engineering/iran-pakistan-offline-integration-991-20261006-local22';
const options={};
for(let i=2;i<process.argv.length;i+=2){
  if(!['--out','--migration'].includes(process.argv[i])||!process.argv[i+1]||options[process.argv[i]])throw Error('Fresh output and committed migration required');
  options[process.argv[i]]=process.argv[i+1];
}
const out=path.resolve(root,options['--out']),migrationPath=options['--migration'];
if(!out.startsWith(path.join(root,prefix)+path.sep)||fs.existsSync(out)||!migrationPath?.startsWith(prefix+'/'))throw Error('Fresh owned output required');
const head=execFileSync('git',['-C',root,'rev-parse','HEAD'],{encoding:'utf8'}).trim();
const digest=raw=>createHash('sha256').update(raw).digest('hex');
const executed=committedPreparationFiles(root,head,['package.json',prefix+'/patch-native.mjs',
  'src/ownership-assets.js','src/ownership-codec.js','src/ownership-method.js','src/pixel-ownership.js','src/pixel-grid.js',
  'src/native-grid.js','src/native-runtime.js','scripts/audit-grid-intervals.mjs',
  'scripts/native-ownership/require-verified-selection.mjs','scripts/native-ownership/verified-candidates.json',
  'scripts/native-ownership/read-pinned-build-file.mjs','scripts/package-inputs.mjs','scripts/evidence-quality.mjs',
  'scripts/native-ownership/native-preparation-guards.mjs','scripts/native-ownership/compile-native-ownership.mjs',
  'coordination/engineering/iran-pakistan-native-joint-991-20261006-local21/native-check.mjs']);
let consumed=executed.reduce((n,f)=>n+f.bytes,0);
const inputs=[];
function read(commit,name){
  if(!/^[a-f0-9]{40}$/.test(commit)||!name.split('/').every(p=>p&&p!=='.'&&p!=='..'))throw Error('Pinned ordinary input required');
  const tree=execFileSync('git',['-C',root,'ls-tree','-z',commit,'--',name],{encoding:'utf8'});
  if(!/^100644 blob /.test(tree)||tree.slice(tree.indexOf('\t')+1)!==name+'\0')throw Error('Input must be ordinary');
  const blob=tree.split(' ')[2].split('\t')[0];
  const bytes=Number(execFileSync('git',['-C',root,'cat-file','-s',blob],{encoding:'utf8'}));
  if(bytes>32*1024*1024)throw Error('Input file exceeds bounded size');
  consumed+=bytes;if(consumed>256*1024*1024)throw Error('Input/output byte budget exceeded');
  const raw=execFileSync('git',['-C',root,'cat-file','blob',blob],{maxBuffer:32*1024*1024});
  if(raw.length!==bytes)throw Error('Incomplete input');
  inputs.push({commit,path:name,bytes,sha256:digest(raw)});return raw;
}
const originalCommit='548c5f89f00271050823076a84695bb41e1b8454';
const originalPrefix='coordination/engineering/native-grid-candidate-1010-20261005-local16/candidate-v1/';
const originalRaw=read(originalCommit,originalPrefix+'manifest.json'),original=JSON.parse(originalRaw);
if(digest(originalRaw)!=='efe31373ff6a2c3f4ba5f11f8cbe37b25337778b344d9dbf1d3dfde301e3e722')throw Error('Original verified manifest differs');
const verificationRaw=read(originalCommit,'coordination/engineering/native-grid-candidate-1010-20261005-local16/decoded-native-verification.json');
if(digest(verificationRaw)!=='3fd8d5cfb18d100af0aee8bb94d33ce25bb5ccb9b2e02a55a8c15d585a86a410')throw Error('Original exact-domain proof differs');
validateNativeSelectionReceipt(original,digest(originalRaw),JSON.parse(verificationRaw));
const migration=JSON.parse(read(head,migrationPath));
if(migration.before_footprints_sha256!==original.footprints_sha256||migration.changed_ids.length!==2||
  migration.complete_reconstructed_features!==original.accounting.owners||migration.historical_claims_transferred!==false||
  migration.exact_original_features_restored!==true)throw Error('Staged geometry differs from verified native baseline');
const proofCommit='d0cc67eac85038159f88a673acbc39b77ab7461d';
const candidates=JSON.parse(read(proofCommit,'coordination/engineering/iran-pakistan-native-joint-991-20261006-local21/results-v3/candidates.json'));
const staged=JSON.parse(read('06bf4087bf5aec0e7071830ba61e99105f2c3697','coordination/engineering/iran-pakistan-grid-proof-971-20261005-local11/results-v1/staged-neighbors.json'));
const latitudeEncoded=read(original.native_latitudes.commit,original.native_latitudes.path);
if(digest(latitudeEncoded)!==original.native_latitudes.sha256)throw Error('Normative latitude pin differs');
const latitudeRaw=gunzipSync(latitudeEncoded,{maxOutputLength:original.size*8});
if(digest(latitudeRaw)!=='66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23')throw Error('Normative latitude bytes differ');
const latitudes=Float64Array.from({length:original.size},(_,y)=>latitudeRaw.readDoubleLE(y*8));
const changes=check(staged,candidates,latitudes);
if(changes.counts.changed!==954||changes.counts.lost||changes.counts.new_multiple||changes.counts.outside_component_changed)throw Error('Actual source delta proof differs');
const grid=await loadOwnershipAssets(original,async url=>new Response(read(originalCommit,originalPrefix+url.slice(2))));
const edits=new Map();
for(const edit of changes.changed_runs){
  if(edit.before.length||edit.after.length!==1||!edit.component)throw Error('Only component-contained unowned-cell additions supported');
  if(!edits.has(edit.y))edits.set(edit.y,[]);edits.get(edit.y).push({start:edit.start,end:edit.end,id:edit.after[0]});
}
const counts=new Map(Array.from({length:original.accounting.owners},(_,i)=>[i+1,0]));
const rows=new Uint32Array(original.size*2),parts=[],partWords=1048576,buffer=new Uint32Array(partWords);
let used=0,offset=0,runs=0,owned=0,changedCells=0,changedRows=0;
fs.mkdirSync(out,{recursive:false});
function write(name,raw,decoded=raw){
  if(Math.max(raw.length,decoded.length)>32*1024*1024)throw Error('Product exceeds bounded size');
  consumed+=raw.length;if(consumed>256*1024*1024)throw Error('Input/output byte budget exceeded');
  const file=path.join(out,name);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,raw,{flag:'wx'});
  return {path:name,bytes:raw.length,sha256:digest(raw),decoded_bytes:decoded.length,decoded_sha256:digest(decoded)};
}
function part(kind,first,words){
  const raw=Buffer.from(words.buffer,words.byteOffset,words.byteLength);
  return {kind,offset:first,words:words.length,encoding:'byte-shuffle',...write(`native-v1/ownership/${kind}-${first}.bin.gz`,gzipSync(shuffleOwnershipBytes(words),{level:9}),raw)};
}
function flush(){if(used){parts.push(part('runs',offset,buffer.slice(0,used)));offset+=used;used=0;}}
function append({start,end,id}){
  if(used===partWords)flush();buffer[used++]=(id%8192)*524288+start;buffer[used++]=Math.floor(id/8192)*524288+end-1;
  runs++;owned+=end-start;counts.set(id,counts.get(id)+end-start);
}
for(let y=0;y<grid.size;y++){
  rows[y*2]=runs;const rowEdits=edits.get(y)??[];const existing=[];
  for(let k=grid.rows[y*2];k<grid.rows[y*2]+grid.rows[y*2+1];k++)existing.push(ownershipRun(grid,k));
  if(rowEdits.length){
    for(const edit of rowEdits){
      if(!counts.has(edit.id)||existing.some(run=>run.start<edit.end&&run.end>edit.start))throw Error('Global baseline owns proposed empty cells');
      changedCells+=edit.end-edit.start;
    }
    changedRows++;
  }
  const merged=[...existing,...rowEdits].sort((a,b)=>a.start-b.start);let pending=null;
  for(const run of merged){
    if(pending&&pending.end>run.start)throw Error('New global overlap');
    if(pending&&pending.end===run.start&&pending.id===run.id)pending.end=run.end;
    else{if(pending)append(pending);pending={...run};}
  }
  if(pending)append(pending);rows[y*2+1]=runs-rows[y*2];
}
flush();parts.push(part('rows',0,rows));
if(changedCells!==954||owned!==original.accounting.owned_cells+954)throw Error('Global added-cell count differs');
// Deliberately not a selectable manifest: a new release must be prepared first.
const pending={...original,parts,runWords:runs*2,footprints_sha256:migration.after_footprints_sha256,geographic_release:null,
  provenance:{...original.provenance,evaluation_commit:head,original_source_point_sets_unchanged:false,
    source_migration:{commit:head,path:migrationPath,sha256:inputs.find(f=>f.path===migrationPath).sha256},
    native_baseline_manifest:{commit:originalCommit,path:originalPrefix+'manifest.json',sha256:digest(originalRaw)}},
  accounting:{...original.accounting,owned_cells:owned},installation_ready:false,release_pending:true};
write('pending-manifest.json',Buffer.from(JSON.stringify(pending)+'\n'));
write('patch-report.json',Buffer.from(JSON.stringify({version:1,evaluation_commit:head,executed_sources:executed,inputs,
  checked_rows:grid.size,checked_baseline_runs:grid.runs.length/2,checked_cells:grid.size**2,unchecked_cells:0,
  output_runs:runs,changed_rows:changedRows,changed_cells:changedCells,lost_cells:0,new_overlaps:0,
  before_owned_cells:original.accounting.owned_cells,after_owned_cells:owned,per_owner_cells:[...counts],
  release_pending:true,installed:false,published:false,
  limits:['Exact additive patch to independently verified baseline grid; new cells recomputed from joint source proof.',
    'Final decoded readback and two-run equality remain separate checks.','No new source/geography/publication approval.']})+'\n'));
console.log(JSON.stringify({output:options['--out'],changed_cells:changedCells,changed_rows:changedRows,runs,owned_cells:owned,release_pending:true}));
