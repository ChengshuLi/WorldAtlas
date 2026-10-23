import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {packagePreparedStartupOwnership,readPreparedFinalOwnership} from '../scripts/package-startup-ownership.mjs';
const hash=raw=>createHash('sha256').update(raw).digest('hex');
const nativePath='coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/native-v9/manifest.json';

async function fixture(t){
  const directory=await fs.mkdtemp(path.join(os.tmpdir(),'atlas-prepared-startup-'));
  t.after(()=>fs.rm(directory,{recursive:true,force:true}));
  const source=path.join(directory,'source'),destination=path.join(directory,'out');
  await fs.mkdir(source);const native=JSON.parse(await fs.readFile(nativePath));
  const manifestSha='a'.repeat(64),row=native.parts.find(part=>part.kind==='rows');
  const payloads=new Map([[row.path,Buffer.from('row')],['ownership-vintages/'+manifestSha+'/native-v1/ownership/startup-runs-0.bin.gz',Buffer.from('runs')],['native-v1/native-row-latitudes.f64le.gz',Buffer.from('latitudes')],['native-v1/ownership/startup-runs-0.bin.gz',Buffer.from('previous public URL')]]);
  const manifest={...native,parts:[{...row,sha256:hash(payloads.get(row.path))}],native_latitudes:{...native.native_latitudes,sha256:hash(payloads.get('native-v1/native-row-latitudes.f64le.gz'))}};
  const parts=[{...manifest.parts[0]},{kind:'runs',path:[...payloads.keys()][1],offset:0,words:manifest.runWords,encoding:'byte-shuffle',sha256:hash(Buffer.from('runs')),decoded_sha256:'b'.repeat(64)}];
  const pixelMap=Object.fromEntries(['version','coordinateBits','size','runWords','method','footprints_sha256','hierarchy_sha256','geographic_release'].map(key=>[key,manifest[key]]));
  pixelMap.parts=parts;pixelMap.native_latitudes={...manifest.native_latitudes,transport_path:'native-v1/native-row-latitudes.f64le.gz'};
  const files=[];for(const [relative,raw]of payloads){await fs.mkdir(path.dirname(path.join(source,relative)),{recursive:true});await fs.writeFile(path.join(source,relative),raw);files.push({path:relative,bytes:raw.length,sha256:hash(raw)});}
  const index={version:1,native_manifest_sha256:manifestSha,release_id:manifest.geographic_release,footprints_sha256:manifest.footprints_sha256,hierarchy_sha256:manifest.hierarchy_sha256,pixelMap,files};
  const write=()=>fs.writeFile(path.join(source,'index.json'),JSON.stringify(index));await write();
  return{source,destination,manifest,manifestSha,payloads,index,write};
}

test('prepared startup copies every exact current and retained public asset',async t=>{
 const f=await fixture(t),result=await packagePreparedStartupOwnership(f);
 assert.deepEqual(result.pixelMap,f.index.pixelMap);
 for(const [name,bytes]of f.payloads)assert.deepEqual(await fs.readFile(path.join(f.destination,name)),bytes);
 await assert.rejects(packagePreparedStartupOwnership(f),/EEXIST/);
});

test('prepared startup ignores row object key order but preserves every field identity',async t=>{
 const f=await fixture(t),original=f.index.pixelMap.parts[0];
 const reordered=Object.fromEntries(Object.entries(original).sort(([a],[b])=>a.localeCompare(b)));
 assert.notEqual(JSON.stringify(reordered),JSON.stringify(original));
 assert.deepEqual(reordered,original);
 f.index.pixelMap.parts[0]=reordered;await f.write();
 const result=await packagePreparedStartupOwnership(f);
 assert.deepEqual(result.pixelMap.parts[0],original);
 for(const [name,bytes]of f.payloads)assert.deepEqual(await fs.readFile(path.join(f.destination,name)),bytes);
 const changes=Object.entries(reordered).map(([key,value])=>[key,{...reordered,[key]:typeof value==='number'?value+1:'changed-'+value}]);
 changes.push(['extra',{...reordered,unexpected:true}]);
 const missing={...reordered};delete missing.decoded_sha256;changes.push(['missing',missing]);
 for(const [label,part]of changes){
  f.index.pixelMap.parts[0]=part;await f.write();const destination=f.destination+'-'+label;
  await assert.rejects(packagePreparedStartupOwnership({...f,destination}),/row identity differs/);
  await assert.rejects(fs.stat(destination),{code:'ENOENT'});
 }
});

