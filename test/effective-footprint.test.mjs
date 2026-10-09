import test from 'node:test';
import assert from 'node:assert/strict';
import {effectivePrimitiveGeometries, effectiveFootprintValue, effectiveFootprintBounds, assertLegacyFootprint, footprintValueSha256} from '../src/effective-footprint.js';
const rectangle = (a,b,c,d) => ({type:'Polygon',coordinates:[[[a,b],[c,b],[c,d],[a,d],[a,b]]]});
const old = {id:'A',pixelIndex:1,properties:{parent_id:'P',name:'original'},geometry:rectangle(0,0,1,1)};
function additive() { return {...old, additiveFootprint:{version:1,kind:'retained-base-plus-additions',baseline_release_sha256:'a'.repeat(64),base_geometry_sha256:footprintValueSha256(old.geometry),ledger_sha256:'b'.repeat(64),rule_sha256:'c'.repeat(64),additions:[{component_id:'gap-1',geometry:rectangle(1,0,2,1),geometry_sha256:footprintValueSha256(rectangle(1,0,2,1)),source_receipt_sha256:'d'.repeat(64)}]}}; }
test('legacy geometry/digest input is literal and additive primitives keep complete base',()=>{
 assert.equal(effectiveFootprintValue(old),old.geometry); const feature=additive(), raw=JSON.stringify(old);
 const parts=effectivePrimitiveGeometries(feature);assert.equal(parts[0],old.geometry);assert.equal(parts.length,2);
 assert.deepEqual(effectiveFootprintBounds(feature),[0,0,2,1]);assert.equal(JSON.stringify(old),raw);
 assert.equal(effectiveFootprintValue(feature).kind,'retained-base-plus-additions');assert.throws(()=>assertLegacyFootprint(feature),/effective-footprint consumer/);
});
test('actual whole representation rejects drift, missing/duplicate/foreign/unsupported fields and complete pointsets',()=>{
 for (const mutate of [f=>f.geometry.coordinates[0][0][0]=.1,f=>f.additiveFootprint.ledger_sha256='bad',f=>f.additiveFootprint.rule_sha256='bad',f=>f.additiveFootprint.additions=[],f=>f.additiveFootprint.additions.push(structuredClone(f.additiveFootprint.additions[0])),f=>f.additiveFootprint.additions[0].geometry.coordinates[0][1][0]=5,f=>delete f.additiveFootprint.additions[0].source_receipt_sha256,f=>f.additiveFootprint.extra=true,f=>f.additiveFootprint.additions[0].geometry.type='GeometryCollection',f=>f.additiveFootprint.additions[0].geometry.coordinates[0].pop()]) {
  const f=structuredClone(additive()); mutate(f);assert.throws(()=>effectivePrimitiveGeometries(f));
 }
});
