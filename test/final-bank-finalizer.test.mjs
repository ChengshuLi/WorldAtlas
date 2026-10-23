import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync,spawnSync} from 'node:child_process';
import {gunzipSync,gzipSync} from 'node:zlib';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {omitFixtureObjects} from './helpers/git-object-fixture.mjs';
import {committedPackageInputs} from '../scripts/package-output-artifact.mjs';
import {admitPackageInputTransition,preparedStartupPackageTransition} from '../scripts/package-inputs.mjs';
import {trustedFixture,appendNativeAuthority,referenceCheckpointFixture} from './fixtures/selected-checkpoint.mjs';
import {selectedDataSelection} from '../scripts/integration-profile.mjs';
import {oldBank} from './fixtures/final-bank.mjs';
import {pinReader,composeAuthorities,finalizeDelivery,prepareFinalizedStartupOwnership,publishFinalizedDelivery} from '../scripts/prepare-delivery-handoff.mjs';
const bank='data/canonical-grid/current-startup/';
async function prepare(t,options={}){
 const f=await trustedFixture(t,{nativeAppend:true,finalBank:true,...options}),seed=await f.api.qualifyCheckpoint({reader:f.reader});
 const old=await oldBank(f,seed.state);f.api.releaseCheckpoint(seed.state);
 f.save('.github/package-inputs.json',{version:1,description:'Actual finalizer fixture',inputs:['.github/package-inputs.json','data/ownership-selection.json',f.selection.manifest_path,bank,
  f.selection.additive_release.path,...['runtime_envelope'].map(k=>f.sidecar[k].path),...['ledger','patch'].map(k=>f.sidecar.logical_asset_map[k].path)],optional_inputs:[],verification_paths:[],generated_outputs:['dist/']});
 f.bankCommit=f.commit();const reader=new f.native.ImmutableReader(f.root,f.bankCommit),before=await f.api.qualifyCheckpoint({reader});assert.equal(before.available,true);
 return {f,old,reader,before};
}
async function finalize(f,commit,extra={},destination='coordination/engineering/final-bank-test/finalized'){
 const reader=pinReader(f.root),config={version:2,selector:{commit,path:'data/ownership-selection.json'},package_inputs:{commit,path:'.github/package-inputs.json'},...extra};
 const outputs=finalizeDelivery(config,reader);await prepareFinalizedStartupOwnership(outputs);
 publishFinalizedDelivery(f.root,destination,outputs,{phase:'finalize',fixture:true});
 return {outputs,selection:JSON.parse(outputs['ownership-selection.json']),index:JSON.parse(outputs['startup-ownership.json'])};
}
test('existing finalizer migrates accepted E without reading old ledger/patch and adopts with explicit resume',async t=>{
 const {f,old,reader,before}=await prepare(t),normal=pinReader(f.root),read=normal.read;
 const forbidden=new Set([f.sidecar.logical_asset_map.ledger.path,f.sidecar.logical_asset_map.patch.path,f.sidecar.authority_registry.path]);
 const actual={...normal,read(pin){assert(!forbidden.has(pin.path),'Historical repairs are not final-bank preparation operands');return read(pin);}};
 const config={version:2,selector:{commit:f.bankCommit,path:'data/ownership-selection.json'},package_inputs:{commit:f.bankCommit,path:'.github/package-inputs.json'}};
 assert.throws(()=>finalizeDelivery({...config,accepted_checkpoint:{obsolete:true}},actual),/Exact final-bank preparation config/);
 const outputs=finalizeDelivery(config,actual);assert.throws(()=>publishFinalizedDelivery(f.root,'early',outputs,{}),/finished startup bank/);
 await prepareFinalizedStartupOwnership(outputs);const selection=JSON.parse(outputs['ownership-selection.json']);assert.equal(selection.version,2);assert.equal(selection.additive_release,undefined);
 publishFinalizedDelivery(f.root,'coordination/engineering/final-bank-test/finalized',outputs,{phase:'finalize'});publishFinalizedDelivery(f.root,'coordination/engineering/final-bank-test/finalized',outputs,{phase:'finalize'},true);
 const commit=f.commit(),transition=await f.api.qualifyTransition({state:before.state,reader:new f.native.ImmutableReader(f.root,commit,{invocation:reader.invocation})});
 assert.equal(transition.available,true);assert.equal(transition.changedNativeRows.length,0);assert.equal(transition.candidate.version,2);
 assert.deepEqual(JSON.parse(outputs['startup-ownership.json']).compatibility_files,old.index.compatibility_files);
 const inputs=JSON.parse(outputs['package-inputs.json']).inputs;for(const name of forbidden)assert(!inputs.includes(name));
 for(const p of old.index.compatibility_files)assert(fs.existsSync(path.join(f.root,bank,p.path)));
 assert.throws(()=>finalizeDelivery({...config,change_evidence:f.pin('data/registry.json',f.bankCommit)},normal),/migration cannot change/);f.api.releaseCheckpoint(transition.candidate);
});
test('existing finalizer prepares only a new native append and preserves its next unchanged transition',async t=>{
 const {f,reader,before}=await prepare(t),migration=await finalize(f,f.bankCommit),at=f.commit();
 const first=await f.api.qualifyTransition({state:before.state,reader:new f.native.ImmutableReader(f.root,at,{invocation:reader.invocation})});assert.equal(first.available,true);
 const added=await appendNativeAuthority(f,{owner:1,name:'coordination/engineering/next-only',completedConstructor:true});
 f.save('data/ownership-selection.json',migration.selection);
 const source=pinReader(f.root),binding=source.json(added.entry.source_authority);
 const composed=await composeAuthorities({version:2,selector:f.pin('data/ownership-selection.json',at),authorities:[{rule_preimage:added.entry.rule_preimage,source_authority:added.entry.source_authority,ledger:added.entry.completed_constructor,native_patch:binding.native_patch}]},source);
 assert.deepEqual(Object.keys(composed),['authority-registry.json']);assert.deepEqual(JSON.parse(composed['authority-registry.json']).entries,[added.entry]);
 f.save('coordination/engineering/next-only/registry.json',JSON.parse(composed['authority-registry.json']));const evidenceCommit=f.commit(),hook=f.pin('coordination/engineering/next-only/registry.json',evidenceCommit);
 const result=await finalize(f,at,{change_evidence:hook},'coordination/engineering/final-bank-test/next-finalized'),next=f.commit();
 assert(!JSON.parse(result.outputs['package-inputs.json']).inputs.includes(hook.path),'New qualification evidence is not a current website operand');
 const snapshot=commit=>{const definition=JSON.parse(f.git('show',commit+':.github/package-inputs.json')),selection=JSON.parse(f.git('show',commit+':data/ownership-selection.json'));
   return {head:commit,definition,selection,producer:{kind:'immediate-cloudflare-build-v1'},files:committedPackageInputs(f.root,definition,commit)};};
 const packageBefore=snapshot(at),packageAfter=snapshot(next),preparedStartup={beforeIndex:f.git('show',at+':'+bank+'index.json'),afterIndex:f.git('show',next+':'+bank+'index.json'),beforeSelection:f.git('show',at+':data/ownership-selection.json'),afterSelection:f.git('show',next+':data/ownership-selection.json')};
 const packageTransition=admitPackageInputTransition(packageBefore,packageAfter,{preparedStartup});assert(packageTransition.added_selected_inputs.length>0);
 // The ordinary metadata planner reaches final-bank reuse with no historical
 // sidecar/ledger traversal. Its API fixture uses these actual emitted banks
 // and new full evidence pins; unrelated author-fixture setup is not a change.
 const tree=commit=>new Map(f.git('ls-tree','-rlz',commit).toString().split('\0').filter(Boolean).map(line=>{
   const [meta,name]=line.split('\t'),[mode,type,sha,size]=meta.trim().split(/\s+/);return [name,{path:name,mode,type,sha,size:Number(size)}];}));
 const baseline={entries:tree(at)},candidateTree=tree(next),authored={entries:new Map(baseline.entries)},smoke='scripts/selected-delivery-smoke.mjs';
 const smokeRaw=fs.readFileSync(new URL('../scripts/selected-delivery-smoke.mjs',import.meta.url)),smokeRow={path:smoke,mode:'100644',type:'blob',sha:createHash('sha1').update(`blob ${smokeRaw.length}\0`).update(smokeRaw).digest('hex'),size:smokeRaw.length};
 baseline.entries.set(smoke,smokeRow);authored.entries.set(smoke,smokeRow);
 for(const name of [...authored.entries.keys()])if(name.startsWith(bank))authored.entries.delete(name);
 for(const [name,row]of candidateTree)if(name.startsWith(bank))authored.entries.set(name,row);
 const expectedPath='coordination/engineering/final-bank-test/next-finalized/selected-delivery-expectations.json';
 for(const name of ['data/ownership-selection.json','.github/package-inputs.json',expectedPath,hook.path,
   added.entry.rule_preimage.path,added.entry.source_authority.path,added.entry.completed_constructor.path,binding.native_patch.path,binding.source_evidence.path])authored.entries.set(name,candidateTree.get(name));
 const files=[...new Set([...baseline.entries.keys(),...authored.entries.keys()])].filter(name=>baseline.entries.get(name)?.sha!==authored.entries.get(name)?.sha)
   .map(filename=>({filename,status:!baseline.entries.has(filename)?'added':!authored.entries.has(filename)?'removed':'modified'}));
 const requested=[],api=async route=>{const oid=/\/git\/blobs\/([a-f0-9]{40})$/.exec(route)?.[1];assert(oid,'Only exact current metadata bodies are requested');requested.push(oid);
   return {encoding:'base64',content:f.git('cat-file','blob',oid).toString('base64')};};
 const diagnostics={},planning={api,repo:'fixture/repo',branch:'codex/final-bank',files,baseline,authored,metadataDiagnostics:diagnostics};
 const planned=await selectedDataSelection(planning);assert.equal(planned?.test_selection,'selected-data',JSON.stringify(diagnostics));assert.equal(planned.expectations_path,expectedPath);
 assert(!requested.includes(f.sidecar.authority_registry.git_blob_oid),'No old registry traversal');
 assert.equal(await selectedDataSelection({...planning,files:[...files,{filename:'coordination/engineering/unbound/new.json',status:'added'}]}),null,'Unbound changes retain full integration');

 const refresh=(source,name,body)=>{source.files=source.files.filter(row=>row.path!==name);source.files.push({path:name,mode:'100644',oid:createHash('sha1').update(`blob ${body.length}\0`).update(body).digest('hex'),bytes:body.length});};
 const tampered=structuredClone(packageAfter),pins=JSON.parse(preparedStartup.afterIndex),promised='native-v1/ownership/startup-runs-999.bin.gz';
 pins.files=pins.files.filter(pin=>pin.path!==promised);pins.compatibility_files=pins.compatibility_files.filter(pin=>pin.path!==promised);tampered.files=tampered.files.filter(pin=>pin.path!==bank+promised);
 const changedIndex=Buffer.from(JSON.stringify(pins));tampered.selection.prepared_bank={path:bank+'index.json',bytes:changedIndex.length,sha256:createHash('sha256').update(changedIndex).digest('hex')};
 const changedSelector=Buffer.from(JSON.stringify(tampered.selection));refresh(tampered,bank+'index.json',changedIndex);refresh(tampered,'data/ownership-selection.json',changedSelector);
 assert.throws(()=>preparedStartupPackageTransition(packageBefore,tampered,{...preparedStartup,afterIndex:changedIndex,afterSelection:changedSelector}),/changes compatibility/,'A coherent candidate cannot retire a promised v1 URL');
 assert.throws(()=>admitPackageInputTransition({...packageBefore,selection:f.selection},packageAfter,{preparedStartup}),/genuine full capture/);
 const admitted=await f.api.qualifyTransition({state:first.candidate,reader:new f.native.ImmutableReader(f.root,next,{invocation:reader.invocation})});
 assert.equal(admitted.available,true);assert.deepEqual(admitted.changedNativeRows,[added.y]);
 const stable=await finalize(f,next,{},'coordination/engineering/final-bank-test/unchanged-finalized'),same=f.commit();assert.deepEqual(stable.index,result.index);
 const unchanged=await f.api.qualifyTransition({state:admitted.candidate,reader:new f.native.ImmutableReader(f.root,same,{invocation:reader.invocation})});
 assert.equal(unchanged.available,true);assert.deepEqual(unchanged.changedNativeRows,[]);f.api.releaseCheckpoint(unchanged.candidate);
});

