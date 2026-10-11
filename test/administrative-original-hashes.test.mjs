import fs from 'node:fs';
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {admitAdministrativeOriginalPreimages,originalAdministrativeCandidateHash,originalAdministrativeProductFeatures,originalAdministrativeProductMatch,retainedAdministrativeSourcePremises,retainedAdministrativeFragmentPremises} from '../scripts/additive-gap-repair.mjs';
import {canonicalValue,footprintValueSha256 as digest} from '../src/effective-footprint.js';
import {candidateBudget} from '../scripts/native-ownership/native-preparation-guards.mjs';
const sha=body=>createHash('sha256').update(body).digest('hex');
const canonical=value=>JSON.stringify(canonicalValue(value))+'\n';
const bytes=value=>Buffer.from(canonical(value).replaceAll('25,','25.0,').replaceAll('-8,','-8.0,'));
function fixture(){
 const geometry={type:'Polygon',coordinates:[[[25,-8],[26,-8],[25,-7],[25,-8]]]},feature={type:'Feature',id:'candidate',properties:{name:'original'},geometry};
 const featureBytes=bytes(feature),geometryBytes=bytes(geometry),source_path='original.geojson';
 const body=Buffer.from(JSON.stringify({type:'FeatureCollection',features:[feature]}));
 const binding={source_path,source_sha256:sha(body),feature_index:0,feature_sha256:sha(featureBytes),geometry_sha256:sha(geometryBytes),feature_bytes_base64:featureBytes.toString('base64'),geometry_bytes_base64:geometryBytes.toString('base64')};
 const candidateBinding={...binding,component_id:'candidate',derived_js_canonical_sha256:digest(feature),derived_js_geometry_canonical_sha256:digest(geometry)};
 return {geometry,feature,body,pin:{path:source_path},binding,scope:{original_administrative_canonical_bindings:[binding],original_candidate_canonical_bindings:[candidateBinding]}};
}
test('candidate geometry preserves the exact old numeric preimage in both full and fragment paths',()=>{
 const f=fixture(),record={component_id:'candidate',candidate_feature_sha256:f.binding.feature_sha256,candidate_geometry_sha256:f.binding.geometry_sha256,complete_support:{hierarchy_disagreements:{}}};
 const sourceCase={component_id:'candidate',original_candidate_feature:f.feature,retained_payload:{}},target={id:'target',geometry:f.geometry,properties:{}};
 assert.notEqual(record.candidate_geometry_sha256,digest(f.geometry));
 for(const fn of [retainedAdministrativeSourcePremises,retainedAdministrativeFragmentPremises]){
  const args={record,sourceCase,target,sourceScope:f.scope,candidate:f.geometry,fragment:f.geometry};
  assert.equal(fn(args).failed_premises.includes('original-full-candidate-binding'),false);
  assert.equal(fn({...args,sourceScope:{}}).failed_premises.includes('original-full-candidate-binding'),true);
 }
 const check=(scope=f.scope,value=f.geometry,expected=f.binding.geometry_sha256)=>originalAdministrativeCandidateHash({sourceScope:scope,componentId:'candidate',candidate:value,expected,kind:'geometry'});
 assert.equal(check(),true);assert.equal(check({},f.geometry,digest(f.geometry)),true);
 for(const mutate of [s=>s.original_candidate_canonical_bindings.push(structuredClone(s.original_candidate_canonical_bindings[0])),s=>s.original_candidate_canonical_bindings[0].component_id='foreign',s=>delete s.original_candidate_canonical_bindings[0].geometry_bytes_base64,s=>s.original_candidate_canonical_bindings[0].geometry_bytes_base64=Buffer.from('{}').toString('base64'),s=>s.original_candidate_canonical_bindings[0].derived_js_geometry_canonical_sha256='0'.repeat(64)]){
  const scope=structuredClone(f.scope);mutate(scope);assert.equal(check(scope),false);
 }
 const changed=structuredClone(f.geometry);changed.coordinates[0][0][0]=24;
 const rebound=structuredClone(f.scope);rebound.original_candidate_canonical_bindings[0].derived_js_geometry_canonical_sha256=digest(changed);
 assert.equal(check(rebound,changed),false);
});
test('whole product joins retain canonical and original pairs without duplicate feature matches',()=>{
 const f=fixture(),features=originalAdministrativeProductFeatures({sourceScope:f.scope,pin:f.pin,body:f.body});
 assert.equal(features.length,1);
 assert.equal(originalAdministrativeProductMatch(features[0],f.binding.feature_sha256,f.binding.geometry_sha256),true);
 assert.equal(originalAdministrativeProductMatch(features[0],digest(f.feature),digest(f.geometry)),true);
 assert.equal(originalAdministrativeProductMatch(features[0],f.binding.feature_sha256,digest(f.geometry)),false);
 assert.equal(originalAdministrativeProductMatch(features[0],digest(f.feature),f.binding.geometry_sha256),false);
 const missing=originalAdministrativeProductFeatures({sourceScope:{},pin:f.pin,body:f.body});
 assert.equal(originalAdministrativeProductMatch(missing[0],f.binding.feature_sha256,f.binding.geometry_sha256),false);
});
test('whole product preimages reject rebinding, wrong ordinal, duplicates and actual changed values',()=>{
 const f=fixture(),check=scope=>originalAdministrativeProductFeatures({sourceScope:scope,pin:f.pin,body:f.body});
 for(const mutate of [s=>s.original_administrative_canonical_bindings[0].source_sha256='0'.repeat(64),s=>s.original_administrative_canonical_bindings[0].feature_index=1,s=>s.original_administrative_canonical_bindings[0].feature_index=-1,s=>s.original_administrative_canonical_bindings.push(structuredClone(f.binding)),s=>delete s.original_administrative_canonical_bindings[0].geometry_bytes_base64,s=>s.original_administrative_canonical_bindings[0].feature_bytes_base64=Buffer.from('{}').toString('base64')]){
  const scope=structuredClone(f.scope);mutate(scope);assert.throws(()=>check(scope),/binding|preimage/);
 }
 for(const mutate of [x=>x.properties.name='foreign',x=>x.geometry.coordinates[0][0][0]=24]){
  const changed=structuredClone(f.feature);mutate(changed);
  const body=Buffer.from(JSON.stringify({type:'FeatureCollection',features:[changed]}));
  const scope=structuredClone(f.scope);scope.original_administrative_canonical_bindings[0].source_sha256=sha(body);
  assert.throws(()=>originalAdministrativeProductFeatures({sourceScope:scope,pin:f.pin,body}),/complete value/);
 }
 const scope=structuredClone(f.scope),other=structuredClone(f.feature);other.properties.extra='not in original';
 const raw=bytes(other);scope.original_administrative_canonical_bindings[0].feature_bytes_base64=raw.toString('base64');scope.original_administrative_canonical_bindings[0].feature_sha256=sha(raw);
 assert.throws(()=>check(scope),/complete value/);
 const otherProduct=originalAdministrativeProductFeatures({sourceScope:f.scope,pin:{path:'foreign.geojson'},body:f.body});
 assert.equal(originalAdministrativeProductMatch(otherProduct[0],f.binding.feature_sha256,f.binding.geometry_sha256),false);
});

