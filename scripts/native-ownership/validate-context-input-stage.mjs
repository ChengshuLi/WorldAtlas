// Mandatory original->compact lineage for the offline native build.
// This is not the legacy voluntary partition mechanism or factual source approval.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {gunzipSync} from 'node:zlib';
import {fileURLToPath} from 'node:url';
import {validateEvidence, repositoryReader, sha256, safeEvidencePath} from '../evidence-quality.mjs';
import {loadNativeSourceInputs} from './native-only-inputs.mjs';
import {compactContextInputs} from './compact-context-inputs.mjs';
import {inPackageImage,readPinnedBuildFile} from './read-pinned-build-file.mjs';

export const CONTEXT_STAGE_PATH='coordination/engineering/native-grid-integration-1010-20261005-local17/context-inputs-v1/evidence-quality.json';
const need=(ok,message)=>{if(!ok)throw Error(message);};
export async function validateContextInputStage({root=process.cwd(),readFile,
  manifestPath=CONTEXT_STAGE_PATH,expectedReference,loadSource=loadNativeSourceInputs,subjectIds=[]}={}) {
 safeEvidencePath(manifestPath);
 const ordinary=readFile??repositoryReader(root);
 const manifest=JSON.parse(ordinary(manifestPath,'candidate'));
 {
  need(Array.isArray(manifest.immutable_snapshots),'Missing declared immutable package snapshots');
  const snapshots=new Map();
  const commits=new Set([manifest.baseline.commit,manifest.transform.original_commit,manifest.transform.generator_commit,manifest.transform.readback_commit]);
  for(const pin of manifest.immutable_snapshots){
   safeEvidencePath(pin.path);safeEvidencePath(pin.snapshot_path);
   need(commits.has(pin.commit)&&manifest.baseline.files.some(f=>f.path===pin.path&&f.sha256===pin.sha256&&f.bytes===pin.bytes),
    'Package snapshot lacks original byte binding');
   need(pin.snapshot_path===pin.path||manifest.outputs.some(f=>f.path===pin.snapshot_path&&f.sha256===pin.sha256&&f.bytes===pin.bytes),
    'Package code snapshot is not declared');
   const key=pin.commit+':'+pin.path;need(!snapshots.has(key),'Duplicate immutable package snapshot');snapshots.set(key,pin);
  }
  if(!readFile&&inPackageImage(root))readFile=(name,vintage)=>{
   if(vintage==='candidate')return ordinary(name,vintage);
   const pin=snapshots.get(vintage+':'+name);need(pin,'Missing immutable package snapshot');
   return readPinnedBuildFile({root,commit:vintage,path:name,snapshotPath:pin.snapshot_path,sha256:pin.sha256,bytes:pin.bytes});
  };
 };
 readFile??=ordinary;
 need(manifest.issue===1010&&manifest.lane==='engineering','Wrong native context stage scope');
 need(manifest.transform?.kind==='original-native-to-compact-context-v1'&&!manifest.input_stages,
  'Unsupported or recursive context stage');
 const bytes=validateEvidence(manifest,{readFile,expectedIssue:1010,expectedLane:'engineering'});
 const dir=path.posix.dirname(manifestPath),inputsPath=dir+'/inputs.json',proofPath=dir+'/verification.json';
 const declared=name=>manifest.outputs.find(d=>d.path===name);
 need(declared(inputsPath)&&declared(proofPath),'Missing complete context stage reports');
 const inputs=JSON.parse(readFile(inputsPath,'candidate')),proof=JSON.parse(readFile(proofPath,'candidate'));
 assert.equal(inputs.baseline_commit,manifest.transform.original_commit);
 assert.equal(manifest.transform.generator_commit,inputs.execution_commit);
 assert.equal(manifest.transform.readback_commit,proof.verification_commit);
 assert.equal(proof.preparation_commit,inputs.execution_commit);
 assert.equal(proof.baseline_commit,inputs.baseline_commit);
 const commonCode=['package.json','scripts/native-ownership/compact-context-inputs.mjs',
  'scripts/native-ownership/native-only-inputs.mjs','scripts/native-ownership/native-preparation-guards.mjs',
  'src/native-runtime.js','scripts/native-ownership/compile-native-ownership.mjs','src/native-grid.js','scripts/audit-grid-intervals.mjs'];
 const metadataCode=['scripts/selected-reference-metadata.mjs','src/reference-metadata.js'];
 const authenticateCode=(commit,file)=>{
  const snapshots=manifest.immutable_snapshots.filter(pin=>pin.commit===commit&&pin.path===file.path);
  need(snapshots.length===1&&snapshots[0].bytes===file.bytes&&snapshots[0].sha256===file.sha256,
   'Executed context code lacks an exact immutable snapshot');
  need(manifest.baseline.files.some(pin=>pin.path===file.path&&pin.bytes===file.bytes&&pin.sha256===file.sha256),
   'Executed context code omitted from stage inventory');
  const raw=readFile(file.path,commit);
  need(raw.length===file.bytes&&sha256(raw)===file.sha256,'Executed context code differs');
  return raw;
 };
 for(const [commit,inventory,entry] of [[inputs.execution_commit,inputs.executed_sources,'prepare-context-inputs.mjs'],
  [proof.verification_commit,proof.executed_sources,'verify-context-inputs.mjs']]){
  need(/^[a-f0-9]{40}$/.test(commit),'Missing immutable executed-code commit');
  need(Array.isArray(inventory),'Missing executed context code inventory');
  const compact=inventory.filter(file=>file.path==='scripts/native-ownership/compact-context-inputs.mjs');
  need(compact.length===1,'Incomplete or duplicate executed context code closure');
  // Infer each known closure from its authenticated source vintage, never from
  // the inventory it supplied. Static relative imports use the existing parser
  // convention; an old preparation and current readback may differ here.
  const raw=authenticateCode(commit,compact[0]);
  const current=[...raw.toString('utf8').matchAll(/(?:from\s*|import\s*)['"]([^'"]+)['"]/g)]
   .some(match=>match[1]==='../selected-reference-metadata.mjs');
  assert.deepEqual(inventory.map(f=>f.path).sort(),[...commonCode,...(current?metadataCode:[]),'scripts/native-ownership/'+entry].sort(),
   'Incomplete or duplicate executed context code closure');
  for(const file of inventory)authenticateCode(commit,file);
 }
 const expectedSnapshots=new Set([
  ...manifest.baseline.files.map(f=>(f.commit??manifest.baseline.commit)+':'+f.path),
  ...inputs.source_files.map(f=>inputs.baseline_commit+':'+f.path),
  ...inputs.executed_sources.map(f=>inputs.execution_commit+':'+f.path),
  ...proof.executed_sources.map(f=>proof.verification_commit+':'+f.path)
 ]);
 assert.deepEqual(manifest.immutable_snapshots.map(f=>f.commit+':'+f.path).sort(),[...expectedSnapshots].sort(),
  'Incomplete immutable package snapshot inventory');
 const original=await loadSource(root,inputs.baseline_commit,{readFile});
 assert.deepEqual(inputs.source_files,original.sourceFiles);
 assert.deepEqual(proof.source_files,original.sourceFiles);
 for(const source of original.sourceFiles){
  const descriptor=manifest.baseline.files.find(d=>d.path===source.path);
  need(descriptor&&descriptor.sha256===source.sha256&&descriptor.bytes===source.bytes,'Incomplete original context stage inventory');
 }
 const features=[];let next=1;
 for(const part of inputs.parts){
  safeEvidencePath(part.path);need(/^part-[0-9]+\.json\.gz$/.test(part.path),'Unsafe compact context part');
  const descriptor=declared(dir+'/'+part.path);
  need(descriptor&&descriptor.sha256===part.sha256&&descriptor.bytes===part.bytes&&
   descriptor.uncompressed_sha256===part.uncompressed_sha256&&descriptor.uncompressed_bytes===part.uncompressed_bytes,
   'Compact context output is not byte-bound');
  const values=JSON.parse(gunzipSync(readFile(descriptor.path,'candidate'),{maxOutputLength:part.uncompressed_bytes+1}));
  need(part.first_owner===next&&values.length===part.owners,'Incomplete compact context sequence');
  for(const feature of values){need(feature.pixelIndex===next++,'Compact owner index differs');features.push(feature);}
 }
 const result=compactContextInputs(features,original.bounds,original.manifest.footprints_sha256);
 assert.equal(features.length,original.roster.length);assert.equal(proof.locations,features.length);
 assert.equal(proof.vertices,original.vertices);assert.equal(inputs.vertices,original.vertices);
 assert.equal(inputs.footprints_sha256,result.footprints_sha256);assert.equal(proof.footprints_sha256,result.footprints_sha256);
 assert.equal(inputs.owner_sha256,result.owner_sha256);assert.equal(proof.owner_sha256,result.owner_sha256);
 for(let i=0;i<features.length;i++){
  assert.equal(features[i].id,original.roster[i].id);
  assert.equal(features[i].properties.parent_id,original.roster[i].parent_id);
 }
 assert.equal(inputs.original_release,original.release.id);
 need(proof.run_one_sha256===proof.run_two_sha256&&/^[a-f0-9]{64}$/.test(proof.run_one_sha256),'Context vintages disagree');
 const products=inputs.parts.map(p=>({path:p.path,bytes:p.bytes,sha256:p.sha256}));
 const inputRaw=readFile(inputsPath,'candidate');products.push({path:'inputs.json',bytes:inputRaw.length,sha256:sha256(inputRaw)});
 products.sort((a,b)=>a.path.localeCompare(b.path));
 assert.deepEqual(proof.products,products);assert.equal(sha256(JSON.stringify(products)),proof.run_one_sha256);
 if(expectedReference){
  assert.equal(expectedReference.id,inputs.original_release);
  assert.equal(expectedReference.id,original.release.id);
  assert.equal(expectedReference.footprints_sha256,result.footprints_sha256);
  assert.equal(expectedReference.hierarchy_sha256,original.manifest.hierarchy_sha256);
 }
 need(inputs.installation_ready===false&&proof.installation_ready===false&&proof.scientific_approval===false,
  'Context transform cannot grant installation or factual approval');
 need(Array.isArray(subjectIds)&&new Set(subjectIds).size===subjectIds.length&&subjectIds.every(id=>typeof id==='string'&&original.roster.some(f=>f.id===id)),
  'Invalid or absent original context migration subject');
 const subjectSourceParts=[...new Set(original.roster.filter(f=>subjectIds.includes(f.id)).map(f=>f.path))].sort();
 return {status:'verified',manifest_path:manifestPath,manifest_sha256:sha256(readFile(manifestPath,'candidate')),
  checked_files:bytes.checked.length,locations:features.length,vertices:original.vertices,
  source_files:original.sourceFiles.length,footprints_sha256:result.footprints_sha256,
  source_inventory:original.sourceFiles,subject_source_parts:subjectSourceParts,
  owner_sha256:result.owner_sha256,limits:bytes.limits,scientific_approval:false};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))
 console.log(JSON.stringify(await validateContextInputStage(),null,2));
