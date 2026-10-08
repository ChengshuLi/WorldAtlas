// Exactly the approved unchanged v6→v7 stage, followed by the two-target v7→v8 stage.
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import{execFileSync}from'node:child_process';import{gunzipSync}from'node:zlib';import{createHash}from'node:crypto';import{fileURLToPath}from'node:url';
import{restoreWholeImage}from'./whole-image.mjs';import{restoreCanonicalProducts,getRestoredCanonicalProducts}from'./restore-canonical-products.mjs';import{validateContextMigration}from'../../../scripts/native-ownership/validate-context-migration.mjs';
import{candidateBudget,requirePlainExecution}from'../../../scripts/native-ownership/native-preparation-guards.mjs';import{repositoryReader,safeEvidencePath}from'../../../scripts/evidence-quality.mjs';
import{validateNativeSelectionReceipt}from'../../../scripts/native-ownership/require-verified-selection.mjs';
import{BEFORE,AFTER,TARGETS}from'./native-producer.mjs';
import{isDeepStrictEqual}from'node:util';
import{rebindCoverageManifest}from'../../../scripts/rebind-coverage-manifest.mjs';
const sha=b=>createHash('sha256').update(b).digest('hex');
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
export async function validateChainedBuildContext({root,expectedReference,stagePath,stageRaw,stage,readFile}){
 requirePlainExecution();assert.equal(stage.version,2);assert.equal(stage.issue,1295);assert.equal(stage.kind,'retained-identity-context-continuation-v2');assert.equal(stage.lane,'engineering');
 assert.deepEqual(stage.subject_ids,[...TARGETS]);assert.equal(stage.prior_stage_sha256,FIXED_PRIOR_STAGE_SHA);
 const ordinary=readFile??repositoryReader(root),budget=candidateBudget([]),seen=new Map();budget.add({bytes:stageRaw.length});
 function read(pin){safeEvidencePath(pin.path);assert(Number.isSafeInteger(pin.bytes)&&pin.bytes>0&&pin.bytes<=32*1024*1024&&/^[a-f0-9]{64}$/.test(pin.sha256));if(seen.has(pin.path))assert.deepEqual(pin,seen.get(pin.path));
  const raw=ordinary(pin.path,'candidate');assert.equal(raw.length,pin.bytes);assert.equal(sha(raw),pin.sha256);if(!seen.has(pin.path)){budget.add({bytes:raw.length});seen.set(pin.path,pin);}return raw;}
 const actualCodeRoot=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..'),required=new Set(['package.json']);
 function visit(p){if(required.has(p))return;required.add(p);const file=path.join(actualCodeRoot,p);assert(fs.realpathSync(file)===file&&fs.lstatSync(file).isFile());const raw=fs.readFileSync(file);assert(raw.length<=32*1024*1024);for(const m of raw.toString('utf8').matchAll(/(?:from\s*|import\s*(?:\(\s*)?)['"]([^'"]+)['"]/g))if(m[1].startsWith('.'))visit(path.posix.normalize(path.posix.join(path.posix.dirname(p),m[1])));}
 visit('scripts/native-ownership/validate-build-context-stage.mjs');assert.deepEqual(stage.validator_sources.map(p=>p.path).sort(),[...required].sort(),'Complete actual context validator import closure required');
 for(const pin of stage.validator_sources){const raw=read(pin);assert(raw.equals(fs.readFileSync(path.join(actualCodeRoot,pin.path))),'Declared validator differs from actual executed source');}
 const imageIndexRaw=read(stage.prior_image),imageIndex=JSON.parse(imageIndexRaw),imageBase=path.posix.dirname(stage.prior_image.path);
 for(const pin of imageIndex.parts)read({path:imageBase+'/'+pin.path,bytes:pin.bytes,sha256:pin.sha256});
 const parent=path.join(root,'.cache');fs.mkdirSync(parent,{recursive:true});assert.equal(fs.realpathSync(parent),parent);
 const temporary=fs.mkdtempSync(path.join(parent,'native-context-1295-'));
 let image;
 if(stage.prior_image.original_index_sha256){
  assert.equal(stage.prior_image.original_index_sha256,'e34743a84df2aaaa668b4e7b23c4f6870379edfe7eb88a427d6005b47333a393');
  const retained=restoreCanonicalProducts({root,temporaryRoot:parent});
  assert.equal(retained.prior_index_sha256,stage.prior_image.sha256);
  image=getRestoredCanonicalProducts(root).priorImage;
 }else{image=path.join(temporary,'prior');restoreWholeImage(path.join(root,imageBase),image,{expectedIndexSha:stage.prior_image.sha256});}
 const oldStageRaw=fs.readFileSync(path.join(image,'data/native-context-migration/manifest.json'));assert.equal(sha(oldStageRaw),FIXED_PRIOR_STAGE_SHA);const oldStage=JSON.parse(oldStageRaw);
 assert.equal(oldStage.version,1);assert.equal(oldStage.kind,'retained-identity-context-migration-v1');assert.equal(oldStage.validator_sources.length,17);
 for(const pin of oldStage.validator_sources){safeEvidencePath(pin.path);const raw=fs.readFileSync(path.join(image,pin.path));assert.equal(raw.length,pin.bytes);assert.equal(sha(raw),pin.sha256);}
 assert.equal(sha(fs.readFileSync(path.join(image,'scripts/native-ownership/validate-build-context-stage.mjs'))),FIXED_PRIOR_VALIDATOR_SHA);
 const oldRegistry=JSON.parse(gunzipSync(fs.readFileSync(path.join(image,oldStage.releases.path)),{maxOutputLength:32*1024*1024}));
 const registry=JSON.parse(gunzipSync(read(stage.releases),{maxOutputLength:32*1024*1024}));assert.equal(registry.releases.length,8);assert.deepEqual(registry.releases.slice(0,7),oldRegistry.releases);
 assert.deepEqual(registry.batches.slice(0,oldRegistry.batches.length),oldRegistry.batches);assert.deepEqual(registry.sources_batches.slice(0,oldRegistry.sources_batches.length),oldRegistry.sources_batches);
 assert.equal(registry.original_catalog_sha256,oldRegistry.original_catalog_sha256);const predecessor=registry.releases.at(-2),release=registry.releases.at(-1);
 assert.equal(predecessor.footprints_sha256,BEFORE);assert.equal(release.footprints_sha256,AFTER);assert.equal(predecessor.id,stage.predecessor_release_id);assert.equal(release.id,stage.successor_release_id);assert.deepEqual(release,expectedReference);
 const oldValidatorPath="./scripts/native-ownership/validate-build-context-stage.mjs";
 const command="import fs from 'node:fs';import{gunzipSync}from'node:zlib';import{validateBuildContextStage}from "+JSON.stringify(oldValidatorPath)+";const s=JSON.parse(fs.readFileSync('data/native-context-migration/manifest.json'));const r=JSON.parse(gunzipSync(fs.readFileSync(s.releases.path)));const result=await validateBuildContextStage({root:process.cwd(),expectedReference:r.releases.at(-1)});process.stdout.write(JSON.stringify(result.receipt));";
 const runner=path.join(image,'replay-original-v1.mjs');fs.writeFileSync(runner,command+'\n',{flag:'wx'});
 const priorRaw=execFileSync(process.execPath,[runner],{cwd:image,env:{...process.env,WORLDATLAS_PACKAGE_STAGE:image},maxBuffer:32*1024*1024});const prior=JSON.parse(priorRaw);
 assert.equal(prior.status,'verified');assert.equal(prior.migration.locations,49625);assert.equal(prior.migration.footprints_sha256,BEFORE);assert.equal(prior.migration.successor_release_id,predecessor.id);
 function legacyContext(pin){const index=JSON.parse(fs.readFileSync(path.join(image,pin.path))),rows=[];for(const p of index.parts){const base=p.reused_from??pin.path;const raw=fs.readFileSync(path.join(image,path.posix.dirname(base),p.path));assert.equal(raw.length,p.bytes);assert.equal(sha(raw),p.sha256);const decoded=gunzipSync(raw,{maxOutputLength:32*1024*1024});assert.equal(decoded.length,p.uncompressed_bytes);assert.equal(sha(decoded),p.uncompressed_sha256);rows.push(...JSON.parse(decoded));}return {index,rows};}
 const before=legacyContext(oldStage.after_context),afterIndex=JSON.parse(read(stage.after_context)),after=[];
 const nativeComparisonRaw=read(stage.native_comparison);assert.equal(sha(nativeComparisonRaw),FIXED_NATIVE_COMPARISON_SHA);
 const nativeComparison=JSON.parse(nativeComparisonRaw),nativeManifestRaw=read(stage.native_manifest),nativeManifest=JSON.parse(nativeManifestRaw);
 validateNativeSelectionReceipt(nativeManifest,sha(nativeManifestRaw),nativeComparison);
 const originalContextProduct=nativeComparison.products.find(p=>p.path==='context-index.json');assert.equal(stage.after_context.bytes,originalContextProduct.bytes);assert.equal(stage.after_context.sha256,originalContextProduct.sha256);
 assert(stage.after_context_image,'Complete retained successor-context transport required');
 const afterImageRaw=read(stage.after_context_image),afterImageIndex=JSON.parse(afterImageRaw),afterImageBase=path.posix.dirname(stage.after_context_image.path);
 for(const pin of afterImageIndex.parts)read({path:afterImageBase+'/'+pin.path,bytes:pin.bytes,sha256:pin.sha256});
 authenticateSuccessorContextInventory(read(stage.after_context),afterImageIndex,nativeComparisonRaw);
 const afterImage=path.join(temporary,'successor-context');restoreWholeImage(path.join(root,afterImageBase),afterImage,{expectedIndexSha:stage.after_context_image.sha256});
 for(const pin of afterIndex.parts){
  safeEvidencePath(pin.path);const originalProduct=nativeComparison.products.find(p=>p.path===pin.path);assert.equal(pin.bytes,originalProduct.bytes);assert.equal(pin.sha256,originalProduct.sha256);
  const retained=afterImageIndex.files.find(p=>p.path===pin.path);
  assert.equal(retained.mode,'100644');assert.equal(retained.bytes,pin.bytes);assert.equal(retained.sha256,pin.sha256);
  assert.equal(retained.original_binding.scientific_execution_commit,'5b32388df0501b013ac9a3ba97864932db493d59');
  assert.deepEqual(retained.original_binding.original_product,pin,'Original complete scientific context descriptor changed');
  const raw=fs.readFileSync(path.join(afterImage,pin.path));assert.equal(raw.length,pin.bytes);assert.equal(sha(raw),pin.sha256);
  const decoded=gunzipSync(raw,{maxOutputLength:32*1024*1024});assert.equal(decoded.length,pin.decoded_bytes);assert.equal(sha(decoded),pin.decoded_sha256);const rows=JSON.parse(decoded);shareUnchangedContextGeometry(rows,before.rows);after.push(...rows);
 }
 assert.equal(before.rows.length,49625);assert.equal(after.length,49625);assert.equal(before.index.owner_sha256,afterIndex.owner_sha256);assert.equal(afterIndex.owner_sha256,prior.migration.owner_sha256);
 // Child receipts are evidence, never substitutes for a live branded proof.
 const originalRelease=oldRegistry.releases.at(-2);assert.equal(originalRelease.version,6);assert.equal(predecessor.version,7);assert.equal(release.version,8);
 const middleRaw=read(stage.coverage_middle_grid);assert.equal(sha(middleRaw),FIXED_MIDDLE_GRID_SHA);
 const middleGrid=JSON.parse(middleRaw);assert.equal(middleGrid.geographic_release,predecessor.id);assert.equal(middleGrid.footprints_sha256,predecessor.footprints_sha256);
 assert.equal(middleGrid.hierarchy_sha256,predecessor.hierarchy_sha256);
 const priorMigration=(()=>{
  const original=legacyContext(oldStage.before_context);shareUnchangedContextGeometry(original.rows,before.rows);const oldCandidates=JSON.parse(fs.readFileSync(path.join(image,oldStage.native_proposal.path)));
  assert.equal(sha(fs.readFileSync(path.join(image,oldStage.native_proposal.path))),oldStage.native_proposal.sha256);
  return validateContextMigration({original:original.rows,migrated:before.rows,candidates:oldCandidates,predecessorRelease:originalRelease,release:predecessor,migrationManifestFile:path.join(image,oldStage.geometry_manifest.path)});
 })();
 assert.equal(priorMigration.owner_sha256,prior.migration.owner_sha256);
 const candidates=JSON.parse(read(stage.native_proposal));assert.deepEqual(Object.keys(candidates).sort(),[...TARGETS].sort());
 const geometryManifest=JSON.parse(read(stage.geometry_manifest)),geometryBase=path.posix.dirname(stage.geometry_manifest.path),pins=Object.entries(geometryManifest.files).map(([name,pin])=>({path:geometryBase+'/'+(pin.archive_path??name),bytes:pin.bytes,sha256:pin.sha256}));assert.deepEqual(stage.geometry_files,pins);for(const pin of pins)read(pin);
 const migration=validateContextMigration({original:before.rows,migrated:after,candidates,predecessorRelease:predecessor,release,migrationManifestFile:path.join(root,stage.geometry_manifest.path)});
 assert.equal(migration.owner_sha256,prior.migration.owner_sha256);const {geometryValidation,...compact}=migration;
 return {receipt:{status:'verified',stage_path:stagePath,stage_sha256:sha(stageRaw),original_stage:prior.original_stage,migration:compact,
  original_v1_replay:{actual_command:command,explicit_module_pins:oldStage.validator_sources,accepted_module_read_vintage:'913db0624b8aa79b188ff17a7f5c4ae0c0f63965',advertised_prior_execution_commit:oldStage.execution_commit,
   advertised_commit_matches_validator_closure:false,receipt_sha256:sha(priorRaw),receipt:prior,input_image_index_sha256:stage.prior_image.sha256},
  physical_association_chain:{versions:[6,7,8],middle_native_manifest_sha256:sha(middleRaw),original_migration_receipt_sha256:priorMigration.geometryValidation.proofs[0].receipt_sha256,successor_migration_receipt_sha256:geometryValidation.proofs[0].receipt_sha256,physical_assets_recalculated:false},checked_files:seen.size,context_transport:{index_sha256:stage.after_context_image.sha256,original_encoded_bodies:afterImageIndex.files.length,original_encoded_bytes:afterImageIndex.whole_bytes,ordinary_parts:afterImageIndex.parts.length,full_context_rows:after.length},budget:budget.snapshot(),scientific_approval:false,limits:['Original v1 advertised daa8 execution differs from its explicitly pinned reviewed validator closure; exact accepted pin bytes are actually replayed','No geographic factual or publication approval granted by context lineage']},predecessorRelease:predecessor,geometryValidation,coverageContinuation:{originalRelease,middleRelease:predecessor,middleGrid,middleGridSha256:sha(middleRaw),originalGeometryValidation:priorMigration.geometryValidation}};
}
