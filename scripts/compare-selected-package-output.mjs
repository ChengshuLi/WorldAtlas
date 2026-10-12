// One-time rollout proof: compare a genuine full build and assembled output for
// the same selected state. Never substitutes for live consumers.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
import {inventoryPackageOutput} from './package-output-artifact.mjs';
export function compareSelectedPackageOutput({full,assembled,originalHead,currentHead}) {
  assert.match(originalHead,/^[a-f0-9]{40}$/);assert.match(currentHead,/^[a-f0-9]{40}$/);
  const before=inventoryPackageOutput(full),after=inventoryPackageOutput(assembled);
  assert.deepEqual(before.files.map(row=>row.path),after.files.map(row=>row.path),'Complete output member sets differ');
  const atlas='dist/client/atlas-geography.json';let exactFiles=0,exactBytes=0;
  for(let index=0;index<before.files.length;index++){
    const a=before.files[index],b=after.files[index];
    if(a.path!==atlas){assert.deepEqual(a,b,'Output bytes differ: '+a.path);exactFiles++;exactBytes+=a.bytes;}
  }
  const read=root=>JSON.parse(fs.readFileSync(path.join(root,atlas)));
  const a=read(full),b=read(assembled);
  assert.equal(a.nativeContextInputStage?.current_execution?.source_head,currentHead,'Full output must record actual current build head');
  assert.equal(b.nativeContextInputStage?.current_execution?.source_head,originalHead,'Assembly must preserve original context head');
  // Only this provenance scalar differs. Runtime, complete code closure,
  // scientific counters and current additive descriptors must remain equal.
  a.nativeContextInputStage.current_execution.source_head=originalHead;
  assert.deepEqual(a,b,'Atlas content differs beyond preserved original source provenance');
  return {version:1,kind:'actual-full-versus-assembled-output-comparison',original_head:originalHead,current_head:currentHead,
    files:before.files.length,exact_byte_files:exactFiles,exact_bytes:exactBytes,atlas_semantic_equal:true,
    explicit_provenance_difference:'nativeContextInputStage.current_execution.source_head',
    limitation:'Source provenance is intentionally original; all other atlas fields and every other output byte match.'};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  assert.equal(process.argv.length,6,'Usage: node scripts/compare-selected-package-output.mjs FULL_ROOT ASSEMBLED_ROOT ORIGINAL_HEAD CURRENT_HEAD');
  console.log(JSON.stringify(compareSelectedPackageOutput({full:process.argv[2],assembled:process.argv[3],originalHead:process.argv[4],currentHead:process.argv[5]})));
}
