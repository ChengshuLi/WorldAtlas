import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {compileNativeRuntime} from '../src/native-runtime.js';
import {compileNativeLocationContext,nativeDisplayContext} from '../src/native-location-context.js';
import {pickOwnership,ownershipRun} from '../src/pixel-ownership.js';
import {projectCell} from '../src/pixel-grid.js';
const size=262166,raw=gunzipSync(fs.readFileSync('coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz'));
const latitudes=Float64Array.from({length:size},(_,y)=>raw.readDoubleLE(y*8));
const ring=(a,b,c,d)=>[[a,b],[c,b],[c,d],[a,d],[a,b]];
const feature=(id,pixelIndex,coords)=>({id,pixelIndex,properties:{parent_id:'original-parent:'+id,name:id,dated_fact:'retained'},geometry:{type:'Polygon',coordinates:coords}});
const reference=[feature('A',1,[ring(0,0,1,1)]),feature('B',8192,[ring(0,0,2,2)]),feature('C',67108863,[ring(-2,-1,-1,1)])];
const digest=value=>createHash('sha256').update(JSON.stringify(value)).digest('hex');
const base=await compileNativeRuntime(reference,{size,latitudes});
base.footprints_sha256=digest(reference.map(f=>[f.id,f.geometry]).sort((a,b)=>a[0].localeCompare(b[0])));
base.reference_owner_sha256=digest(reference.map(f=>[f.pixelIndex,f.id]).sort((a,b)=>a[0]-b[0]));
const original=JSON.stringify(reference);

test('dated removal, replacement, holes and additions equal complete native compilation over every canonical row/run',async()=>{
 const changedB=feature('B',8192,[ring(0,0,2,2),ring(.25,.25,.75,.75)]);
 const added=feature('new-D',undefined,[ring(4,0,5,1)]);
 const features=[added,reference[2],changedB];
 const result=await compileNativeLocationContext({referenceFeatures:reference,features,base,latitudes,rowBlock:511});
 const expected=await compileNativeRuntime(result.context.features.map((f,i)=>({...f,pixelIndex:i+1})),{size,latitudes,rowBlock:127});
 assert.deepEqual(result.grid.rows,expected.rows);assert.deepEqual(result.grid.runs,expected.runs);
 assert.deepEqual(result.context.owners,[{index:1,id:'B',referenceIndex:8192},{index:2,id:'C',referenceIndex:67108863},{index:3,id:'new-D',referenceIndex:null}]);
 assert.ok(result.accounting.recomputedRows>0&&result.accounting.recomputedRows<size);
 assert.equal(result.accounting.recomputedRows+result.accounting.reusedRows,size);
 // Independent rectangle-interior controls: removed first owner exposes the
 // original overlapping neighbor, a true hole stays empty, new island is mapped.
 for(const [lon,lat,id]of [[.1,.1,1],[.5,.5,0],[-1.5,.5,2],[4.5,.5,3],[3,.5,0]]){
  const [x,y]=projectCell(lon,lat);assert.equal(pickOwnership(result.grid,x,y),id);
 }
 assert.equal(JSON.stringify(reference),original);
 assert.equal(features[1].pixelIndex,67108863);
});

test('dated metadata changes reuse all native reference rows with explicit dense identity mapping',async()=>{
 const features=reference.map(f=>({...f,properties:{...f.properties,name:'Dated '+f.id,parent_id:'dated-parent'}})).reverse();
 const result=await compileNativeLocationContext({referenceFeatures:reference,features,base,latitudes});
 assert.equal(result.accounting.recomputedRows,0);assert.equal(result.accounting.reusedRows,size);
 const expected=await compileNativeRuntime(result.context.features.map((f,i)=>({...f,pixelIndex:i+1})),{size,latitudes});
 assert.deepEqual(result.grid.rows,expected.rows);assert.deepEqual(result.grid.runs,expected.runs);
 assert.equal(result.context.features[1].properties.parent_id,'dated-parent');
 assert.equal(JSON.stringify(reference),original);
});