test('original preimages and complete products retain byte admission limits',()=>{
 const f=fixture(),oversized='A'.repeat(Math.ceil(32*1024*1024/3)*4+1);
 const scope=structuredClone(f.scope);scope.original_administrative_canonical_bindings[0].feature_bytes_base64=oversized;
 assert.throws(()=>originalAdministrativeProductFeatures({sourceScope:scope,pin:f.pin,body:f.body}),/oversized/);
 assert.throws(()=>originalAdministrativeProductFeatures({sourceScope:{},pin:f.pin,body:Buffer.alloc(32*1024*1024+1)}),/byte bounds/);
 scope.original_candidate_canonical_bindings[0].geometry_bytes_base64=oversized;
 assert.equal(originalAdministrativeCandidateHash({sourceScope:scope,componentId:'candidate',candidate:f.geometry,expected:f.binding.geometry_sha256,kind:'geometry'}),false);
});

test('original alias decoding uses the same phase budget across products and native cases',()=>{
 const f=fixture(),budget=candidateBudget([],{reserveBytes:0,reserveDescriptors:0});
 admitAdministrativeOriginalPreimages(f.scope,budget);
 const once=budget.snapshot();assert.equal(once.accounted_descriptors,9);assert(once.accounted_bytes>0);
 admitAdministrativeOriginalPreimages(f.scope,budget,{products:false,componentIds:['candidate']});
 assert.equal(budget.snapshot().accounted_descriptors,12);
 const almostFull=candidateBudget([],{reserveBytes:256*1024*1024-1,reserveDescriptors:0});
 assert.throws(()=>admitAdministrativeOriginalPreimages(f.scope,almostFull),/Aggregate evidence/);
 const crowded=structuredClone(f.scope);crowded.original_administrative_canonical_bindings=Array(257).fill(f.binding);
 assert.throws(()=>admitAdministrativeOriginalPreimages(crowded,budget),/descriptor limit/);
});

test('registered original-hash programme preserves all prior methods and exact reviewed current vector',()=>{
 const catalogue=JSON.parse(fs.readFileSync(new URL('../coordination/engineering/selected-geography-effective-prevention-20261009/supported-programs.json',import.meta.url)));
 assert.equal(sha(canonical(catalogue.programs.slice(0,15))),'c0a9744587b0c0c78da2365008e3b2392deb18abbd9aa947209cb784fcb32ada');
 assert.equal(sha(canonical(catalogue.current_rebind_migrations.slice(0,1))),'b94c0b3a5d6d020b23465489049cf2c9299e12ee47b009850e81aec139c2a4ae');
 const approved=catalogue.programs[15];assert.equal(approved.accepted_head,'e2a1061921b1917ed48f0578940ee0494d02dc90');
 assert.equal(approved.independent_review_comment,6111057198);
 assert.equal(sha(canonical(approved.source_executed_code)),'d0155921b5a930c7d78dadbda85631bc261a92428c93fc52aee37c355d851412');
 assert.deepEqual(approved.source_executed_code,approved.native_executed_code);
 // Historical approval stays literal even after future caller changes.
 assert.equal(approved.source_executed_code.length,17);
});
