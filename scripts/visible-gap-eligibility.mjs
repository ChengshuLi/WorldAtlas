// Display eligibility only. Inputs still need their ordinary source/selection custody.
// Use the same exact native operator as ownership preparation; never area/size proxies.
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {nativePolygonIntervals, NATIVE_GRID_METHOD} from '../src/native-grid.js';

const demand=(ok,message)=>{if(!ok)throw Error(message);};
const sha=body=>createHash('sha256').update(body).digest('hex');
const canonical=value=>Array.isArray(value)?value.map(canonical):value&&typeof value==='object'
  ?Object.fromEntries(Object.keys(value).sort().map(key=>[key,canonical(value[key])])):value;
export const visibilityDigest=value=>sha(Buffer.from(JSON.stringify(canonical(value))+'\n'));
export const VISIBILITY_METHOD='current-native-unassigned-cell-witness-v1';

export function decodeVisibilityLatitudes(encoded,pin,size) {
  demand(pin&&Number.isSafeInteger(size)&&size>1&&pin.decoded_bytes===size*8
    &&encoded.length===pin.bytes&&sha(encoded)===pin.sha256,'Visibility latitude encoded binding differs');
  const raw=gunzipSync(encoded,{maxOutputLength:size*8});
  demand(raw.length===size*8&&sha(raw)===pin.decoded_sha256,'Visibility normative latitude bytes differ');
  return Float64Array.from({length:size},(_,y)=>raw.readDoubleLE(y*8));
}

function indexCandidates(candidates) {
  demand(Array.isArray(candidates)&&candidates.length<=4096,'Bounded visibility candidate roster required');
  const ids=new Set();
  return candidates.map((candidate,i)=>{
    demand(typeof candidate.component_id==='string'&&!ids.has(candidate.component_id),'Duplicate/missing visibility component');
    ids.add(candidate.component_id);
    const g=candidate.geometry;
    demand(['Polygon','MultiPolygon'].includes(g?.type),'Visibility requires the exact polygon primitive');
    const bounds=[Infinity,Infinity,-Infinity,-Infinity];let vertices=0;
    const polygons=(g.type==='Polygon'?[g.coordinates]:g.coordinates).map(p=>p.map(r=>{
      for(const point of r){
        demand(Array.isArray(point)&&point.length===2&&point.every(Number.isFinite),'Invalid native visibility coordinate');
        bounds[0]=Math.min(bounds[0],point[0]);bounds[1]=Math.min(bounds[1],point[1]);
        bounds[2]=Math.max(bounds[2],point[0]);bounds[3]=Math.max(bounds[3],point[1]);vertices++;
      }
      return Float64Array.from(r.flat());
    }));
    const digest=visibilityDigest(g);
    demand(candidate.geometry_sha256===undefined||candidate.geometry_sha256===digest,'Visibility candidate geometry binding differs');
    return {index:i+1,polygons,bounds,vertices,candidate,geometry_sha256:digest};
  });
}
function ownerRows(rows,size) {
  const result=new Map();let previous=-1;
  for(const row of rows){
    demand(Number.isInteger(row.y)&&row.y>previous&&row.y>=0&&row.y<size&&Array.isArray(row.runs),'Incomplete/unordered visibility owner row');
    previous=row.y;let end=0;
    for(const run of row.runs){
      demand(run.length===3&&run.every(Number.isSafeInteger)&&run[0]>=end&&run[1]>run[0]
        &&run[1]<=size&&run[2]>0,'Invalid complete visibility owner interval');end=run[1];
    }
    result.set(row.y,row.runs);
  }
  return result;
}
function emptySpans(start,end,owned) {
  const result=[];let at=start;
  for(const [left,right]of owned){
    if(right<=at)continue;if(left>=end)break;
    if(left>at)result.push([at,Math.min(left,end)]);
    at=Math.max(at,right);if(at>=end)break;
  }
  if(at<end)result.push([at,end]);return result;
}
function firstAtOrBelow(latitudes,value) {
  let lo=0,hi=latitudes.length;
  while(lo<hi){const mid=Math.floor((lo+hi)/2);if(latitudes[mid]>value)lo=mid+1;else hi=mid;}
  return lo;
}
function mergeSpans(spans) {
  const result=[];
  for(const span of spans.sort((a,b)=>a[0]-b[0]||a[1]-b[1])){
    const last=result.at(-1);
    if(last&&span[0]<=last[1])last[1]=Math.max(last[1],span[1]);else result.push([...span]);
  }
  return result;
}

