import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {gzipSync,gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {spawnSync,execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
import {omitFixtureObjects} from './helpers/git-object-fixture.mjs';
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

test('accepted main directly advances A then B then code-only without any historical checkpoint',async t=>{
 const f=await trustedFixture(t,{nativeAppend:true,finalBank:true});
 const seed=await f.api.qualifyCheckpoint({reader:f.reader});
 const old=await oldBank(f,seed.state);f.api.releaseCheckpoint(seed.state);
 // One actual accepted source member locates the lazy owner. No old certificate
 // or candidate-authored geometry is used as its original geometry authority.
 const sourceWorld=f.selected;
 f.save('data/bank.json',{version:1,kind:'complete-world-index-with-exact-encoded-overrides',locations:old.features.length,world_index:f.pin('data/world-index.json',sourceWorld),
  release_id:f.selection.release_id,native_manifest_sha256:f.selection.sha256,
  footprints_sha256:f.manifest.footprints_sha256,unchanged_files:[f.pin('data/source.json',f.selected)],overrides:[]});
 const sourceAt=f.commit(),sourcePin=f.pin('data/bank.json',sourceAt);
 f.sidecar.base_selection={...f.sidecar.base_selection,selected_geography:{version:1,
  kind:'complete-world-index-with-exact-encoded-overrides',path:sourcePin.path,bytes:sourcePin.bytes,sha256:sourcePin.sha256}};
 let features=old.features.map(p=>finishEffectiveFootprint(p,valueSha)),ownership=old.ownership;
 const initial=await writeFinal(f,old.index,features,ownership);
 const forbidden=['data/selected-checkpoint.json','accepted/','accepted-rebind/','original/','data/registry.json','data/ledger.json','data/patch.json','data/sidecar.json','data/envelope.json'];
 const compare=async(base,candidate,options={})=>{
  const beforeReader=new f.native.ImmutableReader(f.root,base),afterReader=new f.native.ImmutableReader(f.root,candidate,{invocation:beforeReader.invocation});
  for(const reader of [beforeReader,afterReader]){
   const read=reader.read.bind(reader);reader.read=(name,...args)=>{
    assert(!forbidden.some(p=>name===p||p.endsWith('/')&&name.startsWith(p)),'Historical dependency read: '+name);
    if(options.fail===name)throw Error('Interrupted current member read');return read(name,...args);
   };
  }
  return f.api.compareAcceptedFinalBank({beforeReader,afterReader});
 };
 const add=async(prior,owner,name)=>{
  const added=await appendNativeAuthority(f,{owner,name,completedConstructor:true,membershipPath:'data/source.json'});
  f.save(name+'/only.json',{version:1,kind:'retained-rule-authority-registry-v1',entries:[added.entry]});
  const at=f.commit(),hook=f.pin(name+'/only.json',at);
  const components=added.proof.original_ledger.rows.filter(p=>p.disposition==='assigned').map(p=>({...nativeLiteral(p),authority_sha256:added.entry.authority_sha256,rule_sha256:added.entry.rule_sha256}));
  const previousFeatures=features,previousOwnership=ownership;
  features=features.map(p=>p.id!==f.features[owner].id?p:extendFinishedNativeFootprint({...p,geometry:p.geometry??components[0].base_geometry},components,valueSha));
  const words=mergeUnassignedNativeIntervals(ownership,added.proof.native_proof.native_patches[0].rows,{owners:new Set([1,2,3]),allowed:new Set([1,2,3])});
  ownership={...ownership,...words,runWords:words.runs.length};
  const next=await writeFinal(f,prior.index,features,ownership,hook);
  return {...next,added,hook,previousFeatures,previousOwnership};
 };
 const a=await add(initial,1,'repair-a');
 const first=await compare(initial.commit,a.commit);assert.equal(first.native_row_scope.added_cells,1);
 const b=await add(a,2,'repair-b');
 const second=await compare(a.commit,b.commit);assert.equal(second.native_row_scope.added_cells,1);
 assert.deepEqual(second.native_row_scope.changed_rows,[b.added.y]);
 // The historical hint may be stale or nonsense; it is not baseline authority.
 f.save('data/selected-checkpoint.json',{obsolete:'must not be read'});f.save('code-only.txt','ordinary code change');const code=f.commit();
 const unchanged=await compare(b.commit,code);assert.equal(unchanged.native_row_scope.added_cells,0);
 assert.deepEqual(unchanged.native_row_scope.changed_rows,[]);assert.equal(unchanged.checkpoint_custody.baseline_commit,b.commit);
 assert(!Object.hasOwn(unchanged.checkpoint_custody,'baseline_checkpoint'));
 await t.test('latest-only B cannot certify an A plus B delta against stale main',async()=>{
  await assert.rejects(compare(initial.commit,b.commit),/positive destinations differ from complete qualified source scope/);
 });
 await t.test('an unused proof pointer is provenance, not an instruction to alter the final map',async()=>{
  f.git('reset','--hard',b.commit);
  const sameMap=await writeFinal(f,b.index,b.previousFeatures,b.previousOwnership,b.hook);
  const report=await compare(a.commit,sameMap.commit);
  assert.deepEqual(report.changes,[]);assert.equal(report.added_cells,0);
 });
 await t.test('withdrawal compares current files without replaying the restored old hook',async()=>{
  const report=await compare(b.commit,a.commit);
  assert.equal(report.status,'validated-native-map-transition');assert.equal(report.removed_cells,1);
  assert.equal(report.added_cells,0);assert.equal(report.reassigned_cells,0);
  assert.deepEqual(report.changes,[{row:b.added.y,start:b.added.x,end:b.added.x+1,previous_owner:'C',candidate_owner:null}]);
  assert(!report.input_inventory.some(p=>p.path.includes('repair-a/')||p.path.includes('repair-b/')));
 });
 await t.test('one comparison handles mixed positive and withdrawal changes',async()=>{
  f.git('reset','--hard',b.commit);
  const cOnly=a.previousFeatures.map((p,i)=>i===2?features[i]:p);
  const cWords=mergeUnassignedNativeIntervals(a.previousOwnership,b.added.proof.native_proof.native_patches[0].rows,{owners:new Set([1,2,3]),allowed:new Set([1,2,3])});
  const current=await writeFinal(f,b.index,cOnly,{...a.previousOwnership,...cWords,runWords:cWords.runs.length},b.hook);
  const report=await compare(current.commit,a.commit);
  assert.equal(report.status,'validated-native-map-transition');assert.equal(report.added_cells,1);
  assert.equal(report.removed_cells,1);assert.equal(report.reassigned_cells,0);assert.equal(report.changes.length,2);
 });
 await t.test('coherent native context cannot hide its new cells outside declared bounds',async()=>{
  f.git('reset','--hard',a.commit);const bad=structuredClone(b.previousFeatures);bad[1].finishedFootprint.native_bounds=[0,0,0,0];
  const candidate=await writeFinal(f,a.index,bad,b.previousOwnership,a.hook);
  await assert.rejects(compare(initial.commit,candidate.commit),/bounds omit declared cells/);
 });
 await t.test('source-qualified reassignment corrects an accepted wrong owner without an unassigned intermediate',async()=>{
  f.git('reset','--hard',a.commit);
  const baselineFeatures=structuredClone(a.previousFeatures),component=a.added.proof.original_ledger.rows[0];
  const first=baselineFeatures[0].finishedFootprint;
  for(const row of component.native_rows){const existing=first.native_rows.find(p=>p.y===row.y);
   if(existing)existing.runs.push(...row.runs.map(([x,end])=>[x,end]));
   else first.native_rows.push({y:row.y,runs:row.runs.map(([x,end])=>[x,end])});}
  first.native_rows.sort((a,b)=>a.y-b.y);for(const row of first.native_rows)row.runs.sort((a,b)=>a[0]-b[0]);
  first.native_bounds=[-180,-90,180,90];
  const wrongRuns=Uint32Array.from(b.previousOwnership.runs),stride=2**ownership.coordinateBits;
  const rowStart=b.previousOwnership.rows[a.added.y*2],rowEnd=rowStart+b.previousOwnership.rows[a.added.y*2+1];
  for(let i=rowStart;i<rowEnd;i++)if(wrongRuns[i*2]%stride===a.added.x)wrongRuns[i*2]=stride+a.added.x;
  const wrong=await writeFinal(f,a.index,baselineFeatures,{...b.previousOwnership,runs:wrongRuns},a.hook);
  const report=await compare(wrong.commit,a.commit);
  assert.equal(report.status,'validated-native-map-transition');assert.equal(report.reassigned_cells,1);
  assert.equal(report.removed_cells,0);assert.equal(report.added_cells,0);
  assert.deepEqual(report.changes,[{row:a.added.y,start:a.added.x,end:a.added.x+1,previous_owner:'A',candidate_owner:'B'}]);
  assert.equal(report.repair_visibility.new_components,1);
 });
 await t.test('partly omitted positive source scope still refuses',async()=>{
  f.git('reset','--hard',initial.commit);
  const added=await appendNativeAuthority(f,{targetOwners:[1,2],name:'pair',completedConstructor:true,membershipPath:'data/source.json'});
  f.save('pair/only.json',{version:1,kind:'retained-rule-authority-registry-v1',entries:[added.entry]});const at=f.commit();
  // Only B is visible, although this new proof assigns B and C.
  const partial=await writeFinal(f,a.index,b.previousFeatures,b.previousOwnership,f.pin('pair/only.json',at));
  await assert.rejects(compare(initial.commit,partial.commit),/positive destinations differ from complete qualified source scope/);
 });
 await t.test('words without matching context and context without matching words both refuse',async()=>{
  f.git('reset','--hard',b.commit);
  const wordsOnly=await writeFinal(f,b.index,features,b.previousOwnership,a.hook);
  await assert.rejects(compare(b.commit,wordsOnly.commit),/words and exact finished-context changes differ/);
  const contextOnly=await writeFinal(f,b.index,b.previousFeatures,ownership,a.hook);
  await assert.rejects(compare(b.commit,contextOnly.commit),/words and exact finished-context changes differ/);
 });
 await t.test('unexplained third reassignment is rejected even with coherent bank hashes',async()=>{
  f.git('reset','--hard',b.commit);const runs=Uint32Array.from(ownership.runs),stride=2**ownership.coordinateBits;
  runs[0]=(Math.floor(runs[0]/stride)===3?2:3)*stride+runs[0]%stride;
  const changed=await writeFinal(f,b.index,features,{...ownership,runs},b.hook);
  await assert.rejects(compare(b.commit,changed.commit),/positive destinations differ from complete qualified source scope/);
 });
 await t.test('a held disposition cannot authorize otherwise coherent positive cells',async()=>{
  f.git('reset','--hard',b.commit);
  const constructed=JSON.parse(f.git('show',b.added.entry.completed_constructor.commit+':'+b.added.entry.completed_constructor.path));
  constructed.ledger_rows[0].disposition='held';f.save('held-constructor.json',constructed);const at=f.commit();
  f.save('held-registry.json',{version:1,kind:'retained-rule-authority-registry-v1',entries:[{...b.added.entry,completed_constructor:f.pin('held-constructor.json',at)}]});
  const registryAt=f.commit(),held=await writeFinal(f,b.index,features,ownership,f.pin('held-registry.json',registryAt));
  await assert.rejects(compare(a.commit,held.commit),/outside its assigned dispositions/);
 });
 await t.test('coherently rebound new lazy geometry must still match accepted N source',async()=>{
  f.git('reset','--hard',b.commit);
  const json=pin=>JSON.parse(f.git('show',pin.commit+':'+pin.path));
  const binding=json(b.added.entry.source_authority),evidence=json(binding.source_evidence),constructed=json(b.added.entry.completed_constructor);
  const geometry=structuredClone(evidence.targets[0].base_geometry);geometry.coordinates[0].forEach(point=>point[0]+=0.01);
  evidence.targets[0].base_geometry=geometry;f.save('forged/evidence.json',evidence);const ev=f.commit();
  binding.source_evidence=f.pin('forged/evidence.json',ev);
  const preimage={...binding,kind:'source-target-native-rule-v1'};
  f.save('forged/binding.json',binding);f.save('forged/rule.json',preimage);const bound=f.commit();
  const row=constructed.ledger_rows[0];row.base_geometry=geometry;row.base_geometry_sha256=valueSha(geometry);
  row.component_id='source-target:'+valueSha({target_id:row.target_id,evidence:binding.source_evidence.sha256});
  constructed.component_ids=[row.component_id];constructed.rule_sha256=valueSha(preimage);
  constructed.inputs.source_evidence={commit:binding.source_evidence.commit,path:binding.source_evidence.path};
  f.save('forged/constructed.json',constructed);const built=f.commit();
  const entry={policy_id:b.added.entry.policy_id,policy_version:1,rule_preimage:f.pin('forged/rule.json',bound),
   rule_sha256:valueSha(preimage),source_authority:f.pin('forged/binding.json',bound)};
  entry.authority_sha256=valueSha(entry);entry.completed_constructor=f.pin('forged/constructed.json',built);
  f.save('forged/registry.json',{version:1,kind:'retained-rule-authority-registry-v1',entries:[entry]});const issued=f.commit();
  const component={...row,authority_sha256:entry.authority_sha256,rule_sha256:entry.rule_sha256};
  const forgedFeatures=b.previousFeatures.map(p=>p.id!==row.target_id?p:extendFinishedNativeFootprint({...p,geometry},[component],valueSha));
  const forged=await writeFinal(f,b.index,forgedFeatures,ownership,f.pin('forged/registry.json',issued));
  await assert.rejects(compare(a.commit,forged.commit),/original reference geometry|original target identity\/geometry/);
 });
 await t.test('a coherent completed proof cannot attach a foreign target ID to an existing non-lazy owner',async()=>{
  f.git('reset','--hard',a.commit);
  const baselineFeatures=structuredClone(a.previousFeatures);baselineFeatures[1].geometry=f.features[1].geometry;
  const baseline=await writeFinal(f,a.index,baselineFeatures,a.previousOwnership);
  const json=pin=>JSON.parse(f.git('show',pin.commit+':'+pin.path));
  const binding=json(a.added.entry.source_authority),evidence=json(binding.source_evidence),constructed=json(a.added.entry.completed_constructor);
  evidence.targets[0].target_id='foreign-target';f.save('foreign/evidence.json',evidence);const ev=f.commit();
  binding.source_evidence=f.pin('foreign/evidence.json',ev);const preimage={...binding,kind:'source-target-native-rule-v1'};
  f.save('foreign/binding.json',binding);f.save('foreign/rule.json',preimage);const bound=f.commit();
  const row=constructed.ledger_rows[0];row.target_id='foreign-target';
  row.component_id='source-target:'+valueSha({target_id:row.target_id,evidence:binding.source_evidence.sha256});
  constructed.component_ids=[row.component_id];constructed.rule_sha256=valueSha(preimage);
  constructed.inputs.source_evidence={commit:binding.source_evidence.commit,path:binding.source_evidence.path};
  f.save('foreign/constructed.json',constructed);const built=f.commit();
  const entry={policy_id:a.added.entry.policy_id,policy_version:1,rule_preimage:f.pin('foreign/rule.json',bound),
   rule_sha256:valueSha(preimage),source_authority:f.pin('foreign/binding.json',bound)};
  entry.authority_sha256=valueSha(entry);entry.completed_constructor=f.pin('foreign/constructed.json',built);
  f.save('foreign/registry.json',{version:1,kind:'retained-rule-authority-registry-v1',entries:[entry]});const issued=f.commit();
  const candidate=await writeFinal(f,a.index,b.previousFeatures,b.previousOwnership,f.pin('foreign/registry.json',issued));
  await assert.rejects(compare(baseline.commit,candidate.commit),/Positive source target differs from the accepted owner identity/);
 });
 await t.test('interrupted body read cannot issue success and exact retry succeeds',async()=>{
  await assert.rejects(compare(a.commit,b.commit,{fail:root+'/'+b.index.pixelMap.parts.find(p=>p.kind==='runs').path}),/Interrupted/);
  const retry=await compare(a.commit,b.commit);assert.equal(retry.native_row_scope.added_cells,1);
 });
 await t.test('real joint CLI uses accepted main directly and emits no promotion product',()=>{
  const entry='coordination/engineering/selected-geography-effective-prevention-20261009/selected-joint-entry.mjs';
  for(const [base,candidate,added]of [[a.commit,b.commit,1],[b.commit,code,0],[b.commit,a.commit,0]]){
   f.git('reset','--hard',base);
   const destination=path.join(f.root,'unused-'+added),env={...process.env};delete env.NODE_OPTIONS;delete env.NODE_PATH;delete env.GH_TOKEN;
   const result=spawnSync(process.execPath,[path.join(f.root,entry),f.root,base,base,candidate,destination],{env,encoding:'utf8'});
   assert.equal(result.status,0,result.stderr);const report=JSON.parse(result.stdout);
   assert.equal(report.mode,'accepted-final-map-comparison-v1');assert.equal(report.derived_checkpoint,null);
   assert.equal(report.native.native_row_scope.added_cells,added);assert.equal(fs.existsSync(destination),false);
   assert(report.native.input_inventory.every(p=>!forbidden.some(name=>p.path===name||name.endsWith('/')&&p.path.startsWith(name))));
   assert(!result.stderr.includes('checkpoint-acquisition'));
  }
  f.git('reset','--hard',b.commit);
  const env={...process.env};delete env.NODE_OPTIONS;delete env.NODE_PATH;
  const refused=spawnSync(process.execPath,[path.join(f.root,entry),f.root,b.commit,a.commit,b.commit,path.join(f.root,'wrong-code')],{encoding:'utf8',env});
  assert.notEqual(refused.status,0);assert.match(refused.stderr,/must execute the accepted baseline checker/);
 });
 await t.test('cold current operands import exactly once while compatibility and previous repairs stay absent',()=>{
  f.git('reset','--hard',a.commit);
  const entry='coordination/engineering/selected-geography-effective-prevention-20261009/selected-joint-entry.mjs';
  const binding=JSON.parse(f.git('show',b.added.entry.source_authority.commit+':'+b.added.entry.source_authority.path));
  const inputs=[...a.index.pixelMap.parts,...a.index.preparedOwnership.context_parts].map(p=>f.pin(root+'/'+p.path,a.commit));
  inputs.push(...[...b.index.pixelMap.parts,...b.index.preparedOwnership.context_parts].map(p=>f.pin(root+'/'+p.path,b.commit)),
   b.hook,b.added.entry.rule_preimage,b.added.entry.source_authority,b.added.entry.completed_constructor,
   binding.source_evidence,binding.native_patch,sourcePin,f.pin('data/world-index.json',sourceWorld),f.pin('data/source.json',f.selected));
  const required=[...new Map(inputs.map(p=>[p.git_blob_oid,p])).values()];
  const compatibility=f.pin(root+'/'+b.index.compatibility_files.find(p=>p.path.endsWith('999.bin.gz')).path,b.commit);
  const omitted=[...required,compatibility,a.hook];
  const remote=fs.mkdtempSync(path.join(path.dirname(f.root),'.final-map-remote-'));t.after(()=>fs.rmSync(remote,{recursive:true,force:true}));
  execFileSync('git',['clone','--bare','--no-hardlinks',f.root,remote],{stdio:'ignore'});
  execFileSync('git',['-C',remote,'config','uploadpack.allowAnySHA1InWant','true']);
  execFileSync('git',['-C',remote,'config','uploadpack.allowFilter','true']);
  const url=pathToFileURL(remote).href,unavailable=pathToFileURL(path.join(remote,'absent')).href;
  f.git('config','url.'+unavailable+'.insteadOf','https://github.com/ChengshuLi/WorldAtlas.git');
  omitFixtureObjects(t,f.root,omitted.map(p=>p.git_blob_oid));
  const objects=()=>new Set(f.git('cat-file','--batch-all-objects','--batch-check=%(objectname)').toString().trim().split('\n'));
  const previous=objects(),env={...process.env,GH_TOKEN:''};delete env.NODE_OPTIONS;delete env.NODE_PATH;
  const run=(base,candidate)=>spawnSync(process.execPath,[path.join(f.root,entry),f.root,base,base,candidate,path.join(f.root,'no-product')],{encoding:'utf8',env});
  const refused=run(a.commit,b.commit);assert.notEqual(refused.status,0);assert.match(refused.stderr,/Geography object acquisition failed/);
  assert.equal(refused.stdout,'');assert(!fs.existsSync(path.join(f.root,'no-product')));assert.deepEqual([...objects()].sort(),[...previous].sort());
  f.git('config','--unset','url.'+unavailable+'.insteadOf');f.git('config','url.'+url+'.insteadOf','https://github.com/ChengshuLi/WorldAtlas.git');
  const cold=run(a.commit,b.commit);assert.equal(cold.status,0,cold.stderr);assert.equal(JSON.parse(cold.stdout).native.native_row_scope.added_cells,1);
  assert.deepEqual([...objects()].filter(id=>!previous.has(id)).sort(),required.map(p=>p.git_blob_oid).sort());
  assert.throws(()=>f.git('cat-file','-e',compatibility.git_blob_oid));assert.throws(()=>f.git('cat-file','-e',a.hook.git_blob_oid));
  f.git('config','--unset','url.'+url+'.insteadOf');f.git('config','url.'+unavailable+'.insteadOf','https://github.com/ChengshuLi/WorldAtlas.git');
  const warm=run(a.commit,b.commit);assert.equal(warm.status,0,warm.stderr);assert.deepEqual(JSON.parse(warm.stdout),JSON.parse(cold.stdout));
  t.diagnostic('Imported '+required.length+' current/new-evidence blobs, '+required.reduce((n,p)=>n+p.bytes,0)+' logical bytes; no compatibility or previous-authority body.');
 });
 f.git('reset','--hard',code);
});
