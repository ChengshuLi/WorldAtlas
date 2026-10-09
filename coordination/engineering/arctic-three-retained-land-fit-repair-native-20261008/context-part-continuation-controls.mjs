import assert from 'node:assert/strict';
import {continueContextPart} from './context-part-continuation.mjs';
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
console.log(JSON.stringify({positive:2,negative:negatives,unchanged_row_identity:true}));
