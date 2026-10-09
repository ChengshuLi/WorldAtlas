// Complete source preadmission for the original numerical phase plus the third
// continuation. Package-issued code authority remains independent of this data.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {admitCurrentExecution} from '../eastern-two-gap-repair-native-20261007/current-execution.mjs';
import {reserveArcticContinuation} from './arctic-context.mjs';
const TOTAL=256*1024*1024,CAP=32*1024*1024;
const CATALOGUE='c30a7f4412ee422c2995e305d227aaf32d09adddb8b670a116f2aed3502429f0';
const same=(a,b)=>['dev','ino','size','mode','mtimeMs','ctimeMs'].forEach(k=>assert.equal(a[k],b[k],'Ordinary identity changed'));
function ordinary(root,pin){
 assert(typeof pin.path==='string'&&!path.isAbsolute(pin.path)&&pin.path.split('/').every(s=>s&&s!=='.'&&s!=='..')&&!pin.path.includes('\\'));
 assert(Number.isSafeInteger(pin.bytes)&&pin.bytes>=0&&pin.bytes<=CAP&&/^[a-f0-9]{64}$/.test(pin.sha256));
 const file=path.join(root,pin.path);for(let p=file;;p=path.dirname(p)){assert(!fs.lstatSync(p).isSymbolicLink());if(p===path.dirname(p))break}
 const stat=fs.lstatSync(file);assert(stat.isFile()&&(stat.mode&511)===420);assert.equal(stat.size,pin.bytes);return {file,stat};
}
function authenticate(root,pin){
 const {file,stat}=ordinary(root,pin);const fd=fs.openSync(file,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW);const hash=createHash('sha256');const buffer=Buffer.allocUnsafe(1024*1024);
 try{same(stat,fs.fstatSync(fd));let n;while((n=fs.readSync(fd,buffer,0,buffer.length,null)))hash.update(buffer.subarray(0,n));same(stat,fs.fstatSync(fd));same(stat,fs.lstatSync(file));}finally{fs.closeSync(fd)}
 assert.equal(hash.digest('hex'),pin.sha256,'Whole prior numerical body changed');return file;
}
function boundedMetadataBytes(root,relative,bytes){
 assert(bytes<=131072);const {file,stat}=ordinary(root,{path:relative,bytes,sha256:'0'.repeat(64)});
 const fd=fs.openSync(file,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW);let raw;
 try{same(stat,fs.fstatSync(fd));raw=fs.readFileSync(fd);same(stat,fs.fstatSync(fd));}finally{fs.closeSync(fd)}
 same(stat,fs.lstatSync(file));assert.equal(raw.length,bytes);return raw;
}
function metadata(root,pin){assert(pin.bytes<=131072);const file=authenticate(root,pin);return JSON.parse(fs.readFileSync(file));}
export function preflightArcticPackage({root,stageRaw,stage,priorImage}){
 assert.equal(fs.realpathSync(root),root);assert.equal(fs.realpathSync(priorImage),priorImage);assert(priorImage.startsWith(root+'/.cache/'));
 const name=process.env.WORLDATLAS_CURRENT_EXECUTION_PATH,expected=process.env.WORLDATLAS_CURRENT_EXECUTION_SHA256;
 assert.equal(name,'.cache/current-context-execution.json');assert(/^[a-f0-9]{64}$/.test(expected??''));
 const recordSize=fs.lstatSync(path.join(root,name)).size;
 assert(process.execPath&&fs.statSync(process.execPath).size+recordSize+stageRaw.length+stage.numericalCatalogue.bytes<TOTAL,'Bounded metadata discovery admission');
 const record=metadata(root,{path:name,bytes:recordSize,sha256:expected});
 assert.equal(record.stage_root,root);assert.equal(record.source_root,fs.realpathSync(process.env.WORLDATLAS_PACKAGE_SOURCE_ROOT));assert(['scripts/build-static-inner.mjs','scripts/build-hosted-inner.mjs'].includes(record.entry_point),'Actual package inner entry required');
 const current=admitCurrentExecution(record,[record.source_root,root]);
 assert.equal(stage.numericalCatalogue.sha256,CATALOGUE);
 const catalogue=metadata(root,stage.numericalCatalogue);assert.equal(catalogue.kind,'original-v6-v7-v8-complete-numerical-input-catalogue');assert.equal(catalogue.stage_sha256,'78347715e701c7e7d9775d17f3934dd3c1b61dbc46533d6179c979ae629d69d7');assert.equal(catalogue.prior_stage_sha256,'471e6a71856c13b5856cd74f24b79cc9961b3b091980e8b9106a19c1f32a2765');assert.equal(catalogue.historical_code_reserved_bytes,current.historical_code_reserved_bytes);
 const reservation=reserveArcticContinuation({root,stageRaw,stage});
 const admitted=new Map();let numerical=stage.numericalCatalogue.bytes,descriptors=1;
 for(const pin of catalogue.files){assert(['root','prior'].includes(pin.space));const physical=pin.space==='root'?root:priorImage;const {file}=ordinary(physical,pin);const previous=admitted.get(file);if(previous)assert.deepEqual(previous,pin);else{admitted.set(file,pin);numerical+=pin.bytes+(pin.decoded_bytes??0);descriptors++;}assert(Number.isSafeInteger(pin.decoded_bytes??0)&&(pin.decoded_bytes??0)<=CAP);}
 for(const allocation of catalogue.retained_allocations){assert(['complete-retained-record-variants','complete-row-byte-layout'].includes(allocation.kind));assert(Number.isSafeInteger(allocation.bytes)&&allocation.bytes>0&&allocation.bytes<=CAP);numerical+=allocation.bytes;descriptors++;}
 const complete=current.complete_phase_bytes+numerical+reservation.reservedBytes;
 const count=current.current_code_physical_roots.length*record.files.length+1+descriptors+reservation.reservedDescriptors;
 assert(count<=512,'Complete unique code/runtime/input descriptor limit');assert(complete<=TOTAL,'Entire original plus third numerical phase before runtime/body authentication');
 // All complete physical source bodies are authenticated only after the combined
 // prospective cap passes. Their later decoder and original scientific checks remain.
 for(const [file,pin] of admitted){const base=pin.space==='root'?root:priorImage;assert.equal(authenticate(base,pin),file);}
 for(const pin of reservation.pins.values())authenticate(root,pin);
 return {record,reservation,complete_phase_bytes:complete,descriptors:count,numerical_catalogue_sha256:CATALOGUE,original_acquisitions_and_validations_still_required:true};
}