test('actual final-bank copier and emitted consumer require no historical repair files',async t=>{
 const {f,old,before}=await prepare(t),result=await finalize(f,f.bankCommit);f.commit();
 const {packagePreparedStartupOwnership}=await import('../scripts/package-startup-ownership.mjs');
 const {checkEmittedSelectedDelivery}=await import('../scripts/selected-delivery-smoke.mjs');
 const emitted=path.join(f.root,'dist/client'),features=old.features.map(({additiveFootprint,...feature})=>feature);
 const copied=await packagePreparedStartupOwnership({manifest:f.manifest,manifestSha:f.selection.sha256,source:path.join(f.root,bank),destination:emitted,
  selected:{finalBank:result.selection.prepared_bank,reference_release:result.selection.reference,base:f.envelope.base_reference},features});
 const atlas={parts:['locations.json'],pixelMap:copied.pixelMap,preparedOwnership:copied.preparedOwnership,reference_release:result.selection.reference};
 fs.writeFileSync(path.join(emitted,'locations.json'),JSON.stringify(features));fs.writeFileSync(path.join(emitted,'atlas-geography.json'),JSON.stringify(atlas));
 const hidden=[f.selection.additive_release.path,f.sidecar.runtime_envelope.path,f.sidecar.authority_registry.path,f.sidecar.logical_asset_map.ledger.path,f.sidecar.logical_asset_map.patch.path];
 for(const name of hidden)fs.rmSync(path.join(f.root,name),{force:true});
 const options={root:f.root,emittedDirectory:emitted},report=await checkEmittedSelectedDelivery(options);
 assert.equal(report.kind,'actual-emitted-final-bank-consumer');assert.equal(report.complete_row_words,old.ownership.rows.length);assert(report.occupied_controls_picked_and_sampled>0);
 assert(report.inputs.every(pin=>!hidden.includes(pin.path)&&!pin.path.startsWith('additive-repairs/')));
 const whole=fs.readFileSync(path.join(emitted,copied.preparedOwnership.context_parts[0].path));
 fs.writeFileSync(path.join(emitted,copied.preparedOwnership.context_parts[0].path),Buffer.from('wrong'));
 await assert.rejects(checkEmittedSelectedDelivery(options),/identity differs|length|size|bytes|hash|file budget/i);
 fs.writeFileSync(path.join(emitted,copied.preparedOwnership.context_parts[0].path),whole);
 fs.writeFileSync(path.join(emitted,'atlas-geography.json'),JSON.stringify({...atlas,additiveRelease:f.envelope}));
 await assert.rejects(checkEmittedSelectedDelivery(options),/historical repair envelope/);
 fs.writeFileSync(path.join(emitted,'atlas-geography.json'),JSON.stringify({...atlas,pixelMap:{...atlas.pixelMap,runWords:atlas.pixelMap.runWords+2}}));
 await assert.rejects(checkEmittedSelectedDelivery(options),/words descriptor/);
 f.api.releaseCheckpoint(before.state);
});


