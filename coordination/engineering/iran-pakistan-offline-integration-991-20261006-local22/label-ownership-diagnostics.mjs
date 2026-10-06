// Preserve old diagnostics and label their actual historical scope explicitly.
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {committedPreparationFiles,requirePlainExecution,candidateBudget} from '../../../scripts/native-ownership/native-preparation-guards.mjs';
requirePlainExecution();
const prefix='coordination/engineering/iran-pakistan-offline-integration-991-20261006-local22',dir=prefix+'/repaired-ownership-history-v1',output=dir+'/historical-diagnostics.json';
if(fs.existsSync(output))throw Error('Fresh historical note required');
const head=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),baseline='d0cc67eac85038159f88a673acbc39b77ab7461d';
const code=committedPreparationFiles(process.cwd(),head,['package.json',prefix+'/label-ownership-diagnostics.mjs','scripts/native-ownership/native-preparation-guards.mjs']),budget=candidateBudget(code);
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const index=JSON.parse(fs.readFileSync(dir+'/index.json')),diagnostics=[];
for(const name of ['candidate-recovery.json','threshold-refinement.json']){
 const original=execFileSync('git',['show',baseline+':data/ownership-history/'+name],{maxBuffer:32*1024*1024}),actual=fs.readFileSync(path.join(dir,name));
 assert(original.equals(actual));budget.add({bytes:original.length});budget.add({bytes:actual.length});
 diagnostics.push({path:name,bytes:actual.length,sha256:sha(actual),original_commit:baseline,original_path:'data/ownership-history/'+name,original_diagnostic_footprints_sha256:JSON.parse(actual).footprints_sha256,scope:'Historical diagnostic only; superseded for current repaired footprints. Not a current validation or source of newly recomputed owner rows.'});
}
const note={version:1,execution_commit:head,producer:code,current_ownership_index_sha256:sha(fs.readFileSync(dir+'/index.json')),current_footprints_sha256:index.footprints_sha256,diagnostics,current_validation_paths:['../ownership-before-verification-v1.json','../repaired-ownership-verification-v1.json','../repaired-ownership-runtime-verification-v1.json'],rule:'All original diagnostic bytes and claims remain intact. Their original footprint labels are authoritative for their historical scope; neither the old unchanged-footprints wording nor a prior threshold check certifies the repaired geography. Current changed-ID derivation uses every hash-pinned baseline prepared political source record and the archived exact helpers, without a candidate-recovery filter.',budget:budget.snapshot(),geographic_approval:false,installed:false,published:false};
fs.writeFileSync(output,JSON.stringify(note)+'\n',{flag:'wx'});console.log(JSON.stringify({diagnostics:diagnostics.length,original_bytes_preserved:true}));
