// Bounded actual pre-change/current transition comparison. Run at repository root.
// Every Git fixture is exclusively created by the shared test builder and removed
// in finally. Output is stdout; the caller chooses a fresh retained result path.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {valueBytes,valueSha} from '../selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
import {MODULE,sha,trustedFixture,appendNativeAuthority} from '../../../test/fixtures/selected-checkpoint.mjs';
const cleanups=[],t={after:fn=>cleanups.push(fn)};
try {
 const f=await trustedFixture(t,{nativeAppend:true});
 const next=await appendNativeAuthority(f),originalSource=execFileSync('git',['show','4aa52927bf61765cc462a2d0824fa5bce83df919:'+MODULE],{maxBuffer:33554433});
 async function run(api){
  const liveCaller=Buffer.alloc(65536,0x5a);
  const reader=new f.native.ImmutableReader(f.root,f.selected,{allowance:f.reader.allowance}),budget={shared:reader.budget,carriedBytes:1024+liveCaller.byteLength};
  const baseline=api.qualifyCheckpoint({reader,budget});
  const candidateReader=new f.native.ImmutableReader(f.root,next.candidate,{allowance:reader.allowance,budget:reader.budget});
  const transition=api.qualifyTransition({state:baseline.state,reader:candidateReader,budget});
  assert.equal(transition.available,true);
  const state=structuredClone(transition.candidate),provenance=state.accepted_execution;
  delete state.accepted_execution;
  api.projectSourceFeatures({state:transition.candidate,ids:[],budget});
  const metadata=candidateReader.metadataBytes;
  const source=api.projectSourceFeatures({state:transition.candidate,ids:['A','B','C'],budget});
  const native=api.projectNativeRows({state:transition.candidate,rows:[next.y],budget});
  const census=api.checkpointRouteCensus({transition,budget});
  const semantic={state,changedIds:transition.changedIds,changedNativeRows:transition.changedNativeRows,
   source:{features:source.features,inverse:source.inverse,inputs:source.inputs,custody:source.custody,state_binding:source.state_binding},
   native:{rows:native.rows,requested_rows:native.requested_rows,native_binding:native.native_binding,inputs:native.inputs,
    reused_rows:native.reused_rows,acquired_rows:native.acquired_rows,new_whole_inputs:native.custody.new_whole_inputs,
    retained_native_inputs:native.custody.retained_native_inputs},census};
  assert.equal(liveCaller.reduce((n,v)=>n+v,0),65536*0x5a);
  api.releaseCheckpoint(baseline.state);return {semantic,metadata,provenance};
 }
 const after=await run(f.api);
 f.save(MODULE,originalSource);f.commit();
 const beforeAPI=await import(pathToFileURL(path.join(f.root,MODULE)).href+'?before');
 const before=await run(beforeAPI);
 const {trusted_catalogue_commit:beforeCatalogue,...beforeOrigin}=before.provenance;
 const {trusted_catalogue_commit:afterCatalogue,...afterOrigin}=after.provenance;
 assert.deepEqual(afterOrigin,beforeOrigin);assert.notEqual(afterCatalogue,beforeCatalogue);
 assert.deepEqual(after.semantic,before.semantic);assert(valueBytes(after.semantic).equals(valueBytes(before.semantic)));
 const full={entry:next.entry,nativeOnly:true,patches:next.proof.native_proof.native_patches,ledger:next.proof.original_ledger,
  contract:next.proof.native_proof.native_contract,source_scope_ids:next.proof.source_scope_ids};
 const compact={entry:next.entry,nativeOnly:true,patches:next.proof.native_proof.native_patches};
 const expected=7*(valueBytes(full).length-valueBytes(compact).length);
 assert.equal(before.metadata-after.metadata,expected);
 console.log(JSON.stringify({kind:'actual-checkpoint-before-after',source_baseline:'4aa52927bf61765cc462a2d0824fa5bce83df919',
  old_source_sha256:sha(originalSource),new_source_sha256:sha(fs.readFileSync(MODULE)),
  fixture_source_sha256:sha(fs.readFileSync('test/fixtures/selected-checkpoint.mjs')),runner_source_sha256:sha(fs.readFileSync(fileURLToPath(import.meta.url))),semantic_output_sha256:valueSha(after.semantic),
  semantic_output_bytes:valueBytes(after.semantic).length,semantic_bytes_equal:true,genuine_caller_buffer_bytes:65536,complete_original_patch_sha256s:next.proof.native_proof.native_patches.map(valueSha),
  complete_metadata_charge_before:before.metadata,complete_metadata_charge_after:after.metadata,exact_retired_charge_bytes:expected,
  provenance_before:before.provenance,provenance_after:after.provenance,
  limits:['Synthetic ordinary-Git source/native fixture with one genuinely qualified cell, not Indonesia science or a production refusal replay.',
  'Distinct execution provenance and actual phase byte accounting are retained separately; no RSS or speedup saving is inferred.']} ,null,2));
} finally {for(const cleanup of cleanups.reverse())cleanup();}
