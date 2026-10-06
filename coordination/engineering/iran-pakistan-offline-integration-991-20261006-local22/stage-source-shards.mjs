// Preserve original JSON geometry ordering as well as every unchanged source value.
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {gunzipSync} from 'node:zlib';
import {candidateBudget,committedPreparationFiles,requirePlainExecution} from '../../../scripts/native-ownership/native-preparation-guards.mjs';
import {footprintHash} from '../../../scripts/check-prepared.mjs';
requirePlainExecution();
const prefix='coordination/engineering/iran-pakistan-offline-integration-991-20261006-local22',out=prefix+'/source-shards-v1';
assert(!fs.existsSync(out));
const head=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),baseline='d0cc67eac85038159f88a673acbc39b77ab7461d';
const code=committedPreparationFiles(process.cwd(),head,['package.json',prefix+'/stage-source-shards.mjs','scripts/native-ownership/native-preparation-guards.mjs','scripts/check-prepared.mjs']);
const sha=b=>createHash('sha256').update(b).digest('hex'),budget=candidateBudget(code),inputs=[],products=[];
const read=p=>{const raw=fs.readFileSync(p);budget.add({bytes:raw.length});inputs.push({path:p,bytes:raw.length,sha256:sha(raw)});return raw;};
const dir=prefix+'/repaired-context-v2',index=JSON.parse(read(dir+'/inputs.json')),context=[];
for(const part of index.parts){const raw=read(dir+'/'+part.path);assert.equal(raw.length,part.bytes);assert.equal(sha(raw),part.sha256);const decoded=gunzipSync(raw,{maxOutputLength:32*1024*1024});assert.equal(sha(decoded),part.uncompressed_sha256);assert.equal(decoded.length,part.uncompressed_bytes);context.push(...JSON.parse(decoded));}
assert.equal(footprintHash(context),index.footprints_sha256);const byId=new Map(context.map(f=>[f.id,f]));
const targets=new Set(['gb:IRN:ADM2:26516999B17111396986996','gb:PAK:ADM2:60131773B78019453337506']);const changed=[];
fs.mkdirSync(out);
for(const file of ['part-11.json','part-17.json']){
 const p='data/geography/'+file,raw=execFileSync('git',['show',baseline+':'+p],{maxBuffer:32*1024*1024});budget.add({bytes:raw.length});inputs.push({commit:baseline,path:p,bytes:raw.length,sha256:sha(raw)});const shard=JSON.parse(raw);
 for(const feature of shard.features){const after=byId.get(feature.id);assert(after);if(targets.has(feature.id)){feature.geometry=after.geometry;changed.push(feature.id);}else assert.equal(JSON.stringify(feature.geometry),JSON.stringify(after.geometry));}
 const result=Buffer.from(JSON.stringify(shard));budget.add({bytes:result.length});fs.writeFileSync(out+'/'+file,result,{flag:'wx'});fs.writeFileSync(p,result);assert.deepEqual(fs.readFileSync(p),result);products.push({path:out+'/'+file,destination:p,bytes:result.length,sha256:sha(result)});
}
assert.deepEqual(changed.sort(),[...targets].sort());
// The complete original compact stage already verifies all unchanged raw shards.
// Match these two whole shard geometries to the exact selected compact context.
fs.writeFileSync(out+'/verification.json',JSON.stringify({version:1,execution_commit:head,baseline_commit:baseline,code,inputs,products,changed_ids:changed,expected_footprints_sha256:index.footprints_sha256,budget:budget.snapshot(),published:false,correction:'Earlier Python source staging reordered geometry object keys; coordinates were unchanged, but the normative application footprint hash must retain original ordering.'})+'\n',{flag:'wx'});
console.log(JSON.stringify({changed_ids:changed,budget:budget.snapshot()}));
