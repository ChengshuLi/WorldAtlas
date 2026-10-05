import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {gzipSync} from 'node:zlib';
import {packOwnership,pickOwnership} from '../src/pixel-ownership.js';
import {shuffleOwnershipBytes} from '../src/ownership-codec.js';
import {loadCoverageClassification,validateCoverageManifest,coverageExplanation,coverageText} from '../src/coverage-classification.js';
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
function fixture(){
 const packed=packOwnership({size:8,rows:Array.from({length:8},()=>Uint32Array.from([1,3,1,4,6,2]))});
 const manifest={kind:'physical-reference-classification',classification_version:1,version:2,size:8,coordinateBits:3,runWords:packed.runs.length,release_id:'fixture-release',footprints_sha256:'a'.repeat(64),hierarchy_sha256:'b'.repeat(64),canonical_grid_sha256:'c'.repeat(64),sources:[{name:'land',url:'https://example.test/land',original_sha256:'d'.repeat(64)},{name:'water',url:'https://example.test/water',original_sha256:'e'.repeat(64)}],parts:[]},files=new Map();
 for(const kind of ['rows','runs']){
  const words=packed[kind],bytes=gzipSync(shuffleOwnershipBytes(words)),path=`coverage-classification/${kind}-0.bin.gz`;
  manifest.parts.push({kind,offset:0,words:words.length,path,encoding:'byte-shuffle',compressed_bytes:bytes.length,sha256:hash(bytes),decoded_sha256:hash(new Uint8Array(words.buffer))});files.set('./'+path,bytes);
 }
 return {manifest,expected:{...manifest},files,fetcher:async path=>new Response(files.get(path))};
}
test('physical classes preserve land, water and unknown holes without creating location IDs',async()=>{
 const f=fixture(),coverage=await loadCoverageClassification(f.manifest,f.expected,f.fetcher);
 assert.deepEqual([0,1,3,4,6].map(x=>pickOwnership(coverage.grid,x,2)),[0,1,0,2,0]);
 const point={x:1,y:2},latlng={lat:26.8032,lng:63.207727};
 assert.match(coverageText(coverageExplanation(coverage,point,latlng)),/Possible geographic coverage gap.*26.80320.*smaller waterways.*Modern reference/);
 assert.equal(coverageExplanation(coverage,{x:4,y:2},latlng).kind,2);
 assert.match(coverageText(coverageExplanation(null,point,latlng)),/water or geographic coverage is not verified/);
});
test('stale release/grid/source pins and allocation/path abuse fail before fetch',async()=>{
 for(const mutate of [m=>m.release_id='other',m=>m.footprints_sha256='f'.repeat(64),m=>m.canonical_grid_sha256='f'.repeat(64),m=>m.size=9,m=>m.runWords=16000002,m=>m.parts[0].path='../rows.gz',m=>m.parts[0].decoded_sha256=null,m=>m.sources=[]]){
  const f=fixture();mutate(f.manifest);let fetched=false;
  await assert.rejects(loadCoverageClassification(f.manifest,f.expected,async()=>{fetched=true;throw Error('fetch');}));assert.equal(fetched,false);
 }
});
test('corrupt transport and decoded classes fail; automatic host decompression is supported',async()=>{
 const bad=fixture();bad.files.get('./coverage-classification/runs-0.bin.gz')[12]^=1;
 await assert.rejects(loadCoverageClassification(bad.manifest,bad.expected,bad.fetcher),/checksum/);
 const wrong=fixture(),packed=packOwnership({size:8,rows:Array.from({length:8},()=>Uint32Array.from([1,3,3,4,6,2]))});
 const bytes=gzipSync(shuffleOwnershipBytes(packed.runs)),part=wrong.manifest.parts[1];
 Object.assign(part,{sha256:hash(bytes),decoded_sha256:hash(new Uint8Array(packed.runs.buffer)),compressed_bytes:bytes.length});wrong.files.set('./'+part.path,bytes);
 await assert.rejects(loadCoverageClassification(wrong.manifest,wrong.expected,wrong.fetcher),/Invalid coverage class/);
 const decoded=fixture();const grid=packOwnership({size:8,rows:Array.from({length:8},()=>Uint32Array.from([1,3,1,4,6,2]))});
 for(const kind of ['rows','runs'])decoded.files.set(`./coverage-classification/${kind}-0.bin.gz`,shuffleOwnershipBytes(grid[kind]));
 assert.equal(pickOwnership((await loadCoverageClassification(decoded.manifest,decoded.expected,decoded.fetcher)).grid,4,3),2);
});
test('overlapping packed runs are rejected even with valid hashes',async()=>{
 const f=fixture(),words=new Uint32Array(32);
 for(let i=0;i<8;i++)words.set([(1<<3)|1,3,(2<<3)|3,5],i*4);
 const bytes=gzipSync(shuffleOwnershipBytes(words)),part=f.manifest.parts[1];
 Object.assign(part,{sha256:hash(bytes),decoded_sha256:hash(new Uint8Array(words.buffer)),compressed_bytes:bytes.length});f.files.set('./'+part.path,bytes);
 await assert.rejects(loadCoverageClassification(f.manifest,f.expected,f.fetcher),/overlapping run/);
});

test('scientific scanlines preserve holes, priority, unknowns and reproducibility',()=>{
 const result=spawnSync(process.env.PYTHON??'python3',['test/coverage-classification.py'],{encoding:'utf8',timeout:30000});
 assert.equal(result.status,0,(result.stdout??'')+(result.stderr??''));
});
