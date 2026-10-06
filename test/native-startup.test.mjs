import test, {after} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {shuffleOwnershipBytes} from '../src/ownership-codec.js';
import {pickOwnership} from '../src/pixel-ownership.js';
import {packageStartupOwnership} from '../scripts/package-startup-ownership.mjs';
import {loadOwnershipAssets} from '../src/ownership-assets.js';
import {ownershipMetadata,NATIVE_METHOD,LATITUDE_DIGEST} from '../src/ownership-method.js';

const scratch=fileURLToPath(new URL('../.cache/native-startup-controls/',import.meta.url));
await fs.mkdir(scratch,{recursive:true});
const root=await fs.mkdtemp(path.join(scratch,'run-'));
after(async()=>{await fs.rm(root,{recursive:true});});
const digest=bytes=>createHash('sha256').update(bytes).digest('hex');
const reference={id:'geography:synthetic-fixture',footprints_sha256:'3'.repeat(64),hierarchy_sha256:'4'.repeat(64)};
const nativePins={geographic_release:reference.id,footprints_sha256:reference.footprints_sha256,hierarchy_sha256:reference.hierarchy_sha256};
const latitude={root:'repository',role:'immutable-normative-rule-input',
  path:'coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz',
  commit:'1'.repeat(40),bytes:1851757,sha256:'2'.repeat(64),decoded_bytes:262166*8,decoded_sha256:LATITUDE_DIGEST};
// Synthetic contract-only data; this does not certify real native membership.
async function fixture(name,native,large=false){
  const source=path.join(root,name,'source'),destination=path.join(root,name,'destination');
  const prefix=native?'native-v1/ownership':'ownership',size=262166;
  const rows=new Uint32Array(size*2),runs=large?new Uint32Array(size*8*2):Uint32Array.from([12,2**19+19]);
  if(large)for(let y=0;y<size;y++){
    rows[y*2]=y*8;rows[y*2+1]=8;
    for(let x=0;x<8;x++){
      runs[(y*8+x)*2]=(x%2)*2**19+x;
      runs[(y*8+x)*2+1]=2**19+x;
    }
  }else{rows[1]=1;for(let y=1;y<size;y++)rows[y*2]=1;}
  const parts=[];
  for(const [kind,whole]of [['rows',rows],['runs',runs]])for(let offset=0;offset<whole.length;offset+=1048576){
    const words=whole.subarray(offset,Math.min(offset+1048576,whole.length));
    const raw=Buffer.alloc(words.length*4);words.forEach((v,i)=>raw.writeUInt32LE(v,i*4));
    const bytes=gzipSync(shuffleOwnershipBytes(words),{level:9}),relative=prefix+'/'+kind+'-'+offset+'.bin.gz';
    await fs.mkdir(path.dirname(path.join(source,relative)),{recursive:true});await fs.writeFile(path.join(source,relative),bytes,{flag:'wx'});
    parts.push({kind,path:relative,offset,words:words.length,encoding:'byte-shuffle',sha256:digest(bytes),decoded_sha256:digest(raw)});
  }
  const manifest={version:2,coordinateBits:19,size,runWords:runs.length,parts,
    ...(native?{method:NATIVE_METHOD,native_latitudes:latitude,...nativePins}:{})};
  return {source,destination,manifest,rows,runs};
}
test('startup transport retains native rule and exact GPU words; legacy assets keep their original namespace',async()=>{
  for(const native of [false,true]){
    const f=await fixture(native?'native-fixture':'legacy-fixture',native);
    const originalFiles=await Promise.all(f.manifest.parts.map(async p=>digest(await fs.readFile(path.join(f.source,p.path)))));
    const packaged=await packageStartupOwnership(f);
    assert.deepEqual(ownershipMetadata(packaged.pixelMap),ownershipMetadata(f.manifest));
    const row=f.manifest.parts.find(p=>p.kind==='rows');
    await fs.mkdir(path.dirname(path.join(f.destination,row.path)),{recursive:true});
    await fs.copyFile(path.join(f.source,row.path),path.join(f.destination,row.path));
    const decoded=await loadOwnershipAssets(packaged.pixelMap,async url=>new Response(await fs.readFile(path.join(f.destination,url.slice(2)))),{requireNative:native,expectedReference:native?reference:undefined});
    assert.deepEqual(decoded.rows,f.rows);assert.deepEqual(decoded.runs,f.runs);
    assert.equal(pickOwnership(decoded,12,0),8192);assert.equal(pickOwnership(decoded,19,0),8192);
    assert.equal(pickOwnership(decoded,20,0),0);assert.equal(pickOwnership(decoded,12,1),0);
    assert.equal(decoded.method,native?NATIVE_METHOD:undefined);
    assert.equal(packaged.pixelMap.parts.find(p=>p.kind==='runs').path,(native?'native-v1/ownership':'ownership')+'/startup-runs-0.bin.gz');
    assert.deepEqual(await Promise.all(f.manifest.parts.map(async p=>digest(await fs.readFile(path.join(f.source,p.path))))),originalFiles);
  }
});
test('current native requirement rejects legacy and unknown or corrupted rules before fetching any ownership data',async()=>{
  const base={version:2,coordinateBits:19,size:262166,runWords:0,parts:[]};
  for(const manifest of [base,{...base,method:'unknown'},
    {...base,method:NATIVE_METHOD,native_latitudes:{...latitude,decoded_sha256:'0'.repeat(64)}},
    {...base,method:NATIVE_METHOD,native_latitudes:{...latitude,path:'../different-table'}},
    {...base,method:NATIVE_METHOD,native_latitudes:{...latitude,commit:'main'}},
    {...base,method:NATIVE_METHOD,native_latitudes:latitude,size:262144}]){
    let fetched=false;
    await assert.rejects(loadOwnershipAssets(manifest,async()=>{fetched=true;throw Error('unexpected fetch');},{requireNative:true,expectedReference:reference}));
    assert.equal(fetched,false);
  }
});
test('native packaging rejects a legacy path namespace before creating any destination',async()=>{
  const f=await fixture('wrong-path-fixture',false);
  f.manifest.method=NATIVE_METHOD;f.manifest.native_latitudes=latitude;Object.assign(f.manifest,nativePins);
  await assert.rejects(packageStartupOwnership(f),/Invalid canonical ownership input/);
  await assert.rejects(fs.access(f.destination));
});

