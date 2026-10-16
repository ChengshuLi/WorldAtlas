import {createHash} from 'node:crypto';
import {nativeRuntimeIndex} from '../../src/native-runtime.js';
import {validateReferenceMetadataProjection} from '../selected-reference-metadata.mjs';
const digest=bytes=>createHash('sha256').update(bytes).digest('hex');

// A derivative input for a separately reviewed transform stage, never a new
// geographic source or factual catalog. Retain original geometry type/coordinates,
// immutable IDs and explicit original owner indices; omit unused metadata.
// Current parents require a complete source/receipt application, never a map.
export function compactContextInputs(features,bounds,expectedFootprints,{metadataApplication}={}) {
 if(!Array.isArray(features)||!Array.isArray(bounds)||features.length!==bounds.length||!features.length)
  throw Error('Complete original feature and owner inventories required');
 let referenceOwners=bounds;
 if(metadataApplication!==undefined){
  if(metadataApplication.manifest?.footprints_sha256!==expectedFootprints)
   throw Error('Selected context differs from original native footprint');
  referenceOwners=validateReferenceMetadataProjection({...metadataApplication,owners:bounds}).owners;
 }
 const owners=new Map(referenceOwners.map(owner=>[owner.id,owner]));
 if(owners.size!==bounds.length||bounds.some((owner,i)=>owner.index!==i+1||typeof owner.province_id!=='string'))
  throw Error('Complete explicit original owner/parent mapping required');
 if(referenceOwners.some((owner,i)=>owner.id!==bounds[i].id||owner.index!==bounds[i].index))
  throw Error('Current reference context changes original owner identity or index');
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
  scope:metadataApplication===undefined
   ?'Original native geometry and explicit identity/parent indices only; omitted metadata remains in untouched original files.'
   :'Original native geometry and stable owner indices with fully validated current reference parents; omitted metadata remains in untouched original files.'};
}
