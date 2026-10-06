// Integrate recomputed rows only after mandatory full-source/context validation.
// No live import, source interval extension, dictionary renumbering or history transfer.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gzipSync,gunzipSync} from 'node:zlib';
import assert from 'node:assert/strict';
import {validateContextInputStage,CONTEXT_STAGE_PATH} from '../../../scripts/native-ownership/validate-context-input-stage.mjs';
import {validateContextMigration} from '../../../scripts/native-ownership/validate-context-migration.mjs';
import {committedPreparationFiles,requirePlainExecution,candidateBudget} from '../../../scripts/native-ownership/native-preparation-guards.mjs';
requirePlainExecution();
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const prefix='coordination/engineering/iran-pakistan-offline-integration-991-20261006-local22';
const out=path.resolve(root,process.argv[2]??'');
if(!out.startsWith(path.join(root,prefix)+path.sep)||fs.existsSync(out))throw Error('Fresh owned bundle required');
const head=execFileSync('git',['-C',root,'rev-parse','HEAD'],{encoding:'utf8'}).trim(),baseline='d0cc67eac85038159f88a673acbc39b77ab7461d';
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const immutable=(commit,name)=>execFileSync('git',['-C',root,'show',commit+':'+name],{maxBuffer:32*1024*1024});
const code=committedPreparationFiles(root,head,['package.json',prefix+'/prepare-repaired-reference-bundle.mjs',
 'scripts/native-ownership/validate-context-input-stage.mjs','scripts/native-ownership/validate-context-migration.mjs',
 'scripts/native-ownership/native-preparation-guards.mjs','scripts/native-ownership/native-only-inputs.mjs',
 'scripts/native-ownership/compact-context-inputs.mjs','scripts/native-ownership/read-pinned-build-file.mjs',
 'scripts/native-ownership/compile-native-ownership.mjs','scripts/audit-grid-intervals.mjs','scripts/evidence-quality.mjs',
 'src/native-runtime.js','src/native-grid.js','scripts/check-prepared.mjs','scripts/prepare-geographic-release.mjs',
 'scripts/read-geographic-release-manifest.mjs','hosted/geographic-releases.js']);
const inputs=[],budget=candidateBudget(code);
const read=(commit,name)=>{
 const raw=immutable(commit,name),pin={commit,path:name,bytes:raw.length,sha256:sha(raw)};
 inputs.push(pin);budget.add(pin);return raw;
};
const json=(commit,name)=>{const raw=read(commit,name);return JSON.parse(name.endsWith('.gz')?gunzipSync(raw,{maxOutputLength:32*1024*1024}):raw);};
const releases=json(head,prefix+'/successor-release-v1/releases-v7-gzip.json.gz').releases;
const predecessor=releases.at(-2),release=releases.at(-1);
// This existing mandatory stage owns its separate 256 MiB source->compact
// budget. Its complete original inventory supplies actual shard byte hashes.
const sourceStage=await validateContextInputStage({root,expectedReference:predecessor,
 readFile:(name,vintage)=>immutable(vintage==='candidate'?baseline:vintage,name)});
const oldContext='coordination/engineering/native-grid-integration-1010-20261005-local17/context-inputs-v1';
const old=json(baseline,oldContext+'/inputs.json'),next=json(head,prefix+'/repaired-context-v2/inputs.json');
const decodeContext=(commit,dir,manifest)=>manifest.parts.flatMap(part=>{
 const raw=read(commit,dir+'/'+part.path),decoded=gunzipSync(raw,{maxOutputLength:32*1024*1024});
 assert.equal(raw.length,part.bytes);assert.equal(sha(raw),part.sha256);
 assert.equal(decoded.length,part.uncompressed_bytes);assert.equal(sha(decoded),part.uncompressed_sha256);
 return JSON.parse(decoded);
});
const original=decodeContext(baseline,oldContext,old),migrated=decodeContext(head,prefix+'/repaired-context-v2',next);
const candidates=json(baseline,'coordination/engineering/iran-pakistan-native-joint-991-20261006-local21/results-v3/candidates.json');
for(const name of ['index.json','migration-receipt.json']){
 const file=prefix+'/release-proof-v3/'+name;assert(read(head,file).equals(fs.readFileSync(path.join(root,file))));
}
const context=validateContextMigration({original,migrated,candidates,predecessorRelease:predecessor,release,
 migrationManifestFile:path.join(root,prefix,'release-proof-v3/index.json')});
