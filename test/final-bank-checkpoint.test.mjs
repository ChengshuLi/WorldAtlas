import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {gzipSync,gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {trustedFixture,appendNativeAuthority} from './fixtures/selected-checkpoint.mjs';
import {valueSha,valueBytes,coordinateBounds} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
import {nativeLiteral} from './helpers/native-literal.mjs';
import {unshuffleOwnershipBytes} from '../src/ownership-codec.js';
import {finalBankReference} from '../src/reference-metadata.js';
import {ownershipMetadata} from '../src/ownership-method.js';
import {finishEffectiveFootprint,extendFinishedNativeFootprint,mergeUnassignedNativeIntervals,finishedReleaseFootprintDigest} from '../src/native-grid.js';
import {packageFinalStartupOwnership} from '../scripts/package-startup-ownership.mjs';
import {prepareFinalBankStartupOwnership} from '../scripts/prepare-startup-ownership.mjs';
import {oldBank,writeFinal} from './fixtures/final-bank.mjs';
const root='data/canonical-grid/current-startup',hash=b=>createHash('sha256').update(b).digest('hex');
test('final-bank migration and second transition preserve the real lazy context and nonzero-y native append',async t=>{
 const f=await trustedFixture(t,{nativeAppend:true,finalBank:true});
 const seed=await f.api.qualifyCheckpoint({reader:f.reader});assert.equal(seed.available,true);
 const old=await oldBank(f,seed.state);f.api.releaseCheckpoint(seed.state);
 const reader=new f.native.ImmutableReader(f.root,f.bankCommit),baseline=await f.api.qualifyCheckpoint({reader});assert.equal(baseline.available,true);
 const features=old.features.map(p=>finishEffectiveFootprint(p,valueSha));assert.equal(features[1].geometry,null);
 const migration=await writeFinal(f,old.index,features,old.ownership);
 const transition=await f.api.qualifyTransition({state:baseline.state,reader:new f.native.ImmutableReader(f.root,migration.commit,{invocation:reader.invocation})});
 assert.equal(transition.available,true);assert.equal(transition.candidate.version,2);assert.equal(transition.changedNativeRows.length,0);
 assert.equal(transition.candidate.certificate.entries[1][8],transition.candidate.certificate.entries[1][7]);
 const added=await appendNativeAuthority(f,{owner:1,name:'new-native',completedConstructor:true});assert(added.y>0);
 f.save('new-native/only-registry.json',{version:1,kind:'retained-rule-authority-registry-v1',entries:[added.entry]});const evidenceCommit=f.commit(),hook=f.pin('new-native/only-registry.json',evidenceCommit);
 const components=added.proof.original_ledger.rows.filter(r=>r.disposition==='assigned').map(r=>({...nativeLiteral(r),authority_sha256:added.entry.authority_sha256,rule_sha256:added.entry.rule_sha256}));
 const nextFeatures=features.map(p=>p.id!==f.features[1].id?p:extendFinishedNativeFootprint({...p,geometry:components[0].base_geometry},components,valueSha));
 const words=mergeUnassignedNativeIntervals(old.ownership,added.proof.native_proof.native_patches[0].rows,{owners:new Set([1,2,3]),allowed:new Set([1,2,3])});
 const appended=await writeFinal(f,migration.index,nextFeatures,{...old.ownership,...words,runWords:words.runs.length},hook);
 const next=await f.api.qualifyTransition({state:transition.candidate,reader:new f.native.ImmutableReader(f.root,appended.commit,{invocation:reader.invocation})});
 assert.equal(next.available,true);assert.deepEqual(next.changedNativeRows,[added.y]);
 assert.deepEqual(next.changedIds,[f.features[1].id]);
 const unchanged=await f.api.qualifyTransition({state:next.candidate,reader:new f.native.ImmutableReader(f.root,appended.commit,{invocation:reader.invocation})});
 assert.equal(unchanged.available,true);assert.deepEqual(unchanged.changedIds,[]);assert.deepEqual(unchanged.changedNativeRows,[]);
 assert.deepEqual(unchanged.candidate.accepted_authorities,next.candidate.accepted_authorities);
 const normative=f.api.projectNativeRows({state:next.candidate,rows:[1,added.y]});
 assert.equal(normative.native_binding.manifest_sha256,f.selection.sha256);
 assert.deepEqual(normative.rows[1].runs,[],'Normative N must not silently become current E');
 const streamed=[];await f.api.visitNativeIntervals({state:next.candidate,rows:[1,added.y],visit:async row=>{
  const runs=[];for await(const run of row.runs)runs.push(run);streamed.push({y:row.y,runs});}});
 assert.deepEqual(streamed,normative.rows);
 const restore=()=>f.git('reset','--hard',appended.commit);
 const writeIndex=(index,selection=appended.selection)=>{
  const raw=valueBytes(index);f.save(root+'/index.json',index);f.save('data/ownership-selection.json',{...selection,
   prepared_bank:{path:root+'/index.json',bytes:raw.length,sha256:hash(raw)}});return f.commit();};
 const refuses=async(mutator,expression)=>{restore();const index=structuredClone(appended.index),selection=structuredClone(appended.selection);
  mutator(index,selection);const candidate=writeIndex(index,selection);
  await assert.rejects(f.api.qualifyTransition({state:next.candidate,reader:new f.native.ImmutableReader(f.root,candidate,{invocation:reader.invocation})}),expression);};
 await t.test('coherently shortened fixed compatibility roster refuses',()=>refuses(index=>{
  const old=index.compatibility_files.find(p=>p.path.endsWith('999.bin.gz'));
  index.compatibility_files=index.compatibility_files.filter(p=>p!==old);index.files=index.files.filter(p=>p.path!==old.path);fs.unlinkSync(path.join(f.root,root,old.path));
 },/accepted fixed compatibility roster/));
 await t.test('unchanged declarations cannot hide a rebound compatibility body',()=>refuses(index=>{
  const old=index.compatibility_files.find(p=>p.path.endsWith('999.bin.gz'));fs.writeFileSync(path.join(f.root,root,old.path),Buffer.from('different compatible body'));
 },/rebound an accepted compatibility body/));
 await t.test('runtime reference descriptor cannot self-declare a projection',()=>refuses(index=>{
  index.referenceMetadata={version:1,asset:{path:'forged',bytes:1,sha256:'a'.repeat(64)}};
 },/actual selected projection/));
 await t.test('coherent E header still must bind the consumed full word streams',()=>refuses((index,selection)=>{
  const proof=index.preparedOwnership;proof.rows_sha256='f'.repeat(64);
  const reference=finalBankReference(proof,index.pixelMap,finishedReleaseFootprintDigest(proof.base_reference,nextFeatures,valueSha),valueSha);
  proof.effective_reference=reference;selection.reference=reference;index.release_id=reference.id;index.footprints_sha256=reference.footprints_sha256;
  index.pixelMap.geographic_release=reference.id;index.pixelMap.footprints_sha256=reference.footprints_sha256;
 },/complete word stream differs/));
 await t.test('coherent finished bank cannot reassign an unrelated accepted cell',async()=>{
  restore();const changedRuns=Uint32Array.from(words.runs),stride=2**old.ownership.coordinateBits;
  const oldOwner=Math.floor(changedRuns[0]/stride),x=changedRuns[0]%stride;assert(oldOwner>0);
  changedRuns[0]=(oldOwner===3?2:3)*stride+x;
  const changed=await writeFinal(f,appended.index,nextFeatures,{...old.ownership,...words,runs:changedRuns,runWords:changedRuns.length},hook);
  await assert.rejects(f.api.qualifyTransition({state:next.candidate,reader:new f.native.ImmutableReader(f.root,changed.commit,{invocation:reader.invocation})}),/outside the qualified new intervals/);
 });
 await t.test('coherent finished context cannot hide an unrelated property change',async()=>{
  restore();const changedFeatures=structuredClone(nextFeatures);changedFeatures[0].properties.hidden='unqualified';
  const changed=await writeFinal(f,appended.index,changedFeatures,{...old.ownership,...words,runWords:words.runs.length},hook);
  await assert.rejects(f.api.qualifyTransition({state:next.candidate,reader:new f.native.ImmutableReader(f.root,changed.commit,{invocation:reader.invocation})}),/Final context changed outside/);
 });
 await t.test('changed evidence hook cannot repeat an accepted authority',async()=>{
  restore();f.save('new-native/repeated.json',{version:1,kind:'retained-rule-authority-registry-v1',entries:[added.entry]});const origin=f.commit(),pin=f.pin('new-native/repeated.json',origin);
  const candidate=writeIndex(appended.index,{...appended.selection,change_evidence:pin});
  await assert.rejects(f.api.qualifyTransition({state:next.candidate,reader:new f.native.ImmutableReader(f.root,candidate,{invocation:reader.invocation})}),/already accepted authority identity/);
 });
 restore();

});
