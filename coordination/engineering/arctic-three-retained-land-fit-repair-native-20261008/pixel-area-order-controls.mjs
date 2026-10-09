import assert from 'node:assert/strict';
import {nativeRowArea,selectedOwnerRuns,sumCompleteOwnerRuns} from './pixel-area-order.mjs';
const rows=new Uint32Array([0,2,2,1,3,1,4,1]);
const runs=[[0,2,1],[3,4,2],[0,4,1],[1,4,2],[0,1,1]];
const words=new Uint32Array(runs.flatMap(([a,b,o])=>[o*4+a,b-1]));
const options={size:4,coordinateBits:2,owners:2,targetOwners:[1,2]};
const groups=[{offset:0,words:4,targets:selectedOwnerRuns(rows,words.slice(0,4),{...options,offset:0})},{offset:4,words:6,targets:selectedOwnerRuns(rows,words.slice(4),{...options,offset:4})}];
const result=sumCompleteOwnerRuns(groups,{...options,totalRunWords:10});
const counts=[0,0,0],areas=[0,0,0],rowAreas=new Float64Array(4);
const A=6378137,F=1/298.257223563,E2=F*(2-F),E=Math.sqrt(E2),C=A*A*(1-E2)/2,strip=u=>C*(u/(1-E2*u*u)+Math.atanh(E*u)/E);
for(let y=0;y<4;y++){const north=Math.atan(Math.sinh(Math.PI*(1-2*y/4))),south=Math.atan(Math.sinh(Math.PI*(1-2*(y+1)/4)));rowAreas[y]=(strip(Math.sin(north))-strip(Math.sin(south)))*2*Math.PI/4;assert.equal(nativeRowArea(y,4),rowAreas[y]);}
let y=0;for(let i=0;i<runs.length;i++){while(i>=rows[y*2]+rows[y*2+1])y++;const [a,b,o]=runs[i];counts[o]+=b-a;areas[o]+=(b-a)*rowAreas[y];}
for(const o of [1,2]){assert.equal(result[o].cells,counts[o]);assert.equal(result[o].grid_wgs84_area_m2,areas[o]);}
let negatives=0;const reject=fn=>{assert.throws(fn);negatives++;};
reject(()=>sumCompleteOwnerRuns(groups.slice(0,1),{...options,totalRunWords:10}));
reject(()=>sumCompleteOwnerRuns([...groups].reverse(),{...options,totalRunWords:10}));
reject(()=>selectedOwnerRuns(rows,words,{...options,offset:0,targetOwners:[1,1]}));
reject(()=>selectedOwnerRuns(rows,words,{...options,offset:10}));
reject(()=>selectedOwnerRuns(rows,new Uint32Array([5,0]),{...options,offset:0}));
reject(()=>sumCompleteOwnerRuns([{...groups[0],targets:{1:groups[0].targets[1]}}],{...options,totalRunWords:4}));
console.log(JSON.stringify({positive:2,negative:negatives,original_binary64_area_order:true}));
