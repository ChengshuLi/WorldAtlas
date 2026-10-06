// Restore complete, hash-pinned compact geometry snapshots for scoped ownership derivation.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {committedPreparationFiles,requirePlainExecution,candidateBudget} from '../../../scripts/native-ownership/native-preparation-guards.mjs';
requirePlainExecution();
const root=process.cwd(),prefix='coordination/engineering/iran-pakistan-offline-integration-991-20261006-local22';
const output=process.argv[2];
if(!output?.startsWith(prefix+'/')||fs.existsSync(output)||path.resolve(output).startsWith(path.resolve(root,prefix)+path.sep)===false)throw Error('Fresh owned output required');
const head=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),baseline='d0cc67eac85038159f88a673acbc39b77ab7461d';
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const producer=committedPreparationFiles(root,head,['package.json',prefix+'/prepare-ownership-snapshots.mjs','scripts/native-ownership/native-preparation-guards.mjs','scripts/prepare-ownership-incremental.py']);
const budget=candidateBudget(producer),inputs=[],products=[];
function read(commit,name){const raw=execFileSync('git',['show',commit+':'+name],{maxBuffer:32*1024*1024});const pin={commit,path:name,bytes:raw.length,sha256:sha(raw)};budget.add(pin);inputs.push(pin);return raw;}
function write(name,raw){budget.add({bytes:raw.length});const file=path.join(output,name);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,raw,{flag:'wx'});products.push({path:name,bytes:raw.length,sha256:sha(raw)});}
const verification=JSON.parse(read(head,prefix+'/repaired-context-verification-v2.json'));
assert.equal(verification.locations,49625);
for(const [tag,commit,dir] of [['before',baseline,'coordination/engineering/native-grid-integration-1010-20261005-local17/context-inputs-v1'],['after',head,prefix+'/repaired-context-v2']]){
 const manifest=JSON.parse(read(commit,dir+'/inputs.json')),parts=[],features=[];
 for(const part of manifest.parts){const raw=read(commit,dir+'/'+part.path);assert.equal(raw.length,part.bytes);assert.equal(sha(raw),part.sha256);const decoded=gunzipSync(raw,{maxOutputLength:32*1024*1024});assert.equal(sha(decoded),part.uncompressed_sha256);assert.equal(decoded.length,part.uncompressed_bytes);features.push(...JSON.parse(decoded));write(tag+'/'+part.path,raw);parts.push({path:part.path,bytes:raw.length,sha256:sha(raw)});}
 assert.equal(features.length,49625);assert.equal(new Set(features.map(f=>f.id)).size,features.length);
 const pairs=features.map(f=>[f.id,f.geometry]).sort((a,b)=>a[0].localeCompare(b[0]));const footprint=sha(Buffer.from(JSON.stringify(pairs)));
 const receipt=JSON.parse(read(head,prefix+'/release-proof-v3/migration-receipt.json'));assert.equal(footprint,receipt[tag+'_footprints_sha256']);
 write(tag+'/world.json',Buffer.from(JSON.stringify({version:1,parts,locations:features.length,footprints_sha256:footprint})+'\n'));
}
const ownership=JSON.parse(read(baseline,'data/ownership-history/index.json'));
// The baseline explicitly pins the empty non-example boundary set. No date
// override is silently omitted: a nonempty baseline fingerprint rejects here.
assert.equal(ownership.inputs.boundary_versions,sha(Buffer.from('[]')));
write('boundaries.json',Buffer.from('[]\n'));
write('migration-receipt.json',read(head,prefix+'/release-proof-v3/migration-receipt.json'));
write('preparation-verification.json',Buffer.from(JSON.stringify({execution_commit:head,producer,inputs,products,budget:budget.finish(),locations:49625,non_example_boundary_versions:0,installed:false,published:false})+'\n'));
console.log(JSON.stringify({locations:49625,products:products.length,budget:budget.finish()}));
