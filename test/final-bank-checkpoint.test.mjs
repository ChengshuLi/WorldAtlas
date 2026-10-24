import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {gzipSync,gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {spawnSync,execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
import {omitFixtureObjects} from './helpers/git-object-fixture.mjs';
import {trustedFixture,appendNativeAuthority} from './fixtures/selected-checkpoint.mjs';
import {valueSha,valueBytes,coordinateBounds,projectCompletedGeometryBody,restoreCompletedGeometryBody} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
import {nativeLiteral} from './helpers/native-literal.mjs';
import {unshuffleOwnershipBytes} from '../src/ownership-codec.js';
import {finalBankReference} from '../src/reference-metadata.js';
import {ownershipMetadata} from '../src/ownership-method.js';
import {finishEffectiveFootprint,extendFinishedNativeFootprint,mergeUnassignedNativeIntervals,finishedReleaseFootprintDigest} from '../src/native-grid.js';
import {packageFinalStartupOwnership} from '../scripts/package-startup-ownership.mjs';
import {prepareFinalBankStartupOwnership} from '../scripts/prepare-startup-ownership.mjs';
import {oldBank,writeFinal} from './fixtures/final-bank.mjs';
const root='data/canonical-grid/current-startup',hash=b=>createHash('sha256').update(b).digest('hex');
test('accepted main directly advances A then B then code-only without any historical checkpoint',async t=>{
 const f=await trustedFixture(t,{nativeAppend:true,finalBank:true,omitLatitudeFields:['mode','git_blob_oid']});
 const old=await oldBank(f);
 // One actual accepted source member locates the lazy owner. No old certificate
 // or candidate-authored geometry is used as its original geometry authority.
 const sourceWorld=f.selected;
 const historicalPin=(name,at)=>{const p=f.pin(name,at);delete p.mode;delete p.git_blob_oid;return p;};
 f.save('data/bank.json',{version:1,kind:'complete-world-index-with-exact-encoded-overrides',locations:old.features.length,world_index:historicalPin('data/world-index.json',sourceWorld),
  release_id:f.selection.release_id,native_manifest_sha256:f.selection.sha256,
  footprints_sha256:f.manifest.footprints_sha256,unchanged_files:[historicalPin('data/source.json',f.selected)],overrides:[]});
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
 await assert.rejects(compare(f.selected,initial.commit),/requires accepted and proposed final banks/);
 const a=await add(initial,1,'repair-a');
 const first=await compare(initial.commit,a.commit);assert.equal(first.native_row_scope.added_cells,1);
 const b=await add(a,2,'repair-b');
 const second=await compare(a.commit,b.commit);assert.equal(second.native_row_scope.added_cells,1);
 assert.deepEqual(second.native_row_scope.changed_rows,[b.added.y]);

 await t.test('typed geometry custody reconstructs exact private originals from accepted N',async t=>{
  f.git('reset','--hard',a.commit);
  const originalRegistry=JSON.parse(f.git('show',a.hook.commit+':'+a.hook.path));
  const binding=JSON.parse(f.git('show',a.added.entry.source_authority.commit+':'+a.added.entry.source_authority.path));
  const beforeReader=new f.native.ImmutableReader(f.root,initial.commit);
  const projected=await f.api.projectCompletedAuthorityRegistry({beforeReader,registry:originalRegistry,
    readOriginal:p=>f.git('show',p.commit+':'+p.path)});
  const originals=[a.added.entry.completed_constructor,binding.source_evidence];
  assert.equal(projected.completed_geometry_custody.length,1);
  for(const role of ['completed_constructor','source_evidence']){
    const part=projected.completed_geometry_custody[0][role];
    assert(part.slots.length>0);
    assert((part.body[role==='source_evidence'?'targets':'ledger_rows']).every(row=>!Object.hasOwn(row,'base_geometry')));
  }
  const commitProjection=mutation=>{
    f.git('reset','--hard',a.commit);const registry=structuredClone(projected);mutation?.(registry);
    f.save('projected-registry.json',registry);const at=f.commit();
    f.save('data/ownership-selection.json',{...a.selection,change_evidence:f.pin('projected-registry.json',at)});
    for(const p of originals)fs.unlinkSync(path.join(f.root,p.path));
    return f.commit();
  };
  const compareProjection=async candidate=>{
    const beforeReader=new f.native.ImmutableReader(f.root,initial.commit),afterReader=new f.native.ImmutableReader(f.root,candidate,{invocation:beforeReader.invocation});
    for(const r of [beforeReader,afterReader])for(const method of ['read','stream']){
      const original=r[method].bind(r);r[method]=(name,...args)=>{
        assert(!originals.some(p=>p.path===name),'Projected proof must not reopen the full private original');return original(name,...args);
      };
    }
    return f.api.compareAcceptedFinalBank({beforeReader,afterReader});
  };
  const candidate=commitProjection();const report=await compareProjection(candidate);
  assert.equal(report.native_row_scope.added_cells,1);assert.equal(report.completed_geometry_custody.length,1);
  assert.deepEqual(report.completed_geometry_custody[0].originals,originals);
  assert(report.input_inventory.some(p=>p.path==='data/source.json'&&p.whole_body_consumed));
  const cold=async(name,omitted,expected)=>t.test(name,async t=>{
    const clone=fs.mkdtempSync(path.join(os.tmpdir(),'projected-proof-cold-'));t.after(()=>fs.rmSync(clone,{recursive:true,force:true}));
    fs.cpSync(f.root,clone,{recursive:true});omitFixtureObjects(t,clone,[...new Set(omitted)]);
    const beforeReader=new f.native.ImmutableReader(clone,initial.commit),afterReader=new f.native.ImmutableReader(clone,candidate,{invocation:beforeReader.invocation});
    const run=()=>f.api.compareAcceptedFinalBank({beforeReader,afterReader});
    if(expected)await assert.rejects(run(),expected);else {
      assert.equal((await run()).native_row_scope.added_cells,1);
      execFileSync('git',['-C',clone,'reset','--hard',initial.commit],{stdio:'ignore'});
      const env={...process.env};delete env.NODE_PATH;delete env.NODE_OPTIONS;delete env.GH_TOKEN;
      const entry=path.join(clone,'coordination/engineering/selected-geography-effective-prevention-20261009/selected-joint-entry.mjs');
      const result=spawnSync(process.execPath,[entry,clone,initial.commit,initial.commit,candidate,path.join(clone,'no-checkpoint')],{env,encoding:'utf8',timeout:30000});
      assert.equal(result.status,0,result.stderr);const report=JSON.parse(result.stdout);
      assert.equal(report.native.native_row_scope.added_cells,1);assert.equal(report.native.completed_geometry_custody.length,1);
    }
  });
  await cold('known original commits with both private artifact bodies absent',originals.map(p=>p.git_blob_oid));
  await cold('absent private origin commits and bodies',originals.flatMap(p=>[p.commit,p.git_blob_oid]));
  const acceptedSource=f.pin('data/source.json',sourceWorld);
  await cold('candidate geometry cannot replace unavailable accepted N',[acceptedSource.git_blob_oid],new RegExp(acceptedSource.git_blob_oid));
  const bad=[
    ['retained source field',r=>r.completed_geometry_custody[0].source_evidence.body.base_reference.id+='x',/original (whole byte identity|byte size)/],
    ['geometry hash',r=>r.completed_geometry_custody[0].source_evidence.slots[0].base_geometry_sha256='0'.repeat(64),/geometry hash/],
    ['owner',r=>r.completed_geometry_custody[0].source_evidence.slots[0].pixelIndex++,/slot/],
    ['target',r=>r.completed_geometry_custody[0].source_evidence.slots[0].target_id='foreign',/slot/],
    ['missing slot',r=>r.completed_geometry_custody[0].source_evidence.slots=[],/slots/],
    ['duplicate slot',r=>r.completed_geometry_custody[0].source_evidence.slots.push(r.completed_geometry_custody[0].source_evidence.slots[0]),/slots/],
    ['foreign slot field',r=>r.completed_geometry_custody[0].source_evidence.slots[0].path='targets/0/other',/slot/],
    ['retained geometry',r=>r.completed_geometry_custody[0].source_evidence.body.targets[0].base_geometry=f.features[1].geometry,/slot/],
    ['wrong original pin',r=>r.completed_geometry_custody[0].source_evidence.original.sha256='0'.repeat(64),/source pin differs/],
    ['known original mode',r=>{r.entries[0].completed_constructor.mode='100755';r.completed_geometry_custody[0].completed_constructor.original.mode='100755';},/Known completed geometry origin differs/],
    ['known original path',r=>{r.entries[0].completed_constructor.path='absent.json';r.completed_geometry_custody[0].completed_constructor.original.path='absent.json';},/Known completed geometry origin differs/],
    ['known original OID',r=>{r.entries[0].completed_constructor.git_blob_oid='0'.repeat(40);r.completed_geometry_custody[0].completed_constructor.original.git_blob_oid='0'.repeat(40);},/Known completed geometry origin differs/],
    ['original reconstructed size',r=>{r.entries[0].completed_constructor.bytes++;r.completed_geometry_custody[0].completed_constructor.original.bytes++;},/whole byte identity/],

    ['unused authority',r=>r.completed_geometry_custody[0].authority_sha256='f'.repeat(64),/custody/],
    ['duplicate authority',r=>r.completed_geometry_custody.push(r.completed_geometry_custody[0]),/custody/],
    ['unknown role',r=>r.completed_geometry_custody[0].native_patch={},/custody/],
    ['foreign original source path',r=>r.completed_geometry_custody[0].source_evidence.body.source_membership.parts[0].path='data/foreign.json',/outside accepted original N/]
  ];
  for(const [name,change,reason]of bad)await t.test(name,()=>assert.rejects(compareProjection(commitProjection(change)),reason));
  f.git('reset','--hard',b.commit);
 });

 const mutateIndex=async(name,mutator,expression)=>t.test(name,async()=>{
  f.git('reset','--hard',b.commit);const index=structuredClone(b.index),selection=structuredClone(b.selection);
  mutator(index,selection);const raw=valueBytes(index);f.save(root+'/index.json',index);
  f.save('data/ownership-selection.json',{...selection,prepared_bank:{path:root+'/index.json',bytes:raw.length,sha256:hash(raw)}});
  await assert.rejects(compare(b.commit,f.commit()),expression);
 });
 await mutateIndex('coherently shortened compatibility roster refuses',index=>{
  const old=index.compatibility_files.find(p=>p.path.endsWith('999.bin.gz'));
  index.compatibility_files=index.compatibility_files.filter(p=>p!==old);index.files=index.files.filter(p=>p.path!==old.path);fs.unlinkSync(path.join(f.root,root,old.path));
 },/accepted fixed compatibility roster/);
 await mutateIndex('unchanged descriptors cannot hide rebound compatibility bytes',index=>{
  fs.writeFileSync(path.join(f.root,root,index.compatibility_files.find(p=>p.path.endsWith('999.bin.gz')).path),'changed');
 },/rebound an accepted compatibility body/);
 await mutateIndex('runtime reference cannot self-declare a projection',index=>{
  index.referenceMetadata={version:1,asset:{path:'forged',bytes:1,sha256:'a'.repeat(64)}};
 },/actual selected projection/);
 await mutateIndex('coherent E header must bind whole word streams',(index,selection)=>{
  const proof=index.preparedOwnership;proof.rows_sha256='f'.repeat(64);
  const reference=finalBankReference(proof,index.pixelMap,finishedReleaseFootprintDigest(proof.base_reference,features,valueSha),valueSha);
  proof.effective_reference=reference;selection.reference=reference;index.release_id=reference.id;index.footprints_sha256=reference.footprints_sha256;
  index.pixelMap.geographic_release=reference.id;index.pixelMap.footprints_sha256=reference.footprints_sha256;
 },/complete word stream differs/);
 await t.test('coherent context cannot change unrelated properties',async()=>{
  f.git('reset','--hard',b.commit);const altered=structuredClone(features);altered[0].properties.hidden='unqualified';
  const candidate=await writeFinal(f,b.index,altered,ownership,b.hook);
  await assert.rejects(compare(b.commit,candidate.commit),/unrelated owner\/reference properties/);
 });
 f.git('reset','--hard',b.commit);
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
 await t.test('final positive evidence without a completed constructor cannot reopen historical qualification',async()=>{
  f.git('reset','--hard',b.commit);
  const {completed_constructor,...entry}=b.added.entry;
  f.save('incomplete/registry.json',{version:1,kind:'retained-rule-authority-registry-v1',entries:[entry]});
  const issued=f.commit(),candidate=await writeFinal(f,b.index,features,ownership,f.pin('incomplete/registry.json',issued));
  await assert.rejects(compare(a.commit,candidate.commit,{fail:entry.source_authority.path}),/require completed native source-target authority/);
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
 await t.test('cold joint entry acquires only current exact headers and bodies; denial and retry retain custody',()=>{
  f.git('reset','--hard',a.commit);
  const entry='coordination/engineering/selected-geography-effective-prevention-20261009/selected-joint-entry.mjs';
  const binding=JSON.parse(f.git('show',b.added.entry.source_authority.commit+':'+b.added.entry.source_authority.path));
  const inputs=[...a.index.pixelMap.parts,...a.index.preparedOwnership.context_parts].map(p=>f.pin(root+'/'+p.path,a.commit));
  inputs.push(...[...b.index.pixelMap.parts,...b.index.preparedOwnership.context_parts].map(p=>f.pin(root+'/'+p.path,b.commit)),
   b.hook,b.added.entry.rule_preimage,b.added.entry.source_authority,b.added.entry.completed_constructor,
   binding.source_evidence,binding.native_patch,sourcePin,f.pin('data/world-index.json',sourceWorld),f.pin('data/source.json',f.selected));
  const headers=[f.pin('data/ownership-selection.json',a.commit),f.pin('data/ownership-selection.json',b.commit),
   f.pin(root+'/index.json',a.commit),f.pin(root+'/index.json',b.commit),f.pin(f.selection.manifest_path,a.commit)];
  inputs.push(...headers);
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
  // The only test seam is the provider metadata response. All source modules,
  // native object acquisition, execution identity and comparison are unchanged.
  const directories=[...new Set(headers.map(p=>f.git('rev-parse',p.commit+':'+path.posix.dirname(p.path)).toString().trim()))];
  const driver=path.join(f.root,'cold-joint-driver.mjs');
  fs.writeFileSync(driver,`import fs from 'node:fs';import assert from 'node:assert/strict';import {execFileSync} from 'node:child_process';
const calls=[];globalThis.fetch=async(url,options)=>{const u=new URL(url),match=/^\\/repos\\/ChengshuLi\\/WorldAtlas\\/git\\/trees\\/([a-f0-9]{40})$/.exec(u.pathname);
 assert.equal(u.origin,'https://api.github.com');assert.equal(u.search,'');assert(match);assert(${JSON.stringify(directories)}.includes(match[1]));
 assert(!options.headers.Authorization&&!options.headers.authorization);calls.push(match[1]);
 if(process.env.FIXTURE_DENY_METADATA==='1')return new Response('{}',{status:403});
 const raw=execFileSync('git',['-C',${JSON.stringify(remote)},'ls-tree','-l','-z',match[1]],{env:{...process.env,GIT_NO_LAZY_FETCH:'1',GIT_NO_REPLACE_OBJECTS:'1'}}).toString();
 const tree=raw.split('\\0').filter(Boolean).map(line=>{const [,mode,type,sha,size,path]=line.match(/^(\\d+) (\\w+) ([a-f0-9]+)\\s+(\\d+|-)\\t(.+)$/s);return {mode,type,sha,path,...(type==='blob'?{size:Number(size)}:{})};});
 return new Response(JSON.stringify({sha:match[1],truncated:false,tree}),{status:200});};
const {selectedJointStage}=await import(${JSON.stringify(pathToFileURL(path.join(f.root,entry)).href)});
const [base,candidate,destination]=process.argv.slice(2);
const report=await selectedJointStage(${JSON.stringify(f.root)},base,base,candidate,destination);
console.log(JSON.stringify({report,metadata_requests:calls}));`);
  const run=(base,candidate,extra={})=>spawnSync(process.execPath,[driver,base,candidate,path.join(f.root,'no-product')],{encoding:'utf8',env:{...env,...extra}});
  const denied=run(a.commit,b.commit,{FIXTURE_DENY_METADATA:'1'});
  assert.notEqual(denied.status,0);assert.match(denied.stderr,/Geography tree metadata unavailable .*HTTP 403/);
  assert.equal(denied.stdout,'');assert(!fs.existsSync(path.join(f.root,'no-product')));assert.deepEqual([...objects()].sort(),[...previous].sort());
  const refused=run(a.commit,b.commit);assert.notEqual(refused.status,0);assert.match(refused.stderr,/Geography object acquisition failed/);
  assert.equal(refused.stdout,'');assert(!fs.existsSync(path.join(f.root,'no-product')));assert.deepEqual([...objects()].sort(),[...previous].sort());
  f.git('config','--unset','url.'+unavailable+'.insteadOf');f.git('config','url.'+url+'.insteadOf','https://github.com/ChengshuLi/WorldAtlas.git');
  const cold=run(a.commit,b.commit);assert.equal(cold.status,0,cold.stderr);assert.equal(JSON.parse(cold.stdout).report.native.native_row_scope.added_cells,1);
  assert.deepEqual([...new Set(JSON.parse(cold.stdout).metadata_requests)].sort(),directories.sort());
  assert.deepEqual([...objects()].filter(id=>!previous.has(id)).sort(),required.map(p=>p.git_blob_oid).sort());
  assert.throws(()=>f.git('cat-file','-e',compatibility.git_blob_oid));assert.throws(()=>f.git('cat-file','-e',a.hook.git_blob_oid));
  f.git('config','--unset','url.'+url+'.insteadOf');f.git('config','url.'+unavailable+'.insteadOf','https://github.com/ChengshuLi/WorldAtlas.git');
  const warm=run(a.commit,b.commit);assert.equal(warm.status,0,warm.stderr);assert.deepEqual(JSON.parse(warm.stdout).report,JSON.parse(cold.stdout).report);
  assert.deepEqual(JSON.parse(warm.stdout).metadata_requests,[]);
  t.diagnostic('Imported '+required.length+' current/new-evidence blobs, '+required.reduce((n,p)=>n+p.bytes,0)+' logical bytes; no compatibility or previous-authority body.');
 });
 f.git('reset','--hard',code);
});

async function historicalDescriptorFixture(t,options={}) {
 const f=await trustedFixture(t,{nativeAppend:true,finalBank:true,
  omitLatitudeFields:['mode','git_blob_oid'],...options});
 const old=await oldBank(f),features=old.features.map(p=>finishEffectiveFootprint(p,valueSha));
 // Two accepted synthetic final banks differ by a one-cell withdrawal. Keeping
 // one native cell forces the comparator to authenticate the original lattice;
 // an unchanged-bank comparison would never exercise its bounds reader.
 const y=Math.floor(f.manifest.size/2),x=y;
 const bank=async(count,prior)=>{
  const context=structuredClone(features);
  context[0].finishedFootprint.native_rows=[{y,runs:[[x,x+count]]}];
  context[0].finishedFootprint.native_bounds=[-180,-90,180,90];
  const words=mergeUnassignedNativeIntervals(old.ownership,[{y,runs:[[x,x+count,1]]}],{owners:new Set([1,2,3]),allowed:new Set([1,2,3])});
  return writeFinal(f,prior,context,{...old.ownership,...words,runWords:words.runs.length});
 };
 const baseline=await bank(2,old.index),initial=await bank(1,baseline.index);
 const compare=(version=initial.commit,configure=()=>{})=>{
  const beforeReader=new f.native.ImmutableReader(f.root,baseline.commit),afterReader=new f.native.ImmutableReader(f.root,version,{invocation:beforeReader.invocation});
  const callbacks=configure(beforeReader,afterReader)??{};
  return f.api.compareAcceptedFinalBank({beforeReader,afterReader,...callbacks});
 };
 return {...f,initial,compare};
}

test('final-bank admission and comparison preserve historical body descriptor identities',async t=>{
 for(const omitted of [['mode','git_blob_oid'],['mode'],['git_blob_oid']])await t.test('missing '+omitted.join('/'),async t=>{
  const f=await historicalDescriptorFixture(t,{omitLatitudeFields:omitted,latitudePinChanges:{role:'immutable-normative-rule-input'}});
  const original=structuredClone(f.manifest.native_latitudes),report=await f.compare();
  assert.equal(report.native_row_scope.added_cells,0);assert.equal(report.removed_cells,1);assert.deepEqual(f.manifest.native_latitudes,original);
 });
 const cases=[
  ['contradictory supplied OID',{omitLatitudeFields:['mode'],latitudePinChanges:{git_blob_oid:'0'.repeat(40)}},/original mode\/OID differs/],
  ['contradictory supplied mode',{omitLatitudeFields:['git_blob_oid'],latitudePinChanges:{mode:'100755'}},/original mode\/OID differs/],
  ['explicit missing mode is malformed',{latitudePinChanges:{mode:null}},/Incomplete immutable checkpoint pin/],
  ['missing mandatory encoded size',{omitLatitudeFields:['mode','git_blob_oid','bytes']},/Native ownership rule input is missing or incompatible/],
  ['wrong encoded size',{latitudePinChanges:{bytes:1}},/whole mode\/OID\/size|whole size/],
  ['wrong encoded hash',{latitudePinChanges:{sha256:'0'.repeat(64)}},/Prepared startup native latitude differs/],
  ['wrong decoded size',{latitudePinChanges:{decoded_bytes:8}},/Native ownership rule input is missing or incompatible/],
  ['wrong decoded hash',{latitudePinChanges:{decoded_sha256:'0'.repeat(64)}},/Native ownership rule input is missing or incompatible/],
  ['missing decoded size',{omitLatitudeFields:['mode','git_blob_oid','decoded_bytes']},/Native ownership rule input is missing or incompatible/],
  ['symlink original',{latitudeSymlink:true},/Missing ordinary original checkpoint path/],
  ['missing original path',{latitudePinChanges:{path:'original/missing-latitudes.gz'}},/Native ownership rule input is missing or incompatible/]
 ];
 // Invalid normative headers may be refused by the unchanged bank admission
 // guard before comparison; neither construction nor comparison may accept them.
 for(const [name,options,pattern]of cases)await t.test(name,async t=>{
  await assert.rejects(async()=>{const f=await historicalDescriptorFixture(t,options);await f.compare();},pattern);
 });
});

test('historical descriptor acquisition authenticates cold original objects, never a changed current alias',async t=>{
 for(const absentOrigin of [false,true])await t.test(absentOrigin?'private absent origin with differing current alias':'known origin with absent body',async t=>{
  const f=await historicalDescriptorFixture(t),p=f.manifest.native_latitudes,raw=f.git('show',p.commit+':'+p.path),oid=f.git('rev-parse',p.commit+':'+p.path).toString().trim();
  const remote=path.join(f.root,'original-remote.git');execFileSync('git',['clone','--bare','--no-hardlinks',f.root,remote],{stdio:'pipe'});
  for(const key of ['uploadpack.allowFilter','uploadpack.allowAnySHA1InWant'])execFileSync('git',['-C',remote,'config',key,'true']);
  f.save(p.path,Buffer.from('Different current alias must never authenticate original latitude bytes\n'));const current=f.commit();
  omitFixtureObjects(t,f.root,[oid,...(absentOrigin?[p.commit]:[])]);
  const execute=(command,args,options)=>execFileSync(command,args.map(arg=>arg==='https://github.com/ChengshuLi/WorldAtlas.git'?'file://'+remote:arg),options);
  if(absentOrigin){
   await assert.rejects(f.compare(current,before=>{
    const original=before.acquireOriginalPaths.bind(before);
    before.acquireOriginalPaths=pins=>original(pins,{execute:(command,args,options)=>{
     if(args.includes('fetch'))throw Error('Fixture unavailable original origin');
     return execFileSync(command,args,options);
    }});
    return {acquireAuthorityInputs:async(reader,pins)=>{for(const pin of pins){assert.notEqual(pin.path,p.path,'An incomplete original pin must not use the current alias transport');await reader.acquirePinned(pin);}}};
   }),/Immutable origin object fetch failed/);
   assert.throws(()=>f.git('--no-lazy-fetch','cat-file','-e',p.commit+'^{commit}'));
   assert.throws(()=>f.git('--no-lazy-fetch','cat-file','-e',oid));
  }
  let normalized=0,privateOrigins=0;
  const report=await f.compare(current,before=>{
   const original=before.acquireOriginalPaths.bind(before);
   before.acquireOriginalPaths=(pins)=>{privateOrigins++;assert.deepEqual(pins,[p]);return original(pins,{execute});};
   return {acquireAuthorityInputs:async(reader,pins)=>{
    for(const complete of pins){if(complete.path===p.path){normalized++;assert.deepEqual(complete,{...p,mode:'100644',git_blob_oid:oid});}await reader.acquirePinned(complete,{execute});}
   }};
  });
  assert.equal(report.native_row_scope.added_cells,0);assert.equal(privateOrigins,absentOrigin?1:0);assert.equal(normalized,absentOrigin?0:1);
  assert.deepEqual(f.git('cat-file','blob',oid),raw);
  if(absentOrigin)assert.throws(()=>f.git('--no-lazy-fetch','cat-file','-e',p.commit+'^{commit}'));
 });
});


test('completed geometry transport requires exact canonical original wire bytes',async t=>{
 const geometry={type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,0]]]},body={version:1,kind:'source-target-native-evidence-v1',
  targets:[{id:'one',target_id:'A',pixelIndex:1,base_geometry:geometry},{id:'two',target_id:'B',pixelIndex:2,base_geometry:geometry}],
  negative_evidence:{held:['original-hold'],source:'original-source'}};
 const raw=valueBytes(body),pin=bytes=>({commit:'a'.repeat(40),path:'original.json',mode:'100644',bytes:bytes.length,sha256:hash(bytes),
  git_blob_oid:createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex')}),original=pin(raw);
 const projection=projectCompletedGeometryBody(raw,original,'source_evidence');
 const restored=await restoreCompletedGeometryBody(projection,'source_evidence',original,()=>geometry);
 assert.deepEqual(restored,body);assert(Object.isFrozen(restored)&&Object.isFrozen(restored.targets[0].base_geometry.coordinates));
 const changed=async(change,reason)=>{const p=structuredClone(projection);change(p);await assert.rejects(restoreCompletedGeometryBody(p,'source_evidence',p.original,()=>geometry),reason);};
 await t.test('wrong original size',()=>changed(p=>p.original.bytes++,/whole byte identity/));
 await t.test('wrong original SHA',()=>changed(p=>p.original.sha256='0'.repeat(64),/whole byte identity/));
 await t.test('wrong original Git OID',()=>changed(p=>p.original.git_blob_oid='0'.repeat(40),/whole byte identity/));
 await t.test('nonordinary original mode',()=>changed(p=>p.original.mode='120000',/immutable body identity/));
 await t.test('altered negative evidence',()=>changed(p=>p.body.negative_evidence.held=[],/whole byte identity/));
 await t.test('nongeometry omission',()=>changed(p=>delete p.body.negative_evidence,/whole byte identity/));
 await t.test('reordered omission slots',()=>changed(p=>p.slots.reverse(),/slot/));
 await t.test('unknown compression contract',()=>changed(p=>p.original.decoded_bytes=1,/decoded body|unencoded original/));
 for(const [name,bytes]of [['whitespace',Buffer.from(JSON.stringify(body,null,2)+'\n')],['missing newline',raw.subarray(0,-1)],
  ['duplicate JSON key',Buffer.from(raw.toString().replace('"version":1','"version":1,"version":1'))],
  ['negative zero lexical form',Buffer.from(raw.toString().replace('[0,0]','[-0,0]'))]])
  await t.test(name,()=>assert.throws(()=>projectCompletedGeometryBody(bytes,pin(bytes),'source_evidence'),/whole byte identity|byte size/));
});
