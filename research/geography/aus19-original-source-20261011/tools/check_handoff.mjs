// Actual registered v2 and retained scientific-premise entry points only.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {retainedAdministrativeSourcePremises,registeredAdministrativeViews,registeredOriginalPhysicalProduct} from '../../../../scripts/additive-gap-repair.mjs';
const scope=JSON.parse(fs.readFileSync(new URL('../vintages/source-handoff-001/source-handoff.json',import.meta.url)));
const clone=()=>structuredClone(scope);
const targetFor=(s,i=0)=>{const c=s.candidate_source_native_bindings[i];return s.current_neighbor_binding.rows.find(r=>r.component_id===c.component_id).candidate_neighbors.find(r=>r.feature.id===c.retained_payload.target_stable_location_id).feature;};
function premise(s,i=0,target=targetFor(s,i)){const c=s.candidate_source_native_bindings[i],p=s.original_physical_comparison_bindings.find(r=>r.component_id===c.component_id);return retainedAdministrativeSourcePremises({record:p.physical_comparison.row,candidate:c.original_candidate_feature.geometry,sourceCase:c,sourceScope:s,target});}
const entry={format:'source-native-execution-cohort-v2',id:scope.execution_cohort_id,cohort_ids:scope.scopeIds,target_ids:[...new Set(scope.candidate_source_native_bindings.map(c=>c.retained_payload.target_stable_location_id))]};
let count=0;function test(name,fn){fn();count++;console.log('ok '+count+' - '+name);}
for(let i=0;i<scope.scopeIds.length;i++)test('actual complete case '+i+' satisfies retained source-relative premises',()=>{const r=premise(scope,i);assert.equal(r.source_compatible,true,JSON.stringify(r));assert.deepEqual(r.failed_premises,[]);assert.equal(r.authority,'unapproved');});
test('required original target preimage cannot be omitted',()=>{const s=clone();s.original_target_canonical_bindings=s.original_target_canonical_bindings.filter(r=>r.target_id!=='gb:AUS:ADM2:25037944B47305351718046');assert.equal(premise(s,1).source_compatible,false);});
test('corrupt original target byte preimage refuses',()=>{const s=clone(),b=s.original_target_canonical_bindings.find(r=>r.target_id==='gb:AUS:ADM2:25037944B47305351718046');b.feature_bytes_base64=Buffer.from('{}\n').toString('base64');assert.equal(premise(s,1).source_compatible,false);});
test('exact v2 scientific and passive membership',()=>{assert.equal(registeredAdministrativeViews(scope,entry).cohort.length,scope.scopeIds.length);assert.equal(scope.original_gap_membership.members.length,scope.scopeIds.length);assert.equal(scope.original_membership_evidence.programme_components,95173);});
test('changed complete candidate refuses',()=>{const s=clone();s.candidate_source_native_bindings[0].original_candidate_feature.geometry.coordinates[0][1][0]+=0.01;assert.equal(premise(s).source_compatible,false);});
test('positive mapped water refuses',()=>{const s=clone(),r=s.original_physical_comparison_bindings[0].physical_comparison.row;r.complete_support.mapped_inland_water_support=structuredClone(r.complete_support.mapped_land_support);assert.equal(premise(s).source_compatible,false);});
test('wrong original native record hash refuses',()=>{const s=clone();s.original_physical_comparison_bindings[0].original_queried_source_metadata[0].original_source_record_metadata.record_sha256='0'.repeat(64);assert.equal(premise(s).source_compatible,false);});
test('missing full query refuses',()=>{const s=clone();s.original_physical_comparison_bindings[0].physical_comparison.row.query_relations=[];assert.equal(premise(s).source_compatible,false);});
test('coherently changed target parent fails original relation',()=>{const s=clone(),t=structuredClone(targetFor(s));t.properties.parent_id='framework:province:foreign';s.candidate_source_native_bindings[0].retained_payload.target_current_feature.parent_id=t.properties.parent_id;assert.equal(premise(s,0,t).source_compatible,false);});
test('wrong unique source subject refuses',()=>{const s=clone();s.candidate_source_native_bindings[0].retained_source_operation_row.source_comparison_record.uniquely_covering_compatible_recorded_subject.id='gb:AUS:ADM2:foreign';assert.equal(premise(s).source_compatible,false);});
test('missing admitted case refuses',()=>{const s=clone();s.candidate_source_native_bindings.pop();assert.throws(()=>registeredAdministrativeViews(s,entry));});
test('duplicate admitted case refuses',()=>{const s=clone();s.candidate_source_native_bindings[1]=structuredClone(s.candidate_source_native_bindings[0]);assert.throws(()=>registeredAdministrativeViews(s,entry));});
test('missing passive member refuses',()=>{const s=clone();s.original_gap_membership.members.pop();assert.throws(()=>registeredAdministrativeViews(s,entry));});
test('fabricated passive member refuses',()=>{const s=clone();s.original_gap_membership.members.push({...s.original_gap_membership.members[0],component_id:'physical-component:foreign'});assert.throws(()=>registeredAdministrativeViews(s,entry));});
// Expectations come independently from the immutable original report and actual
// complete product bytes, not from the projected registration under test.
const originalReport=JSON.parse(execFileSync('git',['show','6a99a7606b9c2d11ac8cd093610653d4cd5d1382:coordination/engineering/global-physical-comparison-20261006/results/report.json']));
const productByPath=new Map(originalReport.products.map(p=>[p.path,p]));
const names=['004','007','027','028','029','030','043','044','047','053','061','064','065'].map(n=>'components-'+n+'.jsonl.gz').concat('sources-000.jsonl.gz');
const physicalPlan=JSON.parse(fs.readFileSync(new URL('../physical-plan.json',import.meta.url)));
const sha=b=>createHash('sha256').update(b).digest('hex');
const lock=JSON.parse(fs.readFileSync(new URL('./source-entry-lock.json',import.meta.url)));
let logical=lock.node_executable.bytes+lock.project_files.reduce((n,p)=>n+p.bytes,0)+lock.installed_files.reduce((n,p)=>n+p.bytes,0)+fs.statSync(new URL('../vintages/source-handoff-001/source-handoff.json',import.meta.url)).size+1024*1024;
for(const name of names)test('actual registered original product '+name,()=>{
 const product=productByPath.get(name),part=name.split('-')[1].split('.')[0];
 const reuse=physicalPlan.reused_products[name];
 const encoded=name.startsWith('sources-')?execFileSync('git',['show','6a99a7606b9c2d11ac8cd093610653d4cd5d1382:research/geography/ukraine-original-singleton-source-fit-20261010/vintages/physical-restoration-001/'+name],{maxBuffer:4*1024*1024}):reuse?execFileSync('git',['show',reuse.commit+':'+reuse.path],{maxBuffer:4*1024*1024}):fs.readFileSync(new URL('../vintages/physical-custody-'+part+'-002/'+name,import.meta.url));
 const decoded=gunzipSync(encoded,{maxOutputLength:product.uncompressed_bytes+1});logical+=encoded.length+decoded.length;assert(logical<256*1024*1024);
 assert.equal(encoded.length,product.bytes);assert.equal(sha(encoded),product.sha256);assert.equal(decoded.length,product.uncompressed_bytes);assert.equal(sha(decoded),product.uncompressed_sha256);
 const rows=decoded.toString().trimEnd().split('\n').length;
 assert.equal(registeredOriginalPhysicalProduct(scope,product,rows),true);assert.equal(registeredOriginalPhysicalProduct(scope,product,rows+1),false);
});
const first=productByPath.get(names[0]),registeredRows=scope.physical_restoration.restorations.find(p=>p.path===first.path).rows;
for(const key of ['bytes','sha256','uncompressed_bytes','uncompressed_sha256'])test('altered original product '+key+' refuses',()=>{const product=structuredClone(first);product[key]=typeof product[key]==='number'?product[key]+1:'0'.repeat(64);assert.equal(registeredOriginalPhysicalProduct(scope,product,registeredRows),false);});
test('altered declared complete row count refuses',()=>{const s=clone();s.physical_restoration.restorations[0].rows++;assert.equal(registeredOriginalPhysicalProduct(s,first,registeredRows),false);});
test('duplicate whole product registration refuses',()=>{const s=clone();s.physical_restoration.restorations.push(structuredClone(s.physical_restoration.restorations[0]));assert.equal(registeredOriginalPhysicalProduct(s,first,registeredRows),false);});
test('missing whole product registration refuses',()=>{const s=clone();s.physical_restoration.restorations=s.physical_restoration.restorations.filter(p=>p.path!==first.path);assert.equal(registeredOriginalPhysicalProduct(s,first,registeredRows),false);});
test('historical receipt-list shape refuses',()=>{const s=clone();s.physical_restoration=s.physical_restoration_receipts;assert.equal(registeredOriginalPhysicalProduct(s,first,registeredRows),false);});
assert(process.resourceUsage().maxRSS*1024<512*1024**2);
console.log('1..'+count);
console.log(JSON.stringify({original_product_logical_bytes:logical,peak_rss_bytes:process.resourceUsage().maxRSS*1024}));