test('one-time migration retires only authenticated historical declarations, preserving independent/current roles',async t=>{
 const {f,before}=await prepare(t,{packageRoles:true});
 const definition=JSON.parse(fs.readFileSync(path.join(f.root,'.github/package-inputs.json')));
 const historical=['original/rule.json','original/binding.json','original/native-request.json','original/source-publication.json','accepted-rebind/request.json'];
 f.save('data/unrelated.json',{retained:true});definition.inputs.push(...historical,'data/registry.json','data/world-index.json','data/unrelated.json');
 definition.verification_paths.push('original/source-publication.json');f.save('.github/package-inputs.json',definition);const commit=f.commit();
 const result=await finalize(f,commit),inputs=JSON.parse(result.outputs['package-inputs.json']).inputs;
 for(const name of historical)assert(!inputs.includes(name),name);
 assert(!inputs.includes('data/registry.json'));
 for(const name of ['data/world-index.json','data/unrelated.json',bank])assert(inputs.includes(name),name);
 assert.deepEqual(JSON.parse(result.outputs['package-inputs.json']).verification_paths,definition.verification_paths,'Verification custody remains exact outside website inputs');
 for(const name of historical)assert(fs.existsSync(path.join(f.root,name)),'Historical source remains in Git/worktree');
 const expectations=JSON.parse(result.outputs['selected-delivery-expectations.json']);assert.deepEqual(expectations.bank,result.selection.prepared_bank);
 f.api.releaseCheckpoint(before.state);
});


