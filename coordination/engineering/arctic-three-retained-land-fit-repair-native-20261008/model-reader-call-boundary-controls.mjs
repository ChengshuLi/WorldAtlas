// Exact production-call extraction with real complete selector/stage metadata.
// Delegated whole restoration/consumption is not executed by this tiny control.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
const root=process.cwd(),N2='coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008';
const raw=fs.readFileSync(new URL('./prepare-model-reader-checkout.mjs',import.meta.url));
const source=raw.toString(),start=source.indexOf('export async function prepareModelReaderCheckout');
assert(start>=0);
const git=process.platform==='darwin'?'/Library/Developer/CommandLineTools/usr/bin/git':'/usr/bin/git';
function original(relative){return JSON.parse(fs.existsSync(relative)?fs.readFileSync(relative):execFileSync(git,['show','HEAD:'+relative]));}
const selection=original('data/ownership-selection.json'),stage=original(N2+'/context-stage-v9.json');
const AsyncFunction=Object.getPrototypeOf(async function(){}).constructor;
async function invoke({profile='full',shard=2,changeSelection,changeStage,failPreflight=false}={}){
 const selected=structuredClone(selection),sidecar=structuredClone(stage),events=[];let reads=0;
 changeSelection?.(selected);changeStage?.(sidecar);
 const mockFs={realpathSync:value=>value,readFileSync:file=>{reads++;return Buffer.from(JSON.stringify(file.endsWith('ownership-selection.json')?selected:sidecar));},mkdirSync:()=>events.push('mkdir')};
 const preflight=options=>{events.push('preflight');assert.deepEqual(options,{source:root,stage:root,sidecar});if(failPreflight)throw Error('admission refused');return {actual_admission_fixture:true};};
 const issue=options=>{events.push('issue');assert.equal(options.root,root);assert.equal(options.admission.actual_admission_fixture,true);return {private_execution_fixture:true};};
 const restore=options=>{events.push('restore');assert.equal(options.root,root);assert.equal(options.mode,'checkout');assert.equal(options.temporaryRoot,path.join(root,'.cache'));return {original_custody_fixture:true};};
 const consume=async options=>{events.push('consume');assert.equal(options.restoredReceipt.original_custody_fixture,true);assert.equal(options.currentExecution.private_execution_fixture,true);return {receipt:{current_execution:{fixture:true}}};};
 const install=async options=>{events.push('install');assert.equal(options.context.receipt.current_execution.fixture,true);return {fixture:true};};
 const factory=new AsyncFunction('assert','fs','path','N2','preflightArtifactPackage','issueCheckoutExecution','restoreCanonicalProducts','consumeQualifiedArcticArtifacts','installV9Stage',source.slice(start).replace('export async function','async function')+'\nreturn prepareModelReaderCheckout;');
 const fn=await factory(assert,mockFs,path,N2,preflight,issue,restore,consume,install);
 try{return {result:await fn({root,profile,shard}),events,reads};}catch(error){error.events=events;error.reads=reads;throw error;}
}
const positive=await invoke();
assert.deepEqual(positive.events,['preflight','issue','mkdir','restore','consume','install']);assert.equal(positive.result.applicable,true);
let rejected=0;
for(const options of [{profile:'evidence'},{shard:0},{changeStage:s=>s.version=3},{changeSelection:s=>s.artifact_consumption.certificate.sha256='0'.repeat(64)},{failPreflight:true}]){
 await assert.rejects(()=>invoke(options),error=>{assert(!error.events.includes('restore'));return true;});rejected++;
}
console.log(JSON.stringify({positive:1,rejected,actual_production_source_sha256:createHash('sha256').update(raw).digest('hex'),metadata:{selection,stage},order:positive.events,
 limitation:'Exact production function, real complete metadata and stubbed delegated boundaries; no restoration, consumption, installer or full normal checkout qualification.'},null,2));

