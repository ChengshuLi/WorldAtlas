import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {compactContextInputs} from '../scripts/native-ownership/compact-context-inputs.mjs';
const ring=[[0,0],[1,0],[1,1],[0,0]];
const features=[{id:'B',properties:{parent_id:'P2',name:'Original B',fact:'retained'},geometry:{type:'MultiPolygon',coordinates:[[ring]]}},
 {id:'A',properties:{parent_id:'P1'},geometry:{type:'Polygon',coordinates:[ring]}}];
const bounds=[{id:'A',index:1,province_id:'P1'},{id:'B',index:2,province_id:'P2'}];
const sha=value=>createHash('sha256').update(JSON.stringify(value)).digest('hex');
const footprint=sha(features.map(f=>[f.id,f.geometry]).sort((a,b)=>a[0].localeCompare(b[0])));
test('compact derivative preserves exact native geometry type, coordinates and original owner/parent mapping',()=>{
 const original=JSON.stringify(features),a=compactContextInputs(features,bounds,footprint),b=compactContextInputs(features,bounds,footprint);
 assert.deepEqual(a,b);assert.equal(JSON.stringify(features),original);
 assert.deepEqual(a.features.map(f=>[f.id,f.pixelIndex,f.properties.parent_id]),[['A',1,'P1'],['B',2,'P2']]);
 assert.equal(a.features[1].geometry.type,'MultiPolygon');assert.deepEqual(a.features[1].geometry,features[0].geometry);
 assert.equal(a.footprints_sha256,footprint);assert.equal(features[0].properties.fact,'retained');
});
test('incomplete IDs, wrong parents, drifted source digest and malformed native rings reject',()=>{
 assert.throws(()=>compactContextInputs(features.slice(1),bounds,footprint),/inventories/);
 assert.throws(()=>compactContextInputs([features[0],features[0]],bounds,footprint),/identity/);
 const wrong=structuredClone(features);wrong[0].properties.parent_id='wrong';
 assert.throws(()=>compactContextInputs(wrong,bounds,footprint),/parent/);
 assert.throws(()=>compactContextInputs(features,bounds,'0'.repeat(64)),/digest/);
 const broken=structuredClone(features);broken[0].geometry.coordinates[0][0][0][0]=NaN;
 assert.throws(()=>compactContextInputs(broken,bounds,footprint),/coordinates/);
});
