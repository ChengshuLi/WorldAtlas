// Exactly the approved unchanged v6→v7 stage, followed by the two-target v7→v8 stage.
import fs from 'node:fs';import path from 'node:path';import os from 'node:os';import assert from 'node:assert/strict';import{execFileSync}from'node:child_process';import{gunzipSync}from'node:zlib';import{createHash}from'node:crypto';
import{restoreWholeImage}from'./whole-image.mjs';import{validateContextMigration}from'../../../scripts/native-ownership/validate-context-migration.mjs';
import{candidateBudget,requirePlainExecution}from'../../../scripts/native-ownership/native-preparation-guards.mjs';import{repositoryReader,safeEvidencePath}from'../../../scripts/evidence-quality.mjs';
import{BEFORE,AFTER,TARGETS}from'./native-producer.mjs';
const sha=b=>createHash('sha256').update(b).digest('hex');
export const FIXED_PRIOR_STAGE_SHA='471e6a71856c13b5856cd74f24b79cc9961b3b091980e8b9106a19c1f32a2765';
export const FIXED_PRIOR_VALIDATOR_SHA='5b6da335c43e438a7fefac264b01d7aafeeba8096dc808a22475e07caa63a4e7';
export async function validateChainedBuildContext({root,expectedReference,stagePath,stageRaw,stage,readFile}){
 requirePlainExecution();assert.equal(stage.version,2);assert.equal(stage.issue,1295);assert.equal(stage.kind,'retained-identity-context-continuation-v2');assert.equal(stage.lane,'engineering');
 assert.deepEqual(stage.subject_ids,[...TARGETS]);assert.equal(stage.prior_stage_sha256,FIXED_PRIOR_STAGE_SHA);
 const ordinary=readFile??repositoryReader(root),budget=candidateBudget([]),seen=new Map();budget.add({bytes:stageRaw.length});
 function read(pin){safeEvidencePath(pin.path);assert(Number.isSafeInteger(pin.bytes)&&pin.bytes>0&&pin.bytes<=32*1024*1024&&/^[a-f0-9]{64}$/.test(pin.sha256));if(seen.has(pin.path))assert.deepEqual(pin,seen.get(pin.path));
  const raw=ordinary(pin.path,'candidate');assert.equal(raw.length,pin.bytes);assert.equal(sha(raw),pin.sha256);if(!seen.has(pin.path)){budget.add({bytes:raw.length});seen.set(pin.path,pin);}return raw;}
 for(const pin of stage.validator_sources)read(pin);
 const imageIndexRaw=read(stage.prior_image),imageIndex=JSON.parse(imageIndexRaw),imageBase=path.posix.dirname(stage.prior_image.path);
 for(const pin of imageIndex.parts)read({path:imageBase+'/'+pin.path,bytes:pin.bytes,sha256:pin.sha256});
 const parent=path.join(root,'.cache');fs.mkdirSync(parent,{recursive:true});assert.equal(fs.realpathSync(parent),parent);
 const temporary=fs.mkdtempSync(path.join(parent,'native-context-1295-')),image=path.join(temporary,'prior');
 restoreWholeImage(path.join(root,imageBase),image,{expectedIndexSha:stage.prior_image.sha256});
 const oldStageRaw=fs.readFileSync(path.join(image,'data/native-context-migration/manifest.json'));assert.equal(sha(oldStageRaw),FIXED_PRIOR_STAGE_SHA);const oldStage=JSON.parse(oldStageRaw);
 assert.equal(oldStage.version,1);assert.equal(oldStage.kind,'retained-identity-context-migration-v1');assert.equal(oldStage.validator_sources.length,17);
 for(const pin of oldStage.validator_sources){safeEvidencePath(pin.path);const raw=fs.readFileSync(path.join(image,pin.path));assert.equal(raw.length,pin.bytes);assert.equal(sha(raw),pin.sha256);}
 assert.equal(sha(fs.readFileSync(path.join(image,'scripts/native-ownership/validate-build-context-stage.mjs'))),FIXED_PRIOR_VALIDATOR_SHA);
 const oldRegistry=JSON.parse(gunzipSync(fs.readFileSync(path.join(image,oldStage.releases.path)),{maxOutputLength:32*1024*1024}));
 const registry=JSON.parse(gunzipSync(read(stage.releases),{maxOutputLength:32*1024*1024}));assert.equal(registry.releases.length,8);assert.deepEqual(registry.releases.slice(0,7),oldRegistry.releases);
 assert.deepEqual(registry.batches.slice(0,oldRegistry.batches.length),oldRegistry.batches);assert.deepEqual(registry.sources_batches.slice(0,oldRegistry.sources_batches.length),oldRegistry.sources_batches);
 assert.equal(registry.original_catalog_sha256,oldRegistry.original_catalog_sha256);const predecessor=registry.releases.at(-2),release=registry.releases.at(-1);
 assert.equal(predecessor.footprints_sha256,BEFORE);assert.equal(release.footprints_sha256,AFTER);assert.equal(predecessor.id,stage.predecessor_release_id);assert.equal(release.id,stage.successor_release_id);assert.deepEqual(release,expectedReference);
 const command="import fs from 'node:fs';import{gunzipSync}from'node:zlib';import{validateBuildContextStage}from'./scripts/native-ownership/validate-build-context-stage.mjs';const s=JSON.parse(fs.readFileSync('data/native-context-migration/manifest.json'));const r=JSON.parse(gunzipSync(fs.readFileSync(s.releases.path)));const result=await validateBuildContextStage({root:process.cwd(),expectedReference:r.releases.at(-1)});process.stdout.write(JSON.stringify(result.receipt));";
 const priorRaw=execFileSync(process.execPath,['--input-type=module','-e',command],{cwd:image,env:{...process.env,WORLDATLAS_PACKAGE_STAGE:image},maxBuffer:32*1024*1024});const prior=JSON.parse(priorRaw);
 assert.equal(prior.status,'verified');assert.equal(prior.migration.locations,49625);assert.equal(prior.migration.footprints_sha256,BEFORE);assert.equal(prior.migration.successor_release_id,predecessor.id);
 function legacyContext(pin){const index=JSON.parse(fs.readFileSync(path.join(image,pin.path))),rows=[];for(const p of index.parts){const base=p.reused_from??pin.path;const raw=fs.readFileSync(path.join(image,path.posix.dirname(base),p.path));assert.equal(raw.length,p.bytes);assert.equal(sha(raw),p.sha256);const decoded=gunzipSync(raw,{maxOutputLength:32*1024*1024});assert.equal(decoded.length,p.uncompressed_bytes);assert.equal(sha(decoded),p.uncompressed_sha256);rows.push(...JSON.parse(decoded));}return {index,rows};}
 const before=legacyContext(oldStage.after_context),afterIndex=JSON.parse(read(stage.after_context)),after=[];
 for(const pin of afterIndex.parts){safeEvidencePath(pin.path);const raw=read({path:path.posix.dirname(stage.after_context.path)+'/'+pin.path,bytes:pin.bytes,sha256:pin.sha256}),decoded=gunzipSync(raw,{maxOutputLength:32*1024*1024});assert.equal(decoded.length,pin.decoded_bytes);assert.equal(sha(decoded),pin.decoded_sha256);after.push(...JSON.parse(decoded));}
 assert.equal(before.rows.length,49625);assert.equal(after.length,49625);assert.equal(before.index.owner_sha256,afterIndex.owner_sha256);assert.equal(afterIndex.owner_sha256,prior.migration.owner_sha256);
 const candidates=JSON.parse(read(stage.native_proposal));assert.deepEqual(Object.keys(candidates).sort(),[...TARGETS].sort());
 const geometryManifest=JSON.parse(read(stage.geometry_manifest)),geometryBase=path.posix.dirname(stage.geometry_manifest.path),pins=Object.entries(geometryManifest.files).map(([name,pin])=>({path:geometryBase+'/'+(pin.archive_path??name),bytes:pin.bytes,sha256:pin.sha256}));assert.deepEqual(stage.geometry_files,pins);for(const pin of pins)read(pin);
 const migration=validateContextMigration({original:before.rows,migrated:after,candidates,predecessorRelease:predecessor,release,migrationManifestFile:path.join(root,stage.geometry_manifest.path)});
 assert.equal(migration.owner_sha256,prior.migration.owner_sha256);const {geometryValidation,...compact}=migration;
 return {receipt:{status:'verified',stage_path:stagePath,stage_sha256:sha(stageRaw),original_stage:prior.original_stage,migration:compact,
  original_v1_replay:{actual_command:command,explicit_module_pins:oldStage.validator_sources,accepted_module_read_vintage:'913db0624b8aa79b188ff17a7f5c4ae0c0f63965',advertised_prior_execution_commit:oldStage.execution_commit,
   advertised_commit_matches_validator_closure:false,receipt_sha256:sha(priorRaw),receipt:prior,input_image_index_sha256:stage.prior_image.sha256},
  checked_files:seen.size,budget:budget.snapshot(),scientific_approval:false,limits:['Original v1 advertised daa8 execution differs from its explicitly pinned reviewed validator closure; exact accepted pin bytes are actually replayed','No geographic factual or publication approval granted by context lineage']},predecessorRelease:predecessor,geometryValidation};
}