// Complete selected root-space inputs and actual executing source closure must
// be included in the real sparse package definition before a hosted dispatch.
const {validatePackageInputs,containsPackagePath}=await import('../../../scripts/package-inputs.mjs');
const {completeReleaseProductInputs}=await import('./release-product-inputs.mjs');
const {gunzipSync}=await import('node:zlib');
const certificate=original(N2+'/qualified-artifacts/consumption-certificate.json');
const codeInventory=original(N2+'/qualified-artifacts/application-consumer-code.json');
const cataloguePin=certificate.release_product_catalogue;
const catalogueRaw=fs.readFileSync(cataloguePin.path);
assert.equal(catalogueRaw.length,cataloguePin.bytes);
assert.equal(createHash('sha256').update(catalogueRaw).digest('hex'),cataloguePin.sha256);
const catalogueDecoded=gunzipSync(catalogueRaw);
assert.equal(catalogueDecoded.length,cataloguePin.decoded_bytes);
assert.equal(createHash('sha256').update(catalogueDecoded).digest('hex'),cataloguePin.decoded_sha256);
const expanded=completeReleaseProductInputs(certificate,JSON.parse(catalogueDecoded));
assert.equal(expanded.length,533);
const required=new Set([stage.artifact_consumption.certificate.path,stage.artifact_consumption.review.path]);
for(const pin of expanded)if((pin.space??'root')==='root')required.add(pin.path);
for(const pin of codeInventory.critical_files)required.add(pin.path);
for(const entry of ['scripts/build-static-inner.mjs','scripts/build-hosted-inner.mjs']){
 for(const pin of codeInventory.entry_critical_files[entry])required.add(pin.path);
 for(const relative of codeInventory.entry_roles[entry].actual_current_execution_wrappers)required.add(relative);
}
function requirePackageCoverage(value){
 const definition=validatePackageInputs(value);
 for(const relative of required)assert(containsPackagePath(definition.inputs,relative),'Missing selected package input: '+relative);
 return definition;
}
const definition=original('.github/package-inputs.json');
requirePackageCoverage(definition);
let missingPathRefusals=0;
for(const relative of [
 N2+'/selected-geography/part-29-application.json.gz',
 N2+'/application-geometry-serialization.mjs',N2+'/application-geometry-producer.mjs',
 N2+'/phase-admission.mjs',N2+'/artifact-checkout-execution.mjs',N2+'/prepare-model-reader-checkout.mjs'
]){
 const omitted=structuredClone(definition);
 omitted.inputs=omitted.inputs.filter(input=>input!==relative);
 assert.throws(()=>requirePackageCoverage(omitted),/Missing selected package input:/);
 missingPathRefusals++;
}
console.log(JSON.stringify({package_coverage_positive:1,missing_path_refusals:missingPathRefusals,
 expanded_roles:expanded.length,required_root_and_executing_paths:required.size,
 input_definition_sha256:createHash('sha256').update(fs.readFileSync('.github/package-inputs.json')).digest('hex'),
 limitation:'Real selected certificate/catalogue and code metadata joined to real sparse config; no package materialization, artifact consumption or scientific replay.'},null,2));

// Execute the exact selected-runner call against the real setup observer.
const {observeSetupPhase}=await import('../../../scripts/ci-setup-observations.mjs');
const runner=fs.readFileSync('scripts/run-integration-tests.mjs','utf8');
const begin=runner.indexOf('const selectedCheckout=await observeSetupPhase(');
const finish=runner.indexOf('console.log(JSON.stringify({selected_model_reader_checkout:selectedCheckout}));',begin);
assert(begin>=0&&finish>begin);
const invocation=runner.slice(begin,finish);
const delegatedImport="const {prepareModelReaderCheckout}=await import('../coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/prepare-model-reader-checkout.mjs');";
assert(invocation.includes(delegatedImport));
const actualCall=new AsyncFunction('observeSetupPhase','prepareModelReaderCheckout','profile','shard',invocation.replace(delegatedImport,'')+'\nreturn selectedCheckout;');
const observations=[];let delegated=0;
const observed=(name,work)=>observeSetupPhase(name,work,{emit:value=>observations.push(value)});
const selected=await actualCall(observed,async options=>{delegated++;assert.deepEqual(options,{root:process.cwd(),profile:'full',shard:2});return {distinct_selected_checkout_fixture:true};},'full',2);
assert.equal(selected.distinct_selected_checkout_fixture,true);assert.equal(delegated,1);
assert.deepEqual(observations.map(value=>[value.setup_phase,value.status]),[['canonical-checkout','started'],['canonical-checkout','success']]);
let forbiddenDelegated=0;
await assert.rejects(()=>observeSetupPhase('selected-model-reader-checkout',async()=>{forbiddenDelegated++;}),/assert|expression/i);
assert.equal(forbiddenDelegated,0);
console.log(JSON.stringify({actual_runner_observer_positive:1,unsupported_label_refused_before_work:1,
 runner_sha256:createHash('sha256').update(runner).digest('hex'),
 limitation:'Exact runner invocation and actual observer with delegated checkout stub; no restore, consumption or full regression run.'},null,2));
