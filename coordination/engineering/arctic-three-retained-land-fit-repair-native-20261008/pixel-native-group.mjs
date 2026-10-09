import assert from 'node:assert/strict';
import {readAdmittedBody} from './phase-admission.mjs';
import {decodeInstalledWords} from './selected-native-inputs.mjs';
import {selectedOwnerRuns} from './pixel-area-order.mjs';

// A finished complete-word input group, not a cropped native computation.
export function pixelNativeGroup(admission, plan) {
 assert.equal(plan.kind,'complete-native-target-run-accounting-group');
 const manifest=JSON.parse(readAdmittedBody(admission,plan.manifest.path));
 assert.equal(manifest.size,262166);assert.equal(manifest.coordinateBits,19);
 assert.equal(manifest.runWords,57617774);
 const parts=manifest.parts.filter(p=>p.kind==='runs');
 assert.equal(parts.length,55);let offset=0;
 for(const part of parts){assert.equal(part.offset,offset);offset+=part.words;}
 assert.equal(offset,manifest.runWords);
 assert(Number.isSafeInteger(plan.ordinal)&&plan.ordinal>=0&&plan.ordinal<14);
 const expected=parts.slice(plan.ordinal*4,plan.ordinal*4+4);
 assert.equal(plan.parts.length,expected.length);
 const rows=decodeInstalledWords(admission,plan.rows);
 assert.equal(rows.length,manifest.size*2);let next=0;
 for(let y=0;y<manifest.size;y++){assert.equal(rows[2*y],next);next+=rows[2*y+1];}
 assert.equal(next*2,manifest.runWords);
 const results=[];
 for(let i=0;i<expected.length;i++) {
  const old=plan.parts[i].before,current=plan.parts[i].after;
  for(const key of ['kind','offset','words','bytes','sha256','decoded_bytes','decoded_sha256','encoding'])assert.equal(old[key],expected[i][key]);
  assert.equal(old.original_path,expected[i].path);
  assert.equal(current.offset,old.offset);assert.equal(current.words,old.words);
  const before=decodeInstalledWords(admission,old);
  const after=current.path===old.path?before:decodeInstalledWords(admission,current);
  if(current.path===old.path)for(const key of ['bytes','sha256','decoded_bytes','decoded_sha256'])assert.equal(current[key],old[key]);
  const options={offset:old.offset,size:manifest.size,coordinateBits:manifest.coordinateBits,owners:49625,targetOwners:[6666,6757]};
  results.push({offset:old.offset,words:old.words,before:selectedOwnerRuns(rows,before,options),after:selectedOwnerRuns(rows,after,options),
   original_encoded_sha256:old.sha256,current_encoded_sha256:current.sha256,original_canonical_sha256:old.decoded_sha256,current_canonical_sha256:current.decoded_sha256});
 }
 return {version:1,kind:plan.kind,ordinal:plan.ordinal,total_groups:14,full_run_parts:55,full_row_count:262166,
  owner_count:49625,total_run_words:57617774,target_owners:[6666,6757],parts:results,grid_rows_computed:0,activated:false};
}
