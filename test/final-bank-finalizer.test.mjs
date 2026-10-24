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
import {oldBank,initialFinalBank,compareFinal} from './fixtures/final-bank.mjs';
import {pinReader,composeAuthorities,finalizeDelivery,prepareFinalizedStartupOwnership,publishFinalizedDelivery,supportedInputs,nativeAuthority,publishOwnedProducts,jsonBytes,digest} from '../scripts/prepare-delivery-handoff.mjs';
const bank='data/canonical-grid/current-startup/';
async function prepare(t,options={}){
 const f=await trustedFixture(t,{nativeAppend:true,finalBank:true,...options});
 const old=await initialFinalBank(f);
 f.save('.github/package-inputs.json',{version:1,description:'Actual finalizer fixture',inputs:['.github/package-inputs.json','data/ownership-selection.json',f.selection.manifest_path,bank],optional_inputs:[],verification_paths:[],generated_outputs:['dist/']});
 f.bankCommit=f.commit();const reader=new f.native.ImmutableReader(f.root,f.bankCommit),before=undefined;
 return {f,old,reader,before};
}
async function finalize(f,commit,extra={},destination='coordination/engineering/final-bank-test/finalized'){
 const reader=pinReader(f.root),config={version:2,selector:{commit,path:'data/ownership-selection.json'},package_inputs:{commit,path:'.github/package-inputs.json'},...extra};
 const outputs=finalizeDelivery(config,reader);await prepareFinalizedStartupOwnership(outputs);
 publishFinalizedDelivery(f.root,destination,outputs,{phase:'finalize',fixture:true});
 return {outputs,selection:JSON.parse(outputs['ownership-selection.json']),index:JSON.parse(outputs['startup-ownership.json'])};
}
test('existing finalizer prepares only a new native append and preserves its next unchanged transition',async t=>{
 const {f,reader,before}=await prepare(t),migration=await finalize(f,f.bankCommit),at=f.commit();
 await compareFinal(f,f.bankCommit,at);
 const added=await appendNativeAuthority(f,{membershipPath:'data/source.json',owner:1,name:'coordination/engineering/next-only',completedConstructor:true});
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
 // A withdrawal restores the prior complete bank without making the previous
 // authority registry a current metadata operand. Use the actual emitted bank
 // descriptors on both sides, and derive the complete changed-file vector.
 const withdrawn={entries:new Map(authored.entries)};
 for(const name of [...withdrawn.entries.keys()])if(name.startsWith(bank))withdrawn.entries.delete(name);
 for(const [name,row]of baseline.entries)if(name.startsWith(bank))withdrawn.entries.set(name,row);
 withdrawn.entries.set('data/ownership-selection.json',baseline.entries.get('data/ownership-selection.json'));
 withdrawn.entries.set('.github/package-inputs.json',baseline.entries.get('.github/package-inputs.json'));
 const withdrawalExpected=Buffer.from(JSON.stringify({version:2,kind:'selected-final-bank-consumer-v2',bank:migration.selection.prepared_bank,reference:migration.selection.reference}));
 const expectedOid=execFileSync('git',['-C',f.root,'hash-object','-w','--stdin'],{input:withdrawalExpected,encoding:'utf8'}).trim();
 const withdrawalExpectedPath='coordination/engineering/final-bank-test/withdrawal-planner/selected-delivery-expectations.json';
 withdrawn.entries.set(withdrawalExpectedPath,{path:withdrawalExpectedPath,mode:'100644',type:'blob',sha:expectedOid,size:withdrawalExpected.length});
 const withdrawalFiles=[...new Set([...authored.entries.keys(),...withdrawn.entries.keys()])]
  .filter(name=>authored.entries.get(name)?.sha!==withdrawn.entries.get(name)?.sha)
  .map(filename=>({filename,status:!authored.entries.has(filename)?'added':!withdrawn.entries.has(filename)?'removed':'modified'}));
 const withdrawalRequests=[],withdrawalDiagnostics={};
 const withdrawalPlan=await selectedDataSelection({...planning,baseline:authored,authored:withdrawn,files:withdrawalFiles,
  metadataDiagnostics:withdrawalDiagnostics,api:async route=>{withdrawalRequests.push(route);return api(route);}});
 assert.equal(withdrawalPlan?.test_selection,'selected-data',JSON.stringify(withdrawalDiagnostics));
 assert(!withdrawalRequests.some(route=>route.endsWith(hook.git_blob_oid)||route.endsWith(f.sidecar.authority_registry.git_blob_oid)),
  'Withdrawal planning does not traverse either previous repair registry');

 assert.equal(await selectedDataSelection({...planning,files:[...files,{filename:'coordination/engineering/unbound/new.json',status:'added'}]}),null,'Unbound changes retain full integration');

 const refresh=(source,name,body)=>{source.files=source.files.filter(row=>row.path!==name);source.files.push({path:name,mode:'100644',oid:createHash('sha1').update(`blob ${body.length}\0`).update(body).digest('hex'),bytes:body.length});};
 const tampered=structuredClone(packageAfter),pins=JSON.parse(preparedStartup.afterIndex),promised='native-v1/ownership/startup-runs-999.bin.gz';
 pins.files=pins.files.filter(pin=>pin.path!==promised);pins.compatibility_files=pins.compatibility_files.filter(pin=>pin.path!==promised);tampered.files=tampered.files.filter(pin=>pin.path!==bank+promised);
 const changedIndex=Buffer.from(JSON.stringify(pins));tampered.selection.prepared_bank={path:bank+'index.json',bytes:changedIndex.length,sha256:createHash('sha256').update(changedIndex).digest('hex')};
 const changedSelector=Buffer.from(JSON.stringify(tampered.selection));refresh(tampered,bank+'index.json',changedIndex);refresh(tampered,'data/ownership-selection.json',changedSelector);
 assert.throws(()=>preparedStartupPackageTransition(packageBefore,tampered,{...preparedStartup,afterIndex:changedIndex,afterSelection:changedSelector}),/changes compatibility/,'A coherent candidate cannot retire a promised v1 URL');
 assert.throws(()=>admitPackageInputTransition({...packageBefore,selection:f.selection},packageAfter,{preparedStartup}),/genuine full capture/);
 const admitted=await compareFinal(f,at,next);assert.deepEqual(admitted.native_row_scope.changed_rows,[added.y]);
 const stable=await finalize(f,next,{},'coordination/engineering/final-bank-test/unchanged-finalized'),same=f.commit();assert.deepEqual(stable.index,result.index);
 const unchanged=await compareFinal(f,next,same);assert.deepEqual(unchanged.native_row_scope.changed_rows,[]);
});