test('final-bank reference-only authoring retains words and uses the existing complete metadata qualification',async t=>{
 const original=await referenceCheckpointFixture(t,{finalBank:true}),git=(...args)=>execFileSync('git',['-C',original.repo,...args],{maxBuffer:Infinity});
 const read=(commit,name)=>git('show',commit+':'+name),json=(commit,name)=>JSON.parse(read(commit,name));
 const selected=json(original.selected,'data/ownership-selection.json'),sidecar=json(original.selected,selected.additive_release.path);
 const f={...original,root:original.repo,git,save:original.write,selection:selected,sidecar,
   registry:json(sidecar.authority_registry.commit,sidecar.authority_registry.path),patch:json(sidecar.logical_asset_map.patch.commit,sidecar.logical_asset_map.patch.path),
   envelope:json(sidecar.runtime_envelope.commit,sidecar.runtime_envelope.path)};
 const sourceNames=['data/ownership-selection.json','data/hierarchy.json','data/geography/fixture.json','data/geographic-releases/current-manifest.json','data/geographic-releases/releases.json.gz'];
 for(const name of sourceNames)f.save(name,read(original.selected,name));
 await oldBank(f,original.state);f.save('.github/package-inputs.json',{version:1,description:'Reference-only final-bank fixture',inputs:['.github/package-inputs.json','data/ownership-selection.json',f.selection.manifest_path,bank,
  selected.additive_release.path,sidecar.runtime_envelope.path,sidecar.logical_asset_map.ledger.path,sidecar.logical_asset_map.patch.path],optional_inputs:[],verification_paths:[],generated_outputs:['dist/']});
 const bankCommit=f.commit(),reader=new f.native.ImmutableReader(f.root,bankCommit),before=await f.api.qualifyCheckpoint({reader});assert.equal(before.available,true);
 const migration=await finalize(f,bankCommit),at=f.commit(),first=await f.api.qualifyTransition({state:before.state,reader:new f.native.ImmutableReader(f.root,at,{invocation:reader.invocation})});assert.equal(first.available,true);
 for(const name of sourceNames.filter(name=>name!=='data/ownership-selection.json'))f.save(name,read(original.candidate,name));
 const projection=original.projection;f.save('inputs/projection.json',projection);const proposed=f.commit(),pin=f.pin('inputs/projection.json',proposed);
 const result=await finalize(f,at,{reference_projection:pin},'coordination/engineering/final-bank-test/reference-finalized'),candidate=f.commit();
 const next=await f.api.qualifyTransition({state:first.candidate,reader:new f.native.ImmutableReader(f.root,candidate,{invocation:reader.invocation})});
 assert.equal(next.available,true);assert.deepEqual(next.changedNativeRows,[]);assert(next.changedIds.length>0);
 const directBefore=new f.native.ImmutableReader(f.root,at);
 const direct=await f.api.compareAcceptedFinalBank({beforeReader:directBefore,afterReader:new f.native.ImmutableReader(f.root,candidate,{invocation:directBefore.invocation})});
 assert.equal(direct.native_row_scope.added_cells,0);assert(direct.changed_ids.length>0);
 assert.deepEqual(result.index.preparedOwnership.native_pixel_map,migration.index.preparedOwnership.native_pixel_map);
 assert.equal(result.index.preparedOwnership.rows_sha256,migration.index.preparedOwnership.rows_sha256);
 assert.equal(result.index.preparedOwnership.runs_word_stream_sha256,migration.index.preparedOwnership.runs_word_stream_sha256);
 assert.deepEqual(result.index.preparedOwnership.base_reference,projection.reference);
 // A later final-profile pointer replacement retires only its exact prior
 // declaration, not the old source/evidence file or independently used inputs.
 f.save('inputs/projection-next.json',projection);const replacement=f.commit();
 const again=await finalize(f,candidate,{reference_projection:f.pin('inputs/projection-next.json',replacement)},'coordination/engineering/final-bank-test/reference-replaced');
 const metadataSuccessor=f.commit(),priorMetadata=new f.native.ImmutableReader(f.root,candidate);
 const repeatedMetadata=await f.api.compareAcceptedFinalBank({beforeReader:priorMetadata,afterReader:new f.native.ImmutableReader(f.root,metadataSuccessor,{invocation:priorMetadata.invocation})});
 assert.equal(repeatedMetadata.native_row_scope.added_cells,0);assert.deepEqual(repeatedMetadata.changed_ids,[]);
 await t.test('coherently rebound release still must declare each metadata receipt',async()=>{
  const release=JSON.parse(gunzipSync(read(metadataSuccessor,'data/geographic-releases/releases.json.gz')));
  delete release.releases.at(-1).metadata.metadata_migration_sha256;
  const encoded=gzipSync(Buffer.from(JSON.stringify(release))),digest=createHash('sha256').update(encoded).digest('hex');
  f.save('data/geographic-releases/releases.json.gz',encoded);f.save('data/geographic-releases/current-manifest.json',{path:'releases.json.gz',sha256:digest});
  const rebound=f.commit(),accepted=new f.native.ImmutableReader(f.root,at);
  await assert.rejects(f.api.compareAcceptedFinalBank({beforeReader:accepted,afterReader:new f.native.ImmutableReader(f.root,rebound,{invocation:accepted.invocation})}),/does not bind every applied metadata receipt/);
  f.git('reset','--hard',metadataSuccessor);
 });
 const declarations=JSON.parse(again.outputs['package-inputs.json']);
 assert(!declarations.inputs.includes('inputs/projection.json'));assert(declarations.inputs.includes('inputs/projection-next.json'));
 assert(fs.existsSync(path.join(f.root,'inputs/projection.json')),'Original projection evidence remains recoverable');
 assert.equal(again.index.preparedOwnership.runs_word_stream_sha256,result.index.preparedOwnership.runs_word_stream_sha256);
 // The real database publication stamps generated reference revisions on its
 // catalog rows. The bank preserves source properties, not those DB defaults.
 const {packagePreparedStartupOwnership}=await import('../scripts/package-startup-ownership.mjs');
 const {checkEmittedSelectedDelivery}=await import('../scripts/selected-delivery-smoke.mjs');
 const revision='a'.repeat(64),referenceMetadata={...again.index.referenceMetadata,application_reference_revision:revision};
 const features=again.index.preparedOwnership.context_parts.flatMap(pin=>JSON.parse(gunzipSync(fs.readFileSync(path.join(f.root,bank,pin.path)))))
  .map(({finishedFootprint,...feature})=>({...feature,properties:{...feature.properties,metadata:{...feature.properties.metadata,reference_revision:revision}}}));
 const emitted=path.join(f.root,'dist/client');
 const copied=await packagePreparedStartupOwnership({manifest:f.manifest,manifestSha:f.selection.sha256,source:path.join(f.root,bank),destination:emitted,
  selected:{finalBank:again.selection.prepared_bank,reference_release:again.selection.reference,base:projection.reference,referenceMetadata},features});
 const atlas={parts:['locations.json'],pixelMap:copied.pixelMap,preparedOwnership:copied.preparedOwnership,reference_release:again.selection.reference,referenceMetadata};
 const write=(name,value)=>{const file=path.join(emitted,name);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,JSON.stringify(value));};
 write('atlas-geography.json',atlas);write('locations.json',features);
 const projectionFile=path.join(emitted,referenceMetadata.asset.path);fs.mkdirSync(path.dirname(projectionFile),{recursive:true});
 fs.writeFileSync(projectionFile,fs.readFileSync(path.join(f.root,again.selection.reference_projection.path)));
 const options={root:f.root,emittedDirectory:emitted};
 assert.equal((await checkEmittedSelectedDelivery(options)).kind,'actual-emitted-final-bank-consumer');
 for(const value of [undefined,'b'.repeat(64)]){
  const metadata={...referenceMetadata};if(value===undefined)delete metadata.application_reference_revision;else metadata.application_reference_revision=value;
  write('atlas-geography.json',{...atlas,referenceMetadata:metadata});
  await assert.rejects(checkEmittedSelectedDelivery(options),/Generated reference revision differs/);
 }
 write('atlas-geography.json',atlas);
 const wrongRow=structuredClone(features);wrongRow[0].properties.metadata.reference_revision='c'.repeat(64);write('locations.json',wrongRow);
 await assert.rejects(checkEmittedSelectedDelivery(options),/Generated reference revision differs/);
 const wrongProperty=structuredClone(features);wrongProperty[0].properties.name+=' altered';write('locations.json',wrongProperty);
 await assert.rejects(checkEmittedSelectedDelivery(options),/Current reference properties differ/);write('locations.json',features);
 write('atlas-geography.json',{...atlas,referenceMetadata:{...referenceMetadata,asset:{...referenceMetadata.asset,sha256:'d'.repeat(64)}}});
 await assert.rejects(checkEmittedSelectedDelivery(options),/deep-equal|equal/);write('atlas-geography.json',atlas);
 await t.test('cold reference-only CLI admits exact current metadata without historical or native transport bodies',()=>{
  const sourcePin=f.pin(selected.selected_geography.path,at),source=json(at,sourcePin.path);
  const required=[...new Map([
   sourcePin,source.world_index,projection.hierarchy.before,projection.hierarchy.after,...projection.receipts,
   ...projection.source_updates.flatMap(update=>[update.before,update.after]),
   ...[...migration.index.pixelMap.parts,...migration.index.preparedOwnership.context_parts].map(p=>f.pin(bank+p.path,at)),
   ...[...result.index.pixelMap.parts,...result.index.preparedOwnership.context_parts].map(p=>f.pin(bank+p.path,candidate))
  ].map(p=>[p.git_blob_oid,p])).values()];
  const used=new Set(required.map(p=>p.git_blob_oid));
  const unnecessary=[...new Map([
   f.pin('data/canonical-grid/bounds.json.gz',at),...f.manifest.parts.map(p=>f.pin(path.posix.dirname(selected.manifest_path)+'/'+p.path,at)),
   ...['authority_registry','runtime_envelope'].map(k=>sidecar[k]),sidecar.logical_asset_map.ledger,sidecar.logical_asset_map.patch,
   ...result.index.compatibility_files.map(p=>f.pin(bank+p.path,candidate))
  ].filter(p=>!used.has(p.git_blob_oid)).map(p=>[p.git_blob_oid,p])).values()];
  assert(unnecessary.length>0);
  const remote=fs.mkdtempSync(path.join(path.dirname(f.root),'.reference-map-remote-'));t.after(()=>fs.rmSync(remote,{recursive:true,force:true}));
  execFileSync('git',['clone','--bare','--no-hardlinks',f.root,remote],{stdio:'ignore'});
  execFileSync('git',['-C',remote,'config','uploadpack.allowAnySHA1InWant','true']);execFileSync('git',['-C',remote,'config','uploadpack.allowFilter','true']);
  f.git('reset','--hard',at);f.git('config','url.'+pathToFileURL(remote).href+'.insteadOf','https://github.com/ChengshuLi/WorldAtlas.git');
  omitFixtureObjects(t,f.root,[...required,...unnecessary].map(p=>p.git_blob_oid));
  const objects=()=>new Set(f.git('--no-lazy-fetch','--no-replace-objects','cat-file','--batch-all-objects','--batch-check=%(objectname)').toString().trim().split('\n'));
  const before=objects(),env={...process.env,GH_TOKEN:''};delete env.NODE_OPTIONS;delete env.NODE_PATH;
  const command='coordination/engineering/selected-geography-effective-prevention-20261009/selected-joint-entry.mjs';
  const run=()=>spawnSync(process.execPath,[path.join(f.root,command),f.root,at,at,candidate,path.join(f.root,'no-reference-product')],{encoding:'utf8',env});
  const cold=run();assert.equal(cold.status,0,cold.stderr);const report=JSON.parse(cold.stdout);
  assert.equal(report.mode,'accepted-final-map-comparison-v1');assert.equal(report.native.native_row_scope.added_cells,0);
  const after=objects();
  assert.deepEqual([...after].filter(id=>!before.has(id)).sort(),required.map(p=>p.git_blob_oid).sort());
  // Promisor-aware existence probes need not prove local materialization.
  for(const p of unnecessary)assert(!after.has(p.git_blob_oid),'Unrelated object remains absent locally: '+p.path);
  assert(!fs.existsSync(path.join(f.root,'no-reference-product')));
  f.git('config','--unset','url.'+pathToFileURL(remote).href+'.insteadOf');
  f.git('config','url.'+pathToFileURL(path.join(remote,'absent')).href+'.insteadOf','https://github.com/ChengshuLi/WorldAtlas.git');
  const warm=run();assert.equal(warm.status,0,warm.stderr);assert.deepEqual(JSON.parse(warm.stdout),report);
  t.diagnostic('Cold reference imported '+required.length+' exact metadata/current-bank blobs; '+unnecessary.length+' unrelated native/history/compatibility blobs remain absent.');
 });
 f.api.releaseCheckpoint(next.candidate);f.api.releaseCheckpoint(original.state);
});


