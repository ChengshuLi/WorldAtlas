// Exactly the approved unchanged v6→v7 stage, followed by the two-target v7→v8 stage.
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import{execFile}from'node:child_process';import{gunzipSync}from'node:zlib';import{createHash}from'node:crypto';import{fileURLToPath}from'node:url';
import{restoreWholeImage}from'../eastern-two-gap-repair-native-20261007/whole-image.mjs';import{restoreCanonicalProducts,getRestoredCanonicalProducts,restoredContextMember,restoredContextPatch}from'../eastern-two-gap-repair-native-20261007/restore-canonical-products.mjs';import{validateContextMigration}from'../../../scripts/native-ownership/validate-context-migration.mjs';
import{candidateBudget,requirePlainExecution}from'../../../scripts/native-ownership/native-preparation-guards.mjs';import{repositoryReader,safeEvidencePath}from'../../../scripts/evidence-quality.mjs';
import{validateNativeSelectionReceipt}from'../../../scripts/native-ownership/require-verified-selection.mjs';
import{BEFORE,AFTER,TARGETS}from'../eastern-two-gap-repair-native-20261007/native-producer.mjs';
import{isDeepStrictEqual,promisify}from'node:util';
import{rebindCoverageManifest}from'../../../scripts/rebind-coverage-manifest.mjs';
import{requireCurrentExecution,admitCurrentExecution}from'../eastern-two-gap-repair-native-20261007/current-execution.mjs';
import{acquireOriginalContextPair,constructAliasedContextChunk,readContextBody}from'../eastern-two-gap-repair-native-20261007/context-record-alias.mjs';
import{applyBytePatch,verifyWholeBytes}from'../eastern-two-gap-repair-native-20261007/byte-patch.mjs';
import{requireValidatedGeometryMigrations}from'../../../scripts/prepare-geographic-release.mjs';
// Current wrapper plumbing only. Archived stages and algorithm banks remain
// literal; the package boundary authenticates this separately executing body.
const successfulContexts=new WeakMap();
function freezeContext(value){
 if(value&&typeof value==='object'&&!Object.isFrozen(value)){
  for(const child of Object.values(value))freezeContext(child);Object.freeze(value);
 }return value;
}
function retainSuccessfulContext(result,rows,index,enabled=false){
 assert.equal(typeof enabled,'boolean');if(!enabled)return result;
 assert.equal(result.receipt.status,'verified');
 requireValidatedGeometryMigrations(result.geometryValidation);
 requireValidatedGeometryMigrations(result.coverageContinuation.originalGeometryValidation);
 assert.equal(rows.length,49625);assert.equal(new Set(rows.map(row=>row.id)).size,49625);
 assert.equal(index.locations,49625);assert.equal(index.footprints_sha256,AFTER);
 assert.equal(index.owner_sha256,result.receipt.migration.owner_sha256);
 successfulContexts.set(result,{receipt_sha256:sha(JSON.stringify(result.receipt)),
  rows:freezeContext(rows),index:freezeContext(index)});
 return result;
}
export function getSuccessfulChainedContext(result){
 const saved=successfulContexts.get(result);assert(saved,'Actual successful chained validation identity required');
 assert.equal(sha(JSON.stringify(result.receipt)),saved.receipt_sha256,'Validated receipt changed');
 requireValidatedGeometryMigrations(result.geometryValidation);
 requireValidatedGeometryMigrations(result.coverageContinuation.originalGeometryValidation);
 return Object.freeze({rows:saved.rows,index:saved.index});
}
const executeFile=promisify(execFile);
// Preserve the replay boundary; bound only the original child old-space, not the plain outer Node.
export async function replayOriginalV1(runner,image){
 const {stdout}=await executeFile(process.execPath,['--max-old-space-size=1536',runner],{cwd:image,env:{...process.env,WORLDATLAS_PACKAGE_STAGE:image},maxBuffer:32*1024*1024,encoding:'buffer'});
 return stdout;
}
const sha=b=>createHash('sha256').update(b).digest('hex');
export function selectBuildContextValidator(stage,{legacy,current}){
 assert.equal(typeof legacy,'function');assert.equal(typeof current,'function');
 if(stage?.version===2){
  assert.equal(stage.kind,'retained-identity-context-continuation-v2');
  assert.equal(stage.issue,1295);
  return current;
 }
 return legacy;
}
export const FIXED_PRIOR_STAGE_SHA='471e6a71856c13b5856cd74f24b79cc9961b3b091980e8b9106a19c1f32a2765';
export const FIXED_NATIVE_COMPARISON_SHA='3e5d3a3f06d7e5340fea11b90deb8acc97d9e0c38f067e455e81359602b0aa28';
export const FIXED_PRIOR_VALIDATOR_SHA='5b6da335c43e438a7fefac264b01d7aafeeba8096dc808a22475e07caa63a4e7';
// Lossless in-memory aliases only after complete decoded bytes were authenticated.
export function shareUnchangedContextGeometry(rows,reference){
 const byId=new Map(reference.map(f=>[f.id,f.geometry]));assert.equal(byId.size,reference.length);
 let shared=0;for(const row of rows){const prior=byId.get(row.id);if(prior&&isDeepStrictEqual(row.geometry,prior)&&JSON.stringify(row.geometry)===JSON.stringify(prior)){row.geometry=prior;shared++;}}
 return shared;
}
export const FIXED_MIDDLE_GRID_SHA='70204c43deefd1af97c898f120d3638d4b8a3953445df37036d5771a54d718cc';
// Exactly two authentic retained-identity migrations, with the same middle body.
export function foldCoverageContinuation(manifest,{originalGrid,originalGridSha256,selectedGrid,selectedGridSha256,release,steps}){
 assert(Array.isArray(steps)&&steps.length===2,'Exactly two ordered physical-association steps required');
 assert.deepEqual(steps.map(s=>[s.predecessorRelease.version,s.release.version]),[[6,7],[7,8]],'Physical-association steps must be v6→v7→v8');
 assert.deepEqual(steps[0].release,steps[1].predecessorRelease,'Complete middle release must be identical');
 assert.deepEqual(steps[1].release,release,'Final physical association differs from selected release');
 assert.equal(steps[0].selectedGridSha256,FIXED_MIDDLE_GRID_SHA,'Wrong accepted intermediate native manifest');
 assert.deepEqual(steps[0].selectedGrid,steps[1].originalGrid,'Exact same middle native manifest required');
 assert.equal(steps[0].selectedGridSha256,steps[1].originalGridSha256,'Middle native byte binding changed');
 assert.deepEqual(steps[0].originalGrid,originalGrid);assert.equal(steps[0].originalGridSha256,originalGridSha256);
 assert.deepEqual(steps[1].selectedGrid,selectedGrid);assert.equal(steps[1].selectedGridSha256,selectedGridSha256);
 let result=manifest;const bindings=[];
 for(const step of steps){result=rebindCoverageManifest(result,step);bindings.push(structuredClone(result.ownership_binding));}
 const originalFields=structuredClone(result);delete originalFields.ownership_binding;
 for(const key of ['release_id','footprints_sha256','canonical_grid_sha256'])originalFields[key]=manifest[key];
 assert.deepEqual(originalFields,manifest,'Original classes/sources/blocked tiles/encoded asset bindings must remain unchanged');
 result.ownership_binding.previous_associations=bindings.slice(0,-1);
 return result;
}
export function authenticateSuccessorContextInventory(indexRaw,imageIndex,comparisonRaw){
 assert.equal(sha(comparisonRaw),FIXED_NATIVE_COMPARISON_SHA,'Original complete native comparison binding changed');
 const comparison=JSON.parse(comparisonRaw),original=comparison.products.find(p=>p.path==='context-index.json');
 assert.equal(indexRaw.length,original.bytes);assert.equal(sha(indexRaw),original.sha256,'Original full context index changed');
 const index=JSON.parse(indexRaw);assert.deepEqual(imageIndex.files.map(p=>p.path).sort(),index.parts.map(p=>p.path).sort(),'Complete original context body roster required');
 for(const pin of index.parts){const product=comparison.products.find(p=>p.path===pin.path),retained=imageIndex.files.find(p=>p.path===pin.path);
  assert.equal(pin.bytes,product.bytes);assert.equal(pin.sha256,product.sha256);assert.equal(retained.mode,'100644');assert.equal(retained.bytes,pin.bytes);assert.equal(retained.sha256,pin.sha256);
  assert.equal(retained.original_binding.scientific_execution_commit,'5b32388df0501b013ac9a3ba97864932db493d59');assert.deepEqual(retained.original_binding.original_product,pin,'Original complete scientific context descriptor changed');
 }return index;
}
export function verifyRegistryContinuation(originalRaw,currentRaw,binding){
 assert(binding&&/^[a-f0-9]{64}$/.test(binding.manifest_sha256),'Explicit successor registry binding required');
 const original=JSON.parse(originalRaw),current=JSON.parse(currentRaw);
 assert.equal(original.version,1);assert.equal(current.version,1);assert.deepEqual(Object.keys(current).sort(),Object.keys(original).sort());
 const expected={...original,candidates:{...original.candidates,[binding.manifest_sha256]:binding.pin}};
 assert(!Object.hasOwn(original.candidates,binding.manifest_sha256),'Successor must be a new immutable manifest');
 assert(/^[a-f0-9]{40}$/.test(binding.pin?.commit));assert(/^[a-f0-9]{64}$/.test(binding.pin?.sha256));
 assert.equal(binding.pin.path,'coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/native-selection-receipt.json');
 assert.equal(binding.pin.role,'reviewed-exhaustive-native-rule-comparison');assert.equal(binding.pin.installation_approval,false);
 assert.deepEqual(current,expected,'Entire original registry must remain exact; only one bound successor allowed');
 return {original_entries:Object.keys(original.candidates).length,added_entries:1,manifest_sha256:binding.manifest_sha256};
}
export function verifyAuthoredValidatorSources({stage,codeIndex,authored,currentFiles,currentRoot,registryContinuation,charge=()=>{}}){
 const required=new Set(['package.json']);
 function visit(p){if(required.has(p))return;required.add(p);safeEvidencePath(p);const raw=fs.readFileSync(path.join(authored,p));for(const m of raw.toString('utf8').matchAll(/(?:from\s*|import\s*(?:\(\s*)?)['"]([^'"]+)['"]/g))if(m[1].startsWith('.'))visit(path.posix.normalize(path.posix.join(path.posix.dirname(p),m[1])));}
 visit('scripts/native-ownership/validate-build-context-stage.mjs');assert.deepEqual(stage.validator_sources.map(p=>p.path).sort(),[...required].sort(),'Complete authored validator import closure required');
 const wrappers=new Set(['package.json','scripts/evidence-quality.mjs','scripts/native-ownership/validate-build-context-stage.mjs','coordination/engineering/eastern-two-gap-repair-native-20261007/chained-context.mjs']);
 for(const pin of stage.validator_sources){const member=codeIndex.files.find(p=>p.path===pin.path);assert(member);assert.equal(member.bytes,pin.bytes);assert.equal(member.sha256,pin.sha256);const raw=fs.readFileSync(path.join(authored,pin.path));assert.equal(raw.length,pin.bytes);assert.equal(sha(raw),pin.sha256);charge(raw.length);
  if(!wrappers.has(pin.path)){const current=currentFiles.find(p=>p.path===pin.path);assert(current);if(pin.path==='scripts/native-ownership/verified-candidates.json'&&current.sha256!==pin.sha256){
   assert(currentRoot);const extended=fs.readFileSync(path.join(currentRoot,pin.path));assert.equal(extended.length,current.bytes);assert.equal(sha(extended),current.sha256);verifyRegistryContinuation(raw,extended,registryContinuation);
  }else if(pin.path.endsWith('/restore-canonical-products.mjs')&&current.sha256!==pin.sha256){
   assert(currentRoot,'Exact current restoration extension source required');const extended=fs.readFileSync(path.join(currentRoot,pin.path));assert.equal(sha(extended),current.sha256);
   const start=extended.indexOf(Buffer.from('// Select an exact member')),end=extended.indexOf(Buffer.from('function checkoutMetadata'),start);assert(start>=0&&end>start);
   assert.equal(sha(extended.subarray(start,end)),'6563ec0357559af17da4d14de887e9f06426a73a5e67392cc739aac4188e7e6b','Only the exact reviewed selected-member extension is allowed');
   assert.equal(sha(Buffer.concat([extended.subarray(0,start),extended.subarray(end)])),pin.sha256,'Entire original restoration module must remain byte-identical');
  }else assert.equal(current.sha256,pin.sha256,'Historical numerical/helper algorithm changed; requalification required');if(pin.path!=='scripts/native-ownership/verified-candidates.json')assert.equal(current.bytes,pin.bytes+(current.sha256===pin.sha256?0:2525));assert.equal(current.mode,member.mode);}
 }
 return {authored_files:stage.validator_sources.length,numerical_files_unchanged:stage.validator_sources.filter(p=>!wrappers.has(p.path)&&p.path!=='scripts/native-ownership/verified-candidates.json').length,registry_continuation_requested:registryContinuation!==undefined};
}
export async function validateChainedBuildContext({root,expectedReference,stagePath,stageRaw,stage,readFile,currentExecution,retainContextForContinuation=false,registryContinuation,continuationReservedBytes=0,continuationReservedDescriptors=0}){
 requirePlainExecution();assert.equal(stage.version,2);assert.equal(stage.issue,1295);assert.equal(stage.kind,'retained-identity-context-continuation-v2');assert.equal(stage.lane,'engineering');
 assert.deepEqual(stage.subject_ids,[...TARGETS]);assert.equal(stage.prior_stage_sha256,FIXED_PRIOR_STAGE_SHA);
 assert(Number.isSafeInteger(continuationReservedBytes)&&continuationReservedBytes>=0);assert(Number.isInteger(continuationReservedDescriptors)&&continuationReservedDescriptors>=0);
 assert(continuationReservedBytes===0&&continuationReservedDescriptors===0||retainContextForContinuation===true&&registryContinuation,'Continuation reserve requires explicit guarded successor route');
 const currentAdmission=admitCurrentExecution(currentExecution,[currentExecution.source_root,currentExecution.stage_root]);
 assert(currentAdmission.complete_phase_bytes+continuationReservedBytes<=256*1024*1024,'Current execution and whole continuation exceed cap before runtime/body reads');
 const ordinary=readFile??repositoryReader(root),budget=candidateBudget([],{reserveBytes:currentAdmission.installed_runtime_bytes+131072+continuationReservedBytes,reserveDescriptors:16+continuationReservedDescriptors}),seen=new Map(),admitted=new Set();budget.add({bytes:stageRaw.length});
 function read(pin){safeEvidencePath(pin.path);assert(Number.isSafeInteger(pin.bytes)&&pin.bytes>0&&pin.bytes<=32*1024*1024&&/^[a-f0-9]{64}$/.test(pin.sha256));if(seen.has(pin.path))assert.deepEqual(pin,seen.get(pin.path));
  if(!admitted.has(pin.path)){budget.add({bytes:pin.bytes});admitted.add(pin.path);}
  const raw=ordinary(pin.path,'candidate');assert.equal(raw.length,pin.bytes);assert.equal(sha(raw),pin.sha256);if(!seen.has(pin.path))seen.set(pin.path,pin);return raw;}
 requireCurrentExecution(currentExecution);
 budget.add({bytes:Buffer.byteLength(JSON.stringify(currentExecution)+'\n')});
 for(const physicalRoot of currentAdmission.current_code_physical_roots)for(const pin of currentExecution.files)budget.add({bytes:pin.bytes});
 // These authored sources are historical custody, not assertions about a
 // publisher's later merged checkout. Authenticate them against their fixed bank.
 const codeBase='coordination/engineering/eastern-two-gap-repair-native-20261007/current-consumer-code';
 const codeIndexRaw=ordinary(codeBase+'/index.json','candidate');
 assert.equal(sha(codeIndexRaw),'de4a8f7aac3380fc7c5f1cc06ac9bbf0d170c0921d7ef72d5e46187439a80be9');
 budget.add({bytes:codeIndexRaw.length});const codeIndex=JSON.parse(codeIndexRaw);
 for(const pin of codeIndex.parts)read({path:codeBase+'/'+pin.path,bytes:pin.bytes,sha256:pin.sha256});
 for(const pin of codeIndex.files)budget.add({bytes:pin.bytes});
 const codeParent=path.join(root,'.cache');fs.mkdirSync(codeParent,{recursive:true});assert.equal(fs.realpathSync(codeParent),codeParent);
 const codeTemporary=fs.mkdtempSync(path.join(codeParent,'context-authored-code-'));
 const authored=path.join(codeTemporary,'image');restoreWholeImage(path.join(root,codeBase),authored,{expectedIndexSha:sha(codeIndexRaw)});
 verifyAuthoredValidatorSources({stage,codeIndex,authored,currentFiles:currentExecution.files,currentRoot:root,registryContinuation:retainContextForContinuation?registryContinuation:undefined});
 const imageIndexRaw=read(stage.prior_image),imageIndex=JSON.parse(imageIndexRaw),imageBase=path.posix.dirname(stage.prior_image.path);
 // Complete original transport lineage remains pinned; the prior image was already restored and authenticated before stock readers.
 const parent=path.join(root,'.cache');fs.mkdirSync(parent,{recursive:true});assert.equal(fs.realpathSync(parent),parent);
 const temporary=fs.mkdtempSync(path.join(parent,'native-context-1295-'));
 let image;
 if(stage.prior_image.original_index_sha256){
  assert.equal(stage.prior_image.original_index_sha256,'e34743a84df2aaaa668b4e7b23c4f6870379edfe7eb88a427d6005b47333a393');
  const selected=restoredContextMember(root,'data/native-context-migration/manifest.json',{prior:true});
  assert.equal(selected.original_index_sha256,stage.prior_image.original_index_sha256);
  image=selected.file.slice(0,-'data/native-context-migration/manifest.json'.length-1);
 }else{image=path.join(temporary,'prior');restoreWholeImage(path.join(root,imageBase),image,{expectedIndexSha:stage.prior_image.sha256});}
 const oldStageMember=restoredContextMember(root,'data/native-context-migration/manifest.json',{prior:true});budget.add({bytes:oldStageMember.pin.bytes});const oldStageRaw=readContextBody(oldStageMember.file,oldStageMember.pin);assert.equal(sha(oldStageRaw),FIXED_PRIOR_STAGE_SHA);const oldStage=JSON.parse(oldStageRaw);
 assert.equal(oldStage.version,1);assert.equal(oldStage.kind,'retained-identity-context-migration-v1');assert.equal(oldStage.validator_sources.length,17);
 for(const pin of oldStage.validator_sources){safeEvidencePath(pin.path);budget.add({bytes:pin.bytes});const member=restoredContextMember(root,pin.path,{prior:true});assert.equal(member.pin.bytes,pin.bytes);assert.equal(member.pin.sha256,pin.sha256);const raw=readContextBody(member.file,member.pin);assert.equal(raw.length,pin.bytes);assert.equal(sha(raw),pin.sha256);}
 assert.equal(sha(fs.readFileSync(path.join(image,'scripts/native-ownership/validate-build-context-stage.mjs'))),FIXED_PRIOR_VALIDATOR_SHA);
 const oldRegistryMember=restoredContextMember(root,oldStage.releases.path,{prior:true});assert.equal(oldRegistryMember.pin.bytes,oldStage.releases.bytes);assert.equal(oldRegistryMember.pin.sha256,oldStage.releases.sha256);budget.add({bytes:oldStage.releases.bytes});const oldRegistryWire=readContextBody(oldRegistryMember.file,oldRegistryMember.pin);assert.equal(oldRegistryWire.length,oldStage.releases.bytes);assert.equal(sha(oldRegistryWire),oldStage.releases.sha256);
 const decodeRegistry=raw=>{const bytes=raw.readUInt32LE(raw.length-4);budget.add({bytes});const decoded=gunzipSync(raw,{maxOutputLength:32*1024*1024});assert.equal(decoded.length,bytes);return JSON.parse(decoded);};
 const oldRegistry=decodeRegistry(oldRegistryWire);
 const registry=decodeRegistry(read(stage.releases));assert.equal(registry.releases.length,8);assert.deepEqual(registry.releases.slice(0,7),oldRegistry.releases);
 assert.deepEqual(registry.batches.slice(0,oldRegistry.batches.length),oldRegistry.batches);assert.deepEqual(registry.sources_batches.slice(0,oldRegistry.sources_batches.length),oldRegistry.sources_batches);
 assert.equal(registry.original_catalog_sha256,oldRegistry.original_catalog_sha256);const predecessor=registry.releases.at(-2),release=registry.releases.at(-1);
 assert.equal(predecessor.footprints_sha256,BEFORE);assert.equal(release.footprints_sha256,AFTER);assert.equal(predecessor.id,stage.predecessor_release_id);assert.equal(release.id,stage.successor_release_id);assert.deepEqual(release,expectedReference);
 const oldValidatorPath="./scripts/native-ownership/validate-build-context-stage.mjs";
 const command="import fs from 'node:fs';import{gunzipSync}from'node:zlib';import{validateBuildContextStage}from "+JSON.stringify(oldValidatorPath)+";const s=JSON.parse(fs.readFileSync('data/native-context-migration/manifest.json'));const r=JSON.parse(gunzipSync(fs.readFileSync(s.releases.path)));const result=await validateBuildContextStage({root:process.cwd(),expectedReference:r.releases.at(-1)});process.stdout.write(JSON.stringify(result.receipt));";
 const runner=path.join(image,'replay-original-v1.mjs');fs.writeFileSync(runner,command+'\n',{flag:'wx'});
 const priorRaw=await replayOriginalV1(runner,image);const prior=JSON.parse(priorRaw);
 assert.equal(prior.status,'verified');assert.equal(prior.migration.locations,49625);assert.equal(prior.migration.footprints_sha256,BEFORE);assert.equal(prior.migration.successor_release_id,predecessor.id);
 const priorAdmitted=new Set();const readPrior=pin=>{const selected=restoredContextMember(root,pin.path,{prior:true});assert.equal(selected.pin.bytes,pin.bytes);assert.equal(selected.pin.sha256,pin.sha256);if(!priorAdmitted.has(pin.path)){budget.add({bytes:pin.bytes});priorAdmitted.add(pin.path);}const raw=readContextBody(selected.file,selected.pin);assert.equal(raw.length,pin.bytes);assert.equal(sha(raw),pin.sha256);return raw;};
 const originalIndex=JSON.parse(readPrior(oldStage.before_context)),middleIndex=JSON.parse(readPrior(oldStage.after_context));
 const afterIndex=JSON.parse(read(stage.after_context));
 const nativeComparisonRaw=read(stage.native_comparison);assert.equal(sha(nativeComparisonRaw),FIXED_NATIVE_COMPARISON_SHA);
 const nativeComparison=JSON.parse(nativeComparisonRaw),nativeManifestRaw=read(stage.native_manifest),nativeManifest=JSON.parse(nativeManifestRaw);
 validateNativeSelectionReceipt(nativeManifest,sha(nativeManifestRaw),nativeComparison);
 const originalContextProduct=nativeComparison.products.find(p=>p.path==='context-index.json');assert.equal(stage.after_context.bytes,originalContextProduct.bytes);assert.equal(stage.after_context.sha256,originalContextProduct.sha256);
 const afterImageRaw=read(stage.after_context_image),afterImageIndex=JSON.parse(afterImageRaw);
 authenticateSuccessorContextInventory(read(stage.after_context),afterImageIndex,nativeComparisonRaw);
 const acquisitions=[],plans=[];
 const normalized=p=>({...p,decoded_bytes:p.decoded_bytes??p.uncompressed_bytes,decoded_sha256:p.decoded_sha256??p.uncompressed_sha256,mode:'100644'});
 const middleMember=p=>restoredContextMember(root,path.posix.dirname(p.reused_from??oldStage.after_context.path)+'/'+p.path,{prior:true});
 assert.equal(originalIndex.parts.length,middleIndex.parts.length);assert.equal(afterIndex.parts.length,middleIndex.parts.length);
 for(let i=0;i<middleIndex.parts.length;i++){
  const middle=normalized(middleIndex.parts[i]),old=normalized(originalIndex.parts[i]),next=normalized(afterIndex.parts[i]);
  assert.equal(old.path,middle.path);assert.equal(path.posix.basename(next.path),middle.path);
  const selected=middleMember(middleIndex.parts[i]);assert.equal(selected.pin.bytes,middle.bytes);assert.equal(selected.pin.sha256,middle.sha256);
  const plan={middle,selected,original:old,successor:next,pairs:[]};
  for(const [kind,target,member,baseSide] of [
   ['original',old,()=>restoredContextMember(root,path.posix.dirname(oldStage.before_context.path)+'/'+old.path,{prior:true}),1],
   ['successor',next,()=>restoredContextMember(root,'data/canonical-grid/eastern-v8/'+next.path),0]]){
   if(target.bytes===middle.bytes&&target.sha256===middle.sha256){assert.equal(target.decoded_bytes,middle.decoded_bytes);assert.equal(target.decoded_sha256,middle.decoded_sha256);continue;}
   let other,afterRaw,patchBudget;
   if(kind==='successor'){const custody=restoredContextPatch(root,{runtimeBytes:currentAdmission.installed_runtime_bytes,codeBytes:currentAdmission.current_code_bytes+570577});patchBudget=custody.budget;const decodedSize=custody.raw.readUInt32LE(custody.raw.length-4);assert(decodedSize<=32*1024*1024);assert(custody.budget.complete_phase_bytes+decodedSize+middle.bytes+middle.decoded_bytes+target.bytes+target.decoded_bytes<=256*1024*1024,'Complete changed-chunk acquisition before decoder');const patch=JSON.parse(gunzipSync(custody.raw,{maxOutputLength:32*1024*1024}));assert.equal(patch.kind,'whole-original-encoded-context-byte-delta-v1');const originalWire=readContextBody(selected.file,selected.pin);verifyWholeBytes(originalWire,patch.original_source);assert.equal(patch.current_member.bytes,target.bytes);assert.equal(patch.current_member.sha256,target.sha256);afterRaw=applyBytePatch(patch.commands,patch.current_member,name=>{assert.equal(name,'original');return originalWire;});other={file:null,pin:target};}
   else other=member();
   assert.equal(other.pin.bytes,target.bytes);assert.equal(other.pin.sha256,target.sha256);
   const pair=acquireOriginalContextPair({beforeFile:baseSide?other.file:selected.file,afterFile:baseSide?selected.file:other.file,beforePin:baseSide?target:middle,afterPin:baseSide?middle:target,afterRaw,runtimeBytes:currentAdmission.installed_runtime_bytes,codeBytes:currentAdmission.current_code_bytes+570577});
   plan.pairs.push({kind,pair,baseSide});acquisitions.push({kind,part:middle.path,budget:pair.budget,patch_custody_budget:patchBudget,changed:pair.changes.map(c=>({ordinal:c.ordinal,id:c.id,before_bytes:c.before.length,after_bytes:c.after.length,before_sha256:c.before_sha256,after_sha256:c.after_sha256}))});
  }
  plans.push(plan);
 }
 const geometryManifest=JSON.parse(read(stage.geometry_manifest)),geometryBase=path.posix.dirname(stage.geometry_manifest.path),pins=Object.entries(geometryManifest.files).map(([name,pin])=>({path:geometryBase+'/'+(pin.archive_path??name),bytes:pin.bytes,sha256:pin.sha256}));assert.deepEqual(stage.geometry_files,pins);
 for(const pin of Object.values(geometryManifest.files))if(pin.uncompressed_bytes!==undefined){assert(Number.isSafeInteger(pin.uncompressed_bytes)&&pin.uncompressed_bytes<=32*1024*1024);budget.add({bytes:pin.uncompressed_bytes});}
 // Prospective complete numerical phase: one full v7 dictionary plus complete
 // changed-record variants, never two almost-identical decoded world copies.
 for(const pin of [stage.coverage_middle_grid,stage.native_proposal,stage.geometry_manifest,...stage.geometry_files])if(!admitted.has(pin.path)){budget.add({bytes:pin.bytes});admitted.add(pin.path);}
 for(const pin of [oldStage.native_proposal,oldStage.geometry_manifest,...(oldStage.geometry_files??[])])if(!priorAdmitted.has(pin.path)){budget.add({bytes:pin.bytes});priorAdmitted.add(pin.path);}
 for(const plan of plans){budget.add({bytes:plan.middle.bytes});budget.add({bytes:plan.middle.decoded_bytes});for(const entry of plan.pairs){for(const c of entry.pair.changes)budget.add({bytes:c.before.length+c.after.length});budget.add({bytes:Buffer.byteLength(JSON.stringify(entry.pair.layouts))});}}
 const before={index:middleIndex,rows:[]},originalRows=[],after=[];
 for(const plan of plans){const raw=readContextBody(plan.selected.file,plan.selected.pin);assert.equal(raw.length,plan.middle.bytes);assert.equal(sha(raw),plan.middle.sha256);const decoded=gunzipSync(raw,{maxOutputLength:32*1024*1024});assert.equal(decoded.length,plan.middle.decoded_bytes);assert.equal(sha(decoded),plan.middle.decoded_sha256);
  let base,original,successor;
  assert(plan.pairs.length<=1);
  if(!plan.pairs.length){base=JSON.parse(decoded);original=base;successor=base;}
  for(const entry of plan.pairs){const constructed=constructAliasedContextChunk(decoded,entry.pair,{baseSide:entry.baseSide});base=constructed.original_rows;original=base;successor=base;if(entry.kind==='original')original=constructed.rows;else successor=constructed.rows;}
  before.rows.push(...base);originalRows.push(...original);after.push(...successor);
 }
 for(const rows of [originalRows,before.rows,after]){assert.equal(rows.length,49625);assert.equal(new Set(rows.map(row=>row.id)).size,49625);assert.deepEqual(rows.map(row=>[row.id,row.pixelIndex]),before.rows.map(row=>[row.id,row.pixelIndex]));}assert.equal(before.index.owner_sha256,afterIndex.owner_sha256);assert.equal(afterIndex.owner_sha256,prior.migration.owner_sha256);
 // Child receipts are evidence, never substitutes for a live branded proof.
 const originalRelease=oldRegistry.releases.at(-2);assert.equal(originalRelease.version,6);assert.equal(predecessor.version,7);assert.equal(release.version,8);
 const middleRaw=read(stage.coverage_middle_grid);assert.equal(sha(middleRaw),FIXED_MIDDLE_GRID_SHA);
 const middleGrid=JSON.parse(middleRaw);assert.equal(middleGrid.geographic_release,predecessor.id);assert.equal(middleGrid.footprints_sha256,predecessor.footprints_sha256);
 assert.equal(middleGrid.hierarchy_sha256,predecessor.hierarchy_sha256);
 readPrior(oldStage.geometry_manifest);for(const pin of oldStage.geometry_files??[])readPrior(pin);
 const priorMigration=(()=>{
  const original={rows:originalRows};shareUnchangedContextGeometry(original.rows,before.rows);const oldCandidates=JSON.parse(readPrior(oldStage.native_proposal));
  assert.equal(sha(fs.readFileSync(path.join(image,oldStage.native_proposal.path))),oldStage.native_proposal.sha256);
  return validateContextMigration({original:original.rows,migrated:before.rows,candidates:oldCandidates,predecessorRelease:originalRelease,release:predecessor,migrationManifestFile:path.join(image,oldStage.geometry_manifest.path)});
 })();
 assert.equal(priorMigration.owner_sha256,prior.migration.owner_sha256);
 const candidates=JSON.parse(read(stage.native_proposal));assert.deepEqual(Object.keys(candidates).sort(),[...TARGETS].sort());
 for(const pin of pins)read(pin);
 const migration=validateContextMigration({original:before.rows,migrated:after,candidates,predecessorRelease:predecessor,release,migrationManifestFile:path.join(root,stage.geometry_manifest.path)});
 assert.equal(migration.owner_sha256,prior.migration.owner_sha256);const {geometryValidation,...compact}=migration;
 requireCurrentExecution(currentExecution);
 return retainSuccessfulContext({receipt:{status:'verified',stage_path:stagePath,stage_sha256:sha(stageRaw),original_stage:prior.original_stage,migration:compact,current_execution:currentExecution,authored_validator_code_index_sha256:sha(codeIndexRaw),
  original_v1_replay:{actual_command:command,child_invocation:{executable:process.execPath,exec_argv:['--max-old-space-size=1536'],cwd:image,max_buffer_bytes:32*1024*1024,timeout_ms:0,kill_signal:'SIGTERM',old_space_is_not_rss_cap:true},explicit_module_pins:oldStage.validator_sources,accepted_module_read_vintage:'913db0624b8aa79b188ff17a7f5c4ae0c0f63965',advertised_prior_execution_commit:oldStage.execution_commit,
   advertised_commit_matches_validator_closure:false,receipt_sha256:sha(priorRaw),receipt:prior,input_image_index_sha256:stage.prior_image.sha256},
  physical_association_chain:{versions:[6,7,8],middle_native_manifest_sha256:sha(middleRaw),original_migration_receipt_sha256:priorMigration.geometryValidation.proofs[0].receipt_sha256,successor_migration_receipt_sha256:geometryValidation.proofs[0].receipt_sha256,physical_assets_recalculated:false},checked_files:seen.size,context_record_acquisitions:acquisitions,context_transport:{transport_redecoded:false,index_sha256:stage.after_context_image.sha256,original_encoded_bodies:afterImageIndex.files.length,original_encoded_bytes:afterImageIndex.whole_bytes,ordinary_parts:afterImageIndex.parts.length,full_context_rows:after.length},budget:{...budget.snapshot(),installed_runtime_bytes:currentAdmission.installed_runtime_bytes,reserved_review_bytes:131072,complete_phase_bytes:budget.snapshot().accounted_bytes+currentAdmission.installed_runtime_bytes+131072+continuationReservedBytes,...(continuationReservedBytes?{continuation_reserved_bytes:continuationReservedBytes,continuation_reserved_descriptors:continuationReservedDescriptors}:{})},scientific_approval:false,limits:['Original v1 advertised daa8 execution differs from its explicitly pinned reviewed validator closure; exact accepted pin bytes are actually replayed','No geographic factual or publication approval granted by context lineage']},predecessorRelease:predecessor,geometryValidation,coverageContinuation:{originalRelease,middleRelease:predecessor,middleGrid,middleGridSha256:sha(middleRaw),originalGeometryValidation:priorMigration.geometryValidation}},after,afterIndex,retainContextForContinuation);
}
