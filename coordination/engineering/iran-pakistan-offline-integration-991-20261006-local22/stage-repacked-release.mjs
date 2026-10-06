import fs from 'node:fs';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {requirePlainExecution,committedPreparationFiles,candidateBudget} from '../../../scripts/native-ownership/native-preparation-guards.mjs';
import {BUILD_CONTEXT_VALIDATOR_SOURCES,validateBuildContextStage} from '../../../scripts/native-ownership/validate-build-context-stage.mjs';
import {readGeographicReleaseManifest} from '../../../scripts/read-geographic-release-manifest.mjs';
requirePlainExecution();
const P='coordination/engineering/iran-pakistan-offline-integration-991-20261006-local22';
const source=P+'/repacked-release-v2',output=P+'/repacked-release-staging-v1.json';
assert(!fs.existsSync(output),'Preserve prior staging receipt');
const head=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
const code=committedPreparationFiles(process.cwd(),head,[...BUILD_CONTEXT_VALIDATOR_SOURCES,P+'/stage-repacked-release.mjs']);
const sha=bytes=>createHash('sha256').update(bytes).digest('hex'),budget=candidateBudget(code);
const archiveBudget=candidateBudget(code);
function immutable(name,admission=budget){const raw=fs.readFileSync(name),original=execFileSync('git',['show',head+':'+name],{maxBuffer:32*1024*1024});assert.deepEqual(raw,original);admission.add({bytes:raw.length});return raw;}
const raw=immutable(source+'/verification.json'),proof=JSON.parse(raw);
// Superseded files may leave this isolated branch only after their exact
// producing source is on the remote archive branch.
execFileSync('git',['merge-base','--is-ancestor',proof.execution_commit,'origin/engineering/iran-pakistan-offline-integration-991-20261006-local22']);
const expectedReference=readGeographicReleaseManifest().releases.at(-1);
const before=await validateBuildContextStage({expectedReference});
const removed=[];
for(const pin of proof.original_membership_batches){
  const name='data/geographic-releases/'+pin.path,bytes=immutable(name,archiveBudget);
  assert.equal(bytes.length,pin.bytes);assert.equal(sha(bytes),pin.sha256);
  removed.push({path:name,commit:proof.execution_commit,bytes:bytes.length,sha256:sha(bytes)});
}
const copies=[];
for(const pin of [...proof.new_membership_batches,proof.registry,proof.pointer]){
  const from=source+'/'+pin.path,to='data/geographic-releases/'+pin.path,bytes=immutable(from);
  assert.equal(bytes.length,pin.bytes);assert.equal(sha(bytes),pin.sha256);
  fs.writeFileSync(to,bytes);assert.deepEqual(fs.readFileSync(to),bytes);
  budget.add({bytes:bytes.length});copies.push({from,to,bytes:bytes.length,sha256:sha(bytes)});
}
assert.deepEqual(readGeographicReleaseManifest().releases.at(-1),expectedReference,'Repack must not rewrite the release');
const stagePath='data/native-context-migration/manifest.json',prior=fs.readFileSync(stagePath),stage=JSON.parse(prior);
assert.equal(stage.releases.sha256,proof.source_registry.sha256);
stage.releases={path:'data/geographic-releases/'+proof.registry.path,bytes:proof.registry.bytes,sha256:proof.registry.sha256};
fs.writeFileSync(stagePath,JSON.stringify(stage)+'\n');
const after=await validateBuildContextStage({expectedReference});
assert.deepEqual(after.receipt.migration,before.receipt.migration);
assert.deepEqual(after.receipt.original_stage,before.receipt.original_stage);
for(const pin of removed){assert.equal(sha(fs.readFileSync(pin.path)),pin.sha256);fs.unlinkSync(pin.path);}
const current=fs.readFileSync(stagePath);
fs.writeFileSync(output,JSON.stringify({version:1,execution_commit:head,code,source_verification:{path:source+'/verification.json',bytes:raw.length,sha256:sha(raw)},copies,removed_from_isolated_branch:removed,prior_context_manifest_sha256:sha(prior),current_context_manifest_sha256:sha(current),mandatory_before:before.receipt,mandatory_after:after.receipt,mandatory_copy_phase_budget:budget.snapshot(),mandatory_original_archive_phase_budget:archiveBudget.snapshot(),whole_originals_retained_in_remote_source_commit:true,published:false})+'\n',{flag:'wx'});
console.log(JSON.stringify({copied:copies.length,removed:removed.length,release:expectedReference.id,mandatory_stage:after.receipt.status,budget:budget.snapshot()}));