test('final-to-final preparation retains cold sparse compatibility bodies and exact resume without acquisition',async t=>{
 const {f,before}=await prepare(t),migration=await finalize(f,f.bankCommit),at=f.commit();f.api.releaseCheckpoint(before.state);
 const active=new Set([...migration.index.pixelMap.parts,...migration.index.preparedOwnership.context_parts].map(p=>p.path));
 const fixed=migration.index.compatibility_files.find(p=>!active.has(p.path)&&p.path.endsWith('startup-runs-999.bin.gz'));assert(fixed);
 const name=bank+fixed.path,oid=f.git('rev-parse',at+':'+name).toString().trim();
 const object=path.join(f.root,'.git/objects',oid.slice(0,2),oid.slice(2)),held=object+'.test-held';
 execFileSync('git',['sparse-checkout','set','--no-cone','--stdin'],{cwd:f.root,input:`/*\n!/${name}\n`,stdio:'pipe'});
 assert(!fs.existsSync(path.join(f.root,name)));assert.equal(f.git('ls-files','-t','--',name).toString(),'S '+name+'\n');
 assert(fs.statSync(object).isFile());fs.renameSync(object,held);
 try {
  const normal=pinReader(f.root,{execute(command,args,options){assert(!args.includes('fetch'),'Unchanged compatibility body must not be acquired');return execFileSync(command,args,options);}});
  const read=normal.read,reader={...normal,read(pin){assert.notEqual(pin.path,name,'Unchanged compatibility body must not be read');return read(pin);}};
  const outputs=finalizeDelivery({version:2,selector:{commit:at,path:'data/ownership-selection.json'},package_inputs:{commit:at,path:'.github/package-inputs.json'}},reader);
  await prepareFinalizedStartupOwnership(outputs);
  const destination='coordination/engineering/final-bank-test/cold-finalized';
  publishFinalizedDelivery(f.root,destination,outputs,{phase:'finalize'});
  publishFinalizedDelivery(f.root,destination,outputs,{phase:'finalize'},true);
  assert.deepEqual(JSON.parse(outputs['startup-ownership.json']),migration.index);
  assert(!fs.existsSync(path.join(f.root,name)),'Sparse compatibility path remains absent');
  assert(!fs.existsSync(object),'Missing compatibility object remains absent');
  assert.equal(f.git('rev-parse','HEAD:'+name).toString().trim(),oid,'Accepted ordinary Git identity is retained');
  const configPath='coordination/engineering/final-bank-test/cold-config.json',cliDestination='coordination/engineering/final-bank-test/cold-cli-finalized';
  f.save(configPath,{version:2,selector:{commit:at,path:'data/ownership-selection.json'},package_inputs:{commit:at,path:'.github/package-inputs.json'}});
  const command=fileURLToPath(new URL('../scripts/prepare-delivery-handoff.mjs',import.meta.url));
  for(const flags of [[],['--resume']]) execFileSync(process.execPath,[command,'finalize',configPath,cliDestination,...flags],
   {cwd:f.root,env:{...process.env,GIT_NO_LAZY_FETCH:'1',GIT_NO_REPLACE_OBJECTS:'1'},stdio:'pipe'});
  assert(!fs.existsSync(object)&&!fs.existsSync(path.join(f.root,name)),'Actual CLI/resume leaves the same absent body unhydrated');
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(f.root,cliDestination,'startup-ownership.json'))),migration.index);
  const committed=f.commit();assert.equal(f.git('rev-parse',committed+':'+name).toString().trim(),oid,
   'Normal git add -A and commit preserve the exact cold sparse member');
 } finally {fs.renameSync(held,object);}
});