test('changed source, original owner mapping, duplicate IDs, malformed geometry and cancellation reject without partial output',async()=>{
 await assert.rejects(compileNativeLocationContext({referenceFeatures:reference,features:reference,base:{...base,footprints_sha256:'0'.repeat(64)},latitudes}),/source bytes/);
 const reordered=reference.map((f,i)=>({...f,pixelIndex:i+1}));
 await assert.rejects(compileNativeLocationContext({referenceFeatures:reordered,features:reference,base,latitudes}),/identity mapping/);
 assert.throws(()=>nativeDisplayContext(reference,[reference[0],reference[0]]),/identity/);
 await assert.rejects(compileNativeLocationContext({referenceFeatures:reference,features:[{...reference[0],geometry:null}],base,latitudes}),/native geometry/);
 const controller=new AbortController();
 await assert.rejects(compileNativeLocationContext({referenceFeatures:reference,features:reference.slice(1),base,latitudes,
  signal:controller.signal,onProgress:()=>controller.abort()}),{name:'AbortError'});
 const corrupt=new Float64Array(latitudes);corrupt[0]+=1e-8;
 await assert.rejects(compileNativeLocationContext({referenceFeatures:reference,features:reference,base,latitudes:corrupt}),/latitude rule/);
});


test('streamed reuse coalesces adjacent fragments without changing dense owners or untouched gaps',async()=>{
 let row=-1,index=-1,run;
 for(let y=0;y<size&&row<0;y++)for(let n=base.rows[y*2];n<base.rows[y*2]+base.rows[y*2+1];n++){
  const candidate=ownershipRun(base,n);
  if(candidate.end-candidate.start>2){row=y;index=n;run=candidate;break;}
 }
 assert.ok(row>=0);
 const runs=new Uint32Array(base.runs.length+2),rows=new Uint32Array(base.rows);
 runs.set(base.runs.subarray(0,index*2));
 const middle=run.start+1,factor=2**19,ownerBase=2**13;
 const encode=(offset,start,end)=>{runs[offset]=run.id%ownerBase*factor+start;runs[offset+1]=Math.floor(run.id/ownerBase)*factor+end-1;};
 encode(index*2,run.start,middle);encode(index*2+2,middle,run.end);
 runs.set(base.runs.subarray(index*2+2),index*2+4);
 rows[row*2+1]++;
 for(let y=row+1;y<size;y++)rows[y*2]++;
 const result=await compileNativeLocationContext({referenceFeatures:reference,features:reference,base:{...base,rows,runs},latitudes});
 const expected=await compileNativeRuntime(result.context.features.map((f,i)=>({...f,pixelIndex:i+1})),{size,latitudes});
 assert.deepEqual(result.grid.rows,expected.rows);assert.deepEqual(result.grid.runs,expected.runs);
 assert.equal(result.accounting.recomputedRows,0);
});


test('same retained geometry object with a new additive ledger recomputes native rows and equals a full compile',async()=>{
 const {footprintValueSha256:hash,compileEffectiveNativeRuntime}=await import('../src/effective-footprint.js');
 const old=reference[0],gain={type:'Polygon',coordinates:[ring(1,0,1.01,.01)]};
 const changed={...old,additiveFootprint:{version:1,kind:'retained-base-plus-additions',baseline_release_sha256:'a'.repeat(64),
  base_geometry_sha256:hash(old.geometry),ledger_sha256:'b'.repeat(64),rule_sha256:'c'.repeat(64),
  additions:[{component_id:'fixture-gap',geometry:gain,geometry_sha256:hash(gain),source_receipt_sha256:'d'.repeat(64)}]}};
 const result=await compileNativeLocationContext({referenceFeatures:reference,features:[changed,...reference.slice(1)],base,latitudes});
 const expected=await compileEffectiveNativeRuntime(result.context.features.map((f,i)=>({...f,pixelIndex:i+1})),{size,latitudes});
 assert.deepEqual(result.grid.rows,expected.rows);assert.deepEqual(result.grid.runs,expected.runs);
 assert.ok(result.accounting.recomputedRows>0);assert.equal(changed.geometry,old.geometry);
});