// Group candidates sharing one <=4096-row block to amortize latitude validation.
// Archived representative cells may choose this block; failure never proves zero.
export function screenNativeGapCandidates({candidates,size,latitudes,rows,rowStart,rowEnd,selection}) {
  demand(selection&&/^[a-f0-9]{64}$/.test(selection.current_selection_sha256)
    &&/^[a-f0-9]{64}$/.test(selection.patch_sha256),'Current effective selection binding required');
  const index=indexCandidates(candidates),owned=ownerRows(rows,size);
  demand(owned.size===rowEnd-rowStart&&[...owned.keys()].every((y,i)=>y===rowStart+i),
    'Visibility requires every complete effective owner row in its declared block');
  const native=nativePolygonIntervals(index,{size,latitudes,rowStart,rowEnd});
  const counts=index.map(()=>({nativeCells:0,unowned:0,witness:null}));
  for(const [y,spans]of native.rows){
    const byOwner=new Map();
    for(const span of spans){if(!byOwner.has(span.owner))byOwner.set(span.owner,[]);byOwner.get(span.owner).push([span.start,span.end]);}
    for(const [owner,parts]of byOwner){
      const count=counts[owner-1];
      for(const [start,end]of mergeSpans(parts)){
        count.nativeCells+=end-start;
        for(const [left,right]of emptySpans(start,end,owned.get(y))){
          count.unowned+=right-left;count.witness??={x:left,y,current_owner:0};
        }
      }
    }
  }
  return index.map(item=>{
    const {nativeCells,unowned,witness}=counts[item.index-1];
    const first=firstAtOrBelow(latitudes,item.bounds[3]),end=firstAtOrBelow(latitudes,item.bounds[1]);
    const complete=first>=rowStart&&end<=rowEnd;
    return {component_id:item.candidate.component_id,geometry_sha256:item.geometry_sha256,
      status:witness?'visible':complete?'invisible':'unknown',repair_eligible:!!witness,
      reason:witness?'current-unassigned-native-cell':complete?(nativeCells?'already-covered-native-cells':'no-native-cell'):'partial-negative-scan',
      method:VISIBILITY_METHOD,native_method:NATIVE_GRID_METHOD,
      current_selection_sha256:selection.current_selection_sha256,patch_sha256:selection.patch_sha256,
      containing_native_asset_ids:selection.containing_native_asset_ids??[],
      source_family_id:item.candidate.source_family_id??null,source_product_sha256:item.candidate.source_product_sha256??null,
      bounds:item.bounds,source:item.candidate.source??null,target_id:item.candidate.target_id??null,
      complete_native_scope:complete,checked_rows:[rowStart,rowEnd],required_rows:[first,end],
      native_candidate_cells:complete?nativeCells:null,current_unassigned_cells:complete?unowned:null,
      witnessed_unassigned_cells:unowned,witness,
      estimated_native_work:{vertices:item.vertices,rows:end-first},
      limits:['Visibility is not source approval. A native cell is visible at supported maximum zoom; world-view sampling can hide it.']};
  });
}

// This applies at the requested baseline->candidate boundary only. Historical
// checkpoint traversal and unchanged accepted zero-cell primitives remain valid.
export function newVisibleRepairCandidates(before,after) {
  const old=new Set(before.map(row=>row.component_id)),seen=new Set();
  const added=[];
  for(const row of after){
    demand(!seen.has(row.component_id),'Duplicate candidate repair component');seen.add(row.component_id);
    if(old.has(row.component_id))continue;
    if(!['assigned','zero-cell'].includes(row.disposition))continue;
    demand(row.disposition==='assigned'&&Number.isSafeInteger(row.native_cells)&&row.native_cells>0,
      'New gap repair must change map cells: '+row.component_id);
    added.push(row);
  }
  return added;
}

// Every observed row is a complete actual before/after owner row. Find a literal
// native sample inside each new primitive that changes from unowned to its owner.
// A positive aggregate or a sibling's unrelated changed cell cannot pass.
export function repairVisibilityWitnesses({candidates,size,latitudes,beforeRows,afterRows}) {
  const before=ownerRows(beforeRows,size),after=ownerRows(afterRows,size),ys=[...before.keys()];
  demand(JSON.stringify(ys)===JSON.stringify([...after.keys()]),'Visibility before/after row scope differs');
  const index=indexCandidates(candidates),witnesses=new Map();
  for(let k=0;k<ys.length;){
    const start=ys[k];let end=k+1;while(end<ys.length&&ys[end]-start<4096)end++;
    const native=nativePolygonIntervals(index,{size,latitudes,rowStart:start,rowEnd:ys[end-1]+1});
    for(let n=k;n<end;n++){
      const y=ys[n];
      for(const span of native.rows.get(y)??[]){
        const item=index[span.owner-1];if(witnesses.has(item.candidate.component_id))continue;
        for(const [left,right]of emptySpans(span.start,span.end,before.get(y))){
          const hit=after.get(y).find(run=>run[2]===item.candidate.pixelIndex&&Math.max(left,run[0])<Math.min(right,run[1]));
          if(hit){witnesses.set(item.candidate.component_id,{component_id:item.candidate.component_id,
            geometry_sha256:item.geometry_sha256,x:Math.max(left,hit[0]),y,
            previous_owner:0,candidate_owner:hit[2]});break;}
        }
      }
    }
    k=end;
  }
  return candidates.map(row=>witnesses.get(row.component_id)??null);
}
