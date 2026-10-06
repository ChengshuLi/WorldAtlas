import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {isDeepStrictEqual} from 'node:util';
import {requirePlainExecution,committedPreparationFiles,candidateBudget} from '../../../scripts/native-ownership/native-preparation-guards.mjs';
import {BUILD_CONTEXT_VALIDATOR_SOURCES,validateBuildContextStage} from '../../../scripts/native-ownership/validate-build-context-stage.mjs';
import {readGeographicReleaseManifest} from '../../../scripts/read-geographic-release-manifest.mjs';
requirePlainExecution();
const P='coordination/engineering/iran-pakistan-offline-integration-991-20261006-local22',output=P+'/context-part-reuse-v1.json';
assert(!fs.existsSync(output),'Preserve prior verification');
const head=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
const code=committedPreparationFiles(process.cwd(),head,[...BUILD_CONTEXT_VALIDATOR_SOURCES,P+'/deduplicate-context-parts.mjs']);
const budget=candidateBudget(code),sha=b=>createHash('sha256').update(b).digest('hex');
function read(name){const raw=fs.readFileSync(name);budget.add({bytes:raw.length});return raw;}
const stagePath='data/native-context-migration/manifest.json',oldStage=read(stagePath),stage=JSON.parse(oldStage);
const oldAfter=read(stage.after_context.path),after=JSON.parse(oldAfter),before=JSON.parse(read(stage.before_context.path));
const reused=[];
for(const part of after.parts){
  const original=before.parts.find(p=>p.path===part.path);
  if(!isDeepStrictEqual(part,original))continue;
  const priorPath=path.posix.dirname(stage.before_context.path)+'/'+part.path;
  const duplicatePath=path.posix.dirname(stage.after_context.path)+'/'+part.path;
  const originalBytes=read(priorPath),duplicate=read(duplicatePath);
  assert.deepEqual(originalBytes,duplicate);assert.equal(duplicate.length,part.bytes);assert.equal(sha(duplicate),part.sha256);
  reused.push({original_path:priorPath,removed_duplicate_path:duplicatePath,bytes:part.bytes,sha256:part.sha256});
  part.reused_from=stage.before_context.path;
}
assert.equal(reused.length,32);assert.equal(after.parts.length,34);
const updatedAfter=Buffer.from(JSON.stringify(after)+'\n');fs.writeFileSync(stage.after_context.path,updatedAfter);
stage.after_context.bytes=updatedAfter.length;stage.after_context.sha256=sha(updatedAfter);
stage.validator_sources=code.filter(p=>BUILD_CONTEXT_VALIDATOR_SOURCES.includes(p.path));
fs.writeFileSync(stagePath,JSON.stringify(stage)+'\n');
const expectedReference=readGeographicReleaseManifest().releases.at(-1);
// Remove duplicates before the complete gate. A stale current-directory read
// therefore cannot accidentally make the inherited representation pass.
for(const pin of reused)fs.unlinkSync(pin.removed_duplicate_path);
const lineage=await validateBuildContextStage({expectedReference});
assert.equal(lineage.receipt.migration.locations,49625);assert.equal(lineage.receipt.migration.changed_locations,2);
const checks=[];
// Changing an inherited descriptor's pin and the index's pin cannot bypass the
// exact original-part comparison. The full source/after-world gate still runs.
const inherited=after.parts.find(p=>p.reused_from);
for(const [name,mutate] of [['wrong-before-context',p=>p.reused_from=stage.after_context.path],['altered-inherited-pin',p=>p.sha256='0'.repeat(64)]]){
 const index=structuredClone(after);mutate(index.parts.find(p=>p.path===inherited.path));const raw=Buffer.from(JSON.stringify(index)+'\n');
 const bad=structuredClone(stage);bad.after_context.bytes=raw.length;bad.after_context.sha256=sha(raw);
 await assert.rejects(()=>validateBuildContextStage({expectedReference,readFile:p=>p===stagePath?Buffer.from(JSON.stringify(bad)+'\n'):p===stage.after_context.path?raw:fs.readFileSync(p)}),name==='wrong-before-context'?/Only an exact mandatory before-context part/:/Reused context part differs/);checks.push({name,rejected:true});
}
const current=fs.readFileSync(stagePath);
fs.writeFileSync(output,JSON.stringify({version:1,execution_commit:head,code,original_stage_sha256:sha(oldStage),original_after_index_sha256:sha(oldAfter),current_stage_sha256:sha(current),current_after_index:{path:stage.after_context.path,bytes:updatedAfter.length,sha256:sha(updatedAfter)},reused_parts:reused,retained_changed_parts:after.parts.filter(p=>!p.reused_from),duplicate_bytes_removed:reused.reduce((n,p)=>n+p.bytes,0),complete_world_validation:lineage.receipt,negative_controls:checks,budget:budget.snapshot(),all_original_source_parts_mandatory:true,all_after_parts_mandatory:true,published:false})+'\n',{flag:'wx'});
console.log(JSON.stringify({reused:reused.length,bytes_removed:reused.reduce((n,p)=>n+p.bytes,0),locations:lineage.receipt.migration.locations,negative_controls:checks,budget:budget.snapshot()}));
