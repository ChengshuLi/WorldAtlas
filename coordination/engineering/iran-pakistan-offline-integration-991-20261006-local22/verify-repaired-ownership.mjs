// Exhaustive independent row/evidence preservation readback; no installation.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {execFileSync} from 'node:child_process';
import {candidateBudget,committedPreparationFiles,requirePlainExecution} from '../../../scripts/native-ownership/native-preparation-guards.mjs';
requirePlainExecution();
const root=process.cwd(),prefix='coordination/engineering/iran-pakistan-offline-integration-991-20261006-local22';
const oldDir='data/ownership-history',newDir=prefix+'/repaired-ownership-history-v1',out=prefix+'/repaired-ownership-verification-v1.json';
if(fs.existsSync(out))throw Error('Fresh verification output required');
const head=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
const code=committedPreparationFiles(root,head,['package.json',prefix+'/verify-repaired-ownership.mjs','scripts/native-ownership/native-preparation-guards.mjs']);
const budget=candidateBudget(code),inputs=[];
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const read=(dir,name)=>{assert(!name.split('/').includes('..'));const raw=fs.readFileSync(path.join(dir,name));const pin={path:dir+'/'+name,bytes:raw.length,sha256:sha(raw)};budget.add(pin);inputs.push(pin);return raw;};
const decode=raw=>JSON.parse(raw[0]===31?gunzipSync(raw,{maxOutputLength:32*1024*1024}):raw);
const oldRaw=read(oldDir,'index.json'),old=decode(oldRaw),next=decode(read(newDir,'index.json'));
const receipt=decode(read(newDir,'migration-receipt.json')),changed=new Set(receipt.changed_ids);
assert.equal(changed.size,2);assert.deepEqual(receipt.added_ids,[]);assert.deepEqual(receipt.removed_ids,[]);
assert.equal(next.footprints_sha256,receipt.after_footprints_sha256);assert.equal(old.footprints_sha256,receipt.before_footprints_sha256);
assert.equal(next.incremental_preparation.original_index_sha256,sha(oldRaw));assert.equal(next.incremental_preparation.unknown_changed,false);
for(const field of ['owner_ids','labels','source_ids','statuses_order'])assert.deepEqual(next[field].slice(0,old[field].length),old[field]);
for(const field of ['valid_from','valid_to','locations'])assert.equal(next[field],old[field]);
for(let i=0;i<old.evidence_parts.length;i++){
 const before=old.evidence_parts[i],after=next.evidence_parts[i];assert.deepEqual(after,before);
 const a=read(oldDir,before.path),b=read(newDir,after.path);assert.equal(sha(a),before.sha256);assert(a.equals(b));
}
for(const part of next.evidence_parts.slice(old.evidence_parts.length))assert.equal(sha(read(newDir,part.path)),part.sha256);
const beforeRows=new Map(),originalTargets=new Map();let originalIntervals=0;
for(const part of old.parts){const raw=read(oldDir,part.path);assert.equal(sha(raw),part.sha256);for(const [id,rows] of decode(raw)){assert(!beforeRows.has(id));beforeRows.set(id,sha(Buffer.from(JSON.stringify(rows))));originalIntervals+=rows.length;if(changed.has(id))originalTargets.set(id,rows);}}
assert.equal(beforeRows.size,old.locations);assert.equal(originalIntervals,old.intervals);
const seen=new Set(),statuses={},targetRows={};let intervals=0,reusedIntervals=0;
for(const part of next.parts){const raw=read(newDir,part.path);assert.equal(sha(raw),part.sha256);for(const [id,rows] of decode(raw)){
 assert(beforeRows.has(id)&&!seen.has(id));seen.add(id);intervals+=rows.length;
 if(changed.has(id))targetRows[id]=rows;else {assert.equal(sha(Buffer.from(JSON.stringify(rows))),beforeRows.get(id));reusedIntervals+=rows.length;}
 let previous=null;for(const [a,b,owner,status,evidence] of rows){assert(Number.isInteger(a)&&Number.isInteger(b)&&a!==0&&b!==0&&a<b&&a>=next.valid_from&&b<=next.valid_to&&(previous===null||a>=previous));previous=b;assert(owner===null||Number.isInteger(owner)&&owner>=0&&owner<next.owner_ids.length);assert(Number.isInteger(status)&&status>=0&&status<next.statuses_order.length);assert(Number.isInteger(evidence)&&evidence>=0&&evidence<next.evidence_records);const label=next.statuses_order[status];assert.equal(label==='derived',owner!==null);statuses[label]=(statuses[label]??0)+1;}
}}
assert.equal(seen.size,old.locations);assert.equal(intervals,next.intervals);assert.deepEqual(statuses,next.statuses);assert.equal(reusedIntervals,next.incremental_preparation.reused_intervals);
assert.equal(next.incremental_preparation.reused_locations,old.locations-2);assert.equal(next.incremental_preparation.changed_locations,2);assert.equal(next.incremental_preparation.source_records_scanned,13378);
const archive=decode(read(newDir,next.incremental_preparation.archive_path));assert.equal(archive.original_index_sha256,sha(oldRaw));assert.deepEqual(archive.original_index,old);
const archivedTargets=new Map();for(const part of archive.parts){const raw=read(newDir,part.path);assert.equal(sha(raw),part.sha256);for(const [id,rows] of decode(raw)){assert(changed.has(id)&&!archivedTargets.has(id));archivedTargets.set(id,rows);}}
assert.deepEqual(archivedTargets,originalTargets);
for(const [name,hash] of Object.entries(next.incremental_preparation.retained_prior_archives))assert.equal(sha(read(newDir,name)),hash);
for(const part of next.execution_algorithms)assert.equal(sha(read(newDir,part.path)),part.sha256);
const report={execution_commit:head,producer:code,inputs,locations:seen.size,reused_locations:seen.size-2,changed_ids:[...changed],intervals,reused_intervals:reusedIntervals,derived_intervals:intervals-reusedIntervals,target_intervals:Object.fromEntries(Object.entries(targetRows).map(([id,rows])=>[id,rows.length])),all_unaffected_record_values_exact:true,all_original_evidence_indices_and_bytes_preserved:true,original_changed_rows_archived:true,budget:budget.snapshot(),installed:false,published:false};
fs.writeFileSync(out,JSON.stringify(report)+'\n',{flag:'wx'});console.log(JSON.stringify({...report,producer:undefined,inputs:undefined}));
