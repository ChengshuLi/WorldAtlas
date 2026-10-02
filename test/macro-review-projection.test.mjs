import test from 'node:test';
import assert from 'node:assert/strict';
import {validateMacroReviewProjection} from '../scripts/prepare-macro-review-projection.mjs';
const units=[{id:'c',name:'C',level:'continent',parent_id:null},{id:'s',name:'S',level:'subcontinent',parent_id:'c'},{id:'r',name:'R',level:'region',parent_id:'s'},{id:'a',name:'A',level:'area',parent_id:'r'},{id:'p',name:'P',level:'province',parent_id:'a'}];
const pins={hierarchy_sha256:'a'.repeat(64),location_index_sha256:'b'.repeat(64),footprints_sha256:'c'.repeat(64)};
function fixture(){
 const hierarchy=units.map(row=>row.id==='r'?{...row,id:'new:r',name:'New R'}:row.id==='a'?{...row,parent_id:'new:r'}:{...row}),locations=[{id:'l',name:'L',parent_id:'p',owner:'Owner'}];
 const projection={version:1,kind:'current-membership-projection',semantic_complete:false,regional_interiors_approved:false,historical_claims_transferred:false,geometry_changes:0,current_pins:{...pins},counts:{locations:1,groups:5,continent:1,subcontinent:1,region:1,area:1,province:1},locations:[{...locations[0],parent_chain:['p','a','new:r','s','c'],status:'open',semantic_status:'open'}],groups:hierarchy.map(row=>({...row,member_location_ids:['l'],branch_semantic_status:'open'})),archived_predecessors:[{...units[2]}],crosswalks:[{retired_units:[{...units[2]}],group_changes:[{id:'r',before:{...units[2]},after:null},{id:'new:r',before:null,after:{...hierarchy[2]}}]}]};
 return {projection,hierarchy,locations,currentPins:{...pins},baselineHierarchy:units,baselineLocations:locations.map(row=>({...row}))};
}
test('current projection preserves identities and keeps source inspection separate from semantic approval',()=>{
 const result=validateMacroReviewProjection(fixture());assert.equal(result.validated,true);assert.equal(result.semantic_complete,false);assert.equal(result.projection_only,true);assert.equal(result.baseline_inspections_preserved,true);
});
test('source-backed projection cannot change timeline facts or invent geographic review completion',()=>{
 for(const change of [{semantic_complete:true},{historical_claims_transferred:true},{regional_interiors_approved:true},{geometry_changes:1}]){const input=fixture();Object.assign(input.projection,change);assert.throws(()=>validateMacroReviewProjection(input),/contract/);}
});
test('current pins and exact counts must describe the actual geography',()=>{
 let input=fixture();input.currentPins.hierarchy_sha256='d'.repeat(64);assert.throws(()=>validateMacroReviewProjection(input),/stale geographic pins/);
 input=fixture();input.projection.counts.region=81;assert.throws(()=>validateMacroReviewProjection(input),/counts differ/);
});
test('complete current chains cannot be reordered or silently assigned different parents',()=>{
 for(const change of [row=>row.parent_chain.reverse(),row=>row.parent_id='new:r',row=>row.name='Invented',row=>row.owner='Changed',row=>row.status='approved']){const input=fixture();change(input.projection.locations[0]);assert.throws(()=>validateMacroReviewProjection(input),/stale or unapproved/);}
});
test('every retired or created parent has exact original archive and explicit crosswalk',()=>{
 for(const change of [input=>input.projection.archived_predecessors[0].name='Rewritten original',input=>input.projection.archived_predecessors=[],input=>input.projection.crosswalks[0].retired_units=[],input=>input.projection.crosswalks[0].group_changes=[]]){const input=fixture();change(input);assert.throws(()=>validateMacroReviewProjection(input));}
});
test('location conservation and exact parent descendant membership remain exhaustive',()=>{
 let input=fixture();input.baselineLocations.push({id:'lost'});assert.throws(()=>validateMacroReviewProjection(input),/loses original/);
 input=fixture();input.projection.groups[0].member_location_ids=[];assert.throws(()=>validateMacroReviewProjection(input),/stale group membership/);
 input=fixture();input.projection.groups[0].branch_semantic_status='approved';assert.throws(()=>validateMacroReviewProjection(input),/semantic approval/);
});