const changed=new Set(context.changed_ids),known=new Set(original.map(f=>f.id));
const scientificRaw=read(head,prefix+'/environment-references-v2.json'),scientific=JSON.parse(scientificRaw);
assert(scientificRaw.equals(read(head,prefix+'/environment-references-v3.json')));
assert.equal(scientific.before_footprints_sha256,predecessor.footprints_sha256);
assert.equal(scientific.after_footprints_sha256,release.footprints_sha256);
assert.deepEqual(scientific.changed_ids,context.changed_ids);
assert.equal(scientific.original_before_values_exactly_reproduced,true);assert.equal(scientific.derived_records,14);
assert.deepEqual(scientific.remaining_attributes,[]);assert.equal(scientific.historical_claims_transferred,false);
const source='data/reference-attributes/',indexRaw=read(baseline,source+'index.json'),index=JSON.parse(indexRaw);
assert.equal(index.footprints_sha256,predecessor.footprints_sha256);assert.equal(index.locations,context.locations);
const types=structuredClone(index.types),values=structuredClone(index.values),oldRows=new Map(),partRows=new Map(),partRaws=new Map();
for(const name of index.parts){
 const raw=read(baseline,source+name);assert.equal(sha(raw),index.parts_sha256[name]);
 const rows=JSON.parse(gunzipSync(raw,{maxOutputLength:32*1024*1024}));partRows.set(name,rows);partRaws.set(name,raw);
 for(const [id,records] of rows){assert(known.has(id));if(!oldRows.has(id))oldRows.set(id,[]);oldRows.get(id).push(...records);}
}
const sortRows=rows=>structuredClone(rows).sort((a,b)=>a[0]-b[0]||a[1]-b[1]);
for(const id of changed)assert.deepEqual(sortRows(oldRows.get(id)),sortRows(scientific.computed.before[id]));
assert.equal([...oldRows.values()].reduce((n,rows)=>n+rows.length,0),index.records);
// Compute the new prepared-shard fingerprint from the mandatory validated
// original inventory plus exact, property-preserving changed shard bytes.
const world=json(baseline,'data/world-index.json'),sourceHashes=new Map(sourceStage.source_inventory.map(pin=>[pin.path,pin.sha256]));
const stage=json(head,prefix+'/results-v2/summary.json');
for(const name of stage.changed_parts){
 const previous=json(baseline,name),actual=json(head,prefix+'/results-v2/stage/'+name);
 const expected={...previous,features:previous.features.map(f=>candidates[f.id]?{...f,geometry:candidates[f.id]}:f)};
 assert.deepEqual(actual,expected);
 const raw=immutable(head,prefix+'/results-v2/stage/'+name);sourceHashes.set(name,sha(raw));
}
const geographySha=sha(Buffer.from(world.parts.map(name=>{const hash=sourceHashes.get('data/'+name);assert(hash);return hash;}).join('')));
fs.mkdirSync(out);
const products=[];
const write=(name,raw)=>{
 budget.add({bytes:raw.length});fs.mkdirSync(path.dirname(path.join(out,name)),{recursive:true});fs.writeFileSync(path.join(out,name),raw,{flag:'wx'});
 products.push({path:name,bytes:raw.length,sha256:sha(raw)});return sha(raw);
};
const encoded=value=>gzipSync(Buffer.from(JSON.stringify(value)+'\n'),{level:9});
const parts=[],activeRows=new Map();
for(const name of index.parts){
 const previous=partRows.get(name),kept=previous.filter(([id])=>!changed.has(id));
 if(!kept.length)continue;
 const raw=kept.length===previous.length?partRaws.get(name):encoded(kept);write(name,raw);parts.push(name);
 for(const [id,records] of kept){if(!activeRows.has(id))activeRows.set(id,[]);activeRows.get(id).push(...records);}
}
const delta=[...changed].sort().map(id=>[id,sortRows(scientific.computed.after[id])]);
const deltaName='incremental-'+sha(scientificRaw).slice(0,16)+'-delta-0.json.gz';write(deltaName,encoded(delta));parts.push(deltaName);
for(const [id,rows] of delta)activeRows.set(id,rows);
const archiveSha=write('migration-before-records.json.gz',encoded([...changed].sort().map(id=>[id,oldRows.get(id)])));
write('migration-new-evidence.json.gz',encoded(scientific.vegetation_evidence.after));
const oldIndexSha=sha(indexRaw),priorPrefix='prior-archives/'+oldIndexSha+'/',retained={};
const tree=execFileSync('git',['-C',root,'ls-tree','-r','--name-only',baseline,'--',source+'prior-archives',source+'incremental-receipt.json',source+'migration-before-records.json.gz',source+'migration-new-evidence.json.gz'],{encoding:'utf8'}).trim().split('\n').filter(Boolean);
for(const file of tree){const name=priorPrefix+file.slice(source.length),raw=read(baseline,file);retained[name]=write(name,raw);}
retained[priorPrefix+'index.json']=write(priorPrefix+'index.json',indexRaw);
const counts=new Map();let total=0;
for(const [id,rows] of activeRows){const seen=new Set();for(const row of rows){
 assert.equal(row.length,4);const type=types[row[0]];assert(type&&values[row[1]]!==undefined);
 assert(Number.isFinite(row[2])&&row[2]>=0&&row[2]<=1&&Number.isFinite(row[3])&&row[3]>=0&&row[3]<=1);
 const interval=JSON.stringify([type.attribute,type.valid_from,type.valid_to]);assert(!seen.has(interval));seen.add(interval);
 const key=JSON.stringify([type.attribute,type.valid_from,type.status]);counts.set(key,(counts.get(key)??0)+1);total++;
}}
assert.equal(total,index.records);assert.equal(activeRows.size,index.represented_locations);
assert.deepEqual(index.types,types);assert.deepEqual(index.values,values);
const receipt={version:1,execution_commit:head,executed_sources:code,inputs,mandatory_original_context_stage:sourceStage,
 before_footprints_sha256:predecessor.footprints_sha256,after_footprints_sha256:release.footprints_sha256,
 original_index_sha256:oldIndexSha,migration_receipt_sha256:context.geometryValidation.proofs[0].receipt_sha256,
 changed_ids:context.changed_ids,added_ids:[],removed_ids:[],reused_locations:context.unchanged_locations,recomputed_locations:2,
 reused_records:total-14,derived_records:14,after_records:total,unknown_changed:false,
 source_recomputation:{commit:head,path:prefix+'/environment-references-v2.json',sha256:sha(scientificRaw)},
 sources:scientific.native_sources,archive:{path:'migration-before-records.json.gz',sha256:archiveSha,locations:2,records:14},
 retained_prior_archives:retained,historical_claims_transferred:false,source_intervals_unchanged:true,source_dictionaries_prefix_preserved:true,
 installed:false,published:false};
