import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {ImmutableReader,readArtifactConsumption,scientificArtifactIdentity,scientificNativeBase,requireCurrentArtifactBase,requireScientificArtifactSuccession} from '../scripts/check-effective-geographic-regression.mjs';
const root='coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/qualified-artifacts/';
const read=name=>JSON.parse(fs.readFileSync(root+name));
const original=read('consumption-certificate.json'),originalCode=read('application-consumer-code.json');
const successor=read('consumption-certificate-canonical-hash-1963.json'),successorCode=read('application-consumer-code-canonical-hash-1963.json');
const hash=value=>createHash('sha256').update(JSON.stringify(value)).digest('hex');
const expected=scientificArtifactIdentity(original,originalCode);
const base={version:1,method:'native-linear-evenodd-first-owner-v1',manifest_path:original.selected_artifact_bindings.native_manifest.path,sha256:original.native_manifest_sha256,release_id:original.steps.at(-1).successor_release_id,selected_geography:original.selected_artifact_bindings.selected_geography,artifact_consumption:{certificate:original.application_consumer_code,review:{}}};

test('actual 1963 body-only successor preserves all156 non-code inputs and scientific fields',()=>{
 const before=[hash(original),hash(originalCode),hash(successor),hash(successorCode)];
 assert.equal(original.application_inputs.length,190);assert.equal(expected.science.application_inputs.length,156);
 assert.deepEqual(scientificArtifactIdentity(successor,successorCode),expected);
 assert.deepEqual([hash(original),hash(originalCode),hash(successor),hash(successorCode)],before);
 assert.equal(expected.science.application_inputs.filter(p=>p.path.endsWith('.mjs')).length,4,'Retained serialization code is scientific custody, not current execution');
});

test('every scientific certificate field and input remains in the comparison',()=>{
 for(const key of Object.keys(expected.science)){
  const c=structuredClone(successor);c[key]=null;
  if(key==='application_inputs')assert.throws(()=>scientificArtifactIdentity(c,successorCode));
  else assert.notDeepEqual(scientificArtifactIdentity(c,successorCode),expected,key);
 }
 const c=structuredClone(successor);c.unknown_future_operand=true;assert.throws(()=>scientificArtifactIdentity(c,successorCode),/schema/);
 for(const index of [0,20,100]){
  const c=structuredClone(successor);const row=expected.science.application_inputs[index];c.application_inputs.find(p=>p.path===row.path).sha256='0'.repeat(64);
  assert.notDeepEqual(scientificArtifactIdentity(c,successorCode),expected);
 }
});

test('critical roles cannot be moved, removed, duplicated or absorb scientific inputs',()=>{
 for(const edit of [code=>code.critical_files.pop(),code=>code.critical_files.push(code.critical_files[0]),code=>code.critical_files[0].path+='-moved',code=>code.entry_roles[Object.keys(code.entry_roles)[0]].actual_current_execution_wrappers.pop()]){
  const code=structuredClone(successorCode);edit(code);
  try{assert.notDeepEqual(scientificArtifactIdentity(successor,code),expected);}catch(error){if(error.code==='ERR_ASSERTION')throw error;}
 }
 const c=structuredClone(successor),code=structuredClone(successorCode),row=c.application_inputs.find(p=>p.path===expected.science.application_inputs[0].path);
 code.critical_files.push(structuredClone(row));assert.notDeepEqual(scientificArtifactIdentity(c,code),expected);
 const c2=structuredClone(successor);c2.application_inputs.find(p=>p.path===successorCode.critical_files[0].path).sha256='0'.repeat(64);
 assert.throws(()=>scientificArtifactIdentity(c2,successorCode),/code inventory pin/);
});

test('scientific selector has an exact complete roster and keeps all factual fields',()=>{
 for(const key of ['version','method','manifest_path','sha256','release_id','selected_geography']){
  const changed=structuredClone(base);changed[key]=key==='selected_geography'?{...base[key],sha256:'0'.repeat(64)}:key==='version'?2:base[key]+'x';
  try{assert.notDeepEqual(scientificNativeBase(changed),scientificNativeBase(base),key);}catch(error){if(error.code==='ERR_ASSERTION')throw error;}
 }
 for(const edit of [s=>s.future_scientific_operand=1,s=>delete s.sha256,s=>s.additive_release={}]){const s=structuredClone(base);edit(s);assert.throws(()=>scientificNativeBase(s));}
});

test('neither a truthy authority object nor a cloned snapshot grants private current authority',()=>{
 for(const authority of [undefined,null,{},structuredClone({certificate:successor,code_inventory:successorCode})]){
  const snapshot={selection:structuredClone(base),manifest:{},reader:{version:'1'.repeat(40)},artifactConsumption:authority};
  assert.throws(()=>requireCurrentArtifactBase(snapshot,base),/privately authenticated/);
  assert.throws(()=>requireScientificArtifactSuccession(snapshot,base,'1'.repeat(40)),/privately authenticated/);
 }
});


test('genuine successor review authenticates complete current authority and rejects invalid bindings',()=>{
 const repo=fs.mkdtempSync(path.join(os.tmpdir(),'artifact-succession-'));
 const git=(...args)=>execFileSync('git',['-C',repo,...args],{stdio:['ignore','pipe','pipe']}).toString().trim();
 const copy=p=>{const target=path.join(repo,p);fs.mkdirSync(path.dirname(target),{recursive:true});fs.copyFileSync(p,target);};
 try{
  git('init');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid');
  const certificatePath=root+'consumption-certificate-canonical-hash-1963.json',reviewPath=root+'independent-canonical-hash-1963-review.json';
  const pin=p=>{const raw=fs.readFileSync(p);return {path:p,mode:'100644',bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex')};};
  const selected={...structuredClone(base),artifact_consumption:{certificate:pin(certificatePath),review:pin(reviewPath)}};
  const paths=[certificatePath,reviewPath,successor.application_consumer_code.path,successor.qualification_inventory.path,successor.release_product_catalogue.path,successor.selected_artifact_bindings.registry.path,successor.selected_artifact_bindings.native_manifest.path];
  paths.forEach(copy);git('add','.');git('commit','-m','Genuine retained metadata fixture');const head=git('rev-parse','HEAD');
  const manifest=JSON.parse(fs.readFileSync(selected.manifest_path));
  const consume=s=>readArtifactConsumption(new ImmutableReader(repo,head),s,manifest);
  const accepted=consume(selected);assert.equal(accepted.review_id,6185604321);assert.deepEqual(scientificArtifactIdentity(accepted.certificate,accepted.code_inventory),expected);
  for(const edit of [s=>s.artifact_consumption.review.sha256='0'.repeat(64),s=>s.artifact_consumption.review.sha256='79024f6fd9335b0ad9da0ed936f5eabc600188f6176d9f953ceb006946626dbd',s=>s.artifact_consumption.certificate.sha256='0'.repeat(64),s=>s.artifact_consumption.certificate.mode='100755',s=>s.artifact_consumption.certificate.bytes++,s=>s.artifact_consumption.approved=true,s=>s.release_id+='-changed',s=>s.selected_geography.sha256='0'.repeat(64)]){
   const s=structuredClone(selected);edit(s);assert.throws(()=>consume(s));
  }
  const missing=structuredClone(selected);delete missing.artifact_consumption;assert.equal(consume(missing),null);
  assert.throws(()=>requireCurrentArtifactBase({selection:missing,artifactConsumption:accepted},base),/privately authenticated/);
 }finally{fs.rmSync(repo,{recursive:true,force:true});}
});
