// Independent file readback for the bounded original->compact transform stage.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {gunzipSync} from 'node:zlib';
import {loadNativeSourceInputs} from './native-only-inputs.mjs';
import {compactContextInputs} from './compact-context-inputs.mjs';
import {requirePlainExecution,committedPreparationFiles} from './native-preparation-guards.mjs';
requirePlainExecution();
const [first,second]=process.argv.slice(2);
if(!/^[a-zA-Z0-9_-]+$/.test(first??'')||!/^[a-zA-Z0-9_-]+$/.test(second??'')||first===second)
 throw Error('Use TWO DISTINCT COMPLETE VINTAGES');
const directory=name=>path.resolve('.cache/native-context-inputs',name);
const digest=raw=>createHash('sha256').update(raw).digest('hex');
const inventory=dir=>fs.readdirSync(dir,{withFileTypes:true}).map(item=>{
 if(!item.isFile())throw Error('Ordinary complete stage files required');
 const raw=fs.readFileSync(path.join(dir,item.name));return {path:item.name,bytes:raw.length,sha256:digest(raw)};
}).sort((a,b)=>a.path.localeCompare(b.path));
const one=inventory(directory(first)),two=inventory(directory(second));assert.deepEqual(one,two);
const report=JSON.parse(fs.readFileSync(path.join(directory(first),'inputs.json')));
const repo=fs.realpathSync('.'),head=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
const code=committedPreparationFiles(repo,head,['package.json','scripts/native-ownership/verify-context-inputs.mjs',
 'scripts/native-ownership/compact-context-inputs.mjs','scripts/native-ownership/native-only-inputs.mjs',
 'scripts/native-ownership/native-preparation-guards.mjs','src/native-runtime.js',
 'scripts/native-ownership/compile-native-ownership.mjs','src/native-grid.js','scripts/audit-grid-intervals.mjs']);
const source=await loadNativeSourceInputs(repo,report.baseline_commit);
assert.deepEqual(report.source_files,source.sourceFiles);
assert.equal(report.original_release,source.release.id);assert.equal(report.installation_ready,false);
const features=[];let next=1;
for(const part of report.parts){
 if(part.first_owner!==next||!/^part-[0-9]+\.json\.gz$/.test(part.path))throw Error('Incomplete source-stage part inventory');
 const encoded=fs.readFileSync(path.join(directory(first),part.path));
 assert.equal(encoded.length,part.bytes);assert.equal(digest(encoded),part.sha256);
 const raw=gunzipSync(encoded,{maxOutputLength:32*1024*1024});
 assert.equal(raw.length,part.uncompressed_bytes);assert.equal(digest(raw),part.uncompressed_sha256);
 const values=JSON.parse(raw);assert.equal(values.length,part.owners);
 for(const feature of values){assert.equal(feature.pixelIndex,next++);features.push(feature);}
}
assert.equal(report.parts.length+1,one.length);assert.equal(features.length,source.roster.length);
const result=compactContextInputs(features,source.bounds,source.manifest.footprints_sha256);
assert.equal(result.owner_sha256,report.owner_sha256);
for(let i=0;i<features.length;i++){
 assert.equal(features[i].id,source.roster[i].id);assert.equal(features[i].properties.parent_id,source.roster[i].parent_id);
}
const proof={version:1,scope:'Complete original-native-source to lossless geometry/ID/parent/index derivative; no source approval or live content change',
 baseline_commit:report.baseline_commit,preparation_commit:report.execution_commit,verification_commit:head,
 executed_sources:code,source_files:source.sourceFiles,products:one,locations:features.length,vertices:source.vertices,
 footprints_sha256:result.footprints_sha256,owner_sha256:result.owner_sha256,
 run_one_sha256:digest(Buffer.from(JSON.stringify(one))),run_two_sha256:digest(Buffer.from(JSON.stringify(two))),
 original_source_files_verified:source.sourceFiles.length,complete_original_ids_and_parents:true,
 unchanged_original_point_sets:true,installation_ready:false,scientific_approval:false};
console.log(JSON.stringify(proof));