const receiptSha=write('incremental-receipt.json',Buffer.from(JSON.stringify(receipt)+'\n'));
index.parts=parts;index.parts_sha256=Object.fromEntries(parts.map(name=>[name,products.find(p=>p.path===name).sha256]));
index.footprints_sha256=release.footprints_sha256;
index.inputs.original_preparation_geography??=index.inputs.geography;index.inputs.geography=geographySha;
index.inputs.footprints_sha256=release.footprints_sha256;index.inputs.incremental_migration_sha256=receipt.migration_receipt_sha256;
index.incremental_preparation={receipt:'incremental-receipt.json',receipt_sha256:receiptSha,original_index_sha256:oldIndexSha,
 reused_locations:context.unchanged_locations,recomputed_locations:2,reused_records:total-14,derived_records:14};
index.vegetation_numerical_review_applicability='Original review retained for unchanged IDs; changed footprints are covered by original-source recomputation and incremental receipt';
write('index.json',Buffer.from(JSON.stringify(index)+'\n'));
write('preparation-verification.json',Buffer.from(JSON.stringify({execution_commit:head,products:[...products],
 locations:context.locations,changed_ids:context.changed_ids,records:total,preserved_original_dictionaries:true,
 source_stage_scope:CONTEXT_STAGE_PATH,budget:budget.snapshot(),installed:false,published:false})+'\n'));
console.log(JSON.stringify({locations:context.locations,records:total,recomputed:2,derived_records:14,parts:parts.length,installed:false}));