test('retained final compatibility keeps canonical preflight, committed identity and recheck guards',async t=>{
 const {f,before}=await prepare(t),migration=await finalize(f,f.bankCommit),at=f.commit();f.api.releaseCheckpoint(before.state);
 const fixed=migration.index.compatibility_files.find(p=>p.path.endsWith('startup-runs-999.bin.gz'));assert(fixed);
 const name=bank+fixed.path,file=path.join(f.root,name),original=fs.readFileSync(file),reader=pinReader(f.root);
 const outputs=finalizeDelivery({version:2,selector:{commit:at,path:'data/ownership-selection.json'},package_inputs:{commit:at,path:'.github/package-inputs.json'}},reader);
 await prepareFinalizedStartupOwnership(outputs);
 const destination='coordination/engineering/final-bank-test/retained-guards';
 const publish=()=>publishFinalizedDelivery(f.root,destination,outputs,{phase:'finalize'});
 for(const mutation of ['bytes','symlink','mode','directory','missing']){
  if(mutation==='bytes')fs.writeFileSync(file,Buffer.from('edited compatibility'));
  if(mutation==='symlink'){fs.unlinkSync(file);fs.symlinkSync('missing-sentinel',file);}
  if(mutation==='mode')fs.chmodSync(file,0o755);
  if(mutation==='directory'){fs.unlinkSync(file);fs.mkdirSync(file);}
  if(mutation==='missing')fs.unlinkSync(file);
  assert.throws(publish,/Canonical output changed outside|Nonordinary canonical output/);
  assert(!fs.existsSync(path.join(f.root,destination)),'Refusal precedes staging');
  if(mutation==='directory')fs.rmdirSync(file);else if(mutation!=='missing')fs.unlinkSync(file);
  fs.writeFileSync(file,original,{mode:0o644});
 }
 f.git('update-index','--force-remove',name);
 assert.throws(publish,/Indexed retained compatibility differs/);assert(!fs.existsSync(path.join(f.root,destination)));
 f.git('add','--',name);
 f.save(name,Buffer.from('different staged compatibility'));f.git('add','--',name);fs.writeFileSync(file,original);
 assert.throws(publish,/Indexed retained compatibility differs/);assert(!fs.existsSync(path.join(f.root,destination)));
 f.git('add','--',name);
 f.save(name,Buffer.from('different committed compatibility'));f.commit();
 assert.throws(publish,/Committed retained compatibility differs/);assert(!fs.existsSync(path.join(f.root,destination)));
 f.save(name,original);f.commit();
 assert.throws(()=>publishFinalizedDelivery(f.root,name+'/child',outputs,{}),/overlaps canonical/);
 // Alter the index after preflight while staging occurs, without touching bytes.
 const initialWrite=fs.writeFileSync,indexDestination=destination+'-index';let indexChanged=false;
 fs.writeFileSync=function(filename,...args){const result=initialWrite.call(this,filename,...args);
  if(!indexChanged&&typeof filename==='string'&&filename.includes(indexDestination)){indexChanged=true;f.git('update-index','--force-remove',name);}return result;};
 try{assert.throws(()=>publishFinalizedDelivery(f.root,indexDestination,outputs,{phase:'finalize'}),/Indexed retained compatibility differs/);assert(indexChanged);}finally{fs.writeFileSync=initialWrite;f.git('add','--',name);}
 assert.deepEqual(fs.readFileSync(file),original);
 // Alter a retained input after the full-set preflight, while staging occurs.
 const write=fs.writeFileSync;let changed=false;
 fs.writeFileSync=function(filename,...args){const result=write.call(this,filename,...args);
  if(!changed&&typeof filename==='string'&&filename.includes(destination)){changed=true;write(file,Buffer.from('changed during staging'));}return result;};
 try{assert.throws(publish,/Canonical output changed outside/);assert(changed);}finally{fs.writeFileSync=write;}
 assert.equal(fs.readFileSync(file).toString(),'changed during staging');fs.writeFileSync(file,original);
 publishFinalizedDelivery(f.root,destination,outputs,{phase:'finalize'},true);
 assert.deepEqual(fs.readFileSync(file),original,'Exact explicit resume preserves compatibility');
});

test('compatibility roles that also serve current E retain complete body acquisition',async t=>{
 const {f,before}=await prepare(t),migration=await finalize(f,f.bankCommit);f.api.releaseCheckpoint(before.state);
 const part=migration.index.pixelMap.parts.find(p=>!migration.index.compatibility_files.some(c=>c.path===p.path));assert(part);
 const pin=migration.index.files.find(p=>p.path===part.path);migration.index.compatibility_files.push(pin);
 const raw=Buffer.from(JSON.stringify(migration.index)),selection={...migration.selection,prepared_bank:{...migration.selection.prepared_bank,bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex')}};
 f.save(bank+'index.json',raw);f.save('data/ownership-selection.json',selection);const at=f.commit(),normal=pinReader(f.root),acquire=normal.acquire;
 const reader={...normal,async acquire(pins){if(pins.some(p=>p.path===bank+part.path))throw Error('required current-E member acquired');return acquire(pins);}};
 const outputs=finalizeDelivery({version:2,selector:{commit:at,path:'data/ownership-selection.json'},package_inputs:{commit:at,path:'.github/package-inputs.json'}},reader);
 await assert.rejects(prepareFinalizedStartupOwnership(outputs),/required current-E member acquired/);
});