test('startup transport merges original partitions across its four-million-word chunk boundary without changing any run',async()=>{
  const f=await fixture('native-large-fixture',true,true);
  assert.equal(f.manifest.parts.filter(p=>p.kind==='runs').length,5);
  const packaged=await packageStartupOwnership(f);
  const runParts=packaged.pixelMap.parts.filter(p=>p.kind==='runs');
  assert.equal(runParts.length,2);assert.equal(runParts[0].words,4194304);assert.equal(runParts[1].offset,4194304);
  assert.equal(runParts[1].words,f.runs.length-4194304);
  const row=f.manifest.parts.find(p=>p.kind==='rows');
  await fs.copyFile(path.join(f.source,row.path),path.join(f.destination,row.path));
  const decoded=await loadOwnershipAssets(packaged.pixelMap,async url=>new Response(await fs.readFile(path.join(f.destination,url.slice(2)))),{requireNative:true,expectedReference:reference});
  assert.deepEqual(decoded.rows,f.rows);assert.deepEqual(decoded.runs,f.runs);
  for(const y of [0,262143,262144,262165])for(let x=0;x<8;x++)
    assert.equal(pickOwnership(decoded,x,y),8192+x%2);
  assert.equal(packaged.runs_word_stream_sha256,digest(Buffer.from(f.runs.buffer)));
});

test('native transport source pins must agree with the selected reference release before any fetch',async()=>{
  const manifest={version:2,coordinateBits:19,size:262166,runWords:0,parts:[],method:NATIVE_METHOD,
    native_latitudes:latitude,...nativePins};
  assert.equal(ownershipMetadata(manifest,{requireNative:true,expectedReference:reference}).geographic_release,reference.id);
  assert.throws(()=>ownershipMetadata(manifest,{requireNative:true}),/independently selected reference/);
  assert.throws(()=>ownershipMetadata({version:2,size:262166,coordinateBits:19,runWords:0},
    {expectedReference:reference}),/cannot use legacy/);
  for(const key of ['id','footprints_sha256','hierarchy_sha256']){
    const mismatch={...reference,[key]:key==='id'?'geography:different':'0'.repeat(64)};let fetched=false;
    await assert.rejects(loadOwnershipAssets(manifest,async()=>{fetched=true;throw Error('unexpected fetch');},
      {requireNative:true,expectedReference:mismatch}),/selected reference release/);
    assert.equal(fetched,false);
  }
  for(const key of Object.keys(nativePins)){
    const missing={...manifest};delete missing[key];
    assert.throws(()=>ownershipMetadata(missing),/source\/release pins/);
  }
});