// This distinct route is ordinary application consumption, not a numerical
// qualification phase. Preserve member caps and report complete real bytes;
// do not apply the unrelated aggregate numerical cap to the normal package.
export function preflightArtifactPackage({source, stage, sidecar}) {
 assert.equal(sidecar.version,4);assert.equal(sidecar.kind,'arctic-qualified-artifact-application-consumption-v1');assert.equal(sidecar.issue,1520);
 const certificatePin=sidecar.artifact_consumption.certificate;
 const certificate=metadata(stage,certificatePin);
 assert.equal(certificate.kind,'qualified-arctic-immutable-product-certificate-v1');
 assert.equal(certificate.issue,1520);
 assert(Array.isArray(certificate.application_inputs)&&certificate.application_inputs.length>0);
 const pins=[certificatePin,sidecar.artifact_consumption.review,...certificate.application_inputs];
 const physical=new Map();let encoded=0,decoded=0;
 for(const root of new Set([source,stage]))for(const pin of pins){
  assert(['root','prior','image'].includes(pin.space??'root'));
  assert.equal(pin.mode,'100644');
  if(pin.space==='prior'||pin.space==='image'){
   assert(Number.isSafeInteger(pin.bytes)&&pin.bytes>=0&&pin.bytes<=CAP&&/^[a-f0-9]{64}$/.test(pin.sha256));
   assert(Number.isSafeInteger(pin.decoded_bytes??0)&&(pin.decoded_bytes??0)<=CAP);
   continue; // Reconstructed members: physical transport is in this roster,
             // complete member admission/authentication occurs after restoration.
  }
  const {file}=ordinary(root,pin);
  const previous=physical.get(file);if(previous){assert.deepEqual(previous,pin);continue;}
  physical.set(file,pin);encoded+=pin.bytes;
  assert(Number.isSafeInteger(pin.decoded_bytes??0)&&(pin.decoded_bytes??0)<=CAP);decoded+=pin.decoded_bytes??0;
 }
 assert(Number.isSafeInteger(encoded+decoded));
 return {version:1,kind:'qualified-artifact-normal-package-stat-admission',
  numerical_producers_invoked:false,numerical_aggregate_cap_applied:false,
  encoded_input_bytes:encoded,decoded_input_bytes:decoded,
  distinct_physical_members:physical.size,
  declared_reconstructed_members:certificate.application_inputs.filter(pin=>['prior','image'].includes(pin.space)).length,
  reconstructed_member_bytes:certificate.application_inputs.filter(pin=>['prior','image'].includes(pin.space)).reduce((total,pin)=>total+pin.bytes+(pin.decoded_bytes??0),0),
  reconstructed_members_authenticated_before_consumption_in_inner:true,installed_runtime_bytes:fs.statSync(process.execPath).size,
  certificate_sha256:certificatePin.sha256,ordinary_member_cap:CAP};
}

