import assert from 'node:assert/strict';

// Exact original audit strip equations and sequential binary64 accumulation.
export function nativeRowArea(y,size) {
 const A=6378137,F=1/298.257223563,E2=F*(2-F),E=Math.sqrt(E2),C=A*A*(1-E2)/2;
 const strip=u=>C*(u/(1-E2*u*u)+Math.atanh(E*u)/E);
 const north=Math.atan(Math.sinh(Math.PI*(1-2*y/size))),south=Math.atan(Math.sinh(Math.PI*(1-2*(y+1)/size)));
 const area=(strip(Math.sin(north))-strip(Math.sin(south)))*2*Math.PI/size;
 assert(area>0);return area;
}
export function selectedOwnerRuns(rows,words,{offset,size,coordinateBits,owners,targetOwners}) {
 assert(rows instanceof Uint32Array&&rows.length===size*2);
 assert(words instanceof Uint32Array&&words.length%2===0&&offset%2===0);
 assert(new Set(targetOwners).size===2&&targetOwners.every(owner=>owner>=1&&owner<=owners));
 const result=Object.fromEntries(targetOwners.map(owner=>[owner,[]]));
 const first=offset/2;let lo=0,hi=size;
 while(lo<hi){const mid=Math.floor((lo+hi)/2);if(rows[mid*2]+rows[mid*2+1]<=first)lo=mid+1;else hi=mid;}
 let y=lo;const mask=2**coordinateBits-1,base=2**(32-coordinateBits);
 for(let k=0;k<words.length;k+=2){const run=(offset+k)/2;
  while(y<size&&run>=rows[y*2]+rows[y*2+1])y++;
  assert(y<size&&run>=rows[y*2]);
  const a=words[k],b=words[k+1],start=a&mask,end=(b&mask)+1,owner=(a>>>coordinateBits)+(b>>>coordinateBits)*base;
  assert(end>start&&end<=size&&owner>=1&&owner<=owners);
  if(result[owner])result[owner].push([run,y,end-start]);
 }
 return result;
}
export function sumCompleteOwnerRuns(groups,{size,totalRunWords,targetOwners}) {
 const result=Object.fromEntries(targetOwners.map(owner=>[owner,{cells:0,grid_wgs84_area_m2:0,runs:0}]));
 let offset=0;
 for(const group of groups){assert.equal(group.offset,offset);assert(group.words>0&&group.words%2===0);offset+=group.words;
  assert.deepEqual(Object.keys(group.targets).map(Number).sort((a,b)=>a-b),[...targetOwners].sort((a,b)=>a-b));
  for(const owner of targetOwners){let previous=-1;for(const [run,y,length] of group.targets[owner]){
   assert(Number.isInteger(run)&&run>=group.offset/2&&run<(group.offset+group.words)/2&&run>previous);previous=run;
   assert(Number.isInteger(y)&&y>=0&&y<size&&Number.isInteger(length)&&length>0&&length<=size);
   result[owner].cells+=length;result[owner].grid_wgs84_area_m2+=length*nativeRowArea(y,size);result[owner].runs++;
  }}
 }
 assert.equal(offset,totalRunWords);return result;
}
