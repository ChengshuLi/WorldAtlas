// Audit selected native transport by runs, without compiling projected ownership.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {unshuffleOwnershipBytes} from '../../../src/ownership-codec.js';
import {candidateBudget,requirePlainExecution,committedPreparationFiles} from '../../../scripts/native-ownership/native-preparation-guards.mjs';

requirePlainExecution();
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const prefix='coordination/engineering/iran-pakistan-offline-integration-991-20261006-local22';
const options={};
for(let i=2;i<process.argv.length;i+=2){
  if(!['--out','--python','--manifest','--parts-root','--before-context','--after-context'].includes(process.argv[i])||!process.argv[i+1]||options[process.argv[i]])throw Error('Explicit fresh output and optional pinned input paths required');
  options[process.argv[i]]=process.argv[i+1];
}
const out=path.resolve(root,options['--out']??'');
if(!out.startsWith(path.join(root,prefix)+path.sep)||fs.existsSync(out))throw Error('Fresh owned output required');
const head=execFileSync('git',['-C',root,'rev-parse','HEAD'],{encoding:'utf8'}).trim();
const sha=raw=>createHash('sha256').update(raw).digest('hex'),MAX=32*1024*1024,BUDGET=256*1024*1024;
const inputs=new Map();let produced=0;
const admission=candidateBudget([]);
function budget(){const used=[...inputs.values()].reduce((n,p)=>n+p.bytes,0)+produced;if(used>BUDGET)throw Error('Encoded input/output budget exceeded');return used;}
function safe(name){if(path.posix.isAbsolute(name)||name.split('/').some(p=>!p||p==='.'||p==='..'))throw Error('Unsafe ordinary input path');}
function read(name,pin,commit=head){
  safe(name);if(!/^[a-f0-9]{40}$/.test(commit))throw Error('Immutable commit required');
  const spec=commit+':'+name;
  const tree=execFileSync('git',['-C',root,'ls-tree','-z',commit,'--',name],{encoding:'utf8'});
  if(!/^100644 blob /.test(tree)||tree.slice(tree.indexOf('\t')+1)!==name+'\0')throw Error('Ordinary committed blob required: '+name);
  const size=Number(execFileSync('git',['-C',root,'cat-file','-s',spec],{encoding:'utf8'}));
  if(size>MAX)throw Error('Encoded file exceeds 32MiB');
  const raw=execFileSync('git',['-C',root,'show',spec],{maxBuffer:MAX}),digest=sha(raw);
  if(raw.length!==size||pin&&(digest!==pin.sha256||pin.bytes!=null&&size!==pin.bytes))throw Error('Pinned encoded input differs: '+name);
  const value={commit,path:name,bytes:size,sha256:digest};
  if(inputs.has(spec)&&JSON.stringify(inputs.get(spec))!==JSON.stringify(value))throw Error('Conflicting input pin');
  if(!inputs.has(spec))admission.add(value);inputs.set(spec,value);budget();return raw;
}
const sources=[prefix+'/audit-native-pixels.mjs',prefix+'/audit-native-pixel-sources.py','src/ownership-codec.js','scripts/native-ownership/native-preparation-guards.mjs','scripts/ellipsoidal_area.py','requirements.txt','package.json','package-lock.json'];
const producer=committedPreparationFiles(root,head,sources);
for(const pin of producer)read(pin.path,pin);
const manifestPath=options['--manifest']??prefix+'/native-selected-v1/manifest.json';
const manifestRaw=read(manifestPath),manifest=JSON.parse(manifestRaw);
if(manifest.version!==2||manifest.method!=='native-linear-evenodd-first-owner-v1'||manifest.size!==262166||manifest.coordinateBits!==19||manifest.accounting.owners!==49625)throw Error('Unsupported selected native manifest');
const beforePath=options['--before-context']??'coordination/engineering/native-grid-integration-1010-20261005-local17/context-inputs-v1/inputs.json';
const afterPath=options['--after-context']??prefix+'/repaired-context-v2/inputs.json';
const oldPixelPath='data/pixel-audit.json',oldPixel=JSON.parse(read(oldPixelPath));
const sourceRaw=execFileSync(options['--python']??'python3',['-I','-B',path.join(root,prefix,'audit-native-pixel-sources.py')],{
  input:JSON.stringify({root,commit:head,helper:prefix+'/audit-native-pixel-sources.py',before:beforePath,after:afterPath,old_pixel:oldPixelPath,
    targets:['gb:IRN:ADM2:26516999B17111396986996','gb:PAK:ADM2:60131773B78019453337506']}),maxBuffer:MAX});
