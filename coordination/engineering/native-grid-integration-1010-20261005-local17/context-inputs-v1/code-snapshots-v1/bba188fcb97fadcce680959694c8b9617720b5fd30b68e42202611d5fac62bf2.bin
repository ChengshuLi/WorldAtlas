import {createHash} from 'node:crypto';
import {nativeRuntimeIndex} from '../../src/native-runtime.js';
const digest=bytes=>createHash('sha256').update(bytes).digest('hex');

// A derivative input for a separately reviewed transform stage, never a new
// geographic source or factual catalog. Retain original geometry type/coordinates,
// immutable IDs/parents and explicit original owner indices; omit unused metadata.
export function compactContextInputs(features,bounds,expectedFootprints) {
 if(!Array.isArray(features)||!Array.isArray(bounds)||features.length!==bounds.length||!features.length)
  throw Error('Complete original feature and owner inventories required');
 const owners=new Map(bounds.map(owner=>[owner.id,owner]));
 if(owners.size!==bounds.length||bounds.some((owner,i)=>owner.index!==i+1||typeof owner.province_id!=='string'))
  throw Error('Complete explicit original owner/parent mapping required');
 const seen=new Set();
 const output=features.map(feature=>{
  const owner=owners.get(feature.id);
  if(!owner||seen.has(feature.id)||feature.properties?.parent_id!==owner.province_id)
   throw Error('Original stable identity/parent differs');
  seen.add(feature.id);
  return {id:feature.id,pixelIndex:owner.index,properties:{parent_id:owner.province_id},geometry:feature.geometry};
 }).sort((a,b)=>a.pixelIndex-b.pixelIndex);
 nativeRuntimeIndex(output); // Reject malformed rings, nonfinite input or unsupported geometry.
 const hash=createHash('sha256').update('[');
 const ordered=[...output].sort((a,b)=>a.id.localeCompare(b.id));
 for(let i=0;i<ordered.length;i++){if(i)hash.update(',');hash.update(JSON.stringify([ordered[i].id,ordered[i].geometry]));}
 const footprints=hash.update(']').digest('hex');
 if(footprints!==expectedFootprints)throw Error('Original source footprint digest differs');
 return {features:output,footprints_sha256:footprints,
  owner_sha256:digest(JSON.stringify(output.map(f=>[f.pixelIndex,f.id]))),
  scope:'Original native geometry and explicit identity/parent indices only; omitted metadata remains in untouched original files.'};
}
