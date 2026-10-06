import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {repositoryReader} from '../scripts/evidence-quality.mjs';
import {validateContextInputStage,CONTEXT_STAGE_PATH} from '../scripts/native-ownership/validate-context-input-stage.mjs';
import {readPinnedBuildFile,inPackageImage} from '../scripts/native-ownership/read-pinned-build-file.mjs';
import {selectBuildOwnership} from '../scripts/select-build-ownership.mjs';
import {packageNativeLatitudes} from '../scripts/package-native-latitudes.mjs';
const root=process.cwd(),reader=repositoryReader(root);
const candidatePath='coordination/engineering/native-grid-candidate-1010-20261005-local16/candidate-v1/manifest.json';
const candidate=JSON.parse(fs.readFileSync(candidatePath));
const reference={id:candidate.geographic_release,footprints_sha256:candidate.footprints_sha256,hierarchy_sha256:candidate.hierarchy_sha256};
const dir=path.posix.dirname(CONTEXT_STAGE_PATH),stage=JSON.parse(fs.readFileSync(CONTEXT_STAGE_PATH));
const proofPath='coordination/engineering/native-grid-candidate-1010-20261005-local16/decoded-native-verification.json';
function write(image,name,raw){const target=path.join(image,name);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,raw);}
test('declared ordinary package snapshots authenticate complete native source stage and transport without any Git repository',{timeout:180000},async()=>{
 const cache=path.join(root,'.cache/native-package-input-tests');fs.mkdirSync(cache,{recursive:true});
 const image=fs.mkdtempSync(path.join(cache,'image-')),old=process.env.WORLDATLAS_PACKAGE_STAGE,oldCeiling=process.env.GIT_CEILING_DIRECTORIES;
 try{
  write(image,CONTEXT_STAGE_PATH,fs.readFileSync(CONTEXT_STAGE_PATH));
  for(const output of stage.outputs)write(image,output.path,fs.readFileSync(output.path));
  for(const source of stage.baseline.files.filter(f=>f.path.startsWith('data/')))write(image,source.path,reader(source.path,stage.baseline.commit));
  write(image,candidatePath,fs.readFileSync(candidatePath));write(image,proofPath,fs.readFileSync(proofPath));
  write(image,candidate.native_latitudes.path,reader(candidate.native_latitudes.path,stage.baseline.commit));
  process.env.GIT_CEILING_DIRECTORIES=fs.realpathSync(cache);
  assert.notEqual(spawnSync('git',['-C',image,'rev-parse','--git-dir'],{encoding:'utf8'}).status,0,'package image cannot discover a parent Git repository');
  process.env.WORLDATLAS_PACKAGE_STAGE=image;process.chdir(image);
  const result=await validateContextInputStage({expectedReference:reference});
  assert.equal(result.locations,49625);assert.equal(result.source_files,43);assert.equal(result.scientific_approval,false);
  const selected=await selectBuildOwnership({manifestPath:candidatePath,expectedSha256:'efe31373ff6a2c3f4ba5f11f8cbe37b25337778b344d9dbf1d3dfde301e3e722',expectedReference:reference,requireNative:true});
  assert.equal(selected.verification.installation_approval,false);
  const packaged=await packageNativeLatitudes({manifest:selected.manifest,expectedReference:reference,destination:'dist'});
  assert.equal(packaged.native_latitudes.decoded_sha256,candidate.native_latitudes.decoded_sha256);
  const bounds=path.join(image,'data/canonical-grid/bounds.json.gz'),saved=fs.readFileSync(bounds);fs.writeFileSync(bounds,Buffer.from('tampered'));
  await assert.rejects(selectBuildOwnership({manifestPath:candidatePath,expectedSha256:'efe31373ff6a2c3f4ba5f11f8cbe37b25337778b344d9dbf1d3dfde301e3e722',expectedReference:reference}),/snapshot bytes differ/);fs.writeFileSync(bounds,saved);
  fs.unlinkSync(path.join(image,proofPath));
  await assert.rejects(selectBuildOwnership({manifestPath:candidatePath,expectedSha256:'efe31373ff6a2c3f4ba5f11f8cbe37b25337778b344d9dbf1d3dfde301e3e722',expectedReference:reference}),/ENOENT/);
  const snapshot=stage.immutable_snapshots.find(f=>f.snapshot_path!==f.path);
  fs.writeFileSync(path.join(image,snapshot.snapshot_path),Buffer.from('tampered code'));
  await assert.rejects(validateContextInputStage({expectedReference:reference}),/bytes mismatch|snapshot bytes differ/);
  assert.throws(()=>readPinnedBuildFile({commit:stage.baseline.commit,path:'../secret',sha256:'0'.repeat(64)}),/Unsafe/);
  assert.throws(()=>inPackageImage(root),/differs from declared/);
 }finally{process.chdir(root);if(old===undefined)delete process.env.WORLDATLAS_PACKAGE_STAGE;else process.env.WORLDATLAS_PACKAGE_STAGE=old;if(oldCeiling===undefined)delete process.env.GIT_CEILING_DIRECTORIES;else process.env.GIT_CEILING_DIRECTORIES=oldCeiling;fs.rmSync(image,{recursive:true,force:true});}
});
