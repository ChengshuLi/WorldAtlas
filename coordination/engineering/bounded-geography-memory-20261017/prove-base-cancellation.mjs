import assert from 'node:assert/strict';
import fs from 'node:fs';
import {pathToFileURL,fileURLToPath} from 'node:url';
const checkout=fileURLToPath(new URL('../../../',import.meta.url));
const {compareIntervals,repairVisibilityWitnesses,visibilityDigest}=await import(pathToFileURL(checkout+'/scripts/check-effective-geographic-regression.mjs'));
const {applyNativeAdditiveRows}=await import(pathToFileURL(checkout+'/scripts/selected-checkpoint-native.mjs'));
const {nativeRowLatitudes}=await import(pathToFileURL(checkout+'/src/native-grid.js'));
const size=4,y=1,owners=[{id:'A'},{id:'B'}],latitudes=nativeRowLatitudes(size);
function runs(cells){const out=[];for(let x=0;x<cells.length;){const owner=cells[x];let end=x+1;while(end<cells.length&&cells[end]===owner)end++;if(owner)out.push([x,end,owner]);x=end;}return out;}
const row=runs=>[{y,runs}],rect=(a,b)=>({type:'Polygon',coordinates:[[[a,-85],[b,-85],[b,85],[a,85],[a,-85]]]});
const geometry=rect(-180,180);
function native(owner,a=0,b=4){return {representation:'native-cells',component_id:`native-${owner}-${a}-${b}`,target_id:owners[owner-1].id,pixelIndex:owner,disposition:'assigned',base_geometry:geometry,base_geometry_sha256:visibilityDigest(geometry),native_rows:[{y,runs:[[a,b,owner]]}],native_bounds:[-180,-85,180,85],native_cells:b-a,source_receipt_sha256:'a'.repeat(64),authority_sha256:'b'.repeat(64),rule_sha256:'c'.repeat(64)};}
const natives=[native(1),native(2),native(1,1,3),native(2,0,1)];
const polygons=[rect(-180,180),rect(-180,0),rect(0,180),{type:'MultiPolygon',coordinates:[rect(90,180).coordinates,rect(-180,-90).coordinates]}].flatMap((geometry,i)=>[1,2].map(pixelIndex=>({component_id:`polygon-${i}-${pixelIndex}`,target_id:owners[pixelIndex-1].id,pixelIndex,geometry})));
const choices=[[1,0,0],[2,0,0]];for(let old=0;old<=2;old++)for(let next=0;next<=2;next++)choices.push([0,old,next]);
let cases=0,witnessChecks=0,polygonChecks=0,lossCases=0,positiveWitnesses=0;
const began=performance.now();
for(let code=0;code<choices.length**size;code++){
  let n=code;const base=[],old=[],next=[];
  for(let x=0;x<size;x++){const a=choices[n%choices.length];n=Math.floor(n/choices.length);base.push(a[0]);old.push(a[1]);next.push(a[2]);}
  const baseRows=row(runs(base)),oldPatch=row(runs(old)),nextPatch=row(runs(next));
  const before=applyNativeAdditiveRows(baseRows,{rows:oldPatch},{size,owners}),after=applyNativeAdditiveRows(baseRows,{rows:nextPatch},{size,owners});
  const full=compareIntervals(before[0].runs,after[0].runs,{row:y,ownersBefore:owners,ownersAfter:owners});
  const canceled=compareIntervals(oldPatch[0].runs,nextPatch[0].runs,{row:y,ownersBefore:owners,ownersAfter:owners});
  assert.deepEqual(canceled,full,`ordered loss intervals at code ${code}`);if(full.length)lossCases++;
  const a=repairVisibilityWitnesses({candidates:natives,size,latitudes,beforeRows:before,afterRows:after});
  const b=repairVisibilityWitnesses({candidates:natives,size,latitudes,beforeRows:oldPatch,afterRows:nextPatch});
  assert.deepEqual(b,a,`native first witnesses at code ${code}`);witnessChecks+=natives.length;positiveWitnesses+=a.filter(Boolean).length;
  if(code%17===0||code<121){
    const a=repairVisibilityWitnesses({candidates:polygons,size,latitudes,beforeRows:before,afterRows:after});
    const b=repairVisibilityWitnesses({candidates:polygons,size,latitudes,beforeRows:oldPatch,afterRows:nextPatch});
    assert.deepEqual(b,a,`polygon first witnesses at code ${code}`);polygonChecks+=polygons.length;
  }
  cases++;
}
// Independent cells verify the reduction's necessary boundaries, not only algebraic equality.
assert.throws(()=>applyNativeAdditiveRows(row([[0,2,1]]),{rows:row([[1,3,1]])},{size,owners}),/overlaps/);
const overlapFull=repairVisibilityWitnesses({candidates:[native(1)],size,latitudes,beforeRows:row([[0,2,1]]),afterRows:row([[0,2,1]])});
const overlapPatch=repairVisibilityWitnesses({candidates:[native(1)],size,latitudes,beforeRows:row([]),afterRows:row([[0,2,1]])});
assert.notDeepEqual(overlapFull,overlapPatch,'omitting disjointness must be caught by this counterexample');
const rebound=compareIntervals([[0,1,1]],[[0,1,1]],{row:y,ownersBefore:[{id:'A'}],ownersAfter:[{id:'B'}]});assert.equal(rebound.length,1,'same base bytes cannot cancel a rebound owner roster');
console.log(JSON.stringify({codeIdentity:'executing checkout; preserve exact Git head with this result',cases,lossCases,nativeWitnessChecks:witnessChecks,polygonWitnessChecks:polygonChecks,positiveNativeWitnesses:positiveWitnesses,adverseControls:2,milliseconds:performance.now()-began,scope:'Exact same authenticated base and stable owners; both patches independently disjoint. No source approval.'},null,2));
