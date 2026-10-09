import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {effectiveNativeRuntimeIndex as nativeRuntimeIndex} from '../src/effective-footprint.js';
import {nativeSourceDigest} from '../src/native-source-digest.js';
import {pointInFeature} from '../src/geometry.js';
import {footprintHash} from '../scripts/check-prepared.mjs';
import {footprintValueSha256 as hash} from '../src/effective-footprint.js';
const rectangle=(a,b,c,d)=>({type:'Polygon',coordinates:[[[a,b],[c,b],[c,d],[a,d],[a,b]]]});
const base={id:'one',pixelIndex:1,properties:{parent_id:'parent'},geometry:rectangle(0,0,1,1)};
const addition=rectangle(1,0,2,1);
const feature={...base,additiveFootprint:{version:1,kind:'retained-base-plus-additions',baseline_release_sha256:'a'.repeat(64),
 base_geometry_sha256:hash(base.geometry),ledger_sha256:'b'.repeat(64),rule_sha256:'c'.repeat(64),
 additions:[{component_id:'gap',geometry:addition,geometry_sha256:hash(addition),source_receipt_sha256:'d'.repeat(64)}]}};
test('all primitives aggregate one stable reference owner and continuous membership preserves base and adds exact area',()=>{
 const index=nativeRuntimeIndex([feature]);assert.equal(index.length,1);assert.equal(index[0].polygons.length,2);assert.equal(index[0].index,1);
 for(const point of [[.5,.5],[1.5,.5]])assert.equal(pointInFeature(point,feature),true);
 assert.equal(pointInFeature([2.5,.5],feature),false);assert.equal(base.geometry,feature.geometry);
 assert.throws(()=>nativeRuntimeIndex([feature,{...feature,id:'foreign'}]),/unique/);
});
test('legacy digests remain literal; ledger-only change invalidates effective source digest without changing the historical OGC digest',async()=>{
 const literal=createHash('sha256').update(JSON.stringify([[base.id,base.geometry]])).digest('hex');
 assert.equal((await nativeSourceDigest([base])).sha256,literal);assert.equal(footprintHash([base]),literal);
 const effective=(await nativeSourceDigest([feature])).sha256;assert.notEqual(effective,literal);assert.notEqual(footprintHash([feature]),effective);
 const rebound=structuredClone(feature);rebound.additiveFootprint.ledger_sha256='e'.repeat(64);
 assert.notEqual((await nativeSourceDigest([rebound])).sha256,effective);
 assert.notEqual(footprintHash([feature]),effective); // historical OGC digest is deliberately unchanged

});

test('complete approved original pointsets produce identical native intervals under the explicit primitive adapter',async()=>{
 const fs=await import('node:fs'),{gunzipSync}=await import('node:zlib');
 const {nativePolygonIntervals}=await import('../src/native-grid.js');
 const {coverageRow}=await import('../scripts/audit-grid-intervals.mjs');
 const {nativeRuntimeIndex:originalIndex}=await import('../src/native-runtime.js');
 const fixturesRaw=fs.readFileSync('coordination/engineering/additive-native-gap-repair-20261008/accepted-1295-whole-fixtures.json');
 assert.equal(createHash('sha256').update(fixturesRaw).digest('hex'),'acd45e97757c84d9fba135e8eba8059372e09a529234d7fe5e488b2e5890817e');
 const latRaw=gunzipSync(fs.readFileSync('coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz'));
 const size=262166,latitudes=Float64Array.from({length:size},(_,y)=>latRaw.readDoubleLE(y*8));
 assert.equal(createHash('sha256').update(latRaw).digest('hex'),'66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23');
 let gained=0;
 for(const fixture of JSON.parse(fixturesRaw)){
  const baseline={id:fixture.id,pixelIndex:fixture.pixelIndex,geometry:fixture.old};
  const effective={...baseline,additiveFootprint:{version:1,kind:'retained-base-plus-additions',baseline_release_sha256:'a'.repeat(64),
   base_geometry_sha256:hash(fixture.old),ledger_sha256:'b'.repeat(64),rule_sha256:'c'.repeat(64),
   additions:[{component_id:fixture.id+':accepted-gain',geometry:fixture.gain,geometry_sha256:hash(fixture.gain),source_receipt_sha256:'d'.repeat(64)}]}};
  const polys=fixture.gain.type==='Polygon'?[fixture.gain.coordinates]:fixture.gain.coordinates;
  const ys=polys.flat(2).map(point=>point[1]),south=Math.min(...ys),north=Math.max(...ys);
  let first=latitudes.findIndex(lat=>lat<=north),end=latitudes.findIndex(lat=>lat<south);
  first=Math.max(0,first-2);end=end<0?size:Math.min(size,end+2);assert.ok(end-first<=4096);
  const options={size,latitudes,rowStart:first,rowEnd:end};
  const old=nativePolygonIntervals(originalIndex([baseline]),options),actual=nativePolygonIntervals(nativeRuntimeIndex([effective]),options);
  const approved=nativePolygonIntervals(originalIndex([{...baseline,geometry:fixture.approved_new}]),options);
  for(let y=first;y<end;y++){
   const rows=value=>coverageRow(value.rows.get(y)??[],size).filter(row=>row.owners.length);
   assert.deepEqual(rows(actual),rows(approved));
   const cells=value=>rows(value).reduce((sum,row)=>sum+row.end-row.start,0);
   assert.ok(cells(actual)>=cells(old));gained+=cells(actual)-cells(old);
  }
  assert.equal(effective.geometry,baseline.geometry);
 }
 assert.equal(gained,3); // Exact original accepted CAN103 two cells + CAN114 one.
});

test('legacy byte hashing does not bypass strict validation for actual additive records',async()=>{
 for(const mutate of [f=>f.geometry=null,f=>f.additiveFootprint=undefined,f=>f.additiveFootprint.rule_sha256='bad',f=>f.additiveFootprint.additions[0].geometry.coordinates=[]]){
  const changed=structuredClone(feature);mutate(changed);
  await assert.rejects(nativeSourceDigest([changed]));
 }
});
