// Scoped #1295 successor: exact reviewed pointsets, original numerical compiler.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {gzipSync,gunzipSync} from 'node:zlib';
import {compactContextInputs} from '../../../scripts/native-ownership/compact-context-inputs.mjs';
import {nativeRuntimeIndex} from '../../../src/native-runtime.js';
import {compileNativeOwnership} from '../../../scripts/native-ownership/compile-native-ownership.mjs';
import {nativeCandidateManifest,NATIVE_CANONICAL_LATITUDE_SHA256} from '../../../scripts/native-ownership/native-candidate-manifest.mjs';
import {committedPreparationFiles,requirePlainExecution,createNativeCandidateOutput} from '../../../scripts/native-ownership/native-preparation-guards.mjs';
import {shuffleOwnershipBytes} from '../../../src/ownership-codec.js';
import {footprintHash} from '../../../scripts/check-prepared.mjs';
export const BEFORE='6ea7c3613759d7b747c800c399b70c1be24e1f6aea21fc81c389cfdcc78d3eb1';
export const AFTER='b9a3c8bf375217dba3a50d1a022ec7e4ac6c6f1cdedff22845da953c805b7433';
export const TARGETS=['atlas:physical:CAN-103:QUE','atlas:physical:CAN-114:NFL'];
const PROPOSAL='b4b7db357ba92d19df513f188bbd046fe66a35e4';
const PREFIX='coordination/engineering/eastern-two-gap-repair-20261007/run-one/';
const SHA=b=>createHash('sha256').update(b).digest('hex');
const json=x=>Buffer.from(JSON.stringify(x)+'\n');
const safe=p=>typeof p==='string'&&/^[a-zA-Z0-9_.\/-]+$/.test(p)&&p.split('/').every(x=>x&&x!=='.'&&x!=='..');
export function immutableReader(repo,commit){
 assert.match(commit,/^[a-f0-9]{40}$/,'Exact immutable source commit required before Git');
 const files=new Map();
 function read(p){
  assert(safe(p),'Ordinary source path required');
  if(files.has(p))return files.get(p).raw;
  const tree=execFileSync('git',['-C',repo,'ls-tree','-z',commit,'--',p],{encoding:'utf8'});
  assert(/^100(?:644|755) blob /.test(tree)&&tree.slice(tree.indexOf('\t')+1)===p+'\0','Missing ordinary source '+p);
  const oid=tree.split(' ')[2].split('\t')[0];
  const bytes=Number(execFileSync('git',['-C',repo,'cat-file','-s',oid],{encoding:'utf8'}));
  assert(Number.isSafeInteger(bytes)&&bytes>0&&bytes<=32*1024*1024,'Bounded source bytes required');
  const raw=execFileSync('git',['-C',repo,'cat-file','blob',oid],{maxBuffer:32*1024*1024});
  assert.equal(raw.length,bytes);
  const decoded=raw[0]===31&&raw[1]===139?gunzipSync(raw,{maxOutputLength:32*1024*1024}):raw;
  files.set(p,{raw,pin:{commit,path:p,mode:tree.split(' ')[0],blob:oid,bytes,sha256:SHA(raw),decoded_bytes:decoded.length,decoded_sha256:SHA(decoded)}});
  return raw;
 }
 return {read,object:p=>{const raw=read(p);return JSON.parse(raw[0]===31&&raw[1]===139?gunzipSync(raw,{maxOutputLength:32*1024*1024}):raw);},pins:()=>[...files.values()].map(x=>x.pin)};
}
export function loadSuccessor(repo,baseline){
 const current=immutableReader(repo,baseline),reviewed=immutableReader(repo,PROPOSAL);
 const world=current.object('data/world-index.json'),features=[];
 for(const p of world.parts)features.push(...current.object('data/'+p).features);
 assert.equal(features.length,49625,'Complete current world required');
 assert.equal(footprintHash(features),BEFORE,'Current source predecessor is stale');
 const hierarchy=current.read('data/hierarchy.json');
 const pointer=current.object('data/geographic-releases/current-manifest.json');
 const registryRaw=current.read('data/geographic-releases/'+pointer.path);assert.equal(SHA(registryRaw),pointer.sha256);
 const registry=current.object('data/geographic-releases/'+pointer.path),predecessor=registry.releases.at(-1);
 assert.equal(predecessor.version,7);assert.equal(predecessor.footprints_sha256,BEFORE);assert.equal(predecessor.hierarchy_sha256,SHA(hierarchy));
 const proposal=reviewed.object(PREFIX+'proposed-part-29.json.gz');
 const original=current.object('data/geography/part-29.json');
 assert.equal(proposal.features.length,original.features.length);
 const changed=[];
 for(let i=0;i<original.features.length;i++){
  const a=original.features[i],b=proposal.features[i];
  assert.equal(a.id,b.id,'Reviewed part order/identity changed');
  assert.deepEqual({...b,geometry:a.geometry},a,'Reviewed immutable feature fields changed');
  if(!assertGeometryEqual(a.geometry,b.geometry))changed.push(a.id);
 }
 assert.deepEqual(changed.sort(),[...TARGETS].sort(),'Only the exact two reviewed additions are allowed');
 const byId=new Map(proposal.features.map(f=>[f.id,f]));
 const after=features.map(f=>byId.get(f.id)??f);
 assert.equal(footprintHash(after),AFTER);
 const manifestRaw=current.read('data/canonical-grid/manifest.json'),manifest=JSON.parse(manifestRaw);
 assert.equal(manifest.size,262166);assert.equal(manifest.coordinateBits,19);
 const boundsRaw=current.read('data/canonical-grid/'+manifest.bounds.path);assert.equal(SHA(boundsRaw),manifest.bounds.sha256);
 const bounds=JSON.parse(gunzipSync(boundsRaw,{maxOutputLength:32*1024*1024}));
 const membership=current.read('data/canonical-grid/'+manifest.province_membership.path);assert.equal(SHA(membership),manifest.province_membership.sha256);
 const compact=compactContextInputs(after,bounds,AFTER);
 const old=compactContextInputs(features,bounds,BEFORE);assert.equal(old.owner_sha256,compact.owner_sha256);
 const latitudePath='coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz';
 const latitudeEncoded=current.read(latitudePath),latitudeRaw=gunzipSync(latitudeEncoded,{maxOutputLength:manifest.size*8});
 assert.equal(latitudeRaw.length,manifest.size*8);assert.equal(SHA(latitudeRaw),NATIVE_CANONICAL_LATITUDE_SHA256);
 const latitudes=Float64Array.from({length:manifest.size},(_,i)=>latitudeRaw.readDoubleLE(i*8));
 assert(latitudes.every((v,i)=>Number.isFinite(v)&&v>=-90&&v<=90&&(i===0||v<latitudes[i-1])),'Normative latitude domain/order differs');
 const crosswalk=reviewed.read(PREFIX+'crosswalk.json.gz');
 const key=SHA(json([predecessor.id,8,AFTER,SHA(crosswalk)]));
 return {features:compact.features,old:old.features,index:nativeRuntimeIndex(compact.features),manifest,manifestRaw,predecessor,registry,
  sourceFiles:[...current.pins(),...reviewed.pins()],ownerSha:compact.owner_sha256,latitudes,
  releaseId:'geography:review:'+key,sourceId:'source:atlas:geographic-review:'+key,
  latitude:{root:'repository',role:'immutable-normative-rule-input',path:latitudePath,commit:baseline,bytes:latitudeEncoded.length,sha256:SHA(latitudeEncoded),decoded_bytes:latitudeRaw.length,decoded_sha256:SHA(latitudeRaw)},
  originalCanonicalSha:SHA(manifestRaw)};
}
function assertGeometryEqual(a,b){try{assert.deepEqual(a,b);return true;}catch{return false;}}
export function executedClosure(repo,head){
 const names=new Set(['package.json']);
 function visit(p){if(names.has(p))return;names.add(p);const text=fs.readFileSync(path.join(repo,p),'utf8');
  for(const match of text.matchAll(/(?:from\s*|import\s*)['"]([^'"]+)['"]/g))if(match[1].startsWith('.'))visit(path.posix.normalize(path.posix.join(path.posix.dirname(p),match[1])));
 }
 visit(path.relative(repo,fileURLToPath(import.meta.url)));return committedPreparationFiles(repo,head,[...names].sort());
}
export async function run(baseline,vintage,{inputOnly=false}={}){
 requirePlainExecution();assert.match(baseline,/^[a-f0-9]{40}$/);assert.match(vintage,/^[a-zA-Z0-9_-]+$/);
 const repo=fs.realpathSync('.'),head=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
 const code=executedClosure(repo,head),inputs=loadSuccessor(repo,baseline);
 const capsule={baseline_commit:baseline,execution_commit:head,source_files:inputs.sourceFiles,executed_sources:code,
  original_canonical_sha256:inputs.originalCanonicalSha,owner_sha256:inputs.ownerSha,before_footprints_sha256:BEFORE,after_footprints_sha256:AFTER,
  release_id:inputs.releaseId,locations:inputs.features.length,software:{node:process.version,v8:process.versions.v8,zlib:process.versions.zlib,platform:process.platform,arch:process.arch},
  source_approval:'Only two Main-approved physical-reference additions; no legal/water/historical-cause approval'};
 if(inputOnly){console.log(JSON.stringify(capsule));return capsule;}
 const out=createNativeCandidateOutput(repo,'.cache/native-grid-candidates/'+vintage),products=[];
 const write=(p,raw,decoded=raw)=>{assert(safe(p));assert(raw.length<=32*1024*1024&&decoded.length<=32*1024*1024);const dest=path.join(out,p);fs.mkdirSync(path.dirname(dest),{recursive:true});fs.writeFileSync(dest,raw,{flag:'wx'});const pin={path:p,bytes:raw.length,sha256:SHA(raw),decoded_bytes:decoded.length,decoded_sha256:SHA(decoded)};products.push(pin);return pin;};
 const compactParts=[];
 for(let first=0;first<inputs.features.length;first+=1500){const raw=json(inputs.features.slice(first,first+1500));compactParts.push({...write('context/part-'+first+'.json.gz',gzipSync(raw,{level:9}),raw),first_owner:first+1,owners:Math.min(1500,inputs.features.length-first)});}
 const compiled=await compileNativeOwnership(inputs.index,{size:inputs.manifest.size,latitudes:inputs.latitudes,
  writePart:async(part,words)=>{const raw=Buffer.alloc(words.length*4);words.forEach((v,i)=>raw.writeUInt32LE(v,i*4));return {...part,...write(`native-v1/ownership/${part.kind}-${part.offset}.bin.gz`,gzipSync(shuffleOwnershipBytes(words),{level:9}),raw),encoding:'byte-shuffle'};},
  onBlock:block=>fs.writeFileSync(path.join(out,'progress.json'),json({phase:'compiling',...block}))});
 // Existing helper binds archival identities/rule; successor pointset provenance is explicit.
 const manifest=nativeCandidateManifest({original:inputs.manifest,originalSha256:inputs.originalCanonicalSha,baselineCommit:baseline,evaluationCommit:head,
  releaseId:inputs.releaseId,rosterSha256:inputs.ownerSha,ownerCount:inputs.features.length,latitude:{...inputs.latitude,commit:head},compiled});
 manifest.footprints_sha256=AFTER;manifest.hierarchy_sha256=inputs.predecessor.hierarchy_sha256;
 manifest.provenance.original_source_point_sets_unchanged=false;
 manifest.provenance.source_migration={issue:1295,proposal_commit:PROPOSAL,baseline_commit:baseline,before_footprints_sha256:BEFORE,after_footprints_sha256:AFTER,changed_ids:TARGETS,history_transfer:'none',compact_context_owner_sha256:inputs.ownerSha};
 write('manifest.json',json(manifest));write('context-index.json',json({version:1,parts:compactParts,locations:49625,footprints_sha256:AFTER,owner_sha256:inputs.ownerSha}));
 write('execution.json',json(capsule));
 const raw=json({version:1,...capsule,compiled,products,scope:'Complete successor native measurement; factual/physical approval remains separate',installation_ready:false});write('report.json.gz',gzipSync(raw,{level:9}),raw);
 fs.writeFileSync(path.join(out,'progress.json'),json({phase:'complete',checked_rows:compiled.checked_rows,checked_cells:compiled.checked_cells,products:products.length}));
 console.log(JSON.stringify({output:out,checked_cells:compiled.checked_cells,products:products.length}));
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){const [baseline,vintage,option]=process.argv.slice(2);if(option&&!['--input-only'].includes(option))throw Error('Unknown option');await run(baseline,vintage,{inputOnly:option==='--input-only'});}