test('actual final-bank copier and emitted consumer require no historical repair files',async t=>{
 const {f,old,before}=await prepare(t),result=await finalize(f,f.bankCommit);f.commit();
 const {packagePreparedStartupOwnership}=await import('../scripts/package-startup-ownership.mjs');
 const {checkEmittedSelectedDelivery,runSelectedDeliverySmoke}=await import('../scripts/selected-delivery-smoke.mjs');
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
 const expectationsPath=path.join(f.root,'expectations.json'),outputPath=path.join(f.root,'smoke-report.json');
 fs.writeFileSync(expectationsPath,result.outputs['selected-delivery-expectations.json']);
 const cliReport=await runSelectedDeliverySmoke({...options,expectationsPath,outputPath});
 assert.equal(cliReport.kind,'actual-emitted-final-bank-consumer');
 const receipt=fs.readFileSync(outputPath);
 await assert.rejects(runSelectedDeliverySmoke({...options,expectationsPath,outputPath}),/exists|already|collision/i);
 assert.deepEqual(fs.readFileSync(outputPath),receipt);
 fs.unlinkSync(outputPath);fs.symlinkSync('missing-target',outputPath);
 await assert.rejects(runSelectedDeliverySmoke({...options,expectationsPath,outputPath}),/exists|ordinary|symlink|collision/i);
 fs.unlinkSync(outputPath);
 const whole=fs.readFileSync(path.join(emitted,copied.preparedOwnership.context_parts[0].path));
 fs.writeFileSync(path.join(emitted,copied.preparedOwnership.context_parts[0].path),Buffer.from('wrong'));
 await assert.rejects(checkEmittedSelectedDelivery(options),/identity differs|length|size|bytes|hash|file budget/i);
 fs.writeFileSync(path.join(emitted,copied.preparedOwnership.context_parts[0].path),whole);
 fs.writeFileSync(path.join(emitted,'atlas-geography.json'),JSON.stringify({...atlas,additiveRelease:f.envelope}));
 await assert.rejects(checkEmittedSelectedDelivery(options),/historical repair envelope/);
 fs.writeFileSync(path.join(emitted,'atlas-geography.json'),JSON.stringify({...atlas,pixelMap:{...atlas.pixelMap,runWords:atlas.pixelMap.runWords+2}}));
 await assert.rejects(checkEmittedSelectedDelivery(options),/words descriptor/);

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
 await initialFinalBank(f,original.state);f.save('.github/package-inputs.json',{version:1,description:'Reference-only final-bank fixture',inputs:['.github/package-inputs.json','data/ownership-selection.json',f.selection.manifest_path,bank,
  selected.additive_release.path,sidecar.runtime_envelope.path,sidecar.logical_asset_map.ledger.path,sidecar.logical_asset_map.patch.path],optional_inputs:[],verification_paths:[],generated_outputs:['dist/']});
 const bankCommit=f.commit(),reader=new f.native.ImmutableReader(f.root,bankCommit);
 const migration=await finalize(f,bankCommit),at=f.commit();await compareFinal(f,bankCommit,at);
 for(const name of sourceNames.filter(name=>name!=='data/ownership-selection.json'))f.save(name,read(original.candidate,name));
 const projection=original.projection;f.save('inputs/projection.json',projection);const proposed=f.commit(),pin=f.pin('inputs/projection.json',proposed);
 const result=await finalize(f,at,{reference_projection:pin},'coordination/engineering/final-bank-test/reference-finalized'),candidate=f.commit();
 const next=await compareFinal(f,at,candidate);assert.deepEqual(next.native_row_scope.changed_rows,[]);assert(next.changed_ids.length>0);
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
 const {checkEmittedSelectedDelivery,runSelectedDeliverySmoke}=await import('../scripts/selected-delivery-smoke.mjs');
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

});