const source=JSON.parse(sourceRaw);
for(const pin of source.inputs){const key=pin.commit+':'+pin.path;if(inputs.has(key)&&JSON.stringify(inputs.get(key))!==JSON.stringify(pin))throw Error('Helper input pin differs');if(!inputs.has(key))admission.add(pin);inputs.set(key,pin);}budget();
if(source.after_footprints_sha256!==manifest.footprints_sha256||source.rows.length!==49625||source.unchanged_geometry_count!==49623||source.before_footprints_sha256!==oldPixel.footprints_sha256||oldPixel.hierarchy_sha256!==manifest.hierarchy_sha256)throw Error('Source audit binding differs');
const roster=source.rows.map(([id,index])=>[index,id]);
if(sha(JSON.stringify(roster))!==source.owner_sha256)throw Error('Stable roster digest differs');
const boundsPin=manifest.original_assets.bounds;
const bounds=JSON.parse(gunzipSync(read(boundsPin.path,boundsPin,boundsPin.commit),{maxOutputLength:MAX}));
if(bounds.length!==source.rows.length||bounds.some((b,i)=>b.id!==source.rows[i][0]||b.index!==source.rows[i][1]||b.province_id!==source.rows[i][3]))throw Error('Original bounds identity/parent differs');
const latitudePin=manifest.native_latitudes,latitudeRaw=gunzipSync(read(latitudePin.path,latitudePin,latitudePin.commit),{maxOutputLength:MAX});
if(latitudeRaw.length!==latitudePin.decoded_bytes||latitudeRaw.length!==manifest.size*8||sha(latitudeRaw)!==latitudePin.decoded_sha256)throw Error('Normative latitude bytes differ');
let previousLatitude=Infinity;
for(let y=0;y<manifest.size;y++){const latitude=latitudeRaw.readDoubleLE(y*8);if(!Number.isFinite(latitude)||latitude>=previousLatitude||Math.abs(latitude)>90)throw Error('Invalid normative latitude sequence');previousLatitude=latitude;}
const partsRoot=options['--parts-root']??prefix+'/native-selected-v1';safe(partsRoot);
function decode(part){
  if(!['rows','runs'].includes(part.kind)||part.encoding!=='byte-shuffle'||!Number.isInteger(part.words)||part.words<1||part.words>1048576||part.words%2||!Number.isSafeInteger(part.offset)||part.offset<0||part.offset%2)throw Error('Invalid bounded native part');
  const encoded=read(partsRoot+'/'+part.path,part),decoded=gunzipSync(encoded,{maxOutputLength:MAX});
  if(decoded.length!==part.words*4)throw Error('Shuffled word count differs');
  const words=unshuffleOwnershipBytes(decoded,part.words),raw=Buffer.from(words.buffer,words.byteOffset,words.byteLength);
  if(raw.length!==part.decoded_bytes||sha(raw)!==part.decoded_sha256)throw Error('Decoded native part hash differs');return words;
}
const rows=new Uint32Array(manifest.size*2);let rowWords=0;
const paths=new Set();for(const part of manifest.parts){safe(part.path);if(paths.has(part.path))throw Error('Duplicate selected part path');paths.add(part.path);}
for(const part of manifest.parts.filter(p=>p.kind==='rows').sort((a,b)=>a.offset-b.offset)){
  if(part.offset!==rowWords||rowWords+part.words>rows.length)throw Error('Row parts inventory differs');rows.set(decode(part),rowWords);rowWords+=part.words;
}
if(rowWords!==rows.length||manifest.parts.some(p=>!['rows','runs'].includes(p.kind)))throw Error('Incomplete selected native inventory');
let expectedRun=0;for(let y=0;y<manifest.size;y++){if(rows[y*2]!==expectedRun)throw Error('Invalid complete row offset');expectedRun+=rows[y*2+1];if(expectedRun*2>manifest.runWords)throw Error('Row run domain exceeded');}
if(expectedRun*2!==manifest.runWords)throw Error('Unreferenced native runs');
const counts=new Float64Array(49626),areas=new Float64Array(49626),rowAreas=new Float64Array(manifest.size);
const A=6378137,F=1/298.257223563,E2=F*(2-F),E=Math.sqrt(E2),C=A*A*(1-E2)/2;
const strip=u=>C*(u/(1-E2*u*u)+Math.atanh(E*u)/E);
for(let y=0;y<manifest.size;y++){
  const north=Math.atan(Math.sinh(Math.PI*(1-2*y/manifest.size))),south=Math.atan(Math.sinh(Math.PI*(1-2*(y+1)/manifest.size)));
  rowAreas[y]=(strip(Math.sin(north))-strip(Math.sin(south)))*2*Math.PI/manifest.size;
  if(!(rowAreas[y]>0))throw Error('Invalid ellipsoid cell area');
}
const factor=2**manifest.coordinateBits,mask=factor-1,base=2**(32-manifest.coordinateBits);
let wordOffset=0,y=0,previousEnd=0,previousOwner=0,owned=0,checkedRuns=0;
for(const part of manifest.parts.filter(p=>p.kind==='runs').sort((a,b)=>a.offset-b.offset)){
  if(part.offset!==wordOffset||wordOffset+part.words>manifest.runWords)throw Error('Run part inventory differs');
  const words=decode(part);
  for(let k=0;k<words.length;k+=2){
    const run=(wordOffset+k)/2;
    while(y<manifest.size&&run>=rows[y*2]+rows[y*2+1]){y++;previousEnd=0;previousOwner=0;}
    if(y>=manifest.size||run<rows[y*2])throw Error('Run outside exact row domain');
    const a=words[k],b=words[k+1],start=a&mask,end=(b&mask)+1,id=(a>>>manifest.coordinateBits)+(b>>>manifest.coordinateBits)*base;
    if(start<previousEnd||end<=start||end>manifest.size||id<1||id>49625||start===previousEnd&&previousOwner===id)throw Error('Overlapping, invalid, or noncanonical native run');
    const cells=end-start;counts[id]+=cells;areas[id]+=cells*rowAreas[y];owned+=cells;checkedRuns++;previousEnd=end;previousOwner=id;
  }
  wordOffset+=part.words;
  console.log(JSON.stringify({phase:'native-run-audit',words:wordOffset,total_words:manifest.runWords}));
}
if(wordOffset!==manifest.runWords||checkedRuns!==expectedRun||owned!==manifest.accounting.owned_cells||manifest.accounting.checked_rows!==manifest.size||manifest.accounting.checked_cells!==manifest.size**2||manifest.accounting.unchecked_cells!==0)throw Error('Full native accounting differs');
const oldById=new Map(oldPixel.records.map(r=>[r.id,r]));
const records=source.rows.map(([id,index,sourceArea])=>{
  const prior=oldById.get(id),cells=counts[index],gridArea=areas[index];if(!prior||!(sourceArea>0)||!Number.isFinite(gridArea))throw Error('Missing source-area/identity proof');
  if(!Number.isFinite(sourceArea))throw Error('Nonfinite source area');
  return {id,name:prior.name,owner:prior.owner,cells,status:cells?'represented':'missing',reason:cells?null:'No selected native cell center falls inside this source territory',source_wgs84_area_m2:sourceArea,grid_wgs84_area_m2:gridArea,source_area_cells:null,relative_area_error:gridArea/sourceArea-1};
});
const report={version:2,footprints_sha256:manifest.footprints_sha256,hierarchy_sha256:manifest.hierarchy_sha256,
  reference_release:manifest.geographic_release,native_manifest:{commit:head,path:manifestPath,sha256:sha(manifestRaw)},method:manifest.method,
  native_latitudes:latitudePin,grid_zoom:Math.log2(manifest.size/256),grid_size:manifest.size,locations:records.length,
  represented:records.filter(r=>r.cells>0).length,missing:records.filter(r=>!r.cells),high_distortion:records.filter(r=>Math.abs(r.relative_area_error)>.25),
  covered_cells:owned,water_or_uncovered_cells:manifest.size**2-owned,
  background_policy:'Zero ID denotes water or unsupported source coverage; this audit does not classify either.',
  area_method:'WGS84 occupied Web Mercator cell surface areas summed from fully decoded selected native runs; source areas retained only after exact compact geometry equality, with changed polygons reintegrated.',
  records,scientific_approval:false,installation_ready:false,published:false};
