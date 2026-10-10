import fs from 'node:fs';
import assert from 'node:assert/strict';
import {retainedAdministrative318CaseView,retainedAdministrativeSourcePremises} from './literal-boundary-controls-module.mjs';
const read=name=>JSON.parse(fs.readFileSync(new URL(name,import.meta.url)));
const fit=read('administrative-source-rule-fit.json'),physicalCase=read('BRN-original-physical-case.json'),querySources=read('BRN-original-query-metadata.json'),targetBindings=read('BRN-target-canonical-bindings.json'),target=read('BRN-complete-current-target.json');
const componentId=physicalCase.case.component_id;
const input={fit,physicalCase,querySources,targetBindings,componentId};
function check(i,t=target){const v=retainedAdministrative318CaseView(i);const result=retainedAdministrativeSourcePremises({record:v.record,candidate:v.sourceCase.original_candidate_feature.geometry,sourceCase:v.sourceCase,sourceScope:v.sourceScope,target:t});assert.equal(result.source_compatible,true,JSON.stringify(result.failed_premises));return v;}
const results=[];function pass(name,fn){fn();results.push({name,result:'PASS'});}function refuse(name,mutate){const i=structuredClone(input),t=structuredClone(target);mutate(i,t);assert.throws(()=>check(i,t));results.push({name,result:'REFUSE'});}
pass('Actual BRN complete original source/physical/query/current-target',()=>check(input));
pass('Original disjoint query0 remains disjoint; query9 alone covers',()=>{const v=check(input);assert.equal(v.record.query_relations[0].disjoint,true);assert.equal(v.record.query_relations[0].intersects,false);assert.equal(v.record.query_relations[1].source_covers_candidate,true);});
refuse('Foreign accepted batch',i=>i.fit.batch_id='foreign');
refuse('Missing original query',i=>i.querySources.pop());
refuse('Missing original query pointset descriptor',i=>i.fit.cases.find(r=>r.component_id===componentId).original_physical_query_custody.complete_query_source_pointsets.pop());
refuse('Query metadata hash drift',i=>i.querySources[0].native_record_sha256='0'.repeat(64));
refuse('Original physical inverse drift',i=>i.physicalCase.case.physical_query_relations[0].intersects=true);
refuse('Whole candidate geometry drift',i=>i.fit.cases.find(r=>r.component_id===componentId).current_component_candidate.feature.geometry.coordinates[0][0][0]+=0.01);
refuse('Missing full-source fit',i=>i.fit.cases.find(r=>r.component_id===componentId).source_rule_fit_state='held');
refuse('Whole completion cannot be minted',i=>i.fit.cases.find(r=>r.component_id===componentId).whole_gap_completion=true);
refuse('Original target preimage SHA drift',(i,t)=>{i.targetBindings[0].feature_bytes_base64=Buffer.from('{}').toString('base64');t.properties.name='foreign';});
refuse('Current target parent drift',(i,t)=>t.properties.parent_id='foreign');
refuse('Nonzero contradictory residual',i=>{const r=i.fit.cases.find(r=>r.component_id===componentId);r.original_administrative_comparison.record.component_minus_source_union.planar_area_coordinate_units_squared=1e-12;i.physicalCase.case.existing_full_admin_comparison.record.component_minus_source_union.planar_area_coordinate_units_squared=1e-12;});
console.log(JSON.stringify({scope:'Extracted literal schema/premise boundary only; no producer, source/GIS/native operator or current-reader issuance',positives:results.filter(x=>x.result==='PASS').length,refusals:results.filter(x=>x.result==='REFUSE').length,results},null,2));
