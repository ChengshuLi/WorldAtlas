import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {effectiveSourcePolicies,correctedLocationSourceRole} from '../src/source-policy-corrections.js';
const base=JSON.parse(fs.readFileSync(new URL('../data/location-policy.json',import.meta.url))),bundle=JSON.parse(gunzipSync(fs.readFileSync(new URL('../data/source-policy-corrections/europe-v1.json.gz',import.meta.url))));

test('sourced policy overlay changes exactly the three proven roles without mutating original source policy',()=>{
 const before=JSON.stringify(base),effective=effectiveSourcePolicies(base,bundle);assert.equal(JSON.stringify(base),before);assert.match(effective.countries.ITA.role,/labour systems/);assert.match(effective.countries.ESP.role,/agricultural/);assert.match(effective.countries.XKX.role,/districts/);
 for(const [iso,policy]of Object.entries(base.countries)){if(!['ITA','ESP','XKX'].includes(iso))assert.deepEqual(effective.countries[iso],policy);else{assert.deepEqual(effective.countries[iso].retained_administrative_selection,policy);assert.equal(effective.countries[iso].source_policy_correction.local_granularity_approved,false);}}
 assert.equal(createHash('sha256').update(bundle.retained_base_policy.raw_utf8).digest('hex'),bundle.retained_base_policy.sha256);assert.equal(bundle.retained_base_policy.raw_utf8,fs.readFileSync(new URL('../data/location-policy.json',import.meta.url),'utf8'));
 assert.deepEqual(effectiveSourcePolicies(effective,bundle),effective);
});

test('unrelated original-policy edits and duplicate correction identities require new review',()=>{
 const changed=structuredClone(base);changed.countries.ESP.role='Different unsourced role';assert.throws(()=>effectiveSourcePolicies(changed,bundle),/changed since correction/);
 assert.throws(()=>effectiveSourcePolicies(base,{...bundle,policy_corrections:[...bundle.policy_corrections,bundle.policy_corrections[0]]}),/Duplicate/);
 const invalid=structuredClone(bundle);delete invalid.policy_corrections[0].after_policy.effective_level;assert.throws(()=>effectiveSourcePolicies(base,invalid),/effective level/);
});

test('every crosswalked location exposes its individually supported role and unchanged source vintage',()=>{
 const counts={};for(const row of bundle.location_annotations){counts[row.classification]=(counts[row.classification]??0)+1;const corrected=correctedLocationSourceRole(row.location_id,bundle);assert.equal(corrected.reference_year,row.before_annotation.reference_year);assert.equal(corrected.source_id,row.before_annotation.source_id);assert.equal(corrected.license,row.before_annotation.license);assert.equal(corrected.local_granularity_approved,false);assert.ok(corrected.effective_source_role);}
 assert.deepEqual(counts,{'italy-labour-system':610,'spain-agricultural-district':341,'spain-municipality':43,'kosovo-district':7});assert.equal(correctedLocationSourceRole('not-an-affected-location',bundle),null);
 assert.throws(()=>correctedLocationSourceRole('same',{location_annotations:[{location_id:'same'},{location_id:'same'}]}),/Duplicate/);
});

test('Monaco and Luxembourg remain explicit stable-ID proposals with no hierarchy mutation',()=>{
 const units=new Map(JSON.parse(fs.readFileSync(new URL('../data/hierarchy.json',import.meta.url))).map(unit=>[unit.id,unit]));for(const proposal of bundle.area_label_proposals){assert.deepEqual(units.get(proposal.entity_id),proposal.before_group);assert.equal(proposal.status,'proposed-not-installed');assert.equal(proposal.member_location_ids.length,1);assert.equal(proposal.identity_changed,false);assert.equal(proposal.parent_changed,false);assert.equal(proposal.geometry_changed,false);assert.equal(proposal.granularity_exception_approved,false);}
});