const raw=Buffer.from(JSON.stringify(report)+'\n');if(raw.length>MAX)throw Error('Pixel audit output exceeds 32MiB');produced+=raw.length;
admission.add({bytes:raw.length});
function runtimeHash(filename){const hash=createHash('sha256'),fd=fs.openSync(filename,'r'),buffer=Buffer.alloc(1048576);try{let count;while((count=fs.readSync(fd,buffer,0,buffer.length,null)))hash.update(buffer.subarray(0,count));}finally{fs.closeSync(fd);}return {path:fs.realpathSync(filename),sha256:hash.digest('hex')};}
const evidence={version:1,execution_commit:head,producer,inputs:[...inputs.values()],
  source_comparison:{changed_ids:source.changed_ids,unchanged_geometry_count:source.unchanged_geometry_count,owner_sha256:source.owner_sha256,area_policy:source.area_policy},
  runtime:{node:process.version,node_executable:runtimeHash(process.execPath),python:source.runtime},normative_latitudes_preserved:true,
  checked_rows:manifest.size,checked_cells:manifest.size**2,checked_runs:checkedRuns,unchecked_cells:0,
  audit:{path:'pixel-audit.json',bytes:raw.length,sha256:sha(raw)},budget:{...admission.snapshot(),encoded_input_output_bytes:budget(),maximum_file_bytes:MAX},
  limits:['Native transport accounting and ellipsoid surface integration do not establish geographic/source authority or historical membership.','Zero cells remain unclassified.','Exact compact geometry comparison permits retention of unchanged source areas; all native occupied areas and owner counts are freshly recomputed.']};
