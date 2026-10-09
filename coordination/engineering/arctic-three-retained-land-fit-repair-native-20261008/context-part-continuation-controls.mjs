import assert from 'node:assert/strict';
import {continueContextPart,continueContextIndex} from './context-part-continuation.mjs';
const ids=['atlas:physical:CAN-15:NWT','atlas:physical:CAN-25:NUN','unchanged'];
const before=ids.map((id,i)=>({id,pixelIndex:i+1,properties:{parent_id:'parent'},geometry:{type:'Polygon',coordinates:[[[i,0],[i+1,0],[i,1],[i,0]]]}}));
const changed=before.slice(0,2).map(row=>({...row,geometry:{...row.geometry,coordinates:[...row.geometry.coordinates,[[9,0],[10,0],[9,1],[9,0]]]}}));
const result=continueContextPart(before,changed,{firstOwner:1,owners:3});
assert.equal(result.after[2],before[2]); assert.equal(result.unchanged_full_rows,1);
assert.deepEqual(result.after.map(row=>{const {geometry,...metadata}=row;return metadata;}),before.map(row=>{const {geometry,...metadata}=row;return metadata;}));
let negatives=0;function reject(fn){assert.throws(fn);negatives++;}
reject(()=>continueContextPart(before,changed.slice(0,1),{firstOwner:1,owners:3}));
reject(()=>continueContextPart([before[1],before[0],before[2]],changed,{firstOwner:1,owners:3}));
reject(()=>continueContextPart(before,changed.map(row=>({...row,properties:{parent_id:'wrong'}})),{firstOwner:1,owners:3}));
reject(()=>continueContextPart(before,[before[0],changed[1]],{firstOwner:1,owners:3}));
reject(()=>continueContextPart(before,changed.map(row=>({...row,foreign:true})),{firstOwner:1,owners:3}));
reject(()=>continueContextPart(before.slice(0,2),changed,{firstOwner:1,owners:3}));
const footprints={original_footprints_sha256:'b9a3c8bf375217dba3a50d1a022ec7e4ac6c6f1cdedff22845da953c805b7433',current_footprints_sha256:'2deeff1457ff9238cb3dbe599e9a858dcce29d8ba88e2a66abe2785ddec0aed9'};
const index={version:1,locations:49625,footprints_sha256:footprints.original_footprints_sha256,
 owner_sha256:'90facdfa2c74a935e7e64fe2b2467de3b09f3b816eb96ba350f4f5bacb2227c2',
 parts:Array.from({length:34},(_,i)=>({path:`context/part-${i*1500}.json.gz`,first_owner:i*1500+1,owners:i===33?125:1500,sha256:'old'}))};
const nextPart={...index.parts[4],sha256:'current'},nextIndex=continueContextIndex(index,nextPart,footprints);
assert.equal(nextIndex.footprints_sha256,footprints.current_footprints_sha256);
assert.equal(nextIndex.owner_sha256,index.owner_sha256);assert.equal(nextIndex.locations,index.locations);
for(let i=0;i<34;i++)if(i!==4)assert.equal(nextIndex.parts[i],index.parts[i]);
reject(()=>continueContextIndex({...index,footprints_sha256:'0'.repeat(64)},nextPart,footprints));
reject(()=>continueContextIndex({...index,owner_sha256:'0'.repeat(64)},nextPart,footprints));
reject(()=>continueContextIndex({...index,locations:49624},nextPart,footprints));
reject(()=>continueContextIndex(index,{...nextPart,path:'foreign'},footprints));
console.log(JSON.stringify({positive:3,negative:negatives,unchanged_row_identity:true,successor_index_metadata:true}));
