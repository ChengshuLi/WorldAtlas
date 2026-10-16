import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {verifyNativeSeamView,nativePolygonIntervals,nativeRuntimeIndex} from '../src/native-grid.js';
const box=(left,right,bottom=-1,top=1)=>({type:'Polygon',coordinates:[[[left,bottom],[right,bottom],[right,top],[left,top],[left,bottom]]]});
const options={size:360,latitudes:Float64Array.from({length:360},(_,i)=>89.75-i*.5)};
test('explicit seam comparison preserves strict defaults and rejects changed complete spans or ties',()=>{
 const original=box(170,180.0000000000001),view=box(170,180);
 const before=structuredClone({original,view});
 assert.equal(verifyNativeSeamView(original,view,options).overrun_vertices,2);
 assert.deepEqual({original,view},before);
 assert.throws(()=>nativeRuntimeIndex([{id:'a',pixelIndex:1,geometry:original}]),/Original lon\/lat/);
 const index=[{index:1,polygons:original.coordinates.map(r=>[Float64Array.from(r.flat())])}];
 assert.throws(()=>nativePolygonIntervals(index,{...options,rowStart:0,rowEnd:360}),/Invalid native lon\/lat/);
 for(const invalid of [box(170,180.000000000001),box(170,181),box(170,540)])
  assert.throws(()=>verifyNativeSeamView(invalid,view,options),/exceeds retained roundoff/);
 assert.throws(()=>verifyNativeSeamView(view,view,options),/actual retained seam overrun/);
 assert.throws(()=>verifyNativeSeamView(original,box(169,180),options),/changes complete native spans or boundary ties/);
 // Same occupied spans, but a new exact cell-centre boundary must still fail.
 assert.throws(()=>verifyNativeSeamView(original,box(169.5,180),options),/changes complete native spans or boundary ties/);
 assert.throws(()=>verifyNativeSeamView(original,view,{size:360,latitudes:[]}),/explicit latitude table/);
 assert.throws(()=>verifyNativeSeamView(original,view,{...options,latitudes:new Float64Array(360)}),/decreasing native/);
 const malformed=structuredClone(view);malformed.coordinates[0].pop();
 assert.throws(()=>verifyNativeSeamView(original,malformed,options),/Unclosed native ring/);
});
test('all actual Fiji source, physical and query views preserve the complete native pointsets',()=>{
 const prefix=new URL('../coordination/engineering/fiji-current-cell-20261016/',import.meta.url);
 const read=name=>JSON.parse(fs.readFileSync(new URL(name,prefix)));
 const stage=read('original-stage-inputs.json'),physical=read('physical-001/whole-target-support.json');
 const table=read('canonical-views-001/canonical-seam-views.json');
 const pin=read('source-002/source-evidence.json').native_latitudes;
 const encoded=fs.readFileSync(new URL('../'+pin.path,import.meta.url));
 const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
 assert.equal(encoded.length,pin.bytes);assert.equal(sha(encoded),pin.sha256);
 const bytes=gunzipSync(encoded,{maxOutputLength:pin.decoded_bytes});
 assert.equal(bytes.length,pin.decoded_bytes);assert.equal(sha(bytes),pin.decoded_sha256);
 const normative={size:262166,latitudes:Float64Array.from({length:262166},(_,i)=>bytes.readDoubleLE(i*8))};
 let sourceOverruns=0,physicalCount=0;
 assert.equal(table.records.length,10);
 for(const record of table.records){
  const target=record.role==='source'?stage.find(s=>s.target===record.source_id).consumed:
   physical.results.find(s=>s.target===record.source_id);
  const original=record.pointer.slice(1).split('/').reduce((value,key)=>value[key],target);
  const result=verifyNativeSeamView(original,record.geometry,normative);
  if(record.role==='source')sourceOverruns+=result.overrun_vertices;else physicalCount++;
  assert.ok(result.native_cells>0);
  assert.ok(result.checked_rows>1);
 }
 assert.equal(sourceOverruns,10);assert.equal(physicalCount,8);
});