let receipt=Buffer.from(JSON.stringify(evidence)+'\n');
for(let pass=0;pass<4;pass++){evidence.budget.encoded_input_output_bytes=budget()+receipt.length;evidence.budget.accounted_bytes=admission.snapshot().accounted_bytes+receipt.length;evidence.budget.accounted_descriptors=admission.snapshot().accounted_descriptors+1;const next=Buffer.from(JSON.stringify(evidence)+'\n');if(next.length===receipt.length){receipt=next;break;}receipt=next;}
if(receipt.length>MAX)throw Error('Receipt exceeds 32MiB');admission.add({bytes:receipt.length});produced+=receipt.length;if(evidence.budget.encoded_input_output_bytes!==budget()||evidence.budget.accounted_bytes!==admission.snapshot().accounted_bytes)throw Error('Receipt budget did not stabilize');
fs.mkdirSync(out);fs.writeFileSync(path.join(out,'pixel-audit.json'),raw,{flag:'wx'});fs.writeFileSync(path.join(out,'verification.json'),receipt,{flag:'wx'});
if(sha(fs.readFileSync(path.join(out,'pixel-audit.json')))!==sha(raw)||sha(fs.readFileSync(path.join(out,'verification.json')))!==sha(receipt))throw Error('Output readback differs');
console.log(JSON.stringify({locations:records.length,represented:report.represented,missing:report.missing.length,high_distortion:report.high_distortion.length,owned_cells:owned,encoded_input_output_bytes:budget()}));
