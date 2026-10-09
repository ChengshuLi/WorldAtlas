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
