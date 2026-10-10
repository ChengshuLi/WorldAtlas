import {fixturePreUse,fixtureCommand,fixtureIssuedPlan,executionFixture} from './execution-custody-fixture.mjs';
import assert from 'node:assert/strict';import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {CURRENT_REBIND_CODE,currentRebindResult,verifyCurrentRebindProducts} from './current-rebind.mjs';
import {valueSha,valueBytes,normaliseRetainedRepairLedger} from '../../selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const Q='coordination/engineering/additive-native-gap-batch-20261008/composition-v2/';
const registry=JSON.parse(fs.readFileSync(Q+'original-registry.json')),ledger=JSON.parse(fs.readFileSync(Q+'composed-original-ledger.json'));
const rows=[...normaliseRetainedRepairLedger(ledger,registry).rows.values()];
const roots=['coordination/engineering/additive-native-gap-repair-20261008/add031-release-proposal-v3-run1/', 'coordination/engineering/additive-native-gap-batch-20261008/batch-proposal-v1-run1/'];
const patches=roots.map((r,i)=>JSON.parse(fs.readFileSync(r+(i?'patch-batch.json':'patch-add031.json'))));
const windows=roots.flatMap(r=>JSON.parse(fs.readFileSync(r+'owner-window.json'))),map=new Map(windows.map(row=>[row.y,row.complete_owner_intervals]));
const wanted=[...new Set(patches.flatMap(p=>p.rows.map(row=>row.y)))].sort((a,b)=>a-b),currentRows=wanted.map(y=>({y,runs:map.get(y)}));
const targets=[...new Map(rows.map(row=>[row.target_id,{target_id:row.target_id,pixelIndex:row.pixelIndex,geometry:row.base_geometry,geometry_sha256:row.base_geometry_sha256}])).values()].sort((a,b)=>a.target_id.localeCompare(b.target_id));
const baseSelection={manifest_path:'fixture/manifest.json',sha256:'1'.repeat(64),release_id:'geography:fixture',release_manifest_sha256:'2'.repeat(64),canonical_grid_sha256:'3'.repeat(64)};
const expectedCode=CURRENT_REBIND_CODE.map(path=>{const body=fs.readFileSync(path);return {path,bytes:body.length,sha256:createHash('sha256').update(body).digest('hex')};});
const acquisition={version:1,kind:'complete-selected-rebind-inputs-v1',target_sources:targets.map(t=>({target_id:t.target_id,path:'fixture/source.json'})),source_inputs:[{path:'fixture/source.json',whole_body_sha256:'4'.repeat(64),bytes:1024}],predecessor_proof:null,predecessor_rows:[],native_inputs:[{logical_path:'fixture/runs.bin.gz',asset:{sha256:'5'.repeat(64)},custody:{kind:'ordinary-native-body',pin:{path:'fixture/runs.bin.gz',bytes:1024,mode:'100644',git_blob_oid:'2'.repeat(40),sha256:'5'.repeat(64)}}}],manifest_sha256:'6'.repeat(64)};
const acquisitionPhases=[{kind:'complete-current-native-window-group',rows:wanted,parts:['runs.bin.gz'],complete_phase_bytes:131072000,descriptors:20}];
const request={version:1,kind:'issued-native-additive-current-bank-rebind-v1',execution_commit:'1'.repeat(40),executed_code:expectedCode,
 base_selection:baseSelection,authority_registry_sha256:valueSha(registry),original_rows:rows,original_patch_sha256s:patches.map(valueSha),current_targets:targets,current_rows:currentRows,acquisition,execution:{command:fixtureCommand,pre_use:fixturePreUse(expectedCode)},size:262166,
 limits:{complete_phase_bytes:268435456,descriptors:512,output_bytes:33554432,rss_bytes:536870912,sampled_stop_bytes:402653184,wall_seconds:1200}};