test('final-to-final preparation retains cold sparse compatibility bodies and exact resume without acquisition',async t=>{
 const {f,before}=await prepare(t),migration=await finalize(f,f.bankCommit),at=f.commit();
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
 const {f,before}=await prepare(t),migration=await finalize(f,f.bankCommit),at=f.commit();
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
 const {f,before}=await prepare(t),migration=await finalize(f,f.bankCommit);
 const part=migration.index.pixelMap.parts.find(p=>!migration.index.compatibility_files.some(c=>c.path===p.path));assert(part);
 const pin=migration.index.files.find(p=>p.path===part.path);migration.index.compatibility_files.push(pin);
 const raw=Buffer.from(JSON.stringify(migration.index)),selection={...migration.selection,prepared_bank:{...migration.selection.prepared_bank,bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex')}};
 f.save(bank+'index.json',raw);f.save('data/ownership-selection.json',selection);const at=f.commit(),normal=pinReader(f.root),acquire=normal.acquire;
 const reader={...normal,async acquire(pins){if(pins.some(p=>p.path===bank+part.path))throw Error('required current-E member acquired');return acquire(pins);}};
 const outputs=finalizeDelivery({version:2,selector:{commit:at,path:'data/ownership-selection.json'},package_inputs:{commit:at,path:'.github/package-inputs.json'}},reader);
 await assert.rejects(prepareFinalizedStartupOwnership(outputs),/required current-E member acquired/);
});


test('finalizer retires exact sparse current-bank preimages through normal staging and resume',async t=>{
 const {f,before}=await prepare(t),migration=await finalize(f,f.bankCommit),at=f.commit();
 const added=await appendNativeAuthority(f,{membershipPath:'data/source.json',owner:1,name:'coordination/engineering/sparse-retirement',completedConstructor:true});
 f.save('data/ownership-selection.json',migration.selection);f.save('coordination/engineering/sparse-retirement/registry.json',{version:1,kind:'retained-rule-authority-registry-v1',entries:[added.entry]});
 const source=f.commit(),hook=f.pin('coordination/engineering/sparse-retirement/registry.json',source);
 const retired=[migration.index.preparedOwnership.context_parts[0].path,migration.index.pixelMap.parts.find(p=>p.kind==='runs').path].map(p=>bank+p);
 const active=new Set([...migration.index.pixelMap.parts,...migration.index.preparedOwnership.context_parts].map(p=>p.path));
 const fixed=bank+migration.index.compatibility_files.find(p=>!active.has(p.path)&&p.path.endsWith('startup-runs-999.bin.gz')).path;
 const fixedEntry=f.git('ls-files','--stage','-z','--',fixed).toString();
 execFileSync('git',['sparse-checkout','set','--no-cone','--stdin'],{cwd:f.root,input:`/*\n${[...retired,fixed].map(p=>'!/'+p).join('\n')}\n`,stdio:'pipe'});
 for(const name of [...retired,fixed]){assert(!fs.existsSync(path.join(f.root,name)));assert.equal(f.git('ls-files','-v','--',name).toString(),'S '+name+'\n');}
 const originalIndex=f.git('ls-files','--stage','-v','-z').toString().split('\0').filter(Boolean);
 const reader=pinReader(f.root),outputs=finalizeDelivery({version:2,selector:{commit:at,path:'data/ownership-selection.json'},package_inputs:{commit:at,path:'.github/package-inputs.json'},change_evidence:hook},reader);
 await prepareFinalizedStartupOwnership(outputs);
 const index=JSON.parse(outputs['startup-ownership.json']);
 for(const name of retired)assert(!index.files.some(p=>bank+p.path===name),'The control must actually retire this old current part');
 const destination='coordination/engineering/final-bank-test/sparse-retired';
 publishFinalizedDelivery(f.root,destination,outputs,{phase:'finalize'});
 for(const name of retired){assert(!fs.existsSync(path.join(f.root,name)));assert.equal(f.git('ls-files','--stage','--',name).length,0,'Sparse retirement must remove the obsolete index entry');}
 assert.deepEqual(f.git('ls-files','--stage','-v','-z').toString().split('\0').filter(Boolean),
  originalIndex.filter(row=>!retired.some(name=>row.endsWith('\t'+name))),'Every unrelated index identity and flag remains exact');
 assert.equal(f.git('ls-files','--stage','-z','--',fixed).toString(),fixedEntry);assert.equal(f.git('ls-files','-v','--',fixed).toString(),'S '+fixed+'\n');
 publishFinalizedDelivery(f.root,destination,outputs,{phase:'finalize'},true);
 f.git('add','-A');const committed=f.commit();
 const actual=f.git('ls-tree','-r','--name-only',committed,'--',bank).toString().trim().split('\n').sort();
 assert.deepEqual(actual,[bank+'index.json',...index.files.map(p=>bank+p.path)].sort(),'Normal staging commits exactly the final bank, without retired sparse URLs');
 assert.equal(f.git('ls-files','--stage','-z','--',fixed).toString(),fixedEntry);assert.equal(f.git('ls-files','-v','--',fixed).toString(),'S '+fixed+'\n');
 publishFinalizedDelivery(f.root,destination,outputs,{phase:'finalize'},true);
});


test('retiring current-bank paths refuse non-sparse loss, staged replacements and changed index custody',async t=>{
 const {f,before}=await prepare(t),migration=await finalize(f,f.bankCommit),at=f.commit();
 const added=await appendNativeAuthority(f,{membershipPath:'data/source.json',owner:1,name:'coordination/engineering/retirement-guards',completedConstructor:true});
 f.save('data/ownership-selection.json',migration.selection);f.save('coordination/engineering/retirement-guards/registry.json',{version:1,kind:'retained-rule-authority-registry-v1',entries:[added.entry]});
 const source=f.commit(),hook=f.pin('coordination/engineering/retirement-guards/registry.json',source);
 const name=bank+migration.index.preparedOwnership.context_parts[0].path,file=path.join(f.root,name),original=fs.readFileSync(file),oid=f.git('rev-parse',source+':'+name).toString().trim();
 const reader=pinReader(f.root),outputs=finalizeDelivery({version:2,selector:{commit:at,path:'data/ownership-selection.json'},package_inputs:{commit:at,path:'.github/package-inputs.json'},change_evidence:hook},reader);
 await prepareFinalizedStartupOwnership(outputs);assert(!JSON.parse(outputs['startup-ownership.json']).files.some(p=>bank+p.path===name));
 const destination='coordination/engineering/final-bank-test/retirement-guards',publish=(resume=false)=>publishFinalizedDelivery(f.root,destination,outputs,{phase:'finalize'},resume);
 const pristine=()=>{f.git('update-index','--no-assume-unchanged','--no-skip-worktree','--',name);fs.writeFileSync(file,original,{mode:0o644});fs.chmodSync(file,0o644);f.git('add','--',name);};
 for(const mutation of ['missing','deleted-index','staged-bytes','staged-mode','assume-unchanged']){
  if(mutation==='missing')fs.unlinkSync(file);
  if(mutation==='deleted-index')f.git('update-index','--force-remove','--',name);
  if(mutation==='staged-bytes'){fs.writeFileSync(file,Buffer.from('wrong staged input'));f.git('add','--',name);fs.writeFileSync(file,original);}
  if(mutation==='staged-mode')f.git('update-index','--chmod=+x','--',name);
  if(mutation==='assume-unchanged')f.git('update-index','--assume-unchanged','--',name);
  assert.throws(()=>publish(),/Canonical output changed outside|Indexed final-bank retirement differs/,mutation);
  assert(!fs.existsSync(path.join(f.root,destination)),'Invalid preimage refuses before staging');
  if(mutation==='deleted-index')f.git('update-index','--add','--cacheinfo',`100644,${oid},${name}`);
  pristine();
 }
 fs.writeFileSync(file,Buffer.from('different committed preimage'));f.commit();
 assert.throws(()=>publish(),/Committed canonical baseline differs/);pristine();f.commit();
 f.git('rm','--',name);f.commit();f.save(name,original);f.git('add','--',name);
 assert.throws(()=>publish(),/Indexed final-bank retirement differs/,'A removed HEAD path cannot conceal a newly staged replacement');f.commit();
 execFileSync('git',['sparse-checkout','set','--no-cone','--stdin'],{cwd:f.root,input:`/*\n!/${name}\n`,stdio:'pipe'});
 assert(!fs.existsSync(file));assert.equal(f.git('ls-files','-v','--',name).toString(),'S '+name+'\n');
 f.save(name,Buffer.from('changed sparse body'));assert.throws(()=>publish(),/Canonical output changed outside/);fs.unlinkSync(file);
 fs.symlinkSync('missing-sentinel',file);assert.throws(()=>publish(),/Nonordinary canonical output/);fs.unlinkSync(file);
 assert(!fs.existsSync(path.join(f.root,destination)),'Sparse byte/type refusals precede staging');
 const selector=fs.readFileSync(path.join(f.root,'data/ownership-selection.json')),write=fs.writeFileSync;let changed=false;
 fs.writeFileSync=function(filename,...args){const result=write.call(this,filename,...args);
  if(!changed&&typeof filename==='string'&&filename.includes(destination)){changed=true;f.git('update-index','--force-remove','--',name);}return result;};
 try{assert.throws(()=>publish(),/retirement index changed before adoption/);assert(changed);}finally{fs.writeFileSync=write;}
 assert.deepEqual(fs.readFileSync(path.join(f.root,'data/ownership-selection.json')),selector,'Staging-time index changes refuse before selector adoption');
 f.git('update-index','--add','--cacheinfo',`100644,${oid},${name}`);f.git('update-index','--skip-worktree','--',name);
 publish(true);assert.equal(f.git('ls-files','--stage','--',name).length,0);
});


test('finalizer derives complete sparse output preimages without a caller input list',async t=>{
 const {f,before}=await prepare(t),migration=await finalize(f,f.bankCommit),at=f.commit();
 const added=await appendNativeAuthority(f,{membershipPath:'data/source.json',owner:1,name:'coordination/engineering/automatic-preimages',completedConstructor:true});
 f.save('data/ownership-selection.json',migration.selection);f.save('coordination/engineering/automatic-preimages/registry.json',{version:1,kind:'retained-rule-authority-registry-v1',entries:[added.entry]});
 const source=f.commit(),hook=f.pin('coordination/engineering/automatic-preimages/registry.json',source);
 execFileSync('git',['sparse-checkout','set','--no-cone','--stdin'],{cwd:f.root,input:'/*\n!/data/\n!/.github/package-inputs.json\n',stdio:'pipe'});
 for(const name of ['data/ownership-selection.json','.github/package-inputs.json',bank+'index.json']){
  assert(!fs.existsSync(path.join(f.root,name)));assert.equal(f.git('ls-files','-v','--',name).toString(),'S '+name+'\n');
 }
 const initial=f.git('ls-files','--stage','-v','-z').toString().split('\0').filter(Boolean),normal=pinReader(f.root),calls=[];
 const reader={...normal,git(...args){if(args[0]==='sparse-checkout')calls.push(args);return normal.git(...args);}};
 const outputs=finalizeDelivery({version:2,selector:{commit:at,path:'data/ownership-selection.json'},package_inputs:{commit:at,path:'.github/package-inputs.json'},change_evidence:hook},reader);
 await prepareFinalizedStartupOwnership(outputs);const index=JSON.parse(outputs['startup-ownership.json']);
 const destination='coordination/engineering/final-bank-test/automatic-preimages';
 publishFinalizedDelivery(f.root,destination,outputs,{phase:'finalize'});
 assert.equal(calls.length,1);assert.deepEqual(calls[0].slice(0,3),['sparse-checkout','add','--']);
 const requested=new Set(calls[0].slice(3).map(name=>name.slice(1)));
 for(const name of ['data/ownership-selection.json','.github/package-inputs.json',bank+'index.json'])assert(requested.has(name));
 const current=new Set([...migration.index.pixelMap.parts,...migration.index.preparedOwnership.context_parts].map(p=>p.path));
 for(const pin of migration.index.compatibility_files.filter(p=>!current.has(p.path))){
  assert(!requested.has(bank+pin.path));assert(!fs.existsSync(path.join(f.root,bank+pin.path)));assert.equal(f.git('ls-files','-v','--',bank+pin.path).toString(),'S '+bank+pin.path+'\n');
 }
 const retired=new Set(migration.index.files.filter(p=>!index.files.some(next=>next.path===p.path)).map(p=>bank+p.path));
 const expected=initial.filter(row=>![...retired].some(name=>row.endsWith('\t'+name))).map(row=>requested.has(row.split('\t')[1])?row.replace(/^S /,'H '):row);
 assert.deepEqual(f.git('ls-files','--stage','-v','-z').toString().split('\0').filter(Boolean),expected,'Only planned output inclusions and exact retirements change index flags/entries');
 assert.deepEqual(fs.readFileSync(path.join(f.root,'data/ownership-selection.json')),outputs['ownership-selection.json']);
 publishFinalizedDelivery(f.root,destination,outputs,{phase:'finalize'},true);
 f.git('add','-A');const committed=f.commit();
 assert.deepEqual(f.git('ls-tree','-r','--name-only',committed,'--',bank).toString().trim().split('\n').sort(),[bank+'index.json',...index.files.map(p=>bank+p.path)].sort());
 assert.deepEqual(f.git('show',committed+':data/ownership-selection.json'),outputs['ownership-selection.json']);
 publishFinalizedDelivery(f.root,destination,outputs,{phase:'finalize'},true);
});


test('automatic sparse preimages refuse deleted, staged, edited and racing canonical state',async t=>{
 const {f,before}=await prepare(t);
 const normal=pinReader(f.root),calls=[];let duringMaterialization=false;
 const reader={...normal,git(...args){if(args[0]==='sparse-checkout')calls.push(args);const result=normal.git(...args);
  if(duringMaterialization&&args[0]==='sparse-checkout')f.git('update-index','--add','--cacheinfo',`100644,${bad},${name}`);return result;}};
 const outputs=finalizeDelivery({version:2,selector:{commit:f.bankCommit,path:'data/ownership-selection.json'},package_inputs:{commit:f.bankCommit,path:'.github/package-inputs.json'}},reader);
 await prepareFinalizedStartupOwnership(outputs);
 const name='data/ownership-selection.json',file=path.join(f.root,name),original=f.git('show',f.bankCommit+':'+name),oid=f.git('rev-parse',f.bankCommit+':'+name).toString().trim();
 execFileSync('git',['sparse-checkout','set','--no-cone','--stdin'],{cwd:f.root,input:'/*\n!/data/\n!/.github/package-inputs.json\n',stdio:'pipe'});
 const destination='coordination/engineering/final-bank-test/preimage-refusals',publish=(resume=false)=>publishFinalizedDelivery(f.root,destination,outputs,{phase:'finalize'},resume);
 const reset=()=>{if(fs.lstatSync(file,{throwIfNoEntry:false}))fs.unlinkSync(file);f.git('update-index','--add','--cacheinfo',`100644,${oid},${name}`);f.git('update-index','--no-assume-unchanged','--',name);f.git('update-index','--skip-worktree','--',name);assert.equal(f.git('ls-files','-v','--',name).toString(),'S '+name+'\n');};
 const bad=f.git('hash-object','-w','--stdin').toString().trim();
 for(const mutation of ['ordinary-loss','staged-deletion','staged-bytes','staged-mode','assume-unchanged','edited','symlink']){
  if(mutation==='ordinary-loss')f.git('update-index','--no-skip-worktree','--',name);
  if(mutation==='staged-deletion')f.git('update-index','--force-remove','--',name);
  if(mutation==='staged-bytes'){f.git('update-index','--add','--cacheinfo',`100644,${bad},${name}`);f.git('update-index','--skip-worktree','--',name);}
  if(mutation==='staged-mode'){f.git('update-index','--add','--cacheinfo',`100755,${oid},${name}`);f.git('update-index','--skip-worktree','--',name);}
  if(mutation==='assume-unchanged')f.git('update-index','--assume-unchanged','--',name);
  if(mutation==='edited')f.save(name,Buffer.from('user edit'));
  if(mutation==='symlink'){fs.mkdirSync(path.dirname(file),{recursive:true});fs.symlinkSync('missing',file);}
  assert.throws(()=>publish(),/Indexed canonical output differs|Canonical output changed outside|Nonordinary canonical output/,mutation);
  assert(!fs.existsSync(path.join(f.root,destination)));assert.equal(calls.length,0,'Invalid state refuses before materialization');reset();
 }
 const packageFile=path.join(f.root,'.github/package-inputs.json');f.save('.github/package-inputs.json',Buffer.from('unrelated output edit'));
 assert.throws(()=>publish(),/Canonical output changed outside/);assert.equal(calls.length,0);assert(!fs.existsSync(file));fs.unlinkSync(packageFile);
 const write=fs.writeFileSync;let changed=false;
 fs.writeFileSync=function(filename,...args){const result=write.call(this,filename,...args);
  if(!changed&&typeof filename==='string'&&filename.includes(destination)){changed=true;f.git('update-index','--force-remove','--',name);}return result;};
 try{assert.throws(()=>publish(),/Canonical output index changed before materialization/);assert(changed);}finally{fs.writeFileSync=write;}
 assert.equal(calls.length,0);assert(!fs.existsSync(file));reset();
 duringMaterialization=true;assert.throws(()=>publish(true),/Canonical output index changed during materialization/);
 assert.deepEqual(fs.readFileSync(file),original,'A materialization-time index race refuses before selector adoption');duringMaterialization=false;reset();
 publish(true);assert.equal(calls.length,2);assert.deepEqual(fs.readFileSync(file),outputs['ownership-selection.json']);
});


test('normal finalize CLI automatically materializes its sparse canonical preimages',async t=>{
 const {f,before}=await prepare(t);
 const config='coordination/engineering/final-bank-test/automatic-cli.json',destination='.cache/delivery-handoff/automatic-cli';
 f.save(config,{version:2,selector:{commit:f.bankCommit,path:'data/ownership-selection.json'},package_inputs:{commit:f.bankCommit,path:'.github/package-inputs.json'}});
 execFileSync('git',['sparse-checkout','set','--no-cone','--stdin'],{cwd:f.root,input:'/*\n!/data/\n!/.github/package-inputs.json\n',stdio:'pipe'});
 assert(!fs.existsSync(path.join(f.root,'data/ownership-selection.json')));
 const entry=fileURLToPath(new URL('../scripts/prepare-delivery-handoff.mjs',import.meta.url));
 const run=flags=>execFileSync(process.execPath,[entry,'finalize',config,destination,...flags],{cwd:f.root,env:{...process.env,GIT_NO_LAZY_FETCH:'1',GIT_NO_REPLACE_OBJECTS:'1'},encoding:'utf8',stdio:'pipe'});
 run([]);
 const selection=JSON.parse(fs.readFileSync(path.join(f.root,'data/ownership-selection.json'))),index=JSON.parse(fs.readFileSync(path.join(f.root,bank+'index.json')));
 assert.equal(selection.version,2);assert.equal(selection.prepared_bank.sha256,createHash('sha256').update(fs.readFileSync(path.join(f.root,bank+'index.json'))).digest('hex'));
 assert.deepEqual(fs.readFileSync(path.join(f.root,'data/ownership-selection.json')),fs.readFileSync(path.join(f.root,destination,'ownership-selection.json')));
 run(['--resume']);f.git('add','-A');const committed=f.commit();
 assert.deepEqual(f.git('ls-tree','-r','--name-only',committed,'--',bank).toString().trim().split('\n').sort(),[bank+'index.json',...index.files.map(p=>bank+p.path)].sort());
});

test('actual finalizer CLI adopts a proposed withdrawal bank through the ordinary writer and exact resume',async t=>{
 const {f,before}=await prepare(t),migration=await finalize(f,f.bankCommit),at=f.commit();
 const added=await appendNativeAuthority(f,{membershipPath:'data/source.json',owner:1,name:'withdrawal-source',completedConstructor:true});
 f.save('data/ownership-selection.json',migration.selection);
 f.save('withdrawal-source/only.json',{version:1,kind:'retained-rule-authority-registry-v1',entries:[added.entry]});
 const issued=f.commit(),hook=f.pin('withdrawal-source/only.json',issued);
 await finalize(f,at,{change_evidence:hook},'coordination/engineering/final-bank-test/positive');const current=f.commit();
 const config={version:2,selector:{commit:current,path:'data/ownership-selection.json'},
  package_inputs:{commit:current,path:'.github/package-inputs.json'},proposed_selector:{commit:at,path:'data/ownership-selection.json'}};
 f.save('.cache/delivery-handoff/withdrawal-config.json',config);
 const command=fileURLToPath(new URL('../scripts/prepare-delivery-handoff.mjs',import.meta.url));
 const args=[command,'finalize','.cache/delivery-handoff/withdrawal-config.json','coordination/engineering/final-bank-test/withdrawal'];
 const env={...process.env};delete env.NODE_OPTIONS;delete env.NODE_PATH;
 const actual=spawnSync(process.execPath,args,{cwd:f.root,env,encoding:'utf8'});assert.equal(actual.status,0,actual.stderr);
 assert.deepEqual(JSON.parse(fs.readFileSync(path.join(f.root,'data/ownership-selection.json'))),migration.selection);
 const resumed=spawnSync(process.execPath,[...args,'--resume'],{cwd:f.root,env,encoding:'utf8'});assert.equal(resumed.status,0,resumed.stderr);
 const candidate=f.commit(),beforeReader=new f.native.ImmutableReader(f.root,current),afterReader=new f.native.ImmutableReader(f.root,candidate,{invocation:beforeReader.invocation});
 const report=await f.api.compareAcceptedFinalBank({beforeReader,afterReader});
 assert.equal(report.status,'validated-native-map-transition');assert.equal(report.removed_cells,1);assert.equal(report.reassigned_cells,0);
 assert.equal(report.repair_visibility.new_components,0);
 assert(!report.input_inventory.some(p=>p.path.startsWith('withdrawal-source/')),'Withdrawal never reopens the positive source constructor');
 const source=pinReader(f.root);
 assert.throws(()=>finalizeDelivery({...config,change_evidence:hook},source),/already carries its complete/);
});

test('retired version-1 finalization and composition refuse before reading any operand',async()=>{
 const reader=new Proxy({}, {get(){throw Error('Retired route read an operand');}});
 assert.throws(()=>finalizeDelivery({version:1},reader),/requires final-map version 2/);
 await assert.rejects(composeAuthorities({version:1},reader),/requires final-map version 2/);
});


test('accepted-map supported inputs construct and finalize only the genuinely novel cells',async t=>{
 const {f}=await prepare(t),baseline=f.bankCommit;
 const first=await appendNativeAuthority(f,{membershipPath:'data/source.json',owner:1,name:'coordination/engineering/incremental-first',completedConstructor:true});
 const compose=async(entry,at,name)=>{
  const reader=pinReader(f.root),binding=reader.json(entry.source_authority);
  const outputs=await composeAuthorities({version:2,selector:f.pin('data/ownership-selection.json',at),authorities:[{
   rule_preimage:entry.rule_preimage,source_authority:entry.source_authority,ledger:entry.completed_constructor,native_patch:binding.native_patch}]},reader);
  f.save(name,outputs['authority-registry.json']);return f.pin(name,f.commit());
 };
 f.save('data/ownership-selection.json',JSON.parse(f.git('show',baseline+':data/ownership-selection.json')));
 const firstHook=await compose(first.entry,baseline,'coordination/engineering/incremental-first/registry.json');
 await finalize(f,baseline,{change_evidence:firstHook},'coordination/engineering/incremental-first/final');const accepted=f.commit();
 const {x,y}=first;
 const full=await appendNativeAuthority(f,{membershipPath:'data/source.json',owner:1,name:'coordination/engineering/incremental-full',completedConstructor:true,
  nativePatchRows:[{y,runs:[[x,x+3,2]]}],mutateEvidence:e=>{for(const target of e.targets)target.coverage_rows=[{y,runs:[[x,x+3,'mapped_land_support']]}];}});
 f.save('data/ownership-selection.json',JSON.parse(f.git('show',accepted+':data/ownership-selection.json')));
 const fullHook=await compose(full.entry,accepted,'coordination/engineering/incremental-full/registry.json');
 await assert.rejects(finalize(f,accepted,{change_evidence:fullHook},'coordination/engineering/incremental-full/refused'),/would replace an assigned cell/);
 const binding=pinReader(f.root).json(full.entry.source_authority),locator=p=>({commit:p.commit,path:p.path});
 const diagnostic=await nativeAuthority({version:1,source_evidence:locator(binding.source_evidence),native_patch:locator(binding.native_patch)},pinReader(f.root),f.root,true);
 assert.equal(diagnostic.observation.supported_cells,3);
 f.save('coordination/engineering/incremental-full/diagnostic.json',diagnostic.products['native-diagnostic.json']);const diagnosticAt=f.commit();
 const prepared=await supportedInputs({version:1,diagnostic:{commit:diagnosticAt,path:'coordination/engineering/incremental-full/diagnostic.json'},
  accepted_selector:{commit:accepted,path:'data/ownership-selection.json'}},pinReader(f.root));
 const account=JSON.parse(prepared['original-scope-partition.json']);assert.equal(account.original_cells,3);assert.equal(account.already_present_cells,1);assert.equal(account.supported_cells,2);
 assert.deepEqual(JSON.parse(prepared['native-patch.json']).rows,[{y,runs:[[x+1,x+3,2]]}]);
 for(const [name,raw]of Object.entries(prepared))f.save('coordination/engineering/incremental-novel/'+name,raw);
 const preparedAt=f.commit(),inputs={version:1,source_evidence:{commit:preparedAt,path:'coordination/engineering/incremental-novel/source-evidence.json'},native_patch:{commit:preparedAt,path:'coordination/engineering/incremental-novel/native-patch.json'}};
 const qualified=await nativeAuthority(inputs,pinReader(f.root),f.root);assert.equal(qualified.observation.qualified_cells,2);
 const destination='coordination/engineering/incremental-novel/authority';
 publishOwnedProducts(f.root,destination,qualified.products,{phase:'native-authority',fixture:true});const authorityAt=f.commit();
 const entry={rule_preimage:f.pin(destination+'/original-rule-preimage.json',authorityAt),source_authority:f.pin(destination+'/authority-binding.json',authorityAt),completed_constructor:f.pin(destination+'/constructor-result.json',authorityAt)};
 const hook=await compose(entry,accepted,'coordination/engineering/incremental-novel/registry.json');
 await finalize(f,accepted,{change_evidence:hook},'coordination/engineering/incremental-novel/final');const candidate=f.commit();
 const report=await compareFinal(f,accepted,candidate);assert.equal(report.added_cells,2);assert.equal(report.removed_cells,0);assert.equal(report.reassigned_cells,0);
 assert.deepEqual(report.changes,[{row:y,start:x+1,end:x+3,previous_owner:null,candidate_owner:'B'}]);
});

// Real immutable Git readers and the existing canonical final-bank loader own
// acceptance input authentication; no caller-supplied ownership map is trusted.
async function acceptedFixture(t) {
  const {trustedFixture} = await import('./fixtures/selected-checkpoint.mjs');
  const {initialFinalBank} = await import('./fixtures/final-bank.mjs');
  const {pinReader} = await import('../scripts/prepare-delivery-handoff.mjs');
  const f = await trustedFixture(t, {nativeAppend:true, finalBank:true});
  await initialFinalBank(f);
  const selectorCommit = f.git('rev-parse','HEAD').toString().trim();
  const contract = Object.fromEntries(['size','coordinateBits','method','native_latitudes','hierarchy_sha256','original_assets'].map(k=>[k,f.manifest[k]]));
  async function run({supported=[[2,4,1]], held=[[4,5,1]], mutateSource=()=>{}, mutateDiagnostic=()=>{}, mutateSelector=()=>{}, mutateReader=()=>{}, priorHoldRuns, accepted=true}={}) {
    f.git('reset','--hard',selectorCommit);
    const requested=[...supported,...held].sort((a,b)=>a[0]-b[0]);
    const source={version:1,kind:'source-target-native-evidence-v1',native_contract:contract,base_reference:f.envelope.base_reference,
      families:[{original:'complete retained source'}],negative_sources:[{original:'complete foreign family'}],
      targets:[{id:'member-a',target_id:'A',pixelIndex:1,source_members:['a','b'],
        coverage_rows:[{y:1,runs:requested.map(([a,b])=>[a,b,'mapped_land_support'])}]}]};
    mutateSource(source);
    f.save('incremental/source.json',source);f.save('incremental/patch.json',{rows:[{y:1,runs:requested}]});
    const inputsAt=f.commit(),pins={source_evidence:f.pin('incremental/source.json',inputsAt),native_patch:f.pin('incremental/patch.json',inputsAt)};
    const count=r=>r.reduce((n,[a,b])=>n+b-a,0);
    const diagnostic={version:1,kind:'source-target-native-diagnostic-v1',native_contract:contract,original_pins:pins,
      rule_sha256:digest(jsonBytes({version:1,kind:'source-target-native-rule-v1',...pins})),
      requested_rows:[{y:1,runs:requested}],supported_rows:supported.length?[{y:1,runs:supported}]:[],held_rows:held.length?[{y:1,runs:held}]:[],
      decision_rows:[{y:1,runs:[...supported.map(r=>[...r,'assigned_cells']),...held.map(r=>[...r,'territorial_exclusion_cells'])].sort((a,b)=>a[0]-b[0])}],
      requested_cells:count(requested),supported_cells:count(supported),held_cells:count(held)};
    mutateDiagnostic(diagnostic);f.save('incremental/diagnostic.json',diagnostic);const at=f.commit();
    const config={version:1,diagnostic:{commit:at,path:'incremental/diagnostic.json'},
      ...(accepted?{accepted_selector:{commit:selectorCommit,path:'data/ownership-selection.json'}}:{})};
    if(priorHoldRuns){f.save('incremental/prior-holds.json',{rows:[{y:1,runs:priorHoldRuns}]});config.prior_holds={commit:f.commit(),path:'incremental/prior-holds.json'};}
    mutateSelector(config,f);
    const reader=pinReader(f.root);mutateReader(reader);
    const output=await supportedInputs(config,reader);
    return {output:Object.fromEntries(Object.entries(output).map(([name,raw])=>[name,JSON.parse(raw)])),source,diagnostic,pins,config};
  }
  return {...f,run,selectorCommit};
}

test('accepted final map partitions full support into exact novel/already-present/held keys',async t=>{
 const f=await acceptedFixture(t);
 for(const [name,supported,held,novel,present] of [
  ['mixed',[[2,4,1]],[[4,5,1]],[[3,4,1]],[[2,3,1]]],
  ['all novel',[[10,12,1]],[[12,13,1]],[[10,12,1]],[]],
  ['zero novel',[[2,3,1]],[[4,5,1]],[],[[2,3,1]]],
  ['entirely held',[],[[2,3,1]],[],[]],
  ['full-width intervals',[[2,262166,1]],[],[[3,262166,1]],[[2,3,1]]]
 ])await t.test(name,async()=>{
  const {output:o,source,diagnostic,pins}=await f.run({supported,held});
  assert.deepEqual(o['native-patch.json'].rows,novel.length?[{y:1,runs:novel}]:[]);
  assert.deepEqual(o['already-present-original.json'].rows,present.length?[{y:1,runs:present}]:[]);
  assert.deepEqual(o['held-original.json'].rows,held.length?[{y:1,runs:held.map(r=>[...r,'territorial_exclusion_cells'])}]:[]);
  assert.deepEqual(o['source-evidence.json'],{...source,targets:novel.length?source.targets.map(target=>({...target,coverage_rows:[{y:1,runs:novel.map(([a,b])=>[a,b,'mapped_land_support'])}]})):[]});
  const a=o['original-scope-partition.json'];assert.equal(a.original_cells,a.supported_cells+a.already_present_cells+a.held_cells);
  assert.equal(a.native_supported_cells,diagnostic.supported_cells);assert.deepEqual(a.original_inputs,pins);
  assert(a.accepted_input_inventory.some(p=>p.path.endsWith('/index.json')));
  for(const owner of a.owners)assert.equal(owner.original_cells,owner.supported_cells+owner.already_present_cells+owner.held_cells);
 });
 await t.test('prior holds cannot become already-present or novel authority',async()=>{
  const {output:o}=await f.run({priorHoldRuns:[[2,4,1,'prior-unresolved']]});
  assert.deepEqual(o['native-patch.json'].rows,[]);assert.deepEqual(o['already-present-original.json'].rows,[]);
  assert.deepEqual(o['held-original.json'].rows,[{y:1,runs:[[2,4,1,'prior-unresolved'],[4,5,1,'territorial_exclusion_cells']]}]);
  const a=o['original-scope-partition.json'];assert.equal(a.original_cells,3);assert.equal(a.held_cells,3);assert.equal(a.already_present_cells,0);
 });
 await t.test('omitting selector retains complete original supported route',async()=>{
  const {output:o}=await f.run({accepted:false});assert.deepEqual(o['native-patch.json'].rows,[{y:1,runs:[[2,4,1]]}]);
  assert(!Object.hasOwn(o,'already-present-original.json'));assert(!Object.hasOwn(o['original-scope-partition.json'],'accepted_selector'));
 });
});

test('incremental support refuses conflicts, identity substitutions and incomplete accepted state',async t=>{
 const f=await acceptedFixture(t);
 const cases=[
  ['unexpected replacement operand',{mutateSelector:c=>c.source_evidence={}},/Explicit incremental supported-input locators/],
  ['different occupied owner',{supported:[[0,1,1]],held:[]},/conflicts with accepted owner/],
  ['foreign target identity',{mutateSource:s=>s.targets[0].target_id='B'},/owner identity differs/],
  ['missing target identity',{mutateSource:s=>delete s.targets[0].target_id},/owner identity differs/],
  ['native contract substitution',{mutateSource:s=>s.base_reference={...s.base_reference,id:'geography:foreign'}},/original native contract/],
  ['noncanonical selector path',{mutateSelector:c=>c.accepted_selector.path='incremental/source.json'},/Canonical accepted selector/],
  ['missing immutable selector',{mutateSelector:c=>c.accepted_selector.commit='0'.repeat(40)},/Missing ordinary|not a tree|bad object|Not a valid object/],
  ['stale committed selection',{mutateSelector:(_c,f)=>{const s=JSON.parse(f.git('show','HEAD:data/ownership-selection.json'));s.reference.id='geography:stale';f.save('data/ownership-selection.json',s);f.commit();}},/differs from current committed selection/],
  ['mismatched accepted native manifest',{mutateSelector:(c,f)=>{const s=JSON.parse(f.git('show','HEAD:data/ownership-selection.json'));s.native_selection.sha256='0'.repeat(64);f.save('data/ownership-selection.json',s);c.accepted_selector.commit=f.commit();}},/Accepted native manifest differs/],
  ['incomplete original owner coverage',{mutateSource:s=>s.targets[0].coverage_rows[0].runs.shift()},/coverage rows differ/],
  ['missing accepted body',{mutateReader:r=>{const read=r.read;r.read=p=>{if((p.path.startsWith('data/canonical-grid/current-startup/')&&!p.path.endsWith('/index.json')))throw Error('Fixture required accepted body unavailable');return read(p);};}},/required accepted body unavailable/],
  ['altered accepted body',{mutateReader:r=>{const read=r.read;r.read=p=>{const raw=read(p);return (p.path.startsWith('data/canonical-grid/current-startup/')&&!p.path.endsWith('/index.json'))?Buffer.from(raw).fill(0):raw;};}},/whole identity differs/]
 ];
 for(const [name,options,pattern]of cases)await t.test(name,async()=>{await assert.rejects(f.run(options),pattern);});
});

test('stock supported-inputs CLI awaits accepted-map preparation and preserves exact resume',async t=>{
  const f=await acceptedFixture(t),{config,output}=await f.run();
  f.save('incremental/config.json',config);f.commit();
  const env={...process.env};delete env.NODE_PATH;delete env.NODE_OPTIONS;
  const args=[path.resolve('scripts/prepare-delivery-handoff.mjs'),'supported-inputs','incremental/config.json','coordination/engineering/incremental-test/output'];
  for(const flags of [[],['--resume']]){
   const run=spawnSync(process.execPath,[...args,...flags],{cwd:f.root,env,encoding:'utf8'});
   assert.equal(run.status,0,run.stderr);
   for(const [name,value]of Object.entries(output))assert.deepEqual(JSON.parse(fs.readFileSync(path.join(f.root,'coordination/engineering/incremental-test/output',name))),value);
  }
 });

test('stock completed-custody CLI preserves private originals and genuine finalizer qualification',async t=>{
 const {f}=await prepare(t),migration=await finalize(f,f.bankCommit),base=f.commit();
 const added=await appendNativeAuthority(f,{membershipPath:'data/source.json',owner:1,name:'coordination/engineering/projected-next',completedConstructor:true});
 f.save('data/ownership-selection.json',migration.selection);
 const reader=pinReader(f.root),binding=reader.json(added.entry.source_authority);
 const composed=await composeAuthorities({version:2,selector:f.pin('data/ownership-selection.json',base),authorities:[{
  rule_preimage:added.entry.rule_preimage,source_authority:added.entry.source_authority,ledger:added.entry.completed_constructor,native_patch:binding.native_patch}]},reader);
 f.save('coordination/engineering/projected-next/registry.json',JSON.parse(composed['authority-registry.json']));const original=f.commit();
 const originals=[added.entry.completed_constructor,binding.source_evidence],bytes=originals.map(p=>reader.read(p));
 const config={version:1,accepted_selector:{commit:base,path:'data/ownership-selection.json'},
  authority_registry:{commit:original,path:'coordination/engineering/projected-next/registry.json'}};
 f.save('custody-config.json',config);
 const destination='coordination/engineering/projected-custody/output',args=[path.resolve('scripts/prepare-delivery-handoff.mjs'),'completed-custody','custody-config.json',destination];
 const run=extra=>spawnSync(process.execPath,[...args,...extra],{cwd:f.root,encoding:'utf8',env:{...process.env,NODE_OPTIONS:'',NODE_PATH:''},timeout:30000});
 const first=run([]);assert.equal(first.status,0,first.stderr);
 const registry=JSON.parse(fs.readFileSync(path.join(f.root,destination,'authority-registry.json')));
 assert.deepEqual(registry.entries,[added.entry]);assert.equal(registry.completed_geometry_custody.length,1);
 assert.equal(registry.completed_geometry_custody[0].completed_constructor.native_bounds,'accepted-native-centres-v1');
 assert(registry.completed_geometry_custody[0].completed_constructor.body.ledger_rows.every(row=>!Object.hasOwn(row,'native_bounds')));
 assert(!Object.hasOwn(registry.completed_geometry_custody[0].source_evidence,'native_bounds'));
 const resumed=run(['--resume']);assert.equal(resumed.status,0,resumed.stderr);
 for(let i=0;i<originals.length;i++)assert.deepEqual(reader.read(originals[i]),bytes[i]);
 const projected=f.commit(),hook=f.pin(destination+'/authority-registry.json',projected);
 await finalize(f,base,{change_evidence:hook},'coordination/engineering/projected-finalized/output');const candidate=f.commit();
 const report=await compareFinal(f,base,candidate);
 assert.equal(report.native_row_scope.added_cells,1);assert.equal(report.completed_geometry_custody.length,1);
});