test('prepared startup rejects stale selection, missing rosters and changed bytes before publication',async t=>{
 const f=await fixture(t);
 await assert.rejects(packagePreparedStartupOwnership({...f,manifestSha:'c'.repeat(64)}),/selected native reference/);
 f.index.files.pop();await f.write();await assert.rejects(packagePreparedStartupOwnership(f),/roster omits/);
 f.index.files.push({path:'native-v1/ownership/startup-runs-0.bin.gz',bytes:19,sha256:hash(Buffer.from('previous public URL'))});await f.write();
 await fs.writeFile(path.join(f.source,f.index.files[0].path),'truncated gzip');
 await assert.rejects(packagePreparedStartupOwnership(f),/bytes changed/);
 await assert.rejects(fs.stat(f.destination),{code:'ENOENT'});
});

test('prepared startup refuses unsafe paths and source or destination links without overwriting sentinels',async t=>{
 const f=await fixture(t),outside=path.join(path.dirname(f.source),'sentinel');await fs.writeFile(outside,'retained');
 const current=f.index.files[0];f.index.files[0]={...current,path:'../sentinel'};await f.write();
 await assert.rejects(packagePreparedStartupOwnership(f),/roster omits|Unsafe/);
 f.index.files[0]=current;await f.write();await fs.unlink(path.join(f.source,current.path));await fs.symlink(outside,path.join(f.source,current.path));
 await assert.rejects(packagePreparedStartupOwnership(f),/nonordinary/);
 assert.equal(await fs.readFile(outside,'utf8'),'retained');
});

// New reviewed banks may change row offsets. Their original source pins stay
// exact while the deployment address moves to that selected manifest vintage.
test('prepared startup accepts exact versioned rows without rebinding predecessor URLs',async t=>{
 const f=await fixture(t),part=f.index.pixelMap.parts.find(pin=>pin.kind==='rows');
 const original=part.path,versioned='ownership-vintages/'+f.manifestSha+'/'+original;
 const bytes=f.payloads.get(original);
 await fs.mkdir(path.dirname(path.join(f.source,versioned)),{recursive:true});
 await fs.writeFile(path.join(f.source,versioned),bytes);
 f.index.files.push({path:versioned,bytes:bytes.length,sha256:hash(bytes)});
 part.path=versioned;await f.write();
 const result=await packagePreparedStartupOwnership(f);
 assert.equal(result.pixelMap.parts.find(pin=>pin.kind==='rows').path,versioned);
 assert.deepEqual(await fs.readFile(path.join(f.destination,original)),bytes);
 assert.deepEqual(await fs.readFile(path.join(f.destination,versioned)),bytes);
 part.path='ownership-vintages/'+'c'.repeat(64)+'/'+original;await f.write();
 await assert.rejects(packagePreparedStartupOwnership({...f,destination:f.destination+'-foreign'}),/row identity differs/);
 part.path=versioned;part.bytes++;await f.write();
 await assert.rejects(packagePreparedStartupOwnership({...f,destination:f.destination+'-changed'}),/row identity differs/);
});

test('prepared startup binds complete selected latitude and optional canonical identity before writing',async t=>{
 const f=await fixture(t),latitude={...f.index.pixelMap.native_latitudes};
 for(const [key,value]of [['bytes',0],['decoded_bytes',0],['decoded_sha256','0'.repeat(64)],['transport_path','foreign-latitude.gz'],['commit','0'.repeat(40)]]){
  f.index.pixelMap.native_latitudes={...latitude,[key]:value};await f.write();
  await assert.rejects(packagePreparedStartupOwnership(f),/native latitude differs/);
  await assert.rejects(fs.stat(f.destination),{code:'ENOENT'});
 }
 f.index.pixelMap.native_latitudes=latitude;
 f.index.pixelMap.canonical_grid_sha256='c'.repeat(64);await f.write();
 await assert.rejects(packagePreparedStartupOwnership(f),/canonical grid identity differs/);
 await assert.rejects(fs.stat(f.destination),{code:'ENOENT'});
 f.index.pixelMap.canonical_grid_sha256=f.manifestSha;await f.write();
 await packagePreparedStartupOwnership(f);
});