const planBytes=valueBytes(fixtureIssuedPlan(request));request.execution.pre_use.plan.bytes=planBytes.length;request.execution.pre_use.plan.sha256=createHash('sha256').update(planBytes).digest('hex');
const result=currentRebindResult({baseSelection,registry,originalRows:rows,originalPatches:patches,currentTargets:targets,currentRows,size:262166});
const pin=(name,body)=>({commit:'1'.repeat(40),path:'fixture/'+name+'.json',mode:'100644',git_blob_oid:'2'.repeat(40),bytes:(Buffer.isBuffer(body)?body:valueBytes(body)).length,sha256:createHash('sha256').update(Buffer.isBuffer(body)?body:valueBytes(body)).digest('hex')});
const bodyPins={request:pin('request',request),result:pin('result',result)};
const facts={version:1,kind:'native-additive-current-bank-rebind-facts-v1',execution_commit:request.execution_commit,request_sha256:bodyPins.request.sha256,result_sha256:bodyPins.result.sha256,complete_phase_bytes:131072000,descriptors:20,acquisition_sha256:valueSha(acquisition),acquisition_phases:acquisitionPhases};bodyPins.facts=pin('facts',facts);
const publication={version:1,kind:'native-additive-current-bank-rebind-publication-v1',execution_commit:request.execution_commit,request_sha256:bodyPins.request.sha256,outputs:{facts:{path:'facts.json',bytes:bodyPins.facts.bytes,sha256:bodyPins.facts.sha256},result:{path:'result.json',bytes:bodyPins.result.bytes,sha256:bodyPins.result.sha256}}};bodyPins.publication=pin('publication',publication);
const execution=executionFixture(request,{requestPin:bodyPins.request,publicationPin:bodyPins.publication,resultPin:bodyPins.result,pin});
const operating={execution_custody:execution.pins,version:1,kind:'native-additive-current-bank-rebind-operating-v1',execution_commit:request.execution_commit,request_sha256:bodyPins.request.sha256,publication_sha256:bodyPins.publication.sha256,exit_code:0,signal:null,owned_processes_remaining:[],lifetime_rss_bytes:100000000,elapsed_seconds:1};bodyPins.operating=pin('operating',operating);
const certificate={version:1,kind:'qualified-native-additive-current-bank-rebind-v1',execution_commit:request.execution_commit,base_selection:baseSelection,authority_registry_sha256:valueSha(registry),...bodyPins};
const all={certificate,request,facts,publication,operating,result,baseSelection,registry,originalRows:rows,originalPatches:patches,size:262166,expectedCode,bodyPins,executionCustody:execution.bodies,acquired:{base_selection:baseSelection,current_targets:structuredClone(targets),current_rows:structuredClone(currentRows),acquisition:structuredClone(acquisition),acquisition_phases:structuredClone(acquisitionPhases)}};
assert.deepEqual(verifyCurrentRebindProducts(all),result);assert.equal(result.native.assigned_cells,141);assert.equal(result.current_targets.length,7);
// Direct mathematical refusals reach the actual applicability branches, not
// only the whole product byte guard.
let semantic=0;const semanticReject=mutate=>{const operands=structuredClone({baseSelection,registry,originalRows:rows,originalPatches:patches,currentTargets:targets,currentRows,size:262166});mutate(operands);assert.throws(()=>currentRebindResult(operands));semantic++;};
semanticReject(c=>c.currentRows.pop());semanticReject(c=>c.currentTargets.reverse());semanticReject(c=>c.currentTargets.push({...c.currentTargets[0],target_id:'zz-foreign'}));
semanticReject(c=>c.currentTargets[0].geometry.coordinates[0][0][0]+=1);
semanticReject(c=>{const row=c.originalPatches[0].rows[0];c.currentRows.find(r=>r.y===row.y).runs.push([...row.runs[0]]);c.currentRows.find(r=>r.y===row.y).runs.sort((a,b)=>a[0]-b[0]);});
semanticReject(c=>c.originalRows.reverse());
let negatives=0;const reject=mutate=>{const c=structuredClone(all);for(const name of Object.keys(c.executionCustody))c.executionCustody[name]=Buffer.from(c.executionCustody[name]);mutate(c);assert.throws(()=>verifyCurrentRebindProducts(c));negatives++;};
reject(c=>c.result=undefined);reject(c=>c.result.original_rows.pop());reject(c=>c.result.native.effective_rows[0].runs.pop());
reject(c=>c.request.current_rows.pop());reject(c=>c.request.current_targets.reverse());
reject(c=>c.request.original_rows[0].geometry.coordinates[0][0][0]+=1);
reject(c=>c.certificate.base_selection={...c.certificate.base_selection,sha256:'f'.repeat(64)});reject(c=>c.certificate.authority_registry_sha256='f'.repeat(64));
reject(c=>c.request.executed_code[0].sha256='f'.repeat(64));reject(c=>c.publication.outputs.result.sha256='f'.repeat(64));
reject(c=>c.operating.exit_code=false);reject(c=>c.operating.owned_processes_remaining=[1]);reject(c=>c.operating.lifetime_rss_bytes=536870913);
reject(c=>c.operating.elapsed_seconds=1201);reject(c=>c.facts.complete_phase_bytes=268435457);reject(c=>c.facts.descriptors=513);
reject(c=>c.request.limits.descriptors=true);reject(c=>c.result.current_targets[0].geometry_sha256='f'.repeat(64));
// Coherent self-consistent request changes still cannot substitute actual operands.
const coherentReject=mutate=>{const c=structuredClone(all);for(const name of Object.keys(c.executionCustody))c.executionCustody[name]=Buffer.from(c.executionCustody[name]);mutate(c);c.bodyPins.request=pin('request',c.request);c.certificate.request=c.bodyPins.request;c.facts.request_sha256=c.bodyPins.request.sha256;c.facts.acquisition_sha256=c.request.acquisition===undefined?'0'.repeat(64):valueSha(c.request.acquisition);c.bodyPins.facts=pin('facts',c.facts);c.certificate.facts=c.bodyPins.facts;c.publication.request_sha256=c.bodyPins.request.sha256;c.publication.outputs.facts={path:'facts.json',bytes:c.bodyPins.facts.bytes,sha256:c.bodyPins.facts.sha256};c.bodyPins.publication=pin('publication',c.publication);c.certificate.publication=c.bodyPins.publication;c.operating.request_sha256=c.bodyPins.request.sha256;c.operating.publication_sha256=c.bodyPins.publication.sha256;c.bodyPins.operating=pin('operating',c.operating);c.certificate.operating=c.bodyPins.operating;assert.throws(()=>verifyCurrentRebindProducts(c));negatives++;};
coherentReject(c=>delete c.request.acquisition);coherentReject(c=>c.request.acquisition.native_inputs=[]);coherentReject(c=>c.request.acquisition.source_inputs[0].whole_body_sha256='f'.repeat(64));coherentReject(c=>c.request.current_rows.pop());reject(c=>delete c.acquired);
console.log(JSON.stringify({version:1,kind:'complete-original-rebind-product-boundary-controls',supported_components:rows.length,targets:targets.length,original_cells:result.native.assigned_cells,negative_controls:negatives,semantic_negative_controls:semantic,method_code:expectedCode,limits:['Complete original operands; certificate/selection/operating records are explicit fixtures, not authority or actual v9 qualification.','No source fitness, native kernel, activation or world computation executed.']}));
export {all};
