import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {requirePlainExecution,committedPreparationFiles} from '../../../scripts/native-ownership/native-preparation-guards.mjs';
import {BUILD_CONTEXT_VALIDATOR_SOURCES,validateBuildContextStage} from '../../../scripts/native-ownership/validate-build-context-stage.mjs';
import {readGeographicReleaseManifest} from '../../../scripts/read-geographic-release-manifest.mjs';

requirePlainExecution();
const prefix='coordination/engineering/iran-pakistan-offline-integration-991-20261006-local22';
const output=prefix+'/build-context-relocation-v1.json';
assert(!fs.existsSync(output),'Preserve prior relocation verification');
const head=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
const code=committedPreparationFiles(process.cwd(),head,[...BUILD_CONTEXT_VALIDATOR_SOURCES,prefix+'/relocate-build-context.mjs']);
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const stagePath='data/native-context-migration/manifest.json';
const prior=fs.readFileSync(stagePath),stage=JSON.parse(prior);
const expectedReference=readGeographicReleaseManifest('data/geographic-releases').releases.at(-1);
const before=await validateBuildContextStage({expectedReference});
const relocations=[];
function relocate(pin,newPath){
  const old=fs.readFileSync(pin.path),replacement=fs.readFileSync(newPath);
  assert.equal(old.length,pin.bytes);assert.equal(sha(old),pin.sha256);
  assert.deepEqual(replacement,old,'Relocation must retain exact whole bytes');
  relocations.push({before:{path:pin.path,bytes:pin.bytes,sha256:pin.sha256},after:{path:newPath,bytes:replacement.length,sha256:sha(replacement)}});
  pin.path=newPath;
}
for(const pin of stage.original_snapshot_overrides)relocate(pin,'data/native-context-migration/snapshots/'+pin.original_path);
relocate(stage.releases,'data/geographic-releases/releases-v7-gzip.json.gz');
// This is a storage-path change only. Original preparation provenance stays
// immutable; the new receipt separately records this execution and full gates.
fs.writeFileSync(stagePath,JSON.stringify(stage)+'\n');
const after=await validateBuildContextStage({expectedReference});
assert.deepEqual(before.receipt.migration,after.receipt.migration);
assert.deepEqual(before.receipt.original_stage,after.receipt.original_stage);
const manifestPath='.github/package-inputs.json',manifest=JSON.parse(fs.readFileSync(manifestPath));
const removed=[prefix+'/migrated-build-context-v4/snapshots/',prefix+'/successor-release-v1/releases-v7-gzip.json.gz'];
for(const entry of removed)assert(manifest.inputs.includes(entry));
assert(manifest.inputs.includes('data/native-context-migration/'));
assert(manifest.inputs.includes('data/geographic-releases/'));
manifest.inputs=manifest.inputs.filter(entry=>!removed.includes(entry));
fs.writeFileSync(manifestPath,JSON.stringify(manifest,null,2)+'\n');
const current=fs.readFileSync(stagePath);
fs.writeFileSync(output,JSON.stringify({version:1,execution_commit:head,code,prior_manifest:{path:stagePath,bytes:prior.length,sha256:sha(prior)},current_manifest:{path:stagePath,bytes:current.length,sha256:sha(current)},relocations,removed_duplicate_package_inputs:removed,mandatory_validation_before:before.receipt,mandatory_validation_after:after.receipt,whole_bytes_preserved:true,scientific_approval:false,published:false})+'\n',{flag:'wx'});
console.log(JSON.stringify({relocated_pins:relocations.length,original_source_locations:after.receipt.original_stage.locations,mandatory_stage:after.receipt.status,budget:after.receipt.budget}));