test('finished-bank profile uses the existing copier and complete decoder without historical repair reads',async t=>{
 const f=await fixture(t),{prepareFinalBankStartupOwnership}=await import('../scripts/prepare-startup-ownership.mjs');
 const {finalBankReference}=await import('../src/effective-footprint.js');
 const base={id:f.manifest.geographic_release,footprints_sha256:f.manifest.footprints_sha256,hierarchy_sha256:f.manifest.hierarchy_sha256};
 const ownerHash=hash(Buffer.from(JSON.stringify([[1,'A']]))),features=[{id:'A',pixelIndex:1,geometry:null,properties:{id:'A',parent_id:'P'},gridBounds:[0,0,1,1]}];
 const native={...f.index.pixelMap,canonical_grid_sha256:f.manifestSha};
 const previous={...f.index,version:2,compatibility_files:f.index.files,preparedOwnership:{native_pixel_map:native,owners:1,reference_owner_sha256:ownerHash}};
 const rows=new Uint32Array(262166*2);rows[1]=1;for(let y=1;y<262166;y++)rows[y*2]=1;
 const ownership={...native,rows,runs:Uint32Array.of(2**19+12,19),runWords:2,reference_owner_sha256:ownerHash};
 const stage=path.join(path.dirname(f.source),'finished');
 const index=await prepareFinalBankStartupOwnership({manifest:f.manifest,manifestSha:f.manifestSha,previous,ownership,features,baseReference:base,destination:stage});
 const generated=[];
 async function collect(relative=''){
  for(const entry of await fs.readdir(path.join(stage,relative),{withFileTypes:true})){
   const name=relative?relative+'/'+entry.name:entry.name;
   if(entry.isDirectory())await collect(name);else {const raw=await fs.readFile(path.join(stage,name));generated.push({path:name,bytes:raw.length,sha256:hash(raw)});await fs.mkdir(path.dirname(path.join(f.source,name)),{recursive:true});await fs.writeFile(path.join(f.source,name),raw);}
  }
 }
 await collect();index.files=[...previous.files,...generated].sort((a,b)=>a.path.localeCompare(b.path));
 const indexRaw=Buffer.from(JSON.stringify(index));await fs.writeFile(path.join(f.source,'index.json'),indexRaw);
 const selected={finalBank:{path:'data/canonical-grid/current-startup/index.json',bytes:indexRaw.length,sha256:hash(indexRaw)},base,reference_release:index.preparedOwnership.effective_reference};
 const copied=await packagePreparedStartupOwnership({...f,selected,features});assert.deepEqual(copied.pixelMap,index.pixelMap);assert.equal(copied.preparedOwnership.version,3);assert(!Object.hasOwn(index,'additiveRelease'));
 for(const [name,raw]of f.payloads)assert.deepEqual(await fs.readFile(path.join(f.destination,name)),raw);
 const requests=[],read=async pin=>{requests.push(pin.path);return fs.readFile(path.join(f.source,pin.path));};
 const decoded=await readPreparedFinalOwnership({indexRaw,manifest:f.manifest,manifestSha:f.manifestSha,selected,features,read});
 assert.deepEqual(decoded.ownership.rows,rows);assert.deepEqual(decoded.ownership.runs,ownership.runs);assert.deepEqual(decoded.features,features);
 assert.deepEqual([...new Set(requests)].sort(),[...index.pixelMap.parts,...index.preparedOwnership.context_parts].map(p=>p.path).sort());
 assert(!requests.some(p=>/ledger|patch|sidecar/.test(p)));
 // Recompute a coherent E/selector around a false whole-stream declaration.
 // Hashing declarations is not proof that they describe the consumed arrays.
 const forged=structuredClone(index);forged.preparedOwnership.rows_sha256='c'.repeat(64);
 const e=finalBankReference(forged.preparedOwnership,forged.pixelMap,forged.footprints_sha256);
 forged.preparedOwnership.effective_reference=e;forged.release_id=e.id;forged.pixelMap.geographic_release=e.id;
 const badRaw=Buffer.from(JSON.stringify(forged)),badSelected={...selected,finalBank:{...selected.finalBank,bytes:badRaw.length,sha256:hash(badRaw)},reference_release:e};
 await assert.rejects(readPreparedFinalOwnership({indexRaw:badRaw,manifest:f.manifest,manifestSha:f.manifestSha,selected:badSelected,features,read}),/complete word stream differs/);
 const changed=structuredClone(features);changed[0].properties.parent_id='foreign';
 await assert.rejects(readPreparedFinalOwnership({indexRaw,manifest:f.manifest,manifestSha:f.manifestSha,selected,features:changed,read}),/owner, parent or bounds differ/);
 await assert.rejects(readPreparedFinalOwnership({indexRaw,manifest:f.manifest,manifestSha:f.manifestSha,selected:{...selected,finalBank:{...selected.finalBank,sha256:'f'.repeat(64)}},features,read}),/one-way selected index pin/);
 const badRead=async pin=>{const raw=await read(pin);return pin.path===index.pixelMap.parts[0].path?Buffer.concat([raw,Buffer.from('changed')]):raw;};
 await assert.rejects(readPreparedFinalOwnership({indexRaw,manifest:f.manifest,manifestSha:f.manifestSha,selected,features,read:badRead}),/whole identity differs/);
});
