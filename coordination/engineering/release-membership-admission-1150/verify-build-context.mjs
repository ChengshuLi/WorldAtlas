// Full mandatory context validation at a frozen validator code vintage.
// Run from this tool's immutable Git blob, with a fresh owned output filename.
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {registerHooks} from 'node:module';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {gunzipSync} from 'node:zlib';
import assert from 'node:assert/strict';
const [toolCommit,codeCommit,output]=process.argv.slice(1);
for(const commit of [toolCommit,codeCommit])assert.match(commit??'',/^[a-f0-9]{40}$/);
const root=fs.realpathSync(process.cwd()),owned='coordination/engineering/release-membership-admission-1150/';
const sha=b=>createHash('sha256').update(b).digest('hex');
const git=(commit,file)=>execFileSync('git',['show',commit+':'+file],{maxBuffer:32*1024*1024});
const self=owned+'verify-build-context.mjs',prefix='data:text/javascript;base64,';
assert.ok(import.meta.url.startsWith(prefix));assert.deepEqual(Buffer.from(import.meta.url.slice(prefix.length),'base64'),git(toolCommit,self));
const destination=path.resolve(root,output??'');assert.ok(destination.startsWith(path.join(root,owned)+path.sep)&&destination.endsWith('.json'),'Fresh owned JSON output required');
for(let current=destination;current!==root;current=path.dirname(current)){
 let stat;try{stat=fs.lstatSync(current);}catch(e){if(e.code!=='ENOENT')throw e;}
 assert.ok(!stat?.isSymbolicLink(),'Output symlink refused');if(current===destination)assert.equal(stat,undefined,'Existing output refused');
}
assert.ok(fs.statSync(path.dirname(destination)).isDirectory());
const code=new Map(),inputs=new Map(),cache=new Map();
const remember=(inventory,file,commit,raw)=>{const key=commit+':'+file;if(!inventory.has(key)){
 assert.ok(raw.length<=32*1024*1024);const row={path:file,commit,bytes:raw.length,sha256:sha(raw)};
 if(file.endsWith('.gz')){const decoded=gunzipSync(raw,{maxOutputLength:32*1024*1024});row.uncompressed_bytes=decoded.length;row.uncompressed_sha256=sha(decoded);}
 inventory.set(key,row);
}return raw;};
remember(code,self,toolCommit,git(toolCommit,self));remember(code,'package.json',codeCommit,git(codeCommit,'package.json'));
registerHooks({load(url,context,next){if(url.startsWith('file:')){const file=fileURLToPath(url);if(file.startsWith(root+path.sep)&&/\.(js|mjs)$/.test(file)){
 const name=path.relative(root,file).split(path.sep).join('/'),raw=git(codeCommit,name);remember(code,name,codeCommit,raw);return{format:'module',source:raw.toString(),shortCircuit:true};
}}return next(url,context);}});
const candidate=owned+'candidate-build-context-stage.json',original=owned+'original-build-context-stage.json';
const ordinary=(file,vintage='candidate')=>{const commit=vintage==='candidate'?(file.startsWith(owned)?toolCommit:codeCommit):vintage;const key=commit+':'+file;
 if(!cache.has(key))cache.set(key,git(commit,file));return remember(inputs,file,commit,cache.get(key));};
const stage=JSON.parse(ordinary(candidate)),prior=JSON.parse(ordinary(original));
assert.equal(stage.execution_commit,codeCommit);
for(const key of Object.keys(prior))if(!['execution_commit','validator_sources'].includes(key))assert.deepEqual(stage[key],prior[key],key);
const {validateBuildContextStage,BUILD_CONTEXT_VALIDATOR_SOURCES}=await import(pathToFileURL(path.join(root,'scripts/native-ownership/validate-build-context-stage.mjs')).href);
assert.deepEqual(stage.validator_sources.map(p=>p.path).sort(),[...BUILD_CONTEXT_VALIDATOR_SOURCES].sort());
for(const pin of stage.validator_sources){const raw=ordinary(pin.path);assert.equal(raw.length,pin.bytes);assert.equal(sha(raw),pin.sha256);}
// The existing geometry validator also reads its two ordinary proof files.
// Verify those actual materialized bytes against the frozen code-vintage Git blobs.
const materialized=[stage.geometry_manifest,...stage.geometry_files];
for(const pin of materialized){const full=path.join(root,pin.path);assert.ok(fs.lstatSync(full).isFile()&&!fs.lstatSync(full).isSymbolicLink());assert.deepEqual(fs.readFileSync(full),ordinary(pin.path));}
const registry=JSON.parse(gunzipSync(ordinary(stage.releases.path),{maxOutputLength:32*1024*1024}));
await assert.rejects(validateBuildContextStage({root,stagePath:original,readFile:ordinary,expectedReference:registry.releases.at(-1)}),/Context migration input bytes differ: hosted\/geographic-releases.js/);
const result=await validateBuildContextStage({root,stagePath:candidate,readFile:ordinary,expectedReference:registry.releases.at(-1)});
for(const pin of materialized)assert.deepEqual(fs.readFileSync(path.join(root,pin.path)),ordinary(pin.path));
for(const pin of stage.validator_sources)assert.ok([...code.values()].some(row=>row.path===pin.path&&row.sha256===pin.sha256)||pin.path==='package.json');
const compact={receipt:result.receipt,predecessorRelease:result.predecessorRelease,geometry_validation:{proofs:result.geometryValidation.proofs.length,changed_ids:[...result.geometryValidation.changedIds].sort(),retired_ids:[...result.geometryValidation.retiredIds],added_ids:[...result.geometryValidation.addedIds]}};
const proof={tool_commit:toolCommit,execution_commit:codeCommit,original_manifest_sha256:sha(ordinary(original)),candidate_manifest_sha256:sha(ordinary(candidate)),runtime:process.versions.node,inputs:[...inputs.values()],execution_code:[...code.values()],result:compact,limits:'Read-only mandatory context validation; no geometry/source/release edits, installation, deployment, provider writes or scientific approval.'};
const bytes=Buffer.from(JSON.stringify(proof,null,2)+'\n');assert.ok(bytes.length<=32*1024*1024);fs.writeFileSync(destination,bytes,{flag:'wx'});console.log(JSON.stringify({status:result.receipt.status,locations:result.receipt.original_stage.locations,changed_locations:result.receipt.migration.changed_locations,output}));
