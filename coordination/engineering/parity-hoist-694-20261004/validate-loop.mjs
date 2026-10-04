import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {decodeDerived} from '../../../src/derived-records.js';
import {resolveAttributes} from '../../../src/attributes.js';
import {resolveTemporal} from '../../../src/temporal.js';
import {runtimeOwnershipBucket,runtimeOwnershipData} from '../../../src/runtime-ownership.js';

const base='15cb52b8e6fd26164e306bde1128e66317a0149e';
const file='test/prepared-parity.test.mjs';
const original=execFileSync('git',['show',`${base}:${file}`],{encoding:'utf8'});
const current=fs.readFileSync(file,'utf8');
const helper=original.slice(original.indexOf('function canonical('),original.indexOf('function prepared('))+
 original.slice(original.indexOf('function expectedReferences('),original.indexOf('function ownershipSnapshots('))+
 original.slice(original.indexOf('function selectedStates('),original.indexOf("test('ownership codecs"));
const loop=source=>source.slice(source.indexOf('  for(const year of years)',source.indexOf("test('static and server")),source.indexOf(' }finally{db.close();}',source.indexOf("test('static and server")));
function run(source,{badExamples=null,badOwnership=false}={}){
 const years=[-3000,-1,1,1000,1444,1901,1931,1961,1991,2020,2024,2025,2026];
 const shared={version:2,source:'Fixture source',source_url:'https://example.org',owner_ids:['owner:fixture'],statuses_order:['derived'],labels:['Fixture owner'],source_ids:['fixture:source'],entities:{'owner:fixture':{name:'Fixture owner'}}};
 const bucket={version:1,source_index_sha256:'fixture-pin',valid_from:-3000,valid_to:2027,parts:[[['location:fixture',[[-3000,2027,0,0,0]]]]],evidence:[[0,1,1,[[0,1]],[0],0]]};
 const runtime={version:1,encoding:'ownership-v2-century',source_index_sha256:'fixture-pin',shared,buckets:[{path:'fixture.json',valid_from:-3000,valid_to:2027}]};
 const references={index:{version:2,types:[{attribute:'population',method:'estimate',status:'estimate',valid_from:-3000,valid_to:2027,source:'Fixture reference',metadata:{precision:'exact'}}],values:[42]},parts:[[['location:fixture',[[0,0,1,1]]]]]};
 const reference={features:[{id:'location:fixture',properties:{name:'Fixture location',metadata:{}}}],units:[],temporal:{entities:[],history:[],links:[]}};
 const history={states:[{location_id:'location:fixture',valid_from:-3000,valid_to:2027,is_example:1,population:7,source:'Example fixture'}],attributes:[]};
 const inputs={bucket,runtime,references,reference,history};
 const before=JSON.stringify(inputs),calls={decodeDerived:0,expectedReferences:0,fingerprint:0,snapshot:0,resolveTemporal:0,resolveAttributes:0},assertions=[],modes=[];
 const context={createHash,path,years,runtime,references,reference,serverReference:reference,history,buckets:new Map(),staticRoot:'fixture',db:{},owners:new Map(),read:()=>bucket};
 context.assert={equal:(a,b,message)=>{assert.equal(a,b,message);assertions.push(['equal',message??null]);},deepEqual:(a,b,message)=>{assert.deepEqual(a,b,message);assertions.push(['deepEqual',message??null]);}};
 vm.createContext(context);vm.runInContext(helper,context);
 const independent=context.expectedReferences,rawFingerprint=context.fingerprint;
 context.expectedReferences=(...args)=>{calls.expectedReferences++;return independent(...args);};
 context.fingerprint=(...args)=>{calls.fingerprint++;return rawFingerprint(...args);};
 context.runtimeOwnershipBucket=runtimeOwnershipBucket;context.runtimeOwnershipData=runtimeOwnershipData;
 context.decodeDerived=(...args)=>{calls.decodeDerived++;const rows=decodeDerived(...args);if(badOwnership)rows[0].value='Corrupt static owner';return rows;};
 context.resolveTemporal=(...args)=>{calls.resolveTemporal++;return resolveTemporal(...args);};
 context.resolveAttributes=(...args)=>{calls.resolveAttributes++;return resolveAttributes(...args);};
 for(const year of years)context.owners.set(year,context.expectedOwners({index:{...shared,evidence:bucket.evidence},parts:bucket.parts},year));
 context.snapshot=(_,year,examples)=>{calls.snapshot++;modes.push([year,examples]);const states=history.states.filter(row=>!row.is_example||examples),attributes=[...decodeDerived(bucket.parts,{...shared,evidence:bucket.evidence},year),...independent(references,year)];if(badExamples===examples)attributes[0]={...attributes[0],value:'Corrupt server owner'};return {states,attributes,polities:vm.runInContext('[]',context)};};
 vm.runInContext(loop(source),context);
 assert.equal(JSON.stringify(inputs),before,'Resolver and preparation inputs are unchanged');
 return {calls,assertions,modes};
}
const before=run(original),after=run(current);
assert.deepEqual(after.assertions,before.assertions,'Every original assertion still executes in the same order');
assert.deepEqual(after.modes,before.modes,'Every original year/examples snapshot remains');
for(const key of ['snapshot','resolveTemporal','resolveAttributes'])assert.equal(after.calls[key],before.calls[key]);
assert.equal(before.calls.decodeDerived,26);assert.equal(after.calls.decodeDerived,13);
assert.equal(before.calls.expectedReferences,26);assert.equal(after.calls.expectedReferences,13);
assert.equal(before.calls.fingerprint,104);assert.equal(after.calls.fingerprint,78);
for(const source of [original,current]){
 for(const badExamples of [false,true])assert.throws(()=>run(source,{badExamples}),/all resolved fields\/provenance/);
 assert.throws(()=>run(source,{badOwnership:true}),/Actual static temporal transport/);
}
console.log(JSON.stringify({base,source_file:file,source_sha256:createHash('sha256').update(current).digest('hex'),fixture_only:true,baseline:before.calls,updated:after.calls,assertions_preserved:after.assertions.length,modes_preserved:after.modes.length,inputs_unchanged:true,negative_controls:['server corruption rejected with examples false','server corruption rejected with examples true','static ownership corruption rejected'],limits:['Synthetic one-location fixture executing extracted actual source loops; not the prepared full atlas and not a performance benchmark']},null,2));
