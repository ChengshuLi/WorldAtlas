// Mandatory original lineage plus a separately bounded explicit geometry migration.
// This validates a build input; it never grants geographic or factual approval.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {gunzipSync} from 'node:zlib';
import {validateContextInputStage,CONTEXT_STAGE_PATH} from './validate-context-input-stage.mjs';
import {validateContextMigration} from './validate-context-migration.mjs';
import {candidateBudget} from './native-preparation-guards.mjs';
import {readPinnedBuildFile} from './read-pinned-build-file.mjs';
import {repositoryReader,safeEvidencePath,sha256} from '../evidence-quality.mjs';

export const BUILD_CONTEXT_STAGE_PATH='data/native-context-migration/manifest.json';
export const BUILD_CONTEXT_VALIDATOR_SOURCES=[
 'package.json','scripts/native-ownership/validate-build-context-stage.mjs',
 'scripts/native-ownership/validate-context-input-stage.mjs','scripts/native-ownership/validate-context-migration.mjs',
 'scripts/native-ownership/native-only-inputs.mjs','scripts/native-ownership/compact-context-inputs.mjs',
 'scripts/native-ownership/read-pinned-build-file.mjs','scripts/native-ownership/native-preparation-guards.mjs',
 'scripts/native-ownership/compile-native-ownership.mjs','scripts/audit-grid-intervals.mjs','scripts/evidence-quality.mjs',
 'scripts/prepare-geographic-release.mjs','scripts/check-prepared.mjs','scripts/read-geographic-release-manifest.mjs',
 'src/native-runtime.js','src/native-grid.js','hosted/geographic-releases.js'
];
const fail=(ok,message)=>{if(!ok)throw Error(message);};
export async function validateBuildContextStage({root=process.cwd(),expectedReference,
 stagePath=BUILD_CONTEXT_STAGE_PATH,readFile}={}) {
 safeEvidencePath(stagePath);
 if(!fs.existsSync(path.join(root,stagePath))&&!readFile){
  const receipt=await validateContextInputStage({root,expectedReference});
  return {receipt};
 }
 const ordinary=readFile??repositoryReader(root),stageRaw=ordinary(stagePath,'candidate'),stage=JSON.parse(stageRaw);
 fail(stage.version===1&&Number.isSafeInteger(stage.issue)&&stage.issue>0&&stage.lane==='engineering'&&stage.kind==='retained-identity-context-migration-v1'&&!stage.input_stages,
  'Unsupported build context migration stage');
 fail(stage.original_stage?.path===CONTEXT_STAGE_PATH,'Wrong mandatory original context stage');
 assert.deepEqual(stage.validator_sources.map(p=>p.path).sort(),[...BUILD_CONTEXT_VALIDATOR_SOURCES].sort(),
  'Incomplete or duplicate migrated context validator closure');
 const budget=candidateBudget([]),checked=new Map();budget.add({bytes:stageRaw.length});
 const read=pin=>{
  safeEvidencePath(pin?.path);fail(Number.isSafeInteger(pin.bytes)&&pin.bytes>=0&&/^[a-f0-9]{64}$/.test(pin.sha256??''),'Invalid context stage byte pin');
  if(checked.has(pin.path)){assert.deepEqual(checked.get(pin.path),pin,'Conflicting context stage pin');return ordinary(pin.path,'candidate');}
  const raw=ordinary(pin.path,'candidate');fail(raw.length===pin.bytes&&sha256(raw)===pin.sha256,'Context migration input bytes differ: '+pin.path);
  budget.add({bytes:raw.length});checked.set(pin.path,pin);return raw;
 };
 for(const pin of stage.validator_sources)read(pin);
 const originalManifest=JSON.parse(read(stage.original_stage));
 const oldSnapshots=new Map(originalManifest.immutable_snapshots.map(pin=>[pin.commit+':'+pin.path,pin]));
 const aliases=new Map(),allowed=new Set(originalManifest.baseline.files.filter(pin=>pin.path.startsWith('data/geography/')).map(pin=>pin.path));
 allowed.add('data/geographic-releases/current-manifest.json');
 for(const alias of stage.original_snapshot_overrides){
  const key=alias.commit+':'+alias.original_path,pin=oldSnapshots.get(key);
  fail(pin&&allowed.has(alias.original_path)&&alias.bytes===pin.bytes&&alias.sha256===pin.sha256&&!aliases.has(key),
   'Invalid or duplicate original context snapshot override');
  aliases.set(key,alias);read({path:alias.path,bytes:alias.bytes,sha256:alias.sha256});
 }
 const registry=JSON.parse(gunzipSync(read(stage.releases),{maxOutputLength:32*1024*1024}));
 const predecessor=registry.releases.at(-2),release=registry.releases.at(-1);
 fail(predecessor?.id===stage.predecessor_release_id&&release?.id===stage.successor_release_id,
  'Wrong actual context migration release chain');
 assert.deepEqual(release,expectedReference,'Build release differs from context migration successor');
 const originalReader=(name,vintage)=>{
  if(vintage==='candidate')return ordinary(name,vintage);
  const key=vintage+':'+name,pin=oldSnapshots.get(key);fail(pin,'Undeclared immutable original context input');
  const alias=aliases.get(key);
  if(alias)return read({path:alias.path,bytes:alias.bytes,sha256:alias.sha256});
  return readPinnedBuildFile({root,commit:pin.commit,path:pin.path,snapshotPath:pin.snapshot_path,sha256:pin.sha256,bytes:pin.bytes});
 };
 const sourceCommit=originalManifest.transform.original_commit;
 const originalPointer=JSON.parse(originalReader('data/geographic-releases/current-manifest.json',sourceCommit));
 const registryPin=oldSnapshots.get(sourceCommit+':data/geographic-releases/'+originalPointer.path);
 fail(registryPin&&stage.predecessor_registry.path===registryPin.snapshot_path&&stage.predecessor_registry.bytes===registryPin.bytes&&
  stage.predecessor_registry.sha256===registryPin.sha256&&registryPin.sha256===originalPointer.sha256,
  'Unbound original release registry');
 const originalRegistry=JSON.parse(gunzipSync(read(stage.predecessor_registry),{maxOutputLength:32*1024*1024}));
 assert.equal(registry.version,originalRegistry.version);assert.equal(registry.original_catalog_sha256,originalRegistry.original_catalog_sha256);
 assert.deepEqual(registry.releases.slice(0,-1),originalRegistry.releases,'Original release records changed');
 assert.deepEqual(registry.batches.slice(0,originalRegistry.batches.length),originalRegistry.batches,'Original release batch records changed');
 assert.deepEqual(registry.sources_batches.slice(0,originalRegistry.sources_batches.length),originalRegistry.sources_batches,'Original source batches changed');
 // Keep the existing complete original-source stage mandatory and unchanged.
 const candidates=JSON.parse(read(stage.native_proposal));
 const originalReceipt=await validateContextInputStage({root,readFile:originalReader,expectedReference:predecessor,subjectIds:Object.keys(candidates)});
 const changedSourceParts=new Set([...originalReceipt.subject_source_parts,'data/geographic-releases/current-manifest.json']);
 assert.deepEqual([...aliases.keys()].sort(),[...oldSnapshots].filter(([,pin])=>changedSourceParts.has(pin.path)).map(([key])=>key).sort(),
  'Original changed-input snapshots are incomplete or outside the exact subjects');
 const decodeContext=pin=>{
  const inputs=JSON.parse(read(pin)),dir=path.posix.dirname(pin.path),features=[];
  for(const part of inputs.parts){safeEvidencePath(part.path);fail(/^part-[0-9]+\.json\.gz$/.test(part.path),'Unsafe migrated context part');
   const raw=read({path:dir+'/'+part.path,bytes:part.bytes,sha256:part.sha256}),decoded=gunzipSync(raw,{maxOutputLength:32*1024*1024});
   fail(decoded.length===part.uncompressed_bytes&&sha256(decoded)===part.uncompressed_sha256,'Context decoded bytes differ');
   features.push(...JSON.parse(decoded));
  }
  return {inputs,features};
 };
 fail(stage.before_context.path===path.posix.dirname(CONTEXT_STAGE_PATH)+'/inputs.json','Wrong original compact context input');
 const before=decodeContext(stage.before_context),after=decodeContext(stage.after_context);
 assert.equal(before.inputs.footprints_sha256,originalReceipt.footprints_sha256);assert.equal(before.inputs.owner_sha256,originalReceipt.owner_sha256);
 const geometryManifest=JSON.parse(read(stage.geometry_manifest)),base=path.posix.dirname(stage.geometry_manifest.path);
 const geometryPins=Object.entries(geometryManifest.files).map(([name,pin])=>({path:path.posix.normalize(base+'/'+(pin.archive_path??name)),bytes:pin.bytes,sha256:pin.sha256}));
 assert.deepEqual(stage.geometry_files,geometryPins,'Incomplete geometry proof file budget');
 for(const pin of geometryPins)read(pin);
 const migration=validateContextMigration({original:before.features,migrated:after.features,candidates,
  predecessorRelease:predecessor,release,migrationManifestFile:path.join(root,stage.geometry_manifest.path)});
 assert.equal(after.inputs.footprints_sha256,migration.footprints_sha256);assert.equal(after.inputs.owner_sha256,migration.owner_sha256);
 assert.equal(migration.owner_sha256,originalReceipt.owner_sha256);
 const {geometryValidation,...migrationReceipt}=migration;
 return {receipt:{status:'verified',stage_path:stagePath,stage_sha256:sha256(stageRaw),original_stage:originalReceipt,
   migration:migrationReceipt,checked_files:checked.size,budget:budget.snapshot(),scientific_approval:false},
   predecessorRelease:predecessor,geometryValidation};
}