// Outer boundary: bounded immutable metadata discovery precedes execution
// issuance. No old bank is restored here; the inner boundary authenticates its
// actual complete reconstructed source bodies before the numerical methods.
export function preflightOuterArcticPackage({source,stage,entry}){
 const relative='coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/context-stage-v9.json';
 const file=path.join(stage,relative);let initial;
 try{initial=fs.lstatSync(file);}catch(error){if(error.code==='ENOENT')return null;throw error;}
 assert(initial.isFile()&&!initial.isSymbolicLink()&&initial.size<=131072);
 const runtime=fs.statSync(process.execPath).size;assert(runtime+initial.size+131072<TOTAL,'Bounded metadata discovery before first runtime open');
 const raw=boundedMetadataBytes(stage,relative,initial.size);
 const sourceRaw=boundedMetadataBytes(source,relative,initial.size);assert(raw.equals(sourceRaw),'Package sidecar differs from actual source');
 const sidecar=JSON.parse(raw);
 if(sidecar.version===4)return preflightArtifactPackage({source,stage,sidecar});
 assert.equal(sidecar.numericalCatalogue.sha256,CATALOGUE);
 const catalogue=metadata(stage,sidecar.numericalCatalogue);assert.equal(catalogue.kind,'original-v6-v7-v8-complete-numerical-input-catalogue');assert.equal(catalogue.stage_sha256,'78347715e701c7e7d9775d17f3934dd3c1b61dbc46533d6179c979ae629d69d7');
 assert.equal(catalogue.prior_stage_sha256,'471e6a71856c13b5856cd74f24b79cc9961b3b091980e8b9106a19c1f32a2765');assert.equal(catalogue.files.length,69);
 const reservation=reserveArcticContinuation({root:stage,stageRaw:raw,stage:sidecar,declaredOriginalInputs:catalogue.files});
 let numerical=sidecar.numericalCatalogue.bytes;
 const identities=new Map();
 for(const pin of catalogue.files){assert(['root','prior'].includes(pin.space));assert(Number.isSafeInteger(pin.bytes)&&pin.bytes>=0&&pin.bytes<=CAP);assert(Number.isSafeInteger(pin.decoded_bytes??0)&&(pin.decoded_bytes??0)<=CAP);assert(/^[a-f0-9]{64}$/.test(pin.sha256));const key=pin.space+':'+pin.path;assert(!identities.has(key));identities.set(key,pin);numerical+=pin.bytes+(pin.decoded_bytes??0);}
 for(const p of catalogue.retained_allocations){assert(Number.isSafeInteger(p.bytes)&&p.bytes>0&&p.bytes<=CAP);numerical+=p.bytes;}
 // Reserve complete actual metadata record capacity before recursive discovery.
 let complete=runtime+570577+131072+131072+numerical+reservation.reservedBytes;
 let descriptors=1+1+catalogue.files.length+catalogue.retained_allocations.length+reservation.reservedDescriptors;
 assert(complete<=TOTAL&&descriptors<=512,'Complete source union exceeds cap before code/runtime opens');
 const names=new Set();
 function visit(p,parse=true){
  assert(!path.isAbsolute(p)&&p.split('/').every(s=>s&&s!=='.'&&s!=='..'));if(names.has(p))return;names.add(p);
  const roots=[source,stage];let bytes;
  for(const root of roots){const pathname=path.join(root,p);for(let a=pathname;;a=path.dirname(a)){assert(!fs.lstatSync(a).isSymbolicLink());if(a===path.dirname(a))break}const stat=fs.lstatSync(pathname);assert(stat.isFile()&&[420,493].includes(stat.mode&511)&&stat.size<=CAP);if(bytes!==undefined)assert.equal(bytes,stat.size);bytes=stat.size;}
  complete+=bytes*new Set(roots).size;descriptors+=new Set(roots).size;assert(complete<=TOTAL&&descriptors<=512,'Complete code/context/runtime union exceeds cap BEFORE next code body open');
  if(parse){const code=fs.readFileSync(path.join(source,p));for(const m of code.toString('utf8').matchAll(/(?:from\s*|import\s*(?:\(\s*)?)['"]([^'"]+)['"]/g))if(m[1].startsWith('.'))visit(path.posix.normalize(path.posix.join(path.posix.dirname(p),m[1])));}
 }
 visit('package.json',false);visit('.github/package-inputs.json',false);
 for(const p of ['scripts/native-ownership/validate-build-context-stage.mjs','coordination/engineering/eastern-two-gap-repair-native-20261007/current-execution.mjs','scripts/package-build.mjs',entry])visit(p);
 return {version:1,kind:'complete-original-plus-third-before-first-execution-authentication',catalogue_sha256:CATALOGUE,sidecar_sha256:createHash('sha256').update(raw).digest('hex'),complete_phase_bytes:complete,descriptors,code_files:[...names].sort(),original_restored_bodies_rechecked_in_inner:true,second_restoration_performed:false};
}
