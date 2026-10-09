// Pure metadata continuation. Every old compressed asset remains separately retained.
import assert from 'node:assert/strict';
export const OLD_NATIVE_SHA='a71edb65cbd7986e245f626e8a34b70e12c12d081ca24fc936bdd84e1bb07885';
export const OLD_FOOTPRINT='b9a3c8bf375217dba3a50d1a022ec7e4ac6c6f1cdedff22845da953c805b7433';
export const NEW_FOOTPRINT='2deeff1457ff9238cb3dbe599e9a858dcce29d8ba88e2a66abe2785ddec0aed9';
const offsets=[1048576,3145728];
const qualified=new Map([[1048576,{bytes:999496,sha256:'fceeec44661182bb9344083dd8aefee195d521b982619602f55a4c4e21f84ce7',decoded_sha256:'f52a0988fd97fb763e971e801beeead98750b07d3a91203c001b16fd19ccb703'}],[3145728,{bytes:903226,sha256:'51a2e4a95b922856870e644fcf1c2ec6685fc36d49a1ad684708d6df8e42b47b',decoded_sha256:'7592fb5201a5fc0dc3624708a2bd6ffabca5b84e1d68023955a1b77fc96ad511'}]]);
export function continueNativeManifest(original,{originalSha,replacements,selectedProof,footprints,releaseId}){
 assert.equal(originalSha,OLD_NATIVE_SHA);assert.equal(original.footprints_sha256,OLD_FOOTPRINT);
 assert.equal(original.version,2);assert.equal(original.method,'native-linear-evenodd-first-owner-v1');
 assert.equal(original.size,262166);assert.equal(original.coordinateBits,19);assert.equal(original.runWords,57617774);
 assert.equal(original.parts.length,56);assert.equal(original.parts.filter(p=>p.kind==='runs').length,55);
 assert.equal(original.parts.filter(p=>p.kind==='rows').length,1);
 assert.equal(new Set(original.parts.map(p=>p.path)).size,56);
 assert.deepEqual(original.accounting,{checked_rows:262166,checked_cells:68731011556,unchecked_cells:0,owned_cells:13854401485,owners:49625});
 assert.equal(selectedProof.kind,'exact-selected-native-old-new-counterparty-proof');assert.equal(selectedProof.checked_rows,60);assert.equal(selectedProof.unchanged_rows,262106);assert.equal(selectedProof.full_owner_count,49625);assert.equal(selectedProof.added_cells,141);assert.equal(selectedProof.removed_cells,0);assert.equal(selectedProof.reassigned_cells,0);
 assert.equal(footprints.original_footprints_sha256,OLD_FOOTPRINT);assert.equal(footprints.current_footprints_sha256,NEW_FOOTPRINT);
 assert.equal(typeof releaseId,'string');assert(/^geography:review:[a-f0-9]{64}$/.test(releaseId));assert.notEqual(releaseId,original.geographic_release);
 assert.equal(replacements.length,2);assert.deepEqual(replacements.map(p=>p.offset).sort((a,b)=>a-b),offsets);
 const parts=original.parts.map(part=>{
  const replacement=replacements.find(p=>p.offset===part.offset&&part.kind==='runs');
  if(!replacement)return part;
  assert.equal(replacement.kind,'runs');assert.equal(replacement.words,part.words);assert.equal(replacement.decoded_bytes,part.decoded_bytes);
  assert.equal(replacement.path,part.path);assert.equal(replacement.encoding,part.encoding);
  for(const key of ['bytes','sha256','decoded_sha256'])assert.equal(replacement[key],qualified.get(part.offset)[key],'Qualified whole replacement differs');
  assert(Number.isSafeInteger(replacement.bytes)&&replacement.bytes>0&&replacement.bytes<=32*1024*1024);
  return {...part,...replacement};
 });
 assert.equal(parts.filter((p,i)=>p===original.parts[i]).length,54);
 return {...original,footprints_sha256:NEW_FOOTPRINT,geographic_release:releaseId,parts,
  accounting:{...original.accounting,owned_cells:original.accounting.owned_cells+141},
  provenance:{...original.provenance,retained_predecessor_manifest_sha256:OLD_NATIVE_SHA,successor_continuation:{issue:1520,complete_owners:49625,selected_old_new_rows:60,reused_rows:262106,added_cells:141,removed_cells:0,reassigned_cells:0,old_compressed_bodies_retained:true,whole_world_kernel_reexecuted:false}},scientific_approval:false,installation_ready:false};
}
