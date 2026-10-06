// Actual no-Git package image with changed live input paths and retained originals.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {pathToFileURL} from 'node:url';
import {committedPreparationFiles,requirePlainExecution} from '../../../scripts/native-ownership/native-preparation-guards.mjs';
requirePlainExecution();
const root=process.cwd(),prefix='coordination/engineering/iran-pakistan-offline-integration-991-20261006-local22',head=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
const image=path.join(root,'.cache/reference-repair-991/build-context-image-v2');
if(fs.existsSync(image))throw Error('Fresh context image required');
const producer=committedPreparationFiles(root,head,['package.json',prefix+'/verify-build-context-package.mjs','scripts/native-ownership/native-preparation-guards.mjs']);
const stagePath=prefix+'/migrated-build-context-v3/manifest.json',stage=JSON.parse(fs.readFileSync(stagePath)),old=JSON.parse(fs.readFileSync(stage.original_stage.path));
const inputs=new Set([stagePath,...stage.validator_sources.map(p=>p.path),stage.original_stage.path,stage.before_context.path,stage.after_context.path,stage.native_proposal.path,stage.geometry_manifest.path,stage.releases.path,...stage.geometry_files.map(p=>p.path),...stage.original_snapshot_overrides.map(p=>p.path)]);
for(const manifest of [stage.before_context,stage.after_context])for(const part of JSON.parse(fs.readFileSync(manifest.path)).parts)inputs.add(path.posix.dirname(manifest.path)+'/'+part.path);
for(const pin of old.immutable_snapshots)inputs.add(pin.snapshot_path);
for(const pin of old.outputs)inputs.add(pin.path);
const sha=raw=>createHash('sha256').update(raw).digest('hex'),inventory=[];
for(const name of inputs){const target=path.join(image,name),raw=fs.readFileSync(name);fs.mkdirSync(path.dirname(target),{recursive:true});fs.copyFileSync(name,target,fs.constants.COPYFILE_FICLONE);inventory.push({path:name,bytes:raw.length,sha256:sha(raw)});}
// Simulate the actual integration: current geography/release paths now refer
// to repaired inputs. Original-source validation must use explicit old aliases.
for(const part of ['data/geography/part-11.json','data/geography/part-17.json']){
 const source=prefix+'/results-v2/stage/'+part,target=path.join(image,part);fs.copyFileSync(source,target);const raw=fs.readFileSync(target);inventory[inventory.findIndex(p=>p.path===part)]={path:part,bytes:raw.length,sha256:sha(raw)};
}
const pointer=fs.readFileSync(prefix+'/successor-release-v1/current-manifest.json');fs.writeFileSync(path.join(image,'data/geographic-releases/current-manifest.json'),pointer);inventory[inventory.findIndex(p=>p.path==='data/geographic-releases/current-manifest.json')]={path:'data/geographic-releases/current-manifest.json',bytes:pointer.length,sha256:sha(pointer)};
assert(!fs.existsSync(path.join(image,'.git')));const originalCwd=process.cwd();process.chdir(image);process.env.WORLDATLAS_PACKAGE_STAGE=image;
try{
 const {validateBuildContextStage}=await import(pathToFileURL(path.join(image,'scripts/native-ownership/validate-build-context-stage.mjs')));
 const registry=JSON.parse(gunzipSync(fs.readFileSync(stage.releases.path))),expectedReference=registry.releases.at(-1);
 const result=await validateBuildContextStage({root:image,stagePath,expectedReference});assert.equal(result.receipt.migration.locations,49625);
 // Early structural controls still run the public mandatory entry point.
 const cases=[['missing-validator-code',value=>value.validator_sources.pop()],['missing-original-snapshot',value=>value.original_snapshot_overrides.pop()],['wrong-source-release',value=>value.successor_release_id='wrong']];
 const initial=fs.readFileSync(stagePath),controls=[];
 for(const [name,mutate] of cases){const value=JSON.parse(initial);mutate(value);fs.writeFileSync(stagePath,JSON.stringify(value));await assert.rejects(()=>validateBuildContextStage({root:image,stagePath,expectedReference}));controls.push(name);}
 fs.writeFileSync(stagePath,initial);
 const report={execution_commit:head,producer,image_inventory:inventory,package_has_git:false,replaced_current_inputs:['data/geography/part-11.json','data/geography/part-17.json','data/geographic-releases/current-manifest.json'],original_snapshot_aliases_validated:true,receipt:result.receipt,negative_controls:controls,installed:false,published:false};
 fs.writeFileSync(path.join(root,prefix,'migrated-build-context-package-verification-v2.json'),JSON.stringify(report)+'\n',{flag:'wx'});console.log(JSON.stringify({locations:49625,package_has_git:false,negative_controls:controls.length,migration_budget:result.receipt.budget}));
}finally{process.chdir(originalCwd);delete process.env.WORLDATLAS_PACKAGE_STAGE;}
