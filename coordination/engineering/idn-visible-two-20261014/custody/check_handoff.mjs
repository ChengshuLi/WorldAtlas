// Genuine v2 view/source-predicate functions; no issued SOURCE result or GIS.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {retainedAdministrativeSourcePremises, registeredAdministrativeViews, originalAdministrativeTargetHash} from '../../../../scripts/additive-gap-repair.mjs';
const scope=JSON.parse(fs.readFileSync(new URL('../vintages/source-handoff-002/source-handoff.json',import.meta.url)));
const clone=()=>structuredClone(scope);
const targetFor=(s,i)=>s.current_neighbor_binding.rows.find(r=>r.component_id===s.scopeIds[i]).candidate_neighbors.find(n=>n.feature.id===s.candidate_source_native_bindings[i].retained_payload.target_stable_location_id).feature;
function premise(s,i=0,target=targetFor(s,i)){
 const sourceCase=s.candidate_source_native_bindings[i],record=s.original_physical_comparison_bindings[i].physical_comparison.row;
 return retainedAdministrativeSourcePremises({record,candidate:sourceCase.original_candidate_feature.geometry,sourceCase,sourceScope:s,target});
}
const entry={format:'source-native-execution-cohort-v2',id:scope.execution_cohort_id,cohort_ids:scope.scopeIds,target_ids:scope.candidate_source_native_bindings.map(c=>c.retained_payload.target_stable_location_id)};
let count=0;
function test(name,fn){fn();count++;console.log('ok '+count+' - '+name);}
for(let i=0;i<2;i++)test('actual complete IDN case '+i+' retains source-relative support and unapproved truth',()=>{
 const r=premise(scope,i);assert.equal(r.source_compatible,true,JSON.stringify(r));assert.deepEqual(r.failed_premises,[]);assert.equal(r.authority,'unapproved');assert.equal(r.status,'unknown-source-fitness-and-observation-date');
});
test('actual v2 has two executable cases with passive original318 accounting',()=>{assert.equal(registeredAdministrativeViews(scope,entry).cohort.length,2);assert.equal(scope.original_gap_membership.members.length,2);assert.equal(scope.original_membership_evidence.original_batch_size,318);assert.equal(scope.accepted_ledger_bindings.length,2);});
test('actual target hashes need no cross-language aliases',()=>assert.deepEqual(scope.original_target_canonical_bindings,[]));
for(const binding of scope.original_target_canonical_bindings){
 const i=scope.candidate_source_native_bindings.findIndex(c=>c.retained_payload.target_stable_location_id===binding.target_id),target=targetFor(scope,i);
 test('alias '+binding.target_id+' succeeds only with authentic complete Python preimage',()=>{assert.equal(originalAdministrativeTargetHash({sourceScope:scope,target,kind:'feature',expected:binding.feature_sha256}),true);assert.equal(originalAdministrativeTargetHash({sourceScope:{},target,kind:'feature',expected:binding.feature_sha256}),false);});
 test('tampered alias '+binding.target_id+' is refused',()=>{const s=clone();s.original_target_canonical_bindings.find(r=>r.target_id===binding.target_id).feature_bytes_base64=Buffer.from('{}\n').toString('base64');assert.equal(premise(s,i).source_compatible,false);});
}
test('changed complete candidate is refused',()=>{const s=clone();s.candidate_source_native_bindings[0].original_candidate_feature.geometry.coordinates[0][1][0]+=0.01;assert.equal(premise(s).source_compatible,false);});
test('positive mapped-water support is refused',()=>{const s=clone();const r=s.original_physical_comparison_bindings[0].physical_comparison.row;r.complete_support.mapped_inland_water_support=structuredClone(r.complete_support.mapped_land_support);assert.equal(premise(s).source_compatible,false);});
test('wrong complete native metadata is refused',()=>{const s=clone();s.original_physical_comparison_bindings[0].original_queried_source_metadata[0].original_source_record_metadata.record_sha256='0'.repeat(64);assert.equal(premise(s).source_compatible,false);});
test('missing original query is refused',()=>{const s=clone();s.original_physical_comparison_bindings[0].physical_comparison.row.query_relations=[];assert.equal(premise(s).source_compatible,false);});
test('changed target parent fails original source relation',()=>{const s=clone(),t=structuredClone(targetFor(s,0));t.properties.parent_id='framework:province:foreign';s.candidate_source_native_bindings[0].retained_payload.target_current_feature.parent_id=t.properties.parent_id;assert.equal(premise(s,0,t).source_compatible,false);});
test('nonempty original source remainder is refused',()=>{const s=clone();s.candidate_source_native_bindings[0].retained_source_operation_row.source_comparison_record.component_minus_source_union.is_empty=false;assert.equal(premise(s).source_compatible,false);});
test('wrong unique source subject is refused',()=>{const s=clone();s.candidate_source_native_bindings[0].retained_source_operation_row.source_comparison_record.uniquely_covering_compatible_recorded_subject.id='gb:IDN:ADM2:foreign';assert.equal(premise(s).source_compatible,false);});
test('missing executable case is refused',()=>{const s=clone();s.candidate_source_native_bindings.pop();assert.throws(()=>registeredAdministrativeViews(s,entry));});
test('duplicate executable case is refused',()=>{const s=clone();s.candidate_source_native_bindings[1]=structuredClone(s.candidate_source_native_bindings[0]);assert.throws(()=>registeredAdministrativeViews(s,entry));});
test('missing passive member is refused',()=>{const s=clone();s.original_gap_membership.members.pop();assert.throws(()=>registeredAdministrativeViews(s,entry));});
test('extra fabricated passive member is refused',()=>{const s=clone();s.original_gap_membership.members.push({...s.original_gap_membership.members[0],component_id:'physical-component:foreign'});assert.throws(()=>registeredAdministrativeViews(s,entry));});
test('complete reused source metadata has original native roster coverage',()=>{
 const base='a35ba193cfe5c84424a4952ca752593ebf9d7102';
 const sha=raw=>createHash('sha256').update(raw).digest('hex');
 function rows(path,encodedHash,decodedHash,encodedBytes,decodedBytes){
  const raw=execFileSync('git',['show',base+':'+path],{maxBuffer:3*1024**2});
  assert.equal(raw.length,encodedBytes);assert.equal(sha(raw),encodedHash);
  const body=gunzipSync(raw,{maxOutputLength:9*1024**2});
  assert.equal(body.length,decodedBytes);assert.equal(sha(body),decodedHash);
  const result=body.toString().trimEnd().split('\n').map(JSON.parse);
  assert.equal(new Set(result.map(r=>r.id)).size,result.length);return result;
 }
 const native=rows('coordination/engineering/gshhg-native-member-custody-20261007/results/records-000.jsonl.gz','888e0fbe4ff2c466a96e9bdf089cc9a796e807de5dd4782ad58e0c3ebdb4ab50','2270f64f3ed5b693df2466006902a58467f026d7260e55e8082058349facfe1b',1888476,8388394);
 const original=rows('research/geography/ukraine-original-singleton-source-fit-20261010/vintages/physical-restoration-001/sources-000.jsonl.gz','aaf5e4f099ab25c6e6f96632787f1654ba6054ed378fd591b360e36274ffc264','a75923307b24ff73fe3090307b2c8d6e590a22dbb91f4d43f92a52ac0fd23705',2173285,8388327);
 assert.equal(native.length,11801);assert.equal(original.length,10746);
 const byId=new Map(native.map(r=>[r.id,r]));
 for(const r of original){const n=byId.get(r.id);assert.ok(n);
  for(const [a,b] of [['id','id'],['native_offset','offset'],['native_record_bytes','record_bytes'],['ordinal','ordinal'],['n','n'],['header_native_values','header_int32'],['record_sha256','record_sha256'],['coordinate_bytes_sha256','coordinate_bytes_sha256']])assert.deepEqual(r[a],n[b]);
 }
 const originalIds=new Set(original.map(r=>r.id));
 for(const c of scope.original_physical_comparison_bindings)for(const r of c.original_queried_source_metadata)assert.ok(originalIds.has(r.original_source_record_metadata.id));
});
console.log('1..'+count);
