import assert from 'node:assert/strict';
import {joinPixelAccounting,installedPixelTarget} from './pixel-accounting-join.mjs';
import fs from 'node:fs';
import {nativeRowArea} from './pixel-area-order.mjs';
// Synthetic complete-shaped predecessor boundary, not a world restoration.
const parts=[];for(let i=0,offset=0;i<55;i++) {
 const words=i===54?57617774-offset:1048576;
 parts.push({offset,words,targets:{6666:[],6757:[]}});offset+=words;
}
parts[0].targets={6666:[[0,100,20]],6757:[[1,100,30]]};
const groups=Array.from({length:28},(_,ordinal)=>{
 const value={version:1,kind:'complete-native-target-run-accounting-group',ordinal,total_groups:28,
  full_run_parts:55,full_row_count:262166,owner_count:49625,total_run_words:57617774,
  target_owners:[6666,6757],grid_rows_computed:0,activated:false,parts:parts.slice(ordinal*2,ordinal*2+2)};
 const before=structuredClone({...value,side:'before'}),after=structuredClone({...value,side:'after'});
 if(ordinal===0){after.parts[0].targets[6666][0][2]+=140;after.parts[0].targets[6757][0][2]++;}
 return {before,after};
});
const pixel={locations:49625,records:Array.from({length:49625},(_,i)=>({id:`id${i+1}`,owner:i+1}))};
for(const [owner,id,cells] of [[6666,'atlas:physical:CAN-15:NWT',20],[6757,'atlas:physical:CAN-25:NUN',30]])
 Object.assign(pixel.records[owner-1],{id,owner:'Canada',cells,grid_wgs84_area_m2:Number((cells*nativeRowArea(100,262166)).toFixed(6))});
const result=joinPixelAccounting(groups,pixel);assert.equal(result.added_cells,141);assert.equal(result.records.length,2);
let negatives=0;
function reject(change){const g=structuredClone(groups),p=structuredClone(pixel);change(g,p);assert.throws(()=>joinPixelAccounting(g,p));negatives++;}
reject(g=>g.pop());reject(g=>g.reverse());reject(g=>g[0].after.parts[0].offset=2);
reject((g,p)=>p.records[6665].cells++);reject((g,p)=>p.records[6665].grid_wgs84_area_m2+=0.000001);
reject((g,p)=>p.records[6665].id='foreign');reject(g=>g[0].before.owner_count--);
reject(g=>g[0].after.parts[0].targets[6666][0][2]++);
reject(g=>g[0].after.parts[0].targets[6666].push([0,100,1]));
console.log(JSON.stringify({positive:1,negative:negatives,fixture:'synthetic-complete-shaped-join-boundary',grid_rows_computed:0}));

const actual=JSON.parse(fs.readFileSync(new URL('./pixel-accounting-original-records.json',import.meta.url)));
assert.equal(actual.source.sha256,'a49773818f963c15c27b52a0cad7be6dabcb6dddf9523bdbc253118e177c9cd8');
for(const row of actual.records)assert.strictEqual(installedPixelTarget(actual.records,row.id),row);
assert.throws(()=>installedPixelTarget([...actual.records,actual.records[0]],actual.records[0].id));
assert.throws(()=>installedPixelTarget([],actual.records[0].id));
assert.throws(()=>installedPixelTarget(actual.records,'CAN-15:NWT'));
console.log(JSON.stringify({actual_original_records:2,lookup_positive:2,lookup_negative:3,opaque_country_metadata_retained:true}));
