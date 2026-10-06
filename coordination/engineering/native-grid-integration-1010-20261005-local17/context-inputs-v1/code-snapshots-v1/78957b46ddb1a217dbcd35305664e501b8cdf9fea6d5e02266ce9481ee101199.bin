// Immutable original-source -> compact runtime-input stage. No original writes.
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gzipSync,gunzipSync} from 'node:zlib';
import {loadNativeSourceInputs} from './native-only-inputs.mjs';
import {compactContextInputs} from './compact-context-inputs.mjs';
import {committedPreparationFiles,requirePlainExecution,candidateBudget} from './native-preparation-guards.mjs';
requirePlainExecution();
const [baseline,vintage]=process.argv.slice(2);
if(!/^[a-f0-9]{40}$/.test(baseline??'')||!/^[a-zA-Z0-9_-]+$/.test(vintage??''))throw Error('Use IMMUTABLE-BASELINE FRESH-VINTAGE');
const repo=fs.realpathSync('.'),head=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
const code=committedPreparationFiles(repo,head,['package.json',
 'scripts/native-ownership/prepare-context-inputs.mjs','scripts/native-ownership/compact-context-inputs.mjs',
 'scripts/native-ownership/native-only-inputs.mjs','scripts/native-ownership/native-preparation-guards.mjs',
 'src/native-runtime.js','scripts/native-ownership/compile-native-ownership.mjs','src/native-grid.js','scripts/audit-grid-intervals.mjs']);
const inputs=await loadNativeSourceInputs(repo,baseline),sourceFiles=new Map(inputs.sourceFiles.map(file=>[file.path,file]));
const digest=raw=>createHash('sha256').update(raw).digest('hex');
const read=name=>{
 const pin=sourceFiles.get(name);if(!pin)throw Error('Undeclared original input');
 const raw=execFileSync('git',['show',baseline+':'+name],{maxBuffer:32*1024*1024});
 if(raw.length!==pin.bytes||digest(raw)!==pin.sha256)throw Error('Original input bytes changed');
 return JSON.parse(raw[0]===31&&raw[1]===139?gunzipSync(raw,{maxOutputLength:32*1024*1024}):raw);
};
const world=read('data/world-index.json'),features=[];
for(const part of world.parts)features.push(...read('data/'+part).features);
const compact=compactContextInputs(features,inputs.bounds,inputs.manifest.footprints_sha256);
const admission=candidateBudget([...inputs.sourceFiles,...code],{reserveBytes:131072,reserveDescriptors:16});
const directory=path.join('.cache/native-context-inputs',vintage);
fs.mkdirSync('.cache/native-context-inputs',{recursive:true});
if(fs.realpathSync('.cache/native-context-inputs')!==path.join(repo,'.cache/native-context-inputs'))throw Error('Ordinary owned output parent required');
fs.mkdirSync(directory); // A fresh exclusive vintage; existing outputs remain intact.
const parts=[];
for(let first=0;first<compact.features.length;first+=1500){
 const values=compact.features.slice(first,first+1500),raw=Buffer.from(JSON.stringify(values)+'\n');
 if(raw.length>32*1024*1024)throw Error('Compact decoded part exceeds existing file budget');
 const encoded=gzipSync(raw,{level:9}),name='part-'+first+'.json.gz';admission.add({bytes:encoded.length});
 fs.writeFileSync(path.join(directory,name),encoded,{flag:'wx'});
 parts.push({path:name,bytes:encoded.length,sha256:digest(encoded),uncompressed_bytes:raw.length,
  uncompressed_sha256:digest(raw),first_owner:first+1,owners:values.length});
}
const report={version:1,baseline_commit:baseline,execution_commit:head,source_files:inputs.sourceFiles,executed_sources:code,
 original_release:inputs.release.id,footprints_sha256:compact.footprints_sha256,owner_sha256:compact.owner_sha256,
 locations:compact.features.length,vertices:inputs.vertices,parts,scope:compact.scope,
 budget:admission.snapshot(),original_files_written:false,scientific_approval:false,installation_ready:false,
 limits:['Lossless original native geometry and stable ID/parent/index derivative only; complete original metadata remains in source files.',
 'No grid, boundary, factual content, source authority or production delivery change.']};
const raw=Buffer.from(JSON.stringify(report)+'\n');admission.add({bytes:raw.length});
fs.writeFileSync(path.join(directory,'inputs.json'),raw,{flag:'wx'});
console.log(JSON.stringify({directory,report_sha256:digest(raw),parts:parts.length,bytes:parts.reduce((n,p)=>n+p.bytes,0),budget:admission.snapshot()}));
