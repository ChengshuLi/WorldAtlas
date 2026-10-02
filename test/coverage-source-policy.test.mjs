import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {coverageScope} from '../src/coverage-scope.js';
import {selectedSourcePolicyRoles,coverageSourcePolicy,sourcePolicyCoverageHTML,effectiveSourcePolicies} from '../src/source-policy-corrections.js';
const read=path=>JSON.parse(fs.readFileSync(new URL('../data/'+path,import.meta.url)));
const summary=read('source-policy-corrections/summary.json'),review=read('world-review.json'),base=read('location-policy.json');
const sourceBytes=fs.readFileSync(new URL('../data/source-policy-corrections/europe-v1.json.gz',import.meta.url)),bundle=JSON.parse(gunzipSync(sourceBytes));
const parents=new Map(read('hierarchy.json').map(unit=>[unit.id,unit]));
const owners={ITA:'Italy',ESP:'Spain',XKX:'Kosovo'};
const features=bundle.location_annotations.map(row=>({id:row.location_id,properties:{reference_owner:owners[row.profile_iso],parent_id:row.parent_chain[0]}}));

test('bounded source-policy projection is exact, reproducible, and small enough to deploy',()=>{
 assert.equal(summary.source_bundle.sha256,createHash('sha256').update(sourceBytes).digest('hex'));
 assert.equal(summary.source_bundle.bytes,sourceBytes.length);
 assert.ok(fs.statSync(new URL('../data/source-policy-corrections/summary.json',import.meta.url)).size<80000);
 assert.deepEqual(effectiveSourcePolicies(base,summary),effectiveSourcePolicies(base,bundle));
 const ids=new Map(summary.role_groups.flatMap(group=>group.location_ids.map(id=>[id,group])));
 assert.equal(ids.size,1001);
 for(const row of bundle.location_annotations){const group=ids.get(row.location_id);assert.equal(group.profile_iso,row.profile_iso);assert.equal(group.classification,row.classification);assert.equal(group.effective_source_role,row.after_annotation.effective_source_role);}
 assert.equal(summary.semantic_complete,false);assert.equal(summary.geography_changed,false);
 execFileSync('python',['scripts/prepare-source-policy-summary.py','--check'],{cwd:new URL('..',import.meta.url)});
});

test('coverage corrections count selected location identities on every applicable continent',()=>{
 const before=JSON.stringify(review);
 for(const [continent,total,spainAgricultural,spainMunicipal] of [['',1001,341,43],['Europe',989,333,39],['Africa',12,8,4]]){
  const scope=coverageScope(features,parents,review.territories,{continent});assert.equal(scope.features.length,total);
  const roles=selectedSourcePolicyRoles(scope.features,summary);const spanish=roles.get('ESP');
  assert.equal(spanish.get('spain-agricultural-district').count,spainAgricultural);assert.equal(spanish.get('spain-municipality').count,spainMunicipal);
  const profile=scope.profiles.find(row=>row.owner==='Spain');const corrected=coverageSourcePolicy(profile,summary,roles);
  assert.equal(corrected.roles.reduce((sum,row)=>sum+row.count,0),profile.selected_locations);
  assert.match(corrected.policy.role,/agricultural/);assert.equal(corrected.policy.source_policy_correction.local_granularity_approved,false);
 }
 assert.equal(JSON.stringify(review),before);
 const unrelated=review.territories.find(row=>row.owner==='Canada');assert.deepEqual(coverageSourcePolicy(unrelated,summary,new Map()),{policy:unrelated.policy,correction:null,roles:[]});
});

test('coverage presents corrected roles with collapsed evidence and explicitly retained earlier descriptions',()=>{
 const roles=selectedSourcePolicyRoles(features,summary);
 for(const iso of ['ITA','ESP','XKX']){
  const profile=review.territories.find(row=>row.iso===iso),presentation=coverageSourcePolicy(profile,summary,roles),output=sourcePolicyCoverageHTML(presentation,summary);
  assert.ok(output.startsWith(`<p><strong>Source role:</strong> ${presentation.policy.role}</p>`));
  assert.match(output,/<details><summary>Correction evidence and earlier source description<\/summary>/);
  assert.match(output,/Location scale and geographic boundaries remain under review/);
  assert.match(output,/<strong>Earlier description:<\/strong>/);
  assert.ok(output.includes(profile.policy.role));assert.ok(output.includes(presentation.policy.effective_level));
 }
 const malicious={policy:{role:'<script>invalid</script>',effective_level:'<bad>',reason:'<svg>'},correction:{evidence_ids:['bad'],before_policy:{role:'<old>',level:'ADM3'}},roles:[{role:'<bad>',count:1}]};
 const output=sourcePolicyCoverageHTML(malicious,{reviewed_at:'<today>',source_evidence:[{id:'bad',fact:'<img>',urls:['javascript:alert(1)','https://example.test/?x="']}]});
 assert.doesNotMatch(output,/<script>|<svg>|javascript:/);assert.match(output,/&lt;script&gt;/);assert.match(output,/&quot;/);
});

test('duplicate role IDs and stale policy assumptions cannot silently update coverage',()=>{
 const group=summary.role_groups[0];assert.throws(()=>selectedSourcePolicyRoles(features,{...summary,role_groups:[group,group]}),/Duplicate/);
 const profile=structuredClone(review.territories.find(row=>row.iso==='ITA'));profile.policy.role='A new unsourced role';assert.throws(()=>coverageSourcePolicy(profile,summary,new Map()),/changed since correction/);
});
